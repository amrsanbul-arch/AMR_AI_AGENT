from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ReelStudioRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=180)
    audience: str = Field(default="", max_length=180)
    duration_seconds: Literal[15, 30, 45] = 30
    tone: Literal["friendly", "professional", "playful", "educational"] = "friendly"

    @field_validator("topic", "audience")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    @field_validator("topic")
    @classmethod
    def require_topic(cls, value: str) -> str:
        if len(value) < 2:
            raise ValueError("topic must contain at least two non-space characters")
        return value


class ReelScene(BaseModel):
    start_seconds: int
    end_seconds: int
    shot_ar: str
    shot_en: str
    screen_text_ar: str
    screen_text_en: str
    voiceover_ar: str
    voiceover_en: str


class ReelStudioResponse(BaseModel):
    generator: Literal["free_template"] = "free_template"
    title_ar: str
    title_en: str
    duration_seconds: int
    concept_ar: str
    concept_en: str
    hook_ar: str
    hook_en: str
    voiceover_ar: str
    voiceover_en: str
    caption_ar: str
    caption_en: str
    cta_ar: str
    cta_en: str
    scenes: list[ReelScene]
    production_note_ar: str
    production_note_en: str


def generate_reel_studio(request: ReelStudioRequest) -> ReelStudioResponse:
    """Create an editable bilingual production outline locally; it does not make media or publish."""
    topic = request.topic
    audience_ar = f" للجمهور: {request.audience}." if request.audience else ""
    audience_en = f" Audience: {request.audience}." if request.audience else ""
    schedules = {
        15: [(0, 2), (2, 6), (6, 12), (12, 15)],
        30: [(0, 3), (3, 9), (9, 23), (23, 30)],
        45: [(0, 3), (3, 12), (12, 36), (36, 45)],
    }
    script_ar = [
        f"هل تعرف أهم نقطة لازم تعرفها عن {topic}؟",
        f"المشكلة الشائعة إننا بنعقّد {topic} أو بنبدأ من غير هدف واضح.",
        f"ابدأ بخطوة واحدة: حدّد النتيجة اللي عايز توصل لها، وجرّب طريقة بسيطة على مثال حقيقي. لاحظ الفرق وعدّل حسب تجربتك.",
        "الخلاصة: خطوة واضحة أحسن من كلام كتير. احفظ الفيديو وارجع له.",
    ]
    script_en = [
        f"What's one thing worth knowing about {topic}?",
        f"A common mistake is overcomplicating {topic} or starting without a clear goal.",
        f"Start with one step: choose the outcome you want, then try a simple approach on a real example. Notice what changes and adapt it to your experience.",
        "The takeaway: one clear step beats a lot of noise. Save this for later.",
    ]
    shots_ar = [
        "لقطة قريبة للوجه؛ ابدأ مباشرة بسؤال، مع حركة دخول بسيطة.",
        "لقطة متوسطة وأنت تشرح المشكلة؛ أظهر كلمة مفتاحية على الشاشة.",
        "لقطات تفصيلية متتابعة لمثال أو تطبيق فعلي؛ بدّل الزاوية مرة واحدة.",
        "ارجع للكاميرا بلقطة ثابتة؛ اختم بإشارة بسيطة للحفظ أو المتابعة.",
    ]
    shots_en = [
        "Tight talking-head shot; open on the question with a subtle push-in.",
        "Medium shot explaining the problem; highlight one keyword on screen.",
        "A few close-up cuts showing a real example or demonstration; change angle once.",
        "Return to a steady talking-head shot; finish with a small save/follow gesture.",
    ]
    screen_ar = [
        f"سؤال سريع عن {topic}",
        "تجنّب التعقيد",
        "جرّب خطوة واحدة",
        "احفظها للتطبيق",
    ]
    screen_en = [
        f"A quick question about {topic}",
        "Skip the overthinking",
        "Try one clear step",
        "Save this to try it",
    ]
    scenes = [
        ReelScene(
            start_seconds=start,
            end_seconds=end,
            shot_ar=shots_ar[index],
            shot_en=shots_en[index],
            screen_text_ar=screen_ar[index],
            screen_text_en=screen_en[index],
            voiceover_ar=script_ar[index],
            voiceover_en=script_en[index],
        )
        for index, (start, end) in enumerate(schedules[request.duration_seconds])
    ]
    full_ar = " ".join(script_ar)
    full_en = " ".join(script_en)
    return ReelStudioResponse(
        title_ar=f"Reel: {topic}",
        title_en=f"Reel: {topic}",
        duration_seconds=request.duration_seconds,
        concept_ar=f"فكرة قصيرة تقدّم نقطة عملية واحدة عن {topic} بأسلوب {request.tone}.{audience_ar}",
        concept_en=f"A short Reel sharing one practical point about {topic} in a {request.tone} tone.{audience_en}",
        hook_ar=script_ar[0],
        hook_en=script_en[0],
        voiceover_ar=full_ar,
        voiceover_en=full_en,
        caption_ar=f"خطوة بسيطة عن {topic}: اختر هدفًا واضحًا وجرّب طريقة واحدة على مثال حقيقي. {audience_ar.strip()}\n\n#ريلز #محتوى_مفيد",
        caption_en=f"One simple step for {topic}: pick a clear goal and test one approach on a real example.{audience_en}\n\n#Reels #HelpfulContent",
        cta_ar="احفظه للتطبيق، واكتب سؤالك في التعليقات.",
        cta_en="Save it to try later, and leave your question in the comments.",
        scenes=scenes,
        production_note_ar="مسودة نصية مجانية قابلة للتعديل فقط؛ لا تُنشئ صورًا أو فيديو، ولا تنشر تلقائيًا. راجع الملاءمة والحقائق وأضف تجربتك قبل الاستخدام.",
        production_note_en="Free editable text outline only; it does not generate images or video and never publishes automatically. Check fit and facts, then add your own experience.",
    )
