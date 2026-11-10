# Architecture notes — Stage 3

- `web/`: Next.js app-router dashboard, Arabic RTL default, English toggle, responsive content studio. It calls the FastAPI content endpoint; no Instagram credentials are used in the browser.
- `api/app/content.py`: validated request/response schemas and a zero-cost deterministic template generator for ideas, captions and Reel outlines. `free_template` deliberately identifies the generator; it is not an LLM or account-data-derived output.
- `api/app/main.py`: `/healthz` reports service health only and `/api/content/generate` returns editable drafts. CORS allows only `WEB_ORIGIN`; when unset, localhost development origins are used.
- `worker/`: reserved for scheduled/background work; no publishing or scheduling code exists yet.

The API tests cover health truthfulness, all three content modes, language, invalid input, and local CORS. There is no Meta connection, account data, AI-provider integration, persistence, or publishing. Treat outputs as starter drafts; verify factual claims and edit before use. OAuth, token encryption, scoped Meta permissions, audit logging, approval gates and official API integration remain separate validated milestones.
