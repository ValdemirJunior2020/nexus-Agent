# Ollama Universal SuperAgent v2 architecture

```text
APP / USER
   |
   v
FastAPI :8787
   |
   v
SESSION MEMORY
   |
   v
TOOL ROUTER ------------------------------+
   |                                      |
   | finish                               | tool
   v                                      v
PLANNER                             TOOL REGISTRY
   |                                      |
   |                    +-----------------+-------------------+
   |                    |                 |                   |
   |                Browser Use          MCP             Agent Reach
   |                    |                 |                   |
   |                 Ollama       stdio / HTTP      gh / yt-dlp / reader
   |                    |                 |                   |
   |                    +-------- observation --------------+
   |                                      |
   +<-------------------------------------+
   |
   +--> Researcher
   +--> Coder
   +--> Analyst
   +--> Document Analyst
   +--> QA
   +--> Critic
   |
   v
SYNTHESIZER
   |
   v
REVIEWER -- fail --> CORRECTIVE REWRITE --+
   |                                       |
   +---------------- pass <----------------+
   |
   v
FINAL ANSWER
```

The LLM's private reasoning is not exposed as a product feature. The system exposes useful execution metadata such as which specialists/tools were used and the review score.
