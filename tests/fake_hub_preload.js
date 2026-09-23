() => {
  if (location.protocol !== "http:") return;
  let seed = {};
  try { seed = JSON.parse(localStorage.getItem("__fakehub_seed") || "{}") || {}; } catch (e) {}
  const now = Date.now();
  const H = window.__H = {
    seed,
    cfg: Object.assign({ cwd: "/home/u/proj", fsRoot: "/home/u/proj", ws_url: "" }, seed.cfg || {}),
    rows: seed.rows || [
      { sessionId: "11111111-aaaa-7aaa-8aaa-000000000001", title: "First chat", agentTitle: "First chat", titleIsManual: false, archived: false, cwd: "/home/u/proj", updatedAt: now - 60000 },
      { sessionId: "22222222-bbbb-7bbb-8bbb-000000000002", title: "Second chat", agentTitle: "Second chat", titleIsManual: false, archived: false, cwd: "/home/u/proj", updatedAt: now - 3600000 }
    ],
    live: seed.live || [],
    meta: seed.meta !== false,
    history: seed.history || {},
    sent: [], fetchLog: [], sockets: [],
    newCount: 0, grReq: {}, promptIds: {},
    promptMode: seed.promptMode || "hold",
    deadPing: false, newDelay: seed.newDelay || 40, wsNewFails: !!seed.wsNewFails,
    closeOnOpen: seed.closeOnOpen || 0
  };
  H.cur = () => { for (let i = H.sockets.length - 1; i >= 0; i--) if (H.sockets[i].readyState === 1) return H.sockets[i]; return null; };
  H.push = obj => { const s = H.cur(); if (s) s._deliver(obj); return !!s; };
  H.row = id => H.rows.find(r => r.sessionId === id);
  H.prompts = () => H.sent.filter(m => m.method === "session/prompt");
  H.news = () => H.sent.filter(m => m.method === "session/new");
  function newSession(params) {
    const k = params && params._grReq;
    if (k && H.grReq[k]) return H.grReq[k];
    H.newCount++;
    const sid = "99999999-new" + H.newCount + "-7ccc-8ccc-00000000000" + H.newCount;
    const res = { sessionId: sid };
    H.rows.unshift({ sessionId: sid, title: "", agentTitle: "", titleIsManual: false, archived: false, cwd: params.cwd, updatedAt: Date.now(), pending: true });
    if (k) H.grReq[k] = res;
    return res;
  }
  H.newSession = newSession;
  const J = (status, obj) => new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json" } });
  window.fetch = async (url, opts) => {
    opts = opts || {};
    const u = new URL(String(url), location.origin);
    const p = u.pathname, method = (opts.method || "GET").toUpperCase();
    let body = null;
    try { if (typeof opts.body === "string") body = JSON.parse(opts.body); } catch (e) {}
    H.fetchLog.push({ method, path: p, query: u.search, body });
    if (H.fetchHook) { const r = await H.fetchHook(method, p, body, u); if (r) return r; }
    if (p === "/config.json") return J(200, H.cfg);
    if (p === "/health") return J(200, { ok: true, ready: true });
    if (p === "/api/sessions") {
      const rows = H.rows.map(r => {
        const o = Object.assign({}, r);
        if (!H.meta) { delete o.archived; delete o.titleIsManual; delete o.agentTitle; }
        return o;
      });
      const out = { ok: true, sessions: rows };
      if (H.meta) out.total = rows.length;
      return J(200, out);
    }
    if (p === "/api/session/archived" && method === "GET") return J(200, { ok: true, ids: H.rows.filter(r => r.archived).map(r => r.sessionId) });
    if (p === "/api/session/archived" && method === "POST") {
      if (H.archiveFail) return J(500, { ok: false, error: "disk full" });
      if (Array.isArray(body && body.ids)) { body.ids.forEach(id => { const r = H.row(id); if (r) r.archived = true; }); return J(200, { ok: true }); }
      const r = H.row(body && (body.sessionId || body.id));
      if (r) r.archived = !!body.archived;
      return J(200, { ok: true });
    }
    if (p === "/api/session/rename") {
      const r = H.row(body.sessionId);
      if (r) { const t = String(body.title || "").trim(); r.title = t || r.agentTitle; r.titleIsManual = !!t; }
      return J(200, { ok: true, title: r ? r.title : body.title });
    }
    if (p === "/api/session/titles") return J(200, { ok: true, titles: {} });
    if (p === "/api/session/history") {
      const sidq = u.searchParams.get("sessionId");
      const live = u.searchParams.get("live") === "1";
      const h = H.history[sidq];
      if (live) {
        const since = +u.searchParams.get("since") || 0;
        const q = (H.liveEvents && H.liveEvents[sidq]) || [];
        const evs = q.filter(e => e._off >= since);
        const end = q.length ? Math.max(since, q[q.length - 1]._off + 1) : since;
        return J(200, { ok: true, sessionId: sidq, events: evs, meta: { live: true, size: end, end, has_more: false } });
      }
      if (!h) return J(200, { ok: false, error: "session dir not found" });
      return J(200, { ok: true, sessionId: sidq, events: h, title: "", meta: { size: 100, end: 100, has_more: false } });
    }
    if (p === "/api/work") return J(200, { ok: true, jobs: H.jobs || [] });
    if (p === "/api/att") return J(200, { ok: true, items: [] });
    if (p === "/api/session/new") return J(200, Object.assign({ ok: true }, newSession(body || {})));
    if (p === "/api/session/prompt") {
      if (body && body._grPromptId && H.promptIds[body._grPromptId]) return J(200, { ok: true, duplicate: true });
      if (body && body._grPromptId) H.promptIds[body._grPromptId] = 1;
      if (H.httpPromptMode === "running") return J(200, { ok: true, running: true, id: body.requestId, sessionId: body.sessionId, promptId: body._grPromptId });
      if (H.httpPromptMode === "error") return J(502, { ok: false, error: "agent rejected" });
      return J(200, { ok: true, done: true, stopReason: "end_turn" });
    }
    return J(200, { ok: true });
  };
  class FakeWS {
    constructor(url) {
      this.url = url; this.readyState = 0; this.sent = [];
      H.sockets.push(this);
      setTimeout(() => {
        if (this.readyState !== 0) return;
        this.readyState = 1;
        this.onopen && this.onopen({});
        if (H.closeOnOpen) setTimeout(() => this.serverClose(H.closeOnOpen, H.closeReason || ""), 30);
      }, 15);
    }
    send(s) {
      if (this.readyState !== 1) throw new Error("not open");
      const m = JSON.parse(s);
      this.sent.push(m); H.sent.push(m);
      if (H.onSend && H.onSend(m, this) === false) return;
      this._hub(m);
    }
    _reply(id, result, delay) { setTimeout(() => { if (this.readyState === 1) this._deliver({ jsonrpc: "2.0", id, result }); }, delay || 5); }
    _error(id, message, delay) { setTimeout(() => { if (this.readyState === 1) this._deliver({ jsonrpc: "2.0", id, error: { code: -32000, message } }); }, delay || 5); }
    _hub(m) {
      const p = m.params || {};
      switch (m.method) {
        case "initialize": return this._reply(m.id, { protocolVersion: 1 });
        case "_x.ai/sessions/list": return this._reply(m.id, { sessions: H.live });
        case "session/load": return this._reply(m.id, {}, 20);
        case "session/new":
          if (H.wsNewFails) return this._error(m.id, "timeout: session/new", 30);
          return this._reply(m.id, newSession(p), H.newDelay);
        case "session/prompt": {
          const pid = p._grPromptId;
          if (pid && H.promptIds[pid]) return this._reply(m.id, { stopReason: "duplicate", duplicateOf: pid }, 10);
          if (pid) H.promptIds[pid] = 1;
          const done = ok => setTimeout(() => { if (this.readyState === 1) this._deliver({ jsonrpc: "2.0", method: "_x.ai/remote/rpc_done", params: { id: m.id, ok, detached: false, sessionId: p.sessionId, cid: this.cid || "", method: "session/prompt", promptId: pid } }); }, 45);
          if (H.promptMode === "error") { this._error(m.id, "Prompt is too long: 210000 tokens > 200000 maximum", 30); return done(false); }
          if (H.promptMode === "ok") { this._reply(m.id, { stopReason: "end_turn" }, 30); return done(true); }
          return;
        }
        case "_x.ai/remote/ping":
          if (H.deadPing) return;
          return setTimeout(() => this._deliver({ jsonrpc: "2.0", method: "_x.ai/remote/pong", params: { t: p.t, hub_up: true } }), 5);
        case "_x.ai/remote/hello": this.cid = p.cid; return;
        default: if (m.id != null) this._reply(m.id, {});
      }
    }
    _deliver(obj) { this.onmessage && this.onmessage({ data: JSON.stringify(obj) }); }
    close(code, reason) {
      if (this.readyState === 3) return;
      this.readyState = 3;
      setTimeout(() => this.onclose && this.onclose({ code: code || 1000, reason: reason || "" }), 0);
    }
    serverClose(code, reason) {
      if (this.readyState === 3) return;
      this.readyState = 3;
      this.onclose && this.onclose({ code: code || 1006, reason: reason || "" });
    }
  }
  FakeWS.CONNECTING = 0; FakeWS.OPEN = 1; FakeWS.CLOSING = 2; FakeWS.CLOSED = 3;
  window.WebSocket = FakeWS;
  try { if (navigator.serviceWorker) navigator.serviceWorker.register = () => Promise.resolve({}); } catch (e) {}
  try { localStorage.setItem("grok_remote_tour_done", "1"); } catch (e) {}
}
