from fastapi.testclient import TestClient

from app import agent, llm, main
from app.models import Event, SKU
from app.store import load_merchant


def sku(i):
    return SKU(id=i, name=i, price=1, unit_cost=1, salvage_value=0, moq=1, lot_size=1, max_stock=50,
               concept_tags=["anime"], base_weight=1.0, **{})


EVENT = Event(id="evt_anime_music", name="Anime Music Festival", theme="anime", geo="Taipei",
              date="2026-11-14", attendance=8000, attendance_source="synthetic", seed_concepts=["anime"])


def test_fit_is_clipped_and_missing_sku_stays_unknown(monkeypatch):
    monkeypatch.setattr(llm, "chat_json", lambda messages, timeout=60: {"scores": [
        {"sku_id": "A", "fit": 1.7, "reason": "strong"}, {"sku_id": "Z", "fit": 0.3, "reason": "unknown id"}]})
    out = agent.fit_scores(EVENT, [sku("A"), sku("B")], [{"name": "Kingdom", "affinity": 0.9}])
    assert out["A"]["fit"] == 1.0 and out["A"]["reason"] == "strong"
    assert out["B"]["fit"] is None and "Z" not in out


def test_prompt_carries_qloo_evidence_and_sku_tags():
    msgs = agent._prompt(EVENT, [sku("A")], [{"name": "Kingdom", "affinity": 0.9}])
    assert "Kingdom" in msgs[1]["content"] and "anime" in msgs[1]["content"]


def test_missing_llm_config_is_503(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    client = TestClient(main.app)
    r = client.post("/api/agent/stock", json={"event_id": "evt_anime_music"})
    assert r.status_code == 503


def test_agent_endpoint_uses_fit_in_planner(monkeypatch):
    merchant = load_merchant()
    scores = {"llm": True}
    def fake(messages, timeout=60):
        return {"scores": [{"sku_id": s.id, "fit": 0.9 if i == 0 else 0.1, "reason": "r"}
                           for i, s in enumerate(merchant.skus)]}
    monkeypatch.setattr(llm, "chat_json", fake)
    monkeypatch.setattr(main.qloo_gateway, "recommend", lambda ev: {"status": "ok", "results": [
        {"name": "Kingdom", "affinity": 0.92}]})
    client = TestClient(main.app)
    r = client.post("/api/agent/stock", json={"event_id": "evt_anime_music"})
    assert r.status_code == 200
    body = r.json()
    assert body["evidence_films"] == ["Kingdom"]
    statuses = {row["sku_id"]: row["affinity_status"] for row in body["plan"]["skus"]}
    assert statuses[merchant.skus[0].id] == "agent_fit"
    assert body["reasons"][merchant.skus[0].id] == "r"
