import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import PlainTextResponse

from . import p2, pipeline, qloo_gateway
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
