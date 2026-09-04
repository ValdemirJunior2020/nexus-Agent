# NEXUS Agent v3 Architecture

```text
APPLICATION / USER
        |
        v
NEXUS API :8787
        |
        v
ENGINE ROUTER
        |
        +------------------+---------------------+
        |                  |                     |
        v                  v                     v
 OLLAMA DIRECT        NEXUS ENGINE          DEERFLOW ENGINE
 simple/fast          medium/complex        long-horizon/heavy
        |                  |                     |
        |            TOOL ROUTER                 | HTTP/SSE
        |             /   |   \                  v
        |        Browser MCP AgentReach     DeerFlow :2026
        |                  |               plan / sandbox /
        |            PLANNER               skills / subagents /
        |                  |               memory / artifacts
        |          SPECIALIST FAN-OUT              |
        |        Research / Code / QA              |
        |          Analyst / Critic                |
        |                  |                       |
        +----------> SYNTHESIS <-------------------+
                           |
                           v
                    NEXUS REVIEWER
                           |
                 pass -----+----- fail
                           |       |
                           |       +--> correction
                           |            - NEXUS rewrite, or
                           |            - same DeerFlow thread
                           v
                      FINAL ANSWER
```

## Engine rules

`ollama` is the low-overhead path. `nexus` is the normal multi-agent/tool path. `deerflow` is reserved for long-horizon work where its sandbox, planning, subagents, skills, or extended execution are worth the extra overhead.

## DeerFlow isolation

DeerFlow is not vendored into the NEXUS repository. NEXUS uses DeerFlow's official Gateway/LangGraph-compatible API. Each NEXUS `session_id` can map to a persistent DeerFlow `thread_id` in local SQLite.

## Failure behavior

DeerFlow health is checked before automatic delegation. If it is unavailable, the engine router falls back to NEXUS. Optional integrations are not allowed to make the core server unusable.
