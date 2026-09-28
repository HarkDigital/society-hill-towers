// Round 161 rebuild (the Sep 25 design study, revision 2): Founder's Hall, Girard College (Thomas U. Walter, 1833 to 1847). A peripteral Corinthian
// temple of Chester County white marble: 8 columns on each end, 11 on each flank (34), on eleven risers of steps, a
// low gable roof with a pediment at both ends, the main door on the south.
// Dimensions from HABS PA-1731 (sheet 1, first floor plan: stylobate 162'-0" x 216'-6", cella 114'-4" x 169'-6";
// sheet 2, portico column detail: steps 6'-10", column with base and capital 66'-9", entablature 16'-8", 90'-3" to
// the top of the raking cornice at the corner, the rake about 12.2 degrees; written data: 55'-0" shafts, 8'-0"
// capitals, a 16' x 32' doorway under an elaborate hood, and on each flank four recessed window groups: a stair-hall
// stack of three windows at each end, and two classroom groups of four windows and a blind niche on the first and
// second storeys, with only two small floor-level windows a room on the third).
(function () {
  const FT = 0.3048;
  const CX = -2165.35, CZ = -3159.25;           // OSM footprint centroid (scene_wide 'Founder's Hall')
  const ANG = 9.0 * Math.PI / 180;              // the footprint's long edges run 9.0 degrees off north
  const C = Math.cos(ANG), S = Math.sin(ANG);
  const P = (u, v) => [CX + u * C - v * S, CZ + u * S + v * C];
  // stylobate 162' x 216'-6"; ten treads of about 0.35 m all round (185' x 239' at the foot of the steps)
  const HW = 162 * FT / 2, HL = 216.5 * FT / 2, TREAD = 0.35, NSTEP = 10;
  const SW = HW + NSTEP * TREAD, SLN = HL + NSTEP * TREAD;   // the outer step line
  const OW = SW + 1.5, OL = SLN + 1.5;
  const SKIP = [P(-OW, -OL), P(OW, -OL), P(OW, OL), P(-OW, OL)];

  RB.add({
    id: 'gc',
    name: "Founder's Hall, Girard College",
    center: [CX, CZ],
    skip: [SKIP],
    // [bearing of the eye from the target, horizontal distance, eye height, aim height]
    views: [[158, 270, 110, 6], [215, 140, 20, 14], [189, 85, 5, 17], [65, 70, 2, 4]],
    build(api) {
      const { THREE, K } = api;
      const f = K.frame(CX, CZ, ANG);
      const B = K.builder();

      // ---- materials (photo colours)
      const M = {
        col: K.mat('#cac6bc', { rough: 0.7 }),                 // columns, entablature, pediment, trim: white marble
        wall: K.mat('#cdbd98', { rough: 0.8 }),                // the cella's warmer honey-cream ashlar
        step: K.mat('#7f8488', { rough: 0.8 }),                // grey-blue marble treads
        riser: K.mat('#5b6065', { rough: 0.8 }),               // the risers, about 30% under the treads so each step draws a line
        roof: K.mat('#8a8e91', { rough: 0.55 }),               // stainless-steel roof over the marble one
        glass: K.glass(),
        door: K.mat('#2f3d33', { rough: 0.6 })                 // hunter-green doors
      };
      // the lawn apron: in the app, the app's own bare-ground meadow material (groundSurfMat, the non-vertex-colour
      // one, COLORS.ground 0x243818; the wide ground's vertex tint is 1 outside Fairmount), so the apron is the same
      // lawn; in the viewer a plain lawn colour
      let lawn = null;
      if (api.where === 'app' && api.lawn) lawn = api.lawn;
      const lawnBorrowed = !!lawn;
      if (!lawn) lawn = K.mat('#6f8f4a', { rough: 0.95 });

      // ---- ground and levels
      // The real hall stands on a level lawn with all eleven risers showing. The drawn ground here is a 1.2 m mound,
      // so the foot of the steps is set at the HIGHEST ground on and just outside the outer step line, and a lawn
      // apron runs level 1 m out from the bottom riser and then falls at 8% until it passes under the drawn ground.
      const gAt = (u, v) => { const p = f.p(u, v); return api.ground(p[0], p[1]); };
      const rectPts = (hw, hl, step) => {
        const out = [];
        for (const [u0, v0, u1, v1] of [[-hw, -hl, hw, -hl], [hw, -hl, hw, hl], [hw, hl, -hw, hl], [-hw, hl, -hw, -hl]]) {
          const n = Math.max(1, Math.round(Math.hypot(u1 - u0, v1 - v0) / step));
          for (let i = 0; i < n; i++) out.push([u0 + (u1 - u0) * i / n, v0 + (v1 - v0) * i / n]);
        }
        return out;
      };
      let gTop = -1e9, gMin = 1e9, nS = 0;
      const stepLine = [];
      for (const d of [0, 1.0]) for (const [u, v] of rectPts(SW + d, SLN + d, 2)) { const g = gAt(u, v); if (d === 0) stepLine.push(g); gTop = Math.max(gTop, g); gMin = Math.min(gMin, g); nS++; }
      for (let a = -1; a <= 1.001; a += 0.25) for (let b = -1; b <= 1.001; b += 0.25) gMin = Math.min(gMin, gAt(a * SW, b * SLN));
      const gBase = gTop + 0.03;                                  // the foot of the bottom riser
      const RISE = 6.833 * FT / (NSTEP + 1);                      // 6'-10" in eleven risers
      const yS = gBase + (NSTEP + 1) * RISE;                      // stylobate top
      const yF = gMin - 1.5;                                      // foundation
      if (api.where === 'app') {
        stepLine.sort((a, b) => a - b);
        api.log('GC ground: ' + nS + ' samples on and 1 m outside the step line, max ' + gTop.toFixed(2) + ', step-line median ' + stepLine[stepLine.length >> 1].toFixed(2) + ', min ' + gMin.toFixed(2) + '; foot of steps ' + gBase.toFixed(2) + ', stylobate ' + yS.toFixed(2) + '; lawn material ' + (lawnBorrowed ? 'borrowed from the app' : 'kit'));
      }

      // local-geometry helpers: build in (x = u, y, z = v), then place into the world
      const L = (g) => f.place(g, 0);
      const W3 = (u, v, y) => { const p = f.p(u, v); return [p[0], y, p[1]]; };
      const boxL = (u, y, v, du, dy, dv, rotY) => { const g = new THREE.BoxGeometry(du, dy, dv); if (rotY) g.rotateY(rotY); g.translate(u, y, v); return L(g); };
      const slab = (u0, u1, v0, v1, y0, y1) => K.slabF(f, Math.min(u0, u1), Math.max(u0, u1), Math.min(v0, v1), Math.max(v0, v1), y0, y1);
      const rectRing = (hw, hl) => [f.p(-hw, -hl), f.p(hw, -hl), f.p(hw, hl), f.p(-hw, hl)];
      // face normals (flat shading) baked into the geometry, so faceted parts share the smooth marble material
      const flat = (g) => { const q = g.index ? g.toNonIndexed() : g; q.deleteAttribute('normal'); q.computeVertexNormals(); return q; };
      // extrude one or more outlines drawn in the (u, y) plane along v from v0 to v1
      const extrudeUY = (outlines, v0, v1, holes) => {
        const shapes = outlines.map((pts) => {
          const sh = new THREE.Shape(pts.map((p) => new THREE.Vector2(p[0], p[1])));
          if (holes) for (const h of holes) sh.holes.push(new THREE.Path(h.map((p) => new THREE.Vector2(p[0], p[1]))));
          return sh;
        });
        const g = new THREE.ExtrudeGeometry(shapes, { depth: v1 - v0, bevelEnabled: false, steps: 1 });
        g.translate(0, 0, v0);
        return L(g);
      };

      // ---- stylobate and the steps all round: treads and risers as separate faces, the risers a shade darker
      const INS = W3(0, 0, yF - 30);
      const yk = (k) => yS - k * RISE;
      B.add(M.step, K.quad(W3(-HW, -HL, yS), W3(HW, -HL, yS), W3(HW, HL, yS), W3(-HW, HL, yS), INS));
      for (let k = 0; k <= NSTEP; k++) {
        const ho = HW + k * TREAD, lo = HL + k * TREAD;
        if (k > 0) {
          const hi = ho - TREAD, li = lo - TREAD, y = yk(k);
          B.add(M.step, K.quad(W3(-ho, -lo, y), W3(ho, -lo, y), W3(hi, -li, y), W3(-hi, -li, y), INS));
          B.add(M.step, K.quad(W3(ho, -lo, y), W3(ho, lo, y), W3(hi, li, y), W3(hi, -li, y), INS));
          B.add(M.step, K.quad(W3(ho, lo, y), W3(-ho, lo, y), W3(-hi, li, y), W3(hi, li, y), INS));
          B.add(M.step, K.quad(W3(-ho, lo, y), W3(-ho, -lo, y), W3(-hi, -li, y), W3(-hi, li, y), INS));
        }
        const yt = yk(k), yb = k === NSTEP ? yF : yk(k + 1);
        for (const [a, b] of [[[-ho, -lo], [ho, -lo]], [[ho, -lo], [ho, lo]], [[ho, lo], [-ho, lo]], [[-ho, lo], [-ho, -lo]]]) {
          B.add(M.riser, K.quad(W3(a[0], a[1], yb), W3(b[0], b[1], yb), W3(b[0], b[1], yt), W3(a[0], a[1], yt), INS));
        }
      }

      // ---- the peristyle: 8 x 11 Corinthian columns. HABS: 66'-9" overall, a 3'-9" Attic base standing straight on
      // the top step (no plinth), a 55'-0" fluted shaft 6 ft across, an 8'-0" capital
      const CH = 66.75 * FT;                              // stylobate to the top of the abacus (20.35 m)
      const yA = yS + CH;
      const CU = HW - 4.5 * FT, CV = HL - 4.5 * FT;       // column axes; the lower torus stops 0.2 m short of the edge
      const Y_SH0 = 1.14, Y_SH1 = 17.9, Y_BELL = 19.95;   // base top, shaft top (base + 55 ft), bell top under the abacus
      const baseL = new THREE.LatheGeometry([[1.12, 0.0], [1.17, 0.12], [1.12, 0.3], [0.99, 0.36], [0.96, 0.46], [1.06, 0.56], [1.07, 0.64], [0.99, 0.76], [0.95, 0.82], [0.95, 0.9], [0.915, Y_SH0]].map((p) => new THREE.Vector2(p[0], p[1])), 16);
      const bellL = new THREE.LatheGeometry([[0.78, Y_SH1], [0.85, Y_SH1 + 0.05], [0.85, Y_SH1 + 0.2], [0.8, Y_SH1 + 0.24], [1.02, Y_BELL]].map((p) => new THREE.Vector2(p[0], p[1])), 16);
      // the fluted shaft: a flat-shaded 24-sided frustum pair with entasis (HABS draws 24 flutes)
      const sh1 = new THREE.CylinderGeometry(0.905, 0.915, 6.5 - Y_SH0, 24, 1, true); sh1.translate(0, (Y_SH0 + 6.5) / 2, 0);
      const sh2 = new THREE.CylinderGeometry(0.78, 0.905, Y_SH1 - 6.5, 24, 1, true); sh2.translate(0, (6.5 + Y_SH1) / 2, 0);
      const shaft1 = flat(sh1), shaft2 = flat(sh2);
      const leaf1 = flat(new THREE.CylinderGeometry(1.2, 0.86, 0.8, 8)); leaf1.translate(0, Y_SH1 + 0.24 + 0.4, 0);
      const leaf2g = new THREE.CylinderGeometry(1.42, 0.98, 0.8, 8); leaf2g.rotateY(Math.PI / 8); leaf2g.translate(0, Y_SH1 + 0.94 + 0.4, 0);
      const leaf2 = flat(leaf2g);
      const column = (u, v) => {
        for (const src of [baseL, bellL, shaft1, shaft2, leaf1, leaf2]) { const g = src.clone(); g.translate(u, yS, v); B.add(M.col, L(g)); }
        for (const [a, b] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) B.add(M.col, flat(boxL(u + a * 1.12, yS + 19.62, v + b * 1.12, 0.62, 0.66, 0.5, a * b > 0 ? Math.PI / 4 : -Math.PI / 4)));  // volutes
        B.add(M.col, boxL(u, yA - 0.2, v, 3.2, 0.4, 3.2));                                // abacus (10.6 ft)
      };
      const cols = [];
      for (let i = 0; i < 8; i++) { const u = -CU + i * 2 * CU / 7; cols.push([u, -CV]); cols.push([u, CV]); }
      for (let j = 1; j < 10; j++) { const v = -CV + j * 2 * CV / 10; cols.push([-CU, v]); cols.push([CU, v]); }
      for (const [u, v] of cols) column(u, v);

      // ---- entablature (HABS: 16'-8" with the raking cornice). Architrave as a ring so the peristyle ceiling shows.
      const aU = CU + 0.8, aV = CV + 0.8;                 // architrave / frieze face
      const ring = (d, y0, y1, inner) => {
        const out = rectRing(aU + d, aV + d);
        if (inner == null) return K.prism(out, y0, y1);
        return K.prism(out, y0, y1, [rectRing(CU - inner, CV - inner)]);
      };
      B.add(M.col, ring(-0.06, yA, yA + 0.55, 0.95));      // three fasciae
      B.add(M.col, ring(0.0, yA + 0.55, yA + 1.1, 0.95));
      B.add(M.col, ring(0.06, yA + 1.1, yA + 1.5, 0.95));
      B.add(M.col, ring(0.18, yA + 1.5, yA + 1.68, 0.95)); // crowning moulding
      B.add(M.col, ring(0.0, yA + 1.68, yA + 2.87));       // frieze (solid: its underside is the peristyle ceiling)
      B.add(M.col, ring(0.18, yA + 2.87, yA + 3.05));      // bed moulding
      B.add(M.col, ring(0.12, yA + 3.05, yA + 3.45));      // dentil backing
      B.add(M.col, ring(0.55, yA + 3.45, yA + 3.62));      // ovolo
      B.add(M.col, ring(1.05, yA + 3.62, yA + 4.05));      // corona
      B.add(M.col, ring(1.15, yA + 4.05, yA + 4.35));      // cyma
      const yC = yA + 4.35;
      // dentils on the horizontal cornice only (HABS sheet 2 shows none on the rake)
      const DP = 0.6, DW = 0.42;
      const dentRow = (len, place) => { const n = Math.floor(len / DP); for (let i = 0; i < n; i++) place(-len / 2 + (i + 0.5) * len / n); };
      dentRow(2 * (aU + 0.3), (u) => { B.add(M.col, boxL(u, yA + 3.25, -(aV + 0.3), DW, 0.4, 0.36)); B.add(M.col, boxL(u, yA + 3.25, aV + 0.3, DW, 0.4, 0.36)); });
      dentRow(2 * (aV + 0.3), (v) => { B.add(M.col, boxL(-(aU + 0.3), yA + 3.25, v, 0.36, 0.4, DW)); B.add(M.col, boxL(aU + 0.3, yA + 3.25, v, 0.36, 0.4, DW)); });

      // ---- the cella: honey-cream ashlar up to the peristyle ceiling, corner antae. The flank faces carry four
      // recessed window groups each (HABS written data B.3 and B.5.b), so the wall is a core set back RD with a skin
      // of ashlar round the recesses.
      const WU = 114.33 * FT / 2, WV = 169.5 * FT / 2, RD = 0.3;
      const yW1 = yA + 1.7;
      const G0 = 0.7, G1 = 19.1;                          // the recesses run from the base course to under the capital band
      const GRP = [[20.8, 23.1, 'stair'], [3.025, 15.655, 'room']];
      const groups = [];
      for (const [a, b, t] of GRP) { groups.push([a, b, t, 1]); groups.push([-b, -a, t, -1]); }
      groups.sort((p, q) => p[0] - q[0]);
      B.add(M.wall, slab(-(WU - RD), WU - RD, -WV, WV, yS - 0.1, yW1));
      for (const s of [1, -1]) {
        const u0 = s * (WU - RD), u1 = s * WU;
        let v = -WV;
        for (const [a, b] of groups) { B.add(M.wall, slab(u0, u1, v, a, yS - 0.1, yW1)); B.add(M.wall, slab(u0, u1, a, b, yS + G1, yW1)); v = b; }
        B.add(M.wall, slab(u0, u1, v, WV, yS - 0.1, yW1));
      }
      B.add(M.col, slab(-WU - 0.12, WU + 0.12, -WV - 0.12, WV + 0.12, yS - 0.1, yS + G0));    // base course (the recesses' floor)
      B.add(M.col, slab(-WU - 0.08, WU + 0.08, -WV - 0.08, WV + 0.08, yA - 0.5, yA + 0.1));      // band at the capitals
      for (const [a, b] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) {
        const u = a * (WU + 0.3 - 1.15), v = b * (WV + 0.3 - 1.15);
        B.add(M.col, boxL(u, yS + 0.3, v, 2.6, 0.6, 2.6));                     // anta base
        B.add(M.col, boxL(u, (yS + 0.6 + yA - 1.2) / 2, v, 2.3, yA - 1.2 - yS - 0.6, 2.3));
        B.add(M.col, boxL(u, yA - 0.6, v, 2.6, 1.2, 2.6));                     // anta capital
      }
      // ceiling beams from the architrave to the cella at every column
      for (const [u, v] of cols) {
        if (Math.abs(Math.abs(u) - CU) < 0.1 && Math.abs(Math.abs(v) - CV) < 0.1) continue;
        if (Math.abs(Math.abs(v) - CV) < 0.1) { const v0 = Math.sign(v) * WV, v1 = Math.sign(v) * (CV - 0.95); B.add(M.col, boxL(u, yA + 1.28, (v0 + v1) / 2, 0.8, 0.8, Math.abs(v1 - v0))); }
        else { const u0 = Math.sign(u) * WU, u1 = Math.sign(u) * (CU - 0.95); B.add(M.col, boxL((u0 + u1) / 2, yA + 1.28, v, Math.abs(u1 - u0), 0.8, 0.8)); }
      }

      // ---- the great doors, south (main) and north: 16 ft x 32 ft in a massive marble frame under a projecting hood
      // carried on two consoles
      const DWd = 16 * FT, DH = 32 * FT, JW = 1.2;
      for (const s of [1, -1]) {
        const vf = s * WV;
        const IN = W3(0, vf - s * 3, yS + 4);
        const q = (u, y, dv) => W3(u, vf + s * dv, y);
        B.add(M.door, K.quad(q(-DWd / 2, yS, 0.15), q(DWd / 2, yS, 0.15), q(DWd / 2, yS + DH, 0.15), q(-DWd / 2, yS + DH, 0.15), IN));
        for (const a of [-1, 1]) {
          B.add(M.col, boxL(a * (DWd / 2 + JW / 2), yS + (DH + 1.1) / 2, vf + s * 0.3, JW, DH + 1.1, 0.6));                 // jambs
          B.add(M.col, boxL(a * (DWd / 2 + JW + 0.15), yS + DH + 0.55, vf + s * 0.28, 0.3, 1.1, 0.56));                   // ears
          B.add(M.col, boxL(a * (DWd / 2 + JW - 0.25), yS + DH + 1.1 + 0.6, vf + s * 0.45, 0.5, 1.2, 0.9));              // consoles
          B.add(M.door, boxL(a * DWd / 4, yS + DH / 2, vf + s * 0.18, 0.08, DH, 0.06));                                   // leaf divisions
        }
        B.add(M.door, boxL(0, yS + DH * 0.62, vf + s * 0.18, DWd, 0.1, 0.06));                                             // panel rail
        B.add(M.col, boxL(0, yS + DH + 0.55, vf + s * 0.3, DWd + 2 * JW, 1.1, 0.6));                                       // lintel
        B.add(M.col, boxL(0, yS + DH + 1.1 + 0.6, vf + s * 0.2, DWd + 2 * JW - 1.0, 1.2, 0.4));                           // frieze panel
        B.add(M.col, boxL(0, yS + DH + 2.3 + 0.3, vf + s * 0.6, DWd + 2 * JW + 0.8, 0.6, 1.2));                           // hood (projects 1.2 m)
        B.add(M.col, boxL(0, yS + DH + 2.9 + 0.1, vf + s * 0.65, DWd + 2 * JW + 1.1, 0.2, 1.3));                          // hood cap
      }

      // ---- flank windows (HABS B.3, B.5.b and the plan): per flank, a stair-hall stack at each end (three windows over
      // one another, framed by thin pilasters) and two classroom groups of five bays between pilaster strips: four
      // casements and, in the bay next to the stair hall, a blind niche, on the first and second storeys (the second's
      // run to the floor behind iron balustrades); on the third storey only two small windows at floor level a room.
      const WW = 1.5;
      const ROOM_BAYS = [4.4, 6.87, 9.34, 11.81, 14.28];   // 2.47 m pitch; 14.28 is the blind niche
      for (const s of [1, -1]) {
        const uR = s * (WU - RD);                          // the recessed face
        const IN = (v, y) => W3(s * (WU - 3), v, y);
        const pr = (v0, v1, y0, y1, d0, d1, mat) => B.add(mat || M.col, slab(uR + s * d0, uR + s * d1, v0, v1, yS + y0, yS + y1));
        const glass = (v, w, y0, y1) => { const u = uR + s * 0.1; B.add(M.glass, K.quad(W3(u, v - w / 2, yS + y0), W3(u, v + w / 2, yS + y0), W3(u, v + w / 2, yS + y1), W3(u, v - w / 2, yS + y1), IN(v, yS + (y0 + y1) / 2))); };
        const surround = (v, w, y0, y1) => { pr(v - w / 2 - 0.15, v + w / 2 + 0.15, y0 - 0.18, y0, 0, 0.25); pr(v - w / 2 - 0.15, v + w / 2 + 0.15, y1, y1 + 0.3, 0, 0.25); };
        const casement = (v, w, y0, y1, bal) => {
          glass(v, w, y0, y1);
          pr(v - 0.045, v + 0.045, y0, y1, 0.11, 0.19);                                          // mullion
          const yt = y0 + (y1 - y0) * 0.62; pr(v - w / 2, v + w / 2, yt - 0.05, yt + 0.05, 0.11, 0.19);   // transom
          surround(v, w, y0, y1);
          if (bal) pr(v - w / 2 - 0.1, v + w / 2 + 0.1, y0, y0 + 0.8, 0.18, 0.3);                  // iron balustrade
        };
        const pil = (v, y0, y1) => pr(v - 0.14, v + 0.14, y0, y1, 0, 0.18);
        for (const sv of [1, -1]) {
          // stair-hall stack
          const vs = sv * 21.95;
          pil(sv * 20.94, G0, G1); pil(sv * 22.96, G0, G1);
          casement(vs, WW, 1.0, 5.2); casement(vs, WW, 8.4, 12.6, true); casement(vs, WW, 15.6, 18.6);
          // classroom group
          for (let i = 0; i <= 5; i++) pil(sv * (3.165 + i * 2.47), G0, G1);
          for (const b of ROOM_BAYS) {
            const v = sv * b;
            if (b === 14.28) { surround(v, WW, 1.0, 5.2); surround(v, WW, 8.4, 12.6); continue; }  // blind niche
            casement(v, WW, 1.0, 5.2); casement(v, WW, 8.4, 12.6, true);
            if (b === 6.87 || b === 11.81) { glass(v, 1.0, 15.4, 16.3); surround(v, 1.0, 15.4, 16.3); }
          }
        }
      }

      // ---- the roof: a low gable (HABS sheet 2's rake, about 12.2 degrees) with a pediment at each end
      const T = Math.tan(12.2 * Math.PI / 180);
      const RU = aU + 1.15;                                // eave at the cyma face
      const RH = RU * T;                                   // ridge rise over yC
      const roofEnd = aV - 0.3;
      B.add(M.roof, extrudeUY([[[-RU, yC - 0.4], [RU, yC - 0.4], [RU, yC], [0, yC + RH], [-RU, yC]]], -roofEnd, roofEnd));
      // standing-seam ribs and a ridge cap
      const SLr = Math.hypot(RU, RH), SA = Math.atan2(RH, RU);
      for (let v = -roofEnd + 0.9; v < roofEnd; v += 1.8) for (const s of [-1, 1]) {
        const g = new THREE.BoxGeometry(SLr, 0.1, 0.09); g.rotateZ(s * -SA); g.translate(s * RU / 2, yC + RH / 2 + 0.05, v); B.add(M.roof, L(g));
      }
      B.add(M.roof, boxL(0, yC + RH + 0.05, 0, 0.5, 0.25, 2 * roofEnd));
      // pediments: a recessed tympanum framed by the raking cornice, whose sima carries a band of upright palmettes
      // ("carved bands of highly abstracted acanthus-type leaves", HABS B.6; drawn on sheet 2)
      const RK = 1.45, TOP = 0.76;                         // raking cornice depth and its rise over the roof plane (sheet 2: the
      // rake's top at the corner stands 0.76 m over the horizontal cornice, 16'-8" over the abacus, 90'-3" over the lawn)
      const ti = RU - (RK - TOP) / T;                      // where the tympanum's rake meets the horizontal cornice
      const PAL = [[-0.2, 0], [0.2, 0], [0.2, 0.3], [0, 0.6], [-0.2, 0.3]];
      for (const s of [1, -1]) {
        const vf = s * aV;
        const outer = [[-RU, yC - 0.05], [RU, yC - 0.05], [RU, yC + TOP], [0, yC + RH + TOP], [-RU, yC + TOP]];
        const inner = [[-ti, yC], [0, yC + RH + TOP - RK], [ti, yC]];
        const v0 = s > 0 ? vf - 0.6 : -(aV + 1.15), v1 = s > 0 ? aV + 1.15 : -(aV - 0.6);
        B.add(M.col, extrudeUY([outer], v0, v1, [inner]));
        B.add(M.col, extrudeUY([[[-ti, yC], [ti, yC], [0, yC + RH + TOP - RK]]], s > 0 ? vf - 1.2 : -aV, s > 0 ? aV : -(aV - 1.2)));
        // a bed moulding under the raking cornice
        for (const a of [-1, 1]) {
          const len = Math.hypot(ti, RH + TOP - RK), g = new THREE.BoxGeometry(len, 0.35, 0.4);
          g.rotateZ(a * -Math.atan2(RH + TOP - RK, ti)); g.translate(a * ti / 2, yC + (RH + TOP - RK) / 2 - 0.1, vf + s * 0.15);
          B.add(M.col, L(g));
        }
        // the palmette band: upright blades every 0.9 m on the sima face, their tips 0.15 m over the rake
        const blades = [];
        for (const a of [-1, 1]) for (let x = 0.6; x < RU - 0.45; x += 0.9) {
          const u = a * (RU - x), yb = yC + TOP + x * T - 0.45;
          blades.push(PAL.map((p) => [u + p[0], yb + p[1]]));
        }
        const fv = aV + 1.15;
        B.add(M.col, extrudeUY(blades, s > 0 ? fv - 0.07 : -(fv + 0.05), s > 0 ? fv + 0.05 : -(fv - 0.07)));
      }

      // ---- the lawn apron (app only): level 1 m out from the bottom riser at the foot of the steps, then an 8% fall
      // until it passes under the drawn ground; its inner edge tucks under the bottom tread
      if (api.where === 'app') {
        const DS = [-0.3, 1.0, 2.5, 4.5, 7, 10, 13, 16, 19.5];
        const NU = 18, NV = 24;
        const perim = (hw, hl) => {
          const out = [];
          for (let i = 0; i < NU; i++) out.push([-hw + 2 * hw * i / NU, -hl]);
          for (let i = 0; i < NV; i++) out.push([hw, -hl + 2 * hl * i / NV]);
          for (let i = 0; i < NU; i++) out.push([hw - 2 * hw * i / NU, hl]);
          for (let i = 0; i < NV; i++) out.push([-hw, hl - 2 * hl * i / NV]);
          return out;
        };
        const pos = [], idx = [];
        const NP = 2 * (NU + NV);
        let above = 0, buried = 0;
        DS.forEach((d, r) => {
          for (const [u, v] of perim(SW + d, SLN + d)) {
            const g = gAt(u, v);
            let h = gBase - 0.08 * Math.max(0, d - 1.0);
            if (r === DS.length - 1) h = Math.min(h, g - 0.3);
            if (r > 0 && r < DS.length - 1) { if (h > g + 0.02) above++; else buried++; }
            const w = W3(u, v, h); pos.push(w[0], w[1], w[2]);
          }
        });
        for (let r = 0; r < DS.length - 1; r++) for (let j = 0; j < NP; j++) {
          const a = r * NP + j, b = r * NP + (j + 1) % NP, c = (r + 1) * NP + (j + 1) % NP, e = (r + 1) * NP + j;
          idx.push(a, b, c, a, c, e);
        }
        const ag = new THREE.BufferGeometry();
        ag.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
        // face the triangles up
        const pa = new THREE.Vector3(pos[0], pos[1], pos[2]), pb = new THREE.Vector3(pos[3], pos[4], pos[5]), pc = new THREE.Vector3(pos[(NP + 1) * 3], pos[(NP + 1) * 3 + 1], pos[(NP + 1) * 3 + 2]);
        if (pb.clone().sub(pa).cross(pc.clone().sub(pa)).y < 0) for (let i = 0; i < idx.length; i += 3) { const t = idx[i + 1]; idx[i + 1] = idx[i + 2]; idx[i + 2] = t; }
        ag.setIndex(idx);
        ag.computeVertexNormals();
        B.add(lawn, ag);
        api.log('GC apron: ' + above + ' vertices stand over the drawn ground, ' + buried + ' pass under it');
      }

      const grp = B.done();
      // the apron neither casts nor receives shadows: the app's wide ground receives none, so a shadowed apron would
      // show as a dark patch ('Rebuilding the landmarks' sets receiveShadow on everything, so pin it off here)
      grp.traverse((o) => { if (o.isMesh && o.material === lawn) { o.userData.noShadow = true; Object.defineProperty(o, 'receiveShadow', { get() { return false; }, set() {}, configurable: true }); } });
      return grp;
    }
  });
})();
