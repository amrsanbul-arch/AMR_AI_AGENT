"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { parseAssistantCommand, type AssistantIntent } from "../../lib/assistant-intents.mjs";

type Lang = "ar" | "en";
type ChatMessage = { id: number; role: "user" | "assistant"; text: string; href?: string; actionLabel?: string };
type PendingIntent = { intent: AssistantIntent; lang: Lang };
type ContentPiece = { title: string; hook: string; body: string; cta: string; hashtags: string[]; scenes: string[] };
type ContentResult = { generator: string; notice: string; pieces: ContentPiece[] };
type ReelResult = { generator: string; title_ar: string; title_en: string; duration_seconds: number; hook_ar: string; hook_en: string; voiceover_ar: string; voiceover_en: string; caption_ar: string; caption_en: string; production_note_ar: string; production_note_en: string; scenes: Array<{ start_seconds: number; end_seconds: number; shot_ar: string; shot_en: string; screen_text_ar: string; screen_text_en: string; voiceover_ar: string; voiceover_en: string }> };
type TrendResult = { source: string; trend_count: number; notice: string; trends: Array<{ query: string; approximate_traffic: string; relevance: number; matched_terms: string[] }> };
type Metric = { available: boolean; value: number | null; reason?: string };
type Insights = { metrics: Record<string, Metric> };
type Performance = { sample_size: number; comparable_count: number; missing_count_metrics: number; top_posts: Array<{ caption: string; likes_and_comments: number }>; top_reels: Array<{ caption: string; likes_and_comments: number }>; notice: string };
type Strategy = { recommendations: Array<{ title_ar: string; title_en: string; text_ar: string; text_en: string }>; limitations_ar: string; limitations_en: string };
type Profile = { official_status: string; official_fields: Record<string, unknown>; official_fields_not_returned: string[]; notice: string };

