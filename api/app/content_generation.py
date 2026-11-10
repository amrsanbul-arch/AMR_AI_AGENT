from __future__ import annotations

import json
import os

from pydantic import ValidationError

from app.content import ContentMode, ContentRequest, ContentResponse, generate_content
from app.local_ai import generate_json, provider_status
from app.owner_auth import _auth_configured
from app.reel_studio import ReelStudioRequest, ReelStudioResponse, generate_reel_studio


def _ollama_enabled() -> bool:
    # The local model is never exposed as a public generation proxy: require configured owner auth.
    return provider_status()["generator"] == "ollama" and _auth_configured()


def _fallback_notice(language: str, original: str) -> str:
    if language == "ar":
        return f"تعذر استخدام نموذج Ollama المحلي الآن؛ جهزت بدلًا منه مسودة القوالب المجانية. {original}"
    return f"The local Ollama model was unavailable, so I used the free template fallback. {original}"


def _content_prompt(request: ContentRequest) -> str:
    count = 3 if request.mode == ContentMode.ideas else 1
    return (
        "Create editable social-media draft content. Return JSON with keys mode, language, pieces, notice. "
        "Each piece must have title, hook, body, cta, hashtags (array of strings), scenes (array of strings). "
        f"Make exactly {count} piece(s), in language {request.language}; keep all text in that language. "
        f"Mode: {request.mode.value}. Topic: {json.dumps(request.topic, ensure_ascii=False)}. "
        f"Audience: {json.dumps(request.audience, ensure_ascii=False)}. Tone: {request.tone}. "
        "Avoid invented statistics, factual claims without qualification, and promises. For a Reel script, include an actionable scene outline."
    )


def _valid_content_result(data: object, request: ContentRequest) -> ContentResponse | None:
    try:
        result = ContentResponse.model_validate(data)
        expected_count = 3 if request.mode == ContentMode.ideas else 1
        if result.mode != request.mode or result.language != request.language or len(result.pieces) != expected_count:
            return None
        if any(not piece.title.strip() or not piece.hook.strip() or not piece.body.strip() for piece in result.pieces):
            return None
        return result.model_copy(update={"generator": "ollama"})
    except (ValidationError, TypeError, ValueError):
        return None


async def generate_content_with_provider(request: ContentRequest) -> ContentResponse:
    template = generate_content(request)
    if not _ollama_enabled():
        return template
    data = await generate_json(_content_prompt(request))
    result = _valid_content_result(data, request)
    if result is None:
        return template.model_copy(update={"notice": _fallback_notice(request.language, template.notice)})
    return result


def _reel_prompt(request: ReelStudioRequest) -> str:
    return (
        "Create a practical bilingual Instagram Reel storyboard. Return a JSON object with keys: "
        "title_ar,title_en,duration_seconds,concept_ar,concept_en,hook_ar,hook_en,voiceover_ar,voiceover_en,"
        "caption_ar,caption_en,cta_ar,cta_en,scenes,production_note_ar,production_note_en. "
        "scenes must contain exactly four objects, each with start_seconds,end_seconds,shot_ar,shot_en,"
        "screen_text_ar,screen_text_en,voiceover_ar,voiceover_en. Use exactly these contiguous time intervals: "
        f"{[(a, b) for a, b in ({15: [(0,2),(2,6),(6,12),(12,15)], 30: [(0,3),(3,9),(9,23),(23,30)], 45: [(0,3),(3,12),(12,36),(36,45)]}[request.duration_seconds])]}. "
        f"Total duration {request.duration_seconds} seconds. Topic: {json.dumps(request.topic, ensure_ascii=False)}. "
        f"Audience: {json.dumps(request.audience, ensure_ascii=False)}. Tone: {request.tone}. "
        "Arabic fields must be natural Arabic; English fields must be natural English. Avoid unsupported factual claims. "
        "State that this is text only, does not make video or images, and does not publish."
    )


def _valid_reel_result(data: object, request: ReelStudioRequest) -> ReelStudioResponse | None:
    try:
        result = ReelStudioResponse.model_validate(data)
        if result.duration_seconds != request.duration_seconds or len(result.scenes) != 4:
            return None
        expected = {15: [(0,2),(2,6),(6,12),(12,15)], 30: [(0,3),(3,9),(9,23),(23,30)], 45: [(0,3),(3,12),(12,36),(36,45)]}[request.duration_seconds]
        actual = [(scene.start_seconds, scene.end_seconds) for scene in result.scenes]
        if actual != expected:
            return None
        required = [result.title_ar, result.title_en, result.concept_ar, result.concept_en, result.hook_ar, result.hook_en,
                    result.voiceover_ar, result.voiceover_en, result.caption_ar, result.caption_en,
                    result.cta_ar, result.cta_en, result.production_note_ar, result.production_note_en]
        if any(not item.strip() for item in required):
            return None
        if any(not all((scene.shot_ar, scene.shot_en, scene.screen_text_ar, scene.screen_text_en, scene.voiceover_ar, scene.voiceover_en)) for scene in result.scenes):
            return None
        return result.model_copy(update={"generator": "ollama"})
    except (ValidationError, TypeError, ValueError):
        return None


async def generate_reel_with_provider(request: ReelStudioRequest) -> ReelStudioResponse:
    template = generate_reel_studio(request)
    if not _ollama_enabled():
        return template
    data = await generate_json(_reel_prompt(request))
    result = _valid_reel_result(data, request)
    if result is None:
        return template.model_copy(update={
            "production_note_ar": "تعذر استخدام نموذج Ollama المحلي؛ هذه نسخة القالب المجاني. " + template.production_note_ar,
            "production_note_en": "The local Ollama model was unavailable; this is the free template fallback. " + template.production_note_en,
        })
    return result
