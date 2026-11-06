// Cache only the public app shell and explicitly labelled teaching examples.
// Uploaded documents, status responses and real AI reports are never cached.
const CACHE = 'wenmo-pages-public-v3';
const PUBLIC_ASSETS = [
  '/Essay-Marking-System/', '/Essay-Marking-System/static/style.css', '/Essay-Marking-System/static/mobile-app.css', '/Essay-Marking-System/static/app.js',
  '/Essay-Marking-System/static/mobile-app.js', '/Essay-Marking-System/static/site-config.js', '/Essay-Marking-System/static/site-api.js', '/Essay-Marking-System/static/manifest.webmanifest',
  '/Essay-Marking-System/static/art/writing-garden.svg', '/Essay-Marking-System/static/art/story.svg', '/Essay-Marking-System/static/art/argument.svg',
  '/Essay-Marking-System/static/art/wenmo-180.png', '/Essay-Marking-System/static/art/wenmo-192.png', '/Essay-Marking-System/static/art/wenmo-512.png',
  '/Essay-Marking-System/static/art/wenmo-maskable-512.png', '/Essay-Marking-System/examples/narrative.json', '/Essay-Marking-System/examples/argumentative.json'
];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(PUBLIC_ASSETS)));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('wenmo-pages-public-') && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) return;
  if (!PUBLIC_ASSETS.includes(url.pathname)) return;
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).catch(() => caches.match('/Essay-Marking-System/')));
  } else {
    event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request)));
  }
});
