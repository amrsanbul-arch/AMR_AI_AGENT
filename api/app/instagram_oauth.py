"""Official Instagram Login OAuth and encrypted local credential storage.

No live Meta credentials are bundled. Network calls are injectable for tests.
"""
from __future__ import annotations

import hmac
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import httpx
from cryptography.fernet import Fernet
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

router = APIRouter(prefix="/api/instagram", tags=["instagram"])
STATE_COOKIE = "amr_ig_oauth_state"
CALLBACK_PATH = "/api/instagram/callback"
AUTH_URL = "https://www.instagram.com/oauth/authorize"
SHORT_TOKEN_URL = "https://api.instagram.com/oauth/access_token"
LONG_TOKEN_URL = "https://graph.instagram.com/access_token"
PROFILE_URL = "https://graph.instagram.com/me"
REQUIRED_SCOPE = "instagram_business_basic"


@dataclass(frozen=True)
class Settings:
    app_id: str
    app_secret: str
    redirect_uri: str
    encryption_key: str
    db_path: str
    app_env: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_id=os.getenv("META_APP_ID", "").strip(),
            app_secret=os.getenv("META_APP_SECRET", "").strip(),
            redirect_uri=os.getenv("META_REDIRECT_URI", "").strip(),
            encryption_key=os.getenv("INSTAGRAM_TOKEN_ENCRYPTION_KEY", "").strip(),
            db_path=os.getenv("INSTAGRAM_TOKEN_DB_PATH", "data/instagram.sqlite3"),
            app_env=os.getenv("APP_ENV", "development").strip().lower(),
        )

    def configured(self) -> bool:
        # This stage has no owner-authentication layer. Refuse to expose OAuth in production
        # until a later stage adds authenticated owner-only access to these routes.
        if self.app_env == "production":
            return False
        if not (self.app_id and self.app_secret and self.redirect_uri and self.encryption_key):
            return False
        parsed = urlsplit(self.redirect_uri)
        local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}
        if (parsed.scheme != "https" and not local_http) or parsed.path != CALLBACK_PATH or parsed.query or parsed.fragment:
            return False
        try:
            _fernet(self.encryption_key)
        except (ValueError, TypeError, UnicodeError):
            return False
        return True


def _fernet(key: str) -> Fernet:
    # Fernet enforces a URL-safe base64-encoded 32-byte key; never invent a fallback key.
    return Fernet(key.encode("ascii"))


