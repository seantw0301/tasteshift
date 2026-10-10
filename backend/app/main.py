import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import pipeline, qloo_gateway
from .models import AblationRequest, PlanRequest
from .store import TRACES, get_event, load_events, load_merchant

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
        raise HTTPException(404, f"unknown event {e}")


@app.get("/api/fixtures")
def fixtures():
    qmode, note = qloo_gateway.mode()
    return {"merchant": load_merchant(), "events": load_events(), "qloo_mode": qmode, "qloo_note": note}


@app.post("/api/events/analyze")
def analyze(req: PlanRequest):
    try:
        event = get_event(req.event_id)
    except KeyError:
        raise HTTPException(404, "unknown event")
    return {"event": event, "event_dna": qloo_gateway.event_dna(event), "qloo_mode": qloo_gateway.mode()[0]}


@app.post("/api/optimize/stock")
def optimize(req: PlanRequest):
    return _guard(pipeline.make_plan, req)


@app.post("/api/evaluation/ablation")
def ablation(req: AblationRequest):
    return _guard(pipeline.ablation, req)


@app.get("/api/decisions/{decision_id}/audit")
def audit(decision_id: str):
    if decision_id not in TRACES:
        raise HTTPException(404, "unknown decision; re-run the plan to regenerate its trace")
    return TRACES[decision_id]
