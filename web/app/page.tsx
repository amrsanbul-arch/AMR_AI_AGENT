"use client";

import { useEffect, useState, type FormEvent } from "react";

type Lang = "ar" | "en";
type View = "overview" | "studio" | "calendar" | "insights" | "settings";

type Copy = {
  [key: string]: string;
};
type ContentMode = "ideas" | "caption" | "reel_script";
type ContentPiece = { title: string; hook: string; body: string; cta: string; hashtags: string[]; scenes: string[] };
type ContentResult = { mode: ContentMode; language: "ar" | "en"; generator: "free_template"; notice: string; pieces: ContentPiece[] };

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
    settingsTitle: "إعدادات الحساب", settingsSub: "إعداد الاتصال واللغة وطريقة الموافقة.", connection: "اتصال Instagram", officialOnly: "تكامل رسمي فقط", accountType: "نوع الحساب", creator: "Creator · منشئ محتوى", permissions: "الصلاحيات", notSet: "لم يتم الربط بعد",
    manual: "يدوي", approvalMode: "موافقة قبل النشر", automation: "أتمتة النشر", stop: "إيقاف الأتمتة", stopNote: "متوقف حتى يتم إعداد الربط الرسمي.",
    mobileNav: "التنقل", coming: "قيد التجهيز", stage: "المرحلة 2 · لوحة التحكم", zeroData: "لا بيانات تجريبية", zeroDataSub: "كل الأرقام تبقى فارغة حتى نقرأها من مصدر حقيقي.",
    today: "اليوم", week: "هذا الأسبوع", month: "هذا الشهر", updated: "آخر تحديث", none: "—", apiStatus: "حالة الربط", noConnection: "لا يوجد اتصال بإنستجرام", onlyOfficial: "لن نستخدم تسجيل دخول أو كشطًا غير رسميًا.",
    startContent: "ابدأ بتجهيز محتواك", startContentSub: "ستتمكن من بناء أفكار وسكربتات ومراجعتها قبل النشر.", security: "الأمان أولًا", securityText: "لا كلمات مرور محفوظة · صلاحيات رسمية · موافقة قبل النشر", daily: "نظرة يومية", contentReady: "ما يحتاج انتباهك", noPending: "لا توجد عناصر للمراجعة بعد", buildNext: "استوديو المحتوى المحلي المجاني جاهز للمسودات؛ لا يوجد نشر أو ربط Instagram بعد.",
    studioTitle: "مساعد المحتوى المجاني", studioIntro: "اكتب موضوعك واختر نوع المسودة. النتائج محلية قابلة للتعديل، ولا تُنشر تلقائيًا.",
    topicLabel: "موضوع المحتوى", topicPlaceholder: "مثال: تصوير الطعام للمطاعم", audienceLabel: "الجمهور (اختياري)", audiencePlaceholder: "مثال: أصحاب المطاعم الصغيرة",
    modeLabel: "نوع المحتوى", ideasMode: "أفكار", captionMode: "كابشن", reelMode: "سكريبت Reel", toneLabel: "النبرة", friendlyTone: "ودودة", professionalTone: "احترافية", playfulTone: "مرحة", educationalTone: "تعليمية",
    generate: "جهّز مسودة", generating: "بجهّز…", generated: "المسودات المقترحة", hookLabel: "الافتتاحية", bodyLabel: "النص", ctaLabel: "دعوة للتفاعل", hashtagsLabel: "هاشتاجات مقترحة", scenesLabel: "تقسيم المشاهد", generatorError: "تعذر الاتصال بخادم المساعد. شغّل API محليًا وحاول تاني.", generatorLocal: "محلي مجاني",

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
    settingsTitle: "Account settings", settingsSub: "Connection, language, and approval preferences.", connection: "Instagram connection", officialOnly: "Official integration only", accountType: "Account type", creator: "Creator", permissions: "Permissions", notSet: "Not connected",
    manual: "Manual", approvalMode: "Approval before publishing", automation: "Publishing automation", stop: "Stop automation", stopNote: "Inactive until official connection is configured.",
    mobileNav: "Navigation", coming: "Coming soon", stage: "Stage 2 · Dashboard", zeroData: "No sample data", zeroDataSub: "Metrics stay empty until read from a real source.",
    today: "Today", week: "This week", month: "This month", updated: "Last updated", none: "—", apiStatus: "Connection status", noConnection: "No Instagram connection", onlyOfficial: "No unofficial login or scraping will be used.",
    startContent: "Start preparing content", startContentSub: "Build ideas and scripts, then review them before publishing.", security: "Security first", securityText: "No saved passwords · Official permissions · Review before publishing", daily: "Daily overview", contentReady: "Needs your attention", noPending: "Nothing to review yet", buildNext: "The free local content studio is ready for drafts; Instagram is not connected and nothing publishes.",
    studioTitle: "Free content assistant", studioIntro: "Add a topic and choose a draft type. Results are local and editable; nothing is published.",
    topicLabel: "Content topic", topicPlaceholder: "e.g. food photography for restaurants", audienceLabel: "Audience (optional)", audiencePlaceholder: "e.g. small restaurant owners",
    modeLabel: "Content type", ideasMode: "Ideas", captionMode: "Caption", reelMode: "Reel script", toneLabel: "Tone", friendlyTone: "Friendly", professionalTone: "Professional", playfulTone: "Playful", educationalTone: "Educational",
    generate: "Generate draft", generating: "Working…", generated: "Suggested drafts", hookLabel: "Hook", bodyLabel: "Copy", ctaLabel: "Call to action", hashtagsLabel: "Suggested hashtags", scenesLabel: "Scene outline", generatorError: "Could not reach the assistant API. Start it locally and try again.", generatorLocal: "FREE · LOCAL",

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