const copy = {
  ar: {
    brand: "AMR AI", title: "المساعد المحادثي", intro: "اكتب طلبًا قصيرًا بالعربي أو English. أنفّذ فقط الأوامر المحددة هنا، وأوضح لما البيانات أو الصلاحية مش متاحة.",
    placeholder: "مثال: اعمل أفكار عن القهوة…", send: "إرسال", back: "لوحة التحكم", toggle: "EN",
    welcome: "أقدر أساعدك في أفكار وكابشنات وReels، بحث Google Trends، قراءة التحليلات ومراجعة الملف، أو فتح التقويم.",
    prompts: "جرّب مثلًا", examples: ["أفكار محتوى عن القهوة", "اكتب كابشن عن السفر", "حلل حسابي", "اعرض تقويم النشر"],
    follow: "عن أي موضوع؟ ابعت اسم الموضوع عشان أجهز المسودة.", followTrends: "عن أي موضوع أبحث في مؤشرات Google Trends العامة؟", followStrategy: "عن أي موضوع تريد تقرير الاستراتيجية؟",
    unsupported: "مش واضح لي طلب مدعوم. أقدر أجهز أفكار أو كابشن أو سكريبت Reel، أبحث Google Trends، أقرأ التحليلات الرسمية، أراجع الملف، أعمل تقرير استراتيجية، أو أفتح التقويم.",
    busy: "بجهّز…", network: "ماقدرتش أوصل للخادم دلوقتي. تأكد إن API شغال وحاول تاني.", unauthorized: "الطلب ده يحتاج تسجيل دخول المالك. افتح لوحة التحكم وسجّل دخولك، وبعدها جرّب هنا تاني.",
    noConnection: "حساب Instagram لسه مش متصل؛ مفيش تحليلات فعلية أقدر أعرضها. اربطه من لوحة التحكم بالطريقة الرسمية أولًا.",
    unavailable: "المعلومة دي مش متاحة حاليًا من الخادم أو من صلاحيات الحساب؛ ماخمنتش قيمة بديلة.",
    requestFailed: "الخادم ماقدرش ينفذ الطلب بالشكل ده. راجع الموضوع أو صياغة الأمر وجرب تاني.",
    generator: "المولّد", free: "قوالب محلية مجانية", local: "Ollama محلي اختياري", source: "المصدر", trendsLimit: "دي إشارات بحث عامة من Google، مش ترندات Instagram ولا مقياس لاهتمام جمهور حسابك.",
    calendar: "افتح تقويم النشر من هنا. ده انتقال للوحة فقط؛ المساعد ما أنشأش أو غيّر أي منشور أو موعد.",
    profileLimit: "المراجعة تعتمد على الحقول الرسمية التي أعادها التكامل فقط. الحقول الناقصة لا تعني أنها فارغة، ولا يتم تعديل الحساب.",
    analyticsLimit: "العينة من أحدث الوسائط التي أعادها Instagram؛ ترتيب المحتوى يعتمد على الإعجابات والتعليقات المتاحة فقط، وليس معدل التفاعل أو تفسير سبب الأداء.",
    reportLimit: "التوصيات فرضيات للتجربة، وإشارات Google Trends ليست بيانات Instagram.",
    connected: "الحساب متصل", noFields: "مافيش حقول ملف رسمية معروضة في النتيجة الحالية.",
    topicPrompt: "عن أي موضوع؟", noResults: "مافيش عناصر قابلة للمقارنة في عينة البيانات دي.",
  },
  en: {
    brand: "AMR AI", title: "Conversational assistant", intro: "Type a short request in English or Arabic. I only run the bounded actions shown here and call out missing access or data.",
    placeholder: "Try: give me ideas about coffee…", send: "Send", back: "Dashboard", toggle: "عربي",
    welcome: "I can prepare ideas, captions and Reel scripts; check public Google Trends; read official analytics or review your profile; or open the publishing calendar.",
    prompts: "Try", examples: ["content ideas about coffee", "write a caption about travel", "analyze my account", "show publishing calendar"],
    follow: "What topic should the draft cover? Send just the topic.", followTrends: "What topic should I search in public Google Trends signals?", followStrategy: "What topic should the strategy report cover?",
    unsupported: "I don't recognize a supported request. I can prepare ideas, captions or a Reel script; search Google Trends; read official analytics; review the profile; build a strategy report; or open the calendar.",
    busy: "Working…", network: "I couldn't reach the API. Check that it is running, then try again.", unauthorized: "This needs owner sign-in. Open the dashboard, sign in, then try here again.",
    noConnection: "Instagram isn't connected, so there's no real account analytics to show. Connect it through the official flow from the dashboard first.",
    unavailable: "That data isn't available from the server or current account permissions; I didn't guess a replacement value.",
    requestFailed: "The server couldn't handle that request as written. Check the topic or command and try again.",
    generator: "Generator", free: "Free local templates", local: "Optional local Ollama", source: "Source", trendsLimit: "These are public Google search signals, not Instagram trends or evidence of your audience's interest.",
    calendar: "Open the publishing calendar here. This only navigates to the dashboard; I didn't create or change any post or schedule.",
    profileLimit: "This review uses only profile fields returned by the official integration. Missing fields aren't assumed empty, and nothing is edited.",
    analyticsLimit: "This sample uses recent media returned by Instagram; ranking uses only available likes and comments, not an engagement rate or explanation of performance.",
    reportLimit: "Recommendations are hypotheses to test, and Google Trends signals are not Instagram data.",
    connected: "Account connected", noFields: "No official profile fields were returned in this result.",
    topicPrompt: "What topic?", noResults: "No comparable items were available in this data sample.",
  },
} as const;

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

