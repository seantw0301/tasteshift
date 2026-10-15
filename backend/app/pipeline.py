"""End-to-end plan, Qloo On/Off ablation, what-if replans and the decision trace."""
import hashlib
import json
import math
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import engine, qloo_gateway
from .models import AblationRequest, IngredientNeed, Merchant, Plan, PlanRequest, Scenario, SkuPlan
from .store import TRACES, get_event, load_merchant


def _blocked(merchant: Merchant) -> Dict[str, str]:
    return {
        s.id: f"license '{s.requires_license}' not held"
        for s in merchant.skus
        if s.requires_license and s.requires_license not in merchant.licenses_held
    }


def _apply_scenario(merchant: Merchant, sc: Optional[Scenario]) -> Tuple[list, float, np.ndarray, List[str]]:
    """Return (adjusted SKUs, attendance multiplier, per-SKU demand multiplier, human-readable notes)."""
    skus, mult, att, notes = merchant.skus, np.ones(len(merchant.skus)), 1.0, []
    if sc is None:
        return skus, att, mult, notes
    if sc.rain:
        att *= engine.ASSUMPTIONS["rain_attendance_factor"]
        mult = mult * np.array([s.rain_factor for s in skus])
        hit = [s.name for s in skus if s.rain_factor < 0.75]
        notes.append(f"Rain: crowd x{engine.ASSUMPTIONS['rain_attendance_factor']}"
                     + (f"; weather-sensitive items cut further ({', '.join(hit)})" if hit else ""))
    if sc.attendance_factor != 1:
        att *= sc.attendance_factor
        notes.append(f"Attendance x{sc.attendance_factor}")
    if sc.competitor_factor != 1:
        att *= sc.competitor_factor
        notes.append(f"Rival stalls: booth traffic x{sc.competitor_factor}")
    if sc.cost_factor != 1 or sc.price_factor != 1 or sc.moq_factor != 1:
        skus = [s.model_copy(update={
            "unit_cost": round(s.unit_cost * sc.cost_factor, 2),
            "price": round(s.price * sc.price_factor, 2),
            "moq": max(1, int(round(s.moq * sc.moq_factor / s.lot_size)) * s.lot_size),
        }) for s in skus]
        if sc.cost_factor != 1:
            notes.append(f"Unit cost x{sc.cost_factor}")
        if sc.price_factor != 1:
            notes.append(f"Price x{sc.price_factor} (demand response to price is not modelled)")
        if sc.moq_factor != 1:
            notes.append(f"Supplier MOQ x{sc.moq_factor}")
    return skus, att, mult, notes


def _ingredients(merchant: Merchant, qty: Dict[str, int]) -> List[IngredientNeed]:
    need: Dict[Tuple[str, str], list] = {}
    for sku_id, lines in merchant.recipes.items():
        for ln in lines:
            if qty.get(sku_id):
                row = need.setdefault((ln.ingredient, ln.unit), [0.0, []])
                row[0] += qty[sku_id] * ln.qty_per_unit * (1 + ln.waste_rate)
                row[1].append(sku_id)
    # Countable items are rounded up; you cannot buy part of a cup.
    return [IngredientNeed(ingredient=k[0], unit=k[1], for_skus=v[1],
                           quantity=math.ceil(v[0]) if k[1] == "pc" else round(v[0], 2))
            for k, v in sorted(need.items())]


def build_demand(req: PlanRequest, aff_override: Optional[Dict[str, Optional[float]]] = None,
                 beta: Optional[float] = None, seed: Optional[int] = None, planner_aff: Optional[dict] = None):
    """Shared demand construction for planning and for hidden-environment evaluation."""
    merchant, event = load_merchant(req.merchant_id), get_event(req.event_id)
    skus, att_mult, sku_mult, notes = _apply_scenario(merchant, req.scenario)
    attendance = req.attendance or event.attendance
    dna = qloo_gateway.event_dna(event)
    aff_full = {s.id: engine.sku_affinity(s, dna) for s in skus}
    if planner_aff is not None:
        aff_full = {s.id: planner_aff.get(s.id, (None, "unknown", [])) for s in skus}
    aff = aff_override if aff_override is not None else {
        k: (v[0] if req.qloo_on else None) for k, v in aff_full.items()}
    if req.weight_overrides:
        skus = [s.model_copy(update={"base_weight": s.base_weight * req.weight_overrides.get(s.id, 1.0)}) for s in skus]
    share = engine.shares(skus, aff, engine.ASSUMPTIONS["affinity_tilt_beta"] if beta is None else beta)
    mean = engine.total_units(merchant, attendance) * att_mult * share * sku_mult
    demand = engine.scenarios(mean, req.seed if seed is None else seed)
    cap_note = None
    if merchant.capacity:
        c = merchant.capacity
        raw = demand.sum()
        demand = engine.apply_capacity(demand, c.units_per_hour, c.hourly_profile)
        cap_note = (f"{c.label}: {c.units_per_hour:g}/hour over {c.hours} h; "
                    f"{(1 - demand.sum() / raw) * 100:.1f}% of demand lost to peak-hour queues")
    return merchant, event, skus, attendance, dna, aff_full, demand, notes, cap_note


