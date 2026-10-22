"""Minimal OpenAI-compatible chat client for the agent layer. Config comes from the environment only."""
import json
import os

import httpx


class LLMUnavailable(RuntimeError):
    pass


def chat_json(messages: list, timeout: float = 60.0) -> dict:
    base = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "")
    if not (base and key and model):
        raise LLMUnavailable("set LLM_BASE_URL, LLM_MODEL and LLM_API_KEY in .env")
    try:
        r = httpx.post(f"{base}/chat/completions", timeout=timeout,
                       headers={"Authorization": f"Bearer {key}"},
                       json={"model": model, "messages": messages, "temperature": 0,
                             "response_format": {"type": "json_object"}})
        r.raise_for_status()
        return json.loads(r.json()["choices"][0]["message"]["content"])
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
        raise LLMUnavailable(f"LLM call failed ({type(e).__name__})") from e


def chat_tools(messages: list, tools: list, timeout: float = 90.0) -> dict:
    """One chat turn with function calling. Returns the assistant message (may contain tool_calls)."""
    base = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "")
    if not (base and key and model):
        raise LLMUnavailable("set LLM_BASE_URL, LLM_MODEL and LLM_API_KEY in .env")
    try:
        r = httpx.post(f"{base}/chat/completions", timeout=timeout,
                       headers={"Authorization": f"Bearer {key}"},
                       json={"model": model, "messages": messages, "tools": tools,
                             "tool_choice": "auto", "temperature": 0})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
        raise LLMUnavailable(f"LLM call failed ({type(e).__name__})") from e
