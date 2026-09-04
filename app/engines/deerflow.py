import json
import os
import re
from typing import Any, Optional

import httpx

from ..config import CONFIG


def _cfg() -> dict[str, Any]:
    return CONFIG.get("deerflow", {})


def _base_urls() -> tuple[str, str]:
    cfg = _cfg()
    base = str(os.getenv("DEERFLOW_URL") or cfg.get("base_url") or "http://127.0.0.1:2026").rstrip("/")
    langgraph = str(
        os.getenv("DEERFLOW_LANGGRAPH_URL")
        or cfg.get("langgraph_url")
        or f"{base}/api/langgraph"
    ).rstrip("/")
    return base, langgraph


def _headers(session_id: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    cfg = _cfg()
    token_env = str(cfg.get("internal_auth_token_env") or "DEER_FLOW_INTERNAL_AUTH_TOKEN")
    token = os.getenv(token_env)
    if token:
        headers["X-DeerFlow-Internal-Token"] = token
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", session_id or "default")[:120]
        prefix = str(cfg.get("owner_prefix") or "nexus")
        headers["X-DeerFlow-Owner-User-Id"] = f"{prefix}_{safe}"
    return headers


async def status() -> dict[str, Any]:
    cfg = _cfg()
    enabled = bool(cfg.get("enabled", True))
    base, langgraph = _base_urls()
    if not enabled:
        return {"enabled": False, "available": False, "base_url": base, "langgraph_url": langgraph}
    timeout = float(cfg.get("health_timeout_seconds", 4))
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(f"{base}/health", headers={k: v for k, v in _headers("health").items() if k != "Accept"})
        return {
            "enabled": True,
            "available": response.is_success,
            "status_code": response.status_code,
            "base_url": base,
            "langgraph_url": langgraph,
        }
    except Exception as exc:
        return {
            "enabled": True,
            "available": False,
            "base_url": base,
            "langgraph_url": langgraph,
            "error": f"{type(exc).__name__}: {exc}",
        }


async def create_thread(session_id: str) -> str:
    _, langgraph = _base_urls()
    timeout = float(_cfg().get("timeout_seconds", 1800))
    headers = _headers(session_id)
    headers.pop("Accept", None)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.post(f"{langgraph}/threads", json={"metadata": {"source": "nexus", "nexus_session_id": session_id}}, headers=headers)
        response.raise_for_status()
        data = response.json()
    thread_id = str(data.get("thread_id") or "").strip()
    if not thread_id:
        raise RuntimeError("DeerFlow created a thread but did not return thread_id")
    return thread_id


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
        return "\n".join(x for x in parts if x).strip()
    if content is None:
        return ""
    return str(content)


def _last_ai_text(values: Any) -> str:
    if not isinstance(values, dict):
        return ""
    messages = values.get("messages")
    if not isinstance(messages, list):
        inner = values.get("values")
        if isinstance(inner, dict):
            messages = inner.get("messages")
    if not isinstance(messages, list):
        return ""
    for msg in reversed(messages):
        if not isinstance(msg, dict):
            continue
        msg_type = str(msg.get("type") or msg.get("role") or "").lower()
        if msg_type in {"ai", "assistant", "aimessage"}:
            text = _content_to_text(msg.get("content"))
            if text:
                return text
    return ""


async def run(
    prompt: str,
    session_id: str,
    thread_id: Optional[str] = None,
    model: Optional[str] = None,
    mode: str = "ultra",
) -> dict[str, Any]:
    cfg = _cfg()
    if not cfg.get("enabled", True):
        return {"ok": False, "error": "DeerFlow engine is disabled"}

    _, langgraph = _base_urls()
    timeout = float(cfg.get("timeout_seconds", 1800))
    if not thread_id:
        thread_id = await create_thread(session_id)

    mode = (mode or "ultra").lower()
    mode_flags = {
        "flash": (False, False, False),
        "standard": (True, False, False),
        "pro": (True, True, False),
        "ultra": (True, True, True),
    }
    thinking, plan_mode, subagents = mode_flags.get(mode, mode_flags["ultra"])

    context: dict[str, Any] = {
        "thinking_enabled": thinking,
        "is_plan_mode": plan_mode,
        "subagent_enabled": subagents,
        "thread_id": thread_id,
    }
    if model and cfg.get("pass_model_name", False):
        context["model_name"] = model

    payload = {
        "assistant_id": str(cfg.get("assistant_id") or "lead_agent"),
        "input": {
            "messages": [
                {
                    "type": "human",
                    "content": [{"type": "text", "text": prompt}],
                }
            ]
        },
        "stream_mode": ["values", "messages-tuple"],
        "stream_subgraphs": True,
        "config": {"recursion_limit": int(cfg.get("recursion_limit", 1000))},
        "context": context,
    }

    event_type = ""
    last_values: Any = None
    incremental_parts: list[str] = []
    errors: list[str] = []
    run_id: Optional[str] = None

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=15), follow_redirects=True) as client:
        async with client.stream(
            "POST",
            f"{langgraph}/threads/{thread_id}/runs/stream",
            json=payload,
            headers=_headers(session_id),
        ) as response:
            if response.status_code == 404:
                return {"ok": False, "error": "thread_not_found", "thread_id": thread_id, "status_code": 404}
            response.raise_for_status()
            async for raw_line in response.aiter_lines():
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                    continue
                if not line.startswith("data:"):
                    continue
                raw_data = line[5:].strip()
                try:
                    data = json.loads(raw_data)
                except Exception:
                    data = raw_data

                if event_type == "metadata" and isinstance(data, dict):
                    run_id = str(data.get("run_id") or run_id or "") or None
                elif event_type == "values":
                    last_values = data
                elif event_type == "messages-tuple":
                    # Different DeerFlow/LangGraph versions can shape this event differently.
                    candidates = data if isinstance(data, list) else [data]
                    for candidate in candidates:
                        if isinstance(candidate, dict):
                            role = str(candidate.get("type") or candidate.get("role") or "").lower()
                            if role in {"ai", "assistant", "aimessage"}:
                                text = _content_to_text(candidate.get("content"))
                                if text:
                                    incremental_parts.append(text)
                        elif isinstance(candidate, str):
                            incremental_parts.append(candidate)
                elif event_type == "error":
                    errors.append(raw_data[:4000])

    answer = _last_ai_text(last_values)
    if not answer and incremental_parts:
        answer = "".join(incremental_parts).strip()
    if errors and not answer:
        return {"ok": False, "error": "DeerFlow stream error", "details": errors, "thread_id": thread_id, "run_id": run_id}
    if not answer:
        return {"ok": False, "error": "DeerFlow completed without a readable final AI message", "thread_id": thread_id, "run_id": run_id}

    return {
        "ok": True,
        "answer": answer,
        "thread_id": thread_id,
        "run_id": run_id,
        "mode": mode,
        "engine": "deerflow",
    }