def make_plan(req: PlanRequest, planner_aff: Optional[dict] = None) -> Plan:
    merchant, event, skus, attendance, dna, aff_full, demand, notes, cap_note = build_demand(req, planner_aff=planner_aff)
    budget = req.budget if req.budget is not None else merchant.budget
    qmode, fallback = qloo_gateway.mode()
    blocked = _blocked(merchant)
    qty = engine.optimize(skus, demand, budget, blocked, req.risk)

    rows = []
    for i, s in enumerate(skus):
        d, q = demand[:, i], qty[s.id]
        a, status, ev = aff_full[s.id] if req.qloo_on else (None, "not_used", [])
        rows.append(SkuPlan(
            sku_id=s.id, name=s.name, affinity=a, affinity_status=status, evidence_ids=ev,
            demand_p10=round(float(np.percentile(d, 10)), 1),
            demand_p50=round(float(np.percentile(d, 50)), 1),
            demand_p90=round(float(np.percentile(d, 90)), 1),
            stock_qty=q, cost=q * s.unit_cost,
            expected_profit=round(engine.sku_profit(s, q, d), 0) if q else 0.0,
            stockout_risk=round(float(np.mean(d > q)), 3) if q else None,
            leftover_units=round(float(np.mean(np.maximum(q - d, 0))), 1),
            excluded_reason=blocked.get(s.id),
        ))

    sc = req.scenario.model_dump() if req.scenario else None
    key = json.dumps([event.id, merchant.id, attendance, budget, req.qloo_on, req.seed, req.risk, sc,
                      sorted(req.weight_overrides.items()), engine.MODEL_VERSION, qmode, planner_aff is not None])
    decision_id = "dec_" + hashlib.sha256(key.encode()).hexdigest()[:12]
    plan = Plan(
        decision_id=decision_id, event_id=event.id, merchant_id=merchant.id, risk=req.risk,
        qloo_on=req.qloo_on, qloo_mode=qmode, attendance=attendance, budget=budget,
        total_cost=sum(r.cost for r in rows), expected_profit=sum(r.expected_profit for r in rows),
        skus=rows, event_dna=dna if req.qloo_on else [], assumptions=engine.ASSUMPTIONS,
        scenario_notes=notes, ingredients=_ingredients(merchant, qty), capacity_note=cap_note,
        metrics=engine.evaluate(skus, qty, demand),
    )
    TRACES[decision_id] = {
        "decision_id": decision_id,
        "model_version": engine.MODEL_VERSION,
        "scenario_seed": req.seed,
        "n_scenarios": engine.N_SCENARIOS,
        "risk": {"posture": req.risk, **engine.RISK[req.risk]},
        "scenario": {"levers": sc, "effects": notes},
        "qloo": {"on": req.qloo_on, "mode": qmode, "fallback_note": fallback,
                 "evidence": [e.model_dump() for e in plan.event_dna]},
        "inputs": [
            {"field": "event.attendance", "value": attendance,
             "origin": "merchant_input" if req.attendance else event.attendance_source},
            {"field": "merchant.budget", "value": budget, "origin": "merchant_input" if req.budget is not None else "synthetic"},
            {"field": "merchant.booth_reach", "value": merchant.booth_reach, "origin": "model_estimate"},
            {"field": "merchant.conversion", "value": merchant.conversion, "origin": "model_estimate"},
            {"field": "merchant.units_per_buyer", "value": merchant.units_per_buyer, "origin": "model_estimate"},
            {"field": "sku catalog (price, cost, MOQ, max stock)", "value": f"{len(skus)} SKUs", "origin": "synthetic"},
            {"field": "sku -> concept tag mapping", "value": "proxy mapping, not Qloo product IDs", "origin": "merchant_input"},
            {"field": "event DNA affinities", "value": f"{len(plan.event_dna)} tags", "origin": "synthetic" if qmode == "mock" else "qloo_live"},
            {"field": "recipes / capacity", "value": cap_note or ("recipes" if merchant.recipes else "n/a"), "origin": "synthetic"},
            {"field": "calibration weights", "value": req.weight_overrides or "none", "origin": "historical_data" if req.weight_overrides else "unknown"},
        ],
        "assumptions": {k: {"value": v, "origin": "model_estimate"} for k, v in engine.ASSUMPTIONS.items()},
        "constraints": {
            "budget": budget, "total_cost": plan.total_cost,
            "rule": "per SKU: qty = 0 or MOQ <= qty <= max_stock, in lot_size steps; sum(cost) <= budget",
            "license_exclusions": blocked, "capacity": cap_note,
        },
        "ingredients": [i.model_dump() for i in plan.ingredients],
        "skus": [dict(r.model_dump(), mapping=s.concept_tags, moq=s.moq, max_stock=s.max_stock, unit_cost=s.unit_cost)
                 for r, s in zip(rows, skus)],
        "limits": "Affinity is a cultural-relevance signal, not sales, conversion or market share.",
    }
    return plan


