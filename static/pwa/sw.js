// DroidCommand Service Worker
const CACHE_NAME = 'droidcommand-v11';
const STATIC_ASSETS = [
  '/',
  '/warroom',
  '/static/pwa/manifest.json',
  '/static/pwa/css/dimension.css',
  '/static/pwa/js/app.js',
  '/static/pwa/js/glass.js',
  '/static/pwa/js/modules.js',
  '/static/pwa/js/vesper_cockpit.js',
  '/static/pwa/js/cortex.js',
  '/static/pwa/js/radar.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.warn('[SW] Pre-cache warning:', err);
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Never cache API or stream endpoints
  if (url.pathname.startsWith('/api/') || url.pathname.includes('/screen-stream')) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => {
      const networked = fetch(event.request)
        .then((response) => {
          if (response && response.status === 200 && response.type === 'basic') {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          }
          return response;
        })
        .catch(() => cached);

      return cached || networked;
    })
  );
});
