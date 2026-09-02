# philly3d.com — VPS operations

Everything in this directory is applied **by hand, by the owner**, on the lionspool VPS (`ssh lionspool-vps`, root; the box also serves harkpicks.com and thelionspool.com from the same nginx — a bad config test darkens all three, so `nginx -t` before every reload, no exceptions). Nothing here is applied automatically; `deploy_philly3d.sh` only ever touches `/var/www/philly3d` and `/var/www/philly3d-prev`.

| file | goes to | what it is |
|---|---|---|
| `philly3d.http.conf.example` | `/etc/nginx/conf.d/philly3d-http.conf` | http-scope pieces: the IP-free `beacon` log format, the `$philly3d_acao` origin map |
| `philly3d.vhost.example` | `/etc/nginx/sites-available/philly3d` | the three server blocks (80 → https, www → apex, apex) with every addition commented |
| `nginx-restart.conf` | `/etc/systemd/system/nginx.service.d/restart.conf` | nginx retries a failed start every 30 s forever |
| `uptime.md` | — | two-line external HEAD check with email alerting |
| `septa_bake.py` + `septa-bake.service` (loop; `septa-bake.timer` is the oneshot alternative) | `/opt/philly3d/`, `/etc/systemd/system/` | SEPTA TransitViewAll → `/var/www/philly3d/septa.json` every 10 s |
| `ais_relay.py` + `ais-relay.service` | `/opt/philly3d/`, `/etc/systemd/system/` | one aisstream.io socket → `/var/www/philly3d/ais.json` every 4 s |
| `../deploy_philly3d.sh` | run from the laptop | tests → build → gzip gate → keep prev pair → `rsync --delay-updates` → live sha256 verify; `--rollback` |

## 1. Rebuild the VPS from scratch

Recorded facts (handoff.md Rounds 31, 39, Aug 27 incident): Ubuntu, nginx 1.24.0 from the distro (`gzip on` in nginx.conf, `gzip_types` commented out, so only text/html is compressed on the fly — the `.gz` twins matter), Python 3.12.3, no `websockets` module, no IPv6 egress, systemd-resolved at 127.0.0.53, certbot with the nginx plugin's `options-ssl-nginx.conf`.

1. **Packages:** `apt install nginx certbot python3` (python3-certbot-nginx is where `/etc/letsencrypt/options-ssl-nginx.conf` and `ssl-dhparams.pem` come from; install it even though issuance uses `--webroot`).
2. **Web root:** `mkdir -p /var/www/philly3d /var/www/philly3d-prev /var/cache/nginx/adsb`. Every file nginx serves must be **mode 644, world-readable** — the laptop checkout lives in CloudStorage where everything is mode 600 and `rsync -az` ships that faithfully; nginx then answers a site-wide 403 (Round 39 lost ten minutes to it). `deploy_philly3d.sh` stages into a temp dir and `chmod 644`s there because macOS openrsync has no `--chmod`; if you ever copy files any other way, `chmod 644 /var/www/philly3d/*` afterwards.
3. **Cache zone:** `/etc/nginx/conf.d/adsb_cache.conf` containing exactly
   `proxy_cache_path /var/cache/nginx/adsb levels=1 keys_zone=adsb_cache:1m max_size=10m inactive=60s use_temp_path=off;`
