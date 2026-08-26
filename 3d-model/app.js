/* Society Hill Towers — interactive 3D model.
   Coordinate system: x = east, y = up, z = south, meters, origin at the towers' centroid. */
(function () {
  'use strict';

  // ---------------------------------------------------------------- config
  // Facade spec from published sources + photo measurement (see About panel):
  // 31 stories = tall lobby + 30 residential floors; egg-crate grid on a 6 ft
  // (1.83 m) module, windows taller than wide, grid floating on a colonnade.
  const TOWER = {
    height: 94.2,          // to roof parapet (CTBUH); OSM tags 89 m
    floors: 30,            // residential floors above the lobby
    lobbyH: 5.6,
    parapetH: 1.2,
    bayPitch: 1.83,        // structural module, m
    cornerW: 0.78,         // solid corner pier width per face
    mullionW: 0.42,        // vertical concrete member face width
    mullionD: 0.5,         // grid projection depth in front of the glass
    spandrelH: 0.72,       // horizontal concrete band height per floor
    glassInset: 0.45,      // glass recess behind the concrete face
    lobbyInset: 3.4,       // ground-floor glass recess behind the colonnade
    colSpacing: 3,         // lobby column every Nth grid line
    penthouseH: 3.1,
  };

  const COLORS = {
    concrete: 0xc8c3b2,    // warm buff exposed-aggregate concrete (photo-sampled)
    concreteDark: 0xaaa595,
    glass: 0x37343f,       // dark blue-gray: clear glass, dark interiors, anodized frames
    glassLobby: 0x2e2b35,
    ground: 0x8b8c78,     // block interiors read as yards/gardens from above
    plaza: 0x96604a,       // brick-paved plaza and circular drive
    asphalt: 0x3b3833,
    footway: 0x7c584a,     // society hill brick sidewalks
    park: 0x243818,        // grass — stored very deep: the legacy-color pipeline + ACES
    parkDark: 0x1d2c13,    // lift flat lawns ~2.5x at noon (cf. roads: 0x3b3833 -> light gray)
    water: 0x3d5560,
    pier: 0x8f8a7d,
    trunk: 0x5b4a38,
    bronze: 0x4d3b26,
    skyZenith: 0x4279c4,
    skyHorizon: 0xc8dcea,
    skyGround: 0xa9b3ba,   // below-horizon haze — from altitude the dome shows past the world's edge
    haze: 0xdfd4b8,
    sun: 0xffe9c4,
  };

  const LABEL_FADE = [540, 880];

  // ---------------------------------------------------------------- dom
  const canvas = document.getElementById('gl');
  const veil = document.getElementById('veil');
  const btnEnter = document.getElementById('btnEnter');
  const loadmsg = document.getElementById('loadmsg');
  const hintEl = document.getElementById('hint');
  const crosshair = document.getElementById('crosshair');
  const labelsRoot = document.getElementById('labels');
  const needle = document.getElementById('needle');
  const stick = document.getElementById('stick');
  const stickNub = stick.querySelector('.nub');
  window.addEventListener('error', (e) => {
    const lm = document.getElementById('loadmsg');
    if (lm && !window.__fatalShown) { window.__fatalShown = true; lm.textContent = 'Error: ' + ((e && e.message) || 'unknown'); }
  });
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const isTouch = window.matchMedia('(pointer: coarse)').matches;

  let renderer;
  try {
    // Log depth EVERYWHERE. The Aug-24 Safari standard-depth fallback was built
    // for the "hollow buildings" report, which round 4 proved was an earcut
    // cap-winding bug, not Safari — and standard depth over a 26 km far plane
    // quantizes the few-cm flat separations into heavy z-fight shimmer on
    // phones (every iPhone browser is Safari-engined). Keep ?logdepth=0 as an
    // escape hatch if a real per-fragment-depth defect ever surfaces.
    const qsDepth = /[?&]logdepth=(\d)/.exec(location.search);
    window.__useLogDepth = qsDepth ? qsDepth[1] === '1' : true;
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance', logarithmicDepthBuffer: window.__useLogDepth });
    if (!renderer.getContext()) throw new Error('no context');
  } catch (e) {
    document.getElementById('nogl').style.display = 'flex';
    veil.style.display = 'none';
    return;
  }
  const DPR_CAP = window.matchMedia('(pointer: coarse)').matches ? 1.5 : 1.75;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, DPR_CAP));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.06;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(COLORS.haze, 1250, 4200);

  const camera = new THREE.PerspectiveCamera(58, window.innerWidth / window.innerHeight, window.__useLogDepth ? 0.75 : 1.0, 26000);

  // flat surfaces are layered with generous gaps to keep the depth buffer honest
  const LAYER = { park: 0.06, plaza: 0.1, deck: 0.14, sidewalk: 0.16, road: 0.24, footway: 0.32, basin: 0.36, pool: 0.38 };

  // ---------------------------------------------------------------- helpers
  const V3 = THREE.Vector3;
  function hash01(n) { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); }
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function lerp(a, b, t) { return a + (b - a) * t; }

  function signedArea(pts) {
    let a = 0;
    for (let i = 0, n = pts.length; i < n; i++) {
      const p = pts[i], q = pts[(i + 1) % n];
      a += p[0] * q[1] - q[0] * p[1];
    }
    return a / 2;
  }
  function pointInPoly(x, y, pts) {
    let inside = false;
    for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      const xi = pts[i][0], yi = pts[i][1], xj = pts[j][0], yj = pts[j][1];
      if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }
  function polyCentroid(pts) {
    let x = 0, y = 0, a = 0;
    for (let i = 0, n = pts.length; i < n; i++) {
      const p = pts[i], q = pts[(i + 1) % n];
      const c = p[0] * q[1] - q[0] * p[1];
      a += c; x += (p[0] + q[0]) * c; y += (p[1] + q[1]) * c;
    }
    a *= 0.5;
    if (Math.abs(a) < 1e-6) return [pts[0][0], pts[0][1]];
    return [x / (6 * a), y / (6 * a)];
  }

  // shape plane: (sx, sy) = (x, -z); extruded +depth then rotateX(-90) -> world (x, h, z)
  function shapeFromPoly(poly, holes) {
    const pts = poly.map(p => new THREE.Vector2(p[0], -p[1]));
    if (THREE.ShapeUtils.area(pts) < 0) pts.reverse();
    const shape = new THREE.Shape(pts);
    if (holes) for (const h of holes) {
      const hp = h.map(p => new THREE.Vector2(p[0], -p[1]));
      if (THREE.ShapeUtils.area(hp) > 0) hp.reverse();
      shape.holes.push(new THREE.Path(hp));
    }
    return shape;
  }
  function extrudePoly(poly, holes, h, minH) {
    const geom = new THREE.ExtrudeGeometry(shapeFromPoly(poly, holes), {
      depth: h - (minH || 0), bevelEnabled: false, curveSegments: 1,
    });
    geom.rotateX(-Math.PI / 2);
    if (minH) geom.translate(0, minH, 0);
    return geom;
  }

  // Building volume built edge by edge so each facade carries its own coordinates
  // (aWallU along the wall, aWallL wall length, aWallH wall height): the facade
  // shader centers bays on every wall instead of slicing a world grid at corners.
  function buildingGeom(poly, holes, h, minH) {
    const base = minH || 0;
    const pos = [], nor = [], wu = [], wl = [], wh = [];
    const ring = (pts, outwardSign) => {
      const n = pts.length;
      for (let i = 0; i < n; i++) {
        const a = pts[i], b = pts[(i + 1) % n];
        const dx = b[0] - a[0], dz = b[1] - a[1];
        const L = Math.hypot(dx, dz);
        if (L < 0.05) continue;
        const nx = (dz / L) * outwardSign, nz = (-dx / L) * outwardSign;
        const A = [a[0], base, a[1]], B = [b[0], base, b[1]], C = [b[0], h, b[1]], Dd = [a[0], h, a[1]];
        const flip = ((-dz) * nx + dx * nz) < 0;
        const tri = (P, Q, R, uP, uQ, uR) => {
          pos.push(P[0], P[1], P[2], Q[0], Q[1], Q[2], R[0], R[1], R[2]);
          for (let k = 0; k < 3; k++) { nor.push(nx, 0, nz); wl.push(L); wh.push(h); }
          wu.push(uP, uQ, uR);
        };
        if (!flip) { tri(A, B, C, 0, L, L); tri(A, C, Dd, 0, L, 0); }
        else { tri(A, C, B, 0, L, L); tri(A, Dd, C, 0, 0, L); }
      }
    };
    const outerSign = signedArea(poly) > 0 ? 1 : -1;
    ring(poly, outerSign);
    if (holes) for (const hl of holes) if (hl.length >= 3) ring(hl, signedArea(hl) > 0 ? -1 : 1);
    // roof cap
    const cap = new THREE.ShapeGeometry(shapeFromPoly(poly, holes));
    cap.rotateX(-Math.PI / 2);
    cap.translate(0, h, 0);
    const cg = cap.index ? cap.toNonIndexed() : cap;
    const cp = cg.attributes.position.array, cn = cg.attributes.normal.array;
    for (let i = 0; i < cp.length; i += 3) { pos.push(cp[i], cp[i + 1], cp[i + 2]); nor.push(cn[i], cn[i + 1], cn[i + 2]); wu.push(0); wl.push(0); wh.push(h); }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
    g.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(nor), 3));
    g.setAttribute('aWallU', new THREE.BufferAttribute(new Float32Array(wu), 1));
    g.setAttribute('aWallL', new THREE.BufferAttribute(new Float32Array(wl), 1));
    g.setAttribute('aWallH', new THREE.BufferAttribute(new Float32Array(wh), 1));
    return g;
  }

  // merge many geometries into one, painting a flat color per part (with optional
  // ground-darkening to fake ambient occlusion at street level)
  function mergeColored(parts, ao) {
    let count = 0;
    const prepped = parts.map(p => {
      const g = p.geom.index ? p.geom.toNonIndexed() : p.geom;
      count += g.attributes.position.count;
      return { g, c: p.color };
    });
    const pos = new Float32Array(count * 3);
    const nor = new Float32Array(count * 3);
    const col = new Float32Array(count * 3);
    const sty = new Float32Array(count);
    const flh = new Float32Array(count);
    const wu = new Float32Array(count), wl = new Float32Array(count), wh = new Float32Array(count), bs = new Float32Array(count);
    let o = 0;
    const c = new THREE.Color();
    for (let pi = 0; pi < prepped.length; pi++) {
      const { g, c: color } = prepped[pi];
      const styleV = parts[pi].style || 0;
      const flhV = parts[pi].flh ? Math.round(parts[pi].flh * 10) : 0;
      const baseY = parts[pi].baseY || 0;
      const p = g.attributes.position.array;
      const n = g.attributes.normal.array;
      const vc = g.attributes.position.count;
      pos.set(p, o * 3); nor.set(n, o * 3);
      if (g.attributes.aWallU) { wu.set(g.attributes.aWallU.array, o); wl.set(g.attributes.aWallL.array, o); wh.set(g.attributes.aWallH.array, o); }
      for (let i = 0; i < vc; i++) {
        sty[o + i] = styleV;
        flh[o + i] = flhV;
        bs[o + i] = baseY;
        c.copy(color);
        if (ao) {
          const y = p[i * 3 + 1];
          const f = 0.72 + 0.28 * clamp((y - baseY) / 7, 0, 1);
          c.multiplyScalar(f);
        }
        col[(o + i) * 3] = c.r; col[(o + i) * 3 + 1] = c.g; col[(o + i) * 3 + 2] = c.b;
      }
      o += vc;
    }
    const out = new THREE.BufferGeometry();
    out.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    out.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
    out.setAttribute('color', new THREE.BufferAttribute(col, 3));
    out.setAttribute('aStyle', new THREE.BufferAttribute(sty, 1));
    out.setAttribute('aFloorH', new THREE.BufferAttribute(flh, 1));
    out.setAttribute('aWallU', new THREE.BufferAttribute(wu, 1));
    out.setAttribute('aWallL', new THREE.BufferAttribute(wl, 1));
    out.setAttribute('aWallH', new THREE.BufferAttribute(wh, 1));
    out.setAttribute('aBase', new THREE.BufferAttribute(bs, 1));
    return out;
  }

  function box(w, h, d, x, y, z, ry) {
    const g = new THREE.BoxGeometry(w, h, d);
    if (ry) g.rotateY(ry);
    g.translate(x, y, z);
    return g;
  }

  // drop near-collinear vertices from a ring (roof fitting)
  function simplifyRing(poly, tol) {
    const n = poly.length, out = [];
    for (let i = 0; i < n; i++) {
      const a = poly[(i - 1 + n) % n], b = poly[i], c = poly[(i + 1) % n];
      const dx = c[0] - a[0], dz = c[1] - a[1];
      const L = Math.hypot(dx, dz) || 1;
      if (Math.abs((b[0] - a[0]) * dz - (b[1] - a[1]) * dx) / L > tol) out.push(b);
    }
    return out.length >= 3 ? out : poly;
  }

  // horizontal filled polygon at height y (sampled-roof-color overlay caps).
  // earcut's triangles are canonically CCW in the shape plane - always emit forward.
  function capGeom(poly, holes, y) {
    const v2c = poly.map(p => new THREE.Vector2(p[0], -p[1]));
    const hvc = (holes || []).map(hl => hl.map(q => new THREE.Vector2(q[0], -q[1])));
    const tris = THREE.ShapeUtils.triangulateShape(v2c, hvc);
    const all = (holes && holes.length) ? poly.concat(...holes) : poly;
    const pos = new Float32Array(all.length * 3);
    for (let i = 0; i < all.length; i++) { pos[i * 3] = all[i][0]; pos[i * 3 + 1] = y; pos[i * 3 + 2] = all[i][1]; }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const idx = [];
    for (const t of tris) idx.push(t[0], t[1], t[2]);
    g.setIndex(idx);
    g.computeVertexNormals();
    return g;
  }

  // gable built on the footprint quad itself: eaves are the longer opposite-edge
  // pair, the ridge joins the other pair's midpoints — the roof meets the wall
  // at every vertex, no floating overhangs on skewed footprints
  function quadGable(quad, eaveH, ridgeH, ridgeRad) {
    const E = [0, 1, 2, 3].map(i => {
      const p = quad[i], q = quad[(i + 1) % 4];
      return { a: p, b: q, len: Math.hypot(q[0] - p[0], q[1] - p[1]) };
    });
    let usePair02 = E[0].len + E[2].len >= E[1].len + E[3].len;
    if (ridgeRad != null) {
      // LiDAR-measured ridge direction: eaves run parallel to the ridge, so pick
      // the edge pair axially closest to it (falls back to the longer pair above)
      const axd = (e) => {
        const a = Math.atan2(e.b[1] - e.a[1], e.b[0] - e.a[0]);
        const d = Math.abs((((a - ridgeRad) % Math.PI) + Math.PI) % Math.PI);
        return Math.min(d, Math.PI - d);
      };
      usePair02 = axd(E[0]) + axd(E[2]) <= axd(E[1]) + axd(E[3]);
    }
    const ev = usePair02 ? [E[0], E[2]] : [E[1], E[3]];
    const ge = usePair02 ? [E[1], E[3]] : [E[0], E[2]];
    const r0 = [(ge[0].a[0] + ge[0].b[0]) / 2, (ge[0].a[1] + ge[0].b[1]) / 2];
    const r1 = [(ge[1].a[0] + ge[1].b[0]) / 2, (ge[1].a[1] + ge[1].b[1]) / 2];
    const cx = (quad[0][0] + quad[1][0] + quad[2][0] + quad[3][0]) / 4;
    const cz = (quad[0][1] + quad[1][1] + quad[2][1] + quad[3][1]) / 4;
    const slopes = [], ends = [], endU = [];
    const pushTri = (arr, A, B, C) => arr.push(A[0], A[1], A[2], B[0], B[1], B[2], C[0], C[1], C[2]);
    const V = (p, y) => [p[0], y, p[1]];
    const slopeQuad = (ea, ridgeNear, ridgeFar) => {
      // ea runs a->b; the ridge end near ea.b is ridgeNear
      let A = V(ea.a, eaveH), B = V(ea.b, eaveH), R0 = V(ridgeNear, ridgeH), R1 = V(ridgeFar, ridgeH);
      const ny = (B[0] - A[0]) * (R0[2] - A[2]) - (B[2] - A[2]) * (R0[0] - A[0]);
      if (ny > 0) { const tmp = A; A = B; B = tmp; const t2 = R0; R0 = R1; R1 = t2; }
      pushTri(slopes, A, B, R0); pushTri(slopes, A, R0, R1);
    };
    // each eave edge's near ridge end is the midpoint of the ge edge SHARING its
    // b vertex — which pair that is depends on where the ring started (usePair02
    // false meant ev[0].b touches ge[1], and the old fixed r0/r1 order emitted a
    // bowtie: a see-through wedge + a coplanar double wedge on half the gables)
    const near0 = (ge[0].a === ev[0].b || ge[0].b === ev[0].b) ? r0 : r1;
    slopeQuad(ev[0], near0, near0 === r0 ? r1 : r0);
    const near1 = (ge[0].a === ev[1].b || ge[0].b === ev[1].b) ? r0 : r1;
    slopeQuad(ev[1], near1, near1 === r0 ? r1 : r0);
    const endTri = (g, r) => {
      let A = V(g.a, eaveH), B = V(g.b, eaveH);
      const R = V(r, ridgeH);
      const mx = (g.a[0] + g.b[0]) / 2 - cx, mz = (g.a[1] + g.b[1]) / 2 - cz;
      const nx = (B[2] - A[2]), nz = -(B[0] - A[0]); // normal of tri (A,B,R) in xz
      if (nx * mx + nz * mz < 0) { const tmp = A; A = B; B = tmp; }
      pushTri(ends, A, B, R);
      endU.push(0, g.len, g.len / 2);
    };
    endTri(ge[0], r0); endTri(ge[1], r1);
    const mk = (arr, isEnds, len) => {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(arr), 3));
      g.computeVertexNormals();
      if (isEnds) {
        const n = arr.length / 3;
        g.setAttribute('aWallU', new THREE.BufferAttribute(new Float32Array(endU), 1));
        g.setAttribute('aWallL', new THREE.BufferAttribute(new Float32Array(n).fill(len), 1));
        g.setAttribute('aWallH', new THREE.BufferAttribute(new Float32Array(n).fill(eaveH), 1));
      }
      return g;
    };
    return { slopes: mk(slopes), ends: mk(ends, true, (ge[0].len + ge[1].len) / 2), eaves: ev, ridge: [r0, r1] };
  }

  // hip roof on the footprint quad: like quadGable but the ridge is inset from both
  // ends and the end faces are sloped planes (roof material), not vertical walls.
  // Only used for LiDAR-measured hips — the guess lottery never emits one.
  function quadHip(quad, eaveH, ridgeH, ridgeRad) {
    const E = [0, 1, 2, 3].map(i => {
      const p = quad[i], q = quad[(i + 1) % 4];
      return { a: p, b: q, len: Math.hypot(q[0] - p[0], q[1] - p[1]) };
    });
    let usePair02 = E[0].len + E[2].len >= E[1].len + E[3].len;
    if (ridgeRad != null) {
      const axd = (e) => {
        const a = Math.atan2(e.b[1] - e.a[1], e.b[0] - e.a[0]);
        const d = Math.abs((((a - ridgeRad) % Math.PI) + Math.PI) % Math.PI);
        return Math.min(d, Math.PI - d);
      };
      usePair02 = axd(E[0]) + axd(E[2]) <= axd(E[1]) + axd(E[3]);
    }
    const ev = usePair02 ? [E[0], E[2]] : [E[1], E[3]];
    const ge = usePair02 ? [E[1], E[3]] : [E[0], E[2]];
    const r0 = [(ge[0].a[0] + ge[0].b[0]) / 2, (ge[0].a[1] + ge[0].b[1]) / 2];
    const r1 = [(ge[1].a[0] + ge[1].b[0]) / 2, (ge[1].a[1] + ge[1].b[1]) / 2];
    const rl = Math.hypot(r1[0] - r0[0], r1[1] - r0[1]) || 1;
    const rdx = (r1[0] - r0[0]) / rl, rdz = (r1[1] - r0[1]) / rl;
    const span = (ge[0].len + ge[1].len) / 2;
    const ins = Math.min(span / 2, rl * 0.38);
    const R0 = [r0[0] + rdx * ins, r0[1] + rdz * ins];
    const R1 = [r1[0] - rdx * ins, r1[1] - rdz * ins];
    const slopes = [];
    const pushTri = (A, B, C) => slopes.push(A[0], A[1], A[2], B[0], B[1], B[2], C[0], C[1], C[2]);
    const V = (p, y) => [p[0], y, p[1]];
    const slopeQuad = (ea, ridgeNear, ridgeFar) => {
      let A = V(ea.a, eaveH), B = V(ea.b, eaveH), Q0 = V(ridgeNear, ridgeH), Q1 = V(ridgeFar, ridgeH);
      const ny = (B[0] - A[0]) * (Q0[2] - A[2]) - (B[2] - A[2]) * (Q0[0] - A[0]);
      if (ny > 0) { const t = A; A = B; B = t; const t2 = Q0; Q0 = Q1; Q1 = t2; }
      pushTri(A, B, Q0); pushTri(A, Q0, Q1);
    };
    const hn0 = (ge[0].a === ev[0].b || ge[0].b === ev[0].b) ? R0 : R1;
    slopeQuad(ev[0], hn0, hn0 === R0 ? R1 : R0);
    const hn1 = (ge[0].a === ev[1].b || ge[0].b === ev[1].b) ? R0 : R1;
    slopeQuad(ev[1], hn1, hn1 === R0 ? R1 : R0);
    const endTri = (g, r) => {
      let A = V(g.a, eaveH), B = V(g.b, eaveH);
      const R = V(r, ridgeH);
      const ny = (B[0] - A[0]) * (R[2] - A[2]) - (B[2] - A[2]) * (R[0] - A[0]);
      if (ny > 0) { const t = A; A = B; B = t; }
      pushTri(A, B, R);
    };
    endTri(ge[0], R0); endTri(ge[1], R1);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(slopes), 3));
    g.computeVertexNormals();
    return { slopes: g, ends: null, eaves: [ev[0], ev[1], ge[0], ge[1]], ridge: [R0, R1] };
  }

  // minimum-area oriented bounding box (aligned with some polygon edge)
  function orientedBox(poly) {
    let best = null;
    for (let i = 0; i < poly.length; i++) {
      const p = poly[i], q = poly[(i + 1) % poly.length];
      const ex = q[0] - p[0], ez = q[1] - p[1];
      const L = Math.hypot(ex, ez);
      if (L < 0.3) continue;
      const ux = ex / L, uz = ez / L;
      let minU = 1e9, maxU = -1e9, minV = 1e9, maxV = -1e9;
      for (const t of poly) {
        const u = t[0] * ux + t[1] * uz, v = -t[0] * uz + t[1] * ux;
        if (u < minU) minU = u; if (u > maxU) maxU = u;
        if (v < minV) minV = v; if (v > maxV) maxV = v;
      }
      const area = (maxU - minU) * (maxV - minV);
      if (!best || area < best.area) best = { area, ux, uz, minU, maxU, minV, maxV };
    }
    if (!best) return null;
    const cu = (best.minU + best.maxU) / 2, cv = (best.minV + best.maxV) / 2;
    return {
      cx: best.ux * cu - best.uz * cv,
      cz: best.uz * cu + best.ux * cv,
      ux: best.ux, uz: best.uz,
      w: best.maxU - best.minU, d: best.maxV - best.minV,
      fill: 0, area: best.area,
    };
  }

  // hip roof over an OBB: ridge along the long axis, shortened at both ends
  function hipGeom(ob, eaveH, ridgeH, overhang) {
    const long = Math.max(ob.w, ob.d), span = Math.min(ob.w, ob.d);
    let ax = ob.ux, az = ob.uz;
    if (ob.d > ob.w) { ax = -ob.uz; az = ob.ux; }
    const px = az, pz = -ax; // right-handed with y-up regardless of source winding
    const hl = long / 2 + (overhang || 0.3), hs = span / 2 + (overhang || 0.3);
    const hr = Math.max(0.5, hl - hs); // ridge half-length
    const P = (u, v, y) => [ob.cx + ax * u + px * v, y, ob.cz + az * u + pz * v];
    const A = P(-hl, -hs, eaveH), B = P(hl, -hs, eaveH), C = P(hl, hs, eaveH), D = P(-hl, hs, eaveH);
    const R1 = P(-hr, 0, ridgeH), R2 = P(hr, 0, ridgeH);
    const pos = [];
    const tri = (a, b, c) => { pos.push(a[0], a[1], a[2], b[0], b[1], b[2], c[0], c[1], c[2]); };
    tri(A, B, R2); tri(A, R2, R1);  // long slope v<0
    tri(C, D, R1); tri(C, R1, R2);  // long slope v>0
    tri(D, A, R1);                   // hip end u<0
    tri(B, C, R2);                   // hip end u>0
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
    g.computeVertexNormals();
    return g;
  }

  // classical column row: n cylinders from (x0,z0) to (x1,z1). Shafts run 2.2 m
  // below grade like walls and tree trunks — colonnades are lifted by the height
  // at the building CENTROID, and sloping ground was leaving columns airborne
  // (the Second Bank's south portico floated above the falling lawn).
  function columnRow(x0, z0, x1, z1, n, h, r, yBase) {
    const geoms = [];
    const sink = 2.2;
    for (let i = 0; i < n; i++) {
      const t = n === 1 ? 0.5 : i / (n - 1);
      const g = new THREE.CylinderGeometry(r * 0.88, r, h + sink, 10);
      g.translate(x0 + (x1 - x0) * t, (yBase || 0) - sink + (h + sink) / 2, z0 + (z1 - z0) * t);
      geoms.push(g);
    }
    return geoms;
  }

  // cupola: square or round base stage + louvered drum + cap
  function cupolaGeoms(cx, cz, yBase, size, tall) {
    const g1 = new THREE.BoxGeometry(size, tall * 0.32, size);
    g1.translate(cx, yBase + tall * 0.16, cz);
    const g2 = new THREE.CylinderGeometry(size * 0.34, size * 0.38, tall * 0.42, 8);
    g2.translate(cx, yBase + tall * 0.32 + tall * 0.21, cz);
    const g3 = new THREE.ConeGeometry(size * 0.42, tall * 0.26, 10);
    g3.translate(cx, yBase + tall * 0.74 + tall * 0.13, cz);
    return [g1, g2, g3];
  }

  // point on an OBB long axis end (dir = world direction to prefer), and face info
  function obbAxis(ob) {
    let ax = ob.ux, az = ob.uz;
    if (ob.d > ob.w) { ax = -ob.uz; az = ob.ux; }
    return { ax, az, px: az, pz: -ax, hl: Math.max(ob.w, ob.d) / 2, hs: Math.min(ob.w, ob.d) / 2 };
  }
  function obbEnd(ob, dirX, dirZ) {
    const a = obbAxis(ob);
    const s = (a.ax * dirX + a.az * dirZ) >= 0 ? 1 : -1;
    return { x: ob.cx + a.ax * a.hl * s, z: ob.cz + a.az * a.hl * s, ax: a.ax * s, az: a.az * s, a };
  }

  // gable roof prism over an OBB: two slopes meeting at a ridge along the long
  // axis, vertical gable-end triangles. Returns non-indexed geometry.
  function gableGeom(ob, eaveH, ridgeH, overhang, endOverhang) {
    const long = Math.max(ob.w, ob.d), span = Math.min(ob.w, ob.d);
    // ridge axis unit vector = OBB long axis
    let ax = ob.ux, az = ob.uz;
    if (ob.d > ob.w) { ax = -ob.uz; az = ob.ux; }
    const px = az, pz = -ax; // right-handed with y-up regardless of source winding
    // gable ends sit flush on the wall plane; only the eaves overhang
    const hl = long / 2 + (endOverhang || 0), hs = span / 2 + (overhang || 0.3);
    const P = (u, v, y) => [ob.cx + ax * u + px * v, y, ob.cz + az * u + pz * v];
    const A = P(-hl, -hs, eaveH), B = P(hl, -hs, eaveH), C = P(hl, hs, eaveH), D = P(-hl, hs, eaveH);
    const R1 = P(-hl, 0, ridgeH), R2 = P(hl, 0, ridgeH);
    const slopes = [], ends = [], endU = [];
    const tri = (arr) => (a, b, c) => { arr.push(a[0], a[1], a[2], b[0], b[1], b[2], c[0], c[1], c[2]); };
    const st = tri(slopes), et = tri(ends);
    st(A, B, R2); st(A, R2, R1);   // slope on the v<0 side
    st(C, D, R1); st(C, R1, R2);   // slope on the v>0 side
    et(D, A, R1); endU.push(0, hs * 2, hs);  // gable end at u=-hl (outward -u)
    et(B, C, R2); endU.push(0, hs * 2, hs);  // gable end at u=+hl (outward +u)
    const mk = (arr, ends) => {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(arr), 3));
      g.computeVertexNormals();
      if (ends) {
        const n = arr.length / 3;
        g.setAttribute('aWallU', new THREE.BufferAttribute(new Float32Array(endU), 1));
        g.setAttribute('aWallL', new THREE.BufferAttribute(new Float32Array(n).fill(hs * 2), 1));
        g.setAttribute('aWallH', new THREE.BufferAttribute(new Float32Array(n).fill(eaveH), 1));
      }
      return g;
    };
    return { slopes: mk(slopes), ends: mk(ends, true), ax, az, px, pz, hl, hs };
  }

  // flat road ribbon with round joints
  function ribbon(pts, w, y, yFn) {
    pts = densify(pts, 10);
    // deterministic few-cm lift so no two ribbons are ever exactly coplanar
    y += hash01(pts[0][0] * 0.13 + pts[0][1] * 0.71) * 0.06;
    const hw = w / 2;
    const tris = [];
    const ys = pts.map(p => y + (yFn ? yFn(p[0], p[1]) : siteY(p[0], p[1], 'road')));
    for (let i = 0; i < pts.length - 1; i++) {
      const ax = pts[i][0], az = pts[i][1], bx = pts[i + 1][0], bz = pts[i + 1][1];
      let dx = bx - ax, dz = bz - az;
      const len = Math.hypot(dx, dz);
      if (len < 0.01) continue;
      dx /= len; dz /= len;
      const px = -dz * hw, pz = dx * hw;
      const ya = ys[i], yb = ys[i + 1];
      tris.push(ax + px, ya, az + pz, bx + px, yb, bz + pz, bx - px, yb, bz - pz);
      tris.push(ax + px, ya, az + pz, bx - px, yb, bz - pz, ax - px, ya, az - pz);
    }
    for (let i = 0; i < pts.length; i++) {
      const cx = pts[i][0], cz = pts[i][1], yc = ys[i];
      const S = 8;
      for (let k = 0; k < S; k++) {
        const a0 = (k / S) * Math.PI * 2, a1 = ((k + 1) / S) * Math.PI * 2;
        tris.push(cx, yc, cz,
          cx + Math.cos(a1) * hw, yc, cz + Math.sin(a1) * hw,
          cx + Math.cos(a0) * hw, yc, cz + Math.sin(a0) * hw);
      }
    }
    const g = new THREE.BufferGeometry();
    const arr = new Float32Array(tris);
    g.setAttribute('position', new THREE.BufferAttribute(arr, 3));
    const n = new Float32Array(arr.length);
    for (let i = 0; i < n.length; i += 3) { n[i] = 0; n[i + 1] = 1; n[i + 2] = 0; }
    g.setAttribute('normal', new THREE.BufferAttribute(n, 3));
    return g;
  }
  // streets follow the terrain: add a vertex every `step` meters
  function densify(pts, step) {
    const out = [pts[0]];
    for (let i = 0; i < pts.length - 1; i++) {
      const a = pts[i], b = pts[i + 1];
      const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const k = Math.max(1, Math.ceil(L / step));
      for (let j = 1; j <= k; j++) out.push([a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k]);
    }
    return out;
  }

  // Bowyer-Watson Delaunay on [x,z] points -> triangles of indices
  function delaunay(P) {
    const n = P.length;
    let minX = Infinity, minZ = Infinity, maxX = -Infinity, maxZ = -Infinity;
    for (const q of P) { minX = Math.min(minX, q[0]); maxX = Math.max(maxX, q[0]); minZ = Math.min(minZ, q[1]); maxZ = Math.max(maxZ, q[1]); }
    const dm = Math.max(maxX - minX, maxZ - minZ) * 3 + 10, mx = (minX + maxX) / 2, mz = (minZ + maxZ) / 2;
    const pts = P.concat([[mx - dm * 2, mz - dm], [mx, mz + dm * 2], [mx + dm * 2, mz - dm]]);
    const circ = (ia, ib, ic) => {
      const ax = pts[ia][0], az = pts[ia][1], bx = pts[ib][0], bz = pts[ib][1], cx = pts[ic][0], cz = pts[ic][1];
      const d = 2 * (ax * (bz - cz) + bx * (cz - az) + cx * (az - bz));
      if (Math.abs(d) < 1e-9) return null;
      const a2 = ax * ax + az * az, b2 = bx * bx + bz * bz, c2 = cx * cx + cz * cz;
      const ux = (a2 * (bz - cz) + b2 * (cz - az) + c2 * (az - bz)) / d;
      const uz = (a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)) / d;
      return { x: ux, z: uz, r2: (ax - ux) * (ax - ux) + (az - uz) * (az - uz) };
    };
    let tris = [{ a: n, b: n + 1, c: n + 2, cc: circ(n, n + 1, n + 2) }];
    const key = (u, v) => u < v ? u * 1048576 + v : v * 1048576 + u;
    for (let i = 0; i < n; i++) {
      const px = pts[i][0], pz = pts[i][1];
      const bad = [], keep = [];
      for (const tr of tris) {
        if (tr.cc && (px - tr.cc.x) * (px - tr.cc.x) + (pz - tr.cc.z) * (pz - tr.cc.z) <= tr.cc.r2) bad.push(tr); else keep.push(tr);
      }
      const count = new Map();
      for (const tr of bad) for (const e of [[tr.a, tr.b], [tr.b, tr.c], [tr.c, tr.a]]) { const k = key(e[0], e[1]); count.set(k, (count.get(k) || 0) + 1); }
      for (const tr of bad) for (const e of [[tr.a, tr.b], [tr.b, tr.c], [tr.c, tr.a]]) {
        if (count.get(key(e[0], e[1])) === 1) keep.push({ a: e[0], b: e[1], c: i, cc: circ(e[0], e[1], i) });
      }
      tris = keep;
    }
    return tris.filter(tr => tr.a < n && tr.b < n && tr.c < n).map(tr => [tr.a, tr.b, tr.c]);
  }

  // a flat polygon draped over the terrain: densified boundary + interior points, triangulated
  function drapedPoly(poly, yOff, spacing) {
    const area = Math.abs(signedArea(poly));
    spacing = Math.max(spacing, Math.sqrt(area / 420));
    const pts = [];
    const n = poly.length;
    for (let i = 0; i < n; i++) {
      const a = poly[i], b = poly[(i + 1) % n];
      const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const k = Math.max(1, Math.ceil(L / spacing));
      for (let j = 0; j < k; j++) pts.push([a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k]);
    }
    let x0 = Infinity, z0 = Infinity, x1 = -Infinity, z1 = -Infinity;
    for (const q of poly) { x0 = Math.min(x0, q[0]); x1 = Math.max(x1, q[0]); z0 = Math.min(z0, q[1]); z1 = Math.max(z1, q[1]); }
    const edgeDist = (x, z) => {
      let best = Infinity;
      for (let i = 0; i < n; i++) {
        const a = poly[i], b = poly[(i + 1) % n];
        const dx = b[0] - a[0], dz = b[1] - a[1], L2 = dx * dx + dz * dz;
        let tt = L2 > 0 ? ((x - a[0]) * dx + (z - a[1]) * dz) / L2 : 0; tt = clamp(tt, 0, 1);
        const ex = a[0] + dx * tt - x, ez = a[1] + dz * tt - z;
        best = Math.min(best, ex * ex + ez * ez);
      }
      return Math.sqrt(best);
    };
    for (let x = x0 + spacing * 0.5; x < x1; x += spacing) for (let z = z0 + spacing * 0.5; z < z1; z += spacing) {
      const px = x + (hash01(x * 0.37 + z * 1.91) - 0.5) * spacing * 0.4, pz = z + (hash01(x * 1.13 + z * 0.71) - 0.5) * spacing * 0.4;
      if (pointInPoly(px, pz, poly) && edgeDist(px, pz) > spacing * 0.3) pts.push([px, pz]);
    }
    const tris = delaunay(pts);
    const pos = [];
    const ys = pts.map(q => siteY(q[0], q[1], 'ground') + yOff);
    for (const [ia, ib, ic] of tris) {
      const A = pts[ia], B = pts[ib], C = pts[ic];
      if (!pointInPoly((A[0] + B[0] + C[0]) / 3, (A[1] + B[1] + C[1]) / 3, poly)) continue;
      // orient so the normal points up (+y): in xz, (B-A)x(C-A) must be negative for a right-handed y-up frame
      const cr = (B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0]);
      const [P1, y1, P2, y2] = cr < 0 ? [B, ys[ib], C, ys[ic]] : [C, ys[ic], B, ys[ib]];
      pos.push(A[0], ys[ia], A[1], P1[0], y1, P1[1], P2[0], y2, P2[1]);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
    g.computeVertexNormals();
    return g;
  }

  function offsetPolyline(pts, d) {
    const out = [];
    for (let i = 0; i < pts.length; i++) {
      const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[Math.min(pts.length - 1, i + 1)];
      const dx = p2[0] - p0[0], dz = p2[1] - p0[1];
      const L = Math.hypot(dx, dz) || 1;
      out.push([p1[0] - (dz / L) * d, p1[1] + (dx / L) * d]);
    }
    return out;
  }

  function flatPoly(poly, holes, y, noTerrain) {
    const g = new THREE.ShapeGeometry(shapeFromPoly(poly, holes));
    g.rotateX(-Math.PI / 2);
    g.translate(0, y, 0);
    if (!noTerrain) {
      const pa = g.attributes.position;
      for (let i = 0; i < pa.count; i++) pa.setY(i, pa.getY(i) + siteY(pa.getX(i), pa.getZ(i), 'ground'));
    }
    return g;
  }

  // ---------------------------------------------------------------- lighting & sky
  const hemi = new THREE.HemisphereLight(0xd3deea, 0x8f8166, 0.55);
  scene.add(hemi);
  const sunDir = new V3(-0.62, 0.5, 0.27).normalize(); // replaced each frame by the solar clock
  let lastAim = { cx: -120, cz: 0, extent: 640 };
  const sun = new THREE.DirectionalLight(COLORS.sun, 1.58);
  sun.castShadow = true;
  const SHADOW_RES = window.matchMedia('(pointer: coarse)').matches ? 2048 : 4096;
  sun.shadow.mapSize.set(SHADOW_RES, SHADOW_RES);
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 1.4;
  sun.shadow.camera.near = 100;
  sun.shadow.camera.far = 2600;
  scene.add(sun);
  scene.add(sun.target);

  function aimSun(cx, cz, extent) {
    lastAim = { cx, cz, extent };
    const c = sun.shadow.camera;
    const texel = (extent * 2) / SHADOW_RES;
    cx = Math.round(cx / (texel * 8)) * texel * 8;
    cz = Math.round(cz / (texel * 8)) * texel * 8;
    sun.position.set(cx + sunDir.x * 1200, sunDir.y * 1200, cz + sunDir.z * 1200);
    sun.target.position.set(cx, 0, cz);
    c.left = -extent; c.right = extent; c.top = extent; c.bottom = -extent;
    c.updateProjectionMatrix();
  }
  aimSun(-1450, -700, 800);

  const WX = { cover: 0.22, ok: false };            // live-weather state (see applyWx below)
  const wxWind = new THREE.Vector2(0.0012, 0.0005);
  const skyMat = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
    uniforms: {
      cZenith: { value: new THREE.Color(COLORS.skyZenith) },
      cHorizon: { value: new THREE.Color(COLORS.skyHorizon) },
      cGround: { value: new THREE.Color(COLORS.skyGround) },
      uSun: { value: sunDir.clone() },
      cSun: { value: new THREE.Color(COLORS.sun) },
      uCloud: { value: 0.22 },
      uCloudLight: { value: 1.0 },
      uCloudOff: { value: new THREE.Vector2(0, 0) },
      uMoon: { value: new THREE.Vector3(0, -1, 0) },
      uMoonU: { value: new THREE.Vector3(1, 0, 0) },
      uMoonV: { value: new THREE.Vector3(0, 0, 1) },
      uMoonK: { value: 0.5 },
      uMoonI: { value: 0 },
    },
    vertexShader:
      'varying vec3 vDir;\n' +
      'void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); gl_Position.z = gl_Position.w; }',
    fragmentShader:
      'varying vec3 vDir; uniform vec3 cZenith, cHorizon, cGround, uSun, cSun;\n' +
      'uniform float uCloud, uCloudLight; uniform vec2 uCloudOff;\n' +
      'uniform vec3 uMoon, uMoonU, uMoonV; uniform float uMoonK, uMoonI;\n' +
      'float chash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }\n' +
      'float cnoise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);\n' +
      '  return mix(mix(chash(i), chash(i+vec2(1.,0.)), f.x), mix(chash(i+vec2(0.,1.)), chash(i+vec2(1.,1.)), f.x), f.y); }\n' +
      'void main(){\n' +
      // normalize per fragment: the dome is coarse (32x18) and interpolated vDir
      // shrinks inside triangles, which smeared the old pow-based glow into a
      // vertical streak along the sun meridian. A round disc + radial halo on the
      // true angle reads like the actual sun.
      '  vec3 nd = normalize(vDir);\n' +
      '  float h = nd.y;\n' +
      '  vec3 col = h >= 0.0 ? mix(cHorizon, cZenith, pow(h, 0.52)) : mix(cHorizon, cGround, clamp(-h*1.5,0.,1.));\n' +
      '  float s = clamp(dot(nd, uSun), 0.0, 1.0);\n' +
      '  float sunAng = acos(s);\n' +
      '  float disc = 1.0 - smoothstep(0.0085, 0.0118, sunAng);\n' +
      '  col += cSun * (disc * 1.7 + exp(-sunAng * sunAng * 95.0) * 0.24 + pow(s, 12.0) * 0.10);\n' +
      // the Moon: a phased disc on the per-fragment normalized direction (nd,
      // never vDir — the coarse dome smears interpolated math, the sun lesson).
      // The terminator ellipse comes straight from the illuminated fraction; its
      // orientation from the world-space sun and moon vectors via uMoonU.
      '  if (uMoonI > 0.002) {\n' +
      '    float mAng = acos(clamp(dot(nd, uMoon), -1.0, 1.0));\n' +
      '    if (mAng < 0.06) {\n' +
      '      float mu = dot(nd, uMoonU) / 0.0091;\n' +
      '      float mv = dot(nd, uMoonV) / 0.0091;\n' +
      '      float mr = sqrt(mu * mu + mv * mv);\n' +
      '      float inD = 1.0 - smoothstep(0.93, 1.06, mr);\n' +
      '      float lim = sqrt(max(0.0, 1.0 - mv * mv));\n' +
      '      float ut = -(2.0 * uMoonK - 1.0) * lim;\n' +
      '      float lit = smoothstep(ut - 0.12, ut + 0.12, mu);\n' +
      '      vec3 mc = vec3(0.93, 0.94, 0.90);\n' +
      '      col = mix(col, mc * (0.11 + 0.89 * lit), inD * uMoonI);\n' +
      '    }\n' +
      '    col += vec3(0.93, 0.94, 0.90) * exp(-mAng * mAng * 2600.0) * 0.10 * uMoonI * uMoonK;\n' +
      '  }\n' +
      '  if (h > 0.01 && uCloud > 0.003) {\n' +
      '    vec2 cp = nd.xz / (h + 0.18) * 1.7 + uCloudOff;\n' +
      '    float d = cnoise(cp) * 0.55 + cnoise(cp * 2.7 + 13.1) * 0.30 + cnoise(cp * 7.3 + 41.7) * 0.15;\n' +
      '    float cov = clamp(uCloud, 0.0, 1.0);\n' +
      '    float m = smoothstep(1.0 - cov * 0.88 - 0.06, min(1.0, 1.06 - cov * 0.5), d);\n' +
      '    float horiz = smoothstep(0.02, 0.15, h);\n' +
      '    vec3 cc = mix(vec3(0.985, 0.99, 1.0), vec3(0.60, 0.64, 0.70), cov * 0.8) * uCloudLight;\n' +
      '    col = mix(col, cc, m * horiz * 0.92);\n' +
      '  }\n' +
      '  gl_FragColor = vec4(col, 1.0);\n' +
      '}',
  });
  const sky = new THREE.Mesh(new THREE.SphereGeometry(5200, 32, 18), skyMat);
  sky.frustumCulled = false;
  scene.add(sky);

  // environment map for glass: sky gradient + sun glare + dark ground and
  // building silhouettes so reflections have structure; refreshed as the sun moves
  const envScene = new THREE.Scene();
  const envSky = new THREE.Mesh(new THREE.SphereGeometry(50, 16, 10), skyMat.clone());
  envScene.add(envSky);
  const envGround = new THREE.Mesh(new THREE.CircleGeometry(45, 16), new THREE.MeshBasicMaterial({ color: COLORS.skyGround }));
  envGround.rotation.x = -Math.PI / 2; envGround.position.y = -4;
  envScene.add(envGround);
  const envSun = new THREE.Mesh(new THREE.SphereGeometry(3.5, 10, 8), new THREE.MeshBasicMaterial({ color: 0xfff2d8 }));
  envScene.add(envSun);
  {
    const bm = new THREE.MeshBasicMaterial({ color: 0x23262c });
    for (let k = 0; k < 9; k++) {
      const ang = k * 0.7 + 0.3;
      const bx = new THREE.Mesh(new THREE.BoxGeometry(4 + (k % 3) * 3, 6 + (k * 7) % 18, 4), bm);
      bx.position.set(Math.cos(ang) * 28, bx.geometry.parameters.height / 2 - 4, Math.sin(ang) * 28);
      envScene.add(bx);
    }
  }
  const pmremGen = new THREE.PMREMGenerator(renderer);
  let envRT = null;
  function refreshEnv() {
    for (const k of ['cZenith', 'cHorizon', 'cGround', 'cSun']) envSky.material.uniforms[k].value.copy(skyMat.uniforms[k].value);
    envSky.material.uniforms.uSun.value.copy(skyMat.uniforms.uSun.value);
    envSky.material.uniforms.uCloud.value = skyMat.uniforms.uCloud.value;
    envSky.material.uniforms.uCloudLight.value = skyMat.uniforms.uCloudLight.value;
    envSky.material.uniforms.uCloudOff.value.copy(skyMat.uniforms.uCloudOff.value);
    // the env sun ball must dim with cloud cover or overcast glass keeps a clear-sky hotspot
    envSun.material.color.set(0xfff2d8).multiplyScalar(1 - 0.65 * WX.cover);
    envGround.material.color.copy(skyMat.uniforms.cGround.value);
    envSun.position.copy(skyMat.uniforms.uSun.value).multiplyScalar(44);
    const rt = pmremGen.fromScene(envScene, 0.05);
    scene.environment = rt.texture;
    if (envRT) envRT.dispose();
    envRT = rt;
  }
  refreshEnv();

  // ---------------------------------------------------------------- data-driven build
  const D = SCENE_DATA;
  const META_L = (META && META.landmarks && META.landmarks.landmarks) || (META && META.landmarks) || [];
  const towers = D.towers || [];
  const towersCenter = new V3(0, 0, 0);
  if (towers.length) {
    const cs = new V3();
    for (const t of towers) cs.add(new V3(t.centroid[0], 0, t.centroid[1]));
    towersCenter.copy(cs.multiplyScalar(1 / towers.length));
  }

  const bounds = { minX: 1e9, maxX: -1e9, minZ: 1e9, maxZ: -1e9 };
  for (const b of D.buildings) for (const p of b.poly) {
    if (p[0] < bounds.minX) bounds.minX = p[0];
    if (p[0] > bounds.maxX) bounds.maxX = p[0];
    if (p[1] < bounds.minZ) bounds.minZ = p[1];
    if (p[1] > bounds.maxZ) bounds.maxZ = p[1];
  }

  // waterfront: the Delaware's edge runs diagonally here. Fit a line along
  // Columbus Blvd; water lies ~90m east (normal side) of it.
  const wl = { px: 380, pz: 0, dx: 0, dz: 1, nx: 1, nz: 0, off: 92 };
  {
    const pts = [];
    for (const r of D.roads) if (r.name && /columbus/i.test(r.name)) for (const p of r.pts) pts.push(p);
    if (pts.length > 3) {
      let mx = 0, mz = 0;
      for (const p of pts) { mx += p[0]; mz += p[1]; }
      mx /= pts.length; mz /= pts.length;
      let sxx = 0, sxz = 0, szz = 0;
      for (const p of pts) { const ax = p[0] - mx, az = p[1] - mz; sxx += ax * ax; sxz += ax * az; szz += az * az; }
      const ang = 0.5 * Math.atan2(2 * sxz, sxx - szz);
      wl.px = mx; wl.pz = mz;
      wl.dx = Math.cos(ang); wl.dz = Math.sin(ang);
      if (wl.dz < 0) { wl.dx = -wl.dx; wl.dz = -wl.dz; } // along-shore direction runs south
      wl.nx = -wl.dz; wl.nz = wl.dx;
      if (wl.nx < 0) { wl.nx = -wl.nx; wl.nz = -wl.nz; }
    }
  }
  // signed distance east of the waterline; > 0 means in the river
  function inWater(x, z) { return x - xShore(z); }
  // rough Delaware west-bank polyline for the whole city (meets SHORE at the core ends):
  // east of it low terrain is river (dives to the bed); west of it low terrain is
  // made-land and clamps just above the water plane instead of flooding
  const DEL_BANK = [[13500, -21700], [10500, -18500], [7300, -14500], [4300, -10500], [2500, -7200], [1500, -4480], [900, -2600], [450, -1500], [404, -520], [345, 850], [700, 2200], [1300, 3600], [2000, 4800], [2600, 6400], [3400, 7600], [5200, 9700]];
  function delawareX(z) {
    for (let i = 0; i < DEL_BANK.length - 1; i++) {
      const a = DEL_BANK[i], b = DEL_BANK[i + 1];
      if (z >= a[1] && z <= b[1]) { const t = (z - a[1]) / Math.max(1e-6, b[1] - a[1]); return a[0] + (b[0] - a[0]) * t; }
    }
    return z < DEL_BANK[0][1] ? DEL_BANK[0][0] : DEL_BANK[DEL_BANK.length - 1][0];
  }
  function eastOfDelaware(x, z) { return x > delawareX(z) - 120; }
  // rough Schuylkill centerline; within 260 m counts as its corridor (bridge territory)
  const SCHUYLKILL = [[-8500, -11500], [-7700, -9400], [-6900, -7700], [-5600, -5300], [-4700, -3300], [-4100, -1600], [-4300, -400], [-4500, 1100], [-4200, 2600], [-3900, 4200], [-3700, 5600], [-3860, 7240]];
  function nearSchuylkill(x, z) {
    for (let i = 0; i < SCHUYLKILL.length - 1; i++) {
      const a = SCHUYLKILL[i], b = SCHUYLKILL[i + 1];
      const dx = b[0] - a[0], dz = b[1] - a[1];
      const L2 = dx * dx + dz * dz;
      let t = L2 > 0 ? ((x - a[0]) * dx + (z - a[1]) * dz) / L2 : 0;
      t = clamp(t, 0, 1);
      const px = x - (a[0] + dx * t), pz = z - (a[1] + dz * t);
      if (px * px + pz * pz < 260 * 260) return true;
    }
    return false;
  }
  function riverCorridor(x, z) { return eastOfDelaware(x, z) || nearSchuylkill(x, z); }
  // Walt Whitman crossing corridor: the custom suspension deck owns this stretch of
  // water — packed motorway segments here rendered as a second, disjointed bridge.
  // Distance to the raw OSM alignment (only ever consulted for deck-lifted river
  // segments, so the on-land approaches keep their real ramps).
  function wwbNear(x, z, r) {
    if (typeof WWB_PTS === 'undefined' || !WWB_PTS || WWB_PTS.length < 4) return false;
    r = r || 85;
    let best = Infinity;
    for (let i = 1; i < WWB_PTS.length; i++) {
      const A = WWB_PTS[i - 1], B = WWB_PTS[i];
      const dx = B[0] - A[0], dz = B[1] - A[1], L2 = dx * dx + dz * dz || 1e-9;
      const tt = clamp(((x - A[0]) * dx + (z - A[1]) * dz) / L2, 0, 1);
      const ex = A[0] + dx * tt - x, ez = A[1] + dz * tt - z;
      const d2 = ex * ex + ez * ez;
      if (d2 < best) best = d2;
    }
    return best < r * r;
  }

  // ---------------------------------------------------------------- overpasses
  // Baked by bake_overpasses.py from the raw OSM bridge/viaduct/layer/tunnel tags
  // (the packed road formats carry none of them). el = elevated chains with a
  // solved height profile, sk = sunken expressway carriageways, cor = the open-cut
  // corridor runs of the Vine Street Expressway [[x, z, floorY, halfW], ...].
  const OVP = (typeof OVERPASSES !== 'undefined' && OVERPASSES) ? OVERPASSES : { el: [], sk: [], cor: [] };
  const ovpGrid = new Map();
  const OVP_CELL = 28;
  const ovpSegs = [];   // ax, az, bx, bz, ya, yb, hw, cls, chainId (stride 9; cls -1 open cut, -2 covered)
  const OVP_STRIDE = 9;
  {
    const add = (a, b, hw, cls, id) => {
      const idx = ovpSegs.length;
      ovpSegs.push(a[0], a[1], b[0], b[1], a[2], b[2], hw, cls, id);
      const minx = Math.floor((Math.min(a[0], b[0]) - hw) / OVP_CELL), maxx = Math.floor((Math.max(a[0], b[0]) + hw) / OVP_CELL);
      const minz = Math.floor((Math.min(a[1], b[1]) - hw) / OVP_CELL), maxz = Math.floor((Math.max(a[1], b[1]) + hw) / OVP_CELL);
      for (let gx = minx; gx <= maxx; gx++) for (let gz = minz; gz <= maxz; gz++) {
        const k = gx + ':' + gz;
        let arr = ovpGrid.get(k);
        if (!arr) { arr = []; ovpGrid.set(k, arr); }
        arr.push(idx);
      }
    };
    OVP.el.forEach((c, ci) => { for (let i = 0; i + 1 < c.p.length; i++) add(c.p[i], c.p[i + 1], c.w / 2, c.c, ci); });
    // sunken runs: -1 = open cut (digs holes, grows walls), -2 = covered tunnel
    // (suppresses the packed road but leaves the ground alone)
    OVP.sk.forEach((c, ci) => { for (let i = 0; i + 1 < c.p.length; i++) add(c.p[i], c.p[i + 1], c.w / 2 + 2, c.cov ? -2 : -1, 1000 + ci); });
  }
  // a packed road segment lying along a baked chain is the same OSM way: the
  // deck (or sunken roadway) build owns it, so the flat ribbon must not draw.
  // The radius is a FIXED 2.6 m: same-way centerlines coincide within the two
  // simplification tolerances, while parallel surface streets sit 8 m or more
  // away. (The old chainWidth/2 + 3 swept 11 m on motorways and ate the streets
  // running beside the embankments.)
  function ovpOwned(ax, az, bx, bz) {
    if (!ovpSegs.length) return false;
    let ux = bx - ax, uz = bz - az;
    const L = Math.hypot(ux, uz) || 1;
    ux /= L; uz /= L;
    const hit = (x, z) => {
      const arr = ovpGrid.get(Math.floor(x / OVP_CELL) + ':' + Math.floor(z / OVP_CELL));
      if (!arr) return false;
      for (const s of arr) {
        const sax = ovpSegs[s], saz = ovpSegs[s + 1], sbx = ovpSegs[s + 2], sbz = ovpSegs[s + 3];
        let dx = sbx - sax, dz = sbz - saz;
        const sl = Math.hypot(dx, dz) || 1;
        if (Math.abs((dx * ux + dz * uz) / sl) < 0.8) continue;
        let t = ((x - sax) * dx + (z - saz) * dz) / (sl * sl);
        t = clamp(t, 0, 1);
        const px = sax + dx * t - x, pz = saz + dz * t - z;
        if (px * px + pz * pz < 2.6 * 2.6) return true;
      }
      return false;
    };
    // both ENDPOINTS suffice: requiring the midpoint too let curved duplicates
    // escape where the simplified chain corner-cuts the arc (mid bulges ~5 m)
    return hit(ax, az) && hit(bx, bz);
  }
  // does a building footprint straddle a motorway deck or an open cut? (an OSM
  // artifact: nothing real stands across I-95 — Mike's building through the
  // viaduct). The audit proved centroid tests miss edge-on straddlers 5 times
  // out of 7, so every footprint EDGE is walked against the swath.
  function ovpCutHit(x, z) {
    const arr = ovpGrid.get(Math.floor(x / OVP_CELL) + ':' + Math.floor(z / OVP_CELL));
    if (!arr) return false;
    for (const s of arr) {
      const cls = ovpSegs[s + 7];
      if (cls > 1 && cls !== -1) continue;           // motorway/trunk decks and open cuts only
      const sax = ovpSegs[s], saz = ovpSegs[s + 1], sbx = ovpSegs[s + 2], sbz = ovpSegs[s + 3], hw = ovpSegs[s + 6];
      const dx = sbx - sax, dz = sbz - saz;
      const L2 = dx * dx + dz * dz || 1e-9;
      let t = ((x - sax) * dx + (z - saz) * dz) / L2;
      t = clamp(t, 0, 1);
      const px = sax + dx * t - x, pz = saz + dz * t - z;
      const r = Math.max(2, hw - 1);
      if (px * px + pz * pz < r * r) return true;
    }
    return false;
  }
  function ovpStraddle(poly, cx, cz) {
    if (ovpCutHit(cx, cz)) return true;
    if (poly) {
      for (let i = 0; i < poly.length; i++) {
        const a = poly[i], b = poly[(i + 1) % poly.length];
        const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const k = Math.max(1, Math.ceil(L / 3));
        for (let j = 0; j <= k; j++) {
          const t = j / k;
          if (ovpCutHit(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)) return true;
        }
      }
    }
    return vineCut(cx, cz, -1) !== null;
  }
  // deck-top height at a point, aligned to a travel direction when one is given
  // (buses and street labels ride the deck; things merely passing beneath do not)
  function ovpDeckY(x, z, ux, uz) {
    const arr = ovpGrid.get(Math.floor(x / OVP_CELL) + ':' + Math.floor(z / OVP_CELL));
    if (!arr) return null;
    let best = null;
    for (const s of arr) {
      if (ovpSegs[s + 7] < 0) continue;            // sunken carriageways never lift
      const sax = ovpSegs[s], saz = ovpSegs[s + 1], sbx = ovpSegs[s + 2], sbz = ovpSegs[s + 3], hw = ovpSegs[s + 6];
      const dx = sbx - sax, dz = sbz - saz;
      const sl = Math.hypot(dx, dz) || 1;
      if (ux !== undefined && Math.abs((dx * ux + dz * uz) / sl) < 0.72) continue;
      let t = ((x - sax) * dx + (z - saz) * dz) / (sl * sl);
      t = clamp(t, 0, 1);
      const px = sax + dx * t - x, pz = saz + dz * t - z;
      if (px * px + pz * pz > (hw + 1.5) * (hw + 1.5)) continue;
      const y = ovpSegs[s + 4] + (ovpSegs[s + 5] - ovpSegs[s + 4]) * t;
      if (best === null || y > best) best = y;
    }
    return best;
  }
  // the Vine Street open cut: corridor membership + floor height (pad widens or,
  // negative, shrinks the tested corridor width)
  const vineBox = { x0: 1e9, x1: -1e9, z0: 1e9, z1: -1e9 };
  for (const run of OVP.cor) for (const p of run) {
    vineBox.x0 = Math.min(vineBox.x0, p[0] - p[3] - 4); vineBox.x1 = Math.max(vineBox.x1, p[0] + p[3] + 4);
    vineBox.z0 = Math.min(vineBox.z0, p[1] - p[3] - 4); vineBox.z1 = Math.max(vineBox.z1, p[1] + p[3] + 4);
  }
  function vineCut(x, z, pad) {
    if (x < vineBox.x0 || x > vineBox.x1 || z < vineBox.z0 || z > vineBox.z1) return null;
    pad = pad || 0;
    for (const run of OVP.cor) {
      for (let i = 0; i + 1 < run.length; i++) {
        const a = run[i], b = run[i + 1];
        const dx = b[0] - a[0], dz = b[1] - a[1];
        const L2 = dx * dx + dz * dz || 1e-9;
        let t = ((x - a[0]) * dx + (z - a[1]) * dz) / L2;
        t = clamp(t, 0, 1);
        const px = a[0] + dx * t - x, pz = a[1] + dz * t - z;
        const hw = a[3] + (b[3] - a[3]) * t + pad;
        if (px * px + pz * pz < hw * hw) return a[2] + (b[2] - a[2]) * t;
      }
    }
    return null;
  }
  // sunken RAMP approaches dive below grade outside the main corridor: the ground
  // must open over them too (they get their own narrow walled cuts)
  function sunkCutNear(x, z, pad) {
    const arr = ovpGrid.get(Math.floor(x / OVP_CELL) + ':' + Math.floor(z / OVP_CELL));
    if (!arr) return null;
    for (const s of arr) {
      if (ovpSegs[s + 7] !== -1) continue;
      const sax = ovpSegs[s], saz = ovpSegs[s + 1], sbx = ovpSegs[s + 2], sbz = ovpSegs[s + 3], hw = ovpSegs[s + 6];
      const dx = sbx - sax, dz = sbz - saz;
      const L2 = dx * dx + dz * dz || 1e-9;
      let t = ((x - sax) * dx + (z - saz) * dz) / L2;
      t = clamp(t, 0, 1);
      const px = sax + dx * t - x, pz = saz + dz * t - z;
      const r = hw + (pad || 0);
      if (px * px + pz * pz > r * r) continue;
      const y = ovpSegs[s + 4] + (ovpSegs[s + 5] - ovpSegs[s + 4]) * t;
      if (y < demY(x, z) - 1.2) return y;
    }
    return null;
  }
  function cutHole(x, z) {
    return vineCut(x, z, -1) !== null || sunkCutNear(x, z, 1) !== null;
  }

  // ---------------------------------------------------------------- living water
  // Every water material shares these uniforms; liquify() injects a moving sum of
  // directional gradient waves that tilts the shading normal (sun glitter, moving
  // sky reflections) plus a faint albedo shimmer so matte views from altitude read
  // too. No vertex displacement: shorelines and copings stay watertight. Amplitude
  // follows the live wind (applyWx); a distance fade keeps far water calm so the
  // ripple field never aliases into noise at the horizon.
  const waterU = { uTime: { value: 7.3 }, uWAmp: { value: 1.0 }, uWDir: { value: new THREE.Vector2(0.86, 0.5) }, uSun: { value: new THREE.Vector3(0.3, 0.8, 0.2) } };
  function liquify(mat, scale, amp, speed) {
    mat.onBeforeCompile = (sh) => {
      sh.uniforms.uTime = waterU.uTime;
      sh.uniforms.uWAmp = waterU.uWAmp;
      sh.uniforms.uWDir = waterU.uWDir;
      sh.uniforms.uSun = waterU.uSun;
      sh.uniforms.uNite = nightUniform;   // resolved at first render, after its declaration
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vWq;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nvWq = (modelMatrix * vec4(transformed, 1.0)).xyz;');
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vWq;\nuniform float uTime, uWAmp, uNite;\nuniform vec2 uWDir;\nuniform vec3 uSun;\nfloat wGlint = 0.0;\n' +
          'vec2 wgrad(vec2 p, vec2 d, float lam, float sp, float t) {\n' +
          '  float k = 6.2831853 / lam;\n' +
          '  return d * (cos(dot(p, d) * k + t * sp) * k);\n' +
          '}\n')
        .replace('#include <normal_fragment_begin>', '#include <normal_fragment_begin>\n{\n' +
          '  float wsc = ' + scale.toFixed(3) + ';\n' +
          '  float wsp = ' + speed.toFixed(3) + ';\n' +
          '  float wamp = ' + amp.toFixed(3) + ' * uWAmp;\n' +
          '  vec2 wd = normalize(uWDir);\n' +
          '  vec2 wp = vec2(-wd.y, wd.x);\n' +
          '  float wdist = length(vViewPosition);\n' +
          '  float wfade = clamp(1.35 - wdist / (2600.0 * wsc + 420.0), 0.14, 1.0);\n' +
          '  vec2 g = wgrad(vWq.xz, wd, 46.0 * wsc, 1.15 * wsp, uTime) * 0.5;\n' +
          '  g += wgrad(vWq.xz, normalize(wd + wp * 0.62), 21.0 * wsc, 1.6 * wsp, uTime) * 0.34;\n' +
          '  g += wgrad(vWq.xz, normalize(wd - wp * 0.8), 9.5 * wsc, 2.3 * wsp, uTime) * 0.22;\n' +
          '  g += wgrad(vWq.xz, normalize(wp - wd * 0.35), 4.1 * wsc, 3.1 * wsp, uTime) * 0.11;\n' +
          '  g *= wamp * wfade;\n' +
          '  vec3 wn = normalize(vec3(-g.x, 1.0, -g.y));\n' +
          '  normal = normalize(mix(normal, wn, 0.92));\n' +
          '  float wh = sin(dot(vWq.xz, wd) * (6.2831853 / (46.0 * wsc)) + uTime * 1.15 * wsp)\n' +
          '           + 0.7 * sin(dot(vWq.xz, normalize(wd - wp * 0.8)) * (6.2831853 / (9.5 * wsc)) + uTime * 2.3 * wsp)\n' +
          '           + 0.45 * sin(dot(vWq.xz, normalize(wp + wd * 0.5)) * (6.2831853 / (3.1 * wsc)) + uTime * 3.6 * wsp);\n' +
          '  diffuseColor.rgb *= 1.0 + wh * 0.075 * wamp * wfade;\n' +
          // sun glitter on the perturbed surface: the material is deliberately rough
          // (the river must not mirror the sky), so the sparkle is added explicitly
          '  vec3 wview = normalize(cameraPosition - vWq);\n' +
          '  float wspec = pow(max(dot(wview, reflect(-normalize(uSun), wn)), 0.0), 140.0);\n' +
          // at night uSun is the MOON: keep a faint moonglade, not a sequin field
          '  wGlint = wspec * smoothstep(0.02, 0.1, uSun.y) * (0.55 + 0.45 * uWAmp) * wfade * (1.0 - uNite * 0.85);\n' +
          '}\n')
        .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\n' +
          'totalEmissiveRadiance += vec3(1.0, 0.93, 0.78) * wGlint * 1.15;\n');
    };
  }
  // the outer rivers and far water polygons share one animated material
  const riverMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.42, metalness: 0.18, envMapIntensity: 0.55 });
  liquify(riverMat, 1.0, 1.35, 1.0);

  function waterPoint(along, out) {
    // along: meters along the shoreline from the towers' projection; out: meters east of the bulkhead
    const t = (towersCenter.x - wl.px) * wl.dx + (towersCenter.z - wl.pz) * wl.dz;
    return [
      wl.px + wl.dx * (t + along) + wl.nx * (wl.off + out),
      wl.pz + wl.dz * (t + along) + wl.nz * (wl.off + out),
    ];
  }

  // ---------------------------------------------------------------- terrain
  // Society Hill sits on a bluff ~10 m above the Delaware. East of Front St the
  // I-95 trench drops 8 m, then the Penn's Landing shelf sits 6.5-7.5 m below the
  // city, then the bulkhead and the river. Cap decks bridge the trench at
  // Foglietta Plaza and the Vietnam memorial; the new Park at Penn's Landing is a
  // continuous lawn sloping from Front St down to the promenade. Heights are
  // relative to the city datum (y = 0); lateral offsets are measured from the
  // fitted Columbus Blvd centerline (positive = toward the river).
  // Elevation: USGS NED 10 m grid (dem.json, meters above sea level). The datum
  // is the towers' site (8.3 m ASL) so the towers stay at y = 0; the rest of the
  // city rides the real ground — Front St ~5 m lower, 5th St ~2 m higher.
  const DEM0 = (typeof DEM !== 'undefined' && DEM && DEM.rows) ? DEM : null;
  const DEMW = (typeof DEM_WIDE !== 'undefined' && DEM_WIDE && DEM_WIDE.rows) ? DEM_WIDE : null;
  const DEMS = (typeof DEM_SOUTH !== 'undefined' && DEM_SOUTH && DEM_SOUTH.rows) ? DEM_SOUTH : null;
  const DEMC = (typeof DEM_CITY !== 'undefined' && DEM_CITY && DEM_CITY.rows) ? DEM_CITY : null;
  const CORE_EXT = { x0: -640, x1: 770, z0: -520, z1: 850 }; // the detailed extract
  function inCore(x, z) { return x >= CORE_EXT.x0 && x <= CORE_EXT.x1 && z >= CORE_EXT.z0 && z <= CORE_EXT.z1; }
  function sampleDem(G, x, z, fallback) {
    const fx = (x - G.x0) / G.cell, fz = (z - G.z0) / G.cell;
    if (fx < 0 || fz < 0 || fx > G.nx - 1 || fz > G.nz - 1) return null;
    const i = clamp(Math.floor(fx), 0, G.nx - 2), j = clamp(Math.floor(fz), 0, G.nz - 2);
    const tx = clamp(fx - i, 0, 1), tz = clamp(fz - j, 0, 1);
    const r0 = G.rows[j], r1 = G.rows[j + 1];
    const v = (a) => (a == null ? fallback : a);
    const a = v(r0[i]) * (1 - tx) + v(r0[i + 1]) * tx;
    const b = v(r1[i]) * (1 - tx) + v(r1[i + 1]) * tx;
    return a * (1 - tz) + b * tz;
  }
  function demAbs(x, z) {
    // null DEM cells (NED voids over made land) must NOT fall back to 0 ASL — that is
    // below the model's water plane and floods whole blocks (the stadium site)
    let v = DEM0 ? sampleDem(DEM0, x, z, 8.34) : null;
    if (v == null && DEMW) v = sampleDem(DEMW, x, z, 3.2);
    if (v == null && DEMS) v = sampleDem(DEMS, x, z, 3.2);
    if (v == null && DEMC) v = sampleDem(DEMC, x, z, 4.0);
    if (v == null && DEMW) { // beyond the grids: clamp to the nearest edge sample
      const G = (DEMS && z > DEMW.z0 + DEMW.cell * (DEMW.nz - 1)) ? DEMS : DEMW;
      v = sampleDem(G, clamp(x, G.x0, G.x0 + G.cell * (G.nx - 1)), clamp(z, G.z0, G.z0 + G.cell * (G.nz - 1)), 0);
    }
    return v == null ? 8.34 : v;
  }
  const DATUM = demAbs(towersCenter.x, towersCenter.z);
  function demY(x, z) { return demAbs(x, z) - DATUM; }
  // constructed waterfront, relative to the datum (river ~0.5 m ASL, shelf ~3 m, I-95 ~1.5 m)
  const TERRAIN = { trenchW: 10, trenchE: 72, trenchFloor: 1.5 - DATUM, shelfLo: 2.4 - DATUM, shelfHi: 4.0 - DATUM, bulkhead: 2.8 - DATUM, water: 0.5 - DATUM, bed: -2.0 - DATUM };
  // Front St line (the city grid runs ~10 deg off my axes; I-95 hugs Front St's east side)
  const fl = { px: 140, pz: 0, dx: -0.167, dz: 0.986, nx: 0.986, nz: 0.167 };
  {
    const pts = [];
    for (const r of D.roads) if (r.name && /front street/i.test(r.name)) for (const q of r.pts) pts.push(q);
    if (pts.length > 3) {
      let mx = 0, mz = 0;
      for (const q of pts) { mx += q[0]; mz += q[1]; }
      mx /= pts.length; mz /= pts.length;
      let sxx = 0, sxz = 0, szz = 0;
      for (const q of pts) { const ax = q[0] - mx, az = q[1] - mz; sxx += ax * ax; sxz += ax * az; szz += az * az; }
      const ang = 0.5 * Math.atan2(2 * sxz, sxx - szz);
      fl.px = mx; fl.pz = mz; fl.dx = Math.cos(ang); fl.dz = Math.sin(ang);
      if (fl.dz < 0) { fl.dx = -fl.dx; fl.dz = -fl.dz; }
      fl.nx = -fl.dz; fl.nz = fl.dx;
      if (fl.nx < 0) { fl.nx = -fl.nx; fl.nz = -fl.nz; }
    }
  }
  function frontOff(x, z) { return (x - fl.px) * fl.nx + (z - fl.pz) * fl.nz; }
  function frontPt(o, z) { const t = (z - fl.pz - fl.nz * o) / fl.dz; return [fl.px + fl.nx * o + fl.dx * t, z]; }
  // the city plateau near the trench must not inherit DEM samples that fell into I-95
  function cityY(x, z) {
    const o = frontOff(x, z);
    if (o > -100) { const [rx] = frontPt(-110, z); return Math.max(demY(x, z), demY(rx, z) - 0.4); }
    return demY(x, z);
  }
  function frontDem(z) { const [rx] = frontPt(-110, z); return demY(rx, z); }
  // the Delaware's edge as a polyline x(z): Penn's Landing bulges east, the marina
  // basin is notched in, the shore pulls back south of the museum ships
  const SHORE = [[404, -3000], [404, -520], [422, -350], [422, -200], [432, -60], [432, -8], [312, -6], [312, 216], [432, 218], [432, 232], [345, 240], [345, 430], [380, 450], [380, 500], [345, 520], [345, 3500]];
  function xShore(z) {
    for (let i = 0; i < SHORE.length - 1; i++) {
      const a = SHORE[i], b = SHORE[i + 1];
      if (z >= a[1] && z <= b[1]) { const t = (z - a[1]) / Math.max(1e-6, b[1] - a[1]); return a[0] + (b[0] - a[0]) * t; }
    }
    return z < SHORE[0][1] ? SHORE[0][0] : SHORE[SHORE.length - 1][0];
  }
  const CAPS = [
    { z0: -345, z1: -201, kind: 'park' },      // Park at Penn's Landing: Chestnut -> Walnut
    { z0: -25, z1: 64, kind: 'deck', dy: 0 },  // Foglietta Plaza: Dock -> Spruce
    { z0: 64, z1: 122, kind: 'deck', dy: -1 }, // Vietnam Veterans Memorial deck
  ];
  const slips = []; // ship berths carved into the shelf: [x0, x1, z0, z1]
  for (const b of D.buildings) {
    if (b.t !== 'ship' || !b.poly || b.poly.length < 3) continue;
    let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9;
    for (const q of b.poly) { x0 = Math.min(x0, q[0]); x1 = Math.max(x1, q[0]); z0 = Math.min(z0, q[1]); z1 = Math.max(z1, q[1]); }
    slips.push([x0 - 7, x1 + 7, z0 - 7, z1 + 7]);
  }
  const extraTreeSpots = [];
  const poolTreeSpots = [];   // pool-terrace ring — planted through clear() so none land in buildings
  function inRiver(x, z) {
    if (x > xShore(z)) return true;
    for (const sl of slips) if (x > sl[0] && x < sl[1] && z > sl[2] && z < sl[3]) return true;
    return false;
  }
  function shelfY(x, z) { return clamp(demY(x, z), TERRAIN.shelfLo, TERRAIN.shelfHi); }
  function parkCapY(x, z) {
    const [xf] = frontPt(TERRAIN.trenchW, z);
    const top = frontDem(z);
    return top + (TERRAIN.bulkhead - top) * clamp((x - xf) / Math.max(20, xShore(z) - xf), 0, 1);
  }
  const PLAZA_R = 58;
  // each tower also stands on its own full-height rectangular pad: the radial feather
  // alone starts INSIDE the south tower's footprint (its SE corner is ~70 m out), so
  // the lawn dropped away under the fixed-height base and the colonnade/lobby floated
  const towerPads = towers.map(t => {
    const ang = -(t.angleRad || 0);
    return { cx: t.centroid[0], cz: t.centroid[1], hw: t.width_m / 2 + 5, hd: t.depth_m / 2 + 5, cos: Math.cos(ang), sin: Math.sin(ang) };
  });
  function plazaLift(x, z) {
    // wide smoothstep feather: the draped lawns/ribbons sample this at ~10 m, so a
    // tight linear falloff aliased into wedges that sliced across the plaza edge
    const d = Math.hypot(x - towersCenter.x, z - towersCenter.z);
    let t = d < PLAZA_R ? 1.0 : (d >= PLAZA_R + 16 ? 0 : 1 - (d - PLAZA_R) / 16);
    for (const p of towerPads) {
      if (t >= 1) break;
      const dx = x - p.cx, dz = z - p.cz;
      const u = Math.abs(dx * p.cos - dz * p.sin) - p.hw;
      const v = Math.abs(dx * p.sin + dz * p.cos) - p.hd;
      const dr = Math.max(u, v);
      const tp = dr <= 0 ? 1.0 : (dr >= 12 ? 0 : 1 - dr / 12);
      if (tp > t) t = tp;
    }
    if (t <= 0) return 0;
    if (t >= 1) return 1.0;
    return t * t * (3 - 2 * t);
  }
  const bermSpots = []; // [x, z, rx, rz, rotY] — trees must not sprout through the lawn berms
  // where things sit. mode 'ground' = objects, trees, lawns; 'road' = streets
  // (bridged over the trench, tunnelled under the park cap)
  function siteY(x, z, mode) {
    if (!inCore(x, z)) { // outer districts ride the wide DEM. Low terrain east of the
      // Delaware bank is river; low LAND west of it (stadiums, FDR, the airport — NED
      // reads made-land near 0 ASL) clamps just above the water plane instead of flooding
      const y = demY(x, z);
      if (y >= TERRAIN.water + 0.6) return y;
      return eastOfDelaware(x, z) ? TERRAIN.bulkhead : TERRAIN.water + 0.45;
    }
    if (inRiver(x, z)) return TERRAIN.bulkhead;
    const o = frontOff(x, z);
    const cap = CAPS.find(c => z > c.z0 && z < c.z1);
    if (cap && cap.kind === 'park' && o > TERRAIN.trenchW - 3) {
      if (mode === 'road') return o > TERRAIN.trenchE ? shelfY(x, z) : parkCapY(x, z) - 0.35;
      return parkCapY(x, z);
    }
    if (o < TERRAIN.trenchW) return cityY(x, z) + plazaLift(x, z);
    if (o < TERRAIN.trenchE) return (cap && cap.kind === 'deck') ? frontDem(z) + cap.dy : (mode === 'road' ? frontDem(z) : TERRAIN.trenchFloor);
    return shelfY(x, z);
  }
  function walkY(x, z) { return Math.max(siteY(x, z, 'ground'), siteY(x, z, 'road')); }

  // collision + occupancy structures (filled during build)
  const colGrid = new Map();
  const COL_CELL = 8;
  const colSegs = [];
  function colKey(cx, cz) { return cx + ':' + cz; }
  function addColSeg(ax, az, bx, bz) {
    const idx = colSegs.length;
    colSegs.push(ax, az, bx, bz);
    const minx = Math.floor(Math.min(ax, bx) / COL_CELL), maxx = Math.floor(Math.max(ax, bx) / COL_CELL);
    const minz = Math.floor(Math.min(az, bz) / COL_CELL), maxz = Math.floor(Math.max(az, bz) / COL_CELL);
    for (let gx = minx; gx <= maxx; gx++) for (let gz = minz; gz <= maxz; gz++) {
      const k = colKey(gx, gz);
      let a = colGrid.get(k);
      if (!a) { a = []; colGrid.set(k, a); }
      a.push(idx);
    }
  }
  // road segments for tree rejection (streets only; park paths keep their trees)
  const roadGrid = new Map();
  const ROAD_CELL = 12;
  function addRoadSeg(ax, az, bx, bz, hw) {
    const idx = roadSegs.length;
    roadSegs.push(ax, az, bx, bz, hw);
    const minx = Math.floor((Math.min(ax, bx) - hw) / ROAD_CELL), maxx = Math.floor((Math.max(ax, bx) + hw) / ROAD_CELL);
    const minz = Math.floor((Math.min(az, bz) - hw) / ROAD_CELL), maxz = Math.floor((Math.max(az, bz) + hw) / ROAD_CELL);
    for (let gx = minx; gx <= maxx; gx++) for (let gz = minz; gz <= maxz; gz++) {
      const k = gx + ':' + gz;
      let a = roadGrid.get(k);
      if (!a) { a = []; roadGrid.set(k, a); }
      a.push(idx);
    }
  }
  const roadSegs = [];
  function nearRoad(x, z, pad) {
    const a = roadGrid.get(Math.floor(x / ROAD_CELL) + ':' + Math.floor(z / ROAD_CELL));
    if (!a) return false;
    for (const s of a) {
      const ax = roadSegs[s], az = roadSegs[s + 1], bx = roadSegs[s + 2], bz = roadSegs[s + 3], hw = roadSegs[s + 4];
      const dx = bx - ax, dz = bz - az;
      const L2 = dx * dx + dz * dz;
      let t = L2 > 0 ? ((x - ax) * dx + (z - az) * dz) / L2 : 0;
      t = clamp(t, 0, 1);
      const px = ax + dx * t - x, pz = az + dz * t - z;
      const r = hw + pad;
      if (px * px + pz * pz < r * r) return true;
    }
    return false;
  }

  // like nearRoad, but only matches core segments running PARALLEL to (ux, uz) —
  // used to drop wide-set duplicates without notching perpendicular crossings
  function nearRoadAligned(x, z, pad, ux, uz) {
    const a = roadGrid.get(Math.floor(x / ROAD_CELL) + ':' + Math.floor(z / ROAD_CELL));
    if (!a) return false;
    for (const s of a) {
      const ax = roadSegs[s], az = roadSegs[s + 1], bx = roadSegs[s + 2], bz = roadSegs[s + 3], hw = roadSegs[s + 4];
      let dx = bx - ax, dz = bz - az;
      const L = Math.hypot(dx, dz) || 1;
      dx /= L; dz /= L;
      if (Math.abs(dx * ux + dz * uz) < 0.82) continue;
      let t = ((x - ax) * (bx - ax) + (z - az) * (bz - az)) / (L * L);
      t = clamp(t, 0, 1);
      const px = ax + (bx - ax) * t - x, pz = az + (bz - az) * t - z;
      const r = hw + pad;
      if (px * px + pz * pz < r * r) return true;
    }
    return false;
  }

  function nearBuildingEdge(x, z, r) {
    const gx = Math.floor(x / COL_CELL), gz = Math.floor(z / COL_CELL);
    for (let ix = gx - 1; ix <= gx + 1; ix++) for (let iz = gz - 1; iz <= gz + 1; iz++) {
      const a = colGrid.get(colKey(ix, iz));
      if (!a) continue;
      for (const s of a) {
        const ax = colSegs[s], az = colSegs[s + 1], bx = colSegs[s + 2], bz = colSegs[s + 3];
        const dx = bx - ax, dz = bz - az;
        const L2 = dx * dx + dz * dz;
        let t = L2 > 0 ? ((x - ax) * dx + (z - az) * dz) / L2 : 0;
        t = clamp(t, 0, 1);
        const px = ax + dx * t - x, pz = az + dz * t - z;
        if (px * px + pz * pz < r * r) return true;
      }
    }
    return false;
  }

  const buildingPolys = []; // interior tests (tree placement)
  const polyGrid = new Map();
  const POLY_CELL = 16;
  function registerPoly(poly) {
    const idx = buildingPolys.length;
    buildingPolys.push(poly);
    let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9;
    for (const p of poly) {
      if (p[0] < x0) x0 = p[0]; if (p[0] > x1) x1 = p[0];
      if (p[1] < z0) z0 = p[1]; if (p[1] > z1) z1 = p[1];
    }
    for (let gx = Math.floor(x0 / POLY_CELL); gx <= Math.floor(x1 / POLY_CELL); gx++)
      for (let gz = Math.floor(z0 / POLY_CELL); gz <= Math.floor(z1 / POLY_CELL); gz++) {
        const k = gx + ':' + gz;
        let a = polyGrid.get(k);
        if (!a) { a = []; polyGrid.set(k, a); }
        a.push(idx);
      }
  }
  function insideBuilding(x, z) {
    const a = polyGrid.get(Math.floor(x / POLY_CELL) + ':' + Math.floor(z / POLY_CELL));
    if (!a) return false;
    for (const idx of a) if (pointInPoly(x, z, buildingPolys[idx])) return true;
    return false;
  }
  const rayTargets = [];   // double-click focus raycasts only against these
  // phones die on PEAK memory, not triangle count: once the GPU holds a big
  // merged geometry we never raycast, the CPU-side typed arrays are pure waste
  function freeOnUpload(g) {
    for (const k in g.attributes) g.attributes[k].onUpload(function () { this.array = null; });
    if (g.index) g.index.onUpload(function () { this.array = null; });
  }

  const groupCity = new THREE.Group();
  scene.add(groupCity);

  const buildSteps = [];
  function step(msg, fn) { buildSteps.push({ msg, fn }); }

  // ------------------------------------------------ ground, water, roads, parks
  step('Laying out the ground', () => {
    const groundMat = new THREE.MeshStandardMaterial({ color: COLORS.ground, roughness: 0.96, metalness: 0 });
    groundMats.push(groundMat);
    const Z0 = CORE_EXT.z0, Z1 = CORE_EXT.z1;
    const flat = (poly, y) => { const g = new THREE.ShapeGeometry(shapeFromPoly(poly, null)); g.rotateX(-Math.PI / 2); g.translate(0, y, 0); return g; };
    // city heightfield (12.5 m) riding the DEM, diving into the trench east of Front St
    {
      const X0 = CORE_EXT.x0, X1 = CORE_EXT.x1, ZA = CORE_EXT.z0, ZB = CORE_EXT.z1, cell = 12.5;
      const nx = Math.round((X1 - X0) / cell), nz = Math.round((ZB - ZA) / cell);
      const pos = [];
      for (let j = 0; j <= nz; j++) for (let i = 0; i <= nx; i++) {
        const x = X0 + i * cell, z = ZA + j * cell;
        // east of the trench the shelf mesh takes over; past the shoreline this
        // field must dive below the water plane or it reads as a slab on the river
        // (the -4 margin keeps interpolated cell faces from surfacing east of the bulkhead)
        const y = frontOff(x, z) < TERRAIN.trenchW ? cityY(x, z) - 0.05 : ((inWater(x, z) > -4 || inRiver(x, z)) ? TERRAIN.bed - 0.05 : TERRAIN.trenchFloor - 0.05);
        pos.push(x, y, z);
      }
      const idx = [];
      for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
        const a = j * (nx + 1) + i, b = a + 1, c = a + nx + 1, d = c + 1;
        idx.push(a, c, b, b, c, d);
      }
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
      g.setIndex(idx);
      g.computeVertexNormals();
      const city = new THREE.Mesh(g, groundMat);
      city.receiveShadow = true; groupCity.add(city); rayTargets.push(city);
      // river bed under everything; the water plane sits above it
      const far = new THREE.Mesh(flat([[-9000, -9000], [9000, -9000], [9000, 9000], [-9000, 9000]], TERRAIN.bed), new THREE.MeshStandardMaterial({ color: 0x4a4f48, roughness: 1 }));
      groupCity.add(far);
    }
    // outer districts: 25 m heightfields around the core, water where the DEM sits at river level
    {
      const W = { x0: -3700, x1: 2300, z0: -4480, z1: 6400 };
      const strips = [
        [W.x0, W.x1, W.z0, CORE_EXT.z0], [W.x0, W.x1, CORE_EXT.z1, W.z1],
        [W.x0, CORE_EXT.x0, CORE_EXT.z0, CORE_EXT.z1], [CORE_EXT.x1, W.x1, CORE_EXT.z0, CORE_EXT.z1],
      ];
      // Fairmount greening: around the Art Museum the bare heightfield is parkland,
      // not pavement — vertex-tint those cells toward park green (ratio of park to
      // ground, so the day/night ground retint still applies), feathered 80 m
      const wideGroundMat = groundMat.clone();
      wideGroundMat.vertexColors = true;
      groundMats.push(wideGroundMat);
      const FMZ = { x0: -3690, x1: -2480, z0: -2950, z1: -1720 };
      const pkC = new THREE.Color(COLORS.park), gdC = new THREE.Color(COLORS.ground);
      const fmR = [pkC.r / gdC.r, pkC.g / gdC.g, pkC.b / gdC.b];
      for (const [x0, x1, z0, z1] of strips) {
        const cell = 25, nx = Math.max(1, Math.round((x1 - x0) / cell)), nz = Math.max(1, Math.round((z1 - z0) / cell));
        const pos = [];
        const col = [];
        const hole = [];   // vertices inside the Vine Street cut: their cells are skipped
        for (let j = 0; j <= nz; j++) for (let i = 0; i <= nx; i++) {
          const x = x0 + (x1 - x0) * i / nx, z = z0 + (z1 - z0) * j / nz;
          const y = demY(x, z);
          let yy = (y < TERRAIN.water + 0.6 ? (eastOfDelaware(x, z) ? TERRAIN.bed : TERRAIN.water + 0.45) : y) - 0.05;
          // NED reads a made-land shelf across the Delaware at the Walt Whitman
          // crossing (~3 m above water mid-river) — those cells rendered as a flat
          // gray band under the deck; between the banks, send them to the bed
          if (x > 880 && x < 1950 && y >= TERRAIN.water + 0.6 && y < TERRAIN.water + 4.5 && wwbNear(x, z, 260)) yy = TERRAIN.bed - 0.05;
          pos.push(x, yy, z);
          hole.push(cutHole(x, z) ? 1 : 0);
          const inD = Math.min(x - FMZ.x0, FMZ.x1 - x, z - FMZ.z0, FMZ.z1 - z);
          const t = clamp(inD / 80, 0, 1);
          col.push(1 + (fmR[0] - 1) * t, 1 + (fmR[1] - 1) * t, 1 + (fmR[2] - 1) * t);
        }
        const idx = [];
        for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
          const a = j * (nx + 1) + i, b = a + 1, c = a + nx + 1, d = c + 1;
          // the Vine Street Expressway cut is open ground: drop cells touching it
          // (index skip only — pos and col stay parallel; the collar apron built in
          // 'Raising the overpasses' hides the ragged hole rim at grade)
          if (hole[a] || hole[b] || hole[c] || hole[d]) continue;
          idx.push(a, c, b, b, c, d);
        }
        const g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
        g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(col), 3));
        g.setIndex(idx);
        g.computeVertexNormals();
        const m = new THREE.Mesh(g, wideGroundMat);
        groupCity.add(m); rayTargets.push(m);
      }
    }
    // trench floor
    const trench = new THREE.Mesh(flat([frontPt(TERRAIN.trenchW, Z0), frontPt(TERRAIN.trenchE, Z0), frontPt(TERRAIN.trenchE, Z1), frontPt(TERRAIN.trenchW, Z1)], TERRAIN.trenchFloor),
      new THREE.MeshStandardMaterial({ color: 0x4b4843, roughness: 0.95 }));
    trench.receiveShadow = true; groupCity.add(trench);
    // waterfront shelf: heightfield between the trench's east wall and the shoreline, 5 m rows
    {
      const rows = [], cols = 40;
      for (let z = Z0; z <= Z1; z += 5) rows.push(z);
      const pos = [];
      for (const z of rows) {
        const [xw] = frontPt(TERRAIN.trenchE - 1, z);
        const xe = xShore(z) + 2;
        for (let c = 0; c <= cols; c++) {
          const x = xw + (xe - xw) * (c / cols);
          pos.push(x, inRiver(x, z) ? TERRAIN.bed : shelfY(x, z), z);
        }
      }
      const idx = [];
      const W = cols + 1;
      for (let r = 0; r < rows.length - 1; r++) for (let c = 0; c < cols; c++) {
        const a = r * W + c, b = a + 1, cc = a + W, d = cc + 1;
        idx.push(a, cc, b, b, cc, d);
      }
      const shelfG = new THREE.BufferGeometry();
      shelfG.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
      shelfG.setIndex(idx);
      shelfG.computeVertexNormals();
      const shelf = new THREE.Mesh(shelfG, groundMat);
      shelf.receiveShadow = true; groupCity.add(shelf); rayTargets.push(shelf);
    }
    // (river bed is the global far plane; the water surface is one plane at river level)
    // vertical faces: trench walls (parapet on the Front St side), bulkhead along the shore, ship slips
    const wallParts = [];
    const vstrip = (ax, az, bx, bz, y0, y1, hex) => {
      const arr = new Float32Array([ax, y0, az, bx, y0, bz, bx, y1, bz, ax, y0, az, bx, y1, bz, ax, y1, az]);
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(arr, 3));
      g.computeVertexNormals();
      wallParts.push({ geom: g, color: new THREE.Color(hex), style: 3 });
    };
    // trench walls step with Front St's elevation; 25 m strips
    for (let z = -1200; z < 1800; z += 25) {
      const a = frontPt(TERRAIN.trenchW, z), b = frontPt(TERRAIN.trenchW, z + 25);
      vstrip(a[0], a[1], b[0], b[1], TERRAIN.trenchFloor - 0.3, frontDem(z + 12) + 1.2, '#9a978f');
      const c = frontPt(TERRAIN.trenchE, z), d = frontPt(TERRAIN.trenchE, z + 25);
      vstrip(c[0], c[1], d[0], d[1], TERRAIN.trenchFloor - 0.3, shelfY(d[0] + 3, z + 12) + 0.3, '#9a978f');
    }
    for (let i = 0; i < SHORE.length - 1; i++) vstrip(SHORE[i][0], SHORE[i][1], SHORE[i + 1][0], SHORE[i + 1][1], TERRAIN.bed, TERRAIN.bulkhead, '#6f6a62');
    for (const sl of slips) {
      vstrip(sl[0], sl[2], sl[0], sl[3], TERRAIN.bed, TERRAIN.bulkhead, '#6f6a62');
      vstrip(sl[0], sl[2], sl[1], sl[2], TERRAIN.bed, TERRAIN.bulkhead, '#6f6a62');
      vstrip(sl[0], sl[3], sl[1], sl[3], TERRAIN.bed, TERRAIN.bulkhead, '#6f6a62');
    }
    const walls = new THREE.Mesh(mergeColored(wallParts), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.9, side: THREE.DoubleSide }));
    walls.receiveShadow = true; groupCity.add(walls);

    const waterMat = new THREE.MeshStandardMaterial({ color: COLORS.water, roughness: 0.42, metalness: 0.18, envMapIntensity: 0.55 });
    liquify(waterMat, 1.0, 1.35, 1.0);      // the Delaware breathes
    const water = new THREE.Mesh(flat([[-9000, -9000], [9000, -9000], [9000, 9000], [-9000, 9000]], TERRAIN.water), waterMat);
    water.receiveShadow = true;
    groupCity.add(water);
    const slipParts = [];
    const rectPoly = (r) => [[r[0], r[2]], [r[1], r[2]], [r[1], r[3]], [r[0], r[3]]];
    for (const sl of slips) slipParts.push({ geom: flatPoly(rectPoly(sl), null, TERRAIN.water + 0.05, true), color: new THREE.Color(COLORS.water) });
    if (slipParts.length) groupCity.add(new THREE.Mesh(mergeColored(slipParts), waterMat));
    // OSM-mapped water bodies (basins, fountains)
    const wparts = [];
    for (const a of D.areas || []) {
      if (a.kind === 'water' && a.poly.length >= 3) wparts.push({ geom: flatPoly(a.poly, null, LAYER.basin), color: new THREE.Color(COLORS.water) });
    }
    if (wparts.length) {
      const basinMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.3, metalness: 0.2 });
      liquify(basinMat, 0.12, 0.9, 2.2);   // pond-scale ripples on basins and fountains
      const wm = new THREE.Mesh(mergeColored(wparts), basinMat);
      groupCity.add(wm);
    }
    // swimming pools (OSM leisure=swimming_pool; missed by the original query)
    const POOLS = [
      [[8.25, 71.61], [6.98, 79.82], [23.46, 82.32], [24.72, 74.11]],       // Society Hill Towers pool, south of 220 Locust
      [[-1.29, 180.63], [9.59, 182.37], [10.57, 176.36], [-0.31, 174.61]],  // townhouse-court pool near Delancey
    ];
    const poolParts = [], deckParts = [];
    for (let pi = 0; pi < POOLS.length; pi++) {
      const poly = POOLS[pi];
      registerPoly(poly); // keeps trees off the water
      if (pi === 0) {
        // The towers' pool terrace sits on the plaza feather, so terrain-following
        // 4-corner planes tilt every which way and slice each other (the "odd shape").
        // Build it as one LEVEL terrace instead: a skirted slab at the highest ground
        // point under it, the pool cut in as a true hole, water sunk in-ground.
        const ob = orientedBox(poly);
        const a = obbAxis(ob);
        const m = 5;
        const rim = (e) => [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([su, sv]) => [
          ob.cx + a.ax * su * (a.hl + e) + a.px * sv * (a.hs + e),
          ob.cz + a.az * su * (a.hl + e) + a.pz * sv * (a.hs + e),
        ]);
        const deck = rim(m);
        let ref = siteY(ob.cx, ob.cz, 'ground');
        for (const q of deck) ref = Math.max(ref, siteY(q[0], q[1], 'ground'));
        const top = ref + 0.14;
        deckParts.push({ geom: buildingGeom(deck, [poly], top, ref - 1.8), color: new THREE.Color(0xb3ab9c) });
        deckParts.push({ geom: flatPoly(rim(0.9), [poly], top + 0.012, true), color: new THREE.Color(0xe9e5da) }); // flush coping
        poolParts.push({ geom: flatPoly(poly, null, top - 0.12, true), color: new THREE.Color(0x3fa9c9) });
        registerPoly(deck);
        // shade trees ringing the terrace (planted on the surrounding lawn)
        for (let side = 0; side < 4; side++) {
          const n = side % 2 === 0 ? 5 : 3;
          for (let i = 0; i < n; i++) {
            const t = (i + 0.5) / n * 2 - 1;
            const [eu, ev] = side % 2 === 0 ? [t * (a.hl + m), (side === 0 ? -1 : 1) * (a.hs + m + 3.1)]
              : [(side === 1 ? -1 : 1) * (a.hl + m + 3.1), t * (a.hs + m)];
            poolTreeSpots.push([
              ob.cx + a.ax * eu + a.px * ev + (hash01(side * 7.1 + i) - 0.5) * 1.4,
              ob.cz + a.az * eu + a.pz * ev + (hash01(side * 3.3 + i + 9) - 0.5) * 1.4,
            ]);
          }
        }
      } else {
        poolParts.push({ geom: flatPoly(poly, null, LAYER.pool), color: new THREE.Color(0x3fa9c9) });
        const obC = orientedBox(poly);
        const aC = obbAxis(obC);
        const cop = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([su, sv]) => [
          obC.cx + aC.ax * su * (aC.hl + 0.9) + aC.px * sv * (aC.hs + 0.9),
          obC.cz + aC.az * su * (aC.hl + 0.9) + aC.pz * sv * (aC.hs + 0.9),
        ]);
        deckParts.push({ geom: flatPoly(cop, null, LAYER.pool - 0.015), color: new THREE.Color(0xe9e5da) });
      }
    }
    // pool water animates, so it splits from the decks and copings
    const poolWaterMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.35, metalness: 0.15, envMapIntensity: 0.7 });
    liquify(poolWaterMat, 0.055, 0.8, 2.6);
    const poolWater = new THREE.Mesh(mergeColored(poolParts), poolWaterMat);
    poolWater.receiveShadow = true;
    groupCity.add(poolWater);
    const poolMesh = new THREE.Mesh(mergeColored(deckParts),
      new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.35, metalness: 0.15, envMapIntensity: 0.7 }));
    poolMesh.receiveShadow = true;
    groupCity.add(poolMesh);
  });

  step('Shaping the waterfront', () => {
    const parts = [];
    const band = (o0, o1, z0, z1) => [frontPt(o0, z0), frontPt(o1, z0), frontPt(o1, z1), frontPt(o0, z1)];
    // cap decks over the trench: slab + edge fascia + a header beam over each
    // portal face, so I-95 visibly dives UNDER the plazas instead of sliding
    // beneath a floating carpet
    const portalFace = (z, topY, dyDrop) => {
      const a = frontPt(TERRAIN.trenchW, z), b = frontPt(TERRAIN.trenchE, z);
      const arr = new Float32Array([a[0], TERRAIN.trenchFloor - 0.4, a[1], b[0], TERRAIN.trenchFloor - 0.4, b[1], b[0], topY, b[1],
                                    a[0], TERRAIN.trenchFloor - 0.4, a[1], b[0], topY, b[1], a[0], topY, a[1]]);
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(arr, 3));
      g.computeVertexNormals();
      parts.push({ geom: g, color: new THREE.Color(0x55524d), style: 3 });
      // header beam across the opening
      let hx = b[0] - a[0], hz = b[1] - a[1];
      const hl = Math.hypot(hx, hz) || 1;
      const hg = new THREE.BoxGeometry(hl + 0.8, 1.25, 0.9);
      hg.rotateY(Math.atan2(-hz, hx));
      hg.translate((a[0] + b[0]) / 2, topY - dyDrop, (a[1] + b[1]) / 2);
      parts.push({ geom: hg, color: new THREE.Color(0x6e6b64), style: 3 });
    };
    for (const c of CAPS) {
      if (c.kind !== 'deck') continue;
      const dg = flatPoly(band(TERRAIN.trenchW - 3, TERRAIN.trenchE + 3, c.z0, c.z1), null, c.dy + 0.12, true);
      const dp = dg.attributes.position;
      for (let i = 0; i < dp.count; i++) dp.setY(i, dp.getY(i) + frontDem(dp.getZ(i)));
      parts.push({ geom: dg, color: new THREE.Color(c.dy < 0 ? 0x8f8a80 : 0x9a6a52), style: 3 });
      for (const ze of [c.z0, c.z1]) {
        const deckY = frontDem(ze) + c.dy + 0.12;
        portalFace(ze, deckY + 0.02, 0.55);
      }
    }
    // the park cap swallows I-95 too: portal faces at both lawn edges
    {
      const pk = CAPS.find(c => c.kind === 'park');
      for (const ze of [pk.z0, pk.z1]) {
        const [mx] = frontPt(40, ze);
        portalFace(ze, parkCapY(mx, ze) + 0.1, 0.6);
      }
    }
    // Park at Penn's Landing: lawn from Front St down to the promenade
    const park = CAPS.find(c => c.kind === 'park');
    {
      const poly = [frontPt(TERRAIN.trenchW - 3, park.z0), [xShore(park.z0) - 12, park.z0], [xShore(park.z1) - 12, park.z1], frontPt(TERRAIN.trenchW - 3, park.z1)];
      parts.push({ geom: drapedPoly(poly, LAYER.park, 12), color: new THREE.Color(COLORS.park), style: 3 });
      for (let i = 0; i < 70; i++) {
        const z = lerp(park.z0 + 8, park.z1 - 8, hash01(i * 2.3 + 9));
        const [xf] = frontPt(TERRAIN.trenchW + 8, z);
        extraTreeSpots.push([lerp(xf, xShore(z) - 26, hash01(i * 1.7 + 3)), z]);
      }
    }
    // riverfront promenade just inside the bulkhead
    {
      const inner = [], outer = [];
      for (let z = -1100; z <= 1700; z += 10) { inner.push([xShore(z) - 11, z]); outer.push([xShore(z) - 0.6, z]); }
      parts.push({ geom: flatPoly(inner.concat(outer.reverse()), null, 0.3), color: new THREE.Color(0xa9a49a), style: 3 });
    }
    // DoubleSide: the cap decks must read from BELOW too (driving the trench)
    const m = new THREE.Mesh(mergeColored(parts), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, side: THREE.DoubleSide }));
    m.receiveShadow = true;
    groupCity.add(m);
  });

  step('Paving the streets', () => {
    const asphaltParts = [], brickParts = [];
    const cBrickWalk = new THREE.Color(COLORS.footway);
    const cConcWalk = new THREE.Color(0x9b968a);
    // with the outer districts loaded, core streets stop at the core boundary (the wide set draws the rest)
    const haveWide = typeof WIDE_B64 !== 'undefined' && !!WIDE_B64;
    const M = 40;
    const insideM = (q) => q[0] >= CORE_EXT.x0 - M && q[0] <= CORE_EXT.x1 + M && q[1] >= CORE_EXT.z0 - M && q[1] <= CORE_EXT.z1 + M;
    const runsOf = (pts) => {
      if (!haveWide) return [pts];
      const runs = []; let cur = [];
      for (let i = 0; i < pts.length; i++) {
        const keep = insideM(pts[i]) || (i > 0 && insideM(pts[i - 1])) || (i + 1 < pts.length && insideM(pts[i + 1]));
        if (keep) cur.push(pts[i]); else { if (cur.length > 1) runs.push(cur); cur = []; }
      }
      if (cur.length > 1) runs.push(cur);
      return runs;
    };
    // I-95 itself runs DOWN in the trench (cross streets bridge over it); without
    // this its lanes float at city level and the dark trench floor shows between
    // them as glitchy patches from above
    const motY = (x, z) => {
      // band edges must match siteY's trench band exactly, and blend down over a ramp
      // length (a binary band left 7 m vertex spikes where densified points straddled it);
      // beyond the trench mesh's z-extent the lanes climb back to grade
      const o = frontOff(x, z);
      const base = siteY(x, z, 'road');
      if (o <= TERRAIN.trenchW || o >= TERRAIN.trenchE) return base;
      const eo = Math.min(o - TERRAIN.trenchW, TERRAIN.trenchE - o) / 14;
      const ez = Math.min(z - (CORE_EXT.z0 + 4), (CORE_EXT.z1 - 4) - z) / 60;
      const t = clamp(Math.min(eo, ez), 0, 1);
      const ts = t * t * (3 - 2 * t);
      return lerp(base, TERRAIN.trenchFloor + 0.55, ts);
    };
    for (const r of D.roads) {
      if (r.pts.length < 2) continue;
      if (/Delancey|Cypress|American|Philip|Stamper|Addison|Panama|Peter's Way|Naudain|Kenilworth/i.test(r.name || '')) r.w = Math.min(r.w, 6);
      const foot = /footway|path|steps|pedestrian|cycleway/.test(r.t);
      const mot = /motorway/.test(r.t);
      const y = foot ? LAYER.footway : LAYER.road;
      const setts = /Dock Street/i.test(r.name || '') || (/2nd Street/i.test(r.name || '') && r.pts[0][1] > 250 && r.pts[0][1] < 420);
      for (const run of runsOf(r.pts)) {
        const g = ribbon(run, r.w, y, mot ? motY : null);
        if (!/footway|path|steps|cycleway/.test(r.t)) {
          for (let i = 0; i < run.length - 1; i++) {
            addRoadSeg(run[i][0], run[i][1], run[i + 1][0], run[i + 1][1], r.w / 2);
            if (!/pedestrian/.test(r.t)) septaRoadAdd(run[i][0], run[i][1], run[i + 1][0], run[i + 1][1]);
          }
        }
        (foot ? brickParts : asphaltParts).push({ geom: g, color: new THREE.Color(foot ? COLORS.footway : (setts ? 0x4d4a46 : COLORS.asphalt)) });
        // sidewalks flanking real streets: brick in the rowhouse core, concrete on arterials
        if (/^(residential|tertiary|living_street|unclassified|secondary|primary)$/.test(r.t)) {
          const walkCol = /residential|tertiary|living_street/.test(r.t) ? cBrickWalk : cConcWalk;
          const off = r.w / 2 + 1.55;
          for (const s of [-1, 1]) brickParts.push({ geom: ribbon(offsetPolyline(run, off * s), 3.0, LAYER.sidewalk), color: walkCol });
        }
      }
    }
    const asphalt = new THREE.Mesh(
      mergeColored(asphaltParts),
      new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95 })
    );
    asphalt.receiveShadow = true;
    groupCity.add(asphalt);
    const brick = new THREE.Mesh(
      mergeColored(brickParts),
      new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.9 })
    );
    brick.receiveShadow = true;
    groupCity.add(brick);
  });

  step('Planting parks and piers', () => {
    const parkParts = [], pierParts = [];
    for (const a of D.areas || []) {
      if (a.poly.length < 3) continue;
      if (a.kind === 'park') {
        const shade = lerp(0.9, 1.1, hash01(a.poly[0][0]));
        const c = new THREE.Color(COLORS.park).multiplyScalar(shade);
        const pa = Math.abs(signedArea(a.poly));
        parkParts.push({ geom: pa > 700 ? drapedPoly(a.poly, LAYER.park, 10) : flatPoly(a.poly, null, LAYER.park), color: c });
      } else if (a.kind === 'pier') {
        const [pcx, pcz] = polyCentroid(a.poly);
        const pg = extrudePoly(a.poly, null, 1.4, 0);
        pg.translate(0, siteY(pcx, pcz, 'ground'), 0);
        pierParts.push({ geom: pg, color: new THREE.Color(COLORS.pier) });
      }
    }
    if (parkParts.length) {
      const parks = new THREE.Mesh(
        mergeColored(parkParts),
        new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1 })
      );
      parks.receiveShadow = true;
      groupCity.add(parks);
    }
    if (pierParts.length) {
      const piers = new THREE.Mesh(
        mergeColored(pierParts),
        new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.9 })
      );
      piers.castShadow = piers.receiveShadow = true;
      groupCity.add(piers);
    }
  });

  // ------------------------------------------------ the city fabric
  const buildingPalette = {
    worship: [0xb3a68e, 0x9d8e77],
    church: [0xb3a68e, 0x9d8e77],
    school: [0xa89a82, 0xb0a28a],
    civic: [0xa89a82, 0xb0a28a],
    garage: [0x8a8578, 0x94907f],
    parking: [0x8a8578, 0x94907f],
    retail: [0x9d968a, 0xa8a191],
    commercial: [0x9d968a, 0x8f887b],
    office: [0x9d968a, 0x8f887b],
    hotel: [0xa39a8a, 0xb0a695],
    brick: [0x9b5a43, 0x8f5140, 0xa56a4e, 0x7d4a3a, 0x94523d, 0xa05f47],
    painted: [0xb8a894, 0xc4b49b, 0xa79a86],
  };
  const highrisePool = [0x8f8d84, 0x9aa0a4, 0xb3aca0, 0x83817c, 0xa39d92];
  // ---- Tier-1 facade attributes: OPA parcel classes + sampled roof palette ----
  // stored -> rendered on sunlit tops measured as R = 31.5 * S^0.423 (legacy-linear
  // lift + ACES compress darks far more than lights); invert per channel so the
  // rendered roof matches the ortho-sampled sRGB. Calibrated by canvas-pixel probe.
  const roofInv = (t) => Math.min(1, Math.pow(Math.max(t, 4) / 31.5, 2.364) / 255);
  const ROOF_PAL = (typeof FACADE_PAL !== 'undefined' && FACADE_PAL && FACADE_PAL.roof)
    ? FACADE_PAL.roof.map(cc => new THREE.Color(roofInv(cc[0]), roofInv(cc[1]), roofInv(cc[2]))) : null;
  const OPA_POOLS = {
    masOld: [0x8f5140, 0x9b5a43, 0x7d4a3a, 0x94523d, 0x86503f, 0xa05f47],
    mas1900: [0x9b5a43, 0xa56a4e, 0x9a6b55, 0x8d5a45, 0x965c46],
    masPost: [0xa56a4e, 0xb07a58, 0x9a7a62, 0xa88a70, 0x8d8478],
    masMod: [0x8a5f4a, 0x9c8874, 0xa89272, 0x8d8a86],
    frame: [0xb8a894, 0xc4b49b, 0xa8a494, 0x9aa08f, 0xb0b4ac, 0xc0bcae],
    stone: [0x8a8274, 0x7b7365, 0x948c7c, 0x6e685c],
    mixed: [0x9d968a, 0x9a6b55, 0x8f887b, 0xa89a86],
    com: [0x9d968a, 0x8f887b, 0xa8a191, 0x83817c],
    ind: [0x8a7e72, 0x7b736b, 0x9c9286, 0x8e5a48],
  };
  // fa = [use, mat, era, stories] -> wall color pool (null = keep the type logic)
  function opaWallPool(fa) {
    const u = fa[0], m = fa[1], e = fa[2];
    if (u === 5) return OPA_POOLS.ind;
    if (u === 4 && m !== 0) return OPA_POOLS.com;
    if (m === 1) return OPA_POOLS.frame;
    if (m === 2) return OPA_POOLS.stone;
    if (m === 3) return OPA_POOLS.mixed;
    if (m === 0) return e <= 2 ? OPA_POOLS.masOld : e === 3 ? OPA_POOLS.mas1900
      : e === 4 ? OPA_POOLS.masPost : e >= 8 ? OPA_POOLS.mas1900 : OPA_POOLS.masMod;
    return null;
  }
  // facade style from the OPA use/era codes (8 = shutterless post-war rowhouse)
  function opaStyle(fa, h) {
    const u = fa[0], e = fa[2];
    if (u === 3 || u === 4) return h > 16 ? 2 : 5;
    if (u === 5) return 3;
    return (e >= 4 && e <= 7) ? 8 : 0;
  }
  function buildingColor(b, i) {
    const h = hash01(i * 7.13);
    let pool;
    const t = b.t || 'generic';
    // modern high-rises read as curtain wall / precast, never rowhouse brick
    if (b.h > 35 && t !== 'church' && t !== 'worship') pool = highrisePool;
    else if (b.fa && t !== 'church' && t !== 'worship' && t !== 'school' && t !== 'civic') pool = opaWallPool(b.fa);
    if (!pool) {
    if (buildingPalette[t]) pool = buildingPalette[t];
    else if (t === 'house' || t === 'residential' || t === 'terrace' || t === 'apartments' || t === 'detached' || t === 'semidetached_house')
      pool = h < 0.14 ? buildingPalette.painted : buildingPalette.brick;
    else if (t === 'generic') {
      const area = Math.abs(signedArea(b.poly));
      pool = area < 350 ? (h < 0.16 ? buildingPalette.painted : buildingPalette.brick) : buildingPalette.commercial;
    } else pool = buildingPalette.commercial;
    }
    const base = new THREE.Color(pool[Math.floor(hash01(i * 3.7) * pool.length) % pool.length]);
    const l = 0.92 + hash01(i * 11.3) * 0.16;
    return base.multiplyScalar(l);
  }

  // buildings with researched custom models skip the generic extruder;
  // 'recolor' specs keep generic geometry with corrected colors/heights
  const REALISM = {
    'The Ryland': { mode: 'custom' },
    'Philadelphia Marriott Old City': { mode: 'custom' },
    'Head House': { mode: 'custom' },
    'Head House Market': { mode: 'custom', open: true },
    "Merchants' Exchange Building": { mode: 'custom' },
    'City Tavern': { mode: 'custom' },
    'Hill-Physick House': { mode: 'custom' },
    'Powel House': { mode: 'custom' },
    'Man Full of Troubles Tavern': { mode: 'custom' },
    "Saint Peter's Church": { mode: 'custom' },
    'Old Pine Street Church': { mode: 'custom' },
    'Mother Bethel African Methodist Episcopal Church': { mode: 'custom' },
    "Old Saint Mary's Church": { mode: 'custom' },
    "Old Saint Joseph's Church": { mode: 'custom' },
    "Old Saint Paul's Church": { mode: 'custom' },
    'Independence Seaport Museum': { mode: 'custom' },
    'Society Hill Synagogue': { mode: 'recolor', color: 0xd2d4d0 },
    'Athenaeum of Philadelphia': { mode: 'recolor', color: 0x7b5844 },
    'Hopkinson House': { mode: 'recolor', color: 0xcfc0a4, h: 92, style: 7 },
    'One Independence Place': { mode: 'recolor', color: 0x5d4536 },
    '2 Independence Place': { mode: 'recolor', color: 0x5d4536 },
    'United States Custom House': { mode: 'custom' },
    'Man Full of Troubles Tavern': { mode: 'custom' },
    "Hilton Philadelphia at Penn's Landing": { mode: 'custom' },
    'Independence Hall': { mode: 'custom' },
    'Congress Hall': { mode: 'custom' },
    'Old City Hall': { mode: 'custom' },
    "Carpenters' Hall": { mode: 'custom' },
    'Second Bank of the United States': { mode: 'custom' },
    'First Bank of the United States': { mode: 'custom' },
    'New Market Garage': { mode: 'custom', key: 'garage' },
    'Penn Mutual Tower': { mode: 'recolor', color: 0x8f8b82 },
    'The Residences at Dockside': { mode: 'custom' },
    'The Moravian': { mode: 'recolor', color: 0x8f4a3a },
    '101 Walnut': { mode: 'recolor', color: 0x96513f },
    'Public Ledger Building': { mode: 'recolor', color: 0x8e4438 },
    'The Curtis Center': { mode: 'recolor', color: 0x8a4034 },
  };
  const upgraded = new Map(); // building object -> realism spec

  step('Raising 2,800 buildings', () => {
    // unnamed footprints identified by location (Philadelphia OPA parcels + 2017 LiDAR)
    const REALISM_NEAR = [
      { x: -140, z: 433, r: 60, minArea: 3000, spec: { mode: 'custom', key: 'abbotts' } },   // Abbotts Square
      { x: 44, z: 334, r: 30, minArea: 1500, spec: { mode: 'custom', key: 'ten410' } },      // 410 at Society Hill
      { x: -18, z: 345, r: 25, minArea: 900, spec: { mode: 'custom', key: 'newmarket' } },   // New Market Complex
      // Glory Beer Bar & Kitchen, 126 Chestnut — MID-BLOCK between Front and 2nd
      // (numbers ascend westward from Front): the deep narrow lot whose front
      // hits the address line, area-weighted centroid (115.1, -283.8)
      { x: 115.1, z: -283.8, r: 5, minArea: 100, spec: { mode: 'custom', key: 'glory' } },
      // Rotten Ralph's, 201 Chestnut — NW corner of 2nd & Chestnut. OSM maps the
      // lot as two shallow strips front-to-back; both go custom and the builder
      // spans them with one massing. The taller rear mass (the graffiti party
      // wall in photos) stays generic but recolored to its real dark brick.
      { x: 43.5, z: -334.3, r: 4, minArea: 40, spec: { mode: 'custom', key: 'ralphs' } },
      { x: 44.4, z: -339.1, r: 4, minArea: 40, spec: { mode: 'custom', key: 'ralphsMid' } },
      { x: 45.6, z: -346.8, r: 4, minArea: 100, spec: { color: '#452a20', style: 3 } },
    ];
    for (const b of D.buildings) {
      if (b.name && REALISM[b.name]) { upgraded.set(b, REALISM[b.name]); continue; }
      if (!b.name && b.poly && b.poly.length >= 3) {
        const [cx, cz] = polyCentroid(b.poly);
        const ar = Math.abs(signedArea(b.poly));
        for (const nr of REALISM_NEAR) {
          if (ar >= nr.minArea && Math.hypot(cx - nr.x, cz - nr.z) < nr.r) { upgraded.set(b, nr.spec); break; }
        }
      }
    }
    const parts = [];
    const roofPalette = [0x45423e, 0x3a3835, 0x54504a, 0x6b4a3d, 0x5d5952];
    for (let i = 0; i < D.buildings.length; i++) {
      const b = D.buildings[i];
      if (!b.poly || b.poly.length < 3) continue;
      if (b.t === 'ship') continue; // hulls are built in their own step
      const p0 = parts.length;
      const spec0 = upgraded.get(b);
      if (spec0 && spec0.mode === 'custom') {
        registerPoly(b.poly); // keeps trees out of the footprint
        if (!spec0.open) {    // open structures (market sheds) stay walkable
          for (let k = 0; k < b.poly.length; k++) {
            const p = b.poly[k], q = b.poly[(k + 1) % b.poly.length];
            addColSeg(p[0], p[1], q[0], q[1]);
          }
        }
        continue;
      }
      if (spec0 && spec0.h) b.h = spec0.h;
      const color = spec0 && spec0.color ? new THREE.Color(spec0.color) : buildingColor(b, i);
      const t = b.t || 'generic';
      const area = Math.abs(signedArea(b.poly));
      // paper-thin OSM slivers (party walls and alley strips mapped as buildings)
      // extrude into tall floating blades that read as broken roofs — clamp
      // anything with an effective width under ~1.7 m down to garden-wall height
      if (!b.minH && b.h > 4) {
        let perim = 0;
        for (let k2 = 0; k2 < b.poly.length; k2++) {
          const p2 = b.poly[k2], q2 = b.poly[(k2 + 1) % b.poly.length];
          perim += Math.hypot(q2[0] - p2[0], q2[1] - p2[1]);
        }
        if ((2 * area) / Math.max(1, perim) < 1.7) b.h = 3.2;
      }
      // facade vocabulary: 0 Georgian rowhouse, 1 church, 2 modern slab, 3 blank, 4 civic arched base, 5 storefront
      const style = spec0 && spec0.style != null ? spec0.style
        : (b.h > 35 || t === 'garage' || t === 'parking') ? 2
        : (t === 'church' || t === 'worship') ? 1
        : b.fa ? opaStyle(b.fa, b.h)
        : (t === 'retail' || t === 'commercial' || t === 'hotel' || t === 'office') ? 5 : 0;
      const trimCol = hash01(i * 2.9) < 0.62 ? new THREE.Color(0xe9e3d3) : new THREE.Color(0x3d3935);
      // roof source: LiDAR-measured form when the 2022 flight resolved one
      // (b.roof = [form, eave, ridge, ridgeRad] from lidar_core.py, form
      // 1 gable / 2 hip, [0] = measured flat — which stays flat, no lottery),
      // else the original hash-lottery guess for plausible rowhouse quads
      let quad = null;
      const mr = Array.isArray(b.roof) && !(spec0 && spec0.h) ? b.roof : null;
      const mForm = mr ? mr[0] : -1;
      const resType = ['house', 'residential', 'terrace', 'apartments', 'detached', 'semidetached_house', 'generic'].includes(t);
      // guessed gables only at true rowhouse height — 14-15 m four-story commercial
      // lofts (Old City, Chestnut St) are flat-roofed, and their long strips gabled
      // into edge-on "blade" slopes towering over the streetwall
      const wantPitch = mr ? (mForm === 1 || mForm === 2) && mr[2] - mr[1] >= 0.8
        : (resType && area < 280 && b.h < 12.5 && hash01(i * 13.7) < 0.8);
      if (wantPitch && !b.minH && (!b.holes || !b.holes.length) && area < (mr ? 650 : 280) && b.poly.length <= (mr ? 10 : 8)) {
        const sp = simplifyRing(b.poly, 0.45);
        if (sp.length === 4) {
          // gables demand an honest rowhouse quad: convex, near-rectangular
          // corners, clearly elongated, and covering the same area as the real
          // footprint. Skewed diamonds tent into leaning pyramids, squarish
          // quads read as spikes, and chopped outlines hang their roof past
          // the walls — all of Mike's "broken roofs". Anything dodgy stays a
          // flat extrusion of the TRUE footprint.
          let convex = true, sgn = 0, rect = true;
          for (let k2 = 0; k2 < 4; k2++) {
            const A2 = sp[k2], B2 = sp[(k2 + 1) % 4], C2 = sp[(k2 + 2) % 4];
            const ux2 = B2[0] - A2[0], uz2 = B2[1] - A2[1], vx2 = C2[0] - B2[0], vz2 = C2[1] - B2[1];
            const cr = ux2 * vz2 - uz2 * vx2;
            if (Math.abs(cr) > 1e-6) {
              if (sgn === 0) sgn = Math.sign(cr);
              else if (Math.sign(cr) !== sgn) { convex = false; break; }
            }
            const l1 = Math.hypot(ux2, uz2) || 1, l2 = Math.hypot(vx2, vz2) || 1;
            if (Math.abs((ux2 * vx2 + uz2 * vz2) / (l1 * l2)) > 0.35) rect = false;
          }
          const e = [0, 1, 2, 3].map(k => Math.hypot(sp[(k + 1) % 4][0] - sp[k][0], sp[(k + 1) % 4][1] - sp[k][1]));
          const span = Math.min((e[0] + e[2]) / 2, (e[1] + e[3]) / 2);
          const long = Math.max((e[0] + e[2]) / 2, (e[1] + e[3]) / 2);
          const aQ = Math.abs(signedArea(sp));
          const elMin = mForm === 2 ? 1.02 : (mr ? 1.2 : 1.35);
          if (convex && rect && Math.abs(aQ - area) <= area * 0.14 &&
            span > 3.2 && span < (mr ? 17 : 13) && long / span >= elMin && long / span < 5) quad = sp;
        }
      }
      // measured floor pitch: OPA stories against the LiDAR height (eave for pitched)
      let flhV = 0;
      if (b.fa && b.fa[3]) {
        const hEff = mr && mForm > 0 ? mr[1] : b.h;
        const r2 = hEff / b.fa[3];
        if (r2 >= 2.2 && r2 <= 5.2) flhV = Math.min(4.6, r2);
      }
      try {
        if (quad) {
          let eaveH, ridgeTop, rrad = null;
          if (mr) {
            eaveH = Math.max(2.6, mr[1]); ridgeTop = mr[2]; rrad = mr[3];
            if (ridgeTop - eaveH < 0.8) eaveH = Math.max(2.2, ridgeTop - 0.8);
          } else {
            const e = [0, 1, 2, 3].map(k => Math.hypot(quad[(k + 1) % 4][0] - quad[k][0], quad[(k + 1) % 4][1] - quad[k][1]));
            const span = Math.min((e[0] + e[2]) / 2, (e[1] + e[3]) / 2);
            let rise = clamp(span * 0.42, 1.4, 3.6);
            if (b.h - rise < 3.4) rise = Math.max(1.2, b.h - 3.4);
            eaveH = b.h - rise; ridgeTop = b.h + 0.05;
          }
          parts.push({ geom: buildingGeom(quad, null, eaveH, -1.5), color, style, flh: flhV });
          const roofCol = (b.rp != null && ROOF_PAL)
            ? ROOF_PAL[b.rp].clone().multiplyScalar(0.92 + hash01(i * 8.9) * 0.18)
            : new THREE.Color(roofPalette[Math.floor(hash01(i * 3.1) * roofPalette.length) % roofPalette.length])
              .multiplyScalar(0.9 + hash01(i * 8.9) * 0.25);
          const g = mForm === 2 ? quadHip(quad, eaveH, ridgeTop, rrad) : quadGable(quad, eaveH, ridgeTop, rrad);
          parts.push({ geom: g.slopes, color: roofCol, style: 3 });
          if (g.ends) parts.push({ geom: g.ends, color, style, flh: flhV });
          // eave boards laid exactly along the wall's eave edges
          for (const ev of g.eaves) {
            const exd = ev.b[0] - ev.a[0], ezd = ev.b[1] - ev.a[1];
            parts.push({
              geom: box(ev.len + 0.1, 0.36, 0.5,
                (ev.a[0] + ev.b[0]) / 2, eaveH - 0.1, (ev.a[1] + ev.b[1]) / 2,
                Math.atan2(-ezd, exd)),
              color: trimCol, style: 3,
            });
          }
          const nCh = hash01(i * 5.3) < 0.72 ? (hash01(i * 7.9) < 0.4 ? 2 : 1) : 0;
          const chH = Math.min(ridgeTop - eaveH, 3.8) + 1.7;
          const rl = Math.hypot(g.ridge[1][0] - g.ridge[0][0], g.ridge[1][1] - g.ridge[0][1]) || 1;
          const rdx = (g.ridge[1][0] - g.ridge[0][0]) / rl, rdz = (g.ridge[1][1] - g.ridge[0][1]) / rl;
          for (let c = 0; c < nCh; c++) {
            const rp = c === 0 ? g.ridge[0] : g.ridge[1];
            const s = c === 0 ? 1 : -1;
            parts.push({
              geom: box(0.95, chH, 0.55,
                rp[0] + rdx * s * 1.0, eaveH + chH / 2, rp[1] + rdz * s * 1.0,
                Math.atan2(-rdz, rdx)),
              color: new THREE.Color(0x6a4132).multiplyScalar(0.88 + hash01(i * 11.7) * 0.22),
            });
          }
        } else {
          // a measured pitched roof whose footprint failed the honest-quad guards
          // drops to a flat extrusion at the roof's mean surface height — never a
          // floating slope (the session's roof rule)
          const hFlat = (mr && mForm > 0) ? Math.max(3, mr[1] + 0.35 * (mr[2] - mr[1])) : b.h;
          parts.push({ geom: buildingGeom(b.poly, b.holes, hFlat, b.minH ? b.minH : -1.5), color, style, flh: flhV });
          // sampled roof color as a thin overlay cap. It must clear the cornice
          // SLAB (a solid extrusion to hFlat+0.06 whose cream top used to play
          // "roof" on every rowhouse) - 9 cm up, deterministic, never coplanar;
          // the slab edge below reads as the cornice lip.
          if (b.rp != null && ROOF_PAL && !b.minH) {
            try {
              parts.push({ geom: capGeom(b.poly, b.holes, hFlat + 0.09),
                color: ROOF_PAL[b.rp].clone().multiplyScalar(0.94 + hash01(i * 8.9) * 0.14), style: 3 });
            } catch (e2) {}
          }
          // flat-roofed rowhouses get a projecting cornice ring at the parapet
          if (resType && !b.minH && (!b.holes || !b.holes.length) && area < 320 && hFlat < 18 && b.poly.length <= 10) {
            const [ccx, ccz] = polyCentroid(b.poly);
            const ring = b.poly.map(pt => {
              const dx = pt[0] - ccx, dz = pt[1] - ccz, L = Math.hypot(dx, dz) || 1;
              return [pt[0] + (dx / L) * 0.3, pt[1] + (dz / L) * 0.3];
            });
            parts.push({ geom: extrudePoly(ring, null, hFlat + 0.06, hFlat - 0.42), color: trimCol, style: 3 });
          }
        }
      } catch (e) { continue; }
      {
        const [lx, lz] = polyCentroid(b.poly);
        const ty = siteY(lx, lz, 'ground');
        if (ty) for (let k = p0; k < parts.length; k++) { parts[k].geom.translate(0, ty, 0); parts[k].baseY = ty; }
      }
      registerPoly(b.poly);
      for (let k = 0; k < b.poly.length; k++) {
        const p = b.poly[k], q = b.poly[(k + 1) % b.poly.length];
        addColSeg(p[0], p[1], q[0], q[1]);
      }
    }
    const mesh = new THREE.Mesh(mergeColored(parts, true), cityMat);
    mesh.castShadow = mesh.receiveShadow = true;
    groupCity.add(mesh);
    rayTargets.push(mesh);
  });

  // procedural windows: world-space grid darkening on wall faces only
  // (shared by the generic fabric and landmark walls)
  const nightUniform = { value: 0 };
  let towerGlassMat = null, towerVarMat = null, rylandGlassMat = null, outerGlassMat = null;
  const groundMats = [];   // bare-earth planes retinted by time of day (pale day tone reads as water at dusk/night)
  const cityMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.92, metalness: 0, envMapIntensity: 0.25 });
  {
    cityMat.onBeforeCompile = (shader) => {
      shader.uniforms.uNight = nightUniform;
      cityMat.userData.shader = shader;
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nattribute float aStyle; attribute float aFloorH; attribute float aWallU; attribute float aWallL; attribute float aWallH; attribute float aBase;\nvarying vec3 vWPos; varying vec3 vWNorm; varying float vStyle; varying float vFloorH; varying float vWallU; varying float vWallL; varying float vWallH; varying float vBase;')
        .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;\nvWNorm = normalize(mat3(modelMatrix) * objectNormal);\nvStyle = aStyle; vFloorH = aFloorH; vWallU = aWallU; vWallL = aWallL; vWallH = aWallH; vBase = aBase;');
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', [
          '#include <common>',
          'uniform float uNight;',
          'varying vec3 vWPos; varying vec3 vWNorm; varying float vStyle; varying float vFloorH; varying float vWallU; varying float vWallL; varying float vWallH; varying float vBase;',
          'float shtLit = 0.0;',
          'float shtHash(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }',
          'float rectM(vec2 m, vec2 c, vec2 s, float aa){ vec2 d = abs(m - c) - s * 0.5; return 1.0 - smoothstep(-aa, aa, max(d.x, d.y)); }',
          'float archM(vec2 m, vec2 c, float w, float h, float aa){ float r = w * 0.5; float dR = max(abs(m.x - c.x) - r, max(c.y - m.y, m.y - (c.y + h - r))); float dC = max(length(vec2(m.x - c.x, m.y - (c.y + h - r))) - r, (c.y + h - r) - m.y); return 1.0 - smoothstep(-aa, aa, min(dR, dC)); }',
        ].join('\n'))
        .replace('#include <color_fragment>', [
          '#include <color_fragment>',
          '{',
          '  vec3 n = normalize(vWNorm);',
          '  int st = int(vStyle + 0.5);',
          '  float v = vWPos.y - vBase;',
          '  if (abs(n.y) < 0.35 && st != 3 && v > 0.0) {',
          '    bool local = vWallL > 0.5;',
          '    float uW;',
          '    if (local) { uW = vWallU; } else { vec2 dir = normalize(n.xz); vec2 perp = vec2(-dir.y, dir.x); uW = dot(vWPos.xz, perp); }',
          '    float aa = 0.6 * max(fwidth(uW), fwidth(v)) + 0.004;',
          // detail fade keys off the vertical derivative only: fwidth(uW) explodes on
          // edge-on walls and used to blank whole facades at grazing angles. detU still
          // gates the BINARY per-column terms (shutters/doors) that would shimmer there.
          '    float det = clamp(1.0 - (0.6 * fwidth(v) + 0.004 - 0.16) / 0.42, 0.0, 1.0);',
          '    float detU = clamp(1.0 - (0.6 * fwidth(uW) + 0.004 - 0.16) / 0.42, 0.0, 1.0);',
          '    float wallTop = local ? vWallH - 0.25 : 1.0e4;',
          '    float brickish = step(diffuseColor.g * 1.12, diffuseColor.r);',
          '    vec3 frameCol = vec3(0.90, 0.88, 0.82);',
          '    vec3 stoneCol = vec3(0.80, 0.76, 0.68);',
          '    vec3 col = diffuseColor.rgb;',
          '    float lit = 0.0, glass = 0.0;',
          '    if (st == 1) {',
          '      float pitch = 4.4;',
          '      float nb = local ? max(1.0, floor(vWallL / pitch)) : 1.0e6;',
          '      float u = local ? uW - (vWallL - nb * pitch) * 0.5 : uW;',
          '      float inWall = local ? step(0.0, u) * step(u, nb * pitch) : 1.0;',
          '      float cu = floor(u / pitch);',
          '      vec2 m = vec2(u - (cu + 0.5) * pitch, v);',
          '      lit = 0.5 + 0.5 * shtHash(vec2(cu, 3.1));',
          '      vec3 gc = vec3(0.08, 0.09, 0.12) + vec3(0.10, 0.09, 0.06) * lit;',
          '      float okU = step(8.9, wallTop) * inWall * det;',
          '      float okL = step(3.2, wallTop) * inWall * det;',
          '      float fmU = archM(m, vec2(0.0, 4.85), 1.68, 3.9, aa) * okU;',
          '      float wmU = archM(m, vec2(0.0, 5.0), 1.4, 3.6, aa) * okU;',
          '      float fmL = rectM(m, vec2(0.0, 1.95), vec2(1.44, 2.14), aa) * okL;',
          '      float wmL = rectM(m, vec2(0.0, 1.95), vec2(1.2, 1.9), aa) * okL;',
          '      col = mix(col, stoneCol, (fmL - wmL) * 0.8);',
          '      col = mix(col, frameCol, (fmU - wmU) * 0.85);',
          '      glass = max(wmU, wmL);',
          '      col = mix(col, gc, glass * 0.92);',
          '      float tr = glass * max(1.0 - smoothstep(0.03, 0.03 + aa, abs(m.x)), max(1.0 - smoothstep(0.025, 0.025 + aa, abs(m.y - 6.6)), 1.0 - smoothstep(0.025, 0.025 + aa, abs(m.y - 2.0))));',
          '      col = mix(col, frameCol, tr * 0.8);',
          '    } else if (st == 2 || st == 6) {',
          '      float pitch = (st == 6) ? 3.6 : 3.0;',
          '      float fp = (st == 6) ? 3.15 : (vFloorH > 5.0 ? vFloorH * 0.1 : 2.95);',
          '      float nb = local ? max(1.0, floor(vWallL / pitch)) : 1.0e6;',
          '      float u = local ? uW - (vWallL - nb * pitch) * 0.5 : uW;',
          '      float inWall = local ? step(0.0, u) * step(u, nb * pitch) : 1.0;',
          '      vec2 cell = vec2(floor(u / pitch), floor(v / fp));',
          '      vec2 m = vec2(u - (cell.x + 0.5) * pitch, v - cell.y * fp);',
          '      float okRow = step(cell.y * fp + 2.5, wallTop) * inWall * det;',
          '      float wm = rectM(m, vec2(0.0, 1.55), vec2(pitch * 0.74, 1.95), aa) * step(0.9, v) * okRow;',
          '      lit = 0.45 + 0.55 * shtHash(cell * 1.3 + 7.0);',
          '      vec3 gc = vec3(0.10, 0.12, 0.15) + vec3(0.12, 0.11, 0.08) * lit;',
          '      if (st == 6 && v < 6.3) {',
          '        vec2 mg = vec2(u - (floor(u / 5.4) + 0.5) * 5.4, v);',
          '        float sf = rectM(mg, vec2(0.0, 3.3), vec2(4.7, 5.3), aa) * inWall * det;',
          '        float sg = rectM(mg, vec2(0.0, 3.3), vec2(4.3, 4.9), aa) * inWall * det;',
          '        col = mix(col, vec3(0.12, 0.11, 0.10), sf * 0.9);',
          '        col = mix(col, vec3(0.22, 0.25, 0.28), sg * 0.9);',
          '        wm = 0.0; glass = sg;',
          '      }',
          '      col = mix(col, gc, wm * 0.9);',
          '      col = mix(col, gc * 0.6, wm * (1.0 - smoothstep(0.03, 0.03 + aa, abs(m.x))) * 0.8);',
          '      col *= 1.0 - 0.10 * det * rectM(m, vec2(0.0, 0.38), vec2(pitch, 0.44), aa);',
          '      glass = max(glass, wm);',
          '    } else if (st == 7) {',
          '      float fp = 2.75;',
          '      float nb = local ? max(1.0, floor(vWallL / 3.4)) : 1.0e6;',
          '      float u7 = local ? uW - (vWallL - nb * 3.4) * 0.5 : uW;',
          '      float inWall = local ? step(0.0, u7) * step(u7, nb * 3.4) : 1.0;',
          '      float row = floor(v / fp);',
          '      float bandV = v - row * fp;',
          '      float ok = inWall * det * step(2.0, v) * step((row + 1.0) * fp, wallTop + 1.3);',
          '      float gBand = rectM(vec2(0.0, bandV), vec2(0.0, 1.45), vec2(9999.0, 1.8), aa) * ok;',
          '      lit = 0.5 + 0.5 * shtHash(vec2(floor(u7 / 3.4), row) + 3.7);',
          '      vec3 gc7 = vec3(0.10, 0.12, 0.14) + vec3(0.10, 0.09, 0.07) * lit;',
          '      col = mix(col, gc7, gBand * 0.9);',
          '      glass = gBand;',
          '    } else {',
          '      float pitch = (st == 4) ? 3.0 : (st == 8 ? 2.35 : 1.9);',
          '      float fp = vFloorH > 5.0 ? vFloorH * 0.1 : 3.05;',
          '      float nb = local ? max(1.0, floor(vWallL / pitch)) : 1.0e6;',
          '      float u = local ? uW - (vWallL - nb * pitch) * 0.5 : uW;',
          '      float inWall = local ? step(0.0, u) * step(u, nb * pitch) : 1.0;',
          '      vec2 cell = vec2(floor(u / pitch), floor(v / fp));',
          '      vec2 m = vec2(u - (cell.x + 0.5) * pitch, v - cell.y * fp);',
          '      float ground = step(v, fp);',
          '      float ww = 0.95, wh = 1.75, sill = 0.85;',
          '      float okRow = step(cell.y * fp + sill + wh, wallTop) * inWall * det;',
          '      lit = 0.5 + 0.5 * shtHash(cell * 1.7 + 11.0);',
          '      vec3 gc = vec3(0.06, 0.07, 0.09) + vec3(0.10, 0.09, 0.06) * lit;',
          '      float doorCol = step(2.5, mod(cell.x, 3.0));',
          '      float isDoor = ground * doorCol * float(st == 0 || st == 8) * brickish * inWall * det * detU;',
          '      float isArch = ground * float(st == 4) * inWall * det;',
          '      float isShop = ground * float(st == 5) * inWall * det;',
          '      float sashOn = (1.0 - max(isDoor, max(isArch, isShop))) * okRow;',
          '      float win = rectM(m, vec2(0.0, sill + wh * 0.5), vec2(ww, wh), aa) * sashOn;',
          '      float frame = (rectM(m, vec2(0.0, sill + wh * 0.5), vec2(ww + 0.16, wh + 0.14), aa) - win) * sashOn;',
          '      vec2 wl = vec2((m.x + ww * 0.5) / ww, (m.y - sill) / wh);',
          '      float mun = win * max(1.0 - smoothstep(0.028, 0.028 + aa, abs(wl.x - 0.5)), max(1.0 - smoothstep(0.02, 0.02 + aa, abs(wl.y - 0.5)), max(1.0 - smoothstep(0.016, 0.016 + aa, abs(wl.y - 0.25)), 1.0 - smoothstep(0.016, 0.016 + aa, abs(wl.y - 0.75)))));',
          '      float lintel = rectM(m, vec2(0.0, sill + wh + 0.2), vec2(ww + 0.4, 0.24), aa) * sashOn * brickish;',
          '      float sillM = rectM(m, vec2(0.0, sill - 0.08), vec2(ww + 0.26, 0.12), aa) * sashOn * brickish;',
          '      float shut = (rectM(m, vec2(-(ww * 0.5 + 0.31), sill + wh * 0.5), vec2(0.44, wh), aa) + rectM(m, vec2(ww * 0.5 + 0.31, sill + wh * 0.5), vec2(0.44, wh), aa)) * sashOn;',
          '      float shOn = step(shtHash(vec2(cell.x * 0.37, 7.31)), 0.5) * brickish * float(st == 0) * detU;',
          '      vec3 shCol = mix(vec3(0.09, 0.13, 0.10), vec3(0.06, 0.06, 0.07), step(0.5, shtHash(vec2(cell.x, 2.17))));',
          '      col = mix(col, stoneCol, max(lintel, sillM) * 0.8);',
          '      col = mix(col, frameCol, frame * 0.9);',
          '      col = mix(col, gc, win * 0.92);',
          '      col = mix(col, frameCol, mun * 0.85);',
          '      col = mix(col, shCol, shut * shOn * 0.9);',
          '      float door = rectM(m, vec2(0.0, 1.45), vec2(1.0, 2.2), aa) * isDoor;',
          '      float dframe = (rectM(m, vec2(0.0, 1.5), vec2(1.26, 2.3), aa) - door) * isDoor;',
          '      float fan = (1.0 - smoothstep(0.52, 0.52 + aa, length(vec2(m.x, m.y - 2.55)))) * step(2.55, m.y) * isDoor;',
          '      float fanIn = (1.0 - smoothstep(0.42, 0.42 + aa, length(vec2(m.x, m.y - 2.55)))) * step(2.55, m.y) * isDoor;',
          '      float stepM = rectM(m, vec2(0.0, 0.17), vec2(1.5, 0.34), aa) * isDoor;',
          '      vec3 dCol = mix(vec3(0.10, 0.08, 0.06), vec3(0.05, 0.09, 0.13), step(0.5, shtHash(vec2(cell.x, 9.1))));',
          '      col = mix(col, frameCol, max(dframe, fan) * 0.9);',
          '      col = mix(col, dCol, door * 0.92);',
          '      col = mix(col, vec3(0.85, 0.83, 0.78) * (0.6 + 0.4 * lit), fanIn * 0.9);',
          '      col = mix(col, vec3(0.85, 0.83, 0.78), stepM * 0.85);',
          '      float archF = archM(m, vec2(0.0, 0.15), 1.9, 2.85, aa) * isArch;',
          '      float arch = archM(m, vec2(0.0, 0.15), 1.6, 2.7, aa) * isArch;',
          '      col = mix(col, frameCol, archF * 0.85);',
          '      col = mix(col, gc * 0.8, arch * 0.9);',
          '      float shopF = rectM(m, vec2(0.0, 1.7), vec2(1.66, 2.7), aa) * isShop;',
          '      float shop = rectM(m, vec2(0.0, 1.7), vec2(1.5, 2.5), aa) * isShop;',
          '      col = mix(col, vec3(0.18, 0.17, 0.16), shopF * 0.9);',
          '      col = mix(col, gc * 1.3, shop * 0.9);',
          '      glass = max(win, max(fanIn, max(arch, shop)));',
          '    }',
          '    // far away the pattern averages to the true facade mix — curtain-wall',
          '    // styles are ~half glass, so they must converge to a visibly darker',
          '    // average instead of washing back to the pale wall color',
          '    vec3 farAvg = diffuseColor.rgb * 0.9; float farW = 0.35;',
          '    if (st == 2 || st == 6 || st == 7) { farAvg = mix(diffuseColor.rgb, vec3(0.115, 0.13, 0.155), 0.48); farW = 0.92; }',
          '    col = mix(col, farAvg, (1.0 - det) * farW);',
          // only about a third of windows are lit at night, at varied warmth; where the
          // pattern fades with distance the facade keeps a soft aggregate glow instead
          // of dying into a solid mass
          '    float litOn = step(0.82, lit) * (0.4 + 0.6 * fract(lit * 9.7));',
          '    // past the per-window fade the facade keeps only the soft aggregate',
          '    // glow (the 3x2-window cluster LOD read as big yellow squares that',
          '    // popped away on approach, removed at the owner\'s request)',
          '    shtLit = mix(0.05, glass * litOn, det);',
          '    diffuseColor.rgb = col;',
          '  }',
          '}',
        ].join('\n'))
        .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance += vec3(1.0, 0.76, 0.46) * shtLit * uNight * 1.3;');
    };
  }

  // ------------------------------------------------ landmark spires
  function findBuilding(nameLike) {
    const re = new RegExp(nameLike.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');
    for (const b of D.buildings) if (b.name && re.test(b.name)) return b;
    return null;
  }
  step('Setting the steeples', () => {
    const parts = [];
    for (const lm of META_L) {
      if (!lm || !lm.spire_kind || lm.spire_kind === 'none' || !lm.spire_height_m) continue;
      const b = findBuilding(lm.name);
      if (!b || upgraded.has(b)) continue; // realism step builds these itself
      const [cx, cz] = polyCentroid(b.poly);
      // measured pitched roofs carry b.h = ridge; seat the steeple at the eave so
      // its base interpenetrates the slopes instead of floating at the ridge line
      const roof = (Array.isArray(b.roof) && b.roof.length > 3) ? b.roof[1] : b.h;
      const total = Math.max(lm.spire_height_m, (Array.isArray(b.roof) && b.roof.length > 3 ? b.roof[2] : roof) + 6);
      const rise = total - roof;
      const col = new THREE.Color(lm.color_hex || '#d9d2c2');
      if (lm.spire_kind === 'steeple') {
        // masonry tower stages in the facade color, then a pale wooden spire
        const baseH = rise * 0.44, spireH = rise * 0.56;
        parts.push({ geom: box(5.4, baseH, 5.4, cx, roof + baseH / 2, cz), color: col });
        const cone = new THREE.ConeGeometry(2.7, spireH, 8);
        cone.translate(cx, roof + baseH + spireH / 2, cz);
        parts.push({ geom: cone, color: new THREE.Color(0xece8dc) });
      } else if (lm.spire_kind === 'cupola') {
        const drum = new THREE.CylinderGeometry(2.1, 2.1, rise * 0.6, 10);
        drum.translate(cx, roof + rise * 0.3, cz);
        parts.push({ geom: drum, color: col });
        const cap = new THREE.ConeGeometry(2.5, rise * 0.4, 10);
        cap.translate(cx, roof + rise * 0.8, cz);
        parts.push({ geom: cap, color: col });
      } else if (lm.spire_kind === 'dome') {
        const dome = new THREE.SphereGeometry(4.5, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2);
        dome.translate(cx, roof, cz);
        parts.push({ geom: dome, color: col });
      } else { // tower
        parts.push({ geom: box(6.5, rise * 0.82, 6.5, cx, roof + rise * 0.41, cz), color: col });
        const cap = new THREE.ConeGeometry(4.6, rise * 0.18, 4);
        cap.rotateY(Math.PI / 4);
        cap.translate(cx, roof + rise * 0.91, cz);
        parts.push({ geom: cap, color: col });
      }
    }
    if (parts.length) {
      const mesh = new THREE.Mesh(
        mergeColored(parts),
        new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85 })
      );
      mesh.castShadow = true;
      groupCity.add(mesh);
    }
  });

  // ------------------------------------------------ researched landmark models
  step('Restoring the landmarks', () => {
    const walls = [];   // gets the window shader
    const detail = [];  // roofs, spires, columns, trim — plain material
    const aw = (geom, hex, style) => walls.push({ geom, color: new THREE.Color(hex), style: style == null ? 0 : style });
    const ad = (geom, hex) => detail.push({ geom, color: new THREE.Color(hex), style: 3 });
    const get = (name) => { for (const b of upgraded.keys()) if (b.name === name) return b; return null; };
    const getKey = (key) => { for (const [b, sp] of upgraded) if (sp.key === key) return b; return null; };
    const mark = () => [walls.length, detail.length, glassParts2.length];
    const liftAt = (m, x, z) => lift(m[0], m[1], m[2], siteY(x, z, 'ground'));
    const liftB = (m, b) => { const [cx, cz] = polyCentroid(b.poly); liftAt(m, cx, cz); };
    const ryAlign = (ax, az) => Math.atan2(-az, ax);
    const glassParts2 = [];
    const lift = (w0, d0, g0, ty) => {
      if (!ty) return;
      for (let k = w0; k < walls.length; k++) { walls[k].geom.translate(0, ty, 0); walls[k].baseY = ty; }
      for (let k = d0; k < detail.length; k++) { detail[k].geom.translate(0, ty, 0); detail[k].baseY = ty; }
      for (let k = g0; k < glassParts2.length; k++) { glassParts2[k].geom.translate(0, ty, 0); glassParts2[k].baseY = ty; }
    };
    const chimney = (x, z, h0, h1, ry, hex) =>
      ad(box(0.95, h1 - h0, 0.55, x, (h0 + h1) / 2, z, ry), hex || '#6a4132');

    // simple researched form: walls to the eave + gable/hip roof + extras
    function classic(name, o) {
      const b = get(name);
      if (!b) return null;
      const ob = orientedBox(b.poly);
      if (!ob) return null;
      const a = obbAxis(ob);
      const st = o.style == null ? 0 : o.style;
      const w0 = walls.length, d0 = detail.length;
      aw(buildingGeom(b.poly, b.holes, o.eave, -1.5), o.wall, st);
      if (o.roof === 'hip') {
        ad(hipGeom(ob, o.eave, o.ridge, 0.4), o.roofCol);
      } else if (o.roof === 'gable') {
        // roofs must sit on the walls: try the footprint quad, then a looser
        // simplification for L-plans (roof covers the main mass, the ell keeps
        // its flat cap). NEVER an OBB gable — it floats beside non-rectangular
        // walls (the City Tavern chimney-side floaters).
        let sp = simplifyRing(b.poly, 0.6);
        if (sp.length !== 4) sp = simplifyRing(b.poly, 1.4);
        if (sp.length === 4) {
          const g = quadGable(sp, o.eave, o.ridge);
          ad(g.slopes, o.roofCol);
          if (o.gableEndsTrim) ad(g.ends, o.trim); else aw(g.ends, o.wall, st);
          for (const ev of g.eaves) {
            ad(box(ev.len + 0.1, 0.4, 0.55,
              (ev.a[0] + ev.b[0]) / 2, o.eave - 0.1, (ev.a[1] + ev.b[1]) / 2,
              Math.atan2(-(ev.b[1] - ev.a[1]), ev.b[0] - ev.a[0])), o.trim);
          }
        } else {
          o.dormers = null;   // no pitched roof for the dormers to sit on
        }
      }
      if (o.chimneys) {
        for (const s of [-1, 1]) {
          if (o.chimneys === 1 && s < 0) continue;
          chimney(ob.cx + a.ax * (a.hl - 1.1) * s, ob.cz + a.az * (a.hl - 1.1) * s,
            o.eave - 1, o.ridge + 1.4, ryAlign(a.ax, a.az), o.wall);
        }
      }
      if (o.dormers) {
        const side = (a.px * o.dormers[0] + a.pz * o.dormers[1]) >= 0 ? 1 : -1;
        const n = o.dormers[2];
        for (let i = 0; i < n; i++) {
          const u = (i - (n - 1) / 2) * (a.hl * 1.1 / Math.max(1, n - 1) + 1.5);
          ad(box(1.35, 1.7, 1.5,
            ob.cx + a.ax * u + a.px * side * (a.hs * 0.55),
            o.eave + 1.1,
            ob.cz + a.az * u + a.pz * side * (a.hs * 0.55),
            ryAlign(a.ax, a.az)), o.trim);
        }
      }
      lift(w0, d0, glassParts2.length, siteY(ob.cx, ob.cz, 'ground'));
      return { b, ob, a };
    }

    // Georgian & Greek Revival core
    classic('Head House', { wall: '#8a4634', trim: '#f2ede0', eave: 7.6, ridge: 10, roof: 'gable', roofCol: '#4a4c50', style: 4 });
    {
      const hh = get('Head House');
      if (hh) {
        const ob = orientedBox(hh.poly);
        const m0 = mark();
        cupolaGeoms(ob.cx, ob.cz, 9.7, 2.5, 5.2).forEach(g => ad(g, '#f2ede0'));
        liftB(m0, hh);
      }
    }
    classic('City Tavern', { wall: '#7f3d2c', trim: '#efe9d8', eave: 11, ridge: 14, roof: 'gable', roofCol: '#5b564e', chimneys: 2, dormers: [1, 0, 3] });
    classic('Hill-Physick House', { wall: '#83402e', trim: '#f1ebdc', eave: 12, ridge: 14.5, roof: 'hip', roofCol: '#3f4044', chimneys: 2 });
    classic('Powel House', { wall: '#7d3b2a', trim: '#f1ebdc', eave: 11, ridge: 13.5, roof: 'gable', roofCol: '#4d4a45', chimneys: 2, dormers: [1, 0, 2] });
    {
      const r = classic('Man Full of Troubles Tavern', { wall: '#8a4a36', trim: '#ece5d3', eave: 5.8, ridge: 8.8, roof: 'gable', roofCol: '#8c7a60', chimneys: 1 });
      if (r) { // pent eave across the south face
        const side = (r.a.pz >= 0) ? 1 : -1;
        const m0 = mark();
        ad(box(Math.max(r.ob.w, r.ob.d), 0.22, 0.7,
          r.ob.cx + r.a.px * side * (r.a.hs + 0.2), 3.1, r.ob.cz + r.a.pz * side * (r.a.hs + 0.2),
          ryAlign(r.a.ax, r.a.az)), '#ece5d3');
        liftB(m0, r.b);
      }
    }

    // churches
    {
      const r = classic("Saint Peter's Church", { wall: '#8e4a38', trim: '#f0ede4', eave: 9.5, ridge: 13.5, roof: 'gable', roofCol: '#5e5d59', style: 1 });
      if (r) { // Strickland tower + white spire at the WEST end, apex ~64 m
        const m0 = mark();
        const e = obbEnd(r.ob, -1, 0);
        const tx = e.x - e.ax * 4.2, tz = e.z - e.az * 4.2;
        aw(box(7.5, 24, 7.5, tx, 12, tz, ryAlign(e.ax, e.az)), '#8e4a38', 1);
        ad(box(4.9, 3.2, 4.9, tx, 25.6, tz, ryAlign(e.ax, e.az)), '#e9e9e5');
        const sp = new THREE.ConeGeometry(3.1, 36.8, 8);
        sp.translate(tx, 27.2 + 18.4, tz);
        ad(sp, '#e9e9e5');
        liftB(m0, r.b);
      }
    }
    {
      const r = classic('Old Pine Street Church', { wall: '#e7d28b', trim: '#eae8df', eave: 10, ridge: 13, roof: 'gable', roofCol: '#7a7a76', gableEndsTrim: true, style: 1 });
      if (r) { // canary stucco temple; octastyle colonnade facing NORTH to Pine St
        const m0 = mark();
        const e = obbEnd(r.ob, 0, -1);
        const hw = r.a.hs - 1.4;
        const cx0 = e.x + e.ax * 1.7 - r.a.px * hw, cz0 = e.z + e.az * 1.7 - r.a.pz * hw;
        const cx1 = e.x + e.ax * 1.7 + r.a.px * hw, cz1 = e.z + e.az * 1.7 + r.a.pz * hw;
        columnRow(cx0, cz0, cx1, cz1, 8, 8.6, 0.44, 0.4).forEach(g => ad(g, '#eae8df'));
        ad(box(hw * 2 + 1.8, 1.2, 1.5, e.x + e.ax * 1.7, 9.6, e.z + e.az * 1.7, ryAlign(r.a.px, r.a.pz)), '#eae8df');
        liftB(m0, r.b);
      }
    }
    {
      const r = classic('Mother Bethel African Methodist Episcopal Church', { wall: '#cfc9bd', trim: '#8a7a66', eave: 11.6, ridge: 15, roof: 'gable', roofCol: '#4b4642', style: 1 });
      if (r) { // granite Romanesque; spired bell tower at the NW corner (6th & Addison)
        const m0 = mark();
        let mnx = 1e9, mnz = 1e9, mxz = -1e9;
        for (const p of r.b.poly) { mnx = Math.min(mnx, p[0]); mnz = Math.min(mnz, p[1]); mxz = Math.max(mxz, p[1]); }
        aw(box(6.5, 22.5, 6.5, mnx + 3.4, 11.25, mnz + 3.4, 0), '#cfc9bd', 1);
        const pyr = new THREE.ConeGeometry(4.4, 10.5, 4);
        pyr.rotateY(Math.PI / 4);
        pyr.translate(mnx + 3.4, 22.5 + 5.25, mnz + 3.4);
        ad(pyr, '#4b4642');
        aw(box(4.4, 12.5, 4.4, mnx + 2.4, 6.25, mxz - 2.6, 0), '#cfc9bd', 1);
        liftB(m0, r.b);
      }
    }
    classic("Old Saint Mary's Church", { wall: '#814238', trim: '#e8e4da', eave: 10, ridge: 14.2, roof: 'gable', roofCol: '#615f5b', style: 1 });
    classic("Old Saint Joseph's Church", { wall: '#95503a', trim: '#edeae0', eave: 9.5, ridge: 12.5, roof: 'gable', roofCol: '#5f5d58', style: 1 });
    classic("Old Saint Paul's Church", { wall: '#d8dad3', trim: '#c2c4bc', eave: 9, ridge: 13, roof: 'gable', roofCol: '#63615c', gableEndsTrim: true, style: 1 });

    // the Shambles: open market shed — two rows of brick piers under a slate gable
    {
      const b = get('Head House Market');
      if (b) {
        const m0 = mark();
        const ob = orientedBox(b.poly);
        const a = obbAxis(ob);
        const L = a.hl * 2;
        const n = Math.max(4, Math.round(L / 3.7));
        for (let i = 0; i <= n; i++) {
          const u = -a.hl + 0.6 + (i / n) * (L - 1.2);
          for (const s of [-1, 1]) {
            aw(box(0.45, 3.3, 0.45,
              ob.cx + a.ax * u + a.px * s * (a.hs - 0.55), 1.65,
              ob.cz + a.az * u + a.pz * s * (a.hs - 0.55), 0), '#8a4634', 3);
          }
        }
        const g = gableGeom(ob, 3.5, 6.3, 0.5, 0.3);
        ad(g.slopes, '#565a5e');
        ad(g.ends, '#565a5e');
        for (const s of [-1, 1]) {
          ad(box(L + 1, 0.24, 0.2,
            ob.cx + a.px * s * (a.hs + 0.35), 3.42, ob.cz + a.pz * s * (a.hs + 0.35),
            ryAlign(a.ax, a.az)), '#e8e2d4');
        }
        liftB(m0, b);
      }
    }

    // Merchants' Exchange: marble block, curved Corinthian colonnade + lantern to Dock St
    {
      const b = get("Merchants' Exchange Building");
      if (b) {
        const m0 = mark();
        aw(buildingGeom(b.poly, b.holes, 17.5, -1.5), '#d9d4c6', 1);
        const [ccx, ccz] = polyCentroid(b.poly);
        let ex = ccx, ez = ccz, best = -1e9;
        for (const p of b.poly) { if (p[0] > best) { best = p[0]; ex = p[0]; ez = p[1]; } }
        let dx = ex - ccx, dz = ez - ccz;
        const dl = Math.hypot(dx, dz) || 1;
        dx /= dl; dz /= dl;
        const arcX = ccx + dx * (dl - 10.5), arcZ = ccz + dz * (dl - 10.5);
        const base = Math.atan2(dz, dx);
        for (let i = 0; i < 8; i++) {
          const th = base + (-0.95 + (i / 7) * 1.9);
          const col = new THREE.CylinderGeometry(0.42, 0.48, 9.2, 10);
          col.translate(arcX + Math.cos(th) * 11.2, 5.2 + 4.6, arcZ + Math.sin(th) * 11.2);
          ad(col, '#d9d4c6');
        }
        const drum = new THREE.CylinderGeometry(2.9, 2.9, 7, 14);
        drum.translate(arcX, 17.5 + 3.5, arcZ);
        ad(drum, '#d9d4c6');
        const cap = new THREE.ConeGeometry(3.3, 3, 14);
        cap.translate(arcX, 24.5 + 1.5, arcZ);
        ad(cap, '#b9b4a6');
        liftB(m0, b);
      }
    }

    // The Ryland: two offset blue-glass bars — same curtain-wall family as the
    // Liberty Place shafts (it reads blue in photos, not white)
    {
      const b = get('The Ryland');
      if (b) {
        const m0 = mark();
        const ob = orientedBox(b.poly);
        const a = obbAxis(ob);
        const ry = ryAlign(a.ax, a.az);
        const L = a.hl * 2 - 0.6, S = a.hs * 2;
        const north = (a.pz < 0) ? 1 : -1; // v-sign whose direction points north
        const bars = [
          { v: north * (S / 4), d: S / 2 - 0.4, h: 110.9 },   // north bar, full height
          { v: -north * (S / 4), d: S / 2 - 0.4, h: 84 },      // south bar + amenity deck
        ];
        for (const bar of bars) {
          const bx = ob.cx + a.px * bar.v, bz = ob.cz + a.pz * bar.v;
          glassParts2.push({ geom: box(L, bar.h, bar.d, bx, bar.h / 2, bz, ry), color: new THREE.Color(0x4f7ba1) });
          // mullion grid a shade darker than the glass: verticals every ~3 m,
          // spandrel band every 3 floors — curtain-wall rhythm, not white trim
          const nV = Math.round(L / 3);
          for (let i = 0; i <= nV; i++) {
            const u = -L / 2 + (i / nV) * L;
            for (const s of [-1, 1]) {
              ad(box(0.16, bar.h, 0.14,
                bx + a.ax * u + a.px * s * (bar.d / 2), bar.h / 2,
                bz + a.az * u + a.pz * s * (bar.d / 2), ry), '#3d5a73');
            }
          }
          for (let y = 9.4; y < bar.h - 1; y += 9.4) {
            for (const s of [-1, 1]) {
              ad(box(L + 0.1, 0.55, 0.16,
                bx + a.px * s * (bar.d / 2), y,
                bz + a.pz * s * (bar.d / 2), ry), '#3d5a73');
            }
          }
        }
        // glass parapet screen on the north bar, pergola on the south roof deck
        const nb = bars[0], sb = bars[1];
        glassParts2.push({
          geom: box(L - 4, 3.2, 1.2, ob.cx + a.px * nb.v, nb.h + 1.6, ob.cz + a.pz * nb.v, ry),
          color: new THREE.Color(0x6c93b4),
        });
        ad(box(9, 2.4, 5, ob.cx + a.px * sb.v, sb.h + 1.2, ob.cz + a.pz * sb.v, ry), '#4a4a4c');
        liftB(m0, b);
      }
    }

    // Marriott Old City (ex-Sheraton): correct height, brick, dark roof, porte-cochere
    {
      const b = get('Philadelphia Marriott Old City');
      if (b) {
        const m0 = mark();
        aw(buildingGeom(b.poly, b.holes, 16.5, -1.5), '#95513f');
        ad(extrudePoly(b.poly, b.holes, 17.1, 16.5), '#3c3f44');
        let wx = 1e9, wz = 0;
        for (const p of b.poly) { if (p[0] < wx) { wx = p[0]; wz = p[1]; } }
        ad(box(14, 0.6, 7.5, wx - 3.5, 4.4, wz, 0), '#efeae0');
        for (const s of [-1, 1]) ad(box(0.6, 4.2, 0.6, wx - 6.8, 2.1, wz + s * 3.2, 0), '#95513f');
        liftB(m0, b);
      }
    }

    // Seaport Museum: pale block with the long verdigris barrel vault
    {
      const b = get('Independence Seaport Museum');
      if (b) {
        const w0 = walls.length, d0 = detail.length;
        aw(buildingGeom(b.poly, b.holes, 11.5, -1.5), '#d8d5cc', 2);
        const ob = orientedBox(b.poly);
        const vault = new THREE.CylinderGeometry(7.5, 7.5, Math.max(ob.w, ob.d) * 0.55, 16, 1, true, Math.PI, Math.PI);
        vault.rotateX(Math.PI / 2);
        vault.scale(1, 5 / 7.5, 1);
        const a = obbAxis(ob);
        vault.rotateY(Math.atan2(-a.az, a.ax) + Math.PI / 2);
        vault.translate(ob.cx, 11.5, ob.cz);
        ad(vault, '#9dbfad');
        lift(w0, d0, glassParts2.length, siteY(ob.cx, ob.cz, 'ground'));
      }
    }

    // --- skyline corrections: buildings OSM tags at the 13 m default
    {
      // US Custom House (1934): limestone base, red-brick shaft, then the white
      // stepped crown — square stage, two octagonal drums, colonnaded lantern, dome
      const b = get('United States Custom House');
      if (b) {
        const m0 = mark();
        const ob = orientedBox(b.poly);
        const ry = ryAlign(obbAxis(ob).ax, obbAxis(ob).az);
        aw(buildingGeom(b.poly, b.holes, 9, -1.5), '#b8ae97', 2);
        aw(buildingGeom(b.poly, b.holes, 40, 9), '#54302a', 2);
        aw(box(33, 9, 33, ob.cx, 40 + 4.5, ob.cz, ry), '#b5ac96', 2);
        const facet = (g) => { const f = g.toNonIndexed(); f.computeVertexNormals(); return f; };
        const oct1 = new THREE.CylinderGeometry(13.2, 14.4, 13, 8);
        oct1.rotateY(ry + Math.PI / 8); oct1.translate(ob.cx, 49 + 6.5, ob.cz);
        ad(facet(oct1), '#b2a993');
        const oct2 = new THREE.CylinderGeometry(9.2, 10.0, 11, 8);
        oct2.rotateY(ry + Math.PI / 8); oct2.translate(ob.cx, 62 + 5.5, ob.cz);
        ad(facet(oct2), '#bab19b');
        const lan = new THREE.CylinderGeometry(5.6, 6.4, 8.5, 8);
        lan.translate(ob.cx, 73 + 4.25, ob.cz);
        ad(facet(lan), '#c0b7a1');
        const dome = new THREE.CylinderGeometry(1.6, 5.8, 5.5, 8);
        dome.translate(ob.cx, 81.5 + 2.75, ob.cz);
        ad(facet(dome), '#a89f8a');
        const fin = new THREE.CylinderGeometry(0.3, 1.4, 2.8, 6);
        fin.translate(ob.cx, 87 + 1.4, ob.cz);
        ad(facet(fin), '#b2a993');
        liftB(m0, b);
      }
    }
    // Man Full of Trouble Tavern (1759): two brick floors under a gambrel roof
    // with dormers, cream pent + cornice, big end chimney — a block from the pool
    {
      const b = get('Man Full of Troubles Tavern');
      if (b) {
        const m0 = mark();
        const ob = orientedBox(b.poly);
        const a = obbAxis(ob);
        const ry = ryAlign(a.ax, a.az);
        const EAVE = 6.6, BRK = 8.8, RIDGE = 9.8, INSET = 1.9;
        aw(buildingGeom(b.poly, null, EAVE, -1.5), '#77402f', 0);
        { // gambrel: two slopes a side + pentagon gable ends (detail mat is DoubleSide)
          const hl = a.hl + 0.35, hs = a.hs + 0.3;
          const P = (u, v, y) => [ob.cx + a.ax * u + a.px * v, y, ob.cz + a.az * u + a.pz * v];
          const pos = [];
          const tri = (A, B, C) => pos.push(A[0], A[1], A[2], B[0], B[1], B[2], C[0], C[1], C[2]);
          for (const s of [-1, 1]) {
            const v0 = s * hs, v1 = s * (hs - INSET);
            tri(P(-hl, v0, EAVE), P(hl, v0, EAVE), P(hl, v1, BRK)); tri(P(-hl, v0, EAVE), P(hl, v1, BRK), P(-hl, v1, BRK));
            tri(P(-hl, v1, BRK), P(hl, v1, BRK), P(hl, 0, RIDGE)); tri(P(-hl, v1, BRK), P(hl, 0, RIDGE), P(-hl, 0, RIDGE));
          }
          for (const e of [-1, 1]) {
            const u = e * hl;
            const ring = [P(u, -hs, EAVE), P(u, -(hs - INSET), BRK), P(u, 0, RIDGE), P(u, hs - INSET, BRK), P(u, hs, EAVE)];
            for (let i2 = 1; i2 < ring.length - 1; i2++) tri(ring[0], ring[i2], ring[i2 + 1]);
          }
          const g = new THREE.BufferGeometry();
          g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
          g.computeVertexNormals();
          ad(g, '#4a3627');
        }
        const northV = (a.pz < 0) ? 1 : -1;                // v-sign toward Spruce Street
        const fx2 = a.px * northV, fz2 = a.pz * northV;
        // cream pent between the floors and cornice at the eave, street face
        ad(box(a.hl * 2 + 0.5, 0.2, 0.8, ob.cx + fx2 * (a.hs + 0.3), 3.7, ob.cz + fz2 * (a.hs + 0.3), ry), '#e9e3d0');
        ad(box(a.hl * 2 + 0.5, 0.28, 0.55, ob.cx + fx2 * (a.hs + 0.2), EAVE - 0.1, ob.cz + fz2 * (a.hs + 0.2), ry), '#e9e3d0');
        for (const du of [-0.42, 0.42]) {                  // dormers on the street slope
          const dx2 = ob.cx + a.ax * du * a.hl + fx2 * (a.hs - 1.0), dz2 = ob.cz + a.az * du * a.hl + fz2 * (a.hs - 1.0);
          ad(box(1.35, 1.6, 1.5, dx2, BRK - 0.75, dz2, ry), '#efe9dc');
          const dr = new THREE.CylinderGeometry(0.02, 1.05, 1.0, 4);
          dr.rotateY(ry + Math.PI / 4); dr.translate(dx2, BRK + 0.55, dz2);
          ad(dr, '#5b4433');
        }
        ad(box(1.5, 2.6, 1.1, ob.cx - a.ax * (a.hl * 0.42), RIDGE + 0.6, ob.cz - a.az * (a.hl * 0.42), ry), '#67382b');
        liftB(m0, b);
      }
    }
    // Glory Beer Bar & Kitchen, 126 Chestnut (mid-block, Front-2nd): one deep
    // narrow lot — dark cast-iron storefront with granite piers at the street,
    // five brick floors over it, low rear range down the lot
    {
      const bG = getKey('glory');
      if (bG) {
        const m0 = mark();
        const ob = orientedBox(bG.poly);
        const a = obbAxis(ob);
        // street face = whichever OBB face points at Chestnut (north, -z);
        // this lot's LONG axis runs back from the street
        let fdx, fdz, fext, sdx, sdz, sext;
        if (Math.abs(a.az) > Math.abs(a.pz)) {
          const s2 = a.az < 0 ? 1 : -1;
          fdx = a.ax * s2; fdz = a.az * s2; fext = a.hl;
          sdx = a.px; sdz = a.pz; sext = a.hs;
        } else {
          const s2 = a.pz < 0 ? 1 : -1;
          fdx = a.px * s2; fdz = a.pz * s2; fext = a.hs;
          sdx = a.ax; sdz = a.az; sext = a.hl;
        }
        const ryF = Math.atan2(-sdz, sdx);
        const ryD = Math.atan2(-fdz, fdx);
        // all-box massing, no pair coplanar (clears or interpenetrates at a
        // DIFFERENT width). The pier order is ENGAGED — flush with the brick
        // plane, never proud of the building — with the floor-2 glazing set
        // 0.5 m behind it and the ground floor a full 2.4 m walk-in porch.
        // Widths pull 15 cm off each lot line so nothing shimmers against
        // the neighbors' party walls.
        const segW = (back, front, y0s, y1s, w2) => box(front - back, y1s - y0s, w2,
          ob.cx + fdx * ((back + front) / 2), (y0s + y1s) / 2,
          ob.cz + fdz * ((back + front) / 2), ryD);
        const F = fext - 0.55;                              // facade plane, at the block line
        const W2 = sext * 2 - 0.3;
        aw(segW(-fext, F - 9.4, -1.5, 8.0, W2 - 0.16), '#6b4c3f', 3);      // rear range
        aw(segW(F - 10, F - 2.4, -1.5, 4.5, W2 - 0.1), '#191c1f', 3);      // porch back wall
        aw(segW(F - 10, F - 0.5, 4.25, 8.3, W2 - 0.08), '#23262b', 3);     // floor-2 glazing, recessed
        aw(segW(F - 26, F - 0.02, 7.9, 17.8, W2 - 0.06), '#74453a', 5);    // brick floors 3-5
        const wx = ob.cx + fdx * F, wz = ob.cz + fdz * F;   // pier plane = facade plane
        const across = (u) => [wx + sdx * u, wz + sdz * u];
        const half = W2 / 2 - 0.3;
        for (let i2 = 0; i2 < 5; i2++) {                    // engaged granite piers, both floors
          const [px2, pz2] = across(-half + (i2 / 4) * half * 2);
          ad(box(0.5, 8.3, 0.44, px2 - fdx * 0.23, 4.15, pz2 - fdz * 0.23, ryF), '#cfc8b8');
        }
        ad(box(W2 - 0.5, 0.45, 0.42, wx - fdx * 0.25, 4.3, wz - fdz * 0.25, ryF), '#cfc8b8');  // transom beam
        ad(box(W2 + 0.05, 0.55, 0.5, wx - fdx * 0.2, 8.1, wz - fdz * 0.2, ryF), '#c4bdae');    // cornice cap
        // "GLORY" — real lettering on a small canvas texture, heavy geometric
        // sans in red on the white board, hung over the transom
        {
          const cnv = document.createElement('canvas');
          cnv.width = 512; cnv.height = 256;
          const ctx = cnv.getContext('2d');
          ctx.fillStyle = '#f2ede2'; ctx.fillRect(0, 0, 512, 256);
          ctx.fillStyle = '#c0272d';
          ctx.font = '900 142px Futura, "Avenir Next", "Century Gothic", "Arial Black", sans-serif';
          ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
          ctx.fillText('GLORY', 256, 134);
          const tex = new THREE.CanvasTexture(cnv);
          tex.encoding = THREE.sRGBEncoding;
          tex.anisotropy = 4;
          const sg = new THREE.Mesh(new THREE.PlaneGeometry(1.05, 0.52),
            new THREE.MeshBasicMaterial({ map: tex }));
          sg.rotation.y = Math.atan2(fdx, fdz);
          // mounted proud of the pier plane like the real board — never clipped
          const [sx3, sz3] = across(-half * 0.25);
          sg.position.set(sx3 + fdx * 0.14, siteY(wx, wz, 'ground') + 5.15, sz3 + fdz * 0.14);
          groupCity.add(sg);
        }
        {  // small weathered-green blade sign on the brick, floors 3-4
          const [bx2, bz2] = across(half * 0.9);
          ad(box(0.3, 3.2, 0.7, bx2 + fdx * 0.28, 11.0, bz2 + fdz * 0.28, ryF), '#3d5347');
        }
        // wrought-iron fence at the sidewalk in front of the porch
        ad(box(W2, 0.9, 0.07, wx + fdx * 1.7, 0.45, wz + fdz * 1.7, ryF), '#1c1e20');
        liftB(m0, bG);
      }
    }
    // Rotten Ralph's, 201 Chestnut (NW corner of 2nd & Chestnut): white-painted
    // corner building whose whole upper floor is a continuous arcade of tall
    // blue-framed round-arched windows wrapping both street faces, corbelled
    // brick parapet band on top, storefront base with striped awnings, blue
    // double door and the hanging corner board sign. Built to the photo; the
    // LiDAR parapet for the lot is ~8.5 m.
    {
      const bR = getKey('ralphs');
      if (bR) {
        const m0 = mark();
        const ob = orientedBox(bR.poly);
        const a = obbAxis(ob);
        let ux = a.ax, uz = a.az;                    // along Chestnut, made WEST
        if (ux > 0) { ux = -ux; uz = -uz; }
        let sx = a.px, sz = a.pz;                    // across, made SOUTH (street)
        if (sz < 0) { sx = -sx; sz = -sz; }
        const W = a.hl * 2;                          // ~14.9 front width
        const D = 9.7;                               // both OSM strips deep
        const Ex = ob.cx - ux * a.hl + sx * a.hs;    // east corner on the front line
        const Ez = ob.cz - uz * a.hl + sz * a.hs;
        const P = (u, d2) => [Ex + ux * u - sx * d2, Ez + uz * u - sz * d2];
        const ryF = Math.atan2(-uz, ux);             // boxes running along the front
        const ryS = Math.atan2(-sz, sx);             // boxes running along 2nd St
        const aS = Math.atan2(sx, sz);               // plane normal toward Chestnut
        const aE = Math.atan2(-ux, -uz);             // plane normal toward 2nd St
        const bx = (u, d2, y, w2, h2, dp2, ry2) => {
          const [px2, pz2] = P(u, d2);
          return box(w2, h2, dp2, px2, y, pz2, ry2 == null ? ryF : ry2);
        };
        const WALL = '#e2dccd', TRIMW = '#eae4d6', BLUE = '#2c4257',
          GLASS = '#20242a', BRICK = '#361e16', DOOR = '#1d2c3d';
        // core block, blank style — every window on it is applied geometry.
        // Its south face lands at d=0.14, east face at u=0.15; applied pieces
        // engage those planes (cross them), never sit coplanar or float.
        aw(bx(W / 2, D / 2 + 0.02, 3.56, W - 0.3, 10.12, D - 0.24), WALL, 3);
        const FS = 0.14, FE = 0.15;                  // wall face planes
        // ---- ground floor, Chestnut face: piers, glass, door ----
        aw(bx(W / 2, 0.06, 1.62, W - 1.1, 3.24, 0.14), GLASS, 3);   // glass, proud of face
        for (const u of [0.5, 4.05, 7.6, 11.15, W - 0.5])           // engaged piers
          ad(bx(u, 0.1, 1.98, 0.46, 3.95, 0.5), TRIMW);
        ad(bx(1.85, 0.03, 1.55, 1.7, 3.1, 0.14), DOOR);             // blue double door
        ad(bx(1.85, 0.08, 3.32, 2.1, 0.42, 0.14), TRIMW);           // door head
        // ground floor, 2nd St face: glass wraps the corner bay, then solid
        aw(bx(0.08, 2.35, 1.62, 3.9, 3.24, 0.14, ryS), GLASS, 3);
        ad(bx(0.02, 0.5, 1.98, 0.5, 3.95, 0.46, ryS), TRIMW);
        ad(bx(0.02, 4.35, 1.98, 0.5, 3.95, 0.46, ryS), TRIMW);
        // striped awning along the Chestnut storefront (blue/white, tilted out)
        {
          const a0 = 2.7, a1 = W - 0.6, n = 26, sw = (a1 - a0) / n;
          for (let i2 = 0; i2 < n; i2++) {
            const g = new THREE.BoxGeometry(sw + 0.01, 0.09, 1.35);
            g.rotateX(-0.5);
            g.rotateY(ryF);
            const [px2, pz2] = P(a0 + (i2 + 0.5) * sw, -0.38);
            g.translate(px2, 3.12, pz2);
            ad(g, i2 % 2 ? '#e6e1d4' : '#25384a');
          }
        }
        // white spandrel band between storefront and the arcade, both faces
        ad(bx(W / 2, 0.02, 4.25, W + 0.04, 0.6, 0.36), TRIMW);
        ad(bx(0.03, D / 2 - 0.1, 4.25, D - 0.2, 0.56, 0.36, ryS), TRIMW);
        // ---- the arcade: 9 bays on Chestnut, 5 on 2nd. (pu,pd) = unit step
        // TOWARD the street off the wall face; planes stack proud of the glass ----
        const bay = (u0, d0, faceA, pu, pd, along) => {
          const y0 = 4.85, y1 = 6.95, r = 0.46;
          const at2 = (k) => P(u0 + pu * k, d0 + pd * k);
          {
            const g = new THREE.PlaneGeometry(0.92, y1 - y0);   // dark glass, rect
            g.rotateY(faceA);
            const [gx2, gz2] = at2(0.05);
            g.translate(gx2, (y0 + y1) / 2, gz2);
            aw(g, GLASS, 3);                        // walls material = truly dark glass
            const c = new THREE.CircleGeometry(r, 12, 0, Math.PI); // arch head glass
            c.rotateY(faceA);
            c.translate(gx2, y1, gz2);
            aw(c, GLASS, 3);
          }
          {
            const rg = new THREE.RingGeometry(r - 0.03, r + 0.1, 16, 1, 0, Math.PI);
            rg.rotateY(faceA);                                   // blue arch ring
            const [rx2, rz2] = at2(0.09);
            rg.translate(rx2, y1, rz2);
            ad(rg, BLUE);
          }
          for (const s2 of [-1, 1]) {                            // blue jambs, engaged
            const ju = faceA === aS ? u0 + s2 * 0.49 : u0 + pu * 0.02;
            const jd = faceA === aS ? d0 + pd * 0.02 : d0 + s2 * 0.49;
            ad(bx(ju, jd, (y0 + y1) / 2, 0.1, y1 - y0, 0.16, along), BLUE);
          }
          const [su2, sd2] = [u0 + pu * 0.05, d0 + pd * 0.05];   // white sill
          ad(bx(su2, sd2, y0 - 0.07, 1.14, 0.13, 0.22, along), TRIMW);
        };
        for (let i2 = 0; i2 < 9; i2++)
          bay(0.72 + (i2 + 0.5) * ((W - 1.44) / 9), FS, aS, 0, -1, ryF);
        for (let i2 = 0; i2 < 5; i2++)
          bay(FE, 1.1 + (i2 + 0.5) * ((D - 1.8) / 5), aE, -1, 0, ryS);
        // ledge above the arches, then the brick parapet band + coping
        ad(bx(W / 2, 0.04, 7.68, W + 0.1, 0.26, 0.4), TRIMW);
        ad(bx(0.05, D / 2 - 0.08, 7.68, D - 0.12, 0.22, 0.4, ryS), TRIMW);
        aw(bx(W / 2, 0.08, 8.26, W + 0.02, 0.95, 0.34), BRICK, 3);
        aw(bx(0.09, D / 2 - 0.06, 8.26, D - 0.08, 0.91, 0.34, ryS), BRICK, 3);
        ad(bx(W / 2, 0.02, 8.8, W + 0.16, 0.18, 0.52), TRIMW);
        ad(bx(0.04, D / 2 - 0.06, 8.8, D + 0.04, 0.15, 0.52, ryS), TRIMW);
        // roof furniture: dark deck, bulkhead, flue
        ad(bx(W / 2, D / 2, 8.68, W - 1.0, 0.14, D - 1.0), '#2e2c28');
        ad(bx(2.6, 7.4, 9.5, 2.4, 1.55, 2.0), '#3a3835');
        {
          const fl = new THREE.CylinderGeometry(0.12, 0.12, 2.3, 8);
          const [px2, pz2] = P(5.4, 6.6);
          fl.translate(px2, 9.8, pz2);
          ad(fl, '#181818');
        }
        // the hanging corner sign: white board, blue border, stacked script
        {
          const cnv = document.createElement('canvas');
          cnv.width = 256; cnv.height = 384;
          const ctx = cnv.getContext('2d');
          ctx.fillStyle = '#f0ece0'; ctx.fillRect(0, 0, 256, 384);
          ctx.strokeStyle = '#274d73'; ctx.lineWidth = 14;
          ctx.strokeRect(10, 10, 236, 364);
          ctx.fillStyle = '#2b527a';
          ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
          ctx.font = 'italic 700 64px Georgia, "Times New Roman", serif';
          ctx.fillText('Rotten', 128, 130);
          ctx.fillText("Ralph's", 128, 230);
          ctx.font = '600 30px Georgia, serif';
          ctx.fillText('BAR', 128, 318);
          const tex = new THREE.CanvasTexture(cnv);
          tex.encoding = THREE.sRGBEncoding;
          tex.anisotropy = 4;
          const mat = new THREE.MeshBasicMaterial({ map: tex });
          const yS2 = siteY(Ex, Ez, 'ground') + 5.5;
          const [sx3, sz3] = P(0.28, -0.62);
          for (const s2 of [0, Math.PI]) {           // printed on BOTH faces — never mirrored
            const sg = new THREE.Mesh(new THREE.PlaneGeometry(0.92, 1.42), mat);
            sg.rotation.y = Math.atan2(ux, uz) + s2;
            sg.position.set(sx3 + Math.sin(sg.rotation.y) * 0.012, yS2, sz3 + Math.cos(sg.rotation.y) * 0.012);
            groupCity.add(sg);
          }
        }
        liftB(m0, bR);
      }
    }
    {
      const b = get("Hilton Philadelphia at Penn's Landing");
      if (b) {
        const ob = orientedBox(b.poly);
        const w0 = walls.length, d0 = detail.length;
        aw(buildingGeom(b.poly, b.holes, 70, -1.5), '#d8cbb3', 2);
        ad(box(22, 4, 12, ob.cx, 72, ob.cz, ryAlign(obbAxis(ob).ax, obbAxis(ob).az)), '#b9ad98');
        lift(w0, d0, glassParts2.length, siteY(ob.cx, ob.cz, 'ground'));
      }
    }
    {
      // Independence Hall: the OSM footprint is the ENTIRE 84 m complex (main
      // block + hyphens + wings), so nothing here may scale off the raw OBB —
      // that put 100 m white bands across the facade. Explicit massing instead:
      // the 33x13.4 gable block with ridge balustrade, end chimneys and string
      // courses, hyphen arcades, two-story end wings, and the staged steeple.
      const b = get('Independence Hall');
      const obIH = b ? orientedBox(b.poly) : null;
      if (obIH) {
        const m0 = mark();
        const a = obbAxis(obIH);
        const ry = ryAlign(a.ax, a.az);
        const sV = (a.pz > 0) ? 1 : -1;
        const Sx = a.px * sV, Sz = a.pz * sV;            // unit vector pointing SOUTH
        // pt(u, s): u along the block axis from the center, s meters SOUTH of the
        // complex's north face
        const pt2 = (u, s) => [obIH.cx + a.ax * u + Sx * (s - a.hs), obIH.cz + a.az * u + Sz * (s - a.hs)];
        const BW = 16.45, BD = 13.4;                     // main block half-width / depth
        const bc = pt2(0, BD / 2);
        aw(box(BW * 2, 13.5, BD, bc[0], 5.25, bc[1], ry), '#7e4534', 0);
        {                                                // footprint-true gable roof
          const q = [pt2(-BW, 0.05), pt2(BW, 0.05), pt2(BW, BD - 0.05), pt2(-BW, BD - 0.05)];
          const g = quadGable(q, 12, 15.2);
          ad(g.slopes, '#4a463f');
          aw(g.ends, '#7e4534', 0);
          for (const ev of g.eaves) {
            ad(box(ev.len + 0.1, 0.4, 0.55,
              (ev.a[0] + ev.b[0]) / 2, 11.9, (ev.a[1] + ev.b[1]) / 2,
              Math.atan2(-(ev.b[1] - ev.a[1]), ev.b[0] - ev.a[0])), '#efeadb');
          }
        }
        ad(box(19, 0.85, 3.0, bc[0], 15.5, bc[1], ry), '#eee9da');                 // ridge-deck balustrade
        for (const s of [-1, 1]) {                                                  // paired end chimney masses
          const e2 = pt2(s * (BW - 1.0), BD / 2);
          ad(box(1.4, 3.6, 5.0, e2[0], 16.2, e2[1], ry), '#6e3c2d');
        }
        for (const s2 of [0.03, BD - 0.03]) {                                       // marble string courses
          const c2 = pt2(0, s2);
          ad(box(BW * 2 + 0.2, 0.42, 0.22, c2[0], 5.2, c2[1], ry), '#e6e0d0');
        }
        // hyphen arcades and two-story wing pavilions
        for (const s of [-1, 1]) {
          const wingU = s * (a.hl - 5.6);
          const hy0 = BW, hy1 = a.hl - 11.2;
          if (hy1 > hy0 + 1.5) {
            const hc = pt2(s * (hy0 + hy1) / 2, 4.8);
            aw(box(hy1 - hy0, 5.6, 9.4, hc[0], 2.8, hc[1], ry), '#7e4534', 4);
            ad(box(hy1 - hy0 + 0.2, 0.4, 9.7, hc[0], 5.8, hc[1], ry), '#efeadb');
          }
          const wc = pt2(wingU, 6.0);
          aw(box(11, 8.4, 12, wc[0], 3.4, wc[1], ry), '#7e4534', 0);
          ad(box(11.3, 0.45, 12.3, wc[0], 8.55, wc[1], ry), '#efeadb');
          const cap = new THREE.CylinderGeometry(0.6, 8.1, 2.6, 4);
          cap.rotateY(ry + Math.PI / 4);
          cap.translate(wc[0], 8.8 + 1.3, wc[1]);
          ad(cap, '#4a463f');
        }
        // engaged tower on the south (Independence Square) face
        const [tx, tz] = pt2(0, BD + 2.6);
        aw(box(9, 21, 9, tx, 10.5, tz, ry), '#7e4534', 1);                          // brick shaft, arched windows
        ad(box(9.9, 0.55, 9.9, tx, 21.15, tz, ry), '#efeadb');                      // cornice
        ad(box(9.1, 0.8, 9.1, tx, 21.8, tz, ry), '#efeadb');                        // balustrade
        ad(box(7.2, 6.2, 7.2, tx, 22.2 + 3.1, tz, ry), '#efeadb');                  // clock stage
        for (const [ux2, uz2] of [[a.ax, a.az], [-a.ax, -a.az], [a.px, a.pz], [-a.px, -a.pz]]) {
          const rim = new THREE.CylinderGeometry(1.7, 1.7, 0.22, 16);
          rim.rotateZ(Math.PI / 2); rim.rotateY(Math.atan2(-uz2, ux2));
          rim.translate(tx + ux2 * 3.65, 25.4, tz + uz2 * 3.65);
          ad(rim, '#3a3d3b');
          const dial = new THREE.CylinderGeometry(1.42, 1.42, 0.3, 16);
          dial.rotateZ(Math.PI / 2); dial.rotateY(Math.atan2(-uz2, ux2));
          dial.translate(tx + ux2 * 3.72, 25.4, tz + uz2 * 3.72);
          ad(dial, '#f3efe2');
        }
        ad(box(5.6, 5.4, 5.6, tx, 28.4 + 2.7, tz, ry), '#efeadb');                  // bell chamber
        for (const [ux2, uz2] of [[a.ax, a.az], [-a.ax, -a.az], [a.px, a.pz], [-a.px, -a.pz]]) {
          ad(box(2.3, 3.7, 0.24, tx + ux2 * 2.85, 30.9, tz + uz2 * 2.85, Math.atan2(-uz2, ux2)), '#2e2c28'); // open arches
        }
        ad(box(6.2, 0.7, 6.2, tx, 33.85, tz, ry), '#efeadb');                       // upper balustrade
        const bell = new THREE.CylinderGeometry(1.3, 3.95, 3.0, 8);
        bell.rotateY(ry + Math.PI / 8); bell.translate(tx, 34.2 + 1.5, tz);
        ad(bell, '#3c3933');                                                        // dark bell roof
        const drum = new THREE.CylinderGeometry(1.5, 1.7, 2.4, 8);
        drum.translate(tx, 37.2 + 1.2, tz);
        ad(drum, '#efeadb');
        const spire = new THREE.ConeGeometry(1.15, 9.5, 8);
        spire.translate(tx, 39.6 + 4.75, tz);
        ad(spire, '#efeadb');
        const orb = new THREE.SphereGeometry(0.4, 8, 6);
        orb.translate(tx, 49.4, tz);
        ad(orb, '#c8a44e');                                                         // gilt ball + vane mast
        const vane = new THREE.CylinderGeometry(0.06, 0.06, 2.4, 5);
        vane.translate(tx, 49.4 + 1.2, tz);
        ad(vane, '#d8d2c2');
        liftB(m0, b);
      }
    }
    for (const nm of ['Congress Hall', 'Old City Hall']) {
      const r = classic(nm, { wall: '#8e4a38', trim: '#f0ede4', eave: 11, ridge: 14.5, roof: 'gable', roofCol: '#4d4a45', chimneys: 2, style: 0 });
      if (r) { const m0 = mark(); cupolaGeoms(r.ob.cx, r.ob.cz, 14.2, 2.4, 5).forEach(g => ad(g, '#f0ede4')); liftB(m0, r.b); }
    }
    {
      const r = classic("Carpenters' Hall", { wall: '#8e4a38', trim: '#f0ede4', eave: 11, ridge: 14, roof: 'hip', roofCol: '#4d4a45', style: 0 });
      if (r) { const m0 = mark(); cupolaGeoms(r.ob.cx, r.ob.cz, 13.8, 2.2, 4.5).forEach(g => ad(g, '#f0ede4')); liftB(m0, r.b); }
    }
    {
      const r = classic('Second Bank of the United States', { wall: '#d9d4c6', trim: '#e6e2d8', eave: 14, ridge: 17.5, roof: 'gable', roofCol: '#6e7276', gableEndsTrim: true, style: 1 });
      if (r) { // Doric octastyle porticos on both short fronts, on marble stylobates
        const m0 = mark();
        for (const dir of [[0, -1], [0, 1]]) {
          const e = obbEnd(r.ob, dir[0], dir[1]);
          const hw = r.a.hs - 1.5;
          ad(box(hw * 2 + 3.4, 2.6, 5.2, e.x + e.ax * 2, -0.6, e.z + e.az * 2, ryAlign(r.a.px, r.a.pz)), '#ddd8ca');
          columnRow(e.x + e.ax * 2 - r.a.px * hw, e.z + e.az * 2 - r.a.pz * hw, e.x + e.ax * 2 + r.a.px * hw, e.z + e.az * 2 + r.a.pz * hw, 8, 9, 0.55, 0.6)
            .forEach(g => ad(g, '#e6e2d8'));
          ad(box(hw * 2 + 2.2, 1.6, 2.4, e.x + e.ax * 2, 10.4, e.z + e.az * 2, ryAlign(r.a.px, r.a.pz)), '#e6e2d8');
        }
        liftB(m0, r.b);
      }
    }
    {
      const r = classic('First Bank of the United States', { wall: '#9a5b45', trim: '#e6e2d8', eave: 14, ridge: 17, roof: 'hip', roofCol: '#6e7276', style: 1 });
      if (r) { // marble Corinthian portico on the 3rd St (west) front
        const m0 = mark();
        const e = obbEnd(r.ob, -1, 0);
        const hw = r.a.hs - 1.6;
        ad(box(hw * 2 + 3, 2.6, 4.8, e.x + e.ax * 1.8, -0.6, e.z + e.az * 1.8, ryAlign(r.a.px, r.a.pz)), '#ddd8ca');
        columnRow(e.x + e.ax * 1.8 - r.a.px * hw, e.z + e.az * 1.8 - r.a.pz * hw, e.x + e.ax * 1.8 + r.a.px * hw, e.z + e.az * 1.8 + r.a.pz * hw, 6, 10, 0.5, 0.5)
          .forEach(g => ad(g, '#e6e2d8'));
        ad(box(hw * 2 + 2, 1.5, 2.2, e.x + e.ax * 1.8, 11.3, e.z + e.az * 1.8, ryAlign(r.a.px, r.a.pz)), '#e6e2d8');
        liftB(m0, r.b);
      }
    }

    // --- Head House Square's big neighbors (OPA parcel + LiDAR massing)
    {
      // Abbotts Square (1982-85): L-shaped block, 8 levels on 2nd St stepping down westward along South St
      const b = getKey('abbotts');
      if (b) {
        const m0 = mark();
        const S = (x) => 464 + (x + 97) * 0.1727;   // South St face
        const N = (x) => 428 + (x + 131) * 0.1625;  // north face of the South St wing
        const brick = '#9a6646', cream = '#e7dfd0';
        const wing = (poly, h, hex, st) => aw(buildingGeom(poly, null, h, -1.5), hex, st == null ? 6 : st);
        wing([[-80, 366], [-97, 464], [-123.6, 459.4], [-106.6, 361.4]], 28.5, brick);            // 2nd St wing (square ends)
        wing([[-97, S(-97)], [-150, S(-150)], [-150, N(-150)], [-97, N(-97)]], 27, brick);            // South St wing, east third
        wing([[-150, S(-150)], [-200, S(-200)], [-200, N(-200)], [-150, N(-150)]], 23, brick);        // middle
        wing([[-200, S(-200)], [-236, S(-236)], [-236, N(-236)], [-200, N(-200)]], 20, brick);        // west end at 3rd St
        wing([[-203, S(-203) - 3], [-233, S(-233) - 3], [-233, N(-233) + 3], [-203, N(-203) + 3]], 22.2, '#e4e2dc', 2); // set-back penthouse
        wing([[-131, N(-131)], [-211, N(-211)], [-211, N(-211) - 13], [-131, N(-131) - 13]], 12.5, brick, 2); // garden-level bar inside the L
        // cream string courses at the top of the double-height retail and along the parapets
        const course = (ax, az, bx, bz, y) => ad(box(Math.hypot(bx - ax, bz - az) + 0.3, 0.45, 0.35, (ax + bx) / 2, y, (az + bz) / 2, ryAlign(bx - ax, bz - az)), cream);
        course(-80, 366, -97, 464, 6.6); course(-80, 366, -97, 464, 28.3);
        course(-97, 464, -236, 440, 6.6); course(-97, 464, -150, 454.8, 26.8); course(-150, 454.8, -200, 446.2, 22.8); course(-200, 446.2, -236, 440, 19.8);
        ad(box(6, 2.6, 6, -88, 29.8, 372, 0), '#cfcac0'); ad(box(6, 2.6, 6, -100, 29.8, 455, 0), '#cfcac0'); // elevator bulkheads
        liftAt(m0, -110, 430);
      }
    }
    {
      // 410 at Society Hill (Toll Brothers, 2015): 4 storeys of red brick with cream bays on a garage podium
      const b = getKey('ten410');
      if (b) {
        const m0 = mark();
        aw(buildingGeom(b.poly, b.holes, 16.8, -1.5), '#9c4b3f', 2);
        let mx = -1e9, mz = 1e9;
        for (const q of b.poly) { mx = Math.max(mx, q[0]); mz = Math.min(mz, q[1]); }
        ad(box(9, 4.5, 9, mx - 7, 16.8 + 2.25, mz + 8, 0), '#cfcac0');
        liftB(m0, b);
      }
    }
    {
      // The Residences at Dockside: stepped ziggurat slab on its pier — a 4-storey
      // podium, then floors that rake down long toward the shore (west) and steeply
      // toward the river, rooftop sail sculptures just east of the summit's center
      const b = get('The Residences at Dockside');
      if (b) {
        const m0 = mark();
        const ob = orientedBox(b.poly);
        const a2 = obbAxis(ob);
        const rya = ryAlign(a2.ax, a2.az);
        const eS = a2.ax > 0 ? 1 : -1;                 // +axis*eS points east (to the river)
        const FP = 2.75, POD = 4 * FP;                 // floor pitch locked to the style-7 shader grid
        const uMax = a2.hl * 0.97;
        // the footprint is Z-shaped: the slab proper is the river half's width, and the
        // extra strip on the shore half is podium only — measure both from the polygon
        const uvOf = (q) => [((q[0] - ob.cx) * a2.ax + (q[1] - ob.cz) * a2.az) * eS, (q[0] - ob.cx) * a2.px + (q[1] - ob.cz) * a2.pz];
        const span = (u0, u1) => {
          let lo = 1e9, hi = -1e9;
          for (const q of b.poly) { const [u, v] = uvOf(q); if (u < u0 || u > u1) continue; lo = Math.min(lo, v); hi = Math.max(hi, v); }
          return hi - lo > 12 ? [lo, hi] : [-a2.hs, a2.hs];
        };
        const [vLo, vHi] = span(5, 60);                // slab width (river half, clear of the east fingers)
        const [wLo, wHi] = span(-1e9, -5);             // full podium width on the shore half
        const v0 = vLo + 0.8, v1 = vHi - 0.8, vC = (vLo + vHi) / 2;
        const at = (u, v) => [ob.cx + a2.ax * eS * u + a2.px * v, ob.cz + a2.az * eS * u + a2.pz * v];
        const rect = (ue0, ue1) => [[-ue0, v0], [ue1, v0], [ue1, v1], [-ue0, v1]].map(([u, v]) => at(u, v));
        // podium: cream precast garage base with a terracotta waterline band, a dark
        // opening band, the oval-porthole band up top, and the round vent near the river end
        aw(buildingGeom(b.poly, b.holes, POD, -1.5), '#e0d2b6', 3);
        for (const [y, h, out, hex] of [[1.1, 2.3, 0.35, '#a5715f'], [5.1, 2.0, 0.15, '#6b645a'], [POD - 1.6, 1.5, 0.15, '#57514a']]) {
          for (const [u0, u1, lo, hi] of [[-uMax, 2, wLo, wHi], [2, uMax - 4, vLo, vHi]]) {
            const [px2, pz2] = at((u0 + u1) / 2, (lo + hi) / 2);
            ad(box(u1 - u0, h, hi - lo + out * 2, px2, y, pz2, rya), hex);
          }
        }
        {
          const vg = new THREE.CylinderGeometry(3.4, 3.4, vHi - vLo + 0.5, 20);
          vg.rotateX(Math.PI / 2); vg.rotateY(rya);
          const [vx, vz] = at(uMax - 10, vC);
          vg.translate(vx, POD - 4.2, vz);
          ad(vg, '#8fb4a4');                           // ship's-wheel garage vent
        }
        // tower: sheer full-height slab on the river half, ~7 two-storey terraced
        // setbacks cascading toward the shore; floors on the 2.75 m shader grid
        const uET = uMax - 6.5;                        // stop short of the pier's east fingers
        let topC = 0, topY = POD;
        for (let i = 0; i < 14; i++) {
          const uW2 = uET - 8.1 * Math.floor(i / 2);
          if (uET + uW2 < 18) break;
          const y0 = POD + FP * i, y1 = y0 + FP;
          aw(buildingGeom(rect(uW2, uET), null, y1, y0), '#d9c7a6', 7);
          const cU = (uET - uW2) / 2, len = (uET + uW2) * 0.96;
          for (const vR of [v0 - 0.7, v1 + 0.7]) {     // continuous balcony rails on both long faces
            const [rx, rz] = at(cU, vR);
            ad(box(len, 0.22, 1.4, rx, y0 + 1.15, rz, rya), '#cfc2a5');
          }
          topC = cU; topY = y1;
        }
        // three tilted ship-funnel wind scoops over the river-end roof
        for (const du of [-11, -5, 1]) {
          const fg = new THREE.CylinderGeometry(1.5, 1.8, 7.5, 12);
          fg.rotateZ(0.22 * eS); fg.rotateY(rya);
          const [fx, fz] = at(uET * 0.65 + du, vC);
          fg.translate(fx, topY + 3.4, fz);
          ad(fg, '#b6bcbf');
        }
        for (const vR of [v0 - 0.35, v1 + 0.35]) {     // seafoam glass accent on the west run
          const [gx, gz] = at(-uET * 0.55, vR);
          ad(box(4.5, 16, 0.5, gx, POD + 8, gz, rya), '#9fc4b4');
        }
        liftB(m0, b);
      }
    }
    {
      // New Market Complex (1970s): 3-storey brown brick commercial block at 2nd & Lombard
      const b = getKey('newmarket');
      if (b) { const m0 = mark(); aw(buildingGeom(b.poly, b.holes, 11.5, -1.5), '#7f4b3b', 5); liftB(m0, b); }
    }
    {
      // New Market Garage (1976): concrete parking decks with a 2-storey brick liner on 2nd St
      const b = get('New Market Garage');
      if (b) {
        const m0 = mark();
        aw(buildingGeom(b.poly, b.holes, 9.9, -1.5), '#b4b2aa', 3);
        aw(box(9, 8, 33, -75.5, 4, 334.5, 0), '#6f3b30', 5);
        aw(box(6, 13.5, 6, -90, 6.75, 345, 0), '#6f3b30', 3);
        liftB(m0, b);
      }
    }

    if (walls.length) {
      const m = new THREE.Mesh(mergeColored(walls, true), cityMat);
      m.castShadow = m.receiveShadow = true;
      groupCity.add(m);
      rayTargets.push(m);
    }
    if (detail.length) {
      const m = new THREE.Mesh(mergeColored(detail),
        new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.8, side: THREE.DoubleSide }));
      m.castShadow = m.receiveShadow = true;
      groupCity.add(m);
    }
    if (glassParts2.length) {
      const m = new THREE.Mesh(mergeColored(glassParts2),
        new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.06, metalness: 0.85, envMapIntensity: 1.7 }));
      m.castShadow = true;
      groupCity.add(m);
      rylandGlassMat = m.material;
      // Night, photo-matched: scattered warm per-panel apartment lights and
      // fully glowing lobby/amenity glass over the lowest floors of each piece
      // (aBase carries every merged part's ground lift). A flat material-wide
      // emissive used to wash the bars to one dead tone.
      rylandGlassMat.onBeforeCompile = (shader) => {
        shader.uniforms.uNight = nightUniform;
        shader.vertexShader = shader.vertexShader
          .replace('#include <common>', '#include <common>\nattribute float aBase;\nvarying float vRyB;\nvarying vec3 vRyW;')
          .replace('#include <begin_vertex>', '#include <begin_vertex>\nvRyB = aBase;\nvRyW = (modelMatrix * vec4(transformed, 1.0)).xyz;');
        shader.fragmentShader = shader.fragmentShader
          .replace('#include <common>', '#include <common>\nuniform float uNight;\nvarying float vRyB;\nvarying vec3 vRyW;\n' +
            // sin-lattice hashes streak along the grid (lit "worms"); this
            // fract-cascade hash is uniform on integer cells
            'float ryh(vec3 p){ p = fract(p * vec3(0.1031, 0.11369, 0.13787)); p += dot(p, p.yzx + 19.19); return fract((p.x + p.y) * p.z); }')
          .replace('#include <emissivemap_fragment>',
            '#include <emissivemap_fragment>\n{\n' +
            // the lit lattice must live in FACADE space, not world axes: the
            // building sits on the rotated grid, so world-x/z cells sliced
            // diagonally across the real panels (half-lit fragments). Derive
            // the along-facade axis per fragment from the surface derivatives;
            // 3.0 m matches the mullion bays, 3.13 m the floor bands, and the
            // face normal keys each face so opposite walls light independently.
            '  float relY = vRyW.y - vRyB;\n' +
            '  vec3 fn = normalize(cross(dFdx(vRyW), dFdy(vRyW)));\n' +
            '  vec2 tanH = normalize(vec2(-fn.z, fn.x) + vec2(1e-4, 0.0));\n' +
            '  float u = dot(vRyW.xz, tanH);\n' +
            '  vec3 cell = floor(vec3(u / 3.0, relY / 3.13, dot(floor(fn.xz * 4.0), vec2(1.0, 9.0))));\n' +
            '  float lit = step(0.74, ryh(cell));\n' +
            '  vec3 warm = vec3(1.0, 0.84, 0.60) * (0.7 + 0.55 * ryh(cell + 7.0));\n' +
            '  float amen = 1.0 - smoothstep(9.2, 10.6, relY);\n' +
            '  totalEmissiveRadiance += warm * max(lit * 0.8, amen * 1.15) * uNight;\n' +
            '}');
      };
    }
  });

  // ------------------------------------------------ museum ships
  step('Mooring the ships', () => {
    const parts = [];
    const W = TERRAIN.water;
    const add = (geom, hex) => parts.push({ geom, color: new THREE.Color(hex), style: 3 });
    for (const b of D.buildings) {
      if (b.t !== 'ship' || !b.poly || b.poly.length < 3) continue;
      const ob = orientedBox(b.poly);
      if (!ob) continue;
      const a = obbAxis(ob);
      const L = a.hl * 2, B = a.hs * 2;
      const ry = Math.atan2(-a.az, a.ax);
      const name = (b.name || '').toLowerCase();
      const at = (u, v) => [ob.cx + a.ax * u + a.px * v, ob.cz + a.az * u + a.pz * v];
      if (name.includes('becuna')) {            // submarine: low black hull, sail
        add(extrudePoly(b.poly, null, W + 3.0, W - 0.3), '#26282a');
        const [sx, sz] = at(L * 0.05, 0);
        add(box(9, 8, 3.2, sx, W + 3 + 4, sz, ry), '#2a2d30');
      } else if (name.includes('moshulu')) {    // four-masted barque
        add(extrudePoly(b.poly, null, W + 8.5, W - 0.3), '#202224');
        add(box(L * 0.97, 0.9, B + 0.25, ob.cx, W + 7.9, ob.cz, ry), '#e9e6de');
        for (const f of [-0.32, -0.1, 0.14, 0.36]) {
          const [mx, mz] = at(L * f, 0);
          const mast = new THREE.CylinderGeometry(0.32, 0.5, 46, 8);
          mast.translate(mx, W + 8.5 + 23, mz);
          add(mast, '#4a4742');
          for (const yh of [18, 30, 40]) add(box(22, 0.3, 0.3, mx, W + 8.5 + yh, mz, ry + Math.PI / 2), '#3e3b37');
        }
      } else {                                   // USS Olympia: white hull, buff superstructure
        add(extrudePoly(b.poly, null, W + 8, W - 0.3), '#e8e6df');
        add(box(L * 0.5, 4, B * 0.7, ob.cx, W + 8 + 2, ob.cz, ry), '#d8c9a0');
        for (const f of [-0.12, 0.12]) {
          const [fx, fz] = at(L * f, 0);
          const fun = new THREE.CylinderGeometry(1.3, 1.4, 8, 10);
          fun.translate(fx, W + 12 + 4, fz);
          add(fun, '#cdbd93');
        }
        for (const f of [-0.3, 0.3]) {
          const [mx, mz] = at(L * f, 0);
          const mast = new THREE.CylinderGeometry(0.3, 0.45, 30, 8);
          mast.translate(mx, W + 8 + 15, mz);
          add(mast, '#4a4742');
        }
      }
    }
    if (parts.length) {
      const m = new THREE.Mesh(mergeColored(parts), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.7, side: THREE.DoubleSide }));
      m.castShadow = true;
      groupCity.add(m);
    }
  });

  // ------------------------------------------------ the three towers
  step('Casting the concrete grid', () => {
    const concreteParts = [], glassParts = [], variedParts = [];
    const cSum = new V3();
    for (const t of towers) cSum.add(new V3(t.centroid[0], 0, t.centroid[1]));
    if (towers.length) towersCenter.copy(cSum.multiplyScalar(1 / towers.length));

    for (let ti = 0; ti < towers.length; ti++) {
      const t = towers[ti];
      const W = t.width_m, Dp = t.depth_m, H = TOWER.height;
      const cx = t.centroid[0], cz = t.centroid[1], ang = -(t.angleRad || 0);
      const floors = TOWER.floors;
      const floorH = (H - TOWER.lobbyH - TOWER.parapetH) / floors; // ~2.91 m
      const gridBot = TOWER.lobbyH, gridTop = H - TOWER.parapetH;
      const gridH = gridTop - gridBot;
      const rot = new THREE.Matrix4().makeRotationY(ang).setPosition(cx, 0, cz);
      const podium = siteY(towersCenter.x, towersCenter.z, 'ground');
      const add = (arr, g, color) => { g.applyMatrix4(rot); g.translate(0, podium, 0); arr.push({ geom: g, color, baseY: podium }); }; // towers stand on the 1 m plaza podium
      const cCon = new THREE.Color(COLORS.concrete);
      const cConD = new THREE.Color(COLORS.concreteDark);

      // per facade: local +x along width, +z along depth
      const sides = [
        { len: W, off: Dp / 2, axis: 'x' },
        { len: W, off: -Dp / 2, axis: 'x' },
        { len: Dp, off: W / 2, axis: 'z' },
        { len: Dp, off: -W / 2, axis: 'z' },
      ];
      for (const s of sides) {
        const inner = s.len - 2 * TOWER.cornerW;
        // researched facade: 18 bays on the wide faces, 12 on the narrow — fixed, not
        // derived from the OSM footprint (which rounds to 17/11 on two of the towers)
        const bays = s.len >= Math.max(W, Dp) - 0.01 ? 18 : 12;
        const bayW = inner / bays;
        // vertical mullions between window bays, lobby soffit to parapet
        for (let bi = 1; bi < bays; bi++) {
          const u = -inner / 2 + bi * bayW;
          const g = s.axis === 'x'
            ? box(TOWER.mullionW, gridH, TOWER.mullionD, u, gridBot + gridH / 2, s.off)
            : box(TOWER.mullionD, gridH, TOWER.mullionW, s.off, gridBot + gridH / 2, u);
          add(concreteParts, g, cCon);
        }
        // horizontal spandrel bands at each floor line
        for (let fi = 1; fi < floors; fi++) {
          const y = gridBot + fi * floorH;
          const g = s.axis === 'x'
            ? box(inner + TOWER.mullionW, TOWER.spandrelH, TOWER.mullionD * 0.96, 0, y, s.off)
            : box(TOWER.mullionD * 0.96, TOWER.spandrelH, inner + TOWER.mullionW, s.off, y, 0);
          add(concreteParts, g, cCon);
        }
        // soffit band where the grid lands on the colonnade
        const soff = s.axis === 'x'
          ? box(s.len + TOWER.mullionD, 1.0, TOWER.mullionD + 0.12, 0, gridBot, s.off)
          : box(TOWER.mullionD + 0.12, 1.0, s.len + TOWER.mullionD, s.off, gridBot, 0);
        add(concreteParts, soff, cCon);
        // plain fascia/parapet band capping the facade
        const fas = s.axis === 'x'
          ? box(s.len + TOWER.mullionD, TOWER.parapetH + 0.5, TOWER.mullionD + 0.08, 0, H - (TOWER.parapetH + 0.5) / 2 + 0.25, s.off)
          : box(TOWER.mullionD + 0.08, TOWER.parapetH + 0.5, s.len + TOWER.mullionD, s.off, H - (TOWER.parapetH + 0.5) / 2 + 0.25, 0);
        add(concreteParts, fas, cCon);
        // recessed glass curtain behind the grid
        const gOff = s.off > 0 ? s.off - TOWER.glassInset : s.off + TOWER.glassInset;
        const gGeom = s.axis === 'x'
          ? box(inner, gridH, 0.1, 0, gridBot + gridH / 2, gOff)
          : box(0.1, gridH, inner, gOff, gridBot + gridH / 2, 0);
        add(glassParts, gGeom, new THREE.Color(COLORS.glass));
        // sparse per-window variation (curtains, blinds, interior depth)
        for (let fi = 0; fi < floors; fi++) {
          for (let bi = 0; bi < bays; bi++) {
            const r = hash01(ti * 977 + s.off * 31 + fi * 13.7 + bi * 3.1);
            if (r > 0.26) continue;
            const u = -inner / 2 + (bi + 0.5) * bayW;
            const y = gridBot + (fi + 0.5) * floorH + TOWER.spandrelH / 4;
            const wW = Math.max(0.5, bayW - TOWER.mullionW - 0.35);
            const wH = floorH - TOWER.spandrelH - 0.3;
            const shade = r < 0.075
              ? new THREE.Color(0xd6ccb4).multiplyScalar(0.85 + hash01(r * 999) * 0.3)  // curtain
              : new THREE.Color(0x2b2f38).multiplyScalar(0.85 + hash01(r * 777) * 0.5); // depth variation
            const vOff = s.off > 0 ? s.off - TOWER.glassInset + 0.07 : s.off + TOWER.glassInset - 0.07;
            const g = s.axis === 'x'
              ? box(wW, wH, 0.04, u, y, vOff)
              : box(0.04, wH, wW, vOff, y, u);
            add(variedParts, g, shade);
          }
        }
        // lobby colonnade: slender columns every Nth grid line, ends included
        const nCols = Math.round(bays / TOWER.colSpacing);
        for (let ci = 0; ci <= nCols; ci++) {
          const u = -inner / 2 + (ci / nCols) * inner;
          // columns run 0.9 m below grade like every wall — the plaza drape is not
          // perfectly at podium height everywhere, and a floating column base reads
          // as clipping at eye level
          const g = s.axis === 'x'
            ? box(0.55, gridBot + 0.9, 0.55, u, gridBot / 2 - 0.45, s.off)
            : box(0.55, gridBot + 0.9, 0.55, s.off, gridBot / 2 - 0.45, u);
          add(concreteParts, g, cCon);
        }
      }
      // solid corner piers, soffit line to roof (the grid turns the corner as an L)
      for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
        add(concreteParts,
          box(TOWER.cornerW + TOWER.mullionD, H - gridBot, TOWER.cornerW + TOWER.mullionD,
            sx * (W / 2 - TOWER.cornerW / 2), gridBot + (H - gridBot) / 2, sz * (Dp / 2 - TOWER.cornerW / 2)),
          cCon);
      }
      // roof deck + long set-back mechanical penthouse strip
      add(concreteParts, box(W - 0.8, 0.45, Dp - 0.8, 0, gridTop - 0.2, 0), cConD);
      add(concreteParts, box(W * 0.62, TOWER.penthouseH, Dp * 0.44, 0, gridTop + TOWER.penthouseH / 2, 0), cConD);
      // lobby glass, deeply recessed behind the colonnade (runs 0.8 m below grade
      // like the columns so no ground slit can ever show under it)
      add(glassParts,
        box(W - TOWER.lobbyInset * 2, gridBot + 0.55, Dp - TOWER.lobbyInset * 2, 0, (gridBot - 1.05) / 2, 0),
        new THREE.Color(COLORS.glassLobby));
      // interior mass, faintly visible through the glass
      add(concreteParts, box(W - 2.2, gridH, Dp - 2.2, 0, gridBot + gridH / 2, 0), new THREE.Color(0x514c45));

      // collision footprint
      const hw = W / 2 + 0.3, hd = Dp / 2 + 0.3;
      const cos = Math.cos(ang), sin = Math.sin(ang);
      const cor = [[-hw, -hd], [hw, -hd], [hw, hd], [-hw, hd]].map(([lx, lz]) =>
        [cx + lx * cos + lz * sin, cz - lx * sin + lz * cos]);
      for (let k = 0; k < 4; k++) addColSeg(cor[k][0], cor[k][1], cor[(k + 1) % 4][0], cor[(k + 1) % 4][1]);
      registerPoly(cor);
    }

    const conMesh = new THREE.Mesh(
      mergeColored(concreteParts, true),
      new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.82, metalness: 0, envMapIntensity: 0.3 })
    );
    conMesh.castShadow = conMesh.receiveShadow = true;
    groupCity.add(conMesh);
    rayTargets.push(conMesh);

    const glassMesh = new THREE.Mesh(
      mergeColored(glassParts),
      new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.1, metalness: 0.7, envMapIntensity: 1.4 })
    );
    groupCity.add(glassMesh);
    towerGlassMat = glassMesh.material;
    towerGlassMat.emissive = new THREE.Color(0xffd9a0);
    towerGlassMat.emissiveIntensity = 0;

    if (variedParts.length) {
      const vm = new THREE.Mesh(
        mergeColored(variedParts),
        new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.6, metalness: 0.1 })
      );
      groupCity.add(vm);
      towerVarMat = vm.material;
      towerVarMat.emissive = new THREE.Color(0xffd08a);
      towerVarMat.emissiveIntensity = 0;
    }

    // brick-paved plaza + Baskin bronze ("Old Man, Young Man, The Future", 1966)
    if (towers.length === 3) {
      // raised brick plaza over the garage, with a step ring and lawn berms around it
      const plazaMat = new THREE.MeshStandardMaterial({ color: COLORS.plaza, roughness: 0.96 });
      const plaza = new THREE.Mesh(new THREE.CylinderGeometry(PLAZA_R, PLAZA_R, 1.0 + LAYER.plaza, 48), plazaMat);
      plaza.position.set(towersCenter.x, cityY(towersCenter.x, towersCenter.z) + (1.0 + LAYER.plaza) / 2, towersCenter.z);
      plaza.receiveShadow = plaza.castShadow = true;
      groupCity.add(plaza);
      const stepRing = new THREE.Mesh(new THREE.CylinderGeometry(PLAZA_R + 2.4, PLAZA_R + 2.4, 0.5, 48),
        new THREE.MeshStandardMaterial({ color: 0xb3ab9c, roughness: 0.95 }));
      stepRing.position.set(towersCenter.x, cityY(towersCenter.x, towersCenter.z) + 0.25, towersCenter.z);
      stepRing.receiveShadow = true;
      groupCity.add(stepRing);
      const bermMat = new THREE.MeshStandardMaterial({ color: COLORS.park, roughness: 1 });
      for (let k = 0; k < 7; k++) {
        const ang = k * (Math.PI * 2 / 7) + 0.4;
        const rr = PLAZA_R + 24 + hash01(k * 3.1) * 14;
        const bx = towersCenter.x + Math.cos(ang) * rr, bz = towersCenter.z + Math.sin(ang) * rr;
        if (nearRoad(bx, bz, 6) || insideBuilding(bx, bz) || nearBuildingEdge(bx, bz, 9) || Math.hypot(bx - 16, bz - 77) < 48) continue;
        const berm = new THREE.Mesh(new THREE.SphereGeometry(1, 14, 8), bermMat);
        berm.scale.set(13 + hash01(k) * 6, 1.5, 6 + hash01(k * 7) * 3);
        berm.rotation.y = ang + Math.PI / 2;
        bermSpots.push([bx, bz, berm.scale.x, berm.scale.z, berm.rotation.y]);
        berm.position.set(bx, cityY(bx, bz) + 0.1, bz);
        berm.receiveShadow = true;
        groupCity.add(berm);
      }

      const bronzeMat = new THREE.MeshStandardMaterial({ color: COLORS.bronze, roughness: 0.45, metalness: 0.75, envMapIntensity: 0.8 });
      const sc = new THREE.Group();
      const b1 = new THREE.Mesh(new THREE.BoxGeometry(0.8, 2.0, 0.6), bronzeMat);  // young man, standing
      b1.position.set(0, 1.35, 0); b1.rotation.y = 0.4;
      const b2 = new THREE.Mesh(new THREE.BoxGeometry(0.9, 1.4, 0.9), bronzeMat);  // old man on his cube
      b2.position.set(1.6, 1.05, 0.4); b2.rotation.y = -0.3;
      const b3 = new THREE.Mesh(new THREE.BoxGeometry(1.4, 1.1, 0.5), bronzeMat);  // the winged Future
      b3.position.set(0.8, 2.1, -0.9); b3.rotation.y = 0.15;
      const base = new THREE.Mesh(new THREE.BoxGeometry(3.4, 0.7, 3.0),
        new THREE.MeshStandardMaterial({ color: 0x8a5a44, roughness: 0.9 }));
      base.position.set(0.8, 0.35, 0);
      sc.add(b1, b2, b3, base);
      sc.position.set(towersCenter.x - 16, siteY(towersCenter.x - 16, towersCenter.z + 28, 'ground') + LAYER.plaza, towersCenter.z + 28);
      sc.traverse(o => { o.castShadow = true; });
      groupCity.add(sc);
    }
  });

  // ------------------------------------------------ the outer districts
  // Center City, South Philadelphia, Northern Liberties, Fishtown/Kensington:
  // ~108k OSM footprints packed as int16 (0.2 m) and rendered as lean indexed
  // chunks — 8-bit normals/colors, no roofs or cornices, world-space windows.
  const outerMeshes = [];
  step('Raising the outer districts', async () => {
    if (typeof WIDE_B64 === 'undefined' || !WIDE_B64) return;
    const bin = Uint8Array.from(atob(WIDE_B64), ch => ch.charCodeAt(0));
    WIDE_B64 = null;   // the 5 MB base64 string has served its purpose
    const hdr = new Int32Array(bin.buffer, 0, 4);
    const body = new Int16Array(bin.buffer, 16);
    const hasAttr = hdr[0] === 0x5348545A;
    if (hdr[0] !== 0x53485458 && !hasAttr) return;
    let k = 0;
    const S = 0.2;
    const CH = 700;
    const chunks = new Map(), glassChunks = new Map();
    const chunkIn = (map) => (x, z) => {
      const key = Math.floor(x / CH) + ':' + Math.floor(z / CH);
      let c = map.get(key);
      if (!c) { c = { pos: [], nor: [], col: [], sty: [], bas: [], flh: [], idx: [], n: 0 }; map.set(key, c); }
      return c;
    };
    const getChunk = chunkIn(chunks), getGlassChunk = chunkIn(glassChunks);
    const glassPal = [0x8fb2cc, 0x9cb9c9, 0xa9bfc9, 0x7ea6c6];
    // OSM maps the suspension-bridge towers/anchorages as building footprints; the
    // bridges build their own steel, so drop any footprint sitting on them
    const BRIDGE_SKIP = [[620.8, -889.9, 60], [1148.8, -770, 60], [1037.2, 4391.6, 60], [1620.1, 4510.7, 60], [400, -940, 45], [1360, -722, 45],
      // landmark towers rebuilt with real massing below: City Hall tower, One & Two Liberty Place
      [-1603, -802, 24], [-1995, -785, 25], [-1937, -689, 20], [-1932.3, -718.2, 9],
      // Philadelphia Museum of Art — custom golden-temple rebuild below owns the hilltop
      [-3094, -2225, 130]];
    // signature curtain walls, matched by location (local metres east/south of the towers)
    const GLASS_TINTS = [
      [-1995, -785, 60, 0x6899c4],   // One Liberty Place complex — blue glass
      [-1937, -689, 55, 0x6899c4],   // Two Liberty Place
      [-1930, -714, 30, 0x6899c4],   // Liberty Place mid-rise element
      [-2087, -965, 85, 0xb4c2c8],   // Comcast Center — silver, near-mirror
      [-2224, -1064, 95, 0xa3b1b8],  // Comcast Technology Center — neutral gray glass
      [-3231, -633, 80, 0xb5d0dc],   // FMC Tower — icy blue-white
      [-3205, -1297, 90, 0x9cb8cf],  // Cira Centre
      [-1771, -622, 70, 0x53748e],   // W / Element — dark glass
      [-2548, -821, 70, 0xa5c4d4],   // Murano
      [-2334, -821, 80, 0x6f9cc0],   // 1901 Market (IBC blue)
    ];
    const palLow = [0x9b5a43, 0x8f5140, 0xa56a4e, 0x7d4a3a, 0x94523d, 0xb8a894, 0xa79a86, 0x8d8a86, 0xc4b49b, 0x9a6b55];
    const palCom = [0x9d968a, 0x8f887b, 0xa8a191, 0x83817c, 0x9aa0a4, 0xb3aca0];
    const palInd = [0x8a7e72, 0x7b736b, 0x9c9286, 0x8e5a48];
    // real skylines are not white: precast tan, limestone, aluminum, blue-gray steel,
    // dark curtain wall, bronze — towers draw from this instead of the pale palCom
    const palTall = [0xa39b8b, 0x8e979e, 0x6e7681, 0x50555e, 0x5c5348, 0x8a8478, 0x9c9284, 0x42474f, 0x76664f, 0x66707c];
    const c = new THREE.Color();
    const cCap = new THREE.Color();
    const v2 = [];
    const yieldNow = () => new Promise(r => { const ch = new MessageChannel(); ch.port1.onmessage = () => r(); ch.port2.postMessage(0); }); // not timer-clamped in hidden tabs
    const pushV = (ch, x, y, z, nx, ny, nz, r, g, b, st, base, fh) => {
      ch.pos.push(x, y, z); ch.nor.push(nx * 127, ny * 127, nz * 127); ch.col.push(r * 255, g * 255, b * 255); ch.sty.push(st); ch.bas.push(base); ch.flh.push(fh || 0);
      return ch.n++;
    };
    const appendBuilding = (ch, poly, y0, y1, color, st, base, holes, fh, capColor) => {
      const sign = signedArea(poly) > 0 ? 1 : -1;
      const n = poly.length;
      const r = color.r, g = color.g, b = color.b;
      const wallRing = (ring, sg) => { for (let i = 0; i < ring.length; i++) {
        const a = ring[i], q = ring[(i + 1) % ring.length];
        const dx = q[0] - a[0], dz = q[1] - a[1];
        const L = Math.hypot(dx, dz);
        if (L < 0.05) continue;
        const nx = (dz / L) * sg, nz = (-dx / L) * sg;
        const i0 = pushV(ch, a[0], y0, a[1], nx, 0, nz, r, g, b, st, base, fh);
        const i1 = pushV(ch, q[0], y0, q[1], nx, 0, nz, r, g, b, st, base, fh);
        const i2 = pushV(ch, q[0], y1, q[1], nx, 0, nz, r, g, b, st, base, fh);
        const i3 = pushV(ch, a[0], y1, a[1], nx, 0, nz, r, g, b, st, base, fh);
        if (((-dz) * nx + dx * nz) >= 0) ch.idx.push(i0, i1, i2, i0, i2, i3); else ch.idx.push(i0, i2, i1, i0, i3, i2);
      } };
      if (holes) for (const hl of holes) wallRing(hl, signedArea(hl) > 0 ? -1 : 1);
      for (let i = 0; i < n; i++) {
        const a = poly[i], q = poly[(i + 1) % n];
        const dx = q[0] - a[0], dz = q[1] - a[1];
        const L = Math.hypot(dx, dz);
        if (L < 0.05) continue;
        const nx = (dz / L) * sign, nz = (-dx / L) * sign;
        const i0 = pushV(ch, a[0], y0, a[1], nx, 0, nz, r, g, b, st, base, fh);
        const i1 = pushV(ch, q[0], y0, q[1], nx, 0, nz, r, g, b, st, base, fh);
        const i2 = pushV(ch, q[0], y1, q[1], nx, 0, nz, r, g, b, st, base, fh);
        const i3 = pushV(ch, a[0], y1, a[1], nx, 0, nz, r, g, b, st, base, fh);
        if (((-dz) * nx + dx * nz) >= 0) ch.idx.push(i0, i1, i2, i0, i2, i3); else ch.idx.push(i0, i2, i1, i0, i3, i2);
      }
      // roof cap (ring when holes are given)
      v2.length = 0;
      for (let i = 0; i < n; i++) v2.push(new THREE.Vector2(poly[i][0], -poly[i][1]));
      const hv = (holes || []).map(hl => hl.map(q => new THREE.Vector2(q[0], -q[1])));
      let tris;
      try { tris = THREE.ShapeUtils.triangulateShape(v2, hv); } catch (e) { return; }
      const capStart = ch.n;
      const cr = capColor ? capColor.r : r * 0.93, cg = capColor ? capColor.g : g * 0.93, cb = capColor ? capColor.b : b * 0.93;
      for (let i = 0; i < n; i++) pushV(ch, poly[i][0], y1, poly[i][1], 0, 1, 0, cr, cg, cb, 3, base);
      for (const hl of (holes || [])) for (const q of hl) pushV(ch, q[0], y1, q[1], 0, 1, 0, cr, cg, cb, 3, base);
      // earcut emits CCW triangles in the shape plane regardless of ring winding,
      // and CCW in (x,-z) maps to up-facing — never flip by ring orientation
      for (const t of tris) ch.idx.push(capStart + t[0], capStart + t[1], capStart + t[2]);
    };
    const nb = hdr[1];
    let njPoly = null;   // USS New Jersey hull outline — custom battleship below
    for (let i = 0; i < nb; i++) {
      const n = body[k++], h = body[k++] / 5, mh = body[k++] / 5, t = body[k++];
      const attrW = hasAttr ? body[k++] : -1, roofW = hasAttr ? body[k++] : -1;
      const poly = new Array(n);
      for (let j = 0; j < n; j++) { poly[j] = [body[k++] * S, body[k++] * S]; }
      const [cx, cz] = polyCentroid(poly);
      if (BRIDGE_SKIP.some(q => Math.hypot(cx - q[0], cz - q[1]) < q[2])) continue;
      if (ovpStraddle(poly, cx, cz)) continue;   // nothing real stands across a motorway deck
      if (t === 7 && Math.hypot(cx - 996, cz - 663) < 80) { njPoly = poly; continue; }
      const base = siteY(cx, cz, 'ground');
      const hsh = hash01(i * 7.13);
      const fa = attrW >= 0 ? [attrW & 7, (attrW >> 3) & 7, (attrW >> 6) & 15, 0] : null;
      const fh = attrW >= 0 && ((attrW >> 10) & 31) > 0 ? 2.2 + (((attrW >> 10) & 31) - 1) * 0.1 : 0;
      let pool = h > 45 ? palTall : (t === 3 || t === 6 || h > 25) ? palCom : (t === 4 ? palInd : palLow);
      if (fa && h <= 45 && t <= 4) { const p2 = opaWallPool(fa); if (p2) pool = p2; }
      c.set(pool[Math.floor(hsh * pool.length) % pool.length]).multiplyScalar(h > 45 ? 0.94 + hash01(i * 11.3) * 0.12 : 0.9 + hash01(i * 11.3) * 0.2);
      let style = h > 30 ? 2 : (t === 3 ? 5 : 0);
      if (fa && h <= 30 && t <= 4) style = opaStyle(fa, h);
      const capC = roofW >= 0 && ROOF_PAL ? cCap.copy(ROOF_PAL[roofW]).multiplyScalar(0.9 + hsh * 0.18) : null;
      if (t === 10) { // glass tower parts: reflective material, no painted windows
        c.set(glassPal[Math.floor(hsh * glassPal.length) % glassPal.length]);
        for (const gt of GLASS_TINTS) if (Math.hypot(cx - gt[0], cz - gt[1]) < gt[2]) { c.set(gt[3]); break; }
        appendBuilding(getGlassChunk(cx, cz), poly, mh > 0 ? base + mh : base - 1.0, base + h, c, 3, base);
        if ((i & 4095) === 4095) { loadmsg.textContent = 'Raising the outer districts, ' + Math.round(i / nb * 100) + '%'; await yieldNow(); }
        continue;
      }
      const chk = getChunk(cx, cz);
      if (t === 8) { // stadium: seating bowl around a sunken field
        const isBaseball = cz < 4650;
        const inner = poly.map(q => [cx + (q[0] - cx) * 0.55, cz + (q[1] - cz) * 0.55]);
        const ob = orientedBox(poly); const ax = obbAxis(ob);
        // contiguous arc of a ring passing keepFn (rotated so the arc never wraps the array seam)
        const arcOf = (pts, keepFn) => {
          const n2 = pts.length;
          let s0 = -1;
          for (let ii = 0; ii < n2; ii++) if (!keepFn(pts[ii])) { s0 = ii; break; }
          if (s0 < 0) return pts.slice();
          const out = [];
          for (let ii = 1; ii <= n2; ii++) { const q = pts[(s0 + ii) % n2]; if (keepFn(q)) out.push(q); }
          return out;
        };
        const upperRing = (keepFn, y0, y1, hex) => {
          const A = arcOf(poly, keepFn), B = arcOf(inner, keepFn);
          if (A.length < 3 || B.length < 3) return;
          c.set(hex);
          appendBuilding(chk, A.concat(B.slice().reverse()), base + y0, base + y1, c, 3, base);
        };
        // field — fan-triangulated about the centroid (earcut chokes on some OSM rings)
        // and high enough that nothing inside the bowl pokes through
        const f0 = chk.n; c.set(0x4f7a3a);
        for (const q of inner) pushV(chk, q[0], base + 1.9, q[1], 0, 1, 0, c.r, c.g, c.b, 3, base);
        const fc = pushV(chk, cx, base + 1.9, cz, 0, 1, 0, c.r, c.g, c.b, 3, base);
        for (let j = 0; j < inner.length; j++) {
          const j2 = (j + 1) % inner.length;
          chk.idx.push(f0 + j, fc, f0 + j2, f0 + j, f0 + j2, fc);
        }
        if (isBaseball) {
          // Citizens Bank Park: brick drum, upper horseshoe open beyond the outfield,
          // pale-green canopy band, dark-red light standards, the left-field scoreboard
          const hx = -1861, hz = 4429;
          const dh = Math.hypot(hx - cx, hz - cz), dhx = (hx - cx) / dh, dhz = (hz - cz) / dh;
          const keepHome = (q) => ((q[0] - cx) * dhx + (q[1] - cz) * dhz) > -0.28 * Math.hypot(q[0] - cx, q[1] - cz);
          c.set(0x8f4f3e);
          appendBuilding(chk, poly, base - 1.0, base + 15, c, 3, base, [inner]);
          upperRing(keepHome, 15, 38, 0x9a9184);
          upperRing(keepHome, 38, 40.5, 0x7fa38c);
          { // infield dirt diamond just in from home plate
            const fx2 = hx - dhx * 20, fz2 = hz - dhz * 20;
            const dPoly = [[fx2 + dhx * 20, fz2 + dhz * 20], [fx2 - dhz * 20, fz2 + dhx * 20], [fx2 - dhx * 20, fz2 - dhz * 20], [fx2 + dhz * 20, fz2 - dhx * 20]];
            const d0 = chk.n; c.set(0xb08355);
            for (const q of dPoly) pushV(chk, q[0], base + 2.05, q[1], 0, 1, 0, c.r, c.g, c.b, 3, base);
            chk.idx.push(d0, d0 + 2, d0 + 1, d0, d0 + 3, d0 + 2);
          }
          c.set(0x6e3a30);
          for (const [su, sv] of [[-0.78, -0.78], [0.78, -0.78], [0.78, 0.78], [-0.78, 0.78]]) {
            const lx = ob.cx + ax.ax * ax.hl * su + ax.px * ax.hs * sv, lz = ob.cz + ax.az * ax.hl * su + ax.pz * ax.hs * sv;
            appendBuilding(chk, [[lx - 1.3, lz - 1.3], [lx + 1.3, lz - 1.3], [lx + 1.3, lz + 1.3], [lx - 1.3, lz + 1.3]], base + 12, base + 50, c, 3, base);
            appendBuilding(chk, [[lx - 3.6, lz - 1.1], [lx + 3.6, lz - 1.1], [lx + 3.6, lz + 1.1], [lx - 3.6, lz + 1.1]], base + 50, base + 55, c, 3, base);
          }
          const sx = -1926, sz = 4330; // left-field scoreboard
          c.set(0x2c3833);
          appendBuilding(chk, [[sx - 20, sz - 2], [sx + 20, sz - 2], [sx + 20, sz + 2], [sx - 20, sz + 2]], base + 12, base + 65, c, 3, base);
        } else {
          // Lincoln Financial Field: dark bowl, silver sideline stands, steel wing
          // canopies with a white fascia, four corner masts, open corners
          c.set(0x4a4f4c);
          appendBuilding(chk, poly, base - 1.0, base + 14, c, 3, base, [inner]);
          for (const sgn of [-1, 1]) {
            upperRing((q) => ((q[0] - ob.cx) * ax.px + (q[1] - ob.cz) * ax.pz) * sgn > ax.hs * 0.30, 14, 46, 0x9aa0a3);
            const cp = [[-ax.hl * 0.6, sgn * ax.hs * 0.40], [ax.hl * 0.6, sgn * ax.hs * 0.40], [ax.hl * 0.6, sgn * ax.hs * 1.0], [-ax.hl * 0.6, sgn * ax.hs * 1.0]]
              .map(([u, v]) => [ob.cx + ax.ax * u + ax.px * v, ob.cz + ax.az * u + ax.pz * v]);
            c.set(0x454b4e);
            appendBuilding(chk, cp, base + 50.5, base + 54, c, 3, base);
            const fe = [[-ax.hl * 0.6, sgn * ax.hs * 0.34], [ax.hl * 0.6, sgn * ax.hs * 0.34], [ax.hl * 0.6, sgn * ax.hs * 0.42], [-ax.hl * 0.6, sgn * ax.hs * 0.42]]
              .map(([u, v]) => [ob.cx + ax.ax * u + ax.px * v, ob.cz + ax.az * u + ax.pz * v]);
            c.set(0xe4e7e9);
            appendBuilding(chk, fe, base + 53, base + 55, c, 3, base);
          }
          c.set(0x8f979b);
          for (const [su, sv] of [[-0.8, -0.9], [0.8, -0.9], [0.8, 0.9], [-0.8, 0.9]]) {
            const mx = ob.cx + ax.ax * ax.hl * su + ax.px * ax.hs * sv, mz = ob.cz + ax.az * ax.hl * su + ax.pz * ax.hs * sv;
            appendBuilding(chk, [[mx - 1.3, mz - 1.3], [mx + 1.3, mz - 1.3], [mx + 1.3, mz + 1.3], [mx - 1.3, mz + 1.3]], base + 14, base + 64, c, 3, base);
          }
        }
      } else if (t === 9) { // Xfinity Mobile Arena: dark walls, glass entry, pale roof slab
        c.set(0x3a3e44);
        appendBuilding(chk, poly, base - 1.0, base + 21, c, 3, base);
        c.set(0x565b60);
        appendBuilding(chk, poly.map(q => [cx + (q[0] - cx) * 0.86, cz + (q[1] - cz) * 0.86]), base + 21, base + 36, c, 3, base);
        c.set(0xcfd2d4);
        appendBuilding(chk, poly.map(q => [cx + (q[0] - cx) * 0.88, cz + (q[1] - cz) * 0.88]), base + 36, base + 38.5, c, 3, base);
        { // glass rotunda + entry bar on the corner, purple screen accents on two faces
          const ob9 = orientedBox(poly); const ax9 = obbAxis(ob9);
          const ex2 = ob9.cx + ax9.ax * ax9.hl * 0.62 + ax9.px * ax9.hs * 0.5, ez2 = ob9.cz + ax9.az * ax9.hl * 0.62 + ax9.pz * ax9.hs * 0.5;
          const oct = [];
          for (let k2 = 0; k2 < 8; k2++) oct.push([ex2 + Math.cos(k2 * Math.PI / 4) * 9, ez2 + Math.sin(k2 * Math.PI / 4) * 9]);
          c.set(0x9fc0d8);
          appendBuilding(chk, oct, base - 1.0, base + 16, c, 3, base);
          c.set(0x5b3f9e);
          for (const sv of [-1, 1]) {
            const px2 = ob9.cx + ax9.px * sv * ax9.hs * 0.97, pz2 = ob9.cz + ax9.pz * sv * ax9.hs * 0.97;
            appendBuilding(chk, [[px2 - 9, pz2 - 1], [px2 + 9, pz2 - 1], [px2 + 9, pz2 + 1], [px2 - 9, pz2 + 1]], base + 22, base + 32, c, 3, base);
          }
        }
      } else appendBuilding(chk, poly, mh > 0 ? base + mh : base - 1.0, base + h, c, style, base, null, fh, capC);
      if (t === 5 && mh === 0 && Math.abs(signedArea(poly)) > 350 && h < 60) {
        // church: square tower to h+9, then a pyramidal spire — the districts' skyline is their steeples
        const tw = 5.5, towerTop = base + h + 9, apex = base + h + 24;
        const sq = [[cx - tw / 2, cz - tw / 2], [cx + tw / 2, cz - tw / 2], [cx + tw / 2, cz + tw / 2], [cx - tw / 2, cz + tw / 2]];
        appendBuilding(chk, sq, base, towerTop, c, 3, base);
        const i0 = chk.n;
        const sc = 0.9;
        for (const q of sq) pushV(chk, q[0], towerTop, q[1], 0, 0.7, 0, c.r * sc, c.g * sc, c.b * sc, 3, base);
        pushV(chk, cx, apex, cz, 0, 1, 0, c.r * sc, c.g * sc, c.b * sc, 3, base);
        chk.idx.push(i0, i0 + 1, i0 + 4, i0 + 1, i0 + 2, i0 + 4, i0 + 2, i0 + 3, i0 + 4, i0 + 3, i0, i0 + 4);
      }
      if ((i & 4095) === 4095) { loadmsg.textContent = 'Raising the outer districts, ' + Math.round(i / nb * 100) + '%'; await yieldNow(); }
    }
    // outer streets. Continuity work: endpoint-snapped heights (no steps at OSM way
    // splits), joint fans at bends, real bridge decks over the rivers, aligned-only
    // duplicate dropping, and a lift blend at the core seam.
    const rc = { pos: [], col: [], idx: [], n: 0 };
    const roadCol = [0x3b3833, 0x3b3833, 0x3f3c37, 0x3f3c37, 0x43403b, 0x45423d, 0x7c584a];
    const yMapW = new Map();
    const ySnap = (map, x, z, y) => {
      const key = Math.round(x * 2) + ':' + Math.round(z * 2);
      const v = map.get(key);
      if (v !== undefined) return v;
      map.set(key, y);
      return y;
    };
    const rcFan = (x, y, z, hw, cr, cg, cb) => {
      const c0 = rc.n;
      rc.pos.push(x, y, z);
      rc.col.push(cr, cg, cb);
      rc.n++;
      for (let s6 = 0; s6 < 7; s6++) {
        const ang = s6 / 6 * Math.PI * 2;
        rc.pos.push(x + Math.cos(ang) * hw, y, z + Math.sin(ang) * hw);
        rc.col.push(cr, cg, cb);
        rc.n++;
      }
      for (let s6 = 0; s6 < 6; s6++) rc.idx.push(c0, c0 + 1 + s6, c0 + 2 + s6);
    };
    for (let i = 0; i < hdr[2]; i++) {
      const n = body[k++], w = body[k++] / 10, t = body[k++];
      let pts = new Array(n);
      for (let j = 0; j < n; j++) pts[j] = [body[k++] * S, body[k++] * S];
      if (t <= 5) for (let j = 0; j + 1 < pts.length; j++) septaRoadAdd(pts[j][0], pts[j][1], pts[j + 1][0], pts[j + 1][1]);
      pts = densify(pts, 15);
      c.set(roadCol[t] || 0x3b3833);
      const hw = w / 2;
      const thr = TERRAIN.water + 0.6;
      for (let j = 0; j < pts.length - 1; j++) {
        const a = pts[j], q = pts[j + 1];
        let dx = q[0] - a[0], dz = q[1] - a[1];
        const L = Math.hypot(dx, dz); if (L < 0.01) continue;
        dx /= L; dz /= L;
        const mx = (a[0] + q[0]) / 2, mz = (a[1] + q[1]) / 2;
        const aLow = demY(a[0], a[1]) < thr, qLow = demY(q[0], q[1]) < thr;
        let deck = 0;
        if ((aLow || qLow) && riverCorridor(mx, mz)) {
          if (t > 2) { if (aLow && qLow) continue; }         // minor roads don't bridge rivers
          else deck = t === 0 ? 20 : 13;                     // major roads become bridge decks
        }
        if (deck && wwbNear(mx, mz)) continue;               // the custom WWB deck owns its crossing
        if (ovpOwned(a[0], a[1], q[0], q[1])) continue;      // a baked overpass deck or sunken roadway owns it
        // a wide segment lying ALONG a core street is a duplicate and would z-fight it
        if (a[0] > CORE_EXT.x0 - 38 && a[0] < CORE_EXT.x1 + 38 && a[1] > CORE_EXT.z0 - 38 && a[1] < CORE_EXT.z1 + 38 &&
            q[0] > CORE_EXT.x0 - 38 && q[0] < CORE_EXT.x1 + 38 && q[1] > CORE_EXT.z0 - 38 && q[1] < CORE_EXT.z1 + 38 &&
            nearRoadAligned(a[0], a[1], 3.5, dx, dz) && nearRoadAligned(q[0], q[1], 3.5, dx, dz) &&
            nearRoadAligned(mx, mz, 2.5, dx, dz)) continue;
        const px = -dz * hw, pz = dx * hw;
        // class-separated lifts, blended down to the core formula near the seam
        const dOut = Math.max(CORE_EXT.x0 - mx, mx - CORE_EXT.x1, CORE_EXT.z0 - mz, mz - CORE_EXT.z1, 0);
        const bl = clamp(dOut / 60, 0, 1);
        const jr = lerp(LAYER.road + hash01(i * 3.7 + 1.1) * 0.06,
          LAYER.road + (6 - Math.min(t, 6)) * 0.055 + hash01(i * 3.7 + 1.1) * 0.1, bl);
        let ya0 = siteY(a[0], a[1], 'road'), yb0 = siteY(q[0], q[1], 'road');
        if (deck) {
          ya0 = Math.max(ya0, TERRAIN.water + (aLow ? deck : deck * 0.35));
          yb0 = Math.max(yb0, TERRAIN.water + (qLow ? deck : deck * 0.35));
        }
        const ya = ySnap(yMapW, a[0], a[1], ya0 + jr), yb = ySnap(yMapW, q[0], q[1], yb0 + jr);
        const b0 = rc.n;
        rc.pos.push(a[0] + px, ya, a[1] + pz, q[0] + px, yb, q[1] + pz, q[0] - px, yb, q[1] - pz, a[0] - px, ya, a[1] - pz);
        for (let m = 0; m < 4; m++) rc.col.push(c.r * 255, c.g * 255, c.b * 255);
        rc.n += 4;
        rc.idx.push(b0, b0 + 1, b0 + 2, b0, b0 + 2, b0 + 3);
        if (j > 0) { // joint fan where the heading bends (quad strips leave notches)
          const p0 = pts[j - 1];
          let ux0 = a[0] - p0[0], uz0 = a[1] - p0[1];
          const L0 = Math.hypot(ux0, uz0) || 1;
          ux0 /= L0; uz0 /= L0;
          if (ux0 * dx + uz0 * dz < 0.99) rcFan(a[0], ya, a[1], hw, c.r * 255, c.g * 255, c.b * 255);
        }
      }
    }
    // -------- landmark rebuilds: City Hall tower + One & Two Liberty Place --------
    // (their OSM parts were skipped above; research-backed massing/colors)
    const lmGlass = [], lmTrim = [];
    {
      const ryG = Math.atan2(-fl.nz, fl.nx);           // rotate local +x onto the grid's east-west
      const sqPoly = (cx, cz, w, d) => [[-w / 2, -d / 2], [w / 2, -d / 2], [w / 2, d / 2], [-w / 2, d / 2]]
        .map(([u, v]) => [cx + fl.nx * u + fl.dx * v, cz + fl.nz * u + fl.dz * v]);
      const gPrism = (cx, cz, w, len, eaveY, apexY, alongNS) => {
        // gable prism: ridge through the center, sloping to eaves on both sides
        const hw = w / 2, hl = len / 2;
        const t = [
          -hl, eaveY, -hw, hl, apexY, 0, hl, eaveY, -hw, -hl, eaveY, -hw, -hl, apexY, 0, hl, apexY, 0,
          hl, eaveY, hw, -hl, apexY, 0, -hl, eaveY, hw, hl, eaveY, hw, hl, apexY, 0, -hl, apexY, 0,
          hl, eaveY, -hw, hl, apexY, 0, hl, eaveY, hw,
          -hl, eaveY, hw, -hl, apexY, 0, -hl, eaveY, -hw,
        ];
        const g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(t), 3));
        g.computeVertexNormals();
        g.rotateY(ryG + (alongNS ? Math.PI / 2 : 0));
        g.translate(cx, 0, cz);
        return g;
      };
      const pyr4 = (cx, cz, w, y0, y1, rT) => {
        const g = new THREE.CylinderGeometry(rT || 0.01, w * 0.707, y1 - y0, 4, 1);
        g.rotateY(Math.PI / 4 + ryG);
        g.translate(cx, (y0 + y1) / 2, cz);
        return g;
      };
      const crown = (cx, cz, base, tiers, gc, wc) => {
        for (const [w, wallTop, apex] of tiers) {
          lmGlass.push({ geom: gPrism(cx, cz, w, w, base + wallTop, base + apex, false), color: gc, style: 3 });
          lmGlass.push({ geom: gPrism(cx, cz, w, w, base + wallTop, base + apex, true), color: gc, style: 3 });
          // white trim: eave band + crossed ridge caps read as the nested chevrons
          lmTrim.push({ geom: box(w + 0.9, 1.3, w + 0.9, cx, base + wallTop + 0.2, cz, ryG), color: wc, style: 3 });
          const rl = Math.hypot(w / 2, apex - wallTop) * 2;
          for (const ns of [0, 1]) {
            const rg = box(w, 0.75, 0.75, 0, 0, 0, 0);
            rg.rotateY(ryG + ns * Math.PI / 2);
            rg.translate(cx, base + apex - 0.2, cz);
            lmTrim.push({ geom: rg, color: wc, style: 3, _rl: rl });
          }
        }
      };
      const cWhite = new THREE.Color(0xdce9f1), cSilver = new THREE.Color(0xcfd6db);
      // --- One Liberty Place (17th & Market): sheer blue shaft, four gabled tiers, needle spire
      {
        const cx = -1995, cz = -785, base = siteY(cx, cz, 'ground');
        const gc = new THREE.Color(0x4f7897), gcCrown = new THREE.Color(0x35679a);
        c.set(0x9c9186);
        appendBuilding(getChunk(cx, cz), sqPoly(cx, cz, 56, 56), base - 1, base + 12, c, 5, base);
        c.copy(gc);
        appendBuilding(getGlassChunk(cx, cz), sqPoly(cx, cz, 48.5, 48.5), base - 1, base + 212, c, 3, base);
        for (const [w, top] of [[36, 223], [26, 233], [17, 242]]) {
          appendBuilding(getGlassChunk(cx, cz), sqPoly(cx, cz, w, w), base + 180, base + top, c, 3, base);
        }
        crown(cx, cz, base, [[48.5, 212, 226], [36, 223, 237], [26, 233, 244], [17, 242, 251]], gcCrown, cWhite);
        lmTrim.push({ geom: pyr4(cx, cz, 8, base + 251, base + 258, 1.0), color: cSilver, style: 3 });
        const mast = new THREE.CylinderGeometry(0.7, 1.0, 23, 8); mast.translate(cx, base + 258 + 11.5, cz);
        lmTrim.push({ geom: mast, color: cSilver, style: 3 });
        const ndl = new THREE.CylinderGeometry(0.05, 0.4, 7, 6); ndl.translate(cx, base + 281 + 3.5, cz);
        lmTrim.push({ geom: ndl, color: cSilver, style: 3 });
      }
      // --- Two Liberty Place (16th & Chestnut): squatter, two big gable tiers, white finial
      {
        const cx = -1937, cz = -689, base = siteY(cx, cz, 'ground');
        const gc = new THREE.Color(0x4a7ba3), gcCrown = new THREE.Color(0x35679a);
        c.copy(gc);
        appendBuilding(getGlassChunk(cx, cz), sqPoly(cx, cz, 38.5, 38.5), base - 1, base + 150, c, 3, base);
        appendBuilding(getGlassChunk(cx, cz), sqPoly(cx, cz, 36, 36), base + 148, base + 185, c, 3, base);
        appendBuilding(getGlassChunk(cx, cz), sqPoly(cx, cz, 34, 34), base + 183, base + 207, c, 3, base);
        appendBuilding(getGlassChunk(cx, cz), sqPoly(cx, cz, 22, 22), base + 205, base + 224, c, 3, base);
        crown(cx, cz, base, [[34, 207, 228], [22, 224, 253]], gcCrown, cWhite);
        lmTrim.push({ geom: pyr4(cx, cz, 5, base + 253, base + 258, 0.4), color: cWhite, style: 3 });
      }
      // --- City Hall: the full Second Empire block (its outline was dropped at pack
      // time for containing part centroids, and the wings were never mapped as parts,
      // so the tower used to rise from bare ground), plus the ornate tower and Penn
      {
        const cx = -1603, cz = -802, base = siteY(cx, cz, 'ground');
        const bx = cx + fl.dx * 55, bz = cz + fl.dz * 55;    // block center: tower on the north face
        const cStone = new THREE.Color(0xb3aa99);
        const cSlate = new THREE.Color(0x51565b);
        const cTower = new THREE.Color(0xc4bdb0);
        const cWhiteM = new THREE.Color(0xdde0e2);           // painted metal above the masonry limit
        const cDome = new THREE.Color(0xbfc9d3);
        const cPenn = new THREE.Color(0x4c4536);             // weathered bronze, warm dark
        // hollow square around the courtyard, arched-window facade style, mansard wings
        c.copy(cStone);
        appendBuilding(getChunk(bx, bz), sqPoly(bx, bz, 148, 143), base - 1, base + 27, c, 1, base, [sqPoly(bx, bz, 64, 59)]);
        for (const [du, dv, ns] of [[0, -50.5, false], [0, 50.5, false], [-53, 0, true], [53, 0, true]]) {
          const wx = bx + fl.nx * du + fl.dx * dv, wz = bz + fl.nz * du + fl.dz * dv;
          lmTrim.push({ geom: gPrism(wx, wz, 40, ns ? 139 : 144, base + 26.9, base + 33.5, ns), color: cSlate, style: 3 });
        }
        for (const su of [-1, 1]) for (const sv of [-1, 1]) { // corner pavilions with steep caps
          const px2 = bx + fl.nx * su * 62 + fl.dx * sv * 59.5, pz2 = bz + fl.nz * su * 62 + fl.dz * sv * 59.5;
          c.copy(cStone);
          appendBuilding(getChunk(px2, pz2), sqPoly(px2, pz2, 25, 25), base - 1, base + 32, c, 1, base);
          lmTrim.push({ geom: pyr4(px2, pz2, 21, base + 32, base + 43, 3.0), color: cSlate, style: 3 });
        }
        for (const [du, dv] of [[74, 0], [-74, 0], [0, 71.5]]) { // center pavilions (E/W/S; N is the tower)
          const px2 = bx + fl.nx * du + fl.dx * dv, pz2 = bz + fl.nz * du + fl.dz * dv;
          c.copy(cStone);
          appendBuilding(getChunk(px2, pz2), sqPoly(px2, pz2, du === 0 ? 30 : 22, du === 0 ? 22 : 30), base - 1, base + 31, c, 1, base);
          lmTrim.push({ geom: pyr4(px2, pz2, 19, base + 31, base + 41, 2.6), color: cSlate, style: 3 });
        }
        // tower: arched-window masonry shaft to the 337 ft masonry limit, in stages
        c.copy(cTower);
        appendBuilding(getChunk(cx, cz), sqPoly(cx, cz, 26, 26), base - 1, base + 40, c, 1, base);
        appendBuilding(getChunk(cx, cz), sqPoly(cx, cz, 22, 22), base + 38, base + 96, c, 1, base);
        appendBuilding(getChunk(cx, cz), sqPoly(cx, cz, 19, 19), base + 94, base + 102.7, c, 1, base);
        // white cast-iron clock stage with corner turrets
        c.copy(cWhiteM);
        appendBuilding(getChunk(cx, cz), sqPoly(cx, cz, 16.5, 16.5), base + 102.7, base + 124, c, 1, base);
        for (const su of [-1, 1]) for (const sv of [-1, 1]) {
          const tx = cx + fl.nx * su * 8 + fl.dx * sv * 8, tz = cz + fl.nz * su * 8 + fl.dz * sv * 8;
          const tur = new THREE.CylinderGeometry(1.5, 1.5, 23, 8); tur.translate(tx, base + 103 + 11.5, tz);
          lmTrim.push({ geom: tur, color: cWhiteM, style: 3 });
          const tc = new THREE.CylinderGeometry(0.1, 1.5, 3.2, 8); tc.translate(tx, base + 126.5 + 1.6, tz);
          lmTrim.push({ geom: tc, color: cDome, style: 3 });
        }
        for (const ns of [0, 1]) for (const s of [-1, 1]) {   // amber clock faces on dark surrounds
          const ux = ns ? fl.dx : fl.nx, uz = ns ? fl.dz : fl.nz;
          const rim = new THREE.CylinderGeometry(4.6, 4.6, 0.4, 20);
          rim.rotateZ(Math.PI / 2);
          rim.rotateY(ryG + ns * Math.PI / 2);
          rim.translate(cx + ux * s * 8.3, base + 116, cz + uz * s * 8.3);
          lmTrim.push({ geom: rim, color: new THREE.Color(0x474c50), style: 3 });
          const disc = new THREE.CylinderGeometry(3.95, 3.95, 0.6, 20);
          disc.rotateZ(Math.PI / 2);
          disc.rotateY(ryG + ns * Math.PI / 2);
          disc.translate(cx + ux * s * 8.45, base + 116, cz + uz * s * 8.45);
          lmTrim.push({ geom: disc, color: new THREE.Color(0xe9dca6), style: 3 });
        }
        // ogee dome as stacked frustums, then the lantern
        for (const [w0, w1, y0, y1] of [[16.5, 12.5, 124, 133], [12.5, 7.5, 133, 143], [7.5, 3.6, 143, 151.5]]) {
          const f = new THREE.CylinderGeometry(w1 * 0.707, w0 * 0.707, y1 - y0, 4, 1);
          f.rotateY(Math.PI / 4 + ryG);
          f.translate(cx, base + (y0 + y1) / 2, cz);
          lmTrim.push({ geom: f, color: cDome, style: 3 });
        }
        const lant = new THREE.CylinderGeometry(2.0, 2.6, 4.3, 8); lant.translate(cx, base + 151.5 + 2.15, cz);
        lmTrim.push({ geom: lant, color: cWhiteM, style: 3 });
        // William Penn — 37 ft figure sculpted from primitives: stockinged calves under
        // a knee-length coat flaring at the hem, broad shoulders, brimmed hat, left arm
        // extended northeast (toward Penn Treaty Park). Reads as the statue, not a post.
        const y0 = base + 155.8;
        const pennAt = (g, dx2, y, dz2) => { g.translate(cx + dx2, y, cz + dz2); lmTrim.push({ geom: g, color: cPenn, style: 3 }); };
        const s2 = Math.SQRT1_2;
        const nex = (fl.nx - fl.dx) * s2, nez = (fl.nz - fl.dz) * s2;   // northeast, unit
        const pex = -nez, pez = nex;                                     // perpendicular (NW)
        pennAt(new THREE.CylinderGeometry(1.35, 1.55, 0.5, 10), 0, y0 + 0.25, 0);            // base plinth
        for (const sgn of [-1, 1])                                                            // calves
          pennAt(new THREE.CylinderGeometry(0.30, 0.36, 1.7, 6), pex * sgn * 0.44, y0 + 0.85, pez * sgn * 0.44);
        pennAt(new THREE.CylinderGeometry(1.02, 1.58, 5.0, 10), 0, y0 + 3.9, 0);             // coat, flared hem
        pennAt(new THREE.CylinderGeometry(1.24, 1.02, 2.9, 10), 0, y0 + 7.85, 0);            // torso to shoulders
        pennAt(new THREE.CylinderGeometry(0.46, 0.52, 0.7, 6), 0, y0 + 9.45, 0);             // neck + cravat
        pennAt(new THREE.SphereGeometry(0.66, 8, 6), 0, y0 + 10.15, 0);                      // head (long hair)
        pennAt(new THREE.CylinderGeometry(1.12, 1.12, 0.16, 10), 0, y0 + 10.62, 0);          // hat brim
        pennAt(new THREE.CylinderGeometry(0.72, 0.64, 0.62, 8), 0, y0 + 10.95, 0);           // hat crown
        {                                                                                     // left arm, extended NE
          const arm = new THREE.CylinderGeometry(0.24, 0.30, 2.5, 6);
          arm.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new V3(0, 1, 0), new V3(nex, -0.34, nez).normalize()));
          pennAt(arm, nex * 1.55, y0 + 8.35, nez * 1.55);
          pennAt(new THREE.SphereGeometry(0.30, 6, 5), nex * 2.75, y0 + 7.9, nez * 2.75);     // hand
        }
        {                                                                                     // right arm, down along the coat with the charter
          const arm = new THREE.CylinderGeometry(0.24, 0.28, 2.4, 6);
          arm.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new V3(0, 1, 0), new V3(-nex * 0.30, 1, -nez * 0.30).normalize()));
          pennAt(arm, -nex * 1.25, y0 + 7.5, -nez * 1.25);
          pennAt(new THREE.BoxGeometry(0.85, 1.05, 0.5), -nex * 1.55, y0 + 6.1, -nez * 1.55); // charter scroll
        }
      }
      // --- Philadelphia Museum of Art: golden Kasota-stone U on Fairmount hill,
      // blue tile gable roofs, central temple portico, wing pediments, court
      // fountain, and the Rocky steps cascading toward Eakins Oval. The OSM
      // footprint (a flat 10 m extrusion) is skipped via BRIDGE_SKIP above.
      {
        const O = [-3112, -2242];                          // center of the central block
        const fu = [0.717, 0.697];                         // unit axis toward the steps (SE, down the Parkway)
        const pv = [-0.697, 0.717];                        // across-axis unit (same handedness as the grid frame)
        const pt = (u, v) => [O[0] + fu[0] * u + pv[0] * v, O[1] + fu[1] * u + pv[1] * v];
        const quad = (u0, u1, v0, v1) => [pt(u0, v0), pt(u1, v0), pt(u1, v1), pt(u0, v1)];
        let T = -1e9;
        for (const q of [pt(-70, -95), pt(-70, 95), pt(55, 95), pt(55, -95), pt(0, 0)]) T = Math.max(T, siteY(q[0], q[1], 'ground'));
        T += 1.0;                                          // terrace deck level
        const chk = getChunk(O[0], O[1]);
        const cGold = new THREE.Color(0x8a744c);           // Kasota limestone (legacy pipeline lifts ~2.2x)
        const cGoldL = new THREE.Color(0x97814f);          // columns, a shade lighter
        const cStone = new THREE.Color(0x6f6455);          // terrace + steps
        const cCourt = new THREE.Color(0x7d7264);          // forecourt paving
        const cRoofM = new THREE.Color(0x2e3d47);          // blue-gray tile
        const cRed = new THREE.Color(0x5e2f26);            // tympanum brick-red
        const roof = (cu, cv, w, len, eave, apex, alongU, col) => {
          // gable prism in the museum's own frame (gPrism is grid-locked)
          const hl = len / 2, hw = w / 2;
          const t = [
            -hl, eave, -hw, hl, apex, 0, hl, eave, -hw, -hl, eave, -hw, -hl, apex, 0, hl, apex, 0,
            hl, eave, hw, -hl, apex, 0, -hl, eave, hw, hl, eave, hw, hl, apex, 0, -hl, apex, 0,
            hl, eave, -hw, hl, apex, 0, hl, eave, hw,
            -hl, eave, hw, -hl, apex, 0, -hl, eave, -hw,
          ];
          const pos = [];
          for (let i2 = 0; i2 < t.length; i2 += 3) {
            const lu = t[i2], lv = t[i2 + 2];
            const w2 = alongU ? pt(cu + lu, cv + lv) : pt(cu - lv, cv + lu); // rotate, never mirror
            pos.push(w2[0], t[i2 + 1], w2[1]);
          }
          const g = new THREE.BufferGeometry();
          g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
          g.computeVertexNormals();
          lmTrim.push({ geom: g, color: col || cRoofM, style: 3 });
        };
        const colAt = (u, v, r2, y0c, y1c) => {
          const g = new THREE.CylinderGeometry(r2, r2 * 1.06, y1c - y0c, 8);
          const w2 = pt(u, v);
          g.translate(w2[0], (y0c + y1c) / 2, w2[1]);
          lmTrim.push({ geom: g, color: cGoldL, style: 3 });
        };
        // terrace plinth (skirted well below the hilltop) and forecourt paving
        c.copy(cStone);
        appendBuilding(chk, quad(-70, 55, -95, 95), T - 9, T, c, 3, T - 9);
        c.copy(cCourt);
        appendBuilding(chk, quad(-15, 55, -45, 45), T, T + 0.12, c, 3, T);
        // main masses: central temple block, rear range, forward wings — style-1
        // walls give them the tall arched fenestration
        c.copy(cGold);
        appendBuilding(chk, quad(-40, 15, -40, 40), T - 1, T + 25, c, 1, T);
        appendBuilding(chk, quad(-70, -40, -95, 95), T - 1, T + 19, c, 1, T);
        appendBuilding(chk, quad(-40, 58, 48, 95), T - 1, T + 19, c, 1, T);
        appendBuilding(chk, quad(-40, 58, -95, -48), T - 1, T + 19, c, 1, T);
        roof(-12.5, 0, 80, 55, T + 25, T + 34, true);      // central ridge, pediment ends fore/aft
        roof(-55, 0, 30, 190, T + 19, T + 25, false);      // rear range, gable ends face NE/SW
        roof(9, 71.5, 47, 98, T + 19, T + 26, true);       // wings — pediment ends face the steps
        roof(9, -71.5, 47, 98, T + 19, T + 26, true);
        // central portico: stepped podium, 8 columns, entablature, pediment + red tympanum
        c.copy(cStone);
        appendBuilding(chk, quad(15, 29, -17, 17), T, T + 3.5, c, 3, T);
        appendBuilding(chk, quad(15, 25, -16, 16), T + 3.5, T + 7, c, 3, T);
        for (let i2 = 0; i2 < 8; i2++) colAt(19.5, -14 + 4 * i2, 0.95, T + 7, T + 19.5);
        c.copy(cGold);
        appendBuilding(chk, quad(12, 24, -17, 17), T + 19.5, T + 21.5, c, 3, T);
        // golden pediment shell with the brick-red tympanum nested inside: the red
        // prism is narrower and lower so only its end triangles poke past the shell
        roof(18, 0, 34, 12, T + 21.5, T + 27.5, true, cGold);
        roof(18, 0, 29, 12.6, T + 22.0, T + 26.6, true, cRed);
        // wing-end porticos facing the forecourt steps
        for (const sv of [-1, 1]) {
          c.copy(cStone);
          appendBuilding(chk, quad(54, 64, sv * 71.5 - 19, sv * 71.5 + 19), T, T + 6.5, c, 3, T);
          for (let i2 = 0; i2 < 6; i2++) colAt(59, sv * 71.5 - 16 + 6.4 * i2, 0.8, T + 6.5, T + 17.5);
          c.copy(cGold);
          appendBuilding(chk, quad(56, 61, sv * 71.5 - 18, sv * 71.5 + 18), T + 17.5, T + 19, c, 3, T);
        }
        // court fountain: octagonal stone ring + water
        {
          const w2 = pt(38, 0);
          const ring = new THREE.CylinderGeometry(10.5, 10.8, 0.9, 8);
          ring.translate(w2[0], T + 0.45, w2[1]);
          lmTrim.push({ geom: ring, color: new THREE.Color(0x8d8272), style: 3 });
          const water = new THREE.CylinderGeometry(8.8, 8.8, 0.5, 16);
          water.translate(w2[0], T + 0.55, w2[1]);
          lmTrim.push({ geom: water, color: new THREE.Color(0x2e6f8a), style: 3 });
        }
        // the Rocky steps: eight broad flights descending the hill toward the
        // Oval. Terrain-safe: the DEM hill bulges above the straight descent
        // line, so each flight tops out just above the ground beneath it and the
        // run never rises downhill — the hillside used to poke through between
        // flights and read as bare white stripes.
        {
          const bot = pt(105, 0);
          const yBot = siteY(bot[0], bot[1], 'ground') + 0.6;
          c.copy(cStone);
          const yT = [];
          for (let i2 = 0; i2 < 8; i2++) {
            let y = T + 0.5 + (yBot - (T + 0.5)) * (i2 + 1) / 8;
            for (const uv of [[6.3 * i2, -34], [6.3 * i2, 34], [6.3 * (i2 + 1), -34], [6.3 * (i2 + 1), 34], [6.3 * (i2 + 0.5), 0]]) {
              const q = pt(55 + uv[0], uv[1]);
              y = Math.max(y, siteY(q[0], q[1], 'ground') + 0.22);
            }
            yT.push(y);
          }
          for (let i2 = 6; i2 >= 0; i2--) yT[i2] = Math.max(yT[i2], yT[i2 + 1] + 0.2);
          for (let i2 = 0; i2 < 8; i2++) {
            appendBuilding(chk, quad(55 + 6.3 * i2, 55 + 6.3 * (i2 + 1) + 0.4, -34, 34), yT[i2] - 7, yT[i2], c, 3, yT[i2] - 7);
          }
        }
        // (the Fairmount greening itself lives in the wide-heightfield builder —
        // the ground cells there are vertex-tinted to park green; a draped lawn
        // here rode above the road ribbons on the bumpy hill and was removed)
      }
      // --- Battleship New Jersey (BB-62), moored on the Camden shore: the OSM
      // hull outline is extruded as the real haze-gray hull, then superstructure,
      // three triple 16-inch turrets, funnels, and masts go on in the hull frame
      if (njPoly) {
        const ob = orientedBox(njPoly);
        const a = obbAxis(ob);
        const W0 = TERRAIN.water;
        let wP = 0, nP = 0, wM = 0, nM = 0;
        for (const q of njPoly) {
          const du = (q[0] - ob.cx) * a.ax + (q[1] - ob.cz) * a.az;
          const dv = (q[0] - ob.cx) * a.px + (q[1] - ob.cz) * a.pz;
          if (du > a.hl * 0.7) { wP += Math.abs(dv); nP++; }
          if (du < -a.hl * 0.7) { wM += Math.abs(dv); nM++; }
        }
        const bow = (wP / Math.max(1, nP)) < (wM / Math.max(1, nM)) ? 1 : -1; // pointier end
        const hx = a.ax * bow, hz = a.az * bow;            // unit vector toward the bow
        const ryS = Math.atan2(-hz, hx);
        const SC = a.hl / 135;                             // hull frame vs the real 270 m
        const at2 = (u, v) => [ob.cx + hx * u * SC + a.px * v, ob.cz + hz * u * SC + a.pz * v];
        const chkN = getChunk(ob.cx, ob.cz);
        const cHull = new THREE.Color(0x383d42);
        c.copy(cHull);
        appendBuilding(chkN, njPoly, W0 - 1.5, W0 + 8.7, c, 3, W0);
        const gray = new THREE.Color(0x484d53), turret = new THREE.Color(0x43474c), barrelC = new THREE.Color(0x393d42);
        const shipBox = (u, v, y, len, h2, wid, col) => {
          const [x2, z2] = at2(u, v);
          lmTrim.push({ geom: box(len, h2, wid, x2, y, z2, ryS), color: col, style: 3 });
        };
        const shipCyl = (u, v, y0c, y1c, r0, r1, col, seg) => {
          const [x2, z2] = at2(u, v);
          const g = new THREE.CylinderGeometry(r0, r1, y1c - y0c, seg || 8);
          g.translate(x2, (y0c + y1c) / 2, z2);
          lmTrim.push({ geom: g, color: col, style: 3 });
        };
        const D0 = W0 + 8.7;                               // main deck
        shipBox(-4, 0, D0 + 2.2, 84, 4.4, 17, gray);       // 01 level
        shipBox(-3, 0, D0 + 6.0, 56, 3.4, 13.5, gray);     // 02 level
        shipBox(22, 0, D0 + 10.5, 10, 5.6, 9, gray);       // forward tower
        shipBox(22, 0, D0 + 15.0, 6, 3.4, 6, gray);        // fire control
        shipCyl(22, 0, D0 + 16.7, D0 + 22.5, 1.5, 1.8, gray);
        shipCyl(16, 0, D0 + 18, D0 + 34, 0.55, 0.8, new THREE.Color(0x33373c), 6);  // main mast
        for (const [fu] of [[2], [-16]]) {                 // funnels with black caps
          shipCyl(fu, 0, D0 + 7.5, D0 + 14.5, 2.5, 3.2, gray);
          shipCyl(fu, 0, D0 + 14.5, D0 + 16.0, 2.6, 2.6, new THREE.Color(0x16181a));
        }
        shipBox(-30, 0, D0 + 8.6, 8, 5.2, 7.5, gray);      // aft tower
        shipCyl(-30, 0, D0 + 11.2, D0 + 24, 0.5, 0.7, new THREE.Color(0x33373c), 6); // aft mast
        const turretAt = (u, y, dir) => {
          shipBox(u, 0, y + 1.7, 14, 3.4, 11, turret);
          for (const v of [-2.7, 0, 2.7]) {
            const g = new THREE.CylinderGeometry(0.42, 0.6, 16.5, 6);
            g.rotateZ(Math.PI / 2 - 0.09);                 // horizontal, tipped up slightly
            g.rotateY(ryS + (dir < 0 ? Math.PI : 0));
            const [x2, z2] = at2(u + dir * 14, v);
            g.translate(x2, y + 2.6, z2);
            lmTrim.push({ geom: g, color: barrelC, style: 3 });
          }
        };
        turretAt(62, D0, 1);                                // turret 1, main deck
        shipBox(43, 0, D0 + 1.6, 13, 3.2, 11.5, gray);      // turret 2 barbette
        turretAt(43, D0 + 3.2, 1);                          // turret 2, superfiring
        turretAt(-58, D0, -1);                              // turret 3, facing aft
      }
    }
    // parks, water, piers (water splits out onto the animated river material)
    const areaParts = [], waterAreaParts = [];
    for (let i = 0; i < hdr[3]; i++) {
      const n = body[k++], kind = body[k++];
      const poly = new Array(n);
      for (let j = 0; j < n; j++) poly[j] = [body[k++] * S, body[k++] * S];
      const [acx, acz] = polyCentroid(poly);
      // the stadium/arena builders own their interiors — OSM's pitch/park drapes
      // in there just z-fight the bowls
      if (kind === 0 && (Math.hypot(acx + 1869, acz - 4375) < 140 || Math.hypot(acx + 1920, acz - 4932) < 150 || Math.hypot(acx + 2327, acz - 4880) < 120)) continue;
      // the Art Museum build owns its hilltop: OSM's paved/park drapes there lie
      // per-vertex on the steep hill and rendered as sheared slabs over the steps
      if (kind !== 1 && Math.hypot(acx + 3080, acz + 2210) < 190) continue;
      // and its Fairmount lawn owns the wider grounds: the white paved-area flats
      // (parking aprons, plazas) blanketed the hill at +1.2 over the grass —
      // any-vertex test, since a big apron's centroid can sit outside the zone
      if (kind > 1 && poly.some((q) => q[0] > -3850 && q[0] < -2480 && q[1] > -2950 && q[1] < -1720)) continue;
      // the Walt Whitman's OSM outline maps as a paved area — it rendered as a
      // flat gray slab floating on the river under the real suspension deck
      if (kind !== 1 && wwbNear(acx, acz)) continue;
      try {
        if (kind === 0) areaParts.push({ geom: Math.abs(signedArea(poly)) > 1500 ? drapedPoly(poly, LAYER.park, 20) : flatPoly(poly, null, LAYER.park), color: new THREE.Color(COLORS.park).multiplyScalar(0.84 + hash01(i) * 0.16), style: 3 });
        else if (kind === 1) waterAreaParts.push({ geom: flatPoly(poly, null, TERRAIN.water + 0.55, true), color: new THREE.Color(COLORS.water), style: 3 });
        else areaParts.push({ geom: flatPoly(poly, null, 1.2), color: new THREE.Color(COLORS.pier), style: 3 });
      } catch (e) { /* degenerate polygon */ }
    }
    loadmsg.textContent = 'Raising the outer districts, uploading';
    await yieldNow();
    for (const ch of glassChunks.values()) {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(ch.pos), 3));
      g.setAttribute('normal', new THREE.BufferAttribute(new Int8Array(ch.nor), 3, true));
      g.setAttribute('color', new THREE.BufferAttribute(new Uint8Array(ch.col), 3, true));
      g.setIndex(ch.idx);
      g.computeBoundingSphere();
      if (!outerGlassMat) {
        outerGlassMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.06, metalness: 0.88, envMapIntensity: 1.8 });
        outerGlassMat.emissive = new THREE.Color(0xffdca6);
        outerGlassMat.emissiveIntensity = 0;
        // curtain-wall rhythm: darker spandrel band at each floor line, thin vertical
        // mullions between panels — world-space, anti-aliased, fading with distance
        outerGlassMat.onBeforeCompile = (sh) => {
          sh.vertexShader = sh.vertexShader
            .replace('#include <common>', '#include <common>\nvarying vec3 vGWp; varying vec3 vGNm;')
            .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvGWp = (modelMatrix * vec4(transformed, 1.0)).xyz;\nvGNm = normalize(mat3(modelMatrix) * objectNormal);');
          sh.fragmentShader = sh.fragmentShader
            .replace('#include <common>', '#include <common>\nvarying vec3 vGWp; varying vec3 vGNm;\nfloat gWall = 0.0; float gLit = 0.0; float gSpand = 0.0;')
            .replace('#include <color_fragment>', '#include <color_fragment>\n{\n' +
              '  vec3 nn = normalize(vGNm);\n' +
              '  float wall = step(abs(nn.y), 0.35);\n' +
              '  vec2 dirH = (abs(nn.x) + abs(nn.z)) > 1e-4 ? normalize(nn.xz) : vec2(1.0, 0.0);\n' +
              '  float u = dot(vGWp.xz, vec2(-dirH.y, dirH.x));\n' +
              '  float aaU = fwidth(u) + 1e-4, aaV = fwidth(vGWp.y) + 1e-4;\n' +
              '  float det = clamp(1.0 - (max(aaU, aaV) - 0.30) / 0.85, 0.0, 1.0) * wall;\n' +
              '  float dv = abs(fract(vGWp.y / 4.0 + 0.5) - 0.5) * 4.0;\n' +
              '  float spand = 1.0 - smoothstep(0.5, 0.5 + aaV, dv);\n' +
              '  float du = abs(fract(u / 1.5 + 0.5) - 0.5) * 1.5;\n' +
              '  float mull = 1.0 - smoothstep(0.05, 0.05 + aaU, du);\n' +
              '  diffuseColor.rgb *= 1.0 - det * (spand * 0.22 + mull * 0.16);\n' +
              '  vec2 pid = vec2(floor(u / 1.5), floor(vGWp.y / 4.0));\n' +
              '  float ph = fract(sin(dot(pid, vec2(127.1, 311.7))) * 43758.5453);\n' +
              // ~28% of curtain-wall panels glow at night, varied; past the per-panel
              // fade the tower keeps only its soft average (the panel-cluster LOD
              // read as big square lights from distance, removed at the owner's request)
              '  gWall = wall;\n' +
              '  gSpand = spand;\n' +
              '  gLit = mix(0.10, step(0.72, ph) * (0.4 + 0.6 * fract(ph * 7.3)), det);\n' +
              '}')
            .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance *= gWall * gLit * (1.0 - gSpand * 0.85) * 3.2;');
        };
      }
      const m = new THREE.Mesh(g, outerGlassMat);
      m.matrixAutoUpdate = false;
      groupCity.add(m);
      outerMeshes.push(m);
    }
    if (lmGlass.length && outerGlassMat) {   // Liberty Place crowns share the curtain-wall glass
      const m = new THREE.Mesh(mergeColored(lmGlass), outerGlassMat);
      m.castShadow = true;
      groupCity.add(m);
      outerMeshes.push(m);
    }
    if (lmTrim.length) {                     // white chevron trim, masts, City Hall metalwork + Penn
      const m = new THREE.Mesh(mergeColored(lmTrim), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.5, metalness: 0.3 }));
      m.castShadow = true;
      groupCity.add(m);
      outerMeshes.push(m);
    }
    for (const ch of chunks.values()) {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(ch.pos), 3));
      g.setAttribute('normal', new THREE.BufferAttribute(new Int8Array(ch.nor), 3, true));
      g.setAttribute('color', new THREE.BufferAttribute(new Uint8Array(ch.col), 3, true));
      g.setAttribute('aStyle', new THREE.BufferAttribute(new Int8Array(ch.sty), 1));
      g.setAttribute('aFloorH', new THREE.BufferAttribute(new Int8Array(ch.flh.map(fv => Math.round(fv * 10))), 1));
      g.setAttribute('aBase', new THREE.BufferAttribute(new Float32Array(ch.bas), 1));
      g.setIndex(ch.idx);
      g.computeBoundingSphere();
      freeOnUpload(g);
      ch.pos = ch.nor = ch.col = ch.sty = ch.flh = ch.bas = ch.idx = null;
      const m = new THREE.Mesh(g, cityMat);
      m.matrixAutoUpdate = false;
      groupCity.add(m);
      outerMeshes.push(m);
    }
    renderer.render(scene, camera);   // upload now, behind the veil, and free the arrays
    await yieldNow();
    if (rc.n) {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(rc.pos), 3));
      g.setAttribute('color', new THREE.BufferAttribute(new Uint8Array(rc.col), 3, true));
      g.setIndex(rc.idx);
      g.computeVertexNormals();
      g.computeBoundingSphere();
      freeOnUpload(g);
      rc.pos = rc.col = rc.idx = null;
      groupCity.add(new THREE.Mesh(g, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, side: THREE.DoubleSide })));
    }
    if (areaParts.length) groupCity.add(new THREE.Mesh(mergeColored(areaParts), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95 })));
    if (waterAreaParts.length) groupCity.add(new THREE.Mesh(mergeColored(waterAreaParts), riverMat));
    // widen the world: camera clamps and fog
    bounds.minX = -3700; bounds.maxX = 2300; bounds.minZ = -4480; bounds.maxZ = 6400;
    scene.fog.near = 1900; scene.fog.far = 7600;

    // Benjamin Franklin Bridge (1926): suspension span from the 5th St anchorage to Camden
    {
      const A = [400, -940], B = [1360, -722];           // anchorages (Philadelphia -> Camden), per OSM way 575987106
      const dx = B[0] - A[0], dz = B[1] - A[1], L = Math.hypot(dx, dz);
      const ux = dx / L, uz = dz / L, ry = Math.atan2(-uz, ux);
      const yA = siteY(A[0], A[1], 'ground') + 12, yMid = TERRAIN.water + 41;
      const pry = Math.atan2(-ux, -uz);                  // frame whose local x runs across the deck
      const parts = [];
      const addP = (geom, hex) => parts.push({ geom, color: new THREE.Color(hex), style: 3 });
      const STEEL = '#8fb4c6', CABLE = '#7c9bac', STONE = '#b0a99e';
      const deckY = (t) => yA + (yMid - yA) * Math.sin(Math.PI * t) * 0.85 + (yMid - yA) * 0.15 * (1 - Math.abs(2 * t - 1));
      const segs = 40;
      for (let i = 0; i < segs; i++) {
        const t0 = i / segs, t1 = (i + 1) / segs;
        const x0 = A[0] + dx * t0, z0 = A[1] + dz * t0, x1 = A[0] + dx * t1, z1 = A[1] + dz * t1;
        const y0 = deckY(t0), y1 = deckY(t1);
        const len = L / segs;
        const slope = Math.atan2(y1 - y0, len);
        const seg = (g) => { g.rotateZ(slope); g.rotateY(ry); g.translate((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2); addP(g, STEEL); };
        seg(box(len + 0.5, 1.5, 39, 0, 0, 0, 0));                       // roadway (PATCO tracks + walkways outboard)
        for (const s of [-1, 1]) {
          seg(box(len + 0.5, 0.9, 0.9, 0, -8, s * 18.5, 0));            // stiffening-truss bottom chords
          const dl = Math.hypot(len, 7);
          const dg = box(dl, 0.7, 0.7, 0, 0, 0, 0);
          dg.rotateZ((i & 1 ? -1 : 1) * Math.atan2(7, len));            // truss diagonals, alternating
          dg.translate(0, -4.4, s * 18.5);
          seg(dg);
          seg(box(0.7, 8, 0.7, len / 2, -4.4, s * 18.5, 0));            // truss verticals
        }
      }
      // steel lattice towers: paired legs on masonry piers, X-braced above the roadway
      const topY = TERRAIN.water + 117;
      const tw = [0.23, 0.78];
      for (const t of tw) {
        const x = A[0] + dx * t, z = A[1] + dz * t;
        const dY = deckY(t);
        addP(box(46, 14, 20, x, TERRAIN.water + 3, z, pry), '#b78771'); // warm granite pier at the waterline
        for (const s of [-1, 1]) {
          addP(box(6.5, topY - TERRAIN.water - 8, 8, x - uz * s * 15.5, (TERRAIN.water + 8 + topY) / 2, z + ux * s * 15.5, pry), STEEL);
        }
        // portal struts: above the roadway, mid-height, and the cap
        const sy = [dY + 7, (dY + 7 + topY - 4) / 2, topY - 4];
        for (const yv of sy) addP(box(34, 4, 5.5, x, yv, z, pry), STEEL);
        addP(box(37, 5, 8, x, topY - 0.5, z, pry), STEEL);              // cap beam carrying the saddles
        // two X-brace panels between the struts, one more below deck to the pier
        const xPanel = (y0, y1, w2) => {
          const h = y1 - y0, dl = Math.hypot(31, h), an = Math.atan2(h, 31);
          for (const sg of [-1, 1]) {
            const g = box(dl, 1.2, 1.2, 0, 0, 0, 0);
            g.rotateZ(sg * an); g.rotateY(pry);
            g.translate(x, (y0 + y1) / 2, z);
            addP(g, STEEL);
          }
        };
        xPanel(sy[0] + 2, sy[1] - 2);
        xPanel(sy[1] + 2, sy[2] - 2);
        xPanel(TERRAIN.water + 11, dY - 3);
      }
      // granite anchorages: 50 m masonry towers the roadway threads through (DRPA: 61 x 50 m)
      for (const [ex, ez] of [A, B]) {
        const g0 = siteY(ex, ez, 'ground');
        addP(box(61, 36 - (g0 - 2), 46, ex, (g0 - 2 + 36) / 2, ez, ry), STONE);
        addP(box(42, 16, 42, ex, 42, ez, ry), '#a89f93');
        addP(box(30, 5, 38, ex, 52.5, ez, ry), '#998f82');
      }
      const cableY = (t) => { // catenary-ish: tower tops at t=0.30/0.70, sag to deck+6 at mid and ends
        if (t < 0.23) return deckY(0) + 8 + (topY - deckY(0) - 8) * Math.pow(t / 0.23, 2);
        if (t > 0.78) return deckY(1) + 8 + (topY - deckY(1) - 8) * Math.pow((1 - t) / 0.22, 2);
        const u = (t - 0.505) / 0.275; return yMid + 6 + (topY - yMid - 6) * u * u;
      };
      for (let i = 0; i < 80; i++) {
        const t0 = i / 80, t1 = (i + 1) / 80;
        for (const s of [-1, 1]) {
          const x0 = A[0] + dx * t0 - uz * s * 15.5, z0 = A[1] + dz * t0 + ux * s * 15.5, x1 = A[0] + dx * t1 - uz * s * 15.5, z1 = A[1] + dz * t1 + ux * s * 15.5;
          const y0 = cableY(t0), y1 = cableY(t1);
          const seg = Math.hypot(L / 80, y1 - y0);
          const g = box(seg + 0.3, 0.9, 0.9, 0, 0, 0, 0);
          g.rotateZ(Math.atan2(y1 - y0, L / 80));
          g.rotateY(ry);
          g.translate((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
          addP(g, CABLE);
          if (t0 > 0.05 && t0 < 0.95) addP(box(0.3, Math.max(0.5, y0 - deckY(t0)), 0.3, x0, (y0 + deckY(t0)) / 2, z0, 0), CABLE);
        }
      }
      const m = new THREE.Mesh(mergeColored(parts), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.6, metalness: 0.3 }));
      m.castShadow = true;
      groupCity.add(m);
    }
    // Walt Whitman Bridge (1957): suspension span on OSM's alignment, Packer Ave approach to Gloucester City
    if (typeof WWB_PTS !== 'undefined' && WWB_PTS && WWB_PTS.length > 3) {
      const line = densify(WWB_PTS, 20);
      const cum = [0];
      for (let i = 1; i < line.length; i++) cum.push(cum[i - 1] + Math.hypot(line[i][0] - line[i - 1][0], line[i][1] - line[i - 1][1]));
      // mid-span at (1318.6, 4454.4); towers 609.6 m apart, side spans 234.7 m (DRPA)
      let mi = 0, best = Infinity;
      for (let i = 0; i < line.length; i++) { const dd = Math.hypot(line[i][0] - 1318.6, line[i][1] - 4454.4); if (dd < best) { best = dd; mi = i; } }
      // The crossing is dead straight on the real bridge, but OSM's motorway line
      // hops between carriageways mid-river (a 15 m right-angle jog at mid-span)
      // and wiggles at the NJ anchorage — the deck built along it came out
      // disjointed. Project the whole span onto its straight chord, then
      // re-measure arc lengths.
      {
        const ptAt = (sv) => {
          let i = 1; while (i < cum.length - 1 && cum[i] < sv) i++;
          const tt = clamp((sv - cum[i - 1]) / Math.max(1e-6, cum[i] - cum[i - 1]), 0, 1);
          return [line[i - 1][0] + (line[i][0] - line[i - 1][0]) * tt, line[i - 1][1] + (line[i][1] - line[i - 1][1]) * tt];
        };
        const sA = cum[mi] - 660, sB = cum[mi] + 660;
        const A = ptAt(sA), B = ptAt(sB);
        for (let i = 0; i < line.length; i++) {
          if (cum[i] > sA && cum[i] < sB) {
            const tt = (cum[i] - sA) / (sB - sA);
            line[i] = [A[0] + (B[0] - A[0]) * tt, A[1] + (B[1] - A[1]) * tt];
          }
        }
        for (let i = 1; i < line.length; i++) cum[i] = cum[i - 1] + Math.hypot(line[i][0] - line[i - 1][0], line[i][1] - line[i - 1][1]);
        best = Infinity;
        for (let i = 0; i < line.length; i++) { const dd = Math.hypot(line[i][0] - 1318.6, line[i][1] - 4454.4); if (dd < best) { best = dd; mi = i; } }
      }
      {
        const mid = cum[mi], half = 304.8, side = 234.7;
        const W0 = TERRAIN.water;
        const deckAt = (i) => {
          const dd = Math.abs(cum[i] - mid);
          let y;
          if (dd <= half) y = W0 + 49 - 6 * (dd / half) * (dd / half);
          else if (dd <= half + side) y = W0 + 43 - 6 * (dd - half) / side;
          else y = W0 + 37 - 0.02 * (dd - half - side);
          return Math.max(y, siteY(line[i][0], line[i][1], 'ground') + 6);
        };
        const parts = [];
        const addP = (geom, hex) => parts.push({ geom, color: new THREE.Color(hex), style: 3 });
        for (let i = 0; i < line.length - 1; i++) {
          const a = line[i], b = line[i + 1];
          const ya = deckAt(i), yb = deckAt(i + 1);
          const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
          const g = box(L + 0.4, 8, 28, 0, 0, 0, 0); // roadway on its 8 m stiffening truss
          g.rotateZ(Math.atan2(yb - ya, L));
          g.rotateY(Math.atan2(-(b[1] - a[1]), b[0] - a[0]));
          g.translate((a[0] + b[0]) / 2, (ya + yb) / 2 - 4, (a[1] + b[1]) / 2);
          addP(g, '#75a889');
        }
        const at = (sv) => { // point + direction along the line at arc length sv
          let i = 1; while (i < cum.length - 1 && cum[i] < sv) i++;
          const tt = (sv - cum[i - 1]) / Math.max(1e-6, cum[i] - cum[i - 1]);
          const a = line[i - 1], b = line[i];
          const ux = (b[0] - a[0]) / Math.max(1e-6, cum[i] - cum[i - 1]), uz = (b[1] - a[1]) / Math.max(1e-6, cum[i] - cum[i - 1]);
          return { x: a[0] + (b[0] - a[0]) * tt, z: a[1] + (b[1] - a[1]) * tt, ux, uz, ry: Math.atan2(-uz, ux) };
        };
        const topY = W0 + 115.2;
        const idxAt = (sv) => { let i = 1; while (i < cum.length - 1 && cum[i] < sv) i++; return i; };
        for (const ts of [mid - half, mid + half]) {
          const q = at(ts);
          addP(box(53, 4, 19.5, q.x, W0 - 0.5, q.z, q.ry), '#a8a59e'); // concrete tower pier at the waterline
          for (const sg of [-1, 1]) addP(box(6, 117, 4.5, q.x - q.uz * sg * 14, W0 - 2 + 58.5, q.z + q.ux * sg * 14, q.ry), '#75a889');
          addP(box(5, 9, 32, q.x, W0 + 109, q.z, q.ry), '#75a889'); // deep top portal below the saddles
          addP(box(4, 6, 32, q.x, W0 + 36, q.z, q.ry), '#75a889');  // portal strut below the deck — legs are clean between

        }
        for (const ts of [mid - half - side - 30, mid + half + side + 30]) { // concrete anchorage blocks
          const q = at(ts);
          addP(box(61, 39.6, 36.6, q.x, deckAt(idxAt(ts)) - 30 + 19.8, q.z, q.ry), '#a8a59e');
        }
        const cableY = (sv) => {
          const dd = Math.abs(sv - mid);
          if (dd <= half) { const u = dd / half; return W0 + 48 + (topY - W0 - 48) * u * u; }
          const e = Math.min(1, (dd - half) / side);
          return topY - (topY - (W0 + 40)) * (1 - (1 - e) * (1 - e));
        };
        const c0 = mid - half - side, c1 = mid + half + side;
        for (let sv = c0; sv < c1; sv += 15) {
          for (const sg of [-1, 1]) {
            const q0 = at(sv), q1 = at(Math.min(c1, sv + 15));
            const y0 = cableY(sv), y1 = cableY(Math.min(c1, sv + 15));
            const x0 = q0.x - q0.uz * sg * 15, z0 = q0.z + q0.ux * sg * 15, x1 = q1.x - q1.uz * sg * 15, z1 = q1.z + q1.ux * sg * 15;
            const seg = Math.hypot(Math.hypot(x1 - x0, z1 - z0), y1 - y0);
            const g = box(seg + 0.3, 0.8, 0.8, 0, 0, 0, 0);
            g.rotateZ(Math.atan2(y1 - y0, Math.hypot(x1 - x0, z1 - z0)));
            g.rotateY(Math.atan2(-(z1 - z0), x1 - x0));
            g.translate((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
            addP(g, '#6b9478');
            if (Math.round(sv / 15) % 2 === 0) {
              let i = 1; while (i < cum.length - 1 && cum[i] < sv) i++;
              const dy = deckAt(i);
              if (y0 - dy > 2) addP(box(0.3, y0 - dy, 0.3, x0, (y0 + dy) / 2, z0, 0), '#6b9478');
            }
          }
        }
        const m = new THREE.Mesh(mergeColored(parts), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.6, metalness: 0.3 }));
        m.castShadow = true;
        groupCity.add(m);
        const qm = at(mid);
        labels.push({ el: (() => { const el = document.createElement('div'); el.className = 'lbl'; el.textContent = 'Walt Whitman Bridge'; labelsRoot.appendChild(el); return el; })(), pos: new V3(qm.x, W0 + 125, qm.z), visible: false, far: true });
      }
    }
    for (const [nm, x, z, hh] of [['Lincoln Financial Field', -1920, 4932, 50], ['Citizens Bank Park', -1869, 4375, 58], ['Xfinity Mobile Arena (Wells Fargo Center)', -2327, 4880, 50]]) {
      const el = document.createElement('div'); el.className = 'lbl'; el.textContent = nm; labelsRoot.appendChild(el);
      labels.push({ el, pos: new V3(x, siteY(x, z, 'ground') + hh, z), visible: false, far: true });
    }
    // labels for the tallest named outer buildings
    if (typeof WIDE_NAMES !== 'undefined' && WIDE_NAMES) {
      for (const q of WIDE_NAMES.filter(w => w.h >= 140).slice(0, 16)) {
        const el = document.createElement('div');
        el.className = 'lbl';
        el.textContent = q.n;
        labelsRoot.appendChild(el);
        labels.push({ el, pos: new V3(q.x, siteY(q.x, q.z, 'ground') + q.h + 10, q.z), visible: false, far: true });
      }
    }
  });

  // ------------------------------------------------ the far ring: the rest of Philadelphia
  step('Raising the rest of Philadelphia', async () => {
    if (typeof CITY_B64 === 'undefined' || !CITY_B64) return;
    const bin = Uint8Array.from(atob(CITY_B64), ch => ch.charCodeAt(0));
    CITY_B64 = null;   // 7 MB of base64 freed
    const hdr = new Int32Array(bin.buffer, 0, 4);
    const hasAttr = hdr[0] === 0x5348545B;
    if (hdr[0] !== 0x53485459 && !hasAttr) return;
    const body = new Int16Array(bin.buffer, 16);
    let k = 0;
    const S = 0.7, CH = 2400;
    const W = { x0: -12000, x1: 16500, z0: -21700, z1: 9700 };
    const WIDEB = { x0: -3700, x1: 2300, z0: -4480, z1: 6400 };
    const chunks = new Map();
    const getChunk = (x, z) => {
      const key = Math.floor(x / CH) + ':' + Math.floor(z / CH);
      let ch = chunks.get(key);
      if (!ch) { ch = { pos: [], nor: [], col: [], sty: [], bas: [], flh: [], idx: [], n: 0 }; chunks.set(key, ch); }
      return ch;
    };
    const palLow = [0x9b5a43, 0x8f5140, 0xa56a4e, 0x7d4a3a, 0x94523d, 0xb8a894, 0xa79a86, 0x8d8a86, 0xc4b49b, 0x9a6b55];
    const palCom = [0x9d968a, 0x8f887b, 0xa8a191, 0x83817c, 0x9aa0a4, 0xb3aca0];
    const palInd = [0x8a7e72, 0x7b736b, 0x9c9286, 0x8e5a48];
    const palTall = [0xa39b8b, 0x8e979e, 0x6e7681, 0x50555e, 0x5c5348, 0x8a8478, 0x9c9284, 0x42474f, 0x76664f, 0x66707c];
    const c = new THREE.Color();
    const cCap = new THREE.Color();
    const v2 = [];
    const yieldNow = () => new Promise(r => { const ch = new MessageChannel(); ch.port1.onmessage = () => r(); ch.port2.postMessage(0); }); // not timer-clamped in hidden tabs
    const pushV = (ch, x, y, z, nx, ny, nz, r, g, b, st, base, fh) => {
      ch.pos.push(x, y, z); ch.nor.push(nx * 127, ny * 127, nz * 127); ch.col.push(r * 255, g * 255, b * 255); ch.sty.push(st); ch.bas.push(base); ch.flh.push(fh || 0);
      return ch.n++;
    };
    const appendB = (ch, poly, y0, y1, color, st, base, fh, capColor) => {
      const n = poly.length, r = color.r, g = color.g, b = color.b;
      const sign = signedArea(poly) > 0 ? 1 : -1;
      for (let i = 0; i < n; i++) {
        const a = poly[i], q = poly[(i + 1) % n];
        const dx = q[0] - a[0], dz = q[1] - a[1];
        const L = Math.hypot(dx, dz);
        if (L < 0.05) continue;
        const nx = (dz / L) * sign, nz = (-dx / L) * sign;
        const i0 = pushV(ch, a[0], y0, a[1], nx, 0, nz, r, g, b, st, base, fh);
        const i1 = pushV(ch, q[0], y0, q[1], nx, 0, nz, r, g, b, st, base, fh);
        const i2 = pushV(ch, q[0], y1, q[1], nx, 0, nz, r, g, b, st, base, fh);
        const i3 = pushV(ch, a[0], y1, a[1], nx, 0, nz, r, g, b, st, base, fh);
        if (((-dz) * nx + dx * nz) >= 0) ch.idx.push(i0, i1, i2, i0, i2, i3); else ch.idx.push(i0, i2, i1, i0, i3, i2);
      }
      v2.length = 0;
      for (let i = 0; i < n; i++) v2.push(new THREE.Vector2(poly[i][0], -poly[i][1]));
      let tris;
      try { tris = THREE.ShapeUtils.triangulateShape(v2, []); } catch (e) { return; }
      const capStart = ch.n;
      const cr = capColor ? capColor.r : r * 0.93, cg = capColor ? capColor.g : g * 0.93, cb = capColor ? capColor.b : b * 0.93;
      for (let i = 0; i < n; i++) pushV(ch, poly[i][0], y1, poly[i][1], 0, 1, 0, cr, cg, cb, 3, base);
      // earcut emits CCW triangles in the shape plane regardless of ring winding
      // (pack_city rings arrive in shapely's CW convention — flipping by ring
      // orientation culled every merged roof); always emit forward = up-facing
      for (const t of tris) ch.idx.push(capStart + t[0], capStart + t[1], capStart + t[2]);
    };
    // buildings (merged block strips + solo talls/churches)
    const nb = hdr[1];
    for (let i = 0; i < nb; i++) {
      const n = body[k++], h = body[k++] / 5, mh = body[k++] / 5, t = body[k++];
      const attrW = hasAttr ? body[k++] : -1, roofW = hasAttr ? body[k++] : -1;
      const poly = new Array(n);
      for (let j = 0; j < n; j++) { poly[j] = [body[k++] * S, body[k++] * S]; }
      const [cx, cz] = polyCentroid(poly);
      if (ovpStraddle(poly, cx, cz)) { if ((i & 4095) === 4095) { loadmsg.textContent = 'Raising the rest of Philadelphia, ' + Math.round(i / nb * 100) + '%'; await yieldNow(); } continue; }
      const base = siteY(cx, cz, 'ground');
      const hsh = hash01(i * 5.31 + 0.7);
      const fa = attrW >= 0 ? [attrW & 7, (attrW >> 3) & 7, (attrW >> 6) & 15, 0] : null;
      const fh = attrW >= 0 && ((attrW >> 10) & 31) > 0 ? 2.2 + (((attrW >> 10) & 31) - 1) * 0.1 : 0;
      let pool = h > 45 ? palTall : (t === 3 || t === 6 || h > 25) ? palCom : (t === 4 ? palInd : palLow);
      if (fa && h <= 45 && t <= 4) { const p2 = opaWallPool(fa); if (p2) pool = p2; }
      c.set(pool[Math.floor(hsh * pool.length) % pool.length]).multiplyScalar(h > 45 ? 0.94 + hash01(i * 13.7) * 0.12 : 0.9 + hash01(i * 13.7) * 0.2);
      let style = h > 30 ? 2 : (t === 3 ? 5 : 0);
      if (fa && h <= 30 && t <= 4) style = opaStyle(fa, h);
      const capC = roofW >= 0 && ROOF_PAL ? cCap.copy(ROOF_PAL[roofW]).multiplyScalar(0.9 + hsh * 0.18) : null;
      appendB(getChunk(cx, cz), poly, mh > 0 ? base + mh : base - 1.0, base + h, c, style, base, fh, capC);
      if (t === 5 && Math.abs(signedArea(poly)) > 350 && h < 60) {
        const chk = getChunk(cx, cz);
        const tw = 5.5, towerTop = base + h + 9, apex = base + h + 24;
        const sq = [[cx - tw / 2, cz - tw / 2], [cx + tw / 2, cz - tw / 2], [cx + tw / 2, cz + tw / 2], [cx - tw / 2, cz + tw / 2]];
        appendB(chk, sq, base, towerTop, c, 3, base);
        const i0 = chk.n;
        for (const q of sq) pushV(chk, q[0], towerTop, q[1], 0, 0.7, 0, c.r * 0.9, c.g * 0.9, c.b * 0.9, 3, base);
        pushV(chk, cx, apex, cz, 0, 1, 0, c.r * 0.9, c.g * 0.9, c.b * 0.9, 3, base);
        chk.idx.push(i0, i0 + 1, i0 + 4, i0 + 1, i0 + 2, i0 + 4, i0 + 2, i0 + 3, i0 + 4, i0 + 3, i0, i0 + 4);
      }
      if ((i & 4095) === 4095) { loadmsg.textContent = 'Raising the rest of Philadelphia, ' + Math.round(i / nb * 100) + '%'; await yieldNow(); }
    }
    // far roads — same continuity treatment as the wide set: endpoint-snapped heights,
    // bend fans, bridge decks over the river corridors
    const rc = { pos: [], col: [], idx: [], n: 0 };
    const roadCol = [0x3b3833, 0x3b3833, 0x3f3c37, 0x3f3c37, 0x43403b, 0x45423d, 0x7c584a];
    const inWide = (p) => p[0] > WIDEB.x0 - 30 && p[0] < WIDEB.x1 + 30 && p[1] > WIDEB.z0 - 30 && p[1] < WIDEB.z1 + 30;
    const yMapF = new Map();
    const ySnapF = (x, z, y) => {
      const key = Math.round(x * 2) + ':' + Math.round(z * 2);
      const v = yMapF.get(key);
      if (v !== undefined) return v;
      yMapF.set(key, y);
      return y;
    };
    const rcFanF = (x, y, z, hw, cr, cg, cb) => {
      const c0 = rc.n;
      rc.pos.push(x, y, z); rc.col.push(cr, cg, cb); rc.n++;
      for (let s6 = 0; s6 < 7; s6++) {
        const ang = s6 / 6 * Math.PI * 2;
        rc.pos.push(x + Math.cos(ang) * hw, y, z + Math.sin(ang) * hw);
        rc.col.push(cr, cg, cb); rc.n++;
      }
      for (let s6 = 0; s6 < 6; s6++) rc.idx.push(c0, c0 + 1 + s6, c0 + 2 + s6);
    };
    for (let i = 0; i < hdr[2]; i++) {
      const n = body[k++], w = body[k++] / 10, t = body[k++];
      let pts = new Array(n);
      for (let j = 0; j < n; j++) pts[j] = [body[k++] * S, body[k++] * S];
      if (t <= 5) for (let j = 0; j + 1 < pts.length; j++) septaRoadAdd(pts[j][0], pts[j][1], pts[j + 1][0], pts[j + 1][1]);
      pts = densify(pts, 30);
      c.set(roadCol[t] || 0x3b3833);
      const hw = w / 2;
      const thr = TERRAIN.water + 0.6;
      for (let j = 0; j < pts.length - 1; j++) {
        const a = pts[j], q = pts[j + 1];
        let dx = q[0] - a[0], dz = q[1] - a[1];
        const L = Math.hypot(dx, dz); if (L < 0.01) continue;
        dx /= L; dz /= L;
        const mx = (a[0] + q[0]) / 2, mz = (a[1] + q[1]) / 2;
        const aLow = demY(a[0], a[1]) < thr, qLow = demY(q[0], q[1]) < thr;
        let deck = 0;
        if ((aLow || qLow) && riverCorridor(mx, mz)) {
          if (t > 2) { if (aLow && qLow) continue; }
          else deck = t === 0 ? 20 : 13;
        }
        if (deck && wwbNear(mx, mz)) continue;         // the custom WWB deck owns its crossing
        if (inWide(a) && inWide(q)) continue;          // the wide set paves there
        if (ovpOwned(a[0], a[1], q[0], q[1])) continue; // a baked overpass deck owns it
        const px = -dz * hw, pz = dx * hw;
        const jr = LAYER.road + (6 - Math.min(t, 6)) * 0.055 + hash01(i * 2.9 + 0.4) * 0.1;
        let ya0 = siteY(a[0], a[1], 'road'), yb0 = siteY(q[0], q[1], 'road');
        if (deck) {
          ya0 = Math.max(ya0, TERRAIN.water + (aLow ? deck : deck * 0.35));
          yb0 = Math.max(yb0, TERRAIN.water + (qLow ? deck : deck * 0.35));
        }
        const ya = ySnapF(a[0], a[1], ya0 + jr), yb = ySnapF(q[0], q[1], yb0 + jr);
        const b0 = rc.n;
        rc.pos.push(a[0] + px, ya, a[1] + pz, q[0] + px, yb, q[1] + pz, q[0] - px, yb, q[1] - pz, a[0] - px, ya, a[1] - pz);
        for (let m = 0; m < 4; m++) rc.col.push(c.r * 255, c.g * 255, c.b * 255);
        rc.n += 4;
        rc.idx.push(b0, b0 + 1, b0 + 2, b0, b0 + 2, b0 + 3);
        if (j > 0) {
          const p0 = pts[j - 1];
          let ux0 = a[0] - p0[0], uz0 = a[1] - p0[1];
          const L0 = Math.hypot(ux0, uz0) || 1;
          ux0 /= L0; uz0 /= L0;
          if (ux0 * dx + uz0 * dz < 0.99) rcFanF(a[0], ya, a[1], hw, c.r * 255, c.g * 255, c.b * 255);
        }
      }
      if ((i & 2047) === 2047) await yieldNow();
    }
    // far areas (water splits out onto the animated river material)
    const areaParts = [], waterAreaParts = [];
    for (let i = 0; i < hdr[3]; i++) {
      const n = body[k++], kind = body[k++];
      const poly = new Array(n);
      for (let j = 0; j < n; j++) poly[j] = [body[k++] * S, body[k++] * S];
      if (kind !== 1) {
        const [acx, acz] = polyCentroid(poly);
        if (wwbNear(acx, acz)) continue;               // the WWB deck owns its crossing
      }
      try {
        if (kind === 0) areaParts.push({ geom: Math.abs(signedArea(poly)) > 40000 ? drapedPoly(poly, LAYER.park, 60) : flatPoly(poly, null, LAYER.park), color: new THREE.Color(COLORS.park).multiplyScalar(0.82 + hash01(i) * 0.18), style: 3 });
        else if (kind === 1) waterAreaParts.push({ geom: flatPoly(poly, null, TERRAIN.water + 0.55, true), color: new THREE.Color(COLORS.water), style: 3 });
        else areaParts.push({ geom: flatPoly(poly, null, LAYER.plaza), color: new THREE.Color(0x9a978e), style: 3 });
      } catch (e) { /* degenerate */ }
    }
    // far ground: 100 m strips around the wide box, down to the riverbed over water
    const farGroundMat = new THREE.MeshStandardMaterial({ color: COLORS.ground, roughness: 0.96, metalness: 0 });
    groundMats.push(farGroundMat);
    for (const [x0, x1, z0, z1] of [
      [W.x0, W.x1, W.z0, WIDEB.z0], [W.x0, W.x1, WIDEB.z1, W.z1],
      [W.x0, WIDEB.x0, WIDEB.z0, WIDEB.z1], [WIDEB.x1, W.x1, WIDEB.z0, WIDEB.z1],
    ]) {
      const cell = 100, nx = Math.max(1, Math.round((x1 - x0) / cell)), nz = Math.max(1, Math.round((z1 - z0) / cell));
      const pos = [];
      for (let j = 0; j <= nz; j++) for (let i = 0; i <= nx; i++) {
        const x = x0 + (x1 - x0) * i / nx, z = z0 + (z1 - z0) * j / nz;
        const y = demY(x, z);
        pos.push(x, (y < TERRAIN.water + 0.6 ? (eastOfDelaware(x, z) ? TERRAIN.bed : TERRAIN.water + 0.45) : y) - 0.07, z);
      }
      const idx = [];
      for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
        const a = j * (nx + 1) + i, b = a + 1, d = a + nx + 1, e = d + 1;
        idx.push(a, d, b, b, d, e);
      }
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
      g.setIndex(idx);
      g.computeVertexNormals();
      const m = new THREE.Mesh(g, farGroundMat);
      m.matrixAutoUpdate = false;
      groupCity.add(m);
    }
    loadmsg.textContent = 'Raising the rest of Philadelphia, uploading';
    await yieldNow();
    for (const ch of chunks.values()) {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(ch.pos), 3));
      g.setAttribute('normal', new THREE.BufferAttribute(new Int8Array(ch.nor), 3, true));
      g.setAttribute('color', new THREE.BufferAttribute(new Uint8Array(ch.col), 3, true));
      g.setAttribute('aStyle', new THREE.BufferAttribute(new Int8Array(ch.sty), 1));
      g.setAttribute('aFloorH', new THREE.BufferAttribute(new Int8Array(ch.flh.map(fv => Math.round(fv * 10))), 1));
      g.setAttribute('aBase', new THREE.BufferAttribute(new Float32Array(ch.bas), 1));
      g.setIndex(ch.idx);
      g.computeBoundingSphere();
      freeOnUpload(g);
      ch.pos = ch.nor = ch.col = ch.sty = ch.flh = ch.bas = ch.idx = null;
      const m = new THREE.Mesh(g, cityMat);
      m.matrixAutoUpdate = false;
      groupCity.add(m);
      outerMeshes.push(m);
    }
    renderer.render(scene, camera);   // upload now, behind the veil, and free the arrays
    await yieldNow();
    if (rc.n) {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(rc.pos), 3));
      g.setAttribute('color', new THREE.BufferAttribute(new Uint8Array(rc.col), 3, true));
      g.setIndex(rc.idx);
      g.computeVertexNormals();
      g.computeBoundingSphere();
      freeOnUpload(g);
      rc.pos = rc.col = rc.idx = null;
      groupCity.add(new THREE.Mesh(g, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, side: THREE.DoubleSide })));
    }
    if (areaParts.length) groupCity.add(new THREE.Mesh(mergeColored(areaParts), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95 })));
    if (waterAreaParts.length) groupCity.add(new THREE.Mesh(mergeColored(waterAreaParts), riverMat));
    // the world is now the whole city
    bounds.minX = -12200; bounds.maxX = 16700; bounds.minZ = -21900; bounds.maxZ = 9900;
    scene.fog.near = 2400; scene.fog.far = 13000;
    // the baked neighborhood layer owns these names when present; the airport
    // keeps its HTML label (a place, not a neighborhood)
    const hasNb = typeof PLACES !== 'undefined' && PLACES && PLACES.nb;
    for (const [nm, lx, lz, lh] of [
      ['Philadelphia International Airport', -8334, 7857, 40],
      ...(hasNb ? [] : [
        ['University City', -4300, -600, 90],
        ['Manayunk', -6803, -8950, 60],
        ['Germantown', -4900, -8500, 60],
        ['Frankford', 5561, -7845, 60],
        ['Northeast Philadelphia', 11499, -15760, 60],
      ]),
    ]) {
      const el = document.createElement('div');
      el.className = 'lbl';
      el.textContent = nm;
      labelsRoot.appendChild(el);
      labels.push({ el, pos: new V3(lx, siteY(lx, lz, 'ground') + lh, lz), visible: false, far: true });
    }
  });

  step('Raising the overpasses', () => {
    if (!OVP.el.length && !OVP.cor.length && !OVP.sk.length) return;
    const parts = [];
    // stored DARK for the legacy color pipeline (flats render ~2.5x lighter)
    const cTop = [0x3b3833, 0x3b3833, 0x3f3c37, 0x3f3c37, 0x43403b, 0x45423d, 0x8f8c85];
    const cConc = 0x6e6b64, cParapet = 0x7d7a73, cPier = 0x6b6760, cCap = 0x5c5852;
    const cWall = 0x5a5751, cCope = 0x7d7a73, cFloor = 0x262421, cGutter = 0x504d47, cLine = 0x8a887f;
    const tint = (hex, m) => new THREE.Color(hex).multiplyScalar(m);
    const dens3 = (pts, step3) => {
      const out = [pts[0].slice()];
      for (let i = 0; i + 1 < pts.length; i++) {
        const a = pts[i], b = pts[i + 1];
        const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const k = Math.max(1, Math.ceil(L / step3));
        for (let j = 1; j <= k; j++) {
          const t = j / k;
          out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]);
        }
      }
      return out;
    };
    const norms = (pts) => {
      const nrm = [];
      for (let i = 0; i < pts.length; i++) {
        const a = pts[Math.max(0, i - 1)], b = pts[Math.min(pts.length - 1, i + 1)];
        let dx = b[0] - a[0], dz = b[1] - a[1];
        const L = Math.hypot(dx, dz) || 1;
        nrm.push([-dz / L, dx / L]);
      }
      return nrm;
    };
    // closed box ribbon: top at y+dyT, bottom at bots[i] (or y+dyB), both sides.
    // seg gate (i) can suppress individual segments (parapet gaps at ramp mouths).
    const boxRibbon = (pts, hw, dyT, dyB, colTop, colSide, bots, gate) => {
      const nrm = norms(pts);
      const top = [], side = [];
      for (let i = 0; i + 1 < pts.length; i++) {
        if (gate && !gate(i)) continue;
        const a = pts[i], b = pts[i + 1], na = nrm[i], nb = nrm[i + 1];
        const aL = [a[0] + na[0] * hw, a[1] + na[1] * hw], aR = [a[0] - na[0] * hw, a[1] - na[1] * hw];
        const bL = [b[0] + nb[0] * hw, b[1] + nb[1] * hw], bR = [b[0] - nb[0] * hw, b[1] - nb[1] * hw];
        const aT = a[2] + dyT, bT = b[2] + dyT;
        const aB = bots ? bots[i] : a[2] + dyB, bB = bots ? bots[i + 1] : b[2] + dyB;
        top.push(aL[0], aT, aL[1], bL[0], bT, bL[1], bR[0], bT, bR[1],
                 aL[0], aT, aL[1], bR[0], bT, bR[1], aR[0], aT, aR[1]);
        side.push(aL[0], aB, aL[1], bL[0], bB, bL[1], bR[0], bB, bR[1],
                  aL[0], aB, aL[1], bR[0], bB, bR[1], aR[0], aB, aR[1]);
        for (const [p0, p1] of [[aL, bL], [aR, bR]]) {
          side.push(p0[0], aT, p0[1], p0[0], aB, p0[1], p1[0], bB, p1[1],
                    p0[0], aT, p0[1], p1[0], bB, p1[1], p1[0], bT, p1[1]);
        }
      }
      const mk = (arr, col) => {
        if (!arr.length) return;
        const g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(arr), 3));
        g.computeVertexNormals();
        parts.push({ geom: g, color: col, style: 3 });
      };
      mk(top, colTop);
      mk(side, colSide);
    };
    const boxAt = (cx, cz, ux, uz, along, across, y0, y1, col) => {
      const g = new THREE.BoxGeometry(along, y1 - y0, across);
      g.rotateY(Math.atan2(-uz, ux));
      g.translate(cx, (y0 + y1) / 2, cz);
      parts.push({ geom: g, color: col, style: 3 });
    };
    const crossingRoadNear = (x, z, r, ux, uz) => {
      const gx = Math.floor(x / SEPTA_RG_CELL), gz = Math.floor(z / SEPTA_RG_CELL);
      for (let cx2 = gx - 1; cx2 <= gx + 1; cx2++) for (let cz2 = gz - 1; cz2 <= gz + 1; cz2++) {
        const a = septaRoadGrid.get(cx2 + ':' + cz2);
        if (!a) continue;
        for (let i = 0; i < a.length; i += 4) {
          const ax = a[i], az = a[i + 1], dx = a[i + 2] - ax, dz = a[i + 3] - az;
          const L2 = dx * dx + dz * dz || 1e-9;
          let tt = ((x - ax) * dx + (z - az) * dz) / L2;
          tt = tt < 0 ? 0 : tt > 1 ? 1 : tt;
          const ex = ax + dx * tt - x, ez = az + dz * tt - z;
          if (ex * ex + ez * ez > r * r) continue;
          const L = Math.sqrt(L2);
          if (Math.abs((dx * ux + dz * uz) / L) < 0.82) return true;
        }
      }
      return false;
    };
    // ------- junction mouths: where one chain's end lands on another's deck -------
    // Parapets and barriers must BREAK there (never a rail across a ramp exit),
    // and the joining deck noses 6 m into the through deck so nothing butts.
    const juncGrid = new Map();
    const JC = 30;
    const juncAdd = (p, q, hw) => {
      // p = chain end, q = the point before it (gives the approach direction)
      let dx = p[0] - q[0], dz = p[1] - q[1];
      const L = Math.hypot(dx, dz) || 1;
      const e = { x: p[0], z: p[1], y: p[2], hw, dx: dx / L, dz: dz / L };
      const k = Math.floor(p[0] / JC) + ':' + Math.floor(p[1] / JC);
      let a = juncGrid.get(k);
      if (!a) { a = []; juncGrid.set(k, a); }
      a.push(e);
    };
    for (const c of OVP.el.concat(OVP.sk)) {
      const e = c.e || [0, 0];
      if (e[0] === 1 && c.p.length > 1) juncAdd(c.p[0], c.p[1], c.w / 2);
      if (e[1] === 1 && c.p.length > 1) juncAdd(c.p[c.p.length - 1], c.p[c.p.length - 2], c.w / 2);
    }
    // is there a ramp mouth at (x,z,y) on the side whose outward normal is (nx,nz)?
    // omit the normal to test both sides (median barriers)
    const mouthAt = (x, z, y, nx, nz, self) => {
      const gx = Math.floor(x / JC), gz = Math.floor(z / JC);
      for (let cx2 = gx - 1; cx2 <= gx + 1; cx2++) for (let cz2 = gz - 1; cz2 <= gz + 1; cz2++) {
        const a = juncGrid.get(cx2 + ':' + cz2);
        if (!a) continue;
        for (const jp of a) {
          if (jp === self) continue;
          const dd = Math.hypot(jp.x - x, jp.z - z);
          if (dd > jp.hw + 6.5 || Math.abs(jp.y - y) > 3.2) continue;
          if (nx === undefined) return true;
          // the mouth opens toward where the ramp came FROM
          if (-(jp.dx * nx + jp.dz * nz) > 0.1 || dd < jp.hw + 1.5) return true;
        }
      }
      return false;
    };
    // another chain's deck at a similar height covering this point (braided ramps,
    // junction noses): parapets must not stab up through the overlapping deck
    const deckOverlapAt = (x, z, y, selfId) => {
      const arr = ovpGrid.get(Math.floor(x / OVP_CELL) + ':' + Math.floor(z / OVP_CELL));
      if (!arr) return false;
      for (const s2 of arr) {
        if (ovpSegs[s2 + 7] < 0 || ovpSegs[s2 + 8] === selfId) continue;
        const sax = ovpSegs[s2], saz = ovpSegs[s2 + 1], sbx = ovpSegs[s2 + 2], sbz = ovpSegs[s2 + 3], hw2 = ovpSegs[s2 + 6];
        const dx = sbx - sax, dz = sbz - saz;
        const L2 = dx * dx + dz * dz || 1e-9;
        let t = ((x - sax) * dx + (z - saz) * dz) / L2;
        t = clamp(t, 0, 1);
        const px = sax + dx * t - x, pz = saz + dz * t - z;
        const r = hw2 - 0.4;
        if (r <= 0 || px * px + pz * pz > r * r) continue;
        const y2 = ovpSegs[s2 + 4] + (ovpSegs[s2 + 5] - ovpSegs[s2 + 4]) * t;
        if (Math.abs(y2 - y) < 2.5) return true;
      }
      return false;
    };
    // another chain's deck passing between the ground and this soffit: a pier
    // must not punch down through a lower roadway (stacked interchanges)
    const deckBetween = (x, z, yLo, yHi, selfId) => {
      const arr = ovpGrid.get(Math.floor(x / OVP_CELL) + ':' + Math.floor(z / OVP_CELL));
      if (!arr) return false;
      for (const s2 of arr) {
        if (ovpSegs[s2 + 7] < 0 || ovpSegs[s2 + 8] === selfId) continue;
        const sax = ovpSegs[s2], saz = ovpSegs[s2 + 1], sbx = ovpSegs[s2 + 2], sbz = ovpSegs[s2 + 3], hw2 = ovpSegs[s2 + 6];
        const dx = sbx - sax, dz = sbz - saz;
        const L2 = dx * dx + dz * dz || 1e-9;
        let t = ((x - sax) * dx + (z - saz) * dz) / L2;
        t = clamp(t, 0, 1);
        const px = sax + dx * t - x, pz = saz + dz * t - z;
        const r = hw2 + 1;
        if (px * px + pz * pz > r * r) continue;
        const y2 = ovpSegs[s2 + 4] + (ovpSegs[s2 + 5] - ovpSegs[s2 + 4]) * t;
        if (y2 > yLo && y2 < yHi) return true;
      }
      return false;
    };
    const shapePts = (c) => {
      const pts = dens3(c.p, 13);
      const e = c.e || [0, 0];
      for (const side of [0, 1]) {
        if ((side ? e[1] : e[0]) !== 1) continue;
        const a = side ? pts[pts.length - 1] : pts[0];
        const b = side ? pts[pts.length - 2] : pts[1];
        let dx = a[0] - b[0], dz = a[1] - b[1];
        const L = Math.hypot(dx, dz) || 1;
        const ext = [a[0] + dx / L * 6, a[1] + dz / L * 6, a[2]];
        if (side) pts.push(ext); else pts.unshift(ext);
      }
      return pts;
    };
    // ---------------- elevated chains: deck box, parapets, piers ----------------
    for (let ci = 0; ci < OVP.el.length; ci++) {
      const c = OVP.el[ci];
      const e = c.e || [0, 0];
      const hw = Math.max(1.6, c.w / 2);
      const dep = c.c <= 1 ? 1.7 : (c.c === 6 ? 0.5 : 1.15);
      const pts = shapePts(c);
      const jit = 0.92 + hash01(ci * 2.13) * 0.16;
      const bots = pts.map((p) => {
        const gy = siteY(p[0], p[1], 'ground');
        return p[2] - gy < 2.2 ? Math.min(p[2] - dep, gy - 0.4) : p[2] - dep;
      });
      boxRibbon(pts, hw, 0, -dep, tint(cTop[c.c] || 0x3b3833, 1), tint(cConc, jit), bots);
      // parapets: fade in past the ends, break at every ramp mouth on their side
      const nrm = norms(pts);
      const ss = [0];
      for (let i = 1; i < pts.length; i++) ss.push(ss[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
      const total = ss[ss.length - 1];
      const pOff = hw - (c.c === 6 ? 0.16 : 0.36);
      const pT = c.c === 6 ? 1.15 : 1.02, pW = c.c === 6 ? 0.09 : 0.17;
      const lead0 = e[0] === 1 ? 6.5 : 14, lead1 = e[1] === 1 ? 6.5 : 14;
      for (const s of [1, -1]) {
        const edge = pts.map((p, i) => [p[0] + nrm[i][0] * pOff * s, p[1] + nrm[i][1] * pOff * s, p[2]]);
        boxRibbon(edge, pW, pT, -0.25, tint(cParapet, jit), tint(cParapet, jit * 0.94), null, (i) => {
          const sm = (ss[i] + ss[i + 1]) / 2;
          if (sm < lead0 || sm > total - lead1) return false;
          const mx = (edge[i][0] + edge[i + 1][0]) / 2, mz = (edge[i][1] + edge[i + 1][1]) / 2;
          const my = (pts[i][2] + pts[i + 1][2]) / 2;
          if (deckOverlapAt(mx, mz, my, ci)) return false;
          return !mouthAt(mx, mz, my, nrm[i][0] * s, nrm[i][1] * s);
        });
      }
      // piers wherever there is clearance and no street crossing beneath
      const gap = c.c <= 1 ? 26 : (c.c === 6 ? 15 : 21);
      let acc = gap * 0.6;
      for (let i = 0; i + 1 < pts.length; i++) {
        const a = pts[i], b = pts[i + 1];
        acc += Math.hypot(b[0] - a[0], b[1] - a[1]);
        if (acc < gap) continue;
        acc = 0;
        const x = (a[0] + b[0]) / 2, z = (a[1] + b[1]) / 2, y = (a[2] + b[2]) / 2;
        let ux = b[0] - a[0], uz = b[1] - a[1];
        const uL = Math.hypot(ux, uz) || 1;
        ux /= uL; uz /= uL;
        const vf = vineCut(x, z, -1);
        const wet = demY(x, z) < TERRAIN.water + 0.6 && riverCorridor(x, z);
        const gy = vf !== null ? vf : (wet ? TERRAIN.bed - 1.2 : siteY(x, z, 'ground'));
        const capBot = y - dep - (c.c === 6 ? 0 : 1.25);
        if (capBot - gy < 2.0) continue;
        if (crossingRoadNear(x, z, 7.5, ux, uz)) continue;
        if (deckBetween(x, z, gy + 0.5, capBot - 0.2, ci)) continue;
        const ps = wet ? 1.6 : 1;
        if (c.c <= 1) {
          boxAt(x, z, ux, uz, 2.3, c.w * 0.92, y - dep - 1.35, y - dep + 0.15, tint(cCap, jit));
          const px = -uz * c.w * 0.24, pz = ux * c.w * 0.24;
          boxAt(x + px, z + pz, ux, uz, 1.5 * ps, 2.0 * ps, gy - 2, capBot + 0.3, tint(cPier, jit));
          boxAt(x - px, z - pz, ux, uz, 1.5 * ps, 2.0 * ps, gy - 2, capBot + 0.3, tint(cPier, jit));
        } else if (c.c === 6) {
          boxAt(x, z, ux, uz, 0.7, 0.7, gy - 2, y - dep + 0.2, tint(cPier, jit));
        } else {
          boxAt(x, z, ux, uz, 1.9, c.w * 0.62, y - dep - 1.15, y - dep + 0.15, tint(cCap, jit));
          boxAt(x, z, ux, uz, 1.35 * ps, 1.8 * ps, gy - 2, capBot + 0.3, tint(cPier, jit));
        }
      }
    }
    // ---------------- the Vine Street cut: walls, floor, portals ----------------
    const collarParts = [];
    const wallQuad = (q, arr) => arr.push(...q);
    for (const run of OVP.cor) {
      const nrm = norms(run);
      const wl = run.map((p, i) => [p[0] + nrm[i][0] * p[3], p[1] + nrm[i][1] * p[3], p[2]]);
      const wr = run.map((p, i) => [p[0] - nrm[i][0] * p[3], p[1] - nrm[i][1] * p[3], p[2]]);
      const gl = wl.map((p) => siteY(p[0], p[1], 'ground'));
      const gr = wr.map((p) => siteY(p[0], p[1], 'ground'));
      const quads = [], copes = [];
      const segGap = (w0, w1, i) => {
        // break the wall where a sunken ramp passes through it (its portal)
        const mx = (w0[i][0] + w0[i + 1][0]) / 2, mz = (w0[i][1] + w0[i + 1][1]) / 2;
        let wx = w0[i + 1][0] - w0[i][0], wz = w0[i + 1][1] - w0[i][1];
        const L = Math.hypot(wx, wz) || 1;
        wx /= L; wz /= L;
        const arr = ovpGrid.get(Math.floor(mx / OVP_CELL) + ':' + Math.floor(mz / OVP_CELL));
        if (!arr) return false;
        for (const s of arr) {
          if (ovpSegs[s + 7] !== -1) continue;
          const sax = ovpSegs[s], saz = ovpSegs[s + 1], sbx = ovpSegs[s + 2], sbz = ovpSegs[s + 3], shw = ovpSegs[s + 6];
          let dx = sbx - sax, dz = sbz - saz;
          const sl = Math.hypot(dx, dz) || 1;
          if (Math.abs((dx * wx + dz * wz) / sl) > 0.85) continue;    // parallel: the mainline itself
          const L2 = sl * sl;
          let t = ((mx - sax) * dx + (mz - saz) * dz) / L2;
          t = clamp(t, 0, 1);
          const px = sax + dx * t - mx, pz = saz + dz * t - mz;
          if (px * px + pz * pz < (shw + 2.5) * (shw + 2.5)) return true;
        }
        return false;
      };
      for (let i = 0; i + 1 < run.length; i++) {
        if (!segGap(wl, wl, i)) {
          wallQuad([wl[i][0], wl[i][2] - 0.6, wl[i][1], wl[i + 1][0], wl[i + 1][2] - 0.6, wl[i + 1][1],
                    wl[i + 1][0], gl[i + 1] + 0.55, wl[i + 1][1],
                    wl[i][0], wl[i][2] - 0.6, wl[i][1], wl[i + 1][0], gl[i + 1] + 0.55, wl[i + 1][1],
                    wl[i][0], gl[i] + 0.55, wl[i][1]], quads);
          copes.push([wl[i], wl[i + 1], gl[i], gl[i + 1]]);
        }
        if (!segGap(wr, wr, i)) {
          wallQuad([wr[i][0], wr[i][2] - 0.6, wr[i][1], wr[i + 1][0], wr[i + 1][2] - 0.6, wr[i + 1][1],
                    wr[i + 1][0], gr[i + 1] + 0.55, wr[i + 1][1],
                    wr[i][0], wr[i][2] - 0.6, wr[i][1], wr[i + 1][0], gr[i + 1] + 0.55, wr[i + 1][1],
                    wr[i][0], gr[i] + 0.55, wr[i][1]], quads);
          copes.push([wr[i], wr[i + 1], gr[i], gr[i + 1]]);
        }
      }
      const wg = new THREE.BufferGeometry();
      wg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(quads), 3));
      wg.computeVertexNormals();
      parts.push({ geom: wg, color: new THREE.Color(cWall), style: 3 });
      // coping caps ride the wall tops (a light parapet band, slightly proud)
      for (const [a, b, ga, gb] of copes) {
        let dx = b[0] - a[0], dz = b[1] - a[1];
        const L = Math.hypot(dx, dz) || 1;
        const ex = (a[0] + b[0]) / 2, ez = (a[1] + b[1]) / 2;
        boxAt(ex, ez, dx / L, dz / L, L + 0.05, 0.55, (ga + gb) / 2 + 0.4, (ga + gb) / 2 + 1.0, tint(cCope, 1));
      }
      // floor slab wall to wall, with lighter gutter strips along each wall base
      const fq = [], gq = [];
      for (let i = 0; i + 1 < run.length; i++) {
        fq.push(wl[i][0], run[i][2], wl[i][1], wl[i + 1][0], run[i + 1][2], wl[i + 1][1], wr[i + 1][0], run[i + 1][2], wr[i + 1][1],
                wl[i][0], run[i][2], wl[i][1], wr[i + 1][0], run[i + 1][2], wr[i + 1][1], wr[i][0], run[i][2], wr[i][1]);
        for (const [w0, s] of [[wl, 1], [wr, -1]]) {
          const g0 = [w0[i][0] - nrm[i][0] * s * 1.1, w0[i][1] - nrm[i][1] * s * 1.1];
          const g1 = [w0[i + 1][0] - nrm[i + 1][0] * s * 1.1, w0[i + 1][1] - nrm[i + 1][1] * s * 1.1];
          gq.push(w0[i][0], run[i][2] + 0.03, w0[i][1], w0[i + 1][0], run[i + 1][2] + 0.03, w0[i + 1][1], g1[0], run[i + 1][2] + 0.03, g1[1],
                  w0[i][0], run[i][2] + 0.03, w0[i][1], g1[0], run[i + 1][2] + 0.03, g1[1], g0[0], run[i][2] + 0.03, g0[1]);
        }
      }
      for (const [arr, col] of [[fq, cFloor], [gq, cGutter]]) {
        const g2 = new THREE.BufferGeometry();
        g2.setAttribute('position', new THREE.BufferAttribute(new Float32Array(arr), 3));
        g2.computeVertexNormals();
        parts.push({ geom: g2, color: new THREE.Color(col), style: 3 });
      }
      // portal faces + header beams where the cut meets a covered section
      for (const e2 of [0, run.length - 1]) {
        const gm = (gl[e2] + gr[e2]) / 2;
        const pg = [wl[e2][0], run[e2][2] - 0.6, wl[e2][1], wr[e2][0], run[e2][2] - 0.6, wr[e2][1],
                    wr[e2][0], gm + 0.55, wr[e2][1],
                    wl[e2][0], run[e2][2] - 0.6, wl[e2][1], wr[e2][0], gm + 0.55, wr[e2][1],
                    wl[e2][0], gm + 0.55, wl[e2][1]];
        const g2 = new THREE.BufferGeometry();
        g2.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pg), 3));
        g2.computeVertexNormals();
        parts.push({ geom: g2, color: new THREE.Color(cWall), style: 3 });
        let hx = wr[e2][0] - wl[e2][0], hz = wr[e2][1] - wl[e2][1];
        const hl = Math.hypot(hx, hz) || 1;
        boxAt((wl[e2][0] + wr[e2][0]) / 2, (wl[e2][1] + wr[e2][1]) / 2, hx / hl, hz / hl,
              hl + 1.2, 1.1, gm - 0.25, gm + 0.85, tint(cCope, 1));
      }
      // grade collar apron hides the ragged heightfield hole around the cut
      for (const s of [1, -1]) {
        const off = run.map((p, i) => [p[0] + nrm[i][0] * (p[3] + 16.5) * s, p[1] + nrm[i][1] * (p[3] + 16.5) * s]);
        collarParts.push({ geom: ribbon(off, 34, 0.07, (x, z) => siteY(x, z, 'ground')), color: new THREE.Color(COLORS.ground), style: 3 });
      }
      // median barrier down the cut, broken at every ramp mouth
      const med = [];
      for (const p of run) {
        if (p[3] < 20 && !mouthAt(p[0], p[1], p[2] + 0.45)) med.push([p[0], p[1], p[2]]);
        else if (med.length > 2) { boxRibbon(med.slice(), 0.26, 0.85, -0.1, tint(cCope, 1), tint(cCope, 0.94)); med.length = 0; }
        else med.length = 0;
      }
      if (med.length > 2) boxRibbon(med, 0.26, 0.85, -0.1, tint(cCope, 1), tint(cCope, 0.94));
    }
    // ------- sunken carriageways and ramps: roadway, edge lines, ramp-cut walls ----
    for (const c of OVP.sk) {
      const pts = shapePts(c);
      const hw = Math.max(1.6, c.w / 2);
      boxRibbon(pts, hw, 0, -0.5, tint(0x33312d, 1), tint(0x2b2926, 1));
      // pale edge lines read as lane striping from altitude
      const nrm = norms(pts);
      for (const s of [1, -1]) {
        const edge = pts.map((p, i) => [p[0] + nrm[i][0] * (hw - 0.45) * s, p[1] + nrm[i][1] * (hw - 0.45) * s, p[2]]);
        boxRibbon(edge, 0.09, 0.03, -0.01, tint(cLine, 1), tint(cLine, 1));
      }
      // outside the main corridor an OPEN sunken ramp runs in its own narrow
      // walled cut; covered tunnels stay under the untouched ground
      const rq = [];
      for (let i = 0; c.cov !== 1 && i + 1 < pts.length; i++) {
        const mx = (pts[i][0] + pts[i + 1][0]) / 2, mz = (pts[i][1] + pts[i + 1][1]) / 2;
        const my = (pts[i][2] + pts[i + 1][2]) / 2;
        if (vineCut(mx, mz, 2) !== null) continue;
        if (demY(mx, mz) - my < 1.0) continue;
        for (const s of [1, -1]) {
          const a = [pts[i][0] + nrm[i][0] * (hw + 0.7) * s, pts[i][1] + nrm[i][1] * (hw + 0.7) * s];
          const b = [pts[i + 1][0] + nrm[i + 1][0] * (hw + 0.7) * s, pts[i + 1][1] + nrm[i + 1][1] * (hw + 0.7) * s];
          const ga = siteY(a[0], a[1], 'ground'), gb = siteY(b[0], b[1], 'ground');
          rq.push(a[0], pts[i][2] - 0.6, a[1], b[0], pts[i + 1][2] - 0.6, b[1], b[0], gb + 0.5, b[1],
                  a[0], pts[i][2] - 0.6, a[1], b[0], gb + 0.5, b[1], a[0], ga + 0.5, a[1]);
        }
      }
      if (rq.length) {
        const g2 = new THREE.BufferGeometry();
        g2.setAttribute('position', new THREE.BufferAttribute(new Float32Array(rq), 3));
        g2.computeVertexNormals();
        parts.push({ geom: g2, color: new THREE.Color(cWall), style: 3 });
        const off1 = pts.map((p, i) => [p[0] + nrm[i][0] * (hw + 12), p[1] + nrm[i][1] * (hw + 12)]);
        const off2 = pts.map((p, i) => [p[0] - nrm[i][0] * (hw + 12), p[1] - nrm[i][1] * (hw + 12)]);
        collarParts.push({ geom: ribbon(off1, 24, 0.07, (x, z) => siteY(x, z, 'ground')), color: new THREE.Color(COLORS.ground), style: 3 });
        collarParts.push({ geom: ribbon(off2, 24, 0.07, (x, z) => siteY(x, z, 'ground')), color: new THREE.Color(COLORS.ground), style: 3 });
      }
    }
    if (parts.length) {
      const ovpMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.92, side: THREE.DoubleSide });
      const mesh = new THREE.Mesh(mergeColored(parts), ovpMat);
      mesh.castShadow = !isTouch;   // phone GPUs skip the deck shadow pass
      mesh.receiveShadow = true;
      groupCity.add(mesh);
      rayTargets.push(mesh);
    }
    if (collarParts.length) {
      const collarMat = new THREE.MeshStandardMaterial({ color: COLORS.ground, roughness: 0.96, metalness: 0, side: THREE.DoubleSide });
      groundMats.push(collarMat);
      const collar = new THREE.Mesh(mergeColored(collarParts), collarMat);
      collar.receiveShadow = true;
      groupCity.add(collar);
    }
  });

  // ------------------------------------------------ trees
  // -------------------------------------------------------------- street trees
  // The real city forest: PPR Tree Inventory 2025 (OpenDataPhilly), baked by
  // fetch_trees.py / pack_trees.py into TREES_B64 (int16, 0.2 m units) and
  // TREE_NAMES (species + latin + canopy group). Every tree is a surveyed
  // street or park tree at its true position, sized by its measured trunk
  // diameter. The old procedural scatter survives below as the fallback when
  // the baked data is absent, so the page always builds.
  let treeInv = null, pickedTree = null;
  const treePickGrid = new Map();
  const TREE_CELL = 24;
  // per-group canopy styling: hue, sat, lit, breadth, height, size mult, shape.
  // Shapes: 0 round crown, 1 conifer spire, 2 vase (zelkova/elm), 3 pyramid
  // (linden). Palettes are pushed well apart so species read at a glance:
  // khaki planetrees, chartreuse ginkgo columns, pale low ornamental puffs,
  // deep oak domes, blue-green conifers.
  // (lightness stored DARK: the legacy color pipeline + ACES lifts flats ~2.5x,
  // so judge these by rendered swatch, never by hex — handoff gotcha)
  // Species separation must live in HUE and SATURATION: the daylight pipeline
  // (strong sun + hemi + ACES) flattens albedo-lightness differences to almost
  // nothing, so chroma carries the identity.
  const TREE_STYLE = [
    [0.26, 0.44, 0.15, 1.0, 1.0, 1.0, 0],      // 0 shade tree / unknown: neutral green
    [0.20, 0.28, 0.16, 1.35, 0.88, 1.25, 0],   // 1 planetree, sycamore: grayed khaki-tan
    [0.33, 0.70, 0.13, 1.0, 1.1, 1.0, 0],      // 2 maple: vivid pure green
    [0.30, 0.60, 0.085, 1.22, 1.02, 1.15, 0],  // 3 oak: deep bottle-green dome
    [0.22, 0.68, 0.165, 1.12, 0.60, 0.72, 0],  // 4 ornamental: bright spring yellow-green puff
    [0.19, 0.55, 0.16, 1.2, 0.72, 0.95, 0],    // 5 locust: warm golden-olive, flat-topped
    [0.36, 0.50, 0.13, 1.0, 1.0, 1.05, 2],     // 6 elm form: cool teal-green vase
    [0.14, 0.68, 0.17, 0.55, 1.55, 0.95, 0],   // 7 ginkgo: unmistakable yellow column
    [0.27, 0.58, 0.145, 1.0, 1.15, 1.0, 3],    // 8 linden: fresh mid-green pyramid
    [0.42, 0.45, 0.075, 1.0, 1.0, 0.92, 1],    // 9 conifer: dark blue-green spire
    [0.30, 0.16, 0.19, 0.72, 1.40, 1.0, 0],    // 10 tall broadleaf: silvery gray-green column
    [0.24, 0.40, 0.15, 1.05, 0.92, 1.0, 0],    // 11 urban misc: dusty olive
  ];
  function treeChipColor(g) {
    const s = TREE_STYLE[g] || TREE_STYLE[0];
    return 'hsl(' + Math.round(s[0] * 360) + ',' + Math.round(s[1] * 100) + '%,' + Math.round((s[2] + 0.13) * 100) + '%)';
  }
  function treeCard(i) {
    const ni = treeInv.ni[i];
    const g = ni >= 0 ? (TREE_NAMES.g[ni] || 0) : 0;
    const name = ni >= 0 ? TREE_NAMES.names[ni] : 'Shade Tree';
    const latin = ni >= 0 ? (TREE_NAMES.latin[ni] || '') : '';
    const dbh = treeInv.dbh[i];
    vehinfoBody.innerHTML =
      '<span class="vroute" style="background:' + treeChipColor(g) + '">' + dbh + '&Prime;</span>' +
      '<span class="vdest">' + septaEsc(name) + '</span>' +
      (latin ? '<div class="vmeta">' + septaEsc(latin) + '</div>' : '') +
      '<div class="vmeta">' + dbh + '-Inch Trunk</div>' +
      '<div class="vmeta">' + (ni >= 0 ? 'PPR Tree Inventory 2025' : 'OpenStreetMap Mapped Tree') + '</div>';
  }
  function updateTreePick() {
    if (pickedTree == null || !treeInv) return;
    _ssv.set(treeInv.x[pickedTree], treeInv.gy[pickedTree] + 3.5, treeInv.z[pickedTree]).project(camera);
    if (_ssv.z > 1 || _ssv.z < -1) vehinfoEl.style.opacity = '0';
    else {
      vehinfoEl.style.opacity = '1';
      vehinfoEl.style.transform = 'translate(-50%,-100%) translate(' +
        ((_ssv.x * 0.5 + 0.5) * window.innerWidth).toFixed(1) + 'px,' +
        ((-_ssv.y * 0.5 + 0.5) * window.innerHeight).toFixed(1) + 'px)';
    }
  }
  function groundPointAt(cx, cy) {
    // march the pick ray to the walkable ground: cheap log-stepped scan, then
    // a short bisection — no raycast against 49k tree instances
    septaNdc.set((cx / window.innerWidth) * 2 - 1, -(cy / window.innerHeight) * 2 + 1);
    septaRay.setFromCamera(septaNdc, camera);
    const o = septaRay.ray.origin, dr = septaRay.ray.direction;
    let t0 = 0;
    for (let t = 10; t < 9000; t *= 1.22) {
      if (o.y + dr.y * t <= walkY(o.x + dr.x * t, o.z + dr.z * t) + 0.5) {
        let lo = t0, hi = t;
        for (let k = 0; k < 12; k++) {
          const m = (lo + hi) / 2;
          if (o.y + dr.y * m <= walkY(o.x + dr.x * m, o.z + dr.z * m) + 0.5) hi = m; else lo = m;
        }
        return [o.x + dr.x * hi, o.z + dr.z * hi];
      }
      t0 = t;
    }
    return null;
  }
  step('Planting the street trees', () => {
    if (typeof TREES_B64 === 'undefined' || !TREES_B64 || typeof TREE_NAMES === 'undefined' || !TREE_NAMES) { plantProceduralTrees(); return; }
    let head, v;
    try {
      const s = atob(TREES_B64);
      TREES_B64 = null;
      const buf = new Uint8Array(s.length);
      for (let i = 0; i < s.length; i++) buf[i] = s.charCodeAt(i);
      head = new Int32Array(buf.buffer, 0, 4);
      if (head[0] !== 0x53485454) throw new Error('bad tree magic');
      v = new Int16Array(buf.buffer, 16);
    } catch (err) { console.error('tree inventory decode failed', err); plantProceduralTrees(); return; }
    const nAll = head[1];
    const WB = { x0: -3700, x1: 2300, z0: -4480, z1: 6400 };  // wide tier (pack_wide.py)
    const inCore = (x, z) => x > CORE_EXT.x0 && x < CORE_EXT.x1 && z > CORE_EXT.z0 && z < CORE_EXT.z1;
    const X = new Float32Array(nAll + 512), Z = new Float32Array(nAll + 512), GY = new Float32Array(nAll + 512);
    const CR = new Float32Array(nAll + 512), CY = new Float32Array(nAll + 512);
    const DBH = new Uint8Array(nAll + 512), NI = new Int16Array(nAll + 512);
    const CORE = new Uint8Array(nAll + 512);
    let n = 0;
    const keepTree = (x, z, dbh, ni, core) => {
      if (vineCut(x, z, 2) !== null) return;   // no trees floating over the expressway cut
      const g = ni >= 0 ? (TREE_NAMES.g[ni] || 0) : 0;
      const st = TREE_STYLE[g] || TREE_STYLE[0];
      X[n] = x; Z[n] = z; DBH[n] = dbh; NI[n] = ni; CORE[n] = core ? 1 : 0;
      GY[n] = siteY(x, z, 'ground');
      CR[n] = clamp((1.1 + dbh * 0.14) * st[5], 1.3, 7.5);
      CY[n] = GY[n] + clamp(2.4 + dbh * 0.1, 2.6, 5.2) * 0.75 + CR[n] * st[4] * 0.72;
      const k = Math.floor(x / TREE_CELL) + ':' + Math.floor(z / TREE_CELL);
      let cell = treePickGrid.get(k);
      if (!cell) { cell = []; treePickGrid.set(k, cell); }
      cell.push(n);
      n++;
    };
    const nearKept = (x, z, r) => {
      const gx = Math.floor(x / TREE_CELL), gz = Math.floor(z / TREE_CELL);
      for (let ix = gx - 1; ix <= gx + 1; ix++) for (let iz = gz - 1; iz <= gz + 1; iz++) {
        const cell = treePickGrid.get(ix + ':' + iz);
        if (!cell) continue;
        for (const ti of cell) {
          const dx = X[ti] - x, dz = Z[ti] - z;
          if (dx * dx + dz * dz < r * r) return true;
        }
      }
      return false;
    };
    const bermHit = (x, z) => {
      for (const [bx, bz, rx, rz, th] of bermSpots) {
        const dx = x - bx, dz = z - bz, cth = Math.cos(th), sth = Math.sin(th);
        const u = dx * cth - dz * sth, w = dx * sth + dz * cth;
        if ((u / rx) * (u / rx) + (w / rz) * (w / rz) < 1.25) return true;
      }
      return false;
    };
    for (let i = 0; i < nAll; i++) {
      const x = v[i * 4] / 5, z = v[i * 4 + 1] / 5;
      const core = inCore(x, z);
      if (!core && isTouch && (i & 1)) continue;          // touch keeps half the wide forest
      if (inWater(x, z) > -2) continue;
      if (core) {
        // the core's landmarks were rebuilt by hand and differ from the city
        // footprints the bake rejected against, so re-check here
        if (insideBuilding(x, z) || nearBuildingEdge(x, z, 0.8)) continue;
        if (nearRoad(x, z, -1.2)) continue;               // >1.2 m INSIDE a road ribbon only
        if (bermHit(x, z)) continue;
      } else if (septaSnapRoad(x, z, 2.4)) continue;      // wide tier: centerline strip only
      keepTree(x, z, clamp(v[i * 4 + 2], 1, 60), v[i * 4 + 3], core);
    }
    const nInv = n;
    // curated grounds the survey doesn't cover: the towers' lawns, pool
    // terraces, and OSM-mapped courtyard trees — only where no surveyed tree
    // already stands within 6 m
    const extras = [];
    for (const t of D.trees || []) extras.push([t[0], t[1], 10]);
    for (const sp of poolTreeSpots) extras.push([sp[0], sp[1], 14]);
    for (const sp of extraTreeSpots) extras.push([sp[0], sp[1], 14]);
    for (let i = 0; i < 90; i++) {
      const ang = hash01(i * 1.9 + 2) * Math.PI * 2, rr = PLAZA_R + 6 + hash01(i * 3.7) * 50;
      extras.push([towersCenter.x + Math.cos(ang) * rr, towersCenter.z + Math.sin(ang) * rr, 12 + Math.round(hash01(i * 7.1) * 10)]);
    }
    for (const [x, z, dbh] of extras) {
      if (n >= X.length) break;
      if (nearKept(x, z, 6)) continue;
      if (inWater(x, z) > -2) continue;
      if (insideBuilding(x, z) || nearBuildingEdge(x, z, 1.6)) continue;
      if (nearRoad(x, z, 1.2)) continue;
      if (bermHit(x, z)) continue;
      keepTree(x, z, dbh, -1, inCore(x, z));
    }
    treeInv = { x: X, z: Z, gy: GY, cr: CR, cy: CY, dbh: DBH, ni: NI, n };
    // ---- instancing: full trees in the core, light trees in 3x3 wide chunks
    const canMat = new THREE.MeshStandardMaterial({ roughness: 0.95 });
    const trunkMat = new THREE.MeshStandardMaterial({ color: COLORS.trunk, roughness: 1 });
    const trunkCoreG = new THREE.CylinderGeometry(0.17, 0.28, 3.6, 6);
    trunkCoreG.translate(0, 1.0, 0);   // extends below grade so raised layers never slice the base
    const trunkWideG = new THREE.CylinderGeometry(0.18, 0.27, 3.6, 5);
    trunkWideG.translate(0, 1.0, 0);
    const canCoreG = new THREE.IcosahedronGeometry(1, 1);
    const canWideG = new THREE.IcosahedronGeometry(1, 0);
    const coneG = new THREE.ConeGeometry(1, 1, 7);
    coneG.translate(0, 0.5, 0);
    // species silhouettes beyond the sphere: a zelkova/elm vase (flaring cup
    // with a low crown cap) and a linden pyramid, both unit-sized like the ico
    const concatGeo = (list) => {
      const parts2 = list.map((g2) => (g2.index ? g2.toNonIndexed() : g2));
      let total = 0;
      for (const g2 of parts2) total += g2.attributes.position.count;
      const pos2 = new Float32Array(total * 3), nor2 = new Float32Array(total * 3);
      let o2 = 0;
      for (const g2 of parts2) {
        pos2.set(g2.attributes.position.array, o2 * 3);
        nor2.set(g2.attributes.normal.array, o2 * 3);
        o2 += g2.attributes.position.count;
      }
      const out = new THREE.BufferGeometry();
      out.setAttribute('position', new THREE.BufferAttribute(pos2, 3));
      out.setAttribute('normal', new THREE.BufferAttribute(nor2, 3));
      return out;
    };
    const vaseG = concatGeo([
      new THREE.CylinderGeometry(1.0, 0.3, 1.3, 7).translate(0, -0.25, 0),
      new THREE.IcosahedronGeometry(1, 0).scale(1.02, 0.5, 1.02).translate(0, 0.42, 0),
    ]);
    const pyrG = new THREE.ConeGeometry(1, 1.7, 7);
    const CHN = 3;
    const chunkOf = (x, z) => {
      const cx2 = clamp(Math.floor((x - WB.x0) / ((WB.x1 - WB.x0) / CHN)), 0, CHN - 1);
      const cz2 = clamp(Math.floor((z - WB.z0) / ((WB.z1 - WB.z0) / CHN)), 0, CHN - 1);
      return cx2 * CHN + cz2;
    };
    // instance transforms don't grow a shared geometry's unit-sized bounding
    // sphere, so every mesh gets its own cloned geometry with a hand-set
    // sphere over its real extent — wide chunks still frustum-cull as wholes
    const instMesh = (base, mat2, count, sx2, sz2, rad) => {
      const g2 = base.clone();
      g2.boundingSphere = new THREE.Sphere(new V3(sx2, 10, sz2), rad);
      return new THREE.InstancedMesh(g2, mat2, count);
    };
    const coreCX = (CORE_EXT.x0 + CORE_EXT.x1) / 2, coreCZ = (CORE_EXT.z0 + CORE_EXT.z1) / 2;
    const coreR = Math.hypot(CORE_EXT.x1 - CORE_EXT.x0, CORE_EXT.z1 - CORE_EXT.z0) / 2 + 40;
    const chW = (WB.x1 - WB.x0) / CHN, chD = (WB.z1 - WB.z0) / CHN;
    const chR = Math.hypot(chW, chD) / 2 + 40;
    const chCX = (c) => WB.x0 + (Math.floor(c / CHN) + 0.5) * chW;
    const chCZ = (c) => WB.z0 + ((c % CHN) + 0.5) * chD;
    const wideR = Math.hypot(WB.x1 - WB.x0, WB.z1 - WB.z0) / 2 + 40;
    // canopies split by shape (round crowns keep the core/wide chunk split;
    // vases, pyramids and conifer spires draw citywide in one mesh each), and
    // every non-conifer tree gets its trunk from the tier trunk meshes
    const buckets = { core: [], cones: [], vases: [], pyrs: [], wide: [], tCore: [], tWide: [] };
    for (let c = 0; c < CHN * CHN; c++) { buckets.wide.push([]); buckets.tWide.push([]); }
    for (let i = 0; i < n; i++) {
      const g = NI[i] >= 0 ? (TREE_NAMES.g[NI[i]] || 0) : 0;
      const shape = (TREE_STYLE[g] || TREE_STYLE[0])[6];
      if (shape === 1) { buckets.cones.push(i); continue; }
      if (CORE[i]) buckets.tCore.push(i); else buckets.tWide[chunkOf(X[i], Z[i])].push(i);
      if (shape === 2) buckets.vases.push(i);
      else if (shape === 3) buckets.pyrs.push(i);
      else if (CORE[i]) buckets.core.push(i);
      else buckets.wide[chunkOf(X[i], Z[i])].push(i);
    }
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), cCan = new THREE.Color();
    const trunkScale = (dbh) => {
      const r = clamp(dbh * 0.0127, 0.06, 0.55) / 0.28;
      const h = clamp(2.4 + dbh * 0.1, 2.6, 5.2) / 3.6;
      return [r, h];
    };
    const canopyAt = (i, st) => {
      // crown base clears head height; center rises with the crown's own
      // vertical extent so puffs sit low and columns ride high
      const th = clamp(2.4 + DBH[i] * 0.1, 2.6, 5.2);
      return GY[i] + th * 0.75 + CR[i] * st[4] * 0.72;
    };
    const paint = (mesh, idx, canopy, full) => {
      for (let k = 0; k < idx.length; k++) {
        const i = idx[k];
        const g = NI[i] >= 0 ? (TREE_NAMES.g[NI[i]] || 0) : 0;
        const st = TREE_STYLE[g] || TREE_STYLE[0];
        q.setFromAxisAngle(_sup, hash01(i * 9.1) * Math.PI * 2);
        if (canopy) {
          const cy = canopyAt(i, st);
          m.compose(new V3(X[i], cy, Z[i]), q, new V3(CR[i] * st[3], CR[i] * st[4] * (0.9 + hash01(i * 7.7) * 0.25), CR[i] * st[3]));
          mesh.setMatrixAt(k, m);
          cCan.setHSL(st[0] + (hash01(i * 4.9) - 0.5) * 0.045, st[1] + (hash01(i * 6.1) - 0.5) * 0.12, st[2] + (hash01(i * 8.3) - 0.5) * 0.05);
          mesh.setColorAt(k, cCan);
        } else {
          const [rs, hs] = trunkScale(DBH[i]);
          const oT = frontOff(X[i], Z[i]);
          const capLift = (CORE[i] && oT > TERRAIN.trenchW - 1 && oT < TERRAIN.trenchE + 1) ? 0.82 : 0;
          m.compose(new V3(X[i], GY[i] + capLift, Z[i]), q, new V3(rs, hs, rs));
          mesh.setMatrixAt(k, m);
        }
      }
      mesh.instanceMatrix.needsUpdate = true;
      if (canopy && mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      mesh.castShadow = !!full;
      mesh.receiveShadow = false;
      groupCity.add(mesh);
    };
    // core: trunks + faceted canopies + two extra lobes each, with shadows
    if (buckets.tCore.length) paint(instMesh(trunkCoreG, trunkMat, buckets.tCore.length, coreCX, coreCZ, coreR), buckets.tCore, false, true);
    const ci = buckets.core;
    if (ci.length) {
      paint(instMesh(canCoreG, canMat, ci.length, coreCX, coreCZ, coreR), ci, true, true);
      const lumps = instMesh(canCoreG, canMat, ci.length * 2, coreCX, coreCZ, coreR);
      for (let k = 0; k < ci.length; k++) {
        const i = ci[k];
        const g = NI[i] >= 0 ? (TREE_NAMES.g[NI[i]] || 0) : 0;
        const st = TREE_STYLE[g] || TREE_STYLE[0];
        const cy = canopyAt(i, st);
        for (let l = 0; l < 2; l++) {
          const a = hash01(i * 3.3 + l * 17.1) * Math.PI * 2;
          const r = CR[i] * (0.45 + 0.25 * hash01(i * 4.1 + l));
          const ls = CR[i] * (0.5 + 0.25 * hash01(i * 6.3 + l * 5));
          m.compose(new V3(X[i] + Math.cos(a) * r, cy - CR[i] * 0.15 + hash01(i + l * 3) * CR[i] * 0.35, Z[i] + Math.sin(a) * r), q, new V3(ls, ls * 0.9, ls));
          lumps.setMatrixAt(k * 2 + l, m);
          cCan.setHSL(st[0] + (hash01(i * 4.9) - 0.5) * 0.04, st[1] - 0.06, st[2] + 0.05 + 0.02 * l);
          lumps.setColorAt(k * 2 + l, cCan);
        }
      }
      lumps.instanceMatrix.needsUpdate = true;
      if (lumps.instanceColor) lumps.instanceColor.needsUpdate = true;
      lumps.castShadow = true;
      groupCity.add(lumps);
    }
    // wide tier: one light trunk + canopy pair per chunk so whole chunks cull
    for (let c = 0; c < CHN * CHN; c++) {
      const ti = buckets.tWide[c];
      if (ti.length) paint(instMesh(trunkWideG, trunkMat, ti.length, chCX(c), chCZ(c), chR), ti, false, false);
      const wi = buckets.wide[c];
      if (wi.length) paint(instMesh(canWideG, canMat, wi.length, chCX(c), chCZ(c), chR), wi, true, false);
    }
    // species silhouettes, citywide: zelkova/elm vases and linden pyramids
    if (buckets.vases.length) paint(instMesh(vaseG, canMat, buckets.vases.length, (WB.x0 + WB.x1) / 2, (WB.z0 + WB.z1) / 2, wideR), buckets.vases, true, false);
    if (buckets.pyrs.length) paint(instMesh(pyrG, canMat, buckets.pyrs.length, (WB.x0 + WB.x1) / 2, (WB.z0 + WB.z1) / 2, wideR), buckets.pyrs, true, false);
    // conifers: cones straight from the ground, both tiers in one mesh
    const ki = buckets.cones;
    if (ki.length) {
      const cones = instMesh(coneG, canMat, ki.length, (WB.x0 + WB.x1) / 2, (WB.z0 + WB.z1) / 2, wideR);
      for (let k = 0; k < ki.length; k++) {
        const i = ki[k];
        const h = clamp(3 + DBH[i] * 0.25, 3.5, 14), r = clamp(0.8 + DBH[i] * 0.06, 1, 3.5);
        q.setFromAxisAngle(_sup, hash01(i * 9.1) * Math.PI * 2);
        m.compose(new V3(X[i], GY[i], Z[i]), q, new V3(r, h, r));
        cones.setMatrixAt(k, m);
        cCan.setHSL(0.34 + (hash01(i * 4.9) - 0.5) * 0.03, 0.35, 0.14 + (hash01(i * 8.3) - 0.5) * 0.04);
        cones.setColorAt(k, cCan);
      }
      cones.instanceMatrix.needsUpdate = true;
      if (cones.instanceColor) cones.instanceColor.needsUpdate = true;
      cones.castShadow = true;
      groupCity.add(cones);
    }
    console.log('planted', nInv, 'surveyed trees +', n - nInv, 'curated,',
      buckets.cones.length, 'conifers,', buckets.vases.length, 'vases,', buckets.pyrs.length, 'pyramids');
  });
  function plantProceduralTrees() {
    const spots = [];
    const minD2 = 6 * 6;
    function clear(x, z) {
      if (inWater(x, z) > -8) return false;
      if (nearBuildingEdge(x, z, 2.4)) return false;
      if (insideBuilding(x, z)) return false;
      if (nearRoad(x, z, 1.2)) return false;
      for (const [bx, bz, rx, rz, th] of bermSpots) {
        const dx = x - bx, dz = z - bz, cth = Math.cos(th), sth = Math.sin(th);
        const u = dx * cth - dz * sth, v = dx * sth + dz * cth;
        if ((u / rx) * (u / rx) + (v / rz) * (v / rz) < 1.25) return false;
      }
      for (let i = spots.length - 1; i >= 0 && i > spots.length - 40; i--) {
        const dx = spots[i][0] - x, dz = spots[i][1] - z;
        if (dx * dx + dz * dz < minD2) return false;
      }
      return true;
    }
    for (const r of D.roads) {
      if (!/residential|living_street|pedestrian|tertiary/.test(r.t)) continue;
      const off = r.w / 2 + 2.4;
      let acc = 0;
      for (let i = 0; i < r.pts.length - 1; i++) {
        const ax = r.pts[i][0], az = r.pts[i][1], bx = r.pts[i + 1][0], bz = r.pts[i + 1][1];
        const segL = Math.hypot(bx - ax, bz - az);
        if (segL < 0.5) continue;
        const ux = (bx - ax) / segL, uz = (bz - az) / segL;
        for (let d = acc; d < segL; d += 13) {
          const px = ax + ux * d, pz = az + uz * d;
          const j = (hash01(px * 0.37 + pz * 1.91) - 0.5) * 4;
          for (const sgn of [-1, 1]) {
            const x = px - uz * (off * sgn) + ux * j, z = pz + ux * (off * sgn) + uz * j;
            if (hash01(x * 3.1 + z * 0.7) < 0.55 && clear(x, z)) spots.push([x, z]);
          }
        }
        acc = 0;
      }
    }
    for (const a of D.areas || []) {
      if (a.kind !== 'park' || a.poly.length < 3) continue;
      let bx0 = 1e9, bx1 = -1e9, bz0 = 1e9, bz1 = -1e9;
      for (const p of a.poly) { bx0 = Math.min(bx0, p[0]); bx1 = Math.max(bx1, p[0]); bz0 = Math.min(bz0, p[1]); bz1 = Math.max(bz1, p[1]); }
      const n = Math.min(40, Math.floor(Math.abs(signedArea(a.poly)) / 220));
      for (let i = 0; i < n * 4 && spots.length < 1700; i++) {
        const x = lerp(bx0, bx1, hash01(i * 1.3 + bx0));
        const z = lerp(bz0, bz1, hash01(i * 2.7 + bz1));
        if (pointInPoly(x, z, a.poly) && clear(x, z)) spots.push([x, z]);
      }
    }
    for (const t of D.trees || []) if (clear(t[0], t[1])) spots.push([t[0], t[1]]);
    // mature trees around the towers' lawns
    for (let i = 0; i < 90 && spots.length < 2300; i++) {
      const ang = hash01(i * 1.9 + 2) * Math.PI * 2, rr = PLAZA_R + 6 + hash01(i * 3.7) * 50;
      const x = towersCenter.x + Math.cos(ang) * rr, z = towersCenter.z + Math.sin(ang) * rr;
      if (clear(x, z)) spots.push([x, z]);
    }
    for (const sp of poolTreeSpots) if (clear(sp[0], sp[1]) && spots.length < 2400) spots.push(sp);
    for (const sp of extraTreeSpots) if (spots.length < 2400) spots.push(sp);

    const N = Math.min(spots.length, 2400);
    if (!N) return;
    const trunkG = new THREE.CylinderGeometry(0.17, 0.28, 3.6, 6);
    trunkG.translate(0, 1.0, 0);   // extends 0.8 m below grade so raised layers never slice the base
    const canG = new THREE.IcosahedronGeometry(1, 1);
    const trunks = new THREE.InstancedMesh(trunkG, new THREE.MeshStandardMaterial({ color: COLORS.trunk, roughness: 1 }), N);
    const cans = new THREE.InstancedMesh(canG, new THREE.MeshStandardMaterial({ roughness: 0.95 }), N);
    const m = new THREE.Matrix4();
    const q = new THREE.Quaternion();
    const cCan = new THREE.Color();
    for (let i = 0; i < N; i++) {
      const [x, z] = spots[i];
      const s = 2.1 + hash01(i * 5.77) * 1.5;
      q.setFromAxisAngle(new V3(0, 1, 0), hash01(i * 9.1) * Math.PI * 2);
      const ty = siteY(x, z, 'ground');
      // over the trench cap decks the below-grade extension would dangle into the
      // I-95 tunnel — lift those trunks so their base sits at the deck surface
      const oT = frontOff(x, z);
      const capLift = (oT > TERRAIN.trenchW - 1 && oT < TERRAIN.trenchE + 1) ? 0.82 : 0;
      m.compose(new V3(x, ty + capLift, z), q, new V3(1, 0.9 + hash01(i * 2.3) * 0.35, 1));
      trunks.setMatrixAt(i, m);
      m.compose(new V3(x, ty + 2.6 + s * 0.72, z), q, new V3(s, s * (0.92 + hash01(i * 7.7) * 0.3), s));
      cans.setMatrixAt(i, m);
      cCan.setHSL(0.26 + hash01(i * 4.9) * 0.05, 0.46 + hash01(i * 6.1) * 0.14, 0.17 + hash01(i * 8.3) * 0.06);
      cans.setColorAt(i, cCan);
    }
    // secondary lobes make the canopies read as foliage rather than balloons
    const lumps = new THREE.InstancedMesh(canG, cans.material, N * 2);
    for (let i = 0; i < N; i++) {
      const [x, z] = spots[i];
      const s = 2.1 + hash01(i * 5.77) * 1.5;
      const baseY = siteY(x, z, 'ground') + 2.6 + s * 0.72;
      for (let k = 0; k < 2; k++) {
        const a = hash01(i * 3.3 + k * 17.1) * Math.PI * 2;
        const r = s * (0.45 + 0.25 * hash01(i * 4.1 + k));
        const ls = s * (0.55 + 0.25 * hash01(i * 6.3 + k * 5));
        m.compose(new V3(x + Math.cos(a) * r, baseY - s * 0.15 + hash01(i + k * 3) * s * 0.4, z + Math.sin(a) * r), q, new V3(ls, ls * 0.9, ls));
        lumps.setMatrixAt(i * 2 + k, m);
        cCan.setHSL(0.26 + hash01(i * 4.9) * 0.045, 0.38 + hash01(i * 6.1) * 0.12, 0.24 + hash01(i * 8.3) * 0.07 + 0.02 * k);
        lumps.setColorAt(i * 2 + k, cCan);
      }
    }
    trunks.castShadow = true;
    cans.castShadow = true;
    lumps.castShadow = true;
    groupCity.add(trunks, cans, lumps);
  }

  // ---------------------------------------------------------------- labels
  const labels = [];
  step('Lettering the landmarks', () => {
    function addLabel(text, x, y, z, cls) {
      const el = document.createElement('div');
      el.className = 'lbl' + (cls ? ' ' + cls : '');
      el.textContent = text;
      labelsRoot.appendChild(el);
      labels.push({ el, pos: new V3(x, y + siteY(x, z, 'ground'), z), visible: false });
    }
    const wanted = [
      ["Saint Peter's Church", "St. Peter's Church"],
      ['Old Pine Street Church', 'Old Pine Street Church'],
      ["Merchants' Exchange", "Merchants' Exchange"],
      ['Head House', 'Head House Square'],
      ['Mother Bethel', 'Mother Bethel A.M.E.'],
      ['Hopkinson House', 'Hopkinson House'],
      ['Society Hill Synagogue', 'Society Hill Synagogue'],
      ['Old Saint Mary', "Old St. Mary's"],
      ['City Tavern', 'City Tavern'],
      ['Hill-Physick', 'Physick House'],
      ['Athenaeum', 'Athenaeum'],
      ['Residences at Dockside', 'Dockside'],
      ['One Independence Place', 'Independence Place'],
      ['The Ryland', 'The Ryland, 1 Dock Street'],
      ['Philadelphia Marriott Old City', 'Marriott Old City'],
      ['Independence Seaport Museum', 'Seaport Museum'],
    ];
    for (const [pat, text] of wanted) {
      const b = findBuilding(pat);
      if (!b) continue;
      const [cx, cz] = polyCentroid(b.poly);
      let h = b.h + 7;
      const lm = META_L.find(l => l.name && l.name.toLowerCase().includes(pat.toLowerCase().slice(0, 8)));
      if (lm && lm.spire_height_m) h = Math.max(h, lm.spire_height_m + 6);
      addLabel(text, cx, h, cz);
    }
    // (the towers carried address labels here; removed at Mike's request)
    const riv = waterPoint(0, 210);
    addLabel('Delaware River', riv[0], 12, riv[1], '');
    const pl = waterPoint(-230, -45);
    addLabel("Penn's Landing", pl[0], 10, pl[1], '');
  });

  let labelsOn = false;   // landmark tags start hidden; Aa button / L key turn them on
  const tmpV = new V3();
  function updateLabels() {
    const w = window.innerWidth, h = window.innerHeight;
    for (const l of labels) {
      if (!labelsOn) { if (l.visible) { l.el.style.opacity = '0'; l.visible = false; } continue; }
      tmpV.copy(l.pos).project(camera);
      const dist = camera.position.distanceTo(l.pos);
      const behind = tmpV.z > 1 || tmpV.z < -1;
      const off = tmpV.x < -1.05 || tmpV.x > 1.05 || tmpV.y < -1.1 || tmpV.y > 1.1;
      const f0 = l.far ? 2200 : LABEL_FADE[0], f1 = l.far ? 3400 : LABEL_FADE[1];
      let op = 1 - clamp((dist - f0) / (f1 - f0), 0, 1);
      if (dist < 26) op = Math.min(op, (dist - 12) / 14);
      if (behind || off || op <= 0.02) {
        if (l.visible) { l.el.style.opacity = '0'; l.visible = false; }
        continue;
      }
      const x = (tmpV.x * 0.5 + 0.5) * w, y = (-tmpV.y * 0.5 + 0.5) * h;
      l.el.style.transform = 'translate(-50%,-100%) translate(' + x.toFixed(1) + 'px,' + y.toFixed(1) + 'px)';
      l.el.style.opacity = op.toFixed(2);
      l.visible = true;
    }
  }

  // ---------------------------------------------------------------- controls
  const MODE = { ORBIT: 0, WALK: 1, FLY: 2 };
  let mode = MODE.ORBIT;
  let introSpin = false; // begins when the veil lifts, ends at first interaction

  const orbit = {
    // intro: glide in from high in the east, settling on City Hall with the
    // tower and Penn front-lit against the Center City skyline
    target: new V3(-1603, 78, -802), goalTarget: new V3(-1603, 78, -802),
    r: 3200, goalR: 700,
    theta: -0.38, goalTheta: 0.52, // azimuth on xz: 0 = +x (east)
    phi: 1.32, goalPhi: 1.22,      // polar from +y
  };
  const walk = {
    pos: new V3(0, 1.7, 0),
    yaw: 0, pitch: 0,
    vel: new V3(),
    keys: {},
    locked: false,
    dragLook: false,
  };
  // fly mode shares walk's look state (yaw/pitch/keys) but moves freely in 3D
  const fly = { pos: new V3(0, 260, 420), vel: new V3(), speed: 90 };

  function applyOrbit(dt) {
    const k = 1 - Math.exp(-dt * 5.2);
    orbit.r = lerp(orbit.r, orbit.goalR, k);
    orbit.theta = lerp(orbit.theta, orbit.goalTheta, k);
    orbit.phi = lerp(orbit.phi, orbit.goalPhi, k);
    orbit.target.lerp(orbit.goalTarget, k);
    const sp = Math.sin(orbit.phi), cp = Math.cos(orbit.phi);
    camera.position.set(
      orbit.target.x + orbit.r * sp * Math.cos(orbit.theta),
      orbit.target.y + orbit.r * cp,
      orbit.target.z + orbit.r * sp * Math.sin(orbit.theta)
    );
    camera.lookAt(orbit.target);
  }

  const _wf = new V3(), _wr = new V3(), _wish = new V3(), _wtmp = new V3();
  function applyWalk(dt) {
    const speed = walk.keys['shift'] ? 9.5 : 3.6;
    const f = _wf.set(Math.sin(walk.yaw), 0, -Math.cos(walk.yaw));  // yaw 0 -> north (-z)
    const r = _wr.set(-f.z, 0, f.x);
    const wish = _wish.set(0, 0, 0);
    if (walk.keys['w'] || walk.keys['arrowup']) wish.add(f);
    if (walk.keys['s'] || walk.keys['arrowdown']) wish.sub(f);
    if (walk.keys['d'] || walk.keys['arrowright']) wish.add(r);
    if (walk.keys['a'] || walk.keys['arrowleft']) wish.sub(r);
    if (joy.active) { wish.add(_wtmp.copy(f).multiplyScalar(-joy.y)).add(_wtmp.copy(r).multiplyScalar(joy.x)); }
    if (wish.lengthSq() > 0) {
      wish.normalize().multiplyScalar(speed);
      walk.vel.x = lerp(walk.vel.x, wish.x, 1 - Math.exp(-dt * 9));
      walk.vel.z = lerp(walk.vel.z, wish.z, 1 - Math.exp(-dt * 9));
    } else {
      const d = Math.exp(-dt * 8);
      walk.vel.x *= d; walk.vel.z *= d;
    }
    let nx = walk.pos.x + walk.vel.x * dt;
    let nz = walk.pos.z + walk.vel.z * dt;
    // collide with building edges: push out
    for (let iter = 0; iter < 2; iter++) {
      const gx = Math.floor(nx / COL_CELL), gz = Math.floor(nz / COL_CELL);
      for (let ix = gx - 1; ix <= gx + 1; ix++) for (let iz = gz - 1; iz <= gz + 1; iz++) {
        const a = colGrid.get(colKey(ix, iz));
        if (!a) continue;
        for (const s of a) {
          const ax = colSegs[s], az = colSegs[s + 1], bx = colSegs[s + 2], bz = colSegs[s + 3];
          const dx = bx - ax, dz = bz - az;
          const L2 = dx * dx + dz * dz;
          let t = L2 > 0 ? ((nx - ax) * dx + (nz - az) * dz) / L2 : 0;
          t = clamp(t, 0, 1);
          const px = nx - (ax + dx * t), pz = nz - (az + dz * t);
          const d2 = px * px + pz * pz;
          const R = 0.55;
          if (d2 < R * R && d2 > 1e-9) {
            const d = Math.sqrt(d2);
            nx += (px / d) * (R - d);
            nz += (pz / d) * (R - d);
          }
        }
      }
    }
    const wd = inWater(nx, nz);
    if (wd > -2) nx -= (wd + 2);
    nx = clamp(nx, bounds.minX - 60, bounds.maxX + 200);
    nz = clamp(nz, bounds.minZ - 60, bounds.maxZ + 60);
    walk.pos.x = nx; walk.pos.z = nz;
    walk.pos.y = walkY(nx, nz) + 1.7;
    camera.position.copy(walk.pos);
    const cp = Math.cos(walk.pitch);
    camera.lookAt(
      walk.pos.x + Math.sin(walk.yaw) * cp,
      walk.pos.y + Math.sin(walk.pitch),
      walk.pos.z - Math.cos(walk.yaw) * cp
    );
  }

  function applyFly(dt) {
    const boost = walk.keys['shift'] ? 3.2 : 1;
    const cp0 = Math.cos(walk.pitch);
    const f = _wf.set(Math.sin(walk.yaw) * cp0, Math.sin(walk.pitch), -Math.cos(walk.yaw) * cp0);
    const r = _wr.set(Math.cos(walk.yaw), 0, Math.sin(walk.yaw));
    const wish = _wish.set(0, 0, 0);
    if (walk.keys['w'] || walk.keys['arrowup']) wish.add(f);
    if (walk.keys['s'] || walk.keys['arrowdown']) wish.sub(f);
    if (walk.keys['d'] || walk.keys['arrowright']) wish.add(r);
    if (walk.keys['a'] || walk.keys['arrowleft']) wish.sub(r);
    if (walk.keys['e'] || walk.keys[' '] || flyTouch.up) wish.y += 1;
    if (walk.keys['q'] || walk.keys['c'] || flyTouch.down) wish.y -= 1;
    if (joy.active) wish.add(_wtmp.copy(f).multiplyScalar(-joy.y)).add(_wtmp.copy(r).multiplyScalar(joy.x));
    if (wish.lengthSq() > 0) {
      // on touch the stick doubles as the throttle: past the ring it pushes to
      // ~2.4x cruise, so mobile can actually cross the city (no scroll wheel)
      const jm = joy.active ? Math.max(0.3, Math.min(2.4, Math.hypot(joy.x, joy.y))) : 1;
      wish.normalize().multiplyScalar(fly.speed * boost * jm);
      fly.vel.lerp(wish, 1 - Math.exp(-dt * 6));
    } else {
      fly.vel.multiplyScalar(Math.exp(-dt * 5));
    }
    fly.pos.addScaledVector(fly.vel, dt);
    fly.pos.x = clamp(fly.pos.x, bounds.minX - 400, bounds.maxX + 600);
    fly.pos.z = clamp(fly.pos.z, bounds.minZ - 400, bounds.maxZ + 400);
    const floorY = Math.max(siteY(fly.pos.x, fly.pos.z, 'ground') + 2.5, TERRAIN.water + 2);
    fly.pos.y = clamp(fly.pos.y, floorY, 1600);
    camera.position.copy(fly.pos);
    const cp = Math.cos(walk.pitch);
    camera.lookAt(
      fly.pos.x + Math.sin(walk.yaw) * cp,
      fly.pos.y + Math.sin(walk.pitch),
      fly.pos.z - Math.cos(walk.yaw) * cp
    );
  }

  // pointer / touch input
  let dragging = false, dragBtn = 0, lastX = 0, lastY = 0, interacted = false, touchArmed = false;
  const joy = { active: false, id: -1, ox: 0, oy: 0, x: 0, y: 0 };
  const lookTouch = { id: -1, x: 0, y: 0 };
  const pinch = { d: 0, x: 0, y: 0 };

  canvas.addEventListener('pointerdown', (e) => {
    if (e.pointerType === 'touch') return; // touch handled separately
    interacted = true; introSpin = false;
    if (mode === MODE.WALK || mode === MODE.FLY) {
      // always start a drag so looking works even where pointer lock is
      // unavailable (sandboxed iframes) or on cooldown; lock upgrades it
      dragging = true; lastX = e.clientX; lastY = e.clientY;
      canvas.setPointerCapture(e.pointerId);
      if (!walk.locked) requestLock();
      return;
    }
    dragging = true; dragBtn = e.button;
    lastX = e.clientX; lastY = e.clientY;
    canvas.setPointerCapture(e.pointerId);
  });
  window.addEventListener('pointermove', (e) => {
    if (e.pointerType === 'touch') return;
    if (mode === MODE.WALK || mode === MODE.FLY) {
      if (walk.locked) return; // movementX path
      if (dragging) {
        walk.yaw += (e.clientX - lastX) * 0.0032;
        walk.pitch = clamp(walk.pitch - (e.clientY - lastY) * 0.0032, -1.45, 1.45);
        lastX = e.clientX; lastY = e.clientY;
      }
      return;
    }
    if (!dragging) return;
    const dx = e.clientX - lastX, dy = e.clientY - lastY;
    lastX = e.clientX; lastY = e.clientY;
    if (dragBtn === 2 || dragBtn === 1 || e.shiftKey) {
      panOrbit(dx, dy);
    } else {
      orbit.goalTheta += dx * 0.0052;
      orbit.goalPhi = clamp(orbit.goalPhi - dy * 0.0042, 0.06, 1.52);
    }
  });
  window.addEventListener('pointerup', () => { dragging = false; });
  canvas.addEventListener('contextmenu', (e) => e.preventDefault());
  canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    interacted = true; introSpin = false;
    if (mode === MODE.FLY) { fly.speed = clamp(fly.speed * Math.exp(-e.deltaY * 0.0012), 10, 500); return; }
    if (mode !== MODE.ORBIT) return;
    orbit.goalR = clamp(orbit.goalR * Math.exp(e.deltaY * 0.0011), 14, 2800);
  }, { passive: false });

  function panOrbit(dx, dy) {
    const s = orbit.goalR * 0.0012;
    const fx = Math.cos(orbit.theta), fz = Math.sin(orbit.theta);
    // grab-style pan: the world follows the cursor.
    // ground-projected screen axes: right = (fz, -fx), up = (-fx, -fz)
    orbit.goalTarget.x += (-fz * dx - fx * dy) * s;
    orbit.goalTarget.z += (fx * dx - fz * dy) * s;
    orbit.goalTarget.x = clamp(orbit.goalTarget.x, bounds.minX - 200, bounds.maxX + 400);
    orbit.goalTarget.z = clamp(orbit.goalTarget.z, bounds.minZ - 200, bounds.maxZ + 200);
  }

  canvas.addEventListener('dblclick', (e) => {
    if (mode !== MODE.ORBIT) return;
    const ray = new THREE.Raycaster();
    ray.setFromCamera(new THREE.Vector2(
      (e.clientX / window.innerWidth) * 2 - 1,
      -(e.clientY / window.innerHeight) * 2 + 1
    ), camera);
    const hits = ray.intersectObjects(rayTargets, false);
    if (hits.length) {
      const p = hits[0].point;
      orbit.goalTarget.set(p.x, Math.max(4, Math.min(p.y, 60)), p.z);
      orbit.goalR = Math.max(60, orbit.goalR * 0.55);
    }
  });

  // touch
  canvas.addEventListener('touchstart', (e) => {
    interacted = true; introSpin = false;
    if (mode === MODE.WALK || mode === MODE.FLY) {
      for (const t of e.changedTouches) {
        if (t.clientX < window.innerWidth / 2 && !joy.active) {
          joy.active = true; joy.id = t.identifier; joy.ox = t.clientX; joy.oy = t.clientY; joy.x = joy.y = 0;
          stick.style.display = 'block';
          stick.style.left = (t.clientX - 54) + 'px';
          stick.style.top = (t.clientY - 54) + 'px';
        } else if (lookTouch.id === -1) {
          lookTouch.id = t.identifier; lookTouch.x = t.clientX; lookTouch.y = t.clientY;
        }
      }
      e.preventDefault();
      return;
    }
    if (e.touches.length === 1) {
      const t = e.touches[0];
      lastX = t.clientX; lastY = t.clientY; touchArmed = true;
    } else if (e.touches.length === 2) {
      const [a, b] = e.touches;
      pinch.d = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
      pinch.x = (a.clientX + b.clientX) / 2; pinch.y = (a.clientY + b.clientY) / 2;
    }
    e.preventDefault();
  }, { passive: false });
  canvas.addEventListener('touchmove', (e) => {
    if (mode === MODE.WALK || mode === MODE.FLY) {
      for (const t of e.changedTouches) {
        if (t.identifier === joy.id) {
          const dx = t.clientX - joy.ox, dy = t.clientY - joy.oy;
          // magnitude runs past the ring to 2.4 — fly reads it as a throttle;
          // walk normalizes the vector so its speed is unaffected
          const m = Math.min(2.4, Math.hypot(dx, dy) / 44);
          const a = Math.atan2(dy, dx);
          joy.x = Math.cos(a) * m; joy.y = Math.sin(a) * m;
          const vis = Math.min(1, m);
          stickNub.style.transform = 'translate(' + (Math.cos(a) * vis * 30) + 'px,' + (Math.sin(a) * vis * 30) + 'px)';
        } else if (t.identifier === lookTouch.id) {
          walk.yaw += (t.clientX - lookTouch.x) * 0.0042;
          walk.pitch = clamp(walk.pitch - (t.clientY - lookTouch.y) * 0.0042, -1.45, 1.45);
          lookTouch.x = t.clientX; lookTouch.y = t.clientY;
        }
      }
      e.preventDefault();
      return;
    }
    if (e.touches.length === 1) {
      const t = e.touches[0];
      if (!touchArmed) { touchArmed = true; lastX = t.clientX; lastY = t.clientY; return; }
      orbit.goalTheta += (t.clientX - lastX) * 0.006;
      orbit.goalPhi = clamp(orbit.goalPhi - (t.clientY - lastY) * 0.005, 0.06, 1.52);
      lastX = t.clientX; lastY = t.clientY;
    } else if (e.touches.length === 2) {
      const [a, b] = e.touches;
      const d = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
      if (pinch.d > 0) orbit.goalR = clamp(orbit.goalR * (pinch.d / d), 14, 2800);
      const cx = (a.clientX + b.clientX) / 2, cy = (a.clientY + b.clientY) / 2;
      panOrbit(cx - pinch.x, cy - pinch.y);
      pinch.d = d; pinch.x = cx; pinch.y = cy;
    }
    e.preventDefault();
  }, { passive: false });
  function onTouchEnd(e) {
    for (const t of e.changedTouches) {
      if (t.identifier === joy.id) { joy.active = false; joy.id = -1; joy.x = joy.y = 0; stick.style.display = 'none'; stickNub.style.transform = ''; }
      if (t.identifier === lookTouch.id) lookTouch.id = -1;
    }
    if (e.touches.length < 2) pinch.d = 0;
    if (e.touches.length === 1) { lastX = e.touches[0].clientX; lastY = e.touches[0].clientY; }
  }
  canvas.addEventListener('touchend', onTouchEnd);
  canvas.addEventListener('touchcancel', onTouchEnd);

  // pointer lock (dragLook only informs the hint text; dragging always works)
  function requestLock() {
    try {
      const p = canvas.requestPointerLock && canvas.requestPointerLock();
      if (p && p.catch) p.catch(() => { walk.dragLook = true; setHint(); });
    } catch (e) { walk.dragLook = true; setHint(); }
  }
  document.addEventListener('pointerlockchange', () => {
    walk.locked = document.pointerLockElement === canvas;
    if (walk.locked) walk.dragLook = false;
    setHint();
  });
  document.addEventListener('pointerlockerror', () => { walk.dragLook = true; setHint(); });
  document.addEventListener('mousemove', (e) => {
    if (!walk.locked || (mode !== MODE.WALK && mode !== MODE.FLY)) return;
    walk.yaw += e.movementX * 0.0021;
    walk.pitch = clamp(walk.pitch - e.movementY * 0.0021, -1.45, 1.45);
  });

  window.addEventListener('keydown', (e) => {
    const k = e.key.toLowerCase();
    if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'BUTTON')) return;
    if (!veil.classList.contains('hidden')) return;      // no shortcuts under the intro veil
    if (about.classList.contains('open')) {              // panel gets the keyboard while open
      if (k === 'escape' || k === 'i') closeAbout();
      return;
    }
    if (k === '1') setMode(MODE.ORBIT);
    else if (k === '2') setMode(MODE.WALK);
    else if (k === '3') setMode(MODE.FLY);
    else if (k === 'l') toggleLabels();
    else if (k === 't') toggleTimePanel();
    else if (k === 'v') toggleTransit();
    else if (k === 'n') toggleStreets();
    else if (k === 'f') toggleLayers();
    else if (k === 'b') toggleIndego();
    else if (k === 'x') toggleFlights();
    else if (k === 'h') toggleShips();
    else if (k === 'p') togglePlaces();
    else if (k === '/') { if (septaCanFetch) { toggleSearch(true); e.preventDefault(); } }
    else if (k === 'escape') { /* browser releases pointer lock */ }
    else walk.keys[k] = true;
    if (['w', 'a', 's', 'd', ' ', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(k)) e.preventDefault();
  });
  window.addEventListener('keyup', (e) => { walk.keys[e.key.toLowerCase()] = false; });
  window.addEventListener('blur', () => { walk.keys = {}; dragging = false; });

  // ---------------------------------------------------------------- modes & viewpoints
  const btnOrbit = document.getElementById('btnOrbit');
  const btnWalk = document.getElementById('btnWalk');
  const btnFly = document.getElementById('btnFly');
  const flyCtl = document.getElementById('flyctl');
  const flyTouch = { up: false, down: false };
  function setHint() {
    if (mode === MODE.ORBIT) {
      hintEl.textContent = isTouch
        ? 'Drag to orbit. Pinch to zoom.'
        : 'Drag to orbit. Scroll to zoom. Double-click to focus.';
    } else if (mode === MODE.FLY) {
      if (isTouch) hintEl.textContent = 'Left thumb flies, push farther for faster. Right thumb looks. ▲▼ climb.';
      else if (walk.locked || walk.dragLook) hintEl.textContent = 'WASD to fly. E and Q for up and down. Shift to boost. Scroll sets speed.';
      else hintEl.textContent = 'Click the scene to take the controls';
    } else {
      if (isTouch) hintEl.textContent = 'Left thumb to move. Right thumb to look.';
      else if (walk.locked) hintEl.textContent = 'WASD to move. Shift to run. Esc releases the mouse.';
      else if (walk.dragLook) hintEl.textContent = 'WASD to move. Drag to look. Shift to run.';
      else hintEl.textContent = 'Click the scene to take the controls';
    }
  }
  function setMode(m) {
    if (m === mode) return;
    const prev = mode;
    mode = m;
    introSpin = false;
    if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
    // drop any in-flight gesture so the new mode doesn't read stale coordinates
    dragging = false; touchArmed = false; pinch.d = 0;
    joy.active = false; joy.id = -1; joy.x = joy.y = 0; lookTouch.id = -1;
    stick.style.display = 'none'; stickNub.style.transform = '';
    btnOrbit.classList.toggle('active', m === MODE.ORBIT);
    btnWalk.classList.toggle('active', m === MODE.WALK);
    btnFly.classList.toggle('active', m === MODE.FLY);
    crosshair.style.display = (m === MODE.WALK || m === MODE.FLY) && !isTouch ? 'block' : 'none';
    flyCtl.classList.toggle('show', m === MODE.FLY && isTouch);
    flyTouch.up = flyTouch.down = false;
    if (m === MODE.WALK) {
      // drop to the ground near where the camera was looking, default to the plaza
      const t = prev === MODE.FLY ? fly.pos : orbit.target;
      let px = clamp(t.x, bounds.minX, bounds.maxX), pz = clamp(t.z, bounds.minZ, bounds.maxZ);
      const wd = inWater(px, pz);
      if (wd > -10) px -= (wd + 10);
      if (!walkSpawned) {
        walk.pos.set(towersCenter.x - 8, 1.7, towersCenter.z + 16);
        walk.yaw = Math.atan2(towersCenter.x + 9 - walk.pos.x, -(towersCenter.z - 41 - walk.pos.z));
        walk.pitch = 0.32;
        walkSpawned = true;
      } else if (Math.hypot(px - walk.pos.x, pz - walk.pos.z) > 220) {
        walk.pos.set(px, 1.7, pz);
      }
      if (!isTouch) requestLock();
    } else if (m === MODE.FLY) {
      // take off from the current camera pose
      camera.getWorldDirection(tmpV);
      walk.yaw = Math.atan2(tmpV.x, -tmpV.z);
      walk.pitch = clamp(Math.asin(clamp(tmpV.y, -1, 1)), -1.45, 1.45);
      fly.pos.copy(camera.position);
      fly.pos.x = clamp(fly.pos.x, bounds.minX - 400, bounds.maxX + 600);
      fly.pos.z = clamp(fly.pos.z, bounds.minZ - 400, bounds.maxZ + 400);
      fly.pos.y = clamp(Math.max(fly.pos.y, siteY(fly.pos.x, fly.pos.z, 'ground') + (prev === MODE.WALK ? 35 : 6)), TERRAIN.water + 2, 1600);
      fly.vel.set(0, 0, 0);
      if (!isTouch) requestLock();
    } else {
      if (walk.locked && document.exitPointerLock) document.exitPointerLock();
      const p = prev === MODE.FLY ? fly.pos : walk.pos;
      orbit.goalTarget.set(p.x, prev === MODE.FLY ? Math.max(20, p.y - 120) : 20, p.z);
      orbit.goalR = Math.max(orbit.goalR, 180);
    }
    setHint();
  }
  let walkSpawned = false;
  btnOrbit.addEventListener('click', () => setMode(MODE.ORBIT));
  btnWalk.addEventListener('click', () => setMode(MODE.WALK));
  // on touch the first Fly tap shows the control tips; Okay proceeds into fly mode
  const flyTips = document.getElementById('flytips');
  let flyTipsSeen = false;
  btnFly.addEventListener('click', () => {
    if (isTouch && !flyTipsSeen && flyTips) { flyTips.classList.add('show'); return; }
    setMode(MODE.FLY);
  });
  if (flyTips) document.getElementById('flyTipsOk').addEventListener('click', () => {
    flyTipsSeen = true;
    flyTips.classList.remove('show');
    setMode(MODE.FLY);
  });
  // touch fly: hold ▲/▼ to climb and descend (E/Q have no finger equivalent)
  for (const [bid, key] of [['flyUp', 'up'], ['flyDown', 'down']]) {
    const b = document.getElementById(bid);
    const on = (e) => { flyTouch[key] = true; interacted = true; e.preventDefault(); };
    const off = () => { flyTouch[key] = false; };
    b.addEventListener('touchstart', on, { passive: false });
    b.addEventListener('touchend', off);
    b.addEventListener('touchcancel', off);
    b.addEventListener('mousedown', on);
    b.addEventListener('mouseup', off);
    b.addEventListener('mouseleave', off);
  }

  const viewpoints = [];
  function addViewpoint(name, fn) { viewpoints.push({ name, fn }); }
  // ---------------------------------------------------------------- live SEPTA transit
  // Real-time vehicles from SEPTA's public API. Neither api.septa.org nor www3 sends
  // CORS headers, but both honor JSONP (?callback=), so each poll is a short-lived
  // <script> tag — live on GitHub Pages / localhost; under the artifact CSP the tags
  // never load and the layer stays silently empty. STREET VEHICLES ONLY by Mike's
  // request (buses + the bus-like street trolleys): rail is skipped — the subway
  // rows (L1/B1–B3) are schedule placeholders with no real fix anyway, and the
  // Regional Rail / NHSL layer was removed 2026-08-25 ("mostly underground and
  // not easy to track"). TrainView is no longer polled.
  const SEPTA_GEO = { lat0: 39.945473644755005, lon0: -75.14474803850973 };  // scene.json origin
  SEPTA_GEO.mx = 111320 * Math.cos(SEPTA_GEO.lat0 * Math.PI / 180); SEPTA_GEO.mz = 110574;
  const SEPTA = { on: true, ok: false, fails: 0, hinted: false };
  const SEPTA_HOSTS = ['https://api.septa.org/api', 'https://www3.septa.org/api'];
  const SEPTA_POLL = isTouch ? 25000 : 15000;          // TransitViewAll is ~370 KB a pull
  const SEPTA_BOX = { la0: 39.855, la1: 40.145, lo0: -75.30, lo1: -74.94 };  // modeled city
  const septaCanFetch = !/claude|usercontent/i.test(location.hostname);
  const septaVeh = new Map();
  const SEPTA_KIND = {                                  // stored dark for the legacy-color lift
    bus: { l: 12.2, w: 2.6, h: 3.1, c: 0x7e858a },
    trolley: { l: 15.3, w: 2.6, h: 3.4, c: 0x2e7448 },
  };
  const SEPTA_TINT = { G1: 0x8a7f2f, D1: 0x7c4767, D2: 0x7c4767 };  // Girard gold, Delco violet
  let septaCbN = 0, septaHost = 0, septaSolid = null, septaPin = null, septaBadge = null, septaReady = false, septaHintT = 0;
  const septaMats = {};
  const septaPickS = [], septaPickP = [], septaPickB = [];
  const btnTransit = document.getElementById('btnTransit');
  const vehinfoEl = document.getElementById('vehinfo');
  const vehinfoBody = document.getElementById('vehinfoBody');
  let pickedVeh = null;
  const septaEsc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  function septaKindOf(r) {
    // rail is out by request (and the subway rows carry no real GPS anyway):
    // only street vehicles — buses and the bus-like street trolleys — render
    if (r === 'L1' || r === 'B1' || r === 'B2' || r === 'B3' || r === 'M1') return null;
    if (/^[TGD]\d$/.test(r)) return 'trolley';
    return 'bus';
  }
  function septaRouteLabel(r) {
    if (r === 'M1_BUS') return 'M1';
    if (r === 'BLVDDIR') return 'BLVD';
    if (r.indexOf('LUCY') === 0) return 'LUCY';
    return r;
  }
  // Approximate underground zone: T-trolleys inside the subway–surface tunnel
  // (40th St portals → 13th) simply aren't drawn — no vehicles under buildings.
  function septaUnder(kind, route, lat, lon) {
    if (kind === 'trolley' && route.charCodeAt(0) === 84)
      return lon > -75.2045 && lon < -75.158 && lat > 39.9465 && lat < 39.9575;
    return false;
  }
  function septaYawFromCompass(deg) {
    const r = deg * Math.PI / 180;
    return Math.atan2(Math.cos(r), Math.sin(r));   // x = east, z = south, rotY 0 = +x
  }
  function septaJsonp(path, cb) {
    let done = false, timer = 0;
    const name = '__septaCb' + (septaCbN++);
    const script = document.createElement('script');
    const fin = (data) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      try { delete window[name]; } catch (e) { window[name] = undefined; }
      if (script.parentNode) script.parentNode.removeChild(script);
      cb(data);
    };
    window[name] = fin;
    script.async = true;
    script.onerror = () => fin(null);
    timer = setTimeout(() => fin(null), 18000);
    script.src = SEPTA_HOSTS[septaHost] + path + '?callback=' + name;
    document.head.appendChild(script);
  }
  function septaUpsert(id, kind, route, lat, lon, apiHdg, info) {
    const x = (lon - SEPTA_GEO.lon0) * SEPTA_GEO.mx, z = -(lat - SEPTA_GEO.lat0) * SEPTA_GEO.mz;
    const under = septaUnder(kind, route, lat, lon);
    const now = performance.now();
    let v = septaVeh.get(id);
    if (!v) {
      v = { id, kind, route, routeLabel: septaRouteLabel(route), tint: SEPTA_TINT[route] || SEPTA_KIND[kind].c,
            info, fx: x, fz: z, tx: x, tz: z, x, z, t0: 0, yaw: 0, yawT: 0, ug: under, lastSeen: now };
      const c = new THREE.Color(v.tint);
      c.r = Math.min(1, c.r * 1.9 + 0.18); c.g = Math.min(1, c.g * 1.9 + 0.18); c.b = Math.min(1, c.b * 1.9 + 0.18);
      v.tintHex = '#' + c.getHexString();
      v.bobP = ((id.charCodeAt(id.length - 1) || 0) * 37 + id.length * 91) % 63 / 10;
      if (apiHdg) v.yaw = v.yawT = septaYawFromCompass(apiHdg);
      septaVeh.set(id, v);
      return;
    }
    v.fx = v.x; v.fz = v.z;
    v.tx = x; v.tz = z; v.t0 = now;
    const mdx = x - v.fx, mdz = z - v.fz, moved = Math.hypot(mdx, mdz);
    if (moved > 420) { v.fx = x; v.fz = z; v.x = x; v.z = z; }   // data jump — snap, don't sprint
    if (apiHdg) v.yawT = septaYawFromCompass(apiHdg);
    else if (moved > 6) v.yawT = Math.atan2(-mdz, mdx);          // derive heading from motion
    v.ug = under; v.info = info; v.lastSeen = now;
  }
  function septaFeedFail() {
    SEPTA.fails++;
    if (SEPTA.fails >= 3) { septaHost = 1 - septaHost; SEPTA.fails = 0; }
  }
  function septaGotTV(d) {
    let routes = d && d.routes;
    if (Array.isArray(routes)) routes = routes[0];
    if (!routes || typeof routes !== 'object') { septaFeedFail(); return; }
    const nowS = Date.now() / 1000;
    for (const rid in routes) {
      const list = routes[rid];
      if (!Array.isArray(list)) continue;
      const kind = septaKindOf(rid);
      if (!kind) continue;
      for (const b of list) {
        const vid = String(b.VehicleID || '');
        if (!vid || vid === '0' || vid === 'None' || vid.indexOf('schedBased') >= 0) continue;
        const ts = +b.timestamp || 0;
        if (ts < 1e9 || nowS - ts > 300) continue;               // placeholder or stale fix
        const lat = +b.lat, lon = +b.lng;
        if (!(lat > SEPTA_BOX.la0 && lat < SEPTA_BOX.la1 && lon > SEPTA_BOX.lo0 && lon < SEPTA_BOX.lo1)) continue;
        septaUpsert('v' + vid, kind, rid, lat, lon, +b.heading || 0,
          { dest: b.destination || '', late: +b.late, next: b.next_stop_name || '' });
      }
    }
    SEPTA.ok = true; SEPTA.fails = 0;
    septaPrune(); septaStatus();
  }
  function septaPrune() {
    const now = performance.now();
    septaVeh.forEach((v, id) => { if (now - v.lastSeen > 50000) septaVeh.delete(id); });
    if (pickedVeh && !septaVeh.has(pickedVeh.id)) { pickedVeh = null; vehinfoEl.hidden = true; }
    else if (pickedVeh) septaCard(pickedVeh);        // keep late/next-stop fresh
  }
  function septaStatus() {
    const n = septaVeh.size;
    btnTransit.title = 'Live SEPTA Vehicles (V): ' + n + ' Tracked Now';
    const tc = document.getElementById('transitCount');
    if (tc) tc.textContent = n ? n + ' Live' : '';
    if (!SEPTA.hinted && n > 0 && veil.classList.contains('hidden')) {
      SEPTA.hinted = true;
      hintEl.textContent = n + ' SEPTA vehicles are live on the map. Tap a pin for its route. V toggles.';
      clearTimeout(septaHintT);
      septaHintT = setTimeout(setHint, 8000);
    }
  }
  function septaPoll(force) {
    if (!SEPTA.on || !septaCanFetch || !septaReady) return;
    if (document.hidden && !force) return;
    septaJsonp('/TransitViewAll/index.php', septaGotTV);
  }
  function septaCard(v) {
    const late = v.info.late;
    const status = (late == null || isNaN(late) || late >= 900) ? '' :
      late > 0 ? late + ' Min Late' : late < 0 ? (-late) + ' Min Early' : 'On Time';
    const bits = [v.kind === 'bus' ? 'Bus' : 'Trolley'];
    if (status) bits.push(status);
    vehinfoBody.innerHTML =
      '<span class="vroute" style="background:' + v.tintHex + '">' + septaEsc(v.routeLabel) + '</span>' +
      '<span class="vdest">To ' + septaEsc(v.info.dest || '—') + '</span>' +
      '<div class="vmeta">' + septaEsc(bits.join(', ')) + '</div>' +
      (v.info.next ? '<div class="vmeta">Next Stop: ' + septaEsc(v.info.next) + '</div>' : '');
  }
  function syncTransitBtn() { btnTransit.classList.toggle('on', SEPTA.on); }
  function toggleTransit() {
    if (!septaCanFetch) return;
    SEPTA.on = !SEPTA.on;
    syncTransitBtn();
    if (SEPTA.on) septaPoll(true);
    else { pickedVeh = null; if (!pickedStation && pickedTree == null) vehinfoEl.hidden = true; }
  }
  btnTransit.addEventListener('click', toggleTransit);
  document.getElementById('vehinfoX').addEventListener('click', () => { pickedVeh = null; pickedStation = null; pickedPlane = null; pickedShip = null; pickedTree = null; vehinfoEl.hidden = true; });
  // tap/click picking (orbit mode, or any touch tap): a short press on a vehicle
  const septaRay = new THREE.Raycaster(), septaNdc = new THREE.Vector2();
  let vpDownX = 0, vpDownY = 0, vpDownT = 0, vpWasLocked = false;
  canvas.addEventListener('pointerdown', (e) => { vpDownX = e.clientX; vpDownY = e.clientY; vpDownT = performance.now(); vpWasLocked = walk.locked; });
  canvas.addEventListener('pointerup', (e) => {
    const sAct = septaReady && SEPTA.on && septaSolid.count > 0;
    const iAct = indegoReady && INDEGO.on && indegoBadge.count > 0;
    const fAct = flightReady && FLIGHTS.on && flightMesh.count > 0;
    const shAct = shipReady && SHIPS.on && shipMesh.count > 0;
    if (!sAct && !iAct && !fAct && !shAct) return;
    // Works in every mode. Under pointer lock (desktop walk/fly look-around) the
    // cursor doesn't exist, so a click picks whatever's under the crosshair —
    // screen center. Unlocked (orbit, drag-look, touch), a short tap picks at
    // the pointer; drags are filtered out.
    let cx, cy;
    if (vpWasLocked && (mode === MODE.WALK || mode === MODE.FLY)) {
      cx = window.innerWidth / 2;
      cy = window.innerHeight / 2;
    } else {
      if (Math.hypot(e.clientX - vpDownX, e.clientY - vpDownY) > 8 || performance.now() - vpDownT > 500) return;
      cx = e.clientX;
      cy = e.clientY;
    }
    septaNdc.set((cx / window.innerWidth) * 2 - 1, -(cy / window.innerHeight) * 2 + 1);
    septaRay.setFromCamera(septaNdc, camera);
    const targets = [];
    if (sAct) targets.push(septaSolid, septaPin, septaBadge);
    if (iAct) targets.push(indegoSolid, indegoBike, indegoBadge);
    if (fAct) targets.push(flightMesh);
    if (shAct) targets.push(shipMesh);
    const hits = septaRay.intersectObjects(targets, false);
    if (hits.length && hits[0].instanceId != null) {
      const h = hits[0];
      let v = null, hitSt = null;
      if (h.object === flightMesh) {
        const p = flightPick[h.instanceId];
        if (p) { pickedVeh = null; pickedStation = null; pickedTree = null; pickedShip = null; pickedPlane = p; flightCard(p); vehinfoEl.hidden = false; return; }
      }
      if (h.object === shipMesh) {
        const p = shipPick[h.instanceId];
        if (p) { pickedVeh = null; pickedStation = null; pickedTree = null; pickedPlane = null; pickedShip = p; shipCard(p); vehinfoEl.hidden = false; return; }
      }
      if (h.object === septaSolid) v = septaPickS[h.instanceId];
      else if (h.object === septaPin) v = septaPickP[h.instanceId];
      else if (h.object === septaBadge) v = septaPickB[h.instanceId];
      else if (h.object === indegoSolid) hitSt = indegoPickS[h.instanceId];
      else if (h.object === indegoBike) hitSt = indegoPickK[h.instanceId];
      else if (h.object === indegoBadge) hitSt = indegoPickB[h.instanceId];
      if (v) { pickedStation = null; pickedTree = null; pickedPlane = null; pickedShip = null; pickedVeh = v; septaCard(v); vehinfoEl.hidden = false; return; }
      if (hitSt) { pickedVeh = null; pickedTree = null; pickedPlane = null; pickedShip = null; pickedStation = hitSt; indegoCard(hitSt); vehinfoEl.hidden = false; return; }
    }
    // forgiving fallback: the nearest vehicle or bike dock within reach of the
    // tap point (a little wider under the crosshair, where aiming is coarser)
    let bestV = null, bestS = null, bestD = (vpWasLocked ? 46 : 30) ** 2;
    if (sAct) septaVeh.forEach((v) => {
      if (v.ug) return;
      _ssv.set(v.dx != null ? v.dx : v.x, (v.gy || 0) + 3, v.dz != null ? v.dz : v.z).project(camera);
      if (_ssv.z > 1 || _ssv.z < -1) return;
      const dx = (_ssv.x * 0.5 + 0.5) * window.innerWidth - cx;
      const dy = (-_ssv.y * 0.5 + 0.5) * window.innerHeight - cy;
      const d2 = dx * dx + dy * dy;
      if (d2 < bestD) { bestD = d2; bestV = v; }
    });
    if (iAct) for (const st of indegoLive) {
      _ssv.set(st.x, st.y + 2.6, st.z).project(camera);
      if (_ssv.z > 1 || _ssv.z < -1) continue;
      const dx = (_ssv.x * 0.5 + 0.5) * window.innerWidth - cx;
      const dy = (-_ssv.y * 0.5 + 0.5) * window.innerHeight - cy;
      const d2 = dx * dx + dy * dy;
      if (d2 < bestD) { bestD = d2; bestS = st; bestV = null; }
    }
    if (bestV) { pickedStation = null; pickedTree = null; pickedPlane = null; pickedShip = null; pickedVeh = bestV; septaCard(bestV); vehinfoEl.hidden = false; return; }
    if (bestS) { pickedVeh = null; pickedTree = null; pickedPlane = null; pickedShip = null; pickedStation = bestS; indegoCard(bestS); vehinfoEl.hidden = false; return; }
    // no vehicle or dock: try the forest. First march the pick ray against the
    // canopy spheres (tapping a crown is the natural gesture), then fall back
    // to the nearest tree around the tapped ground point (trunk-level taps)
    if (treeInv) {
      let bestT = -1;
      const o = septaRay.ray.origin, dr = septaRay.ray.direction;
      for (let t = 5; t < 700 && bestT < 0; t += 6) {
        const px = o.x + dr.x * t, py = o.y + dr.y * t, pz = o.z + dr.z * t;
        const gx = Math.floor(px / TREE_CELL), gz = Math.floor(pz / TREE_CELL);
        for (let ix = gx - 1; ix <= gx + 1; ix++) for (let iz = gz - 1; iz <= gz + 1; iz++) {
          const cell = treePickGrid.get(ix + ':' + iz);
          if (!cell) continue;
          for (const ti of cell) {
            const dx = treeInv.x[ti] - px, dy2 = treeInv.cy[ti] - py, dz = treeInv.z[ti] - pz;
            const rr = Math.max(2.5, treeInv.cr[ti] + 0.6);
            if (dx * dx + dy2 * dy2 + dz * dz < rr * rr) { bestT = ti; break; }
          }
          if (bestT >= 0) break;
        }
      }
      if (bestT < 0) {
        const gp = groundPointAt(cx, cy);
        if (gp) {
          let bestD2 = 0;
          const gx = Math.floor(gp[0] / TREE_CELL), gz = Math.floor(gp[1] / TREE_CELL);
          for (let ix = gx - 1; ix <= gx + 1; ix++) for (let iz = gz - 1; iz <= gz + 1; iz++) {
            const cell = treePickGrid.get(ix + ':' + iz);
            if (!cell) continue;
            for (const ti of cell) {
              const dx = treeInv.x[ti] - gp[0], dz = treeInv.z[ti] - gp[1];
              const d2 = dx * dx + dz * dz;
              const r = Math.max(3.5, treeInv.cr[ti] + 0.8);
              if (d2 < r * r && (bestT < 0 || d2 < bestD2)) { bestT = ti; bestD2 = d2; }
            }
          }
        }
      }
      if (bestT >= 0) { pickedVeh = null; pickedStation = null; pickedPlane = null; pickedShip = null; pickedTree = bestT; treeCard(bestT); vehinfoEl.hidden = false; return; }
    }
    if (pickedVeh || pickedStation || pickedPlane || pickedShip || pickedTree != null) { pickedVeh = null; pickedStation = null; pickedPlane = null; pickedShip = null; pickedTree = null; vehinfoEl.hidden = true; }
  });
  // Road-network spatial hash for snapping live street vehicles onto their
  // streets: raw GPS scatters ±10 m and the straight tween between fixes cuts
  // corners, both of which parked buses inside buildings. Fed by all three road
  // passes (core / wide / far) with drivable classes, queried per vehicle a few
  // times a second and smoothed.
  const septaRoadGrid = new Map();
  const SEPTA_RG_CELL = 36;
  function septaRoadAdd(ax, az, bx, bz) {
    const x0 = Math.floor(Math.min(ax, bx) / SEPTA_RG_CELL), x1 = Math.floor(Math.max(ax, bx) / SEPTA_RG_CELL);
    const z0 = Math.floor(Math.min(az, bz) / SEPTA_RG_CELL), z1 = Math.floor(Math.max(az, bz) / SEPTA_RG_CELL);
    for (let gx = x0; gx <= x1; gx++) for (let gz = z0; gz <= z1; gz++) {
      const key = gx + ':' + gz;
      let a = septaRoadGrid.get(key);
      if (!a) { a = []; septaRoadGrid.set(key, a); }
      a.push(ax, az, bx, bz);
    }
  }
  function septaSnapRoad(x, z, maxD) {
    const gx = Math.floor(x / SEPTA_RG_CELL), gz = Math.floor(z / SEPTA_RG_CELL);
    let bd = maxD * maxD, bx2 = 0, bz2 = 0, bdx = 1, bdz = 0, found = false;
    for (let cx2 = gx - 1; cx2 <= gx + 1; cx2++) for (let cz2 = gz - 1; cz2 <= gz + 1; cz2++) {
      const a = septaRoadGrid.get(cx2 + ':' + cz2);
      if (!a) continue;
      for (let i = 0; i < a.length; i += 4) {
        const ax = a[i], az = a[i + 1], dx = a[i + 2] - ax, dz = a[i + 3] - az;
        const L2 = dx * dx + dz * dz || 1e-9;
        let tt = ((x - ax) * dx + (z - az) * dz) / L2;
        tt = tt < 0 ? 0 : tt > 1 ? 1 : tt;
        const ex = ax + dx * tt - x, ez = az + dz * tt - z;
        const d2 = ex * ex + ez * ez;
        if (d2 < bd) { bd = d2; bx2 = ax + dx * tt; bz2 = az + dz * tt; bdx = dx; bdz = dz; found = true; }
      }
    }
    if (!found) return null;
    const L3 = Math.hypot(bdx, bdz) || 1;
    return [bx2, bz2, bdx / L3, bdz / L3];   // point + street axis, for position AND heading alignment
  }
  function septaMerge(parts) {
    let total = 0;
    parts.forEach((g) => { total += g.attributes.position.count; });
    const pos = new Float32Array(total * 3), nor = new Float32Array(total * 3), col = new Float32Array(total * 3), glo = new Float32Array(total);
    let o = 0;
    for (const g of parts) {
      pos.set(g.attributes.position.array, o * 3);
      nor.set(g.attributes.normal.array, o * 3);
      col.set(g.attributes.color.array, o * 3);
      if (g.attributes.aGlow) glo.set(g.attributes.aGlow.array, o);
      o += g.attributes.position.count;
    }
    const out = new THREE.BufferGeometry();
    out.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    out.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
    out.setAttribute('color', new THREE.BufferAttribute(col, 3));
    out.setAttribute('aGlow', new THREE.BufferAttribute(glo, 1));
    return out;
  }
  function septaColored(g, cr, cg, cb, glow) {
    const gg = g.index ? g.toNonIndexed() : g;
    const n = gg.attributes.position.count;
    const col = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { col[i * 3] = cr; col[i * 3 + 1] = cg; col[i * 3 + 2] = cb; }
    gg.setAttribute('color', new THREE.BufferAttribute(col, 3));
    const glo = new Float32Array(n);
    if (glow) glo.fill(1);
    gg.setAttribute('aGlow', new THREE.BufferAttribute(glo, 1));
    return gg;
  }
  function septaVehGeom(withBand) {
    // unit vehicle: length along x in [-.5,.5], base y=0..1, width z; scaled per
    // class. Vertex colors multiply the per-instance line color, so trim parts
    // are near-black (glass, wheels) or near-white (body) multipliers.
    const parts = [];
    const boxPart = (sx, sy, sz, cx, cy, cz, cr, cg, cb, glow) =>
      parts.push(septaColored(new THREE.BoxGeometry(sx, sy, sz).translate(cx, cy, cz), cr, cg, cb, glow));
    boxPart(0.98, 0.94, 0.94, 0, 0.53, 0, 1, 1, 1);                       // body (takes instance color)
    if (withBand) {
      boxPart(0.9, 0.36, 1.02, 0, 0.72, 0, 0.14, 0.15, 0.17, 1);         // glass band, proud — lit at night
      boxPart(0.99, 0.1, 0.9, 0, 0.07, 0, 0.2, 0.21, 0.22);              // dark undercarriage skirt
      boxPart(0.05, 0.3, 0.8, 0.475, 0.71, 0, 0.13, 0.14, 0.16, 1);      // windshield, engaging the nose
      boxPart(0.5, 0.09, 0.66, -0.05, 1.03, 0, 0.7, 0.72, 0.74);         // roof HVAC unit
      for (const wx of [-0.3, 0.3]) for (const wz of [-0.44, 0.44]) {
        boxPart(0.13, 0.17, 0.1, wx, 0.085, wz, 0.09, 0.09, 0.1);        // wheel blocks, proud of the sides
      }
    }
    return septaMerge(parts);
  }
  function septaPinGeom() {
    // floating map pin: inverted cone + ball, tinted by instance color
    const cone = new THREE.ConeGeometry(1.05, 2.7, 9);
    cone.rotateX(Math.PI);
    cone.translate(0, 1.75, 0);
    const ball = new THREE.SphereGeometry(1.35, 10, 8);
    ball.translate(0, 3.6, 0);
    return septaMerge([septaColored(cone, 0.78, 0.78, 0.78), septaColored(ball, 1, 1, 1)]);
  }
  function septaBadgeTexture() {
    // bus pins wear the SEPTA mark: a marker badge drawn once into a canvas —
    // official geometry from the agency's logo SVG (Wikimedia SEPTA.svg, 500x369
    // box), Path2D-filled under the badge's rounded frame + pointer tip
    const cv = document.createElement('canvas');
    cv.width = 256; cv.height = 320;
    const g = cv.getContext('2d');
    const bw = 240, bh = 200, bx = 8, by = 8, rad = 34;
    const rr = () => {
      g.beginPath();
      g.moveTo(bx + rad, by);
      g.arcTo(bx + bw, by, bx + bw, by + bh, rad);
      g.arcTo(bx + bw, by + bh, bx, by + bh, rad);
      g.arcTo(bx, by + bh, bx, by, rad);
      g.arcTo(bx, by, bx + bw, by, rad);
      g.closePath();
    };
    g.fillStyle = '#fdfbf6';
    g.strokeStyle = 'rgba(28,26,22,0.6)';
    g.lineWidth = 7;
    g.beginPath();                                   // pointer tip first, badge overlaps it
    g.moveTo(128 - 30, by + bh - 6);
    g.lineTo(128, 312);
    g.lineTo(128 + 30, by + bh - 6);
    g.closePath();
    g.fill(); g.stroke();
    rr(); g.fill(); g.stroke();
    const s2 = (bw - 40) / 500;
    g.translate(bx + 20, by + (bh - 369.109 * s2) / 2);
    g.scale(s2, s2);
    g.fillStyle = '#f14728';
    g.fill(new Path2D('M441.775,14.666H340.441L180.888,127.332h148.665l115.779,115.333L333.556,355.107h108.22c25.555,0,44.221-25.332,44.221-43.331V58.221C485.996,39.998,467.33,14.666,441.775,14.666z'));
    g.fill(new Path2D('M206.443,137.998H192.22l87.111,87.107c4.001,3.338,7.11,7.336,13.999,6.893h14.89l-87.555-86.889C216.665,140.664,213.776,137.998,206.443,137.998z'));
    g.fillStyle = '#1f4fa3';
    g.fill(new Path2D('M58.666,355.107h101.111l159.554-112.219H170.887L54.666,127.332L167.11,14.666H58.666c-25.778,0-44,25.332-44,43.776v253.555C14.666,329.775,32.888,355.107,58.666,355.107z'));
    const tex = new THREE.CanvasTexture(cv);
    tex.encoding = THREE.sRGBEncoding;
    tex.anisotropy = 4;
    return tex;
  }
  const _sm = new THREE.Matrix4(), _sq = new THREE.Quaternion(), _sqB = new THREE.Quaternion(), _sp = new V3(), _ss = new V3(), _sc = new THREE.Color(), _sup = new V3(0, 1, 0), _ssv = new V3();
  function updateTransit(now, dt) {
    if (!septaReady) return;
    if (!SEPTA.on) {
      if (septaSolid.count || septaPin.count || septaBadge.count) { septaSolid.count = 0; septaPin.count = 0; septaBadge.count = 0; }
      return;
    }
    let si = 0, pi = 0, bi = 0;
    const cap = 2.6 * dt;
    _sqB.copy(camera.quaternion);                      // badges billboard the camera
    septaVeh.forEach((v) => {
      const k = v.t0 ? Math.min(1, (now - v.t0) / (SEPTA_POLL + 1500)) : 1;
      v.x = v.fx + (v.tx - v.fx) * k;
      v.z = v.fz + (v.tz - v.fz) * k;
      // street vehicles snap to the nearest drivable centerline (refreshed a few
      // times a second, staggered) and glide to it — GPS scatter and corner-cut
      // tweens no longer drive buses through building walls
      let wx = v.x, wz = v.z;
      if (!v.ug && (v.kind === 'bus' || v.kind === 'trolley')) {
        if (v.snT === undefined || now - v.snT > 120) {
          v.snT = now;
          const sn = septaSnapRoad(v.x, v.z, 20);
          if (sn) { v.snx = sn[0]; v.snz = sn[1]; v.sdx = sn[2]; v.sdz = sn[3]; } else { v.snx = null; }
        }
        if (v.snx != null) { wx = v.snx; wz = v.snz; }
      }
      if (v.dx === undefined) { v.dx = wx; v.dz = wz; }
      const kS = 1 - Math.exp(-dt * 7);
      v.dx += (wx - v.dx) * kS;
      v.dz += (wz - v.dz) * kS;
      // heading: align to the snapped street's axis (signed to match the API/
      // displacement heading) so GPS heading noise never parks a bus diagonally
      // across its street; unsnapped vehicles keep the raw heading
      let yawGoal = v.yawT;
      if (v.snx != null) {
        const ry = Math.atan2(-v.sdz, v.sdx);
        let dAx = ry - v.yawT;
        dAx = ((dAx + Math.PI) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2) - Math.PI;
        yawGoal = Math.abs(dAx) <= Math.PI / 2 ? ry : ry + Math.PI;
      }
      let dyaw = yawGoal - v.yaw;
      dyaw = ((dyaw + Math.PI) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2) - Math.PI;
      v.yaw += Math.abs(dyaw) <= cap ? dyaw : Math.sign(dyaw) * cap;
      if (v.ug) return;                 // tunnel trolleys aren't drawn — nothing under buildings
      if (v.gy === undefined || Math.abs(v.dx - v.gx) + Math.abs(v.dz - v.gz) > 2.5) {
        v.gx = v.dx; v.gz = v.dz;
        v.gy = siteY(v.dx, v.dz, 'road');
        // a vehicle on a bridge street rides the deck, not the ground beneath it
        // (aligned to its snapped street axis so passing under a viaduct never lifts)
        if (v.sdx || v.sdz) {
          const oy = ovpDeckY(v.dx, v.dz, v.sdx, v.sdz);
          if (oy !== null && oy > v.gy) v.gy = oy;
        }
      }
      const spec = SEPTA_KIND[v.kind];
      if (si < 1600) {
        _ss.set(spec.l, spec.h, spec.w);
        _sq.setFromAxisAngle(_sup, v.yaw);
        _sp.set(v.dx, v.gy + 0.22, v.dz);
        _sm.compose(_sp, _sq, _ss);
        septaSolid.setMatrixAt(si, _sm);
        septaSolid.setColorAt(si, _sc.setHex(v.tint));
        septaPickS[si++] = v;
      }
      // floating marker, scaled with distance so it stays findable: buses fly
      // the SEPTA-badge billboard, trolleys keep the line-colored lollipop pin
      if (v.kind === 'bus') {
        if (bi < 1024) {
          const py0 = v.gy + spec.h + 0.6;
          _sp.set(v.dx, py0, v.dz);
          const s = clamp(camera.position.distanceTo(_sp) / 240, 1, 8);
          _sp.y += Math.sin(now * 0.003 + v.bobP) * 0.5 * Math.min(s, 2);
          _ss.set(s, s, s);
          _sm.compose(_sp, _sqB, _ss);
          septaBadge.setMatrixAt(bi, _sm);
          septaPickB[bi++] = v;
        }
      } else if (pi < 1024) {
        const py0 = v.gy + spec.h + 0.9;
        _sp.set(v.dx, py0, v.dz);
        const s = clamp(camera.position.distanceTo(_sp) / 240, 1, 8);
        const bob = Math.sin(now * 0.003 + v.bobP) * 0.5 * Math.min(s, 2);
        _sp.y += bob;
        _ss.set(s, s, s);
        _sq.identity();
        _sm.compose(_sp, _sq, _ss);
        septaPin.setMatrixAt(pi, _sm);
        septaPin.setColorAt(pi, _sc.setHex(v.tint).multiplyScalar(2.0));
        septaPickP[pi++] = v;
      }
    });
    septaSolid.count = si;
    septaPin.count = pi;
    septaBadge.count = bi;
    septaSolid.instanceMatrix.needsUpdate = true;
    septaPin.instanceMatrix.needsUpdate = true;
    septaBadge.instanceMatrix.needsUpdate = true;
    if (septaSolid.instanceColor) septaSolid.instanceColor.needsUpdate = true;
    if (septaPin.instanceColor) septaPin.instanceColor.needsUpdate = true;
    if (pickedVeh) {
      const spec = SEPTA_KIND[pickedVeh.kind];
      _ssv.set(pickedVeh.dx, pickedVeh.gy + spec.h + 7, pickedVeh.dz).project(camera);
      if (_ssv.z > 1 || _ssv.z < -1) vehinfoEl.style.opacity = '0';
      else {
        vehinfoEl.style.opacity = '1';
        vehinfoEl.style.transform = 'translate(-50%,-100%) translate(' +
          ((_ssv.x * 0.5 + 0.5) * window.innerWidth).toFixed(1) + 'px,' +
          ((-_ssv.y * 0.5 + 0.5) * window.innerHeight).toFixed(1) + 'px)';
      }
    }
  }

  // ---------------------------------------------------------------- layers panel
  // The three layer toggles (SEPTA vehicles, street names, landmark labels) live
  // as rows in one panel behind the Layers bar button; V/N/L stay as shortcuts.
  const btnLayers = document.getElementById('btnLayers');
  const layersPanel = document.getElementById('layerspanel');
  function toggleLayers(open) {
    const want = open !== undefined ? open : !layersPanel.classList.contains('open');
    layersPanel.classList.toggle('open', want);
  }
  btnLayers.addEventListener('click', () => toggleLayers());

  // ---------------------------------------------------------------- street names
  // Ground-painted street labels: placements baked offline by
  // bake_street_labels.py (the packed wide/far road formats carry no names) and
  // shipped as ST_LABELS; every unique name is drawn once into a canvas atlas
  // and all ~4,700 labels merge into ONE textured quad mesh lying flat on the
  // roadways. Toggle: the St button / N key.
  let stMesh = null, stMat = null, stOn = true;
  const btnStreets = document.getElementById('btnStreets');
  function syncStreetsBtn() { btnStreets.classList.toggle('on', stOn); }
  function toggleStreets() {
    stOn = !stOn;
    if (stMesh) stMesh.visible = stOn;
    syncStreetsBtn();
  }
  btnStreets.addEventListener('click', toggleStreets);
  step('Lettering the streets', async () => {
    if (typeof ST_LABELS === 'undefined' || !ST_LABELS || !ST_LABELS.names) { btnStreets.style.display = 'none'; return; }
    // Preferred path: the offline signed-distance-field atlas (bake_street_sdf.py).
    // A raster atlas magnified 5-9x at street level reads pixelated however its
    // edges are filtered; in an SDF the 0.5 level-set IS the glyph outline, so a
    // per-pixel threshold stays crisp at any zoom. Falls back to the old canvas
    // atlas if the baked data is missing.
    let AW = 4096, AH = 2048, FS = 27, RH = 34;
    const PAD = 9;
    let tex = null, rects = null, sdfMode = false;
    if (typeof ST_SDF !== 'undefined' && ST_SDF && ST_SDF.png) {
      sdfMode = true;
      AW = ST_SDF.w; AH = ST_SDF.h; RH = ST_SDF.rowH; FS = ST_SDF.fs;
      rects = ST_SDF.rects;
      const img = new Image();
      await new Promise((res) => { img.onload = res; img.onerror = res; img.src = 'data:image/png;base64,' + ST_SDF.png; });
      ST_SDF = null;   // the atlas PNG lives in the texture now
      const cv = document.createElement('canvas');
      cv.width = AW; cv.height = AH;
      const g = cv.getContext('2d');
      g.drawImage(img, 0, 0);
      const px = g.getImageData(0, 0, AW, AH).data;
      const lum = new Uint8Array(AW * AH);
      for (let i = 0; i < lum.length; i++) lum[i] = px[i * 4];
      tex = new THREE.DataTexture(lum, AW, AH, THREE.RedFormat, THREE.UnsignedByteType);  // R8: WebGL2 mipmappable (LUMINANCE is not)
      tex.magFilter = THREE.LinearFilter;
      tex.minFilter = THREE.LinearMipmapLinearFilter;
      tex.generateMipmaps = true;
      tex.flipY = true;                    // the UV math below assumes canvas orientation
      tex.anisotropy = 8;
      tex.needsUpdate = true;
    } else {
      try { await document.fonts.load('italic 600 27px "Montserrat"'); } catch (e) { /* fall back to the stack */ }
      const cv = document.createElement('canvas');
      cv.width = AW; cv.height = AH;
      const g = cv.getContext('2d');
      // street lettering: Montserrat semibold italic, map-style
      g.font = 'italic 600 ' + FS + 'px "Montserrat", "Avenir Next", "Segoe UI", sans-serif';
      g.fillStyle = '#fff';
      g.textBaseline = 'middle';
      rects = [];
      let ax = PAD, ay = 0;
      for (const nm of ST_LABELS.names) {
        const w = Math.min(Math.ceil(g.measureText(nm).width), 560);
        if (ax + w + PAD > AW) { ax = PAD; ay += RH; }
        if (ay + RH > AH) { rects.push(null); continue; }
        g.fillText(nm, ax, ay + RH / 2, 560);
        rects.push([ax, ay, w, RH]);
        ax += w + PAD * 2;
      }
      tex = new THREE.CanvasTexture(cv);
      tex.encoding = THREE.sRGBEncoding;
      tex.anisotropy = 8;
    }
    const L2 = ST_LABELS.l;
    const pos = [], uv = [], idx = [];
    const LIFT = [0.66, 0.5, 0.38];        // over siteY(road): major / minor / core (clears ribbon lifts)
    const TH = [7.0, 5.6, 4.4];            // text height in meters per class
    for (let i = 0; i + 4 < L2.length; i += 5) {
      const r = rects[L2[i]];
      if (!r) continue;
      const x = L2[i + 1], z = L2[i + 2], br = L2[i + 3] * Math.PI / 180, cls = L2[i + 4];
      const inCutName = /expressway/i.test(ST_LABELS.names[L2[i]] || '');   // only the mainline name sinks into the cut
      const dx = Math.cos(br), dz = Math.sin(br);
      const ux = dz, uz = -dx;             // glyph-up in world = left of travel (north-up read)
      const th = TH[cls], hw = th * (r[2] / FS) / 2, hh = th * (RH / FS) / 2;
      const u0 = r[0] / AW, u1 = (r[0] + r[2]) / AW;
      const v1 = 1 - r[1] / AH, v0 = 1 - (r[1] + r[3]) / AH;
      // drape the label along the street profile: a flat quad at one height sank
      // an end into the pavement wherever the road slopes (Front St, the trench
      // shoulders), so sample the road height every ~7 m along the text instead
      const cols = Math.max(2, Math.min(10, Math.round(hw / 3.5)));
      // pass 1: column heights (decks lift them, the Vine cut sinks its own name)
      const colY = [];
      for (let c2 = 0; c2 <= cols; c2++) {
        const t2 = c2 / cols * 2 - 1;
        const cxw = x + dx * t2 * hw, czw = z + dz * t2 * hw;
        let ycs = siteY(cxw, czw, 'road');
        const oyc = ovpDeckY(cxw, czw, dx, dz);
        if (oyc !== null && oyc > ycs) ycs = oyc;
        else if (inCutName) {
          const vyc = vineCut(cxw, czw, -2);
          if (vyc !== null) ycs = vyc + 0.45;
        }
        colY.push(ycs);
      }
      // buried roads get no label: under the trench caps the roadway runs below
      // ground (the half-swallowed Delaware Expressway name at Foglietta)
      const midY = colY[Math.floor(cols / 2)];
      if (siteY(x, z, 'ground') - midY > 2.5 && vineCut(x, z, -2) === null) continue;
      // label ends must never climb a trench wall or bank: cap the rise between
      // neighboring columns (steep streets stay legible, walls stop swallowing text)
      for (let c2 = 1; c2 <= cols; c2++) colY[c2] = Math.min(colY[c2], colY[c2 - 1] + 1.0);
      for (let c2 = cols - 1; c2 >= 0; c2--) colY[c2] = Math.min(colY[c2], colY[c2 + 1] + 1.0);
      const i0 = pos.length / 3;
      for (let c2 = 0; c2 <= cols; c2++) {
        const t2 = c2 / cols * 2 - 1;
        const cxw = x + dx * t2 * hw, czw = z + dz * t2 * hw;
        const yc = colY[c2] + LIFT[cls];
        pos.push(cxw - ux * hh, yc, czw - uz * hh, cxw + ux * hh, yc, czw + uz * hh);
        const uc = u0 + (u1 - u0) * (c2 / cols);
        uv.push(uc, v0, uc, v1);
      }
      for (let c2 = 0; c2 < cols; c2++) {
        const a2 = i0 + c2 * 2;
        idx.push(a2, a2 + 2, a2 + 3, a2, a2 + 3, a2 + 1);
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
    geo.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(uv), 2));
    geo.setIndex(idx);
    if (sdfMode) {
      // luminance SDF rides in the alphaMap (.g); the 0.5 level-set is the true
      // outline, thresholded with fwidth-scaled AA — crisp at every zoom
      stMat = new THREE.MeshBasicMaterial({ alphaMap: tex, transparent: true, depthWrite: false, color: 0x2c2822 });
      stMat.onBeforeCompile = (shader) => {
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <alphamap_fragment>',
          '{\n' +
          '  float sd = texture2D(alphaMap, vUv).r;\n' +   // R8: the SDF rides in .r
          '  float w = clamp(fwidth(sd) * 1.1, 0.002, 0.35);\n' +
          '  diffuseColor.a *= smoothstep(0.5 - w, 0.5 + w, sd);\n' +
          '}');
      };
    } else {
      stMat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, color: 0x2c2822 });
      // Alpha-tested magnification fallback: bilinear coverage approximates a
      // distance field near edges; re-threshold with fwidth AA to cut the blocks.
      stMat.onBeforeCompile = (shader) => {
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <map_fragment>',
          '#include <map_fragment>\n{\n' +
          '  float w = clamp(fwidth(diffuseColor.a) * 1.4, 0.02, 0.49);\n' +
          '  diffuseColor.a = smoothstep(0.42 - w, 0.42 + w, diffuseColor.a);\n' +
          '}');
      };
    }
    stMesh = new THREE.Mesh(geo, stMat);
    stMesh.renderOrder = 5;
    stMesh.visible = stOn;
    groupCity.add(stMesh);
    syncStreetsBtn();
  });

  // ---------------------------------------------------------------- places
  // Historic districts and neighborhood names (OpenDataPhilly, baked by
  // fetch_places.py / bake_places.py into PLACES). The sixteen Philadelphia
  // Register districts draw as bronze boundary inlays on the ground, Society
  // Hill first among them; the neighborhood names fade in from altitude as
  // the district-level complement to the painted street names. One toggle
  // covers all of it: the P key.
  let placesOn = true, hdMesh = null, hdMat = null, hdLblMesh = null, hdLblMat = null, nbMesh = null, nbMat = null;
  const btnPlaces = document.getElementById('btnPlaces');
  function syncPlacesBtn() { btnPlaces.classList.toggle('on', placesOn); }
  function togglePlaces() {
    placesOn = !placesOn;
    if (hdMesh) hdMesh.visible = placesOn;
    if (hdLblMesh) hdLblMesh.visible = placesOn;
    if (nbMesh) nbMesh.visible = false;      // applyLighting re-shows it by altitude
    syncPlacesBtn();
  }
  btnPlaces.addEventListener('click', togglePlaces);
  step('Tracing the historic districts', () => {
    if (typeof PLACES === 'undefined' || !PLACES || !PLACES.hd || !PLACES.hd.length) { btnPlaces.style.display = 'none'; return; }
    const parts = [];
    for (const d of PLACES.hd) {
      for (const flat of d.rings) {
        const pts = [];
        for (let i = 0; i + 1 < flat.length; i += 2) pts.push([flat[i], flat[i + 1]]);
        if (pts.length < 3) continue;
        pts.push(pts[0]);                     // close the boundary loop
        // walkY so the inlay rides the trench cap decks instead of diving in;
        // 0.34 sits between the footway and basin lifts. 3.2 m wide: a 1.7 m
        // trial line vanished below one pixel at district-viewing altitude
        parts.push(ribbon(pts, 3.2, 0.34, (x, z) => walkY(x, z)));
      }
    }
    if (!parts.length) return;
    let total = 0;
    for (const g of parts) total += g.attributes.position.count;
    const pos = new Float32Array(total * 3);
    let o = 0;
    for (const g of parts) { pos.set(g.attributes.position.array, o * 3); o += g.attributes.position.count; }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    hdMat = new THREE.MeshBasicMaterial({ color: 0x6b4f26, transparent: true, opacity: 0.85, depthWrite: false });
    hdMesh = new THREE.Mesh(geo, hdMat);
    hdMesh.renderOrder = 4;                   // under the street lettering at 5
    hdMesh.visible = placesOn;
    groupCity.add(hdMesh);
    syncPlacesBtn();
  });
  step('Naming the neighborhoods', async () => {
    if (typeof PLACES === 'undefined' || !PLACES || !PLACES.nb || !PLACES.nb.names) return;
    const AW = 2048, AH = 1024, FS = 30, RH = 38, PAD = 8;
    try { await document.fonts.load('600 30px "Montserrat"'); } catch (e) { /* fall back to the stack */ }
    const cv = document.createElement('canvas');
    cv.width = AW; cv.height = AH;
    const g = cv.getContext('2d');
    g.font = '600 ' + FS + 'px "Montserrat", "Avenir Next", "Segoe UI", sans-serif';
    g.fillStyle = '#fff';
    g.textBaseline = 'middle';
    let ax = PAD, ay = 0;
    const put = (nm, haloed) => {
      const w = Math.min(Math.ceil(g.measureText(nm).width), 520);
      if (ax + w + PAD > AW) { ax = PAD; ay += RH; }
      if (ay + RH > AH) return null;
      if (haloed) {
        // cartographic halo baked in final colors: a pale casing around a dark
        // core stays readable over the pale noon city AND the night ground
        // (a flat tint washed out at noon — Mike's ghost-text screenshot)
        g.lineJoin = 'round';
        g.strokeStyle = 'rgba(248,244,233,0.95)';
        g.lineWidth = 7;
        g.strokeText(nm, ax, ay + RH / 2, 520);
        g.fillStyle = '#2e2a22';
        g.fillText(nm, ax, ay + RH / 2, 520);
        g.fillStyle = '#fff';
      } else {
        g.fillText(nm, ax, ay + RH / 2, 520);
      }
      const r = [ax, ay, w, RH];
      ax += w + PAD * 2;
      return r;
    };
    const nbRects = PLACES.nb.names.map((nm) => put(nm, true));
    const hdLbl = PLACES.hd.filter((d) => d.lbl);
    const hdRects = hdLbl.map((d) => put(d.n, false));
    const tex = new THREE.CanvasTexture(cv);
    tex.encoding = THREE.sRGBEncoding;
    tex.anisotropy = 8;
    const makeMesh = (entries, mat) => {
      // flat north-up quads draped in 4 columns so long names ride the terrain
      const pos = [], uv = [], idx = [];
      for (const [r, x, z, textH, lift] of entries) {
        if (!r) continue;
        const hw = textH * (r[2] / FS) / 2, hh = textH * (RH / FS) / 2;
        const u0 = r[0] / AW, u1 = (r[0] + r[2]) / AW;
        const v1 = 1 - r[1] / AH, v0 = 1 - (r[1] + r[3]) / AH;
        const cols = 4;
        const i0 = pos.length / 3;
        for (let c = 0; c <= cols; c++) {
          const cx = x + (c / cols * 2 - 1) * hw;
          const yc = walkY(cx, z) + lift;
          pos.push(cx, yc, z + hh, cx, yc, z - hh);
          const uc = u0 + (u1 - u0) * (c / cols);
          uv.push(uc, v0, uc, v1);
        }
        for (let c = 0; c < cols; c++) {
          const a = i0 + c * 2;
          idx.push(a, a + 2, a + 3, a, a + 3, a + 1);
        }
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
      geo.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(uv), 2));
      geo.setIndex(idx);
      const mesh = new THREE.Mesh(geo, mat);
      mesh.renderOrder = 5;
      groupCity.add(mesh);
      return mesh;
    };
    // 24 m up: painted at grade the names drown under rowhouse roofs and tree
    // canopies (street names live on open roadway; neighborhoods don't) — a
    // gentle lift clears the fabric while the towers still punch through
    const NB_TH = [110, 80, 55];              // text height by area class
    const L = PLACES.nb.l;
    const nbEntries = [];
    for (let i = 0; i + 3 < L.length; i += 4) nbEntries.push([nbRects[L[i]], L[i + 1], L[i + 2], NB_TH[L[i + 3]] || 55, 24]);
    // no depth test: a neighborhood's name is never blocked by its buildings
    // (Mike's rule) — badges at renderOrder 12 still paint over the names
    nbMat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, depthTest: false, color: 0xffffff, opacity: 0 });
    nbMat.toneMapped = false;   // the atlas carries its own halo colors
    nbMesh = makeMesh(nbEntries, nbMat);
    nbMesh.renderOrder = 11;
    nbMesh.visible = false;                   // fades in from altitude
    const hdEntries = hdLbl.map((d, i) => [hdRects[i], d.lbl[0], d.lbl[1], 26, 12]);
    hdLblMat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, color: 0x8f6f3f, opacity: 0.9 });
    hdLblMesh = makeMesh(hdEntries, hdLblMat);
    hdLblMesh.visible = placesOn;
  });

  // ---------------------------------------------------------------- address search
  // Nominatim (OpenStreetMap) geocoding, bounded to the modeled city box — free,
  // key-less, CORS-open. Blocked (with the button hidden) under the artifact CSP,
  // same as every other live fetch. Results fly the orbit camera to the spot and
  // drop a bronze pin + label for 20 s.
  const btnSearch = document.getElementById('btnSearch');
  const searchPanel = document.getElementById('searchpanel');
  const searchInput = document.getElementById('searchInput');
  const searchOut = document.getElementById('searchOut');
  let searchMark = null, searchBusy = false;
  function toggleSearch(open) {
    const want = open !== undefined ? open : !searchPanel.classList.contains('open');
    searchPanel.classList.toggle('open', want);
    if (want) searchInput.focus();
    else searchInput.blur();
  }
  function searchShortName(s) {
    return String(s || '').split(',').slice(0, 3).join(',');
  }
  function searchGoTo(lat, lon, name) {
    const x = (lon - SEPTA_GEO.lon0) * SEPTA_GEO.mx, z = -(lat - SEPTA_GEO.lat0) * SEPTA_GEO.mz;
    setMode(MODE.ORBIT);
    const gy = siteY(x, z, 'ground');
    orbit.goalTarget.set(x, gy + 12, z);
    orbit.goalR = 300;
    orbit.goalPhi = 1.02;
    placeSearchMark(x, gy, z, name);
    if (isTouch) toggleSearch(false);       // free the screen; desktop keeps the result list up
  }
  function placeSearchMark(x, gy, z, name) {
    clearSearchMark();
    const mesh = new THREE.Mesh(septaPinGeom(), new THREE.MeshBasicMaterial({ vertexColors: true, color: 0xc89b5e, transparent: true, depthWrite: false, depthTest: false }));
    mesh.renderOrder = 12;                    // the search pin is a marker too
    mesh.frustumCulled = false;
    groupCity.add(mesh);
    const el = document.createElement('div');
    el.className = 'lbl smark';
    el.textContent = name;
    labelsRoot.appendChild(el);
    searchMark = { mesh, el, x, y: gy + 1.4, z, until: performance.now() + 20000 };
  }
  function clearSearchMark() {
    if (!searchMark) return;
    groupCity.remove(searchMark.mesh);
    searchMark.mesh.geometry.dispose();
    searchMark.mesh.material.dispose();
    searchMark.el.remove();
    searchMark = null;
  }
  function updateSearchMark(now) {
    if (!searchMark) return;
    if (now > searchMark.until) { clearSearchMark(); return; }
    const s = clamp(camera.position.distanceTo(_ssv.set(searchMark.x, searchMark.y, searchMark.z)) / 240, 1, 8);
    searchMark.mesh.position.set(searchMark.x, searchMark.y + Math.sin(now * 0.004) * 0.5, searchMark.z);
    searchMark.mesh.scale.setScalar(s);
    _ssv.set(searchMark.x, searchMark.y + 5.2 * s + 2, searchMark.z).project(camera);
    if (_ssv.z > 1 || _ssv.z < -1) { searchMark.el.style.opacity = '0'; return; }
    searchMark.el.style.opacity = '1';
    searchMark.el.style.transform = 'translate(-50%,-100%) translate(' +
      ((_ssv.x * 0.5 + 0.5) * window.innerWidth).toFixed(1) + 'px,' +
      ((-_ssv.y * 0.5 + 0.5) * window.innerHeight).toFixed(1) + 'px)';
  }
  function searchGoToBus(v) {
    setMode(MODE.ORBIT);
    const x = v.dx != null ? v.dx : v.x, z = v.dz != null ? v.dz : v.z;
    orbit.goalTarget.set(x, (v.gy || siteY(x, z, 'road')) + 6, z);
    orbit.goalR = 220;
    orbit.goalPhi = 1.02;
    pickedVeh = v;
    septaCard(v);
    vehinfoEl.hidden = false;
    if (isTouch) toggleSearch(false);
  }
  function searchSubmit() {
    const qy = searchInput.value.trim();
    if (!qy || searchBusy) return;
    // a bus/trolley route first ("33", "G1", "route 47"): list its live vehicles
    const rid = qy.toUpperCase().replace(/^(ROUTE|RT|BUS)\s+/, '');
    const live = [];
    septaVeh.forEach((v) => {
      if (!v.ug && (v.routeLabel.toUpperCase() === rid || v.route.toUpperCase() === rid)) live.push(v);
    });
    if (live.length) {
      live.forEach((v) => {
        const x = v.dx != null ? v.dx : v.x, z = v.dz != null ? v.dz : v.z;
        v._sd = (x - camera.position.x) * (x - camera.position.x) + (z - camera.position.z) * (z - camera.position.z);
      });
      live.sort((a2, b2) => a2._sd - b2._sd);
      searchOut.innerHTML = '<div class="smsg">Route ' + septaEsc(rid) + ': ' + live.length + ' Live, Nearest First</div>';
      for (const v of live.slice(0, 8)) {
        const el = document.createElement('div');
        el.className = 'srow';
        el.textContent = v.routeLabel + ' To ' + (v.info.dest || 'Unknown') + (v.info.next ? ', Next: ' + v.info.next : '');
        el.addEventListener('click', () => searchGoToBus(v));
        searchOut.appendChild(el);
      }
      searchGoToBus(live[0]);
      return;
    }
    searchBusy = true;
    searchOut.innerHTML = '<div class="smsg">Searching&hellip;</div>';
    fetch('https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5&bounded=1&viewbox=-75.30,40.145,-74.94,39.855&q=' + encodeURIComponent(qy))
      .then((r) => (r && r.ok ? r.json() : null))
      .then((rows) => {
        searchBusy = false;
        if (!rows) { searchOut.innerHTML = '<div class="smsg">Search failed. Try again in a moment.</div>'; return; }
        // the bounding box spans the rivers — keep the city proper, drop NJ
        rows = rows.filter((r) => /philadelphia/i.test(r.display_name || ''));
        if (!rows.length) { searchOut.innerHTML = '<div class="smsg">No match inside Philadelphia.</div>'; return; }
        searchOut.innerHTML = '';
        for (const r of rows) {
          const el = document.createElement('div');
          el.className = 'srow';
          el.textContent = searchShortName(r.display_name);
          el.addEventListener('click', () => searchGoTo(+r.lat, +r.lon, el.textContent));
          searchOut.appendChild(el);
        }
        searchGoTo(+rows[0].lat, +rows[0].lon, searchShortName(rows[0].display_name));
      })
      .catch(() => { searchBusy = false; searchOut.innerHTML = '<div class="smsg">Search failed. Try again in a moment.</div>'; });
  }
  if (septaCanFetch) {
    btnSearch.addEventListener('click', () => toggleSearch());
    document.getElementById('searchGo').addEventListener('click', searchSubmit);
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') searchSubmit();
      else if (e.key === 'Escape') toggleSearch(false);
      e.stopPropagation();
    });
  } else {
    btnSearch.style.display = 'none';
  }

  // The Market–Frankford El's real alignment (OSM railway=subway elevated + approach
  // ways reduced to one centerline per corridor, local meters): Callowhill portal →
  // Frankford TC, and the West Market leg, 46th St portal → 69th St. Each chain
  // STARTS at its tunnel portal, so the deck ramps up out of the ground there.
  const EL_TRACK = [[286,-830,280,-933,277,-1033,283,-1167,295,-1296,315,-1434,336,-1550,370,-1683,409,-1794,432,-1847,501,-1984,602,-2143,620,-2178,641,-2237,895,-3302,1092,-4498,1099,-4515,1110,-4529,1125,-4541,1481,-4793,1632,-4905,1729,-4974,1790,-5013,2786,-5724,3276,-6069,3311,-6097,4649,-7050,4686,-7079,4711,-7107,4728,-7137,4852,-7383,5530,-8335,5584,-8412,5633,-8492,5746,-8647,5753,-8665,5751,-8687,5742,-8705,5720,-8726],[-5528,-1449,-5572,-1451,-5802,-1445,-5835,-1447,-8807,-1924,-8864,-1939,-8914,-1962,-8947,-1985,-9010,-2044,-9045,-2064,-9073,-2073,-9229,-2108,-9274,-2115,-9313,-2117,-9354,-2112,-9399,-2099,-9435,-2081,-9460,-2065,-9535,-2007,-9659,-1896,-9667,-1889,-9682,-1882,-9701,-1882,-9839,-1898,-9857,-1907,-9898,-1944,-9917,-1950,-9926,-1949,-9944,-1942,-9958,-1922,-9962,-1906]];
  step('Raising the Frankford El', () => {
    const parts = [];
    const steel = new THREE.Color(0x2a2f2b), steelDark = new THREE.Color(0x232724), railC = new THREE.Color(0x353b35);
    const boxAt = (sx, sy, sz, x, y, z, yaw, pitch, col) => {
      const g = new THREE.BoxGeometry(sx, sy, sz);
      if (pitch) g.rotateZ(pitch);
      g.rotateY(yaw);
      g.translate(x, y, z);
      parts.push({ geom: g, color: col });
    };
    for (const flat of EL_TRACK) {
      const pts = [];
      for (let i = 0; i + 3 < flat.length; i += 2) {
        const ax = flat[i], az = flat[i + 1], bx = flat[i + 2], bz = flat[i + 3];
        const n = Math.max(1, Math.round(Math.hypot(bx - ax, bz - az) / 13));
        for (let s = 0; s < n; s++) pts.push([ax + (bx - ax) * s / n, az + (bz - az) * s / n]);
      }
      pts.push([flat[flat.length - 2], flat[flat.length - 1]]);
      const ys = pts.map((p) => siteY(p[0], p[1], 'ground') + 9.2);
      for (let pass = 0; pass < 2; pass++) {           // smooth the deck profile
        const s0 = ys.slice();
        for (let i = 0; i < ys.length; i++) {
          let a = 0, n = 0;
          for (let j = Math.max(0, i - 3); j <= Math.min(ys.length - 1, i + 3); j++) { a += s0[j]; n++; }
          ys[i] = a / n;
        }
      }
      let acc = 0;                                     // portal ramp on the chain's first 170 m
      for (let i = 0; i < pts.length; i++) {
        if (i) acc += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
        if (acc >= 170) break;
        const t = smooth(10, 170, acc);
        const gy = siteY(pts[i][0], pts[i][1], 'ground');
        ys[i] = (gy - 3.4) * (1 - t) + ys[i] * t;
      }
      let bentAcc = 18;
      for (let i = 0; i + 1 < pts.length; i++) {
        const ax = pts[i][0], az = pts[i][1], bx = pts[i + 1][0], bz = pts[i + 1][1];
        const L = Math.hypot(bx - ax, bz - az);
        if (L < 0.6) continue;
        const mx = (ax + bx) / 2, mz = (az + bz) / 2, my = (ys[i] + ys[i + 1]) / 2;
        const yaw = Math.atan2(-(bz - az), bx - ax);
        const pitch = Math.atan2(ys[i + 1] - ys[i], L);
        boxAt(L + 0.55, 1.25, 8.4, mx, my - 0.62, mz, yaw, pitch, steel);       // deck
        const lx = Math.sin(yaw), lz = Math.cos(yaw);                           // lateral unit
        boxAt(L + 0.55, 0.95, 0.32, mx - lx * 3.95, my + 0.45, mz - lz * 3.95, yaw, pitch, railC);
        boxAt(L + 0.55, 0.95, 0.32, mx + lx * 3.95, my + 0.45, mz + lz * 3.95, yaw, pitch, railC);
        bentAcc += L;
        if (bentAcc >= 24) {                           // steel bents down to the street
          bentAcc = 0;
          const gy = siteY(mx, mz, 'ground');
          const top = my - 1.15;
          if (top - gy > 3.4) {
            const hcol = top - gy + 1.2;
            boxAt(0.62, hcol, 0.62, mx - lx * 3.5, gy - 0.8 + hcol / 2, mz - lz * 3.5, yaw, 0, steelDark);
            boxAt(0.62, hcol, 0.62, mx + lx * 3.5, gy - 0.8 + hcol / 2, mz + lz * 3.5, yaw, 0, steelDark);
            boxAt(0.7, 0.85, 7.9, mx, my - 1.55, mz, yaw, pitch, steelDark);    // cross girder
          }
        }
      }
    }
    const el = new THREE.Mesh(mergeColored(parts), new THREE.MeshLambertMaterial({ vertexColors: true }));
    el.castShadow = true;
    el.receiveShadow = true;
    groupCity.add(el);
  });

  step('Rolling out the SEPTA fleet', () => {
    if (!septaCanFetch) { btnTransit.style.display = 'none'; return; }
    // Night look: only the glass band + windshield glow (aGlow mask), the body
    // keeps a faint presence — a flat material-wide emissive washed every bus
    // to a solid white brick after dark.
    const bodyMat = new THREE.MeshLambertMaterial({ vertexColors: true });
    bodyMat.onBeforeCompile = (shader) => {
      shader.uniforms.uNight = nightUniform;
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nattribute float aGlow;\nvarying float vGlow;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nvGlow = aGlow;');
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', '#include <common>\nuniform float uNight;\nvarying float vGlow;')
        .replace('#include <emissivemap_fragment>',
          '#include <emissivemap_fragment>\ntotalEmissiveRadiance += (vec3(1.0, 0.85, 0.62) * vGlow * 0.8 + vec3(0.30, 0.29, 0.27) * 0.10) * uNight;');
    };
    septaMats.body = bodyMat;
    // markers are wayfinding, not scenery: no depth test, so a pin or badge is
    // never swallowed by the skyline (Mike's rule; the vehicles themselves stay
    // solid and occludable)
    // buildings occlude the fleet markers (Mike reversed the x-ray call, Aug 25 evening)
    const pinMat = new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, depthWrite: false });
    const badgeMat = new THREE.MeshBasicMaterial({ map: septaBadgeTexture(), transparent: true, depthWrite: false });
    septaSolid = new THREE.InstancedMesh(septaVehGeom(true), bodyMat, 1600);
    septaPin = new THREE.InstancedMesh(septaPinGeom(), pinMat, 1024);
    septaBadge = new THREE.InstancedMesh(new THREE.PlaneGeometry(4.6, 5.75).translate(0, 2.95, 0), badgeMat, 1024);
    for (const m of [septaSolid, septaPin, septaBadge]) {
      m.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      m.count = 0;
      m.frustumCulled = false;                         // instance bounds don't follow the fleet
      if (m !== septaBadge) {                          // the badge keeps its texture colors
        m.setColorAt(0, _sc.setRGB(1, 1, 1));          // allocates instanceColor
        m.instanceColor.setUsage(THREE.DynamicDrawUsage);
      }
    }
    septaSolid.castShadow = true;
    septaSolid.receiveShadow = true;
    septaPin.renderOrder = 12;                         // markers paint after everything
    septaBadge.renderOrder = 12;                       // transparent cutout, after the opaques
    groupCity.add(septaSolid);
    groupCity.add(septaPin);
    groupCity.add(septaBadge);
    septaReady = true;
    syncTransitBtn();
    setInterval(() => septaPoll(false), SEPTA_POLL);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) septaPoll(false); });
    septaPoll(true);
  });

  // ---------------------------------------------------------------- live Indego bike share
  // Station status from Indego's public feed (Bicycle Transit Systems' worker;
  // CORS-open, server-cached 60 s), the bike-share counterpart to the SEPTA
  // fleet: fixed docks on their real sidewalks, each rack filled with its
  // actual bikes — classic and electric — and a count badge overhead. Same
  // hostname gate as SEPTA: silently absent under the claude.ai artifact CSP.
  const INDEGO_URL = 'https://bts-status.bicycletransit.workers.dev/phl';
  const INDEGO_POLL = 60000;                        // the feed itself is cached 60 s
  const INDEGO_CAP = { st: 400, bk: 2600 };
  const INDEGO = { on: true, ok: false, fails: 0, nextT: 0 };
  const indegoSt = new Map();
  const indegoList = [];                            // badge-tile order, stable per session
  let indegoLive = [];                              // filtered draw order, rebuilt per poll
  let indegoReady = false, indegoDirty = false, indegoSolid = null, indegoBike = null, indegoBadge = null;
  let indegoTex = null, indegoCtx = null, pickedStation = null;
  const indegoPickS = [], indegoPickK = [], indegoPickB = [];
  const btnIndego = document.getElementById('btnIndego');
  const _iq = new THREE.Quaternion(), _iqB = new THREE.Quaternion();
  function indegoStationGeom() {
    // unit dock along x (1.0 scales to the rack's length); y/z in meters.
    // Platform slab + low rack spine + kiosk pylon whose screen glows at night
    // through the fleet material's aGlow term.
    const parts = [];
    const box = (sx, sy, sz, cx, cy, cz, cr, cg, cb, glow) =>
      parts.push(septaColored(new THREE.BoxGeometry(sx, sy, sz).translate(cx, cy, cz), cr, cg, cb, glow));
    box(1.0, 0.08, 2.1, 0, 0.04, 0, 0.58, 0.56, 0.51);          // platform slab
    box(0.94, 0.07, 0.12, 0, 0.34, 0, 1, 1, 1);                 // rack spine (instance color)
    box(0.02, 0.26, 0.1, -0.24, 0.17, 0, 0.45, 0.46, 0.47);     // spine legs
    box(0.02, 0.26, 0.1, 0.24, 0.17, 0, 0.45, 0.46, 0.47);
    box(0.035, 1.85, 0.42, -0.485, 0.93, 0.62, 0.5, 0.49, 0.45); // kiosk pylon
    box(0.03, 0.34, 0.3, -0.47, 1.38, 0.62, 0.95, 0.93, 0.82, 1); // kiosk screen
    return septaMerge(parts);
  }
  function indegoBikeGeom() {
    // ~90-tri parked bike facing +x: two wheels, frame tubes, seat, bars
    const parts = [];
    const wheel = (cx) => {
      const c = new THREE.CylinderGeometry(0.3, 0.3, 0.045, 7);
      c.rotateX(Math.PI / 2);
      c.translate(cx, 0.3, 0);
      parts.push(septaColored(c, 0.12, 0.12, 0.13));
    };
    wheel(-0.42);
    wheel(0.42);
    const box = (sx, sy, sz, cx, cy, cz, cr, cg, cb) =>
      parts.push(septaColored(new THREE.BoxGeometry(sx, sy, sz).translate(cx, cy, cz), cr, cg, cb));
    const g1 = new THREE.BoxGeometry(0.72, 0.055, 0.045);        // down tube, hub to hub
    g1.rotateZ(0.16);
    g1.translate(0, 0.52, 0);
    parts.push(septaColored(g1, 1, 1, 1));
    box(0.05, 0.34, 0.045, -0.34, 0.72, 0, 1, 1, 1);             // seat post
    box(0.05, 0.42, 0.045, 0.38, 0.78, 0, 1, 1, 1);              // head tube
    box(0.2, 0.045, 0.06, -0.36, 0.9, 0, 0.14, 0.14, 0.15);      // saddle
    box(0.05, 0.045, 0.42, 0.4, 1.0, 0, 0.14, 0.14, 0.15);       // handlebar
    return septaMerge(parts);
  }
  function indegoBolt(g, x, y, s) {
    g.beginPath();
    g.moveTo(x + 0.45 * s, y - 0.95 * s);
    g.lineTo(x - 0.35 * s, y + 0.12 * s);
    g.lineTo(x + 0.02 * s, y + 0.12 * s);
    g.lineTo(x - 0.3 * s, y + 0.95 * s);
    g.lineTo(x + 0.5 * s, y - 0.12 * s);
    g.lineTo(x + 0.1 * s, y - 0.12 * s);
    g.closePath();
    g.fill();
  }
  function indegoDrawTiles() {
    // one shared 128 px-tile atlas (32x16 slots), repainted whole each poll:
    // paper coin + live count, ring in Indego blue, amber bolt for e-bikes
    if (!indegoCtx) return;
    const g = indegoCtx;
    g.clearRect(0, 0, 4096, 2048);
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    for (const st of indegoList) {
      if (!indegoSt.has(st.id)) continue;
      const tx = (st.tile % 32) * 128 + 64, ty = ((st.tile / 32) | 0) * 128;
      g.strokeStyle = 'rgba(28,26,22,0.6)';
      g.fillStyle = '#fdfbf6';
      g.lineWidth = 6;
      g.beginPath();                                  // pointer tip, coin overlaps it
      g.moveTo(tx - 13, ty + 88);
      g.lineTo(tx, ty + 120);
      g.lineTo(tx + 13, ty + 88);
      g.closePath();
      g.fill();
      g.stroke();
      g.beginPath();
      g.arc(tx, ty + 48, 40, 0, Math.PI * 2);
      g.fill();
      g.strokeStyle = st.act ? (st.bikes ? '#0ea3c4' : '#98a0a4') : '#565b5e';
      g.stroke();
      g.fillStyle = '#22201c';
      const hasE = st.act && st.ebikes > 0;
      g.font = '700 44px "Montserrat", "Avenir Next", "Segoe UI", sans-serif';
      g.fillText(st.act ? String(st.bikes) : '–', tx, ty + (hasE ? 40 : 49));
      if (hasE) {
        g.fillStyle = '#b97a17';
        indegoBolt(g, tx - 12, ty + 71, 10);
        g.font = '600 24px "Montserrat", "Avenir Next", "Segoe UI", sans-serif';
        g.fillText(String(st.ebikes), tx + 10, ty + 72);
      }
    }
    indegoTex.needsUpdate = true;
  }
  function indegoGot(d) {
    const feats = d && d.features;
    if (!Array.isArray(feats) || !feats.length) { indegoFail(); return; }
    const alive = new Set();
    for (const f of feats) {
      const p = f && f.properties, c = f && f.geometry && f.geometry.coordinates;
      if (!p || !c) continue;
      const lon = +c[0], lat = +c[1];
      if (!(lat > SEPTA_BOX.la0 && lat < SEPTA_BOX.la1 && lon > SEPTA_BOX.lo0 && lon < SEPTA_BOX.lo1)) continue;
      const id = String(p.kioskId || p.id || p.name || '');
      if (!id) continue;
      alive.add(id);
      let st = indegoSt.get(id);
      if (!st) {
        if (indegoSt.size >= INDEGO_CAP.st || indegoList.length >= 512) continue;
        const x = (lon - SEPTA_GEO.lon0) * SEPTA_GEO.mx, z = -(lat - SEPTA_GEO.lat0) * SEPTA_GEO.mz;
        if (!isFinite(x) || !isFinite(z)) continue;
        // orientation only from the road grid — the surveyed position is right,
        // the dock just wants to sit parallel to its street
        const sn = septaSnapRoad(x, z, 30);
        st = { id, x, z, y: siteY(x, z, 'ground'), dx: sn ? sn[2] : 1, dz: sn ? sn[3] : 0, tile: indegoList.length };
        indegoList.push(st);
        indegoSt.set(id, st);
      }
      st.name = p.name || 'Indego Station';
      st.addr = p.addressStreet || '';
      st.bikes = +p.bikesAvailable || 0;
      st.classic = +p.classicBikesAvailable || 0;
      st.ebikes = +p.electricBikesAvailable || 0;
      st.docksOpen = +p.docksAvailable || 0;
      st.docks = +p.totalDocks || 0;
      st.act = p.kioskPublicStatus === 'Active';
      st.slots = Array.isArray(p.bikes) ? p.bikes : null;
      let bSum = 0, bN = 0;
      if (st.slots) for (const b of st.slots) if (b && b.isElectric && b.isAvailable && b.battery != null) { bSum += +b.battery || 0; bN++; }
      st.eAvg = bN ? Math.round(bSum / bN) : null;
    }
    indegoSt.forEach((st, id) => {
      if (!alive.has(id)) {
        indegoSt.delete(id);
        if (pickedStation === st) { pickedStation = null; vehinfoEl.hidden = true; }
      }
    });
    INDEGO.ok = true; INDEGO.fails = 0; INDEGO.nextT = 0;
    indegoDirty = true;
    indegoDrawTiles();
    indegoStatus();
    if (pickedStation) indegoCard(pickedStation);
  }
  function indegoFail() {
    INDEGO.fails++;
    INDEGO.nextT = performance.now() + INDEGO_POLL * Math.min(8, Math.pow(2, INDEGO.fails));
  }
  function indegoPoll(force) {
    if (!INDEGO.on || !septaCanFetch || !indegoReady) return;
    if (document.hidden && !force) return;
    if (!force && performance.now() < INDEGO.nextT) return;
    const ctl = new AbortController();
    const tm = setTimeout(() => ctl.abort(), 15000);
    fetch(INDEGO_URL, { signal: ctl.signal })
      .then((r) => (r && r.ok ? r.json() : null))
      .then((d) => { clearTimeout(tm); if (d) indegoGot(d); else indegoFail(); })
      .catch(() => { clearTimeout(tm); indegoFail(); });
  }
  function indegoCard(st) {
    const lines = [st.classic + ' Classic, ' + st.ebikes + ' Electric, ' + st.docksOpen + (st.docksOpen === 1 ? ' Dock Open' : ' Docks Open')];
    if (st.eAvg != null) lines.push('E-Bikes Average ' + st.eAvg + '% Charge');
    if (!st.act) lines.push('Station Unavailable');
    else if (!st.docksOpen) lines.push('Station Full, No Docks Open');
    if (st.addr) lines.push(st.addr);
    vehinfoBody.innerHTML =
      '<span class="vroute" style="background:#1289a8">' + (st.act ? st.bikes : '–') + '</span>' +
      '<span class="vdest">' + septaEsc(st.name) + '</span>' +
      lines.map((l) => '<div class="vmeta">' + septaEsc(l) + '</div>').join('');
  }
  function indegoStatus() {
    let bikes = 0;
    indegoSt.forEach((st) => { bikes += st.bikes; });
    btnIndego.title = 'Indego Bike Share (B): ' + bikes + ' Bikes At ' + indegoSt.size + ' Stations';
    const ic = document.getElementById('indegoCount');
    if (ic) ic.textContent = indegoSt.size ? String(bikes) : '';
  }
  function syncIndegoBtn() { btnIndego.classList.toggle('on', INDEGO.on); }
  function toggleIndego() {
    if (!septaCanFetch) return;
    INDEGO.on = !INDEGO.on;
    syncIndegoBtn();
    if (INDEGO.on) { indegoDirty = true; indegoPoll(true); }
    else if (pickedStation) { pickedStation = null; vehinfoEl.hidden = true; }
  }
  btnIndego.addEventListener('click', toggleIndego);
  function indegoRebuild() {
    // matrices move only when the data does — this runs per poll, not per frame
    indegoLive = [];
    let si = 0, ki = 0;
    for (const st of indegoList) {
      if (!indegoSt.has(st.id) || si >= INDEGO_CAP.st) continue;
      const rackL = clamp((st.docks || 12) * 0.42, 4, 20);
      st.rackL = rackL;
      const yaw = Math.atan2(-st.dz, st.dx);
      _iq.setFromAxisAngle(_sup, yaw);
      _sp.set(st.x, st.y, st.z);
      _ss.set(rackL, 1, 1);
      _sm.compose(_sp, _iq, _ss);
      indegoSolid.setMatrixAt(si, _sm);
      indegoSolid.setColorAt(si, _sc.setHex(st.act ? (st.bikes ? 0x11758c : 0x565e63) : 0x3a3f42));
      indegoPickS[si] = st;
      indegoBadge.geometry.attributes.aTile.setXY(si, (st.tile % 32) / 32, 1 - (((st.tile / 32) | 0) + 1) / 16);
      indegoPickB[si] = st;
      indegoLive.push(st);
      si++;
      if (st.slots) {
        for (const b of st.slots) {
          if (!b || ki >= INDEGO_CAP.bk) continue;
          const dn = clamp(+b.dockNumber || 1, 1, Math.max(1, st.docks || 1));
          const t = (dn - 0.5) / Math.max(1, st.docks || 1) - 0.5;
          const side = dn % 2 ? 1 : -1;
          const nx = -st.dz * side, nz = st.dx * side;
          _iq.setFromAxisAngle(_sup, Math.atan2(-nz, nx));
          _sp.set(st.x + st.dx * t * rackL + nx * 0.58, st.y + 0.06, st.z + st.dz * t * rackL + nz * 0.58);
          _ss.set(1, 1, 1);
          _sm.compose(_sp, _iq, _ss);
          indegoBike.setMatrixAt(ki, _sm);
          indegoBike.setColorAt(ki, _sc.setHex(b.isAvailable === false ? 0x4b4f52 : b.isElectric ? 0x2c8ca3 : 0x11758c));
          indegoPickK[ki] = st;
          ki++;
        }
      }
    }
    indegoSolid.count = si;
    indegoBike.count = ki;
    indegoBadge.count = si;
    indegoSolid.instanceMatrix.needsUpdate = true;
    indegoBike.instanceMatrix.needsUpdate = true;
    indegoBadge.geometry.attributes.aTile.needsUpdate = true;
    if (indegoSolid.instanceColor) indegoSolid.instanceColor.needsUpdate = true;
    if (indegoBike.instanceColor) indegoBike.instanceColor.needsUpdate = true;
  }
  function updateIndego(now, dt) {
    if (!indegoReady) return;
    if (!INDEGO.on) {
      if (indegoSolid.count || indegoBike.count || indegoBadge.count) {
        indegoSolid.count = 0; indegoBike.count = 0; indegoBadge.count = 0;
      }
      return;
    }
    if (indegoDirty) { indegoDirty = false; indegoRebuild(); }
    // badges billboard the camera every frame; no bob — docks are furniture,
    // bobbing is the vehicles' signature. Own quaternion copy: _sqB is only
    // fresh while the SEPTA layer is on.
    _iqB.copy(camera.quaternion);
    for (let i = 0; i < indegoLive.length; i++) {
      const st = indegoLive[i];
      _sp.set(st.x, st.y + 3.1, st.z);
      const s = clamp(camera.position.distanceTo(_sp) / 260, 1, 8);
      _ss.set(s, s, s);
      _sm.compose(_sp, _iqB, _ss);
      indegoBadge.setMatrixAt(i, _sm);
    }
    indegoBadge.instanceMatrix.needsUpdate = true;
    if (pickedStation) {
      _ssv.set(pickedStation.x, pickedStation.y + 6, pickedStation.z).project(camera);
      if (_ssv.z > 1 || _ssv.z < -1) vehinfoEl.style.opacity = '0';
      else {
        vehinfoEl.style.opacity = '1';
        vehinfoEl.style.transform = 'translate(-50%,-100%) translate(' +
          ((_ssv.x * 0.5 + 0.5) * window.innerWidth).toFixed(1) + 'px,' +
          ((-_ssv.y * 0.5 + 0.5) * window.innerHeight).toFixed(1) + 'px)';
      }
    }
  }
  step('Docking the Indego bikes', () => {
    if (!septaCanFetch) { btnIndego.style.display = 'none'; return; }
    const cv = document.createElement('canvas');
    cv.width = 4096; cv.height = 2048;
    indegoCtx = cv.getContext('2d');
    indegoTex = new THREE.CanvasTexture(cv);
    indegoTex.encoding = THREE.sRGBEncoding;
    indegoTex.anisotropy = 4;
    try { document.fonts.load('700 44px "Montserrat"').catch(() => {}); } catch (e) { /* stack fallback */ }
    const badgeMat = new THREE.MeshBasicMaterial({ map: indegoTex, transparent: true, depthWrite: false });  // occluded by buildings like the SEPTA markers
    badgeMat.onBeforeCompile = (shader) => {
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nattribute vec2 aTile;')
        .replace('#include <uv_vertex>', 'vUv = uv * vec2(0.03125, 0.0625) + aTile;');
    };
    const bodyMat = septaMats.body || new THREE.MeshLambertMaterial({ vertexColors: true });
    indegoSolid = new THREE.InstancedMesh(indegoStationGeom(), bodyMat, INDEGO_CAP.st);
    indegoBike = new THREE.InstancedMesh(indegoBikeGeom(), bodyMat, INDEGO_CAP.bk);
    const bg = new THREE.PlaneGeometry(4.4, 4.4).translate(0, 2.6, 0);
    const aTile = new THREE.InstancedBufferAttribute(new Float32Array(INDEGO_CAP.st * 2), 2);
    aTile.setUsage(THREE.DynamicDrawUsage);
    bg.setAttribute('aTile', aTile);
    indegoBadge = new THREE.InstancedMesh(bg, badgeMat, INDEGO_CAP.st);
    for (const m of [indegoSolid, indegoBike, indegoBadge]) {
      m.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      m.count = 0;
      m.frustumCulled = false;                        // instance bounds don't follow the docks
      if (m !== indegoBadge) {
        m.setColorAt(0, _sc.setRGB(1, 1, 1));         // allocates instanceColor
        m.instanceColor.setUsage(THREE.DynamicDrawUsage);
      }
    }
    indegoSolid.castShadow = true;
    indegoSolid.receiveShadow = true;
    indegoBike.castShadow = true;
    indegoBadge.renderOrder = 12;
    groupCity.add(indegoSolid);
    groupCity.add(indegoBike);
    groupCity.add(indegoBadge);
    indegoReady = true;
    syncIndegoBtn();
    setInterval(() => indegoPoll(false), INDEGO_POLL);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) indegoPoll(false); });
    indegoPoll(true);
  });

  step('Charting the viewpoints', () => {
    const tc = towersCenter;
    addViewpoint('The Towers from the river', () => {
      setMode(MODE.ORBIT);
      orbit.goalTarget.set(tc.x, 46, tc.z);
      orbit.goalR = 520; orbit.goalTheta = Math.PI * 0.06; orbit.goalPhi = 1.28;
    });
    addViewpoint('The plaza, on foot', () => {
      setMode(MODE.WALK);
      walk.pos.set(tc.x - 8, 1.7, tc.z + 16);
      walk.yaw = Math.atan2(tc.x + 9 - walk.pos.x, -(tc.z - 41 - walk.pos.z));
      walk.pitch = 0.3; walkSpawned = true;
    });
    addViewpoint('Aerial — the whole quarter', () => {
      setMode(MODE.ORBIT);
      orbit.goalTarget.set(tc.x - 260, 0, tc.z + 60);
      orbit.goalR = 1450; orbit.goalTheta = 0.9; orbit.goalPhi = 0.72;
    });
    const hh = findBuilding('Head House');
    if (hh) {
      const [cx, cz] = polyCentroid(hh.poly);
      addViewpoint('Head House Square', () => {
        setMode(MODE.ORBIT);
        orbit.goalTarget.set(cx, 12, cz);
        orbit.goalR = 170; orbit.goalTheta = 1.35; orbit.goalPhi = 1.1;
      });
    }
    const sp = findBuilding("Saint Peter's Church");
    if (sp) {
      const [cx, cz] = polyCentroid(sp.poly);
      addViewpoint("St. Peter's steeple", () => {
        setMode(MODE.ORBIT);
        orbit.goalTarget.set(cx, 30, cz);
        orbit.goalR = 200; orbit.goalTheta = 0.5; orbit.goalPhi = 1.05;
      });
    }
    addViewpoint("Penn's Landing", () => {
      setMode(MODE.ORBIT);
      const p = waterPoint(-140, -60);
      orbit.goalTarget.set(p[0], 10, p[1]);
      orbit.goalR = 420; orbit.goalTheta = 2.6; orbit.goalPhi = 1.15;
    });
    // the viewpoints dropdown is retired from the bar for now; the list stays
    // wired so a future UI (or __dbg) can jump to them
    const sel = document.getElementById('viewpoints');
    if (sel) {
      viewpoints.forEach((v, i) => {
        const o = document.createElement('option');
        o.value = String(i); o.textContent = v.name;
        sel.appendChild(o);
      });
      sel.addEventListener('change', () => {
        const i = parseInt(sel.value, 10);
        if (!isNaN(i) && viewpoints[i]) { interacted = true; introSpin = false; viewpoints[i].fn(); }
        sel.value = '';
        sel.blur();
      });
    }
  });

  // labels + about wiring
  const btnLabels = document.getElementById('btnLabels');
  function syncLabelsBtn() { btnLabels.classList.toggle('on', labelsOn); }
  function toggleLabels() {
    labelsOn = !labelsOn;
    syncLabelsBtn();
  }
  btnLabels.addEventListener('click', toggleLabels);
  syncLabelsBtn();
  const about = document.getElementById('about');
  function syncAboutInert() { try { about.inert = !about.classList.contains('open'); } catch (e) { } }
  function toggleAbout() { about.classList.toggle('open'); syncAboutInert(); }
  function closeAbout() { about.classList.remove('open'); syncAboutInert(); }
  syncAboutInert();
  document.getElementById('btnAbout').addEventListener('click', toggleAbout);
  document.getElementById('btnCloseAbout').addEventListener('click', closeAbout);


  // ---------------------------------------------------------------- live flights
  // Real ADS-B traffic over the city and into PHL, from the adsb.fi community
  // feed (open data, but no CORS headers), fetched through a public passthrough.
  // A personal proxy dropped into FLIGHT_PROXY takes precedence and is kinder to
  // everyone. Silent under the artifact CSP like every live layer.
  const FLIGHT_PROXY = '';
  const FLIGHT_TGT = 'https://opendata.adsb.fi/api/v2/lat/39.872/lon/-75.241/dist/30';
  // public passthroughs are individually flaky: rotate to the next on any
  // failure and stay with whichever answers (corsproxy serves only real https
  // page origins, allorigins throttles bursts; a FLIGHT_PROXY worker beats both)
  const FLIGHT_HOSTS = [
    FLIGHT_PROXY,
    'https://api.allorigins.win/raw?url=' + encodeURIComponent(FLIGHT_TGT),
    'https://corsproxy.io/?url=' + encodeURIComponent(FLIGHT_TGT),
  ].filter(Boolean);
  const FLIGHTS = { on: true, ok: false, fails: 0, nextT: 0, busy: false, host: 0 };
  const flightMap = new Map();
  let flightMesh = null, flightStrobe = null, flightReady = false, pickedPlane = null;
  const flightPick = [];
  const FLIGHT_CAP = 80;
  const btnFlights = document.getElementById('btnFlights');
  const _fq = new THREE.Quaternion(), _fe = new THREE.Euler();
  const FLIGHT_LEN = { A1: 12, A2: 24, A3: 38, A4: 48, A5: 64, A7: 12 };
  function flightGeom() {
    // ~120-tri airliner, nose toward +x, unit length 1 (instance scale = meters)
    const parts = [];
    const box = (sx, sy, sz, cx, cy, cz, r, g, b, glow, ry) => {
      const bg = new THREE.BoxGeometry(sx, sy, sz);
      if (ry) bg.rotateY(ry);
      bg.translate(cx, cy, cz);
      parts.push(septaColored(bg, r, g, b, glow || 0));
    };
    box(1.0, 0.085, 0.085, 0, 0, 0, 0.80, 0.81, 0.84);            // fuselage
    box(0.14, 0.07, 0.075, 0.47, 0.008, 0, 0.35, 0.38, 0.44);     // cockpit
    box(0.56, 0.02, 0.09, 0.03, 0.012, 0, 1, 0.93, 0.72, 1);      // cabin glow band
    box(0.15, 0.012, 0.5, 0.03, -0.02, 0.24, 0.72, 0.73, 0.76, 0, -0.5);   // wings, swept
    box(0.15, 0.012, 0.5, 0.03, -0.02, -0.24, 0.72, 0.73, 0.76, 0, 0.5);
    box(0.1, 0.045, 0.05, 0.1, -0.055, 0.17, 0.5, 0.51, 0.54);    // engines
    box(0.1, 0.045, 0.05, 0.1, -0.055, -0.17, 0.5, 0.51, 0.54);
    box(0.08, 0.01, 0.16, -0.44, 0.02, 0.09, 0.72, 0.73, 0.76, 0, -0.4);   // tailplane
    box(0.08, 0.01, 0.16, -0.44, 0.02, -0.09, 0.72, 0.73, 0.76, 0, 0.4);
    box(0.14, 0.15, 0.012, -0.45, 0.1, 0, 0.68, 0.70, 0.74, 0, 0); // fin
    return septaMerge(parts);
  }
  function flightsInit() {
    flightMesh = new THREE.InstancedMesh(flightGeom(), septaMats.body, FLIGHT_CAP);
    flightMesh.frustumCulled = false;
    flightMesh.count = 0;
    groupCity.add(flightMesh);
    const sg = new THREE.OctahedronGeometry(0.8, 0);
    flightStrobe = new THREE.InstancedMesh(sg, new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.9, depthWrite: false }), FLIGHT_CAP);
    flightStrobe.frustumCulled = false;
    flightStrobe.count = 0;
    flightStrobe.renderOrder = 12;
    groupCity.add(flightStrobe);
    flightReady = true;
  }
  function flightPoll() {
    if (!septaCanFetch || !FLIGHTS.on || FLIGHTS.busy || document.hidden) return;
    FLIGHTS.busy = true;
    fetch(FLIGHT_HOSTS[FLIGHTS.host])
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error('http ' + r.status))))
      .then((js) => {
        FLIGHTS.busy = false;
        if (!js || (!js.aircraft && !js.ac)) throw new Error('bad payload');
        FLIGHTS.ok = true;
        FLIGHTS.fails = 0;
        const seen = new Set();
        const now = performance.now();
        for (const a of (js && js.aircraft) || (js && js.ac) || []) {
          if (a.lat == null || a.lon == null) continue;
          const ground = a.alt_baro === 'ground';
          const altFt = ground ? 0 : (a.alt_geom != null ? a.alt_geom : a.alt_baro);
          if (altFt == null || altFt > 20000) continue;
          const x = (a.lon - SITE.lon) * 111320 * Math.cos(SITE.lat * DEG);
          const z = -(a.lat - SITE.lat) * 110574;
          if (x < -12500 || x > 17000 || z < -22000 || z > 10000) continue;
          const hex = a.hex || (a.flight || '').trim();
          if (!hex) continue;
          seen.add(hex);
          let p = flightMap.get(hex);
          if (!p) { p = { hex }; flightMap.set(hex, p); }
          p.ground = ground;
          p.fy = ground ? siteY(x, z, 'ground') + 1.2 : altFt * 0.3048 - 8.34;
          p.fx = x; p.fz = z; p.ft = now;
          const tr = (a.track != null ? a.track : (a.true_heading != null ? a.true_heading : (p.trk || 0)));
          p.trk = tr;
          const gms = (a.gs || 0) * 0.5144;
          p.vx = Math.sin(tr * DEG) * gms;
          p.vz = -Math.cos(tr * DEG) * gms;
          p.vy = ground ? 0 : ((a.geom_rate != null ? a.geom_rate : (a.baro_rate || 0)) * 0.00508);
          p.gs = a.gs || 0;
          p.call = (a.flight || '').trim() || (a.r || '').trim() || hex.toUpperCase();
          p.type = (a.desc || a.t || 'Aircraft');
          p.op = a.ownOp || '';
          p.len = FLIGHT_LEN[a.category] || (a.category === 'A0' ? 20 : 32);
          p.landed = false;
          if (p.dx === undefined || Math.hypot(x - p.dx, z - p.dz) > 3200) { p.dx = x; p.dz = z; p.dy = p.fy; }
        }
        for (const [hex, p] of flightMap) if (!seen.has(hex)) { flightMap.delete(hex); if (pickedPlane === p) { pickedPlane = null; vehinfoEl.hidden = true; } }
        flightStatus();
      })
      .catch(() => { FLIGHTS.busy = false; FLIGHTS.fails++; FLIGHTS.host = (FLIGHTS.host + 1) % FLIGHT_HOSTS.length; FLIGHTS.nextT = performance.now() + (FLIGHTS.fails > FLIGHT_HOSTS.length * 3 ? 180000 : 8000); });
  }
  function flightTest() {
    const now = performance.now();
    const mk = (hex, x, z, altFt, trk, gs, vr, call, type, op, len, ground) => {
      const p = { hex, ground: !!ground, fx: x, fz: z, ft: now,
        fy: ground ? siteY(x, z, 'ground') + 1.2 : altFt * 0.3048 - 8.34,
        trk, gs, vx: Math.sin(trk * DEG) * gs * 0.5144, vz: -Math.cos(trk * DEG) * gs * 0.5144,
        vy: ground ? 0 : vr * 0.00508, call, type, op, len, dx: x, dz: z };
      p.dy = p.fy;
      flightMap.set(hex, p);
    };
    mk('test1', 1200, 900, 1800, 262, 145, -700, 'AAL1776', 'Airbus A321', 'American Airlines', 44);
    mk('test2', -300, -600, 4200, 45, 250, 1400, 'UAL88', 'Boeing 737-800', 'United Airlines', 39);
    mk('test3', -8200, 7700, 0, 90, 12, 0, 'DAL401', 'Boeing 757-200', 'Delta Air Lines', 47, true);
    flightStatus();
    return flightMap.size;
  }
  function flightStatus() {
    if (!btnFlights) return;
    btnFlights.title = 'Live Flights (X): ' + flightMap.size + ' Aircraft Tracked';
    const fc = document.getElementById('flightCount');
    if (fc) fc.textContent = flightMap.size ? String(flightMap.size) : '';
  }
  function flightCard(p) {
    const alt = p.ground ? 'On The Ground' : Math.round((p.dy + 8.34) / 0.3048 / 25) * 25 + ' ft, ' +
      (p.vy > 2 ? 'Climbing' : p.vy < -2 ? 'Descending' : 'Level');
    vehinfoBody.innerHTML =
      '<span class="vroute" style="background:#3a6ea5">' + septaEsc(p.call) + '</span>' +
      '<span class="vdest">' + septaEsc(p.type) + '</span>' +
      (p.op ? '<div class="vmeta">' + septaEsc(p.op) + '</div>' : '') +
      '<div class="vmeta">' + septaEsc(alt + ', ' + Math.round(p.gs) + ' kt') + '</div>' +
      (p.est ? '<div class="vmeta">Estimated Track, Awaiting Signal</div>' : '');
  }
  function syncFlightsBtn() { if (btnFlights) btnFlights.classList.toggle('on', FLIGHTS.on); }
  function toggleFlights() {
    if (!septaCanFetch) return;
    FLIGHTS.on = !FLIGHTS.on;
    syncFlightsBtn();
    if (FLIGHTS.on) { FLIGHTS.nextT = 0; }
    else if (pickedPlane) { pickedPlane = null; vehinfoEl.hidden = true; }
  }
  if (btnFlights) btnFlights.addEventListener('click', toggleFlights);
  syncFlightsBtn();
  function updateFlights(now, dt) {
    if (!septaCanFetch) { if (btnFlights) btnFlights.style.display = 'none'; return; }
    if (!flightReady) { if (septaMats.body) flightsInit(); return; }
    if (now >= FLIGHTS.nextT) {
      FLIGHTS.nextT = now + (FLIGHT_PROXY && FLIGHTS.host === 0 ? 10000 : 90000);
      flightPoll();
    }
    if (!FLIGHTS.on) {
      if (flightMesh.count) { flightMesh.count = 0; flightStrobe.count = 0; flightMesh.instanceMatrix.needsUpdate = true; flightStrobe.instanceMatrix.needsUpdate = true; }
      return;
    }
    let i = 0;
    const night = nightUniform.value;
    const gone = [];
    for (const p of flightMap.values()) {
      if (i >= FLIGHT_CAP) break;
      // dead reckoning: jets cross a block between polls, so fly the last known
      // velocity and ease toward each fresh fix. The feed can go quiet for
      // minutes behind the public passthroughs, so planes KEEP FLYING their
      // track instead of freezing: arrivals settle onto the field, everything
      // else exits the model, and long-stale traffic despawns.
      const age = (now - p.ft) / 1000;
      if (age > 300) { gone.push(p.hex); continue; }
      let px = p.fx + p.vx * age, pz = p.fz + p.vz * age, py = p.fy + p.vy * age;
      if (px < -12500 || px > 17000 || pz < -22000 || pz > 10000) { gone.push(p.hex); continue; }
      if (!p.ground) {
        const gY = siteY(px, pz, 'ground');
        if (py <= gY + 7) { py = gY + 5; p.landed = true; }
        if (p.landed && age > 90) { gone.push(p.hex); continue; }
      }
      const k = 1 - Math.exp(-dt / 0.8);
      p.dx += (px - p.dx) * k;
      p.dz += (pz - p.dz) * k;
      p.dy += (py - p.dy) * k;
      p.est = age > 25;
      const yaw = Math.atan2(-p.vz, p.vx) || 0;
      const pitch = (p.ground || p.landed) ? 0 : clamp(Math.atan2(p.vy, Math.max(30, Math.hypot(p.vx, p.vz))), -0.21, 0.21);
      _fe.set(0, yaw, pitch, 'YZX');
      _fq.setFromEuler(_fe);
      _sp.set(p.dx, p.dy, p.dz);
      _ss.set(p.len, p.len, p.len);
      _sm.compose(_sp, _fq, _ss);
      flightMesh.setMatrixAt(i, _sm);
      flightPick[i] = p;
      // white anti-collision strobe: a sharp double-blink, phase by airframe
      const ph = ((now * 0.001 + ((parseInt(String(p.hex).replace(/[^0-9a-z]/gi, ''), 36) || 0) % 97) * 0.13) % 1.2) / 1.2;
      const blink = (ph < 0.05 || (ph > 0.12 && ph < 0.17)) ? 1 : 0;
      const ssc = blink * (1.2 + 2.2 * night) * Math.max(0.6, p.len / 32);
      _sp.set(p.dx, p.dy + 0.5, p.dz);
      _ss.set(ssc || 0.0001, ssc || 0.0001, ssc || 0.0001);
      _sm.compose(_sp, _fq, _ss);
      flightStrobe.setMatrixAt(i, _sm);
      i++;
    }
    if (gone.length) {
      for (const hx of gone) { const p = flightMap.get(hx); flightMap.delete(hx); if (pickedPlane === p) { pickedPlane = null; vehinfoEl.hidden = true; } }
      flightStatus();
    }
    flightMesh.count = i;
    flightStrobe.count = i;
    flightMesh.instanceMatrix.needsUpdate = true;
    flightStrobe.instanceMatrix.needsUpdate = true;
    if (pickedPlane) {
      flightCard(pickedPlane);
      _ssv.set(pickedPlane.dx, pickedPlane.dy + pickedPlane.len * 0.12 + 6, pickedPlane.dz).project(camera);
      if (_ssv.z > 1 || _ssv.z < -1) vehinfoEl.style.opacity = '0';
      else {
        vehinfoEl.style.opacity = '1';
        vehinfoEl.style.transform = 'translate(-50%,-100%) translate(' +
          ((_ssv.x * 0.5 + 0.5) * window.innerWidth).toFixed(1) + 'px,' +
          ((-_ssv.y * 0.5 + 0.5) * window.innerHeight).toFixed(1) + 'px)';
      }
    }
  }


  // ---------------------------------------------------------------- live ships
  // Real AIS traffic on the rivers via the aisstream.io WebSocket (free key,
  // and WebSockets have no CORS wall, so the page connects DIRECTLY — no
  // passthrough needed, unlike the flight feed). The layer stays hidden until
  // a key is pasted into AIS_KEY. Ships dead-reckon between reports (they are
  // slow, so a few-second cadence renders glassy smooth), moored and anchored
  // vessels hold station, and the card knows a tug from a tanker.
  const AIS_KEY = '';
  const SHIPS = { on: true, ok: false, sock: null, retryT: 0 };
  const shipMap = new Map();
  let shipMesh = null, shipReady = false, pickedShip = null;
  const shipPick = [];
  const SHIP_CAP = 48;
  const btnShips = document.getElementById('btnShips');
  const SHIP_TYPE = (t) => t >= 80 && t < 90 ? ['Tanker', 0x2e2e33] : t >= 70 && t < 80 ? ['Cargo Ship', 0x5a3a34]
    : t >= 60 && t < 70 ? ['Passenger Vessel', 0x8a8d92] : (t === 31 || t === 32 || t === 52) ? ['Tug', 0x3d5a3f]
    : t === 30 ? ['Fishing Vessel', 0x4a5560] : (t === 36 || t === 37) ? ['Pleasure Craft', 0x8f8f88]
    : t === 35 ? ['Military Vessel', 0x4c4f45] : ['Vessel', 0x555a60];
  function shipGeom() {
    // unit hull: length 1 along +x, unit beam along z, scaled per instance
    const parts = [];
    const box = (sx, sy, sz, cx, cy, cz, r, g, b, glow, ry) => {
      const bg = new THREE.BoxGeometry(sx, sy, sz);
      if (ry) bg.rotateY(ry);
      bg.translate(cx, cy, cz);
      parts.push(septaColored(bg, r, g, b, glow || 0));
    };
    // no rotated parts: a rotation baked before the per-instance non-uniform
    // scale (length x beam) shears into a detached blade — the bow tapers in
    // axis-aligned steps instead
    box(0.85, 0.5, 1.0, -0.075, 0.13, 0, 0.15, 0.16, 0.18);       // hull
    box(0.10, 0.5, 0.72, 0.40, 0.13, 0, 0.15, 0.16, 0.18);        // bow step 1
    box(0.06, 0.46, 0.4, 0.475, 0.15, 0, 0.15, 0.16, 0.18);       // bow step 2
    box(0.86, 0.06, 1.01, -0.07, 0.02, 0, 0.45, 0.16, 0.13);      // waterline stripe
    box(0.5, 0.3, 0.8, 0.03, 0.5, 0, 0.38, 0.36, 0.33);           // deck cargo block
    box(0.16, 0.5, 0.7, -0.36, 0.55, 0, 0.78, 0.78, 0.76);        // superstructure
    box(0.17, 0.09, 0.72, -0.36, 0.77, 0, 1, 0.93, 0.72, 1);      // bridge glow band
    box(0.06, 0.2, 0.28, -0.41, 0.9, 0, 0.2, 0.2, 0.22);          // funnel
    box(0.03, 0.05, 0.05, 0.44, 0.45, 0, 1, 0.95, 0.8, 1);        // masthead light
    return septaMerge(parts);
  }
  function shipsInit() {
    shipMesh = new THREE.InstancedMesh(shipGeom(), septaMats.body, SHIP_CAP);
    shipMesh.frustumCulled = false;
    shipMesh.count = 0;
    groupCity.add(shipMesh);
    shipReady = true;
  }
  function shipMsg(ev) {
    let d;
    try { d = JSON.parse(ev.data); } catch (e) { return; }
    const meta = d.MetaData || {};
    const mmsi = meta.MMSI;
    if (!mmsi) return;
    let v = shipMap.get(mmsi);
    if (!v) { v = { mmsi, len: 30, beam: 8, tn: 'Vessel', hull: 0x555a60, sog: 0, cog: 0, moored: false }; shipMap.set(mmsi, v); }
    if (meta.ShipName && meta.ShipName.trim()) v.name = meta.ShipName.trim();
    if (d.MessageType === 'PositionReport' && d.Message && d.Message.PositionReport) {
      const m = d.Message.PositionReport;
      const x = (m.Longitude - SITE.lon) * 111320 * Math.cos(SITE.lat * DEG);
      const z = -(m.Latitude - SITE.lat) * 110574;
      if (x < -12500 || x > 17000 || z < -22000 || z > 10000) return;
      v.fx = x; v.fz = z; v.ft = performance.now();
      v.sog = m.Sog || 0;
      const hd = (m.TrueHeading != null && m.TrueHeading < 360) ? m.TrueHeading : (m.Cog != null ? m.Cog : v.cog);
      v.cog = m.Cog != null ? m.Cog : hd;
      v.hdg = hd;
      v.moored = m.NavigationalStatus === 1 || m.NavigationalStatus === 5 || v.sog < 0.25;
      const gms = v.sog * 0.5144;
      v.vx = Math.sin((v.cog || 0) * DEG) * gms;
      v.vz = -Math.cos((v.cog || 0) * DEG) * gms;
      if (v.dx === undefined || Math.hypot(x - v.dx, z - v.dz) > 1500) { v.dx = x; v.dz = z; }
      SHIPS.ok = true;
    } else if (d.MessageType === 'ShipStaticData' && d.Message && d.Message.ShipStaticData) {
      const s = d.Message.ShipStaticData;
      if (s.Name && s.Name.trim()) v.name = s.Name.trim();
      if (s.Dimension) {
        const L = (s.Dimension.A || 0) + (s.Dimension.B || 0), B = (s.Dimension.C || 0) + (s.Dimension.D || 0);
        if (L > 4) v.len = clamp(L, 8, 340);
        if (B > 1) v.beam = clamp(B, 3, 52);
      }
      if (s.Type) { const [tn, hull] = SHIP_TYPE(s.Type); v.tn = tn; v.hull = hull; }
      if (s.Destination && s.Destination.trim()) v.dest = s.Destination.trim();
    }
  }
  function shipConnect() {
    if (!AIS_KEY || !septaCanFetch || SHIPS.sock) return;
    try {
      const ws = new WebSocket('wss://stream.aisstream.io/v0/stream');
      SHIPS.sock = ws;
      ws.onopen = () => {
        try {
          ws.send(JSON.stringify({ APIKey: AIS_KEY, BoundingBoxes: [[[39.80, -75.45], [40.08, -74.82]]], FilterMessageTypes: ['PositionReport', 'ShipStaticData'] }));
        } catch (e) { /* closed */ }
      };
      ws.onmessage = shipMsg;
      ws.onclose = () => { SHIPS.sock = null; SHIPS.retryT = performance.now() + 30000; };
      ws.onerror = () => { try { ws.close(); } catch (e) {} };
    } catch (e) {
      SHIPS.sock = null;
      SHIPS.retryT = performance.now() + 60000;
    }
  }
  function shipTest() {
    const now = performance.now();
    const mk = (mmsi, x, z, hdg, sog, len, beam, name, tn, hull, dest, moored) => {
      const gms = sog * 0.5144;
      shipMap.set(mmsi, { mmsi, fx: x, fz: z, ft: now, dx: x, dz: z, sog, cog: hdg, hdg,
        vx: Math.sin(hdg * DEG) * gms, vz: -Math.cos(hdg * DEG) * gms,
        len, beam, name, tn, hull, dest, moored: !!moored });
    };
    mk(1001, 620, -250, 12, 9, 182, 28, 'MSC ALTAIR', 'Cargo Ship', 0x5a3a34, 'PHILADELPHIA');
    mk(1002, 680, 2500, 195, 5, 28, 9, 'DELAWARE RESPONDER', 'Tug', 0x3d5a3f, 'ASSIST');
    mk(1003, 760, 1400, 90, 0, 224, 32, 'OVERSEAS LUNA', 'Tanker', 0x2e2e33, 'PAULSBORO', true);
    shipStatus();
    return shipMap.size;
  }
  function shipStatus() {
    if (!btnShips) return;
    btnShips.title = 'Live Ships (H): ' + shipMap.size + ' Vessels Tracked';
    const sc = document.getElementById('shipCount');
    if (sc) sc.textContent = shipMap.size ? String(shipMap.size) : '';
  }
  function shipCard(v) {
    const move = v.moored ? 'Moored' : Math.round(v.sog * 10) / 10 + ' kt';
    vehinfoBody.innerHTML =
      '<span class="vroute" style="background:#1f4f7a">' + septaEsc(v.tn) + '</span>' +
      '<span class="vdest">' + septaEsc(v.name || 'MMSI ' + v.mmsi) + '</span>' +
      '<div class="vmeta">' + septaEsc(move + ', ' + Math.round(v.len) + ' m') + '</div>' +
      (v.dest ? '<div class="vmeta">' + septaEsc('Bound For ' + v.dest) + '</div>' : '');
  }
  function syncShipsBtn() { if (btnShips) btnShips.classList.toggle('on', SHIPS.on); }
  function toggleShips() {
    if (!AIS_KEY || !septaCanFetch) return;
    SHIPS.on = !SHIPS.on;
    syncShipsBtn();
    if (!SHIPS.on && pickedShip) { pickedShip = null; vehinfoEl.hidden = true; }
  }
  if (btnShips) btnShips.addEventListener('click', toggleShips);
  syncShipsBtn();
  function updateShips(now, dt) {
    if (!btnShips) return;
    if (!shipReady) { if (septaMats.body) shipsInit(); return; }
    // without a key the layer stays out of the panel, but injected test
    // vessels (__dbg.shipTest) still render so the pipeline stays provable
    if (!AIS_KEY || !septaCanFetch) { btnShips.style.display = 'none'; if (!shipMap.size) return; }
    if (!SHIPS.sock && now >= SHIPS.retryT) shipConnect();
    if (!SHIPS.on) {
      if (shipMesh.count) { shipMesh.count = 0; shipMesh.instanceMatrix.needsUpdate = true; }
      return;
    }
    let i = 0;
    const gone = [];
    for (const v of shipMap.values()) {
      if (i >= SHIP_CAP) break;
      if (v.dx === undefined) continue;
      const age = (now - v.ft) / 1000;
      if (age > 1800) { gone.push(v.mmsi); continue; }
      const px = v.moored ? v.fx : v.fx + v.vx * Math.min(age, 600);
      const pz = v.moored ? v.fz : v.fz + v.vz * Math.min(age, 600);
      if (px < -12500 || px > 17000 || pz < -22000 || pz > 10000) { gone.push(v.mmsi); continue; }
      const k = 1 - Math.exp(-dt / 1.6);
      v.dx += (px - v.dx) * k;
      v.dz += (pz - v.dz) * k;
      const hd = (v.hdg != null && v.hdg < 360) ? v.hdg : v.cog;
      const hx = Math.sin(hd * DEG), hz = -Math.cos(hd * DEG);
      _fe.set(0, Math.atan2(-hz, hx), 0, 'YZX');
      _fq.setFromEuler(_fe);
      _sp.set(v.dx, TERRAIN.water + 0.1, v.dz);
      _ss.set(v.len, clamp(v.len * 0.09, 2.5, 16), v.beam);
      _sm.compose(_sp, _fq, _ss);
      shipMesh.setMatrixAt(i, _sm);
      shipMesh.setColorAt(i, _sc.setRGB(1, 1, 1));   // neutral: the geometry carries its own scheme
      shipPick[i] = v;
      i++;
    }
    if (gone.length) {
      for (const g of gone) { const v = shipMap.get(g); shipMap.delete(g); if (pickedShip === v) { pickedShip = null; vehinfoEl.hidden = true; } }
      shipStatus();
    }
    shipMesh.count = i;
    shipMesh.instanceMatrix.needsUpdate = true;
    if (shipMesh.instanceColor) shipMesh.instanceColor.needsUpdate = true;
    if (pickedShip) {
      shipCard(pickedShip);
      _ssv.set(pickedShip.dx, TERRAIN.water + clamp(pickedShip.len * 0.09, 2.5, 16) + 6, pickedShip.dz).project(camera);
      if (_ssv.z > 1 || _ssv.z < -1) vehinfoEl.style.opacity = '0';
      else {
        vehinfoEl.style.opacity = '1';
        vehinfoEl.style.transform = 'translate(-50%,-100%) translate(' +
          ((_ssv.x * 0.5 + 0.5) * window.innerWidth).toFixed(1) + 'px,' +
          ((-_ssv.y * 0.5 + 0.5) * window.innerHeight).toFixed(1) + 'px)';
      }
    }
  }

  // ---------------------------------------------------------------- solar clock
  // NOAA solar position for the towers' latitude/longitude; Philadelphia local
  // time with US daylight-saving rules. Drives sun, sky, fog, and the lit windows.
  const SITE = { lat: 39.9455, lon: -75.1447 };
  const DEG = Math.PI / 180;
  function nthSunday(year, month0, nth) { // month0: 0-based; returns UTC ms at 02:00 local-ish (date part only matters)
    const first = new Date(Date.UTC(year, month0, 1));
    const dow = first.getUTCDay();
    const day = 1 + ((7 - dow) % 7) + (nth - 1) * 7;
    return Date.UTC(year, month0, day);
  }
  function tzOffsetMin(y, m, d) { // minutes to add to UTC to get Philadelphia local time
    const t = Date.UTC(y, m - 1, d);
    const start = nthSunday(y, 2, 2), end = nthSunday(y, 10, 1);
    return (t >= start && t < end) ? -240 : -300;
  }
  function solar(utcMs) {
    const JD = utcMs / 86400000 + 2440587.5;
    const T = (JD - 2451545) / 36525;
    const L0 = ((280.46646 + T * (36000.76983 + T * 0.0003032)) % 360 + 360) % 360;
    const M = 357.52911 + T * (35999.05029 - 0.0001537 * T);
    const e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T);
    const C = Math.sin(M * DEG) * (1.914602 - T * (0.004817 + 0.000014 * T)) + Math.sin(2 * M * DEG) * (0.019993 - 0.000101 * T) + Math.sin(3 * M * DEG) * 0.000289;
    const omega = 125.04 - 1934.136 * T;
    const lambda = L0 + C - 0.00569 - 0.00478 * Math.sin(omega * DEG);
    const eps0 = 23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60) / 60;
    const eps = eps0 + 0.00256 * Math.cos(omega * DEG);
    const dec = Math.asin(Math.sin(eps * DEG) * Math.sin(lambda * DEG));
    const y = Math.tan(eps * DEG / 2) ** 2;
    const eot = 4 * (y * Math.sin(2 * L0 * DEG) - 2 * e * Math.sin(M * DEG) + 4 * e * y * Math.sin(M * DEG) * Math.cos(2 * L0 * DEG) - 0.5 * y * y * Math.sin(4 * L0 * DEG) - 1.25 * e * e * Math.sin(2 * M * DEG)) / DEG;
    const utcMin = (utcMs / 60000) % 1440;
    const tst = (utcMin + eot + 4 * SITE.lon + 1440) % 1440;
    const H = (tst / 4 - 180) * DEG;
    const lat = SITE.lat * DEG;
    const E = -Math.cos(dec) * Math.sin(H);
    const N = Math.sin(dec) * Math.cos(lat) - Math.cos(dec) * Math.cos(H) * Math.sin(lat);
    const U = Math.sin(dec) * Math.sin(lat) + Math.cos(dec) * Math.cos(H) * Math.cos(lat);
    return { elev: Math.asin(clamp(U, -1, 1)) / DEG, dir: new V3(E, U, -N).normalize() };
  }
  // the real Moon over Philadelphia: Schlyter's lunar theory (position to ~1-2
  // arcmin here, plenty for a sky disc), topocentric, plus phase from the
  // Sun-Moon elongation. Same az/el -> world mapping as solar().
  function lunar(utcMs) {
    const R = DEG;
    // Schlyter's epoch is "2000 Jan 0.0" = 1999-12-31 00:00 UT, NOT J2000.0 —
    // the 1.5 day difference is a 20 degree lunar longitude error
    const d = utcMs / 86400000 - 10956.0;
    const rev = (a) => ((a % 360) + 360) % 360;
    const Nm = rev(125.1228 - 0.0529538083 * d);
    const im = 5.1454 * R;
    const wm = rev(318.0634 + 0.1643573223 * d);
    const em = 0.0549;
    const Mm = rev(115.3654 + 13.0649929509 * d);
    const ws = rev(282.9404 + 4.70935e-5 * d);
    const Ms = rev(356.047 + 0.9856002585 * d);
    let E = Mm + (em / R) * Math.sin(Mm * R) * (1 + em * Math.cos(Mm * R));
    for (let i = 0; i < 4; i++) E = E - (E - (em / R) * Math.sin(E * R) - Mm) / (1 - em * Math.cos(E * R));
    const xv = 60.2666 * (Math.cos(E * R) - em);
    const yv = 60.2666 * Math.sqrt(1 - em * em) * Math.sin(E * R);
    const v = Math.atan2(yv, xv) / R;
    let r = Math.sqrt(xv * xv + yv * yv);
    const u = (v + wm) * R;
    const xh = r * (Math.cos(Nm * R) * Math.cos(u) - Math.sin(Nm * R) * Math.sin(u) * Math.cos(im));
    const yh = r * (Math.sin(Nm * R) * Math.cos(u) + Math.cos(Nm * R) * Math.sin(u) * Math.cos(im));
    const zh = r * Math.sin(u) * Math.sin(im);
    let lon = Math.atan2(yh, xh) / R;
    let lat = Math.atan2(zh, Math.sqrt(xh * xh + yh * yh)) / R;
    // the Sun's true longitude (for perturbations and phase)
    let Es = Ms + (0.016709 / R) * Math.sin(Ms * R) * (1 + 0.016709 * Math.cos(Ms * R));
    const xs = Math.cos(Es * R) - 0.016709, ys = Math.sqrt(1 - 0.016709 * 0.016709) * Math.sin(Es * R);
    const slon = rev(Math.atan2(ys, xs) / R + ws);
    // major lunar perturbations (Schlyter's series; D and the sidereal base use
    // the Sun's MEAN longitude, the phase uses the true one)
    const Lsun = rev(Ms + ws);
    const Lm = rev(Mm + wm + Nm), D2 = rev(Lm - Lsun), F = rev(Lm - Nm);
    lon += -1.274 * Math.sin((Mm - 2 * D2) * R) + 0.658 * Math.sin(2 * D2 * R) - 0.186 * Math.sin(Ms * R)
         - 0.059 * Math.sin((2 * Mm - 2 * D2) * R) - 0.057 * Math.sin((Mm - 2 * D2 + Ms) * R)
         + 0.053 * Math.sin((Mm + 2 * D2) * R) + 0.046 * Math.sin((2 * D2 - Ms) * R)
         + 0.041 * Math.sin((Mm - Ms) * R) - 0.035 * Math.sin(D2 * R) - 0.031 * Math.sin((Mm + Ms) * R)
         - 0.015 * Math.sin((2 * F - 2 * D2) * R) + 0.011 * Math.sin((Mm - 4 * D2) * R);
    lat += -0.173 * Math.sin((F - 2 * D2) * R) - 0.055 * Math.sin((Mm - F - 2 * D2) * R)
         - 0.046 * Math.sin((Mm + F - 2 * D2) * R) + 0.033 * Math.sin((F + 2 * D2) * R) + 0.017 * Math.sin((2 * Mm + F) * R);
    r += -0.58 * Math.cos((Mm - 2 * D2) * R) - 0.46 * Math.cos(2 * D2 * R);
    const ecl = (23.4393 - 3.563e-7 * d) * R;
    const xg = Math.cos(lon * R) * Math.cos(lat * R), yg = Math.sin(lon * R) * Math.cos(lat * R), zg = Math.sin(lat * R);
    const xe = xg, ye = yg * Math.cos(ecl) - zg * Math.sin(ecl), ze = yg * Math.sin(ecl) + zg * Math.cos(ecl);
    const ra = rev(Math.atan2(ye, xe) / R), dec = Math.atan2(ze, Math.sqrt(xe * xe + ye * ye)) / R;
    const utH = ((utcMs % 86400000) + 86400000) % 86400000 / 3600000;
    const LSTdeg = rev(rev(Lsun + 180) + utH * 15 + SITE.lon);
    let ha = LSTdeg - ra;
    ha = ((ha % 360) + 540) % 360 - 180;
    const lat0 = SITE.lat * R;
    const sinEl = Math.sin(lat0) * Math.sin(dec * R) + Math.cos(lat0) * Math.cos(dec * R) * Math.cos(ha * R);
    let el = Math.asin(clamp(sinEl, -1, 1));
    el -= Math.asin(1 / r) * Math.cos(el);                    // topocentric parallax
    const Ea = -Math.cos(dec * R) * Math.sin(ha * R);
    const Na = Math.sin(dec * R) * Math.cos(lat0) - Math.cos(dec * R) * Math.cos(ha * R) * Math.sin(lat0);
    const az = rev(Math.atan2(Ea, Na) / R);
    const dir = new V3(Math.sin(az * R) * Math.cos(el), Math.sin(el), -Math.cos(az * R) * Math.cos(el)).normalize();
    const elong = Math.acos(clamp(Math.cos(lat * R) * Math.cos((lon - slon) * R), -1, 1));
    return { dir, el: el / R, az, k: (1 - Math.cos(elong)) / 2, wax: Math.sin((lon - slon) * R) > 0 };
  }
  const clock = { y: 2026, m: 8, d: 23, minutes: 720, live: true };
  function clockUtcMs(c, minutes) { return Date.UTC(c.y, c.m - 1, c.d) + (minutes - tzOffsetMin(c.y, c.m, c.d)) * 60000; }
  function setClockToNow() {
    const now = new Date();
    const guessOff = tzOffsetMin(now.getUTCFullYear(), now.getUTCMonth() + 1, now.getUTCDate());
    const loc = new Date(now.getTime() + guessOff * 60000);
    clock.y = loc.getUTCFullYear(); clock.m = loc.getUTCMonth() + 1; clock.d = loc.getUTCDate();
    clock.minutes = loc.getUTCHours() * 60 + loc.getUTCMinutes();
  }
  function sunTimes(c) { // local minutes of sunrise / sunset (elevation crossing -0.833 deg)
    let rise = null, set = null, prev = null;
    for (let mnt = 0; mnt <= 1440; mnt += 2) {
      const el = solar(clockUtcMs(c, mnt)).elev;
      if (prev !== null) {
        if (prev < -0.833 && el >= -0.833) rise = mnt;
        if (prev >= -0.833 && el < -0.833) set = mnt;
      }
      prev = el;
    }
    return { rise, set };
  }
  function fmtTime(mnt) {
    if (mnt == null) return '';
    let h = Math.floor(mnt / 60) % 24; const mm = Math.round(mnt % 60);
    const ap = h >= 12 ? 'PM' : 'AM'; h = h % 12; if (h === 0) h = 12;
    return h + ':' + (mm < 10 ? '0' : '') + mm + ' ' + ap;
  }
  // ---- live weather (Open-Meteo). The claude.ai artifact sandbox blocks external
  // fetches, so there we keep the fair-weather default; on GitHub Pages / local it
  // pulls real Philadelphia cloud cover + wind every 15 minutes.
  // (WX itself is declared before the sky material — refreshEnv reads it at init.)
  function applyWx(js) {
    const cur = js && js.current;
    if (!cur) return;
    WX.cover = clamp((cur.cloud_cover == null ? 22 : cur.cloud_cover) / 100, 0, 1);
    if ((cur.precipitation || 0) > 0.1) WX.cover = Math.max(WX.cover, 0.85);
    const spd = (cur.wind_speed_10m == null ? 8 : cur.wind_speed_10m) / 3.6;
    const dir = ((cur.wind_direction_10m == null ? 250 : cur.wind_direction_10m) + 180) * Math.PI / 180;
    const drift = 0.0008 + spd * 0.00035;
    wxWind.set(Math.sin(dir) * drift, -Math.cos(dir) * drift);
    // the water chop follows the real wind: calm glass at 0, whitecap energy by ~9 m/s
    waterU.uWAmp.value = clamp(0.5 + spd * 0.14, 0.5, 1.8);
    waterU.uWDir.value.set(Math.sin(dir) || 0.86, -Math.cos(dir) || 0.5);
    WX.ok = true;
    lastEnvEl = 999;   // rebake glass reflections with the new cloud deck
    refreshTimeUI();
  }
  const wxCanFetch = !/claude|usercontent/i.test(location.hostname);
  function fetchWeather() {
    if (!wxCanFetch) return;
    try {
      fetch('https://api.open-meteo.com/v1/forecast?latitude=39.9455&longitude=-75.1447&current=cloud_cover,precipitation,weather_code,wind_speed_10m,wind_direction_10m')
        .then(r => (r && r.ok ? r.json() : null))
        .then(applyWx)
        .catch(() => {});
    } catch (e) { /* sandboxed */ }
  }
  const PAL = {
    night: { z: new THREE.Color(0x070c1a), h: new THREE.Color(0x121a2e), g: new THREE.Color(0x0a0a0e) },
    twi: { z: new THREE.Color(0x34456e), h: new THREE.Color(0xf3a468), g: new THREE.Color(0x3a322c) },
    day: { z: new THREE.Color(COLORS.skyZenith), h: new THREE.Color(COLORS.skyHorizon), g: new THREE.Color(COLORS.skyGround) },
  };
  const moonDir = new V3(0.35, 0.62, 0.45).normalize();   // live lunar position (applyLighting)
  const moonHigh = new V3(0.35, 0.62, 0.45).normalize();  // moonless-night fill direction
  const glintDir = new V3(0.3, 0.8, 0.2);                 // what the water sparkles toward
  const _vA = new THREE.Vector3();
  let moonNow = { el: -90, az: 0, k: 0.5, wax: true };
  let lastEnvEl = 999;
  const _c1 = new THREE.Color(), _c2 = new THREE.Color();
  const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
  function applyLighting() {
    const sp = solar(clockUtcMs(clock, clock.minutes));
    const mp = lunar(clockUtcMs(clock, clock.minutes));
    moonNow = mp;
    moonDir.copy(mp.dir);
    const el = sp.elev;
    const dayF = smooth(-4, 10, el);
    const twi = Math.exp(-Math.pow((el + 1) / 7, 2)) * (1 - dayF * 0.6);
    const night = 1 - smooth(-9, 1, el);
    if (el > -3) {
      sunDir.copy(sp.dir);
      sun.intensity = 1.7 * smooth(-3, 15, el) * (1 - 0.72 * WX.cover);
      sun.color.copy(_c1.set(0xff9a55)).lerp(_c2.set(COLORS.sun), smooth(-2, 28, el));
      glintDir.copy(sp.dir);
    } else if (mp.el > 2) {
      // moonlight follows the real moon: direction, and strength by phase
      sunDir.copy(moonDir);
      sun.intensity = (0.05 + 0.13 * mp.k) * (1 - 0.6 * WX.cover);
      sun.color.set(0x8ea0c0);
      glintDir.copy(moonDir);
    } else {
      sunDir.copy(moonHigh);
      sun.intensity = 0.05;
      sun.color.set(0x8ea0c0);
      glintDir.set(0, -1, 0);              // no moon, no moonglade
    }
    aimSun(lastAim.cx, lastAim.cz, lastAim.extent);
    skyMat.uniforms.uSun.value.copy(sp.dir);
    // the phased moon disc: bright-limb tangent from the world sun/moon vectors
    skyMat.uniforms.uMoon.value.copy(mp.dir);
    _vA.copy(sp.dir).addScaledVector(mp.dir, -sp.dir.dot(mp.dir));
    if (_vA.lengthSq() < 1e-6) _vA.set(0, 1, 0).addScaledVector(mp.dir, -mp.dir.y);
    _vA.normalize();
    skyMat.uniforms.uMoonU.value.copy(_vA);
    skyMat.uniforms.uMoonV.value.crossVectors(mp.dir, _vA);
    skyMat.uniforms.uMoonK.value = mp.k;
    skyMat.uniforms.uMoonI.value = smooth(-1, 5, mp.el) * (1 - smooth(-7, 1, el)) * (1 - 0.85 * WX.cover);
    const mixPal = (k) => _c1.copy(PAL.night[k]).lerp(PAL.twi[k], twi).lerp(PAL.day[k], dayF).clone();
    const cz = mixPal('z'), ch = mixPal('h'), cg = mixPal('g');
    // overcast grays the sky toward a flat deck
    cz.lerp(_c2.set(0x93a5b4).multiplyScalar(0.15 + 0.85 * dayF), WX.cover * 0.55);
    ch.lerp(_c2.set(0xc4ccd2).multiplyScalar(0.15 + 0.85 * dayF), WX.cover * 0.5);
    skyMat.uniforms.cZenith.value.copy(cz);
    skyMat.uniforms.cHorizon.value.copy(ch);
    skyMat.uniforms.cGround.value.copy(cg);
    skyMat.uniforms.uCloud.value = WX.cover;
    skyMat.uniforms.uCloudLight.value = 0.10 + 0.95 * dayF + twi * 0.25;
    skyMat.uniforms.cSun.value.copy(_c1.set(0xff8a40)).lerp(_c2.set(COLORS.sun), smooth(0, 20, el));
    scene.fog.color.copy(ch);
    hemi.color.copy(_c1.set(0x1a2238)).lerp(_c2.set(0xd3deea), dayF).lerp(_c1.set(0xf0b080), twi * 0.35);
    hemi.groundColor.copy(_c1.set(0x0c0c10)).lerp(_c2.set(0x8f8166), dayF);
    hemi.intensity = 0.10 + 0.45 * dayF;
    // bare ground follows the light: near-black at night, warm dark earth through
    // twilight, the pale sage only in daylight — the fixed pale tone read as water
    _c1.set(0x232321).lerp(_c2.set(0x55503f), twi).lerp(_c2.set(COLORS.ground), dayF);
    for (const gm of groundMats) gm.color.copy(_c1);
    renderer.toneMappingExposure = 0.95 + 0.11 * dayF;
    nightUniform.value = night;
    // (bus night glow lives in bodyMat's aGlow shader term, driven by uNight)
    if (stMat) stMat.color.copy(_c1.set(0x2c2822)).lerp(_c2.set(0xa8a296), night);  // street text: dark on day roads, pale at night
    if (hdMat) hdMat.color.copy(_c1.set(0x6b4f26)).lerp(_c2.set(0xc89b5e), night);  // district inlays: dark bronze by day, glowing at night
    if (hdLblMat) hdLblMat.color.copy(_c1.set(0x6b4f26)).lerp(_c2.set(0xc89b5e), night);
    if (nbMat) {
      const nbFade = placesOn ? smooth(420, 1000, camera.position.y) : 0;   // names live at altitude
      nbMat.opacity = nbFade * 0.96;
      nbMesh.visible = nbFade > 0.02;
    }
    if (Math.abs(el - lastEnvEl) > 3) { lastEnvEl = el; refreshEnv(); }
    if (towerGlassMat) towerGlassMat.emissiveIntensity = night * 0.16;
    if (towerVarMat) towerVarMat.emissiveIntensity = night * 0.9;
    // (core glass night lighting lives in rylandGlassMat's panel shader, via uNight)
    if (outerGlassMat) outerGlassMat.emissiveIntensity = night * 0.55;
    return el;
  }
  // --- time panel
  const timePanel = document.getElementById('timepanel');
  const timeDate = document.getElementById('timeDate');
  const timeSlider = document.getElementById('timeSlider');
  const timeClockEl = document.getElementById('timeClock');
  const timeSunEl = document.getElementById('timeSun');
  let sunCache = { key: '', rise: null, set: null };
  function clockDateStr() { return clock.y + '-' + (clock.m < 10 ? '0' : '') + clock.m + '-' + (clock.d < 10 ? '0' : '') + clock.d; }
  function refreshTimeUI() {
    const key = clockDateStr();
    if (sunCache.key !== key) { const t = sunTimes(clock); sunCache = { key, rise: t.rise, set: t.set }; }
    if (document.activeElement !== timeDate) timeDate.value = key;
    timeSlider.value = String(clock.minutes);
    const dst = tzOffsetMin(clock.y, clock.m, clock.d) === -240;
    timeClockEl.textContent = fmtTime(clock.minutes) + ' ' + (dst ? 'EDT' : 'EST') + (clock.live ? ' (Live)' : '');
    const mp = lunar(clockUtcMs(clock, clock.minutes));
    const phase = mp.k < 0.02 ? 'New Moon' : mp.k > 0.98 ? 'Full Moon'
      : Math.abs(mp.k - 0.5) < 0.035 ? (mp.wax ? 'First Quarter' : 'Last Quarter')
      : mp.k < 0.5 ? (mp.wax ? 'Waxing Crescent' : 'Waning Crescent')
      : (mp.wax ? 'Waxing Gibbous' : 'Waning Gibbous');
    const oct = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'][Math.round(mp.az / 45) % 8];
    timeSunEl.textContent = '↑ ' + fmtTime(sunCache.rise) + '  ↓ ' + fmtTime(sunCache.set) + (WX.ok ? '   ☁ ' + Math.round(WX.cover * 100) + '%' : '')
      + '   ☾ ' + phase + ' ' + Math.round(mp.k * 100) + '%' + (mp.el > 0 ? ', Up ' + oct : ', Set');
  }
  function toggleTimePanel() { timePanel.classList.toggle('open'); }
  document.getElementById('btnTime').addEventListener('click', toggleTimePanel);
  timeSlider.addEventListener('input', () => { clock.live = false; clock.minutes = parseInt(timeSlider.value, 10); refreshTimeUI(); });
  timeDate.addEventListener('change', () => {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(timeDate.value);
    if (!m) return;
    clock.live = false; clock.y = +m[1]; clock.m = +m[2]; clock.d = +m[3];
    refreshTimeUI();
  });
  document.getElementById('timeNow').addEventListener('click', () => { clock.live = true; setClockToNow(); refreshTimeUI(); });
  for (const btn of timePanel.querySelectorAll('[data-preset]')) {
    btn.addEventListener('click', () => {
      clock.live = false;
      const t = sunTimes(clock);
      const p = btn.getAttribute('data-preset');
      clock.minutes = p === 'dawn' ? Math.max(0, (t.rise == null ? 360 : t.rise) - 12)
        : p === 'noon' ? 750
        : p === 'dusk' ? Math.min(1439, (t.set == null ? 1140 : t.set) + 8)
        : 1320;
      refreshTimeUI();
    });
  }
  setClockToNow();
  refreshTimeUI();
  let lastMinuteTick = -1;

  // ---------------------------------------------------------------- build & loop
  async function build() {
    let failures = 0;
    for (const s of buildSteps) {
      loadmsg.textContent = s.msg;
      await new Promise(r => setTimeout(r, 10));
      try { const r = s.fn(); if (r && typeof r.then === 'function') await r; } catch (err) { failures++; console.error('build step failed:', s.msg, err); }
    }
    loadmsg.textContent = failures ? 'Ready (some detail could not be built)' : 'Ready';
    btnEnter.disabled = false;
    btnEnter.textContent = 'Enter the City';
  }

  btnEnter.addEventListener('click', () => {
    veil.classList.add('hidden');
    if (reducedMotion) {
      orbit.r = orbit.goalR; orbit.theta = orbit.goalTheta; orbit.phi = orbit.goalPhi;
    } else if (!interacted) {
      introSpin = true;
    }
    setHint();
  });

  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, DPR_CAP));
    renderer.setSize(window.innerWidth, window.innerHeight);
  });
  canvas.addEventListener('webglcontextlost', (e) => {
    e.preventDefault();
    const el = document.getElementById('nogl');
    el.style.display = 'flex';
    el.firstElementChild.innerHTML = 'The 3D view was interrupted (graphics memory pressure).<br>Reload the page to continue exploring.';
  });

  let last = performance.now();
  let shadowMode = -1;
  let lastBearing = null;
  function frame(now, once) {
    if (!once) requestAnimationFrame(frame);
    const dt = Math.min((now - last) / 1000, 0.05);
    last = now;
    if (introSpin && !interacted) orbit.goalTheta += dt * 0.045;
    if (clock.live) {
      const nowMin = Math.floor(Date.now() / 60000);
      if (nowMin !== lastMinuteTick) { lastMinuteTick = nowMin; setClockToNow(); refreshTimeUI(); }
    }
    applyLighting();
    if (mode === MODE.ORBIT) applyOrbit(dt);
    else if (mode === MODE.WALK) applyWalk(dt);
    else applyFly(dt);

    // tighter shadow frustum while walking
    const wantShadow = mode === MODE.WALK ? 1 : 0;
    if (wantShadow !== shadowMode) {
      shadowMode = wantShadow;
      if (wantShadow) aimSun(walk.pos.x, walk.pos.z, 300);
      else aimSun(-1450, -700, 800);
    } else if (mode === MODE.WALK) {
      const c = sun.target.position;
      if (Math.hypot(walk.pos.x - c.x, walk.pos.z - c.z) > 120) aimSun(walk.pos.x, walk.pos.z, 300);
    }

    // compass: rotation = -bearing of camera forward (write only on change)
    camera.getWorldDirection(tmpV);
    const bearing = Math.round(Math.atan2(tmpV.x, -tmpV.z) * 1800 / Math.PI) / 10;
    if (bearing !== lastBearing) {
      lastBearing = bearing;
      needle.setAttribute('transform', 'rotate(' + (-bearing) + ' 17 17)');
    }

    sky.position.copy(camera.position);
    skyMat.uniforms.uCloudOff.value.addScaledVector(wxWind, dt);
    if (!reducedMotion) waterU.uTime.value += dt;
    waterU.uSun.value.copy(glintDir);
    updateTransit(now, dt);
    updateIndego(now, dt);
    updateFlights(now, dt);
    updateShips(now, dt);
    updateTreePick();
    updateSearchMark(now);
    updateLabels();
    renderer.render(scene, camera);
  }

  setHint();
  fetchWeather();
  setInterval(fetchWeather, 15 * 60 * 1000);
  build().then(() => {
    if (/[?&]dev\b/.test(location.search)) {
      window.__dbg = { orbit, walk, fly, camera, renderer, scene, WX, waterU, flightTest, shipTest, ships: () => ({ n: shipMap.size, ok: SHIPS.ok, sock: !!SHIPS.sock }), flights: () => ({ n: flightMap.size, ok: FLIGHTS.ok, fails: FLIGHTS.fails, host: FLIGHTS.host }), indego: () => ({ n: indegoSt.size, drawn: indegoLive.length, ok: INDEGO.ok, fails: INDEGO.fails }), frameOnce: () => frame(performance.now(), true), goWalk: (x, z, yaw) => { setMode(MODE.WALK); walk.pos.set(x, 1.7, z); walk.yaw = yaw; walk.pitch = 0.12; }, goFly: (x, y, z, yaw, pitch) => { setMode(MODE.FLY); fly.pos.set(x, y, z); walk.yaw = yaw; walk.pitch = pitch || 0; } };
    }
    requestAnimationFrame(frame);
  });
})();
