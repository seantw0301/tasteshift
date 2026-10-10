"""Fixture loading and the in-memory decision trace store."""
import json
from pathlib import Path
from typing import Dict, List

from .models import Event, Merchant

FIXTURES = Path(__file__).parent / "fixtures"


def load_merchants() -> List[Merchant]:
    return [Merchant(**m) for m in json.loads((FIXTURES / "merchants.json").read_text())]


def load_merchant(merchant_id: str = "merchant_souvenir_01") -> Merchant:
    for m in load_merchants():
        if m.id == merchant_id:
            return m
    raise KeyError(merchant_id)


def load_events() -> List[Event]:
    return [Event(**e) for e in json.loads((FIXTURES / "events.json").read_text())]


def get_event(event_id: str) -> Event:
    for e in load_events():
        if e.id == event_id:
            return e
    raise KeyError(event_id)


TRACES: Dict[str, dict] = {}