def _store(settings: Settings, *, encrypted_token: bytes | None = None,
           username: str | None = None, user_id: str | None = None,
           expires_at: int | None = None, delete: bool = False) -> dict | None:
    path = Path(settings.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA busy_timeout=5000")
        db.execute("""CREATE TABLE IF NOT EXISTS instagram_connection (
            id INTEGER PRIMARY KEY CHECK (id = 1), encrypted_token BLOB NOT NULL,
            username TEXT NOT NULL, user_id TEXT NOT NULL, expires_at INTEGER,
            connected_at INTEGER NOT NULL
        )""")
        if delete:
            db.execute("DELETE FROM instagram_connection WHERE id = 1")
            return None
        if encrypted_token is not None:
            db.execute("""INSERT INTO instagram_connection
                (id, encrypted_token, username, user_id, expires_at, connected_at)
                VALUES (1, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET encrypted_token=excluded.encrypted_token,
                username=excluded.username, user_id=excluded.user_id,
                expires_at=excluded.expires_at, connected_at=excluded.connected_at""",
                (encrypted_token, username or "", user_id or "", expires_at, int(time.time())))
        row = db.execute("SELECT username, user_id, expires_at, connected_at FROM instagram_connection WHERE id=1").fetchone()
    if row is None:
        return None
    return {"username": row[0], "user_id": row[1], "expires_at": row[2], "connected_at": row[3]}


def _request_json(client: httpx.Client, method: str, url: str, **kwargs) -> dict:
    try:
        response = client.request(method, url, timeout=15.0, follow_redirects=False, **kwargs)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("unexpected response")
        return payload
    except (httpx.HTTPError, ValueError, TypeError):
        # Never leak OAuth codes/tokens, app secrets, response bodies, or query URLs.
        raise HTTPException(status_code=502, detail="Instagram authorization could not be completed.") from None


@router.get("/status")
def instagram_status() -> dict:
    settings = Settings.from_env()
    if not settings.configured():
        return {"status": "not_configured", "connected": False, "provider": "instagram"}
    try:
        connection = _store(settings)
    except (sqlite3.Error, OSError):
        raise HTTPException(status_code=503, detail="Instagram connection status is unavailable.") from None
    if not connection:
        return {"status": "not_connected", "connected": False, "provider": "instagram"}
    return {"status": "connected", "connected": True, "provider": "instagram", **connection}


@router.get("/connect")
def instagram_connect():
    settings = Settings.from_env()
    if not settings.configured():
        raise HTTPException(status_code=503, detail="Instagram OAuth is not configured for local development.")
    state = secrets.token_urlsafe(32)
    query = urlencode({
        "client_id": settings.app_id, "redirect_uri": settings.redirect_uri,
        "response_type": "code", "scope": REQUIRED_SCOPE, "state": state,
        "enable_fb_login": "0", "force_authentication": "1",
    })
    redirect = RedirectResponse(f"{AUTH_URL}?{query}", status_code=302)
    redirect.set_cookie(STATE_COOKIE, state, max_age=600, httponly=True,
                        secure=settings.app_env == "production", samesite="lax", path=CALLBACK_PATH)
    redirect.headers["Cache-Control"] = "no-store"
    return redirect


@router.get("/callback")
def instagram_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    settings = Settings.from_env()
    if not settings.configured():
        raise HTTPException(status_code=503, detail="Instagram OAuth is not configured for local development.")
    expected_state = request.cookies.get(STATE_COOKIE, "")
    if error:
        result = JSONResponse({"status": "not_connected", "connected": False,
                               "detail": "Instagram authorization was not completed."}, status_code=400)
    elif not code or not state or not expected_state or not hmac.compare_digest(state, expected_state):
        result = JSONResponse({"detail": "Instagram authorization response is invalid or expired."}, status_code=400)
    else:
        with httpx.Client() as client:
            short = _request_json(client, "POST", SHORT_TOKEN_URL, data={
                "client_id": settings.app_id, "client_secret": settings.app_secret,
                "grant_type": "authorization_code", "redirect_uri": settings.redirect_uri,
                "code": code,
            })
            short_token = short.get("access_token")
            if not isinstance(short_token, str) or not short_token:
                raise HTTPException(status_code=502, detail="Instagram did not return an access token.")
            long_lived = _request_json(client, "GET", LONG_TOKEN_URL, params={
                "grant_type": "ig_exchange_token", "client_secret": settings.app_secret,
                "access_token": short_token,
            })
            long_token = long_lived.get("access_token")
            if not isinstance(long_token, str) or not long_token:
                raise HTTPException(status_code=502, detail="Instagram did not return a long-lived token.")
            profile = _request_json(client, "GET", PROFILE_URL, params={
                "fields": "user_id,username", "access_token": long_token,
            })
        user_id, username = profile.get("user_id"), profile.get("username")
        if not isinstance(user_id, (str, int)) or not isinstance(username, str) or not username:
            raise HTTPException(status_code=502, detail="Instagram profile details were unavailable.")
        try:
            encrypted = _fernet(settings.encryption_key).encrypt(long_token.encode("utf-8"))
            expiry = long_lived.get("expires_in")
            expires_at = int(time.time()) + int(expiry) if isinstance(expiry, (int, float)) else None
            connection = _store(settings, encrypted_token=encrypted, username=username,
                                user_id=str(user_id), expires_at=expires_at)
        except (sqlite3.Error, OSError, ValueError, TypeError):
            raise HTTPException(status_code=503, detail="Instagram credentials could not be stored securely.") from None
        result = JSONResponse({"status": "connected", "connected": True,
                               "provider": "instagram", **connection})
    result.delete_cookie(STATE_COOKIE, path=CALLBACK_PATH)
    result.headers["Cache-Control"] = "no-store"
    result.headers["Pragma"] = "no-cache"
    return result


@router.post("/disconnect")
def instagram_disconnect() -> dict[str, object]:
    settings = Settings.from_env()
    if not settings.configured():
        raise HTTPException(status_code=503, detail="Instagram OAuth is not configured for local development.")
    try:
        _store(settings, delete=True)
    except (sqlite3.Error, OSError):
        raise HTTPException(status_code=503, detail="Local Instagram credentials could not be removed.") from None
    return {"status": "not_connected", "connected": False, "provider": "instagram",
            "notice": "Local credentials removed. Revoke app access in Instagram settings to revoke Meta authorization."}
