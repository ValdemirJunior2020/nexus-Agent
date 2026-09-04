import asyncio
from typing import Any
from ..config import CONFIG

async def browser_status() -> dict[str, Any]:
    try:
        import browser_use  # noqa
        return {"installed": True, "enabled": CONFIG.get("tools", {}).get("browser_use_enabled", True)}
    except Exception as exc:
        return {"installed": False, "enabled": CONFIG.get("tools", {}).get("browser_use_enabled", True), "error": str(exc)}


def _history_to_text(history) -> str:
    for attr in ("final_result", "result", "output"):
        value = getattr(history, attr, None)
        if callable(value):
            try:
                value = value()
            except Exception:
                value = None
        if value:
            return str(value)
    try:
        return str(history)
    except Exception:
        return "Browser task completed but no printable final result was returned."


async def browser_task(task: str, model: str) -> dict[str, Any]:
    if not CONFIG.get("tools", {}).get("browser_use_enabled", True):
        return {"ok": False, "error": "Browser Use is disabled in config.json"}
    if not task.strip():
        return {"ok": False, "error": "Browser task is empty"}

    provider = str(CONFIG.get("llm", {}).get("provider", "llama_cpp")).lower()
    try:
        if provider == "llama_cpp":
            from browser_use import Agent, ChatOpenAI
            cfg = CONFIG.get("llama_cpp", {})
            llm = ChatOpenAI(
                model=str(cfg.get("default_model", "nexus-local")),
                api_key="local-no-key",
                base_url=str(cfg.get("base_url", "http://127.0.0.1:8080")).rstrip("/") + "/v1",
            )
        else:
            from browser_use import Agent, ChatOllama
            ctx = int(CONFIG.get("ollama", {}).get("context_tokens", 8192))
            base_url = CONFIG.get("ollama", {}).get("base_url", "http://127.0.0.1:11434")
            kwargs = {"model": model, "num_ctx": ctx}
            try:
                llm = ChatOllama(**kwargs, host=base_url)
            except TypeError:
                try:
                    llm = ChatOllama(**kwargs, base_url=base_url)
                except TypeError:
                    llm = ChatOllama(**kwargs)
    except Exception as exc:
        return {
            "ok": False,
            "error": "Browser Use model adapter is unavailable. Run INSTALL_POWER_TOOLS.bat.",
            "details": str(exc),
            "provider": provider,
        }

    # Text-only local Qwen models may be less reliable for visual browser actions,
    # so keep vision automatic/disabled when the local model has no vision support.
    try:
        agent = Agent(task=task, llm=llm, use_vision=False if provider == "llama_cpp" else "auto")
    except TypeError:
        agent = Agent(task=task, llm=llm)
    history = await agent.run(max_steps=int(CONFIG.get("tools", {}).get("browser_max_steps", 25)))
    return {"ok": True, "result": _history_to_text(history), "provider": provider}

