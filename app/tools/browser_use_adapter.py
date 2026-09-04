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
    try:
        from browser_use import Agent, ChatOllama
    except Exception as exc:
        return {"ok": False, "error": "Browser Use extra is not installed. Run INSTALL_POWER_TOOLS.bat", "details": str(exc)}

    ctx = int(CONFIG.get("ollama", {}).get("context_tokens", 32768))
    base_url = CONFIG.get("ollama", {}).get("base_url", "http://127.0.0.1:11434")
    kwargs = {"model": model, "num_ctx": ctx}
    # Some browser-use releases accept host/base_url; keep compatibility by falling back.
    try:
        llm = ChatOllama(**kwargs, host=base_url)
    except TypeError:
        try:
            llm = ChatOllama(**kwargs, base_url=base_url)
        except TypeError:
            llm = ChatOllama(**kwargs)

    agent = Agent(task=task, llm=llm)
    history = await agent.run(max_steps=int(CONFIG.get("tools", {}).get("browser_max_steps", 25)))
    return {"ok": True, "result": _history_to_text(history)}
