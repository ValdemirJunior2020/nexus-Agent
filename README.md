# NEXUS Agent v3

A local-first, multi-agent AI runtime for Ollama with planning, tools, specialist agents, review loops, persistent memory, MCP support, browser automation, and optional DeerFlow execution.

NEXUS is designed to give local models a practical agent runtime without forcing multiple orchestration frameworks into the same environment.

## Overview

NEXUS can route requests through different execution paths depending on complexity:

```text
User
  ↓
Engine Router
  ├── Ollama
  ├── NEXUS Agent Runtime
  └── DeerFlow
```

The native NEXUS runtime follows an agentic execution loop:

```text
User
  ↓
Tool Router
  ↓
Tool Execution
  ↓
Observation
  ↓
Specialist Agents
  ↓
Synthesizer
  ↓
Final Reviewer
  ↓
Fix / Pass
```

The model does not merely know tools exist. It can select tools, execute them, inspect observations, continue reasoning, delegate work, synthesize results, and review its own output.

---

## Features

* Planner / orchestrator
* Research agent
* Coding agent
* Analyst
* Document analyst
* QA verifier
* Adversarial critic
* Synthesizer
* Final reviewer
* Automatic specialist subagents
* Retry and correction loops
* Persistent SQLite memory
* Structured tool routing
* Per-request Ollama model selection
* OpenAI-compatible API
* MCP client support
* Browser Use integration
* Agent Reach integration
* Optional DeerFlow 2.0 engine
* Automatic engine routing
* Graceful fallback between engines

---

# Execution Engines

NEXUS v3 supports four engine modes.

## `ollama`

Direct local model execution.

Best for:

* simple questions
* fast responses
* lightweight generation
* tasks that do not need tools or multi-agent orchestration

## `nexus`

Uses the native NEXUS runtime:

* planner
* approved tools
* specialist subagents
* synthesis
* reviewer
* correction loop

Best for structured agent workflows that should remain inside the NEXUS runtime.

## `deerflow`

Uses DeerFlow as an optional long-horizon execution engine.

Best for:

* deep research
* complex coding
* long multi-step workflows
* sandbox workloads
* artifact generation
* large subagent workflows

## `auto`

NEXUS automatically chooses the lightest capable execution engine.

Example:

```json
{
  "prompt": "Research this complex subject and create a complete implementation plan.",
  "model": "qwen3:8b",
  "session_id": "project-42",
  "mode": "deep",
  "engine": "auto",
  "deerflow_mode": "ultra"
}
```

---

# DeerFlow Modes

NEXUS maps DeerFlow execution to four modes:

| Mode       | Behavior                                 |
| ---------- | ---------------------------------------- |
| `flash`    | No planning or subagents                 |
| `standard` | Thinking enabled                         |
| `pro`      | Thinking + planning                      |
| `ultra`    | Thinking + planning + DeerFlow subagents |

---

# Session Continuity

NEXUS stores the DeerFlow `thread_id` associated with each NEXUS `session_id` in the local SQLite memory database.

This means later requests using the same NEXUS session can continue the same DeerFlow conversation.

---

# NEXUS Review of DeerFlow Results

DeerFlow output is not automatically trusted.

NEXUS runs its own Final Reviewer over DeerFlow responses.

If the response fails review:

1. NEXUS generates concrete correction instructions.
2. The correction is sent back to the same DeerFlow thread.
3. DeerFlow produces a revised result.
4. NEXUS reviews the result again.

---

# Graceful Fallback

DeerFlow is optional.

If DeerFlow is:

* disabled
* not installed
* still starting
* unreachable
* unavailable because of configuration issues

NEXUS falls back to the configured fallback engine.

The default fallback is:

```text
nexus
```

The core local API remains usable even when DeerFlow is unavailable.

---

# Installation

## Requirements

You should have:

* Python
* Ollama
* at least one Ollama model installed
* Windows if using the included `.bat` launchers

