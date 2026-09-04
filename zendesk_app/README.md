# NEXUS Zendesk App (foundation)

This folder is a Zendesk Apps Framework (ZAF) ticket-sidebar app. It reads the current ticket through the ZAF SDK and sends a structured request to the NEXUS `/zendesk/analyze` API.

It is intentionally co-pilot only in this build: it does not automatically send customer replies, solve tickets, issue refunds, or change ticket fields. The **Append to internal note** button requires an agent click.

Configure the `nexus_api_url` installation setting to the HTTPS address of the NEXUS server when deployed at work.

Development: run `npx @zendesk/zcli apps:server` inside this folder.
