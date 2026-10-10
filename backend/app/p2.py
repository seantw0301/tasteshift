"""P2: in-event restock from sales, post-event calibration, multi-day restock, purchase orders.

Everything here runs on simulated or user-pasted numbers. No POS or supplier system is connected.
"""
import csv
import io
import math
from typing import Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field

from . import engine, pipeline
from .models import PlanRequest
from .store import TRACES, get_event, load_merchant

PRIOR_WEIGHT = 0.25  # the forecast counts as much as a quarter of the event's sales (model_estimate)


class SalesRequest(PlanRequest):
    elapsed: float = 0.5  # share of the event already over
    sales: Dict[str, int] = Field(default_factory=dict)
    restock_budget: Optional[float] = None


def parse_sales_csv(text: str) -> Dict[str, int]:
    """Accepts `sku_id,units_sold` lines, with or without a header."""
    out = {}
    for row in csv.reader(io.StringIO(text.strip())):
        if len(row) >= 2 and row[1].strip().lstrip("-").isdigit():
            out[row[0].strip()] = max(0, int(row[1]))
    return out


def simulate_sales(req: SalesRequest) -> dict:
    """Synthetic 'POS' reading: one draw from a hidden environment, capped by what was stocked."""
    plan = pipeline.make_plan(req)
    draw = pipeline.hidden_demand(req, k=7)[0]
    sales = {r.sku_id: int(min(r.stock_qty, round(d * req.elapsed))) for r, d in zip(plan.skus, draw)}
    return {"sales": sales, "origin": "synthetic", "note": "Simulated sales, not a real POS feed."}


def restock(req: SalesRequest) -> dict:
    plan = pipeline.make_plan(req)
    merchant, _, skus, _, _, _, demand, _, _ = pipeline.build_demand(req)
    e = min(max(req.elapsed, 0.05), 0.95)
    w = e / (e + PRIOR_WEIGHT)
    net, rows, revenue = np.zeros_like(demand), [], 0.0
    for i, (s, r) in enumerate(zip(skus, plan.skus)):
        sold = min(req.sales.get(s.id, 0), r.stock_qty) if r.stock_qty else 0
        prior = float(demand[:, i].mean())
        run_rate = sold / e
        sold_out = r.stock_qty > 0 and sold >= r.stock_qty
        if r.stock_qty == 0:
            updated, basis = prior, "not stocked, forecast unchanged"
        elif sold_out:
            updated, basis = max(prior, run_rate), "sold out, so sales only give a lower bound"
        else:
            updated, basis = (1 - w) * prior + w * run_rate, f"forecast blended with run rate (weight {w:.2f})"
        on_hand = r.stock_qty - sold
        remaining = demand[:, i] * (updated / prior if prior else 1) * (1 - e)
        net[:, i] = np.maximum(remaining - on_hand, 0)
        revenue += sold * s.price
        rows.append({"sku_id": s.id, "name": s.name, "stocked": r.stock_qty, "sold": sold, "on_hand": on_hand,
                     "sold_out": sold_out, "forecast_total": round(prior, 1), "updated_total": round(updated, 1),
                     "remaining_p50": round(float(np.percentile(remaining, 50)), 1), "basis": basis})
    budget = req.restock_budget if req.restock_budget is not None else plan.budget - plan.total_cost + revenue
    qty = engine.optimize(skus, net, budget, pipeline._blocked(merchant), req.risk)
    for row, s in zip(rows, skus):
        row["restock_qty"] = qty[s.id]
        row["restock_cost"] = qty[s.id] * s.unit_cost
    return {"decision_id": plan.decision_id, "elapsed": e, "restock_budget": round(budget, 0),
            "restock_cost": sum(r["restock_cost"] for r in rows), "revenue_so_far": revenue, "skus": rows,
            "origin": "simulation",
            "note": "Restock budget defaults to unspent budget plus revenue so far. Sales are pasted or simulated, not a live POS feed."}


def calibrate(req: SalesRequest) -> dict:
    """Compare final sales with the forecast and propose damped base-weight corrections for the next event."""
    plan = pipeline.make_plan(req)
    demand = pipeline.build_demand(req)[6]
    rows, errs, weights = [], [], {}
    e = min(max(req.elapsed, 0.05), 1.0)
    for i, r in enumerate(plan.skus):
        if r.stock_qty == 0 or r.sku_id not in req.sales:
            continue
        sold, forecast = req.sales[r.sku_id], float(demand[:, i].mean())
        sold_out = sold >= r.stock_qty
        actual = round(sold / e, 1)  # projected to the full event when it is not over yet
        ratio = actual / forecast if forecast else 1.0
        w = float(np.clip(math.sqrt(max(ratio, 0.01)), 0.5, 2.0))
        if sold_out:
            w = max(w, 1.0)  # true demand was at least this; never correct downward on a sell-out
        else:
            errs.append(abs(actual - forecast) / forecast)
        weights[r.sku_id] = round(w, 2)
        rows.append({"sku_id": r.sku_id, "name": r.name, "forecast": round(forecast, 1), "actual": actual,
                     "sold": sold, "sold_out": sold_out, "weight": round(w, 2)})
    return {"skus": rows, "weight_overrides": weights,
            "mape_uncensored": round(float(np.mean(errs)), 3) if errs else None,
            "origin": "simulation", "projected": e < 1,
            "note": "Sales are projected to the full event at the current run rate. Weights are the square root of actual/forecast, clipped to 0.5-2. One event is weak evidence; sell-outs are treated as lower bounds."}


