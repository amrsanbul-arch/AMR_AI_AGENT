"use client";

import { useEffect, useState, type FormEvent } from "react";

type Lang = "ar" | "en";
type View = "overview" | "studio" | "calendar" | "insights" | "settings";

type Copy = {
  [key: string]: string;
};
type ContentMode = "ideas" | "caption" | "reel_script";
type ContentPiece = { title: string; hook: string; body: string; cta: string; hashtags: string[]; scenes: string[] };
type ReelScene = { start_seconds: number; end_seconds: number; shot_ar: string; shot_en: string; screen_text_ar: string; screen_text_en: string; voiceover_ar: string; voiceover_en: string };
type ReelBoard = { generator: "free_template"; title_ar: string; title_en: string; duration_seconds: number; concept_ar: string; concept_en: string; hook_ar: string; hook_en: string; voiceover_ar: string; voiceover_en: string; caption_ar: string; caption_en: string; cta_ar: string; cta_en: string; scenes: ReelScene[]; production_note_ar: string; production_note_en: string };
type ContentResult = { mode: ContentMode; language: "ar" | "en"; generator: "free_template"; notice: string; pieces: ContentPiece[] };
type OwnerSession = { configured: boolean; authenticated: boolean };
type InstagramStatus = { status: "not_configured" | "not_connected" | "connected"; connected: boolean; username?: string };
type InstagramAccount = { username: string; account_type?: string | null; media_count?: number | null };
type InstagramMedia = { id: string; caption?: string; media_type?: string; media_product_type?: string; permalink?: string; timestamp?: string; media_url?: string; thumbnail_url?: string; like_count?: number; comments_count?: number };
type InsightPoint = { value: number; end_time?: string };
type InsightDatum = { available: boolean; value: number | null; series: InsightPoint[]; reason?: string | null };
type InstagramInsights = { source: "instagram_graph_api"; range_days: number; since: number; until: number; fetched_at: number; metrics: Record<string, InsightDatum> };
type PublishPost = { id: string; caption: string; media_url: string; media_type: "IMAGE" | "REELS" | "VIDEO"; state: string; scheduled_at?: string | null; instagram_media_id?: string | null; error_code?: string | null };

const words: Record<Lang, Copy> = {
  ar: {
    brand: "AMR AI", product: "مدير Instagram الشخصي", account: "حساب المنشئ", offline: "غير متصل",
    nav: "القائمة الرئيسية", overview: "نظرة عامة", studio: "استوديو المحتوى", calendar: "التقويم", insights: "التحليلات", settings: "الإعدادات",
    workspace: "مساحة العمل", welcome: "مساحة واحدة لفكرتك القادمة.", intro: "خطط للمحتوى، جهّز أفكارك، وتابع أداء حسابك من لوحة واحدة.",
    connect: "ربط Instagram الرسمي", next: "الربط الرسمي قيد التجهيز", privacy: "لن نطلب كلمة مرورك أو رمز تحقق.",
    followers: "المتابعون", reach: "الوصول", engagement: "التفاعل", views: "المشاهدات", waiting: "بانتظار الموافقة", scheduled: "مجدول للنشر",
    unavailable: "تظهر البيانات بعد الربط الرسمي", overviewTitle: "ملخص الحساب", overviewSub: "بيانات الحساب غير متاحة حتى الآن.",
    contentTitle: "مساحة المحتوى", contentSub: "الأفكار والمسودات والمحتوى الجاهز للمراجعة.", openStudio: "افتح استوديو المحتوى", emptyDrafts: "مساحة المسودات جاهزة لك", emptyDraftsSub: "أنشئ أفكارًا وكابشنات وسيناريوهات قابلة للتعديل من استوديو المحتوى.",
    performance: "أداء المحتوى", performanceSub: "ستظهر المقارنات والتوصيات بعد وصول بيانات Insights.", topPosts: "أفضل المنشورات", topReels: "أفضل Reels", noData: "لا توجد بيانات لعرضها بعد",
    scheduleTitle: "تقويم النشر", scheduleSub: "هنا ستراجع المسودات والمواعيد قبل النشر.", approvalsTitle: "مراجعتك أولًا", approvalsSub: "المحتوى لن يُنشر قبل تفعيل صلاحية النشر وموافقتك حسب الوضع المختار.",
    settingsTitle: "إعدادات الحساب", settingsSub: "إعداد الاتصال واللغة وطريقة الموافقة.", connection: "اتصال Instagram", officialOnly: "تكامل رسمي فقط", accountType: "نوع الحساب", creator: "Creator · منشئ محتوى", permissions: "الصلاحيات", insightsTitle: "تحليلات Meta الرسمية", insightsSub: "الأرقام تأتي من Instagram Insights؛ قد لا تتوفر بعض المقاييس أو تتأخر.", metricUnavailable: "لم تُرجع Meta هذه القيمة", officialSource: "مصدر: Instagram Graph API", latest: "أحدث قيمة ضمن الفترة", noInsights: "لا توجد بيانات Insights متاحة لهذه الفترة.", notSet: "لم يتم الربط بعد",
    manual: "يدوي", approvalMode: "موافقة قبل النشر", automation: "أتمتة النشر", stop: "إيقاف الأتمتة", stopNote: "متوقف حتى يتم إعداد الربط الرسمي.",
    mobileNav: "التنقل", coming: "قيد التجهيز", stage: "المرحلة 2 · لوحة التحكم", zeroData: "لا بيانات تجريبية", zeroDataSub: "كل الأرقام تبقى فارغة حتى نقرأها من مصدر حقيقي.",
    today: "آخر 24 ساعة", week: "آخر 7 أيام", month: "آخر 30 يومًا", updated: "آخر تحديث", none: "—", apiStatus: "حالة الربط", noConnection: "لا يوجد اتصال بإنستجرام", onlyOfficial: "لن نستخدم تسجيل دخول أو كشطًا غير رسميًا.",
    startContent: "ابدأ بتجهيز محتواك", startContentSub: "ستتمكن من بناء أفكار وسكربتات ومراجعتها قبل النشر.", security: "الأمان أولًا", securityText: "لا كلمات مرور محفوظة · صلاحيات رسمية · موافقة قبل النشر", daily: "نظرة يومية", contentReady: "ما يحتاج انتباهك", noPending: "لا توجد عناصر للمراجعة بعد", buildNext: "استوديو المحتوى المحلي المجاني جاهز للمسودات؛ لا يوجد نشر أو ربط Instagram بعد.",
    studioTitle: "مساعد المحتوى المجاني", studioIntro: "اكتب موضوعك واختر نوع المسودة. النتائج محلية قابلة للتعديل، ولا تُنشر تلقائيًا.",
    topicLabel: "موضوع المحتوى", topicPlaceholder: "مثال: تصوير الطعام للمطاعم", audienceLabel: "الجمهور (اختياري)", audiencePlaceholder: "مثال: أصحاب المطاعم الصغيرة",
    modeLabel: "نوع المحتوى", ideasMode: "أفكار", captionMode: "كابشن", reelMode: "سكريبت Reel", toneLabel: "النبرة", friendlyTone: "ودودة", professionalTone: "احترافية", playfulTone: "مرحة", educationalTone: "تعليمية",
    generate: "جهّز مسودة", generating: "بجهّز…", generated: "المسودات المقترحة", hookLabel: "الافتتاحية", bodyLabel: "النص", ctaLabel: "دعوة للتفاعل", hashtagsLabel: "هاشتاجات مقترحة", scenesLabel: "تقسيم المشاهد", generatorError: "تعذر الاتصال بخادم المساعد. شغّل API محليًا وحاول تاني.", generatorLocal: "محلي مجاني",
    loading: "جارٍ التحميل…", authTitle: "دخول المالك", authIntro: "سجّل الدخول لإدارة لوحة حسابك فقط.", authSetup: "أضف كلمة مرور مالك آمنة في إعدادات الخادم.", password: "كلمة مرور المالك", login: "دخول", loginError: "تعذر تسجيل الدخول. تحقق من كلمة المرور وإعداد الخادم.", logout: "تسجيل الخروج",
    connected: "متصل رسميًا", notConfigured: "إعداد الربط غير مكتمل", setupPending: "أكمل إعداد تطبيق Meta ومفاتيح OAuth على الخادم أولًا.", connectOfficial: "ربط حساب Instagram رسميًا", oauthNotice: "عاد تسجيل الدخول من Instagram؛ حدّث الحالة لعرض الحساب.", apiLoadError: "تعذر تحميل بيانات Instagram. حدّث الصفحة وحاول مجددًا.", accountData: "بيانات الحساب", accountName: "اسم الحساب", mediaCount: "عدد المنشورات", recentMedia: "أحدث المنشورات", noMedia: "لم تُرجع Meta منشورات لهذا الحساب.", permissionNote: "نستخدم فقط الصلاحيات التي وافقت عليها عبر Meta.", refresh: "تحديث البيانات",

  },
  en: {
    brand: "AMR AI", product: "Personal Instagram Manager", account: "Creator account", offline: "Not connected",
    nav: "Main menu", overview: "Overview", studio: "Content studio", calendar: "Calendar", insights: "Analytics", settings: "Settings",
    workspace: "Workspace", welcome: "One space for your next idea.", intro: "Plan content, shape ideas, and follow account performance from one dashboard.",
    connect: "Connect Instagram officially", next: "Official connection is being prepared", privacy: "We will never ask for your password or verification code.",
    followers: "Followers", reach: "Reach", engagement: "Engagement", views: "Views", waiting: "Awaiting approval", scheduled: "Scheduled",
    unavailable: "Available after official connection", overviewTitle: "Account overview", overviewSub: "Account data is not available yet.",
    contentTitle: "Content workspace", contentSub: "Ideas, drafts, and content ready for review.", openStudio: "Open content studio", emptyDrafts: "Your drafts space is ready", emptyDraftsSub: "Create editable ideas, captions, and scripts in the content studio.",
    performance: "Content performance", performanceSub: "Comparisons and recommendations will appear after Insights data is available.", topPosts: "Top posts", topReels: "Top Reels", noData: "No data to show yet",
    scheduleTitle: "Publishing calendar", scheduleSub: "Review drafts and timing here before publishing.", approvalsTitle: "Your review comes first", approvalsSub: "Content will not publish until publishing permission and your selected approval mode are in place.",
    settingsTitle: "Account settings", settingsSub: "Connection, language, and approval preferences.", connection: "Instagram connection", officialOnly: "Official integration only", accountType: "Account type", creator: "Creator", permissions: "Permissions", insightsTitle: "Official Meta insights", insightsSub: "Values come from Instagram Insights; some metrics may be unavailable or delayed.", metricUnavailable: "Meta did not return this metric", officialSource: "Source: Instagram Graph API", latest: "Latest value in range", noInsights: "No Insights data is available for this period.", notSet: "Not connected",
    manual: "Manual", approvalMode: "Approval before publishing", automation: "Publishing automation", stop: "Stop automation", stopNote: "Inactive until official connection is configured.",
    mobileNav: "Navigation", coming: "Coming soon", stage: "Stage 2 · Dashboard", zeroData: "No sample data", zeroDataSub: "Metrics stay empty until read from a real source.",
    today: "Last 24 hours", week: "Last 7 days", month: "Last 30 days", updated: "Last updated", none: "—", apiStatus: "Connection status", noConnection: "No Instagram connection", onlyOfficial: "No unofficial login or scraping will be used.",
    startContent: "Start preparing content", startContentSub: "Build ideas and scripts, then review them before publishing.", security: "Security first", securityText: "No saved passwords · Official permissions · Review before publishing", daily: "Daily overview", contentReady: "Needs your attention", noPending: "Nothing to review yet", buildNext: "The free local content studio is ready for drafts; Instagram is not connected and nothing publishes.",
    studioTitle: "Free content assistant", studioIntro: "Add a topic and choose a draft type. Results are local and editable; nothing is published.",
    topicLabel: "Content topic", topicPlaceholder: "e.g. food photography for restaurants", audienceLabel: "Audience (optional)", audiencePlaceholder: "e.g. small restaurant owners",
    modeLabel: "Content type", ideasMode: "Ideas", captionMode: "Caption", reelMode: "Reel script", toneLabel: "Tone", friendlyTone: "Friendly", professionalTone: "Professional", playfulTone: "Playful", educationalTone: "Educational",
    generate: "Generate draft", generating: "Working…", generated: "Suggested drafts", hookLabel: "Hook", bodyLabel: "Copy", ctaLabel: "Call to action", hashtagsLabel: "Suggested hashtags", scenesLabel: "Scene outline", generatorError: "Could not reach the assistant API. Start it locally and try again.", generatorLocal: "FREE · LOCAL",
    loading: "Loading…", authTitle: "Owner sign-in", authIntro: "Sign in to manage your account dashboard.", authSetup: "Set a secure owner password in the server configuration.", password: "Owner password", login: "Sign in", loginError: "Could not sign in. Check the password and server setup.", logout: "Sign out",
    connected: "Officially connected", notConfigured: "Connection setup incomplete", setupPending: "Finish Meta app and OAuth configuration on the server first.", connectOfficial: "Connect Instagram officially", oauthNotice: "Returned from Instagram sign-in; refresh to load the account.", apiLoadError: "Could not load Instagram data. Refresh and try again.", accountData: "Account data", accountName: "Account name", mediaCount: "Post count", recentMedia: "Recent posts", noMedia: "Meta returned no posts for this account.", permissionNote: "Only permissions approved through Meta are used.", refresh: "Refresh data",

  },
};

