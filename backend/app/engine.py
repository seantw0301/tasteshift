"""Affinity, demand scenarios and the stock optimizer. All numbers come from code, never an LLM."""
from typing import Dict, List, Optional, Tuple

import numpy as np

from .models import Merchant, QlooEvidence, SKU

MODEL_VERSION = "p0-0.1"
N_SCENARIOS = 4000
N_ENVIRONMENTS = 40  # hidden demand environments used by the On/Off ablation
# Explicit, editable demand assumptions (origin: model_estimate).
ASSUMPTIONS = {
    "affinity_tilt_beta": 2.0,   # how strongly the planner lets affinity tilt SKU share
    "sku_demand_cv": 0.35,       # per-SKU demand noise
    "attendance_cv": 0.15,       # shared crowd-size shock
    "truth_tilt_beta": 1.4,      # hidden environment's tilt (differs from the planner's on purpose)
    "truth_taste_noise": 0.25,   # hidden per-SKU taste noise the planner cannot see
    "rain_attendance_factor": 0.7,  # crowd kept when it rains
}
# Risk postures: lam penalises downside (mean minus worst-10% profit), gamma penalises lost sales.
RISK = {
    "conservative": {"lam": 0.5, "gamma": 0.0},
    "balanced": {"lam": 0.0, "gamma": 0.0},
    "aggressive": {"lam": 0.0, "gamma": 0.6},
}


def sku_affinity(sku: SKU, dna: List[QlooEvidence]) -> Tuple[Optional[float], str, List[str]]:
    """Mean affinity over the SKU's proxy concept tags. Tags without evidence are unknown and skipped."""
    by_tag = {e.tag: e for e in dna if e.affinity is not None}
    hits = [by_tag[t] for t in sku.concept_tags if t in by_tag]
    if not hits:
        return None, "unknown", []
    status = "known" if len(hits) == len(sku.concept_tags) else "partial"
    return float(np.mean([h.affinity for h in hits])), status, [h.id for h in hits]


def shares(skus: List[SKU], aff: Dict[str, Optional[float]], beta: float) -> np.ndarray:
    """SKU share of booth demand. Unknown affinity gets a neutral tilt (1.0), not a penalty."""
    known = [a for a in aff.values() if a is not None]
    center = float(np.mean(known)) if known else 0.0
    w = np.array([
        s.base_weight * (np.exp(beta * (aff[s.id] - center)) if aff.get(s.id) is not None else 1.0)
        for s in skus
    ])
    return w / w.sum()


def total_units(m: Merchant, attendance: int) -> float:
    return attendance * m.booth_reach * m.conversion * m.units_per_buyer


def scenarios(mean: np.ndarray, seed: int) -> np.ndarray:
    """Demand matrix (scenarios x SKUs): lognormal SKU noise times a shared attendance shock."""
    rng = np.random.default_rng(seed)
    cv, acv = ASSUMPTIONS["sku_demand_cv"], ASSUMPTIONS["attendance_cv"]
    s, a = np.sqrt(np.log1p(cv**2)), np.sqrt(np.log1p(acv**2))
    crowd = rng.lognormal(-a**2 / 2, a, size=(N_SCENARIOS, 1))
    noise = rng.lognormal(-s**2 / 2, s, size=(N_SCENARIOS, len(mean)))
    return mean * crowd * noise


def apply_capacity(demand: np.ndarray, per_hour: float, profile: List[float]) -> np.ndarray:
    """Cap servable demand hour by hour (grill / prep line). Lost peak-hour demand is not recoverable."""
    total = demand.sum(axis=1, keepdims=True)
    served = sum(np.minimum(total * w, per_hour) for w in profile)
    return demand * np.divide(served, total, out=np.ones_like(total), where=total > 0)


def sku_profit(s: SKU, q: int, d: np.ndarray) -> float:
    sold = np.minimum(d, q)
    return float(np.mean(s.price * sold + s.salvage_value * (q - sold) - s.unit_cost * q))


def sku_objective(s: SKU, q: int, d: np.ndarray, lam: float, gamma: float) -> float:
    """Expected profit adjusted for risk posture. With lam = gamma = 0 this is plain expected profit."""
    sold = np.minimum(d, q)
    profit = s.price * sold + s.salvage_value * (q - sold) - s.unit_cost * q
    mean = float(profit.mean())
    if lam:
        tail = np.sort(profit)[: max(1, len(profit) // 10)].mean()
        mean -= lam * (mean - float(tail))
    if gamma:
        mean -= gamma * (s.price - s.unit_cost) * float(np.mean(np.maximum(d - q, 0)))
    return mean


def optimize(skus: List[SKU], demand: np.ndarray, budget: float, blocked: Dict[str, str],
             risk: str = "balanced") -> Dict[str, int]:
    """Greedy marginal gain per dollar under budget, MOQ (0 or >= MOQ), lot size and max stock."""
    r = RISK[risk]
    q = {s.id: 0 for s in skus}
    cur = {s.id: sku_objective(s, 0, demand[:, i], **r) for i, s in enumerate(skus)}
    spent = 0.0
    while True:
        best = None
        for i, s in enumerate(skus):
            if s.id in blocked:
                continue
            step = s.moq if q[s.id] == 0 else s.lot_size
            nq = q[s.id] + step
            cost = step * s.unit_cost
            if nq > s.max_stock or spent + cost > budget:
                continue
            val = sku_objective(s, nq, demand[:, i], **r)
            gain = val - cur[s.id]
            if gain > 0 and (best is None or gain / cost > best[0]):
                best = (gain / cost, s.id, step, cost, val)
        if best is None:
            return q
        q[best[1]] += best[2]
        cur[best[1]] = best[4]
        spent += best[3]


def evaluate(skus: List[SKU], q: Dict[str, int], demand: np.ndarray) -> dict:
    """Score a stock plan against a demand matrix."""
    profit = np.zeros(demand.shape[0])
    leftover = stockouts = stocked = 0.0
    for i, s in enumerate(skus):
        d, qty = demand[:, i], q[s.id]
        sold = np.minimum(d, qty)
        profit += s.price * sold + s.salvage_value * (qty - sold) - s.unit_cost * qty
        leftover += float(np.mean(qty - sold))
        if qty > 0:
            stocked += 1
            stockouts += float(np.mean(d > qty))
    return {
        "expected_profit": round(float(profit.mean()), 0),
        "profit_p10": round(float(np.percentile(profit, 10)), 0),
        "profit_p90": round(float(np.percentile(profit, 90)), 0),
        "avg_stockout_rate": round(stockouts / stocked, 3) if stocked else None,
        "expected_leftover_units": round(leftover, 1),
        "lost_sales_units": round(float(np.mean(np.maximum(demand - np.array([q[s.id] for s in skus]), 0).sum(axis=1))), 1),
    }
