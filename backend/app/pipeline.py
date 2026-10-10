"""End-to-end plan, Qloo On/Off ablation and the decision trace."""
import hashlib
import json
from typing import Dict, Optional

import numpy as np

from . import engine, qloo_gateway
from .models import AblationRequest, Plan, PlanRequest, SkuPlan
from .store import TRACES, get_event, load_merchant


def _blocked(merchant) -> Dict[str, str]:
    return {
        s.id: f"license '{s.requires_license}' not held"
        for s in merchant.skus
        if s.requires_license and s.requires_license not in merchant.licenses_held
    }


def make_plan(req: PlanRequest) -> Plan:
    merchant, event = load_merchant(), get_event(req.event_id)
    attendance = req.attendance or event.attendance
    budget = req.budget if req.budget is not None else merchant.budget
    skus = merchant.skus
    dna = qloo_gateway.event_dna(event)
    qmode, fallback = qloo_gateway.mode()

    aff_full = {s.id: engine.sku_affinity(s, dna) for s in skus}
    aff: Dict[str, Optional[float]] = {k: (v[0] if req.qloo_on else None) for k, v in aff_full.items()}
    beta = engine.ASSUMPTIONS["affinity_tilt_beta"]
    mean = engine.total_units(merchant, attendance) * engine.shares(skus, aff, beta)
    demand = engine.scenarios(mean, req.seed)
    blocked = _blocked(merchant)
    qty = engine.optimize(skus, demand, budget, blocked)

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

    key = json.dumps([event.id, attendance, budget, req.qloo_on, req.seed, engine.MODEL_VERSION, qmode])
    decision_id = "dec_" + hashlib.sha256(key.encode()).hexdigest()[:12]
    plan = Plan(
        decision_id=decision_id, event_id=event.id, qloo_on=req.qloo_on, qloo_mode=qmode,
        attendance=attendance, budget=budget,
        total_cost=sum(r.cost for r in rows),
        expected_profit=sum(r.expected_profit for r in rows),
        skus=rows, event_dna=dna if req.qloo_on else [], assumptions=engine.ASSUMPTIONS,
    )
    TRACES[decision_id] = {
        "decision_id": decision_id,
        "model_version": engine.MODEL_VERSION,
        "scenario_seed": req.seed,
        "n_scenarios": engine.N_SCENARIOS,
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
        ],
        "assumptions": {k: {"value": v, "origin": "model_estimate"} for k, v in engine.ASSUMPTIONS.items()},
        "constraints": {
            "budget": budget, "total_cost": plan.total_cost,
            "rule": "per SKU: qty = 0 or MOQ <= qty <= max_stock, in lot_size steps; sum(cost) <= budget",
            "license_exclusions": blocked,
        },
        "skus": [dict(r.model_dump(), mapping=s.concept_tags, moq=s.moq, max_stock=s.max_stock)
                 for r, s in zip(rows, skus)],
        "limits": "Affinity is a cultural-relevance signal, not sales, conversion or market share.",
    }
    return plan


def ablation(req: AblationRequest) -> dict:
    """Score the Qloo On and Qloo Off plans against one shared hidden demand environment."""
    merchant, event = load_merchant(), get_event(req.event_id)
    attendance = req.attendance or event.attendance
    skus = merchant.skus
    plans = {on: make_plan(PlanRequest(event_id=req.event_id, attendance=req.attendance,
                                       budget=req.budget, qloo_on=on, seed=req.seed)) for on in (True, False)}

    # Hidden truth: tilt differs from the planner's and adds taste noise the planner never sees.
    # Averaged over several independently drawn environments so one lucky draw cannot decide it.
    dna = qloo_gateway.event_dna(event)
    stock = {on: {r.sku_id: r.stock_qty for r in p.skus} for on, p in plans.items()}
    runs = {True: [], False: []}
    for k in range(engine.N_ENVIRONMENTS):
        rng = np.random.default_rng(req.seed + 1000 + k)
        true_aff = {}
        for s in skus:
            a = engine.sku_affinity(s, dna)[0]
            base = 0.5 if a is None else a
            true_aff[s.id] = float(np.clip(base + rng.normal(0, engine.ASSUMPTIONS["truth_taste_noise"]), 0, 1))
        mean = engine.total_units(merchant, attendance) * engine.shares(skus, true_aff, engine.ASSUMPTIONS["truth_tilt_beta"])
        hidden = engine.scenarios(mean, req.seed + 2000 + k)
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
        "event_id": event.id, "seed": req.seed, **res,
        "delta": {k: round(on[k] - off[k], 3) for k in ("expected_profit", "avg_stockout_rate", "expected_leftover_units", "lost_sales_units")},
        "changed_skus": [s.id for s in skus if on["stock"][s.id] != off["stock"][s.id]],
        "n_environments": engine.N_ENVIRONMENTS,
        "qloo_on_win_rate": round(float(np.mean([d > 0 for d in diffs])), 2),
        "profit_delta_range": [round(min(diffs), 0), round(max(diffs), 0)],
        "environment": "synthetic",
        "caveat": ("Hidden demand is simulated and assumes cultural affinity moves demand. In mock mode the affinity "
                   "signal is also synthetic, so this shows the mechanism, not measured real-world lift."),
    }
