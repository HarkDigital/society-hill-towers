// Philly3D service worker: network only. Its presence (with a real fetch handler) is what
// lets Chrome and Edge offer "Install" for the page; nothing is cached, because the page is
// one 25 MB file rebuilt every deploy and a cached copy would outlive the deploy that
// replaced it. Same-origin navigations go straight to the network; everything else is left
// to the browser's default path.
// The recovery round: "straight to the network" was not true of the loads that mattered. WebKit
// reloads a page killed for memory with stale content allowed (ReturnCacheDataElseLoad, whatever
// Cache-Control says), a session restore does the same, and fetch(e.request) carried that cache
// mode through, so a crash reload ran whichever build the phone's cache held, days old at times,
// with recovery logic older than the build that had just died. A navigation is now fetched by
// its URL with no-cache: always revalidated with the server, so a stale copy is never served, while
// an unchanged build costs a 304 and a new one refreshes the HTTP cache the fallback reads (review:
// no-store downloaded all 12 MB on every visit and froze that cache on an old build). A new Request
// built on a navigate request throws in Chrome, so the URL it is. The request itself is the fallback: offline (the page is no use offline anyway) and on a
// redirect, since a followed redirect cannot answer a navigation (its redirect mode is manual)
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', (e) => {
  if (e.request.mode !== 'navigate' || e.request.method !== 'GET') return;
  e.respondWith(fetch(e.request.url, { cache: 'no-cache', credentials: 'same-origin' })
    .then((r) => (r.redirected ? fetch(e.request) : r), () => fetch(e.request)));
});
