// Round 161 rebuild (the Sep 25 design study): the Sparks Shot Tower, 129-131 Carpenter St, Queen Village (1808, Thomas Sparks,
// John Bishop and James Clement; the first shot tower in the United States).
// Research:
//   OSM way 705302160 (man_made=tower, height 43, building:part inside the rec centre's outline): centre
//     39.93479 N, 75.14634 W -> scene (-135.83, 1179.09). The rec centre (way 705214914, the app's generic
//     'Shot Tower Recreation Center' record, h 13) wraps the tower's north arc, so the tower stands on the rec
//     centre's north wall facing the ballfield; the rec centre stays and nothing is skipped.
//   Wikipedia / PhillyHistory blog / WHYY: 142 ft (43.3 m) to the top of the 20th-century roof (built 150 ft; the
//     city took about 10 ft off after 1913), 30 ft (9.14 m) across at the base tapering to 15 ft (4.57 m) at the
//     top; all brick; workshopoftheworld.com: wall thickness 30, 27, 21, 18, 18, 13, 13 inches in seven stages.
//   Photos (Commons 'Sparks_Sthot_Tower_Philly.JPG' 2013, 'Sparks Shot Tower ... (DSC_3819)', Flickr 2642788206
//     (2005), HABS PA-1621-1 'looking west'): the top is a dark green-black metal collar that flares out from the
//     shaft to about 1.45 times its diameter, a ring of about 36 radial verdigris brackets under its soffit, a
//     thin verdigris bead where it meets the brick, and an almost flat roof with a small knob (no brick corbel,
//     no stone coping). The openings stand in vertical stacks about 5 m apart, bricked in or grilled, taller than
//     wide low down (about 1.1 by 2 m) and smaller near the top (about 0.85 by 1.2 m), under shallow brick heads.
(function () {
  const CX = -135.83, CZ = 1179.09;
  // the street grid's east direction here, from the rec centre's south wall (-148.4, 1191.1) -> (-108.1, 1197.7)
  const GRID = Math.atan2(1197.7 - 1191.1, -108.1 + 148.4);   // +9.3 degrees (math angle, x east, z south)
  RB.add({
    id: 'shot',
    name: 'Sparks Shot Tower',
    center: [CX, CZ],
    aim: [CX, CZ],
    skip: [],
    // [bearing of the eye from the target, horizontal distance, eye height, aim height]
    views: [[145, 230, 70, 24], [12, 125, 34, 24], [280, 75, 42, 30]],
    build(api) {
      const THREE = api.THREE, K = api.K, B = K.builder();
      // ---- ground: the tower's own datum at its centre; the footing runs below the lowest point round it
      const g0 = api.ground(CX, CZ);
      let gMin = g0;
      for (let k = 0; k < 12; k++) { const a = k * Math.PI / 6; gMin = Math.min(gMin, api.ground(CX + 6 * Math.cos(a), CZ + 6 * Math.sin(a))); }
      const Y = g0;                          // datum
      const yFoot = gMin - 1.8;

      // ---- dimensions (metres over the datum)
      const R0 = 4.57, R1 = 2.29, H = 41.2;  // 30 ft base, 15 ft top; the brick shaft runs up into the collar
      const rAt = (y) => R0 + (R1 - R0) * y / H;
      const slope = (R0 - R1) / H;           // horizontal run per metre of rise, for the normals
      const N = 16;                          // facets round the shaft (smooth normals: it reads round)
      const DA = 2 * Math.PI / N;

      // ---- materials: photo colours (K.mat converts them)
      const mBrick = K.mat('#855c4e');                 // weathered Philadelphia brick with lime mortar
      const mBrickDk = K.mat('#744f43');               // bricked-in openings, their heads, the sealed door
      const mGrille = K.mat('#44474a', { rough: 0.6, metal: 0.3 });   // the few openings closed by iron grilles
      const mCollar = K.mat('#1f2a26', { rough: 0.9, metal: 0.05 });    // the dark green-black metal collar
      const mVerd = K.mat('#5d8672', { rough: 0.75, metal: 0.05 });     // brackets and the bead: verdigris paint
      const mRoof = K.mat('#2a2f2c', { rough: 1.0, metal: 0 });      // the almost flat roof above the rim

      // ---- a triangle soup with explicit normals (the shaft is smooth-shaded, the reveals flat)
      function Soup() {
        const P = [], Nn = [];
        return {
          tri(a, b, c, na, nb, nc) { P.push(...a, ...b, ...c); Nn.push(...na, ...nb, ...nc); },
          // quad a b c d (in order round the edge) with a flat normal pointing along `want`
          flat(a, b, c, d, want) {
            const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2], vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
            let n = [uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx];
            const l = Math.hypot(n[0], n[1], n[2]) || 1; n = [n[0] / l, n[1] / l, n[2] / l];
            if (n[0] * want[0] + n[1] * want[1] + n[2] * want[2] < 0) { const t = b; b = d; d = t; n = [-n[0], -n[1], -n[2]]; }
            this.tri(a, b, c, n, n, n); this.tri(a, c, d, n, n, n);
          },
          geom() {
            if (!P.length) return null;
            const g = new THREE.BufferGeometry();
            g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
            g.setAttribute('normal', new THREE.Float32BufferAttribute(Nn, 3));
            g.setAttribute('uv', new THREE.Float32BufferAttribute(new Array(P.length / 3 * 2).fill(0), 2));
            return g;
          }
        };
      }
      const brick = Soup(), brickDk = Soup(), grille = Soup();

      // facet j is centred on the math angle GRID + j * DA, so facets 0, 4, 8 and 12 face the street grid's
      // east, south, west and north
      const ang = (j) => GRID + (j - 0.5) * DA;
      const chordDir = (j, s) => { const a0 = ang(j), a1 = ang(j + 1); return [Math.cos(a0) + (Math.cos(a1) - Math.cos(a0)) * s, Math.sin(a0) + (Math.sin(a1) - Math.sin(a0)) * s]; };
      const SP = (j, s, y) => { const d = chordDir(j, s), r = rAt(y); return [CX + r * d[0], Y + y, CZ + r * d[1]]; };
      const SN = (j, s) => { const d = chordDir(j, s), l = Math.hypot(d[0], d[1]); const n = [d[0] / l, slope, d[1] / l]; const m = Math.hypot(n[0], n[1], n[2]); return [n[0] / m, n[1] / m, n[2] / m]; };
      const facetOut = (j) => { const a = GRID + j * DA; return [Math.cos(a), 0, Math.sin(a)]; };
      function surf(S, j, s0, s1, ya, yb) {   // a smooth piece of facet j, s0..s1 across, ya..yb high, wound outward
        const a = SP(j, s0, ya), b = SP(j, s1, ya), c = SP(j, s1, yb), d = SP(j, s0, yb);
        const na = SN(j, s0), nb = SN(j, s1), o = facetOut(j);
        const ux = b[0] - a[0], uz = b[2] - a[2], vy = d[1] - a[1];
        const nx = -uz * vy, nz = ux * vy;      // (b - a) x (d - a), horizontal part
        if (nx * o[0] + nz * o[2] >= 0) { S.tri(a, b, c, na, nb, nb); S.tri(a, c, d, na, nb, na); }
        else { S.tri(a, c, b, na, nb, nb); S.tri(a, d, c, na, na, nb); }
      }

      // ---- the openings: four stacks (E, S, W, N of the grid) of seven, 5.17 m apart, at matching levels;
      // taller than wide low down, smaller near the top. Most are bricked in; four carry iron grilles.
      const openings = [];
      const grilled = new Set(['12:2', '0:4', '8:1', '12:5']);
      for (const j of [0, 4, 8, 12]) {
        for (let i = 0; i < 7; i++) {
          const t = i / 6, y = 7.0 + i * 5.17;
          openings.push({ j, y, h: 2.0 - 0.8 * t, w: 1.1 - 0.25 * t, kind: grilled.has(j + ':' + i) ? 'grille' : 'win' });
        }
      }
      // the sealed ground-floor entrance, on the ballfield (north) side
      openings.push({ j: 12, y: 0.05, h: 2.7, w: 1.5, kind: 'door' });

      // ---- ring heights: every opening's sill and head, the footing, the datum and the shaft top
      const ys = new Set([+(yFoot - Y).toFixed(3), 0, H]);
      for (const o of openings) { ys.add(+o.y.toFixed(3)); ys.add(+(o.y + o.h).toFixed(3)); }
      const rings = [...ys].sort((a, b) => a - b);
      const inOpen = (j, ya, yb) => openings.find((o) => o.j === j && ya >= o.y - 1e-6 && yb <= o.y + o.h + 1e-6);
      const halfS = (o) => Math.min(0.46, (o.w / 2) / (2 * rAt(o.y) * Math.sin(Math.PI / N)));
      for (let k = 0; k + 1 < rings.length; k++) {
        const ya = rings[k], yb = rings[k + 1];
        for (let j = 0; j < N; j++) {
          const o = inOpen(j, ya, yb);
          if (!o) { surf(brick, j, 0, 1, ya, yb); continue; }
          const hs = halfS(o);
          surf(brick, j, 0, 0.5 - hs, ya, yb);
          surf(brick, j, 0.5 + hs, 1, ya, yb);
        }
      }
      // reveals, backs and brick heads
      for (const o of openings) {
        const hs = halfS(o), s0 = 0.5 - hs, s1 = 0.5 + hs, out = facetOut(o.j);
        const D = o.kind === 'door' ? 0.22 : 0.15;     // shallow: the infill sits just behind the face
        const ya = o.y, yb = o.y + o.h;
        const inw = (p) => [p[0] - out[0] * D, p[1], p[2] - out[2] * D];
        const A = SP(o.j, s0, ya), Bp = SP(o.j, s1, ya), Cp = SP(o.j, s1, yb), Dp = SP(o.j, s0, yb);
        const Ai = inw(A), Bi = inw(Bp), Ci = inw(Cp), Di = inw(Dp);
        const along = [Bp[0] - A[0], 0, Bp[2] - A[2]];
        brick.flat(A, Dp, Di, Ai, along);                                   // left jamb faces +s
        brick.flat(Bp, Cp, Ci, Bi, [-along[0], 0, -along[2]]);             // right jamb faces -s
        brick.flat(Dp, Cp, Ci, Di, [0, -1, 0]);                             // head soffit
        brick.flat(A, Bp, Bi, Ai, [0, 1, 0]);                               // sill
        (o.kind === 'grille' ? grille : brickDk).flat(Ai, Bi, Ci, Di, out); // the infill
        // a shallow brick head (a flat arch of soldier bricks) a few centimetres proud of the face
        const c = SP(o.j, 0.5, yb), len = Math.hypot(along[0], along[2]) + (o.kind === 'door' ? 0.36 : 0.14);
        const hh = o.kind === 'door' ? 0.36 : 0.24;
        const ag = new THREE.BoxGeometry(len, hh, 0.07);
        ag.rotateY(-Math.atan2(along[2], along[0]));
        ag.translate(c[0] + out[0] * 0.0, c[1] + hh / 2, c[2] + out[2] * 0.0);
        B.add(mBrickDk, ag);
      }

      // ---- the collar: a lathe per part, 32 segments round (this is the silhouette). Profiles run bottom to top,
      // so LatheGeometry's faces point outward; each part is its own lathe so the corners stay crisp.
      const NC = 32;
      const lathe = (mat, pts) => {
        const g = new THREE.LatheGeometry(pts.map((p) => new THREE.Vector2(p[0], p[1])), NC, 0, Math.PI * 2);
        g.translate(CX, Y, CZ);
        B.add(mat, g);
      };
      const rT = rAt(H);                     // 2.29, the brick at the collar
      // the verdigris bead where the metal meets the brick
      lathe(mVerd, [[rT - 0.02, H - 0.1], [rT + 0.1, H - 0.06], [rT + 0.14, H + 0.08], [rT + 0.1, H + 0.2], [rT + 0.06, H + 0.25]]);
      // the flared soffit, from the bead out to the rim
      const rIn = rT + 0.06, rRim = 3.40, ySoff0 = H + 0.25, ySoff1 = H + 1.05;
      lathe(mCollar, [[rIn, ySoff0], [rIn + 0.35, ySoff0 + 0.2], [rRim - 0.02, ySoff1]]);
      // the fascia, with a small drip at its foot
      lathe(mCollar, [[rRim - 0.02, ySoff1], [rRim + 0.04, ySoff1 - 0.02], [rRim + 0.04, ySoff1 + 0.4]]);
      // the almost flat roof: a cap on the rim, then a shallow cone
      const yRoof = ySoff1 + 0.4, yApex = 43.05;
      lathe(mRoof, [[rRim + 0.04, yRoof], [rRim - 0.1, yRoof + 0.05], [0.25, yApex - 0.02], [0.001, yApex]]);
      // the knob
      lathe(mCollar, [[0.001, yApex - 0.05], [0.16, yApex], [0.16, yApex + 0.12], [0.1, yApex + 0.22], [0.001, yApex + 0.27]]);
      // 36 radial brackets under the soffit, lighter verdigris, their tops following the flare
      {
        const nB = 36, r0 = rIn + 0.12, r1 = rRim - 0.06;
        const yOn = (r) => r <= rIn + 0.35 ? ySoff0 + (r - rIn) * 0.2 / 0.35 : ySoff0 + 0.2 + (r - rIn - 0.35) * (ySoff1 - ySoff0 - 0.2) / (rRim - 0.02 - rIn - 0.35);
        const y0 = yOn(r0), y1 = yOn(r1), L = Math.hypot(r1 - r0, y1 - y0), phi = Math.atan2(y1 - y0, r1 - r0);
        const dep = 0.14, wid = 0.07;          // thin ribs on the dark soffit (DSC_3819 from below)
        for (let i = 0; i < nB; i++) {
          const th = GRID + (i + 0.5) * 2 * Math.PI / nB;
          const g = new THREE.BoxGeometry(L, dep, wid);
          g.translate(0, -dep / 2 + 0.02, 0);           // hang under the line, tucked 2 cm into the soffit
          g.rotateZ(phi);
          g.translate((r0 + r1) / 2, (y0 + y1) / 2, 0);
          // a deeper outer end, the tooth that reads against the fascia from below
          const tip = new THREE.BoxGeometry(0.16, 0.34, 0.13);
          tip.translate(r1 - 0.06, y1 - 0.14, 0);
          for (const q of [g, tip]) { q.rotateY(-th); q.translate(CX, Y, CZ); B.add(mVerd, q); }
        }
      }

      B.add(mBrick, brick.geom());
      B.add(mBrickDk, brickDk.geom());
      B.add(mGrille, grille.geom());
      if (api.occupy) {   // the base as the tower's own ground: no tree, pole or storefront stands in it
        const ring = [];
        for (let i = 0; i < 24; i++) { const a = i / 24 * Math.PI * 2; ring.push([CX + Math.cos(a) * R0, CZ + Math.sin(a) * R0]); }
        api.occupy(ring, Y + 43.3, 0);
      }
      return B.done();
    }
  });
})();
