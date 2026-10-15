"""Qloo Evidence Gateway.

Mock mode serves the synthetic fixture and labels every record `synthetic` with a `mock:` id,
so nothing here can be mistaken for a real Qloo ID.

Live calls go through the hackathon-supported surface, `qloo exec <workflow>` from
@qloo/qloo-harness, which reads the credential from its own private config or QLOO_API_KEY.
Only what the hackathon kit documents is wired: the result envelope and `find_tags`.
Affinity stays synthetic until the `rank` input schema is checked against `qloo exec --help`.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple

from .models import Event, QlooEvidence
from .store import FIXTURES

_CACHE: Dict[str, List[QlooEvidence]] = {}


HACKATHON_BASE_URL = "https://hackathon.api.qloo.com"
ENVELOPE_STATUSES = {"ok", "empty", "needs_input", "partial", "degraded", "error"}


def _bin() -> str:
    return os.environ.get("QLOO_BIN", "qloo")


def harness_installed() -> bool:
    return shutil.which(_bin()) is not None


def _error(code: str, summary: str, retryable: bool = False) -> dict:
    return {"status": "error", "summary": summary, "results": [], "result_count": 0,
            "error": {"code": code, "retryable": retryable, "recovery": None}}


def run_workflow(workflow: str, payload: dict, timeout: int = 30) -> dict:
    """Run one harness workflow. Always returns a result envelope; never raises, never retries."""
    if not harness_installed():
        return _error("HARNESS_MISSING", "qloo harness not found; npm install --global @qloo/qloo-harness")
    env = dict(os.environ)
    env.setdefault("QLOO_BASE_URL", HACKATHON_BASE_URL)
    env.setdefault("QLOO_TRUSTED_BASE_URL", HACKATHON_BASE_URL)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(payload, f)
    try:
        proc = subprocess.run([_bin(), "exec", workflow, "--input-file", f.name],
                              capture_output=True, text=True, timeout=timeout, env=env)
        envelope = json.loads(proc.stdout)
    except subprocess.TimeoutExpired:
        return _error("TIMEOUT", f"{workflow} timed out after {timeout}s", retryable=True)
    except (ValueError, OSError) as e:
        return _error("BAD_OUTPUT", f"{workflow} returned no JSON envelope ({type(e).__name__})")
    finally:
        os.unlink(f.name)
    if not isinstance(envelope, dict) or envelope.get("status") not in ENVELOPE_STATUSES:
        return _error("UNKNOWN", f"{workflow} returned an unrecognised envelope")
    return envelope


def find_tags(query: str, limit: int = 5) -> dict:
    """Candidate Qloo tags for a concept. Candidates need review before use; they are not matches."""
    return run_workflow("find_tags", {"query": query, "limit": limit})


RECOMMEND_TARGET = "movie"  # one target type per call; affinity is only comparable within one call
NON_LATIN_NAME = re.compile(r"[\u3000-\u9fff\uac00-\ud7af\uff00-\uffef]")  # CJK, Hangul, fullwidth forms
CANDIDATES = FIXTURES / "qloo_tag_candidates.json"
_REC_CACHE: Dict[str, dict] = {}


def _concept_urns(concepts: List[str]) -> List[str]:
    """Owner-confirmed URN per concept. Concepts without a confirmed URN are skipped, never guessed."""
    try:
        confirmed = json.loads(CANDIDATES.read_text()).get("confirmed", {})
    except (OSError, ValueError):
        return []
    return [confirmed[c] for c in concepts if c in confirmed]


def recommend(event: Event) -> dict:
    """One recommend call over all of the event's concept tags and its location. Ok results are cached per event."""
    if event.id in _REC_CACHE:
        return _REC_CACHE[event.id]
    urns = _concept_urns(event.seed_concepts)
    if not urns:
        return _error("NO_TAGS", f"no tag URNs for {event.id}; run scripts/qloo_resolve_tags.sh")
    env = run_workflow("recommend", {"target_type": RECOMMEND_TARGET, "signal_tags": urns,
                                     "signal_location": event.geo, "limit": 20})
    if env.get("status") == "ok":
        # Demo output is English-only: drop entities whose names use CJK, Kana or Hangul scripts.
        env["results"] = [r for r in env.get("results", []) if not NON_LATIN_NAME.search(r.get("name", ""))][:10]
        env["result_count"] = len(env["results"])
        _REC_CACHE[event.id] = env
    return env


def mode() -> Tuple[str, Optional[str]]:
    if harness_installed():
        return "mock", "Qloo harness found. Recommend is shown as evidence; the culture profile that drives stock is synthetic"
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
