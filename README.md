# Ollama Universal SuperAgent v2

A reusable **local multi-agent reasoning + tool server** for Ollama.

## What changed in v2

v1 already had planning, subagents, memory, synthesis, review, retries, an Ollama model switch, and an OpenAI-compatible API.

v2 adds a real agentic tool loop:

`User -> Tool Router -> Tool -> Observation -> Tool Router -> Specialists -> Synthesizer -> Reviewer -> Fix/Pass`

The model no longer just knows that tools exist. It can select and execute them, inspect the returned observation, and continue.

## Included agent behaviors

- planner / orchestrator
- researcher
- coder
- analyst
- document analyst
- QA verifier
- adversarial critic
- synthesizer
- final reviewer
- persistent SQLite memory
- retry / correction loop
- structured tool router
- automatic subagents
- switchable Ollama model per request

## Power tools

### Browser Use + Ollama

Browser Use is an optional adapter. The agent can hand a multi-step website task to a real browser agent while using your selected local Ollama model.

Example tasks:

- open a website and navigate several pages
- click buttons and links
- fill an approved form
- test a web workflow
- collect information that needs interaction instead of a simple HTTP request

The Browser Use adapter is intentionally optional because it downloads a browser and has a much larger dependency tree than the core server.

### MCP client

Configure MCP servers in `mcp_servers.json`.

Both stdio and Streamable HTTP style configurations are supported by the adapter.

Example:

```json
{
  "servers": {
    "my_server": {
      "enabled": true,
      "transport": "stdio",
      "command": "python",
      "args": ["C:/my-tools/server.py"]
    },
    "remote_local_server": {
      "enabled": true,
      "transport": "http",
      "url": "http://127.0.0.1:9000/mcp"
    }
  }
}
```

The tool router can use:

- `mcp_list_tools`
- `mcp_call_tool`

This means you can add future MCP servers without rewriting the main agent.

### Agent Reach integration

Agent Reach is treated as a capability installer/health layer. Its upstream commands are then called through restricted adapters.

Included integrations:

- public URL reader
- GitHub repository inspection through `gh`
- YouTube/public media metadata through `yt-dlp`
- Agent Reach doctor/status

`INSTALL_POWER_TOOLS.bat` runs Agent Reach in **safe mode**, so it doesn't automatically make system-package changes.

## Install

First install the small core:

1. Unzip.
2. Double-click `install.bat`.
3. Double-click `START_AGENT.bat`.

Core API:

`http://127.0.0.1:8787`

Docs:

`http://127.0.0.1:8787/docs`

Then, for Browser Use + MCP + Agent Reach, double-click:

`INSTALL_POWER_TOOLS.bat`

Restart `START_AGENT.bat` afterward.

Check what is available at:

`http://127.0.0.1:8787/tools/status`

## Main agent request

POST `/agent/run`

```json
{
  "prompt": "Research this GitHub project, compare its architecture, and check your answer.",
  "model": "qwen3:8b",
  "session_id": "project-1",
  "mode": "deep",
  "allow_tools": true
}
```

Modes:

- `auto`
- `fast`
- `deep`
- `research`
- `code`
- `qa`
- `document`

`fast` intentionally skips the full tool/subagent pipeline.

## Model-independent

The runtime doesn't hard-code Qwen. Edit `config.json` or set the model in each request.

Examples:

- `qwen3:8b`
- `qwen3-coder`
- DeepSeek models installed in Ollama
- Gemma models
- Llama models
- future Ollama models

The quality of agent planning and browser control still depends heavily on the selected model. Larger/tool-capable local models normally perform multi-step action selection more reliably.

## Tool safety

The general shell remains disabled.

The local filesystem tools are restricted to the `workspace` folder.

Agent Reach subprocess integration is allowlisted to specific capabilities rather than giving the LLM arbitrary terminal access.

MCP servers are opt-in through `mcp_servers.json`.

Browser Use is opt-in through installation/config.

## Endpoints

- `GET /health`
- `GET /v1/models`
- `POST /agent/run`
- `POST /v1/chat/completions`
- `GET /tools/status`
- `POST /tools/browser`
- `GET /tools/mcp/{server}/tools`
- `POST /tools/mcp/{server}/call/{tool_name}`
- `GET /tools/agent-reach/doctor`

## React / Node example

```js
const r = await fetch("http://127.0.0.1:8787/agent/run", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    prompt: "Open the documentation website if needed, inspect it, then explain how to integrate this library.",
    model: "qwen3:8b",
    session_id: "react-dev",
    mode: "code",
    allow_tools: true
  })
});

const data = await r.json();
console.log(data.answer);
console.log(data.metadata.tools_used);
```
## Security

NEXUS Agent is designed to run locally.

By default:

- The API binds to `127.0.0.1`.
- Arbitrary shell execution is disabled.
- Filesystem tools should remain limited to the local workspace.
- MCP integrations are optional.
- Browser automation is optional.
- Local memory and runtime files should not be committed to GitHub.

### Never commit

Do not commit any of the following:

- `.env` files
- API keys
- passwords
- tokens
- private certificates
- browser cookies
- login sessions
- `memory.db`
- private MCP configuration files
- customer or company data
- files placed inside the local workspace

Use environment variables or local configuration files for secrets.

If a secret is accidentally committed, deleting the file is not enough.
Revoke or rotate the exposed credential immediately.

### Network access

NEXUS Agent is configured for local use by default.

Do not expose the API directly to the public internet without authentication,
HTTPS, rate limiting, access controls, and proper network security.
## Why this is one runtime instead of 10 frameworks installed together

The architecture borrows useful patterns from CrewAI, LangGraph, AutoGen, MetaGPT, smolagents, Letta, LlamaIndex, Pydantic AI, Browser Use, Agent Reach, MCP, and evaluator/guardrail systems without forcing all those orchestration frameworks to fight inside one Python environment.

The core stays yours. External frameworks are adapters where they add an actual capability.
