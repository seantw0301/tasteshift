import json

from fastapi.testclient import TestClient

from app import agent_loop, llm, main, qloo_gateway
from app.store import load_merchant


def tool_call(i, name, args):
    return {"id": f"c{i}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


def scripted(responses):
    """Return a fake chat_tools that yields the given assistant messages in order."""
    it = iter(responses)

    def fake(messages, tools, timeout=90.0):
        return next(it)
    return fake


def all_skus_submit(event_id, reason="r"):
    skus = load_merchant().skus
    return {"event_id": event_id, "scores": [{"sku_id": s.id, "fit": 0.5, "reason": reason} for s in skus]}


def stub_qloo(monkeypatch):
    monkeypatch.setattr(qloo_gateway, "find_tags", lambda q, limit=5: {"status": "ok", "results": [
        {"id": "urn:tag:genre:qloo:anime", "name": "Anime"}]})
    monkeypatch.setattr(qloo_gateway, "recommend", lambda ev: {"status": "ok", "results": [
        {"entity_id": "E1", "name": "Kingdom", "affinity": 0.9}, {"entity_id": "E2", "name": "Your Name", "affinity": 0.8}]})
    monkeypatch.setattr(qloo_gateway, "run_workflow", lambda wf, payload, timeout=30: {"status": "ok", "results": [
        {"name": "Kingdom", "affinity": 0.99}, {"name": "Your Name", "affinity": 0.5}]})


def test_qloo_arm_runs_tools_in_order_then_submits(monkeypatch):
    stub_qloo(monkeypatch)
    monkeypatch.setattr(llm, "chat_tools", scripted([
        {"content": None, "tool_calls": [tool_call(1, "list_events", {})]},
        {"content": None, "tool_calls": [tool_call(2, "find_tags", {"query": "anime"})]},
        {"content": None, "tool_calls": [tool_call(3, "recommend_films", {"event_id": "evt_anime_music"})]},
        {"content": None, "tool_calls": [tool_call(4, "rank_films", {"event_id": "evt_anime_music", "entity_ids": ["E1", "E2"]})]},
        {"content": None, "tool_calls": [tool_call(5, "submit_plan", all_skus_submit("evt_anime_music"))]},
    ]))
    out = agent_loop.run_agent("anime festival in Taipei, 8000 people", qloo=True)
    assert out["event_id"] == "evt_anime_music"
    assert [t["tool"] for t in out["trace"] if "tool" in t] == ["list_events", "find_tags", "recommend_films", "rank_films", "submit_plan"]
    assert out["evidence_films"] == ["Kingdom", "Your Name"]
    assert len(out["scores"]) == len(load_merchant().skus)


def test_rank_rejects_ids_not_from_recommend(monkeypatch):
    stub_qloo(monkeypatch)
    monkeypatch.setattr(llm, "chat_tools", scripted([
        {"content": None, "tool_calls": [tool_call(1, "recommend_films", {"event_id": "evt_anime_music"})]},
        {"content": None, "tool_calls": [tool_call(2, "rank_films", {"event_id": "evt_anime_music", "entity_ids": ["X", "Y"]})]},
        {"content": None, "tool_calls": [tool_call(3, "submit_plan", all_skus_submit("evt_anime_music"))]},
    ]))
    out = agent_loop.run_agent("anime", qloo=True)
    rank_step = next(t for t in out["trace"] if t.get("tool") == "rank_films")
    assert "error" in rank_step["result"]


def test_plain_arm_cannot_call_qloo_tools(monkeypatch):
    stub_qloo(monkeypatch)
    monkeypatch.setattr(llm, "chat_tools", scripted([
        {"content": None, "tool_calls": [tool_call(1, "find_tags", {"query": "anime"})]},
        {"content": None, "tool_calls": [tool_call(2, "submit_plan", all_skus_submit("evt_anime_music"))]},
    ]))
    out = agent_loop.run_agent("anime", qloo=False, event_hint="evt_anime_music")
    first = out["trace"][0]
    assert first["tool"] == "find_tags" and "error" in first["result"]
    assert out["qloo"] is False


def test_compare_endpoint_scores_both_arms(monkeypatch):
    stub_qloo(monkeypatch)
    def fake(messages, tools, timeout=90.0):
        names = {t["function"]["name"] for t in tools}
        if "find_tags" in names:
            if not any(m.get("role") == "tool" for m in messages):
                return {"content": None, "tool_calls": [tool_call(1, "list_events", {})]}
            return {"content": None, "tool_calls": [tool_call(2, "submit_plan", all_skus_submit("evt_anime_music", "with"))]}
        if not any(m.get("role") == "tool" for m in messages):
            return {"content": None, "tool_calls": [tool_call(1, "list_events", {})]}
        return {"content": None, "tool_calls": [tool_call(2, "submit_plan", all_skus_submit("evt_anime_music", "without"))]}
    monkeypatch.setattr(llm, "chat_tools", fake)
    r = TestClient(main.app).post("/api/agent/compare", json={"request": "anime festival in Taipei"})
    assert r.status_code == 200
    body = r.json()
    assert body["with_qloo"]["reasons"][load_merchant().skus[0].id] == "with"
    assert body["without_qloo"]["reasons"][load_merchant().skus[0].id] == "without"
    assert "delta_profit" in body["evaluation"]


def test_submit_with_unknown_sku_ids_is_rejected_and_model_retries(monkeypatch):
    stub_qloo(monkeypatch)
    bad = {"event_id": "evt_anime_music", "scores": [{"sku_id": "anime-standees", "fit": 0.9, "reason": "x"}]}
    monkeypatch.setattr(llm, "chat_tools", scripted([
        {"content": None, "tool_calls": [tool_call(1, "submit_plan", bad)]},
        {"content": None, "tool_calls": [tool_call(2, "submit_plan", all_skus_submit("evt_anime_music"))]},
    ]))
    out = agent_loop.run_agent("anime", qloo=False, event_hint="evt_anime_music")
    assert len(out["scores"]) == len(load_merchant().skus)
    assert out["trace"][0]["result"].startswith("no sku_id matched")


def test_citations_are_checked_against_recommended_films(monkeypatch):
    stub_qloo(monkeypatch)
    skus = load_merchant().skus
    scores = [{"sku_id": skus[0].id, "fit": 0.8, "reason": "r", "cited_films": ["Kingdom", "Made Up Film"]}]
    scores += [{"sku_id": s.id, "fit": 0.5, "reason": "r", "cited_films": []} for s in skus[1:]]
    monkeypatch.setattr(llm, "chat_tools", scripted([
        {"content": None, "tool_calls": [tool_call(1, "recommend_films", {"event_id": "evt_anime_music"})]},
        {"content": None, "tool_calls": [tool_call(2, "submit_plan", {"event_id": "evt_anime_music", "scores": scores})]},
    ]))
    out = agent_loop.run_agent("anime", qloo=True)
    assert out["scores"][skus[0].id]["cited"] == ["Kingdom"]
    assert out["citations"] == {"valid": 1, "invalid": 1, "skus_with_valid_citation": 1}