def hidden_demand(req: PlanRequest, k: int = 0) -> np.ndarray:
    """One hidden 'true' demand environment: different tilt plus taste noise the planner never sees."""
    merchant, event = load_merchant(req.merchant_id), get_event(req.event_id)
    dna = qloo_gateway.event_dna(event)
    rng = np.random.default_rng(req.seed + 1000 + k)
    true_aff = {}
    for s in merchant.skus:
        a = engine.sku_affinity(s, dna)[0]
        base = 0.5 if a is None else a
        true_aff[s.id] = float(np.clip(base + rng.normal(0, engine.ASSUMPTIONS["truth_taste_noise"]), 0, 1))
    return build_demand(req, aff_override=true_aff, beta=engine.ASSUMPTIONS["truth_tilt_beta"],
                        seed=req.seed + 2000 + k)[6]


def ablation(req: AblationRequest) -> dict:
    """Score the Qloo On and Qloo Off plans against the same hidden demand environments."""
    base = PlanRequest(event_id=req.event_id, merchant_id=req.merchant_id, attendance=req.attendance,
                       budget=req.budget, seed=req.seed)
    plans = {on: make_plan(base.model_copy(update={"qloo_on": on})) for on in (True, False)}
    skus = load_merchant(req.merchant_id).skus
    stock = {on: {r.sku_id: r.stock_qty for r in p.skus} for on, p in plans.items()}
    runs = {True: [], False: []}
    for k in range(engine.N_ENVIRONMENTS):
        hidden = hidden_demand(base, k)
        for on in (True, False):
            runs[on].append(engine.evaluate(skus, stock[on], hidden))

    res = {}
    for on, p in plans.items():
        avg = {m: round(float(np.mean([r[m] for r in runs[on]])), 3) for m in runs[on][0]}
        res["qloo_on" if on else "qloo_off"] = dict(
            avg, decision_id=p.decision_id, total_cost=p.total_cost, stock=stock[on])
    diffs = [a["expected_profit"] - b["expected_profit"] for a, b in zip(runs[True], runs[False])]
    on, off = res["qloo_on"], res["qloo_off"]
    return {
        "event_id": req.event_id, "seed": req.seed, **res,
        "delta": {k: round(on[k] - off[k], 3) for k in ("expected_profit", "avg_stockout_rate", "expected_leftover_units", "lost_sales_units")},
        "changed_skus": [s.id for s in skus if on["stock"][s.id] != off["stock"][s.id]],
        "n_environments": engine.N_ENVIRONMENTS,
        "qloo_on_win_rate": round(float(np.mean([d > 0 for d in diffs])), 2),
        "profit_delta_range": [round(min(diffs), 0), round(max(diffs), 0)],
        "environment": "synthetic",
        "caveat": ("Hidden demand is simulated and assumes cultural affinity moves demand. In mock mode the affinity "
                   "signal is also synthetic, so this shows the mechanism, not measured real-world lift."),
    }


def three_plans(req: PlanRequest) -> dict:
    """Conservative / Balanced / Aggressive under identical inputs."""
    return {r: make_plan(req.model_copy(update={"risk": r})) for r in engine.RISK}


def replan(req: PlanRequest) -> dict:
    """Recompute under a what-if scenario with the same constraints and say what changed and why."""
    before = make_plan(req.model_copy(update={"scenario": None}))
    after = make_plan(req)
    changes = []
    for b, a in zip(before.skus, after.skus):
        if b.stock_qty != a.stock_qty:
            changes.append({"sku_id": a.sku_id, "name": a.name, "before": b.stock_qty, "after": a.stock_qty,
                            "demand_p50_before": b.demand_p50, "demand_p50_after": a.demand_p50})
    return {"before": before, "after": after, "changes": changes, "why": after.scenario_notes,
            "profit_change": round(after.expected_profit - before.expected_profit, 0)}