function Metric({ icon, label, note }: { icon: string; label: string; note: string }) {
  return <article className="metric-card"><span className="metric-icon"><Icon name={icon} /></span><span className="metric-label">{label}</span><strong className="metric-value">—</strong><span className="metric-note">{note}</span></article>;
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
  const [generating, setGenerating] = useState(false);
  const t = words[lang];
  const rtl = lang === "ar";

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = rtl ? "rtl" : "ltr";
  }, [lang, rtl]);

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

  function changeView(next: View) {
    setView(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

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
            <span className="connection-pill"><i />{t.offline}</span>
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
                <button className="primary-button" disabled title={t.next}><span>{t.connect}</span><Icon name="arrow" size={17}/></button>
                <span className="button-note">{t.next}</span>
              </div>
            </div>
            <div className="hero-side">
              <div className="account-orbit"><span className="orbit-ring"/><span className="orbit-core">A</span><span className="orbit-star star-a"/><span className="orbit-star star-b"/></div>
              <div className="account-chip"><span className="account-avatar">A</span><span><strong>{t.account}</strong><small>Instagram · Creator</small></span><i /></div>
            </div>
          </section>

          <div className="section-heading"><div><p className="eyebrow">{t.daily}</p><h2>{t.overviewTitle}</h2></div><div className="range-control" role="group" aria-label={t.overviewTitle}>{(["today", "week", "month"] as const).map((period) => <button key={period} className={range === period ? "selected" : ""} aria-pressed={range === period} onClick={() => setRange(period)}>{t[period]}</button>)}</div></div>
          <section className="metrics-grid" aria-label={t.overviewTitle}>
            <Metric icon="grid" label={t.followers} note={t.unavailable}/><Metric icon="chart" label={t.reach} note={t.unavailable}/><Metric icon="spark" label={t.engagement} note={t.unavailable}/><Metric icon="chart" label={t.views} note={t.unavailable}/>
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
          <div className="studio-workspace panel">
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
          </div>
          {contentResult && <section className="generated-results" aria-live="polite"><div className="results-heading"><h2>{t.generated}</h2><span className="status-tag">{contentResult.generator === "free_template" ? t.generatorLocal : ""}</span></div><p className="result-notice">{contentResult.notice}</p><div className="result-grid">{contentResult.pieces.map((piece, index) => <article className="result-card panel" key={`${piece.title}-${index}`}><p className="eyebrow">{contentResult.mode === "ideas" ? `${t.ideasMode} ${index + 1}` : t.generated}</p><h3>{piece.title}</h3><div className="result-block"><strong>{t.hookLabel}</strong><p>{piece.hook}</p></div><div className="result-block"><strong>{t.bodyLabel}</strong><p className="result-body">{piece.body}</p></div>{piece.scenes.length > 0 && <div className="result-block"><strong>{t.scenesLabel}</strong><ol>{piece.scenes.map((scene) => <li key={scene}>{scene}</li>)}</ol></div>}<div className="result-block"><strong>{t.ctaLabel}</strong><p>{piece.cta}</p></div><div className="result-block"><strong>{t.hashtagsLabel}</strong><p className="hashtags">{piece.hashtags.join(" ")}</p></div></article>)}</div></section>}
          <div className="info-strip"><strong>{t.approvalsTitle}</strong><span>{t.approvalsSub}</span></div>
        </section>}

        {view === "calendar" && <section className="page-content">
          <div className="page-title-row"><div><p className="eyebrow">{t.stage}</p><h1>{t.scheduleTitle}</h1><p>{t.scheduleSub}</p></div><span className="status-tag">{t.coming}</span></div>
          <div className="calendar-empty panel"><div className="calendar-head"><strong>{t.month}</strong><span>{t.updated} · {t.none}</span></div><div className="calendar-placeholder">{[...Array(35)].map((_, i) => <span key={i} className="calendar-day">{i > 1 && i < 32 ? i - 1 : ""}</span>)}</div><div className="empty-note"><Icon name="lock" size={16}/>{t.noData}</div></div>
          <div className="info-strip"><strong>{t.approvalsTitle}</strong><span>{t.approvalsSub}</span></div>
        </section>}

        {view === "insights" && <section className="page-content">
          <div className="page-title-row"><div><p className="eyebrow">{t.stage}</p><h1>{t.performance}</h1><p>{t.performanceSub}</p></div><span className="status-tag">{t.offline}</span></div>
          <section className="metrics-grid insights-metrics"><Metric icon="grid" label={t.followers} note={t.unavailable}/><Metric icon="chart" label={t.reach} note={t.unavailable}/><Metric icon="spark" label={t.engagement} note={t.unavailable}/><Metric icon="chart" label={t.views} note={t.unavailable}/></section>
          <div className="lower-grid"><article className="panel rank-panel"><h3>{t.topPosts}</h3><div className="rank-empty"><span className="empty-badge"><Icon name="grid"/></span><strong>{t.noData}</strong></div></article><article className="panel rank-panel"><h3>{t.topReels}</h3><div className="rank-empty"><span className="empty-badge"><Icon name="chart"/></span><strong>{t.noData}</strong></div></article></div>
        </section>}

        {view === "settings" && <section className="page-content">
          <div className="page-title-row"><div><p className="eyebrow">{t.stage}</p><h1>{t.settingsTitle}</h1><p>{t.settingsSub}</p></div><span className="status-tag">{t.offline}</span></div>
          <div className="settings-card panel"><div className="settings-row"><span className="settings-icon"><Icon name="grid"/></span><span><strong>{t.connection}</strong><small>{t.onlyOfficial}</small></span><span className="setting-value">{t.notSet}</span></div><div className="settings-row"><span className="settings-icon"><Icon name="spark"/></span><span><strong>{t.accountType}</strong><small>{t.permissions}</small></span><span className="setting-value">{t.creator}</span></div><div className="settings-row"><span className="settings-icon"><Icon name="lock"/></span><span><strong>{t.automation}</strong><small>{t.stopNote}</small></span><span className="setting-value">{t.manual}</span></div></div>
          <div className="info-strip"><strong>{t.security}</strong><span>{t.securityText}</span></div>
        </section>}
      </section>

      <nav className="mobile-nav" aria-label={t.mobileNav}>{menu.slice(0, 4).map((item) => <button key={item.id} className={view === item.id ? "active" : ""} onClick={() => changeView(item.id)} aria-current={view === item.id ? "page" : undefined}><Icon name={item.icon} size={19}/><span>{t[item.key]}</span></button>)}</nav>
    </main>
  );
}