const menu: { id: View; key: string; icon: string }[] = [
  { id: "overview", key: "overview", icon: "grid" },
  { id: "studio", key: "studio", icon: "spark" },
  { id: "calendar", key: "calendar", icon: "calendar" },
  { id: "insights", key: "insights", icon: "chart" },
  { id: "settings", key: "settings", icon: "settings" },
];

function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const paths: Record<string, React.ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
    spark: <><path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-2-5.8L4 11l6-2.2L12 3Z"/><path d="m19 14 1 2.5 2.5 1-2.5 1-1 2.5-1-2.5-2.5-1 2.5-1 1-2.5Z"/></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/></>,
    chart: <><path d="M4 19V5M4 19h17"/><path d="m7 15 4-4 3 2 5-6"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.6a8 8 0 0 1-1.8 1l-.3 1.8h-2.8l-.3-1.8a8 8 0 0 1-1.8-1l-1.7.6-1.4-2.4 1.4-1.1A7 7 0 0 1 7 13l-1.7-.8.7-2.7 1.8.1a8 8 0 0 1 1.4-1.5L8.8 6.3l2.6-1.1 1 1.5a8 8 0 0 1 2.1 0l1-1.5 2.6 1.1-.4 1.8a8 8 0 0 1 1.4 1.5l1.8-.1.7 2.7-1.7.8a7 7 0 0 1-.5 2Z"/></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6"/></>,
    lock: <><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 1 1 8 0v3"/></>,
  };
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name] ?? paths.grid}</svg>;
}

function Metric({ icon, label, note, value = "—" }: { icon: string; label: string; note: string; value?: string }) {
  return <article className="metric-card"><span className="metric-icon"><Icon name={icon} /></span><span className="metric-label">{label}</span><strong className="metric-value">{value}</strong><span className="metric-note">{note}</span></article>;
}

