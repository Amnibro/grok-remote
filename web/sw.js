/* Grok Remote shell worker. Network-first so live UI deploys win.
   Registers only on https / localhost (secure context). */
const CACHE = "grok-remote-pwa-v1";
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
  if (p === "/ws" || p.startsWith("/api/") || p === "/health" || p === "/health/deep" || p === "/config.json" || p === "/config") return;
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
