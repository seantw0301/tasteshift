from app import pipeline
from app.models import AblationRequest, PlanRequest
from app.store import load_merchant

A, F = "evt_anime_music", "evt_family_fair"


def plan(event, **kw):
    return pipeline.make_plan(PlanRequest(event_id=event, **kw))


def test_deterministic():
    assert plan(A).model_dump() == plan(A).model_dump()


def test_constraints():
    m = {s.id: s for s in load_merchant().skus}
    for ev in (A, F):
        for on in (True, False):
            p = plan(ev, qloo_on=on)
            assert p.total_cost <= p.budget
            for r in p.skus:
                s = m[r.sku_id]
                assert r.stock_qty == 0 or s.moq <= r.stock_qty <= s.max_stock
                assert (r.stock_qty - s.moq) % s.lot_size == 0 or r.stock_qty == 0
            assert next(r for r in p.skus if r.sku_id == "SKU12").stock_qty == 0  # unlicensed


def test_same_crowd_different_culture_changes_mix():
    a, f = plan(A), plan(F)
    assert a.attendance == f.attendance and a.budget == f.budget
    assert [r.stock_qty for r in a.skus] != [r.stock_qty for r in f.skus]


def test_qloo_off_ignores_event_culture():
    assert [r.stock_qty for r in plan(A, qloo_on=False).skus] == [r.stock_qty for r in plan(F, qloo_on=False).skus]


def test_unknown_affinity_is_none_not_zero():
    tote = next(r for r in plan(A).skus if r.sku_id == "SKU09")
    assert tote.affinity is None and tote.affinity_status == "unknown"


def test_ablation_runs_and_is_labeled():
    r = pipeline.ablation(AblationRequest(event_id=A))
    assert r["environment"] == "synthetic" and "qloo_on" in r and "qloo_off" in r
