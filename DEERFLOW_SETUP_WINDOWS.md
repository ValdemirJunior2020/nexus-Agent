# DeerFlow setup for NEXUS v3 on Windows

NEXUS v3 does **not** modify or vendor DeerFlow into this Git repository. It connects to DeerFlow through its official HTTP/LangGraph-compatible API.

## Recommended layout

Keep DeerFlow in a separate folder, for example:

```text
C:\AI\deer-flow\
C:\Projects\NEXUS\
```

That keeps both projects independent and avoids nested Git repositories.

## Official DeerFlow setup

DeerFlow 2.0 recommends Docker for evaluation/development. Clone the official project separately:

```powershell
git clone https://github.com/bytedance/deer-flow.git C:\AI\deer-flow
cd C:\AI\deer-flow
```

Then follow DeerFlow's current `Install.md` / setup wizard. Its normal local proxy is:

```text
http://127.0.0.1:2026
```

NEXUS expects the LangGraph-compatible API at:

```text
http://127.0.0.1:2026/api/langgraph
```

These addresses can be changed in NEXUS `config.json` or with `DEERFLOW_URL` and `DEERFLOW_LANGGRAPH_URL` environment variables.

## Verify from NEXUS

Start NEXUS, then open:

```text
http://127.0.0.1:8787/engines/status
```

When DeerFlow is running you should see `deerflow.available: true`.

## Security

For a server-to-server deployment, DeerFlow supports an internal auth token. Keep that token in the environment, never in Git:

```text
DEER_FLOW_INTERNAL_AUTH_TOKEN=<your-secret>
```

NEXUS reads it automatically when present and sends a per-session owner ID for isolation.
