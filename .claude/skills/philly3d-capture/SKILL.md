---
name: philly3d-capture
description: Run, screenshot, and verify the Philly3D page (3d-model/society-hill-towers.html) in the Claude browser pane, including before/after comparison against the deployed build. Use this skill whenever you need to SEE the Philly3D model rather than reason about its source: any change to app.js, the shaders, the packers or the baked data; any request to screenshot, capture, compare, or check how something looks; any "did this break anything" or "show me before and after"; any check of a card, a badge, a label or a light theme; and any citywide survey through the __dbg probes. Use it even when the ask sounds like a small edit, because the page cannot be served from the checkout and the pane runs no animation frames, so the naive approach silently fails.
---

# Verifying Philly3D in the browser pane

The page is a single 26 MB HTML file with no dev server, no build watcher and no
test harness for its rendering. The only way to know a change worked is to look
at it. Two environment facts make the naive approach fail silently rather than
loudly, which is why this skill exists:

- **macOS TCC blocks serving from the checkout.** The pane's dev server calls
  `os.getcwd()` and gets a PermissionError inside Dropbox CloudStorage. Always
  serve a copy from the session scratchpad.
- **The pane runs no animation frames.** Nothing renders on its own. Every frame
  is one `__dbg.frameOnce()` call. A page that looks frozen is working correctly.

Read `references/pane-gotchas.md` before a long session. It holds the timing and
throttling facts that cost the most time to rediscover. `references/poses.md` has
the camera pose tables.

## The loop

### 1. Build and stage

```bash
cd 3d-model && python3 build.py
SP="<session scratchpad>/serve" && mkdir -p "$SP"
cp 3d-model/society-hill-towers.html "$SP/after.html"
```

For a before/after, take the baseline from git rather than rebuilding it:

```bash
git show HEAD:3d-model/society-hill-towers.html > "$SP/before.html"
```

This settles "did this round break it" in two minutes, and it distinguishes a
regression you introduced from something that was already wrong. Round 85's Kelly
Drive kink turned out identical in the deployed build, which is the only reason it
did not eat the round.

### 2. Serve it

Add one entry to `.claude/launch.json` pointing at that directory, then
`preview_start` it by name. Reuse an existing entry whose path still exists rather
than adding another; the file has accumulated a dead entry per session.

```json
{ "name": "sht-serve", "runtimeExecutable": "sh",
  "runtimeArgs": ["-c", "cd <scratchpad>/serve && exec python3 -m http.server 8947"],
  "port": 8947 }
```

### 3. Load, and bump the cache-buster

```
http://localhost:8947/after.html?dev=1&dpr=1&v=1
```

`?dev=1` is what exposes `window.__dbg`; without it nothing below works. **Bump
`v` on every reload.** `navigate` to a URL the pane already shows does not
reload, so a rebuilt `after.html` keeps running the old build and you debug a
ghost.

### 4. Poll for `__dbg` in its own call

`javascript_tool` times out at 45 s and a cold load takes 40 to 45 s, so a call
that both waits and captures will die mid-capture while the page keeps going.
Split it: poll in one call capped at 38 s, act in the next.

```js
const t0 = performance.now();
while (performance.now() - t0 < 38000) {
  if (window.__dbg && window.__dbg.goFly) break;
  await new Promise(r => setTimeout(r, 1000));
}
({ ready: !!window.__dbg, secs: Math.round((performance.now() - t0) / 1000) })
```

A warm reload lands in 6 to 8 s, so most calls after the first are quick.

### 5. Get past the chrome

```js
for (const id of ['btnGuideClose', 'btnEnter']) {
  const el = document.getElementById(id); if (el) el.click();
}
```

The guide is a first-visit overlay keyed on `localStorage philly3d.guide`, and the
scratch origin is always a first visit. Turn off `#btnTransit` and `#btnIndego`
for a clean architectural view: the SEPTA bubbles clutter every pose.

### 6. Check markup headlessly before reaching for pixels

Most verification is not visual at all. `__dbg.cardFor(kind, id)` returns the
card's `innerHTML` as a string, so a card's text, link or badge can be asserted
without a single screenshot, and the assertion is exact rather than eyeballed.

```js
const d = window.__dbg;
d.amtrakTest();                      // seeds four fixture trains
d.cardFor('amtrak', 't655');         // -> the card's innerHTML
```

