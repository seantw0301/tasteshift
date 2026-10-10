"""Fixture loading and the in-memory decision trace store."""
import json
from pathlib import Path
from typing import Dict, List

from .models import Event, Merchant

FIXTURES = Path(__file__).parent / "fixtures"


def load_merchant() -> Merchant:
    return Merchant(**json.loads((FIXTURES / "merchant.json").read_text()))


def load_events() -> List[Event]:
    return [Event(**e) for e in json.loads((FIXTURES / "events.json").read_text())]


def get_event(event_id: str) -> Event:
    for e in load_events():
        if e.id == event_id:
            return e
    raise KeyError(event_id)


TRACES: Dict[str, dict] = {}