class RequestError extends Error { constructor(readonly status: number) { super("request-failed"); } }
async function jsonRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, { credentials: "include", cache: "no-store", ...init });
  if (!response.ok) throw new RequestError(response.status);
  return await response.json() as T;
}
function langOf(input: string): Lang { return /[\u0600-\u06ff]/.test(input) ? "ar" : "en"; }
function safeValue(value: unknown): string {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

export default function AssistantPage() {
  const [lang, setLang] = useState<Lang>("ar");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState<PendingIntent | null>(null);
  const [busy, setBusy] = useState(false);
  const sequence = useRef(0);
  const bottom = useRef<HTMLDivElement>(null);
  const t = copy[lang];
  const rtl = lang === "ar";

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = rtl ? "rtl" : "ltr";
  }, [lang, rtl]);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [messages, busy]);

  function add(role: ChatMessage["role"], text: string, href?: string, actionLabel?: string) {
    sequence.current += 1;
    setMessages((current) => [...current, { id: sequence.current, role, text, href, actionLabel }]);
  }

  async function runIntent(intent: AssistantIntent, topic: string | null, responseLang: Lang) {
    const words = copy[responseLang];
    try {
      if (intent === "ideas" || intent === "caption") {
        const data = await jsonRequest<ContentResult>("/api/content/generate", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mode: intent, topic, audience: "", tone: "friendly", language: responseLang }),
        });
        const result = data.pieces.map((piece, index) => [
          `${index + 1}. ${piece.title}`, piece.hook, piece.body, piece.cta,
          piece.hashtags.length ? piece.hashtags.join(" ") : "",
        ].filter(Boolean).join("\n")).join("\n\n");
        add("assistant", `${result}\n\n${data.notice}\n${words.generator}: ${data.generator === "ollama" ? words.local : words.free}`);
        return;
      }
      if (intent === "reel") {
        const data = await jsonRequest<ReelResult>("/api/content/reel-studio", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic, audience: "", duration_seconds: 30, tone: "friendly" }),
        });
        const title = responseLang === "ar" ? data.title_ar : data.title_en;
        const hook = responseLang === "ar" ? data.hook_ar : data.hook_en;
        const voiceover = responseLang === "ar" ? data.voiceover_ar : data.voiceover_en;
        const caption = responseLang === "ar" ? data.caption_ar : data.caption_en;
        const note = responseLang === "ar" ? data.production_note_ar : data.production_note_en;
        const scenes = data.scenes.map((scene) => `${scene.start_seconds}–${scene.end_seconds}s: ${responseLang === "ar" ? scene.shot_ar : scene.shot_en}\n${responseLang === "ar" ? scene.screen_text_ar : scene.screen_text_en}`).join("\n");
        add("assistant", `${title}\n\nHook: ${hook}\n\n${voiceover}\n\n${scenes}\n\n${caption}\n\n${note}\n${words.generator}: ${data.generator === "ollama" ? words.local : words.free}`);
        return;
      }
      if (intent === "trends") {
        const params = new URLSearchParams({ topic: topic || "", geo: "EG" });
        const data = await jsonRequest<TrendResult>(`/api/trends/research?${params.toString()}`);
        const rows = data.trends.slice(0, 5).map((item) => `- ${item.query}${item.approximate_traffic ? ` · ${item.approximate_traffic}` : ""} · ${responseLang === "ar" ? "مطابقة" : "match"} ${item.relevance}/100`).join("\n");
        add("assistant", `${words.source}: ${data.source} · ${data.trend_count}\n${rows || words.noResults}\n\n${data.notice || words.trendsLimit}`);
        return;
      }
      if (intent === "analytics") {
        const status = await jsonRequest<{ connected: boolean }>("/api/instagram/status");
        if (!status.connected) { add("assistant", words.noConnection); return; }
        const [insights, performance] = await Promise.all([
          jsonRequest<Insights>("/api/instagram/insights?days=7"),
          jsonRequest<Performance>("/api/instagram/performance/content?limit=12"),
        ]);
        const metricNames: Record<string, [string, string]> = {
          follower_count: ["المتابعون", "Followers"], reach: ["الوصول", "Reach"], views: ["المشاهدات", "Views"],
          accounts_engaged: ["الحسابات المتفاعلة", "Engaged accounts"], total_interactions: ["إجمالي التفاعلات", "Total interactions"],
        };
        const metrics = Object.entries(metricNames).map(([key, name]) => {
          const metric = insights.metrics?.[key];
          return `${responseLang === "ar" ? name[0] : name[1]}: ${metric?.available && metric.value !== null ? metric.value : "—"}`;
        }).join("\n");
        const top = [...performance.top_posts, ...performance.top_reels].slice(0, 3)
          .map((item) => `- ${item.caption?.trim() || (responseLang === "ar" ? "بدون كابشن" : "No caption")} · ${item.likes_and_comments}`).join("\n");
        const countLine = responseLang === "ar"
          ? `العينة: ${performance.sample_size} · قابلة للمقارنة: ${performance.comparable_count} · مقاييس ناقصة: ${performance.missing_count_metrics}`
          : `Sample: ${performance.sample_size} · comparable: ${performance.comparable_count} · missing metrics: ${performance.missing_count_metrics}`;
        add("assistant", `${words.connected}\n${metrics}\n\n${countLine}\n${top || words.noResults}\n\n${performance.notice}\n${words.analyticsLimit}`);
        return;
      }
      if (intent === "profile") {
        const data = await jsonRequest<Profile>("/api/profile/audit", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
        const rows = Object.entries(data.official_fields || {}).map(([key, value]) => `${key}: ${safeValue(value)}`).filter((line) => !line.endsWith(": "));
        const status = data.official_status === "available"
          ? words.connected
          : (responseLang === "ar" ? "بيانات الحساب الرسمية غير متاحة حاليًا." : "Official account data is currently unavailable.");
        add("assistant", `${status}\n${rows.join("\n") || words.noFields}\n\n${data.notice}\n${words.profileLimit}`);
        return;
      }
      if (intent === "strategy") {
        const data = await jsonRequest<Strategy>("/api/strategy/report", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic, geo: "EG" }),
        });
        const suggestions = data.recommendations.slice(0, 3).map((item, index) => `${index + 1}. ${responseLang === "ar" ? item.title_ar : item.title_en}\n${responseLang === "ar" ? item.text_ar : item.text_en}`).join("\n\n");
        add("assistant", `${suggestions}\n\n${responseLang === "ar" ? data.limitations_ar : data.limitations_en}\n${words.reportLimit}`);
      }
    } catch (error) {
      if (error instanceof RequestError && error.status === 401) add("assistant", words.unauthorized, "/?view=overview", words.back);
      else if (error instanceof RequestError) add("assistant", error.status >= 500 ? words.unavailable : words.requestFailed);
      else add("assistant", words.network);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    add("user", text);
    let intent: AssistantIntent;
    let responseLang: Lang;
    let topic: string | null;
    if (pending) {
      intent = pending.intent; responseLang = pending.lang; topic = text; setPending(null);
    } else {
      const parsed = parseAssistantCommand(text);
      if (!parsed) { add("assistant", copy[langOf(text)].unsupported); return; }
      intent = parsed.intent; responseLang = langOf(text); topic = parsed.topic;
    }
    if (intent === "calendar") {
      const words = copy[responseLang];
      add("assistant", words.calendar, "/?view=calendar", words.back);
      return;
    }
    if (["ideas", "caption", "reel", "trends", "strategy"].includes(intent) && !topic) {
      setPending({ intent, lang: responseLang });
      const words = copy[responseLang];
      add("assistant", intent === "trends" ? words.followTrends : intent === "strategy" ? words.followStrategy : words.follow);
      return;
    }
    setBusy(true);
    try { await runIntent(intent, topic, responseLang); }
    finally { setBusy(false); }
  }

  return <main className="assistant-shell" dir={rtl ? "rtl" : "ltr"} lang={lang}>
    <header className="assistant-topbar">
      <Link className="assistant-brand" href="/">{copy[lang].brand}<span> · {copy[lang].title}</span></Link>
      <div className="assistant-head-actions"><Link href="/">{copy[lang].back}</Link><button className="language-button" onClick={() => setLang(rtl ? "en" : "ar")} aria-label={rtl ? "Switch to English" : "التبديل إلى العربية"}>{copy[lang].toggle}</button></div>
    </header>
    <section className="assistant-main">
      <div className="assistant-intro"><span className="assistant-mark">A<span>.</span></span><p className="eyebrow">AMR AI</p><h1>{copy[lang].title}</h1><p>{copy[lang].intro}</p></div>
      <div className="assistant-chat panel" aria-label={copy[lang].title}>
        <div className="assistant-messages" aria-live="polite">
          {messages.length === 0 && <div className="assistant-welcome"><p>{copy[lang].welcome}</p><strong>{copy[lang].prompts}</strong><div className="assistant-examples">{copy[lang].examples.map((example) => <button key={example} type="button" onClick={() => setInput(example)}>{example}</button>)}</div></div>}
          {messages.map((message) => <div key={message.id} className={`chat-bubble ${message.role}`}><p>{message.text}</p>{message.href && <Link className="primary-button" href={message.href}>{message.actionLabel || copy[lang].back} →</Link>}</div>)}
          {busy && <div className="chat-bubble assistant busy-bubble">{copy[lang].busy}</div>}
          <div ref={bottom} />
        </div>
        <form className="assistant-compose" onSubmit={submit}>
          <label className="sr-only" htmlFor="assistant-message">{copy[lang].title}</label>
          <input id="assistant-message" value={input} onChange={(event) => setInput(event.target.value)} placeholder={pending ? copy[pending.lang].topicPrompt : copy[lang].placeholder} disabled={busy} autoComplete="off" />
          <button className="primary-button" type="submit" disabled={busy || !input.trim()}>{copy[lang].send}</button>
        </form>
        <p className="assistant-scope-note">{lang === "ar" ? "لا يرسل رسائل ولا ينشر أو يغيّر الحساب. النشر يظل خلف موافقة النشر الحالية." : "It does not send messages, publish, or edit your account. Publishing remains behind the existing approval flow."}</p>
      </div>
    </section>
  </main>;
}