Example model:

```powershell
ollama pull qwen3:8b
```

## Core Installation

1. Clone or download this repository.
2. Run:

```text
install.bat
```

3. Start NEXUS:

```text
START_AGENT.bat
```

The API runs locally at:

```text
http://127.0.0.1:8787
```

Interactive API documentation:

```text
http://127.0.0.1:8787/docs
```

---

# Optional Power Tools

For Browser Use, MCP support, and Agent Reach, run:

```text
INSTALL_POWER_TOOLS.bat
```

Then restart:

```text
START_AGENT.bat
```

Check available capabilities:

```text
GET http://127.0.0.1:8787/tools/status
```

---

# Browser Use + Ollama

Browser Use is an optional adapter that allows an agent to perform interactive web tasks while using the selected local Ollama model.

Example tasks:

* navigate multiple pages
* click links and buttons
* fill approved forms
* test web workflows
* inspect interactive websites
* gather information requiring browser interaction

Browser Use is intentionally optional because it requires a browser installation and has a significantly larger dependency tree than the core server.

---

# MCP Client

Configure MCP servers in:

```text
mcp_servers.json
```

Both `stdio` and Streamable HTTP-style configurations are supported.

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

```text
mcp_list_tools
mcp_call_tool
```

This allows new MCP servers to be added without rewriting the main NEXUS agent runtime.

---

# Agent Reach Integration

Agent Reach is used as a capability installation and health layer.

Its upstream commands are exposed through restricted NEXUS adapters.

Included integrations:

* public URL reader
* GitHub repository inspection through `gh`
* YouTube and public media metadata through `yt-dlp`
* Agent Reach doctor/status

`INSTALL_POWER_TOOLS.bat` runs Agent Reach in safe mode so it does not automatically make unrestricted system-package changes.

---

# API Usage

## Main Agent Request

```text
POST /agent/run
```

Example:

```json
{
  "prompt": "Research this GitHub project, compare its architecture, and check your answer.",
  "model": "qwen3:8b",
  "session_id": "project-1",
  "mode": "deep",
  "allow_tools": true,
  "engine": "auto"
}
```

Supported modes:

* `auto`
* `fast`
* `deep`
* `research`
* `code`
* `qa`
* `document`

`fast` intentionally skips most of the full tool and subagent pipeline.

---

# Model Support

The runtime does not hard-code a specific Ollama model.

Set the default model in:

```text
config.json
```

or specify one per request.

Examples:

```text
qwen3:8b
qwen3-coder
deepseek-r1
gemma
llama
```

Any compatible future Ollama model can also be used.

Agent quality depends heavily on the selected model. Larger models and models with stronger reasoning/tool-selection capabilities generally perform more reliably on long multi-step workflows.

---

# React / Node Example

```js
const response = await fetch("http://127.0.0.1:8787/agent/run", {
  method: "POST",
  headers: {
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    prompt:
      "Open the documentation website if needed, inspect it, then explain how to integrate this library.",
    model: "qwen3:8b",
    session_id: "react-dev",
    mode: "code",
    engine: "auto",
    allow_tools: true
  })
});

const data = await response.json();

console.log(data.answer);
console.log(data.metadata.tools_used);
```

---

# API Endpoints

## Core

```text
GET  /health
GET  /v1/models
POST /agent/run
POST /v1/chat/completions
```

## Tools

```text
GET  /tools/status
POST /tools/browser

GET  /tools/mcp/{server}/tools
POST /tools/mcp/{server}/call/{tool_name}

GET  /tools/agent-reach/doctor
```

## Engines

```text
GET  /engines/status
GET  /engines/deerflow/status
POST /engines/deerflow/run
```

---

# DeerFlow Configuration

`config.json` contains a `deerflow` section.

Example:

