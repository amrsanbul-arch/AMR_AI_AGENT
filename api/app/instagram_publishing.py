"""Official Instagram content publishing with explicit, immutable approval snapshots.

Scheduling is application-managed (no Meta native scheduler). A timed-out final publish is
marked unknown and is never retried automatically to avoid duplicate posts.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.owner_auth import _check_request_origin, require_owner
from app.instagram_oauth import Settings, _graph_url, _stored_access_token

router = APIRouter(prefix="/api/instagram", tags=["instagram-publishing"], dependencies=[Depends(require_owner)])
MAX_CAPTION = 2200
POLL_SECONDS = 60
MAX_PROCESSING_SECONDS = 300


class DraftInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    caption: str = Field(default="", max_length=MAX_CAPTION)
    media_url: str = Field(min_length=1, max_length=2048)
    media_type: str = Field(pattern="^(IMAGE|REELS|VIDEO)$")

    @field_validator("media_url")
    @classmethod
    def public_https_url(cls, value: str) -> str:
        parsed = urlsplit(value.strip())
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Media must use a public HTTPS URL.")
        host = parsed.hostname.lower().rstrip(".")
        if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost") or host.endswith(".local"):
            raise ValueError("Media URL must be publicly reachable.")
        import ipaddress
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved):
            raise ValueError("Media URL must be publicly reachable.")
        return value.strip()


class ApprovalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approved: bool
    mode: str = Field(pattern="^(publish_now|schedule)$")
    scheduled_at: datetime | None = None

    @field_validator("scheduled_at")
    @classmethod
    def aware_time(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("scheduled_at must include a timezone.")
        return value


class PublishServiceError(Exception):
    def __init__(self, message: str, *, final_publish_attempted: bool = False):
        self.final_publish_attempted = final_publish_attempted
        super().__init__(message)


def _db_path() -> Path:
    path = Path(os.getenv("INSTAGRAM_POSTS_DB_PATH", "data/instagram_posts.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    return path


def _db() -> sqlite3.Connection:
    db = sqlite3.connect(_db_path(), timeout=5, isolation_level="IMMEDIATE")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=5000")
    db.execute("""CREATE TABLE IF NOT EXISTS instagram_posts (
      id TEXT PRIMARY KEY, caption TEXT NOT NULL, media_url TEXT NOT NULL, media_type TEXT NOT NULL,
      state TEXT NOT NULL, scheduled_at TEXT, approved_hash TEXT, approved_at TEXT,
      instagram_media_id TEXT, error_code TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    )""")
    return db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize(row: sqlite3.Row) -> dict:
    return {key: row[key] for key in row.keys() if key not in {"approved_hash"}}


def _content_hash(row: sqlite3.Row | dict) -> str:
    data = {key: row[key] for key in ("caption", "media_url", "media_type")}
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _get(post_id: str) -> sqlite3.Row:
    with _db() as db:
        row = db.execute("SELECT * FROM instagram_posts WHERE id=?", (post_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Content item was not found.")
    return row


def _update_state(post_id: str, state: str, *, error: str | None = None, media_id: str | None = None) -> None:
    with _db() as db:
        db.execute("UPDATE instagram_posts SET state=?, error_code=?, instagram_media_id=COALESCE(?,instagram_media_id), updated_at=? WHERE id=?",
                   (state, error, media_id, _now(), post_id))


def _graph_request(client: httpx.Client, method: str, url: str, *, data: dict | None = None, params: dict | None = None) -> dict:
    try:
        response = client.request(method, url, data=data, params=params, timeout=20, follow_redirects=False)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("invalid response")
        return payload
    except (httpx.HTTPError, ValueError, TypeError):
        raise PublishServiceError("instagram_api_error") from None


def _publish_remote(post: sqlite3.Row, token: str, user_id: str, *, client_factory=None,
                    sleep= time.sleep, poll_interval: int = POLL_SECONDS,
                    max_wait: int = MAX_PROCESSING_SECONDS) -> str:
    """Create a Meta media container, wait for processing, then publish once."""
    client_factory = client_factory or httpx.Client
    versioned_media = _graph_url(f"{user_id}/media")
    versioned_container = lambda container: _graph_url(container)
    fields = {"caption": post["caption"]}
    if post["media_type"] == "IMAGE":
        fields.update({"image_url": post["media_url"]})
    else:
        fields.update({"video_url": post["media_url"], "media_type": post["media_type"]})
    try:
        with client_factory() as client:
            container = _graph_request(client, "POST", versioned_media, data={**fields, "access_token": token})
            container_id = container.get("id")
            if not isinstance(container_id, str) or not container_id.isdigit():
                raise PublishServiceError("invalid_container_response")
            deadline = time.monotonic() + max_wait
            while True:
                status = _graph_request(client, "GET", versioned_container(container_id),
                                        params={"fields": "status_code", "access_token": token})
                state = status.get("status_code")
                if state == "FINISHED":
                    break
                if state in {"ERROR", "EXPIRED"}:
                    raise PublishServiceError("container_processing_failed")
                if state != "IN_PROGRESS" or time.monotonic() >= deadline:
                    raise PublishServiceError("container_processing_timeout")
                sleep(poll_interval)
            # The network call below is a non-idempotent publication. Any transport or API
            # error is treated as ambiguous; caller records unknown and must not retry.
            try:
                published = _graph_request(client, "POST", _graph_url(f"{user_id}/media_publish"),
                                           data={"creation_id": container_id, "access_token": token})
            except PublishServiceError:
                raise PublishServiceError("publish_outcome_unknown", final_publish_attempted=True) from None
            media_id = published.get("id")
            if not isinstance(media_id, (str, int)) or not str(media_id).isdigit():
                raise PublishServiceError("publish_outcome_unknown", final_publish_attempted=True)
            return str(media_id)
    except PublishServiceError:
        raise
    except Exception:
        # Connection lifecycle or transport failures can occur after the final request.
        raise PublishServiceError("publish_outcome_unknown", final_publish_attempted=True) from None


def _execute_claimed(post_id: str, *, client_factory=None, sleep=time.sleep,
                     poll_interval=POLL_SECONDS, max_wait=MAX_PROCESSING_SECONDS) -> dict:
    settings = Settings.from_env()
    row = _get(post_id)
    if row["state"] != "publishing" or row["approved_hash"] != _content_hash(row):
        _update_state(post_id, "failed", error="approval_snapshot_mismatch")
        return _serialize(_get(post_id))
    try:
        token, connection = _stored_access_token(settings)
        media_id = _publish_remote(row, token, str(connection["user_id"]), client_factory=client_factory,
                                   sleep=sleep, poll_interval=poll_interval, max_wait=max_wait)
    except PublishServiceError as exc:
        _update_state(post_id, "unknown" if exc.final_publish_attempted else "failed", error=str(exc))
    except HTTPException as exc:
        _update_state(post_id, "failed", error="instagram_not_connected" if exc.status_code == 409 else "instagram_unavailable")
    else:
        _update_state(post_id, "published", media_id=media_id)
    return _serialize(_get(post_id))


def _claim(post_id: str, *, due_only: bool = False) -> bool:
    now = _now()
    with _db() as db:
        row = db.execute("SELECT * FROM instagram_posts WHERE id=?", (post_id,)).fetchone()
        if row is None or row["approved_hash"] != _content_hash(row):
            return False
        if due_only:
            cursor = db.execute("UPDATE instagram_posts SET state='publishing', updated_at=? WHERE id=? AND state='scheduled' AND scheduled_at<=?",
                                (now, post_id, now))
        else:
            cursor = db.execute("UPDATE instagram_posts SET state='publishing', updated_at=? WHERE id=? AND state='approved'",
                                (now, post_id))
        return cursor.rowcount == 1


@router.post("/posts", status_code=201)
def create_draft(body: DraftInput, request: Request) -> dict:
    _check_request_origin(request)
    post_id, now = str(uuid.uuid4()), _now()
    with _db() as db:
        db.execute("INSERT INTO instagram_posts(id,caption,media_url,media_type,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                   (post_id, body.caption, body.media_url, body.media_type, "draft", now, now))
    return _serialize(_get(post_id))


@router.get("/posts")
def list_posts() -> dict:
    with _db() as db:
        rows = db.execute("SELECT * FROM instagram_posts ORDER BY COALESCE(scheduled_at,created_at) DESC LIMIT 100").fetchall()
    return {"data": [_serialize(row) for row in rows]}


@router.put("/posts/{post_id}")
def update_draft(post_id: str, body: DraftInput, request: Request) -> dict:
    _check_request_origin(request)
    row = _get(post_id)
    if row["state"] != "draft":
        raise HTTPException(status_code=409, detail="Only an unapproved draft can be edited.")
    with _db() as db:
        db.execute("UPDATE instagram_posts SET caption=?,media_url=?,media_type=?,updated_at=? WHERE id=? AND state='draft'",
                   (body.caption, body.media_url, body.media_type, _now(), post_id))
    return _serialize(_get(post_id))


@router.post("/posts/{post_id}/approve")
def approve_post(post_id: str, body: ApprovalInput, request: Request) -> dict:
    _check_request_origin(request)
    if body.approved is not True:
        raise HTTPException(status_code=400, detail="Explicit approval is required.")
    row = _get(post_id)
    if row["state"] != "draft":
        raise HTTPException(status_code=409, detail="This item is not an unapproved draft.")
    if body.mode == "schedule":
        if body.scheduled_at is None:
            raise HTTPException(status_code=422, detail="Choose a scheduled time with timezone.")
        when = body.scheduled_at.astimezone(timezone.utc)
        if when <= datetime.now(timezone.utc):
            raise HTTPException(status_code=422, detail="Scheduled time must be in the future.")
        state, scheduled_at = "scheduled", when.isoformat()
    else:
        if body.scheduled_at is not None:
            raise HTTPException(status_code=422, detail="A publish-now approval cannot include a scheduled time.")
        state, scheduled_at = "approved", None
    snapshot = _content_hash(row)
    with _db() as db:
        db.execute("UPDATE instagram_posts SET state=?,scheduled_at=?,approved_hash=?,approved_at=?,updated_at=? WHERE id=? AND state='draft'",
                   (state, scheduled_at, snapshot, _now(), _now(), post_id))
    if body.mode == "schedule":
        return _serialize(_get(post_id))
    if not _claim(post_id):
        raise HTTPException(status_code=409, detail="Approval could not be claimed; review the post status before retrying.")
    return _execute_claimed(post_id)


@router.post("/posts/{post_id}/cancel")
def cancel_scheduled(post_id: str, request: Request) -> dict:
    _check_request_origin(request)
    with _db() as db:
        cursor = db.execute("UPDATE instagram_posts SET state='cancelled',updated_at=? WHERE id=? AND state='scheduled'",
                            (_now(), post_id))
    if cursor.rowcount != 1:
        raise HTTPException(status_code=409, detail="Only a scheduled post can be cancelled.")
    return _serialize(_get(post_id))


async def scheduled_publisher_loop() -> None:
    """Optional local scheduler loop; safe claim prevents multiple processes publishing one job."""
    while True:
        try:
            with _db() as db:
                rows = db.execute("SELECT id FROM instagram_posts WHERE state='scheduled' AND scheduled_at<=? ORDER BY scheduled_at LIMIT 10",
                                  (_now(),)).fetchall()
            for row in rows:
                if _claim(row["id"], due_only=True):
                    await asyncio.to_thread(_execute_claimed, row["id"])
        except Exception:
            # Keep scheduler alive; individual errors are stored on each job where possible.
            pass
        await asyncio.sleep(20)


def scheduler_enabled() -> bool:
    return os.getenv("INSTAGRAM_SCHEDULER_ENABLED", "false").strip().lower() in {"1", "true", "yes"}
