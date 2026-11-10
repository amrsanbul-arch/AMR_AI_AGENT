# AMR AI architecture and launch-readiness

This repository is a single-owner, mobile-friendly web application: Next.js client, FastAPI API, and local SQLite persistence. It uses official Instagram Login/Graph endpoints only. The current code is a staged prototype; it is not a deployed service and has not been connected to a live Instagram account.

## Runtime components

- `web/`: Arabic/English RTL-responsive dashboard, content studio, profile review, trends, analytics, strategy report, command center, publishing calendar, and bounded command assistant.
- `api/app/owner_auth.py`: single-owner password verification (PBKDF2-SHA256), signed 12-hour HttpOnly/SameSite session cookie, login throttling, JSON-only mutation checks and explicit Origin validation.
- `api/app/instagram_oauth.py`: fixed official Meta OAuth/Graph hosts, state cookie and callback validation, encrypted long-lived access token (Fernet), profile/media reads, disconnect.
- `api/app/instagram_insights.py` and related modules: official read-only analytics and profile report; missing API fields remain unavailable rather than being fabricated.
- `api/app/instagram_publishing.py`: explicitly approved content drafts, immutable approved-content snapshot, scheduled local worker, claim-before-publish state transition, unknown outcome after ambiguous final publish (no automatic retry), cancellation before claim, and persistent pause/resume control.
- `api/app/audit_log.py`: bounded local audit events with event/outcome and optional opaque content-item UUID only. It does not retain passwords, OAuth tokens, captions, media URLs, IP addresses, or request bodies. A write failure emits a generic warning and does not block the requested operation.
- `api/app/secure_storage.py`: creates private SQLite directories/files with mode `0700`/`0600` on POSIX and repairs existing file permissions when opened.
- Optional content generation uses local templates by default or explicitly configured Ollama. Optional image generation connects to a locally configured ComfyUI endpoint; neither is tested live by automated tests.

## Security properties and operating limits

- The app is intentionally single-owner. All Instagram, publishing, strategy and profile-review APIs require the configured owner session; optional Ollama generation also requires it. This is not tenant isolation: do not expose it as a multi-user service without per-user identity, data ownership and authorization changes.
- In production, owner authentication must be configured, HTTPS is required for OAuth redirect/cookies, and the owner cookie is `Secure`. Configure `WEB_ORIGIN` to exact trusted frontend origins. CORS allows credentials only for those origins and the API mutation guard rejects explicit foreign Origins and non-JSON mutation requests. SameSite=Lax is an additional browser defense, not a substitute for HTTPS and the Origin check.
- Sessions are signed, expire after 12 hours, and are not stored server-side. Logout removes the browser cookie but does not revoke a copied session token before expiry. Rotate `AMR_SESSION_SECRET` to invalidate every existing token. Login throttling is process-local; put a rate limit at a trusted reverse proxy for multi-worker or public deployments.
- Instagram OAuth state is a short-lived HttpOnly cookie bound to the callback. Access tokens are Fernet-encrypted in a private local SQLite file. Keep the encryption key separate from the database and backups. Do not log OAuth callback query strings or outbound Graph request query strings: run Uvicorn with `--no-access-log` and configure reverse-proxy/HTTP logs accordingly. Disconnect removes the local token; the owner must also revoke the app under Instagram settings to revoke Meta authorization.
- SQLite files are owner-only on POSIX. This local file-permissions model does not provide encryption for drafts/queue content, audit records, or database backups. Protect host access, backups and volumes. No multi-tenant data separation is implemented.
- Media URLs must be HTTPS and reject localhost and private/reserved IP literals. The application itself does not fetch these media URLs; it sends them to Meta as the approved media source, and the browser previews the URL. DNS names are not resolved or pinned by the API, so use trusted publicly reachable media hosts. This validation is not a general-purpose URL fetcher or a complete DNS-rebinding defense.
- The scheduled worker starts only when `INSTAGRAM_SCHEDULER_ENABLED=true` at server startup. Its persistent pause control prevents future scheduled items from being claimed, but cannot stop a publication already claimed/in flight or a publish-now action already explicitly approved. Use the Pause control in the publishing calendar to stop new scheduled claims; to disable the worker entirely, set the env flag false and restart the API. Per-post cancellation works only while its state is still `scheduled`.
- SQLite claim transactions prevent two workers sharing the same database from claiming the same scheduled post. The final Instagram publish call is not safely retryable: a lost response becomes `unknown` and is not retried. This reduces duplicate risk but is not a distributed queue or exactly-once guarantee.
- Automated Instagram tests use mocks; they do not authorize or establish a live connection, Meta app review, real publish, or live Ollama/ComfyUI generation. The command center and assistant do not bypass per-post approval.

## Launch prerequisites still owned by the account operator

1. Create/configure the Meta developer app, enable Instagram Login, configure the exact HTTPS redirect URI and request supported scopes for the Creator/professional account.
2. On a private HTTPS deployment, set `APP_ENV=production`, trusted `WEB_ORIGIN`, strong owner password hash and random session secret, `META_APP_ID`, `META_APP_SECRET`, `META_REDIRECT_URI`, and a durable Fernet `INSTAGRAM_TOKEN_ENCRYPTION_KEY`. Never send these secrets in chat or commit them.
3. Protect the machine, database directory and backups; configure a reverse proxy without query-string logging and add rate limiting before public access. The user must run the service on their own trusted host and approve any Instagram account connection through Meta.
4. For scheduled publishing, provide an always-on worker, persistent shared SQLite storage and publicly reachable HTTPS media files; test the real authorized account and revoke access when no longer needed. Free hosting sleep/quotas may make scheduled timing unreliable.
5. Install Ollama/model or ComfyUI/model locally only if desired. Configure network access narrowly; keep these services off the public internet. Run the local FFmpeg bundle on a device with FFmpeg installed.

## Verification boundary

Run `uv run pytest` for mocked API tests, `cd web && npm run test:intents`, and `cd web && npm run build`. A passing test/build establishes local code behavior only. Live Meta OAuth, real Insights fields, publishing, scheduled delivery and external model generation must be tested separately in an explicitly configured private environment.
