import test from "node:test";
import assert from "node:assert/strict";
import { parseAssistantCommand } from "./assistant-intents.mjs";

test("recognizes bilingual content intents and extracts supplied topics", () => {
  assert.deepEqual(parseAssistantCommand("اعمل لي أفكار محتوى عن القهوة"), { intent: "ideas", topic: "القهوة" });
  assert.deepEqual(parseAssistantCommand("write a caption about skincare"), { intent: "caption", topic: "skincare" });
  assert.deepEqual(parseAssistantCommand("جهز سكريبت Reel عن تنظيم الوقت"), { intent: "reel", topic: "تنظيم الوقت" });
  assert.deepEqual(parseAssistantCommand("Reel script for study tips"), { intent: "reel", topic: "study tips" });
});

test("recognizes bounded read-only analysis and navigation commands", () => {
  assert.equal(parseAssistantCommand("حلل حسابي")?.intent, "analytics");
  assert.equal(parseAssistantCommand("show my performance")?.intent, "analytics");
  assert.equal(parseAssistantCommand("analyze my last 10 Reels")?.intent, "analytics");
  assert.equal(parseAssistantCommand("حلل آخر 10 Reels")?.intent, "analytics");
  assert.equal(parseAssistantCommand("راجع البايو")?.intent, "profile");
  assert.equal(parseAssistantCommand("trend research about coffee")?.intent, "trends");
  assert.equal(parseAssistantCommand("اعرض تقويم النشر")?.intent, "calendar");
  assert.equal(parseAssistantCommand("content strategy report about coffee")?.intent, "strategy");
});

test("leaves missing topics for an explicit follow-up and rejects unsupported requests", () => {
  assert.deepEqual(parseAssistantCommand("اعمل أفكار محتوى"), { intent: "ideas", topic: null });
  assert.deepEqual(parseAssistantCommand("write a caption"), { intent: "caption", topic: null });
  assert.equal(parseAssistantCommand("publish this now"), null);
  assert.equal(parseAssistantCommand("hello"), null);
});

test("does not guess a content subject from generic words", () => {
  assert.equal(parseAssistantCommand("ideas about content")?.topic, null);
  assert.equal(parseAssistantCommand("أفكار عن المحتوى")?.topic, null);
});
