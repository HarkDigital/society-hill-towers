// Reading Terminal (Philadelphia and Reading Railroad, 1891 to 1893): a PROPOSED model of Francis Kimball's
// Italian Renaissance headhouse on Market Street and the Wilson Brothers' single-span arched train shed behind it,
// with the Reading Terminal Market at street level under the shed. Round 161's rebuild, from the Sep 25 design study.
//
// Frame: u runs east along the Market Street front (9.53 degrees off the scene's x axis, the OSM headhouse's
// Market edge), v runs south (Market Street is +v). Local origin = the 12th and Market building corner,
// scene (-1282.02, -728.24). Planes, from the OSM footprints (ways 335293079 headhouse, 335512395 the two-storey
// link, 42784822 market and shed, 337052616 the Marriott skybridge) in this frame:
//   headhouse u 0 .. 82.8, v -32.8 .. 0; link v -46.4 .. -32.8; shed u 0 .. 82, v -200.6 .. -46.4;
//   the shed's bridge over Arch Street u 23 .. 60, v -223.3 .. -200.6; the skybridge over 12th u -22.8 .. 0,
//   v -41.4 .. -35; Filbert Street passes under the shed at v -100 (tunnel=building_passage).
// Heights: headhouse cornice 47 m (photo elevation scaled to the 82.8 m front, the city's 2022 LiDAR approx_hgt
// 44.5 m is the roof deck behind the parapet), shed crown 36.6 m (track deck 7.6 m, 95 ft rise; LiDAR 37.8 to
// 39.2 with the monitor).
//
// Revision 2 (after review): every window is its own pane behind its opening, carrying a lit level and a tint in
// its uv, so after dark about 40% of the hotel's rooms glow like the app's own windows (uNight); the masonry is one
// vertex-coloured material that takes the street lamps' pools on its lower storeys and the roofs' night glow the
// way the facade hook does (the app's own lamp and night uniforms, passed in as api.night and api.lampU); the loggia
// is an open two-storey gallery; the corner oriel is one storey on a stepped corbel; the market base is grey
// granite piers and buff brick; the old storefront the app hung on 12th Street stays off (the storefront pass skips
// every rebuild's ground, REBUILD_OCC, as it does the researched footprints since Round 127).
(function () {
  const A = 0.16641530118311473, OX = -1282.02, OZ = -728.24, C = Math.cos(A), S = Math.sin(A);
  const P = (u, v) => [+(OX + u * C - v * S).toFixed(2), +(OZ + u * S + v * C).toFixed(2)];
  const R = (u0, u1, v0, v1) => [P(u0, v0), P(u1, v0), P(u1, v1), P(u0, v1)];

  RB.add({
    id: 'rtm', name: 'Reading Terminal Headhouse and Train Shed',
    center: P(41, -110), aim: P(41, -40),
    // every generic record centred on the headhouse, the link, the market and shed (with its Arch Street bridge),
    // and the Marriott skybridge that the app stands on 12th Street as a 38 m wall
    skip: [R(-1.5, 83.6, -225, 1.5), R(-24, -1.5, -43, -34)],
    views: [[193, 185, 235, 10], [236, 96, 22, 22], [30, 300, 160, 12]],
    build(api) {
      const { THREE, K } = api;
      const F = K.frame(OX, OZ, A);
      const Bd = K.builder();
      const V2 = (a, b) => new THREE.Vector2(a, b);
      const inApp = api.where === 'app';

      // ---- the app's own night and lamp uniforms (shared objects, updated by applyLighting every frame), handed over
      // as api.night and api.lampU; outside the app they stay at their day values.
      const U = { night: { value: 0 }, lampMap: { value: null }, lampBox: { value: new THREE.Vector4(0, 0, 1, 0) }, lampOn: { value: 0 }, lampFade: { value: new THREE.Vector4(0, 0, 0, 1) }, base: { value: 0 } };
      let foundNight = false, foundLamp = false;
      if (inApp) {
        if (api.night) { U.night = api.night; foundNight = true; }
        if (api.lampU) { U.lampMap = api.lampU.uLampMap; U.lampBox = api.lampU.uLampBox; U.lampOn = api.lampU.uLampOn; U.lampFade = api.lampU.uLampFade; foundLamp = true; }
      }
      // the night hooks: 'roof' the Round 150 roof glow (0.3 of a face's own colour on every face turned up),
      // 'lamp' the Round 140/146 street-lamp pools on the lower storeys (lampLightPatch's 'wall' gate), 'glow' a
      // fixed colour after dark, 'panes' the lit windows (uv.x = level, uv.y = tint, warm lamp to cool office)
      const hook = (mat, o, key) => {
        mat.onBeforeCompile = (sh) => {
          sh.uniforms.uNight = U.night; sh.uniforms.uRtmBase = U.base;
          sh.uniforms.uLampMap = U.lampMap; sh.uniforms.uLampBox = U.lampBox; sh.uniforms.uLampOn = U.lampOn; sh.uniforms.uLampFade = U.lampFade;
          if (o.panes) sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec2 vPane;').replace('#include <begin_vertex>', '#include <begin_vertex>\nvPane = uv;');
          const code = ['{', 'vec3 lwp = cameraPosition - vViewPosition * mat3(viewMatrix);', 'vec3 wn = inverseTransformDirection(normal, viewMatrix);'];
          if (o.roof) code.push('totalEmissiveRadiance += diffuseColor.rgb * uNight * 0.3 * smoothstep(0.35, 0.75, wn.y);');
          if (o.lamp) code.push(
            'if (uLampOn > 0.001) {',
            '  vec2 luv = vec2((lwp.x - uLampBox.x) * uLampBox.z, 1.0 - (lwp.z - uLampBox.y) * uLampBox.z);',
            '  float le = min(min(luv.x, 1.0 - luv.x), min(luv.y, 1.0 - luv.y));',
            '  float lk = 0.75 * mix(0.3, 1.0, 1.0 - smoothstep(0.35, 0.7, abs(wn.y))) * (1.0 - smoothstep(3.0, 16.0, lwp.y - uRtmBase)) * (1.0 - smoothstep(uLampFade.z - uLampFade.w, uLampFade.z, distance(lwp.xz, uLampFade.xy)));',
            '  if (le > 0.0 && lk > 0.0) { vec3 la = min(diffuseColor.rgb, vec3(0.35)) * texture2D(uLampMap, luv).rgb * (uLampOn * uLampBox.w * lk);',
            '    vec3 lo = max(la - 0.5, 0.0); totalEmissiveRadiance += min(la, vec3(0.5)) + lo / (1.0 + lo * 2.0); }',
            '}');
          if (o.glow) code.push('totalEmissiveRadiance += vec3(' + o.glow.map((c) => c.toFixed(3)).join(', ') + ') * uNight;');
          if (o.panes) code.push(
            'float pLvl = floor(vPane.x + 0.0005) / 100.0, pTn = fract(vPane.x + 0.0005);',
            'if (uNight > 0.001 && pLvl > 0.001) {',
            '  vec3 tint = pTn < 0.5 ? mix(vec3(1.0, 0.60, 0.31), vec3(1.0, 0.83, 0.59), pTn * 2.0) : mix(vec3(1.0, 0.86, 0.66), vec3(0.80, 0.88, 1.0), pTn * 2.0 - 1.0);',
            // a room's light: brighter toward the ceiling, a soft band under it (the app's office wash, simplified)
            '  float py = vPane.y, pc = (py - 0.84) * 4.3, wash = 0.50 + 0.30 * smoothstep(0.03, 0.85, py) + 0.30 * exp(-pc * pc);',
            '  totalEmissiveRadiance += tint * pLvl * wash * uNight * (1.0 - 0.45 * smoothstep(1500.0, 7000.0, length(vViewPosition)));',
            '}');
          code.push('}');
          sh.fragmentShader = sh.fragmentShader
            .replace('#include <common>', '#include <common>\nuniform float uNight, uRtmBase, uLampOn; uniform sampler2D uLampMap; uniform vec4 uLampBox, uLampFade;' + (o.panes ? '\nvarying vec2 vPane;' : ''))
            .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\n' + code.join('\n'));
        };
        mat.customProgramCacheKey = () => 'rtm-' + key;
        return mat;
      };

      // ---- materials. The masonry and painted walls are one vertex-coloured material (photo colours, converted by
      // the kit's calibration); glass, skylights and the vault metal keep their own optics.
      const COL = {
        gran: '#8c7c72',      // the headhouse's pink granite base
        brick: '#955646',     // the headhouse's salmon-red brick
        cream: '#cbbf9f',     // cream terra cotta: frames, bands, frieze, cornice, the loggia columns
        tan: '#c0a595',       // the shed's painted flanks and the bridges' frames
        roof: '#5a5d61',      // flat membrane roofs and rooftop plant
        soffit: '#4a3a34',    // the loggia gallery's floor and ceiling in shadow
        granG: '#9b958b',     // the market's rock-faced grey granite piers
        buff: '#c8b27f'       // the market's buff brick between them
      };
      const COLV = {}; for (const k in COL) COLV[k] = new THREE.Color(K.stored(COL[k]));
      const mMas = hook(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, metalness: 0 }), { roof: true, lamp: true }, 'mas');
      const mGlass = hook(K.glass().clone(), { panes: true }, 'glass');
      const mSky = hook(K.mat('#6e7a83', { rough: 0.35, metal: 0.1 }).clone(), { glow: [0.12, 0.097, 0.065] }, 'sky');     // #ffcf8a at 0.12
      const mMetal = hook(K.mat('#858c91', { rough: 0.6, metal: 0.1 }).clone(), { roof: true }, 'metal');

      // ---- ground: the drawn ground under each part; stand on the lowest, foundations below it
      const gAt = (u, v) => { const p = F.p(u, v); return api.ground(p[0], p[1]); };
      const hS = [[2, -2], [41, -2], [81, -2], [2, -31], [41, -31], [81, -31], [2, -45], [81, -45]].map((q) => gAt(q[0], q[1]));
      const sS = [[2, -60], [80, -60], [2, -130], [80, -130], [2, -198], [41, -198], [80, -198], [41, -222]].map((q) => gAt(q[0], q[1]));
      // the street fronts set each part's datum (the ground is within 0.7 m everywhere); foundations run 4 m down
      const mean = (a) => a.reduce((x, y) => x + y, 0) / a.length;
      const HB = mean(hS.slice(0, 3)), SB = mean(sS);
      U.base.value = Math.min(HB, SB);
      if (inApp) api.log('rtm ground: headhouse ' + hS.map((g) => g.toFixed(2)).join(' ') + ' | shed ' + sS.map((g) => g.toFixed(2)).join(' ') + ' | HB ' + HB.toFixed(2) + ' SB ' + SB.toFixed(2));
      const FOUND = 4;

      // ---- lit windows: a seeded draw per room (a hotel room's pair of windows lights together)
      let seed = 0x5eed1893;
      const rnd = () => { seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
      // uv.x = round(level x 100) + tint (0 .. 0.99), uv.y = height within the pane (0 sill, 1 head) when `grad`
      const setLit = (g, b, t, grad) => {
        const n = g.attributes.position.count, pa = g.attributes.position, uv = new Float32Array(n * 2);
        let y0 = Infinity, y1 = -Infinity; if (grad) for (let i = 0; i < n; i++) { y0 = Math.min(y0, pa.getY(i)); y1 = Math.max(y1, pa.getY(i)); }
        const x = Math.round(b * 100) + Math.min(0.99, Math.max(0, t));
        for (let i = 0; i < n; i++) { uv[2 * i] = x; uv[2 * i + 1] = grad && y1 > y0 ? (pa.getY(i) - y0) / (y1 - y0) : 0.5; }
        g.setAttribute('uv', new THREE.BufferAttribute(uv, 2)); g.userData.litSet = true; return g;
      };
      const draw = (L) => (L && rnd() < L.p ? [L.b[0] + (L.b[1] - L.b[0]) * rnd(), L.t[0] + (L.t[1] - L.t[0]) * rnd()] : [0, 0]);
      const LIT = {
        hotel: { p: 0.45, b: [0.45, 0.85], t: [0.05, 0.60] },     // the Marriott's rooms, floors 4 to 8 and the rear
        func: { p: 0.55, b: [0.40, 0.75], t: [0.40, 0.70] },      // floors 2 and 3: the hotel's lobby and function rooms
        loggia: { p: 0.85, b: [0.50, 0.80], t: [0.20, 0.45] },    // the loggia's doors, the lobby behind them
        shops: { p: 0.75, b: [0.45, 0.80], t: [0.10, 0.45] },     // Market Street's shops and restaurants
        market: { p: 0.25, b: [0.25, 0.50], t: [0.25, 0.55] },    // the market after hours: night lights only
        hall: { p: 0.55, b: [0.30, 0.60], t: [0.50, 0.85] }       // the track floor: the Convention Center's halls
      };

      // local (u, y, v) geometry collected per part, placed at the end on its own base; `key` is a COL name (the
      // masonry) or a material
      const bag = [];
      const put = (key, g, base) => { if (Array.isArray(g)) g.forEach((x) => bag.push([key, x, base])); else bag.push([key, g, base]); };
      const BX = (u0, u1, y0, y1, v0, v1) => { const g = new THREE.BoxGeometry(Math.abs(u1 - u0), y1 - y0, Math.abs(v1 - v0)); g.translate((u0 + u1) / 2, (y0 + y1) / 2, (v0 + v1) / 2); return g; };

      // ---- faces: axis 'v' = a wall on the plane v = c (Market, rear, the shed ends), axis 'u' = on u = c (12th, east);
      // s = outward sign. Face space: a along the wall, y up, z = depth INTO the wall. The map keeps handedness, so an
      // extruded shape's z = 0 cap faces out.
      const fmat = (f) => {
        const m = new THREE.Matrix4(), s = f.s, c = f.c;
        if (f.axis === 'v') m.set(-s, 0, 0, 0, 0, 1, 0, 0, 0, 0, -s, c, 0, 0, 0, 1);
        else m.set(0, 0, -s, c, 0, 1, 0, 0, s, 0, 0, 0, 0, 0, 0, 1);
        return m;
      };
      const aOf = (f, p) => (f.axis === 'v' ? -f.s * p : f.s * p);
      const fp = (f, a, y, z) => (f.axis === 'v' ? [-f.s * a, y, f.c - f.s * z] : [f.c - f.s * z, y, f.s * a]);
      const face = (axis, c, s) => ({ axis, c, s });
      const holePts = (f, h) => {
        const a0 = Math.min(aOf(f, h.p0), aOf(f, h.p1)), a1 = Math.max(aOf(f, h.p0), aOf(f, h.p1));
        const pts = [V2(a0, h.y0), V2(a1, h.y0), V2(a1, h.y1)];
        if (h.arch) { const r = (a1 - a0) / 2, ac = (a0 + a1) / 2, n = 8; for (let k = 1; k < n; k++) pts.push(V2(ac + r * Math.cos(Math.PI * k / n), h.y1 + r * Math.sin(Math.PI * k / n))); }
        pts.push(V2(a0, h.y1));
        return pts;
      };
      const top = (h) => h.y1 + (h.arch ? Math.abs(h.p1 - h.p0) / 2 : 0);
      // a wall layer from p0 to p1 (u or v), y0 to y1, `depth` deep, with openings; behind every opening that is not
      // an open passage, a glass pane with its own lit draw (L = a LIT spec, false for no glass)
      const layer = (key, f, p0, p1, y0, y1, holes, depth, base, L) => {
        const a0 = Math.min(aOf(f, p0), aOf(f, p1)), a1 = Math.max(aOf(f, p0), aOf(f, p1));
        const sh = new THREE.Shape([V2(a0, y0), V2(a1, y0), V2(a1, y1), V2(a0, y1)]);
        for (const h of holes) sh.holes.push(new THREE.Path(holePts(f, h)));
        const g = new THREE.ExtrudeGeometry(sh, { depth, bevelEnabled: false, steps: 1, curveSegments: 1 });
        g.applyMatrix4(fmat(f));
        put(key, g, base);
        if (L === false) return;
        const rooms = new Map(), z = depth - 0.03;
        for (const h of holes) {
          if (h.open) continue;
          const b0 = Math.min(aOf(f, h.p0), aOf(f, h.p1)) - 0.03, b1 = Math.max(aOf(f, h.p0), aOf(f, h.p1)) + 0.03, yt = top(h) + 0.03, yb = h.y0 - 0.03;
          let d = h.rm != null ? rooms.get(h.rm) : null;
          if (!d) { d = draw(L); if (h.rm != null) rooms.set(h.rm, d); }
          const q = K.quad(fp(f, b0, yb, z), fp(f, b1, yb, z), fp(f, b1, yt, z), fp(f, b0, yt, z), fp(f, (b0 + b1) / 2, (yb + yt) / 2, depth + 3));
          put(mGlass, setLit(q, d[0], d[1], true), base);
        }
      };
      // a box in face space (z < 0 stands proud of the face)
      const fbox = (f, p0, p1, y0, y1, z0, z1) => {
        const a0 = Math.min(aOf(f, p0), aOf(f, p1)), a1 = Math.max(aOf(f, p0), aOf(f, p1));
        const g = new THREE.BoxGeometry(a1 - a0, y1 - y0, z1 - z0); g.translate((a0 + a1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
        return g.applyMatrix4(fmat(f));
      };
      // horizontal bands across a face, broken wherever an opening crosses them
      const bands = (key, f, p0, p1, ys, hb, holes, proud, base) => {
        const lo = Math.min(p0, p1), hi = Math.max(p0, p1);
        for (const yb of ys) {
          const cut = holes.filter((h) => h.y0 < yb + hb && top(h) > yb).map((h) => [Math.min(h.p0, h.p1) - 0.12, Math.max(h.p0, h.p1) + 0.12]).sort((x, y) => x[0] - y[0]);
          let p = lo;
          for (const c of cut) { if (c[0] > p + 0.05) put(key, fbox(f, p, Math.min(c[0], hi), yb, yb + hb, -proud, 0.1), base); p = Math.max(p, c[1]); }
          if (hi > p + 0.05) put(key, fbox(f, p, hi, yb, yb + hb, -proud, 0.1), base);
        }
      };
      // a voussoir ring round an arched opening (half annulus, proud of the face)
      const ring = (key, f, h, w, proud, base) => {
        const a0 = Math.min(aOf(f, h.p0), aOf(f, h.p1)), a1 = Math.max(aOf(f, h.p0), aOf(f, h.p1)), r = (a1 - a0) / 2, ac = (a0 + a1) / 2, n = 8;
        const pts = [];
        for (let k = 0; k <= n; k++) pts.push(V2(ac + (r + w) * Math.cos(Math.PI * k / n), h.y1 + (r + w) * Math.sin(Math.PI * k / n)));
        for (let k = n; k >= 0; k--) pts.push(V2(ac + r * Math.cos(Math.PI * k / n), h.y1 + r * Math.sin(Math.PI * k / n)));
        const g = new THREE.ExtrudeGeometry(new THREE.Shape(pts), { depth: proud + 0.08, bevelEnabled: false, curveSegments: 1 });
        g.translate(0, 0, -proud);
        put(key, g.applyMatrix4(fmat(f)), base);
      };
      // radiating voussoirs: n wedge blocks alternating two colours, the middle one a taller keystone
      const wedges = (f, h, w, proud, base, keys, n) => {
        const a0 = Math.min(aOf(f, h.p0), aOf(f, h.p1)), a1 = Math.max(aOf(f, h.p0), aOf(f, h.p1)), r = (a1 - a0) / 2, ac = (a0 + a1) / 2, mid = (n - 1) / 2;
        for (let k = 0; k < n; k++) {
          const t0 = Math.PI * k / n, t1 = Math.PI * (k + 1) / n, ro = r + w + (k === mid ? 0.3 : 0);
          const pts = [V2(ac + r * Math.cos(t0), h.y1 + r * Math.sin(t0)), V2(ac + ro * Math.cos(t0), h.y1 + ro * Math.sin(t0)), V2(ac + ro * Math.cos(t1), h.y1 + ro * Math.sin(t1)), V2(ac + r * Math.cos(t1), h.y1 + r * Math.sin(t1))];
          const pr = proud + (k === mid ? 0.08 : 0);
          const g = new THREE.ExtrudeGeometry(new THREE.Shape(pts), { depth: pr + 0.08, bevelEnabled: false, curveSegments: 1 });
          g.translate(0, 0, -pr);
          put(keys[k % 2], g.applyMatrix4(fmat(f)), base);
        }
      };
      let roomCtr = 0;
      const pairs = (centres, gap, w, y0, y1, arch) => { const o = []; for (const c of centres) { const rm = roomCtr++; for (const d of [-gap, gap]) o.push({ p0: c + d - w / 2, p1: c + d + w / 2, y0, y1, arch, rm }); } return o; };
      const singles = (centres, w, y0, y1, arch) => centres.map((c) => ({ p0: c - w / 2, p1: c + w / 2, y0, y1, arch }));
      const range = (a, step, n) => Array.from({ length: n }, (_, k) => a + step * k);

      // =================================================================== HEADHOUSE
      const HH = HB;
      const Y = { g: 7.9, z2: 19.1, ledge: 20.1, z3: 37.3, band: 38.0, attic: 42.4, frieze: 44.7, top: 47.4, roof: 45.6 };
      const W_BAYS = [5.6, 11.9, 18.2], C_BAYS = range(24.6, 6.3, 6), E_BAYS = [62.1, 68.4, 74.7], E_SINGLE = 80.3;
      const T_BAYS = [-5.6, -11.9, -18.2, -24.5], T_SINGLE = -30.1;      // 12th Street face, v
      const CR = 3.2;                                                       // rounded base corner at 12th and Market
      const fM = face('v', 0, 1), fMc = face('v', -0.9, 1), fT = face('u', 0, -1), fR = face('v', -32.8, -1);
      const LG = { face: -0.9, arc: 0.8, back: -4.1, wall: 0.3, core: -4.45, floor: 9.75, ceil: 17.5 };   // the loggia, v and y

      // core (inside every layer; recessed behind the loggia's back wall)
      put('brick', BX(0.9, 82.8, -FOUND, Y.g, -32.45, -4.2), HH);
      put('brick', BX(0.9, 82.8, Y.g, Y.z2, -32.45, LG.core), HH);
      put('brick', BX(0.9, 82.8, Y.z2, Y.roof, -32.45, -4.2), HH);
      put('brick', BX(CR, 82.8, -FOUND, Y.g, -4.2, -0.93), HH);
      put('brick', BX(0.9, 22.3, Y.g, Y.z2, LG.core, -0.47), HH);
      put('brick', BX(58.4, 82.8, Y.g, Y.z2, LG.core, -0.47), HH);
      put('brick', BX(0.9, 82.8, Y.z2, Y.roof, -4.2, -1.4), HH);
      // pavilion side returns where the centre steps back 0.9 m
      put('brick', BX(21.8, 22.3, Y.g, Y.top - 0.4, -0.9, -0.3), HH); put('brick', BX(58.4, 58.9, Y.g, Y.top - 0.4, -0.9, -0.3), HH);
      // the rounded corner: granite and banded brick to the ledge
      { const g1 = new THREE.CylinderGeometry(CR, CR, Y.g + FOUND, 16, 1); g1.translate(CR, (Y.g - FOUND) / 2, -CR); put('gran', g1, HH);
        const g2 = new THREE.CylinderGeometry(CR, CR, Y.z2 - Y.g, 16, 1); g2.translate(CR, (Y.g + Y.z2) / 2, -CR); put('brick', g2, HH);
        for (const yb of [8.5].concat(range(10.15, 0.95, 9))) { const b = new THREE.CylinderGeometry(CR + 0.06, CR + 0.06, yb === 8.5 ? 1.2 : 0.22, 16, 1, true); b.translate(CR, yb + (yb === 8.5 ? 0.6 : 0.11), -CR); put('cream', b, HH); } }

      // -- ground floor: pink granite, round arches (Market 12, 12th 4) and doors: shops and restaurants
      const gM = singles(range(5.8, 6.3, 12), 3.9, 0.35, 4.9, true).concat([{ p0: 80.1, p1: 81.8, y0: 0.35, y1: 3.9 }]);
      layer('gran', fM, CR, 82.8, -FOUND, Y.g, gM, 0.9, HH, LIT.shops);
      const gT = singles([-5.9, -12.2, -18.5, -24.8], 3.9, 0.35, 4.9, true).concat([{ p0: -29.6, p1: -31.3, y0: 0.35, y1: 3.9 }]);
      layer('gran', fT, -CR, -32.8, -FOUND, Y.g, gT, 0.9, HH, LIT.shops);
      for (const h of gM.slice(0, 12)) ring('gran', fM, h, 0.55, 0.12, HH);
      for (const h of gT.slice(0, 4)) ring('gran', fT, h, 0.55, 0.12, HH);
      put('gran', fbox(fM, CR, 82.8, -FOUND, 0.45, -0.18, 0.1), HH);              // plinth
      put('gran', fbox(fT, -CR, -32.8, -FOUND, 0.45, -0.18, 0.1), HH);
      put('cream', fbox(fM, CR, 82.8, Y.g - 0.4, Y.g, -0.3, 0.1), HH);            // granite cap
      put('cream', fbox(fT, -CR, -32.8, Y.g - 0.4, Y.g, -0.3, 0.1), HH);

      // -- floors 2 and 3: banded brick. Pavilions: paired round-arched windows over paired square ones.
      const f2 = (bays) => pairs(bays, 0.95, 1.4, 9.8, 12.5, true).concat(pairs(bays, 0.95, 1.4, 15.2, 17.9, false));
      const hW = f2(W_BAYS), hE = f2(E_BAYS).concat(singles([E_SINGLE], 1.3, 9.8, 12.5, true), singles([E_SINGLE], 1.3, 15.2, 17.9, false));
      const hT = f2(T_BAYS).concat(singles([T_SINGLE], 1.3, 9.8, 12.5, true), singles([T_SINGLE], 1.3, 15.2, 17.9, false));
      layer('brick', fM, CR, 22.3, Y.g, Y.z2, hW.filter((h) => h.p0 > CR + 0.3), 0.45, HH, LIT.func);
      layer('brick', fM, 58.4, 82.8, Y.g, Y.z2, hE, 0.45, HH, LIT.func);
      layer('brick', fT, -CR, -32.8, Y.g, Y.z2, hT.filter((h) => h.p1 < -CR - 0.3), 0.45, HH, LIT.func);
      const bandYs = range(10.15, 0.95, 9);
      bands('cream', fM, CR, 22.3, bandYs, 0.22, hW, 0.06, HH);
      bands('cream', fM, 58.4, 82.8, bandYs, 0.22, hE, 0.06, HH);
      bands('cream', fT, -CR, -32.8, bandYs, 0.22, hT, 0.06, HH);
      // balustrade course under the second floor, all round the street fronts
      put('cream', fbox(fM, CR, 22.3, 8.5, 9.7, -0.3, 0.1), HH);
      put('cream', fbox(fM, 58.4, 82.8, 8.5, 9.7, -0.3, 0.1), HH);
      put('cream', fbox(fMc, 22.3, 58.4, 8.5, 9.7, -0.3, 0.1), HH);
      put('cream', fbox(fT, -CR, -32.8, 8.5, 9.7, -0.3, 0.1), HH);
      for (const h of hW.concat(hE, hT)) if (h.arch && Math.abs(h.p0) > CR + 0.3) ring('cream', h.p0 < 0 ? fT : fM, h, 0.18, 0.06, HH);

      // -- the centre: an OPEN two-storey loggia. (1) the arcade face, 0.8 m deep: six arches on piers, no glass;
      // (2) the gallery behind it, 2.4 m deep, its floor and ceiling in shadow; (3) the back wall with six glazed
      // arched doors; bold radiating voussoirs, cream and brick, and paired Ionic columns standing free of the piers
      const hLog = singles(C_BAYS, 4.5, 9.8, 15.2, true);
      layer('brick', fMc, 22.3, 58.4, Y.g, Y.z2, hLog, LG.arc, HH, false);
      bands('cream', fMc, 22.3, 58.4, bandYs, 0.22, hLog, 0.06, HH);
      put('soffit', BX(22.3, 58.4, Y.g, LG.floor, LG.core, LG.face - LG.arc + 0.02), HH);           // gallery floor
      put('soffit', BX(22.3, 58.4, LG.ceil, Y.z2, LG.core, LG.face - LG.arc + 0.02), HH);           // gallery ceiling
      const fL = face('v', LG.back, 1), hBack = singles(C_BAYS, 3.6, 9.8, 15.2, true);
      layer('brick', fL, 22.3, 58.4, LG.floor, LG.ceil, hBack, LG.wall, HH, LIT.loggia);
      for (const h of hBack) ring('cream', fL, h, 0.28, 0.05, HH);
      for (const h of hLog) {
        wedges(fMc, h, 1.1, 0.1, HH, ['cream', 'brick'], 13);
        put('cream', fbox(fMc, h.p0, h.p1, 9.7, 10.8, 0.2, 0.6), HH);            // the loggia's balustrade
        put('cream', fbox(fMc, h.p0, h.p1, 9.7, 9.8, 0.05, 0.75), HH);           // its sill
      }
      for (let k = 0; k <= 6; k++) {
        const pu = 22.35 + 6.3 * k, lo = k === 0 ? pu - 0.05 : pu - 1.0, hi = k === 6 ? pu + 0.05 : pu + 1.0;
        put('cream', fbox(fMc, lo, hi, 9.7, 10.8, -0.72, 0.05), HH);              // pedestal
        put('cream', fbox(fMc, lo, hi, 15.2, 15.55, -0.72, 0.05), HH);            // impost the arches spring from
        for (const d of k === 0 ? [0.55] : k === 6 ? [-0.55] : [-0.55, 0.55]) {
          const q = fp(fMc, aOf(fMc, pu + d), 0, -0.36);
          put('cream', K.column(q[0], 10.8, q[2], 4.4, 0.24, 'ionic', 10), HH);
        }
      }

      // -- the ledge under the fourth floor, with a balustrade in front of every bay
      const ledge = (f, p0, p1, bays, w) => {
        put('cream', fbox(f, p0, p1, Y.z2, Y.ledge, -0.7, 0.2), HH);
        for (const b of bays) put('cream', fbox(f, b - w / 2, b + w / 2, Y.ledge, Y.ledge + 0.9, -0.6, -0.35), HH);
      };
      ledge(fM, -0.7, 22.3, W_BAYS, 4.4); ledge(fMc, 22.3, 58.4, C_BAYS, 4.4); ledge(fM, 58.4, 82.8, E_BAYS.concat([E_SINGLE]), 2.2);
      ledge(fT, 0, -32.8, T_BAYS, 4.4);

      // -- floors 4 to 7: cream terra-cotta bays of paired round-arched windows between red brick piers. Floor 4's
      // windows are tall (3.65 m to the crown), floors 5 to 7 about 2.6 m (measured on the Highsmith elevation)
      const up = (bays, single) => {
        let o = [];
        for (let k = 0; k < 4; k++) {
          const y0 = k === 0 ? 21.0 : 21.0 + 4.05 * k + 0.6, y1 = k === 0 ? y0 + 3.0 : y0 + 1.95;
          o = o.concat(pairs(bays, 0.95, 1.3, y0, y1, true));
          if (single != null) o = o.concat(singles([single], 1.2, y0, y1, true));
        }
        return o;
      };
      const u3W = up(W_BAYS), u3C = up(C_BAYS), u3E = up(E_BAYS, E_SINGLE), u3T = up(T_BAYS, T_SINGLE);
      layer('cream', fM, 0, 22.3, Y.ledge, Y.z3, u3W, 0.45, HH, LIT.hotel);
      layer('cream', fMc, 22.3, 58.4, Y.ledge, Y.z3, u3C, 0.45, HH, LIT.hotel);
      layer('cream', fM, 58.4, 82.8, Y.ledge, Y.z3, u3E, 0.45, HH, LIT.hotel);
      layer('cream', fT, 0, -32.8, Y.ledge, Y.z3, u3T, 0.45, HH, LIT.hotel);
      // brick piers between the bays, a little proud
      const piers = (f, p0, p1, panels) => {
        const lo = Math.min(p0, p1), hi = Math.max(p0, p1), cuts = panels.map((c) => [c[0] - c[1] / 2, c[0] + c[1] / 2]).sort((x, y) => x[0] - y[0]);
        let p = lo;
        for (const c of cuts) { if (c[0] > p + 0.1) put('brick', fbox(f, p, c[0], Y.ledge, Y.z3, -0.1, 0.1), HH); p = Math.max(p, c[1]); }
        if (hi > p + 0.1) put('brick', fbox(f, p, hi, Y.ledge, Y.z3, -0.1, 0.1), HH);
      };
      piers(fM, 0, 22.3, W_BAYS.map((b) => [b, 4.4]));
      piers(fMc, 22.3, 58.4, C_BAYS.map((b) => [b, 4.4]));
      piers(fM, 58.4, 82.8, E_BAYS.map((b) => [b, 4.4]).concat([[E_SINGLE, 2.2]]));
      piers(fT, 0, -32.8, T_BAYS.map((b) => [b, 4.4]).concat([[T_SINGLE, 2.2]]));

      // -- band, eighth-floor attic, frieze of oculi, the deep cornice
      const attic = (f, p0, p1, bays, single) => {
        put('cream', fbox(f, p0, p1, Y.z3, Y.band, -0.3, 0.1), HH);
        const hs = pairs(bays, 0.95, 1.2, 38.7, 41.4, false).concat(single != null ? singles([single], 1.1, 38.7, 41.4, false) : []);
        layer('cream', f, p0, p1, Y.band, Y.attic, hs, 0.4, HH, LIT.hotel);
        put('cream', fbox(f, p0, p1, Y.attic, Y.frieze, -0.15, 0.1), HH);
        const lo = Math.min(p0, p1), hi = Math.max(p0, p1), n = Math.floor((hi - lo) / 2.1);
        for (let k = 0; k < n; k++) {
          const pc = lo + (hi - lo) * (k + 0.5) / n, q = fp(f, aOf(f, pc), 43.55, -0.17), dsk = new THREE.CircleGeometry(0.42, 8);
          const nrm = f.axis === 'v' ? [0, 0, f.s] : [f.s, 0, 0];
          dsk.lookAt(new THREE.Vector3(nrm[0], nrm[1], nrm[2])); dsk.translate(q[0], q[1], q[2]);
          put(mGlass, setLit(dsk, 0, 0), HH);
        }
      };
      attic(fM, -0.1, 22.3, W_BAYS); attic(fMc, 22.3, 58.4, C_BAYS); attic(fM, 58.4, 82.8, E_BAYS, E_SINGLE); attic(fT, 0, -32.8, T_BAYS, T_SINGLE);
      const cornice = (f, p0, p1, yt, k) => {
        if (yt - 1.9 > Y.frieze - 0.25) put('cream', fbox(f, p0, p1, Y.frieze - 0.3, yt - 1.9, -0.5 * k, 1.6), HH);
        put('cream', fbox(f, p0, p1, yt - 1.9, yt - 0.9, -1.75 * k, 1.6), HH);
        put('cream', fbox(f, p0, p1, yt - 0.9, yt - 0.45, -1.45 * k, 1.6), HH);
        put('cream', fbox(f, p0, p1, yt - 0.45, yt, -0.6 * k, 1.6), HH);
        // modillions under the corona, a metre apart
        const lo = Math.min(p0, p1), hi = Math.max(p0, p1);
        for (let p = lo + 0.6; p < hi - 0.3; p += 1.0) put('cream', fbox(f, p - 0.13, p + 0.13, yt - 2.3, yt - 1.9, -1.55 * k, -0.4), HH);
      };
      // the pavilions read by standing 0.9 m forward, their cornice only 0.3 m above the centre's
      cornice(fM, -1.35, 23.0, Y.top, 1); cornice(fM, 57.7, 82.8, Y.top, 1); cornice(fMc, 22.3, 58.4, Y.top - 0.3, 1);
      cornice(fT, 0, -32.8 - 0.5, Y.top, 1);
      // the rear over the link: plain brick, sash windows, a lighter cornice
      { const hs = []; for (const y0 of [16.2, 20.4, 24.6, 28.7, 32.8, 36.9]) for (let k = 0; k < 20; k++) hs.push({ p0: 2.4 + 4.1 * k, p1: 3.7 + 4.1 * k, y0, y1: y0 + 2.4 });
        layer('brick', fR, 0.9, 82.8, 14.5, Y.frieze, hs, 0.35, HH, LIT.hotel);
        put('cream', fbox(fR, 0, 82.8, Y.frieze, Y.top - 0.8, -0.3, 1.6), HH);
        put('cream', fbox(fR, 0, 82.8, Y.top - 0.8, Y.top - 0.3, -0.6, 1.6), HH); }
      // roof, bulkheads and plant
      put('roof', BX(0.5, 82.4, Y.roof - 0.3, Y.roof + 0.1, -32.3, -0.6), HH);
      put('brick', BX(38, 45, Y.roof, Y.roof + 4.2, -26, -20), HH);
      put('roof', BX(38, 45, Y.roof + 4.2, Y.roof + 4.5, -26, -20), HH);
      put(mMetal, BX(12, 20, Y.roof, Y.roof + 2.4, -22, -12), HH);
      put(mMetal, BX(60, 70, Y.roof, Y.roof + 2.8, -24, -15), HH);
      put(mMetal, BX(26, 31, Y.roof, Y.roof + 1.8, -12, -8), HH);

      // -- the corner oriel: ONE storey (floor 4) of round-arched lights between colonnettes, an entablature (the
      // "Philadelphia and Reading" band), a balustraded balcony at the floor-5 sill, and under it a short stepped
      // corbel flaring out of the rounded base corner. Floor 5 behind the balcony is the plain brick corner pier.
      { const oc = [0.55, -0.55], ro = 2.6, cy = (g, y0, h) => { g.translate(oc[0], y0 + h / 2, oc[1]); return g; };
        put('cream', cy(new THREE.CylinderGeometry(ro, ro, 4.2, 16, 1), 20.1, 4.2), HH);                         // drum
        put('cream', cy(new THREE.CylinderGeometry(ro + 0.12, ro + 0.12, 0.3, 16, 1), 20.1, 0.3), HH);           // sill course
        put('cream', cy(new THREE.CylinderGeometry(ro + 0.15, ro + 0.15, 1.0, 16, 1), 24.3, 1.0), HH);           // entablature
        put('cream', cy(new THREE.CylinderGeometry(ro + 0.5, ro + 0.4, 0.3, 16, 1), 25.3, 0.3), HH);             // balcony slab
        put('cream', cy(new THREE.CylinderGeometry(ro + 0.42, ro + 0.42, 0.14, 16, 1), 26.2, 0.14), HH);         // its rail
        // corbel: three stacked frusta down to the rounded base
        put('cream', cy(new THREE.CylinderGeometry(ro, 2.2, 0.6, 16, 1), 19.5, 0.6), HH);
        put('cream', cy(new THREE.CylinderGeometry(2.2, 1.8, 0.8, 16, 1), 18.7, 0.8), HH);
        put('cream', cy(new THREE.CylinderGeometry(1.8, 1.4, 1.0, 16, 1), 17.7, 1.0), HH);
        // balusters on the part of the balcony that stands outside the walls
        for (let k = 0; k < 40; k++) {
          const t = 2 * Math.PI * k / 40, bx = oc[0] + (ro + 0.42) * Math.sin(t), bz = oc[1] + (ro + 0.42) * Math.cos(t);
          if (!(bx < -0.15 || bz > 0.15)) continue;
          const b = new THREE.BoxGeometry(0.11, 0.62, 0.11); b.translate(bx, 25.9, bz); put('cream', b, HH);
        }
        // three arched lights facing the corner and 40 degrees either side, colonnettes between them
        const lights = (hdg) => { const t = hdg * Math.PI / 180; return [Math.cos(t), -Math.sin(t)]; };
        for (const ang of [-40, 0, 40]) {
          const [dx, dz] = lights(225 + ang), rot = Math.atan2(dx, dz), rr = ro + 0.07;
          const w = new THREE.PlaneGeometry(1.1, 2.05); w.translate(0, 21.0 + 1.025, 0);
          const hd = new THREE.CircleGeometry(0.55, 8, 0, Math.PI); hd.translate(0, 23.05, 0);
          for (const g of [w, hd]) { g.rotateY(rot); g.translate(oc[0] + dx * rr, 0, oc[1] + dz * rr); }
          const d = rnd() < 0.5 ? [0.55, 0.3] : [0, 0];
          put(mGlass, setLit(w, d[0], d[1], true), HH); put(mGlass, setLit(hd, d[0], d[1]), HH);
        }
        for (const ang of [-60, -20, 20, 60]) {
          const [dx, dz] = lights(225 + ang), c = new THREE.CylinderGeometry(0.1, 0.12, 3.9, 8, 1);
          c.translate(oc[0] + dx * (ro + 0.1), 20.4 + 1.95, oc[1] + dz * (ro + 0.1)); put('cream', c, HH);
        }
      }

      // =================================================================== THE LINK (v -46.4 .. -32.8) AND THE SHED
      const SH = SB, WT = 14.5;                               // flank wall top
      const fS12 = face('u', 0, -1), fSN = face('v', -200.6, -1), fSE = face('u', 82, 1);
      // lower core: the market hall, split by the Filbert Street passage; the track deck on top at 7.6
      const FIL = [-104.5, -95.5];
      put('tan', BX(0.6, 81.4, -FOUND, 7.6, FIL[1], -46.4), SH);
      put('tan', BX(0.6, 81.4, -FOUND, 7.6, -200.0, FIL[0]), SH);
      put('tan', BX(0.6, 81.4, 5.6, 7.6, FIL[0], FIL[1]), SH);
      put('tan', BX(0.4, 82.4, -FOUND, WT, -46.4, -32.8), HH);                   // the link, two storeys
      put('roof', BX(0.4, 82.4, WT, WT + 0.3, -46.4, -32.8), HH);
      // flank walls to the vault's springing, and the gutters inside them
      put('tan', BX(0.4, 1.3, 7.6, WT, -200.6, -46.4), SH);
      put('tan', BX(80.7, 81.6, 7.6, WT, -200.6, -46.4), SH);
      put('tan', BX(0.4, 81.6, 7.6, WT, -200.2, -199.4), SH);
      put('roof', BX(1.3, 2.75, WT - 0.3, WT, -200.3, -46.4), SH);
      put('roof', BX(79.25, 80.7, WT - 0.3, WT, -200.3, -46.4), SH);
      // the market's street storey: buff brick with rock-faced grey granite piers between the shop openings, a
      // granite base course, a cream course, then the track floor's big sash windows in the painted upper wall
      const marketBase = (f, p0, p1, g, base) => {
        layer('buff', f, p0, p1, -FOUND, 6.4, g, 0.6, base, LIT.market);
        const lo = Math.min(p0, p1), hi = Math.max(p0, p1), cuts = g.map((h) => [Math.min(h.p0, h.p1), Math.max(h.p0, h.p1)]).sort((x, y) => x[0] - y[0]);
        let p = lo;
        for (const c of cuts) { if (c[0] > p + 0.3) put('granG', fbox(f, p + 0.1, c[0] - 0.1, -FOUND, 6.4, -0.16, 0.1), base); p = Math.max(p, c[1]); }
        if (hi > p + 0.3) put('granG', fbox(f, p + 0.1, hi - 0.1, -FOUND, 6.4, -0.16, 0.1), base);
        put('granG', fbox(f, lo, hi, -FOUND, 0.35, -0.2, 0.1), base);
        put('cream', fbox(f, lo, hi, 6.4, 7.3, -0.25, 0.1), base);
      };
      // 12th Street flank (the link and the shed)
      { const g = [], u = [];
        for (let v = -36.0; v > -199; v -= 6.3) {
          if (v < FIL[1] + 1 && v > FIL[0] - 1) continue;
          g.push({ p0: v + 1.9, p1: v - 1.9, y0: 0.35, y1: 4.6 });
          u.push({ p0: v + 2.3, p1: v - 2.3, y0: 8.1, y1: 12.7 });
        }
        const open = { p0: FIL[1], p1: FIL[0], y0: -FOUND, y1: 5.6, open: true };
        marketBase(fS12, -32.8, -200.6, g.concat([open]), SH);
        layer('tan', fS12, -32.8, -200.6, 7.3, 13.6, u, 0.4, SH, LIT.hall);
        put('tan', fbox(fS12, -32.8, -200.6, 13.6, WT, -0.45, 0.1), SH);
        // pilasters between the upper windows
        for (const h of u) put('tan', fbox(fS12, h.p0 + 0.9, h.p0 + 0.2, 7.3, 13.6, -0.15, 0.1), SH); }
      // Arch Street end: same treatment either side of the bridge
      { const g = [], u = [];
        for (let x = 4.0; x < 80; x += 6.3) { g.push({ p0: x - 1.9, p1: x + 1.9, y0: 0.35, y1: 4.6 }); if (x < 21 || x > 62) u.push({ p0: x - 2.3, p1: x + 2.3, y0: 8.1, y1: 12.7 }); }
        marketBase(fSN, 0, 82, g, SH);
        layer('tan', fSN, 0, 82, 7.3, 13.6, u, 0.4, SH, LIT.hall);
        put('tan', fbox(fSN, 0, 82, 13.6, WT, -0.45, 0.1), SH); }
      // east flank against its neighbours: the passage and a plain painted wall
      layer('tan', fSE, -46.4, -200.6, -FOUND, WT, [{ p0: FIL[1], p1: FIL[0], y0: -FOUND, y1: 5.6, open: true }], 0.6, SH, false);
      // the passage: a dark tunnel lining under the deck
      put('roof', BX(0.6, 81.4, 5.3, 5.6, FIL[0], FIL[1]), SH);

      // ---- the vault: a three-centred pointed arch, 80.4 m span, 29 m rise over the 7.6 m track deck
      const U1 = 81.2, UM = 41.0, HALF = 40.2, SPR = 7.6, RISE = 29.0, VS = -46.4, VN = -200.6;
      const prof = (u) => { const t = Math.min(1, Math.abs((u - UM) / HALF)); return SPR + RISE * (0.7 * Math.sqrt(1 - t * t) + 0.3 * (1 - t)); };
      const NP = 40, PU = [];
      for (let k = 0; k <= NP; k++) PU.push(UM - HALF * Math.cos(Math.PI * k / NP));
      const PR = PU.map((u) => [u, prof(u)]);
      const nrm = PR.map((p, i) => {
        const a = PR[Math.max(0, i - 1)], b = PR[Math.min(NP, i + 1)], dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy);
        return [-dy / l, dx / l];
      });
      const vis = (i) => PR[i][1] > WT - 1.5 || (PR[i + 1] && PR[i + 1][1] > WT - 1.5);
      // strip along v following the profile between profile indices [i0, i1], offset `off` along the normal
      const strip = (v0, v1, i0, i1, off, sides) => {
        const pos = [], q = (i) => [PR[i][0] + nrm[i][0] * off, PR[i][1] + nrm[i][1] * off];
        const quad = (a, b, c, d) => pos.push(...a, ...b, ...c, ...a, ...c, ...d);
        for (let i = i0; i < i1; i++) {
          if (!vis(i)) continue;
          const p = q(i), r = q(i + 1);
          quad([p[0], p[1], v1], [r[0], r[1], v1], [r[0], r[1], v0], [p[0], p[1], v0]);
          if (sides) {
            const pb = PR[i], rb = PR[i + 1];
            quad([pb[0], pb[1], v1], [rb[0], rb[1], v1], [r[0], r[1], v1], [p[0], p[1], v1]);
            quad([p[0], p[1], v0], [r[0], r[1], v0], [rb[0], rb[1], v0], [pb[0], pb[1], v0]);
          }
        }
        const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.computeVertexNormals();
        return g;
      };
      put(mMetal, strip(VN, VS, 0, NP, 0, false), SH);
      // transverse ribs (the standing seams' batten lines) every ~9.6 m, and a ridge vent cap
      for (let k = 1; k < 16; k++) { const v = VS - (VS - VN) * k / 16; put(mMetal, strip(v - 0.25, v + 0.25, 0, NP, 0.28, true), SH); }
      { const iL = PU.findIndex((u) => u > UM - 1.3), iR = PU.findIndex((u) => u > UM + 1.3);
        put(mMetal, strip(VN + 3, VS - 3, iL - 1, iR, 0.5, true), SH); }
      // skylight bands either side of the ridge, in two runs: grey translucent glazing a little darker than the
      // roof, glazing bars every 2 m, curbs at the ends
      const sky = (v0, v1) => {
        for (const side of [-1, 1]) {
          const ua = UM + side * 2.6, ub = UM + side * 13.6, lo = Math.min(ua, ub), hi = Math.max(ua, ub);
          const i0 = PU.findIndex((u) => u >= lo), i1 = PU.findIndex((u) => u > hi) - 1;
          put(mSky, strip(v0, v1, i0, i1, 0.24, true), SH);
          put(mMetal, strip(v0, v0 + 0.25, i0, i1, 0.36, true), SH); put(mMetal, strip(v1 - 0.25, v1, i0, i1, 0.36, true), SH);
          for (let v = v0 + 2.0; v < v1 - 1.0; v += 2.0) put(mMetal, strip(v - 0.06, v + 0.06, i0, i1, 0.3, false), SH);
        }
      };
      sky(-186, -134.6); sky(-116, -59);
      // end arches: a deep lip following the profile, and glazed end screens with mullions and transoms; after dark
      // the screens show the Grand Hall's warm light
      const gablePts = (a) => { const o = []; for (let i = 0; i <= NP; i++) if (PR[i][1] >= WT) o.push(V2(a(PR[i][0]), PR[i][1])); return o; };
      const crossU = (y) => { let lo = UM, hi = U1; for (let n = 0; n < 30; n++) { const m = (lo + hi) / 2; if (prof(m) > y) lo = m; else hi = m; } return lo - UM; };
      for (const fv of [face('v', VN, -1), face('v', VS, 1)]) {
        // lip: band between the profile raised 0.7 and lowered 0.4, 1.2 m deep
        const outer = [], inner = [];
        for (let i = 0; i <= NP; i++) { if (PR[i][1] < WT - 0.6) continue; outer.push(V2(aOf(fv, PR[i][0] + nrm[i][0] * 0.7), PR[i][1] + nrm[i][1] * 0.7)); inner.push(V2(aOf(fv, PR[i][0] - nrm[i][0] * 0.4), PR[i][1] - nrm[i][1] * 0.4)); }
        const lip = new THREE.ExtrudeGeometry(new THREE.Shape(outer.concat(inner.reverse())), { depth: 1.2, bevelEnabled: false, curveSegments: 1 });
        put(mMetal, lip.applyMatrix4(fmat(fv)), SH);
        // the glass screen, set 0.9 m in
        const scr = new THREE.ExtrudeGeometry(new THREE.Shape(gablePts((u) => aOf(fv, u))), { depth: 0.1, bevelEnabled: false, curveSegments: 1 });
        scr.translate(0, 0, 0.9); put(mGlass, setLit(scr.applyMatrix4(fmat(fv)), 0.28, 0.12), SH);
        for (let u = 5.3; u < U1 - 3; u += 4.35) { const yt = prof(u) - 0.3; if (yt > WT + 0.5) put('tan', fbox(fv, u - 0.14, u + 0.14, WT, yt, 0.55, 0.95), SH); }
        for (const y of [19.2, 24.0, 28.8, 33.2]) { const d = crossU(y) - 0.3; put('tan', fbox(fv, UM - d, UM + d, y - 0.13, y + 0.13, 0.55, 0.95), SH); }
      }

      // ---- the bridge over Arch Street to the Convention Center (u 23 .. 60, v -223.3 .. -200.6)
      { const b0 = 23, b1 = 60, n0 = -223.3, n1 = -200.6;
        put('tan', BX(b0, b1, 6.6, 7.6, n0, n1), SH);
        put('tan', BX(b0, b1, 13.2, 14.2, n0, n1), SH);
        put('roof', BX(b0 + 0.3, b1 - 0.3, 14.2, 14.45, n0 + 0.3, n1 - 0.3), SH);
        put(mGlass, setLit(BX(b0 + 0.25, b1 - 0.25, 7.6, 13.2, n0, n1), 0.3, 0.75), SH);
        for (let v = n0 + 1.6; v < n1; v += 3.15) for (const u of [b0 + 0.15, b1 - 0.15]) put('tan', BX(u - 0.18, u + 0.18, 7.6, 13.2, v - 0.18, v + 0.18), SH);
        for (let u = b0 + 2.3; u < b1 - 1; u += 3.2) put('tan', BX(u - 0.18, u + 0.18, 7.6, 13.2, n1 - 0.4, n1 - 0.05), SH); }

      // ---- the skybridge over 12th Street to the Marriott (u -22.8 .. 0, v -41.4 .. -35)
      { const s0 = -22.8, s1 = 0.2, w0 = -41.4, w1 = -35.0;
        put('tan', BX(s0, s1, 7.8, 8.6, w0, w1), HH);
        put(mGlass, setLit(BX(s0, s1, 8.6, 12.9, w0 + 0.2, w1 - 0.2), 0.3, 0.7), HH);
        put(mMetal, BX(s0, s1, 12.9, 13.7, w0 - 0.1, w1 + 0.1), HH);
        for (let u = s0 + 1.4; u < s1; u += 2.9) for (const v of [w0 + 0.12, w1 - 0.12]) put('tan', BX(u - 0.15, u + 0.15, 8.6, 12.9, v - 0.15, v + 0.15), HH); }

      // ---- signs: the red neon READING TERMINAL MARKET sign on 12th Street north of Filbert, the Convention Center
      // marquee in the headhouse's middle arches, and the red letters over the 12th and Arch corner
      const signMesh = (lines, w, h, colors, bg, glow, gk, lp, facing, base) => {
        const cv = document.createElement('canvas'); cv.width = 512; cv.height = Math.round(512 * h / w);
        const cx = cv.getContext('2d');
        cx.fillStyle = bg; cx.fillRect(0, 0, cv.width, cv.height);
        cx.strokeStyle = '#e8e4da'; cx.lineWidth = 6; cx.strokeRect(6, 6, cv.width - 12, cv.height - 12);
        const lh = (cv.height - 24) / lines.length;
        cx.textAlign = 'center'; cx.textBaseline = 'middle';
        lines.forEach((t, i) => { cx.fillStyle = colors[i % colors.length]; cx.font = '800 ' + Math.round(lh * 0.78) + 'px Arial, sans-serif'; cx.fillText(t, cv.width / 2, 12 + lh * (i + 0.5), cv.width * 0.9); });
        const tex = new THREE.CanvasTexture(cv); tex.encoding = THREE.sRGBEncoding; tex.anisotropy = 4;
        const m = new THREE.MeshStandardMaterial({ map: tex, roughness: 0.6, emissive: new THREE.Color(glow), emissiveMap: tex, emissiveIntensity: gk });
        const g = new THREE.BoxGeometry(w, h, 0.25);
        // only the front face carries the canvas; the rest reads as the cabinet
        const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) if (i < 16 || i >= 20) uv.setXY(i, 0.02, 0.02);
        g.rotateY(facing); g.translate(lp[0], lp[1], lp[2]);
        F.place(g, base);
        const mesh = new THREE.Mesh(g, m); mesh.userData.noShadow = true;
        Bd.addMesh(mesh);
      };
      signMesh(['READING', 'TERMINAL', 'MARKET'], 5.2, 3.9, ['#ff5a6e', '#ff5a6e', '#ff8a96'], '#1c2a5c', '#ffffff', 0.55, [-0.45, 6.4, -107.2], -Math.PI / 2, SH);
      signMesh(['PENNSYLVANIA CONVENTION CENTER'], 13.0, 1.0, ['#f2efe6'], '#1f2a44', '#ffffff', 0.6, [37.2, 5.6, 0.75], 0, HH);
      // 12th and Arch: READING TERMINAL in red letters over a cream ring carrying MARKET, on a bracket at the corner
      { const cv = document.createElement('canvas'); cv.width = 512; cv.height = 400;
        const c2 = cv.getContext('2d');
        c2.clearRect(0, 0, 512, 400); c2.textAlign = 'center'; c2.textBaseline = 'middle';
        c2.fillStyle = '#d8404a'; c2.font = '900 78px Georgia, serif';
        c2.fillText('READING', 256, 62, 490); c2.fillText('TERMINAL', 256, 150, 500);
        c2.strokeStyle = '#efe8d8'; c2.lineWidth = 58; c2.beginPath(); c2.arc(256, 190, 175, Math.PI * 0.2, Math.PI * 0.8); c2.stroke();
        c2.fillStyle = '#d8404a'; c2.font = '900 46px Georgia, serif';
        const word = 'MARKET', span = Math.PI * 0.36;
        for (let i = 0; i < word.length; i++) { const t = Math.PI * 0.5 + span / 2 - span * (i + 0.5) / word.length; c2.save(); c2.translate(256 + 175 * Math.cos(t), 190 + 175 * Math.sin(t)); c2.rotate(t - Math.PI / 2); c2.fillText(word[i], 0, 2); c2.restore(); }
        const tex = new THREE.CanvasTexture(cv); tex.encoding = THREE.sRGBEncoding; tex.anisotropy = 4;
        const m = new THREE.MeshStandardMaterial({ map: tex, transparent: true, alphaTest: 0.3, roughness: 0.5, side: THREE.DoubleSide, emissive: new THREE.Color('#ffffff'), emissiveMap: tex, emissiveIntensity: 0.35 });
        const g = new THREE.PlaneGeometry(6.0, 4.69);
        g.rotateY(Math.atan2(-1, -1)); g.translate(-1.0, 7.2, -200.6 - 1.0);
        F.place(g, SH);
        const mesh = new THREE.Mesh(g, m); mesh.userData.noShadow = true; Bd.addMesh(mesh); }

      // ---- place everything: the masonry as one vertex-coloured mesh, the rest merged per material by the kit
      const mas = [];
      for (const [m, g, base] of bag) {
        F.place(g, base);
        if (typeof m === 'string') mas.push([g, COLV[m]]);
        else { if (m === mGlass && !g.userData.litSet) setLit(g, 0, 0); Bd.add(m, g); }
      }
      { let n = 0;
        const flat = mas.map(([g, c]) => { const q = g.index ? g.toNonIndexed() : g; if (!q.attributes.normal) q.computeVertexNormals(); n += q.attributes.position.count; return [q, c]; });
        const pos = new Float32Array(n * 3), nor = new Float32Array(n * 3), col = new Float32Array(n * 3);
        let o = 0;
        for (const [q, c] of flat) {
          const k = q.attributes.position.count;
          pos.set(q.attributes.position.array.subarray(0, k * 3), o * 3); nor.set(q.attributes.normal.array.subarray(0, k * 3), o * 3);
          for (let i = 0; i < k; i++) { col[(o + i) * 3] = c.r; col[(o + i) * 3 + 1] = c.g; col[(o + i) * 3 + 2] = c.b; }
          o += k;
        }
        const g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('normal', new THREE.BufferAttribute(nor, 3)); g.setAttribute('color', new THREE.BufferAttribute(col, 3));
        g.computeBoundingSphere();
        Bd.addMesh(new THREE.Mesh(g, mMas));
      }

      bag.length = 0; mas.length = 0;   // merged: nothing may hold the parts (the hooks close over this scope)
      return Bd.done();
    }
  });
})();
