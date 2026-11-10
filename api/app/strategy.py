"""Cautious report builder combining official Instagram media counts and public search signals."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.owner_auth import require_owner
from app.instagram_insights import rank_content_performance
from app.instagram_oauth import Settings, _graph_get, _graph_url, _stored_access_token, MEDIA_FIELDS
from app import trends

router = APIRouter(prefix="/api/strategy", tags=["content strategy"], dependencies=[Depends(require_owner)])


class StrategyRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=120)
    geo: str = Field(default="EG", pattern=r"^[A-Z]{2}$")


def build_strategy_report(topic: str, geo: str, performance: dict | None, trend_report: dict | None,
                          *, generated_at: datetime | None = None, official_status: str = "available",
                          trends_status: str = "available") -> dict:
    """Turn observed values into cautious experiments; never infer audience preferences."""
    now = generated_at or datetime.now(timezone.utc)
    comparable = int(performance.get("comparable_count", 0)) if performance else 0
    sample_size = int(performance.get("sample_size", 0)) if performance else 0
    missing = int(performance.get("missing_count_metrics", 0)) if performance else 0
    posts = performance.get("top_posts", []) if performance else []
    reels = performance.get("top_reels", []) if performance else []
    candidates = []
    if trend_report and isinstance(trend_report.get("trends"), list):
        candidates = [item for item in trend_report["trends"]
                      if isinstance(item, dict) and isinstance(item.get("relevance"), int) and item["relevance"] >= 50][:3]

    recommendations: list[dict] = []
    if official_status != "available" or comparable == 0:
        recommendations.append({
            "kind": "data_gap", "confidence": "insufficient",
            "title_ar": "البيانات الرسمية غير كافية بعد", "title_en": "Official data is not sufficient yet",
            "text_ar": "لم تتوفر عناصر Instagram رسمية بأعداد إعجابات وتعليقات مكتملة؛ هذا لا يعني أن الأرقام صفر. اربط الحساب رسميًا ثم أعد التقرير قبل تغيير الاستراتيجية.",
            "text_en": "No official Instagram items with both likes and comments are available; this does not mean the values are zero. Connect the account officially and rerun before changing strategy.",
            "evidence": [],
        })
    elif comparable < 3:
        recommendations.append({
            "kind": "small_sample", "confidence": "insufficient",
            "title_ar": "العينة صغيرة جدًا للاستنتاج", "title_en": "The sample is too small for a conclusion",
            "text_ar": "لدينا أقل من 3 عناصر قابلة للمقارنة. احتفظ بالنهج الحالي واجمع مزيدًا من بيانات الأداء الرسمية قبل أي تغيير.",
            "text_en": "Fewer than three comparable items are available. Keep the current approach and collect more official performance data before changing it.",
            "evidence": [f"comparable_items={comparable}"],
        })
    else:
        ranked = [row for row in (posts + reels) if isinstance(row, dict)]
        if ranked:
            best = max(ranked, key=lambda row: int(row.get("likes_and_comments", 0)))
            recommendations.append({
                "kind": "content_hypothesis", "confidence": "exploratory",
                "title_ar": "اختبر امتدادًا لأفضل عنصر ظاهر", "title_en": "Test a follow-up to the strongest returned item",
                "text_ar": "جرّب محتوى أصليًا قريبًا من هذا العنصر، ثم قارن نتائجه بنفس المقاييس. الأرقام المعروضة لا تفسر سبب الأداء ولا تثبت أن الموضوع هو السبب.",
                "text_en": "Try an original follow-up near this item, then compare it using the same metrics. These counts do not explain the performance or prove the topic caused it.",
                "evidence": [f"media_id={best.get('id')}", f"likes={best.get('like_count')}", f"comments={best.get('comments_count')}", "metric=likes_plus_comments_only"],
            })
        if posts and reels and len(posts) >= 2 and len(reels) >= 2:
            recommendations.append({
                "kind": "format_test", "confidence": "exploratory",
                "title_ar": "قارن الصيغ باختبار متوازن", "title_en": "Compare formats with a balanced test",
                "text_ar": "توجد منشورات وReels قابلة للمقارنة. جرّب موضوعًا واحدًا بصيغتين متقاربتين؛ هذه العينة لا تثبت أن صيغة بعينها أفضل عمومًا.",
                "text_en": "Comparable posts and Reels are present. Test one topic in two similar formats; this sample does not prove one format is generally better.",
                "evidence": [f"comparable_posts={len(posts)}", f"comparable_reels={len(reels)}"],
            })

    if candidates:
        recommendations.append({
            "kind": "search_signal_experiment", "confidence": "exploratory",
            "title_ar": "حوّل إشارة بحث إلى تجربة محتوى", "title_en": "Turn a search signal into a content experiment",
            "text_ar": "اختر موضوعًا متطابق الكلمات واصنع عنه محتوى أصليًا؛ مؤشرات Google تخص البحث العام فقط، ولا تثبت رواج الموضوع على Instagram أو اهتمام جمهور حسابك.",
            "text_en": "Choose a keyword-overlapping topic for an original post. Google Trends reflects public search signals only; it does not establish Instagram popularity or your audience’s interest.",
            "evidence": [f"google_trends_candidates={len(candidates)}", f"geo={geo}"],
        })
    elif trends_status != "available":
        recommendations.append({
            "kind": "search_signal_unavailable", "confidence": "insufficient",
            "title_ar": "إشارات البحث غير متاحة الآن", "title_en": "Search signals are unavailable right now",
            "text_ar": "تعذر جلب Google Trends؛ لم تُفحص إشارات البحث، لذلك لا نستنتج عدم وجود اهتمام.",
            "text_en": "Google Trends could not be fetched, so search signals were not assessed; this is not evidence of no interest.",
            "evidence": [f"geo={geo}", "source_status=unavailable"],
        })
    else:
        recommendations.append({
            "kind": "no_search_match", "confidence": "limited",
            "title_ar": "لا توجد إشارة بحث متطابقة بما يكفي", "title_en": "No sufficiently matched search signal",
            "text_ar": "لم تظهر مطابقة كلمات قوية في عينة Google Trends الصغيرة؛ هذا لا يثبت غياب اهتمام أو ترند.",
            "text_en": "No strong keyword match appeared in this small Google Trends sample; this does not establish that interest or a trend is absent.",
            "evidence": [f"geo={geo}"],
        })

    limitations_ar = "بيانات Instagram هنا من الحساب المصرح به فقط، ومن أحدث عينة أعادها Graph API؛ الترتيب يستخدم الإعجابات والتعليقات المتاحتين فقط، وليس معدل تفاعل أو إجمالي التفاعلات. Google Trends مصدر منفصل لإشارات بحث عامة، وليس بيانات Instagram أو جمهورك. التوصيات فرضيات اختبار وليست تنبؤات."
    limitations_en = "Instagram evidence is limited to the authorized account and the recent sample returned by Graph API; ranking uses available likes and comments only, not engagement rate or total interactions. Google Trends is a separate public-search source, not Instagram or audience data. Recommendations are test hypotheses, not predictions."
    return {
        "topic": topic, "geo": geo, "generated_at": now.astimezone(timezone.utc).isoformat(),
        "status": "ready" if comparable >= 3 else "limited",
        "official_source": "instagram_graph_api" if official_status == "available" else None,
        "official_status": official_status,
        "sample_size": sample_size, "comparable_count": comparable, "missing_metric_count": missing,
        "performance": performance,
        "trend_source": trend_report.get("source") if trend_report else None,
        "trend_source_url": trend_report.get("source_url") if trend_report else None,
        "trends_status": trends_status,
        "trend_candidates": candidates,
        "recommendations": recommendations,
        "limitations_ar": limitations_ar, "limitations_en": limitations_en,
    }


@router.post("/report")
async def create_strategy_report(request: StrategyRequest) -> dict:
    topic = " ".join(request.topic.split())
    if len(topic) < 2:
        raise HTTPException(status_code=422, detail="Topic must contain at least two non-space characters.")

    performance = None
    official_status = "not_connected"
    settings = Settings.from_env()
    if settings.configured():
        try:
            token, stored = _stored_access_token(settings)
            user_id = stored.get("user_id", "")
            if not isinstance(user_id, str) or not user_id.isdigit():
                official_status = "unavailable"
            else:
                payload = _graph_get(_graph_url(f"{user_id}/media"), token, params={"fields": MEDIA_FIELDS, "limit": 12})
                media = payload.get("data")
                if isinstance(media, list):
                    performance = {"source": "instagram_graph_api", "sample_size": len([item for item in media if isinstance(item, dict)]), **rank_content_performance(media)}
                    official_status = "available" if performance["comparable_count"] else "insufficient_metrics"
                else:
                    official_status = "unavailable"
        except HTTPException:
            official_status = "unavailable"

    trend_report = None
    trends_status = "unavailable"
    try:
        feed = await trends.fetch_google_trends_feed(request.geo)
        trend_report = trends.parse_google_trends_feed(feed, geo=request.geo, topic=topic).model_dump()
        trends_status = "available"
    except (HTTPException, ValueError):
        trends_status = "unavailable"

    return build_strategy_report(topic, request.geo, performance, trend_report,
                                 official_status=official_status, trends_status=trends_status)
