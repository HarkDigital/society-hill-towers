// Personal CORS passthrough for the live-flights layer.
//
// Why this exists (Aug 2026): no ADS-B aggregator speaks CORS to browsers, and
// the free public passthroughs the page rode have died out — allorigins.win and
// codetabs.com return 522 from dead backends, corsproxy.io paywalled proxying
// entirely. This ~30-line worker is the reliable path: it serves ONLY the fixed
// adsb.fi Philadelphia query (useless as an open proxy), answers every origin
// with CORS headers, and caches upstream for 8 s so any number of viewers cost
// adsb.fi at most one request per cadence.
//
// Deploy free (either host, ~5 minutes, no credit card):
//   Cloudflare: dash.cloudflare.com -> Workers & Pages -> Create Worker ->
//               replace the starter code with this file -> Deploy -> copy the
//               https://<name>.<account>.workers.dev URL
//   Deno:       dash.deno.com -> New Playground -> paste this file -> the
//               https://<name>.deno.dev URL is live immediately
// Then paste that URL into FLIGHT_PROXY at the top of the live-flights section
// in app.js, run build.py, and push. The page prefers the proxy and polls it
// at 10 s instead of 90 s.

const UPSTREAM = 'https://opendata.adsb.fi/api/v2/lat/39.872/lon/-75.241/dist/30';
const TTL_MS = 8000;
let cached = { t: 0, body: '' };

const HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Cache-Control': 'no-store',
  'Content-Type': 'application/json',
};

export default {
  async fetch(req) {
    if (req.method === 'OPTIONS') return new Response(null, { headers: HEADERS });
    if (req.method !== 'GET') return new Response('{"error":"GET only"}', { status: 405, headers: HEADERS });
    const now = Date.now();
    if (now - cached.t > TTL_MS) {
      try {
        const up = await fetch(UPSTREAM, { headers: { 'User-Agent': 'society-hill-towers flight layer (personal proxy, cached 8s)' } });
        if (!up.ok) throw new Error('upstream ' + up.status);
        cached = { t: now, body: await up.text() };
      } catch (e) {
        // stale beats empty: keep serving the last good payload and let the
        // page's dead reckoning fly the gap; error only when we have nothing
        if (!cached.body) return new Response(JSON.stringify({ error: String(e && e.message || e) }), { status: 502, headers: HEADERS });
      }
    }
    return new Response(cached.body, { headers: HEADERS });
  },
};
