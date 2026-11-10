"""Single-owner password login and signed, short-lived HttpOnly sessions."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import threading
import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.audit_log import record_event

router = APIRouter(prefix="/api/auth", tags=["authentication"])
COOKIE_NAME = "amr_owner_session"
SESSION_TTL_SECONDS = 12 * 60 * 60
PBKDF2_ITERATIONS = 310_000
_LOGIN_ATTEMPTS: dict[str, deque[float]] = defaultdict(deque)
_LOGIN_LOCK = threading.Lock()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_owner_password(password: str, *, salt: bytes | None = None) -> str:
    """Create an env-safe password hash; run locally, never pass a real password in chat."""
    if len(password) < 14:
        raise ValueError("Owner password must be at least 14 characters.")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${_b64(salt)}${_b64(digest)}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds_text, salt_text, digest_text = encoded.split("$", 3)
        rounds = int(rounds_text)
        if algorithm != "pbkdf2_sha256" or not 100_000 <= rounds <= 1_000_000:
            return False
        expected = _unb64(digest_text)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _unb64(salt_text), rounds)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, UnicodeError):
        return False


def _session_secret() -> bytes:
    secret = os.getenv("AMR_SESSION_SECRET", "").encode("utf-8")
    return secret if len(secret) >= 32 else b""


def _session_token(now: int | None = None) -> str:
    secret = _session_secret()
    if not secret:
        raise HTTPException(status_code=503, detail="Owner authentication is not configured.")
    payload = f"{(now or int(time.time())) + SESSION_TTL_SECONDS}.{secrets.token_urlsafe(24)}"
    signed = _b64(payload.encode("utf-8"))
    signature = _b64(hmac.new(secret, signed.encode("ascii"), hashlib.sha256).digest())
    return f"{signed}.{signature}"


def _valid_session(token: str) -> bool:
    secret = _session_secret()
    if not secret:
        return False
    try:
        encoded_payload, signature = token.split(".", 1)
        expected = _b64(hmac.new(secret, encoded_payload.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return False
        payload = _unb64(encoded_payload).decode("utf-8")
        expires_text, nonce = payload.split(".", 1)
        expires = int(expires_text)
        return bool(nonce) and int(time.time()) < expires <= int(time.time()) + SESSION_TTL_SECONDS + 60
    except (ValueError, TypeError, UnicodeError):
        return False


def _auth_configured() -> bool:
    encoded = os.getenv("AMR_OWNER_PASSWORD_HASH", "").strip()
    secret = _session_secret()
    if not encoded or not secret:
        return False
    # Reject malformed hashes at startup/use time rather than silently accepting a weak config.
    try:
        algorithm, rounds, salt, digest = encoded.split("$", 3)
        return algorithm == "pbkdf2_sha256" and 100_000 <= int(rounds) <= 1_000_000 and len(_unb64(salt)) >= 16 and len(_unb64(digest)) == 32
    except (ValueError, TypeError):
        return False


def require_owner(request: Request) -> None:
    if not _auth_configured():
        raise HTTPException(status_code=503, detail="Owner authentication is not configured.")
    if not _valid_session(request.cookies.get(COOKIE_NAME, "")):
        raise HTTPException(status_code=401, detail="Owner sign-in required.")


class LoginRequest(BaseModel):
    password: Annotated[str, Field(min_length=1, max_length=512)]


def _check_rate_limit(key: str, now: float) -> bool:
    with _LOGIN_LOCK:
        attempts = _LOGIN_ATTEMPTS[key]
        while attempts and now - attempts[0] > 600:
            attempts.popleft()
        return len(attempts) < 5


def _record_failure(key: str, now: float) -> None:
    with _LOGIN_LOCK:
        attempts = _LOGIN_ATTEMPTS[key]
        while attempts and now - attempts[0] > 600:
            attempts.popleft()
        attempts.append(now)


def _clear_failures(key: str) -> None:
    with _LOGIN_LOCK:
        _LOGIN_ATTEMPTS.pop(key, None)


def _check_request_origin(request: Request) -> None:
    """JSON-only mutations plus SameSite cookies; reject an explicit foreign Origin."""
    origin = request.headers.get("origin")
    if origin:
        allowed = {
            item.strip().rstrip("/")
            for item in os.getenv("WEB_ORIGIN", "http://localhost:3000").split(",")
            if item.strip()
        }
        if origin.rstrip("/") not in allowed:
            raise HTTPException(status_code=403, detail="Request origin is not allowed.")
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise HTTPException(status_code=415, detail="Use a JSON request.")


@router.get("/session")
def session_status(request: Request) -> dict[str, bool]:
    return {"configured": _auth_configured(), "authenticated": _valid_session(request.cookies.get(COOKIE_NAME, ""))}


@router.post("/login")
def owner_login(body: LoginRequest, request: Request, response: Response) -> dict[str, bool]:
    _check_request_origin(request)
    if not _auth_configured():
        raise HTTPException(status_code=503, detail="Owner authentication is not configured.")
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    if not _check_rate_limit(key, now):
        record_event("auth.login", "rate_limited")
        raise HTTPException(status_code=429, detail="Too many sign-in attempts. Try again later.")
    encoded = os.getenv("AMR_OWNER_PASSWORD_HASH", "")
    if not _verify_password(body.password, encoded):
        _record_failure(key, now)
        record_event("auth.login", "failure")
        raise HTTPException(status_code=401, detail="Invalid owner credentials.")
    _clear_failures(key)
    record_event("auth.login", "success")
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    response.set_cookie(
        COOKIE_NAME, _session_token(), max_age=SESSION_TTL_SECONDS,
        httponly=True, secure=app_env == "production", samesite="lax", path="/api",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"authenticated": True}


@router.post("/logout")
def owner_logout(request: Request, response: Response, _: None = Depends(require_owner)) -> dict[str, bool]:
    _check_request_origin(request)
    response.delete_cookie(COOKIE_NAME, path="/api", httponly=True,
                           secure=os.getenv("APP_ENV", "development").strip().lower() == "production",
                           samesite="lax")
    response.headers["Cache-Control"] = "no-store"
    record_event("auth.logout", "success")
    return {"authenticated": False}
