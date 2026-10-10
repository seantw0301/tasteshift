"""Qloo Evidence Gateway.

Mock mode serves the synthetic fixture and labels every record `synthetic` with a `mock:` id,
so nothing here can be mistaken for a real Qloo ID. Live mode is intentionally not implemented
until an API key is available and the request shape is verified against Qloo's docs; asking for
it degrades to mock with an explicit fallback note instead of pretending to be live.
"""
import json
import os
from typing import Dict, List, Optional, Tuple

from .models import Event, QlooEvidence
from .store import FIXTURES

_CACHE: Dict[str, List[QlooEvidence]] = {}


def mode() -> Tuple[str, Optional[str]]:
    if os.environ.get("QLOO_API_KEY"):
        return "mock", "QLOO_API_KEY is set but the live client is not implemented yet; serving synthetic fixture"
    return "mock", None


def event_dna(event: Event) -> List[QlooEvidence]:
    if event.id in _CACHE:
        return _CACHE[event.id]
    _, fallback = mode()
    raw = json.loads((FIXTURES / "qloo_mock.json").read_text()).get(event.id, {})
    out = [
        QlooEvidence(
            id=f"mock:ev:{event.id}:{tag}",
            tag_id=f"mock:tag:{tag}",
            tag=tag,
            affinity=aff,
            origin="synthetic",
            query_id=f"mock:q:{event.id}",
            note=fallback,
        )
        for tag, aff in sorted(raw.items(), key=lambda kv: -kv[1])
    ]
    _CACHE[event.id] = out
    return out
