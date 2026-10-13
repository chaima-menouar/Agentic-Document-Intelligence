# n8n integration

Import `health-check.json` into your own n8n instance and run it manually. It performs one GET request to the ADI health endpoint and returns the API response. Expected output is `{"status":"ok"}`. Change the HTTP Request URL when using a local or different deployment. No credentials, messaging, subscription, or schedule is included.

This is a runnable API connectivity workflow, not the A/B/C evaluation pipeline. It has not been activated or tested in an n8n runtime in this session. n8n is optional orchestration around the Python core; it does not replace retrieval, evidence verification or action budgets.

For repeatable quality evaluation, use `scripts/run_hosted_pilot.py`. Automating ingestion and evaluation in n8n next requires a stable session/storage backend and an authenticated job endpoint. The current Vercel process-local workspace is not reliable across instances, so no unattended ingestion workflow is advertised yet.

The project remains usable without n8n. A self-hosted n8n instance needs a host with persistent storage; a local development instance is sufficient for importing and manually trying this workflow.
