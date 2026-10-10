from app import p2, pipeline
from app.models import PlanRequest, Scenario
from app.store import load_merchant

A = "evt_anime_music"


def test_three_plans_respect_constraints_and_order_by_risk():
    for m in ("merchant_souvenir_01", "merchant_juice_01", "merchant_sausage_01"):
        plans = pipeline.three_plans(PlanRequest(event_id=A, merchant_id=m))
        skus = {s.id: s for s in load_merchant(m).skus}
        for p in plans.values():
            assert p.total_cost <= p.budget
            for r in p.skus:
                assert r.stock_qty == 0 or skus[r.sku_id].moq <= r.stock_qty <= skus[r.sku_id].max_stock
        assert plans["conservative"].total_cost <= plans["balanced"].total_cost <= plans["aggressive"].total_cost


def test_recipes_cover_stock_with_waste():
    p = pipeline.make_plan(PlanRequest(event_id=A, merchant_id="merchant_juice_01"))
    cups = next(i for i in p.ingredients if i.ingredient == "cup+lid")
    assert cups.quantity >= sum(r.stock_qty for r in p.skus)
    assert p.capacity_note


def test_capacity_never_adds_demand():
    req = PlanRequest(event_id=A, merchant_id="merchant_sausage_01")
    cap = load_merchant("merchant_sausage_01").capacity
    d = pipeline.build_demand(req)[6]
    assert d.sum(axis=1).max() <= cap.units_per_hour * cap.hours + 1e-6


def test_replan_explains_rain():
    r = pipeline.replan(PlanRequest(event_id="evt_family_fair", scenario=Scenario(rain=True)))
    assert r["why"] and r["changes"] and r["after"].total_cost <= r["after"].budget
    wand = next(s for s in r["after"].skus if s.sku_id == "SKU11")
    assert wand.demand_p50 < next(s for s in r["before"].skus if s.sku_id == "SKU11").demand_p50


def test_restock_and_calibration():
    req = p2.SalesRequest(event_id=A, elapsed=0.5)
    req.sales = p2.simulate_sales(req)["sales"]
    r = p2.restock(req)
    assert r["restock_cost"] <= r["restock_budget"] and r["origin"] == "simulation"
    c = p2.calibrate(req)
    assert all(0.5 <= w <= 2 for w in c["weight_overrides"].values())
    assert all(row["weight"] >= 1 for row in c["skus"] if row["sold_out"])
    pipeline.make_plan(PlanRequest(event_id=A, weight_overrides=c["weight_overrides"]))


def test_sales_csv():
    assert p2.parse_sales_csv("sku_id,units_sold\nSKU01,12\nSKU02, 3\n") == {"SKU01": 12, "SKU02": 3}


def test_multiday_and_purchase_order():
    r = p2.multiday(PlanRequest(event_id="evt_lunar_market", merchant_id="merchant_newyear_01"))
    assert r["days"] == 5 and r["day1_cost"] <= r["budget"]
    assert all(len(s["orders"]) == 5 and s["orders"][0]["firm"] for s in r["skus"])
    p = pipeline.make_plan(PlanRequest(event_id=A, merchant_id="merchant_juice_01"))
    assert "ingredient" in p2.purchase_order_csv(p.decision_id)
