# NEXUS trust + progress update

- Ticket Matrix retrieval is no longer injected into unrelated general prompts.
- Zendesk ticket calls force Ticket Matrix retrieval.
- Matrix prompt context now forbids inventing prohibitions/requirements from blank fields.
- Local direct metadata now reports `engine=local_llm` and provider separately.
- Windows launcher forces UTF-8 console/Python output to reduce mojibake such as `guestâs`.
- Zendesk sidebar now shows a visible 0–100% loading indicator with stages while analysis runs.
- Existing learning, logging, DeerFlow integration, Zendesk foundation, `.git`, and environment template are preserved.
