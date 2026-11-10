"""Small local audit trail containing event names and opaque resource ids only."""
from __future__ import annotations

import logging
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.secure_storage import prepare_private_sqlite

_LOG = logging.getLogger("amr.audit")
_PATH_ENV = "AMR_AUDIT_DB_PATH"
_MAX_EVENTS = 10_000
_EVENTS = {
    "auth.login", "auth.logout", "instagram.connect_started", "instagram.oauth_result",
    "instagram.disconnect", "publishing.draft_created", "publishing.draft_updated",
    "publishing.state", "publishing.scheduler_paused", "publishing.scheduler_resumed",
    "publishing.scheduler_error",
}
_OUTCOMES = {
    "success", "failure", "rate_limited", "connected", "denied", "disconnected",
    "draft", "approved", "scheduled", "publishing", "published", "failed",
    "unknown", "cancelled", "paused", "resumed", "error",
}
_RESOURCE_RE = re.compile(r"^[0-9a-fA-F-]{36}$")


def _path() -> Path:
    return prepare_private_sqlite(Path(os.getenv(_PATH_ENV, "data/audit.sqlite3")))


def record_event(event: str, outcome: str, resource_id: str | None = None) -> bool:
    """Append a redacted event. Inputs are allow-listed; content and credentials never enter."""
    if event not in _EVENTS or outcome not in _OUTCOMES:
        raise ValueError("Audit event is not allow-listed.")
    if resource_id is not None and not _RESOURCE_RE.fullmatch(resource_id):
        raise ValueError("Audit resource id is not an opaque UUID.")
    try:
        path = _path()
        with sqlite3.connect(path, timeout=5) as db:
            db.execute("PRAGMA busy_timeout=5000")
            db.execute("""CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                happened_at TEXT NOT NULL,
                event TEXT NOT NULL,
                outcome TEXT NOT NULL,
                resource_id TEXT
            )""")
            db.execute("INSERT INTO audit_events(happened_at,event,outcome,resource_id) VALUES(?,?,?,?)",
                       (datetime.now(timezone.utc).isoformat(), event, outcome, resource_id))
            db.execute("DELETE FROM audit_events WHERE id NOT IN (SELECT id FROM audit_events ORDER BY id DESC LIMIT ?)",
                       (_MAX_EVENTS,))
        os.chmod(path, 0o600)
        return True
    except (OSError, sqlite3.Error):
        # Never log exception text, request data, tokens, URLs, captions, or secrets.
        _LOG.warning("audit_write_failed")
        return False
