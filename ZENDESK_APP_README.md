# NEXUS Zendesk Operator Foundation

This build prepares NEXUS to run as an agent-facing Zendesk application backend.

## Added
- Ticket Matrix knowledge ingestion (only the `Ticket Matrix` worksheet)
- policy retrieval before every NEXUS/Ollama/DeerFlow execution
- shared policy context for DeerFlow
- controlled learned memory with user/global scopes
- explicit teach, feedback, list-memory, and forget APIs
- `/zendesk/analyze` endpoint for structured ticket context
- official policy precedence over learned memory and historical ticket examples

## Zendesk endpoint
`POST /zendesk/analyze`

The endpoint accepts ticket metadata, tags, public/internal comments, and reservation/platform context. It returns an agent-facing NEXUS recommendation. It does not write back to Zendesk yet.

## Learning
- `POST /learning/teach` stores an explicit lesson.
- `POST /learning/feedback` records feedback and can save a correction.
- `GET /learning/memories/{user_id}` lists active learned memory.
- `DELETE /learning/memories/{memory_id}` forgets a learned item.

Company-wide rules should be taught explicitly with `scope=global` only after approval. Ticket text is never auto-promoted to company policy.

## DeerFlow
DeerFlow receives the same retrieved Ticket Matrix policy and learned-memory context because NEXUS injects that context before handing a request to DeerFlow. This is retrieval/memory-based learning, not model-weight training.

## Next production steps
Zendesk App Framework frontend, Zendesk API auth, ticket write-back permissions, admin-only policy approval, full Zendesk Guide/KB ingestion, audit logs, and production database migration.