export default function Home() {
  const [lang, setLang] = useState<Lang>("ar");
  const [view, setView] = useState<View>("overview");
  const [range, setRange] = useState<"today" | "week" | "month">("today");
  const [contentMode, setContentMode] = useState<ContentMode>("ideas");
  const [topic, setTopic] = useState("");
  const [audience, setAudience] = useState("");
  const [tone, setTone] = useState("friendly");
  const [contentResult, setContentResult] = useState<ContentResult | null>(null);
  const [contentError, setContentError] = useState("");
  const [studioTab, setStudioTab] = useState<"assistant" | "reels">("reels");
  const [reelDuration, setReelDuration] = useState<15 | 30 | 45>(30);
  const [reelBoard, setReelBoard] = useState<ReelBoard | null>(null);
  const [reelBusy, setReelBusy] = useState(false);
  const [reelError, setReelError] = useState("");
  const [reelSaved, setReelSaved] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);
  const [ownerSession, setOwnerSession] = useState<OwnerSession>({ configured: false, authenticated: false });
  const [ownerPassword, setOwnerPassword] = useState("");
  const [loginBusy, setLoginBusy] = useState(false);
  const [authError, setAuthError] = useState("");
  const [instagramStatus, setInstagramStatus] = useState<InstagramStatus | null>(null);
  const [instagramAccount, setInstagramAccount] = useState<InstagramAccount | null>(null);
  const [instagramMedia, setInstagramMedia] = useState<InstagramMedia[]>([]);
  const [instagramInsights, setInstagramInsights] = useState<InstagramInsights | null>(null);
  const [instagramBusy, setInstagramBusy] = useState(false);
  const [instagramError, setInstagramError] = useState("");
  const [publishPosts, setPublishPosts] = useState<PublishPost[]>([]);
  const [postsLoading, setPostsLoading] = useState(false);
  const [postCaption, setPostCaption] = useState("");
  const [postMediaUrl, setPostMediaUrl] = useState("");
  const [postMediaType, setPostMediaType] = useState<PublishPost["media_type"]>("IMAGE");
  const [postBusy, setPostBusy] = useState(false);
  const [postError, setPostError] = useState("");
  const [oauthNotice, setOauthNotice] = useState("");
  const t = words[lang];
  const rtl = lang === "ar";

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem("amr-reel-studio-v1");
      if (saved) setReelBoard(JSON.parse(saved) as ReelBoard);
    } catch { /* Ignore stale or malformed local drafts. */ }
  }, []);

  useEffect(() => {
    if (!reelBoard) return;
    try {
      window.localStorage.setItem("amr-reel-studio-v1", JSON.stringify(reelBoard));
      setReelSaved(true);
    } catch { setReelSaved(false); }
  }, [reelBoard]);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = rtl ? "rtl" : "ltr";
  }, [lang, rtl]);

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

  async function refreshPosts() {
    setPostsLoading(true);
    try {
      const response = await fetch(`${apiBase}/api/instagram/posts`, { credentials: "include", cache: "no-store" });
      if (response.status === 401) { setOwnerSession((current) => ({ ...current, authenticated: false })); return; }
      if (!response.ok) throw new Error("posts-failed");
      const payload = await response.json() as { data?: PublishPost[] };
      setPublishPosts(Array.isArray(payload.data) ? payload.data : []);
    } catch { setPostError(lang === "ar" ? "تعذر تحميل جدول المحتوى." : "Could not load the publishing queue."); }
    finally { setPostsLoading(false); }
  }

  async function createInstagramDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setPostError("");
    let mediaUrl: URL;
    try { mediaUrl = new URL(postMediaUrl); }
    catch { setPostError(lang === "ar" ? "أدخل رابط وسائط صحيحًا يبدأ بـ HTTPS." : "Enter a valid HTTPS media URL."); return; }
    if (mediaUrl.protocol !== "https:") { setPostError(lang === "ar" ? "يجب أن يبدأ رابط الوسائط بـ HTTPS." : "The media URL must use HTTPS."); return; }
    setPostBusy(true);
    try {
      const response = await fetch(`${apiBase}/api/instagram/posts`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ caption: postCaption, media_url: mediaUrl.toString(), media_type: postMediaType }) });
      if (!response.ok) throw new Error("draft-failed");
      const item = await response.json() as PublishPost; setPublishPosts((items) => [item, ...items]); setPostCaption(""); setPostMediaUrl("");
    } catch {
      setPostError(lang === "ar" ? "تعذر تأكيد حفظ المسودة؛ حدّث قائمة المحتوى قبل محاولة حفظها مرة أخرى." : "Draft saving was not confirmed. Refresh the queue before trying again.");
      void refreshPosts();
    }
    finally { setPostBusy(false); }
  }

  async function approveInstagramPost(id: string, mode: "publish_now" | "schedule", localTime?: string) {
    const item = publishPosts.find((post) => post.id === id);
    if (!item) return;
    let scheduled_at: string | undefined;
    if (mode === "schedule") {
      if (!localTime) { setPostError(lang === "ar" ? "اختر موعدًا قبل الجدولة." : "Choose a time before scheduling."); return; }
      const parsedTime = new Date(localTime);
      if (Number.isNaN(parsedTime.getTime()) || parsedTime.getTime() <= Date.now()) {
        setPostError(lang === "ar" ? "اختر موعدًا مستقبليًا." : "Choose a future time."); return;
      }
      scheduled_at = parsedTime.toISOString();
    }
    const action = mode === "publish_now"
      ? (lang === "ar" ? "نشر هذا المحتوى الآن" : "publish this content now")
      : (lang === "ar" ? `جدولة هذا المحتوى في ${new Date(scheduled_at!).toLocaleString("ar-EG")}` : `schedule this content for ${new Date(scheduled_at!).toLocaleString()}`);
    if (!window.confirm(lang === "ar" ? `هل تؤكد موافقتك على ${action}؟` : `Confirm your approval to ${action}?`)) return;

    setPostBusy(true); setPostError("");
    try {
      const response = await fetch(`${apiBase}/api/instagram/posts/${id}/approve`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ approved: true, mode, ...(scheduled_at ? { scheduled_at } : {}) }) });
      const result = await response.json() as PublishPost;
      if (!response.ok) throw new Error("approval-failed");
      setPublishPosts((items) => items.map((post) => post.id === id ? result : post));
      if (result.state === "unknown") setPostError(lang === "ar" ? "نتيجة النشر غير محسومة؛ لن نعيد المحاولة تلقائيًا لتجنب التكرار. حدّث الحالة قبل أي قرار آخر." : "The publish result is unclear; it will not be retried automatically to avoid duplicates. Refresh status before deciding what to do.");
      else if (result.state === "failed") setPostError(lang === "ar" ? "لم يتم النشر. راجع الاتصال والصلاحيات قبل أي محاولة جديدة." : "It was not published. Check the connection and permissions before trying again.");
    } catch {
      setPostError(lang === "ar" ? "لم يصل تأكيد الإجراء؛ حدّث جدول المحتوى لمعرفة الحالة قبل أي محاولة جديدة." : "There was no confirmation. Refresh the queue to check the status before trying again.");
      void refreshPosts();
    }
    finally { setPostBusy(false); }
  }

  async function cancelInstagramSchedule(id: string) {
    const message = lang === "ar" ? "هل تريد إلغاء موعد هذا المنشور؟" : "Cancel this post's scheduled time?";
    if (!window.confirm(message)) return;
    setPostBusy(true); setPostError("");
    try {
      const response = await fetch(`${apiBase}/api/instagram/posts/${id}/cancel`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: "{}" });
      const result = await response.json() as PublishPost;
      if (!response.ok) throw new Error("cancel-failed");
      setPublishPosts((items) => items.map((item) => item.id === id ? result : item));
    } catch {
      setPostError(lang === "ar" ? "لم يصل تأكيد الإلغاء؛ حدّث الجدول لمعرفة الحالة." : "There was no cancellation confirmation. Refresh the queue to check its status.");
      void refreshPosts();
    }
    finally { setPostBusy(false); }
  }

  async function refreshInstagram() {
    setInstagramBusy(true);
    setInstagramError("");
    try {
      const statusResponse = await fetch(`${apiBase}/api/instagram/status`, { credentials: "include", cache: "no-store" });
      if (statusResponse.status === 401) {
        setOwnerSession((current) => ({ ...current, authenticated: false }));
        throw new Error("not-authenticated");
      }
      if (!statusResponse.ok) throw new Error("status-failed");
      const status = await statusResponse.json() as InstagramStatus;
      setInstagramStatus(status);
      if (!status.connected) {
        setInstagramAccount(null);
        setInstagramMedia([]);
        setInstagramInsights(null);
        return;
      }
      const rangeDays = range === "today" ? 1 : range === "week" ? 7 : 30;
      const [accountResponse, mediaResponse, insightsResponse] = await Promise.all([
        fetch(`${apiBase}/api/instagram/account`, { credentials: "include", cache: "no-store" }),
        fetch(`${apiBase}/api/instagram/media?limit=12`, { credentials: "include", cache: "no-store" }),
        fetch(`${apiBase}/api/instagram/insights?days=${rangeDays}`, { credentials: "include", cache: "no-store" }),
      ]);
      if (!accountResponse.ok || !mediaResponse.ok || !insightsResponse.ok) throw new Error("data-failed");
      const account = await accountResponse.json() as InstagramAccount;
      const media = await mediaResponse.json() as { data?: InstagramMedia[] };
      const insights = await insightsResponse.json() as InstagramInsights;
      setInstagramAccount(account);
      setInstagramMedia(Array.isArray(media.data) ? media.data : []);
      setInstagramInsights(insights);
    } catch (error) {
      if (!(error instanceof Error && error.message === "not-authenticated")) setInstagramError(t.apiLoadError);
    } finally {
      setInstagramBusy(false);
    }
  }

  useEffect(() => {
    let active = true;
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    const params = new URLSearchParams(window.location.search);
    if (params.has("instagram")) {
      setOauthNotice(t.oauthNotice);
      window.history.replaceState({}, "", `${window.location.pathname}#settings`);
    }
    fetch(`${apiBaseUrl}/api/auth/session`, { credentials: "include", cache: "no-store" })
      .then((response) => response.json() as Promise<OwnerSession>)
      .then((session) => { if (active) { setOwnerSession(session); setAuthLoading(false); } })
      .catch(() => { if (active) { setOwnerSession({ configured: false, authenticated: false }); setAuthLoading(false); } });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!authLoading && ownerSession.authenticated) { void refreshInstagram(); void refreshPosts(); }
  }, [authLoading, ownerSession.authenticated, range]);

  async function loginOwner(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoginBusy(true);
    setAuthError("");
    try {
      const response = await fetch(`${apiBase}/api/auth/login`, {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: ownerPassword }),
      });
      if (!response.ok) throw new Error("login-failed");
      setOwnerPassword("");
      const sessionResponse = await fetch(`${apiBase}/api/auth/session`, { credentials: "include", cache: "no-store" });
      const session = await sessionResponse.json() as OwnerSession;
      setOwnerSession(session);
    } catch {
      setAuthError(t.loginError);
    } finally {
      setLoginBusy(false);
    }
  }

  async function logoutOwner() {
    try {
      const response = await fetch(`${apiBase}/api/auth/logout`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: "{}" });
      if (!response.ok) throw new Error("logout-failed");
      setOwnerSession((current) => ({ ...current, authenticated: false }));
      setInstagramAccount(null);
      setInstagramMedia([]);
      setInstagramStatus(null);
    } catch {
      setInstagramError(t.apiLoadError);
    }
  }

  async function generateContent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setGenerating(true);
    setContentError("");
    setContentResult(null);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
      const response = await fetch(`${apiBase}/api/content/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: contentMode, topic, audience, tone, language: lang }),
      });
      if (!response.ok) throw new Error("content generation failed");
      setContentResult(await response.json() as ContentResult);
    } catch {
      setContentError(t.generatorError);
    } finally {
      setGenerating(false);
    }
  }

  async function generateReelBoard(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setReelBusy(true); setReelError("");
    try {
      const response = await fetch(`${apiBase}/api/content/reel-studio`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, audience, duration_seconds: reelDuration, tone }),
      });
      if (!response.ok) throw new Error("reel-studio-failed");
      setReelBoard(await response.json() as ReelBoard);
    } catch {
      setReelError(lang === "ar" ? "تعذر تجهيز لوحة الـReel. تأكد أن خادم المشروع يعمل ثم أعد المحاولة." : "Could not build the Reel board. Check that the project server is running, then try again.");
    } finally { setReelBusy(false); }
  }

  function updateReelScene(index: number, field: keyof ReelScene, value: string) {
    setReelBoard((board) => board ? { ...board, scenes: board.scenes.map((scene, current) => current === index ? { ...scene, [field]: value } : scene) } : board);
  }

  async function copyReelBoard() {
    if (!reelBoard) return;
    const text = reelBoard.scenes.map((scene) => `${scene.start_seconds}–${scene.end_seconds}s
SHOT / اللقطة: ${scene.shot_en}
${scene.shot_ar}
ON SCREEN / النص: ${scene.screen_text_en} | ${scene.screen_text_ar}
VO EN: ${scene.voiceover_en}
VO AR: ${scene.voiceover_ar}`).join("\n\n");
    const full = `${reelBoard.title_ar} / ${reelBoard.title_en}\n\n${text}\n\nCAPTION AR\n${reelBoard.caption_ar}\n\nCAPTION EN\n${reelBoard.caption_en}`;
    try { await navigator.clipboard.writeText(full); setReelSaved(true); }
    catch { setReelError(lang === "ar" ? "تعذر النسخ تلقائيًا؛ استخدم زر التصدير النصي." : "Clipboard access is unavailable; use the text export instead."); }
  }

  function exportReelBoard() {
    if (!reelBoard) return;
    const sceneText = reelBoard.scenes.map((scene) => `SCENE ${scene.start_seconds}–${scene.end_seconds}s\nSHOT AR: ${scene.shot_ar}\nSHOT EN: ${scene.shot_en}\nON-SCREEN AR: ${scene.screen_text_ar}\nON-SCREEN EN: ${scene.screen_text_en}\nVOICEOVER AR: ${scene.voiceover_ar}\nVOICEOVER EN: ${scene.voiceover_en}`).join("\n\n");
    const contents = `${reelBoard.title_ar} / ${reelBoard.title_en}\n${reelBoard.duration_seconds}s\n\n${sceneText}\n\nCAPTION AR\n${reelBoard.caption_ar}\n\nCAPTION EN\n${reelBoard.caption_en}\n`;
    const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([contents], { type: "text/plain;charset=utf-8" })); link.download = "reel-storyboard-bilingual.txt"; link.click(); URL.revokeObjectURL(link.href);
  }

  function insightValue(name: string): string {
    const datum = instagramInsights?.metrics?.[name];
    return datum?.available && typeof datum.value === "number"
      ? new Intl.NumberFormat(lang === "ar" ? "ar-EG" : "en-US", { maximumFractionDigits: 0 }).format(datum.value)
      : "—";
  }

  function insightNote(name: string): string {
    return instagramInsights?.metrics?.[name]?.available ? t.latest : t.metricUnavailable;
  }

  function changeView(next: View) {
    setView(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  if (authLoading) return <main className="auth-gate" dir={rtl ? "rtl" : "ltr"}><div className="auth-panel panel">{t.loading}</div></main>;
  if (ownerSession.configured && !ownerSession.authenticated) return <main className="auth-gate" dir={rtl ? "rtl" : "ltr"} lang={lang}><div className="auth-panel panel"><div className="brand-mark">A<span>.</span></div><p className="eyebrow">{t.brand}</p><h1>{t.authTitle}</h1><p>{t.authIntro}</p><form className="owner-login-form" onSubmit={loginOwner}><label htmlFor="owner-password-gate">{t.password}</label><input id="owner-password-gate" type="password" autoComplete="current-password" required minLength={14} value={ownerPassword} onChange={(event) => setOwnerPassword(event.target.value)} /><button className="primary-button" type="submit" disabled={loginBusy}>{loginBusy ? t.loading : t.login}</button>{authError && <p className="form-error" role="alert">{authError}</p>}</form><button className="language-button" onClick={() => setLang(rtl ? "en" : "ar")}>{rtl ? "EN" : "عربي"}</button></div></main>;

  return (
    <main className="app-shell" dir={rtl ? "rtl" : "ltr"} lang={lang}>
      <aside className="sidebar">
        <a className="brand" href="#home" onClick={(e) => { e.preventDefault(); changeView("overview"); }}>
          <span className="brand-mark">A<span>.</span></span>
          <span className="brand-copy"><strong>{t.brand}</strong><small>{t.product}</small></span>
        </a>
        <div className="sidebar-label">{t.nav}</div>
        <nav className="side-nav" aria-label={t.nav}>
          {menu.map((item) => <button key={item.id} className={`nav-item ${view === item.id ? "active" : ""}`} onClick={() => changeView(item.id)} aria-current={view === item.id ? "page" : undefined}>
            <Icon name={item.icon} /><span>{t[item.key]}</span>{item.id === "studio" && <span className="nav-tag">{lang === "ar" ? "مجاني" : "Free"}</span>}
          </button>)}
        </nav>
        <div className="sidebar-bottom">
          <div className="secure-mini"><Icon name="lock" size={17}/><span>{t.officialOnly}</span></div>
          <button className="profile-button" onClick={() => changeView("settings")}>
            <span className="avatar">A</span><span className="profile-copy"><strong>Amr</strong><small>{t.account}</small></span><span className="profile-dot" />
          </button>
        </div>
      </aside>

      <section className="main-panel">
        <header className="topbar">
          <div className="breadcrumb"><span>{t.workspace}</span><span className="crumb-divider">/</span><strong>{t[view]}</strong></div>
          <div className="top-actions">
            <span className="connection-pill"><i />{instagramStatus?.connected ? t.connected : t.offline}</span>
            <button className="language-button" onClick={() => setLang(rtl ? "en" : "ar")} aria-label={rtl ? "Switch to English" : "التبديل إلى العربية"}>{rtl ? "EN" : "عربي"}</button>
            <span className="avatar top-avatar" aria-label="Amr">A</span>
          </div>
        </header>

        {view === "overview" && <>
          <section className="hero-panel">
            <div className="hero-orb orb-one"/><div className="hero-orb orb-two"/>
            <div className="hero-copy">
              <span className="hero-kicker"><span className="live-dot"/>{t.stage}</span>
              <h1>{t.welcome}</h1>
              <p>{t.intro}</p>
              <div className="hero-actions">
                <button className="primary-button" onClick={() => { if (instagramStatus?.status === "not_configured") return; window.location.assign(`${apiBase}/api/instagram/connect`); }} disabled={!ownerSession.authenticated || instagramStatus?.status !== "not_connected"}><span>{instagramStatus?.status === "not_configured" ? t.notConfigured : t.connect}</span><Icon name="arrow" size={17}/></button>
                <span className="button-note">{instagramStatus?.status === "not_configured" ? t.setupPending : t.privacy}</span>
              </div>
            </div>
            <div className="hero-side">
              <div className="account-orbit"><span className="orbit-ring"/><span className="orbit-core">A</span><span className="orbit-star star-a"/><span className="orbit-star star-b"/></div>
              <div className="account-chip"><span className="account-avatar">A</span><span><strong>{t.account}</strong><small>Instagram · Creator</small></span><i /></div>
            </div>
          </section>

          <div className="section-heading"><div><p className="eyebrow">{t.daily}</p><h2>{t.overviewTitle}</h2></div><div className="range-control" role="group" aria-label={t.overviewTitle}>{(["today", "week", "month"] as const).map((period) => <button key={period} className={range === period ? "selected" : ""} aria-pressed={range === period} onClick={() => setRange(period)}>{t[period]}</button>)}</div></div>
          <section className="metrics-grid" aria-label={t.overviewTitle}>
            <Metric icon="grid" label={t.followers} note={instagramInsights ? insightNote("follower_count") : t.unavailable} value={instagramInsights ? insightValue("follower_count") : "—"}/><Metric icon="chart" label={t.reach} note={instagramInsights ? insightNote("reach") : t.unavailable} value={instagramInsights ? insightValue("reach") : "—"}/><Metric icon="spark" label={t.engagement} note={instagramInsights ? insightNote("total_interactions") : t.unavailable} value={instagramInsights ? insightValue("total_interactions") : "—"}/><Metric icon="chart" label={t.views} note={instagramInsights ? insightNote("views") : t.unavailable} value={instagramInsights ? insightValue("views") : "—"}/>
          </section>

          <section className="lower-grid">
            <article className="panel performance-panel">
              <div className="panel-heading"><div><h3>{t.performance}</h3><p>{t.performanceSub}</p></div><button className="icon-button" aria-label={t.insights} onClick={() => changeView("insights")}><Icon name="arrow" size={17}/></button></div>
              <div className="chart-empty"><div className="chart-gridline line-one"/><div className="chart-gridline line-two"/><div className="chart-gridline line-three"/><div className="chart-message"><span className="chart-badge"><Icon name="chart" size={18}/></span><strong>{t.noData}</strong><small>{t.zeroDataSub}</small></div></div>
              <div className="chart-legend"><span><i className="legend-green"/>{t.reach}</span><span><i className="legend-gold"/>{t.engagement}</span></div>
            </article>
            <article className="panel attention-panel">
              <div className="panel-heading"><div><h3>{t.contentReady}</h3><p>{t.approvalsSub}</p></div><span className="attention-icon"><Icon name="lock" size={17}/></span></div>
              <div className="attention-empty"><span className="empty-badge"><Icon name="calendar" size={22}/></span><strong>{t.noPending}</strong><span>{t.noData}</span></div>
              <button className="text-button" onClick={() => changeView("studio")}>{t.openStudio}<Icon name="arrow" size={16}/></button>
            </article>
          </section>

          <section className="feature-grid">
            <button className="feature-card feature-green" onClick={() => changeView("studio")}><span className="feature-icon"><Icon name="spark"/></span><span className="feature-copy"><strong>{t.startContent}</strong><small>{t.startContentSub}</small></span><Icon name="arrow" size={18}/></button>
            <div className="feature-card feature-neutral"><span className="feature-icon"><Icon name="lock"/></span><span className="feature-copy"><strong>{t.security}</strong><small>{t.securityText}</small></span><span className="feature-state">{t.officialOnly}</span></div>
          </section>
          <footer className="page-footer"><span>{t.zeroData}</span><span>{t.buildNext}</span></footer>
        </>}

        {view === "studio" && <section className="page-content">
          <div className="page-title-row"><div><p className="eyebrow">{t.stage}</p><h1>{t.contentTitle}</h1><p>{t.contentSub}</p></div><span className="status-tag">{t.studioTitle}</span></div>
          <div className="studio-switch" role="tablist" aria-label={lang === "ar" ? "أدوات الاستوديو" : "Studio tools"}>
            <button role="tab" aria-selected={studioTab === "reels"} className={studioTab === "reels" ? "active" : ""} onClick={() => setStudioTab("reels")} type="button">{lang === "ar" ? "استوديو Reels" : "Reels studio"}</button>
            <button role="tab" aria-selected={studioTab === "assistant"} className={studioTab === "assistant" ? "active" : ""} onClick={() => setStudioTab("assistant")} type="button">{lang === "ar" ? "أفكار وكابشنات" : "Ideas & captions"}</button>
          </div>
          {studioTab === "reels" && <>
            <div className="studio-workspace panel reel-setup">
              <div className="studio-intro"><span className="studio-art reel-art"><Icon name="spark" size={25}/></span><div><h2>{lang === "ar" ? "خطّط Reel لقطة بلقطة" : "Plan your Reel, shot by shot"}</h2><p>{lang === "ar" ? "اكتب الفكرة، واختر المدة؛ جهّزنا لك لوحة تصوير وسكريبتًا عربيًا وإنجليزيًا قابلين للتعديل." : "Set the idea and length to get an editable shot list and Arabic + English script."}</p></div><span className="reel-free-tag">{lang === "ar" ? "محلي · مجاني" : "LOCAL · FREE"}</span></div>
              <form className="content-form reel-form" onSubmit={generateReelBoard}>
                <div className="form-field"><label htmlFor="reel-topic">{lang === "ar" ? "فكرة الـReel" : "Reel idea"}</label><input id="reel-topic" required minLength={2} maxLength={180} value={topic} onChange={(event) => setTopic(event.target.value)} placeholder={t.topicPlaceholder}/></div>
                <div className="reel-form-row">
                  <div className="form-field"><label htmlFor="reel-audience">{t.audienceLabel}</label><input id="reel-audience" maxLength={180} value={audience} onChange={(event) => setAudience(event.target.value)} placeholder={t.audiencePlaceholder}/></div>
                  <div className="form-field"><label htmlFor="reel-tone">{t.toneLabel}</label><select id="reel-tone" value={tone} onChange={(event) => setTone(event.target.value)}><option value="friendly">{t.friendlyTone}</option><option value="professional">{t.professionalTone}</option><option value="playful">{t.playfulTone}</option><option value="educational">{t.educationalTone}</option></select></div>
                  <div className="form-field"><label>{lang === "ar" ? "مدة الفيديو" : "Reel length"}</label><div className="duration-picker" role="group" aria-label={lang === "ar" ? "مدة الفيديو" : "Reel length"}>{([15, 30, 45] as const).map((seconds) => <button key={seconds} type="button" aria-pressed={reelDuration === seconds} className={reelDuration === seconds ? "selected" : ""} onClick={() => setReelDuration(seconds)}>{seconds}s</button>)}</div></div>
                </div>
                <button className="primary-button studio-submit" type="submit" disabled={reelBusy || topic.trim().length < 2}><span>{reelBusy ? (lang === "ar" ? "جارٍ إعداد اللوحة…" : "Building your board…") : (lang === "ar" ? "جهّز لوحة التصوير" : "Build shot list")}</span><Icon name="spark" size={17}/></button>
                {reelError && <p className="form-error" role="alert">{reelError}</p>}
              </form>
            </div>
            {reelBoard && <section className="reel-board" aria-live="polite">
              <div className="reel-board-head"><div><p className="eyebrow">{lang === "ar" ? "لوحة التصوير" : "YOUR STORYBOARD"}</p><h2>{lang === "ar" ? reelBoard.title_ar : reelBoard.title_en}</h2><p>{lang === "ar" ? reelBoard.concept_ar : reelBoard.concept_en}</p></div><span className="duration-badge">{reelBoard.duration_seconds}s · {lang === "ar" ? "٤ مشاهد" : "4 scenes"}</span></div>
              <div className="reel-board-toolbar"><span className="autosave-note"><i/> {lang === "ar" ? "يُحفظ تلقائيًا على هذا الجهاز" : "Auto-saved on this device"}</span><div><button type="button" className="secondary-button" onClick={() => void copyReelBoard()}>{lang === "ar" ? "نسخ اللوحة" : "Copy board"}</button><button type="button" className="secondary-button" onClick={exportReelBoard}>{lang === "ar" ? "تصدير TXT" : "Export TXT"}</button></div></div>
              <div className="reel-scene-list">{reelBoard.scenes.map((scene, index) => <article className="reel-scene panel" key={`${index}-${scene.start_seconds}`}>
                <div className="scene-topline"><span className="scene-number">{String(index + 1).padStart(2, "0")}</span><div><strong>{lang === "ar" ? `المشهد ${index + 1}` : `Scene ${index + 1}`}</strong><span>{String(scene.start_seconds).padStart(2, "0")}s — {String(scene.end_seconds).padStart(2, "0")}s</span></div><span className="scene-duration">{scene.end_seconds - scene.start_seconds}s</span></div>
                <div className="scene-edit-grid">
                  <label className="scene-edit"><span>🎥 {lang === "ar" ? "اللقطة · عربي" : "Shot · Arabic"}</span><textarea rows={3} value={scene.shot_ar} onChange={(event) => updateReelScene(index, "shot_ar", event.target.value)}/></label>
                  <label className="scene-edit" dir="ltr"><span>🎥 Shot · English</span><textarea rows={3} value={scene.shot_en} onChange={(event) => updateReelScene(index, "shot_en", event.target.value)}/></label>
                  <label className="scene-edit"><span>▤ {lang === "ar" ? "نص الشاشة · عربي" : "On-screen text · Arabic"}</span><input value={scene.screen_text_ar} onChange={(event) => updateReelScene(index, "screen_text_ar", event.target.value)}/></label>
                  <label className="scene-edit" dir="ltr"><span>▤ On-screen text · English</span><input value={scene.screen_text_en} onChange={(event) => updateReelScene(index, "screen_text_en", event.target.value)}/></label>
                  <label className="scene-edit"><span>🎙 {lang === "ar" ? "التعليق الصوتي · عربي" : "Voiceover · Arabic"}</span><textarea rows={3} value={scene.voiceover_ar} onChange={(event) => updateReelScene(index, "voiceover_ar", event.target.value)}/></label>
                  <label className="scene-edit" dir="ltr"><span>🎙 Voiceover · English</span><textarea rows={3} value={scene.voiceover_en} onChange={(event) => updateReelScene(index, "voiceover_en", event.target.value)}/></label>
                </div>
              </article>)}</div>
              <div className="reel-captions"><label className="scene-edit"><span>{lang === "ar" ? "الكابشن · عربي" : "Caption · Arabic"}<small>{reelBoard.caption_ar.length}/2,200</small></span><textarea rows={4} maxLength={2200} value={reelBoard.caption_ar} onChange={(event) => setReelBoard((board) => board ? { ...board, caption_ar: event.target.value } : board)}/></label><label className="scene-edit" dir="ltr"><span>Caption · English<small>{reelBoard.caption_en.length}/2,200</small></span><textarea rows={4} maxLength={2200} value={reelBoard.caption_en} onChange={(event) => setReelBoard((board) => board ? { ...board, caption_en: event.target.value } : board)}/></label></div>
              <p className="reel-note">{lang === "ar" ? reelBoard.production_note_ar : reelBoard.production_note_en}</p>
            </section>}
          </>}
          {studioTab === "assistant" && <div className="studio-workspace panel">
            <div className="studio-intro"><span className="studio-art"><Icon name="spark" size={25}/></span><div><h2>{t.studioTitle}</h2><p>{t.studioIntro}</p></div></div>
            <form className="content-form" onSubmit={generateContent}>
              <div className="form-field"><label htmlFor="topic">{t.topicLabel}</label><input id="topic" required minLength={2} maxLength={180} value={topic} onChange={(e) => setTopic(e.target.value)} placeholder={t.topicPlaceholder}/></div>
              <div className="form-field"><label htmlFor="audience">{t.audienceLabel}</label><input id="audience" maxLength={180} value={audience} onChange={(e) => setAudience(e.target.value)} placeholder={t.audiencePlaceholder}/></div>
              <div className="form-row">
                <div className="form-field"><label htmlFor="mode">{t.modeLabel}</label><select id="mode" value={contentMode} onChange={(e) => setContentMode(e.target.value as ContentMode)}><option value="ideas">{t.ideasMode}</option><option value="caption">{t.captionMode}</option><option value="reel_script">{t.reelMode}</option></select></div>
                <div className="form-field"><label htmlFor="tone">{t.toneLabel}</label><select id="tone" value={tone} onChange={(e) => setTone(e.target.value)}><option value="friendly">{t.friendlyTone}</option><option value="professional">{t.professionalTone}</option><option value="playful">{t.playfulTone}</option><option value="educational">{t.educationalTone}</option></select></div>
              </div>
              <button className="primary-button studio-submit" type="submit" disabled={generating}><span>{generating ? t.generating : t.generate}</span><Icon name="spark" size={17}/></button>
              {contentError && <p className="form-error" role="alert">{contentError}</p>}
            </form>
          </div>}
          {studioTab === "assistant" && contentResult && <section className="generated-results" aria-live="polite"><div className="results-heading"><h2>{t.generated}</h2><span className="status-tag">{contentResult.generator === "free_template" ? t.generatorLocal : ""}</span></div><p className="result-notice">{contentResult.notice}</p><div className="result-grid">{contentResult.pieces.map((piece, index) => <article className="result-card panel" key={`${piece.title}-${index}`}><p className="eyebrow">{contentResult.mode === "ideas" ? `${t.ideasMode} ${index + 1}` : t.generated}</p><h3>{piece.title}</h3><div className="result-block"><strong>{t.hookLabel}</strong><p>{piece.hook}</p></div><div className="result-block"><strong>{t.bodyLabel}</strong><p className="result-body">{piece.body}</p></div>{piece.scenes.length > 0 && <div className="result-block"><strong>{t.scenesLabel}</strong><ol>{piece.scenes.map((scene) => <li key={scene}>{scene}</li>)}</ol></div>}<div className="result-block"><strong>{t.ctaLabel}</strong><p>{piece.cta}</p></div><div className="result-block"><strong>{t.hashtagsLabel}</strong><p className="hashtags">{piece.hashtags.join(" ")}</p></div></article>)}</div></section>}
          {studioTab === "assistant" && <div className="info-strip"><strong>{t.approvalsTitle}</strong><span>{t.approvalsSub}</span></div>}
        </section>}

        {view === "calendar" && <section className="page-content">
          <div className="page-title-row"><div><p className="eyebrow">{t.stage}</p><h1>{t.scheduleTitle}</h1><p>{lang === "ar" ? "كل منشور يحتاج موافقتك الصريحة قبل النشر أو الجدولة." : "Every post needs your explicit approval before publishing or scheduling."}</p></div><span className="status-tag">{instagramStatus?.connected ? t.connected : t.offline}</span></div>
          <div className="studio-workspace panel">
            <div className="studio-intro"><span className="studio-art"><Icon name="calendar" size={24}/></span><div><h2>{lang === "ar" ? "جهّز للمراجعة" : "Prepare for review"}</h2><p>{lang === "ar" ? "احفظ المسودة أولًا؛ لن تُنشر أو تُجدول إلا بعد موافقتك الصريحة." : "Save a draft first. Nothing publishes or gets scheduled without your explicit approval."}</p></div></div>
            <form className="content-form" onSubmit={createInstagramDraft}>
              <div className="form-field"><label htmlFor="publish-caption">{lang === "ar" ? "الكابشن (حتى 2200 حرف)" : "Caption (up to 2,200 characters)"}</label><textarea id="publish-caption" maxLength={2200} rows={4} value={postCaption} onChange={(event) => setPostCaption(event.target.value)} /></div>
              <div className="form-field"><label htmlFor="publish-url">{lang === "ar" ? "رابط الصورة أو الفيديو العام (HTTPS)" : "Public image or video URL (HTTPS)"}</label><input id="publish-url" type="url" required value={postMediaUrl} onChange={(event) => setPostMediaUrl(event.target.value)} placeholder="https://" /></div>
              <div className="form-field"><label htmlFor="publish-type">{lang === "ar" ? "النوع" : "Media type"}</label><select id="publish-type" value={postMediaType} onChange={(event) => setPostMediaType(event.target.value as PublishPost["media_type"])}><option value="IMAGE">{lang === "ar" ? "صورة" : "Image"}</option><option value="REELS">Reel</option><option value="VIDEO">{lang === "ar" ? "فيديو" : "Video"}</option></select></div>
              <button className="primary-button" type="submit" disabled={postBusy || !ownerSession.authenticated}><span>{postBusy ? (lang === "ar" ? "جارٍ الحفظ…" : "Saving…") : (lang === "ar" ? "حفظ كمسودة للمراجعة" : "Save draft for review")}</span></button>
            </form>
          </div>
          {postError && <p className="form-error" role="alert">{postError}</p>}
          <section className="queue-section">
            <div className="panel-heading queue-heading"><div><h2>{lang === "ar" ? "قائمة المحتوى" : "Content queue"}</h2><p>{lang === "ar" ? "راجع كل منشور قبل الموافقة أو الجدولة." : "Review each post before approving or scheduling it."}</p></div><button className="secondary-button" type="button" disabled={postsLoading || postBusy} onClick={() => void refreshPosts()}>{postsLoading ? (lang === "ar" ? "جارٍ التحديث…" : "Refreshing…") : (lang === "ar" ? "تحديث القائمة" : "Refresh queue")}</button></div>
            {postsLoading && publishPosts.length === 0 ? <div className="empty-note">{lang === "ar" ? "جارٍ تحميل المنشورات…" : "Loading posts…"}</div> : publishPosts.length === 0 ? <div className="empty-note">{lang === "ar" ? "لا توجد مسودات بعد. أضف منشورًا للمراجعة." : "No drafts yet. Add a post for review."}</div> : <div className="queue-grid">{publishPosts.map((item) => {
              const stateLabels: Record<string, string> = lang === "ar"
                ? { draft: "مسودة · تنتظر مراجعتك", scheduled: "مجدول", approved: "تمت الموافقة", publishing: "جارٍ النشر", published: "تم النشر", cancelled: "ملغي", failed: "فشل النشر", unknown: "النتيجة غير محسومة" }
                : { draft: "Draft · awaiting your review", scheduled: "Scheduled", approved: "Approved", publishing: "Publishing", published: "Published", cancelled: "Cancelled", failed: "Failed", unknown: "Result unclear" };
              const typeLabel = item.media_type === "IMAGE" ? (lang === "ar" ? "صورة" : "Image") : item.media_type === "REELS" ? "Reel" : (lang === "ar" ? "فيديو" : "Video");
              return <article className="panel publish-card" key={item.id}>
                <div className="publish-card-head"><span className={`status-tag state-${item.state}`}>{stateLabels[item.state] || item.state}</span><span className="media-type-tag">{typeLabel}</span></div>
                <div className="publish-preview" aria-label={lang === "ar" ? "معاينة الوسائط" : "Media preview"}>{item.media_type === "IMAGE" ? <img src={item.media_url} alt={lang === "ar" ? "معاينة المنشور" : "Post preview"} loading="lazy" onError={(event) => { event.currentTarget.style.display = "none"; }} /> : <video src={item.media_url} controls preload="metadata" aria-label={lang === "ar" ? "معاينة الفيديو" : "Video preview"} />}</div>
                <a className="asset-link" href={item.media_url} target="_blank" rel="noreferrer">{lang === "ar" ? "فتح الوسائط" : "Open media"} ↗</a>
                <p className="result-body review-caption">{item.caption || (lang === "ar" ? "بدون كابشن" : "No caption")}</p>
                {item.scheduled_at && <p className="scheduled-time"><Icon name="calendar" size={15}/>{new Date(item.scheduled_at).toLocaleString(lang === "ar" ? "ar-EG" : "en-US", { dateStyle: "medium", timeStyle: "short" })}</p>}
                {item.state === "draft" && <><div className="form-field"><label htmlFor={`time-${item.id}`}>{lang === "ar" ? "موعد النشر (توقيت جهازك)" : "Publish time (your device's local time)"}</label><input id={`time-${item.id}`} type="datetime-local" min={new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0,16)} /></div><div className="approval-buttons"><button className="primary-button" type="button" disabled={postBusy || !instagramStatus?.connected} onClick={() => void approveInstagramPost(item.id, "publish_now")}>{lang === "ar" ? "موافقة ونشر الآن" : "Approve & publish now"}</button><button className="secondary-button" type="button" disabled={postBusy || !instagramStatus?.connected} onClick={() => { const input = document.getElementById(`time-${item.id}`) as HTMLInputElement | null; if (input?.value) void approveInstagramPost(item.id, "schedule", input.value); else setPostError(lang === "ar" ? "اختر موعدًا مستقبليًا أولًا." : "Choose a future time first."); }}>{lang === "ar" ? "موافقة وجدولة" : "Approve & schedule"}</button></div></>}
                {item.state === "scheduled" && <button className="secondary-button" type="button" disabled={postBusy} onClick={() => void cancelInstagramSchedule(item.id)}>{lang === "ar" ? "إلغاء الموعد" : "Cancel schedule"}</button>}
                {item.state === "published" && <p className="result-notice">{lang === "ar" ? "تم النشر عبر Instagram API الرسمي." : "Published through the official Instagram API."}</p>}
                {item.state === "unknown" && <p className="queue-warning">{lang === "ar" ? "لا تعِد النشر قبل تحديث الحالة والتحقق منها لتجنب تكرار المنشور." : "Do not republish until you refresh and verify status, to avoid a duplicate."}</p>}
              </article>;
            })}</div>}
          </section>
          <div className="info-strip"><strong>{t.approvalsTitle}</strong><span>{lang === "ar" ? "الجدولة تُدار داخل التطبيق؛ يلزم أن يبقى الخادم المجاني يعمل في موعد النشر." : "Scheduling is app-managed; the free server must be running when a post is due."}</span></div>
        </section>}

        {view === "insights" && <section className="page-content">
          <div className="page-title-row"><div><p className="eyebrow">{t.insightsTitle}</p><h1>{t.performance}</h1><p>{t.insightsSub}</p></div><span className="status-tag">{instagramStatus?.connected ? t.connected : t.offline}</span></div>
          <div className="section-heading"><div><p className="eyebrow">{t.officialSource}</p><h2>{t.insightsTitle}</h2></div><div className="range-control" role="group" aria-label={t.performance}>{(["today", "week", "month"] as const).map((period) => <button key={period} className={range === period ? "selected" : ""} aria-pressed={range === period} onClick={() => setRange(period)}>{t[period]}</button>)}</div></div>
          <section className="metrics-grid insights-metrics"><Metric icon="grid" label={t.followers} note={instagramInsights ? insightNote("follower_count") : t.unavailable} value={instagramInsights ? insightValue("follower_count") : "—"}/><Metric icon="chart" label={t.reach} note={instagramInsights ? insightNote("reach") : t.unavailable} value={instagramInsights ? insightValue("reach") : "—"}/><Metric icon="spark" label={t.engagement} note={instagramInsights ? insightNote("total_interactions") : t.unavailable} value={instagramInsights ? insightValue("total_interactions") : "—"}/><Metric icon="chart" label={t.views} note={instagramInsights ? insightNote("views") : t.unavailable} value={instagramInsights ? insightValue("views") : "—"}/></section>
          {!instagramStatus?.connected && <div className="info-strip"><strong>{t.noConnection}</strong><span>{t.unavailable}</span></div>}
          {instagramStatus?.connected && !instagramInsights && <div className="empty-note">{t.noInsights}</div>}
          {instagramInsights && <article className="panel insights-detail"><div className="panel-heading"><div><h3>{t.reach}</h3><p>{instagramInsights.range_days} {lang === "ar" ? "يومًا" : "days"} · {t.latest}</p></div><span className="status-tag">{t.officialSource}</span></div>{(() => { const points = instagramInsights.metrics.reach?.series ?? []; const max = Math.max(1, ...points.map((point) => point.value)); return points.length ? <div className="insight-bars" role="img" aria-label={`${t.reach}: ${points.map((point) => point.value).join(", ")}`}>{points.map((point, index) => <div className="insight-bar-wrap" key={`${point.end_time ?? "point"}-${index}`} title={`${point.end_time ?? ""}: ${point.value}`}><span className="insight-bar" style={{ height: `${Math.max(4, (point.value / max) * 100)}%` }}/><small>{point.end_time ? new Date(point.end_time).toLocaleDateString(lang === "ar" ? "ar-EG" : "en-US", { day: "numeric", month: "short" }) : ""}</small></div>)}</div> : <div className="empty-note">{t.noInsights}</div>; })()}</article>}
          <div className="lower-grid"><article className="panel rank-panel"><h3>{t.topPosts}</h3><div className="rank-empty"><span className="empty-badge"><Icon name="grid"/></span><strong>{instagramStatus?.connected ? t.noInsights : t.noData}</strong></div></article><article className="panel rank-panel"><h3>{t.topReels}</h3><div className="rank-empty"><span className="empty-badge"><Icon name="chart"/></span><strong>{instagramStatus?.connected ? t.noInsights : t.noData}</strong></div></article></div>
        </section>}

        {view === "settings" && <section className="page-content">
          <div className="page-title-row"><div><p className="eyebrow">{t.stage}</p><h1>{t.settingsTitle}</h1><p>{t.settingsSub}</p></div><span className="status-tag">{instagramStatus?.connected ? t.connected : t.offline}</span></div>
          <div className="settings-card panel">
            <div className="settings-row"><span className="settings-icon"><Icon name="lock"/></span><span><strong>{t.authTitle}</strong><small>{ownerSession.configured ? t.authIntro : t.authSetup}</small></span>
              {ownerSession.authenticated ? <button className="secondary-button" onClick={logoutOwner}>{t.logout}</button> : null}</div>
            {!ownerSession.authenticated && ownerSession.configured && <form className="owner-login-form" onSubmit={loginOwner}><label htmlFor="owner-password">{t.password}</label><div className="owner-login-controls"><input id="owner-password" type="password" autoComplete="current-password" required minLength={14} value={ownerPassword} onChange={(event) => setOwnerPassword(event.target.value)} /><button className="primary-button" type="submit" disabled={loginBusy}>{loginBusy ? t.loading : t.login}</button></div>{authError && <p className="form-error" role="alert">{authError}</p>}</form>}
          </div>
          {ownerSession.authenticated && <>
            <div className="settings-card panel instagram-data-card">
              <div className="panel-heading"><div><h3>{t.accountData}</h3><p>{t.permissionNote}</p></div><button className="secondary-button" onClick={() => void refreshInstagram()} disabled={instagramBusy}>{instagramBusy ? t.loading : t.refresh}</button></div>
              {instagramStatus?.status === "not_configured" && <div className="empty-note">{t.setupPending}</div>}
              {instagramStatus?.status === "not_connected" && <div className="instagram-connect-row"><span>{t.notSet}</span><button className="primary-button" onClick={() => window.location.assign(`${apiBase}/api/instagram/connect`)}>{t.connectOfficial}</button></div>}
              {instagramStatus?.connected && instagramAccount && <div className="instagram-profile-grid"><div><small>{t.accountName}</small><strong>@{instagramAccount.username}</strong></div><div><small>{t.accountType}</small><strong>{instagramAccount.account_type || "—"}</strong></div><div><small>{t.mediaCount}</small><strong>{typeof instagramAccount.media_count === "number" ? instagramAccount.media_count : "—"}</strong></div></div>}
              {oauthNotice && <p className="result-notice" role="status">{oauthNotice}</p>}
              {instagramError && <p className="form-error" role="alert">{instagramError}</p>}
              {instagramStatus?.connected && <div className="instagram-media-list"><h4>{t.recentMedia}</h4>{instagramMedia.length === 0 ? <p className="empty-note">{t.noMedia}</p> : instagramMedia.map((item) => <article className="instagram-media-item" key={item.id}><div><strong>{item.media_product_type || item.media_type || "Instagram"}</strong><small>{item.timestamp ? new Date(item.timestamp).toLocaleString(lang === "ar" ? "ar-EG" : "en-US") : ""}</small><p>{item.caption || ""}</p></div>{item.permalink && <a href={item.permalink} target="_blank" rel="noreferrer">{item.media_product_type === "REELS" ? "Reel" : "Instagram"} ↗</a>}</article>)}</div>}
            </div>
          </>}
          <div className="settings-card panel"><div className="settings-row"><span className="settings-icon"><Icon name="spark"/></span><span><strong>{t.accountType}</strong><small>{t.permissions}</small></span><span className="setting-value">{t.creator}</span></div><div className="settings-row"><span className="settings-icon"><Icon name="lock"/></span><span><strong>{t.automation}</strong><small>{t.stopNote}</small></span><span className="setting-value">{t.manual}</span></div></div>
          <div className="info-strip"><strong>{t.security}</strong><span>{t.securityText}</span></div>
        </section>}
      </section>

      <nav className="mobile-nav" aria-label={t.mobileNav}>{menu.slice(0, 4).map((item) => <button key={item.id} className={view === item.id ? "active" : ""} onClick={() => changeView(item.id)} aria-current={view === item.id ? "page" : undefined}><Icon name={item.icon} size={19}/><span>{t[item.key]}</span></button>)}</nav>
    </main>
  );
}
