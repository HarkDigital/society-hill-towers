// Round 190 rebuild: Glory Beer Bar & Kitchen, 126 Chestnut St, Old City (Mike: "I want City hall and Glory Beer Bar and
// Kitchen to be totally revamped"; and the look "isn't where I want it to be": photographic, and cheap to draw).
// Research:
//   Philadelphia Historical Commission, Old City Historic District inventory (Dec 2003): "126: 5-story, 4-bay, brick,
//     Greek Revival building with storefront", built 1853 as a store for James A. Brown; squared granite storefront
//     pilasters; a second storey of narrow engaged granite columns with pointed-arch granite window surrounds and a granite
//     cornice over it, paired multi-light steel casements over metal panels; floors 3 to 5 replacement 1/1 windows; a
//     corbelled brick cornice with brick dentils; a stucco penthouse; a concrete and tile stoop (now black wrought iron).
//   Sanborn 1916 vol. 1 plate 32 (LoC via Commons): about 27.5 ft wide, 5 storeys and a basement, 60 ft (18.3 m), the lot
//     running back to Ionic St. LiDAR: P90 roof 19.5 m, the city footprint's max 23.7 m (the stair bulkhead).
//   The OPA address point for 126 (101.01, -284.81) lies in scene building 2541 (h 19.5, generic), area-weighted centroid
//     (99.03, -288.41): the old builder stood on 120 (2806), two lots east, from Round 10b's pro-rated house numbers.
//   Photos (viewed only, none shipped): the Bright MLS listing's street view of 126 from the south sidewalk looking west
//     (the granite two-storey front, the tall near-black doors, the paired round columns and steel casements, the Juliet
//     railing in the east bay, the orange-red brick floors, the corbelled cornice, the faded blue sign box high on the
//     east edge, the white GLORY blade sign on a black bracket, two caged lanterns, the raised cafe with three steps and
//     black wrought-iron railings, bistro tables with galvanized chairs); Wanderlog's close-up of both GLORY signs, a pier,
//     its capital and a lantern; gloryphilly.com's stoop railing (a quatrefoil band under the top rail), the bar (down the
//     west wall, a brick mural by the doors: GLORY / BEER BAR & KITCHEN / THIS MUST BE THE PLACE) and the room upstairs
//     (string lights, a globe cluster, a mantel, farmhouse tables). Hours (Google, Oct 2026): Mon to Wed 4 PM to 2 AM,
//     Thu to Sun 12 PM to 2 AM.
// The model: one merged mesh per level of detail on one facade material (rebuilds draw through it, api.glory), every
// pane, muntin, door panel, joint and moulding in the generated elevations (fetch_glory_art.py, bake_glory_art.py), real
// triangles only where the silhouette and the parallax show: the cut and recessed openings, the piers and their caps,
// the engaged columns, both cornices, the sills, the stoop and its steps, the railings, the lanterns, the signs' bracket,
// the old sign box and the cafe's tables and chairs. The near mesh switches to a far one of a few dozen triangles past
// 200 m (the app's gloryStep). Everything is in the facade's own frame: u east along the front from its west corner,
// v south into the lot, y up from the sidewalk.
(function () {
  const A = [98.51, -307.95], B = [106.97, -306.47];   // the front's west and east corners on the lot line (scene 2541)
  const LOT = [[97.23, -265.88], [91.29, -266.94], [98.51, -307.95], [106.97, -306.47], [106.74, -305.21], [102.6, -281.43], [100.02, -281.87]];
  const CX = 102.74, CZ = -307.21;                     // the front's middle
  const FW = 8.59;                                     // the front's width (the elevations span it)
  const EH = 9.3;                                      // each elevation's height
  const DEPTH = 25.42, REAR = [5.94, 41.6];            // the front block's depth; the rear range's east side and back
  const TOP = 18.6, REAR_TOP = 15.4;                   // the parapet (Sanborn's 60 ft) and the four-storey rear range
  // the research's nominal numbers (bake_glory_art.py NOMINAL), for a page without the art's measures
  const NOMINAL = {
    lower: { bays: [[0.65, 2.09], [2.59, 4.05], [4.51, 6.0], [6.49, 7.94]], doorTop: 4.04, doorFoot: 0.44,
      arcade: [[0.67, 2.15], [2.63, 4.09], [4.49, 5.96], [6.43, 7.92]], spring: 7.77, crown: 8.32, sill2: 4.92,
      cols: [2.27, 2.51, 4.19, 4.39, 6.08, 6.32], colR: 0.11, cornice: [8.6, 9.3], rect: [0, 0.14, 0.49, 0.85] },
    upper: { win: [0.69, 3.49, 6.34].flatMap((y) => [[0.75, 1.81], [2.72, 3.81], [4.94, 6.0], [6.92, 7.95]].map((u) => [u[0], u[1], y, y + 1.83])), rect: [0.5, 0.14, 0.49, 0.85] },
  };
  // the swatches' order in the atlas (bake_glory_art.py SWATCHES)
  const SW = { granite: 0, brick: 1, concrete: 2, iron: 3, rustblue: 4, glow: 5, roof: 6 };
  // aGl's first byte: how the facade shader colours a face
  const M_ELEV = 0, M_SWATCH = 1, M_GLOW = 2, M_CAFE = 3;
  // the signs' canvas (the app's gloryCanvas): [u0, v0, du, dv] in texture uv
  const CV = { panel: [0, 0.5, 0.5, 0.5], plaque: [0, 0.25, 0.25, 0.25], menu: [0.25, 0, 0.1875, 0.5], white: [0.4375, 0.25, 0.03125, 0.25], dark: [0.46875, 0.25, 0.03125, 0.25] };

  RB.add({
    id: 'glory',
    name: 'Glory Beer Bar & Kitchen',
    center: [CX, CZ],
    aim: [CX, CZ],
    skip: [],       // the core's footprint (2541) is held back by REALISM_NEAR in the app, as the custom landmarks are
    core: LOT,
    real: true,     // the realistic look's alone: ?real=0 and ?glory=0 keep the old builder on 120 and the generic 126
    // [bearing of the eye from the target, horizontal distance, eye height, aim height]
    views: [[350, 15, 1.7, 7], [80, 14, 1.9, 9], [20, 60, 10, 7], [10, 140, 110, 8]],
    build(api) {
      const THREE = api.THREE, K = api.K;
      const G = api.glory || null;                      // the app's facade and signs materials, hours and LOD (absent in Node's stub)
      const ART = G && G.art ? G.art : null;
      // the measures come from the photographs as the camera saw them, looking south from the street: the image's left is the
      // EAST end. Mirrored here into the frame's u (east from the west corner), every list ordered from the west
      const mir = (r) => [+(FW - r[1]).toFixed(3), +(FW - r[0]).toFixed(3)];
      const L0 = ART ? ART.lower : NOMINAL.lower, U0 = ART ? ART.upper : NOMINAL.upper;
      const LO = Object.assign({}, L0, { bays: L0.bays.map(mir).reverse(), arcade: L0.arcade.map(mir).reverse(), cols: L0.cols.map((c) => +(FW - c).toFixed(3)).reverse() });
      const UP = Object.assign({}, U0, { win: U0.win.map((w) => mir(w).concat([w[2], w[3]])) });
      const f = K.frameFromEdge(A, B);
      const ux = f.ux, uz = f.uz, vx = f.vx, vz = f.vz;
      { const p = f.p(1, 1), q = [p[0], p[1]]; if (!pointIn(q[0], q[1], LOT)) throw new Error('glory: the frame\'s v does not run into the lot'); }
      // the sidewalk at the front: the ground plus the walk's own lift, so the image's foot meets the paving
      const Y0 = api.ground(CX - vx * 0.2, CZ - vz * 0.2) + (api.where === 'app' ? 0.2 : 0);
      const W = (u, v, y) => [A[0] + u * ux + v * vx, Y0 + y, A[1] + u * uz + v * vz];
      const NU = [ux, 0, uz], NV = [vx, 0, vz], NF = [-vx, 0, -vz], NY = [0, 1, 0], ND = [0, -1, 0], NW_ = [-ux, 0, -uz];
      const nrm = (u, v, y) => { const l = Math.hypot(u, v, y) || 1; return [(u * ux + v * vx) / l, y / l, (u * uz + v * vz) / l]; };
      // the elevations' uv at (u, y) on the front: the ground floor and second storey below EH, the brick storeys above
      const evL = (u, y) => [LO.rect[0] + LO.rect[2] * Math.min(Math.max(1 - u / FW, 0), 1), LO.rect[1] + LO.rect[3] * Math.min(Math.max(y / EH, 0), 1)];
      const evU = (u, y) => [UP.rect[0] + UP.rect[2] * Math.min(Math.max(1 - u / FW, 0), 1), UP.rect[1] + UP.rect[3] * Math.min(Math.max((y - EH) / EH, 0), 1)];
      // which elevation by the face's own middle (ym), so a face reaching the line between them (the granite cornice's top,
      // a lower cell's head at 9.3 m) keeps every corner on its own image: a corner taken from the other one interpolated
      // the face's uv across the atlas, through the swatches (a striped band under the cornice, the second render)
      const ev = (u, y, ym) => ((ym == null ? y : ym) < EH ? evL(u, y) : evU(u, y));

      // ---- an indexed triangle soup: position, normal, uv (Float32), aGl (4 bytes, normalized): every stream a multiple of
      // four bytes (Round 158)
      function Soup() {
        const P = [], N = [], T = [], Gl = [], I = [];
        let n = 0;
        const push = (p, nn, t, g) => { P.push(p[0], p[1], p[2]); N.push(nn[0], nn[1], nn[2]); T.push(t[0], t[1]); Gl.push(g[0], g[1], g[2] || 0, g[3] || 0); return n++; };
        const facing = (a, b, c, nn) => { const e1 = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], e2 = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
          return (e1[1] * e2[2] - e1[2] * e2[1]) * nn[0] + (e1[2] * e2[0] - e1[0] * e2[2]) * nn[1] + (e1[0] * e2[1] - e1[1] * e2[0]) * nn[2]; };
        const S = {
          tri(a, b, c, nn, ta, tb, tc, g) {
            const z = [0, 0];
            if (facing(a, b, c, nn) < 0) { [b, c] = [c, b]; [tb, tc] = [tc, tb]; }
            I.push(push(a, nn, ta || z, g), push(b, nn, tb || z, g), push(c, nn, tc || z, g));
          },
          // a quad a b c d round its edge, wound to face nn
          quad(a, b, c, d, nn, t, g) {
            t = t || [[0, 0], [0, 0], [0, 0], [0, 0]];
            if (facing(a, b, c, nn) < 0) { [a, b, c, d] = [d, c, b, a]; t = [t[3], t[2], t[1], t[0]]; }
            const i = push(a, nn, t[0], g), j = push(b, nn, t[1], g), k = push(c, nn, t[2], g), l = push(d, nn, t[3], g);
            I.push(i, j, k, i, k, l);
          },
          // a face of the front (normal nn) in the frame's (u, y) at depth v, its uv from the elevations
          fq(u0, u1, y0, y1, v, nn, g) {
            const m = (y0 + y1) / 2;
            S.quad(W(u0, v, y0), W(u1, v, y0), W(u1, v, y1), W(u0, v, y1), nn || NF, [ev(u0, y0, m), ev(u1, y0, m), ev(u1, y1, m), ev(u0, y1, m)], g || [M_ELEV, 0]);
          },
          // a box [u0, u1] x [v0, v1] x [y0, y1]: its front (-v) from the elevations, every other face a swatch; skip
          // lists faces to leave out ('f', 'b', 'w', 'e', 't', 'd')
          box(u0, u1, v0, v1, y0, y1, sw, skip, frontG) {
            const s = skip || '', gs = [M_SWATCH, SW[sw]];
            if (s.indexOf('f') < 0) S.fq(u0, u1, y0, y1, v0, NF, frontG);
            if (s.indexOf('b') < 0) S.quad(W(u0, v1, y0), W(u1, v1, y0), W(u1, v1, y1), W(u0, v1, y1), NV, null, gs);
            if (s.indexOf('w') < 0) S.quad(W(u0, v0, y0), W(u0, v1, y0), W(u0, v1, y1), W(u0, v0, y1), NW_, null, gs);
            if (s.indexOf('e') < 0) S.quad(W(u1, v0, y0), W(u1, v1, y0), W(u1, v1, y1), W(u1, v0, y1), NU, null, gs);
            if (s.indexOf('t') < 0) S.quad(W(u0, v0, y1), W(u1, v0, y1), W(u1, v1, y1), W(u0, v1, y1), NY, null, gs);
            if (s.indexOf('d') < 0) S.quad(W(u0, v0, y0), W(u1, v0, y0), W(u1, v1, y0), W(u0, v1, y0), ND, null, gs);
          },
          // a box in any orientation: centre c (local u, v, y), half sizes h, its u axis turned a about y, a swatch g
          obox(cu, cv, cy, hu, hv, hy, a, g, faces) {
            const ca = Math.cos(a || 0), sa = Math.sin(a || 0);
            const L = (du, dv, dy) => W(cu + du * ca - dv * sa, cv + du * sa + dv * ca, cy + dy);
            const Nl = (du, dv) => nrm(du * ca - dv * sa, du * sa + dv * ca, 0);
            const fc = faces || 'fbwetd';
            if (fc.indexOf('f') >= 0) S.quad(L(-hu, -hv, -hy), L(hu, -hv, -hy), L(hu, -hv, hy), L(-hu, -hv, hy), Nl(0, -1), null, g);
            if (fc.indexOf('b') >= 0) S.quad(L(-hu, hv, -hy), L(hu, hv, -hy), L(hu, hv, hy), L(-hu, hv, hy), Nl(0, 1), null, g);
            if (fc.indexOf('w') >= 0) S.quad(L(-hu, -hv, -hy), L(-hu, hv, -hy), L(-hu, hv, hy), L(-hu, -hv, hy), Nl(-1, 0), null, g);
            if (fc.indexOf('e') >= 0) S.quad(L(hu, -hv, -hy), L(hu, hv, -hy), L(hu, hv, hy), L(hu, -hv, hy), Nl(1, 0), null, g);
            if (fc.indexOf('t') >= 0) S.quad(L(-hu, -hv, hy), L(hu, -hv, hy), L(hu, hv, hy), L(-hu, hv, hy), NY, null, g);
            if (fc.indexOf('d') >= 0) S.quad(L(-hu, -hv, -hy), L(hu, -hv, -hy), L(hu, hv, -hy), L(-hu, hv, -hy), ND, null, g);
          },
          // a bar between two local points (u, v, y), square, side s: four sides, no caps (a picket, a rail, a strut)
          bar(p, q, s, g) {
            const d = [q[0] - p[0], q[1] - p[1], q[2] - p[2]], L = Math.hypot(d[0], d[1], d[2]) || 1e-6;
            const t = [d[0] / L, d[1] / L, d[2] / L];
            // two axes across the bar
            let a = Math.abs(t[2]) < 0.9 ? [0, 0, 1] : [1, 0, 0];
            let b = [t[1] * a[2] - t[2] * a[1], t[2] * a[0] - t[0] * a[2], t[0] * a[1] - t[1] * a[0]];
            const lb = Math.hypot(b[0], b[1], b[2]); b = b.map((x) => x / lb);
            a = [b[1] * t[2] - b[2] * t[1], b[2] * t[0] - b[0] * t[2], b[0] * t[1] - b[1] * t[0]];
            const h = s / 2;
            const C = (o, e, k) => W(o[0] + (a[0] * e[0] + b[0] * e[1]) * h, o[1] + (a[1] * e[0] + b[1] * e[1]) * h, o[2] + (a[2] * e[0] + b[2] * e[1]) * h);
            for (const [e0, e1] of [[[1, 1], [1, -1]], [[1, -1], [-1, -1]], [[-1, -1], [-1, 1]], [[-1, 1], [1, 1]]]) {
              const m = [(e0[0] + e1[0]) / 2, (e0[1] + e1[1]) / 2];
              const nl = [a[0] * m[0] + b[0] * m[1], a[1] * m[0] + b[1] * m[1], a[2] * m[0] + b[2] * m[1]];
              S.quad(C(p, e0), C(p, e1), C(q, e1), C(q, e0), nrm(nl[0], nl[1], nl[2]), null, g);
            }
          },
          // a flat strip (a scroll bar of the railing's band) between two local points, w wide straight up: two faces back
          // to back across the run, so it reads from the street and from the stoop
          strip(p, q, w, g) {
            const du = q[0] - p[0], dv = q[1] - p[1], L = Math.hypot(du, dv) || 1e-6, nn = nrm(-dv / L, du / L, 0);
            const a0 = W(p[0], p[1], p[2] - w / 2), a1 = W(q[0], q[1], q[2] - w / 2), a2 = W(q[0], q[1], q[2] + w / 2), a3 = W(p[0], p[1], p[2] + w / 2);
            S.quad(a0, a1, a2, a3, nn, null, g);
            S.quad(a0, a1, a2, a3, [-nn[0], -nn[1], -nn[2]], null, g);
          },
          geom() {
            if (!I.length) return null;
            const g = new THREE.BufferGeometry();
            g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
            g.setAttribute('normal', new THREE.Float32BufferAttribute(N, 3));
            g.setAttribute('uv', new THREE.Float32BufferAttribute(T, 2));
            g.setAttribute('aGl', new THREE.BufferAttribute(new Uint8Array(Gl), 4, true));
            g.setIndex(new THREE.BufferAttribute(n > 65535 ? new Uint32Array(I) : new Uint16Array(I), 1));
            g.computeBoundingSphere();
            return g;
          },
        };
        return S;
      }
      function pointIn(x, z, ring) {
        let c = false;
        for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
          const xi = ring[i][0], zi = ring[i][1], xj = ring[j][0], zj = ring[j][1];
          if ((zi > z) !== (zj > z) && x < (xj - xi) * (z - zi) / (zj - zi) + xi) c = !c;
        }
        return c;
      }

      const near = Soup(), far = Soup(), sign = Soup();
      const GS = (k) => [M_SWATCH, SW[k]];

      // ---- the front, holed for every opening (a grid of cells between the openings' edges; an arch's head leaves its two
      // spandrels as fans from the zone's upper corners), and each opening set back with its reveals, its head and its
      // sill; the recessed face carries the same pixels of the elevation (the doors and casements), so straight on it reads
      // as the image and from the side as a real depth
      const ARCH = [[0, 0], [0.06, 0.38], [0.3, 0.72], [1, 1]];   // a four-centred head's left half, in half-span and rise units
      const archPts = (h) => {
        const hw = (h.u1 - h.u0) / 2, hh = h.yc - h.ys, uc = (h.u0 + h.u1) / 2;
        const L = ARCH.map((p) => [h.u0 + p[0] * hw, h.ys + p[1] * hh]);
        const R = ARCH.slice(0, -1).reverse().map((p) => [h.u1 - p[0] * hw, h.ys + p[1] * hh]);
        void uc;
        return L.concat(R);   // west spring, up to the crown, down to the east spring
      };
      function holedFace(S, yA, yB, holes) {
        const xs = [...new Set([0, FW, ...holes.flatMap((h) => [h.u0, h.u1])])].sort((a, b) => a - b);
        const ys = [...new Set([yA, yB, ...holes.flatMap((h) => [h.y0, h.ys != null ? h.ys : h.y1, h.ys != null ? h.yc : h.y1])])].filter((y) => y >= yA && y <= yB).sort((a, b) => a - b);
        const spandrel = new Set();
        for (let i = 0; i + 1 < xs.length; i++) for (let j = 0; j + 1 < ys.length; j++) {
          const u0 = xs[i], u1 = xs[i + 1], y0 = ys[j], y1 = ys[j + 1], cu = (u0 + u1) / 2, cy = (y0 + y1) / 2;
          if (u1 - u0 < 1e-4 || y1 - y0 < 1e-4) continue;
          const h = holes.find((o) => cu > o.u0 && cu < o.u1 && cy > o.y0 && cy < (o.ys != null ? o.ys : o.y1));
          if (h) continue;
          const a = holes.find((o) => o.ys != null && cu > o.u0 && cu < o.u1 && cy > o.ys && cy < o.yc);
          if (a) {
            if (!spandrel.has(a)) {
              spandrel.add(a);
              const pts = archPts(a), k = (pts.length - 1) / 2;
              for (let q = 0; q < k; q++) S.tri(W(a.u0, 0, a.yc), W(pts[q][0], 0, pts[q][1]), W(pts[q + 1][0], 0, pts[q + 1][1]), NF, ev(a.u0, a.yc), ev(pts[q][0], pts[q][1]), ev(pts[q + 1][0], pts[q + 1][1]), [M_ELEV, 0]);
              for (let q = k; q < pts.length - 1; q++) S.tri(W(a.u1, 0, a.yc), W(pts[q][0], 0, pts[q][1]), W(pts[q + 1][0], 0, pts[q + 1][1]), NF, ev(a.u1, a.yc), ev(pts[q][0], pts[q][1]), ev(pts[q + 1][0], pts[q + 1][1]), [M_ELEV, 0]);
            }
            continue;
          }
          S.fq(u0, u1, y0, y1, 0);
        }
      }
      function recess(S, h, sw) {
        const d = h.d, top = h.ys != null ? h.ys : h.y1, g = GS(sw);
        // the set-back face: the rectangle, then the head's fan from the spring line's middle
        S.fq(h.u0, h.u1, h.y0, top, d);
        if (h.ys != null) {
          const pts = archPts(h), cu = (h.u0 + h.u1) / 2;
          for (let q = 0; q + 1 < pts.length; q++) S.tri(W(cu, d, h.ys), W(pts[q][0], d, pts[q][1]), W(pts[q + 1][0], d, pts[q + 1][1]), NF, ev(cu, h.ys), ev(pts[q][0], pts[q][1]), ev(pts[q + 1][0], pts[q + 1][1]), [M_ELEV, 0]);
          for (let q = 0; q + 1 < pts.length; q++) {   // the head's soffit, a strip per segment facing down into the opening
            const p0 = pts[q], p1 = pts[q + 1], du = p1[0] - p0[0], dy = p1[1] - p0[1], L = Math.hypot(du, dy) || 1;
            S.quad(W(p0[0], 0, p0[1]), W(p1[0], 0, p1[1]), W(p1[0], d, p1[1]), W(p0[0], d, p0[1]), nrm(dy / L, 0, -du / L), null, g);
          }
        } else S.quad(W(h.u0, 0, top), W(h.u1, 0, top), W(h.u1, d, top), W(h.u0, d, top), ND, null, g);
        S.quad(W(h.u0, 0, h.y0), W(h.u0, d, h.y0), W(h.u0, d, top), W(h.u0, 0, top), NU, null, g);   // the west jamb faces east
        S.quad(W(h.u1, 0, h.y0), W(h.u1, d, h.y0), W(h.u1, d, top), W(h.u1, 0, top), NW_, null, g);
        S.quad(W(h.u0, 0, h.y0), W(h.u1, 0, h.y0), W(h.u1, d, h.y0), W(h.u0, d, h.y0), NY, null, g);   // the sill
      }
      const doors = LO.bays.map((b) => ({ u0: b[0], u1: b[1], y0: LO.doorFoot, y1: LO.doorTop, d: 0.25 }));
      const arcade = LO.arcade.map((b) => ({ u0: b[0], u1: b[1], y0: LO.sill2, ys: LO.spring, yc: Math.min(LO.crown, LO.cornice[0] - 0.05), d: 0.20 }));
      const wins = UP.win.map((w) => ({ u0: w[0], u1: w[1], y0: EH + w[2], y1: EH + w[3], d: 0.12 }));
      holedFace(near, 0, EH, doors.concat(arcade));
      holedFace(near, EH, TOP, wins);
      for (const h of doors.concat(arcade)) recess(near, h, 'granite');
      for (const h of wins) recess(near, h, 'brick');
      near.quad(W(0, 0, -1.5), W(FW, 0, -1.5), W(FW, 0, 0), W(0, 0, 0), NF, null, GS('granite'));   // the footing under the walk

      // ---- the granite: five piers (the end two narrower) with their block capitals, the second storey's sill course, the
      // engaged columns in pairs with their bases and capitals, the half piers at the ends, and the cornice
      const capY0 = LO.doorTop - 0.1, capY1 = LO.doorTop + 0.1;
      const pierEdges = [[0, LO.bays[0][0]]];
      for (let i = 0; i < 3; i++) pierEdges.push([LO.bays[i][1], LO.bays[i + 1][0]]);
      pierEdges.push([LO.bays[3][1], FW]);
      const pierMid = pierEdges.map((p) => (p[0] + p[1]) / 2);
      for (const [p0, p1] of pierEdges) {
        near.box(p0, p1, -0.12, 0, -1.5, capY0, 'granite', 'btd');
        near.box(Math.max(0, p0 - 0.05), Math.min(FW, p1 + 0.05), -0.18, 0, capY0, capY1, 'granite', 'b');
      }
      near.box(0, FW, -0.08, 0, LO.sill2 - 0.1, LO.sill2, 'granite', 'b');
      const cR = LO.colR, cV = -cR * 0.55;
      const colY0 = LO.sill2 + 0.12, colY1 = LO.spring - 0.04;
      for (const cu of LO.cols) {
        // the shaft: the front half of a cylinder, twelve facets, its uv projected straight from the elevation
        const n = 12;
        for (let k = 0; k < n; k++) {
          const a0 = Math.PI + Math.PI * k / n, a1 = Math.PI + Math.PI * (k + 1) / n;
          const p0 = [cu + cR * Math.cos(a0), cV + cR * Math.sin(a0)], p1 = [cu + cR * Math.cos(a1), cV + cR * Math.sin(a1)];
          const am = (a0 + a1) / 2, nl = nrm(Math.cos(am), Math.sin(am), 0);
          near.quad(W(p0[0], p0[1], colY0), W(p1[0], p1[1], colY0), W(p1[0], p1[1], colY1), W(p0[0], p0[1], colY1), nl,
            [ev(p0[0], colY0), ev(p1[0], colY0), ev(p1[0], colY1), ev(p0[0], colY1)], [M_ELEV, 0]);
        }
        near.box(cu - cR * 1.25, cu + cR * 1.25, cV - cR * 1.2, 0, LO.sill2, colY0, 'granite', 'b');
        near.box(cu - cR * 1.35, cu + cR * 1.35, cV - cR * 1.3, 0, colY1, colY1 + 0.2, 'granite', 'b');
      }
      near.box(0, LO.arcade[0][0], -0.06, 0, LO.sill2, LO.cornice[0], 'granite', 'bt');
      near.box(LO.arcade[3][1], FW, -0.06, 0, LO.sill2, LO.cornice[0], 'granite', 'bt');
      {
        // the cornice over the second storey: a fascia, a cyma in three facets, the corona and its wash
        const c0 = LO.cornice[0], c1 = LO.cornice[1], hgt = c1 - c0;
        const prof = [[0, c0], [0.05, c0], [0.05, c0 + hgt * 0.32], [0.12, c0 + hgt * 0.42], [0.22, c0 + hgt * 0.52], [0.3, c0 + hgt * 0.62],
          [0.35, c0 + hgt * 0.64], [0.35, c0 + hgt * 0.93], [0.0, c1]];
        for (let k = 0; k + 1 < prof.length; k++) {
          const [o0, y0] = prof[k], [o1, y1] = prof[k + 1];
          const dy = y1 - y0, dv = o1 - o0, L = Math.hypot(dy, dv) || 1;
          const nl = nrm(0, -dy / L, -dv / L);   // outward: away from the wall, and up over a wash or down under a soffit
          const front = Math.abs(dy) > Math.abs(dv) * 1.5;
          near.quad(W(0, -o0, y0), W(FW, -o0, y0), W(FW, -o1, y1), W(0, -o1, y1), nl,
            front ? [ev(0, y0, c0), ev(FW, y0, c0), ev(FW, y1, c0), ev(0, y1, c0)] : null, front ? [M_ELEV, 0] : GS('granite'));
          // the cornice's ends against the neighbours (a corona proud of the party wall line shows its section)
          for (const ue of [0, FW]) near.quad(W(ue, 0, y0), W(ue, -o0, y0), W(ue, -o1, y1), W(ue, 0, y1), ue ? NU : NW_, null, GS('granite'));
        }
      }
      // ---- the brick: the twelve stone sills and lintels, and the corbelled cornice (three stepped courses over the dentil
      // course, then the coping), every front from the upper elevation
      for (const w of wins) {
        near.box(w.u0 - 0.1, w.u1 + 0.1, -0.05, 0, w.y0 - 0.17, w.y0 - 0.02, 'concrete', 'b');
        near.box(w.u0 - 0.13, w.u1 + 0.13, -0.035, 0, w.y1 + 0.03, w.y1 + 0.22, 'concrete', 'b');
      }
      {
        const b0 = TOP - 0.62, steps = [[b0, b0 + 0.18, 0.10], [b0 + 0.18, b0 + 0.3, 0.15], [b0 + 0.3, b0 + 0.42, 0.20], [b0 + 0.42, b0 + 0.54, 0.25], [b0 + 0.54, TOP, 0.27]];
        for (const [y0, y1, o] of steps) near.box(0, FW, -o, 0, y0, y1, 'brick', 'b');
      }

      // ---- the shell: the party walls set 5 cm inside the lot lines, the rear range to Ionic Street, the roofs, the stucco
      // penthouse, the stair bulkhead and the rear range's skylights
      const shell = (S) => {
        S.quad(W(0.05, 0, -1.5), W(0.05, DEPTH, -1.5), W(0.05, DEPTH, TOP), W(0.05, 0, TOP), NW_, null, GS('brick'));
        S.quad(W(FW - 0.04, 0, -1.5), W(FW - 0.04, DEPTH, -1.5), W(FW - 0.04, DEPTH, TOP), W(FW - 0.04, 0, TOP), NU, null, GS('brick'));
        S.quad(W(REAR[0], DEPTH, -1.5), W(FW - 0.04, DEPTH, -1.5), W(FW - 0.04, DEPTH, TOP), W(REAR[0], DEPTH, TOP), NV, null, GS('brick'));
        S.quad(W(0.05, DEPTH, REAR_TOP), W(REAR[0], DEPTH, REAR_TOP), W(REAR[0], DEPTH, TOP), W(0.05, DEPTH, TOP), NV, null, GS('brick'));
        S.quad(W(0, 0, TOP), W(FW, 0, TOP), W(FW - 0.04, DEPTH, TOP), W(0.05, DEPTH, TOP), NY, null, GS('roof'));
        S.quad(W(0.05, DEPTH, -1.5), W(0.05, REAR[1], -1.5), W(0.05, REAR[1], REAR_TOP), W(0.05, DEPTH, REAR_TOP), NW_, null, GS('brick'));
        S.quad(W(REAR[0], DEPTH, -1.5), W(REAR[0], REAR[1], -1.5), W(REAR[0], REAR[1], REAR_TOP), W(REAR[0], DEPTH, REAR_TOP), NU, null, GS('brick'));
        S.quad(W(0.05, REAR[1], -1.5), W(REAR[0], REAR[1], -1.5), W(REAR[0], REAR[1], REAR_TOP), W(0.05, REAR[1], REAR_TOP), NV, null, GS('brick'));
        S.quad(W(0.05, DEPTH, REAR_TOP), W(REAR[0], DEPTH, REAR_TOP), W(REAR[0], REAR[1], REAR_TOP), W(0.05, REAR[1], REAR_TOP), NY, null, GS('roof'));
        S.box(0.5, 5.5, DEPTH + 0.6, DEPTH + 8.6, REAR_TOP, TOP, 'concrete', 'd', GS('concrete'));
        S.box(2.6, 5.8, 12, 16, TOP, 23.0, 'concrete', 'd', GS('concrete'));
      };
      shell(near);
      for (const sv of [DEPTH + 10.5, DEPTH + 13.5]) near.box(1.6, 2.8, sv, sv + 2.4, REAR_TOP, REAR_TOP + 0.35, 'iron', 'd', GS('iron'));

      // ---- the stoop: the raised cafe across the front, its three steps down from the entrance bay, all concrete
      const PT = LO.doorFoot, PV = -1.7;
      const stair = LO.bays[1];
      near.box(0.05, FW - 0.04, PV, 0, -1.5, PT, 'concrete', 'b', GS('concrete'));
      for (let k = 1; k <= 2; k++) near.box(stair[0] - 0.05, stair[1] + 0.05, PV - 0.3 * k, PV - 0.3 * (k - 1), -1.5, PT * (3 - k) / 3, 'concrete', 'b', GS('concrete'));

      // ---- the iron: the stoop's railing (posts, rails, pickets and the quatrefoil band as crossed scroll bars), the stairs'
      // own rails, the Juliet railing in the east bay, the blade sign's bracket, the old box's flat bars, the lanterns'
      // arms and cages, the menu case's frame
      const IRON = GS('iron');
      function railing(p, q, yb, yt, band) {   // local (u, v) ends, the bottom rail's and the top rail's heights over the walk at each end
        const L = Math.hypot(q[0] - p[0], q[1] - p[1]), n = Math.max(1, Math.round(L / 0.12));
        const at = (t, y) => [p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t, y];
        const yAt = (t, ys) => ys[0] + (ys[1] - ys[0]) * t;
        near.bar(at(0, yAt(0, yt)), at(1, yAt(1, yt)), 0.045, IRON);
        near.bar(at(0, yAt(0, yb) + 0.02), at(1, yAt(1, yb) + 0.02), 0.03, IRON);
        if (band) near.bar(at(0, yAt(0, yt) - 0.2), at(1, yAt(1, yt) - 0.2), 0.022, IRON);
        for (let k = 0; k <= n; k++) {
          const t = k / n, post = k === 0 || k === n || k % 10 === 0;
          near.bar(at(t, yAt(t, yb) - (post ? 0.02 : 0)), at(t, yAt(t, yt)), post ? 0.045 : 0.016, IRON);
          if (band && k < n) {   // a scroll's crossed bars in every bay of the band
            const t1 = (k + 1) / n, ya = yAt(t, yt) - 0.2, yb2 = yAt(t1, yt) - 0.2;
            near.strip(at(t, ya), at(t1, yb2 + 0.18), 0.018, IRON);
            near.strip(at(t, ya + 0.18), at(t1, yb2), 0.018, IRON);
          }
        }
      }
      const RV = PV + 0.03, RH = 1.0;
      railing([0.08, RV], [stair[0] - 0.05, RV], [PT, PT], [PT + RH, PT + RH], true);
      railing([stair[1] + 0.05, RV], [FW - 0.08, RV], [PT, PT], [PT + RH, PT + RH], true);
      railing([0.08, RV], [0.08, -0.05], [PT, PT], [PT + RH, PT + RH], true);
      railing([FW - 0.08, RV], [FW - 0.08, -0.05], [PT, PT], [PT + RH, PT + RH], true);
      for (const su of [stair[0] - 0.02, stair[1] + 0.02]) railing([su, RV], [su, PV - 0.62], [PT, 0.02], [PT + RH, 0.9], false);
      {
        const a = LO.arcade[3], jv = -0.16, y0 = LO.sill2 + 0.02;
        railing([a[0] + 0.03, jv], [a[1] - 0.03, jv], [y0, y0], [y0 + 0.92, y0 + 0.92], true);
      }
      // the lanterns: on the second and third piers either side of the entrance, an arm, a cap, a cage of four bars round
      // an octagonal glass (the glow swatch, lit by the photocell after dark)
      const LANT = [];
      for (const pi of [1, 2]) {
        const u = pierMid[pi], v = -0.12 - 0.2, y = 2.75 + PT * 0;
        LANT.push(W(u, v, y + 0.18));
        near.bar([u, -0.12, y + 0.45], [u, v, y + 0.45], 0.04, IRON);
        near.bar([u, v, y + 0.45], [u, v, y + 0.38], 0.03, IRON);
        const r = 0.11, n = 8;
        for (let k = 0; k < n; k++) {
          const a0 = 2 * Math.PI * k / n, a1 = 2 * Math.PI * (k + 1) / n, am = (a0 + a1) / 2;
          const p0 = [u + r * Math.cos(a0), v + r * Math.sin(a0)], p1 = [u + r * Math.cos(a1), v + r * Math.sin(a1)];
          near.quad(W(p0[0], p0[1], y), W(p1[0], p1[1], y), W(p1[0], p1[1], y + 0.36), W(p0[0], p0[1], y + 0.36), nrm(Math.cos(am), Math.sin(am), 0), null, [M_GLOW, SW.glow]);
          const q0 = [u + (r + 0.03) * Math.cos(a0), v + (r + 0.03) * Math.sin(a0)], q1 = [u + (r + 0.03) * Math.cos(a1), v + (r + 0.03) * Math.sin(a1)];
          near.tri(W(q0[0], q0[1], y + 0.36), W(q1[0], q1[1], y + 0.36), W(u, v, y + 0.47), nrm(Math.cos(am), Math.sin(am), 0.8), null, null, null, IRON);
          near.tri(W(q0[0], q0[1], y), W(q1[0], q1[1], y), W(u, v, y - 0.07), nrm(Math.cos(am), Math.sin(am), -0.8), null, null, null, IRON);
        }
        for (let k = 0; k < 4; k++) {
          const a = Math.PI / 4 + k * Math.PI / 2, cu = u + (r + 0.015) * Math.cos(a), cv = v + (r + 0.015) * Math.sin(a);
          near.bar([cu, cv, y - 0.02], [cu, cv, y + 0.38], 0.014, IRON);
        }
      }
      // the blade sign's bracket off the third pier, east of the entrance: a square tube out over the walk, a strut and two
      // hangers; the panel itself is on the signs mesh
      const BU = pierMid[2], BY = capY0 - 0.08, BV1 = -1.62, PAN = [BY - 0.12 - 0.6, BY - 0.12];
      near.bar([BU, -0.12, BY], [BU, BV1, BY], 0.05, IRON);
      near.bar([BU, -0.12, BY - 0.5], [BU, -0.62, BY], 0.035, IRON);
      for (const hv of [-0.4, -1.5]) near.bar([BU, hv, BY - 0.02], [BU, hv, PAN[1]], 0.012, IRON);
      // the old projecting sign box high on the east edge, faded blue and rusting, on two flat bars
      near.box(7.95, 8.25, -1.25, -0.15, 10.2, 12.8, 'rustblue', '', GS('rustblue'));
      for (const by of [10.5, 12.5]) near.box(8.06, 8.14, -0.15, 0, by - 0.03, by + 0.03, 'iron', '', IRON);
      // the menu case on the fourth pier
      const MU = pierMid[3], MY = [PT + 1.0, PT + 1.8];
      near.box(MU - 0.2, MU + 0.2, -0.19, -0.12, MY[0], MY[1], 'iron', 'b', IRON);

      // ---- the cafe: two black bistro tables and six galvanized chairs on the stoop, in front of the third and fourth bays
      // (the shader folds them away while the bar is shut)
      const CAFE_T = [M_CAFE, SW.iron], CAFE_C = [M_CAFE, SW.concrete];
      const table = (u, v) => {
        near.obox(u, v, PT + 0.73, 0.3, 0.3, 0.015, 0, CAFE_T);
        near.obox(u, v, PT + 0.37, 0.03, 0.03, 0.35, 0, CAFE_T, 'fbwe');
        near.obox(u, v, PT + 0.02, 0.22, 0.03, 0.02, 0.3, CAFE_T, 'fbwet');
        near.obox(u, v, PT + 0.02, 0.22, 0.03, 0.02, 0.3 + Math.PI / 2, CAFE_T, 'fbwet');
      };
      const chair = (u, v, a) => {
        const ca = Math.cos(a), sa = Math.sin(a), L = (du, dv) => [u + du * ca - dv * sa, v + du * sa + dv * ca];
        near.obox(u, v, PT + 0.45, 0.18, 0.18, 0.015, a, CAFE_C);
        const bk = L(0, 0.19);
        near.obox(bk[0], bk[1], PT + 0.66, 0.17, 0.012, 0.2, a, CAFE_C, 'fbwet');
        for (const [du, dv] of [[-0.17, -0.17], [0.17, -0.17], [-0.17, 0.17], [0.17, 0.17]]) {
          const top = L(du, dv), foot = L(du * 1.12, dv * 1.12);
          near.bar([top[0], top[1], PT + 0.44], [foot[0], foot[1], PT], 0.022, CAFE_C);
        }
      };
      for (const [tu, tv] of [[5.3, -0.85], [7.3, -0.85]]) {
        table(tu, tv);
        chair(tu - 0.5, tv, Math.PI / 2);
        chair(tu + 0.5, tv, -Math.PI / 2);
      }
      chair(5.3, -1.38, 0); chair(7.3, -1.38, 0);
      chair(6.3, -0.5, Math.PI); chair(4.85, -1.4, 0.4);

      // ---- the far level: the shell, each elevation as one flat face, the two cornices and the stoop as slabs
      shell(far);
      far.fq(0, FW, 0, EH, 0); far.fq(0, FW, EH, TOP, 0);
      far.box(0, FW, -0.35, 0, LO.cornice[0] + 0.3, LO.cornice[1] - 0.05, 'granite', 'bwe', GS('granite'));
      far.box(0, FW, -0.25, 0, TOP - 0.62, TOP, 'brick', 'bwe', GS('brick'));
      far.box(0.05, FW - 0.04, PV, 0, -0.3, PT, 'concrete', 'bd', GS('concrete'));

      // ---- the signs (their own material: the canvas the page letters): the blade panel square to the street, both faces
      // carrying the panel (the back's u not mirrored), the board over the entrance tilted out at its top, the bronze 126
      // plaque on the third pier and the menu in its case on the fourth
      {
        const uvq = (r, flip) => flip ? [[r[0] + r[2], r[1]], [r[0], r[1]], [r[0], r[1] + r[3]], [r[0] + r[2], r[1] + r[3]]]
          : [[r[0], r[1]], [r[0] + r[2], r[1]], [r[0] + r[2], r[1] + r[3]], [r[0], r[1] + r[3]]];
        const g0 = [0, 0];
        // the blade: its long side along -v from the wall outward, 1.2 by 0.6 m, 3 cm thick; read from the west, the
        // panel's left is the wall end; from the east, the street end (so both read left to right)
        const v0 = -0.38, v1 = -1.58, t = 0.015;
        sign.quad(W(BU - t, v0, PAN[0]), W(BU - t, v1, PAN[0]), W(BU - t, v1, PAN[1]), W(BU - t, v0, PAN[1]), NW_, uvq(CV.panel, true), g0);
        sign.quad(W(BU + t, v1, PAN[0]), W(BU + t, v0, PAN[0]), W(BU + t, v0, PAN[1]), W(BU + t, v1, PAN[1]), NU, uvq(CV.panel, true), g0);
        // its edges (white, with the panel's charcoal line) and the board's
        const wq = uvq(CV.white);
        sign.quad(W(BU - t, v0, PAN[1]), W(BU + t, v0, PAN[1]), W(BU + t, v1, PAN[1]), W(BU - t, v1, PAN[1]), NY, wq, g0);
        sign.quad(W(BU - t, v0, PAN[0]), W(BU + t, v0, PAN[0]), W(BU + t, v1, PAN[0]), W(BU - t, v1, PAN[0]), ND, wq, g0);
        sign.quad(W(BU - t, v1, PAN[0]), W(BU + t, v1, PAN[0]), W(BU + t, v1, PAN[1]), W(BU - t, v1, PAN[1]), NF, wq, g0);
        // the flat board over the entrance, on the plain band between the capitals and the sill course, its top 8 degrees out
        const bu = (stair[0] + stair[1]) / 2, bw = 1.45 / 2, bh0 = capY1 + 0.04, bh1 = Math.min(LO.sill2 - 0.14, bh0 + 0.66), tilt = Math.tan(8 * Math.PI / 180) * (bh1 - bh0);
        const fb = [W(bu - bw, -0.05, bh0), W(bu + bw, -0.05, bh0), W(bu + bw, -0.05 - tilt, bh1), W(bu - bw, -0.05 - tilt, bh1)];
        const nb = nrm(0, -1, tilt / (bh1 - bh0));
        sign.quad(fb[0], fb[1], fb[2], fb[3], nb, uvq(CV.panel, true), g0);   // read from the street, east is on the left
        const bk = [W(bu - bw, -0.02, bh0), W(bu + bw, -0.02, bh0), W(bu + bw, -0.02 - tilt, bh1), W(bu - bw, -0.02 - tilt, bh1)];
        sign.quad(fb[3], fb[2], bk[2], bk[3], NY, wq, g0);
        sign.quad(fb[0], fb[3], bk[3], bk[0], NW_, wq, g0);
        sign.quad(fb[1], fb[2], bk[2], bk[1], NU, wq, g0);
        sign.quad(fb[0], fb[1], bk[1], bk[0], ND, wq, g0);
        // the plaque and the menu
        const pu = pierMid[2], py = PT + 0.85;
        sign.quad(W(pu - 0.13, -0.125, py), W(pu + 0.13, -0.125, py), W(pu + 0.13, -0.125, py + 0.17), W(pu - 0.13, -0.125, py + 0.17), NF, uvq(CV.plaque, true), g0);
        sign.quad(W(MU - 0.16, -0.195, MY[0] + 0.05), W(MU + 0.16, -0.195, MY[0] + 0.05), W(MU + 0.16, -0.195, MY[1] - 0.05), W(MU - 0.16, -0.195, MY[1] - 0.05), NF, uvq(CV.menu, true), g0);
      }

      // ---- the meshes: one draw each, near and far on the facade material, the signs on theirs
      const group = new THREE.Group();
      const mk = (S, mat, name) => {
        const g = S.geom();
        if (!g) return null;
        if (name === 'glory-signs') g.deleteAttribute('aGl');   // the signs' material reads no aGl
        const m = new THREE.Mesh(g, mat);
        m.name = name;
        group.add(m);
        return m;
      };
      const frame = { ax: A[0], az: A[1], ux, uz, vx, vz, y0: Y0, fw: FW, lanterns: LANT };
      const facadeMat = G ? G.facade(frame) : K.mat('#a8a59c');
      const signsMat = G ? G.signs() : K.mat('#f0ece7', { rough: 0.6 });
      const mNear = mk(near, facadeMat, 'glory-near'), mFar = mk(far, facadeMat, 'glory-far'), mSign = mk(sign, signsMat, 'glory-signs');
      mSign.userData.noShadow = true;   // a sign a few centimetres thick casts nothing the near map can resolve
      if (G) {
        G.lod(mNear, mFar, mSign, [CX, Y0 + 8, CZ]);
        G.lamps(LANT.map((p) => [p[0], p[1], p[2]]));
        const door = W((stair[0] + stair[1]) / 2, -1.0, 0);
        G.ref({ name: 'Glory Beer Bar & Kitchen', lot: LOT, door: [door[0], door[2]], y0: Y0, c: [CX, Y0 + 8, CZ], n: [-vx, -vz] });
      }
      if (api.occupy) api.occupy(LOT, Y0 + TOP, 0);   // its roof for the placards' grid, its ground for the trees, poles and storefronts
      return group;
    }
  });
})();
