# External uptime check for philly3d.com

The Aug 27 outage lasted nine hours because nobody was told. Either line below fixes that; the first needs no hardware, the second needs any always-on box that is *not* the VPS.

1. **Free hosted monitor:** at UptimeRobot (free tier; Better Stack / Pulsetic are equivalent) add an HTTP(S) monitor for `https://philly3d.com/`, method HEAD, interval 5 minutes, keyword none, alert contact = your email — it mails on the first failed check and again on recovery.
2. **cron + curl from another machine** (mail via the box's `mail`/`sendmail`; swap in a `curl` to a Slack/Discord webhook if you prefer):
   `*/5 * * * * curl -fsSI --max-time 25 -o /dev/null https://philly3d.com/ || printf 'philly3d.com failed a HEAD check at %s\n' "$(date -u)" | mail -s 'philly3d.com DOWN' you@example.com`

Notes: `location = /` answers HEAD with 200 and the page's headers without sending the 23 MB body, so the check is free. Add `https://philly3d.com/adsb` as a second monitor if you want to know when the flight passthrough (not the site) is what died; it 502s independently by design.
