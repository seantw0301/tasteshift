"""Fetch Qloo tag candidates for every concept the demo uses and save them for human review.

Run: python -m app.resolve_tags   (needs the qloo harness and an event credential)
"""
import json
from datetime import datetime, timezone

from . import qloo_gateway
from .store import FIXTURES, load_events, load_merchant

OUT = FIXTURES / "qloo_tag_candidates.json"


def concepts() -> list:
    found = {c for e in load_events() for c in e.seed_concepts}
    found |= {t.replace("_", " ") for s in load_merchant().skus for t in s.concept_tags}
    return sorted(found)


def main() -> int:
    out, failed = {}, 0
    for c in concepts():
        env = qloo_gateway.find_tags(c)
        out[c] = env
        failed += env["status"] == "error"
        print(f"{c:16} {env['status']:12} {env.get('summary', '')[:80]}")
        if env["status"] == "error" and not env["error"].get("retryable"):
            break  # auth or setup problem: stop instead of burning quota
    if failed == len(out):
        print("No live results; nothing written.")
        return 1
    OUT.write_text(json.dumps({"origin": "qloo_live", "fetched_at": datetime.now(timezone.utc).isoformat(),
                               "reviewed": False, "candidates": out}, indent=2))
    print(f"Wrote {OUT}. Review and confirm one tag per concept before using any ID.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