4. **http-scope snippet:** `philly3d.http.conf.example` → `/etc/nginx/conf.d/philly3d-http.conf`.
5. **Vhost:** `philly3d.vhost.example` → `/etc/nginx/sites-available/philly3d`, `ln -s /etc/nginx/sites-available/philly3d /etc/nginx/sites-enabled/philly3d`. Before the certificate exists, temporarily comment out the two `:443` server blocks (they reference `/etc/letsencrypt/live/philly3d.com/…` and `nginx -t` fails without it), `nginx -t && systemctl reload nginx`.
6. **Certificate** (as recorded — `certonly --webroot`, both names, renewal is scheduled by the certbot package's systemd timer and runs through the `:80` ACME location, which is why that path never redirects):
   `certbot certonly --webroot -w /var/www/philly3d -d philly3d.com -d www.philly3d.com`
   then restore the `:443` blocks, `nginx -t && systemctl reload nginx`. Check `systemctl list-timers certbot.timer`.
7. **gzip_static:** nothing to install — it is in the distro build. The page is served from `index.html.gz` (deploy builds it with `gzip -k9`); `gzip_static on` in `location = /` and `location /` makes nginx hand the `.gz` to any client that accepts gzip and the raw file to the rest. The same mechanism serves `septa.json.gz` / `ais.json.gz`.
8. **The `/adsb` resolver line and why `ipv6=off` is load-bearing.** A hostname written literally in `proxy_pass` is resolved once, when nginx loads the config. On Aug 27 unattended-upgrades restarted nginx while systemd-resolved was itself mid-upgrade; that one lookup failed, nginx refused to start, and all three sites were dark for nine hours. `resolver 127.0.0.53 valid=300s ipv6=off; set $adsb_host opendata.adsb.fi; proxy_pass https://$adsb_host/…;` defers DNS to request time: nginx always starts, and a resolver failure at worst 502s `/adsb` while `proxy_cache_use_stale` keeps serving the last 8 s copy. `ipv6=off` matters because the box has no IPv6 egress (`curl -6` dies) — with AAAA answers allowed nginx would pick an unreachable address and the proxy would strand. Do not "clean up" either line.
9. **Restart drop-in:** `mkdir -p /etc/systemd/system/nginx.service.d && cp nginx-restart.conf /etc/systemd/system/nginx.service.d/restart.conf && systemctl daemon-reload`.
10. **Deploy:** from the laptop, `3d-model/deploy_philly3d.sh` (needs the `lionspool-vps` ssh alias). It refuses to ship a proxyless or unbranded build, gates the gzip size, keeps the previous `index.html` + `.gz` in `/var/www/philly3d-prev`, and ends by proving the live site hashes to the local build. `deploy_philly3d.sh --rollback` puts the previous pair back and re-verifies.
11. **Feeds:** sections 3 and 4 below.
12. **Uptime:** `uptime.md`.

## 2. Applying the nginx snippets

Always in this order, always with a test between steps:

```sh
cp -a /etc/nginx/sites-available/philly3d /root/philly3d.vhost.bak-$(date +%F)   # keep the live file
cp philly3d.http.conf.example /etc/nginx/conf.d/philly3d-http.conf
nginx -t                                   # must pass: the map and log_format are now defined
cp philly3d.vhost.example /etc/nginx/sites-available/philly3d   # or merge by hand — see the header comment
nginx -t                                   # must pass before ANY reload
systemctl reload nginx
curl -sI https://philly3d.com/ | grep -iE 'strict-transport|x-content-type|referrer-policy|cache-control|content-encoding'
curl -sI https://www.philly3d.com/ | head -3                              # 301 -> https://philly3d.com/
curl -sI -H 'Origin: https://harkdigital.github.io' https://philly3d.com/adsb | grep -i access-control   # echoes the origin
curl -sI -H 'Origin: https://evil.example' https://philly3d.com/adsb | grep -i access-control            # nothing
```

If `nginx -t` fails, `cp -a /root/philly3d.vhost.bak-… /etc/nginx/sites-available/philly3d` and test again — nginx keeps serving the old config until a reload that passes, so a failed test costs nothing as long as you never reload on red. Things to check against the live file before copying the example over it: the `ssl_dhparam` path (the example assumes certbot's `/etc/letsencrypt/ssl-dhparams.pem`), and that the `proxy_cache adsb_cache` zone name matches `conf.d/adsb_cache.conf`.

What each addition does is written above it in the example; in one line each: HSTS/nosniff/Referrer-Policy on every response (re-declared in every location that has its own `add_header`, because nginx does not inherit them once a location adds any header); `gzip_vary`; `Cache-Control: public, max-age=600, must-revalidate` on the page so a deploy is seen within ten minutes; `www` → apex 301; `/adsb` hides the upstream HSTS/NEL/Report-To/Cache-Control and answers ACAO only to philly3d.com and harkdigital.github.io; `/b` is an opt-in 204 beacon logged without addresses; `/septa.json` and `/ais.json` are static with `.gz` twins, `max-age=10`, ACAO `*`; dotfiles 404.

## 3. SEPTA baker

Stdlib only. Every 10 s it fetches `https://www3.septa.org/api/TransitViewAll/index.php` (fallback `https://api.septa.org/api/…`, the page's `SEPTA_HOSTS`), keeps only the fields the page reads, and writes `/var/www/philly3d/septa.json` and `.gz` atomically (temp file, fsync, rename, mode 644). On any bad answer it logs and **keeps the previous file**; the page treats `t` older than 90 s as "baker down" and falls back to its own JSONP.

```sh
mkdir -p /opt/philly3d && cp septa_bake.py /opt/philly3d/ && chmod 755 /opt/philly3d/septa_bake.py
python3 /opt/philly3d/septa_bake.py --out /var/www/philly3d/septa.json && ls -l /var/www/philly3d/septa.json*   # one bake, by hand
cp septa-bake.service /etc/systemd/system/ && systemctl daemon-reload
systemctl enable --now septa-bake.service      # one --loop process; septa-bake.timer is the oneshot alternative
systemctl status septa-bake ; journalctl -u septa-bake -n 5
curl -s https://philly3d.com/septa.json | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["t"], sum(len(v) for v in d["routes"][0].values()), "vehicles")'
```

Shape written: `{"t": <unix seconds>, "routes": [ { "<routeId>": [ {"VehicleID","lat","lng","heading","timestamp","destination","late","next_stop_name"}, … ] } ]}` — upstream's structure with an added `t`, values untouched. Prefer one long-lived process? The service file's header explains the `--loop` variant.

## 4. AIS relay

Stdlib only — it speaks WebSocket itself (RFC 6455 over `ssl`), so **no `pip install` is needed** on the box (Python 3.12.3, no `websockets` module, and none required). Holds one `wss://stream.aisstream.io/v0/stream` connection with the page's exact subscription (bbox `[[39.80,-75.45],[40.08,-74.82]]`, `PositionReport` + `ShipStaticData`), keeps the fleet by MMSI, writes `/var/www/philly3d/ais.json` + `.gz` every 4 s, drops vessels unseen for 30 min, reconnects with jittered backoff 15 s → 4 min, never exits on its own.

```sh
cp ais_relay.py /opt/philly3d/ && chmod 755 /opt/philly3d/ais_relay.py
mkdir -p /etc/philly3d && printf 'AISSTREAM_KEY=%s\n' 'PASTE-KEY-HERE' > /etc/philly3d/ais.env && chmod 600 /etc/philly3d/ais.env
cp ais-relay.service /etc/systemd/system/ && systemctl daemon-reload
systemctl enable --now ais-relay.service
journalctl -u ais-relay -f            # "stream live" within a few seconds; "upstream says: Api Key Is Not Valid" means the key
curl -s https://philly3d.com/ais.json | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["t"]-d["src"], "s since upstream;", len(d["ships"]), "ships")'
```

Shape written: `{"t": <unix seconds of the write>, "src": <unix seconds of the last upstream message>, "ships": [ {"mmsi": int, "lat", "lon", "sog" (knots), "cog", "hdg" (0–359, 511 or null when unknown), "name" ("" unknown), "type" (AIS type int, 0 unknown), "len" (A+B m or null), "beam" (C+D m or null), "dest" ("" unknown), "nav" (int or null), "t" (unix seconds of that vessel's last position report)} ] }`. The page treats `t` older than 60 s as "relay down".

**The key is single-client.** An aisstream.io free key streams to one connection at a time. Until the page is switched to `/ais.json` it still carries the old key as a direct-WebSocket fallback, so an open browser tab and this relay will steal the stream from each other. Sequence: bring the relay up with the **current** key → switch the page to `/ais.json` and deploy → then rotate.

## 5. What the owner must do by hand

- **Rotate the aisstream.io key** in your aisstream.io account after the relay is live and the page no longer connects directly; put the new key in `/etc/philly3d/ais.env` and `systemctl restart ais-relay`. The old key is in every published copy of the page (by your earlier informed choice) and will keep being tried by cached copies until it is dead.
- **Decide on the beacon.** `location = /b` is installed but nothing calls it; the page only ever fires it if you opt in on the client side. Even then the log holds time, path and browser family — no addresses.
- **Apply every snippet above yourself** with `nginx -t` between steps; nothing in this directory is pushed to the box by any script.
- **Set up the uptime check** (`uptime.md`) — the alert email address is yours to choose.
- **Confirm the `ssl_dhparam` path and the `adsb_cache` zone name** against the live files before overwriting the vhost.
- **Install the nginx restart drop-in** (section 1, step 9) — it was deliberately left off the shared box until now.

## 6. Verification after everything is applied

```sh
nginx -t && systemctl status nginx --no-pager | head -5
systemctl show nginx -p Restart -p RestartUSec
curl -sI https://philly3d.com/ | grep -ciE 'strict-transport-security|x-content-type-options|referrer-policy'   # 3
curl -sI -H 'Accept-Encoding: gzip' https://philly3d.com/ | grep -iE 'content-encoding|vary|cache-control'
curl -sI https://philly3d.com/septa.json ; curl -sI https://philly3d.com/ais.json
curl -sI https://philly3d.com/b ; wc -l /var/log/nginx/philly3d_beacon.log
```
