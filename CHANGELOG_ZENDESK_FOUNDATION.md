# Zendesk Operator Foundation Update

## Knowledge
- Imported **only** the `Ticket Matrix` worksheet from `new matrix-06_22_26 (2)(7).xlsx`.
- Added 5 sections and 46 actionable matrix rules to `knowledge/ticket_matrix.json`.
- Added lexical policy retrieval so relevant matrix rules are injected before execution.
- Official Ticket Matrix rules have higher authority than learned memory and historical examples.

## Learning
- Added persistent learned memory with `user` and `global` scopes.
- Added explicit teaching capture for messages such as `remember this`, `learn this`, `correction`, and `from now on`.
- Added teach, feedback, list-memory, and forget API endpoints.
- Customer/ticket text is not auto-promoted to company policy.

## DeerFlow
- DeerFlow receives the same retrieved Ticket Matrix and learned-memory context that NEXUS receives.
- This is shared retrieval/memory-based learning; it does not modify model weights.

## Zendesk
- Added `/zendesk/analyze` structured ticket endpoint.
- Added a Zendesk Apps Framework ticket-sidebar starter in `zendesk_app/`.
- Sidebar reads ticket context using ZAF and sends it to NEXUS.
- No automatic send/solve/refund actions are enabled in this foundation build.

## Runtime
- Added configurable Ollama `keep_alive` support.
- Existing `.git` content was preserved and not modified.


## Issue logging / Junior repair reports
- Added rotating `data/logs/nexus.log` server logs.
- Added structured `data/logs/issues.jsonl` incident records with `NX-...` IDs.
- Logs API/tool/DeerFlow/Zendesk app failures without intentionally storing complete ticket/prompt bodies.
- Added the user-facing failure message: “I'm saving all the issues happening with me so Junior can fix it later.”
- Added `EXPORT_NEXUS_LOGS.bat` to create a single ZIP report for debugging.
- Zendesk app queues client errors locally while the API is unreachable and retries later.
