import json

from app import qloo_gateway
from app.models import Event


def make_event(seed):
    return Event(id="evt_test", name="Test", theme="t", geo="Taipei", date="2026-11-14",
                 attendance=8000, attendance_source="synthetic", seed_concepts=seed)


def write_candidates(tmp_path, monkeypatch, confirmed):
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps({"reviewed": True, "confirmed": confirmed, "candidates": {}}))
    monkeypatch.setattr(qloo_gateway, "CANDIDATES", path)
    qloo_gateway._REC_CACHE.clear()


def test_only_confirmed_urns_are_sent(tmp_path, monkeypatch):
    write_candidates(tmp_path, monkeypatch, {"anime": "urn:tag:genre:qloo:anime"})
    sent = {}

    def fake(workflow, payload, timeout=30):
        sent.update(payload)
        return {"status": "ok", "results": [], "result_count": 0}

    monkeypatch.setattr(qloo_gateway, "run_workflow", fake)
    qloo_gateway.recommend(make_event(["anime", "j-pop"]))
    assert sent["signal_tags"] == ["urn:tag:genre:qloo:anime"]
    assert sent["signal_location"] == "Taipei" and sent["target_type"] == "movie"


def test_no_confirmed_tags_is_an_error_and_makes_no_call(tmp_path, monkeypatch):
    write_candidates(tmp_path, monkeypatch, {})

    def fail(*a, **k):
        raise AssertionError("harness must not be called without confirmed tags")

    monkeypatch.setattr(qloo_gateway, "run_workflow", fail)
    env = qloo_gateway.recommend(make_event(["anime"]))
    assert env["status"] == "error" and env["error"]["code"] == "NO_TAGS"


def test_results_are_english_only_and_capped_at_ten(tmp_path, monkeypatch):
    write_candidates(tmp_path, monkeypatch, {"anime": "urn:tag:genre:qloo:anime"})
    names = ["佐々木希", "Kingdom"] + [f"Film {i}" for i in range(12)] + ["蔡依林"]
    results = [{"entity_id": str(i), "name": n, "affinity": 0.9} for i, n in enumerate(names)]
    monkeypatch.setattr(qloo_gateway, "run_workflow",
                        lambda *a, **k: {"status": "ok", "results": results, "result_count": len(results)})
    env = qloo_gateway.recommend(make_event(["anime"]))
    assert all(not qloo_gateway.NON_LATIN_NAME.search(r["name"]) for r in env["results"])
    assert len(env["results"]) == 10 and env["result_count"] == 10
    assert env["results"][0]["name"] == "Kingdom"


def test_ok_result_is_cached_per_event(tmp_path, monkeypatch):
    write_candidates(tmp_path, monkeypatch, {"anime": "urn:tag:genre:qloo:anime"})
    calls = []

    def fake(*a, **k):
        calls.append(1)
        return {"status": "ok", "results": [{"entity_id": "1", "name": "Kingdom", "affinity": 1.0}], "result_count": 1}

    monkeypatch.setattr(qloo_gateway, "run_workflow", fake)
    qloo_gateway.recommend(make_event(["anime"]))
    qloo_gateway.recommend(make_event(["anime"]))
    assert len(calls) == 1
