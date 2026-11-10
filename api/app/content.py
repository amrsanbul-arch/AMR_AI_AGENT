from __future__ import annotations

from enum import Enum
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ContentMode(str, Enum):
    ideas = "ideas"
    caption = "caption"
    reel_script = "reel_script"


class ContentRequest(BaseModel):
    mode: ContentMode
    topic: str = Field(min_length=2, max_length=180)
    audience: str = Field(default="", max_length=180)
    tone: Literal["friendly", "professional", "playful", "educational"] = "friendly"
    language: Literal["ar", "en"] = "ar"

    @field_validator("topic")
    @classmethod
    def clean_topic(cls, value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip()
        if len(cleaned) < 2:
            raise ValueError("topic must contain at least two non-space characters")
        return cleaned

    @field_validator("audience")
    @classmethod
    def clean_audience(cls, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()


class ContentPiece(BaseModel):
    title: str
    hook: str
    body: str
    cta: str
    hashtags: list[str] = Field(default_factory=list)
    scenes: list[str] = Field(default_factory=list)


class ContentResponse(BaseModel):
    mode: ContentMode
    language: Literal["ar", "en"]
    generator: Literal["free_template"] = "free_template"
    notice: str
    pieces: list[ContentPiece]


TONE_AR = {
    "friendly": "ودود وقريب",
    "professional": "احترافي وواضح",
    "playful": "خفيف ومرح",
    "educational": "تعليمي وبسيط",
}
TONE_EN = {
    "friendly": "warm and approachable",
    "professional": "clear and professional",
    "playful": "light and playful",
    "educational": "simple and educational",
}


def generate_content(request: ContentRequest) -> ContentResponse:
    """Create editable starter copy locally; no external model or account data is used."""
    if request.language == "ar":
        audience = f" لـ{request.audience}" if request.audience else ""
        tone = TONE_AR[request.tone]
        if request.mode == ContentMode.ideas:
            pieces = [
                ContentPiece(title=f"معلومة سريعة عن {request.topic}", hook=f"هل تعرف المعلومة دي عن {request.topic}؟", body=f"قدّم نقطة واحدة مفيدة عن {request.topic}{audience}، واشرحها بمثال عملي من غير ادعاءات أو أرقام غير موثقة.", cta="إيه أكتر سؤال عندك عن الموضوع؟", hashtags=["#محتوى_مفيد", "#أفكار_محتوى"]),
                ContentPiece(title=f"خطوة عملية في {request.topic}", hook=f"جرّب الخطوة دي لو مهتم بـ{request.topic}.", body=f"اعرض خطوة بسيطة قابلة للتطبيق، ثم وضّح متى تكون مفيدة ومتى لا تكفي وحدها{audience}.", cta="احفظها وارجع لها وقت ما تحتاجها.", hashtags=["#نصائح", "#تعلم"]),
                ContentPiece(title=f"خرافة وحقيقة عن {request.topic}", hook=f"مش كل اللي بنسمعه عن {request.topic} دقيق.", body=f"اختر اعتقادًا شائعًا، وافصله عن معلومة يمكن التحقق منها. أضف مصدرًا موثوقًا عند النشر{audience}.", cta="اكتب اعتقادًا تحب نراجعه بعد كده.", hashtags=["#معلومة", "#وعي"]),
            ]
        elif request.mode == ContentMode.caption:
            pieces = [ContentPiece(title=f"كابشن عن {request.topic}", hook=f"خلّينا نتكلم عن {request.topic} بطريقة بسيطة.", body=f"{request.topic} يستحق نفهمه بعيدًا عن التعقيد.\n\nالفكرة الأساسية: شارك نقطة واحدة واضحة، ثم مثالًا حقيقيًا من تجربتك أو مصدر موثوق.\n\nالنبرة المقترحة: {tone}{audience}.", cta="إيه رأيك؟ شاركني في التعليقات.", hashtags=["#محتوى_عربي", "#إنستجرام", "#نصائح"])]
        else:
            pieces = [ContentPiece(title=f"سكريبت Reel: {request.topic}", hook=f"0–3 ثوانٍ: ابدأ بسؤال يشد الانتباه عن {request.topic}.", body=f"المدة المقترحة: 20–30 ثانية.\nالتعليق الصوتي: \"لو مهتم بـ{request.topic}، خليني أشاركك نقطة عملية. أولًا، وضّح المشكلة في جملة. ثانيًا، قدّم خطوة واحدة مفيدة ومثالًا واضحًا. وفي الآخر، لخّص الفكرة من غير مبالغة.\"\nالنبرة: {tone}{audience}.", cta="تابع للمزيد من الأفكار، أو اكتب سؤالك.", hashtags=["#ريلز", "#أفكار", "#محتوى_مفيد"], scenes=["0–3 ث: لقطة قريبة وسؤال على الشاشة عن الموضوع.", "3–10 ث: شرح المشكلة بجملة واحدة مع نص مختصر.", "10–22 ث: الخطوة العملية ومثال بصري من تصويرك.", "22–30 ث: خلاصة واضحة وCTA على الشاشة."])]
        notice = "مسودة محلية مجانية قابلة للتعديل؛ لا تستخدم بيانات حساب أو نموذجًا خارجيًا. راجع الحقائق وأضف تجربتك قبل النشر."
    else:
        audience = f" for {request.audience}" if request.audience else ""
        tone = TONE_EN[request.tone]
        if request.mode == ContentMode.ideas:
            pieces = [
                ContentPiece(title=f"A quick fact about {request.topic}", hook=f"Did you know this about {request.topic}?", body=f"Share one useful point about {request.topic}{audience}, explain it with a practical example, and avoid unsupported numbers or claims.", cta="What question do you have about this?", hashtags=["#HelpfulContent", "#ContentIdeas"]),
                ContentPiece(title=f"One practical step for {request.topic}", hook=f"Try this simple step if you care about {request.topic}.", body=f"Show one actionable step, when it helps, and when it may not be enough on its own{audience}.", cta="Save this for later.", hashtags=["#Tips", "#Learn"]),
                ContentPiece(title=f"Myth vs. fact: {request.topic}", hook=f"Not everything we hear about {request.topic} is accurate.", body=f"Pick a common belief and contrast it with a verifiable fact. Add a reliable source before publishing{audience}.", cta="Which claim should we fact-check next?", hashtags=["#FactCheck", "#Awareness"]),
            ]
        elif request.mode == ContentMode.caption:
            pieces = [ContentPiece(title=f"Caption about {request.topic}", hook=f"Let's make {request.topic} easier to understand.", body=f"{request.topic} deserves a clear, practical explanation.\n\nMain point: share one specific idea, then add a real example from your experience or a reliable source.\n\nSuggested tone: {tone}{audience}.", cta="What do you think? Tell me in the comments.", hashtags=["#Instagram", "#Content", "#Tips"])]
        else:
            pieces = [ContentPiece(title=f"Reel script: {request.topic}", hook=f"0–3 sec: open with a compelling question about {request.topic}.", body=f"Suggested length: 20–30 seconds.\nVoiceover: \"If you're interested in {request.topic}, here's one practical point. First, state the problem in one sentence. Then share one useful step and a clear example. Wrap up with a simple, accurate takeaway.\"\nTone: {tone}{audience}.", cta="Follow for more ideas, or leave your question below.", hashtags=["#Reels", "#ContentIdeas", "#HelpfulContent"], scenes=["0–3 sec: close-up with an on-screen question.", "3–10 sec: state the problem in one clear line.", "10–22 sec: show the practical step and an original visual example.", "22–30 sec: summarize and show the CTA."])]
        notice = "Free editable local draft; no account data or external model is used. Verify claims and add your own experience before publishing."
    return ContentResponse(mode=request.mode, language=request.language, notice=notice, pieces=pieces)
