// ZanWatch service worker: оболочка приложения из кэша, API — сначала сеть, при отсутствии связи — кэш (U10)
const SHELL = "zw-shell-v1";
const DATA = "zw-data-v1";
const SHELL_FILES = ["/", "/static/manifest.webmanifest", "/static/icon.svg"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(SHELL_FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== SHELL && k !== DATA).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

async function networkFirst(req, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const res = await fetch(req);
    if (res.ok) cache.put(req, res.clone());
    return res;
  } catch (err) {
    const hit = await cache.match(req);
    if (hit) return hit;
    throw err;
  }
}

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.startsWith("/api/")) {
    e.respondWith(networkFirst(e.request, DATA));
  } else if (e.request.mode === "navigate") {
    e.respondWith(networkFirst(new Request("/"), SHELL));
  } else {
    e.respondWith(networkFirst(e.request, SHELL));
  }
});
