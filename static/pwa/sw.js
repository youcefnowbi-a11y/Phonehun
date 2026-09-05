// DroidCommand Service Worker
// v21: static assets are NETWORK-FIRST with cache fallback (was cache-first:
// a refresh served stale JS while "revalidating" — on a live LAN panel the
// cockpit must always run today's code, the cache exists only for offline).
const CACHE_NAME = 'vesper-v21';
const STATIC_ASSETS = [
  '/',
  '/warroom',
  '/static/pwa/manifest.json',
  '/static/pwa/css/dimension.css',
  '/static/pwa/js/app.js',
  '/static/pwa/js/glass.js',
  '/static/pwa/js/phone_intelligence.js',
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

  // HTML Navigation: Network-First so deployments update immediately, fallback to cache offline
  if (event.request.mode === 'navigate' || url.pathname === '/' || url.pathname === '/warroom') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response && response.status === 200) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          }
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Static Assets: NETWORK-FIRST, cache fallback when offline.
  // (v20 was cache-first — after every deploy the user ran yesterday's JS
  // for one load, and mixed old-JS/new-API shapes could dead-render the
  // cockpit: the "refresh wiped everything" report.)
  // ignoreSearch: precached assets carry no ?v= query; the page requests ?v=21.
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response && response.status === 200 && response.type === 'basic') {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        }
        return response;
      })
      .catch(() => caches.match(event.request, { ignoreSearch: true }))
  );
});
