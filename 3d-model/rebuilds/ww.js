// Fairmount Water Works (Frederick Graff and Frederick Graff Jr., 1812 to 1872): a PROPOSED model for Philly3D. Revision 2.
// Sources: HAER PA-51 sheet 4 "Site Development 1812-1978" (the 1978 river elevation and plan), HAER sheet 3 (site plan, the
// dam 1,025 ft at bearing ~287), the HAER PA-51 data pages (p.124: the Engine House main block "three bays, three stories
// with another story below grade", flanked by one-storey boiler sheds north and south with balustraded roofs and four
// chimneys; p.155: "the ten-column Doric portico" of 1835 and "the twelve-column Doric gazebo ... octagonal plan with
// bell-shaped roof", capped by an eagle; p.158: the New Mill House "with large quoins" in the same finished Leiperville
// stone), the NHL nomination (NRHP 76001662: mill house 238 x 56 ft, terrace 253 x 26 ft), Wikimedia Commons photos, and the
// OSM footprints the app draws (scene_wide.json), whose local frame everything is laid out in.
//
// Layout (mill frame fm: u runs north along the river front, v runs east; the river face is v = -16.5 .. -20.4):
//   Engine House (1812-15, 1835 porch)   u' 0..24.7 in its own frame ef, turned 22 degrees to the mill house:
//                                        a three-bay main block (u' 6.1..18.6) of three storeys between one-storey boiler
//                                        sheds, the ten-column porch along the river
//   South Wing / Caretaker's House       u 10.1..17.4        Doric tetrastyle temple, pediment to the river
//   South Entrance House (1871)          u 21.8..35.0        "Schuylkill Freed" on its attic
//   Pavilion (1872)                      u 39.7..52.8        open hexastyle temple, 6 x 9 columns, pediments both ends
//   North Entrance House (1871)          u 57.6..70.8        "Schuylkill Chained"
//   North Wing / Watering Committee      u 74.9..82.5
//   New Mill House (1859-62)             angled into the mound dam, quoined piers, roof plaza with lamp standards
//   Mound dam and the 1835 gazebo        octagonal pier, twelve columns and a bell roof with the eagle
//   Mercury Pavilion (restored 2008)     the octagonal summer house on the hill with Rush's Mercury on its roof
//   Fairmount Dam crest                  327 m at bearing 282 to the drawn west bank, a white spillway apron
//
// Night: every stone, stucco and brick surface takes a floodlight wash (strongest at the foot of each wall, the uplight
// falloff) plus the pools of the terrace's own lamp standards, all scaled by ONE uniform object, LAMP. In the app LAMP is
// lampUniform itself (the app passes it as api.lamp). The glass
// mesh carries a flag in its uv: uv.x is the window's night glow (the Engine House restaurant 0.5, the mill lunettes 0.25,
// the lanterns 1.6), uv.y = 1 turns it into matte dark timber / cast iron (the tailrace gates, the lamp standards, the eagle).
RB.add({
  id: 'ww',
  name: 'Fairmount Water Works',
  center: [-3318, -2305],
  skip: [
    [[-3285, -2235], [-3325, -2235], [-3338, -2328], [-3372, -2338], [-3372, -2378], [-3312, -2372], [-3297, -2300], [-3285, -2270]],
    [[-3405, -2385], [-3389, -2385], [-3389, -2368], [-3405, -2368]],
    [[-3262, -2285], [-3250, -2285], [-3250, -2273], [-3262, -2273]]      // the Mercury Pavilion on the hill
  ],
  // 1 hero from the south-west, 2 the river front, 3 from the north over the mound dam, 4 the land side from the museum's
  // hill (the promenade, the Engine House's exposed basement, Aquarium Drive), 5 from beyond the dam's west landing
  views: [[232, 255, 90, 10], [250, 105, 20, 14], [325, 260, 75, 6], [70, 150, 60, 0], [290, 540, 55, 0]],
  build(api) {
    const { THREE, K } = api;
    const B = K.builder();
    const app = api.where === 'app';

    // ---- the night switch: ONE uniform object. In the app this is lampUniform (0 by day, 1 by night)
    const LAMP = api.lamp || api.lampUniform || { value: 0 };

    // ---- materials (photo colours; K.mat converts to the app's stored-dark pipeline). Every patched material is cloned out
    // of the kit's shared cache so the patches touch only this model
    const mStucco = K.mat('#e0cc9e').clone();              // butter-cream stucco of the temples and the Engine House
    const mTrim = K.mat('#e9dfc4').clone();                // columns, cornices, balustrades, the Rush figures
    const mStone = K.mat('#85847e').clone();               // grey Leiperville ashlar of the mill house river front, the flags
    const mStoneDk = K.mat('#7b7a73').clone();             // the New Mill House, the mound dam, the tide band, the dam crest
    const mRoof = K.mat('#6c7073', { rough: 0.55, metal: 0.2 });   // grey standing-seam metal
    const mBrick = K.mat('#7a5044').clone();               // the brick-paved terrace along the eastern front
    const mGlass = K.glass().clone();                      // dark glazing; uv-flagged glow, or matte iron / timber
    const mFoam = K.mat('#dde7e5', { rough: 0.9 }).clone();   // white water over the dam

    // ---- levels
    const W = app ? -7.34 : 0;                             // the drawn Schuylkill sheet (the viewer's plane is the waterline)
    const T = W + 7.34;                                    // the terrace: top of the mill house, 24 ft over the tailwater

    // ---- frames
    const fm = K.frame(-3293.4, -2265.4, -1.7834);         // along the mill house's landward face (OSM)
    const fmR = K.frame(fm.cx, fm.cz, fm.a + Math.PI / 2); // fm.p(u, v) === fmR.p(v, -u): for faces of constant u
    const ef = K.frameFromEdge([-3295.8, -2240.7], [-3291.4, -2265.0]);   // Engine House east face, SE to NE corner
    const efR = K.frame(ef.cx, ef.cz, ef.a + Math.PI / 2);
    const G = [-3397.2, -2376.5];                          // the gazebo (OSM Eagle Pavilion centroid)
    const MP = [-3256.0, -2279.1];                         // the Mercury Pavilion (OSM centroid)

    // ---- ground check: the plinths run below the lowest drawn ground anywhere under the footprint
    let gMin = W - 3.5, gHi = -Infinity;
    const probe = (x, z) => { const g = api.ground(x, z); if (isFinite(g)) gMin = Math.min(gMin, g); return g; };
    for (let u = 0; u <= 118; u += 6) for (let v = -54; v <= 11; v += 5) probe(...fm.p(u, v));
    for (let u = 0; u <= 25; u += 5) for (let v = -24; v <= 0; v += 4) probe(...ef.p(u, v));
    for (let a = 0; a < 8; a++) probe(G[0] + 6 * Math.cos(a), G[1] + 6 * Math.sin(a));
    for (let u = 23; u <= 90; u += 4) for (const v of [2, 6, 10.5]) gHi = Math.max(gHi, api.ground(...fm.p(u, v)));
    const F = Math.min(gMin, W - 3.5) - 0.8;               // foundation bottom
    if (app && gHi > T - 0.1) api.log('ww: ground under the promenade reaches ' + gHi.toFixed(2) + ' over T ' + T);

    // ---- helpers
    const P3 = (f, u, v, y) => { const p = f.p(u, v); return [p[0], y, p[1]]; };
    const R = (f, pts) => pts.map((q) => f.p(q[0], q[1]));
    const inPoly = (x, z, r) => { let c = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const xi = r[i][0], zi = r[i][1], xj = r[j][0], zj = r[j][1]; if (((zi > z) !== (zj > z)) && (x < (xj - xi) * (z - zi) / (zj - zi) + xi)) c = !c; } return c; };
    const distRing = (x, z, r) => {   // 0 inside, else the distance to the nearest edge
      if (inPoly(x, z, r)) return 0;
      let d = Infinity;
      for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
        const ax = r[j][0], az = r[j][1], dx = r[i][0] - ax, dz = r[i][1] - az, L2 = dx * dx + dz * dz || 1e-9;
        const t = Math.max(0, Math.min(1, ((x - ax) * dx + (z - az) * dz) / L2));
        d = Math.min(d, Math.hypot(ax + dx * t - x, az + dz * t - z));
      }
      return d;
    };
    // the glass flag lives in the uv channel (the builder keeps position, normal and uv): x = night glow, y = 1 for iron
    const flag = (g, gx, gy) => {
      if (Array.isArray(g)) { for (const q of g) flag(q, gx, gy); return g; }
      if (!g) return g;
      if (!g.attributes.uv) g.setAttribute('uv', new THREE.Float32BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
      const a = g.attributes.uv.array;
      for (let i = 0; i < a.length; i += 2) { a[i] = gx; a[i + 1] = gy; }
      g.userData.wwF = 1;
      return g;
    };
    const GL = (g, glow, iron) => flag(g, glow || 0, iron ? 1 : 0);
    { const add0 = B.add; B.add = function (m, g) { if (m === mGlass) { const L = Array.isArray(g) ? g : [g]; for (const q of L) if (q && !q.userData.wwF) flag(q, 0, 0); } return add0(m, g); }; }

    // a balustrade along a world polyline: plinth, rail, square balusters (4-sided, open) and piers at the vertices
    function balustrade(pts, y0, o) {
      o = o || {};
      const h = o.h || 1.0, sp = o.sp || 0.62, m = o.mat || mTrim;
      for (let i = 0; i + 1 < pts.length; i++) {
        const a = pts[i], b = pts[i + 1], s = K.seg(a, b);
        if (s.len < 0.05) continue;
        B.add(m, K.edgeBox(a, b, y0, 0.17, 0.4, 0, 0.2));
        B.add(m, K.edgeBox(a, b, y0 + h - 0.14, 0.14, 0.34, 0, 0.17));
        if (o.solid) B.add(m, K.edgeBox(a, b, y0 + 0.17, h - 0.31, 0.2, 0, 0));
        else {
          const n = Math.max(1, Math.round(s.len / sp));
          for (let k = 0; k < n; k++) {
            const t = (k + 0.5) / n, g = new THREE.CylinderGeometry(0.075, 0.105, h - 0.31, 4, 1, true);
            g.rotateY(Math.PI / 4 - s.ang); g.translate(a[0] + (b[0] - a[0]) * t, y0 + 0.17 + (h - 0.31) / 2, a[1] + (b[1] - a[1]) * t);
            B.add(m, g);
          }
        }
        if (!o.noPiers) B.add(m, K.box(0.46, h + 0.08, 0.46, a[0], y0 + (h + 0.08) / 2, a[1], -s.ang));
      }
      if (!o.noPiers && pts.length > 1) { const a = pts[pts.length - 1], s = K.seg(pts[pts.length - 2], a); B.add(m, K.box(0.46, h + 0.08, 0.46, a[0], y0 + (h + 0.08) / 2, a[1], -s.ang)); }
    }
    // an arched opening on the face v = vf of frame f, outward sign s. The head is a half ellipse of half width hw and rise
    // `rise`, or with o.seg a true segment of a circle (a segmental arch: chord 2 hw, rise `rise`). o.yBot adds the opening
    // below the springing line; o.band a voussoir ring proud of the wall (o.key a keystone); the opening is dark glass
    // (o.glow for a night glow) or, with o.iron, matte dark timber for the tailrace gates
    function arch(f, uc, vf, s, ySpring, hw, rise, o) {
      o = o || {};
      const n = o.n || 10, vv = vf + s * (o.dp || 0.03), IN = P3(f, uc, vf - s, ySpring), dark = [];
      let pt;
      if (o.seg) {
        const Rc = (hw * hw + rise * rise) / (2 * rise), cy = ySpring + rise - Rc, t0 = Math.atan2(ySpring - cy, hw);
        pt = (k, g) => { const t = t0 + (Math.PI - 2 * t0) * k / n; return [uc + (Rc + g) * Math.cos(t), cy + (Rc + g) * Math.sin(t)]; };
      } else pt = (k, g) => { const t = Math.PI * k / n; return [uc + (hw + g) * Math.cos(t), ySpring + (rise + g) * Math.sin(t)]; };
      for (let k = 0; k < n; k++) {
        const a = pt(k, 0), b = pt(k + 1, 0);
        dark.push(K.tri(P3(f, a[0], vv, a[1]), P3(f, b[0], vv, b[1]), P3(f, uc, vv, ySpring), IN));
      }
      if (o.yBot != null) dark.push(K.quad(P3(f, uc - hw, vv, o.yBot), P3(f, uc + hw, vv, o.yBot), P3(f, uc + hw, vv, ySpring), P3(f, uc - hw, vv, ySpring), IN));
      B.add(mGlass, GL(dark, o.glow, o.iron));
      if (o.band) {
        const vb = vf + s * (o.proud || 0.08), ring = [], bd = o.band;
        for (let k = 0; k < n; k++) {
          const a0 = pt(k, 0), a1 = pt(k, bd), b1 = pt(k + 1, bd), b0 = pt(k + 1, 0);
          ring.push(K.quad(P3(f, a0[0], vb, a0[1]), P3(f, a1[0], vb, a1[1]), P3(f, b1[0], vb, b1[1]), P3(f, b0[0], vb, b0[1]), IN));
        }
        if (o.yBot != null && o.jambs) for (const e of [-1, 1]) {
          const u0 = uc + e * hw, u1 = uc + e * (hw + bd);
          ring.push(K.quad(P3(f, u0, vb, o.yBot), P3(f, u1, vb, o.yBot), P3(f, u1, vb, ySpring), P3(f, u0, vb, ySpring), IN));
        }
        B.add(o.bandMat || mStone, ring);
        if (o.key) { const c = pt(n / 2, 0); B.add(o.bandMat || mStone, K.boxF(f, uc, vf + s * ((o.proud || 0.08) + 0.06), 0.75, 0.2, c[1] - 0.1, bd + 0.35)); }
      }
    }
    // a window on the face v = vf (outward s): glass just proud of the wall, a flat frame, a sill; optional round head
    function win(f, uc, vf, s, yb, w, h, o) {
      o = o || {};
      const vg = vf + s * 0.03, IN = P3(f, uc, vf - s, yb + h / 2), a = uc - w / 2, b = uc + w / 2;
      B.add(mGlass, GL(K.quad(P3(f, a, vg, yb), P3(f, b, vg, yb), P3(f, b, vg, yb + h), P3(f, a, vg, yb + h), IN), o.glow));
      const fr = o.frame === undefined ? mTrim : o.frame, fw = o.fw || 0.16, vb = vf + s * 0.07;
      if (o.arch) arch(f, uc, vf, s, yb + h, w / 2, w / 2, { n: 8, band: fr ? fw : 0, bandMat: fr, proud: 0.07, glow: o.glow });
      if (fr) {
        const Q = (u0, u1, y0, y1) => K.quad(P3(f, u0, vb, y0), P3(f, u1, vb, y0), P3(f, u1, vb, y1), P3(f, u0, vb, y1), IN);
        B.add(fr, [Q(a - fw, a, yb, yb + h), Q(b, b + fw, yb, yb + h)]);
        if (!o.arch) B.add(fr, Q(a - fw, b + fw, yb + h, yb + h + fw));
      }
      if (o.sill !== false) B.add(o.sillMat || fr || mTrim, K.boxF(f, uc, vf + s * 0.1, w + 0.34, 0.24, yb - 0.16, 0.16));
    }
    // columns in a frame at local (u, v)
    const col = (f, u, v, y0, h, r, cap, seg) => { const p = f.p(u, v); B.add(mTrim, K.column(p[0], y0, p[1], h, r, cap || 'tuscan', seg || 12)); };
    // a cast-iron lamp standard on the terrace (about 5 m): base, shaft, collar, a lantern that lights with the photocell
    const lamps = [];
    function lampStd(x, z, y0) {
      B.add(mGlass, GL([K.box(0.42, 0.55, 0.42, x, y0 + 0.275, z, 0), K.cyl(0.06, 0.09, 3.3, 6, x, y0 + 0.55, z),
        K.box(0.3, 0.12, 0.3, x, y0 + 3.9, z, 0), K.cone(0.4, 0.42, 4, x, y0 + 4.76, z, Math.PI / 4)], 0, 1));
      B.add(mGlass, GL(K.box(0.46, 0.8, 0.46, x, y0 + 4.36, z, 0), 1.6, 0));
      lamps.push(new THREE.Vector4(x, y0 + 4.3, z, 7.5));
    }
    // a bell (ogee) roof turned on a lathe, with ribs; prof = [[r, y], ...] from the eave up
    function bellRoof(cx, y0, cz, prof, seg, ribs) {
      const g = new THREE.LatheGeometry(prof.map((p) => new THREE.Vector2(p[0], p[1])), seg);
      g.translate(cx, y0, cz);
      B.add(mRoof, g);
      for (let j = 0; j < (ribs || 0); j++) {
        const a = (j + 0.5) * 2 * Math.PI / ribs;
        for (let i = 0; i + 1 < prof.length; i++) {
          const [r0, y0p] = prof[i], [r1, y1p] = prof[i + 1], len = Math.hypot(r1 - r0, y1p - y0p);
          if (len < 0.05) continue;
          const nr = (y1p - y0p) / len, ny = -(r1 - r0) / len;   // outward normal of the profile segment
          const b = new THREE.BoxGeometry(len, 0.1, 0.14);
          b.rotateZ(Math.atan2(y1p - y0p, r1 - r0));
          b.translate((r0 + r1) / 2 + nr * 0.05, (y0p + y1p) / 2 + ny * 0.05, 0);
          b.rotateY(-a);
          b.translate(cx, y0, cz);
          B.add(mRoof, b);
        }
      }
    }

    // =====================================================================================================
    // THE OLD MILL HOUSE (1819-22, remodelled 1867-72): grey ashlar river front, segmental tailrace arches closed by
    // dark gates, lunettes, round-headed French windows over balconies, a cornice and the balustraded terrace on its roof
    // =====================================================================================================
    const millRing = R(fm, [[0, 0], [82.4, 0], [84.6, -0.1], [86.8, -0.6], [91.8, -0.6], [94.0, -0.8], [95.2, -1.3], [96.2, -2.1],
      [97.5, -4.0], [86.0, -10.9], [82.5, -12.8], [82.5, -16.5], [6.75, -16.5]]);
    B.add(mStone, K.prism(millRing, F, T - 0.05));
    B.add(mStone, K.plate(millRing, T, 0.05));             // the promenade on the mill house roof: grey stone flags
    // bays along the river face: [u0, u1, front v, kind]
    const bays = [[6.75, 10.1, -20.35, 'link'], [10.1, 17.4, -20.35, 'wing'], [17.4, 22.3, -16.5, 'rec'], [22.3, 34.7, -18.8, 'big'],
      [34.7, 39.7, -16.5, 'rec'], [39.7, 52.8, -19.6, 'big'], [52.8, 57.4, -16.5, 'rec'], [57.4, 70.3, -18.8, 'big'],
      [70.3, 74.9, -16.5, 'rec'], [74.9, 82.5, -20.35, 'wing']];
    const GATE = { iron: true, dp: 0.07 };                 // the gates sit in front of the tide band
    for (const [u0, u1, vf, kind] of bays) {
      const uc = (u0 + u1) / 2;
      if (vf < -16.6) B.add(mStone, K.slabF(fm, u0, u1, vf, -16.4, F, T - 0.05));
      if (vf < -16.6) B.add(mStone, K.slabF(fm, u0, u1, vf, -16.4, T - 0.05, T));
      if (kind === 'big') {
        // one low segmental arch (6.7 m span, 1.7 m rise, springing 1.6 m over the tailwater) under a heavy voussoir ring
        arch(fm, uc, vf, -1, W + 1.6, 3.35, 1.7, Object.assign({ seg: true, band: 0.55, proud: 0.1, bandMat: mStone, n: 12, yBot: W - 0.4, key: true }, GATE));
        for (const e of [-1, 1]) {
          arch(fm, uc + e * 3.3, vf, -1, W + 5.2, 1.25, 1.25, { band: 0.18, proud: 0.06, bandMat: mTrim, n: 8, glow: 0.25 });
          B.add(mTrim, K.boxF(fm, uc + e * 3.3, vf - 0.1, 2.9, 0.24, W + 5.05, 0.16));
        }
      } else if (kind === 'wing') {
        arch(fm, uc, vf, -1, W + 1.4, 2.9, 2.9, Object.assign({ band: 0.5, proud: 0.1, bandMat: mStone, n: 12, yBot: W - 0.4, key: true }, GATE));
        win(fm, uc, vf, -1, W + 5.15, 1.0, 1.05, { frame: mTrim, glow: 0.2 });
      } else if (kind === 'link') {
        arch(fm, uc, vf, -1, W + 1.0, 1.1, 1.1, Object.assign({ band: 0.35, proud: 0.08, bandMat: mStone, n: 8, yBot: W - 0.4 }, GATE));
      } else {   // recessed bay: a tall round-headed French window over a small balustraded balcony, a low opening at the water
        win(fm, uc, vf, -1, W + 1.9, 2.2, 3.4, { arch: true, frame: mTrim, sill: false, glow: 0.2 });
        B.add(mTrim, K.slabF(fm, uc - 1.25, uc + 1.25, vf - 0.75, vf, W + 1.6, W + 1.8));
        balustrade([fm.p(uc - 1.1, vf - 0.6), fm.p(uc + 1.1, vf - 0.6)], W + 1.8, { h: 0.85, sp: 0.3 });
        B.add(mGlass, GL(K.quad(P3(fm, uc - 0.8, vf - 0.07, W - 0.4), P3(fm, uc + 0.8, vf - 0.07, W - 0.4), P3(fm, uc + 0.8, vf - 0.07, W + 1.2), P3(fm, uc - 0.8, vf - 0.07, W + 1.2), P3(fm, uc, vf + 1, W)), 0, 1));
      }
    }
    // cornice round the river front, the dark tide band at the waterline, and the balustrade along the terrace edge
    const outline = [[6.75, -20.35], [17.4, -20.35], [17.4, -16.5], [22.3, -16.5], [22.3, -18.8], [34.7, -18.8], [34.7, -16.5], [39.7, -16.5],
      [39.7, -19.6], [52.8, -19.6], [52.8, -16.5], [57.4, -16.5], [57.4, -18.8], [70.3, -18.8], [70.3, -16.5], [74.9, -16.5], [74.9, -20.35], [82.5, -20.35]];
    const cornRing = R(fm, outline.concat([[82.5, -13.5], [6.75, -13.5]]));
    B.add(mStone, K.prism(K.offsetRing(cornRing, 0.32), T - 0.75, T - 0.3));
    B.add(mStoneDk, K.prism(K.offsetRing(cornRing, 0.04), W - 0.3, W + 0.9));
    const balRing = K.offsetRing(cornRing, -0.24);
    balustrade(balRing.slice(0, outline.length), T, { h: 1.0 });
    // the south end of the terrace over the link, beside the Engine House porch, and the landward edge south of the
    // promenade, where the terrace stands 3 to 5 m over the drawn ground
    balustrade([fm.p(6.95, -20.1), fm.p(6.95, -16.3)], T, { h: 1.0 });
    balustrade([fm.p(2.0, -0.25), fm.p(23.0, -0.25)], T, { h: 1.0, sp: 0.7 });

    // the promenade over the filled forebay (brick-paved terrace along the eastern front), retaining wall and balustrade
    const promRing = R(fm, [[23, 0], [90, 0], [90, 11], [23, 11]]);
    B.add(mStone, K.prism(promRing, F, T - 0.05));
    B.add(mBrick, K.plate(promRing, T, 0.05));
    B.add(mStone, K.prism(K.offsetRing(promRing, 0.2), T - 0.45, T - 0.2));
    balustrade(R(fm, [[23.25, 0.2], [23.25, 10.75], [89.75, 10.75], [89.75, 0.2]]), T, { h: 1.0, sp: 0.7 });
    for (const u of [26, 41, 56, 71, 86]) lampStd(...fm.p(u, 9.9), T);

    // =====================================================================================================
    // THE WINGS (1822): the Caretaker's House (south) and the Watering Committee (north), Doric tetrastyle temples
    // =====================================================================================================
    for (const [u0, u1] of [[10.1, 17.4], [74.9, 82.5]]) {
      const um = (u0 + u1) / 2, vFr = -20.1, vBk = -7.2;
      B.add(mTrim, K.slabF(fm, u0 + 0.15, u1 - 0.15, vFr + 0.45, vBk, T, T + 0.3));
      B.add(mStucco, K.slabF(fm, u0 + 0.3, u1 - 0.3, -16.9, vBk - 0.1, T + 0.3, T + 4.35));
      for (let i = 0; i < 4; i++) col(fm, u0 + 0.8 + i * (u1 - u0 - 1.6) / 3, -19.25, T + 0.3, 4.05, 0.29, 'doric', 12);
      B.add(mTrim, K.slabF(fm, u0 + 0.05, u1 - 0.05, -19.8, vBk - 0.05, T + 4.35, T + 5.0));
      const g = K.gableF(fm, u0 + 0.05, u1 - 0.05, -19.8, vBk - 0.05, T + 5.0, T + 6.75, false, 0.3);
      B.add(mRoof, g.slopes); B.add(mTrim, g.ends);
      B.add(mTrim, K.pedimentF(fm, u0 - 0.12, u1 + 0.12, -19.95, -1, T + 4.95, 1.9, 0.5));
      B.add(mStucco, K.slabF(fm, um - 0.4, um + 0.4, -10.4, -9.6, T + 5.5, T + 7.5));
      B.add(mTrim, K.slabF(fm, um - 0.5, um + 0.5, -10.5, -9.5, T + 7.5, T + 7.7));
      // door in the portico and a blind arched window on each flank
      B.add(mGlass, GL(K.quad(P3(fm, um - 0.8, -16.93, T + 0.3), P3(fm, um + 0.8, -16.93, T + 0.3), P3(fm, um + 0.8, -16.93, T + 3.2), P3(fm, um - 0.8, -16.93, T + 3.2), P3(fm, um, -15, T + 1)), 0.2));
      win(fmR, -12.2, -(u0 + 0.3), 1, T + 1.3, 1.3, 1.6, { arch: true });
      win(fmR, -12.2, -(u1 - 0.3), -1, T + 1.3, 1.3, 1.6, { arch: true });
    }

    // =====================================================================================================
    // THE ENTRANCE HOUSES (1871): round-headed windows between pilaster strips, a bracketed cornice, a low hip roof, and
    // William Rush's reclining figures on the attic
    // =====================================================================================================
    for (const [u0, u1, v0, v1] of [[21.8, 35.0, -13.4, -9.0], [57.6, 70.8, -13.6, -8.9]]) {
      const um = (u0 + u1) / 2, vm = (v0 + v1) / 2, bu = (i) => u0 + 1.6 + i * (u1 - u0 - 3.2) / 4;
      B.add(mStucco, K.slabF(fm, u0, u1, v0, v1, T, T + 3.05));
      B.add(mTrim, K.slabF(fm, u0 - 0.12, u1 + 0.12, v0 - 0.12, v1 + 0.12, T + 2.7, T + 3.05));   // the bracket course
      B.add(mTrim, K.slabF(fm, u0 - 0.28, u1 + 0.28, v0 - 0.28, v1 + 0.28, T + 3.05, T + 3.35));  // the cornice
      B.add(mTrim, K.slabF(fm, u0 - 0.1, u1 + 0.1, v0 - 0.1, v1 + 0.1, T, T + 0.3));
      // pilaster strips between the bays and at the corners, both long faces
      for (let i = 0; i <= 5; i++) {
        const u = i === 0 ? u0 + 0.2 : i === 5 ? u1 - 0.2 : (bu(i - 1) + bu(i)) / 2;
        B.add(mTrim, K.slabF(fm, u - 0.125, u + 0.125, v0 - 0.08, v1 + 0.08, T + 0.3, T + 2.7));
      }
      for (let i = 0; i < 5; i++) win(fm, bu(i), v0, -1, T + 1.1, 0.9, 1.1, { arch: true, glow: 0.2 });
      for (const i of [0, 1, 3, 4]) win(fm, bu(i), v1, 1, T + 1.1, 0.9, 1.1, { arch: true, glow: 0.2 });
      B.add(mTrim, K.slabF(fm, um - 1.35, um + 1.35, v1, v1 + 0.9, T, T + 3.05));
      B.add(mGlass, GL(K.quad(P3(fm, um - 0.7, v1 + 0.93, T + 0.3), P3(fm, um + 0.7, v1 + 0.93, T + 0.3), P3(fm, um + 0.7, v1 + 0.93, T + 2.6), P3(fm, um - 0.7, v1 + 0.93, T + 2.6), P3(fm, um, v1, T + 1)), 0.25));
      B.add(mRoof, K.hipF(fm, u0 + 0.1, u1 - 0.1, v0 + 0.1, v1 - 0.1, T + 3.35, T + 4.35, 0.15));
      // the attic pedestal and the figure group
      B.add(mStucco, K.slabF(fm, um - 1.5, um + 1.5, vm - 1.0, vm + 1.0, T + 3.35, T + 4.7));
      B.add(mTrim, K.slabF(fm, um - 1.6, um + 1.6, vm - 1.1, vm + 1.1, T + 4.7, T + 4.85));
      const p = fm.p(um, vm), rot = -fm.a;
      const fig = [
        K.box(2.5, 0.42, 0.9, 0, T + 5.06, 0, 0),              // the draped body lying along the pedestal
        K.box(0.55, 0.85, 0.55, 0.95, T + 5.45, 0.05, 0.3),    // torso raised on an elbow
        K.box(0.9, 0.35, 0.55, -0.8, T + 5.35, -0.1, 0.2)      // knees
      ];
      const head = new THREE.IcosahedronGeometry(0.24, 0); head.translate(1.05, T + 6.05, 0.05); fig.push(head);
      for (const g of fig) { g.rotateY(rot); g.translate(p[0], 0, p[1]); B.add(mTrim, g); }
    }

    // =====================================================================================================
    // THE PAVILION (1872, from Graff's 1820 drawing): an open hexastyle temple, 6 by 9 columns, pediments both ends
    // =====================================================================================================
    {
      const u0 = 39.7, u1 = 52.8, v0 = -19.6, v1 = 0.3;
      B.add(mTrim, K.slabF(fm, u0 + 0.2, u1 - 0.2, v0 + 0.45, v1 - 0.2, T, T + 0.3));
      const cu0 = 40.45, cu1 = 52.05, cv0 = -18.75, cv1 = -0.45;
      for (let i = 0; i < 6; i++) { const u = cu0 + i * (cu1 - cu0) / 5; col(fm, u, cv0, T + 0.3, 4.85, 0.36); col(fm, u, cv1, T + 0.3, 4.85, 0.36); }
      for (let j = 1; j < 8; j++) { const v = cv0 + j * (cv1 - cv0) / 8; col(fm, cu0, v, T + 0.3, 4.85, 0.36); col(fm, cu1, v, T + 0.3, 4.85, 0.36); }
      B.add(mTrim, K.slabF(fm, u0 + 0.1, u1 - 0.1, v0 + 0.3, v1 - 0.25, T + 5.15, T + 6.65));
      const g = K.gableF(fm, u0 + 0.1, u1 - 0.1, v0 + 0.3, v1 - 0.25, T + 6.65, T + 9.0, false, 0.35);
      B.add(mRoof, g.slopes); B.add(mTrim, g.ends);
      B.add(mTrim, K.pedimentF(fm, u0 - 0.05, u1 + 0.05, v0 + 0.12, -1, T + 6.6, 2.55, 0.55));
      B.add(mTrim, K.pedimentF(fm, u0 - 0.05, u1 + 0.05, v1 - 0.07, 1, T + 6.6, 2.55, 0.55));
      for (const [v, s] of [[v0 + 0.12, -1], [v1 - 0.07, 1]]) {
        const c = P3(fm, (u0 + u1) / 2, v + s * 0.02, T + 7.75), n = 10, tris = [], IN = P3(fm, (u0 + u1) / 2, v - s, T + 7.75);
        for (let k = 0; k < n; k++) {
          const a0 = 2 * Math.PI * k / n, a1 = 2 * Math.PI * (k + 1) / n;
          tris.push(K.tri(P3(fm, (u0 + u1) / 2 + 0.42 * Math.cos(a0), v + s * 0.02, T + 7.75 + 0.42 * Math.sin(a0)), P3(fm, (u0 + u1) / 2 + 0.42 * Math.cos(a1), v + s * 0.02, T + 7.75 + 0.42 * Math.sin(a1)), c, IN));
        }
        B.add(mGlass, tris);
      }
    }

    // =====================================================================================================
    // THE ENGINE HOUSE (1812-15, Graff; saloon and river porch 1835): a Federal villa on a stone base. HAER: the main block is
    // three bays and three storeys (u' 6.1..18.6) with a roof between tall end walls and four chimneys, flanked north and south
    // by one-storey boiler sheds (to T + 7.0, a lunette each, balustraded roofs); the ten-column Doric porch along the river
    // =====================================================================================================
    {
      const L = 24.7, D = -17.3, M0 = 6.1, M1 = 18.6;
      const sheds = [[0, M0], [M1, L]];
      B.add(mStone, K.slabF(ef, -0.2, L, -23.8, -3.5, F, T - 0.02));
      B.add(mStone, K.slabF(ef, -0.2, 22.9, -23.8, D - 0.1, T - 0.02, T));
      B.add(mStone, K.slabF(ef, -0.45, L, -24.1, -3.5, T - 0.75, T - 0.3));
      B.add(mStoneDk, K.slabF(ef, -0.24, L, -23.84, -3.5, W - 0.3, W + 0.9));   // tide band
      // the river front below the terrace: round openings like the 1815 drawing
      for (let i = 0; i < 6; i++) arch(ef, 2.2 + i * 3.7, -23.8, -1, W + 3.2, 0.55, 0.55, { n: 8, band: 0.16, bandMat: mTrim, proud: 0.05, yBot: W + 2.4 });
      for (let i = 0; i < 4; i++) arch(efR, -19.5 + i * 4.4, 0.2, 1, W + 3.2, 0.55, 0.55, { n: 8, band: 0.16, bandMat: mTrim, proud: 0.05, yBot: W + 2.4 });
      // the porch-level storey runs the full length (main block and sheds), a string course over it
      B.add(mStucco, K.slabF(ef, 0, L, D, 0, F, T + 4.55));
      B.add(mTrim, K.slabF(ef, -0.08, L + 0.08, D - 0.08, 0.08, T + 4.55, T + 4.8));
      // the boiler sheds: one tall storey to T + 7.0, a cornice, a flat roof and a balustrade on the three outer sides
      for (const [a, b] of sheds) {
        B.add(mStucco, K.slabF(ef, a, b, D, 0, T + 4.8, T + 6.7));
        B.add(mTrim, K.slabF(ef, a - (a === 0 ? 0.2 : 0), b + (b === L ? 0.2 : 0), D - 0.2, 0.2, T + 6.7, T + 7.0));
        B.add(mRoof, K.slabF(ef, a + 0.1, b - 0.1, D + 0.1, -0.1, T + 7.0, T + 7.08));
        const out = a === 0 ? 0.25 : L - 0.25, inn = a === 0 ? b - 0.1 : a + 0.1;
        balustrade(R(ef, [[inn, D + 0.05], [out, D + 0.05], [out, -0.05], [inn, -0.05]]), T + 7.0, { h: 0.8, sp: 0.6 });
        const um = (a + b) / 2;
        for (const [vf, s] of [[D, -1], [0, 1]]) arch(ef, um, vf, s, T + 5.3, 0.9, 0.9, { n: 8, band: 0.16, bandMat: mTrim, proud: 0.06, glow: 0.25 });
      }
      // the main block: two more storeys, a cornice, the roof between tall end walls with their chimneys
      B.add(mStucco, K.slabF(ef, M0, M1, D, 0, T + 4.8, T + 10.4));
      B.add(mTrim, K.slabF(ef, M0 - 0.38, M1 + 0.38, D - 0.38, 0.38, T + 10.4, T + 10.85));
      const g = K.gableF(ef, M0, M1, D, 0, T + 10.85, T + 15.2, true, 0.3);
      B.add(mRoof, g.slopes); B.add(mStucco, g.ends);
      for (const [a, b] of [[M0 - 0.3, M0 + 0.55], [M1 - 0.55, M1 + 0.3]]) {
        B.add(mStucco, K.slabF(ef, a, b, -13.6, -3.7, T + 10.85, T + 15.8));
        B.add(mTrim, K.slabF(ef, a - 0.08, b + 0.08, -13.7, -3.6, T + 15.8, T + 16.0));
        B.add(mStucco, K.slabF(ef, a, b, -13.6, -12.2, T + 16.0, T + 16.7));
        B.add(mStucco, K.slabF(ef, a, b, -5.1, -3.7, T + 16.0, T + 16.7));
      }
      // windows. The river and land fronts: five round-headed doors behind the colonnade (three bays and the two sheds'),
      // on the land front a door in the central bay and the sheds' and windows between; the main block's second floor
      // round-headed, its third floor square. The end walls: four openings on the ground floor and the sheds' upper zone,
      // two on the third floor above the shed roofs, two small attic windows in the tall end walls
      const bu = (i) => M0 + (M1 - M0) * (i + 0.5) / 3, bays5 = [(0 + M0) / 2, bu(0), bu(1), bu(2), (M1 + L) / 2];
      for (const u of bays5) win(ef, u, D, -1, T + 0.3, 1.4, 2.75, { arch: true, sill: false, glow: 0.5 });
      bays5.forEach((u, i) => {
        if (i === 0 || i === 2 || i === 4) win(ef, u, 0, 1, T + 0.3, 1.4, 2.75, { arch: true, sill: false, glow: 0.5 });
        else win(ef, u, 0, 1, T + 0.8, 1.35, 2.2, { glow: 0.5 });
      });
      for (let i = 0; i < 3; i++) {
        for (const [vf, s] of [[D, -1], [0, 1]]) {
          win(ef, bu(i), vf, s, T + 5.45, 1.35, 1.85, { arch: true, glow: 0.5 });
          win(ef, bu(i), vf, s, T + 8.3, 1.2, 1.35, {});
        }
      }
      const bv = (i) => D * (i + 0.5) / 4;
      for (let i = 0; i < 4; i++) {
        for (const [c, s] of [[0, 1], [L, -1]]) {
          win(efR, bv(i), -c, s, T + 0.8, 1.3, 2.1, { glow: 0.5 });
          arch(efR, bv(i), -c, s, T + 5.2, 0.7, 0.7, { n: 8, band: 0.14, bandMat: mTrim, proud: 0.06, glow: 0.25 });
        }
      }
      for (const [c, s] of [[M0, 1], [M1, -1]]) for (const v of [D * 0.25, D * 0.75]) win(efR, v, -c, s, T + 8.3, 1.15, 1.35, {});
      for (const [c, s] of [[M0 - 0.3, 1], [M1 + 0.3, -1]]) for (const v of [-10.6, -6.7]) win(efR, v, -c, s, T + 12.1, 0.85, 1.1, {});
      // the land front stands a storey over the drawn ground: basement windows and a plinth band
      for (const u of bays5) win(ef, u, 0, 1, T - 2.9, 1.1, 1.1, { frame: mTrim });
      B.add(mTrim, K.slabF(ef, -0.1, L + 0.1, -3.5, 0.12, T - 0.35, T - 0.05));
      // the 1835 porch: ten Doric columns, a flat roof with its balustrade
      for (let i = 0; i < 10; i++) col(ef, 0.4 + i * 2.46, -23.3, T, 4.3, 0.28, 'doric');
      B.add(mTrim, K.slabF(ef, -0.1, 22.95, -23.85, D, T + 4.3, T + 4.75));
      balustrade(R(ef, [[22.7, -23.6], [0.15, -23.6], [0.15, D - 0.1]]), T + 4.75, { h: 0.85, sp: 0.55 });
    }

    // =====================================================================================================
    // THE NEW MILL HOUSE (1859-62): the old mill house's stone, a step darker, built into the mound dam at an angle. Four
    // quoined piers, three turbine bays each with a small segmental tailrace arch and a rectangular window over it,
    // round-headed windows in the piers, the roof plaza with its lamp standards
    // =====================================================================================================
    const nmhL = [[100.7, -50.6], [113.3, -43.3], [111.8, -40.6], [117.4, -37.4], [103.2, -12.8], [102.9, -13.0], [97.5, -4.0], [86.0, -10.9],
      [82.5, -12.8], [82.5, -20.3], [81.1, -20.3], [82.3, -22.2], [78.1, -24.6], [79.7, -27.3], [80.4, -26.9], [83.4, -32.2], [82.4, -32.8],
      [83.9, -35.4], [85.0, -34.8], [88.6, -41.0], [87.5, -41.6], [89.2, -44.5], [90.3, -43.8], [94.2, -50.4], [93.9, -50.6], [95.6, -53.6]];
    const nmh = R(fm, nmhL);
    B.add(mStoneDk, K.prism(nmh, F, T - 0.05));
    B.add(mStone, K.plate(nmh, T, 0.05));
    const edgeOut = (a, b, ring, y0, h, t, off) => {
      const s = K.seg(a, b), probeP = [s.mid[0] + s.nx * 0.5, s.mid[1] + s.nz * 0.5];
      const sg = inPoly(probeP[0], probeP[1], ring) ? -1 : 1;
      B.add(mStoneDk, K.edgeBox(a, b, y0, h, t, sg * off, off));
    };
    const nA = fm.p(78.1, -24.6), nB = fm.p(95.6, -53.6), nC = fm.p(113.3, -43.3), nD = fm.p(117.4, -37.4), nE = fm.p(97.5, -4.0);
    for (const [a, b] of [[nA, nB], [nB, nC], [nC, nD], [nD, nE]]) edgeOut(a, b, nmh, T - 0.8, 0.45, 0.6, 0.2);
    const cN = K.centroid(nmh);
    const faceFrame = (q0, q1) => {
      const pf = K.frameFromEdge(fm.p(...q0), fm.p(...q1));
      return { pf, len: Math.hypot(q1[0] - q0[0], q1[1] - q0[1]), so: -Math.sign(pf.local(cN[0], cN[1])[1]) };
    };
    for (const [q0, q1] of [[[80.4, -26.9], [83.4, -32.2]], [[85.0, -34.8], [88.6, -41.0]], [[90.3, -43.8], [94.2, -50.4]]]) {
      const { pf, len, so } = faceFrame(q0, q1), pc = len / 2;
      arch(pf, pc, 0, so, W + 1.0, 1.3, 0.8, { seg: true, band: 0.4, proud: 0.08, bandMat: mStone, n: 8, yBot: W - 0.4, iron: true, dp: 0.05 });
      win(pf, pc, 0, so, T - 4.6, 1.1, 2.2, { frame: mStone, sillMat: mStone });
      // the grille over the window
      for (const e of [-0.28, 0, 0.28]) B.add(mGlass, GL(K.boxF(pf, pc + e, so * 0.06, 0.05, 0.05, T - 4.6, 2.2), 0, 1));
    }
    for (const [q0, q1] of [[[78.1, -24.6], [79.7, -27.3]], [[82.4, -32.8], [83.9, -35.4]], [[87.5, -41.6], [89.2, -44.5]], [[93.9, -50.6], [95.6, -53.6]]]) {
      const { pf, len, so } = faceFrame(q0, q1);
      win(pf, len / 2, 0, so, T - 4.6, 1.0, 2.0, { arch: true, frame: mStone, sillMat: mStone });
      // large quoins at both corners of the pier, long and short in turn, every other course
      for (let k = 0; k < 7; k++) {
        const lq = k % 2 ? 0.55 : 0.9, y = W + 0.4 + k * 0.9;
        B.add(mStone, K.slabF(pf, 0, lq, so * 0.1, -so * 0.02, y, y + 0.45));
        B.add(mStone, K.slabF(pf, len - lq, len, so * 0.1, -so * 0.02, y, y + 0.45));
      }
    }
    balustrade([nA, nB, nC, nD], T, { h: 1.0, sp: 0.7 });
    balustrade([nD, nE], T, { h: 1.0, sp: 0.7 });
    // lamp standards on the plaza, 3 m in from the balustrade's corners
    for (const c of [nA, nB, nD, nE]) {
      const dx = cN[0] - c[0], dz = cN[1] - c[1], dl = Math.hypot(dx, dz);
      lampStd(c[0] + dx / dl * 4.2, c[1] + dz / dl * 4.2, T);
    }

    // =====================================================================================================
    // THE MOUND DAM AND THE GAZEBO (1835): octagonal pier at the dam's end; HAER: "the twelve-column Doric gazebo has an
    // octagonal plan with bell-shaped roof, originally capped by an eagle carved by William Rush"
    // =====================================================================================================
    const mound = R(fm, [[103.4, -49.66], [110.6, -44.24], [132.8, -73.7], [125.6, -79.1]]);
    B.add(mStoneDk, K.prism(mound, F, T - 0.55));
    B.add(mStone, K.plate(mound, T - 0.5, 0.05));
    balustrade([fm.p(104.1, -49.2), fm.p(125.9, -78.2)], T - 0.5, { h: 1.0, solid: true });
    balustrade([fm.p(110.0, -44.9), fm.p(131.9, -73.9)], T - 0.5, { h: 1.0, solid: true });
    const pier = [];
    for (let k = 0; k < 8; k++) { const a = Math.PI / 8 + k * Math.PI / 4; pier.push([G[0] + 5.4 * Math.cos(a), G[1] + 5.4 * Math.sin(a)]); }
    {
      B.add(mStoneDk, K.prism(pier, F, T - 0.55));
      B.add(mStone, K.plate(pier, T - 0.5, 0.05));
      const toDam = K.centroid(mound), dd = [toDam[0] - G[0], toDam[1] - G[1]];
      const pr = K.offsetRing(pier, -0.25);
      for (let k = 0; k < 8; k++) {
        const a = pr[k], b = pr[(k + 1) % 8], m = [(a[0] + b[0]) / 2 - G[0], (a[1] + b[1]) / 2 - G[1]];
        if ((m[0] * dd[0] + m[1] * dd[1]) / (Math.hypot(...m) * Math.hypot(...dd)) > 0.8) continue;
        balustrade([a, b], T - 0.5, { h: 1.0, sp: 0.55 });
      }
      const y0 = T - 0.5;
      B.add(mTrim, K.cyl(3.8, 3.9, 0.3, 16, G[0], y0, G[1]));
      for (let k = 0; k < 12; k++) { const a = (k + 0.5) * Math.PI / 6; B.add(mTrim, K.column(G[0] + 3.35 * Math.cos(a), y0 + 0.3, G[1] + 3.35 * Math.sin(a), 4.1, 0.2, 'doric', 10)); }
      B.add(mTrim, K.cyl(3.7, 3.7, 0.3, 16, G[0], y0 + 4.4, G[1]));      // architrave and frieze
      B.add(mTrim, K.cyl(3.9, 3.9, 0.12, 16, G[0], y0 + 4.68, G[1]));    // the cornice lip
      bellRoof(G[0], y0 + 4.8, G[1], [[3.95, 0], [3.7, 0.25], [2.6, 0.9], [1.2, 1.9], [0.45, 2.6], [0.45, 2.9]], 16, 8);
      B.add(mRoof, K.cyl(0.5, 0.5, 0.12, 12, G[0], y0 + 7.7, G[1]));     // the pedestal's cap
      const eagle = [K.box(0.35, 0.42, 0.7, 0, y0 + 8.03, 0, 0.6), K.box(1.5, 0.1, 0.42, 0, y0 + 8.3, 0, 0.6)];
      const eh = new THREE.IcosahedronGeometry(0.15, 0); eh.translate(0.28, y0 + 8.35, 0.28); eagle.push(eh);
      eagle.push(K.box(0.3, 0.2, 0.3, 0, y0 + 7.82, 0, 0));
      for (const g of eagle) { g.translate(G[0], 0, G[1]); }
      B.add(mGlass, GL(eagle, 0, 1));
    }

    // =====================================================================================================
    // THE MERCURY PAVILION (restored 2008): the octagonal summer house on the hill, with a replica of Rush's Mercury
    // (painted white, about two-thirds life size) on its roof
    // =====================================================================================================
    let mpRing = null;
    {
      const r0 = 2.95; mpRing = [];
      for (let k = 0; k < 8; k++) { const a = Math.PI / 8 + k * Math.PI / 4; mpRing.push([MP[0] + r0 * Math.cos(a), MP[1] + r0 * Math.sin(a)]); }
      const plat = mpRing.map((p) => [MP[0] + (p[0] - MP[0]) * 1.15, MP[1] + (p[1] - MP[1]) * 1.15]);
      let gLo = Infinity, gTop = -Infinity;
      for (const p of plat.concat(mpRing, [MP])) { const g = api.ground(p[0], p[1]); gLo = Math.min(gLo, g); gTop = Math.max(gTop, g); }
      const yb = gTop + 0.25;
      B.add(mStone, K.prism(plat, gLo - 0.8, yb - 0.25));                     // the platform on the cliff path
      B.add(mTrim, K.prism(K.offsetRing(plat, 0.08), yb - 0.25, yb));      // its coping
      for (let k = 0; k < 8; k++) { const a = Math.PI / 8 + k * Math.PI / 4; B.add(mTrim, K.column(MP[0] + 2.45 * Math.cos(a), yb, MP[1] + 2.45 * Math.sin(a), 2.9, 0.13, 'tuscan', 8)); }
      for (let k = 0; k < 8; k++) {   // a low railing between the columns, one side open to the path
        if (k === 3) continue;
        const a0 = Math.PI / 8 + k * Math.PI / 4, a1 = a0 + Math.PI / 4;
        const p0 = [MP[0] + 2.45 * Math.cos(a0), MP[1] + 2.45 * Math.sin(a0)], p1 = [MP[0] + 2.45 * Math.cos(a1), MP[1] + 2.45 * Math.sin(a1)];
        B.add(mTrim, K.edgeBox(p0, p1, yb + 0.85, 0.1, 0.1, 0, -0.1));
        B.add(mTrim, K.edgeBox(p0, p1, yb + 0.1, 0.08, 0.1, 0, -0.1));
      }
      B.add(mTrim, K.cyl(2.7, 2.7, 0.35, 8, MP[0], yb + 2.9, MP[1]));
      bellRoof(MP[0], yb + 3.25, MP[1], [[2.95, 0], [2.75, 0.18], [1.9, 0.65], [0.85, 1.3], [0.3, 1.8], [0.3, 2.0]], 8, 0);
      const top = yb + 5.25, fig = [];
      fig.push(K.cyl(0.32, 0.32, 0.2, 8, 0, top, 0));                                   // the globe's base
      fig.push(K.box(0.3, 0.75, 0.22, 0, top + 0.2, 0, 0).translate(0, 0.375, 0));      // legs and body
      fig.push(K.box(0.34, 0.5, 0.24, 0, top + 0.95, 0, 0).translate(0, 0.25, 0));      // torso
      const hd = new THREE.IcosahedronGeometry(0.13, 0); hd.translate(0, top + 1.62, 0); fig.push(hd);
      fig.push(K.box(0.08, 0.55, 0.08, 0.2, top + 1.35, 0, 0).translate(0, 0.27, 0));   // the raised arm with the caduceus
      for (const g of fig) { g.translate(MP[0], 0, MP[1]); B.add(mTrim, g); }
    }

    // =====================================================================================================
    // THE FAIRMOUNT DAM (1819-21, rebuilt 1842-43): crest from the gazebo to the drawn west bank, white water on the downstream face.
    // HAER: 1,025 ft = 312 m at about bearing 287. The app's drawn river is wider there: probed along the line, its bank (drawn
    // ground over the sheet at -7.34) starts 312 m out at bearing 280, about 322 m at 282, 330 m at 284 and never within 440 m at
    // 286 or 287. 282 at 327 m keeps within 5 degrees and 5 per cent of the record and buries the crest's end in the bank
    // =====================================================================================================
    {
      const br = 282 * Math.PI / 180, d = [Math.sin(br), -Math.cos(br)], n = [-d[1], d[0]];   // n: downstream, to the south
      const nd = n[1] > 0 ? n : [-n[0], -n[1]];
      const L = app ? 327 : 16;
      const s0 = [G[0] + 3 * d[0] + 2 * nd[0], G[1] + 3 * d[1] + 2 * nd[1]], s1 = [s0[0] + L * d[0], s0[1] + L * d[1]];
      B.add(mStoneDk, K.edgeBox(s0, s1, W - 2.0, 2.45, 2.6, 0, 0));
      const q = (a, t, y) => [a[0] + nd[0] * t, y, a[1] + nd[1] * t];
      B.add(mFoam, K.quad(q(s0, 1.25, W + 0.45), q(s1, 1.25, W + 0.45), q(s1, 6.5, W - 0.12), q(s0, 6.5, W - 0.12), [s0[0] + nd[0] * 4, W - 3, s0[1] + nd[1] * 4]));
    }

    // =====================================================================================================
    // NIGHT: the floodlight wash and the lamp pools (emissive, scaled by LAMP), the glass flags, the foam dimmed
    // =====================================================================================================
    while (lamps.length < 16) lamps.push(new THREE.Vector4(0, 0, 0, 0));
    const U = {
      uLamp: LAMP, uT: { value: T }, uW: { value: W }, uLamps: { value: lamps },
      uWash: { value: new THREE.Color(K.stored('#ffe2b8', 1)) }, uPoolCol: { value: new THREE.Color(K.stored('#ffcf8a', 1)) },
      uX0: { value: G[0] - 9 }, uX1: { value: -3272 }   // the floodlit stretch: the gazebo to the Engine House (not the dam, not the hill)
    };
    const WASH_GLSL = '#include <emissivemap_fragment>\n{\n' +
      '  float yb = vWwPos.y < uT - 0.3 ? uW : uT;\n' +                         // the river front is lit from the water, the rest from the terrace
      '  float up = clamp(1.25 - (vWwPos.y - yb) / 10.0, 0.4, 1.25);\n' +     // uplight: brightest at the foot of the wall
      '  float side = (1.0 - 0.7 * max(vWwN.y, 0.0)) * step(uX0, vWwPos.x) * step(vWwPos.x, uX1);\n' +   // floodlights hit walls, not floors
      '  vec3 pool = vec3(0.0);\n' +
      '  for (int i = 0; i < 16; i++) { vec4 L = uLamps[i]; if (L.w <= 0.0) continue; vec3 dd = vWwPos - L.xyz; pool += exp(-dot(dd, dd) / (L.w * L.w)); }\n' +
      '  totalEmissiveRadiance += uLamp * diffuseColor.rgb * (uWash * uWashK * up * side + uPoolCol * uPoolK * pool);\n}';
    function washPatch(m, k, poolK) {
      const own = { uWashK: { value: k }, uPoolK: { value: poolK } };
      m.onBeforeCompile = (sh) => {
        Object.assign(sh.uniforms, U, own);
        sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vWwPos, vWwN;')
          .replace('#include <project_vertex>', '#include <project_vertex>\nvWwPos = (modelMatrix * vec4(transformed, 1.0)).xyz; vWwN = normalize(mat3(modelMatrix) * objectNormal);');
        sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec3 vWwPos, vWwN;\nuniform float uLamp, uT, uW, uWashK, uPoolK, uX0, uX1;\nuniform vec3 uWash, uPoolCol;\nuniform vec4 uLamps[16];')
          .replace('#include <emissivemap_fragment>', WASH_GLSL);
      };
      m.customProgramCacheKey = () => 'ww-wash-3';
    }
    washPatch(mStucco, 1.6, 2.5); washPatch(mTrim, 1.7, 2.5); washPatch(mStone, 1.3, 2.5); washPatch(mStoneDk, 0.9, 2.5); washPatch(mBrick, 0.5, 3.0);
    mGlass.onBeforeCompile = (sh) => {
      Object.assign(sh.uniforms, { uLamp: LAMP, uGlowCol: { value: new THREE.Color(K.stored('#ffc98a', 1)) }, uIron: { value: new THREE.Color(K.stored('#3e3a33')) } });
      sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec2 vWwF;').replace('#include <begin_vertex>', '#include <begin_vertex>\nvWwF = uv;');
      sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec2 vWwF;\nuniform float uLamp;\nuniform vec3 uGlowCol, uIron;')
        .replace('#include <metalnessmap_fragment>', '#include <metalnessmap_fragment>\nif (vWwF.y > 0.5) { diffuseColor.rgb = uIron; metalnessFactor = 0.05; roughnessFactor = 0.9; }')
        .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance += uGlowCol * vWwF.x * uLamp;');
    };
    mGlass.customProgramCacheKey = () => 'ww-glass-2';
    mFoam.onBeforeCompile = (sh) => {
      sh.uniforms.uLamp = LAMP;
      sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nuniform float uLamp;')
        .replace('#include <color_fragment>', '#include <color_fragment>\ndiffuseColor.rgb *= 1.0 - 0.65 * uLamp;');
    };
    mFoam.customProgramCacheKey = () => 'ww-foam-2';

    const grp = B.done();
    grp.traverse((o) => { if (o.isMesh && o.material === mFoam) o.userData.noShadow = true; });

    // ---- what the model occupies, with the top of what stands there: api.occupy hands them to REBUILD_OCC, which the
    // tree skip (keepTree) and the pole rejection (the pole loop) read
    // (the river faces as hulls: the mill house with its projecting bays, the New Mill House along its pilasters; `pole` is the
    // margin a pole is rejected within, 3 m on the river faces, where a packed pole stands in the tailrace)
    const ehRing = R(ef, [[-0.5, -24.2], [25.1, -24.2], [25.1, 0.4], [-0.5, 0.4]]);
    const millOcc = R(fm, [[0, 0], [82.4, 0], [84.6, -0.1], [86.8, -0.6], [91.8, -0.6], [94.0, -0.8], [95.2, -1.3], [96.2, -2.1], [97.5, -4.0],
      [86.0, -10.9], [82.5, -12.8], [82.5, -20.6], [6.75, -20.6], [6.75, -16.5]]);
    const nmhOcc = R(fm, [[100.7, -50.6], [113.3, -43.3], [111.8, -40.6], [117.4, -37.4], [103.2, -12.8], [97.5, -4.0], [86.0, -10.9], [82.5, -12.8],
      [82.5, -20.3], [81.1, -20.3], [82.3, -22.2], [78.1, -24.6], [95.6, -53.6]]);
    const occupied = [
      { ring: millOcc, top: T + 9.2, pole: 3 }, { ring: promRing, top: T + 5.2, pole: 0.5 }, { ring: nmhOcc, top: T + 5.2, pole: 3 },
      { ring: mound, top: T + 0.5, pole: 1 }, { ring: pier, top: T + 8.0, pole: 1 }, { ring: ehRing, top: T + 16.7, pole: 1 },
      { ring: mpRing, top: api.ground(MP[0], MP[1]) + 7.5, pole: 1 }
    ];
    grp.userData.occupied = occupied;
    if (app && api.occupy) for (const o of occupied) api.occupy(o.ring, o.top, o.pole);
    return grp;

  }
});
