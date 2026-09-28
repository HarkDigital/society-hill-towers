// Round 161 rebuild (the Sep 25 design study): the Divine Lorraine Hotel, Willis G. Hale's ten-storey Lorraine Apartments of 1892-94,
// 699 N. Broad Street at the south-east corner of Broad and Fairmount (HABS PA-6683; NRHP 02001427).
// Sources: HABS PA-6683 data pages and photos 1, 2, 4, 5, 6 (Library of Congress, pa3878), Wikipedia, Sky Neon Signs
// (the 2016 relighting: two signs, 4 ft channel letters, red neon), Commons photos "Divine Lorraine from Southwest" (2008),
// "Lorraine Hotel Broad St Philly" (the frontal view, 2010) and "View of above courtyard" (the court, open to the sky).
// What it is: a roughly square block of buff roman brick; the Broad Street front is split by a light court that runs half
// way back, bridged at the facade up to the main cornice by two stacked monumental arches, a four-window arcade between
// them and another at the 9th floor; each wing carries two oriel bays from the 2nd to the 8th floor. Over the main cornice
// the two wings rise apart as stepped towers with sky between them: a chamfered arcaded attic, a set-back tier with a
// lunette (the west end of the barrel-vaulted hall behind it: the auditorium north, the banquet hall south) and a narrow
// block under a low pediment facing Broad Street. The sides and rear carry narrow bay strips with oval windows between
// wide iron balconies at every floor over a banded base; the court walls are red common brick; three pedimented portals
// on Broad, the middle one a columned temple front. Two steel-lattice signs, DIVINE / LORRAINE / HOTEL in 4 ft red
// channel letters on three lines, stand on the roof right behind the towers over the north and south walls, lit red at night.
// Frame: u = east (into the block from Broad Street), v = south, rotated 9.65 degrees to the fitted facade line.
(function () {
  const DEG = Math.PI / 180;
  const CX = -1308.5, CZ = -2352.5, ANG = 9.65 * DEG;
  const U0 = -18.2, U1 = 17.3, V0 = -16.7, V1 = 16.2;     // facade (Broad St), rear, north (Fairmount), south
  const CV0 = -3.6, CV1 = 3.2, UC = -1.0;                  // the light court: its sides and its back wall
  const ca = Math.cos(ANG), sa = Math.sin(ANG);
  const W = (u, v) => [CX + u * ca - v * sa, CZ + u * sa + v * ca];
  const skipRing = [W(U0 - 1.4, V0 - 1.6), W(U1 + 1.4, V0 - 1.6), W(U1 + 1.4, V1 + 1.2), W(U0 - 1.4, V1 + 1.2)];

  RB.add({
    id: 'dl',
    name: 'Divine Lorraine Hotel',
    center: [CX, CZ],
    skip: [skipRing],
    views: [[250, 120, 50, 22], [280, 88, 36, 21], [335, 120, 58, 22]],
    build(api) {
      const { THREE, K } = api;
      const f = K.frame(CX, CZ, ANG);
      const fP = K.frame(CX, CZ, ANG + Math.PI / 2);        // faces normal to u: local (u', v') = (v, -u)
      // ---- ground: stand on Broad Street's sidewalk, foundation below the lowest corner
      const samp = [[U0, V0], [U0, V1], [U1, V0], [U1, V1], [U0 - 0.5, -0.2], [0, 0], [U0 - 3, -0.2]];
      const gs = samp.map(([u, v]) => { const p = f.p(u, v); return api.ground(p[0], p[1]); });
      const base = gs[4];
      const lowR = Math.min.apply(null, gs) - base - 1.5;   // relative to base
      if (api.where === 'app') api.log('[dl] ground ' + gs.map((g) => g.toFixed(2)).join(' ') + ' base ' + base.toFixed(2));
      const Y = (y) => base + y;

      // ---- materials (photo colours; the kit stores them for the app's legacy pipeline)
      // after dark the street lamps wash the lower storeys, as the app's lamp map does on its own facades: a stand-in
      // driven by the sky's day factor (api.dayF), since these walls do not read LAMPMAP through api.lampU yet
      const nightU = { value: 0 }, baseU = { value: base };
      const lampWash = (m) => {
        const c = m.clone();
        c.onBeforeCompile = (sh) => {
          sh.uniforms.uNight = nightU; sh.uniforms.uBaseY = baseU;
          sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying float vWY;')
            .replace('#include <project_vertex>', '#include <project_vertex>\nvWY = (modelMatrix * vec4(transformed, 1.0)).y;');
          sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying float vWY; uniform float uNight, uBaseY;')
            .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance += diffuseColor.rgb * vec3(1.0, 0.7, 0.42) * (uNight * 0.45 * (1.0 - smoothstep(3.0, 16.0, vWY - uBaseY)) + uNight * 0.015);');
        };
        c.customProgramCacheKey = () => 'dl-lampwash';
        return c;
      };
      const mBrick = lampWash(K.mat('#a89a7c'));             // buff roman brick, cleaned in 2016
      const mStone = lampWash(K.mat('#d4cab2'));             // stone: the portals, the belt course, the archivolts
      const mBand = lampWash(K.mat('#c4b592'));              // terra cotta string courses, sills and the base's bands
      const mCourt = lampWash(K.mat(K.PALETTE.brickBrown));  // the light court's red-brown common brick
      const mCorn = K.mat('#66705d', { rough: 0.7 });        // painted sheet-metal cornices and the halls' roofs, green-grey
      const mGlass = K.glass('#26303a');
      const mLit = K.glass('#26303a').clone();               // own instance: lit rooms after dark
      mLit.emissive = new THREE.Color('#ffc987').convertSRGBToLinear(); mLit.emissiveIntensity = 0;
      const mIron = K.mat('#2d2f31', { rough: 0.55, metal: 0.4 });     // balconies, the sign's steel and the letters' returns
      const mRoof = K.mat('#8a8782', { rough: 0.95 });                 // the flat roof, a pale membrane
      // the channel letters' red faces: red plexiglass by day, red neon behind it after dark
      const mNeon = new THREE.MeshStandardMaterial({ color: new THREE.Color(K.stored('#b8161c')), roughness: 0.45,
        emissive: new THREE.Color('#ff1414').convertSRGBToLinear(), emissiveIntensity: 0.1 });
      const B = K.builder();

      // ---- helpers
      const V2 = (a, b) => new THREE.Vector2(a, b);
      const P3 = (F, a, b, y) => { const p = F.p(a, b); return [p[0], y, p[1]]; };
      const rectP = (uc, yb, w, h) => [[uc - w / 2, yb], [uc + w / 2, yb], [uc + w / 2, yb + h], [uc - w / 2, yb + h]];
      const archP = (uc, yb, w, hs, n) => {                  // rectangle to the springline, then a half round
        const r = w / 2, out = [[uc - r, yb], [uc + r, yb]]; n = n || 8;
        for (let k = 0; k <= n; k++) { const t = Math.PI * k / n; out.push([uc + r * Math.cos(t), yb + hs + r * Math.sin(t)]); }
        return out;
      };
      const ovalP = (uc, yc, rw, rh, n) => { const out = []; n = n || 10; for (let k = 0; k < n; k++) { const t = 2 * Math.PI * k / n; out.push([uc + rw * Math.cos(t), yc + rh * Math.sin(t)]); } return out; };
      const lift = (pts) => pts.map(([a, b]) => [a, b + base]);
      // a vertical wall in frame F: local u from ua to ub, outer face on v = vf, outward sign s, thickness t, holes in (u, y)
      function shell(F, ua, ub, vf, s, y0, y1, t, holes, outline) {
        const pts = outline || [[ua, y0], [ub, y0], [ub, y1], [ua, y1]];
        const sh = new THREE.Shape(pts.map(([a, b]) => V2(a, b)));
        for (const h of holes || []) sh.holes.push(new THREE.Path(h.map(([a, b]) => V2(a, b))));
        const g = new THREE.ExtrudeGeometry(sh, { depth: t, bevelEnabled: false, steps: 1, curveSegments: 1 });
        g.translate(0, 0, s > 0 ? vf - t : vf);
        return F.place(g, 0);
      }
      // flat polygons (u, y) on the plane v = vp facing s
      function flat(F, polys, vp, s) {
        const g0 = new THREE.ShapeGeometry(polys.map((p) => new THREE.Shape(p.map(([a, b]) => V2(a, b)))), 1);
        const g = g0.index ? g0.toNonIndexed() : g0;
        const a = g.attributes.position.array;
        for (let i = 2; i < a.length; i += 3) a[i] = vp;
        if (s < 0) for (let i = 0; i < a.length; i += 9) for (let k = 0; k < 3; k++) { const tmp = a[i + 3 + k]; a[i + 3 + k] = a[i + 6 + k]; a[i + 6 + k] = tmp; }
        g.deleteAttribute('normal'); g.computeVertexNormals();
        return F.place(g, 0);
      }
      let wn = 0;
      const isLit = () => { wn++; const x = Math.sin(wn * 91.3458 + 17.17) * 43758.5453; return (x - Math.floor(x)) < 0.38; };
      // glass behind holes, split into dark and lit rooms
      function glaze(F, polys, vp, s) {
        const dark = [], on = [];
        for (const p of polys) (isLit() ? on : dark).push(p);
        if (dark.length) B.add(mGlass, flat(F, dark, vp, s));
        if (on.length) B.add(mLit, flat(F, on, vp, s));
      }
      // a wall with window holes (deep reveals) glazed 0.22 m in; opts.outline replaces the rectangle (local u, y)
      function face(F, ua, ub, vf, s, y0, y1, t, wins, opts) {
        opts = opts || {};
        const H = wins.map((w) => lift(w));
        B.add(opts.mat || mBrick, shell(F, ua, ub, vf, s, Y(y0), Y(y1), t, H, opts.outline ? lift(opts.outline) : null));
        const glazed = H.filter((w, i) => !(opts.open && opts.open[i]));
        if (glazed.length) glaze(F, glazed, vf - s * 0.22, s);
      }
      // a terra cotta sill under a window at (uc, yb) on the face v = vf, outward s; a lintel over one
      const sill = (F, uc, yb, w, vf, s) => B.add(mBand, K.boxF(F, uc, vf + s * 0.09, w + 0.3, 0.3, Y(yb - 0.16), 0.16));
      const lintel = (F, uc, yt, w, vf, s) => B.add(mBand, K.boxF(F, uc, vf + s * 0.06, w + 0.35, 0.22, Y(yt), 0.28));
      // a half-annulus archivolt proud of the face
      function archivolt(F, uc, ys, r, band, vf, s, pr, mat) {
        const pts = [], n = r > 1.5 ? 12 : 6;
        for (let k = 0; k <= n; k++) { const t = Math.PI * k / n; pts.push([uc + (r + band) * Math.cos(t), Y(ys) + (r + band) * Math.sin(t)]); }
        for (let k = n; k >= 0; k--) { const t = Math.PI * k / n; pts.push([uc + r * Math.cos(t), Y(ys) + r * Math.sin(t)]); }
        B.add(mat || mStone, shell(F, 0, 0, vf + s * pr, s, 0, 0, pr, [], pts));
      }
      function beam(a, b, t, mat) {
        const dx = b[0] - a[0], dy = b[1] - a[1], dz = b[2] - a[2], L = Math.hypot(dx, dy, dz);
        const g = new THREE.BoxGeometry(t, L, t);
        g.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(dx / L, dy / L, dz / L)));
        g.translate((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2);
        B.add(mat, g);
      }
      // an iron balcony: a solid floor deep enough at its edge to draw the shadow line, a top and a middle rail, end posts
      function balcony(F, uc, vf, s, y, w, d) {
        B.add(mIron, K.boxF(F, uc, vf + s * d / 2, w, d, Y(y - 0.34), 0.34));
        B.add(mIron, K.boxF(F, uc, vf + s * (d - 0.03), w, 0.06, Y(y + 0.9), 0.07));
        B.add(mIron, K.boxF(F, uc, vf + s * (d - 0.03), w, 0.04, Y(y + 0.45), 0.05));
        for (const e of [-1, 1]) B.add(mIron, K.boxF(F, uc + e * (w / 2 - 0.03), vf + s * (d - 0.03), 0.06, 0.06, Y(y), 0.9));
      }
      // a band 0.07 proud of the face v = vf between u0 and u1: front, top and bottom only (the ends are 7 cm)
      function strip(F, u0, u1, vf, s, y0, h) {
        const o = vf + s * 0.07, IN = P3(F, (u0 + u1) / 2, vf - s, y0 + h / 2);
        B.add(mBand, K.quad(P3(F, u0, o, y0), P3(F, u1, o, y0), P3(F, u1, o, y0 + h), P3(F, u0, o, y0 + h), IN));
        B.add(mBand, K.quad(P3(F, u0, vf, y0 + h), P3(F, u1, vf, y0 + h), P3(F, u1, o, y0 + h), P3(F, u0, o, y0 + h), P3(F, (u0 + u1) / 2, vf, y0 - 1)));
        B.add(mBand, K.quad(P3(F, u0, vf, y0), P3(F, u1, vf, y0), P3(F, u1, o, y0), P3(F, u0, o, y0), P3(F, (u0 + u1) / 2, vf, y0 + h + 1)));
      }
      // the banded base: three thin terra cotta bands per storey on floors 1 and 2, broken at every opening
      function rusticate(F, ua, ub, vf, s, holes) {
        const hh = 0.12;
        for (const y of [1.3, 2.6, 3.9, 6.1, 6.85, 7.6]) {
          const cut = [];
          for (const h of holes) {
            let a = 1e9, b = -1e9, lo = 1e9, hi = -1e9;
            for (const [u, yy] of h) { a = Math.min(a, u); b = Math.max(b, u); lo = Math.min(lo, yy); hi = Math.max(hi, yy); }
            if (hi + 0.35 > y && lo - 0.05 < y + hh) cut.push([a - 0.3, b + 0.3]);
          }
          cut.sort((p, q) => p[0] - q[0]);
          let u = ua;
          for (const [a, b] of cut) { if (a > u + 0.2) strip(F, u, a, vf, s, Y(y), hh); u = Math.max(u, b); }
          if (ub > u + 0.2) strip(F, u, ub, vf, s, Y(y), hh);
        }
      }
      const RECT = (d) => [W(U0 - d, V0 - d), W(U1 + d, V0 - d), W(U1 + d, V1 + d), W(U0 - d, V1 + d)];
      const band = (mat, y0, y1, out, inn) => B.add(mat, K.prism(RECT(out), Y(y0), Y(y1), [RECT(-(inn == null ? 0.3 : inn))]));
      // above the court bridge the plan is a U open to Broad Street; c chamfers the four front corners of the two towers
      const UR = (c) => (c ? [[U0 + c, V0], [U1, V0], [U1, V1], [U0 + c, V1], [U0, V1 - c], [U0, CV1 + c], [U0 + c, CV1], [UC, CV1], [UC, CV0], [U0 + c, CV0], [U0, CV0 - c], [U0, V0 + c]]
        : [[U0, V0], [U1, V0], [U1, V1], [U0, V1], [U0, CV1], [UC, CV1], [UC, CV0], [U0, CV0]]).map(([u, v]) => W(u, v));
      const bandU = (mat, y0, y1, out, inn, c) => { const r = UR(c); B.add(mat, K.prism(K.offsetRing(r, out), Y(y0), Y(y1), inn == null ? null : [K.offsetRing(r, -inn)])); };
      // a chamfered rectangle [u0, u1] x [v0, v1] in the building frame, as a world ring
      const chamRect = (u0, u1, v0, v1, c) => [[u0 + c, v0], [u1 - c, v0], [u1, v0 + c], [u1, v1 - c], [u1 - c, v1], [u0 + c, v1], [u0, v1 - c], [u0, v0 + c]].map(([u, v]) => W(u, v));

      // ---- levels (m over the Broad Street sidewalk; HABS photo 1 scaled on a 3.6 m floor, OSM/LiDAR top 44.8 m)
      const FL = (n) => 8.7 + (n - 3) * 3.6;                  // floor n (3..9) bottom; ground 0-5.2, 2nd 5.2-8.7
      const MC0 = 32.85, MCT = 34.1, TOP = 36.9, CH = 1.2;   // the main cornice, the attic top, the towers' chamfer

      // ---- the Broad Street front (fP: v' = 18.2 outward, u' = v): one 1 m thick wall bridging the court to the main
      // cornice; above it the two wings go on alone as the towers' chamfered attic storeys
      {
        const vf = -U0, s = 1, wins = [], open = [];
        const bays = [-13.6, -6.7, 6.2, 13.1], flats = [-10.15, 9.65], top3 = [-13.6, -10.15, -6.7, 6.2, 9.65, 13.1];
        for (const v of bays) wins.push(archP(v, 0.9, 1.9, 2.3));                 // round-headed ground-floor windows
        for (const v of flats) wins.push(rectP(v, 0.6, 1.4, 2.8));                // the two subsidiary portals
        wins.push(archP(-0.2, 0.6, 2.1, 2.7));                                    // the main entrance
        for (const v of flats) { wins.push(rectP(v, 5.9, 1.1, 1.9)); sill(fP, v, 5.9, 1.1, vf, s); }
        for (let n = 3; n <= 8; n++) for (const v of flats) { wins.push(rectP(v, FL(n) + 0.8, 1.2, 2.0)); sill(fP, v, FL(n) + 0.8, 1.2, vf, s); }
        for (const v of top3) { wins.push(archP(v, 30.8, 1.1, 1.3, 6)); wins.push(archP(v, 34.6, 1.0, 1.25, 6)); }
        // the court bridge: two monumental arches, a four-window arcade between them and another at the 9th floor
        const arc4 = [-2.0, -0.8, 0.4, 1.6];
        open[wins.length] = true; wins.push(archP(-0.2, 9.1, 5.0, 4.3, 14));
        for (const v of arc4) wins.push(archP(v, 17.0, 0.72, 1.1, 6));
        open[wins.length] = true; wins.push(archP(-0.2, 19.8, 5.0, 7.5, 14));
        for (const v of arc4) wins.push(archP(v, 31.0, 0.72, 0.8, 6));
        const outline = [[V0, lowR], [V1, lowR], [V1, MCT], [V1 - CH, MCT], [V1 - CH, TOP], [CV1 + CH, TOP], [CV1 + CH, MCT], [CV1, MCT], [CV1, MC0],
          [CV0, MC0], [CV0, MCT], [CV0 - CH, MCT], [CV0 - CH, TOP], [V0 + CH, TOP], [V0 + CH, MCT], [V0, MCT]];
        face(fP, V0, V1, vf, s, lowR, TOP, 1.0, wins, { open, outline });
        rusticate(fP, V0, V1, vf, s, wins);
        // archivolts round the big arches (with keystones), the arcades and the ground-floor arches
        archivolt(fP, -0.2, 13.4, 2.5, 0.55, vf, s, 0.22);
        archivolt(fP, -0.2, 27.3, 2.5, 0.75, vf, s, 0.22);
        B.add(mStone, K.boxF(fP, -0.2, vf + 0.2, 0.7, 0.4, Y(15.75), 0.85));
        B.add(mStone, K.boxF(fP, -0.2, vf + 0.2, 0.8, 0.4, Y(29.65), 1.0));
        for (const v of arc4) { archivolt(fP, v, 18.1, 0.36, 0.12, vf, s, 0.08); archivolt(fP, v, 31.8, 0.36, 0.12, vf, s, 0.08); }
        for (const v of bays) archivolt(fP, v, 3.2, 0.95, 0.32, vf, s, 0.12);
        archivolt(fP, -0.2, 3.3, 1.05, 0.35, vf, s, 0.12);
        B.add(mStone, K.boxF(fP, -0.2, vf + 0.35, 5.6, 0.7, Y(16.5), 0.3));             // the ledge over the lower arch
        B.add(mStone, K.boxF(fP, -0.2, vf + 0.3, 6.0, 0.6, Y(19.5), 0.3));              // the balcony at the upper arch's foot
        B.add(mIron, K.boxF(fP, -0.2, vf + 0.55, 5.4, 0.05, Y(20.4), 0.07));
        B.add(mStone, K.boxF(fP, -0.2, vf + 0.15, 5.4, 0.3, Y(30.7), 0.18));            // the 9th-floor arcade's sill
        // the bridge's own cap: the court's front wall ends at the main cornice's foot, nothing above it
        B.add(mCorn, K.slabF(fP, CV0, CV1, vf - 1.25, vf + 0.3, Y(32.8), Y(33.3)));
        // terra cotta string courses at every floor across the two wings (hidden inside the bays)
        for (let n = 3; n <= 9; n++) for (const [a, b] of [[V0 - 0.02, CV0], [CV1, V1 + 0.02]]) B.add(mBand, K.slabF(fP, a, b, vf - 0.1, vf + 0.07, Y(FL(n) - 0.09), Y(FL(n) + 0.09)));
        // oriel bays, 2nd to 8th floor
        for (const vc of bays) {
          const ring = (sc, pr) => [[vc - 1.8 * sc, vf - 0.05], [vc - 1.1 * sc, vf + pr], [vc + 1.1 * sc, vf + pr], [vc + 1.8 * sc, vf - 0.05]].map(([a, b]) => fP.p(a, b));
          const main = ring(1, 0.85);
          B.add(mBrick, K.prism(main, Y(5.2), Y(30.3)));
          B.add(mStone, K.prism(ring(0.55, 0.4), Y(4.3), Y(4.75)));
          B.add(mStone, K.prism(ring(0.8, 0.65), Y(4.75), Y(5.2)));
          for (let n = 3; n <= 8; n++) B.add(mBand, K.prism(K.offsetRing(main, 0.06), Y(FL(n) - 0.12), Y(FL(n) + 0.1)));
          B.add(mStone, K.prism(K.offsetRing(main, 0.12), Y(30.15), Y(30.45)));      // the cap, a balcony for the 9th
          const inside = P3(fP, vc, vf - 0.5, Y(15));
          B.add(mIron, K.boxF(fP, vc, vf + 0.9, 2.3, 0.05, Y(31.3), 0.07));
          for (const e of [-1, 1]) beam(P3(fP, vc + e * 1.1, vf + 0.9, Y(31.37)), P3(fP, vc + e * 1.8, vf + 0.05, Y(31.37)), 0.06, mIron);
          const pd = [], pl = [];
          for (let n = 2; n <= 8; n++) {
            const yb = Y(n === 2 ? 5.75 : FL(n) + 0.75), h = 1.95;
            (isLit() ? pl : pd).push(rectP(vc - 0.5, yb, 0.82, h), rectP(vc + 0.5, yb, 0.82, h));
            for (const e of [-1, 1]) {                            // the canted sides
              const a = [vc + e * 1.8, vf], b = [vc + e * 1.1, vf + 0.85];
              const L = Math.hypot(b[0] - a[0], b[1] - a[1]), nx = e * (b[1] - a[1]) / L, ny = -e * (b[0] - a[0]) / L;
              const q = (t, o) => [a[0] + (b[0] - a[0]) * t + nx * o, a[1] + (b[1] - a[1]) * t + ny * o];
              const t0 = 0.5 - 0.24 / L, t1 = 0.5 + 0.24 / L, o = 0.02;
              const p0 = q(t0, o), p1 = q(t1, o);
              B.add(isLit() ? mLit : mGlass, K.quad(P3(fP, p0[0], p0[1], yb), P3(fP, p1[0], p1[1], yb), P3(fP, p1[0], p1[1], yb + h), P3(fP, p0[0], p0[1], yb + h), inside));
            }
          }
          if (pd.length) B.add(mGlass, flat(fP, pd, vf + 0.87, 1));
          if (pl.length) B.add(mLit, flat(fP, pl, vf + 0.87, 1));
        }
        // the main portal: a temple front of paired composite columns, entablature, pediment with the coat of arms, statue
        // (kept to 2 m deep: the app's PHMC 'Father Divine' marker post stands 2.2 m out from the facade line)
        B.add(mStone, K.slabF(fP, -3.3, 2.9, vf, vf + 2.0, Y(lowR), Y(0.3)));
        B.add(mStone, K.slabF(fP, -3.0, 2.6, vf, vf + 1.75, Y(0.3), Y(0.6)));
        for (const v of [-2.45, -1.8, 1.4, 2.05]) {
          const p = fP.p(v, vf + 1.4);
          B.add(mStone, K.column(p[0], Y(0.6), p[1], 4.1, 0.25, 'corinthian', 12));
          B.add(mStone, K.boxF(fP, v, vf + 0.1, 0.5, 0.22, Y(0.6), 4.1));
        }
        B.add(mStone, K.boxF(fP, -0.2, vf + 0.9, 5.6, 1.8, Y(4.7), 0.65));
        B.add(mStone, K.pedimentF(fP, -3.0, 2.6, vf + 1.8, 1, Y(5.35), 1.45, 1.8));
        B.add(mStone, K.boxF(fP, -0.2, vf + 1.5, 0.8, 0.6, Y(6.75), 0.35));
        { const p = fP.p(-0.2, vf + 1.5); B.add(mStone, K.cyl(0.17, 0.24, 1.35, 8, p[0], Y(7.1), p[1])); B.add(mStone, K.dome(0.16, p[0], Y(8.45), p[1], 8, 1.3, Math.PI)); }
        // the balustrade across the court's foot
        B.add(mStone, K.slabF(fP, -3.5, 3.1, vf, vf + 0.9, Y(7.45), Y(7.65)));
        B.add(mStone, K.slabF(fP, -3.5, 3.1, vf + 0.72, vf + 0.9, Y(7.65), Y(8.3)));
        // the two subsidiary portals: pilastered doors under pediments
        for (const v of flats) {
          B.add(mStone, K.slabF(fP, v - 1.4, v + 1.4, vf, vf + 1.3, Y(lowR), Y(0.55)));
          for (const e of [-1, 1]) { const p = fP.p(v + e * 0.98, vf + 0.7); B.add(mStone, K.column(p[0], Y(0.55), p[1], 3.0, 0.17, 'ionic', 10)); }
          B.add(mStone, K.boxF(fP, v, vf + 0.55, 2.7, 1.1, Y(3.55), 0.35));
          B.add(mStone, K.pedimentF(fP, v - 1.35, v + 1.35, vf + 1.1, 1, Y(3.9), 0.85, 1.1));
        }
      }

      // ---- the sides (f: along u) and the rear (fP: along v): narrow bay strips with oval windows between wide iron
      // balconies at every floor from the 2nd, over a banded base
      const colsSide = [
        { u: -15.6, k: 'p' }, { u: -11.6, k: 'b' }, { u: -7.1, k: 's', w: 2.0 }, { u: -3.1, k: 'b' }, { u: -0.1, k: 'p' },
        { u: 2.9, k: 'b' }, { u: 6.85, k: 's', w: 2.0 }, { u: 11.0, k: 'b' }, { u: 14.8, k: 'p' }];
      const colsRear = [
        { u: -14.3, k: 'p' }, { u: -10.4, k: 'b' }, { u: -5.25, k: 's', w: 2.0 }, { u: -0.1, k: 'b' }, { u: 5.0, k: 's', w: 2.0 },
        { u: 10.0, k: 'b' }, { u: 14.0, k: 'p' }];
      function sideFace(F, ua, ub, vf, s, cols, pr, annex, tower) {
        const wins = [];
        for (const c of cols) {
          if (c.k === 'b') { wins.push(archP(c.u, 0.9, 1.8, 2.3)); wins.push(archP(c.u, 5.7, 1.2, 1.5, 6)); }
          else { wins.push(rectP(c.u, 1.3, 1.2, 2.3)); lintel(F, c.u, 3.6, 1.2, vf, s); sill(F, c.u, 1.3, 1.2, vf, s); wins.push(rectP(c.u, 5.9, 1.1, 1.9)); sill(F, c.u, 5.9, 1.1, vf, s); }
        }
        const base2 = wins.slice();
        for (const c of cols) {
          if (c.k === 'p') for (let n = 3; n <= 9; n++) { const h = n === 9 ? 1.5 : 2.0; wins.push(rectP(c.u, FL(n) + 0.8, 1.15, h)); sill(F, c.u, FL(n) + 0.8, 1.15, vf, s); }
          if (c.k === 'b') for (let n = 3; n <= 9; n++) wins.push(archP(c.u, FL(n) + 0.3, 1.2, n === 9 ? 1.25 : 1.85, 6));
          wins.push(archP(c.u, 34.6, 0.95, 1.25, 6));
        }
        // the side walls' attic starts behind the tower's chamfer
        const outline = tower ? [[ua, lowR], [ub, lowR], [ub, TOP], [U0 + CH, TOP], [U0 + CH, MCT], [ua, MCT]] : null;
        face(F, ua, ub, vf, s, lowR, TOP, 0.35, wins, { outline });
        rusticate(F, ua, ub, vf, s, base2);
        for (const c of cols) {
          if (c.k === 'b') {
            archivolt(F, c.u, 3.2, 0.9, 0.3, vf, s, 0.1);
            archivolt(F, c.u, 7.2, 0.6, 0.18, vf, s, 0.1);
            for (let n = 2; n <= 9; n++) { const y = n === 2 ? 5.45 : FL(n); if (!(annex && annex(c.u, y))) balcony(F, c.u, vf, s, y, 3.9, 1.0); }
          }
          if (c.k === 's') {
            B.add(mBrick, K.boxF(F, c.u, vf + s * (pr / 2 - 0.05), c.w, pr + 0.1, Y(8.75), 32.85 - 8.75));
            B.add(mStone, K.boxF(F, c.u, vf + s * (pr / 2), c.w + 0.25, pr + 0.25, Y(32.7), 0.35));
            for (let n = 3; n <= 9; n++) B.add(mBand, K.boxF(F, c.u, vf + s * (pr / 2), c.w + 0.1, pr + 0.1, Y(FL(n) - 0.07), 0.14));
            const ov = [];
            for (let n = 3; n <= 9; n++) ov.push(lift(ovalP(c.u, FL(n) + 1.75, 0.42, 0.62, 12)));
            glaze(F, ov, vf + s * (pr + 0.02), s);
          }
        }
      }
      sideFace(f, U0 + 1.0, U1 - 0.35, V0, -1, colsSide, 0.6, null, true);
      sideFace(f, U0 + 1.0, U1 - 0.35, V1, 1, colsSide, 0.6, null, true);
      // the rear: the 1893 service wing (the app's own Annex record) covers its south half to about 22 m
      sideFace(fP, V0, V1, -U1, -1, colsRear, 0.6, (u, y) => u > 6.5 && y < 22, false);

      // ---- the towers' chamfered corners at the attic storey, each with an arched window
      for (const [a, b, ins] of [[[U0, V0 + CH], [U0 + CH, V0], [U0 + 3, V0 + 3]], [[U0 + CH, V1], [U0, V1 - CH], [U0 + 3, V1 - 3]],
        [[U0, CV0 - CH], [U0 + CH, CV0], [U0 + 3, CV0 - 3]], [[U0 + CH, CV1], [U0, CV1 + CH], [U0 + 3, CV1 + 3]]]) {
        const pa = W(a[0], a[1]), pb = W(b[0], b[1]), pi = W(ins[0], ins[1]);
        const Fc = K.frameFromEdge(pa, pb), L = Math.hypot(pb[0] - pa[0], pb[1] - pa[1]);
        const sc = Fc.local(pi[0], pi[1])[1] > 0 ? -1 : 1;
        face(Fc, 0, L, 0, sc, MCT, TOP, 0.35, [archP(L / 2, 34.6, 0.8, 1.15, 6)]);
      }

      // ---- the light court's walls: red common brick up to the bridge, buff face brick on the towers' inner faces above
      {
        const wl = [], wa = [];
        for (let n = 3; n <= 9; n++) for (const u of [-14.2, -10.4, -6.6, -2.9]) wl.push(rectP(u, FL(n) + 0.8, 1.0, 1.9));
        for (const u of [-14.2, -10.4, -6.6, -2.9]) wa.push(archP(u, 34.6, 1.0, 1.25, 6));
        const upper = [[U0 + 1.0, 33.3], [UC, 33.3], [UC, TOP], [U0 + CH, TOP], [U0 + CH, MCT], [U0 + 1.0, MCT]];
        for (const [vv, s] of [[CV0, 1], [CV1, -1]]) {
          face(f, U0 + 1.0, UC, vv, s, 8.7, 33.3, 0.35, wl, { mat: mCourt });
          face(f, U0 + 1.0, UC, vv, s, 33.3, TOP, 0.35, wa, { outline: upper });
        }
        const wb = [];
        for (let n = 3; n <= 9; n++) for (const v of [-1.7, 1.3]) wb.push(rectP(v, FL(n) + 0.8, 1.0, 1.9));
        face(fP, CV0 - 0.35, CV1 + 0.35, -UC, 1, 8.7, 33.3, 0.35, wb, { mat: mCourt });
        face(fP, CV0 - 0.35, CV1 + 0.35, -UC, 1, 33.3, TOP, 0.35, [-1.7, 1.3].map((v) => archP(v, 34.6, 1.0, 1.25, 6)));
        B.add(mRoof, K.prism([W(U0 + 1.0, CV0), W(UC, CV0), W(UC, CV1), W(U0 + 1.0, CV1)], Y(8.55), Y(8.75)));    // the court's floor over the lobby,
        B.add(mGlass, K.slabF(f, -12.5, -5.5, -1.8, 1.4, Y(8.75), Y(8.95)));                                    // and its skylight
        for (let n = 4; n <= 9; n += 1) for (const [vv, s] of [[CV0, 1], [CV1, -1]]) balcony(f, -8.5, vv, s, FL(n), 3.0, 0.8);
      }

      // ---- string courses and cornices: round the full block below the main cornice, round the U above it
      band(mStone, lowR, 0.75, 0.14);                  // the plinth
      band(mStone, 5.0, 5.35, 0.22);                   // over the ground floor
      band(mStone, 8.35, 8.75, 0.32);                  // the belt course over the 2nd floor
      band(mBand, 30.15, 30.35, 0.1);                  // the 9th floor sill course
      bandU(mCorn, 32.85, 33.15, 0.28, 0.3, 0);        // the main cornice: bed moulding,
      {                                                // brackets (none across the court's open front),
        const pitch = 0.95, dep = 0.72, y0 = 33.15, h = 0.5;
        const runs = [['u', V0, U0, U1, -1, 0], ['u', V1, U0, U1, 1, 0], ['v', U1, V0, V1, 1, 0], ['v', U0, V0, CV0, -1, 0], ['v', U0, CV1, V1, -1, 0],
          ['u', CV0, U0, UC, 1, 1], ['u', CV1, U0, UC, -1, 1], ['v', UC, CV0, CV1, -1, 1]];
        for (const [ax, fx, a, b, s, skip] of runs) {
          const n = Math.max(1, Math.round((b - a) / pitch));
          for (let i = skip; i <= n - skip; i++) {
            const t = a + (b - a) * i / n;
            B.add(mCorn, ax === 'u' ? K.boxF(f, t, fx + s * dep / 2, 0.22, dep, Y(y0), h) : K.boxF(f, fx + s * dep / 2, t, dep, 0.22, Y(y0), h));
          }
        }
      }
      bandU(mCorn, 33.65, 34.1, 0.88, 0.3, 0);         // and the corona,
      B.add(mStone, K.prism(K.offsetRing(UR(0), 0.08), Y(34.1), Y(34.25)));   // its stone top, floored under the chamfers
      bandU(mCorn, 36.65, 36.9, 0.22, 0.3, CH);        // the attic cornice and parapet, following the chamfers
      bandU(mCorn, 36.9, 37.45, 0.5, 0.3, CH);
      B.add(mRoof, K.prism(K.offsetRing(UR(CH), -0.3), Y(36.75), Y(37.0)));   // the roof, open over the court

      // ---- over each front wing: a set-back tier with a lunette (the west end of the barrel-vaulted hall behind it) and a
      // narrow pediment block, both on the Broad Street line; the hall's low barrel roof runs back behind them
      for (const [vA, vB] of [[V0, CV0], [CV1, V1]]) {
        const vc = (vA + vB) / 2;
        const tb0 = -17.2, tb1 = -12.5, hwB = 5.0, yB0 = 36.95, yB1 = 39.9;
        const rB = chamRect(tb0, tb1, vc - hwB, vc + hwB, 0.8);
        B.add(mBrick, K.prism(rB, Y(yB0), Y(yB1)));
        B.add(mBand, K.prism(K.offsetRing(rB, 0.08), Y(37.45), Y(37.65)));
        B.add(mCorn, K.prism(K.offsetRing(rB, 0.35), Y(yB1), Y(yB1 + 0.45)));
        for (const e of [-1, 1]) B.add(mStone, K.slabF(f, tb0 - 0.08, tb0 + 0.5, vc + e * 2.9 - 0.3, vc + e * 2.9 + 0.3, Y(37.65), Y(yB1)));   // pilasters
        glaze(fP, [lift(archP(vc, 37.75, 1.8, 0.02, 8))], -tb0 + 0.02, 1);                                   // the lunette
        archivolt(fP, vc, 37.77, 0.9, 0.22, -tb0, 1, 0.1);
        for (const e of [-1, 1]) glaze(fP, [lift(rectP(vc + e * 3.75, 38.1, 0.6, 1.1))], -tb0 + 0.02, 1);
        for (const [vv, s] of [[vc - hwB, -1], [vc + hwB, 1]]) glaze(f, [lift(archP(-14.85, 37.9, 0.9, 0.9, 6))], vv + s * 0.02, s);
        // the pediment block: pilastered corners, cornice, a low pediment (about 25 degrees) with raking cornices, apex at the
        // OSM height of 44.8 m less the sidewalk's rise
        const tc0 = -16.9, tc1 = -13.9, hwC = 2.4, yC0 = yB1 + 0.45, yC1 = 43.0, pH = 1.2;
        B.add(mBrick, K.slabF(f, tc0, tc1, vc - hwC, vc + hwC, Y(yC0 - 0.05), Y(yC1)));
        for (const e of [-1, 1]) B.add(mStone, K.slabF(f, tc0 - 0.12, tc0 + 0.45, vc + e * hwC - 0.3, vc + e * hwC + 0.3, Y(yC0), Y(yC1)));
        B.add(mCorn, K.slabF(f, tc0 - 0.3, tc1 + 0.15, vc - hwC - 0.3, vc + hwC + 0.3, Y(yC1), Y(yC1 + 0.35)));
        B.add(mBrick, K.pedimentF(fP, vc - hwC - 0.2, vc + hwC + 0.2, -tc0 + 0.2, 1, Y(yC1 + 0.35), pH, tc1 - tc0 + 0.35));
        const apex = P3(fP, vc, -tc0 + 0.32, Y(yC1 + 0.35 + pH)), l = P3(fP, vc - hwC - 0.35, -tc0 + 0.32, Y(yC1 + 0.35)), r = P3(fP, vc + hwC + 0.35, -tc0 + 0.32, Y(yC1 + 0.35));
        beam(l, apex, 0.26, mCorn); beam(r, apex, 0.26, mCorn);
        glaze(fP, [lift(rectP(vc, 41.0, 1.5, 1.2))], -tc0 + 0.02, 1);
        // the hall: a curb at the parapet's height and a low barrel roof to the LiDAR ridge, a skylight along its crown
        const hv0 = vA === V0 ? -13.4 : 5.0, hv1 = vA === V0 ? -5.3 : 12.9, ha = tb1, hb = -2.2, hy0 = 37.45, hy1 = 39.8;
        const hm = (hv0 + hv1) / 2, hw = (hv1 - hv0) / 2;
        B.add(mBrick, K.slabF(f, ha, hb, hv0, hv1, Y(36.75), Y(hy0)));
        const prof = []; for (let k = 0; k <= 8; k++) { const t = Math.PI * k / 8; prof.push([hm - hw * Math.cos(t), hy0 + (hy1 - hy0) * Math.sin(t)]); }
        const IN = P3(f, (ha + hb) / 2, hm, Y(hy0 - 2));
        for (let k = 0; k < 8; k++) { const [va, ya] = prof[k], [vb, yb] = prof[k + 1]; B.add(mCorn, K.quad(P3(f, ha, va, Y(ya)), P3(f, hb, va, Y(ya)), P3(f, hb, vb, Y(yb)), P3(f, ha, vb, Y(yb)), IN)); }
        B.add(mBrick, flat(fP, [lift(prof)], -hb, -1));
        B.add(mBrick, flat(fP, [lift(prof)], -ha, 1));
        B.add(mGlass, K.slabF(f, ha + 1.0, hb - 1.0, hm - 0.5, hm + 0.5, Y(hy1 - 0.12), Y(hy1 + 0.2)));
      }
      // the rear chimney stack and the stair bulkhead
      B.add(mBrick, K.slabF(f, 15.0, 17.0, -9.4, -7.4, Y(35.7), Y(42.5)));
      B.add(mStone, K.slabF(f, 14.85, 17.15, -9.55, -7.25, Y(42.5), Y(42.85)));
      B.add(mBrick, K.slabF(f, 8.0, 11.5, -1.5, 1.8, Y(36.9), Y(39.4)));
      B.add(mCorn, K.slabF(f, 7.85, 11.65, -1.65, 1.95, Y(39.4), Y(39.65)));

      // ---- the signs: DIVINE / LORRAINE / HOTEL in 4 ft red channel letters on steel lattices, right behind the towers over
      // the north and south walls. The letters are geometry (no texture): dark returns and backs, a red face that glows
      const SU0 = -12.3, SU1 = -2.3, SUC = (SU0 + SU1) / 2, SW = SU1 - SU0;
      const rails = [40.6, 42.8, 45.0, 46.9], RT = 46.95;
      const lines = [['DIVINE', 45.15], ['LORRAINE', 42.95], ['HOTEL', 40.75]];
      const LH = 1.22, SWK = 0.17, LD = 0.2, GAP = 0.44;
      const LW = { D: 0.84, I: 0.17, V: 0.9, N: 0.86, E: 0.7, L: 0.68, O: 0.96, R: 0.82, A: 0.96, H: 0.86, T: 0.84 };
      const uh = new THREE.Vector3(ca, 0, sa), vh = new THREE.Vector3(-sa, 0, ca), up = new THREE.Vector3(0, 1, 0);
      function glyph(ch, w) {
        const x0 = SWK / 2, x1 = w - SWK / 2, y0 = SWK / 2, y1 = LH - SWK / 2, ym = LH / 2, xm = (x0 + x1) / 2, S = [];
        const arc = (cx, cy, rx, ry, a0, a1, n) => { for (let k = 0; k < n; k++) { const t0 = a0 + (a1 - a0) * k / n, t1 = a0 + (a1 - a0) * (k + 1) / n; S.push([[cx + rx * Math.cos(t0), cy + ry * Math.sin(t0)], [cx + rx * Math.cos(t1), cy + ry * Math.sin(t1)]]); } };
        if (ch === 'D') { const xa = x0 + (x1 - x0) * 0.3; S.push([[x0, y0], [x0, y1]], [[x0, y1], [xa, y1]], [[x0, y0], [xa, y0]]); arc(xa, ym, x1 - xa, (y1 - y0) / 2, Math.PI / 2, -Math.PI / 2, 6); }
        else if (ch === 'I') S.push([[x0, y0], [x0, y1]]);
        else if (ch === 'V') S.push([[x0, y1], [xm, y0]], [[xm, y0], [x1, y1]]);
        else if (ch === 'N') S.push([[x0, y0], [x0, y1]], [[x0, y1], [x1, y0]], [[x1, y0], [x1, y1]]);
        else if (ch === 'E') S.push([[x0, y0], [x0, y1]], [[x0, y1], [x1, y1]], [[x0, ym], [x1 - 0.08, ym]], [[x0, y0], [x1, y0]]);
        else if (ch === 'L') S.push([[x0, y1], [x0, y0]], [[x0, y0], [x1, y0]]);
        else if (ch === 'O') arc(xm, ym, (x1 - x0) / 2, (y1 - y0) / 2, 0, 2 * Math.PI, 14);
        else if (ch === 'R') { const xb = x0 + (x1 - x0) * 0.42, yr = ym - 0.03; S.push([[x0, y0], [x0, y1]], [[x0, y1], [xb, y1]], [[x0, yr], [xb, yr]]); arc(xb, (y1 + yr) / 2, x1 - xb, (y1 - yr) / 2, Math.PI / 2, -Math.PI / 2, 5); S.push([[xb, yr], [x1, y0]]); }
        else if (ch === 'A') { const t = 0.34; S.push([[x0, y0], [xm, y1]], [[xm, y1], [x1, y0]], [[x0 + (xm - x0) * t, y0 + (y1 - y0) * t], [x1 - (x1 - xm) * t, y0 + (y1 - y0) * t]]); }
        else if (ch === 'H') S.push([[x0, y0], [x0, y1]], [[x1, y0], [x1, y1]], [[x0, ym], [x1, ym]]);
        else if (ch === 'T') S.push([[x0, y1], [x1, y1]], [[xm, y1], [xm, y0]]);
        return S;
      }
      const M4 = new THREE.Matrix4();
      function channel(txt, vPlane, s, yb) {
        const ws = [...txt].map((ch) => LW[ch]);
        const lineW = ws.reduce((a, b) => a + b, 0) + GAP * (txt.length - 1);
        const o = f.p(SUC - s * lineW / 2, vPlane);
        M4.makeBasis(uh.clone().multiplyScalar(s), up, vh.clone().multiplyScalar(s)).setPosition(o[0], Y(yb), o[1]);
        let x = 0;
        for (let i = 0; i < txt.length; i++) {
          for (const [p, q] of glyph(txt[i], ws[i])) {
            const dx = q[0] - p[0], dy = q[1] - p[1], L = Math.hypot(dx, dy), ang = Math.atan2(dy, dx);
            const ext = (Math.abs(dx) < 1e-6 || Math.abs(dy) < 1e-6) ? SWK / 2 : 0.035;
            const mx = x + (p[0] + q[0]) / 2, my = (p[1] + q[1]) / 2;
            const g = new THREE.BoxGeometry(L + 2 * ext, SWK, LD); g.rotateZ(ang); g.translate(mx, my, LD / 2); g.applyMatrix4(M4); B.add(mIron, g);
            const fc = new THREE.PlaneGeometry(L + 2 * ext, SWK * 0.86); fc.rotateZ(ang); fc.translate(mx, my, LD + 0.006); fc.applyMatrix4(M4); B.add(mNeon, fc);
          }
          x += ws[i] + GAP;
        }
      }
      for (const [vs, s] of [[V0 + 1.3, -1], [V1 - 1.3, 1]]) {
        // the lattice: five posts from the roof, four rails, X-bracing under the letters and diagonals between the rails
        for (let i = 0; i <= 4; i++) { const u = SU0 + SW * i / 4; B.add(mIron, K.boxF(f, u, vs, 0.16, 0.16, Y(36.95), RT - 36.95)); }
        for (const y of rails) B.add(mIron, K.boxF(f, SUC, vs, SW + 0.3, 0.12, Y(y - 0.06), 0.13));
        for (let i = 0; i < 4; i++) {
          const ua = SU0 + SW * i / 4, ub = SU0 + SW * (i + 1) / 4;
          beam(P3(f, ua, vs, Y(37.0)), P3(f, ub, vs, Y(rails[0])), 0.09, mIron);
          beam(P3(f, ub, vs, Y(37.0)), P3(f, ua, vs, Y(rails[0])), 0.09, mIron);
          for (let j = 0; j < 3; j++) beam(P3(f, (i + j) % 2 ? ua : ub, vs, Y(rails[j])), P3(f, (i + j) % 2 ? ub : ua, vs, Y(rails[j + 1])), 0.08, mIron);
        }
        for (let i = 0; i <= 4; i += 2) { const u = SU0 + SW * i / 4; beam(P3(f, u, vs, Y(rails[2])), P3(f, u, vs - s * 1.5, Y(37.0)), 0.12, mIron); }
        for (const [txt, yb] of lines) channel(txt, vs + s * 0.08, s, yb);
      }

      const grp = B.done();
      // photocell: the sign glows red and a share of the rooms light up after dark (the app's own day factor)
      const nightK = () => (api.dayF ? 1 - api.dayF() : 0);
      for (const m of grp.children) {
        if (m.material === mNeon) { m.userData.noShadow = true; m.onBeforeRender = () => { const n = nightK(); mNeon.emissiveIntensity = 0.1 + 1.4 * n; nightU.value = n; }; }
        if (m.material === mLit) m.onBeforeRender = () => { mLit.emissiveIntensity = 1.1 * nightK(); nightU.value = nightK(); };
      }
      return grp;
    }
  });
})();
