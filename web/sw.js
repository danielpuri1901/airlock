// Airlock service worker — cache the app shell + libs so the guard runs offline
// (airplane mode) after the first load. The 67MB model is cached separately by
// transformers.js in its own Cache storage, so it's not listed here.
const CACHE = "airlock-v1";
const ASSETS = [
  "guard.html",
  "airlock-config.js",
  "ggwave.js",
  "manifest.json",
  "icon.png",
  "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.0.2",
  "https://cdn.jsdelivr.net/npm/algosdk@2.7.0/dist/browser/algosdk.min.js",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS).catch(() => {})));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  e.respondWith(
    caches.match(e.request).then((hit) => {
      if (hit) return hit;
      return fetch(e.request)
        .then((resp) => {
          const copy = resp.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy).catch(() => {}));
          return resp;
        })
        .catch(() => caches.match("guard.html"));
    })
  );
});
