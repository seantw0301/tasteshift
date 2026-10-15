import json

from app import qloo_gateway
from app.models import Event


def make_event(eid):
    return Event(id=eid, name="Test", theme="t", geo="Taipei", date="2026-11-14",
                 attendance=8000, attendance_source="synthetic", seed_concepts=["x"])


def write_anchors(tmp_path, monkeypatch, events):
    path = tmp_path / "anchors.json"
    path.write_text(json.dumps({"reference_panel": [{"entity_id": "P1", "name": "P1"}],
                                "events": events}))
    monkeypatch.setattr(qloo_gateway, "ANCHORS", path)
    qloo_gateway._ANCHOR_CACHE.clear()


def test_scores_are_min_max_normalized_within_the_call(tmp_path, monkeypatch):
    write_anchors(tmp_path, monkeypatch, {"evt_a": [{"concept": "anime", "entity_id": "A", "name": "A"},
                                                    {"concept": "kids", "entity_id": "B", "name": "B"}]})
    results = [{"entity_id": "A", "affinity": 0.9}, {"entity_id": "B", "affinity": 0.5},
               {"entity_id": "P1", "affinity": 0.7}]
    monkeypatch.setattr(qloo_gateway, "run_workflow", lambda *a, **k: {"status": "ok", "results": results})
    ev = {e.tag: e.affinity for e in qloo_gateway.anchor_evidence(make_event("evt_a"))}
    assert ev == {"anime": 1.0, "kids": 0.0}


def test_unscored_anchor_is_omitted_not_zero(tmp_path, monkeypatch):
    write_anchors(tmp_path, monkeypatch, {"evt_b": [{"concept": "anime", "entity_id": "A", "name": "A"},
                                                    {"concept": "kids", "entity_id": "B", "name": "B"}]})
    results = [{"entity_id": "A", "affinity": 0.9}, {"entity_id": "P1", "affinity": 0.2}]
    monkeypatch.setattr(qloo_gateway, "run_workflow", lambda *a, **k: {"status": "ok", "results": results})
    assert [e.tag for e in qloo_gateway.anchor_evidence(make_event("evt_b"))] == ["anime"]


def test_event_without_anchors_makes_no_call(tmp_path, monkeypatch):
    write_anchors(tmp_path, monkeypatch, {"evt_c": []})

    def fail(*a, **k):
        raise AssertionError("no rank call without anchors")

    monkeypatch.setattr(qloo_gateway, "run_workflow", fail)
    assert qloo_gateway.anchor_evidence(make_event("evt_c")) == []


def test_error_envelope_gives_no_evidence(tmp_path, monkeypatch):
    write_anchors(tmp_path, monkeypatch, {"evt_d": [{"concept": "anime", "entity_id": "A", "name": "A"}]})
    monkeypatch.setattr(qloo_gateway, "run_workflow", lambda *a, **k: {"status": "error", "results": []})
    assert qloo_gateway.anchor_evidence(make_event("evt_d")) == []
