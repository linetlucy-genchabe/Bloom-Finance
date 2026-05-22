// ============================================================
// Bloom Finance — Service Worker
// Handles caching, offline support, and background sync
// ============================================================

const CACHE_NAME = 'bloom-finance-v1';
const STATIC_CACHE = 'bloom-static-v1';
const DYNAMIC_CACHE = 'bloom-dynamic-v1';

// Assets to cache immediately on install
const STATIC_ASSETS = [
  '/',
  '/dashboard/',
  '/expenses/',
  '/savings/',
  '/investments/',
  '/subscriptions/',
  '/goals/',
  '/static/css/bloom.css',
  '/static/js/bloom.js',
  '/static/manifest.json',
  'https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap',
  'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js',
];

// Offline fallback page
const OFFLINE_URL = '/offline/';


// ── Install ───────────────────────────────────────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => cache.addAll(STATIC_ASSETS.filter(url => !url.startsWith('http'))))
      .then(() => self.skipWaiting())
  );
});


// ── Activate ──────────────────────────────────────────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => key !== STATIC_CACHE && key !== DYNAMIC_CACHE)
          .map(key => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});


// ── Fetch strategy ────────────────────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests (forms, POST actions)
  if (request.method !== 'GET') return;

  // Skip admin, API calls
  if (url.pathname.startsWith('/admin/')) return;

  // Static assets — Cache First
  if (url.pathname.startsWith('/static/') || url.hostname.includes('fonts.googleapis') || url.hostname.includes('jsdelivr')) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // HTML pages — Network First with offline fallback
  event.respondWith(networkFirstWithOffline(request));
});


// ── Cache strategies ──────────────────────────────────────────────────────────

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('Asset unavailable offline', { status: 503 });
  }
}

async function networkFirstWithOffline(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    // Network failed — try cache
    const cached = await caches.match(request);
    if (cached) return cached;

    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      return offlinePage();
    }
    return new Response('Offline', { status: 503 });
  }
}

function offlinePage() {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Bloom Finance — Offline</title>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Poppins', sans-serif; background: linear-gradient(135deg, #EDD8FF, #FFE4E8); min-height: 100vh; display: flex; align-items: center; justify-content: center; margin: 0; }
    .card { background: white; border-radius: 24px; padding: 48px 40px; text-align: center; max-width: 380px; box-shadow: 0 20px 60px rgba(139,92,200,.15); }
    .icon { font-size: 64px; margin-bottom: 16px; }
    h1 { font-size: 22px; color: #3D2B5E; margin-bottom: 8px; }
    p { color: #7A6B8A; font-size: 14px; line-height: 1.6; }
    button { margin-top: 24px; background: linear-gradient(135deg, #9B72C8, #C8A8E9); color: white; border: none; border-radius: 10px; padding: 12px 28px; font-family: 'Poppins', sans-serif; font-size: 14px; font-weight: 600; cursor: pointer; }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">🌸</div>
    <h1>You're offline</h1>
    <p>Bloom Finance needs a connection to load fresh data. Check your internet and try again.</p>
    <button onclick="location.reload()">Try Again</button>
  </div>
</body>
</html>`;
  return new Response(html, { headers: { 'Content-Type': 'text/html' } });
}


// ── Push notifications ────────────────────────────────────────────────────────
self.addEventListener('push', event => {
  const data = event.data?.json() ?? {};
  const title = data.title || 'Bloom Finance 🌸';
  const options = {
    body: data.body || 'You have a notification',
    icon: '/static/images/icons/icon-192x192.svg',
    badge: '/static/images/icons/icon-72x72.svg',
    vibrate: [100, 50, 100],
    data: { url: data.url || '/dashboard/' },
    actions: [
      { action: 'view', title: 'View' },
      { action: 'dismiss', title: 'Dismiss' },
    ],
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  if (event.action !== 'dismiss') {
    event.waitUntil(clients.openWindow(event.notification.data.url));
  }
});