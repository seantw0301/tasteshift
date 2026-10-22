import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from typing import Optional

from . import agent, agent_loop, llm, p2, pipeline, qloo_gateway
from .models import AblationRequest, PlanRequest
from .store import TRACES, get_event, load_events, load_merchant, load_merchants

app = FastAPI(title="TasteShift P0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"], allow_headers=["*"],
)


def _guard(fn, req):
    try:
        return fn(req)
    except KeyError as e:
        raise HTTPException(404, f"unknown event or merchant {e}")


@app.get("/api/fixtures")
def fixtures():
    qmode, note = qloo_gateway.mode()
    return {"merchant": load_merchant(), "merchants": load_merchants(), "events": load_events(),
            "qloo_mode": qmode, "qloo_note": note}


@app.post("/api/events/analyze")
def analyze(req: PlanRequest):
    try:
        event = get_event(req.event_id)
    except KeyError:
        raise HTTPException(404, "unknown event")
    return {"event": event, "event_dna": qloo_gateway.event_dna(event), "qloo_mode": qloo_gateway.mode()[0]}


@app.post("/api/qloo/recommend")
def qloo_recommend(req: PlanRequest):
    try:
        event = get_event(req.event_id)
    except KeyError:
        raise HTTPException(404, "unknown event")
    return qloo_gateway.recommend(event)


@app.post("/api/agent/stock")
def agent_stock(req: PlanRequest, grounded: bool = True):
    """Qloo-grounded agent: the LLM scores SKU fit from Qloo evidence, and the planner uses that fit."""
    try:
        event = get_event(req.event_id)
    except KeyError:
        raise HTTPException(404, "unknown event")
    evidence = _evidence(event, grounded)
    try:
        scores = agent.fit_scores(event, load_merchant(req.merchant_id).skus, evidence)
    except llm.LLMUnavailable as e:
        raise HTTPException(503, str(e))
    plan = pipeline.make_plan(req.model_copy(update={"qloo_on": True}), planner_aff=agent.planner_affinity(scores))
    return {"plan": plan, "reasons": {sid: v["reason"] for sid, v in scores.items()},
            "evidence_films": [e["name"] for e in evidence]}


def _evidence(event, grounded: bool) -> list:
    """Qloo recommended films as LLM evidence; empty when grounded is False."""
    if not grounded:
        return []
    rec = qloo_gateway.recommend(event)
    if rec.get("status") != "ok":
        return []
    return [{"name": r["name"], "affinity": r.get("affinity") or 0.0} for r in rec.get("results", [])]


@app.post("/api/evaluation/agent")
def agent_eval(req: PlanRequest):
    """Grounded vs ungrounded agent, both scored against the same synthetic hidden environments."""
    try:
        event = get_event(req.event_id)
    except KeyError:
        raise HTTPException(404, "unknown event")
    skus = load_merchant(req.merchant_id).skus
    try:
        g = agent.fit_scores(event, skus, _evidence(event, True))
        u = agent.fit_scores(event, skus, [])
    except llm.LLMUnavailable as e:
        raise HTTPException(503, str(e))
    return pipeline.agent_ablation(req, agent.planner_affinity(g), agent.planner_affinity(u))


@app.post("/api/optimize/stock")
def optimize(req: PlanRequest):
    return _guard(pipeline.make_plan, req)


@app.post("/api/optimize/plans")
def plans(req: PlanRequest):
    return _guard(pipeline.three_plans, req)


@app.post("/api/scenarios/replan")
def replan(req: PlanRequest):
    return _guard(pipeline.replan, req)


@app.post("/api/evaluation/ablation")
def ablation(req: AblationRequest):
    return _guard(pipeline.ablation, req)


@app.get("/api/decisions/{decision_id}/audit")
def audit(decision_id: str):
    if decision_id not in TRACES:
        raise HTTPException(404, "unknown decision; re-run the plan to regenerate its trace")
    return TRACES[decision_id]


@app.get("/api/decisions/{decision_id}/purchase-order.csv", response_class=PlainTextResponse)
def purchase_order(decision_id: str):
    if decision_id not in TRACES:
        raise HTTPException(404, "unknown decision; re-run the plan first")
    return PlainTextResponse(p2.purchase_order_csv(decision_id), media_type="text/csv")


@app.post("/api/sales/simulate")
def sales_simulate(req: p2.SalesRequest):
    return _guard(p2.simulate_sales, req)


@app.post("/api/sales/restock")
def sales_restock(req: p2.SalesRequest):
    return _guard(p2.restock, req)


@app.post("/api/calibration")
def calibration(req: p2.SalesRequest):
    return _guard(p2.calibrate, req)


@app.post("/api/restock/multiday")
def restock_multiday(req: PlanRequest):
    return _guard(p2.multiday, req)


class AgentRequest(BaseModel):
    request: str = Field(min_length=3, max_length=500)
    qloo: bool = True


def _agent_arm(request: str, qloo: bool, event_hint: Optional[str] = None) -> dict:
    try:
        return agent_loop.run_agent(request, qloo=qloo, event_hint=event_hint)
    except llm.LLMUnavailable as e:
        raise HTTPException(503, str(e))


@app.post("/api/agent/run")
def agent_run(req: AgentRequest):
    """One tool-calling agent run: natural-language request -> per-SKU fit -> optimizer plan."""
    arm = _agent_arm(req.request, req.qloo)
    try:
        get_event(arm["event_id"])
    except KeyError:
        raise HTTPException(422, f"agent chose an unknown event: {arm['event_id']}")
    plan = pipeline.make_plan(PlanRequest(event_id=arm["event_id"], qloo_on=True),
                              planner_aff=agent.planner_affinity(arm["scores"]))
    return {"event_id": arm["event_id"], "qloo": arm["qloo"], "trace": arm["trace"],
            "reasons": {k: v["reason"] for k, v in arm["scores"].items()},
            "evidence_films": arm["evidence_films"], "plan": plan}


@app.post("/api/agent/compare")
def agent_compare(req: AgentRequest):
    """Same request, two arms: with Qloo tools and without. Both plans are scored on the same hidden environments."""
    with_q = _agent_arm(req.request, True)
    try:
        get_event(with_q["event_id"])
    except KeyError:
        raise HTTPException(422, f"agent chose an unknown event: {with_q['event_id']}")
    without_q = _agent_arm(req.request, False, event_hint=with_q["event_id"])
    evaluation = pipeline.agent_ablation(PlanRequest(event_id=with_q["event_id"]),
                                         agent.planner_affinity(with_q["scores"]),
                                         agent.planner_affinity(without_q["scores"]))
    def arm_view(arm):
        return {"trace": arm["trace"], "reasons": {k: v["reason"] for k, v in arm["scores"].items()},
                "cited": {k: v["cited"] for k, v in arm["scores"].items()},
                "signals": {k: v.get("signals", []) for k, v in arm["scores"].items()},
                "evidence_films": arm["evidence_films"], "evidence_signals": arm.get("evidence_signals", []),
                "citations": arm["citations"]}
    return {"event_id": with_q["event_id"], "with_qloo": arm_view(with_q), "without_qloo": arm_view(without_q),
            "evaluation": evaluation}
