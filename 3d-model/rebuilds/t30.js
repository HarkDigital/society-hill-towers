// 30th Street Station (Pennsylvania Railroad; Graham, Anderson, Probst and White; opened 1933): a PROPOSED model.
// Everything is laid out in the station's own frame: u runs east along the Market Street front (9.2 degrees off
// the scene's x axis, fitted to the OSM footprint's long edges), v runs south along 30th Street. Local origin is
// scene (-3178, -1160). Key planes, measured from the OSM footprint and building:parts (ways 32272623, 749651799,
// 749651800): east front u 59.0, west front u -38.6, porticos out to u 81.2 / -59.9 over v 2.6 to 48.2, main block
// v -45.5 (north) to 100.6 (Market Street), the SEPTA upper-level shed v -93.3 to -45.5, its west annex over
// 30th Street to u -127.5 (v -87.2 to -44.2), opened for the app's raised North 30th Street deck at u -97 to -78
// and closed there with glazed end walls.
// Sources: Philadelphia Register interior nomination (2018), Great American Stations, WHYY facade restoration story,
// The Lighting Practice (the 2002 exterior lighting: "warm and cool light sources"), Wikimedia Commons photos
// (the east front from the JFK Boulevard bridge, the west portico with its flagpoles, the night view from the
// Cira Centre side) and the Commons east elevation, OSM, Esri World Imagery.
//
// Revision 2 (after review): the night. Four of the materials carry small shader patches (stand-ins for the app's
// facade and room shaders, which a rebuild's plain materials do not run): the limestone takes coursed ashlar joints, the stone takes a floodlight wash
// after dark (cool white over the whole block, as the night photo shows, with the porticos and the attic at full
// strength), the glass draws its steel sash as a pattern and lights its rooms after dark (a fraction of the office
// storeys, the concourse's portico windows and doors always, the upper level's platforms dimly). The patches read
// the app's own lamp photocell (lampUniform, api.lamp) so they turn on with the street lights. Per-part data rides in
// the uv attribute (the builder keeps position, normal and uv only): uv.x = kind * 4 + u01, uv.y = A * 2 + v01.
// In the app only, the Rail Stations pin for 30th Street is lifted onto the pavilion roof (api.pinAt below: the app
// moves the stop's anchor where the rail stops are posted, 'Posting the transit stops').
(function () {
  const A_ = 9.2 * Math.PI / 180, OX = -3178, OZ = -1160, C = Math.cos(A_), S = Math.sin(A_);
  const P = (u, v) => [+(OX + u * C - v * S).toFixed(1), +(OZ + u * S + v * C).toFixed(1)];
  // the app's own footprint for the station (scene_wide.json): every generic record centred inside it is skipped
  const FOOT = [[-3296.9, -1223.6], [-3290.0, -1266.2], [-3202.7, -1252.5], [-3202.0, -1256.3], [-3201.6, -1258.3], [-3196.5, -1257.6], [-3193.4, -1257.1], [-3186.5, -1255.9], [-3105.0, -1242.2], [-3105.4, -1239.5], [-3112.4, -1195.9], [-3113.2, -1190.8], [-3120.1, -1147.4], [-3114.3, -1146.5], [-3109.2, -1145.8], [-3098.3, -1144.0], [-3101.5, -1124.2], [-3105.5, -1100.0], [-3116.2, -1101.6], [-3121.0, -1102.3], [-3128.2, -1103.4], [-3136.5, -1051.2], [-3180.0, -1058.4], [-3231.4, -1066.9], [-3223.9, -1117.8], [-3227.5, -1118.5], [-3234.1, -1119.8], [-3245.0, -1121.9], [-3241.1, -1145.1], [-3237.4, -1167.1], [-3226.1, -1165.6], [-3219.8, -1164.7], [-3216.3, -1164.2], [-3209.6, -1210.2]];

  RB.add({
    id: 't30', name: '30th Street Station', center: P(10, 25),
    skip: [FOOT],
    // the east portico and the south wing from over the Market Street Bridge (the view Philadelphians know), the west
    // portico from 30th Street, and the whole block from the south-west over 30th and Market
    views: [[108, 240, 50, 16], [262, 165, 26, 15], [236, 300, 110, 12]],
    build(api) {
      const { THREE, K } = api;
      const f = K.frame(OX, OZ, A_);
      const B_ = K.builder();
      const add = (m, g) => B_.add(m, g);

      // ---- ground: stand the block on the highest ground under the main building, run the plinth below the lowest
      const gAt = (u, v) => { const p = f.p(u, v); const g = api.ground(p[0], p[1]); return isFinite(g) ? g : 0; };
      let gMax = -1e9, gMin = 1e9;
      for (let u = -38; u <= 59; u += 8) for (let v = -45; v <= 100; v += 8) { const g = gAt(u, v); gMax = Math.max(gMax, g); gMin = Math.min(gMin, g); }
      for (let u = -60; u <= 81; u += 5) for (const v of [3, 25, 48]) gMin = Math.min(gMin, gAt(u, v));
      for (let u = -38; u <= 59; u += 8) gMin = Math.min(gMin, gAt(u, -93));
      const B = gMax + 0.05, BF = gMin - 1.5;          // floor level, foundation bottom
      const y = (h) => B + h;

      // ---- dimensions (metres over the floor level B)
      const uE = 59.0, uW = -38.6, uEP = 81.2, uWP = -59.9, vN = -45.5, vS = 100.6, vP0 = 2.6, vP1 = 48.2;
      const D = 0.6, D2 = D + 0.25;                    // pier depth, core inset behind the glass
      // window heads at 15.6 under a 3.3 m plain band and frieze (the east-entrance photo); storeys of 2.8 m
      const WIN = { g0: 1.2, g1: 3.6, t0: 4.4, t1: 15.6, band: 17.6, frz: 18.9, cor: 19.8, top: 22.9 };
      const SPAN = [7.2, 10.0, 12.8];                  // spandrels on the storey lines
      const HT = 23.7;                                  // corner pavilions stand a little proud of the parapet
      // the entablature is 6 m (col1 22.4 to cor 28.4), the attic's plain face takes up the difference
      const PAV = { col0: 0.3, col1: 22.4, arch: 23.7, frz: 26.7, cor: 28.4, att: 34.9, cap: 35.5 };

      // ---- materials. Photo colours; the kit's calibration (srgb to linear x 0.88) matches the app's pipeline
      const NIGHT = { value: 0 };
      const lin = (hex, g) => new THREE.Color(K.stored(hex, g == null ? 0.88 : g));
      const fl = (x) => { const s = (+x).toFixed(4); return s.indexOf('.') < 0 ? s + '.0' : s; };
      const v3 = (c) => 'vec3(' + fl(c.r) + ', ' + fl(c.g) + ', ' + fl(c.b) + ')';
      // the floodlights: the 2002 scheme's cool white over the stone (the night photo from the Cira side reads a
      // neutral to faintly green white, even over wings and pavilion), warm at the portico doors and lanterns
      const FLOOD = lin('#d6e2ea', 1), FLOOD_K = 0.66, WING_K = 0.72, SHED_K = 0.28;
      const ROOM = lin('#f7e9d0', 1), ROOM_K = 0.55, LIT = 0.42;        // office floors behind the steel sash
      const HALL = lin('#ffcf94', 1), HALL_K = 1.3;                     // the concourse's warm chandelier light
      const SASH = lin('#6f8a7c');                                      // green-grey steel sash (r8, r3 photos)
      const WHITE = lin('#d6d6d0'), PLANT = lin('#8a9096');
      const F_COMMON = [
        'uniform float uNight;',
        'varying vec3 vWP; varying vec3 vWN; varying vec2 vDat;',
        'float t30h(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }',
        'vec2 t30loc(vec3 p) { vec2 d = p.xz - vec2(' + fl(OX) + ', ' + fl(OZ) + '); return vec2(d.x * ' + fl(C) + ' + d.y * ' + fl(S) + ', -d.x * ' + fl(S) + ' + d.y * ' + fl(C) + '); }',
        'float t30kind() { return floor(vDat.x / 4.0 + 0.0001); }',
        // the floodlight's reach over a surface: every wall and soffit, never a roof (the portico floors a little); the porticos (east of the east
        // concourse wall, west of the west one) and the pavilion above the wings take it whole, the wings a little
        // less, the upper level's base a glimmer
        'vec3 t30flood(vec3 p, vec3 n) {',
        '  vec2 L = t30loc(p); float yy = p.y - ' + fl(B) + ';',
        '  float band = step(' + fl(vP0 - 1.8) + ', L.y) * step(L.y, ' + fl(vP1 + 1.8) + ');',
        '  float port = band * max(step(' + fl(uE - 0.8) + ', L.x), step(L.x, ' + fl(uW + 0.8) + '));',
        '  float face = max(1.0 - smoothstep(0.3, 0.75, n.y), port * 0.55 * step(yy, 2.0));',   // the portico floors take the doors' spill
        '  float att = band * step(' + fl(WIN.top - 0.4) + ', yy);',
        '  float w = L.y < ' + fl(vN - 0.3) + ' ? ' + fl(SHED_K) + ' : mix(' + fl(WING_K) + ', 1.0, max(port, att));',
        '  return ' + v3(FLOOD) + ' * (w * mix(0.85, 1.0, clamp(yy / 35.5, 0.0, 1.0)) * face);',
        '}'
      ].join('\n');
      const VERT = (sh) => {
        sh.uniforms.uNight = NIGHT;
        sh.vertexShader = sh.vertexShader
          .replace('#include <common>', '#include <common>\nvarying vec3 vWP; varying vec3 vWN; varying vec2 vDat;')
          .replace('#include <project_vertex>', '#include <project_vertex>\nvWP = (modelMatrix * vec4(transformed, 1.0)).xyz; vWN = normalize(mat3(modelMatrix) * objectNormal); vDat = uv;');
        sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\n' + F_COMMON);
      };
      const FLOOD_GLSL = '#include <lights_fragment_end>\nreflectedLight.indirectDiffuse += diffuseColor.rgb * t30flood(vWP, normalize(vWN)) * (uNight * ' + fl(FLOOD_K) + ');';
      const mk = (name, hex, o, colorCode, lightCode, emisCode) => {
        const m = new THREE.MeshStandardMaterial({ color: lin(hex), roughness: o.rough == null ? 0.85 : o.rough, metalness: o.metal || 0 });
        m.onBeforeCompile = (sh) => {
          VERT(sh);
          if (colorCode) sh.fragmentShader = sh.fragmentShader.replace('#include <color_fragment>', '#include <color_fragment>\n' + colorCode);
          if (lightCode) sh.fragmentShader = sh.fragmentShader.replace('#include <lights_fragment_end>', lightCode);
          if (emisCode) sh.fragmentShader = sh.fragmentShader.replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\n' + emisCode);
        };
        m.customProgramCacheKey = () => 't30-' + name;
        return m;
      };
      // Alabama limestone walls in coursed ashlar: 0.62 m courses, 1.55 m blocks broken on alternate courses, a faint
      // tone per block; the joints keep their average when they shrink under a pixel and fade out below 2.5 px a course
      const JOINTS = [
        'vec3 jn = normalize(vWN);',
        'if (abs(jn.y) < 0.5) {',
        '  vec2 jl = t30loc(vWP);',
        '  vec2 jd = vec2(jn.x * ' + fl(C) + ' + jn.z * ' + fl(S) + ', -jn.x * ' + fl(S) + ' + jn.z * ' + fl(C) + ');',
        '  float jh = abs(jd.x) > abs(jd.y) ? jl.y : jl.x;',
        '  float jy = vWP.y - ' + fl(B) + ';',
        '  float jrow = floor(jy / 0.62);',
        '  float jcx = jh / 1.55 + 0.5 * mod(jrow, 2.0);',
        '  float dy = abs(fract(jy / 0.62 + 0.5) - 0.5) * 0.62, dx = abs(fract(jcx + 0.5) - 0.5) * 1.55;',
        '  float fy = max(fwidth(jy), 1e-4), fx = max(fwidth(jh), 1e-4), jw = 0.02;',
        '  float wy = max(jw, 0.5 * fy), wx = max(jw, 0.5 * fx);',
        '  float ly = (1.0 - smoothstep(wy - 0.5 * fy, wy + 0.5 * fy, dy)) * jw / wy;',
        '  float lx = (1.0 - smoothstep(wx - 0.5 * fx, wx + 0.5 * fx, dx)) * jw / wx;',
        '  float jf = 1.0 - smoothstep(0.62 / 5.0, 0.62 / 2.5, max(fy, fx));',
        '  float jt = 1.0 + (t30h(vec2(jrow, floor(jcx))) - 0.5) * 0.07 * jf;',
        '  diffuseColor.rgb *= jt * (1.0 - 0.28 * max(ly, lx) * jf);',
        '}'
      ].join('\n');
      // trim: flag 1 the corona and dentil course in their own shade (0.85), flag 2 the attic's stone grilles (0.66, the limestone's 0.8)
      const TRIMFLAG = 'float t30tk = t30kind(); if (abs(t30tk - 1.0) < 0.5) diffuseColor.rgb *= 0.85; else if (abs(t30tk - 2.0) < 0.5) diffuseColor.rgb *= 0.66;';
      // glass: the steel sash as a pattern (cells per kind), a little tone per pane; after dark the rooms light
      const GLASS = [
        'float gk = t30kind(); float gA = floor((vDat.y + 0.001) / 2.0);',
        'vec2 g01 = vec2(vDat.x - gk * 4.0, vDat.y - gA * 2.0);',
        'vec2 gcell = vec2(0.0); float gst = 1.0, gglw = 0.0, grm = 0.0, ghall = 0.0;',
        'if (abs(gk - 1.0) < 0.5) { gcell = vec2(6.0, 12.0); gst = 4.0; grm = 1.0; }',          // wing bay, three storeys and the ground-floor mezzanine
        'else if (abs(gk - 2.0) < 0.5) { gcell = vec2(4.0, 3.0); grm = 1.0; }',                          // ground-floor window
        'else if (abs(gk - 3.0) < 0.5) { gcell = vec2(2.0, 3.0); grm = 1.0; }',                          // court and attic lights
        'else if (abs(gk - 4.0) < 0.5) { gcell = vec2(5.0, 14.0); gglw = 0.42; ghall = 1.0; }',            // portico rear-wall window
        'else if (abs(gk - 5.0) < 0.5) { gcell = vec2(4.0, 10.0); gglw = 0.55; ghall = 1.0; }',            // concourse clerestory
        'else if (abs(gk - 6.0) < 0.5) { gcell = vec2(max(gA, 1.0), 3.0); gglw = 0.3; }',                  // upper-level side glazing
        'else if (abs(gk - 7.0) < 0.5) { gcell = vec2(4.0, 12.0); gst = 4.0; grm = 1.0; }',          // corner pavilion window
        'else if (abs(gk - 8.0) < 0.5) { gcell = vec2(4.0, 5.0); gglw = 0.5; }',                           // north waiting room
        'else if (abs(gk - 9.0) < 0.5) { gcell = vec2(max(gA, 1.0), 2.0); gglw = 0.35; }',                 // monitors, skylight
        'else if (abs(gk - 10.0) < 0.5) { gcell = vec2(3.0, 4.0); gglw = 1.0; ghall = 1.0; }',             // bronze-framed doors
        'float gbar = 0.0;',
        'if (gcell.x > 0.0) {',
        '  vec2 q = g01 * gcell; vec2 dd = abs(fract(q + 0.5) - 0.5);',
        '  vec2 fw = max(fwidth(q), vec2(1e-4)); vec2 wb = max(vec2(0.07), 0.5 * fw);',
        '  vec2 bb = (1.0 - smoothstep(wb - 0.5 * fw, wb + 0.5 * fw, dd)) * (0.07 / wb);',
        '  gbar = mix(max(bb.x, bb.y), 0.26, smoothstep(0.3, 0.6, max(fw.x, fw.y)));',
        '  diffuseColor.rgb *= 0.88 + 0.24 * t30h(floor(q) + vec2(gA * 1.7, gk));',
        '  diffuseColor.rgb = mix(diffuseColor.rgb, ' + v3(SASH) + ', gbar);',
        '}',
        'float groom = 0.0;',
        'if (grm > 0.5) { float st = floor(clamp(g01.y, 0.0, 0.999) * gst); groom = step(' + fl(1 - LIT) + ', t30h(vec2(gA, st + 3.0))) * (0.65 + 0.7 * t30h(vec2(st + 5.0, gA + 11.0))); }',
        'float gglow = max(groom, gglw) * (1.0 - gbar);'
      ].join('\n');
      const GLASS_EMIS = 'totalEmissiveRadiance += (ghall > 0.5 ? ' + v3(HALL) + ' * ' + fl(HALL_K) + ' : ' + v3(ROOM) + ' * ' + fl(ROOM_K) + ') * gglow * uNight;';

      const mLime = mk('lime', '#aba395', {}, JOINTS, FLOOD_GLSL);            // Alabama limestone walls (photo mean, r3/r6)
      const mTrim = mk('trim', '#b8b0a2', {}, TRIMFLAG, FLOOD_GLSL);          // columns, cornices, caps, a shade fresher
      const mBase = mk('base', '#8e8980', {}, null, FLOOD_GLSL);              // granite base course, podiums, piers
      const mGlass = mk('glass', '#3b4a47', { rough: 0.22, metal: 0.35 }, GLASS, null, GLASS_EMIS);   // steel-sash glazing
      const mMetal = K.mat('#6f8a7c', { rough: 0.6, metal: 0.3 });           // green-grey spandrels, transoms, sash frames
      const mRoof = mk('roof', '#6b6358', {}, 'if (abs(t30kind() - 1.0) < 0.5) diffuseColor.rgb = ' + v3(WHITE) + ';');   // weathered tan; flag 1 white membrane
      const mShed = mk('shed', '#5a5e61', { rough: 0.6, metal: 0.25 }, 'if (abs(t30kind() - 1.0) < 0.5) diffuseColor.rgb = ' + v3(PLANT) + ';');   // shed steel; flag 1 rooftop plant, poles

      // ---- part data in the uv attribute (see the header)
      let seed = 30;
      const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
      const tag = (g, kind, A) => {
        const a = g.attributes.uv;
        for (let i = 0; i < a.count; i++) a.setXY(i, kind * 4 + Math.min(1, Math.max(0, a.getX(i))), (A || 0) * 2 + Math.min(1, Math.max(0, a.getY(i))));
        return g;
      };
      const seedA = () => Math.floor(rnd() * 2000);

      // ---- local helpers
      const W = (u, v, yy) => { const p = f.p(u, v); return [p[0], yy, p[1]]; };
      const sg = (u0, u1, v0, v1, y0, y1) => K.slabF(f, Math.min(u0, u1), Math.max(u0, u1), Math.min(v0, v1), Math.max(v0, v1), y0, y1);
      const slab = (m, u0, u1, v0, v1, y0, y1) => add(m, sg(u0, u1, v0, v1, y0, y1));
      const rectRing = (u0, u1, v0, v1) => [f.p(u0, v0), f.p(u1, v0), f.p(u1, v1), f.p(u0, v1)];
      // a face: the plane ax = at (the footprint line), outward sign s; t runs along the face, n is the offset
      // outward from the footprint line (negative = inside)
      const face = (ax, at, s) => ({ ax, at, s });
      const UV = (F, t, n) => F.ax === 'u' ? [F.at + F.s * n, t] : [t, F.at + F.s * n];
      const fg = (F, t0, t1, n0, n1, y0, y1) => { const a = UV(F, t0, n0), b = UV(F, t1, n1); return sg(a[0], b[0], a[1], b[1], y0, y1); };
      const fbox = (m, F, t0, t1, n0, n1, y0, y1) => add(m, fg(F, t0, t1, n0, n1, y0, y1));
      const fq = (F, t0, t1, n, y0, y1) => {
        const a = UV(F, t0, n), b = UV(F, t1, n), c = UV(F, (t0 + t1) / 2, n - 1);
        return K.quad(W(a[0], a[1], y0), W(b[0], b[1], y0), W(b[0], b[1], y1), W(a[0], a[1], y1), W(c[0], c[1], (y0 + y1) / 2));
      };
      const fquad = (m, F, t0, t1, n, y0, y1) => add(m, fq(F, t0, t1, n, y0, y1));
      const glass = (F, t0, t1, n, y0, y1, kind, A) => add(mGlass, tag(fq(F, t0, t1, n, y0, y1), kind, A == null ? seedA() : A));

      // a wing facade: tall three-storey window bays between flat limestone piers, a shorter ground-floor window
      // under each, green-grey spandrels on the storey lines (the steel sash itself is the glass's pattern), then the
      // plain band, the frieze, the cornice and the attic with its small lights
      const wingFace = (F, t0, t1, bays) => {
        const edges = [t0];
        for (const b of bays) edges.push(b.c - b.w / 2, b.c + b.w / 2);
        edges.push(t1);
        // piers up to the window heads, then one wall over the whole face from the heads to the parapet, so no seam
        // runs up from a window's corner
        for (let i = 0; i < edges.length; i += 2) if (edges[i + 1] - edges[i] > 0.01) fbox(mLime, F, edges[i], edges[i + 1], -D2, 0, BF, y(WIN.t1));
        for (const b of bays) {
          const a = b.c - b.w / 2, e = b.c + b.w / 2;
          fbox(mLime, F, a, e, -D2, 0, BF, y(WIN.g0));
          fbox(mLime, F, a, e, -D2, 0, y(WIN.g1), y(WIN.t0));
          glass(F, a, e, -D, y(WIN.g0), y(WIN.g1), 2);
          glass(F, a, e, -D, y(WIN.t0), y(WIN.t1), 1);
          for (const yy of SPAN) fbox(mMetal, F, a, e, -D - 0.02, -D + 0.1, y(yy - 0.3), y(yy + 0.3));
          fbox(mTrim, F, a - 0.15, e + 0.15, -D, 0.12, y(WIN.t0 - 0.25), y(WIN.t0));   // stone sill
          glass(F, b.c - 0.9, b.c + 0.9, 0.03, y(20.5), y(21.8), 3);                    // attic light
        }
        // frieze and attic flush with the piers, the projecting cornice (its corona in shade), the parapet cap
        fbox(mLime, F, t0, t1, -D2, 0, y(WIN.t1), y(WIN.top));
        fbox(mTrim, F, t0, t1, -0.1, 0.12, y(WIN.band), y(WIN.frz));
        fbox(mTrim, F, t0, t1, -0.1, 0.45, y(WIN.frz), y(WIN.frz + 0.35));
        add(mTrim, tag(fg(F, t0, t1, -0.1, 0.9, y(WIN.frz + 0.35), y(WIN.cor)), 1));
        fbox(mTrim, F, t0, t1, -0.5, 0.2, y(WIN.top), y(WIN.top + 0.4));
      };
      const bayRun = (c0, c1, n, w) => { const out = [], p = (c1 - c0) / n; for (let i = 0; i < n; i++) out.push({ c: c0 + p * (i + 0.5), w: w || Math.min(4.0, p * 0.62) }); return out; };

      // ---- the main block: a U of offices round a light court on each side of the concourse
      const CU0 = -21, CU1 = 41, CN = -28, CS = 66, HC = 9.0;   // court spans and the court floor (the ticket lobby roof)
      const core = (u0, u1, v0, v1) => slab(mLime, u0, u1, v0, v1, BF, y(WIN.top));
      core(uW + D2, uE - D2, vN + D2, CN);             // north bar
      core(uW + D2, CU0, CN, vP0);                      // north wing, west arm
      core(CU1, uE - D2, CN, vP0);                      // north wing, east arm
      core(uW + D2, uE - D2, CS, vS - D2);              // south bar
      core(uW + D2, CU0, vP1, CS);                      // south wing, west arm
      core(CU1, uE - D2, vP1, CS);                      // south wing, east arm
      slab(mLime, CU0, CU1, CN, vP0, BF, y(HC));        // court floors
      slab(mLime, CU0, CU1, vP1, CS, BF, y(HC));
      slab(mRoof, CU0 + 0.3, CU1 - 0.3, CN + 0.3, vP0 - 0.3, y(HC), y(HC + 0.12));
      add(mRoof, tag(sg(CU0 + 0.3, CU1 - 0.3, vP1 + 0.3, CS - 0.3, y(HC), y(HC + 0.12)), 1));   // south court: white membrane
      // the Ticket Lobby's skylight in the north court (45 by 200 feet under a 20-foot ceiling)
      slab(mTrim, CU0 + 3, CU1 - 3, -14.5, -1.5, y(HC), y(HC + 1.1));
      add(mGlass, tag(sg(CU0 + 4, CU1 - 4, -13.5, -2.5, y(HC + 1.1), y(HC + 1.9)), 9, 12));
      // the south court is a lower roof full of plant (Esri z19): two rows of grey units
      for (let i = 0; i < 5; i++) for (const vv of [54, 61]) { const uc = CU0 + 7 + i * 12; add(mShed, tag(sg(uc - 2.2, uc + 2.2, vv - 1.6, vv + 1.6, y(HC + 0.12), y(HC + 2.0)), 1)); }
      // court walls: plain punched office windows, three floors above the court roof. K.windowsF works in a frame
      // whose u runs along the wall; the glass sits 3 cm proud of the solid wall (a negative inset)
      const courtWall = (u0, v0, u1, v1, n) => {
        const fr = K.frameFromEdge(f.p(u0, v0), f.p(u1, v1)), L = Math.hypot(u1 - u0, v1 - v0);
        const cc = f.p((CU0 + CU1) / 2, v0 < 25 ? (CN + vP0) / 2 : (vP1 + CS) / 2);
        const r = K.windowsF(fr, 2, L - 2, 0, fr.local(cc[0], cc[1])[1] > 0 ? 1 : -1, y(HC + 1.6), 3, 4.0, n, 1.6, 2.2, { inset: -0.03, sill: false });
        for (const g of r.glass) add(mGlass, tag(g, 3, seedA()));
      };
      courtWall(CU0, CN, CU1, CN, 13);                  // north court, north wall
      courtWall(CU0, CN, CU0, vP0, 6);                  // west wall
      courtWall(CU1, CN, CU1, vP0, 6);                  // east wall
      courtWall(CU0, CS, CU1, CS, 13);                  // south court, south wall
      courtWall(CU0, vP1, CU0, CS, 3);
      courtWall(CU1, vP1, CU1, CS, 3);

      // wing roofs (the south wing's white membrane, the north wing weathered tan as in the imagery), parapet caps
      // round the courts, rooftop plant in grey metal in units of about 4 by 3 m
      const roofPlate = (u0, u1, v0, v1, white) => add(mRoof, tag(sg(u0 + 0.3, u1 - 0.3, v0 + 0.3, v1 - 0.3, y(WIN.top), y(WIN.top + 0.15)), white ? 1 : 0));
      roofPlate(uW, uE, vN, CN); roofPlate(uW, CU0, CN, vP0); roofPlate(CU1, uE, CN, vP0);
      roofPlate(uW, uE, CS, vS, true); roofPlate(uW, CU0, vP1, CS, true); roofPlate(CU1, uE, vP1, CS, true);
      for (const [u0, u1, v0, v1] of [[CU0, CU1, CN - 0.5, CN], [CU0, CU1, CS, CS + 0.5], [CU0 - 0.5, CU0, CN, vP0], [CU1, CU1 + 0.5, CN, vP0], [CU0 - 0.5, CU0, vP1, CS], [CU1, CU1 + 0.5, vP1, CS]]) slab(mTrim, u0, u1, v0, v1, y(WIN.top), y(WIN.top + 0.4));
      const plant = (u, v, a, b, h) => add(mShed, tag(sg(u - a / 2, u + a / 2, v - b / 2, v + b / 2, y(WIN.top + 0.15), y(WIN.top + 0.15 + h)), 1));
      plant(-8, -37, 5, 3.5, 2.2); plant(-2, -37, 4, 3, 2.0); plant(22, -38, 4.5, 3.5, 2.0);
      for (let i = 0; i < 4; i++) plant(-5 + i * 4.8, 80, 4, 3, 2.4);          // the old 14 by 8 m block, now four units
      for (let i = 0; i < 3; i++) plant(22 + i * 4.6, 84, 3.8, 3, 2.0);
      for (let i = 0; i < 2; i++) plant(-22 + i * 4.4, 88, 3.6, 2.8, 1.8);
      plant(44, 72, 4, 3, 1.8); plant(44, 77, 4, 3, 1.8);

      // outer wing faces
      const fE = face('u', uE, 1), fW = face('u', uW, -1), fS = face('v', vS, 1), fN = face('v', vN, -1);
      const CB = 8.5;                                   // corner pavilion width
      wingFace(fE, vN + CB, vP0, bayRun(vN + CB, vP0 - 3.6, 6));
      wingFace(fE, vP1, vS - CB, bayRun(vP1 + 3.6, vS - CB, 6));
      wingFace(fW, vN + CB, vP0, bayRun(vN + CB, vP0 - 3.6, 6));
      wingFace(fW, vP1, vS - CB, bayRun(vP1 + 3.6, vS - CB, 6));
      wingFace(fS, uW + CB, uE - CB, bayRun(uW + CB, uE - CB, 12));
      wingFace(fN, uW + CB, uE - CB, bayRun(uW + CB, uE - CB, 12));

      // corner pavilions: solid blocks proud of both faces with one framed window each way
      const corner = (su, sv) => {
        const ua = su > 0 ? uE - CB : uW - 0.5, ub = su > 0 ? uE + 0.5 : uW + CB;
        const va = sv > 0 ? vS - CB : vN - 0.5, vb = sv > 0 ? vS + 0.5 : vN + CB;
        slab(mLime, ua, ub, va, vb, BF, y(HT));
        slab(mTrim, ua - 0.25, ub + 0.25, va - 0.25, vb + 0.25, y(HT), y(HT + 0.45));
        slab(mRoof, ua + 0.5, ub - 0.5, va + 0.5, vb - 0.5, y(HT + 0.45), y(HT + 0.5));
        add(mTrim, tag(sg(ua - 0.9, ub + 0.9, va - 0.9, vb + 0.9, y(WIN.frz + 0.35), y(WIN.cor)), 1));
        slab(mTrim, ua - 0.12, ub + 0.12, va - 0.12, vb + 0.12, y(WIN.band), y(WIN.frz));
        // the window on each outer face
        const Fu = face('u', su > 0 ? uE + 0.5 : uW - 0.5, su), Fv = face('v', sv > 0 ? vS + 0.5 : vN - 0.5, sv);
        const tc = (va + vb) / 2, uc = (ua + ub) / 2;
        for (const [F, c] of [[Fu, tc], [Fv, uc]]) {
          const a = c - 1.5, e = c + 1.5;
          glass(F, a, e, 0.03, y(WIN.t0), y(WIN.t1), 7);
          glass(F, a, e, 0.03, y(WIN.g0), y(WIN.g1), 2);
          for (const yy of SPAN) fbox(mMetal, F, a, e, 0, 0.1, y(yy - 0.3), y(yy + 0.3));
          fbox(mTrim, F, a - 0.45, a, 0, 0.35, y(WIN.t0 - 0.3), y(WIN.t1 + 0.45));   // surround
          fbox(mTrim, F, e, e + 0.45, 0, 0.35, y(WIN.t0 - 0.3), y(WIN.t1 + 0.45));
          fbox(mTrim, F, a - 0.45, e + 0.45, 0, 0.35, y(WIN.t1), y(WIN.t1 + 0.45));
          fbox(mTrim, F, a - 0.45, e + 0.45, 0, 0.35, y(WIN.t0 - 0.3), y(WIN.t0));
        }
      };
      corner(1, 1); corner(1, -1); corner(-1, 1); corner(-1, -1);

      // granite base course round the whole block
      add(mBase, K.prism(K.offsetRing(rectRing(uW, uE, vN, vS), 0.2), BF, y(0.9)));

      // ---- the concourse pavilion: 290 by 135 feet, 95-foot coffered ceiling, carried out over the two porticos
      slab(mLime, uW, uE, vP0, vP1, BF, y(PAV.col1));                     // concourse walls
      slab(mLime, uWP, uEP, vP0, vP1, y(PAV.col1), y(PAV.att));           // entablature and attic over the porticos
      add(mTrim, K.prism(K.offsetRing(rectRing(uWP, uEP, vP0, vP1), 0.15), y(PAV.col1), y(PAV.arch)));      // architrave
      add(mTrim, K.prism(K.offsetRing(rectRing(uWP, uEP, vP0, vP1), 0.3), y(PAV.frz), y(PAV.frz + 0.35)));   // bed mould
      add(mTrim, tag(K.prism(K.offsetRing(rectRing(uWP, uEP, vP0, vP1), 0.75), y(PAV.frz + 0.8), y(PAV.frz + 1.05)), 1));
      add(mTrim, tag(K.prism(K.offsetRing(rectRing(uWP, uEP, vP0, vP1), 1.35), y(PAV.frz + 1.05), y(PAV.cor)), 1));  // corona, in shade
      // the dentil course under the corona, across both portico fronts and their returns
      const dentils = (F, t0, t1) => { for (let t = t0 + 0.4; t < t1 - 0.3; t += 0.75) add(mTrim, tag(fg(F, t, t + 0.36, 0, 0.55, y(PAV.frz + 0.35), y(PAV.frz + 0.8)), 1)); };
      dentils(face('u', uEP, 1), vP0, vP1); dentils(face('u', uWP, -1), vP0, vP1);
      for (const [vv, s] of [[vP0, -1], [vP1, 1]]) { dentils(face('v', vv, s), uE, uEP); dentils(face('v', vv, s), uWP, uW); }
      const capOuter = K.offsetRing(rectRing(uWP, uEP, vP0, vP1), 0.45), capInner = K.offsetRing(rectRing(uWP, uEP, vP0, vP1), -0.9);
      add(mTrim, K.prism(capOuter, y(PAV.att), y(PAV.cap), [capInner]));
      slab(mRoof, uWP + 0.9, uEP - 0.9, vP0 + 0.9, vP1 - 0.9, y(PAV.att), y(PAV.att + 0.12));
      // a row of shallow square stone grilles along the attic's long sides (the Market Street Bridge photo), a shade
      // darker than the attic, never glass
      const attMid = (PAV.cor + PAV.att) / 2;
      for (const [vv, sg_] of [[vP0, -1], [vP1, 1]]) { const F = face('v', vv, sg_); for (let t = uWP + 3.2; t < uEP - 3; t += 3.6) add(mTrim, tag(fq(F, t, t + 1.3, 0.02, y(attMid - 0.65), y(attMid + 0.65)), 2)); }
      for (const [u, v, a, b, h] of [[-10, 14, 4, 3, 1.8], [-5, 14, 4, 3, 1.8], [30, 36, 4, 3.5, 1.5], [52, 12, 3, 3, 1.2]]) add(mShed, tag(sg(u - a / 2, u + a / 2, v - b / 2, v + b / 2, y(PAV.att + 0.12), y(PAV.att + 0.12 + h)), 1));
      // the concourse clerestory: eleven bays a side, seen over the ticket lobby and into the south court
      for (const [vv, s] of [[vP0, -1], [vP1, 1]]) {
        const F = face('v', vv, s), p = (uE - uW) / 11;
        for (let i = 0; i < 11; i++) {
          const c = uW + p * (i + 0.5), a = c - 2.6, e = c + 2.6;
          if (a < CU0 + 0.5 || e > CU1 - 0.5) continue;
          glass(F, a, e, 0.03, y(HC + 1.4), y(21.4), 5, 0);
          for (const yy of [13.5, 17.4]) fbox(mMetal, F, a, e, 0, 0.1, y(yy), y(yy + 0.35));
          fbox(mLime, F, e + 0.3, c + p - 2.9, 0, 0.45, y(HC), y(PAV.col1));     // pier to the next bay
        }
      }

      // ---- the two porticos (porte-cocheres): six Corinthian columns in antis between broad corner piers, two more
      // on each return, a coffered soffit, five tall windows over five doors in the rear wall
      const portico = (s) => {
        const u0 = s > 0 ? uE : uW, u1 = s > 0 ? uEP : uWP, U = (d) => u0 + s * d, depth = Math.abs(u1 - u0);
        const PW = 7.0, PD = 5.0;                        // corner pier: 7 m across the front, 5 m deep
        // floor and podium down to the foundation (the ground falls away east toward the river)
        slab(mBase, U(0), U(depth + 0.6), vP0 - 0.6, vP1 + 0.6, BF, y(PAV.col0));
        // corner piers
        for (const [va, vb] of [[vP0, vP0 + PW], [vP1 - PW, vP1]]) {
          slab(mLime, U(depth - PD), U(depth), va, vb, y(PAV.col0), y(PAV.col1));
          slab(mTrim, U(depth - PD) - 0.1 * s, U(depth) + 0.15 * s, va - 0.15, vb + 0.15, y(PAV.col0), y(1.2));
        }
        // columns: 71 feet, Alabama limestone, Corinthian
        const r = 1.2, H = PAV.col1 - PAV.col0, uc = depth - 1.6;
        const front = [], v0 = vP0 + PW + 1.6, v1 = vP1 - PW - 1.6;
        for (let i = 0; i < 6; i++) front.push([U(uc), v0 + (v1 - v0) * i / 5]);
        for (const dd of [3.2, depth - PD - 2.4]) { front.push([U(dd), vP0 + 1.4]); front.push([U(dd), vP1 - 1.4]); }   // the drive passes between these
        for (const [cu, cv] of front) {
          const p = f.p(cu, cv);
          add(mTrim, K.box(r * 2.9, 0.5, r * 2.9, p[0], y(PAV.col0) + 0.25, p[1], -A_));                 // plinth
          add(mTrim, K.column(p[0], y(PAV.col0 + 0.5), p[1], H - 0.5, r, 'corinthian', 16));
        }
        // coffered soffit: beams under the entablature
        for (let k = 1; k < 4; k++) slab(mLime, U(depth * k / 4) - 0.35, U(depth * k / 4) + 0.35, vP0 + PW * 0.5, vP1 - PW * 0.5, y(PAV.col1 - 0.8), y(PAV.col1));
        for (let k = 1; k < 5; k++) { const vv = vP0 + (vP1 - vP0) * k / 5; slab(mLime, U(0), U(depth - PD * 0.5), vv - 0.35, vv + 0.35, y(PAV.col1 - 0.8), y(PAV.col1)); }
        // rear wall: five bronze-framed door bays (warm, lit all night, the lanterns of the night photo), five tall
        // windows with the concourse's light behind them, flat pilasters between
        const F = face('u', u0, s), step = (v1 - v0) / 5;
        for (let i = 0; i < 5; i++) {
          const c = v0 + step * (i + 0.5);
          glass(F, c - 1.9, c + 1.9, 0.03, y(PAV.col0), y(5.6), 10, 0);
          fbox(mMetal, F, c - 2.0, c + 2.0, 0, 0.08, y(3.9), y(4.15));
          fbox(mTrim, F, c - 2.3, c + 2.3, 0, 0.3, y(5.6), y(6.3));
          glass(F, c - 2.05, c + 2.05, 0.03, y(7.0), y(20.8), 4, 0);
          for (const yy of [10.3, 13.8, 17.3]) fbox(mMetal, F, c - 2.05, c + 2.05, 0, 0.1, y(yy), y(yy + 0.3));
        }
        for (let i = 0; i <= 5; i++) { const c = v0 + step * i; fbox(mLime, F, c - 0.7, c + 0.7, 0, 0.35, y(PAV.col0), y(21.6)); fbox(mTrim, F, c - 0.95, c + 0.95, 0, 0.55, y(20.6), y(21.6)); }
      };
      portico(1); portico(-1);

      // ---- flagpoles (the Commons photos: a row along the east front before the portico and the south wing, three
      // on the west front at the corner piers and the south wing). 15 m, six-sided, light grey, on small granite bases
      const pole = (u, v) => {
        const p = f.p(u, v), g = api.ground(p[0], p[1]), gy = isFinite(g) ? g : 0;
        add(mBase, sg(u - 0.45, u + 0.45, v - 0.45, v + 0.45, Math.min(gy, BF + 1) - 0.5, gy + 0.35));
        add(mShed, tag(K.cyl(0.07, 0.11, 15, 6, p[0], gy + 0.35, p[1]), 1));
        add(mShed, tag(K.cyl(0.16, 0.16, 0.3, 6, p[0], gy + 15.35, p[1]), 1));
      };
      for (let i = 0; i < 5; i++) pole(uEP + 2.6, vP0 + 7.0 + (vP1 - vP0 - 14.0) * i / 4);
      for (let i = 0; i < 3; i++) pole(uE + 2.6, vP1 + 7 + i * 8);
      pole(uWP - 2.6, vP0 + 3.5); pole(uWP - 2.6, vP1 - 3.5); pole(uW - 2.6, vP1 + 8);

      // ---- the SEPTA upper level: three island platforms on a deck over the north end and out across 30th Street,
      // under a long steel shed with five glazed monitors
      const vSN = -93.3, vAN = -87.2, vAS = -44.2, uA = -127.5, DECK = 8.2, EAVE = 12.8, ROOF = 14.2;
      // the limestone base under the platforms (the North Waiting Room and baggage halls), tall windows on its north face
      slab(mLime, uW + 0.3, uE, vSN + 0.4, vN + 0.5, BF, y(DECK));
      add(mBase, K.prism(K.offsetRing(rectRing(uW + 0.3, uE, vSN + 0.4, vN), 0.2), BF, y(0.9)));
      slab(mTrim, uW + 0.1, uE + 0.2, vSN + 0.2, vN, y(DECK), y(DECK + 0.5));
      {
        const F = face('v', vSN + 0.4, -1), p = (uE - uW - 0.3) / 12;
        for (let i = 0; i < 12; i++) {
          const c = uW + 0.3 + p * (i + 0.5);
          glass(F, c - 1.8, c + 1.8, 0.03, y(1.4), y(6.6), 8, 0);
          fbox(mMetal, F, c - 1.8, c + 1.8, 0, 0.1, y(4.3), y(4.55));
          fbox(mTrim, F, c - 2.1, c + 2.1, 0, 0.3, y(6.6), y(7.0));
        }
      }
      // the annex out over the yard. The app lifts North 30th Street to a deck at 13.4 to 14.1 m where it passes the
      // shed (measured in the app by ray), where the real street runs underneath the platforms at the station's
      // floor level, so the annex opens a gap for the street (u -97 to -78) rather than meeting it: the shed keeps its
      // real height either side, and each cut end is closed with a glazed end wall on a stone base course under a
      // steel fascia, so the break reads as built. The station drive at u -50 passes under the eastern piece.
      const GAP0 = -97, GAP1 = -78;
      const ANNEX = [[uA, GAP0], [GAP1, uW + 0.3]], RUNS = [[uA, GAP0], [GAP1, uE]];
      for (const [a0, a1] of ANNEX) slab(mBase, a0, a1, vAN, vAS, y(DECK - 1.3), y(DECK));
      for (const pu of [-124.5, -99.5, -75.5, -58]) for (const pv of [vAN + 2, -66, vAS - 2]) {
        const p = f.p(pu, pv), g = api.ground(p[0], p[1]);
        slab(mBase, pu - 0.8, pu + 0.8, pv - 0.8, pv + 0.8, (isFinite(g) ? g : 0) - 1, y(DECK - 1.3));
      }
      // platforms (three islands) on the deck
      for (const [r0, r1] of RUNS) for (const pv of [-49.4, -65.9, -81.7]) slab(mBase, r0 + 0.5, r1 - 0.5, pv - 4, pv + 4, y(DECK), y(DECK + 1.05));
      // the shed: columns on the platforms, a deep fascia, the roof and five monitors
      for (const [r0, r1] of RUNS) for (const pv of [-49.4, -65.9, -81.7]) for (let pu = r0 + 3; pu < r1 - 1; pu += 12) slab(mShed, pu - 0.25, pu + 0.25, pv - 0.25, pv + 0.25, y(DECK + 1.05), y(EAVE));
      slab(mShed, uW, uE + 0.4, vSN + 0.2, vN, y(EAVE), y(ROOF));
      for (const [a0, a1] of ANNEX) slab(mShed, a0, Math.min(a1, uW), vAN, vAS, y(EAVE), y(ROOF));
      for (const [r0, r1] of RUNS) for (let i = 0; i < 5; i++) {
        const vc = vAS - 4.2 - i * 8.6;
        add(mGlass, tag(sg(r0 + 2, r1 - 1.5, vc - 1.3, vc + 1.3, y(ROOF), y(ROOF + 1.2)), 9, Math.round((r1 - r0) / 2)));
        add(mShed, K.gableF(f, r0 + 1.6, r1 - 1.1, vc - 1.7, vc + 1.7, y(ROOF + 1.2), y(ROOF + 1.9), true, 0.1).all);
      }
      // glazed sides above the deck parapet: the north side of both parts, the annex's south side, and the two ends
      // at the street's gap
      const glazed = (F, t0, t1) => {
        fbox(mLime, F, t0, t1, -0.4, 0, y(DECK), y(DECK + 1.2));
        glass(F, t0, t1, -0.2, y(DECK + 1.2), y(EAVE), 6, Math.max(1, Math.round((t1 - t0) / 1.5)));
        for (let t = t0; t <= t1 + 0.01; t += (t1 - t0) / Math.max(1, Math.round((t1 - t0) / 4.5))) fbox(mShed, F, t - 0.1, t + 0.1, -0.2, 0, y(DECK + 1.2), y(EAVE));
      };
      glazed(face('v', vSN + 0.2, -1), uW, uE);
      for (const [a0, a1] of ANNEX) { glazed(face('v', vAN, -1), a0, Math.min(a1, uW)); glazed(face('v', vAS, 1), a0, Math.min(a1, uW - 0.3)); }
      for (const [uu, s] of [[GAP0, 1], [GAP1, -1]]) {
        const F = face('u', uu, s);
        glazed(F, vAN, vAS);
        fbox(mShed, F, vAN - 0.3, vAS + 0.3, -0.1, 0.3, y(EAVE - 0.5), y(ROOF + 0.15));   // steel fascia over the end
      }

      const grp = B_.done();

      // ---- the night: every patched material reads the app's photocell once a frame (the street lamps' own value)
      let lastFrame = -1;
      const tick = (renderer) => {
        const fr = renderer.info.render.frame;
        if (fr === lastFrame) return;
        lastFrame = fr;
        NIGHT.value = api.lamp ? +api.lamp.value || 0 : 0;
      };
      grp.traverse((o) => { if (o.isMesh) o.onBeforeRender = tick; });

      // ---- the Rail Stations pin (app only). Its anchor stands 4.5 m over the ground at the SEPTA stop's point, local
      // (14, -95), just off the upper-level base's north face, so from the south and west the new block hid it and
      // a tap could not reach it. api.pinAt lifts that one record's anchor onto the pavilion where the rail stops are posted
      // ('Posting the transit stops'). It goes on the attic cap over the 30th Street (west) portico,
      // not the roof's middle: a pin is shown or hidden whole by its anchor, and from 30th Street (the second pose, eye
      // 26 m up) the 35.5 m attic hides the middle of its own roof, while the west edge is seen from there and, across
      // the roof, from every pose above it. The station's box is the ring: the stop inside it moves, and the occlusion
      // test and the tap pick read the new anchor.
      if (api.where === 'app' && api.pinAt) {
        const R = W(uWP + 0.4, (vP0 + vP1) / 2, y(PAV.cap + 0.4));
        api.pinAt([f.p(-130, -97), f.p(86, -97), f.p(86, 102), f.p(-130, 102)], R);
      }
      return grp;
    }
  });
})();