```json
{
  "deerflow": {
    "enabled": true,
    "base_url": "http://127.0.0.1:2026",
    "langgraph_url": "http://127.0.0.1:2026/api/langgraph",
    "assistant_id": "lead_agent",
    "default_mode": "ultra",
    "recursion_limit": 1000,
    "fallback_engine": "nexus"
  }
}
```

DeerFlow remains a separate installation.

See:

```text
DEERFLOW_SETUP_WINDOWS.md
```

---

# Git Architecture

NEXUS does not clone DeerFlow inside this repository and does not modify DeerFlow's `.git` metadata.

Keep DeerFlow in its own folder.

NEXUS communicates with DeerFlow over HTTP.

Example architecture:

```text
NEXUS-Agent/
    ├── NEXUS runtime
    ├── API server
    ├── tool adapters
    ├── SQLite memory
    └── configuration

DeerFlow/
    └── independent repository

NEXUS <---- HTTP ----> DeerFlow
```

This keeps both projects independently upgradeable and avoids nested repository problems.

---

# Tool Safety

NEXUS is designed around restricted tool access.

By default:

* arbitrary shell execution is disabled
* filesystem access is restricted to the configured workspace
* Agent Reach commands are allowlisted
* MCP servers are explicitly opt-in
* browser automation is opt-in
* the API binds to localhost

Giving an LLM arbitrary terminal or filesystem access is intentionally avoided.

---

# Security

NEXUS is designed primarily for local execution.

Default API binding:

```text
127.0.0.1
```

Do not expose the API directly to the public internet without adding appropriate protections such as:

* authentication
* HTTPS
* authorization
* rate limiting
* firewall rules
* network isolation
* auditing

---

## Never Commit Secrets

Do not commit:

* `.env` files
* API keys
* passwords
* access tokens
* private certificates
* browser cookies
* authenticated browser sessions
* `memory.db`
* private MCP configuration
* customer data
* company data
* sensitive workspace files

Use environment variables or local configuration files for secrets.

If a credential is accidentally committed, deleting the file from the repository is not sufficient.

Revoke or rotate the exposed credential immediately.

---

# Why One Runtime Instead of Ten Frameworks?

NEXUS borrows useful architectural ideas from projects and ecosystems such as:

* CrewAI
* LangGraph
* AutoGen
* MetaGPT
* smolagents
* Letta
* LlamaIndex
* Pydantic AI
* Browser Use
* Agent Reach
* MCP
* evaluator and guardrail systems

The goal is not to install every framework into one Python environment.

NEXUS keeps its own orchestration core and uses external projects as adapters when they provide a useful capability.

This reduces dependency conflicts and keeps the runtime understandable, replaceable, and under your control.

---

# Project Philosophy

NEXUS is built around a few principles:

1. **Local-first** — use local Ollama models whenever possible.
2. **Tool-restricted** — agents should receive capabilities, not unrestricted machine access.
3. **Model-independent** — orchestration should not depend on one specific model.
4. **Engine-independent** — complex workloads can be delegated without replacing the core runtime.
5. **Review before trust** — generated results can be checked and corrected.
6. **Composable** — MCP and adapters allow capabilities to grow independently.
7. **Graceful degradation** — optional services should not break the core server.

---

# Version Summary

## v1

Introduced:

* planning
* subagents
* memory
* synthesis
* review
* retries
* Ollama model switching
* OpenAI-compatible API

## v2

Added a real tool execution loop:

```text
Tool Router → Tool → Observation → Continued Agent Reasoning
```

Also added:

* Browser Use
* MCP
* Agent Reach
* stronger tool safety

## v3

Added the hybrid engine architecture:

```text
Ollama + NEXUS + DeerFlow
```

with:

* automatic engine routing
* DeerFlow session continuity
* NEXUS review of DeerFlow results
* correction loops
* graceful engine fallback

---

# Status

NEXUS Agent is under active development.

Expect APIs, adapters, configuration options, and orchestration behavior to continue evolving.
