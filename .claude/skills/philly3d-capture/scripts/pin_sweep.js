// pin blink sweep (Round 143): turns the eye in place 0.02 rad a frame with 16 ms of real time per frame and counts
// pins that were shown on screen (aPinVis > 0.5, |ndc| < 0.95) and then vanished (< 0.1) while still on screen. From a
// fixed eye nothing can change what hides a pin, so every such vanishing is a blink. Inject as a string through
// javascript_tool, then: __pinSweep([[x, y, z, yaw0, yaw1], ...]). Keep one call to about two runs (45 s limit).
// Limits: it sees only the pins loaded in this session (live feeds differ between loads, so compare builds with
// several runs, not one pin), and the first 70 settle frames must pass real time or the half-second hold never lapses.
window.__pinSweep = function (runs, pitch) {
  const d = __dbg, cam = d.camera, V = new THREE.Vector3(), meshes = [];
  d.scene.traverse((o) => { if (o.isInstancedMesh && o.geometry.attributes.aPinVis) meshes.push(o); });
  const wait = () => { const t = performance.now(); while (performance.now() - t < 16) {} };
  const hist = new Map(); let blinks = 0, shown = 0;
  for (const [x, y, z, y0, y1] of runs) {
    d.goFly(x, y, z, y0, pitch ?? -0.12); for (let i = 0; i < 70; i++) { wait(); d.frameOnce(); }
    hist.clear();
    const n = Math.round(Math.abs(y1 - y0) / 0.02);
    for (let f = 0; f <= n; f++) {
      d.goFly(x, y, z, y0 + (y1 - y0) * f / n, pitch ?? -0.12); wait(); d.frameOnce();
      for (const m of meshes) {
        if (!m.visible) continue;
        const e = m.instanceMatrix.array, a = m.geometry.attributes.aPinVis.array;
        for (let i = 0; i < m.count; i++) {
          V.set(e[i * 16 + 12], e[i * 16 + 13], e[i * 16 + 14]);
          const k = m.uuid + Math.round(V.x) + ',' + Math.round(V.z);
          V.project(cam);
          const on = V.z < 1 && Math.abs(V.x) < 0.95 && Math.abs(V.y) < 0.95, h = hist.get(k) || { up: false };
          if (!on) h.up = false; else if (a[i] > 0.5) { if (!h.up) shown++; h.up = true; } else if (a[i] < 0.1 && h.up) { blinks++; h.up = false; }
          hist.set(k, h);
        }
      }
    }
  }
  return { blinks, shownOnScreen: shown };
};
'pin sweep ready';
