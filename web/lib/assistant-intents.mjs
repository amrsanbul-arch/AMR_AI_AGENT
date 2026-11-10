const patterns = [
  ["calendar", /\b(calendar|schedule|scheduled posts|publishing queue)\b|التقويم|تقويم النشر|جدولة|الجدول|مواعيد النشر|المنشورات المجدولة/i],
  ["strategy", /\b(strategy report|content strategy|report)\b|تقرير|استراتيجية|خطّة المحتوى|خطة المحتوى/i],
  ["profile", /\b(profile audit|profile review|bio review|review my bio)\b|راجع(?:ي)?\s+(?:الـ)?(?:ملف|البايو)|مراجعة\s+(?:الملف|البايو)|حلل(?:ي)?\s+(?:الـ)?(?:بايو|bio)|تحسين\s+(?:البايو|الملف)/i],
  ["analytics", /\b(analytics|insights|performance|analyze my account|analy[sz]e (?:my )?(?:last )?\d+ reels?|account analysis)\b|تحليلات|حلل(?:ي)?\s+(?:حسابي|الحساب)|تحليل\s+(?:حسابي|الحساب)|حلل(?:ي)?\s+(?:آخر|اخر)\s+\d+\s+(?:Reels|ريلز)|تحليل\s+(?:آخر|اخر)\s+\d+\s+ريلز|أداء\s+(?:الحساب|المحتوى)/i],
  ["trends", /\b(trend research|trends|trending topics)\b|الترندات|ترند|موضوعات رائجة|مواضيع رائجة/i],
  ["reel", /\b(reel script|reels|reel)\b|سكريبت\s*(?:ريل|رييل)|ريلز|رييلز|ريل(?:ز)?/i],
  ["caption", /\b(caption|captions)\b|كابشنات|كابشن/i],
  ["ideas", /\b(content ideas|post ideas|ideas)\b|أفكار(?:\s+محتوى)?|افكار(?:\s+محتوى)?/i],
];

const filler = /^(?:please\s+)?(?:can you\s+|could you\s+|make\s+me\s+|create\s+|write\s+|show\s+me\s+|give\s+me\s+|for\s+me\s+|about\s+|on\s+|for\s+|around\s+|ممكن\s+|لو\s+سمحت\s+|اعمل(?:ي)?\s*(?:لي)?\s*|جهز(?:ي)?\s*(?:لي)?\s*|اكتب(?:ي)?\s*(?:لي)?\s*|وريني\s*|اعرض(?:ي)?\s*|عن\s+|حول\s+|حوالي\s+|للـ?\s*)/i;

function cleanTopic(value) {
  let text = value.trim().replace(/^[\s:،,؛;.!؟?\-–—]+|[\s،,؛;.!؟?\-–—]+$/g, "");
  // Drop command words/connectors only at the start; keep the actual user-supplied subject intact.
  for (let i = 0; i < 4; i++) {
    const next = text.replace(filler, "").trim();
    if (next === text) break;
    text = next;
  }
  text = text.replace(/\s+/g, " ").trim();
  if (!text || /^(?:me|my account|حسابي|الحساب|محتوى|content|posts?|منشورات|المحتوى)$/i.test(text)) return null;
  return text.length >= 2 ? text : null;
}

export function parseAssistantCommand(input) {
  const text = input.trim();
  if (!text) return null;
  for (const [intent, pattern] of patterns) {
    const match = pattern.exec(text);
    if (!match) continue;
    const tail = text.slice(match.index + match[0].length);
    const about = tail.match(/^\s*(?:about\s+|on\s+|for\s+|around\s+|عن\s+|حول\s+|بخصوص\s+|للـ?\s*)/i);
    const candidate = about ? tail.slice(about[0].length) : tail;
    const topic = cleanTopic(candidate);
    return { intent, topic };
  }
  return null;
}
