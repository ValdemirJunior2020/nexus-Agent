import json
import httpx
from .config import CONFIG

class OllamaClient:
    def __init__(self):
        self.base = CONFIG["ollama"]["base_url"].rstrip("/")
        self.timeout = CONFIG["ollama"].get("timeout_seconds", 600)

    async def models(self):
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"{self.base}/api/tags")
            r.raise_for_status()
            return r.json()

    async def chat(self, messages, model=None, temperature=None, format_json=False):
        model = model or CONFIG["ollama"]["default_model"]
        options = {
            "temperature": CONFIG["ollama"]["temperature"] if temperature is None else temperature,
            "num_ctx": CONFIG["ollama"].get("context_tokens", 32768),
        }
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": options,
        }
        if format_json:
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.post(f"{self.base}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()
            return data["message"]["content"]

    async def embed(self, text, model=None):
        model = model or CONFIG["ollama"]["default_model"]
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.post(f"{self.base}/api/embed", json={"model": model, "input": text})
            r.raise_for_status()
            return r.json()
