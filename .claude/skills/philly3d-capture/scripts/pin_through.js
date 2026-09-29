// pin-through-building counter (Round 169): window.__PM. Inject as a string (javascript_tool, or Runtime.evaluate over CDP for
// long runs), then:  const r = await __PM.run(__PM.turn(x, y, z, pitch, yaw0, degPerSec, seconds), 'label'); __PM.post();
// or __PM.fly(x0, y0, z0, x1, y1, z1, speed, pitch, yawSwing). __PM.fps (30 for a phone's pace, 60 for a computer) sets the
// real time per frame; __PM.depth (2) holds the GPU to a two-frame backlog as a browser's swap chain does (without it an
// unpaced headless loop piles up frames and the pins' reads land 5 to 70 frames late); __PM.setLat(n) holds every read back
// n frames. post() renders a ground-truth image at every recorded camera (the page's own capture rule, only buildings) and
// counts `through` (pin-frames shown with the tip covered: shown means aPinVis > 0.5 AND the gate, recomputed from the
// images __dbg.pinGate() names; a build before Round 169 has no gate), `placardThrough`, the appearance latency of pins
// coming into clear view (latView from out of view, latCov from behind a building), `shownOfClear` and blinks. A run of 120
// frames and its post pass fit one 45 s javascript_tool call on a phone-sized page.
(() => {
  const d = __dbg, R = d.renderer, gl = R.getContext(), scene = d.scene, camera = d.camera;
  window.__yield = () => new Promise((r) => { const c = new MessageChannel(); c.port1.onmessage = () => r(); c.port2.postMessage(0); });
  const V = new THREE.Vector3();
  let MESHES = [];
  const findMeshes = () => { MESHES = []; scene.traverse((o) => { if (o.isInstancedMesh && o.geometry.attributes.aPinVis) MESHES.push(o); }); return MESHES.length; };
  // a knob on the page's fence: a read cannot land before LAT frames have been drawn since its fence (0: as the GPU says)
  let FRAME = 0, LAT = 0;
  const born = new Map(), fsync = gl.fenceSync.bind(gl), gsp = gl.getSyncParameter.bind(gl);
  gl.fenceSync = function (a, b) { const s = fsync(a, b); if (s) born.set(s, FRAME); return s; };
  gl.getSyncParameter = function (s, p) { if (LAT && p === gl.SYNC_STATUS && FRAME - (born.has(s) ? born.get(s) : FRAME) < LAT) return gl.UNSIGNALED; return gsp(s, p); };
  // the truth capture: the page's occRender for the pins, reproduced
  const FAR = 30000;
  const occMat = new THREE.ShaderMaterial({
    uniforms: { uFar: { value: FAR } }, side: THREE.DoubleSide,
    vertexShader: '#include <common>\n#include <logdepthbuf_pars_vertex>\nvarying float vViewZ;\nvoid main() {\n#include <begin_vertex>\n#include <project_vertex>\n#include <logdepthbuf_vertex>\n  vViewZ = -mvPosition.z;\n}',
    fragmentShader: '#include <packing>\n#include <logdepthbuf_pars_fragment>\nuniform float uFar;\nvarying float vViewZ;\nvoid main() {\n#include <logdepthbuf_fragment>\n  gl_FragColor = packDepthToRGBA(clamp(vViewZ / uFar, 0.0, 0.9999));\n}',
  });
  let sky = null; scene.traverse((o) => { if (o.material === d.skyMat) sky = o; });
  const tcam = new THREE.PerspectiveCamera(); tcam.matrixAutoUpdate = false; tcam.matrixWorldAutoUpdate = false;
  const rts = new Map();
  const rtFor = (W, H) => { const k = W + 'x' + H; if (!rts.has(k)) rts.set(k, { rt: new THREE.WebGLRenderTarget(W, H, { depthBuffer: true, stencilBuffer: false }), buf: new Uint8Array(W * H * 4) }); return rts.get(k); };
  function capture(view, proj, W, H, noFlats) {   // view = world to camera, proj as the page's capture camera
    tcam.near = camera.near; tcam.far = camera.far;
    tcam.matrixWorldInverse.copy(view); tcam.matrixWorld.copy(view).invert(); tcam.matrix.copy(tcam.matrixWorld);
    tcam.projectionMatrix.copy(proj); tcam.projectionMatrixInverse.copy(proj).invert();
    const T = rtFor(W, H), hid = [], shown = [];
    scene.traverse((o) => {
      if (o.userData && o.userData.occOnly) { if (noFlats && !o.visible) { o.visible = true; shown.push(o); } return; }
      if (!o.visible || o === scene) return;
      const m = o.material, tr = m && (Array.isArray(m) ? m.some((q) => q.transparent) : m.transparent);
      const nd = m && (Array.isArray(m) ? m.some((q) => q.depthWrite === false) : m.depthWrite === false);
      if (o === sky || o === d.cloudDeck || nd || o.isPoints || o.isLine || o.isSprite || tr || (o.userData && (o.userData.pinSceneDepth || (noFlats && o.userData.occFlat))) || o.isInstancedMesh) { o.visible = false; hid.push(o); }
    });
    const prevRT = R.getRenderTarget(), prevUp = R.shadowMap.autoUpdate, prevNeed = R.shadowMap.needsUpdate, prevOver = scene.overrideMaterial, prevBg = scene.background, prevA = R.getClearAlpha(), cc = new THREE.Color();
    R.getClearColor(cc);
    R.shadowMap.autoUpdate = false; R.shadowMap.needsUpdate = false;
    scene.overrideMaterial = occMat; scene.background = null;
    R.setRenderTarget(T.rt); R.setClearColor(0xffffff, 1); R.clear(true, true, false);
    try { R.render(scene, tcam); } finally {
      R.readRenderTargetPixels(T.rt, 0, 0, W, H, T.buf);
      R.setRenderTarget(prevRT); R.setClearColor(cc, prevA);
      scene.overrideMaterial = prevOver; scene.background = prevBg; R.shadowMap.autoUpdate = prevUp; R.shadowMap.needsUpdate = prevNeed;
      for (const o of hid) o.visible = true;
      for (const o of shown) o.visible = false;
    }
    return { buf: T.buf.slice(), view: view.clone(), proj: proj.clone(), W, H };
  }
  const unpack = (b, o) => (b[o] / 16777216 + b[o + 1] / 65536 + b[o + 2] / 256 + b[o + 3]) / 256 * FAR;
  function answer(C, x, y, z) {   // 1 clear, 0 covered, -1 not in the image (the page's 3 by 3 rule, the tip's need clamped under the sky)
    V.set(x, y, z).applyMatrix4(C.view);
    const vz = -V.z;
    if (vz <= 1 || (C.reach && vz > C.reach)) return -1;
    V.applyMatrix4(C.proj);
    const W = C.W, H = C.H, px = Math.floor((V.x * 0.5 + 0.5) * W), py = Math.floor((V.y * 0.5 + 0.5) * H);
    if (px < 0 || py < 0 || px >= W || py >= H) return -1;
    const need = Math.min(vz - (2.5 + vz * 0.02), FAR * 0.9998);
    for (let j = Math.max(0, py - 1); j <= Math.min(H - 1, py + 1); j++) for (let i = Math.max(0, px - 1); i <= Math.min(W - 1, px + 1); i++) if (unpack(C.buf, (j * W + i) * 4) >= need) return 1;
    return 0;
  }
  const V2b = new THREE.Vector3();
  function both(N, F, x, y, z) {   // the page's occImgBoth, reproduced
    V.set(x, y, z).applyMatrix4(N.view);
    const vza = -V.z;
    V.applyMatrix4(N.proj);
    const W = N.W, H = N.H, px = Math.floor((V.x * 0.5 + 0.5) * W), py = Math.floor((V.y * 0.5 + 0.5) * H);
    V2b.set(x, y, z).applyMatrix4(F.view);
    const vzb = -V2b.z;
    if (vza <= 1 || px < 0 || py < 0 || px >= W || py >= H || vzb <= 1 || vzb > F.reach) return -1;
    const needA = N.reach * 0.999, needB = Math.min(vzb - (2.5 + vzb * 0.02), FAR * 0.9998), e = N.proj.elements;
    for (let j = Math.max(0, py - 1); j <= Math.min(H - 1, py + 1); j++) for (let i = Math.max(0, px - 1); i <= Math.min(W - 1, px + 1); i++) {
      if (unpack(N.buf, (j * W + i) * 4) < needA) continue;
      V2b.set(((i + 0.5) / W * 2 - 1 + e[8]) / e[0] * vza, ((j + 0.5) / H * 2 - 1 + e[9]) / e[5] * vza, -vza).applyMatrix4(N.viewInv).applyMatrix4(F.view).applyMatrix4(F.proj);
      const qi = Math.floor((V2b.x * 0.5 + 0.5) * W - 0.5), qj = Math.floor((V2b.y * 0.5 + 0.5) * H - 0.5);
      if (qi < 0 || qj < 0 || qi + 1 >= W || qj + 1 >= H) continue;
      const o = (qj * W + qi) * 4;
      if (unpack(F.buf, o) >= needB && unpack(F.buf, o + 4) >= needB && unpack(F.buf, o + W * 4) >= needB && unpack(F.buf, o + W * 4 + 4) >= needB) return 1;
    }
    return 0;
  }
  const WIDE = 1.5;
  const wideProj = (p) => { const q = p.clone(); q.elements[0] /= WIDE; q.elements[5] /= WIDE; return q; };
  // on screen: the tip within the screen, a little below it (the badge stands over its tip) and a hair beside it
  const PV = new THREE.Matrix4();
  const onScreen = (x, y, z) => { V.set(x, y, z).applyMatrix4(PV); if (V.z >= 1 || V.z <= -1) return false; return V.x >= -1.03 && V.x <= 1.03 && V.y >= -1.15 && V.y <= 1.0; };
  const PM = window.__PM = {
    fps: 30,
    depth: 2,
    findMeshes, capture, answer, wideProj,
    setLat(n) { LAT = n; return LAT; },
    // a path: an array of [x, y, z, yaw, pitch] per frame
    turn(x, y, z, pitch, yaw0, degPerSec, seconds) { const F = PM.fps, n = Math.round(seconds * F), o = []; for (let f = 0; f <= n; f++) o.push([x, y, z, yaw0 + degPerSec * Math.PI / 180 * f / F, pitch]); return o; },
    fly(x0, y0, z0, x1, y1, z1, speed, pitch, yawSwing) {
      const L = Math.hypot(x1 - x0, y1 - y0, z1 - z0), n = Math.max(2, Math.round(L / speed * PM.fps)), yaw = Math.atan2(x1 - x0, -(z1 - z0)), o = [];
      for (let f = 0; f <= n; f++) { const t = f / n; o.push([x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z0 + (z1 - z0) * t, yaw + (yawSwing || 0) * Math.sin(f / PM.fps * 1.3), pitch]); }
      return o;
    },
    async settle(p, n = 45) { d.goFly(p[0], p[1], p[2], p[3], p[4]); let t = performance.now(); for (let i = 0; i < n; i++) { await __yield(); while (performance.now() - t < 1000 / PM.fps) {} t = performance.now(); FRAME++; d.frameOnce(); } },
    // the run: frames at 33.3 ms of real time each, recorded
    async run(path, label) {
      findMeshes();
      await PM.settle(path[0]);
      const frames = [], fq = [];
      let t = performance.now();
      for (let f = 0; f < path.length; f++) {
        const p = path[f];
        d.goFly(p[0], p[1], p[2], p[3], p[4]);
        await __yield();
        while (fq.length > PM.depth) { const q = fq[0]; let n = 0; while (gsp(q, gl.SYNC_STATUS) !== gl.SIGNALED && n++ < 2000) await __yield(); gl.deleteSync(q); fq.shift(); }
        while (performance.now() - t < 1000 / PM.fps) {}
        t = performance.now();
        FRAME++;
        const c0 = performance.now();
        d.frameOnce();
        const cpu = performance.now() - c0;
        fq.push(fsync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0)); gl.flush();
        camera.updateMatrixWorld();
        const rec = { cam: camera.matrixWorld.clone(), proj: camera.projectionMatrix.clone(), cpu, pins: [], placards: [] };
        PV.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
        MESHES.forEach((m, mi) => {
          if (!m.visible || !m.parent || m.count <= 0) return;
          let vis = true; for (let q = m.parent; q; q = q.parent) if (!q.visible) vis = false;
          if (!vis) return;
          const e = m.instanceMatrix.array, a = m.geometry.attributes.aPinVis.array;
          for (let i = 0; i < m.count; i++) {
            const x = e[i * 16 + 12], y = e[i * 16 + 13], z = e[i * 16 + 14];
            if (!onScreen(x, y, z)) continue;
            rec.pins.push(mi, i, x, y, z, a[i]);
            const st = m.userData.occ; if (st && st.why) rec.st = (rec.st || []).concat([st.why[i], st.age[i], st.okC[i], st.arr[i], d.pinOccAt ? 0 : 0]);
          }
        });
        if (d.pinGate) { const g = d.pinGate(); const im = (q) => q && { view: new THREE.Matrix4().fromArray(q.view), viewInv: new THREE.Matrix4().fromArray(q.viewInv), proj: new THREE.Matrix4().fromArray(q.proj), reach: q.reach, frame: q.frame, noFlats: q.noFlats }; rec.gate = { on: g.on, aNewer: g.aNewer, lag: g.now - g.frame, W: g.W, H: g.H, A: im(g.A), B: im(g.B) }; }
        // the placards on the page: a score bubble or a concert placard shown, with its tip (the roof point it hangs from)
        for (const s of (window.__placardTips ? window.__placardTips() : [])) rec.placards.push(s);
        frames.push(rec);
      }
      PM.last = { label, frames };
      return { label, frames: frames.length, cpuMs: +(frames.reduce((a, r) => a + r.cpu, 0) / frames.length).toFixed(2) };
    },
    // the post pass: truth at every frame's exact camera; the gate's image re-rendered from its recorded camera
    post(opts = {}) {
      const { frames } = PM.last, po = d.pinOcc(), W = po.w, H = po.h;
      const out = { frames: frames.length, pinFrames: 0, onScreen: 0, displayed: 0, through: 0, throughFrames: 0, throughPins: new Set(), placardShown: 0, placardThrough: 0, placardThroughFrames: 0, lat: [], never: 0, blinks: 0, clearShown: 0, clearAll: 0, gateOff: 0, placardClear: 0, placardClearShown: 0, placardBlinks: 0, latCov: [], latView: [], missCpu: 0, missFade: 0, missGate: 0 };
      const gateCache = new Map();
      const hist = new Map(), phist = new Map();   // key -> { clearSince, shownAt, lastShown, hideAt }
      const view = new THREE.Matrix4();
      for (let f = 0; f < frames.length; f++) {
        const r = frames[f];
        view.copy(r.cam).invert();
        const truth = capture(view, wideProj(r.proj), W, H, true);
        let GA = null, GB = null;
        const img = (q) => { const k = q.frame + ':' + q.reach; if (!gateCache.has(k)) { if (gateCache.size > 6) gateCache.delete(gateCache.keys().next().value); gateCache.set(k, Object.assign(capture(q.view, q.proj, r.gate.W, r.gate.H, q.noFlats), { reach: q.reach, viewInv: q.viewInv })); } return gateCache.get(k); };
        if (r.gate && r.gate.on) { GB = img(r.gate.B); if (r.gate.aNewer) GA = img(r.gate.A); }
        const gateOf = (x, y, z) => {
          if (!GB) return 0;
          if (!GA) return answer(GB, x, y, z) === 1 ? 1 : 0;
          V.set(x, y, z).applyMatrix4(GA.view);
          if (-V.z <= GA.reach) return answer(GA, x, y, z) === 1 ? 1 : 0;
          return both(GA, GB, x, y, z) === 1 ? 1 : 0;
        };
        let thr = 0;
        const seen = new Set();
        for (let q = 0; q < r.pins.length; q += 6) {
          const mi = r.pins[q], i = r.pins[q + 1], x = r.pins[q + 2], y = r.pins[q + 3], z = r.pins[q + 4], a = r.pins[q + 5];
          out.onScreen++;
          const t = answer(truth, x, y, z);
          const gate = r.gate ? gateOf(x, y, z) : 1;
          if (r.gate && !r.gate.on) out.gateOff++;
          const shown = a > 0.5 && gate === 1;
          if (shown) out.displayed++;
          if (shown && t === 0) { thr++; out.through++; out.throughPins.add(mi + ':' + i); if (r.gate) { if (r.gate.lag === 0 && (out.ex0 || (out.ex0 = [])).length < 12) { V.set(x, y, z); const dd = Math.round(V.distanceTo(new THREE.Vector3().setFromMatrixPosition(r.cam))); let vza = null; if (GA) { V.applyMatrix4(GA.view); vza = Math.round(-V.z); } out.ex0.push({ f, mi, i, d: dd, vza, aReach: GA && Math.round(GA.reach), bReach: Math.round(GB.reach), aF: r.gate.A && r.gate.A.frame, bF: r.gate.B.frame }); } const kk = 'thrLag' + r.gate.lag + (r.gate.aNewer ? 'A' : ''); out[kk] = (out[kk] || 0) + 1; } }
          // appearance: the truth says clear from some frame on; how long until the pin is displayed
          const key = mi + ':' + i + ':' + Math.round(x / 30) + ',' + Math.round(z / 30);
          seen.add(key);
          let h = hist.get(key);
          if (!h) { h = { clearSince: -1, shown: false, wasShown: false, lastHide: -99, lastCov: -99, first: f }; hist.set(key, h); }
          if (t === 0) h.lastCov = f;
          if (t === 1) {
            out.clearAll++; if (shown) out.clearShown++; else if (a <= 0.5) { if (a > 0.001) out.missFade++; else { out.missCpu++; if (r.st) { const w = r.st[(q / 6) * 5]; out['why' + w] = (out['why' + w] || 0) + 1; if (w === 2) { const ago = f - h.lastCov; const b = ago <= 10 ? 'cov10' : ago <= 30 ? 'cov30' : h.first > f - 3 ? 'new' : 'never30'; out[b] = (out[b] || 0) + 1; } } } } else out.missGate++;
            if (h.clearSince < 0) { h.clearSince = f; h.done = false; h.from = h.lastCov === f - 1 ? 'cov' : 'view'; }
            if (shown && !h.done) { out.lat.push(f - h.clearSince); (h.from === 'cov' ? out.latCov : out.latView).push(f - h.clearSince); h.done = true; }
            if (h.wasShown && !shown) h.lastHide = f;
            if (shown && !h.wasShown && f - h.lastHide <= 10 && h.lastHide > h.clearSince) out.blinks++;
          } else {
            if (h.clearSince >= 0 && !h.done && f - h.clearSince >= 1) out.never++;
            h.clearSince = -1; h.done = false;
          }
          h.wasShown = shown;
        }
        for (const [k, h] of hist) if (!seen.has(k)) { if (h.clearSince >= 0 && !h.done && f - h.clearSince >= 1) out.never++; hist.delete(k); }
        if (thr) out.throughFrames++;
        // the placards
        let pthr = 0;
        for (const s of r.placards) {
          const pk = Math.round(s.x) + ',' + Math.round(s.z), ph = phist.get(pk) || { was: false, hideAt: -99 };
          phist.set(pk, ph);
          const tt = answer(truth, s.x, s.y, s.z);
          if (s.on && tt === 1) { out.placardClear++; if (s.shown) out.placardClearShown++; }
          if (ph.was && !s.shown && s.on) ph.hideAt = f;
          if (!ph.was && s.shown && f - ph.hideAt <= 15) out.placardBlinks++;
          ph.was = s.shown;
          if (!s.shown) continue;
          out.placardShown++;
          if (tt === 0) { pthr++; out.placardThrough++; }
        }
        if (pthr) out.placardThroughFrames++;
      }
      out.throughPins = out.throughPins.size;
      const L = out.lat.slice().sort((a, b) => a - b), q = (p) => L.length ? L[Math.min(L.length - 1, Math.floor(L.length * p))] : null;
      out.latN = L.length; out.latMedMs = L.length ? Math.round(q(0.5) * 1000 / PM.fps) : null; out.latP90Ms = L.length ? Math.round(q(0.9) * 1000 / PM.fps) : null; out.latMeanMs = L.length ? Math.round(L.reduce((a, b) => a + b, 0) / L.length * 1000 / PM.fps) : null; out.lat0 = L.filter((v) => v === 0).length;
      for (const nm of ['latCov', 'latView']) { const A = out[nm].slice().sort((a, b) => a - b); out[nm] = A.length ? { n: A.length, med: Math.round(A[A.length >> 1] * 1000 / PM.fps), p90: Math.round(A[Math.min(A.length - 1, Math.floor(A.length * 0.9))] * 1000 / PM.fps), zero: A.filter((v) => v === 0).length } : null; }
      delete out.lat;
      out.shownOfClear = out.clearAll ? +(out.clearShown / out.clearAll).toFixed(3) : null;
      return out;
    },
  };
  // the placards' tips and whether each is shown now: every tether (a Line carrying pinSceneDepth, [x, y, z, x, top, z]) is
  // visible exactly when the page did not find its placard blocked, and the placard itself shows when its anchor is on screen
  const PV2 = new THREE.Matrix4(), V2 = new THREE.Vector3();
  window.__placardTips = () => {
    const o = [];
    PV2.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    scene.traverse((l) => {
      if (!l.isLine || !l.userData.pinSceneDepth || !l.parent) return;
      const p = l.geometry.attributes.position; if (!p || p.count !== 2) return;
      const x = p.getX(0), y = p.getY(0), z = p.getZ(0), top = p.getY(1);
      V2.set(x, y, z);
      const far = camera.position.distanceTo(V2) > 14000;
      V2.applyMatrix4(PV2);
      const on = !far && V2.z < 1 && V2.z > -1 && V2.x >= -1.1 && V2.x <= 1.1 && V2.y >= -1.2 && V2.y <= 1.2;
      o.push({ shown: l.visible && on, on, x, y: top + 3, z });
    });
    return o;
  };
  return { meshes: findMeshes(), sky: !!sky };
})()
