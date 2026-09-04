import logging
from typing import Any

import httpx

from .config import CONFIG
from .ollama_client import OllamaClient

log = logging.getLogger("nexus.local_llm")


class LlamaCppClient:
    """OpenAI-compatible client for llama.cpp's local HTTP server."""

    def __init__(self):
        cfg = CONFIG.get("llama_cpp", {})
        self.base = str(cfg.get("base_url", "http://127.0.0.1:8080")).rstrip("/")
        self.timeout = float(cfg.get("timeout_seconds", 600))
        self.default_model = str(cfg.get("default_model", "nexus-local"))
        self.temperature = float(cfg.get("temperature", 0.25))
        self.max_tokens = int(cfg.get("max_output_tokens", 4096))

    async def models(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{self.base}/v1/models")
            r.raise_for_status()
            data = r.json()
            # Normalize to Ollama-like shape used by older NEXUS endpoints.
            return {
                "models": [
                    {"name": x.get("id") or self.default_model, "provider": "llama_cpp"}
                    for x in data.get("data", [])
                ] or [{"name": self.default_model, "provider": "llama_cpp"}]
            }

    async def chat(self, messages, model=None, temperature=None, format_json=False):
        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "stream": False,
            "max_tokens": self.max_tokens,
        }
        if format_json:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.post(f"{self.base}/v1/chat/completions", json=payload)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]

    async def embed(self, text, model=None):
        payload = {"model": model or self.default_model, "input": text}
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.post(f"{self.base}/v1/embeddings", json=payload)
            r.raise_for_status()
            return r.json()


class LocalLLMClient:
    """NEXUS local-model abstraction.

    Primary provider can be llama.cpp or Ollama. If the primary provider is
    unavailable, NEXUS can fall back to the configured secondary provider.
    """

    def __init__(self):
        llm_cfg = CONFIG.get("llm", {})
        self.primary = str(llm_cfg.get("provider", "llama_cpp")).lower()
        self.fallback = str(llm_cfg.get("fallback_provider", "ollama")).lower()
        self.allow_fallback = bool(llm_cfg.get("allow_fallback", True))
        self.llama = LlamaCppClient()
        self.ollama = OllamaClient()
        self.last_provider = self.primary

    def default_model(self) -> str:
        if self.primary == "llama_cpp":
            return str(CONFIG.get("llama_cpp", {}).get("default_model", "nexus-local"))
        return str(CONFIG.get("ollama", {}).get("default_model", "qwen3:8b"))

    def _client(self, provider: str):
        if provider == "llama_cpp":
            return self.llama
        if provider == "ollama":
            return self.ollama
        raise ValueError(f"Unsupported local LLM provider: {provider}")

    async def _with_fallback(self, method: str, *args, **kwargs):
        providers = [self.primary]
        if self.allow_fallback and self.fallback and self.fallback != self.primary:
            providers.append(self.fallback)

        last_exc = None
        for provider in providers:
            client = self._client(provider)
            try:
                result = await getattr(client, method)(*args, **kwargs)
                self.last_provider = provider
                return result
            except Exception as exc:
                last_exc = exc
                log.warning("Local LLM provider %s failed for %s: %s", provider, method, exc)
        if last_exc:
            raise last_exc
        raise RuntimeError("No local LLM provider is configured")

    async def models(self):
        return await self._with_fallback("models")

    async def chat(self, messages, model=None, temperature=None, format_json=False):
        # A model name supplied by an Ollama UI is usually invalid for a single-model
        # llama.cpp server. For llama.cpp use its configured alias by default.
        selected = model
        if self.primary == "llama_cpp":
            selected = str(CONFIG.get("llama_cpp", {}).get("default_model", "nexus-local"))
        return await self._with_fallback(
            "chat", messages, model=selected, temperature=temperature, format_json=format_json
        )

    async def embed(self, text, model=None):
        selected = model
        if self.primary == "llama_cpp":
            selected = str(CONFIG.get("llama_cpp", {}).get("default_model", "nexus-local"))
        return await self._with_fallback("embed", text, model=selected)

    async def status(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "primary": self.primary,
            "fallback": self.fallback if self.allow_fallback else None,
            "active": None,
            "providers": {},
        }
        for provider in ("llama_cpp", "ollama"):
            try:
                data = await self._client(provider).models()
                out["providers"][provider] = {
                    "available": True,
                    "models": [m.get("name") for m in data.get("models", [])],
                }
                if out["active"] is None and provider == self.primary:
                    out["active"] = provider
            except Exception as exc:
                out["providers"][provider] = {"available": False, "error": str(exc)}
        if out["active"] is None and self.allow_fallback:
            fb = out["providers"].get(self.fallback, {})
            if fb.get("available"):
                out["active"] = self.fallback
        return out
