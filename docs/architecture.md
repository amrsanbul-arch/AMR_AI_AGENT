# Architecture notes — Stage 3

- `web/`: Next.js app-router dashboard, Arabic RTL default, English toggle, responsive content studio. It calls the FastAPI content endpoint; no Instagram credentials are used in the browser.
- `api/app/content.py`: validated request/response schemas and a zero-cost deterministic template generator for ideas, captions and Reel outlines. `free_template` deliberately identifies the generator; it is not an LLM or account-data-derived output.
- `api/app/main.py`: `/healthz` reports service health only and `/api/content/generate` returns editable drafts. CORS allows only `WEB_ORIGIN`; when unset, localhost development origins are used.
- `worker/`: reserved for scheduled/background work; no publishing or scheduling code exists yet.

The API tests cover health truthfulness, all three content modes, language, invalid input, and local CORS. There is no Meta connection, account data, AI-provider integration, persistence, or publishing. Treat outputs as starter drafts; verify factual claims and edit before use. OAuth, token encryption, scoped Meta permissions, audit logging, approval gates and official API integration remain separate validated milestones.

## Stage — cautious content strategy report

- `api/app/strategy.py` exposes the owner-authenticated `POST /api/strategy/report`. It reads only the connected owner account through the existing official Instagram Graph integration (latest returned media and available like/comment counts), then separately reads the project's existing fixed public Google Trends RSS feed for the requested topic and region.
- The report only suggests low-risk experiments: an original follow-up to a returned high-count item, a balanced post/Reel comparison when enough examples exist, or an idea prompted by visible keyword overlap in the public search feed. These are hypotheses, not causal explanations or forecasts. The endpoint does not infer audience interests, engagement rate, or total interactions from partial metrics.
- Every report shows its Instagram sample/comparable/missing-metric counts, each source's status, the search-feed provenance when available, and bilingual limitations. Fewer than three comparable items are explicitly marked limited; unavailable official metrics are not treated as zero. An unavailable Google feed is distinguished from an available feed with no keyword match.
- Google Trends data represents public Google Search signals only; it is not Instagram trend data, Meta data, nor account-audience evidence. Keyword overlap is a transparent lightweight match heuristic. Trend retrieval is on demand, not a continuous monitor.
- The bilingual mobile content-studio report view requires owner sign-in, links back to the public Trends source, and exports the displayed report as plain text. No live Instagram connection, publishing, unofficial scraping, or paid provider is used by this report module. Tests use mocked official/API and feed responses; they do not demonstrate a live Instagram account connection.
