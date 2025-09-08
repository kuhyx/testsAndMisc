// Minimal image cache-first service worker
const C = 'articles-img-v1';
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  const req = e.request;
  const u = new URL(req.url);
  const isImg = req.destination === 'image' || u.pathname.startsWith('/uploads/');
  if (!isImg || req.method !== 'GET') return;
  e.respondWith((async () => {
    const cache = await caches.open(C);
    const hit = await cache.match(req, { ignoreVary: true, ignoreSearch: false });
    if (hit) return hit;
    const res = await fetch(req);
    if (res && res.ok) cache.put(req, res.clone());
    return res;
  })());
});
