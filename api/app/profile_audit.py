"""Review-only Instagram profile audit using returned official fields and optional manual context."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.owner_auth import require_owner
from app import instagram_oauth

router = APIRouter(prefix="/api/profile", tags=["profile audit"], dependencies=[Depends(require_owner)])

# The existing official integration requests only these profile fields. Do not infer other
# fields from account type, media, or a manual form.
OFFICIAL_PROFILE_FIELDS = ("user_id", "username", "account_type", "media_count")
MANUAL_FIELDS = ("display_name", "bio", "niche", "audience", "offer", "website")
CTA_CUES = (
    "dm me", "message me", "contact me", "book now", "shop now", "learn more", "link in bio",
    "راسلني", "تواصل معي", "احجز الآن", "احجز", "اطلب الآن", "اطلب", "الرابط في البايو", "تابعني",
)


class ProfileAuditRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    bio: str | None = Field(default=None, max_length=2000)
    niche: str | None = Field(default=None, max_length=160)
    audience: str | None = Field(default=None, max_length=240)
    offer: str | None = Field(default=None, max_length=240)
    website: str | None = Field(default=None, max_length=500)


def _manual_values(request: ProfileAuditRequest) -> dict[str, str]:
    return {key: value.strip() for key in MANUAL_FIELDS
            if isinstance(value := getattr(request, key), str) and value.strip()}


def build_profile_audit(account: dict[str, Any] | None, manual: dict[str, str], *, official_status: str) -> dict:
    """Return observed fields and modest checklist prompts, never profile edits or inferred facts."""
    observed: dict[str, Any] = {}
    if isinstance(account, dict):
        for key in OFFICIAL_PROFILE_FIELDS:
            value = account.get(key)
            if value is not None and value != "":
                observed[key] = value

    missing_official = [key for key in ("display_name", "biography", "profile_picture", "website", "category")
                        if key not in observed]
    checks: list[dict[str, str]] = []
    if "username" in observed:
        checks.append({"key": "username", "source": "official", "status": "returned"})
    else:
        checks.append({"key": "username", "source": "official", "status": "not_returned"})
    if "account_type" in observed:
        checks.append({"key": "account_type", "source": "official", "status": "returned"})
    else:
        checks.append({"key": "account_type", "source": "official", "status": "not_returned"})
    if "media_count" in observed:
        checks.append({"key": "media_count", "source": "official", "status": "returned"})
    else:
        checks.append({"key": "media_count", "source": "official", "status": "not_returned"})
    for field in MANUAL_FIELDS:
        checks.append({"key": field, "source": "manual" if field in manual else "not_provided", "status": "provided" if field in manual else "needs_manual_input"})

    bio = manual.get("bio", "")
    bio_lower = bio.casefold()
    has_cta_cue = any(cue.casefold() in bio_lower for cue in CTA_CUES) if bio else None
    niche = manual.get("niche", "")
    niche_mentioned = bool(niche and bio and niche.casefold() in bio_lower) if niche and bio else None

    prompts = [
        {"key": "audience_value", "basis": "manual_input" if manual.get("audience") or manual.get("offer") else "needs_manual_input"},
        {"key": "bio_action", "basis": "manual_bio" if bio else "needs_manual_input"},
        {"key": "visual_identity", "basis": "not_available_from_current_api"},
    ]
    return {
        "status": "ready" if observed or manual else "limited",
        "official_status": official_status,
        "official_source": "instagram_graph_api" if official_status == "available" else None,
        "official_fields": observed,
        "official_fields_not_returned": missing_official,
        "checks": checks,
        "manual_review": {
            "fields_received": [field for field in MANUAL_FIELDS if field in manual],
            "bio_character_count": len(bio) if bio else None,
            "bio_contains_simple_cta_cue": has_cta_cue,
            "bio_contains_manual_niche_text": niche_mentioned,
            "heuristics_note": "Simple text checks only; they do not judge clarity, quality, audience fit, or conversion.",
        },
        "review_prompts": prompts,
        "notice": "Suggestions are review-only. No Instagram profile field is edited or saved by this report.",
    }


@router.post("/audit")
def audit_profile(request: ProfileAuditRequest) -> dict:
    """Fetch only existing official read fields, then review optional user-entered context in memory."""
    official_status = "not_connected"
    account: dict[str, Any] | None = None
    settings = instagram_oauth.Settings.from_env()
    if not settings.configured():
        official_status = "not_configured"
    else:
        try:
            account = instagram_oauth.instagram_account()
            official_status = "available"
        except HTTPException as exc:
            if exc.status_code == 409:
                official_status = "not_connected"
            else:
                official_status = "unavailable"
    return build_profile_audit(account, _manual_values(request), official_status=official_status)
