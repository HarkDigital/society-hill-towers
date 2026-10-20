// Round 213 rebuild (Mike, with a street photograph of Girard Station from Girard Avenue: "Can we add the stations for the
// elevated train tracks in Fishtown? There should be coverings that are lit from underneath and the structure holding up
// the tracks should be light blue."): the Market-Frankford Line's two Fishtown stations over Front Street, Girard (at Girard
// Avenue) and Berks (at Berks Street), both of the reconstruction's one design.
// Research:
//   the city basemap's points (landmarks.json: 'Market Frankford El Station - Girard' at (727, -2589), '- Berks' at
//     (959, -3669)); OSM: West Girard Avenue crosses the El's centreline at (725.3, -2590.2) between its two carriageways,
//     West Berks Street at (955.8, -3671.2); the El runs straight through both (EL_TRACK's (641, -2237) to (895, -3302)
//     and on to (1092, -4498)). OSM's 'Berks SEPTA MFL Station' footprint (scene_wide.json, 16 m, 35 points) wraps the El's
//     deck and its two street-level wings, so the generic extrusion stood a 16 m office box round the tracks: it is
//     skipped (the app keeps its roof note and its flight wall).
//   Mike's photograph: the station house sits on the El over the cross street, its long sides navy blue panels over a
//     silver band at the deck, silver tiled towers at its corners, the SEPTA mark and 'Girard Station' on the corner
//     tower, two windows of four lights high on the blue; under it the El's steel in light blue, a lattice truss across
//     the avenue; beyond it the platforms under their roofs.
//   Side platforms at the cars' floor outboard of the two tracks (the cars are 2.84 m wide, the tracks 3.7 m apart:
//     EL_RAIL), 110 m long for a six-car train (M-4 cars, 16.8 m), the house over the middle 40 m and a roof on columns
//     over the rest, a silver windscreen with a glass band along the outer edge, and LED strips under every roof and
//     under the house's ceiling, lit with the street lamps' photocell (api.lamp), the soffits and the platforms washed by
//     them, the windows lit after dark (api.night).
// The deck's height and direction come from the app (api.elAt: the El's own smoothed profile); the station is built level
// at the crossing and sheared to the profile's slope along the track.
(function () {
  const STATIONS = [
    { key: 'girard', name: 'Girard Station', at: [725.3, -2590.2] },
    { key: 'berks', name: 'Berks Station', at: [955.8, -3671.2] },
  ];
  // OSM's footprint at Berks (scene_wide.json 'Berks SEPTA MFL Station'): its record is skipped
  const BERKS_FOOT = [[926.82, -3647.21], [928.15, -3654.87], [929.4, -3662.69], [934.21, -3661.89], [934.77, -3659.14], [935.25, -3657.74], [935.67, -3656.5], [937.07, -3653.55], [940.1, -3653.12], [940.76, -3656.92], [941.42, -3660.69], [947.95, -3659.52], [948.24, -3661.13], [948.52, -3663.02], [949.41, -3668.65], [947.46, -3669.09], [948.63, -3676.03], [956.12, -3674.71], [953.42, -3658.62], [958.82, -3657.86], [961.77, -3675.25], [966.07, -3674.48], [968.01, -3674.13], [971.41, -3673.52], [972.78, -3670.73], [973.64, -3667.15], [973.81, -3663.46], [973.18, -3659.31], [971.81, -3655.78], [965.18, -3656.87], [961.97, -3637.95], [955.5, -3639.08], [958.08, -3654.49], [952.83, -3655.39], [950.84, -3643.54]];
  // the El's direction where the profile is not handed over (the scratch harness): the two straight runs
  const RUNS = [[[641, -2237], [895, -3302]], [[895, -3302], [1092, -4498]]];

  RB.add({
    id: 'elst', name: 'Girard and Berks El stations', center: STATIONS[0].at, aim: STATIONS[0].at,
    skip: [BERKS_FOOT],
    // Girard from Girard Avenue east of the El (the photograph's view), from over Front Street, and Berks from the south-east
    views: [[78, 60, 6, 9], [175, 140, 45, 8], [120, 130, 40, 8]],
    build(api) {
      const THREE = api.THREE, K = api.K, B = K.builder();
      const NIGHT = api.night || { value: 0 }, LAMP = api.lamp || NIGHT;
      // ---- materials: photo colours (K.mat converts them); the metallic ones keep the realism pass's wall art off
      const mSteel = K.mat('#6aa6b8', { rough: 0.6, metal: 0.3 });        // the El's light blue paint
      const mSteelDk = mSteel;   // the truss's web in the same paint (the test's twelve materials)
      const mNavy = K.mat('#22408f', { rough: 0.35, metal: 0.45 });       // the house's enamelled navy panels
      const mSilver = K.mat('#c8cbcd', { rough: 0.45, metal: 0.4 });      // the silver band, the corner towers' tiles, the windscreens
      const mWhite = mSilver;                                              // the window frames, the windscreen's mullions
      const mConc = K.mat('#b4b1a8', { rough: 0.9 });                     // the platforms' concrete
      const mEdge = K.mat('#d9b62c', { rough: 0.7, metal: 0.3 });         // the tactile strip at the edge
      const mRoof = K.mat('#55595c', { rough: 0.8, metal: 0.3 });         // the roofs' tops
      // the night: a fixed colour times the photocell (strips), or the night (windows); the soffits and the platforms take a
      // wash of the strips' light over their own colour
      const lit = (hex, k, src, key) => {
        const m = new THREE.MeshStandardMaterial({ color: new THREE.Color(K.stored(hex)), roughness: 0.5, metalness: 0.3, emissive: new THREE.Color(K.stored(hex, 1)), emissiveIntensity: k });
        const U = src === 'night' ? NIGHT : LAMP;
        m.onBeforeCompile = (sh) => {
          sh.uniforms.uElN = U;
          sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nuniform float uElN;')
            .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance *= uElN;');
        };
        m.customProgramCacheKey = () => 'elst-' + key;
        return m;
      };
      const mStrip = lit('#fff4de', 2.6, 'lamp', 'strip');          // the LED strips
      const mSoffit = lit('#d9dadb', 0.7, 'lamp', 'soffit');        // a roof's underside in their light
      const mFloorLit = lit('#c4c1b8', 0.4, 'lamp', 'floor');       // the platform under them
      const mPane = lit('#f3d9a8', 0.9, 'night', 'pane');            // the house's windows after dark
      mPane.color.set(K.stored('#28333c')); mPane.roughness = 0.15; mPane.metalness = 0.5;
      mFloorLit.color.set(K.stored('#b4b1a8')); mFloorLit.roughness = 0.9;
      mSoffit.color.set(K.stored('#b8bbbd'));

      const out = [];
      for (const S of STATIONS) {
        let signMat = null;   // one sign material a station, its two panels sharing it
        // ---- the El at the crossing: the rail bed's height and the track's direction
        let e = api.elAt ? api.elAt(S.at[0], S.at[1]) : null;
        if (!e) {
          let best = null;
          for (const [a, b] of RUNS) {
            const dx = b[0] - a[0], dz = b[1] - a[1], L2 = dx * dx + dz * dz, t = Math.max(0, Math.min(1, ((S.at[0] - a[0]) * dx + (S.at[1] - a[1]) * dz) / L2));
            const px = a[0] + dx * t, pz = a[1] + dz * t, d = Math.hypot(px - S.at[0], pz - S.at[1]);
            if (!best || d < best.d) best = { d, x: px, z: pz, ux: dx / Math.sqrt(L2), uz: dz / Math.sqrt(L2) };
          }
          e = { x: best.x, z: best.z, ux: best.ux, uz: best.uz, y: api.ground(best.x, best.z) + 9.2, slope: 0 };
        }
        const f = K.frame(e.x, e.z, Math.atan2(e.uz, e.ux)), Y = e.y;   // u along the track (toward Frankford), v across
        const W = (u, y, v) => { const q = f.p(u, v); return [q[0], y, q[1]]; };
        const RT = Y + 0.4, PT = RT + 1.05;               // the railhead, the platform's top (the cars' floor)
        const PE = 3.35, PO = 6.65, PL = 55, HL = 20;     // the platform's edge and outer side, its half-length, the house's
        const HV = 7.4, HB = Y - 1.45, HT = PT + 4.3;     // the house's half-width, its foot (the silver band's), its eave
        const g0 = Math.min(api.ground(e.x, e.z), api.ground(...f.p(0, HV)), api.ground(...f.p(0, -HV)));
        const TB = Math.max(HB - 2.3, g0 + 5.0);          // the truss's bottom chord, never under 5 m over the street
        const s0 = B;   // one builder for both stations
        const slab = (m, u0, u1, v0, v1, y0, y1) => s0.add(m, K.slabF(f, u0, u1, v0, v1, y0, y1));
        const beam = (m, p, q, w) => {   // a member between two points in the frame [u, y, v]
          const a = W(p[0], p[1], p[2]), b = W(q[0], q[1], q[2]);
          const d = new THREE.Vector3(b[0] - a[0], b[1] - a[1], b[2] - a[2]), L = d.length();
          const g = new THREE.BoxGeometry(w, L, w);
          g.applyMatrix4(new THREE.Matrix4().compose(new THREE.Vector3((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2),
            new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.normalize()), new THREE.Vector3(1, 1, 1)));
          s0.add(m, g);
        };
        for (const s of [-1, 1]) {
          const lo = (a, b) => (s > 0 ? [a, b] : [-b, -a]);
          // ---- the platform: its slab on a light blue girder, the tactile strip, lit concrete under the roofs
          const [pe0, pe1] = lo(PE, PO), [st0, st1] = lo(PE, PE + 0.6), [pg0, pg1] = lo(PO - 0.25, PO + 0.05);
          slab(mConc, -PL, PL, pe0, pe1, Y - 0.35, PT - 0.02);
          slab(mFloorLit, -PL + 3, PL - 3, ...lo(PE + 0.6, PO - 0.3), PT - 0.02, PT);
          slab(mEdge, -PL, PL, st0, st1, PT - 0.02, PT + 0.005);
          slab(mSteel, -PL, PL, pg0, pg1, Y - 1.25, Y - 0.35);   // the fascia girder under the outer edge
          // ---- the roofs beyond the house: columns on the outer side, the roof, its fascia, the strips under it
          for (const [u0, u1] of [[-PL + 3, -HL], [HL, PL - 3]]) {
            for (let u = u0 + 1; u <= u1 - 0.5; u += 7.5) slab(mSteel, u - 0.14, u + 0.14, ...lo(PO - 0.55, PO - 0.27), PT, PT + 3.3);
            slab(mRoof, u0, u1, ...lo(PE - 0.25, PO + 0.35), PT + 3.42, PT + 3.6);
            slab(mSoffit, u0, u1, ...lo(PE - 0.25, PO + 0.35), PT + 3.3, PT + 3.42);
            slab(mSilver, u0, u1, ...lo(PO + 0.35, PO + 0.45), PT + 3.15, PT + 3.65);   // the outer fascia
            slab(mSilver, u0, u1, ...lo(PE - 0.35, PE - 0.25), PT + 3.2, PT + 3.65);    // the inner fascia over the track
            for (const v of [PE + 0.9, PE + 2.3]) slab(mStrip, u0 + 0.4, u1 - 0.4, ...lo(v - 0.09, v + 0.09), PT + 3.26, PT + 3.3);
            // the windscreen: silver panels to the rail, a glass band over them
            slab(mSilver, u0, u1, ...lo(PO - 0.2, PO - 0.1), PT, PT + 1.15);
            slab(mPane, u0, u1, ...lo(PO - 0.18, PO - 0.12), PT + 1.15, PT + 2.5);
            for (let u = u0; u <= u1 + 0.01; u += 2.5) slab(mWhite, u - 0.04, u + 0.04, ...lo(PO - 0.22, PO - 0.08), PT + 1.15, PT + 2.5);
            slab(mWhite, u0, u1, ...lo(PO - 0.22, PO - 0.08), PT + 2.5, PT + 2.6);
          }
          // ---- the house over the cross street: the silver band at the deck, the navy panels, the corner towers
          const [hv0, hv1] = lo(HV - 0.3, HV);
          slab(mSilver, -HL, HL, hv0, hv1, HB, PT - 0.7);
          slab(mNavy, -HL + 2.6, HL - 2.6, hv0, hv1, PT - 0.7, HT);
          for (const uc of [-HL + 1.3, HL - 1.3]) {
            slab(mSilver, uc - 1.3, uc + 1.3, ...lo(HV - 0.3, HV + 0.25), HB - 0.2, HT + 1.1);
            for (let y = HB + 0.6; y < HT + 1.0; y += 0.62) slab(mRoof, uc - 1.32, uc + 1.32, ...lo(HV + 0.25, HV + 0.27), y, y + 0.025);   // the tiles' joints
          }
          // two windows of four lights high on the navy, at the house's end away from the sign
          for (const uw of [s * 6.5, s * 11.5]) {
            slab(mPane, uw - 1.3, uw + 1.3, ...lo(HV, HV + 0.04), PT + 1.6, PT + 3.5);
            slab(mWhite, uw - 1.42, uw + 1.42, ...lo(HV, HV + 0.07), PT + 1.48, PT + 1.6);
            slab(mWhite, uw - 1.42, uw + 1.42, ...lo(HV, HV + 0.07), PT + 3.5, PT + 3.62);
            for (const du of [-1.42, -0.06, 1.3]) slab(mWhite, uw + du, uw + du + 0.12, ...lo(HV, HV + 0.07), PT + 1.6, PT + 3.5);
            slab(mWhite, uw - 1.3, uw + 1.3, ...lo(HV, HV + 0.07), PT + 2.5, PT + 2.6);
          }
          // the sign on the corner tower at the house's other end, facing out
          {
            const uc = -s * (HL - 1.3), sg = signPlane(S.name, 2.3, 3.2, signMat);
            signMat = sg.material;
            const q = W(uc, PT + 2.2, s * (HV + 0.29));
            const nx = -Math.sin(f.a) * s, nz = Math.cos(f.a) * s;
            sg.geometry.rotateY(Math.atan2(nx, nz)); sg.geometry.translate(q[0], q[1], q[2]);   // in the geometry, as every other part (the review harness reads positions)
            sg.geometry.computeBoundingSphere();
            s0.addMesh(sg);
          }
          // ---- the truss across the street under the house: light blue chords, posts and diagonals on each outer side
          const vt = s * (HV - 0.45);
          beam(mSteel, [-HL, HB - 0.15, vt], [HL, HB - 0.15, vt], 0.42);
          beam(mSteel, [-HL, TB + 0.2, vt], [HL, TB + 0.2, vt], 0.42);
          const n = 8, du = 2 * HL / n;
          for (let k = 0; k <= n; k++) {
            const u = -HL + k * du;
            beam(mSteelDk, [u, TB + 0.2, vt], [u, HB - 0.15, vt], 0.3);
            if (k < n) beam(mSteelDk, k % 2 ? [u, TB + 0.2, vt] : [u, HB - 0.15, vt], k % 2 ? [u + du, HB - 0.15, vt] : [u + du, TB + 0.2, vt], 0.26);
          }
          // the columns at the house's corners, down to the street
          for (const u of [-HL, HL]) {
            const q = f.p(u, s * (HV - 0.45)), gy = api.ground(q[0], q[1]);
            slab(mSteel, u - 0.35, u + 0.35, s * (HV - 0.45) - 0.35, s * (HV - 0.45) + 0.35, gy - 0.6, TB + 0.2);
          }
        }
        // ---- the house's ends over the tracks (the trains run through under them), its roof and its ceiling's strips
        for (const u of [-HL, HL]) slab(mNavy, u - 0.15, u + 0.15, -HV, HV, PT + 3.1, HT);
        slab(mRoof, -HL - 0.2, HL + 0.2, -HV - 0.2, HV + 0.2, HT, HT + 0.25);
        slab(mSoffit, -HL, HL, -HV + 0.3, HV - 0.3, HT - 0.12, HT);
        for (const v of [-5.4, -4.1, 4.1, 5.4]) slab(mStrip, -HL + 0.5, HL - 0.5, v - 0.09, v + 0.09, HT - 0.16, HT - 0.12);
        // ---- the El's slope along the platforms: the profile's own, sheared in about the crossing
        out.push({ f, slope: e.slope || 0, u0: -PL - 1, u1: PL + 1, cx: e.x, cz: e.z, ux: e.ux, uz: e.uz });
        api.occupy(K.rect(f, -PL, PL, -HV - 0.5, HV + 0.5), HT + 1.1, 1);
      }
      const grp = B.done();
      // shear every vertex within a station's reach by its slope along the track (the El's profile: 0.1 to 0.4 per cent here)
      grp.traverse((o) => {
        if (!o.isMesh || !o.geometry || o.material.map) return;
        const P = o.geometry.attributes.position;
        for (let i = 0; i < P.count; i++) {
          const x = P.getX(i), z = P.getZ(i);
          for (const st of out) {
            const u = (x - st.cx) * st.ux + (z - st.cz) * st.uz, v = -(x - st.cx) * st.uz + (z - st.cz) * st.ux;
            if (u > st.u0 - 2 && u < st.u1 + 2 && Math.abs(v) < 14) { P.setY(i, P.getY(i) + st.slope * u); break; }
          }
        }
        P.needsUpdate = true; o.geometry.computeBoundingSphere();
      });
      for (const o of grp.children) if (o.material === mStrip || o.material === mPane) o.userData.noShadow = true;
      return grp;

      // the SEPTA mark over the station's name, on a white tile panel: the page draws it (no art file)
      function signPlane(name, w, h, mat0) {
        if (mat0) { const m0 = new THREE.Mesh(new THREE.PlaneGeometry(w, h), mat0); m0.userData.noShadow = true; return m0; }
        const cv = document.createElement('canvas'); cv.width = 512; cv.height = Math.round(512 * h / w);
        const g = cv.getContext('2d'), Wc = cv.width, Hc = cv.height;
        g.fillStyle = '#cfd2d4'; g.fillRect(0, 0, Wc, Hc);
        const m = Wc * 0.1, s = Wc * 0.8, y0 = Hc * 0.08;
        g.fillStyle = '#ffffff'; g.strokeStyle = '#c42a2f'; g.lineWidth = Wc * 0.02;
        g.beginPath(); g.rect(m, y0, s, s * 0.82); g.fill(); g.stroke();
        // the mark: a blue chevron over a red one, the two arrows of the S
        const cx = Wc / 2, cy = y0 + s * 0.41, a = s * 0.32;
        g.fillStyle = '#1f3d8f';
        g.beginPath(); g.moveTo(cx - a, cy - a * 0.15); g.lineTo(cx - a * 0.1, cy - a * 0.85); g.lineTo(cx + a * 0.55, cy - a * 0.85); g.lineTo(cx - a * 0.2, cy - a * 0.2); g.lineTo(cx + a * 0.2, cy + a * 0.05); g.lineTo(cx - a * 0.35, cy + a * 0.05); g.closePath(); g.fill();
        g.fillStyle = '#d0202e';
        g.beginPath(); g.moveTo(cx + a, cy + a * 0.15); g.lineTo(cx + a * 0.1, cy + a * 0.85); g.lineTo(cx - a * 0.55, cy + a * 0.85); g.lineTo(cx + a * 0.2, cy + a * 0.2); g.lineTo(cx - a * 0.2, cy - a * 0.05); g.lineTo(cx + a * 0.35, cy - a * 0.05); g.closePath(); g.fill();
        g.fillStyle = '#1f3d8f'; g.textAlign = 'center'; g.textBaseline = 'middle';
        const words = name.split(' ');
        g.font = '700 ' + Math.round(Wc * 0.15) + 'px Arial, sans-serif';
        g.fillText(words[0], Wc / 2, y0 + s * 0.82 + Hc * 0.11, Wc * 0.9);
        g.fillText(words.slice(1).join(' '), Wc / 2, y0 + s * 0.82 + Hc * 0.22, Wc * 0.9);
        const tex = new THREE.CanvasTexture(cv);
        tex.encoding = THREE.sRGBEncoding; tex.anisotropy = 4;
        const mat = new THREE.MeshStandardMaterial({ map: tex, roughness: 0.5, metalness: 0.1 });
        const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h), mat);
        mesh.userData.noShadow = true;
        return mesh;
      }
    },
  });
})();
