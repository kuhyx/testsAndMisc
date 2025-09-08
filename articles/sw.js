// Minimal image cache-first service worker
const C = 'articles-img-v2';
const AC = 'articles-json-v1';
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const u = new URL(req.url);
  const isImg = req.destination === 'image' || u.pathname.startsWith('/uploads/');
  const isArticle = u.pathname.startsWith('/api/articles/') && u.pathname.length > '/api/articles/'.length;
  if (isImg) {
    e.respondWith((async () => {
      const cache = await caches.open(C);
      const hit = await cache.match(req, { ignoreVary: true, ignoreSearch: false });
      if (hit) return hit;
      const res = await fetch(req);
      if (res && res.ok) cache.put(req, res.clone());
      return res;
    })());
  } else if (isArticle) {
    e.respondWith((async () => {
      const cache = await caches.open(AC);
      const hit = await cache.match(req);
      if (hit) return hit;
      const res = await fetch(req);
      if (res && res.ok) cache.put(req, res.clone());
      return res;
    })());
  }
});
