// Cache only the public app shell and explicitly labelled teaching examples.
// Uploaded documents, status responses and real AI reports are never cached.
const CACHE = 'wenmo-public-v3';
const PUBLIC_ASSETS = [
  '/', '/static/style.css', '/static/mobile-app.css', '/static/app.js',
  '/static/mobile-app.js', '/static/site-config.js', '/static/site-api.js', '/static/manifest.webmanifest',
  '/static/art/writing-garden.svg', '/static/art/story.svg', '/static/art/argument.svg',
  '/static/art/wenmo-180.png', '/static/art/wenmo-192.png', '/static/art/wenmo-512.png',
  '/static/art/wenmo-maskable-512.png', '/api/demo/narrative', '/api/demo/argumentative'
];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(PUBLIC_ASSETS)));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('wenmo-public-') && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) return;
  if (!PUBLIC_ASSETS.includes(url.pathname)) return;
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).catch(() => caches.match('/')));
  } else {
    event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request)));
  }
});
