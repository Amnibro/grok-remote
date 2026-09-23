/* Grok Remote shell worker. Network-first so live UI deploys win.
   Registers only on https / localhost (secure context). */
const CACHE = "grok-remote-pwa-v2";
const SHELL = "/__shell__";
self.addEventListener("install", (e) => {
  self.skipWaiting();
});
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});
function isLive(p) {
  return p === "/ws" || p.startsWith("/ws/") || p.startsWith("/api/") || p === "/health" || p.startsWith("/health/") || p === "/config.json" || p === "/config";
}
const OFFLINE_HTML = "<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>" +
  "<title>Grok Remote · offline</title><body style='font:15px system-ui;background:#0a0b0e;color:#e4e4e7;padding:24px'>" +
  "<h3>Grok Remote is offline</h3><p>This device cannot reach the PC right now. Check Wi-Fi / the tunnel, then " +
  "<a href='' style='color:#9ad' onclick='location.reload();return false'>retry</a>.</p></body>";
self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  let u;
  try {
    u = new URL(req.url);
  } catch (err) {
    return;
  }
  if (u.origin !== self.location.origin) return;
  const p = u.pathname;
  if (isLive(p)) return;
  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req)
        .then((res) => {
          if (res && res.ok && (p === "/" || p === "/index.html")) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(SHELL, copy)).catch(() => {});
          }
          return res;
        })
        .catch(() =>
          caches.match(SHELL).then((hit) => hit || new Response(OFFLINE_HTML, { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } }))
        )
    );
    return;
  }
  e.respondWith(
    fetch(req)
      .then((res) => {
        if (res && res.ok && p.startsWith("/static/")) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        }
        return res;
      })
      .catch(() => caches.match(req))
  );
});
