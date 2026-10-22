"""Qloo-grounded SKU fit: the LLM scores each SKU's fit to the event audience, citing Qloo evidence.

Output is validated and clipped; a SKU the model does not score stays unknown (None), never zero.
"""
from typing import Dict, List, Optional

from . import llm
from .models import Event, SKU

SYSTEM = (
    "You score how well each souvenir SKU fits an event's audience. Use only the evidence given. "
    "Return JSON: {\"scores\": [{\"sku_id\": str, \"fit\": number between 0 and 1, \"reason\": short string}]}. "
    "Give one entry per SKU. Do not invent Qloo data."
)


def _prompt(event: Event, skus: List[SKU], evidence: List[dict]) -> List[dict]:
    ev_lines = [f"- {e['name']} (Qloo affinity {e['affinity']:.2f})" for e in evidence] or ["- none"]
    sku_lines = [f"- {s.id}: {s.name} (concept tags: {', '.join(s.concept_tags) or 'none'})" for s in skus]
    user = "\n".join([
        f"Event: {event.name}. Theme: {event.theme}. City: {event.geo}. Seed concepts: {', '.join(event.seed_concepts)}.",
        "Qloo recommended films for this audience (relative within this list):",
        *ev_lines,
        "SKUs:",
        *sku_lines,
    ])
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def fit_scores(event: Event, skus: List[SKU], evidence: List[dict]) -> Dict[str, dict]:
    """Return {sku_id: {"fit": float|None, "reason": str}} for every SKU."""
    raw = llm.chat_json(_prompt(event, skus, evidence))
    out: Dict[str, dict] = {s.id: {"fit": None, "reason": "not scored by the model"} for s in skus}
    for item in raw.get("scores", []):
        sid = item.get("sku_id")
        if sid not in out:
            continue
        try:
            fit = min(1.0, max(0.0, float(item["fit"])))
        except (KeyError, TypeError, ValueError):
            continue
        out[sid] = {"fit": round(fit, 4), "reason": str(item.get("reason", ""))[:300]}
    return out


def planner_affinity(scores: Dict[str, dict]) -> Dict[str, tuple]:
    """Map agent fit to the engine's (affinity, status, evidence_ids) shape."""
    return {sid: ((v["fit"], "agent_fit", []) if v["fit"] is not None else (None, "unknown", []))
            for sid, v in scores.items()}
