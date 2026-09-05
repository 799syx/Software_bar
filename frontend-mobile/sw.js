const CACHE_NAME = "lingshan-mobile-v4";
const SHELL = [
  "/mobile/",
  "/mobile/index.html",
  "/mobile/styles.css",
  "/mobile/app.js",
  "/mobile/manifest.webmanifest",
  "/assets/scenic/photos/lingshan-grand-buddha.jpg",
  "/assets/scenic/photos/lingshan-screen-wall.jpg",
  "/assets/scenic/photos/five-brightness-bridge.png",
  "/assets/scenic/photos/buddha-foot-altar.png",
  "/assets/scenic/photos/five-wisdom-gate.jpg",
  "/assets/scenic/photos/bodhi-avenue.png",
  "/assets/scenic/photos/demon-subduing-relief.png",
  "/assets/scenic/photos/ashoka-pillar.png",
  "/assets/scenic/photos/children-mitreya.png",
  "/assets/scenic/photos/buddhist-culture-museum.jpg",
  "/assets/scenic/photos/nine-dragons-bath.jpg",
  "/assets/scenic/photos/brahma-palace.jpg",
  "/assets/scenic/photos/five-seal-mandala.jpg",
  "/assets/scenic/photos/brahma-flower-sea.png",
  "/assets/scenic/photos/manfeilong-pagoda.png",
  "/assets/scenic/photos/wujinyi-zhai.png",
  "/assets/scenic/photos/nianhua-plaza.png",
  "/assets/scenic/photos/nianhua-hall.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.pathname.startsWith("/api/")) return;
  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(() => caches.match("/mobile/index.html")));
    return;
  }
  if (url.origin !== self.location.origin) return;
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        }
        return response;
      });
    })
  );
});
