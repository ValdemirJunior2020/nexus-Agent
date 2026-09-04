# NEXUS v3

- Added hybrid engine router: `auto`, `ollama`, `nexus`, `deerflow`.
- Added DeerFlow 2.0 HTTP/SSE adapter using its LangGraph-compatible API.
- Added DeerFlow flash / standard / pro / ultra execution modes.
- Added persistent NEXUS-session to DeerFlow-thread mapping in SQLite.
- Added NEXUS final review and correction loop over DeerFlow answers.
- Added automatic DeerFlow health check and graceful fallback to NEXUS.
- Added `/engines/status`, `/engines/deerflow/status`, and `/engines/deerflow/run`.
- Added `TEST_DEERFLOW.bat` and Windows setup notes.
- DeerFlow stays external; the NEXUS `.git` repository metadata is not modified.
