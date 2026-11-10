export default function Home() {
  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand-mark">A</div>
        <div>
          <p className="eyebrow">AMR AI</p>
          <h1>مدير Instagram الشخصي</h1>
        </div>
        <span className="status"><i /> غير متصل</span>
      </header>
      <section className="welcome">
        <p className="eyebrow">المرحلة الأولى · الهيكل الأساسي</p>
        <h2>مساحة عملك تبدأ من هنا.</h2>
        <p>اللوحة قيد البناء. لا يوجد اتصال بحساب Instagram ولا تُعرض بيانات تجريبية كأنها حقيقية.</p>
        <div className="actions"><button disabled>ربط Instagram الرسمي · لاحقًا</button><span>لا تشارك كلمة مرورك أو رموز التحقق.</span></div>
      </section>
      <section className="grid" aria-label="مكونات قادمة">
        <article><span className="number">01</span><h3>نظرة عامة</h3><p>إحصاءات حقيقية بعد ربط API رسمي.</p></article>
        <article><span className="number">02</span><h3>استوديو المحتوى</h3><p>أفكار وكتابة وسيناريوهات بمساعدة AI.</p></article>
        <article><span className="number">03</span><h3>التقويم والنشر</h3><p>جدولة وموافقات ضمن صلاحيات Meta.</p></article>
      </section>
      <footer>واجهة تأسيسية · البيانات الحقيقية ستظهر بعد بناء التكامل الرسمي.</footer>
    </main>
  );
}
