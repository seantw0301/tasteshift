"""Tool-calling agent: turns a natural-language request into a per-SKU fit plan, then the existing optimizer runs.

Qloo arm: find_tags, recommend_films, rank_films, audience_profile and taste_tags are available and their results go into the model's context.
No-Qloo arm: only list_events and submit_plan, so the model decides from its own knowledge.
"""
import json
from typing import Dict, List, Optional

from . import llm, qloo_gateway
from .store import get_event, load_events, load_merchant

MAX_STEPS = 14
SUBMIT = "submit_plan"

_TOOL_LIST_EVENTS = {"type": "function", "function": {
    "name": "list_events", "description": "List the events you can plan for.",
    "parameters": {"type": "object", "properties": {}}}}
_TOOL_FIND_TAGS = {"type": "function", "function": {
    "name": "find_tags", "description": "Look up Qloo taste tags for a concept (e.g. 'anime', 'matcha').",
    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}}
_TOOL_RECOMMEND = {"type": "function", "function": {
    "name": "recommend_films", "description": "Qloo recommendations for an event's audience: films with affinity.",
    "parameters": {"type": "object", "properties": {"event_id": {"type": "string"}}, "required": ["event_id"]}}}
_TOOL_RANK = {"type": "function", "function": {
    "name": "rank_films", "description": "Rank up to 10 films returned by recommend_films for an event; scores are relative within this call.",
    "parameters": {"type": "object", "properties": {
        "event_id": {"type": "string"}, "entity_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 10}},
        "required": ["event_id", "entity_ids"]}}}
_FILM_IDS = {"event_id": {"type": "string"}, "entity_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 5}}
_TOOL_AUDIENCE = {"type": "function", "function": {
    "name": "audience_profile",
    "description": "Qloo audience demographics (age bands, gender skew; positive = over-indexed) for up to 5 films from recommend_films.",
    "parameters": {"type": "object", "properties": _FILM_IDS, "required": ["event_id", "entity_ids"]}}}
_TOOL_TASTE = {"type": "function", "function": {
    "name": "taste_tags",
    "description": "Cross-domain Qloo taste tags (food, brands, places, styles) shared by the audiences of up to 5 films from recommend_films.",
    "parameters": {"type": "object", "properties": _FILM_IDS, "required": ["event_id", "entity_ids"]}}}
_TOOL_SUBMIT = {"type": "function", "function": {
    "name": SUBMIT, "description": "Submit your final per-SKU fit for the chosen event. Ends the task.",
    "parameters": {"type": "object", "properties": {
        "event_id": {"type": "string"},
        "scores": {"type": "array", "items": {"type": "object", "properties": {
            "sku_id": {"type": "string"}, "fit": {"type": "number", "minimum": 0, "maximum": 1},
            "reason": {"type": "string"},
            "cited_films": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
            "cited_signals": {"type": "array", "items": {"type": "string"}, "maxItems": 3}},
            "required": ["sku_id", "fit", "reason"]}}},
        "required": ["event_id", "scores"]}}}

SYSTEM_QLOO = (
    "You are a souvenir stocking agent. Decide which SKUs a merchant should stock for an event. "
    "Steps: list_events to identify the event; find_tags for its concepts; recommend_films for its audience; "
    "rank_films on the strongest films; audience_profile and taste_tags on the top 3-5 films to learn who the crowd is "
    "(age, gender) and what else they like (food, brands, styles); then submit_plan with a fit score (0-1), "
    "a one-sentence English reason, cited_films: 1-3 exact film names from recommend_films, and "
    "cited_signals: 1-3 exact signal names returned by audience_profile (e.g. 'age:35_to_44', 'gender:male') "
    "or taste_tags (tag name) that support that SKU. Use [] only if nothing is relevant."
)
SYSTEM_PLAIN = (
    "You are a souvenir stocking agent. Decide which SKUs a merchant should stock for an event. "
    "Steps: list_events to identify the event, then submit_plan with a fit score (0-1) and a one-sentence reason per SKU. "
    "Reasons must be in English."
)


def _summ(obj, limit=1500) -> str:
    s = json.dumps(obj, ensure_ascii=False, default=str)
    return s if len(s) <= limit else s[:limit] + "...(truncated)"


def _run_tool(name: str, args: dict, qloo: bool, ctx: dict) -> dict:
    if name == "list_events":
        return {"events": [{"id": e.id, "name": e.name, "theme": e.theme, "city": e.geo,
                            "attendance": e.attendance, "seed_concepts": e.seed_concepts} for e in load_events()]}
    if not qloo:
        return {"error": f"unknown or unavailable tool {name}"}
    if name == "find_tags":
        env = qloo_gateway.find_tags(str(args.get("query", "")), limit=5)
        return {"status": env.get("status"), "tags": [{"id": r["id"], "name": r["name"]} for r in env.get("results", [])]}
    if name == "recommend_films":
        event = get_event(str(args.get("event_id", "")))
        env = qloo_gateway.recommend(event)
        films = [{"entity_id": r["entity_id"], "name": r["name"], "affinity": r.get("affinity")}
                 for r in env.get("results", [])] if env.get("status") == "ok" else []
        ctx.setdefault("films", {})[event.id] = {f["entity_id"] for f in films}
        return {"status": env.get("status"), "films": films}
    if name == "rank_films":
        event = get_event(str(args.get("event_id", "")))
        ids = list(dict.fromkeys(args.get("entity_ids", [])))[:10]
        allowed = ctx.get("films", {}).get(event.id, set())
        ids = [i for i in ids if i in allowed]
        if len(ids) < 2:
            return {"error": "pass at least two entity_ids returned by recommend_films for this event"}
        env = qloo_gateway.run_workflow("rank", {"options": ids, "option_type": "movie", "signal_location": event.geo})
        return {"status": env.get("status"), "ranked": [{"name": r["name"], "affinity": r.get("affinity")}
                                                         for r in env.get("results", [])]}
    if name in ("audience_profile", "taste_tags"):
        event = get_event(str(args.get("event_id", "")))
        allowed = ctx.get("films", {}).get(event.id, set())
        ids = [i for i in dict.fromkeys(args.get("entity_ids", [])) if i in allowed][:5]
        if not ids:
            return {"error": "pass entity_ids returned by recommend_films for this event"}
        signals = ctx.setdefault("signals", set())
        if name == "audience_profile":
            out = qloo_gateway.audience_profile(ids)
            signals.update(f"age:{k}" for k in out.get("age", {}))
            signals.update(f"gender:{k}" for k in out.get("gender", {}))
            return out
        out = qloo_gateway.taste_tags(ids)
        signals.update(t["name"] for t in out.get("tags", []))
        return out
    return {"error": f"unknown tool {name}"}


def run_agent(request: str, qloo: bool, event_hint: Optional[str] = None) -> dict:
    """Run the tool loop. Returns the chosen event, per-SKU scores, the tool trace and the Qloo evidence used."""
    tools = [_TOOL_LIST_EVENTS, _TOOL_SUBMIT] + (
        [_TOOL_FIND_TAGS, _TOOL_RECOMMEND, _TOOL_RANK, _TOOL_AUDIENCE, _TOOL_TASTE] if qloo else [])
    sku_lines = "\n".join(f"- {s.id}: {s.name}" for s in load_merchant().skus)
    user = request if event_hint is None else f"{request}\nUse event_id {event_hint}."
    user += f"\nSKUs (use these exact sku_id values in submit_plan):\n{sku_lines}"
    messages = [{"role": "system", "content": SYSTEM_QLOO if qloo else SYSTEM_PLAIN},
                {"role": "user", "content": user}]
    ctx: Dict = {}
    trace: List[dict] = []
    for step in range(MAX_STEPS):
        msg = llm.chat_tools(messages, tools)
        calls = msg.get("tool_calls") or []
        if not calls:
            messages.append({"role": "user", "content": "Call a tool. Finish by calling submit_plan."})
            trace.append({"step": step, "note": "model replied without a tool call"})
            continue
        messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
        for c in calls:
            name = c["function"]["name"]
            try:
                args = json.loads(c["function"].get("arguments") or "{}")
            except ValueError:
                args = {}
            if name == SUBMIT:
                event_id = str(args.get("event_id", ""))
                known = {s.id for s in load_merchant().skus}
                valid_films = {f["name"] for f in ctx.get("last_films", [])}
                scores, cite_ok, cite_bad, sig_bad = {}, 0, 0, 0
                for s in args.get("scores", []):
                    if s.get("sku_id") not in known or "fit" not in s:
                        continue
                    cited = [c for c in s.get("cited_films", []) if isinstance(c, str)]
                    ok = [c for c in cited if c in valid_films]
                    sig = [c for c in s.get("cited_signals", []) if isinstance(c, str)]
                    sig_ok = [c for c in sig if c in ctx.get("signals", set())]
                    cite_ok += len(ok)
                    cite_bad += len(cited) - len(ok)
                    sig_bad += len(sig) - len(sig_ok)
                    scores[s["sku_id"]] = {"fit": min(1.0, max(0.0, float(s["fit"]))),
                                           "reason": str(s.get("reason", ""))[:300], "cited": ok, "signals": sig_ok}
                trace.append({"step": step, "tool": SUBMIT, "event_id": event_id, "n_scores": len(scores)})
                if not scores:
                    result = {"error": "no sku_id matched; use the exact sku_id values listed in the prompt"}
                    trace[-1]["result"] = result["error"]
                    messages.append({"role": "tool", "tool_call_id": c["id"], "content": _summ(result)})
                    continue
                n_with_cite = sum(1 for v in scores.values() if v["cited"])
                n_with_any = sum(1 for v in scores.values() if v["cited"] or v["signals"])
                return {"event_id": event_id, "scores": scores, "trace": trace,
                        "evidence_films": [f["name"] for f in ctx.get("last_films", [])],
                        "qloo": qloo,
                        "evidence_signals": sorted(ctx.get("signals", set())),
                        "citations": {"valid": cite_ok, "invalid": cite_bad, "skus_with_valid_citation": n_with_cite,
                                      "signals_valid": sum(len(v["signals"]) for v in scores.values()),
                                      "signals_invalid": sig_bad, "skus_with_any_qloo_citation": n_with_any}}
            try:
                result = _run_tool(name, args, qloo, ctx)
            except Exception as e:  # tool errors go back to the model, not to the user
                result = {"error": f"{type(e).__name__}: {e}"}
            if name == "recommend_films" and isinstance(result.get("films"), list):
                ctx["last_films"] = result["films"]
            trace.append({"step": step, "tool": name, "args": args, "result": _summ(result, 300)})
            messages.append({"role": "tool", "tool_call_id": c["id"], "content": _summ(result)})
    raise llm.LLMUnavailable("agent did not submit a plan within the step limit")
