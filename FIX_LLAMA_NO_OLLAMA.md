# llama.cpp-only startup fix

This build removes Ollama as an installation requirement.

- `install.bat` no longer checks for or starts Ollama.
- `START_AGENT.bat` requires llama.cpp health on `127.0.0.1:8080` and stops with a clear message if it is offline.
- `config.json` uses llama.cpp as the only local LLM provider; Ollama fallback is disabled.
- Existing Zendesk, Ticket Matrix, learning, DeerFlow, and issue logging features are preserved.
