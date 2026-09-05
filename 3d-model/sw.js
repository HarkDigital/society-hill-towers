// Philly3D service worker: network only. Its presence (with a real fetch handler) is what
// lets Chrome and Edge offer "Install" for the page; nothing is cached, because the page is
// one 25 MB file rebuilt every deploy and a cached copy would outlive the deploy that
// replaced it. Same-origin navigations go straight to the network; everything else is left
// to the browser's default path.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', (e) => {
  if (e.request.mode !== 'navigate') return;
  e.respondWith(fetch(e.request));
});