def _lots(q: float, s) -> int:
    if q <= 0:
        return 0
    return max(s.moq, int(math.ceil(q / s.lot_size)) * s.lot_size)


def multiday(req: PlanRequest) -> dict:
    """Day-by-day order-up-to plan with shelf life and last-day clearance. Day 1 is firm; later days are expected values."""
    merchant, event = load_merchant(req.merchant_id), get_event(req.event_id)
    days = event.days
    curve = event.day_curve or [1 / days] * days
    base = pipeline.build_demand(req)
    skus, total = base[2], base[6]  # total: event demand at one day's attendance
    budget = req.budget if req.budget is not None else merchant.budget
    blocked = pipeline._blocked(merchant)
    out, day1_cost = [], 0.0
    plans = []
    for i, s in enumerate(skus):
        life = min(s.shelf_life_days or 1, days)  # nothing outlives the event
        mean_total = total[:, i].mean() * days
        daily = [engine.scenarios(np.array([mean_total * c]), req.seed + 50 * (d + 1) + i)[:, 0] for d, c in enumerate(curve)]
        levels = []
        for d in range(days):
            carry = life > 1 and d < days - 1
            over = 0.02 * s.unit_cost if carry else s.unit_cost - s.salvage_value
            frac = min((s.price - s.unit_cost) / (s.price - s.unit_cost + over), 0.9)
            levels.append(0 if s.id in blocked else float(np.quantile(daily[d], frac)))
        plans.append((s, life, daily, levels))
        day1_cost += _lots(levels[0], s) * s.unit_cost
    scale = min(1.0, budget / day1_cost) if day1_cost else 1.0

    for s, life, daily, levels in plans:
        n = len(daily[0])
        ages = [np.zeros(n) for _ in range(life)]  # ages[0] = bought today
        orders, sold_all, expired_all, profit = [], 0.0, 0.0, np.zeros(n)
        for d in range(days):
            inv = sum(ages)
            target = levels[d] * (scale if d == 0 else 1.0)
            want = np.maximum(target - inv, 0)
            order = np.array([_lots(x, s) for x in np.round(want, 0)]) if d else np.full(n, _lots(float(want[0]), s) if scale == 1 else int(want[0] // s.lot_size) * s.lot_size)
            ages[0] = ages[0] + order
            left = daily[d].copy()
            for a in range(life - 1, -1, -1):  # sell oldest first
                take = np.minimum(ages[a], left)
                ages[a] = ages[a] - take
                left -= take
            sold = daily[d] - left
            last = d == days - 1
            expired = ages[-1] if not last else sum(ages)
            profit += s.price * sold - s.unit_cost * order + (s.salvage_value * expired if last else 0)
            sold_all += float(sold.mean())
            expired_all += float(expired.mean())
            ages = [np.zeros(n)] + ages[:-1]
            orders.append({"day": d + 1, "firm": d == 0, "order_mean": round(float(order.mean()), 1),
                           "order_p10": float(np.percentile(order, 10)), "order_p90": float(np.percentile(order, 90)),
                           "demand_p50": round(float(np.percentile(daily[d], 50)), 1)})
        out.append({"sku_id": s.id, "name": s.name, "shelf_life_days": s.shelf_life_days, "orders": orders,
                    "expected_sold": round(sold_all, 1), "expected_unsold_or_expired": round(expired_all, 1),
                    "expected_profit": round(float(profit.mean()), 0), "excluded_reason": blocked.get(s.id)})
    return {"event_id": event.id, "merchant_id": merchant.id, "days": days, "day_curve": curve,
            "day1_cost": round(sum(o["orders"][0]["order_mean"] * s.unit_cost for o, s in zip(out, skus)), 0),
            "budget": budget, "skus": out, "expected_profit": sum(o["expected_profit"] for o in out),
            "origin": "simulation",
            "note": "Daily replenishment with no lead time. Budget is enforced on the firm day-1 order only; later orders are expected values that depend on actual sales."}


def purchase_order_csv(decision_id: str) -> str:
    """Supplier hand-off: a plain CSV, since no supplier system is connected."""
    t = TRACES[decision_id]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["type", "item", "quantity", "unit", "unit_cost", "line_cost"])
    for s in t["skus"]:
        if s["stock_qty"]:
            w.writerow(["sku", s["name"], s["stock_qty"], "pc", s["unit_cost"], s["cost"]])
    for i in t["ingredients"]:
        w.writerow(["ingredient", i["ingredient"], i["quantity"], i["unit"], "", ""])
    return buf.getvalue()
