import { createRequire } from "node:module";
import assert from "node:assert/strict";
import fs from "node:fs";
const require = createRequire(import.meta.url);
const { createChatRuntime } = require("../web/chat-runtime.js");
const runtimeSrc = fs.readFileSync(new URL("../web/chat-runtime.js", import.meta.url), "utf8");

const chat = createChatRuntime();
chat.open("sess-aaaa-1111", 1);
assert.equal(chat.state.openSid, "sess-aaaa-1111");
assert.equal(chat.room("sess-aaaa-1111").attach, "loading");
assert.equal(chat.belongs("sess-aaaa-1111"), true);
assert.equal(chat.belongs("sess-bbbb-2222"), false);
assert.equal(chat.belongs("sess-aaaa"), false, "C4: no prefix matching, the hub sends full ids");
assert.equal(chat.belongs("sess-aaaX"), false, "no match without hyphen boundary");
assert.equal(chat.belongs(" sess-aaaa-1111 "), true, "whitespace is not identity");
assert.equal(chat.accept("sess-aaaa-1111", { history: true }), true);
assert.equal(chat.accept("sess-aaaa-1111", { replay: true }), true, "replay is caller-gated like Aug 1");
assert.equal(chat.accept("sess-aaaa-1111", { switching: true }), true, "switching is caller-gated like Aug 1");
assert.equal(chat.accept("sess-bbbb-2222", {}), false);
assert.equal(chat.accept("", { history: true }), true);
assert.equal(chat.accept("", {}), false);
assert.equal(chat.idsMatch("sess-aaaa-1111","sess-aaaa"), false, "strict ids (C4)");
assert.equal(chat.idsMatch("sess-aaaa-1111","sess-aaaa-1111"), true);
assert.equal(chat.idsMatch("",""), false);

chat.warming("sess-aaaa-1111");
assert.equal(chat.room("sess-aaaa-1111").attach, "warming");
chat.ready("sess-aaaa-1111");
assert.equal(chat.room("sess-aaaa-1111").attach, "ready");
assert.equal(chat.accept("sess-aaaa-1111", {}), true);
assert.notEqual(chat.room("sess-aaaa"), chat.room("sess-aaaa-1111"), "a prefix is a different room (C4)");

const tools = chat.noteTool("sess-aaaa-1111", "t1", "in_progress");
assert.equal(tools.has("t1"), true);
chat.noteTool("sess-aaaa-1111", "t1", "completed");
assert.equal(chat.room("sess-aaaa-1111").pendingTools.has("t1"), false);
chat.noteTool("sess-bbbb-2222", "t2", "running");
assert.equal(chat.room("sess-aaaa-1111").pendingTools.has("t2"), false, "other session tools stay in their room");
assert.equal(chat.room("sess-bbbb-2222").pendingTools.has("t2"), true);

chat.setJobs([
  { sid: "sess-aaaa-1111", running: 1, phase: "responding", title: "this chat" },
  { sid: "sess-aaaa", running: 1, phase: "tools", title: "a different (short) id is another chat" },
  { sid: "sess-bbbb-2222", running: 1, phase: "tools", title: "other", last_user: "do work" },
  { sid: "sess-cccc-3333", running: 0, tools: [{ status: "completed" }] },
  { sid: "sess-dddd-4444", running: 0, phase: "stalled", detail: "agent accepted the prompt and returned nothing" }
]);
const extra = chat.extraJobs();
assert.deepEqual(extra.map(j => j.sid), ["sess-aaaa", "sess-bbbb-2222"], "strict: the prefix job is not this chat");
assert.equal(chat.jobLive({ running: 0, phase: "stalled" }), false);
assert.equal(runtimeSrc.includes('st+" · "+title'), false);
assert.equal(runtimeSrc.includes("agent-home-act"), true);
assert.equal(typeof chat.placeBatch, "function");
assert.equal(typeof chat.setHomeTitle, "function");

chat.saveCursors({ curAgent: { id: "bubble-a" }, userWireBuf: "hi" }, "sess-aaaa-1111");
chat.open("sess-bbbb-2222", 2);
assert.equal(chat.cursors("sess-aaaa-1111").curAgent.id, "bubble-a");
assert.equal(chat.cursors("sess-bbbb-2222").curAgent, null, "new room starts with empty cursors");
assert.equal(chat.belongs("sess-aaaa-1111"), false);
assert.equal(chat.accept("sess-aaaa-1111", {}), false);

console.log("ok");
