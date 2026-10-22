#!/usr/bin/env python3
"""Repeat /api/agent/compare N times and summarise with-Qloo vs without-Qloo.

Usage: scripts/agent_eval.py <api_base> <runs> [request text]
  e.g. scripts/agent_eval.py https://demo.jxdtw.com/tasteshift/api 20
Writes one JSON line per run to stdout-adjacent file agent_eval_runs.jsonl in the current directory.
"""
import json
import statistics
import sys
import urllib.request

DEFAULT = "I am running a souvenir booth at an 8,000-person anime music festival in Taipei. What should I stock?"


def compare(base: str, text: str) -> dict:
    req = urllib.request.Request(f"{base}/agent/compare", data=json.dumps({"request": text}).encode(),
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def main() -> None:
    base, runs = sys.argv[1].rstrip("/"), int(sys.argv[2])
    text = sys.argv[3] if len(sys.argv) > 3 else DEFAULT
    rows = []
    with open("agent_eval_runs.jsonl", "a") as log:
        for i in range(runs):
            try:
                d = compare(base, text)
            except Exception as e:  # keep going; a failed run is reported, not hidden
                print(f"run {i + 1}: failed ({type(e).__name__})", flush=True)
                continue
            ev, c = d["evaluation"], d["with_qloo"]["citations"]
            row = {"event_id": d["event_id"], "delta": ev["delta_profit"], "win": ev["grounded_win_rate"],
                   "changed": len(ev.get("changed_skus", [])), **c}
            rows.append(row)
            log.write(json.dumps(row) + "\n")
            print(f"run {i + 1}: delta {row['delta']:+.0f} win {row['win']:.2f} "
                  f"skus_cited {row.get('skus_with_any_qloo_citation')}", flush=True)
    if len(rows) < 2:
        sys.exit("not enough successful runs")
    deltas = [r["delta"] for r in rows]
    mean, sd = statistics.mean(deltas), statistics.stdev(deltas)
    half = 1.96 * sd / len(deltas) ** 0.5
    n_skus = 12 * len(rows)
    print(json.dumps({
        "n": len(rows), "failed": runs - len(rows), "mean_delta": round(mean), "sd": round(sd),
        "ci95": [round(mean - half), round(mean + half)],
        "pos_neg_zero": [sum(d > 0 for d in deltas), sum(d < 0 for d in deltas), sum(d == 0 for d in deltas)],
        "mean_win_rate": round(statistics.mean(r["win"] for r in rows), 2),
        "mean_changed_skus": round(statistics.mean(r["changed"] for r in rows), 1),
        "film_citations_valid_invalid": [sum(r["valid"] for r in rows), sum(r["invalid"] for r in rows)],
        "signal_citations_valid_invalid": [sum(r.get("signals_valid", 0) for r in rows),
                                           sum(r.get("signals_invalid", 0) for r in rows)],
        "skus_with_film_citation": f"{sum(r['skus_with_valid_citation'] for r in rows)}/{n_skus}",
        "skus_with_any_qloo_citation": f"{sum(r.get('skus_with_any_qloo_citation', 0) for r in rows)}/{n_skus}",
    }, indent=1))


if __name__ == "__main__":
    main()
