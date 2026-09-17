# Browser pane gotchas

Every item here cost real time to find. They share a shape: the pane does not
error, it just quietly does something other than what you assumed, so the
symptom shows up later as a wrong conclusion rather than a failure.

## Timing and throttling

- **A hidden pane is CPU- and timer-throttled.** Build timings measured while the
  pane is hidden are inflated several fold. Only compare A/B runs in the same pane
  state, and take any performance number from a visible pane.
- **`setTimeout` / `setInterval` are clamped** to 1 s in a hidden pane, then to
  once a minute after about 5 minutes hidden. Timer loops stall. Drive real time
  from a MessageChannel yield loop calling `__dbg.frameOnce()` every 50 ms of
  `performance.now()`, which is not throttled.
- **A synchronous `frameOnce()` loop advances no real time.** Glides, fetch
  callbacks and cadence gates never fire inside one. If you are waiting for
  something to arrive, you need real time to pass between frames.
- **`javascript_tool` times out at 45 s** and the page keeps running after it does,
  so a timed-out call leaves you unsure what completed. Keep calls short and
  single-purpose.
- **Page load**: about 6 s warm, 40 to 45 s cold. `window.__dbg` is undefined until
  the build finishes.

## Reloading and tabs

- **`navigate` to the URL the pane already shows does not reload.** Same path and
  hash means nothing happens and you keep testing the old build. Bump a throwaway
  query (`&v=N`) every time.
- **Pass `tabId` explicitly on every call.** A stray tab from an agent or an
  earlier step can become active, and calls without `tabId` land there and report
  "No site is open".

## Live feeds

- **`document.hidden` stays true in the pane even after `tabs_select`**, so any
  poll gated on it never fires. For a verification spoof it:

  ```js
  Object.defineProperty(document, 'hidden', { get: () => false, configurable: true });
  ```

  Then drive `frameOnce()` and allow about 2.5 s of real time for the fetch.
- **Feeds can be served from the scratch directory.** On localhost the page reads
  `/concerts.json`, `/lightning.json`, `/amtrak.json` and friends from the origin,
  so a fixture beside `after.html` exercises the real code path. Bake fixtures
  through the real baker's `project()` so the contract under test is the baker's,
  not your idea of it.
- **The baked feeds are already in the page's trimmed shape** (`num`, `route`,
  `id`), not the upstream API's raw field names. Only the direct-API fallback path
  does the renaming.

## Captures

- **Screenshots of a hidden pane fail.** Canvas captures through `__cap` work
  regardless, which is the main reason the helper exists.
- **Captures come out at the pane's DPR**, typically 2240x1260. Crop with PIL for
  pin-sized detail rather than squinting at a full frame.
- **The canvas never includes the HUD or DOM cards.** Those need the pane's own
  screenshot, which needs a visible pane.

## Rendering and measurement

- **Frame timing in the pane is not trustworthy**, even with `gl.finish()` around
  `frameOnce`. Count triangles and draw calls instead:
  `renderer.info` with `autoReset = false`.
- **Freed geometries cannot be raycast or bounding-boxed** from `__dbg.scene`
  (`freeOnUpload`), and their attribute arrays read back `null`, so a vertex colour
  cannot be sampled from the scene graph at all. Measure the **pixels** instead:
  point the camera straight down, drive `frameOnce()`, then `drawImage` the WebGL
  canvas into a small 2D canvas and average `getImageData`. Round 87 settled
  "is the woodland tint actually landing" that way in one call, with West Park's
  ground at [59, 75, 45] against [74, 87, 60] for non-park ground beside it.

  ```js
  const off = document.createElement('canvas'); off.width = off.height = 120;
  const ctx = off.getContext('2d');
  __dbg.goFly(x, 500, z, 0, -1.5707);
  for (let i = 0; i < 8; i++) __dbg.frameOnce();
  ctx.drawImage(__dbg.renderer.domElement, cv.width / 2 - 60, cv.height / 2 - 60, 120, 120, 0, 0, 120, 120);
  // then average ctx.getImageData(0, 0, 120, 120).data
  ```
- **Live shader experiments need a new cache key.** r149 reuses the first
  variant's compiled program, so set
  `mat.customProgramCacheKey = () => 'variantN'` and `needsUpdate`.
- **`applyLighting` rewrites uniforms every frame.** `detFar`, `sunLight.intensity`,
  `castShadow` and `postBright.uThr` are all overwritten, so an override set once
  silently proves nothing. Patch after it, and always run a control patch
  (`diffuseColor.rgb *= 0.3`) to confirm your edit is reaching the shader at all.

## Shell

- **In zsh, `set -- $var` does not word-split.** Spell probe arguments out.
- **A `while read` loop over a file with no trailing newline drops the last line.**
  Worth remembering when a survey silently comes back one item short.