The other feeds have the same shape: `flightTest()`, `shipTest()`,
`concertTest()`, `closureTest()`. Kinds for `cardFor` are `amtrak`, `flight`,
`closure`, `market`, `marker`, `art`, and ships by default.

### 7. Capture when you actually need pixels

Screenshots of a hidden pane fail, so captures go through a page-side helper that
POSTs the canvas to a local sink.

```bash
python3 .claude/skills/philly3d-capture/scripts/capture_server.py 8934   # background
lsof -nP -i :8934      # kill a previous session's sink first, or captures land in its scratchpad
```

Inject `scripts/cap.js` as a string, then:

```js
await __cap('skyline-after.jpg', -300, 240, 900, -0.653, -0.12, 6);
```

Files land in `captures/` beside the sink script; `Read` them afterwards. Two
constraints that produce silent garbage when broken:

- **Never `await` between the last `frameOnce()` and `toBlob`.** The compositor
  can present and clear the buffer in that gap and you get a 17 KB all-black jpeg
  that looks like a rendering bug.
- **Keep one `javascript_tool` call under about six captures**, or it times out at
  45 s while the page carries on, leaving you unsure which captures are real.

The canvas never includes the HUD or any DOM card. For those, take the pane's own
screenshot instead, which means the pane has to be visible.

### 7b. Measure pins and flicker instead of eyeballing them

Mike has reported pins that flash or vanish (Rounds 126, 127, 138, 143) and flicker
(Rounds 130, 140, 144) again and again; settle each with a number, before and after:

- **Pins**: inject `scripts/pin_sweep.js`, then `__pinSweep([[x, y, z, yaw0, yaw1], ...])`
  on the deployed build (`before.html`) and the new one at the same eyes. It returns
  on-screen showings and blinks; Round 143 went from 135 of 189 to 5 of 47.
- **Flicker**: three PNG captures 0.5 m apart, then
  `python3 scripts/flicker_diff.py captures/<prefix> --crop x0,y0,x1,y1` and read the crop.

### 7c. Measure memory the way an iPhone counts it (Round 158)

Never read the pane's `performance.memory` as live memory: Chrome collects lazily, and Round 158 read 800 to 1,500 MB
there against a live heap of 114 MB. On iOS the page is charged for its JS heap AND every WebGL buffer and texture, and
WebKit's ANGLE Metal backend keeps a padded copy of any vertex stream whose stride or offset is not a multiple of 4.
The tools in `scripts/memory/` (Node 18+, Google Chrome installed; they launch their own headless Chrome):

- `inject.py in.html out.html`: stages a build with `gpuhook.js` (bufferData / texImage2D / renderbuffer bytes, the
  peak, and the ANGLE audit: `__gpu.mis`, bytes of padded copies by stream format) ahead of everything.
- `measure.mjs <url> <label> <port>`: phone emulation (740x360 at 1.25, touch), a forced GC and the live heap at every
  loading-message change, then Enter, six frames and a look around; writes `meas-<label>.json` (peak live and where,
  GPU and copies at ready, after the frames, after the look, triangles, `PERF.failed`, the tier). Add `&lite=0|1|2`.
- `snap.mjs <url> <label> <port> <regex>`: a heap snapshot at the first loading message matching the regex, summarised
  by constructor and largest strings; `node --max-old-space-size=8192 retainers.mjs snap-<label>.heapsnapshot` groups
  closures, arrays, strings and numbers by their retainer chain (it found Round 158's 345,000 road-triangle closures).

Compare against a build from git that is known to work on the phone (`git show <sha>:3d-model/society-hill-towers.html`):
Round 158's reference is Sep 17's e90c765, 981 MB of GPU plus copies after the first frames, 162 MB peak live heap.

### 8. Syntax-check after every app.js edit

```bash
node --check 3d-model/app.js
```

Node is installed (`/opt/homebrew/bin/node`) and parses the file in about 0.06 s.
`scripts/jscheck.js` is the JavaScriptCore fallback via
`osascript -l JavaScript`, which is what the test suite uses so it stays portable;
reach for it only if node is missing.

## What a verified change looks like

Report what you actually observed, not that you looked. A capture at a named pose,
a probe's numbers, or an assertion on returned markup. "Verified in the pane" with
nothing behind it is the failure mode this whole loop exists to prevent, and the
devlog's value depends on the difference.

Frame timing measured in the pane is not trustworthy (see the gotchas file). When
the question is cost, count geometry instead: `renderer.info` with
`autoReset = false`, or `__dbg.perf()` in a **visible** pane.
