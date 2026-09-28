// Eastern State Penitentiary (John Haviland, 1822-1836; later blocks to 1959), 2027 Fairmount Avenue.
// Round 161 rebuild (the Sep 25 design study, revision 2 after review). The level-topped granite wall on the OSM wall lines with its buttresses and
// blind lancets, the four corner towers (partial octagons on Fairmount Avenue, plain squares on Brown Street) with their
// brick guard houses, the castellated front (three-storey wings behind a solid parapet, two flanking towers with
// machicolations, the gate block with its pointed arch between gabled buttresses, the 1937 barbican and the octagonal
// central tower), the Observatory with its brick crown and 1951 steel lookout, and the fifteen cellblocks placed from
// the HABS PA-1729 written data (the building-by-building descriptions) checked on a z19 orthophoto and the OSM star:
// 1 to 3 and 8 to 11 one storey, 4 to 7 two storeys with their tan brick third storeys at the hub, 12 and 14 three
// storeys of pale concrete with flat roofs, 13 and 15 flat. Also the kitchen, the Industrial Building, the garage,
// the Bertillon office, the courtyard additions, the sheds and the sand track and yards.
(function () {
  // ---- plan data (scene frame: x east, z south, metres)
  const HUB = [-2377.5, -2529.5];
  // corner tower centres (OSM building ways 1408585768 to 71)
  const SW = [-2482.45, -2433.85], SE = [-2285.6, -2429.0], NE = [-2283.75, -2623.7], NW = [-2476.6, -2628.07];
  // the wall's outer faces (OSM barrier=wall ways 1408585763, 66, 67), tower face to tower face; the south wall is on
  // the Fairmount frame at v = +0.9 (ways 1408585764 and 65), either side of the front building
  const W_E = [[-2284.76, -2432.8], [-2281.21, -2620.23]];
  const W_N = [[-2287.26, -2626.13], [-2473.1, -2630.56]];
  const W_W = [[-2479.45, -2624.61], [-2483.29, -2437.56]];

  RB.add({
    id: 'esp',
    name: 'Eastern State Penitentiary',
    center: [-2383, -2528],
    aim: [-2385, -2505],
    skip: [
      // everything inside the wall: the star, the Industrial Building, the greenhouse and the two sheds
      [[-2482.3, -2436.9], [-2285.9, -2431.9], [-2282.3, -2621.6], [-2474.6, -2629.6], [-2478.4, -2624.2]],
      // the front building on Fairmount Avenue and the four corner towers
      [[-2418, -2426], [-2352, -2424], [-2352, -2453], [-2418, -2460]],
      [[-2488, -2440], [-2477, -2440], [-2477, -2428], [-2488, -2428]],
      [[-2291, -2435], [-2280, -2435], [-2280, -2423], [-2291, -2423]],
      [[-2289, -2629], [-2278, -2629], [-2278, -2618], [-2289, -2618]],
      [[-2482, -2634], [-2471, -2634], [-2471, -2622], [-2482, -2622]]
    ],
    views: [
      [205, 265, 100, 6],
      [141, 190, 38, 7],
      [25, 260, 100, 0]
    ],
    build(api) {
      const THREE = api.THREE, K = api.K, G = api.ground;
      const B = K.builder();

      // ---- night: the app's lamp pools (LAMPMAP) and a warm floodlight wash on the Fairmount front. The kit's plain
      // materials never see LAMPMAP, so the lamp map's uniforms come in as api.lampU (lampMapU, the ones lampLightPatch
      // reads) and the same pool term is added to clones of the kit materials here.
      const LAMP = api.where === 'app' && api.lampU ? api.lampU : null;   // the app's lamp map uniforms (lampLightPatch's)
      function nightPatch(mat, mode, flood) {
        if (!LAMP) return mat;
        const m = mat.clone();
        m.onBeforeCompile = (sh) => {
          sh.uniforms.uLampMap = LAMP.uLampMap; sh.uniforms.uLampBox = LAMP.uLampBox; sh.uniforms.uLampOn = LAMP.uLampOn; sh.uniforms.uLampFade = LAMP.uLampFade;
          sh.vertexShader = sh.vertexShader
            .replace('#include <common>', '#include <common>\nvarying vec3 vEspW; varying vec3 vEspN;')
            .replace('#include <project_vertex>', '#include <project_vertex>\nvEspW = (modelMatrix * vec4(transformed, 1.0)).xyz; vEspN = normalize(mat3(modelMatrix) * objectNormal);');
          const gate = mode === 'ground' ? 'smoothstep(0.35, 0.7, vEspN.y)'
            : '0.75 * mix(0.3, 1.0, 1.0 - smoothstep(0.35, 0.7, abs(vEspN.y))) * (1.0 - smoothstep(3.0, 16.0, lwp.y - 20.0))';
          sh.fragmentShader = sh.fragmentShader
            .replace('void main() {', 'uniform sampler2D uLampMap; uniform vec4 uLampBox, uLampFade; uniform float uLampOn;\nvarying vec3 vEspW; varying vec3 vEspN;\nvoid main() {')
            .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\n' + [
              'if (uLampOn > 0.001) {',
              '  vec3 lwp = vEspW;',
              '  vec2 luv = vec2((lwp.x - uLampBox.x) * uLampBox.z, 1.0 - (lwp.z - uLampBox.y) * uLampBox.z);',
              '  float le = min(min(luv.x, 1.0 - luv.x), min(luv.y, 1.0 - luv.y));',
              '  float lk = ' + gate + ' * (1.0 - smoothstep(uLampFade.z - uLampFade.w, uLampFade.z, distance(lwp.xz, uLampFade.xy)));',
              '  if (le > 0.0 && lk > 0.0) { vec3 la = min(diffuseColor.rgb, vec3(0.35)) * texture2D(uLampMap, luv).rgb * (uLampOn * uLampBox.w * lk);',
              '    vec3 lo = max(la - 0.5, 0.0); totalEmissiveRadiance += min(la, vec3(0.5)) + lo / (1.0 + lo * 2.0); }',
              flood ? [
                // ground-mounted floods on the Fairmount front and the two south towers: south faces only, fading upward
                '  float fFront = step(-2419.0, lwp.x) * step(lwp.x, -2349.0) * smoothstep(-2450.0, -2446.0, lwp.z);',
                '  float fTw = max(1.0 - smoothstep(5.0, 6.5, distance(lwp.xz, vec2(-2482.45, -2433.85))), 1.0 - smoothstep(5.0, 6.5, distance(lwp.xz, vec2(-2285.6, -2429.0))));',
                '  float fN = smoothstep(0.25, 0.75, vEspN.z);',
                '  float fH = mix(1.0, 0.3, smoothstep(0.0, 22.0, lwp.y - 19.5));',
                '  totalEmissiveRadiance += diffuseColor.rgb * vec3(1.0, 0.74, 0.46) * (1.6 * uLampOn * max(fFront, fTw) * fN * fH);'
              ].join('\n') : '',
              '}'
            ].join('\n'));
        };
        m.customProgramCacheKey = () => 'esp-night-' + mode + (flood ? '-flood' : '');
        return m;
      }
      const M = (hex, o, mode, flood) => nightPatch(K.mat(hex, o), mode || 'wall', flood);

      // ---- materials (photo colours; the kit converts them). Eight materials, eight meshes.
      const STONE = M('#655f56', { rough: 0.92 }, 'wall', true);        // weathered squared granite
      const TRIM = M('#c2bbab', { rough: 0.85 }, 'wall', true);         // cast stone copings and courses; the pale concrete of 12, 13, 14
      const ROOF_D = M('#2e2d2d', { rough: 0.9 }, 'wall');              // tar, asphalt and built-up roofs (the aerial's near-black field)
      const ROOF_R = M('#8e4538', { rough: 0.75 }, 'wall');             // the red standing-seam roofs (9, 2, the corridors)
      const ROOF_L = M('#9b968a', { rough: 0.9 }, 'wall');              // pale membranes (3, 4, 7), the galvanised lookout
      const GLASS = K.glass('#1d232a');                                  // openings, skylights, blind recesses
      const BRICK = M('#9c7258', { rough: 0.9 }, 'wall');               // the guard houses and the tan and red brick crowns
      const SAND = M('#b9a887', { rough: 0.95 }, 'ground');             // the perimeter track and the front yard

      // ---- ground
      const gAt = (x, z) => G(x, z) || 0;
      const gSpan = (pts) => { let lo = Infinity, hi = -Infinity; for (const p of pts) { const g = gAt(p[0], p[1]); if (g < lo) lo = g; if (g > hi) hi = g; } return [lo, hi]; };
      const W3 = (p, y) => [p[0], y, p[1]];
      const add = (m, g) => B.add(m, g);

      // ---- helpers
      const len2 = (a, b) => Math.hypot(b[0] - a[0], b[1] - a[1]);
      const lerp2 = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
      const ngon = (c, r, n, a0) => { const out = []; for (let i = 0; i < n; i++) { const a = a0 + i * 2 * Math.PI / n; out.push([c[0] + r * Math.cos(a), c[1] + r * Math.sin(a)]); } return out; };
      // merlons along a world segment a -> b (outer face on the segment, pushed `inSign` along the left normal)
      function merlonsSeg(a, b, y0, h, t, mw, gw, inSign) {
        const s = K.seg(a, b), n = Math.max(1, Math.floor((s.len + gw) / (mw + gw)));
        const used = n * mw + (n - 1) * gw, st = (s.len - used) / 2, out = [];
        for (let i = 0; i < n; i++) {
          const s0 = st + i * (mw + gw);
          out.push(K.edgeBox([a[0] + s.ux * s0, a[1] + s.uz * s0], [a[0] + s.ux * (s0 + mw), a[1] + s.uz * (s0 + mw)], y0, h, t, inSign * t / 2));
        }
        return out;
      }
      // merlons round a ring (one per edge, two on long edges)
      function ringMerlons(ring, y0, h, t, frac) {
        const sgn = K.signedArea(ring) > 0 ? 1 : -1, out = [];
        for (let i = 0; i < ring.length; i++) {
          const a = ring[i], b = ring[(i + 1) % ring.length], L = len2(a, b), k = L > 3.6 ? 2 : 1;
          for (let j = 0; j < k; j++) {
            const c0 = (j + 0.5) / k, hw = (frac || 0.55) / k / 2;
            out.push(K.edgeBox(lerp2(a, b, c0 - hw), lerp2(a, b, c0 + hw), y0, h, t, -sgn * t / 2));
          }
        }
        return out;
      }
      // an n-sided frustum with a vertex at angle a0
      function frustum(c, rTop, rBot, y0, y1, n, a0) {
        const g = new THREE.CylinderGeometry(rTop, rBot, y1 - y0, n, 1, false);
        g.rotateY(Math.PI / 2 - a0);
        g.translate(c[0], (y0 + y1) / 2, c[1]);
        return g;
      }
      // a pointed arch (dark panel) on the plane v = vf of frame f, outward sign s: span w, springing at ys, apex ys + rise,
      // with a square lower part from yBottom
      function pointedArch(f, uc, vf, s, ys, w, rise, yBottom) {
        const out = [], W = (u, y) => { const p = f.p(u, vf); return [p[0], y, p[1]]; };
        const IN = (() => { const p = f.p(uc, vf - s * 2); return [p[0], ys, p[1]]; })();
        const n = 4, half = [];
        for (let k = 0; k <= n; k++) { const a = (Math.PI / 2) * k / n; half.push([uc - w / 2 + 0.36 * w * (1 - Math.cos(a)), ys + 0.72 * rise * Math.sin(a)]); }
        half.push([uc, ys + rise]);
        const pts = half.concat(half.slice(0, -1).reverse().map((q) => [2 * uc - q[0], q[1]]));
        for (let i = 0; i < pts.length - 1; i++) out.push(K.tri(W(uc, ys), W(pts[i][0], pts[i][1]), W(pts[i + 1][0], pts[i + 1][1]), IN));
        if (yBottom != null && yBottom < ys) out.push(K.quad(W(uc - w / 2, yBottom), W(uc + w / 2, yBottom), W(uc + w / 2, ys), W(uc - w / 2, ys), IN));
        return out;
      }
      // a lancet window (dark, 3 cm proud of the face) with a stone sill
      function lancet(f, uc, vf, s, y0, w, h, sill) {
        const rise = Math.min(w * 0.9, h * 0.4);
        add(GLASS, pointedArch(f, uc, vf + s * 0.03, s, y0 + h - rise, w, rise, y0));
        if (sill !== false) add(TRIM, K.boxF(f, uc, vf + s * 0.1, w + 0.3, 0.3, y0 - 0.2, 0.2));
      }
      // a slab along a -> b between offsets o0 and o1 along the unit normal n, from y0 up to a top running ta -> tb
      function sBox(a, b, n, o0, o1, y0, ta, tb) {
        const P = (p, o, y) => [p[0] + n[0] * o, y, p[1] + n[1] * o];
        const C = [(a[0] + b[0]) / 2 + n[0] * (o0 + o1) / 2, (y0 + Math.min(ta, tb)) / 2, (a[1] + b[1]) / 2 + n[1] * (o0 + o1) / 2];
        return [
          K.quad(P(a, o0, y0), P(b, o0, y0), P(b, o0, tb), P(a, o0, ta), C),
          K.quad(P(a, o1, y0), P(b, o1, y0), P(b, o1, tb), P(a, o1, ta), C),
          K.quad(P(a, o0, ta), P(b, o0, tb), P(b, o1, tb), P(a, o1, ta), C),
          K.quad(P(a, o0, y0), P(a, o1, y0), P(a, o1, ta), P(a, o0, ta), C),
          K.quad(P(b, o0, y0), P(b, o1, y0), P(b, o1, tb), P(b, o0, tb), C)
        ];
      }
      // a battered buttress: at p on the outer face, d along the wall, n outward; w wide, projecting pb at y0 and pt at y1
      function buttress(p, d, n, w, y0, y1, pb, pt) {
        const P = (u, o, y) => [p[0] + d[0] * u + n[0] * o, y, p[1] + d[1] * u + n[1] * o];
        const C = [p[0] - n[0] * 0.5, (y0 + y1) / 2, p[1] - n[1] * 0.5], h = w / 2;
        return [
          K.quad(P(-h, pb, y0), P(h, pb, y0), P(h, pt, y1), P(-h, pt, y1), C),
          K.quad(P(-h, 0, y0), P(-h, pb, y0), P(-h, pt, y1), P(-h, 0, y1), C),
          K.quad(P(h, 0, y0), P(h, pb, y0), P(h, pt, y1), P(h, 0, y1), C),
          K.quad(P(-h, 0, y1 + 0.45), P(h, 0, y1 + 0.45), P(h, pt, y1), P(-h, pt, y1), C),
          K.tri(P(-h, 0, y1), P(-h, pt, y1), P(-h, 0, y1 + 0.45), C),
          K.tri(P(h, 0, y1), P(h, pt, y1), P(h, 0, y1 + 0.45), C)
        ];
      }
      // a ground-hugging plate over a strip a -> b (offsets o0..o1 along n), sampled every ~5 m, lifted `lift`
      function drapeStrip(a, b, n, o0, o1, lift) {
        const L = len2(a, b), k = Math.max(1, Math.round(L / 5)), out = [];
        const P = (t, o) => { const q = lerp2(a, b, t), x = q[0] + n[0] * o, z = q[1] + n[1] * o; return [x, gAt(x, z) + lift, z]; };
        for (let i = 0; i < k; i++) {
          const t0 = i / k, t1 = (i + 1) / k, mid = lerp2(a, b, (t0 + t1) / 2);
          out.push(K.quad(P(t0, o0), P(t1, o0), P(t1, o1), P(t0, o1), [mid[0], gAt(mid[0], mid[1]) - 5, mid[1]]));
        }
        return out;
      }
      // a ground-hugging plate over a convex polygon (fan from its centroid, edges split every ~6 m)
      function drapePoly(ring, lift) {
        const c = K.centroid(ring), cy = gAt(c[0], c[1]) + lift, out = [];
        for (let i = 0; i < ring.length; i++) {
          const a = ring[i], b = ring[(i + 1) % ring.length], k = Math.max(1, Math.round(len2(a, b) / 6));
          for (let j = 0; j < k; j++) {
            const p = lerp2(a, b, j / k), q = lerp2(a, b, (j + 1) / k);
            out.push(K.tri([c[0], cy, c[1]], [p[0], gAt(p[0], p[1]) + lift, p[1]], [q[0], gAt(q[0], q[1]) + lift, q[1]], [c[0], cy - 5, c[1]]));
          }
        }
        return out;
      }

      // =====================================================================================
      // 1. THE PERIMETER WALL: 30 ft of squared granite with ONE level coping (the ground inside was made level and
      //    the wall shortens toward Brown Street, HABS). A vertical outer face with a plinth that follows the street,
      //    the battered inner face as a slope, ten battered buttresses on each of the east, north and west walls at
      //    50 ft, and fourteen blind lancets on the Fairmount front
      // =====================================================================================
      const FS = K.frameFromEdge(SW, SE);                          // the Fairmount Avenue front: u east, v out (south)
      const WALL_T = 1.1, BATTER = 2.6, VS = 0.9;
      const cxS = (SW[0] + SE[0] + NE[0] + NW[0]) / 4, czS = (SW[1] + SE[1] + NE[1] + NW[1]) / 4;
      let gSum = 0; for (let i = 0; i <= 10; i++) { const p = FS.p(4 + i * 18.9, VS); gSum += gAt(p[0], p[1]); }
      const gS = gSum / 11, WT = gS + 9.14;                        // the one coping level
      let gFs = 0; for (let i = 0; i <= 7; i++) { const p = FS.p(67 + i * 8.8, 2.5); gFs += gAt(p[0], p[1]); }
      const gF = gFs / 8;                                          // the Fairmount grade at the front building
      function wallRun(a, b, opt) {
        opt = opt || {};
        const s = K.seg(a, b), toC = [cxS - s.mid[0], czS - s.mid[1]];
        const inSign = (s.nx * toC[0] + s.nz * toC[1]) > 0 ? 1 : -1, nIn = [s.nx * inSign, s.nz * inSign], nOut = [-nIn[0], -nIn[1]], d = [s.ux, s.uz];
        const off = (p, dd) => [p[0] + nIn[0] * dd, p[1] + nIn[1] * dd];
        const nSeg = Math.max(1, Math.round(s.len / 22));
        for (let i = 0; i < nSeg; i++) {
          const p0 = lerp2(a, b, i / nSeg), p1 = lerp2(a, b, (i + 1) / nSeg), pm = lerp2(p0, p1, 0.5);
          const [lo] = gSpan([p0, p1, pm, off(p0, WALL_T + BATTER), off(p1, WALL_T + BATTER), off(p0, -1), off(p1, -1)]);
          const base = lo - 1.5;
          add(STONE, K.edgeBox(p0, p1, base, WT - base, WALL_T, inSign * WALL_T / 2));
          add(TRIM, K.edgeBox(p0, p1, WT, 0.3, WALL_T + 0.3, inSign * WALL_T / 2));
          // the outer plinth and its cap, following the street
          const g0 = gAt(p0[0], p0[1]), g1 = gAt(p1[0], p1[1]);
          add(STONE, sBox(p0, p1, nIn, -0.4, 0.05, base, g0 + 1.2, g1 + 1.2));
          add(TRIM, sBox(p0, p1, nIn, -0.55, 0.0, g0 + 1.05, g0 + 1.25, g1 + 1.25).slice(0, 3));
          // the battered inner face, from under the coping down to the yard
          const i0 = off(p0, WALL_T), i1 = off(p1, WALL_T), q0 = off(p0, WALL_T + BATTER), q1 = off(p1, WALL_T + BATTER);
          add(STONE, K.quad(W3(i0, WT - 1.6), W3(i1, WT - 1.6), W3(q1, gAt(q1[0], q1[1]) - 0.4), W3(q0, gAt(q0[0], q0[1]) - 0.4), W3(off(pm, -3), base)));
        }
        // ten battered buttresses at 50 ft (15.24 m), centred on the wall
        if (opt.buttresses) {
          for (let k = 0; k < 10; k++) {
            const t = 0.5 + (k - 4.5) * 15.24 / s.len, p = lerp2(a, b, t), g = gAt(p[0], p[1]);
            add(STONE, buttress(p, d, nOut, 2.0, g - 0.4, WT - 1.5, 1.2, 0.4));
          }
        }
        // blind lancets (filled with concrete): dark recesses with a stone lintel and sill
        if (opt.lancets) {
          const f = K.frameFromEdge(a, b), sg = f.local(a[0] + nOut[0], a[1] + nOut[1])[1] > 0 ? 1 : -1;
          for (let k = 0; k < opt.lancets; k++) {
            const u = s.len * (k + 0.5) / opt.lancets, p = f.p(u, 0), g = gAt(p[0], p[1]);
            add(GLASS, pointedArch(f, u, sg * 0.03, sg, g + 5.9, 0.55, 0.5, g + 3.1));
            add(TRIM, K.boxF(f, u, sg * 0.1, 0.95, 0.25, g + 2.9, 0.2));
            add(TRIM, K.boxF(f, u, sg * 0.08, 0.9, 0.2, g + 6.45, 0.22));
          }
        }
        return { nIn, nOut };
      }
      // south: the runs either side of the front building (u 3.9 to 66.4 and 129.1 to 193.1); then east, north and west
      wallRun(FS.p(3.9, VS), FS.p(66.4, VS), { lancets: 7 });
      wallRun(FS.p(129.1, VS), FS.p(193.1, VS), { lancets: 7 });
      const wE = wallRun(W_E[0], W_E[1], { buttresses: true });
      const wN = wallRun(W_N[0], W_N[1], { buttresses: true });
      const wW = wallRun(W_W[0], W_W[1], { buttresses: true });

      // the sand perimeter track inside all four walls and the sand yard behind the front building
      {
        const T0 = WALL_T + BATTER + 0.2, T1 = T0 + 7;
        const sandAdd = (g) => add(SAND, g);
        sandAdd(drapeStrip(FS.p(8, VS), FS.p(62, VS), [-FS.vx, -FS.vz], T0, T1, 0.22));
        sandAdd(drapeStrip(FS.p(133, VS), FS.p(189, VS), [-FS.vx, -FS.vz], T0, T1, 0.22));
        sandAdd(drapeStrip(lerp2(W_E[0], W_E[1], 0.02), lerp2(W_E[0], W_E[1], 0.98), wE.nIn, T0, T1, 0.22));
        sandAdd(drapeStrip(lerp2(W_N[0], W_N[1], 0.02), lerp2(W_N[0], W_N[1], 0.98), wN.nIn, T0, T1, 0.22));
        sandAdd(drapeStrip(lerp2(W_W[0], W_W[1], 0.02), lerp2(W_W[0], W_W[1], 0.98), wW.nIn, T0, T1, 0.22));
        sandAdd(drapePoly([[-2428, -2443.5], [-2405.1, -2465.5], [-2363, -2464.6], [-2340.5, -2441]], 0.22));
      }

      // =====================================================================================
      // 2. THE FOUR CORNER TOWERS, their battlements level with each other over the level wall. The south towers are
      //    partial octagons projecting past both walls, with lancets and slits; the north towers are plain squares that
      //    project very slightly and have no windows (HABS). Each carries its brick guard house (by 1945).
      // =====================================================================================
      function cornerTower(c, ang, hx, hz, ch, south) {
        const f = K.frame(c[0], c[1], ang);
        const ring = ch > 0
          ? [f.p(-hx + ch, -hz), f.p(hx - ch, -hz), f.p(hx, -hz + ch), f.p(hx, hz - ch), f.p(hx - ch, hz), f.p(-hx + ch, hz), f.p(-hx, hz - ch), f.p(-hx, -hz + ch)]
          : [f.p(-hx, -hz), f.p(hx, -hz), f.p(hx, hz), f.p(-hx, hz)];
        const [lo, hi] = gSpan(ring.concat([c])), base = lo - 1.5, C0 = WT + 1.6;
        if (south) {
          add(STONE, K.prism(K.offsetRing(ring, 0.55), base, hi + 2.6));                // battered base, stepped
          add(TRIM, K.prism(K.offsetRing(ring, 0.62), hi + 2.6, hi + 2.85));
        } else {
          add(STONE, K.prism(K.offsetRing(ring, 0.3), base, hi + 1.2));
          add(TRIM, K.prism(K.offsetRing(ring, 0.36), hi + 1.2, hi + 1.4));
        }
        add(STONE, K.prism(ring, base, C0));
        add(TRIM, K.prism(K.offsetRing(ring, 0.28), C0, C0 + 0.6));                    // corbel course
        const R2 = K.offsetRing(ring, 0.55);
        add(STONE, K.prism(R2, C0 + 0.6, C0 + 1.1));
        add(STONE, K.ringWalls(R2, C0 + 1.1, 1.15, 0.5));
        add(TRIM, K.ringWalls(K.offsetRing(R2, 0.05), C0 + 2.25, 0.14, 0.6));
        add(STONE, ringMerlons(R2, C0 + 2.39, 0.95, 0.5, 0.5));
        // the guard house: brick, a band of metal windows, a thin concrete slab roof
        const r0 = C0 + 1.1;
        add(BRICK, K.slabF(f, -1.8, 1.8, -1.8, 1.8, r0, r0 + 2.1));
        add(GLASS, K.slabF(f, -1.72, 1.72, -1.72, 1.72, r0 + 2.1, r0 + 3.0));
        for (const [pu, pv] of [[-1.6, -1.6], [1.6, -1.6], [1.6, 1.6], [-1.6, 1.6]]) add(BRICK, K.boxF(f, pu, pv, 0.42, 0.42, r0 + 2.1, 0.9));
        add(BRICK, K.slabF(f, -1.8, 1.8, -1.8, 1.8, r0 + 3.0, r0 + 3.6));
        add(TRIM, K.slabF(f, -2.05, 2.05, -2.05, 2.05, r0 + 3.6, r0 + 3.8));
        // openings on the south towers' outward faces: a lancet high up and a slit lower down
        if (south) {
          const out = [c[0] - cxS, c[1] - czS], ol = Math.hypot(out[0], out[1]);
          for (let i = 0; i < ring.length; i++) {
            const a = ring[i], b = ring[(i + 1) % ring.length], m = lerp2(a, b, 0.5), dm = [m[0] - c[0], m[1] - c[1]], dl = Math.hypot(dm[0], dm[1]);
            if ((dm[0] * out[0] + dm[1] * out[1]) / (dl * ol) < 0.25 || len2(a, b) < 2) continue;
            const ef = K.frameFromEdge(a, b), sg = ef.local(c[0], c[1])[1] > 0 ? -1 : 1, L = len2(a, b);
            add(GLASS, pointedArch(ef, L / 2, sg * 0.03, sg, hi + 9.3, 0.5, 0.45, hi + 7.4));
            const A = ef.p(L / 2 - 0.17, sg * 0.03), Bq = ef.p(L / 2 + 0.17, sg * 0.03);
            add(GLASS, K.quad(W3(A, hi + 4.2), W3(Bq, hi + 4.2), W3(Bq, hi + 5.6), W3(A, hi + 5.6), W3(c, hi + 5)));
          }
        }
      }
      cornerTower(SW, FS.a, 3.81, 3.76, 2.0, true);
      cornerTower(SE, FS.a, 3.77, 3.8, 2.0, true);
      const aN = Math.atan2(W_N[0][1] - W_N[1][1], W_N[0][0] - W_N[1][0]);
      cornerTower(NE, aN, 3.55, 3.5, 0, false);
      cornerTower(NW, aN, 3.52, 3.5, 0, false);

      // =====================================================================================
      // 3. THE FRONT BUILDING (200 ft on Fairmount Avenue, from the OSM footprint): three towers linked by three-storey
      //    wings. Heights from the rectified HABS elevation photo (205871): the wing parapet 13.2 m over the street,
      //    a solid band with small caps; the flanking towers to 18.3 m with pointed-arch machicolations; the octagonal
      //    central tower to 23 m. The battlements hide shed roofs (HABS), so no roof shows from the street.
      // =====================================================================================
      {
        const f = FS, U0 = 98.4, fp = (u, v) => f.p(u, v);
        const [lo] = gSpan([fp(66.4, 4), fp(129.1, 4), fp(129.1, -22), fp(66.4, -22), fp(98, -9)]);
        const base = lo - 1.5, g = gF;
        const slab = (m, u0, u1, v0, v1, y0, y1) => add(m, K.slabF(f, u0, u1, v0, v1, y0, y1));
        const shed = (u0, u1, vHi, yHi, vLo, yLo) => { const W = (u, v, y) => { const p = fp(u, v); return [p[0], y, p[1]]; }; add(ROOF_D, K.quad(W(u0, vHi, yHi), W(u1, vHi, yHi), W(u1, vLo, yLo), W(u0, vLo, yLo), W((u0 + u1) / 2, (vHi + vLo) / 2, yLo - 3))); };
        // -- the two wings: body, water table, string course, a solid parapet with small caps, three slender lancets
        for (const [u0, u1] of [[77.0, 92.4], [104.4, 119.6]]) {
          const v0 = -9.5, v1 = 1.5;
          slab(STONE, u0, u1, v0, v1, base, g + 12.0);
          slab(STONE, u0, u1, v1 - 0.6, v1, g + 12.0, g + 13.2);                    // the front parapet band
          slab(STONE, u0, u1, v0, v0 + 0.5, g + 12.0, g + 12.7);                    // the rear parapet
          shed(u0, u1, v1 - 0.6, g + 12.9, v0 + 0.5, g + 12.15);
          slab(TRIM, u0, u1, v1, v1 + 0.2, g + 3.1, g + 3.35);                      // the water table
          slab(TRIM, u0, u1, v1, v1 + 0.25, g + 11.0, g + 11.3);                    // the string course
          slab(TRIM, u0, u1, v1 - 0.7, v1 + 0.12, g + 13.2, g + 13.35);             // coping
          const n = Math.floor((u1 - u0 - 1.2) / 3.5) + 1, st = (u1 - u0 - (n - 1) * 3.5) / 2;
          for (let k = 0; k < n; k++) { const u = u0 + st + k * 3.5; slab(STONE, u - 0.6, u + 0.6, v1 - 0.7, v1 + 0.04, g + 13.35, g + 13.9); }
          for (const t of [0.2, 0.47, 0.74]) lancet(f, u0 + (u1 - u0) * t, v1, 1, g + 3.9, 0.8, 5.8);
          const wr = K.windowsF(f, u0 + 1.8, u1 - 1.8, v0, -1, g + 2.2, 3, 3.5, 4, 0.9, 1.6, { inset: -0.04 });
          add(GLASS, wr.glass); add(TRIM, wr.trim);
        }
        // -- the two flanking towers: pointed-arch machicolations under a crenellated parapet, triple lancets on the
        //    front with three narrow windows above, three tiers of three windows on the back
        for (const [u0, u1] of [[66.4, 77.0], [119.6, 129.1]]) {
          const v0 = -7.5, v1 = 3.8, uc = (u0 + u1) / 2;
          slab(STONE, u0, u1, v0, v1, base, g + 15.1);
          slab(STONE, u0 - 0.25, u1 + 0.25, v0 - 0.25, v1 + 0.25, base, g + 1.4);
          slab(TRIM, u0 - 0.3, u1 + 0.3, v0 - 0.3, v1 + 0.3, g + 1.4, g + 1.6);
          slab(TRIM, u0 - 0.1, u1 + 0.1, v1, v1 + 0.2, g + 3.1, g + 3.35);
          // the machicolation band carried on arched brackets
          slab(STONE, u0 - 0.55, u1 + 0.55, v0 - 0.55, v1 + 0.55, g + 15.1, g + 16.2);
          for (let u = u0 + 0.45; u <= u1 - 0.3; u += 1.15) { slab(TRIM, u - 0.16, u + 0.16, v1, v1 + 0.55, g + 14.2, g + 15.1); slab(TRIM, u - 0.16, u + 0.16, v0 - 0.55, v0, g + 14.2, g + 15.1); }
          for (let v = v0 + 0.45; v <= v1 - 0.3; v += 1.15) { slab(TRIM, u0 - 0.55, u0, v - 0.16, v + 0.16, g + 14.2, g + 15.1); slab(TRIM, u1, u1 + 0.55, v - 0.16, v + 0.16, g + 14.2, g + 15.1); }
          const R = K.rect(f, u0 - 0.55, u1 + 0.55, v0 - 0.55, v1 + 0.55);
          add(STONE, K.ringWalls(R, g + 16.2, 1.1, 0.5));
          add(TRIM, K.ringWalls(K.offsetRing(R, 0.06), g + 17.3, 0.14, 0.62));
          const rs = K.signedArea(R) > 0 ? -1 : 1;
          for (let i = 0; i < 4; i++) add(STONE, merlonsSeg(R[i], R[(i + 1) % 4], g + 17.44, 0.86, 0.5, 1.3, 0.8, rs));
          slab(ROOF_D, u0 - 0.1, u1 + 0.1, v0 - 0.1, v1 + 0.1, g + 16.2, g + 16.3);
          for (const du of [-1.3, 0, 1.3]) lancet(f, uc + du, v1, 1, g + 3.9, 0.85, 4.4, false);
          slab(TRIM, uc - 2.0, uc + 2.0, v1, v1 + 0.3, g + 3.7, g + 3.9);
          const ws = K.windowsF(f, uc - 1.6, uc + 1.6, v1, 1, g + 10.2, 1, 0, 3, 0.4, 1.7, { inset: -0.04, sill: false });
          add(GLASS, ws.glass);
          const wb = K.windowsF(f, uc - 2.4, uc + 2.4, v0, -1, g + 2.6, 3, 3.6, 3, 0.8, 1.5, { inset: -0.04 });
          add(GLASS, wb.glass); add(TRIM, wb.trim);
        }
        // -- the gate block: the pointed gateway (27 ft by 15 ft) with its hood mould and portcullis, between two gabled
        //    buttresses rising over the parapet
        {
          const u0 = 92.4, u1 = 104.4, v0 = -12.1, v1 = 4.0;
          slab(STONE, u0, u1, v0, v1, base, g + 12.0);
          slab(STONE, u0, u1, v1 - 0.6, v1, g + 12.0, g + 13.2);
          slab(TRIM, u0, u1, v1 - 0.7, v1 + 0.12, g + 13.2, g + 13.35);
          slab(TRIM, u0, u1, v1, v1 + 0.25, g + 11.0, g + 11.3);
          slab(ROOF_D, u0 + 0.3, u1 - 0.3, v0 + 0.3, v1 - 0.6, g + 12.0, g + 12.1);
          for (const u of [u0, u1]) {
            slab(STONE, u - 0.8, u + 0.8, v1 - 1.0, v1 + 0.7, base, g + 13.3);
            add(TRIM, K.gableF(f, u - 0.8, u + 0.8, v1 - 1.0, v1 + 0.7, g + 13.3, g + 14.6, false, 0.06).all);
          }
          add(TRIM, pointedArch(f, U0, v1 + 0.02, 1, g + 5.2, 5.6, 3.9, g + 5.0));          // the stone reveal
          add(GLASS, pointedArch(f, U0, v1 + 0.05, 1, g + 5.3, 4.6, 3.1, g + 5.1));         // the opening
          for (let k = -2; k <= 2; k++) add(TRIM, K.slabF(f, U0 + k * 0.85 - 0.06, U0 + k * 0.85 + 0.06, v1 + 0.06, v1 + 0.12, g + 5.3, g + 5.3 + 3.0 * (1 - Math.pow(Math.abs(k) / 2.7, 2))));
          add(TRIM, K.slabF(f, U0 - 2.2, U0 + 2.2, v1 + 0.06, v1 + 0.12, g + 7.1, g + 7.2));
          add(TRIM, K.slabF(f, U0 - 3.1, U0 + 3.1, v1, v1 + 0.2, g + 9.35, g + 9.55));      // hood mould
          // the octagonal central tower: louvred lancets, a corbelled crenellated top at 23 m
          const tc = fp(U0, -4.6), a0 = f.a + Math.PI / 8, oct = ngon(tc, 3.55, 8, a0);
          add(STONE, K.prism(oct, g + 11.5, g + 19.8));
          add(TRIM, K.prism(K.offsetRing(oct, 0.22), g + 19.8, g + 20.4));
          const oct2 = K.offsetRing(oct, 0.55);
          add(STONE, K.prism(oct2, g + 20.4, g + 20.8));
          add(STONE, K.ringWalls(oct2, g + 20.8, 1.1, 0.5));
          add(TRIM, K.ringWalls(K.offsetRing(oct2, 0.05), g + 21.9, 0.14, 0.6));
          add(STONE, ringMerlons(oct2, g + 22.04, 0.96, 0.5, 0.5));
          add(ROOF_D, frustum(tc, 0.3, 3.3, g + 20.8, g + 22.0, 8, a0));
          for (let i = 0; i < 8; i++) {
            const a = oct[i], b = oct[(i + 1) % 8], ef = K.frameFromEdge(a, b), L = len2(a, b), sg = ef.local(tc[0], tc[1])[1] > 0 ? -1 : 1;
            if (i % 2 === 0) add(GLASS, pointedArch(ef, L / 2, sg * 0.03, sg, g + 17.4, 0.8, 0.7, g + 14.6));
            else { const A = ef.p(L / 2 - 0.12, sg * 0.03), Bq = ef.p(L / 2 + 0.12, sg * 0.03); add(GLASS, K.quad(W3(A, g + 15.2), W3(Bq, g + 15.2), W3(Bq, g + 17.0), W3(A, g + 17.0), W3(tc, g + 16))); }
          }
          // the large through-way to the north (one storey, pale roof)
          slab(STONE, 104.3, 115.3, -21.2, v0 + 0.2, base, g + 6.2);
          slab(ROOF_L, 104.4, 115.2, -21.1, v0 + 0.2, g + 6.2, g + 6.35);
          slab(TRIM, 104.3, 115.3, -21.3, -20.9, g + 6.2, g + 6.7);
        }
        // -- the barbican (1937-38) across the foot of the gate, about half the wing height
        {
          const u0 = U0 - 5.7, u1 = U0 + 5.7, v0 = 4.0, v1 = 7.3;
          slab(STONE, u0, u1, v0 - 0.2, v1, base, g + 6.9);
          slab(TRIM, u0 - 0.1, u1 + 0.1, v0 - 0.2, v1 + 0.1, g + 6.9, g + 7.1);
          const W = (u, y) => { const p = fp(u, v1 + 0.02); return [p[0], y, p[1]]; }, IN = (() => { const p = fp(U0, v0); return [p[0], g + 2, p[1]]; })();
          add(GLASS, K.quad(W(U0 - 1.6, g), W(U0 + 1.6, g), W(U0 + 1.6, g + 3.9), W(U0 - 1.6, g + 3.9), IN));
          slab(TRIM, U0 - 1.9, U0 + 1.9, v1, v1 + 0.12, g + 3.9, g + 4.35);
          add(GLASS, K.quad(W(U0 + 2.7, g), W(U0 + 3.8, g), W(U0 + 3.8, g + 2.4), W(U0 + 2.7, g + 2.4), IN));
          for (const u of [U0 - 4.5, U0 + 4.5]) slab(TRIM, u - 0.25, u + 0.25, v1, v1 + 0.08, g + 4.9, g + 5.6);
        }
        // -- the one-storey courtyard additions behind the wings (HABS): the mess hall in the west yard, the L-shaped
        //    visiting room in the east yard, the small generator house by the north gate
        flatBlock([fp(72.5, -25.0), fp(92.0, -24.9), fp(92.0, -18.1), fp(67.3, -18.3), fp(67.3, -19.4)].reverse(), 4.5, ROOF_D, STONE);
        flatBlock([[-2367, -2447], [-2358, -2447], [-2358, -2458], [-2352.5, -2458], [-2352.5, -2441.5], [-2367, -2441.5]], 4.2, ROOF_L, STONE);
        flatBlock([[-2380, -2461.5], [-2366, -2461.5], [-2366, -2457.5], [-2380, -2457.5]], 3.2, ROOF_L, STONE);
      }

      // =====================================================================================
      // 4. THE OBSERVATORY: two storeys of rough ashlar (40 ft octagon) capped with concrete, the tan and red brick
      //    extension wall above, a low corrugated roof, and the 1951 steel lookout: a tapering shaft, the grated walkway
      //    with its rail, the glazed room and the tent roof, 19.7 m (the app's record)
      // =====================================================================================
      {
        const c = HUB, a0 = FS.a + Math.PI / 8;
        const [lo, hi] = gSpan(ngon(c, 7, 8, a0)), base = lo - 1.5, g = hi;
        const oct = ngon(c, 6.6, 8, a0);
        add(STONE, K.prism(oct, base, g + 8.8));
        add(TRIM, K.corniceRing(oct, g + 8.6, g + 9.0, 0.2));
        add(BRICK, K.prism(K.offsetRing(oct, -0.15), g + 9.0, g + 10.8));
        add(TRIM, K.corniceRing(K.offsetRing(oct, -0.15), g + 10.8, g + 11.05, 0.12));
        add(ROOF_D, frustum(c, 3.0, 6.5, g + 11.05, g + 12.2, 8, a0));
        add(ROOF_L, frustum(c, 2.2, 2.7, g + 12.2, g + 15.2, 8, a0));
        add(ROOF_L, frustum(c, 3.35, 3.35, g + 15.2, g + 15.45, 8, a0));
        const rr = ngon(c, 3.25, 8, a0);
        for (let i = 0; i < 8; i++) add(ROOF_L, K.edgeBox(rr[i], rr[(i + 1) % 8], g + 15.45, 1.0, 0.07, 0));
        add(ROOF_L, frustum(c, 2.3, 2.3, g + 15.45, g + 16.0, 8, a0));
        add(GLASS, frustum(c, 2.2, 2.2, g + 16.0, g + 17.3, 8, a0));
        for (const p of ngon(c, 2.26, 8, a0)) add(ROOF_L, K.box(0.2, 1.3, 0.2, p[0], g + 16.65, p[1]));
        add(ROOF_L, frustum(c, 2.35, 2.35, g + 17.3, g + 17.7, 8, a0));
        add(ROOF_D, frustum(c, 0.05, 2.9, g + 17.7, g + 19.7, 8, a0));
        for (let i = 0; i < 8; i++) {
          const a = oct[i], b = oct[(i + 1) % 8], sg = K.seg(a, b), m = lerp2(a, b, 0.5);
          const o = [m[0] + (m[0] - c[0]) * 0.004, m[1] + (m[1] - c[1]) * 0.004];
          const A = [o[0] - sg.ux * 0.55, o[1] - sg.uz * 0.55], Bq = [o[0] + sg.ux * 0.55, o[1] + sg.uz * 0.55];
          add(GLASS, K.quad(W3(A, g + 6.0), W3(Bq, g + 6.0), W3(Bq, g + 7.7), W3(A, g + 7.7), W3(c, g + 7)));
        }
      }

      // =====================================================================================
      // 5. THE CELLBLOCKS
      // =====================================================================================
      // a gabled block on a centre line p0 -> p1, width w. Options:
      //   aisles: [{ side (-1 / +1 in the block's v), from, to, w, h }] the one-storey wings (the old exercise yards)
      //   hoods: { pitch, rows: [v / hw, ...] } cell skylights in the roof's own material
      //   corr: n corridor skylights along the ridge; sky: n large gabled skylights (the two-storey blocks)
      //   third: length of the tan brick third storey at the hub end; windows: rows of cell windows (later blocks)
      //   neck: { len, w } a narrower corridor neck at the start
      function block(p0, p1, w, eave, ridge, roof, o) {
        o = o || {};
        const f = K.frameFromEdge(p0, p1), L = len2(p0, p1), hw = w / 2, n0 = o.neck ? o.neck.len : 0;
        const aw = (o.aisles || []).reduce((m, a) => Math.max(m, a.w), 0);
        const [lo, hi] = gSpan(K.rect(f, 0, L, -hw - aw, hw + aw).concat([f.p(L / 2, 0)])), base = lo - 1.5, g = hi;
        if (o.neck) {
          const nw = o.neck.w / 2;
          add(STONE, K.slabF(f, 0, n0 + 0.5, -nw, nw, base, g + eave - 0.4));
          const gn = K.gableF(f, 0, n0 + 0.5, -nw, nw, g + eave - 0.4, g + eave + 1.6, true, 0.25);
          add(o.neckRoof || roof, gn.slopes); add(STONE, gn.ends);
        }
        add(STONE, K.slabF(f, n0, L, -hw, hw, base, g + eave));
        add(TRIM, K.slabF(f, n0 - 0.12, L + 0.12, -hw - 0.12, hw + 0.12, g + eave - 0.35, g + eave));
        const gb = K.gableF(f, n0, L, -hw, hw, g + eave, g + ridge, true, 0.35);
        add(roof, gb.slopes); add(STONE, gb.ends);
        for (const a of (o.aisles || [])) {
          const v0 = a.side < 0 ? -hw - a.w : hw, v1 = a.side < 0 ? -hw : hw + a.w, u0 = Math.max(a.from, n0), u1 = Math.min(a.to == null ? L - 0.5 : a.to, L - 0.5), h = a.h || 4.0;
          add(STONE, K.slabF(f, u0, u1, v0, v1, base, g + h));
          add(a.roof || ROOF_D, K.slabF(f, u0 + 0.15, u1 - 0.15, v0 + (a.side < 0 ? 0.15 : 0), v1 - (a.side > 0 ? 0.15 : 0), g + h, g + h + 0.12));
          add(TRIM, K.slabF(f, u0, u1, a.side < 0 ? v0 - 0.05 : v1 - 0.3, a.side < 0 ? v0 + 0.3 : v1 + 0.05, g + h, g + h + 0.35));
        }
        const slopeY = (v) => g + eave + (ridge - eave) * (1 - Math.abs(v) / hw);
        if (o.hoods) {
          for (let u = n0 + 1.6; u <= L - 1.4; u += o.hoods.pitch) for (const r of o.hoods.rows) {
            const v = r * hw; add(o.hoods.mat || roof, K.boxF(f, u, v, 0.6, 0.6, slopeY(v) - 0.3, 0.62));
          }
        }
        if (o.corr) {
          for (let k = 0; k < o.corr; k++) { const u = n0 + 3 + (L - n0 - 6) * (o.corr === 1 ? 0.5 : k / (o.corr - 1)); add(ROOF_L, K.boxF(f, u, 0, 1.3, 1.2, g + ridge - 0.25, 0.55)); }
        }
        if (o.sky) {
          for (let k = 0; k < o.sky; k++) {
            const u = n0 + (o.third || 0) + 4 + (L - n0 - (o.third || 0) - 8) * (o.sky === 1 ? 0.5 : k / (o.sky - 1));
            add(TRIM, K.boxF(f, u, 0, 5.2, 2.6, g + ridge - 0.6, 0.9));
            add(GLASS, K.gableF(f, u - 2.5, u + 2.5, -1.25, 1.25, g + ridge + 0.3, g + ridge + 1.05, true, 0.05).all);
          }
        }
        if (o.third) {
          const t0 = n0 + 0.3, t1 = n0 + o.third, tv = hw - 1.4;
          add(BRICK, K.slabF(f, t0, t1, -tv, tv, g + eave - 0.3, g + eave + 3.3));
          add(TRIM, K.slabF(f, t0 - 0.15, t1 + 0.15, -tv - 0.15, tv + 0.15, g + eave + 3.3, g + eave + 3.55));
          add(ROOF_D, K.slabF(f, t0 + 0.2, t1 - 0.2, -tv + 0.2, tv - 0.2, g + eave + 3.55, g + eave + 3.62));
          for (const sd of [-1, 1]) { const ww = K.windowsF(f, t0 + 1.5, t1 - 1.5, sd * tv, sd, g + eave + 1.0, 1, 0, 3, 0.8, 1.2, { inset: -0.04, sill: false }); add(GLASS, ww.glass); }
        }
        if (o.windows) {
          const n = Math.max(2, Math.floor((L - n0 - 3) / 3.2));
          for (const sd of [-1, 1]) { const ww = K.windowsF(f, n0 + 1.8, L - 1.8, sd * hw, sd, g + 1.6, o.windows, (eave - 1.2) / o.windows, n, 0.75, 1.3, { inset: -0.04, sill: false }); add(GLASS, ww.glass); }
        }
        return { f, g, L };
      }
      // a flat-roofed block on a polygon: walls, a membrane roof, a coping, optional roof skylights
      function flatBlock(ring, h, roof, wall, coping) {
        const [lo, hi] = gSpan(ring.concat([K.centroid(ring)])), base = lo - 1.5, g = hi;
        add(wall || STONE, K.prism(ring, base, g + h));
        add(roof, K.prism(K.offsetRing(ring, -0.3), g + h, g + h + 0.05));
        add(coping || TRIM, K.ringWalls(K.offsetRing(ring, 0.05), g + h, 0.5, 0.4));
        return g;
      }
      // a three-storey concrete bar with a nearly flat roof and a trapezoidal end profile (Cellblocks 12 and 14):
      // pale walls with three rows of narrow casement windows, a concrete cornice, a low-pitched built-up roof
      function concreteBar(p0, p1, w, h, o) {
        o = o || {};
        const f = K.frameFromEdge(p0, p1), L = len2(p0, p1), hw = w / 2;
        const [lo, hi] = gSpan(K.rect(f, 0, L, -hw, hw)), base = lo - 1.5, g = o.g != null ? o.g : hi;
        add(TRIM, K.slabF(f, 0, L, -hw, hw, base, g + h));
        add(STONE, K.slabF(f, -0.08, L + 0.08, -hw - 0.08, hw + 0.08, base, g + 0.9));                      // water table
        add(TRIM, K.slabF(f, -0.25, L + 0.25, -hw - 0.25, hw + 0.25, g + h - 0.35, g + h));                  // cornice
        add(ROOF_D, K.hipF(f, 0.1, L - 0.1, -hw + 0.1, hw - 0.1, g + h, g + h + 0.55, 0.0));
        const n = Math.max(3, Math.round((L - 3) / (o.pitch || 2.7)));
        for (const sd of [-1, 1]) {
          if (o.sides && o.sides.indexOf(sd) < 0) continue;
          const ww = K.windowsF(f, 1.6, L - 1.6, sd * hw, sd, g + 1.7, 3, 3.3, n, 0.55, 1.35, { inset: -0.04 });
          add(GLASS, ww.glass); add(TRIM, ww.trim);
        }
        // the frontispiece on the far end: a projecting concrete bay with the door and two triple windows
        if (o.front) {
          const sgn = o.front, uF = sgn > 0 ? L : 0;
          const d0 = uF, d1 = uF + sgn * 1.2;
          add(TRIM, K.slabF(f, Math.min(d0, d1), Math.max(d0, d1), -2.6, 2.6, base, g + h + 0.6));
          add(TRIM, K.slabF(f, Math.min(d0, d1) - 0.15, Math.max(d0, d1) + 0.15, -2.8, 2.8, g + h + 0.6, g + h + 0.85));
          const Q = (v, y) => W3(f.p(d1 + sgn * 0.03, v), y), IN = W3(f.p(uF - sgn * 2, 0), g + 2);
          add(GLASS, K.quad(Q(-0.9, g + 0.2), Q(0.9, g + 0.2), Q(0.9, g + 2.9), Q(-0.9, g + 2.9), IN));
          for (const yy of [4.4, 7.7]) for (const dv of [-0.9, 0, 0.9]) add(GLASS, K.quad(Q(dv - 0.35, g + yy), Q(dv + 0.35, g + yy), Q(dv + 0.35, g + yy + 1.7), Q(dv - 0.35, g + yy + 1.7), IN));
        }
        return { f, g, L };
      }
      // the short covered corridors from the Center (red roofs)
      function spoke(from, to, w, h) {
        const f = K.frameFromEdge(from, to), L = len2(from, to);
        const [lo, hi] = gSpan([from, to]), base = lo - 1.5, g = hi, e = h || 5.0;
        add(STONE, K.slabF(f, 0, L, -w / 2, w / 2, base, g + e));
        const gb = K.gableF(f, 0, L, -w / 2, w / 2, g + e, g + e + 1.8, true, 0.25);
        add(ROOF_R, gb.slopes); add(STONE, gb.ends);
      }
      const fromHub = (to, r) => { const d = len2(HUB, to); return [HUB[0] + (to[0] - HUB[0]) / d * r, HUB[1] + (to[1] - HUB[1]) / d * r]; };
      const HOOD2 = { pitch: 4.6, rows: [-0.5, 0.5] }, HOOD4 = { pitch: 2.4, rows: [-0.7, -0.3, 0.3, 0.7] };

      // -- the seven originals (HABS: 1 to 3 one storey with wings, 4 to 7 two storeys with wings and a third storey at the hub)
      // 1 (SE, 1823-29, extended 1869-70): the corridor on the orthophoto's skylight row, dark gable; its wings, the
      // chapel and the shoe shop are the flat field below
      block([-2373.6, -2522.1], [-2300.5, -2446.5], 13, 5.4, 8.2, ROOF_D, { neck: { len: 12, w: 6.5 }, hoods: HOOD2, corr: 12 });
      block([-2362, -2528.8], [-2294.5, -2528.3], 16, 5.4, 8.2, ROOF_R, { hoods: HOOD2, corr: 11, aisles: [{ side: -1, from: 8, w: 4.8 }, { side: 1, from: 8, w: 4.8 }] });   // 2 (E)
      block([-2362, -2551], [-2316.4, -2590.2], 13.5, 5.4, 8.2, ROOF_L, { hoods: HOOD2, corr: 15, aisles: [{ side: 1, from: 6, w: 4.8 }] });                                 // 3 (NE); 14 took its SE yards
      block([-2378.8, -2548], [-2380.2, -2618], 14, 9.0, 11.6, ROOF_L, { sky: 2, third: 13, aisles: [{ side: -1, from: 14, w: 6, h: 4.4 }, { side: 1, from: 14, w: 6, h: 4.4 }] });   // 4 (N)
      block([-2395, -2546], [-2459, -2611], 15, 9.0, 11.8, ROOF_D, { sky: 3, third: 13, aisles: [{ side: -1, from: 14, w: 5, h: 4.4 }, { side: 1, from: 14, w: 5, h: 4.4 }] });    // 5 (NW)
      {
        // 6 (W): the south range's twelve eastern yards gave way to Cellblock 12 (HABS)
        const f6 = K.frameFromEdge([-2396, -2531.5], [-2471, -2531.5]), sN = f6.local(-2430, -2560)[1] > 0 ? 1 : -1;
        block([-2396, -2531.5], [-2471, -2531.5], 15, 9.0, 11.8, ROOF_D, { sky: 2, third: 13, aisles: [{ side: sN, from: 12, w: 5, h: 4.4 }, { side: -sN, from: 44, w: 5.3, h: 4.4 }] });
        // 7 (SW): the north-west range's thirteen eastern yards gave way to 12; the garage continues it
        const f7 = K.frameFromEdge([-2394, -2513], [-2461, -2450]), sNW = f7.local(-2440, -2500)[1] > 0 ? 1 : -1;
        block([-2394, -2513], [-2461, -2450], 15, 9.0, 11.8, ROOF_L, { sky: 3, third: 13, aisles: [{ side: -sNW, from: 8, w: 3.2, h: 4.2 }, { side: sNW, from: 35, w: 9, h: 4.4 }] });
      }
      // -- the later blocks
      // 8 and 9 (Cassidy, 1877-79): the one-storey V astride the axial corridor south of the Observatory, 9 the red roof
      block([-2386, -2495], [-2438, -2445.5], 16.5, 5.2, 7.9, ROOF_D, { hoods: HOOD4, corr: 12 });
      block([-2385.05, -2500.25], [-2331.3, -2443.8], 16.5, 5.2, 7.9, ROOF_R, { hoods: HOOD4, corr: 12 });
      // the Bertillon office (1940-41), the triangle between their south ends, fieldstone over concrete
      {
        const tri = [[-2381, -2488], [-2363, -2464.6], [-2405.1, -2465.5]];
        const gB = flatBlock(tri, 4.5, ROOF_D, STONE);
        const fb = K.frameFromEdge(tri[2], tri[1]), sg = fb.local(tri[0][0], tri[0][1])[1] > 0 ? -1 : 1, L = len2(tri[2], tri[1]);
        const IN = W3(K.centroid(tri), gB + 2);
        const W = (u, y) => W3(fb.p(u, sg * 0.03), y);
        add(GLASS, K.quad(W(L / 2 - 1.1, gB), W(L / 2 + 1.1, gB), W(L / 2 + 1.1, gB + 3.6), W(L / 2 - 1.1, gB + 3.6), IN));
        for (const du of [-12, -7, 7, 12]) add(GLASS, K.quad(W(L / 2 + du - 1.1, gB + 1.3), W(L / 2 + du + 1.1, gB + 1.3), W(L / 2 + du + 1.1, gB + 3.2), W(L / 2 + du - 1.1, gB + 3.2), IN));
      }
      // 10 (1878-79, ESE) and 11 (1894, ENE): the near mirror pair off the artery east of the Observatory
      block([-2352, -2512], [-2298, -2484], 12, 5.5, 8.0, ROOF_D, { hoods: HOOD2, corr: 8 });
      block([-2352, -2539.3], [-2299, -2567.4], 12, 5.5, 8.0, ROOF_D, { hoods: HOOD2, corr: 8 });
      // 13 (1909-26): the one-storey concrete punishment block abutting the north-east of 10
      flatBlock([[-2322, -2503.3], [-2295.5, -2489.4], [-2295, -2498.2], [-2321, -2509.3]], 5.0, ROOF_D, TRIM, STONE);
      // 12 (1909-11): three storeys of pale reinforced concrete WSW between 6 and 7, a one-storey bottleneck to the hub,
      // the frontispiece on the west end
      flatBlock([[-2385.5, -2524.8], [-2394, -2515.5], [-2417, -2511.5], [-2421.5, -2522.5]], 4.5, ROOF_D, TRIM);
      concreteBar([-2418.8, -2516], [-2468.1, -2496.9], 14.3, 11.5, { front: 1 });
      // 14 (1926-27): three storeys of concrete bent into the space between 3 and 11, a boxy frontispiece on the east
      {
        const gc = gSpan([[-2342, -2553.5], [-2323, -2566], [-2294, -2577]])[1];
        concreteBar([-2343, -2552.8], [-2322, -2566.6], 10, 11.5, { g: gc });
        concreteBar([-2324.5, -2565.4], [-2294, -2577], 10, 11.5, { g: gc, front: 1 });
      }
      // 15 (1956-59, Death Row): two storeys of cut stone over concrete, flat, north from the east end of 2
      {
        const r15 = [[-2306, -2537], [-2293.5, -2537], [-2293.5, -2562.5], [-2306, -2554.5]];
        const g15 = flatBlock(r15, 7.5, ROOF_D, STONE, TRIM);
        const fe = K.frameFromEdge(r15[1], r15[2]);
        const we = K.windowsF(fe, 1.5, 24, 0, fe.local(-2300, -2550)[1] > 0 ? -1 : 1, g15 + 1.4, 2, 3.3, 8, 0.7, 1.2, { inset: -0.04 });
        add(GLASS, we.glass); add(TRIM, we.trim);
      }
      // the flat one-storey field round Cellblock 1: its yard wings (roofed over), the chapel and offices to the
      // south-west, the shoe shop wedge toward 10 (the orthophoto's dark field, OSM star)
      flatBlock([[-2371.2, -2499.7], [-2311.4, -2436.9], [-2308.5, -2437.8], [-2293.2, -2452.3], [-2296.2, -2455.4], [-2295.5, -2489.4], [-2343.5, -2510.5]], 4.2, ROOF_D, STONE);
      // the end of 3: the 1878 extension with its 1922 solarium (flat) and the red-roofed hospital block
      flatBlock([[-2322.3, -2595.9], [-2316.8, -2602.3], [-2304.5, -2590.2], [-2310.5, -2584.4]], 5.6, ROOF_D, STONE);
      {
        const c = [[-2304.5, -2590.2], [-2318.0, -2602.7], [-2303.2, -2618.2], [-2291.4, -2605.5]];
        const f = K.frameFromEdge(c[0], c[1]), loc = c.map((p) => f.local(p[0], p[1]));
        const u0 = Math.min(...loc.map((q) => q[0])), u1 = Math.max(...loc.map((q) => q[0])), v0 = Math.min(...loc.map((q) => q[1])), v1 = Math.max(...loc.map((q) => q[1]));
        const [lo, hi] = gSpan(c), base = lo - 1.5, g = hi;
        add(STONE, K.prism(c, base, g + 7.8));
        add(TRIM, K.corniceRing(c, g + 7.5, g + 7.8, 0.15));
        add(ROOF_R, K.hipF(f, u0, u1, v0, v1, g + 7.8, g + 11.2, 0.3));
      }
      // the Kitchen between 4 and 5: Haviland's two-storey keyhole-shaped pumphouse with its gable and spherical
      // finials, the round end to the north, one-storey cookhouse and oven additions to the south-east and north-east
      {
        const k0 = [-2405, -2585], k1 = [-2412, -2612];
        const r = block(k0, k1, 12, 8.5, 11.0, ROOF_D, {});
        for (const u of [0, r.L]) { const p = r.f.p(u, 0); add(TRIM, K.dome(0.55, p[0], r.g + 11.0, p[1], 10, 1, Math.PI)); }
        const rc = [-2413.2, -2616.5], [loR] = gSpan([rc]);
        add(STONE, K.cyl(6.2, 6.2, r.g + 8.5 - (loR - 1.5), 12, rc[0], loR - 1.5, rc[1]));
        add(TRIM, K.cyl(6.4, 6.4, 0.3, 12, rc[0], r.g + 8.2, rc[1]));
        add(ROOF_D, K.cone(6.5, 2.4, 12, rc[0], r.g + 8.5, rc[1]));
        flatBlock([[-2400.5, -2600], [-2394, -2598.5], [-2394, -2577], [-2400.5, -2578]], 4.5, ROOF_D, STONE);
        flatBlock([[-2408, -2619.5], [-2397, -2621], [-2395, -2605], [-2406.5, -2603.5]], 4.5, ROOF_D, STONE);
      }
      // the Industrial Building (Morris and Vaux, 1905-07) between 5 and 6: a two-and-a-half-storey L of rusticated
      // granite, gable roofs, three gable-end chimneys, a gabled skylight along the east wing's ridge (OSM way 75450143)
      {
        const fa = K.frameFromEdge([-2463.4, -2559], [-2463.4, -2576.7]);          // the long arm running north, ridge north-south
        const [loA, hiA] = gSpan([[-2470, -2576.7], [-2457, -2576.7], [-2470, -2547.5], [-2446, -2547.5], [-2446, -2559]]);
        const base = loA - 1.5, g = hiA;
        add(STONE, K.slabF(fa, 0, 17.7, -6.45, 6.45, base, g + 10));
        const ga = K.gableF(fa, 0, 17.7, -6.45, 6.45, g + 10, g + 13, true, 0.3);
        add(ROOF_D, ga.slopes); add(STONE, ga.ends);
        const fb = K.frameFromEdge([-2470.1, -2553.25], [-2446, -2553.25]);        // the foot running east (the east wing), ridge east-west
        add(STONE, K.slabF(fb, 0, 24.1, -5.75, 5.75, base, g + 10));
        const gb = K.gableF(fb, 0, 24.1, -5.75, 5.75, g + 10, g + 13, true, 0.3);
        add(ROOF_D, gb.slopes); add(STONE, gb.ends);
        add(TRIM, K.slabF(fa, -0.1, 17.8, -6.55, 6.55, g + 9.7, g + 10));
        add(TRIM, K.slabF(fb, -0.1, 24.2, -5.85, 5.85, g + 9.7, g + 10));
        add(TRIM, K.boxF(fb, 12.5, 0, 16, 1.4, g + 12.6, 0.5));
        add(GLASS, K.gableF(fb, 4.5, 20.5, -0.8, 0.8, g + 13.05, g + 13.7, true, 0.05).all);
        for (const [ff, u] of [[fa, 17.7], [fb, 0], [fb, 24.1]]) { const p = ff.p(u, 0); add(STONE, K.box(1.2, 3.2, 1.2, p[0], g + 13.4, p[1])); }
        for (const [ff, u0, u1, sd, hw] of [[fa, 1.5, 16.5, 1, 6.45], [fa, 1.5, 16.5, -1, 6.45], [fb, 13, 23, -1, 5.75], [fb, 1.5, 23, 1, 5.75]]) {
          const ww = K.windowsF(ff, u0, u1, sd * hw, sd, g + 1.8, 2, 4.0, Math.max(2, Math.round((u1 - u0) / 3.2)), 1.1, 2.2, { inset: -0.04, lintel: true });
          add(GLASS, ww.glass); add(TRIM, ww.trim);
        }
      }
      // the garage complex along 7's north-west range (one storey with a half-storey loft, concrete)
      flatBlock([[-2449.3, -2483.6], [-2455.8, -2490.9], [-2466.4, -2487.3], [-2474.6, -2481.3], [-2469.1, -2471.8], [-2474.8, -2465.8], [-2473.3, -2460.5], [-2460, -2448.5]], 4.8, ROOF_D, TRIM, STONE);
      // the greenhouse (1930s) between 13 and 2: a white concrete base under a glass gable
      {
        const fg = K.frameFromEdge([-2304.2, -2509.9], [-2293.9, -2509.6]);
        const [lo, hi] = gSpan([[-2304.2, -2512.6], [-2293.9, -2506.8]]);
        add(TRIM, K.slabF(fg, 0, 10.3, -2.8, 2.8, lo - 0.5, hi + 0.9));
        add(GLASS, K.slabF(fg, 0.1, 10.2, -2.7, 2.7, hi + 0.9, hi + 3.2));
        add(GLASS, K.gableF(fg, 0.1, 10.2, -2.7, 2.7, hi + 3.2, hi + 4.5, true, 0.1).all);
        for (let u = 0.1; u <= 10.3; u += 2.55) add(TRIM, K.boxF(fg, Math.min(10.2, u), 0, 0.12, 5.5, hi + 3.2, 0.14));
      }
      // the two sheds kept generic before (OSM ways 1502791621 and 75450140): single storey
      flatBlock([[-2448.6, -2617.3], [-2444.0, -2621.5], [-2433.9, -2610.1], [-2438.0, -2606.4]], 3.3, ROOF_L, TRIM);
      flatBlock([[-2469.0, -2514.5], [-2468.6, -2510.7], [-2462.9, -2511.2], [-2463.3, -2515.0]], 3.3, ROOF_D, STONE);
      // -- the corridors from the Center: to 2, 3, 4, 5, 6 and 7, the artery to 10 and 11, and the axial corridor
      // south to the V of 8 and 9
      for (const to of [[-2378.8, -2549], [-2362, -2551], [-2362, -2528.8], [-2352, -2512], [-2352, -2539.3], [-2394, -2513], [-2396, -2531.5], [-2395, -2546]]) spoke(fromHub(to, 4), to, 5.2);
      spoke([-2380.2, -2524], [-2381.6, -2495], 7.0, 5.2);

      const grp = B.done();
      for (const m of grp.children) if (m.material === SAND) m.userData.noShadow = true;
      return grp;
    }
  });
})();
