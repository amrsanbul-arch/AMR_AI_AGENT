# Architecture notes — Stage 1

- `web/`: Next.js app-router shell, Arabic RTL by default; English localization is a later feature.
- `api/`: FastAPI service; route modules reserved for later account, content and analytics capabilities.
- `worker/`: reserved for scheduled/background work; deliberately no Instagram publishing code yet.
- `docs/`: architecture and implementation notes.

Initial checks intentionally describe service health only. `/healthz` is not an Instagram connectivity check. OAuth, token encryption, least-privilege scopes, audit logging, approval gates, scheduling and Meta integration are later milestones and must be validated before any account action.
