// The modelling kit of the landmark rebuilds (Round 161; three r149, plain script, no modules). Built for the Sep 25
// design study (seven researched proposals modelled in a scratch harness and reviewed against today's build), kept
// as it was there so the rebuilds draw exactly what was reviewed. RB.kit(THREE) -> K. Everything is in the scene
// frame: x = east, z = south, y = up, metres.
//
// Frames: most buildings sit on the street grid (~10 degrees off the axes), so build in a local frame:
//   const f = K.frame(cx, cz, angleRad)   // u axis = (cos a, sin a) in (x, z); v axis = (-sin a, cos a)
//   f.p(u, v) -> [x, z]                   // local to world
//   K.frameFromEdge([x0, z0], [x1, z1])   // frame whose u axis runs along that edge, origin at its first point
// Geometry helpers return a THREE.BufferGeometry (world space). Collect them with a builder, one merged
// mesh per material:
//   const B = K.builder(); B.add(K.mat('#d8cfbd'), geom); ...; return B.done();
// Colours: give K.mat the REAL colour as it reads in a daylight photo (sRGB hex). The app runs r149's legacy
// colour pipeline (a stored hex is used as linear, then sRGB output and ACES lift it ~2.2x), so K.mat stores
// srgbToLinear(photo) x 0.88, the same calibration as the app's own Philadelphia Museum of Art (Kasota stone
// stored 0x8a744c). Pass { stored: true } to hand it an app-style stored hex unchanged.
RB.kit = (function () {
 let cache = null;
 return function (THREE) {
  if (cache) return cache;
  const K = {};
  const V3 = THREE.Vector3;

  // photo colours (sRGB, as the material reads in daylight); K.mat converts them
  K.PALETTE = {
    marble: '#e2ddd2', marbleTrim: '#ece8df', limestone: '#d2c8b2', limestoneWarm: '#d5c299', kasota: '#cdb487',
    granite: '#a9a49a', granitePink: '#b99a8c', brownstone: '#7a5a48', brickRed: '#9c5340', brickDark: '#7a4032',
    brickBrown: '#8e5a44', whiteTrim: '#efebe2', slate: '#5a5d62', roofGrey: '#808489', roofDark: '#4a4c50',
    copperGreen: '#79a996', verdigris: '#86b3a3', bronze: '#6d5a40', glass: '#27323d', glassBlue: '#34506a',
    stuccoPale: '#e6d9b4', ironDark: '#2e3033', steel: '#8a9096', stoneGrey: '#a29c90', terracotta: '#b8744c',
    gold: '#c49a45', schist: '#7d7b6e', serpentine: '#6f7a5e', rustedIron: '#6e4a36', concrete: '#b4b0a6'
  };
  const _c = new THREE.Color();
  K.stored = function (hex, gain) { _c.set(hex); _c.convertSRGBToLinear(); _c.multiplyScalar(gain == null ? 0.88 : gain); return '#' + _c.getHexString(); };

  // ---- materials (cached by key)
  const mats = new Map();
  K.mat = function (hex, o) {
    o = o || {};
    const key = [hex, o.stored, o.gain, o.rough, o.metal, o.emissive, o.emissiveIntensity, o.side, o.flat, o.opacity, o.map ? o.map.uuid : ''].join('|');
    if (mats.has(key)) return mats.get(key);
    const col = o.stored ? hex : K.stored(hex, o.gain);
    const m = new THREE.MeshStandardMaterial({
      color: new THREE.Color(col), roughness: o.rough == null ? 0.85 : o.rough, metalness: o.metal || 0,
      emissive: new THREE.Color(o.emissive ? (o.stored ? o.emissive : K.stored(o.emissive, 1)) : '#000000'), emissiveIntensity: o.emissiveIntensity == null ? 1 : o.emissiveIntensity,
      side: o.side === 'double' ? THREE.DoubleSide : THREE.FrontSide, flatShading: !!o.flat,
      transparent: o.opacity != null && o.opacity < 1, opacity: o.opacity == null ? 1 : o.opacity, map: o.map || null
    });
    m.userData.kitKey = key;
    mats.set(key, m);
    return m;
  };
  K.glass = function (hex) { return K.mat(hex || K.PALETTE.glass, { rough: 0.22, metal: 0.35 }); };

  // ---- builder: merge per material
  K.builder = function () {
    const parts = new Map();
    const B = {
      add(mat, geom) {
        if (!geom) return B;
        if (Array.isArray(geom)) { for (const g of geom) B.add(mat, g); return B; }
        if (!parts.has(mat)) parts.set(mat, []);
        parts.get(mat).push(geom);
        return B;
      },
      addMesh(mesh) { (B.extra || (B.extra = [])).push(mesh); return B; },
      done() {
        const grp = new THREE.Group();
        for (const [mat, geoms] of parts) {
          const g = K.merge(geoms);
          if (!g) continue;
          const mesh = new THREE.Mesh(g, mat);
          grp.add(mesh);
        }
        if (B.extra) for (const m of B.extra) grp.add(m);
        // let the parts go: a def's hooks close over its build() scope, which holds this builder, so the pre-merge
        // geometries would otherwise live as long as the page (Round 161 review)
        parts.clear(); B.extra = null;
        return grp;
      }
    };
    return B;
  };
  K.merge = function (geoms) {
    let n = 0;
    const flat = geoms.map((g) => {
      let q = g.index ? g.toNonIndexed() : g;
      if (!q.attributes.normal) q.computeVertexNormals();
      n += q.attributes.position.count;
      return q;
    });
    if (!n) return null;
    const pos = new Float32Array(n * 3), nor = new Float32Array(n * 3), uv = new Float32Array(n * 2);
    let o = 0;
    for (const q of flat) {
      const c = q.attributes.position.count;
      pos.set(q.attributes.position.array.subarray(0, c * 3), o * 3);
      nor.set(q.attributes.normal.array.subarray(0, c * 3), o * 3);
      if (q.attributes.uv) uv.set(q.attributes.uv.array.subarray(0, c * 2), o * 2);
      o += c;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
    g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
    g.computeBoundingSphere();
    return g;
  };

  // ---- frames
  K.frame = function (cx, cz, a) {
    const c = Math.cos(a), s = Math.sin(a);
    const f = {
      cx, cz, a, ux: c, uz: s, vx: -s, vz: c,
      p(u, v) { return [cx + u * c - v * s, cz + u * s + v * c]; },
      // local geometry (x = u, y = up, z = v) placed into the world
      place(geom, y0) { geom.rotateY(-a); geom.translate(cx, y0 || 0, cz); return geom; },
      // world point to local [u, v]
      local(x, z) { const dx = x - cx, dz = z - cz; return [dx * c + dz * s, -dx * s + dz * c]; }
    };
    return f;
  };
  K.frameFromEdge = function (p0, p1) { return K.frame(p0[0], p0[1], Math.atan2(p1[1] - p0[1], p1[0] - p0[0])); };
  K.seg = function (a, b) {
    const dx = b[0] - a[0], dz = b[1] - a[1], len = Math.hypot(dx, dz) || 1e-9;
    const ux = dx / len, uz = dz / len;
    // n = left-hand normal walking a -> b on a north-up map (walking east, n points north)
    return { len, ux, uz, nx: uz, nz: -ux, mid: [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2], ang: Math.atan2(dz, dx) };
  };
  K.centroid = function (ring) { let x = 0, z = 0; for (const p of ring) { x += p[0]; z += p[1]; } return [x / ring.length, z / ring.length]; };
  K.offsetRing = function (ring, d) {   // d > 0 grows the ring outward, d < 0 shrinks it, whatever its winding
    const n = ring.length, out = [];
    const area = K.signedArea(ring), sgn = area > 0 ? 1 : -1;
    for (let i = 0; i < n; i++) {
      const p0 = ring[(i - 1 + n) % n], p1 = ring[i], p2 = ring[(i + 1) % n];
      const a = K.seg(p0, p1), b = K.seg(p1, p2);
      // outward normal: for positive signed area (x east, z south) the left normal n points outward
      const n0x = a.nx * sgn, n0z = a.nz * sgn, n1x = b.nx * sgn, n1z = b.nz * sgn;
      let mx = n0x + n1x, mz = n0z + n1z; const ml = Math.hypot(mx, mz) || 1e-9; mx /= ml; mz /= ml;
      const cosh = Math.max(0.3, mx * n0x + mz * n0z);
      out.push([p1[0] + mx * d / cosh, p1[1] + mz * d / cosh]);
    }
    return out;
  };
  K.signedArea = function (ring) { let s = 0; for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) s += ring[j][0] * ring[i][1] - ring[i][0] * ring[j][1]; return s / 2; };
  K.rect = function (f, u0, u1, v0, v1) { return [f.p(u0, v0), f.p(u1, v0), f.p(u1, v1), f.p(u0, v1)]; };

  // ---- primitives (world space)
  // box centred at (x, y, z), rotated ry about y (radians; same sense as Object3D.rotation.y)
  K.box = function (w, h, d, x, y, z, ry) {
    const g = new THREE.BoxGeometry(w, h, d);
    if (ry) g.rotateY(ry);
    g.translate(x, y, z);
    return g;
  };
  // box in a frame: centred at local (u, v), size du along u, dv along v, from y0 to y0 + h
  K.boxF = function (f, u, v, du, dv, y0, h) {
    const g = new THREE.BoxGeometry(du, h, dv);
    g.translate(u, y0 + h / 2, v);
    return f.place(g, 0);
  };
  // box spanning local [u0, u1] x [v0, v1] from y0 to y1
  K.slabF = function (f, u0, u1, v0, v1, y0, y1) {
    return K.boxF(f, (u0 + u1) / 2, (v0 + v1) / 2, Math.abs(u1 - u0), Math.abs(v1 - v0), y0, y1 - y0);
  };
  // extrude a world ring (with optional holes) from y0 to y1, caps included
  K.prism = function (ring, y0, y1, holes) {
    const toShapePts = (r) => r.map((p) => new THREE.Vector2(p[0], -p[1]));
    let pts = toShapePts(ring);
    if (THREE.ShapeUtils.isClockWise(pts)) pts = pts.reverse();
    const shape = new THREE.Shape(pts);
    if (holes) for (const h of holes) { let hp = toShapePts(h); if (!THREE.ShapeUtils.isClockWise(hp)) hp = hp.reverse(); shape.holes.push(new THREE.Path(hp)); }
    const g = new THREE.ExtrudeGeometry(shape, { depth: y1 - y0, bevelEnabled: false, steps: 1 });
    g.rotateX(-Math.PI / 2);
    g.translate(0, y0, 0);
    return g;
  };
  // a wall of thickness t along a -> b, from y0 up h, centred on the segment offset `off` along its left normal
  K.edgeBox = function (a, b, y0, h, t, off, extend) {
    const s = K.seg(a, b), e = extend || 0;
    const g = new THREE.BoxGeometry(s.len + 2 * e, h, t);
    g.rotateY(-s.ang);
    g.translate(s.mid[0] + s.nx * (off || 0), y0 + h / 2, s.mid[1] + s.nz * (off || 0));
    return g;
  };
  // walls round a ring (parapets, fortress walls): thickness t, pushed inward so the outer face is on the ring
  K.ringWalls = function (ring, y0, h, t) {
    const out = [], sgn = K.signedArea(ring) > 0 ? 1 : -1;
    for (let i = 0; i < ring.length; i++) out.push(K.edgeBox(ring[i], ring[(i + 1) % ring.length], y0, h, t, -sgn * t / 2, t / 2));
    return out;
  };
  K.cyl = function (rTop, rBot, h, seg, x, y0, z, open) {
    const g = new THREE.CylinderGeometry(rTop, rBot, h, seg || 16, 1, !!open);
    g.translate(x, y0 + h / 2, z);
    return g;
  };
  K.cone = function (r, h, seg, x, y0, z, rot) {
    const g = new THREE.ConeGeometry(r, h, seg || 16);
    if (rot) g.rotateY(rot);
    g.translate(x, y0 + h / 2, z);
    return g;
  };
  // dome: a spherical cap of radius r standing on y0; rise scales the height (1 = hemisphere)
  K.dome = function (r, x, y0, z, seg, rise, thetaLen) {
    const g = new THREE.SphereGeometry(r, seg || 28, Math.max(6, Math.round((seg || 28) / 3)), 0, Math.PI * 2, 0, thetaLen || Math.PI / 2);
    const top = thetaLen ? r * Math.cos(thetaLen) : 0;
    g.translate(0, -top, 0);
    if (rise && rise !== 1) g.scale(1, rise, 1);
    g.translate(x, y0, z);
    return g;
  };
  // a polygon plate (horizontal) at height y, from a world ring
  K.plate = function (ring, y, t) { return K.prism(ring, y - (t || 0.2), y); };
  // generic quad from four world points [x, y, z] in order round the edge. Pass `inside` (a world point [x, y, z]
  // behind the face, e.g. the building's middle) and the winding is flipped as needed so the normal points away from it
  const faceOut = (pts, inside) => {
    if (!inside) return pts;
    const a = new V3(...pts[0]), b = new V3(...pts[1]), c = new V3(...pts[2]);
    const n = b.clone().sub(a).cross(c.clone().sub(a));
    const m = new V3(); for (const q of pts) m.add(new V3(...q)); m.multiplyScalar(1 / pts.length);
    return n.dot(m.sub(new V3(...inside))) < 0 ? pts.slice().reverse() : pts;
  };
  K.faceOut = faceOut;
  K.quad = function (p0, p1, p2, p3, inside) {
    [p0, p1, p2, p3] = faceOut([p0, p1, p2, p3], inside);
    const g = new THREE.BufferGeometry();
    const a = [p0, p1, p2, p0, p2, p3].flat();
    g.setAttribute('position', new THREE.Float32BufferAttribute(a, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute([0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1], 2));
    g.computeVertexNormals();
    return g;
  };
  K.tri = function (p0, p1, p2, inside) {
    [p0, p1, p2] = faceOut([p0, p1, p2], inside);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute([p0, p1, p2].flat(), 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute([0, 0, 1, 0, 0.5, 1], 2));
    g.computeVertexNormals();
    return g;
  };

  // ---- roofs in a frame: rectangle [u0, u1] x [v0, v1]
  // gable with the ridge along u (alongU true) or along v; returns { slopes, ends } (ends = the two triangular gables)
  K.gableF = function (f, u0, u1, v0, v1, yE, yR, alongU, over) {
    const o = over == null ? 0.35 : over;
    const W = (u, v, y) => { const p = f.p(u, v); return [p[0], y, p[1]]; };
    const slopes = [], ends = [], IN = W((u0 + u1) / 2, (v0 + v1) / 2, yE - 2);
    if (alongU !== false) {
      const vm = (v0 + v1) / 2, dy = (yR - yE) * o / ((v1 - v0) / 2);
      slopes.push(K.quad(W(u1 + o, v0 - o, yE - dy), W(u1 + o, vm, yR), W(u0 - o, vm, yR), W(u0 - o, v0 - o, yE - dy), IN));
      slopes.push(K.quad(W(u0 - o, v1 + o, yE - dy), W(u0 - o, vm, yR), W(u1 + o, vm, yR), W(u1 + o, v1 + o, yE - dy), IN));
      ends.push(K.tri(W(u0, v0, yE), W(u0, vm, yR), W(u0, v1, yE), W(u0 + 1, vm, yE)));
      ends.push(K.tri(W(u1, v1, yE), W(u1, vm, yR), W(u1, v0, yE), W(u1 - 1, vm, yE)));
    } else {
      const um = (u0 + u1) / 2, dy = (yR - yE) * o / ((u1 - u0) / 2);
      slopes.push(K.quad(W(u0 - o, v0 - o, yE - dy), W(um, v0 - o, yR), W(um, v1 + o, yR), W(u0 - o, v1 + o, yE - dy), IN));
      slopes.push(K.quad(W(u1 + o, v1 + o, yE - dy), W(um, v1 + o, yR), W(um, v0 - o, yR), W(u1 + o, v0 - o, yE - dy), IN));
      ends.push(K.tri(W(u1, v0, yE), W(um, v0, yR), W(u0, v0, yE), W(um, v0 + 1, yE)));
      ends.push(K.tri(W(u0, v1, yE), W(um, v1, yR), W(u1, v1, yE), W(um, v1 - 1, yE)));
    }
    return { slopes, ends, all: slopes.concat(ends) };
  };
  // hip roof: ridge along the longer side, rising to yR
  K.hipF = function (f, u0, u1, v0, v1, yE, yR, over) {
    const o = over == null ? 0.35 : over;
    const W = (u, v, y) => { const p = f.p(u, v); return [p[0], y, p[1]]; };
    const du = u1 - u0, dv = v1 - v0, out = [], IN = W((u0 + u1) / 2, (v0 + v1) / 2, yE - 2);
    const a0 = u0 - o, a1 = u1 + o, b0 = v0 - o, b1 = v1 + o;
    if (du >= dv) {
      const vm = (v0 + v1) / 2, inset = dv / 2;
      const r0 = W(u0 + inset, vm, yR), r1 = W(u1 - inset, vm, yR);
      out.push(K.quad(W(a1, b0, yE), r1, r0, W(a0, b0, yE), IN));
      out.push(K.quad(W(a0, b1, yE), r0, r1, W(a1, b1, yE), IN));
      out.push(K.tri(W(a0, b0, yE), r0, W(a0, b1, yE), IN));
      out.push(K.tri(W(a1, b1, yE), r1, W(a1, b0, yE), IN));
    } else {
      const um = (u0 + u1) / 2, inset = du / 2;
      const r0 = W(um, v0 + inset, yR), r1 = W(um, v1 - inset, yR);
      out.push(K.quad(W(a0, b0, yE), r0, r1, W(a0, b1, yE), IN));
      out.push(K.quad(W(a1, b1, yE), r1, r0, W(a1, b0, yE), IN));
      out.push(K.tri(W(a1, b0, yE), r0, W(a0, b0, yE), IN));
      out.push(K.tri(W(a0, b1, yE), r1, W(a1, b1, yE), IN));
    }
    return out;
  };
  // pyramid / pavilion roof on a rectangle
  K.pyramidF = function (f, u0, u1, v0, v1, yE, yT, over) {
    const o = over == null ? 0.25 : over;
    const W = (u, v, y) => { const p = f.p(u, v); return [p[0], y, p[1]]; };
    const t = W((u0 + u1) / 2, (v0 + v1) / 2, yT);
    const c = [W(u0 - o, v0 - o, yE), W(u1 + o, v0 - o, yE), W(u1 + o, v1 + o, yE), W(u0 - o, v1 + o, yE)];
    const IN = W((u0 + u1) / 2, (v0 + v1) / 2, yE - 2);
    return [K.tri(c[1], t, c[0], IN), K.tri(c[2], t, c[1], IN), K.tri(c[3], t, c[2], IN), K.tri(c[0], t, c[3], IN)];
  };
  // pediment: triangular prism on the face at local v (facing sign s = +1 toward +v, -1 toward -v),
  // spanning [u0, u1], base at yB, apex yB + h, depth d back from the face
  K.pedimentF = function (f, u0, u1, v, s, yB, h, d) {
    const W = (u, vv, y) => { const p = f.p(u, vv); return [p[0], y, p[1]]; };
    const vb = v - s * d, um = (u0 + u1) / 2, out = [], IN = W(um, v - s * d / 2, yB + h / 3);
    const F = [W(u0, v, yB), W(u1, v, yB), W(um, v, yB + h)], Bk = [W(u0, vb, yB), W(u1, vb, yB), W(um, vb, yB + h)];
    out.push(K.tri(F[0], F[1], F[2], IN));
    out.push(K.tri(Bk[0], Bk[1], Bk[2], IN));
    out.push(K.quad(F[1], Bk[1], Bk[2], F[2], IN));
    out.push(K.quad(Bk[0], F[0], F[2], Bk[2], IN));
    out.push(K.quad(F[0], F[1], Bk[1], Bk[0], IN));
    return out;
  };

  // ---- classical orders
  // column standing at (x, y0, z): shaft radius r (bottom; entasis to 0.86r at the top), total height h
  // capital: 'doric' | 'ionic' | 'corinthian' | 'tuscan'; returns an array of geometries (one material)
  K.column = function (x, y0, z, h, r, capital, seg) {
    const sg = seg || 16, out = [];
    const cap = capital || 'doric';
    const baseH = cap === 'doric' ? 0 : r * 0.55;
    const capH = cap === 'corinthian' ? r * 2.4 : cap === 'ionic' ? r * 0.9 : r * 0.75;
    if (baseH) { out.push(K.cyl(r * 1.35, r * 1.45, baseH * 0.5, sg, x, y0, z)); out.push(K.cyl(r * 1.15, r * 1.3, baseH * 0.5, sg, x, y0 + baseH * 0.5, z)); }
    const shaftH = h - baseH - capH;
    out.push(K.cyl(r * 0.86, r, shaftH, sg, x, y0 + baseH, z));
    const yc = y0 + baseH + shaftH;
    if (cap === 'corinthian') {
      out.push(K.cyl(r * 1.25, r * 0.9, capH * 0.8, sg, x, yc, z));                   // bell of leaves
      out.push(K.box(r * 2.9, capH * 0.2, r * 2.9, x, yc + capH * 0.9, z));            // abacus
    } else if (cap === 'ionic') {
      out.push(K.cyl(r * 1.0, r * 0.9, capH * 0.35, sg, x, yc, z));
      out.push(K.box(r * 2.7, capH * 0.4, r * 1.6, x, yc + capH * 0.55, z));           // volute band
      out.push(K.box(r * 2.4, capH * 0.25, r * 2.4, x, yc + capH * 0.875, z));
    } else {
      out.push(K.cyl(r * 1.2, r * 0.88, capH * 0.55, sg, x, yc, z));                   // echinus
      out.push(K.box(r * 2.5, capH * 0.45, r * 2.5, x, yc + capH * 0.775, z));         // abacus
    }
    return out;
  };
  // a row of n columns from local (u0, v) to (u1, v) in a frame
  K.colonnadeF = function (f, u0, u1, v, n, y0, h, r, capital) {
    const out = [];
    for (let i = 0; i < n; i++) {
      const u = n === 1 ? (u0 + u1) / 2 : u0 + (u1 - u0) * i / (n - 1);
      const p = f.p(u, v);
      out.push(...K.column(p[0], y0, p[1], h, r, capital));
    }
    return out;
  };
  // entablature / cornice band round a ring: a slab from y0 to y1 grown out by `out` metres
  K.corniceRing = function (ring, y0, y1, out) { return K.prism(K.offsetRing(ring, out), y0, y1); };

  // ---- windows on a wall face in a frame. The face is the plane v = vFace, its outward side is sign s (+1 = +v).
  // cols windows spread evenly over [u0, u1]; rows from y0 at rowH pitch; each winW by winH. The glass quad stands
  // `inset` BEHIND the face and no jambs are drawn, so on a solid wall it is hidden: pass inset 0 (or a small negative
  // one, proud of the face) there, or cut the opening in the wall yourself. opts.arch adds a half-round head,
  // opts.sill a stone sill, opts.frame a hex for jambs/sill (default whiteTrim). Returns { glass: [...], trim: [...] }
  K.windowsF = function (f, u0, u1, vFace, s, y0, rows, rowH, cols, winW, winH, opts) {
    opts = opts || {};
    const glass = [], trim = [], inset = opts.inset == null ? 0.18 : opts.inset;
    const W = (u, v, y) => { const p = f.p(u, v); return [p[0], y, p[1]]; };
    const step = cols > 1 ? (u1 - u0 - winW) / (cols - 1) : 0;
    for (let r = 0; r < rows; r++) {
      const yb = y0 + r * rowH;
      for (let c = 0; c < cols; c++) {
        if (opts.skip && opts.skip(r, c)) continue;
        const uc = cols > 1 ? u0 + winW / 2 + c * step : (u0 + u1) / 2;
        const a = uc - winW / 2, b = uc + winW / 2, vg = vFace - s * inset + s * 0.01, IN = W(uc, vg - s, yb + winH / 2);
        // glass, facing +s
        glass.push(K.quad(W(a, vg, yb), W(b, vg, yb), W(b, vg, yb + winH), W(a, vg, yb + winH), IN));
        if (opts.arch) {
          const rr = winW / 2, n = 8, cx = uc, cy = yb + winH;
          for (let k = 0; k < n; k++) {
            const t0 = Math.PI * k / n, t1 = Math.PI * (k + 1) / n;
            const pA = W(cx + rr * Math.cos(t0), vg, cy + rr * Math.sin(t0)), pB = W(cx + rr * Math.cos(t1), vg, cy + rr * Math.sin(t1)), pC = W(cx, vg, cy);
            glass.push(K.tri(pA, pB, pC, IN));
          }
        }
        if (opts.sill !== false) trim.push(K.boxF(f, uc, vFace + s * 0.08, winW + 0.3, 0.3, yb - 0.18, 0.18));
        if (opts.lintel) trim.push(K.boxF(f, uc, vFace + s * 0.05, winW + 0.4, 0.2, yb + winH + (opts.arch ? winW / 2 : 0), 0.3));
        if (opts.mullion) trim.push(K.boxF(f, uc, vFace - s * inset * 0.5, 0.08, inset, yb, winH));
      }
    }
    return { glass, trim };
  };
  // crenellations along local u at the face v (sign s outward): merlons of width mw, gaps gw, height h, thickness t
  K.crenelF = function (f, u0, u1, v, s, y0, mw, gw, h, t) {
    const out = [];
    for (let u = u0; u + mw <= u1 + 1e-6; u += mw + gw) out.push(K.boxF(f, u + mw / 2, v - s * t / 2, mw, t, y0, h));
    return out;
  };

  // ---- signs: a canvas-lettered plane; returns a Mesh (add with B.addMesh). opts: { color, bg, glow (emissive), font, weight }
  K.sign = function (text, w, h, x, y, z, ry, opts) {
    opts = opts || {};
    const cv = document.createElement('canvas'); cv.width = 1024; cv.height = Math.max(64, Math.round(1024 * h / w));
    const ctx = cv.getContext('2d');
    ctx.fillStyle = opts.bg || 'rgba(0,0,0,0)'; ctx.fillRect(0, 0, cv.width, cv.height);
    ctx.fillStyle = opts.color || '#f2ede0'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.font = (opts.weight || '800') + ' ' + Math.round(cv.height * 0.72) + 'px ' + (opts.font || 'Arial, sans-serif');
    ctx.fillText(text, cv.width / 2, cv.height / 2, cv.width * 0.96);
    const tex = new THREE.CanvasTexture(cv);
    tex.encoding = THREE.sRGBEncoding; tex.anisotropy = 4;
    const m = new THREE.MeshStandardMaterial({ map: tex, transparent: true, alphaTest: 0.1, roughness: 0.6, side: THREE.DoubleSide,
      emissive: new THREE.Color(opts.glow || '#000000'), emissiveMap: opts.glow ? tex : null, emissiveIntensity: opts.glowK || 1 });
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h), m);
    mesh.position.set(x, y, z); mesh.rotation.y = ry || 0;
    mesh.userData.noShadow = true;
    return mesh;
  };

  cache = K;
  return K;
 };
})();
