# NEXUS llama.cpp update

- Added llama.cpp as the primary local inference backend.
- Kept Ollama as an automatic compatibility fallback.
- Added OpenAI-compatible llama.cpp chat/model/embedding client.
- Added `/llm/status` and expanded health/engine status output.
- Reduced default local context from 32768 to 8192 to reduce memory pressure.
- Reduced Ollama fallback keep-alive to 30 seconds.
- Added balanced, low-VRAM, and fast llama.cpp startup profiles.
- Added runtime/model folders without bundling large binaries.
- Existing Zendesk knowledge, Ticket Matrix, learning, DeerFlow integration, and issue logging remain intact.
