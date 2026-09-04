/* Society Hill Towers — interactive 3D model.
   Coordinate system: x = east, y = up, z = south, meters, origin at the towers' centroid. */
(function () {
  'use strict';

  // ---------------------------------------------------------------- config
  // Facade spec from published sources + photo measurement (see About panel):
  // 31 stories = tall lobby + 30 residential floors; egg-crate grid on a 6 ft
  // (1.83 m) module, windows taller than wide, grid floating on a colonnade.
  const TOWER = {
    height: 94.2,          // to roof parapet (CTBUH); OSM tags 89 m
    floors: 30,            // residential floors above the lobby
    lobbyH: 5.6,
    parapetH: 1.2,
    bayPitch: 1.83,        // structural module, m
    cornerW: 0.78,         // solid corner pier width per face
    mullionW: 0.42,        // vertical concrete member face width
    mullionD: 0.5,         // grid projection depth in front of the glass
    spandrelH: 0.72,       // horizontal concrete band height per floor
    glassInset: 0.45,      // glass recess behind the concrete face
    lobbyInset: 3.4,       // ground-floor glass recess behind the colonnade
    colSpacing: 3,         // lobby column every Nth grid line
    penthouseH: 3.1,
  };

  const COLORS = {
    concrete: 0xc8c3b2,    // warm buff exposed-aggregate concrete (photo-sampled)
    concreteDark: 0xaaa595,
    glass: 0x37343f,       // dark blue-gray: clear glass, dark interiors, anodized frames
    glassLobby: 0x2e2b35,
    ground: 0x243818,     // bare earth is the same meadow as the parks (the game's one dark olive); the surfTexPatch mottle carries the variation
    plaza: 0x96604a,       // brick-paved plaza and circular drive
    asphalt: 0x3b3833,
    footway: 0x7c584a,     // society hill brick sidewalks
    park: 0x243818,        // grass — stored very deep: the legacy-color pipeline + ACES
    parkDark: 0x1d2c13,    // lift flat lawns ~2.5x at noon (cf. roads: 0x3b3833 -> light gray)
    water: 0x07297b,     // deep blue, the game's: a body colour, not a lit floor (liquify damps its diffuse)
    pier: 0x8f8a7d,
    trunk: 0x2b2119,       // stored near-black: the legacy lift turns it bark brown (0x5b4a38 read as cream)
    bronze: 0x4d3b26,
    skyZenith: 0x2260c8,   // deeper and more saturated (Mike, with the darker meadow and walls)
    skyHorizon: 0xa6c6ea,  // a blue horizon band, not a white one; the fog takes this colour by day
    skyGround: 0xa9b3ba,   // below-horizon haze — from altitude the dome shows past the world's edge
    haze: 0xb6c9e4,       // aerial perspective goes blue, not sand
    sun: 0xffe5b8,
  };
  // the ground look, one place to tune: parks and bare ground share one meadow shader and one
  // mottle, so the per-polygon park shade goes flat (lerp(1 - spread, 1 + spread, hash)); the
  // woodland is the NW hills' vertex tint, a ratio against COLORS.ground
  const PARK_SHADE_SPREAD = 0;
  const WOODLAND = 0x1b2c12;

  const LABEL_FADE = [540, 880];

  // ---------------------------------------------------------------- dom
  const canvas = document.getElementById('gl');
  const veil = document.getElementById('veil');
  const btnEnter = document.getElementById('btnEnter');
  const loadmsg = document.getElementById('loadmsg');
  const hintEl = document.getElementById('hint');
  const crosshair = document.getElementById('crosshair');
  const labelsRoot = document.getElementById('labels');
  const needle = document.getElementById('needle');
  const stick = document.getElementById('stick');
  const stickNub = stick.querySelector('.nub');
  const padL = document.getElementById('padL'), padR = document.getElementById('padR');
  window.addEventListener('error', (e) => {
    const lm = document.getElementById('loadmsg');
    if (lm && !window.__fatalShown) { window.__fatalShown = true; lm.textContent = 'Error: ' + ((e && e.message) || 'unknown'); }
    beacon('err', { m: String((e && e.message) || 'unknown').slice(0, 80) });
  });
  window.addEventListener('unhandledrejection', (e) => {
    const r = e && e.reason;
    console.error('unhandled rejection', r);
    const lm = document.getElementById('loadmsg');
    if (lm && !window.__fatalShown) { window.__fatalShown = true; lm.textContent = 'Error: ' + ((r && r.message) || String(r)); }
    beacon('err', { m: 'rejection: ' + String((r && r.message) || r).slice(0, 70) });
  });
  // load and frame instrumentation, read through ?dev's __dbg.perf(): which
  // build step dominates on a real device, and what a frame costs there
  const PERF = { t0: performance.now(), steps: [], failed: [], ring: new Float32Array(600), ri: 0, rn: 0 };
  // Opt-in, same-origin telemetry: ops/philly3d.vhost.example gives /b a
  // `return 204` and logs the query string without the client IP. Only on
  // philly3d.com, one request per checkpoint, nothing personal: checkpoint,
  // ms since load, coarse pointer, DPR, cores, deviceMemory, WebGL2, build
  // date. Progressive because an iOS memory kill sends no pagehide: the
  // server's last-seen checkpoint IS the death point. Errors cap at three.
  const BEACON = location.hostname === 'philly3d.com' ? '/b' : null;
  const beaconSeen = new Set();
  let beaconErrs = 0;
  function beacon(st, extra) {
    if (!BEACON) return;
    if (st === 'err') { if (++beaconErrs > 3) return; }
    else if (beaconSeen.has(st)) return;
    else beaconSeen.add(st);
    const q = { st, t: Math.round(performance.now()), tch: isTouch ? 1 : 0, dpr: (window.devicePixelRatio || 1).toFixed(2),
      cores: navigator.hardwareConcurrency || 0, mem: navigator.deviceMemory || 0,
      gl2: (typeof renderer !== 'undefined' && renderer && renderer.capabilities && renderer.capabilities.isWebGL2) ? 1 : 0, b: document.lastModified };
    if (extra) for (const k in extra) if (extra[k] != null) q[k] = extra[k];
    const url = BEACON + '?' + new URLSearchParams(q).toString();
    try { fetch(url, { method: 'POST', keepalive: true, referrerPolicy: 'no-referrer', cache: 'no-store' }).catch(() => {}); }
    catch (e) { try { if (navigator.sendBeacon) navigator.sendBeacon(url); } catch (e2) { /* nothing to do */ } }
  }
  document.addEventListener('visibilitychange', () => {
    const lm = document.getElementById('loadmsg');
    if (document.hidden && !PERF.ready && lm) beacon('bail', { step: lm.textContent.slice(0, 40) });
  });
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const isTouch = window.matchMedia('(pointer: coarse)').matches;

  let renderer;
  try {
    // Log depth EVERYWHERE. The Aug-24 Safari standard-depth fallback was built
    // for the "hollow buildings" report, which round 4 proved was an earcut
    // cap-winding bug, not Safari — and standard depth over a 26 km far plane
    // quantizes the few-cm flat separations into heavy z-fight shimmer on
    // phones (every iPhone browser is Safari-engined). Keep ?logdepth=0 as an
    // escape hatch if a real per-fragment-depth defect ever surfaces.
    const qsDepth = /[?&]logdepth=(\d)/.exec(location.search);
    window.__useLogDepth = qsDepth ? qsDepth[1] === '1' : true;
    // the post pipeline resolves its own 4x multisampled float target, so the canvas skips the
    // browser's multisampled backbuffer when the pipeline will own the frame (probed on a
    // throwaway context here, before the real one exists; POST.on repeats the test on it)
    const postCapable = !isTouch && !/[?&]bloom=0/.test(location.search) && (() => {
      try { const c2 = document.createElement('canvas'); const g2 = c2.getContext('webgl2'); if (!g2) return false; const ok = !!g2.getExtension('EXT_color_buffer_float'); const lose = g2.getExtension('WEBGL_lose_context'); if (lose) lose.loseContext(); return ok; } catch (e) { return false; }
    })();
    renderer = new THREE.WebGLRenderer({ canvas, antialias: !postCapable, powerPreference: 'high-performance', logarithmicDepthBuffer: window.__useLogDepth });
    if (!renderer.getContext()) throw new Error('no context');
  } catch (e) {
    document.getElementById('nogl').style.display = 'flex';
    veil.style.display = 'none';
    return;
  }
  const DPR_CAP = window.matchMedia('(pointer: coarse)').matches ? 1.5 : 1.75;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, DPR_CAP));
  // adaptive resolution: the cap alone treated a 2019 integrated GPU and a
  // 4090 alike. frame() keeps a rolling median of frame time and steps the
  // ratio down 15% when frames run long, back up when they stay short;
  // fragment cost scales with the square, so 1.75 -> 1.25 halves the shading
  // work. ?dpr=1.5 pins it.
  const DPR = { cap: renderer.getPixelRatio(), min: 0.9, cur: renderer.getPixelRatio(), ring: new Float32Array(30), tmp: new Float32Array(30), i: 0, fast: 0, pinned: false };   // cap = the display's own ratio under DPR_CAP: never supersample
  {
    const q = /[?&]dpr=([\d.]+)/.exec(location.search);
    if (q) { DPR.pinned = true; DPR.cur = clamp(+q[1], 0.5, 3); renderer.setPixelRatio(DPR.cur); }
  }
  function applyDPR(r) {
    DPR.cur = r;
    renderer.setPixelRatio(r);   // re-applies the drawing-buffer size
    if (poleMat) poleMat.size = r;     // the point sprites are sized in physical px
    if (towerMat) towerMat.size = r;
    if (floodMat) floodMat.size = r;
  }
  renderer.setSize(window.innerWidth, window.innerHeight);
  // Three.js is PINNED at r149 (build.py asserts it): outputEncoding/sRGBEncoding
  // were removed in r152+, and the ~250 colour constants in this file are tuned
  // to r149's legacy colour pipeline (stored dark, lifted by ACES). An upgrade
  // must set THREE.ColorManagement.enabled = false and use outputColorSpace =
  // SRGBColorSpace, or repaint the whole city.
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.06;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  // the sun moves once a minute at most: the 4096^2 depth pass reruns only when
  // aimSun changes the box or the sun, when the static caster set changes, or
  // every 4th frame while vehicles move through the box (see frame())
  renderer.shadowMap.autoUpdate = false;
  renderer.shadowMap.needsUpdate = true;

  // ---- post. The frame is drawn into a half-float target and finished by a composite pass
  // (ACES + sRGB, the renderer's own pipeline written out by hand) with a bloom of the
  // brightest pixels: the sun, the water's glitter, the lit windows and the white cloud
  // rims glow the way the game's do. Desktop WebGL2 with float targets only; ?bloom=0 turns
  // it off. Materials that write raw colour (the sky dome, the cloud deck) undo the pipeline
  // with an exact algebraic inverse, so their palettes are pixel-identical either way.
  // The renderer itself runs with NO tone mapping while the post pipeline owns the frame:
  // r149 forces LinearEncoding on a render-target pass but still applies renderer.toneMapping
  // to every toneMapped material, so leaving ACES on mapped the scene twice (once into the
  // float target, once in the composite) and the river read milky. The composite carries
  // exposure + ACES + sRGB alone; the target holds linear light (the veil's upload renders
  // draw untonemapped, unseen, and compile every program once, in the post variant).
  const POST = { on: false, w: 0, h: 0, calls: 0, tris: 0 };   // calls/tris: the scene pass's own counts (renderer.info resets per pass)
  POST.on = !isTouch && !!renderer.capabilities.isWebGL2 && !/[?&]bloom=0/.test(location.search) && renderer.extensions.has('EXT_color_buffer_float');
  if (POST.on) renderer.toneMapping = THREE.NoToneMapping;
  const postU = { uExposure: { value: 1.06 }, uPost: { value: POST.on ? 1 : 0 } };
  const ACES_GLSL = [
    'vec3 pRRT(vec3 v){ vec3 a = v * (v + 0.0245786) - 0.000090537; vec3 b = v * (0.983729 * v + 0.4329510) + 0.238081; return a / b; }',
    'const mat3 pAIn = mat3(vec3(0.59719, 0.07600, 0.02840), vec3(0.35458, 0.90834, 0.13383), vec3(0.04823, 0.01566, 0.83777));',
    'const mat3 pAOut = mat3(vec3(1.60475, -0.10208, -0.00327), vec3(-0.53108, 1.10813, -0.07276), vec3(-0.07367, -0.00605, 1.07602));',
    'vec3 pACES(vec3 c, float e){ c = pAIn * (c * e / 0.6); c = pRRT(c); return clamp(pAOut * c, 0.0, 1.0); }',
    'vec3 pToSRGB(vec3 c){ return mix(c * 12.92, 1.055 * pow(max(c, vec3(0.0)), vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c)); }',
  ].join('\n');
  const INV_GLSL = [
    'const mat3 pAInI = mat3(vec3(1.764741, -0.147028, -0.036337), vec3(-0.675778, 1.160252, -0.162436), vec3(-0.088963, -0.013224, 1.198773));',
    'const mat3 pAOutI = mat3(vec3(0.643038, 0.059269, 0.005962), vec3(0.311187, 0.931436, 0.063929), vec3(0.045775, 0.009295, 0.930118));',
    'vec3 pInvRRT(vec3 y){ vec3 A = 1.0 - 0.983729 * y; vec3 B = 0.0245786 - 0.432951 * y; vec3 C = -(0.000090537 + 0.238081 * y); return (-B + sqrt(max(B * B - 4.0 * A * C, vec3(0.0)))) / (2.0 * A); }',
    'vec3 pFromSRGB(vec3 c){ return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(0.04045, c)); }',
    'vec3 pUndo(vec3 c, float e){ c = pFromSRGB(clamp(c, 0.0, 1.0)); c = min(c, vec3(0.985)); c = pAOutI * c; c = pInvRRT(c); c = pAInI * c; return c * 0.6 / e; }',
    'vec3 pUndoLin(vec3 c, float e){ c = min(clamp(c, 0.0, 1.0), vec3(0.985)); c = pAOutI * c; c = pInvRRT(c); c = pAInI * c; return c * 0.6 / e; }',
  ].join('\n');
  // materials that opt out of tone mapping (toneMapped: false: the light points, the car
  // lights, the stadium floods, the pins, the neighbourhood atlas) wrote their colour straight
  // to the canvas, sRGB-encoded by the renderer; under the post pipeline they hand the
  // composite the ACES pre-image of that colour instead (pUndoLin: no sRGB decode, unlike
  // the dome, whose raw values never met the encoder), so they look the same either way
  const postRaw = (mat, opts) => {
    if (!POST.on) return mat;
    // additive lights saturate instead of summing: the 8-bit canvas clamped a thousand far
    // lamps at white, the float target sums them past it (a white band on the night horizon
    // that then bloomed), so the brightest light wins the pixel and the fade rides in the alpha
    if (mat.blending === THREE.AdditiveBlending) {
      mat.blending = THREE.CustomBlending;
      mat.blendEquation = THREE.MaxEquation; mat.blendSrc = THREE.OneFactor; mat.blendDst = THREE.OneFactor;
      mat.blendEquationAlpha = THREE.MaxEquation; mat.blendSrcAlpha = THREE.OneFactor; mat.blendDstAlpha = THREE.OneFactor;
      mat.premultipliedAlpha = true;
    } else if (opts && opts.mask) {
      // a marker or a label is not a light and must not bloom: its white frame's pre-image
      // sits far above the bright pass's threshold, so every pin wore a halo that shimmered
      // as the quarter-res blur resampled it. The bright pass reads the target's alpha as its
      // mask (the cloud deck's coverage rides there), so these blend their colour as before
      // and write a zero alpha under themselves
      mat.blending = THREE.CustomBlending;
      mat.blendEquation = THREE.AddEquation; mat.blendSrc = THREE.SrcAlphaFactor; mat.blendDst = THREE.OneMinusSrcAlphaFactor;
      mat.blendEquationAlpha = THREE.AddEquation; mat.blendSrcAlpha = THREE.ZeroFactor; mat.blendDstAlpha = THREE.OneMinusSrcAlphaFactor;
    }
    const prev = mat.onBeforeCompile;
    mat.onBeforeCompile = (sh, r) => {
      if (prev) prev(sh, r);
      sh.uniforms.uExposure = postU.uExposure;
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', '#include <common>\nuniform float uExposure;\n' + INV_GLSL)
        .replace('#include <encodings_fragment>', '#include <encodings_fragment>\ngl_FragColor.rgb = pUndoLin(gl_FragColor.rgb, uExposure);');
    };
    mat.customProgramCacheKey = () => 'postRaw|' + (prev ? prev.toString() : '');
    return mat;
  };
  let postRT = null, postA = null, postB = null, postQuad = null, postCam = null, postScene = null, postBright = null, postBlur = null, postComp = null;
  // pUndo in JS for the fog colour: the fog mixes inside the target, so under the post pipeline it
  // takes the pre-image of its display colour like the dome, or the far haze comes out of the
  // composite darker than the horizon it is meant to meet (same matrices as INV_GLSL, by column)
  const pUndoColor = (c, e) => {
    const f = (v) => { v = Math.min(Math.max(v, 0), 1); v = v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); return Math.min(v, 0.985); };
    const r = f(c.r), g = f(c.g), b = f(c.b);
    const inv = (y) => { const A = 1 - 0.983729 * y, B = 0.0245786 - 0.432951 * y, C = -(0.000090537 + 0.238081 * y); return (-B + Math.sqrt(Math.max(B * B - 4 * A * C, 0))) / (2 * A); };
    const x = inv(0.643038 * r + 0.311187 * g + 0.045775 * b), y = inv(0.059269 * r + 0.931436 * g + 0.009295 * b), z = inv(0.005962 * r + 0.063929 * g + 0.930118 * b);
    return c.setRGB((1.764741 * x - 0.675778 * y - 0.088963 * z) * 0.6 / e, (-0.147028 * x + 1.160252 * y - 0.013224 * z) * 0.6 / e, (-0.036337 * x - 0.162436 * y + 1.198773 * z) * 0.6 / e);
  };
  const _v2post = new THREE.Vector2();
  function postInit() {
    postCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    postScene = new THREE.Scene();
    const vs = 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }';
    postBright = new THREE.ShaderMaterial({ depthTest: false, depthWrite: false, uniforms: { tScene: { value: null }, uThr: { value: 1.25 }, uExposure: postU.uExposure },
      vertexShader: vs,
      fragmentShader: 'uniform sampler2D tScene; uniform float uThr, uExposure; varying vec2 vUv; void main(){ vec4 t = texture2D(tScene, vUv); vec3 c = t.rgb * uExposure; float l = dot(c, vec3(0.2126, 0.7152, 0.0722)); vec3 b = c * max(l - uThr, 0.0) / max(l, 1e-3); gl_FragColor = vec4(min(b, vec3(2.5)) * t.a, 1.0); }' });
    postBlur = new THREE.ShaderMaterial({ depthTest: false, depthWrite: false, uniforms: { tIn: { value: null }, uDir: { value: new THREE.Vector2(1, 0) } },
      vertexShader: vs,
      fragmentShader: 'uniform sampler2D tIn; uniform vec2 uDir; varying vec2 vUv; void main(){ vec3 c = texture2D(tIn, vUv).rgb * 0.2270270; c += (texture2D(tIn, vUv + uDir * 1.3846154).rgb + texture2D(tIn, vUv - uDir * 1.3846154).rgb) * 0.3162162; c += (texture2D(tIn, vUv + uDir * 3.2307692).rgb + texture2D(tIn, vUv - uDir * 3.2307692).rgb) * 0.0702703; gl_FragColor = vec4(c, 1.0); }' });
    postComp = new THREE.ShaderMaterial({ depthTest: false, depthWrite: false, uniforms: { tScene: { value: null }, tBloom: { value: null }, uBloom: { value: 0.45 }, uExposure: postU.uExposure },
      vertexShader: vs,
      fragmentShader: 'uniform sampler2D tScene, tBloom; uniform float uBloom, uExposure; varying vec2 vUv;\n' + ACES_GLSL + '\nvoid main(){ vec3 c = texture2D(tScene, vUv).rgb + texture2D(tBloom, vUv).rgb * uBloom; c = pToSRGB(pACES(c, uExposure)); c += (fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453) - 0.5) / 255.0; gl_FragColor = vec4(c, 1.0); }' });
    postQuad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), postComp);
    postQuad.frustumCulled = false;
    postScene.add(postQuad);
  }
  function postSize() {
    const s = renderer.getDrawingBufferSize(_v2post);
    if (postRT && s.x === POST.w && s.y === POST.h) return;
    POST.w = s.x; POST.h = s.y;
    if (postRT) { postRT.dispose(); postA.dispose(); postB.dispose(); }
    // stencilBuffer on: r149 gives a depth-only target a 16-bit depth renderbuffer, and depth
    // with stencil DEPTH24_STENCIL8, the 24 bits the canvas had (the layered flats need them)
    postRT = new THREE.WebGLRenderTarget(s.x, s.y, { type: THREE.HalfFloatType, samples: 4, depthBuffer: true, stencilBuffer: true, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter });
    const bw = Math.max(64, Math.round(s.x / 4)), bh = Math.max(64, Math.round(s.y / 4));
    postA = new THREE.WebGLRenderTarget(bw, bh, { type: THREE.HalfFloatType, depthBuffer: false, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter });
    postB = new THREE.WebGLRenderTarget(bw, bh, { type: THREE.HalfFloatType, depthBuffer: false, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter });
  }
  function renderPost(sc, cam) {
    if (!postCam) postInit();
    postSize();
    renderer.setRenderTarget(postRT);
    renderer.render(sc, cam);
    POST.calls = renderer.info.render.calls; POST.tris = renderer.info.render.triangles;
    postQuad.material = postBright; postBright.uniforms.tScene.value = postRT.texture;
    renderer.setRenderTarget(postA); renderer.render(postScene, postCam);
    postQuad.material = postBlur;
    for (let i = 0; i < 2; i++) {
      postBlur.uniforms.tIn.value = postA.texture; postBlur.uniforms.uDir.value.set(1 / postA.width, 0);
      renderer.setRenderTarget(postB); renderer.render(postScene, postCam);
      postBlur.uniforms.tIn.value = postB.texture; postBlur.uniforms.uDir.value.set(0, 1 / postA.height);
      renderer.setRenderTarget(postA); renderer.render(postScene, postCam);
    }
    postQuad.material = postComp; postComp.uniforms.tScene.value = postRT.texture; postComp.uniforms.tBloom.value = postA.texture;
    renderer.setRenderTarget(null); renderer.render(postScene, postCam);
  }

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(COLORS.haze, 8000, 40000);
  const fogBase = { near: 8000, far: 40000 };   // clear-air distances: the game's, weather still shrinks them   // clear-air distances; weather shrinks them live (applyLighting)
  // custom river spans register their true deck profiles here so the traffic
  // layer can ride the actual roadway instead of a flat guess under the bridge
  const BRIDGE_DECKS = [];
  function bridgeDeckLift(x, z) {
    let best = null;
    for (const b of BRIDGE_DECKS) {
      if (x < b.minX - 30 || x > b.maxX + 30 || z < b.minZ - 30 || z > b.maxZ + 30) continue;
      let bd = Infinity, bs = 0;
      for (let i = 0; i + 1 < b.pts.length; i++) {
        const ax = b.pts[i][0], az = b.pts[i][1];
        const dx = b.pts[i + 1][0] - ax, dz = b.pts[i + 1][1] - az;
        const L2 = dx * dx + dz * dz || 1e-6;
        const t = clamp(((x - ax) * dx + (z - az) * dz) / L2, 0, 1);
        const d = Math.hypot(x - (ax + dx * t), z - (az + dz * t));
        if (d < bd) { bd = d; bs = b.cum[i] + Math.sqrt(L2) * t; }
      }
      if (bd > b.halfW) continue;
      const y = b.yAt(bs);
      if (best === null || y > best) best = y;
    }
    return best;
  }
  // pre-scan a packed ring for its water polygons (record layouts: building
  // n,h,mh,t[,attr,roof],2n · road n,w,t,2n · area n,kind,2n — kind 1 = water)
  // and scanline-rasterize them into a coarse grid. Returns an (x,z) => bool
  // "stands in rendered water" test the building pass uses to refuse floaters.
  function wxWaterGrid(body, k0, nb, nRoads, nAreas, hasAttr, S, gx0, gz0, wMeters, hMeters, cell) {
    const gw = Math.ceil(wMeters / cell), gh = Math.ceil(hMeters / cell);
    const grid = new Uint8Array(gw * gh);
    let kk = k0;
    for (let i = 0; i < nb; i++) { const n = body[kk]; kk += (hasAttr ? 6 : 4) + n * 2; }
    for (let i = 0; i < nRoads; i++) { const n = body[kk]; kk += 3 + n * 2; }
    for (let i = 0; i < nAreas; i++) {
      const n = body[kk++], kind = body[kk++];
      if (kind !== 1) { kk += n * 2; continue; }
      const poly = new Array(n);
      let mnZ = Infinity, mxZ = -Infinity;
      for (let j = 0; j < n; j++) {
        poly[j] = [body[kk++] * S, body[kk++] * S];
        mnZ = Math.min(mnZ, poly[j][1]); mxZ = Math.max(mxZ, poly[j][1]);
      }
      const r0 = Math.max(0, Math.floor((mnZ - gz0) / cell)), r1 = Math.min(gh - 1, Math.ceil((mxZ - gz0) / cell));
      for (let r = r0; r <= r1; r++) {
        const zc = gz0 + (r + 0.5) * cell;
        const xs = [];
        for (let j = 0; j < n; j++) {
          const a = poly[j], b = poly[(j + 1) % n];
          if ((a[1] <= zc) !== (b[1] <= zc)) xs.push(a[0] + (zc - a[1]) / (b[1] - a[1]) * (b[0] - a[0]));
        }
        xs.sort((p, q) => p - q);
        for (let q = 0; q + 1 < xs.length; q += 2) {
          const c0 = Math.max(0, Math.round((xs[q] - gx0) / cell)), c1 = Math.min(gw - 1, Math.round((xs[q + 1] - gx0) / cell) - 1);
          for (let cc = c0; cc <= c1; cc++) grid[r * gw + cc] = 1;
        }
      }
    }
    return (x, z) => {
      const cc = Math.floor((x - gx0) / cell), rr = Math.floor((z - gz0) / cell);
      return cc >= 0 && rr >= 0 && cc < gw && rr < gh && grid[rr * gw + cc] === 1;
    };
  }

  const camera = new THREE.PerspectiveCamera(58, window.innerWidth / window.innerHeight, window.__useLogDepth ? 0.75 : 1.0, 26000);

  // flat surfaces are layered with generous gaps to keep the depth buffer honest
  const LAYER = { park: 0.06, plaza: 0.1, deck: 0.14, sidewalk: 0.16, road: 0.24, footway: 0.32, basin: 0.36, pool: 0.38 };

  // ---------------------------------------------------------------- helpers
  const V3 = THREE.Vector3;
  function hash01(n) { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); }
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function lerp(a, b, t) { return a + (b - a) * t; }

  function signedArea(pts) {
    let a = 0;
    for (let i = 0, n = pts.length; i < n; i++) {
      const p = pts[i], q = pts[(i + 1) % n];
      a += p[0] * q[1] - q[0] * p[1];
    }
    return a / 2;
  }
  function pointInPoly(x, y, pts) {
    let inside = false;
    for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      const xi = pts[i][0], yi = pts[i][1], xj = pts[j][0], yj = pts[j][1];
      if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }
  function polyCentroid(pts) {
    let x = 0, y = 0, a = 0;
    for (let i = 0, n = pts.length; i < n; i++) {
      const p = pts[i], q = pts[(i + 1) % n];
      const c = p[0] * q[1] - q[0] * p[1];
      a += c; x += (p[0] + q[0]) * c; y += (p[1] + q[1]) * c;
    }
    a *= 0.5;
    if (Math.abs(a) < 1e-6) return [pts[0][0], pts[0][1]];
    return [x / (6 * a), y / (6 * a)];
  }

  // shape plane: (sx, sy) = (x, -z); extruded +depth then rotateX(-90) -> world (x, h, z)
  function shapeFromPoly(poly, holes) {
    const pts = poly.map(p => new THREE.Vector2(p[0], -p[1]));
    if (THREE.ShapeUtils.area(pts) < 0) pts.reverse();
    const shape = new THREE.Shape(pts);
    if (holes) for (const h of holes) {
      const hp = h.map(p => new THREE.Vector2(p[0], -p[1]));
      if (THREE.ShapeUtils.area(hp) > 0) hp.reverse();
      shape.holes.push(new THREE.Path(hp));
    }
    return shape;
  }
  function extrudePoly(poly, holes, h, minH) {
    const geom = new THREE.ExtrudeGeometry(shapeFromPoly(poly, holes), {
      depth: h - (minH || 0), bevelEnabled: false, curveSegments: 1,
    });
    geom.rotateX(-Math.PI / 2);
    if (minH) geom.translate(0, minH, 0);
    return geom;
  }

  // Building volume built edge by edge so each facade carries its own coordinates
  // (aWallU along the wall, aWallL wall length, aWallH wall height): the facade
  // shader centers bays on every wall instead of slicing a world grid at corners.
  function buildingGeom(poly, holes, h, minH) {
    const base = minH || 0;
    const pos = [], nor = [], wu = [], wl = [], wh = [];
    const ring = (pts, outwardSign) => {
      const n = pts.length;
      for (let i = 0; i < n; i++) {
        const a = pts[i], b = pts[(i + 1) % n];
        const dx = b[0] - a[0], dz = b[1] - a[1];
        const L = Math.hypot(dx, dz);
        if (L < 0.05) continue;
        const nx = (dz / L) * outwardSign, nz = (-dx / L) * outwardSign;
        const A = [a[0], base, a[1]], B = [b[0], base, b[1]], C = [b[0], h, b[1]], Dd = [a[0], h, a[1]];
        const flip = ((-dz) * nx + dx * nz) < 0;
        const tri = (P, Q, R, uP, uQ, uR) => {
          pos.push(P[0], P[1], P[2], Q[0], Q[1], Q[2], R[0], R[1], R[2]);
          for (let k = 0; k < 3; k++) { nor.push(nx, 0, nz); wl.push(L); wh.push(h); }
          wu.push(uP, uQ, uR);
        };
        if (!flip) { tri(A, B, C, 0, L, L); tri(A, C, Dd, 0, L, 0); }
        else { tri(A, C, B, 0, L, L); tri(A, Dd, C, 0, 0, L); }
      }
    };
    const outerSign = signedArea(poly) > 0 ? 1 : -1;
    ring(poly, outerSign);
    if (holes) for (const hl of holes) if (hl.length >= 3) ring(hl, signedArea(hl) > 0 ? -1 : 1);
    // roof cap
    const cap = new THREE.ShapeGeometry(shapeFromPoly(poly, holes));
    cap.rotateX(-Math.PI / 2);
    cap.translate(0, h, 0);
    const cg = cap.index ? cap.toNonIndexed() : cap;
    const cp = cg.attributes.position.array, cn = cg.attributes.normal.array;
    for (let i = 0; i < cp.length; i += 3) { pos.push(cp[i], cp[i + 1], cp[i + 2]); nor.push(cn[i], cn[i + 1], cn[i + 2]); wu.push(0); wl.push(0); wh.push(h); }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
    g.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(nor), 3));
    g.setAttribute('aWallU', new THREE.BufferAttribute(new Float32Array(wu), 1));
    g.setAttribute('aWallL', new THREE.BufferAttribute(new Float32Array(wl), 1));
    g.setAttribute('aWallH', new THREE.BufferAttribute(new Float32Array(wh), 1));
    return g;
  }

  // merge many geometries into one, painting a flat color per part (with optional
  // ground-darkening to fake ambient occlusion at street level). facade picks
  // the per-vertex extras: true attaches the six the cityMat facade shader
  // reads (aStyle, aFloorH, aWallU/L/H, aBase), 'base' only aBase (the Ryland
  // glass night shader), anything else none: streets, parks, water and trim
  // used to carry 24 dead bytes per vertex their plain materials never read
  function mergeColored(parts, ao, facade) {
    let count = 0;
    const prepped = parts.map(p => {
      const g = p.geom.index ? p.geom.toNonIndexed() : p.geom;
      count += g.attributes.position.count;
      return { g, c: p.color };
    });
    const pos = new Float32Array(count * 3);
    const nor = new Float32Array(count * 3);
    const col = new Float32Array(count * 3);
    const full = facade === true;
    const sty = full ? new Float32Array(count) : null;
    const flh = full ? new Float32Array(count) : null;
    const wu = full ? new Float32Array(count) : null, wl = full ? new Float32Array(count) : null, wh = full ? new Float32Array(count) : null;
    const bs = facade ? new Float32Array(count) : null;
    // the lane paint's aLane rides along when any part carries it (zeros elsewhere: the shader skips them)
    const ln = prepped.some(p => !!p.g.attributes.aLane) ? new Float32Array(count * 4) : null;
    let o = 0;
    const c = new THREE.Color();
    for (let pi = 0; pi < prepped.length; pi++) {
      const { g, c: color } = prepped[pi];
      const styleV = parts[pi].style || 0;
      const flhV = parts[pi].flh ? Math.round(parts[pi].flh * 10) : 0;
      const baseY = parts[pi].baseY || 0;
      const p = g.attributes.position.array;
      const n = g.attributes.normal.array;
      const vc = g.attributes.position.count;
      pos.set(p, o * 3); nor.set(n, o * 3);
      if (full && g.attributes.aWallU) { wu.set(g.attributes.aWallU.array, o); wl.set(g.attributes.aWallL.array, o); wh.set(g.attributes.aWallH.array, o); }
      if (ln && g.attributes.aLane) ln.set(g.attributes.aLane.array, o * 4);
      if (full) { sty.fill(styleV, o, o + vc); flh.fill(flhV, o, o + vc); }
      if (bs) bs.fill(baseY, o, o + vc);
      for (let i = 0; i < vc; i++) {
        c.copy(color);
        if (ao) {
          const y = p[i * 3 + 1];
          const f = 0.72 + 0.28 * clamp((y - baseY) / 7, 0, 1);
          c.multiplyScalar(f);
        }
        col[(o + i) * 3] = c.r; col[(o + i) * 3 + 1] = c.g; col[(o + i) * 3 + 2] = c.b;
      }
      o += vc;
    }
    const out = new THREE.BufferGeometry();
    out.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    out.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
    out.setAttribute('color', new THREE.BufferAttribute(col, 3));
    if (full) {
      out.setAttribute('aStyle', new THREE.BufferAttribute(sty, 1));
      out.setAttribute('aFloorH', new THREE.BufferAttribute(flh, 1));
      out.setAttribute('aWallU', new THREE.BufferAttribute(wu, 1));
      out.setAttribute('aWallL', new THREE.BufferAttribute(wl, 1));
      out.setAttribute('aWallH', new THREE.BufferAttribute(wh, 1));
    }
    if (bs) out.setAttribute('aBase', new THREE.BufferAttribute(bs, 1));
    if (ln) out.setAttribute('aLane', new THREE.BufferAttribute(ln, 4));
    return out;
  }

  function box(w, h, d, x, y, z, ry) {
    const g = new THREE.BoxGeometry(w, h, d);
    if (ry) g.rotateY(ry);
    g.translate(x, y, z);
    return g;
  }

  // drop near-collinear vertices from a ring (roof fitting)
  function simplifyRing(poly, tol) {
    const n = poly.length, out = [];
    for (let i = 0; i < n; i++) {
      const a = poly[(i - 1 + n) % n], b = poly[i], c = poly[(i + 1) % n];
      const dx = c[0] - a[0], dz = c[1] - a[1];
      const L = Math.hypot(dx, dz) || 1;
      if (Math.abs((b[0] - a[0]) * dz - (b[1] - a[1]) * dx) / L > tol) out.push(b);
    }
    return out.length >= 3 ? out : poly;
  }

  // horizontal filled polygon at height y (sampled-roof-color overlay caps).
  // earcut's triangles are canonically CCW in the shape plane - always emit forward.
  function capGeom(poly, holes, y) {
    const v2c = poly.map(p => new THREE.Vector2(p[0], -p[1]));
    const hvc = (holes || []).map(hl => hl.map(q => new THREE.Vector2(q[0], -q[1])));
    const tris = THREE.ShapeUtils.triangulateShape(v2c, hvc);
    const all = (holes && holes.length) ? poly.concat(...holes) : poly;
    const pos = new Float32Array(all.length * 3);
    for (let i = 0; i < all.length; i++) { pos[i * 3] = all[i][0]; pos[i * 3 + 1] = y; pos[i * 3 + 2] = all[i][1]; }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const idx = [];
    for (const t of tris) idx.push(t[0], t[1], t[2]);
    g.setIndex(idx);
    g.computeVertexNormals();
    return g;
  }

  // gable built on the footprint quad itself: eaves are the longer opposite-edge
  // pair, the ridge joins the other pair's midpoints — the roof meets the wall
  // at every vertex, no floating overhangs on skewed footprints
  function quadGable(quad, eaveH, ridgeH, ridgeRad) {
    const E = [0, 1, 2, 3].map(i => {
      const p = quad[i], q = quad[(i + 1) % 4];
      return { a: p, b: q, len: Math.hypot(q[0] - p[0], q[1] - p[1]) };
    });
    let usePair02 = E[0].len + E[2].len >= E[1].len + E[3].len;
    if (ridgeRad != null) {
      // LiDAR-measured ridge direction: eaves run parallel to the ridge, so pick
      // the edge pair axially closest to it (falls back to the longer pair above)
      const axd = (e) => {
        const a = Math.atan2(e.b[1] - e.a[1], e.b[0] - e.a[0]);
        const d = Math.abs((((a - ridgeRad) % Math.PI) + Math.PI) % Math.PI);
        return Math.min(d, Math.PI - d);
      };
      usePair02 = axd(E[0]) + axd(E[2]) <= axd(E[1]) + axd(E[3]);
    }
    const ev = usePair02 ? [E[0], E[2]] : [E[1], E[3]];
    const ge = usePair02 ? [E[1], E[3]] : [E[0], E[2]];
    const r0 = [(ge[0].a[0] + ge[0].b[0]) / 2, (ge[0].a[1] + ge[0].b[1]) / 2];
    const r1 = [(ge[1].a[0] + ge[1].b[0]) / 2, (ge[1].a[1] + ge[1].b[1]) / 2];
    const cx = (quad[0][0] + quad[1][0] + quad[2][0] + quad[3][0]) / 4;
    const cz = (quad[0][1] + quad[1][1] + quad[2][1] + quad[3][1]) / 4;
    const slopes = [], ends = [], endU = [];
    const pushTri = (arr, A, B, C) => arr.push(A[0], A[1], A[2], B[0], B[1], B[2], C[0], C[1], C[2]);
    const V = (p, y) => [p[0], y, p[1]];
    const slopeQuad = (ea, ridgeNear, ridgeFar) => {
      // ea runs a->b; the ridge end near ea.b is ridgeNear
      let A = V(ea.a, eaveH), B = V(ea.b, eaveH), R0 = V(ridgeNear, ridgeH), R1 = V(ridgeFar, ridgeH);
      const ny = (B[0] - A[0]) * (R0[2] - A[2]) - (B[2] - A[2]) * (R0[0] - A[0]);
      if (ny > 0) { const tmp = A; A = B; B = tmp; const t2 = R0; R0 = R1; R1 = t2; }
      pushTri(slopes, A, B, R0); pushTri(slopes, A, R0, R1);
    };
    // each eave edge's near ridge end is the midpoint of the ge edge SHARING its
    // b vertex — which pair that is depends on where the ring started (usePair02
    // false meant ev[0].b touches ge[1], and the old fixed r0/r1 order emitted a
    // bowtie: a see-through wedge + a coplanar double wedge on half the gables)
    const near0 = (ge[0].a === ev[0].b || ge[0].b === ev[0].b) ? r0 : r1;
    slopeQuad(ev[0], near0, near0 === r0 ? r1 : r0);
    const near1 = (ge[0].a === ev[1].b || ge[0].b === ev[1].b) ? r0 : r1;
    slopeQuad(ev[1], near1, near1 === r0 ? r1 : r0);
    const endTri = (g, r) => {
      let A = V(g.a, eaveH), B = V(g.b, eaveH);
      const R = V(r, ridgeH);
      const mx = (g.a[0] + g.b[0]) / 2 - cx, mz = (g.a[1] + g.b[1]) / 2 - cz;
      const nx = (B[2] - A[2]), nz = -(B[0] - A[0]); // normal of tri (A,B,R) in xz
      if (nx * mx + nz * mz < 0) { const tmp = A; A = B; B = tmp; }
      pushTri(ends, A, B, R);
      endU.push(0, g.len, g.len / 2);
    };
    endTri(ge[0], r0); endTri(ge[1], r1);
    const mk = (arr, isEnds, len) => {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(arr), 3));
      g.computeVertexNormals();
      if (isEnds) {
        const n = arr.length / 3;
        g.setAttribute('aWallU', new THREE.BufferAttribute(new Float32Array(endU), 1));
        g.setAttribute('aWallL', new THREE.BufferAttribute(new Float32Array(n).fill(len), 1));
        g.setAttribute('aWallH', new THREE.BufferAttribute(new Float32Array(n).fill(eaveH), 1));
      }
      return g;
    };
    return { slopes: mk(slopes), ends: mk(ends, true, (ge[0].len + ge[1].len) / 2), eaves: ev, ridge: [r0, r1] };
  }

  // hip roof on the footprint quad: like quadGable but the ridge is inset from both
  // ends and the end faces are sloped planes (roof material), not vertical walls.
  // Only used for LiDAR-measured hips — the guess lottery never emits one.
  function quadHip(quad, eaveH, ridgeH, ridgeRad) {
    const E = [0, 1, 2, 3].map(i => {
      const p = quad[i], q = quad[(i + 1) % 4];
      return { a: p, b: q, len: Math.hypot(q[0] - p[0], q[1] - p[1]) };
    });
    let usePair02 = E[0].len + E[2].len >= E[1].len + E[3].len;
    if (ridgeRad != null) {
      const axd = (e) => {
        const a = Math.atan2(e.b[1] - e.a[1], e.b[0] - e.a[0]);
        const d = Math.abs((((a - ridgeRad) % Math.PI) + Math.PI) % Math.PI);
        return Math.min(d, Math.PI - d);
      };
      usePair02 = axd(E[0]) + axd(E[2]) <= axd(E[1]) + axd(E[3]);
    }
    const ev = usePair02 ? [E[0], E[2]] : [E[1], E[3]];
    const ge = usePair02 ? [E[1], E[3]] : [E[0], E[2]];
    const r0 = [(ge[0].a[0] + ge[0].b[0]) / 2, (ge[0].a[1] + ge[0].b[1]) / 2];
    const r1 = [(ge[1].a[0] + ge[1].b[0]) / 2, (ge[1].a[1] + ge[1].b[1]) / 2];
    const rl = Math.hypot(r1[0] - r0[0], r1[1] - r0[1]) || 1;
    const rdx = (r1[0] - r0[0]) / rl, rdz = (r1[1] - r0[1]) / rl;
    const span = (ge[0].len + ge[1].len) / 2;
    const ins = Math.min(span / 2, rl * 0.38);
    const R0 = [r0[0] + rdx * ins, r0[1] + rdz * ins];
    const R1 = [r1[0] - rdx * ins, r1[1] - rdz * ins];
    const slopes = [];
    const pushTri = (A, B, C) => slopes.push(A[0], A[1], A[2], B[0], B[1], B[2], C[0], C[1], C[2]);
    const V = (p, y) => [p[0], y, p[1]];
    const slopeQuad = (ea, ridgeNear, ridgeFar) => {
      let A = V(ea.a, eaveH), B = V(ea.b, eaveH), Q0 = V(ridgeNear, ridgeH), Q1 = V(ridgeFar, ridgeH);
      const ny = (B[0] - A[0]) * (Q0[2] - A[2]) - (B[2] - A[2]) * (Q0[0] - A[0]);
      if (ny > 0) { const t = A; A = B; B = t; const t2 = Q0; Q0 = Q1; Q1 = t2; }
      pushTri(A, B, Q0); pushTri(A, Q0, Q1);
    };
    const hn0 = (ge[0].a === ev[0].b || ge[0].b === ev[0].b) ? R0 : R1;
    slopeQuad(ev[0], hn0, hn0 === R0 ? R1 : R0);
    const hn1 = (ge[0].a === ev[1].b || ge[0].b === ev[1].b) ? R0 : R1;
    slopeQuad(ev[1], hn1, hn1 === R0 ? R1 : R0);
    const endTri = (g, r) => {
      let A = V(g.a, eaveH), B = V(g.b, eaveH);
      const R = V(r, ridgeH);
      const ny = (B[0] - A[0]) * (R[2] - A[2]) - (B[2] - A[2]) * (R[0] - A[0]);
      if (ny > 0) { const t = A; A = B; B = t; }
      pushTri(A, B, R);
    };
    endTri(ge[0], R0); endTri(ge[1], R1);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(slopes), 3));
    g.computeVertexNormals();
    return { slopes: g, ends: null, eaves: [ev[0], ev[1], ge[0], ge[1]], ridge: [R0, R1] };
  }

  // minimum-area oriented bounding box (aligned with some polygon edge)
  function orientedBox(poly) {
    let best = null;
    for (let i = 0; i < poly.length; i++) {
      const p = poly[i], q = poly[(i + 1) % poly.length];
      const ex = q[0] - p[0], ez = q[1] - p[1];
      const L = Math.hypot(ex, ez);
      if (L < 0.3) continue;
      const ux = ex / L, uz = ez / L;
      let minU = 1e9, maxU = -1e9, minV = 1e9, maxV = -1e9;
      for (const t of poly) {
        const u = t[0] * ux + t[1] * uz, v = -t[0] * uz + t[1] * ux;
        if (u < minU) minU = u; if (u > maxU) maxU = u;
        if (v < minV) minV = v; if (v > maxV) maxV = v;
      }
      const area = (maxU - minU) * (maxV - minV);
      if (!best || area < best.area) best = { area, ux, uz, minU, maxU, minV, maxV };
    }
    if (!best) return null;
    const cu = (best.minU + best.maxU) / 2, cv = (best.minV + best.maxV) / 2;
    return {
      cx: best.ux * cu - best.uz * cv,
      cz: best.uz * cu + best.ux * cv,
      ux: best.ux, uz: best.uz,
      w: best.maxU - best.minU, d: best.maxV - best.minV,
      fill: 0, area: best.area,
    };
  }

  // hip roof over an OBB: ridge along the long axis, shortened at both ends
  function hipGeom(ob, eaveH, ridgeH, overhang) {
    const long = Math.max(ob.w, ob.d), span = Math.min(ob.w, ob.d);
    let ax = ob.ux, az = ob.uz;
    if (ob.d > ob.w) { ax = -ob.uz; az = ob.ux; }
    const px = az, pz = -ax; // right-handed with y-up regardless of source winding
    const hl = long / 2 + (overhang || 0.3), hs = span / 2 + (overhang || 0.3);
    const hr = Math.max(0.5, hl - hs); // ridge half-length
    const P = (u, v, y) => [ob.cx + ax * u + px * v, y, ob.cz + az * u + pz * v];
    const A = P(-hl, -hs, eaveH), B = P(hl, -hs, eaveH), C = P(hl, hs, eaveH), D = P(-hl, hs, eaveH);
    const R1 = P(-hr, 0, ridgeH), R2 = P(hr, 0, ridgeH);
    const pos = [];
    const tri = (a, b, c) => { pos.push(a[0], a[1], a[2], b[0], b[1], b[2], c[0], c[1], c[2]); };
    tri(A, B, R2); tri(A, R2, R1);  // long slope v<0
    tri(C, D, R1); tri(C, R1, R2);  // long slope v>0
    tri(D, A, R1);                   // hip end u<0
    tri(B, C, R2);                   // hip end u>0
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
    g.computeVertexNormals();
    return g;
  }

  // ---- rooftop clutter. The game's roofs are never bare: a parapet lip round the edge, HVAC
  // boxes in a loose row, a stair bulkhead on the taller buildings, a water tank on the older
  // commercial roofs, a chimney on the flat rowhouse. `add(ring, y0, y1, hex, style, holes)`
  // is the tier's own wall builder. Desktop only: the extra vertices are a fifth of a phone's.
  function insetRing(ring, d) {
    const n = ring.length; let a2 = 0;
    for (let i = 0; i < n; i++) a2 += ring[i][0] * ring[(i + 1) % n][1] - ring[(i + 1) % n][0] * ring[i][1];
    const sgn = a2 > 0 ? 1 : -1, out = [];
    for (let i = 0; i < n; i++) {
      const p0 = ring[(i + n - 1) % n], p1 = ring[i], p2 = ring[(i + 1) % n];
      const L1 = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]) || 1e-9, L2 = Math.hypot(p2[0] - p1[0], p2[1] - p1[1]) || 1e-9;
      const n1x = -(p1[1] - p0[1]) / L1 * sgn, n1z = (p1[0] - p0[0]) / L1 * sgn, n2x = -(p2[1] - p1[1]) / L2 * sgn, n2z = (p2[0] - p1[0]) / L2 * sgn;
      const dot = n1x * n2x + n1z * n2z, k = 1 + dot > 0.3 ? d / (1 + dot) : d;
      out.push([p1[0] + (n1x + n2x) * k, p1[1] + (n1z + n2z) * k]);
    }
    return out;
  }
  function roofClutter(add, poly, base, h, area, t, fa, seed, wallC, far) {
    if (isTouch || h < 5) return;
    const ob = orientedBox(poly), ax = obbAxis(ob);
    if (ax.hs < 2.2) return;
    const top = base + h;
    const at = (u, v) => [ob.cx + ax.ax * u + ax.px * v, ob.cz + ax.az * u + ax.pz * v];
    const rect = (u, v, w, d) => [at(u - w / 2, v - d / 2), at(u + w / 2, v - d / 2), at(u + w / 2, v + d / 2), at(u - w / 2, v + d / 2)];
    const r1 = hash01(seed * 3.1 + 0.2), r2 = hash01(seed * 5.7 + 0.4), r3 = hash01(seed * 7.3 + 0.6);
    if (area < 160) {   // a rowhouse: a chimney on the party wall, a third of them
      if (!far && r1 < 0.32 && ax.hl > 5) add(rect((r2 - 0.5) * ax.hl * 1.1, (r3 < 0.5 ? -1 : 1) * (ax.hs - 0.5), 0.7, 0.6), top - 0.2, top + 1.0 + r2 * 0.5, 0x6a4a3c, 3, null);
      return;
    }
    if (far && (area < 600 || h < 8)) return;
    const darkHex = wallC.clone().multiplyScalar(0.7).getHex();
    if (!far && area > 400 && poly.length <= 24) add(poly, top - 0.05, top + 0.45, darkHex, 3, [insetRing(poly, 0.35)]);   // the parapet lip
    const nH = Math.min(far ? 3 : 4, Math.floor(area / 450) + (r1 < 0.5 ? 1 : 0));
    for (let k = 0; k < nH; k++) {
      const u = ((k + 0.5) / nH - 0.5) * ax.hl * 1.3 + (hash01(seed * 1.7 + k) - 0.5) * 3, v = (hash01(seed * 2.9 + k) - 0.5) * ax.hs * 0.9;
      add(rect(u, v, 2.2 + hash01(seed + k) * 1.4, 1.5), top, top + 0.9 + hash01(seed * 4.3 + k) * 0.6, 0x8d8f8c, 3, null);
    }
    if (h > 10 && area > 350) add(rect(ax.hl * 0.55 * (r2 < 0.5 ? -1 : 1), ax.hs * 0.3 * (r3 < 0.5 ? -1 : 1), 4.5, 3.2), top, top + 2.6, darkHex, 3, null);   // the stair bulkhead
    if ((t === 3 || t === 4) && fa && fa[2] <= 3 && r1 < 0.25 && ax.hs > 4) {   // a water tank
      const oct = []; for (let k = 0; k < 8; k++) { const an = k / 8 * Math.PI * 2; oct.push(at(-ax.hl * 0.3 + Math.cos(an) * 1.7, ax.hs * 0.2 + Math.sin(an) * 1.7)); }
      add(oct, top + 1.6, top + 4.6, 0x4a3a30, 3, null);
    }
  }
  // ---- pitched roofs for the packed tiers (outer districts, far ring, outskirts). The roof
  // word carries a form (0 unresolved, 1 gable, 2 hip, 3 skillion, 4 measured or tagged
  // flat) and a rise in half metres from the LiDAR streaming pass or the OSM roof:shape tag;
  // unresolved small houses take the core's gable lottery. Only an honest footprint quad
  // takes a roof (the core's rules: convex, near-rectangular, elongated, covering the
  // footprint): the walls stop at the eave and quadGable / hipGeom sit on top, pushed
  // straight into the chunk. Anything else stays a flat extrusion
  function roofBits(roofW, packed) {
    if (roofW == null || roofW === -1) return [-1, 0, 0];
    if (!packed) return [roofW, 0, 0];
    const rw = roofW & 0xFFFF;
    return [(rw & 0x1FF) - 1, (rw >> 9) & 7, ((rw >> 12) & 15) * 0.5];
  }
  function roofQuad(poly, area, form) {
    if (area > 650 || poly.length > 12) return null;
    let sp = simplifyRing(poly, 0.6);
    if (sp.length !== 4) {
      // not a clean quad (a bay, a jog where twins meet): the oriented box stands in when
      // the footprint fills it, so the roof overhangs by less than a metre. The core keeps
      // its stricter rule; out here a house is 200 m away and the overhang is invisible
      const ob = orientedBox(poly);
      if (!ob || area < 0.8 * ob.w * ob.d) return null;
      let ax = ob.ux, az = ob.uz, long = ob.w, span = ob.d;
      if (ob.d > ob.w) { ax = -ob.uz; az = ob.ux; long = ob.d; span = ob.w; }
      const px = az, pz = -ax, hl = long / 2 - 0.2, hs = span / 2 - 0.2;
      sp = [[ob.cx - ax * hl - px * hs, ob.cz - az * hl - pz * hs], [ob.cx + ax * hl - px * hs, ob.cz + az * hl - pz * hs], [ob.cx + ax * hl + px * hs, ob.cz + az * hl + pz * hs], [ob.cx - ax * hl + px * hs, ob.cz - az * hl + pz * hs]];
    }
    let convex = true, sgn = 0, rect = true;
    for (let k2 = 0; k2 < 4; k2++) {
      const A2 = sp[k2], B2 = sp[(k2 + 1) % 4], C2 = sp[(k2 + 2) % 4];
      const ux2 = B2[0] - A2[0], uz2 = B2[1] - A2[1], vx2 = C2[0] - B2[0], vz2 = C2[1] - B2[1];
      const cr = ux2 * vz2 - uz2 * vx2;
      if (Math.abs(cr) > 1e-6) { if (sgn === 0) sgn = Math.sign(cr); else if (Math.sign(cr) !== sgn) { convex = false; break; } }
      const l1 = Math.hypot(ux2, uz2) || 1, l2 = Math.hypot(vx2, vz2) || 1;
      if (Math.abs((ux2 * vx2 + uz2 * vz2) / (l1 * l2)) > 0.35) rect = false;
    }
    if (!convex || !rect) return null;
    const e = [0, 1, 2, 3].map(k => Math.hypot(sp[(k + 1) % 4][0] - sp[k][0], sp[(k + 1) % 4][1] - sp[k][1]));
    const span = Math.min((e[0] + e[2]) / 2, (e[1] + e[3]) / 2), long = Math.max((e[0] + e[2]) / 2, (e[1] + e[3]) / 2);
    const aQ = Math.abs(signedArea(sp));
    const elMin = form === 2 ? 1.02 : 1.2;
    if (Math.abs(aQ - area) <= area * 0.25 && span > 3.2 && span < 17 && long / span >= elMin && long / span < 5) return { sp, span, long };
    return null;
  }
  function roofPlan(poly, area, h, t, form, rise, seed) {
    if (form === 4 || form === 3 || h < 3.5) return null;
    let f = form;
    if (f === 0) {   // the lottery: small houses the passes never resolved, at rowhouse height
      if (!(t === 1 || t === 0) || area >= 280 || h >= 12.5 || hash01(seed) >= 0.8) return null;
      f = 1;
    }
    const q = roofQuad(poly, area, f);
    if (!q) return null;
    const r = rise > 0.8 ? Math.min(rise, h * 0.7) : clamp(q.span * 0.33, 1.5, 4.0);
    if (r > h * 0.7) return null;
    return { quad: q.sp, form: f, rise: r };
  }
  function pushGeom(ch, g, r, gc, b, st, base) {
    const p = g.attributes.position.array, n = g.attributes.normal.array;
    for (let i = 0; i + 8 < p.length; i += 9) {
      const i0 = ch.n;
      for (let q = 0; q < 3; q++) { const o = i + q * 3; ch.push(p[o], p[o + 1], p[o + 2], n[o], n[o + 1], n[o + 2], r, gc, b, st, base, 0); }
      ch.idx.push(i0, i0 + 1, i0 + 2);
    }
  }
  // walls to the eave, then the roof; the roof takes the sampled roof colour or a darker wall
  function raisePitched(ch, poly, base, h, plan, wallC, wallStyle, fh, capC, appendFn) {
    const eaveY = base + h - plan.rise, ridgeY = base + h;
    appendFn(ch, poly, base - 1.0, eaveY, wallC, wallStyle, base, null, fh, null, true);
    const rc = capC || _roofTmp.copy(wallC).multiplyScalar(0.72);
    if (plan.form === 2) { const ob = orientedBox(plan.quad); if (ob) { pushGeom(ch, hipGeom(ob, eaveY, ridgeY, 0.3), rc.r, rc.g, rc.b, 3, base); return; } }
    const g = quadGable(plan.quad, eaveY, ridgeY, null);
    pushGeom(ch, g.slopes, rc.r, rc.g, rc.b, 3, base);
    pushGeom(ch, g.ends, wallC.r, wallC.g, wallC.b, 3, base);
  }
  const _roofTmp = new THREE.Color();

  // classical column row: n cylinders from (x0,z0) to (x1,z1). Shafts run 2.2 m
  // below grade like walls and tree trunks — colonnades are lifted by the height
  // at the building CENTROID, and sloping ground was leaving columns airborne
  // (the Second Bank's south portico floated above the falling lawn).
  function columnRow(x0, z0, x1, z1, n, h, r, yBase) {
    const geoms = [];
    const sink = 2.2;
    for (let i = 0; i < n; i++) {
      const t = n === 1 ? 0.5 : i / (n - 1);
      const g = new THREE.CylinderGeometry(r * 0.88, r, h + sink, 10);
      g.translate(x0 + (x1 - x0) * t, (yBase || 0) - sink + (h + sink) / 2, z0 + (z1 - z0) * t);
      geoms.push(g);
    }
    return geoms;
  }

  // cupola: square or round base stage + louvered drum + cap
  function cupolaGeoms(cx, cz, yBase, size, tall) {
    const g1 = new THREE.BoxGeometry(size, tall * 0.32, size);
    g1.translate(cx, yBase + tall * 0.16, cz);
    const g2 = new THREE.CylinderGeometry(size * 0.34, size * 0.38, tall * 0.42, 8);
    g2.translate(cx, yBase + tall * 0.32 + tall * 0.21, cz);
    const g3 = new THREE.ConeGeometry(size * 0.42, tall * 0.26, 10);
    g3.translate(cx, yBase + tall * 0.74 + tall * 0.13, cz);
    return [g1, g2, g3];
  }

  // point on an OBB long axis end (dir = world direction to prefer), and face info
  function obbAxis(ob) {
    let ax = ob.ux, az = ob.uz;
    if (ob.d > ob.w) { ax = -ob.uz; az = ob.ux; }
    return { ax, az, px: az, pz: -ax, hl: Math.max(ob.w, ob.d) / 2, hs: Math.min(ob.w, ob.d) / 2 };
  }
  function obbEnd(ob, dirX, dirZ) {
    const a = obbAxis(ob);
    const s = (a.ax * dirX + a.az * dirZ) >= 0 ? 1 : -1;
    return { x: ob.cx + a.ax * a.hl * s, z: ob.cz + a.az * a.hl * s, ax: a.ax * s, az: a.az * s, a };
  }

  // gable roof prism over an OBB: two slopes meeting at a ridge along the long
  // axis, vertical gable-end triangles. Returns non-indexed geometry.
  function gableGeom(ob, eaveH, ridgeH, overhang, endOverhang) {
    const long = Math.max(ob.w, ob.d), span = Math.min(ob.w, ob.d);
    // ridge axis unit vector = OBB long axis
    let ax = ob.ux, az = ob.uz;
    if (ob.d > ob.w) { ax = -ob.uz; az = ob.ux; }
    const px = az, pz = -ax; // right-handed with y-up regardless of source winding
    // gable ends sit flush on the wall plane; only the eaves overhang
    const hl = long / 2 + (endOverhang || 0), hs = span / 2 + (overhang || 0.3);
    const P = (u, v, y) => [ob.cx + ax * u + px * v, y, ob.cz + az * u + pz * v];
    const A = P(-hl, -hs, eaveH), B = P(hl, -hs, eaveH), C = P(hl, hs, eaveH), D = P(-hl, hs, eaveH);
    const R1 = P(-hl, 0, ridgeH), R2 = P(hl, 0, ridgeH);
    const slopes = [], ends = [], endU = [];
    const tri = (arr) => (a, b, c) => { arr.push(a[0], a[1], a[2], b[0], b[1], b[2], c[0], c[1], c[2]); };
    const st = tri(slopes), et = tri(ends);
    st(A, B, R2); st(A, R2, R1);   // slope on the v<0 side
    st(C, D, R1); st(C, R1, R2);   // slope on the v>0 side
    et(D, A, R1); endU.push(0, hs * 2, hs);  // gable end at u=-hl (outward -u)
    et(B, C, R2); endU.push(0, hs * 2, hs);  // gable end at u=+hl (outward +u)
    const mk = (arr, ends) => {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(arr), 3));
      g.computeVertexNormals();
      if (ends) {
        const n = arr.length / 3;
        g.setAttribute('aWallU', new THREE.BufferAttribute(new Float32Array(endU), 1));
        g.setAttribute('aWallL', new THREE.BufferAttribute(new Float32Array(n).fill(hs * 2), 1));
        g.setAttribute('aWallH', new THREE.BufferAttribute(new Float32Array(n).fill(eaveH), 1));
      }
      return g;
    };
    return { slopes: mk(slopes), ends: mk(ends, true), ax, az, px, pz, hl, hs };
  }

  // flat road ribbon with round joints. `lane` ({cls}) asks for the aLane attribute the
  // lane shader reads: vec4(u, s, hw, cls) per vertex, u the signed across-distance from
  // the centreline, s the distance along the densified polyline, hw the half width, cls
  // 0 two-way street, 1 divided highway, 2 no markings. The joint fans carry the averaged
  // direction at their point and sit 2 cm BELOW their strip: the strips win the overlap,
  // so a fan's slightly different parameterisation at a bend never z-fights the strip's
  // paint, and a fan can never rise above a crossing street more than its strip already does
  function ribbon(pts, w, y, yFn, lane) {
    pts = densify(pts, 10);
    // deterministic few-cm lift so no two ribbons are ever exactly coplanar
    y += hash01(pts[0][0] * 0.13 + pts[0][1] * 0.71) * 0.06;
    const hw = w / 2;
    const tris = [];
    const lanes = lane ? [] : null, cls = lane ? lane.cls : 0;
    const ys = pts.map(p => y + (yFn ? yFn(p[0], p[1]) : siteY(p[0], p[1], 'road')));
    // s along the polyline and the averaged heading at every point (for the fans)
    const ss = new Float64Array(pts.length), hd = lane ? new Float64Array(pts.length * 2) : null;
    for (let i = 1; i < pts.length; i++) ss[i] = ss[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    if (lane) {
      for (let i = 0; i < pts.length; i++) {
        const p0 = pts[Math.max(0, i - 1)], p1 = pts[Math.min(pts.length - 1, i + 1)];
        let ex = p1[0] - p0[0], ez = p1[1] - p0[1];
        const el = Math.hypot(ex, ez) || 1;
        hd[i * 2] = ex / el; hd[i * 2 + 1] = ez / el;
      }
    }
    for (let i = 0; i < pts.length - 1; i++) {
      const ax = pts[i][0], az = pts[i][1], bx = pts[i + 1][0], bz = pts[i + 1][1];
      let dx = bx - ax, dz = bz - az;
      const len = Math.hypot(dx, dz);
      if (len < 0.01) continue;
      dx /= len; dz /= len;
      const px = -dz * hw, pz = dx * hw;
      const ya = ys[i], yb = ys[i + 1];
      tris.push(ax + px, ya, az + pz, bx + px, yb, bz + pz, bx - px, yb, bz - pz);
      tris.push(ax + px, ya, az + pz, bx - px, yb, bz - pz, ax - px, ya, az - pz);
      if (lanes) {
        const sa = ss[i], sb = ss[i + 1];
        lanes.push(hw, sa, hw, cls, hw, sb, hw, cls, -hw, sb, hw, cls);
        lanes.push(hw, sa, hw, cls, -hw, sb, hw, cls, -hw, sa, hw, cls);
      }
    }
    for (let i = 0; i < pts.length; i++) {
      const cx = pts[i][0], cz = pts[i][1], yc = ys[i] - (lane ? 0.02 : 0);
      const S = 8;
      const ddx = lane ? hd[i * 2] : 0, ddz = lane ? hd[i * 2 + 1] : 0, si = ss[i];
      for (let k = 0; k < S; k++) {
        const a0 = (k / S) * Math.PI * 2, a1 = ((k + 1) / S) * Math.PI * 2;
        const ox0 = Math.cos(a0) * hw, oz0 = Math.sin(a0) * hw, ox1 = Math.cos(a1) * hw, oz1 = Math.sin(a1) * hw;
        tris.push(cx, yc, cz, cx + ox1, yc, cz + oz1, cx + ox0, yc, cz + oz0);
        if (lanes) {
          // rim u = offset . n_i (n_i the left normal (-dz, dx), the strip's own sense), s = s_i + offset . d_i
          lanes.push(0, si, hw, cls,
            -ox1 * ddz + oz1 * ddx, si + ox1 * ddx + oz1 * ddz, hw, cls,
            -ox0 * ddz + oz0 * ddx, si + ox0 * ddx + oz0 * ddz, hw, cls);
        }
      }
    }
    const g = new THREE.BufferGeometry();
    const arr = new Float32Array(tris);
    g.setAttribute('position', new THREE.BufferAttribute(arr, 3));
    const n = new Float32Array(arr.length);
    for (let i = 0; i < n.length; i += 3) { n[i] = 0; n[i + 1] = 1; n[i + 2] = 0; }
    g.setAttribute('normal', new THREE.BufferAttribute(n, 3));
    if (lanes) g.setAttribute('aLane', new THREE.BufferAttribute(new Float32Array(lanes), 4));
    return g;
  }
  // Lane paint: white lane lines and a double yellow centre computed in the fragment
  // shader from aLane, so the roads carry no extra geometry. Everything sits inside a
  // real branch: a mesh without the attribute reads GL's default (0, 0, 0, 1), and a
  // zero lane period would be NaN on every desktop GPU (NaN * 0 stays NaN). Widths are
  // clamped to about a pixel with a coverage-preserving gain, dashes go to their mean
  // past aliasing, and the paint fades out past ~2.4 m per pixel.
  // Tunables (one place): LANE_W_TWOWAY 3.3 m per lane on a two-way street, LANE_W_DIVIDED
  // 3.7 m on a divided highway, LANE_YELLOW_HW 3.25 (a double yellow from 6.5 m wide),
  // LANE_LINE_W 0.12 m, LANE_DASH_P 9.0 m (3 m on, 6 m off); the paint colours and the
  // 0.85 strength are stored-colour under the legacy pipeline (pale paint, muted yellow, not neon).
  const LANE_GLSL = {
    laneTwoWay: '3.3', laneDivided: '3.7', yellowHw: '3.25', lineW: '0.16', dashP: '9.0',   // 0.16 m paint: the game's lines are wider than life so they read from a few hundred metres
    white: 'vec3(0.62, 0.62, 0.58)', yellow: 'vec3(0.62, 0.50, 0.14)', strength: '0.85',
  };
  function lanePatch(shader) {
    const T = LANE_GLSL;
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nattribute vec4 aLane; varying vec4 vLane;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvLane = aLane;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec4 vLane;')
      // a line mask with its pixel-wide ramp CENTRED on the edge: a ramp lying inside the
      // line ate a full pixel of it, and from 150 m up (a pixel is the line's width) the
      // paint's coverage fell under half a pixel and the streets read bare
      .replace('void main() {', 'float lnLine(float d, float h, float aa){ return 1.0 - smoothstep(h - 0.5 * aa, h + 0.5 * aa, d); }\nvoid main() {')
      .replace('#include <color_fragment>', '#include <color_fragment>\n' + [
        // the derivatives stay outside the branch (defined only in uniform control flow); they are NaN-safe there
        'float lnW = fwidth(vLane.x) + 1e-4;',                    // metres per pixel across the road
        'float lnLs = fwidth(vLane.y) + 1e-4;',                   // metres per pixel along it
        'if (vLane.z > 0.5 && vLane.w < 1.5) {',
        '  float lnHw = vLane.z, lnU = vLane.x, lnS = vLane.y;',
        '  float lnLineW = max(' + T.lineW + ', lnW * 0.9);',            // never thinner than about a pixel
        '  float lnGain = clamp(' + T.lineW + ' / lnLineW, 0.55, 1.0);', // coverage-preserving intensity (floored: a far street keeps a faint stripe)
        '  float lnFar = 1.0 - smoothstep(1.2, 2.4, lnW);',              // gone past ~2.4 m per pixel
        '  float lnDash = mix(step(fract(lnS / ' + T.dashP + '), 0.333), 0.333, smoothstep(1.5, 4.5, lnLs));',
        '  float lnWhite = 0.0, lnYel = 0.0;',
        '  if (vLane.w < 0.5) {',                                        // a two-way street
        '    if (lnHw >= ' + T.yellowHw + ') {',                         // a double yellow centre, two 0.10 m lines at +-0.16
        '      float lnDy = abs(abs(lnU) - 0.16);',
        '      lnYel = lnLine(lnDy, max(0.05, lnLineW * 0.5), lnW);',
        '    }',
        '    float lnNl = max(1.0, floor(lnHw / ' + T.laneTwoWay + ' + 0.5));', // lanes per side (round)
        '    float lnP = max(lnHw / lnNl, 0.5);',
        '    float lnDu = abs(fract(abs(lnU) / lnP + 0.5) - 0.5) * lnP;',
        '    float lnIn = step(0.5 * lnP, abs(lnU)) * step(abs(lnU), lnHw - 0.5 * lnP);', // not the centre, not the edge
        '    lnWhite = lnLine(lnDu, lnLineW * 0.5, lnW) * lnIn * lnDash;',
        '  } else {',                                                    // divided: lanes across the width, solid edges, no yellow
        '    float lnN = max(2.0, floor(2.0 * lnHw / ' + T.laneDivided + ' + 0.5));',
        '    float lnP = max(2.0 * lnHw / lnN, 0.5);',
        '    float lnV = lnU + lnHw;',
        '    float lnDu = abs(fract(lnV / lnP + 0.5) - 0.5) * lnP;',
        '    float lnIn = step(0.5 * lnP, lnV) * step(lnV, 2.0 * lnHw - 0.5 * lnP);',
        '    lnWhite = lnLine(lnDu, lnLineW * 0.5, lnW) * lnIn * lnDash;',
        '    float lnDe = abs(abs(lnU) - (lnHw - 0.35));',
        '    lnWhite = max(lnWhite, lnLine(lnDe, lnLineW * 0.5, lnW));',
        '  }',
        '  diffuseColor.rgb = mix(diffuseColor.rgb, ' + T.white + ', lnWhite * lnGain * lnFar * ' + T.strength + ');',
        '  diffuseColor.rgb = mix(diffuseColor.rgb, ' + T.yellow + ', lnYel * lnGain * lnFar * ' + T.strength + ');',
        '}',
      ].join('\n'));
  }
  // the road material: surfMat's meadow/mottle hook with the lane paint chained after it.
  // Each hook inserts after the first '#include <color_fragment>', so the later call lands
  // earlier in the shader: lanePatch first here means the asphalt mottle runs first and the
  // paint goes over it (the weather hookup wraps snow over both and re-keys). r149 keys the
  // program on onBeforeCompile.toString(), so a wrapped hook needs its own cache key (gotcha 15).
  function roadMat(o) {
    const m = surfMat(o);
    const prev = m.onBeforeCompile;
    m.onBeforeCompile = (sh, r) => { lanePatch(sh); prev(sh, r); };
    m.customProgramCacheKey = () => 'lane|' + prev.toString();
    return m;
  }
  // streets follow the terrain: add a vertex every `step` meters
  function densify(pts, step) {
    const out = [pts[0]];
    for (let i = 0; i < pts.length - 1; i++) {
      const a = pts[i], b = pts[i + 1];
      const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const k = Math.max(1, Math.ceil(L / step));
      for (let j = 1; j <= k; j++) out.push([a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k]);
    }
    return out;
  }

  // Bowyer-Watson Delaunay on [x,z] points -> triangles of indices
  function delaunay(P) {
    const n = P.length;
    let minX = Infinity, minZ = Infinity, maxX = -Infinity, maxZ = -Infinity;
    for (const q of P) { minX = Math.min(minX, q[0]); maxX = Math.max(maxX, q[0]); minZ = Math.min(minZ, q[1]); maxZ = Math.max(maxZ, q[1]); }
    const dm = Math.max(maxX - minX, maxZ - minZ) * 3 + 10, mx = (minX + maxX) / 2, mz = (minZ + maxZ) / 2;
    const pts = P.concat([[mx - dm * 2, mz - dm], [mx, mz + dm * 2], [mx + dm * 2, mz - dm]]);
    const circ = (ia, ib, ic) => {
      const ax = pts[ia][0], az = pts[ia][1], bx = pts[ib][0], bz = pts[ib][1], cx = pts[ic][0], cz = pts[ic][1];
      const d = 2 * (ax * (bz - cz) + bx * (cz - az) + cx * (az - bz));
      if (Math.abs(d) < 1e-9) return null;
      const a2 = ax * ax + az * az, b2 = bx * bx + bz * bz, c2 = cx * cx + cz * cz;
      const ux = (a2 * (bz - cz) + b2 * (cz - az) + c2 * (az - bz)) / d;
      const uz = (a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)) / d;
      return { x: ux, z: uz, r2: (ax - ux) * (ax - ux) + (az - uz) * (az - uz) };
    };
    let tris = [{ a: n, b: n + 1, c: n + 2, cc: circ(n, n + 1, n + 2) }];
    const key = (u, v) => u < v ? u * 1048576 + v : v * 1048576 + u;
    for (let i = 0; i < n; i++) {
      const px = pts[i][0], pz = pts[i][1];
      const bad = [], keep = [];
      for (const tr of tris) {
        if (tr.cc && (px - tr.cc.x) * (px - tr.cc.x) + (pz - tr.cc.z) * (pz - tr.cc.z) <= tr.cc.r2) bad.push(tr); else keep.push(tr);
      }
      const count = new Map();
      for (const tr of bad) for (const e of [[tr.a, tr.b], [tr.b, tr.c], [tr.c, tr.a]]) { const k = key(e[0], e[1]); count.set(k, (count.get(k) || 0) + 1); }
      for (const tr of bad) for (const e of [[tr.a, tr.b], [tr.b, tr.c], [tr.c, tr.a]]) {
        if (count.get(key(e[0], e[1])) === 1) keep.push({ a: e[0], b: e[1], c: i, cc: circ(e[0], e[1], i) });
      }
      tris = keep;
    }
    return tris.filter(tr => tr.a < n && tr.b < n && tr.c < n).map(tr => [tr.a, tr.b, tr.c]);
  }

  // A flat water sheet whose vertices carry their distance to the shore in the colour's alpha
  // (0 at the bank, 1 at 60 m out): earcut over the outline and its holes, every triangle split
  // `levels` times so the interior has vertices of its own, the distance from a grid of the
  // edges. liquify() reads the alpha for the shallows tint, the shoreline foam and calmer
  // water under the bank, the way the game's water shows its depth
  function flatShorePoly(poly, holes, y, levels) {
    const g0 = flatPoly(poly, holes, y, true).toNonIndexed();
    const p0 = g0.attributes.position.array;
    let tris = [];
    for (let i = 0; i < p0.length; i += 9) tris.push([[p0[i], p0[i + 2]], [p0[i + 3], p0[i + 5]], [p0[i + 6], p0[i + 8]]]);
    for (let l = 0; l < (levels || 0); l++) {
      const out = [];
      for (const [A, B, C] of tris) {
        const AB = [(A[0] + B[0]) / 2, (A[1] + B[1]) / 2], BC = [(B[0] + C[0]) / 2, (B[1] + C[1]) / 2], CA = [(C[0] + A[0]) / 2, (C[1] + A[1]) / 2];
        out.push([A, AB, CA], [AB, B, BC], [CA, BC, C], [AB, BC, CA]);
      }
      tris = out;
    }
    const rings = [poly].concat(holes || []);
    const EC = 30, egrid = new Map(), segs = [];
    for (let ri = 0; ri < rings.length; ri++) {
      const r = rings[ri], n = r.length;
      let ar = 0; for (let k = 0; k < n; k++) ar += r[k][0] * r[(k + 1) % n][1] - r[(k + 1) % n][0] * r[k][1];
      const sgn = (ar > 0 ? 1 : -1) * (ri === 0 ? 1 : -1);   // the normal away from the water (into the island for a hole)
      for (let k = 0; k < n; k++) {
        const a = r[k], b = r[(k + 1) % n], dx = b[0] - a[0], dz = b[1] - a[1], L = Math.hypot(dx, dz);
        if (L < 0.01) continue;
        // a shore only where the ground 4 m outside the edge stands above the water; a seam with
        // another sheet, a tier's clip edge or a bank the DEM floods is open water to the shader
        const ox = (dz / L) * sgn, oz = (-dx / L) * sgn, mx = (a[0] + b[0]) / 2 + ox * 4, mz = (a[1] + b[1]) / 2 + oz * 4;
        if (siteY(mx, mz, 'ground') < TERRAIN.water + 0.4) continue;
        const sid = segs.length; segs.push([a[0], a[1], dx / L, dz / L, L]);
        for (let gx = Math.floor(Math.min(a[0], b[0]) / EC); gx <= Math.floor(Math.max(a[0], b[0]) / EC); gx++)
          for (let gz = Math.floor(Math.min(a[1], b[1]) / EC); gz <= Math.floor(Math.max(a[1], b[1]) / EC); gz++) { const key = gx + ':' + gz; let lst = egrid.get(key); if (!lst) { lst = []; egrid.set(key, lst); } lst.push(sid); }
      }
    }
    const dist = (x, z) => {
      let best = 3600; const gx = Math.floor(x / EC), gz = Math.floor(z / EC);
      for (let a = -2; a <= 2; a++) for (let b2 = -2; b2 <= 2; b2++) {
        const lst = egrid.get((gx + a) + ':' + (gz + b2)); if (!lst) continue;
        for (const sid of lst) { const sg = segs[sid]; const t = clamp((x - sg[0]) * sg[2] + (z - sg[1]) * sg[3], 0, sg[4]); const px = x - (sg[0] + sg[2] * t), pz = z - (sg[1] + sg[3] * t), d2 = px * px + pz * pz; if (d2 < best) best = d2; }
      }
      return Math.sqrt(best);
    };
    const n = tris.length * 3, pos = new Float32Array(n * 3), nor = new Float32Array(n * 3), col = new Float32Array(n * 4);
    const wc = new THREE.Color(COLORS.water);
    let o = 0;
    for (const tri of tris) for (const q of tri) {
      pos[o * 3] = q[0]; pos[o * 3 + 1] = y; pos[o * 3 + 2] = q[1];
      nor[o * 3 + 1] = 1;
      col[o * 4] = wc.r; col[o * 4 + 1] = wc.g; col[o * 4 + 2] = wc.b; col[o * 4 + 3] = Math.min(1, dist(q[0], q[1]) / 60);
      o++;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
    g.setAttribute('color', new THREE.BufferAttribute(col, 4));
    return g;
  }
  // the water parts merged with a four-channel colour (a part without its own shore alpha is deep water)
  function mergeWater(parts) {
    let count = 0;
    const prepped = parts.map(p => { const g = p.geom.index ? p.geom.toNonIndexed() : p.geom; count += g.attributes.position.count; return { g, c: p.color }; });
    const pos = new Float32Array(count * 3), nor = new Float32Array(count * 3), col = new Float32Array(count * 4);
    let o = 0;
    for (const { g, c } of prepped) {
      const vc = g.attributes.position.count;
      pos.set(g.attributes.position.array, o * 3); nor.set(g.attributes.normal.array, o * 3);
      const ca = g.attributes.color;
      if (ca && ca.itemSize === 4) col.set(ca.array, o * 4);
      else for (let i = 0; i < vc; i++) { col[(o + i) * 4] = c.r; col[(o + i) * 4 + 1] = c.g; col[(o + i) * 4 + 2] = c.b; col[(o + i) * 4 + 3] = 1; }
      o += vc;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
    g.setAttribute('color', new THREE.BufferAttribute(col, 4));
    return g;
  }
  // a flat polygon draped over the terrain: densified boundary + interior points, triangulated
  // the drape's terrain read: siteY, but carved with the Schuylkill's channel like the ground
  // meshes are, so a park drawn across the pool dips under the water instead of roofing it
  function drapeY(x, z, mode) {
    return riverCarve(x, z, siteY(x, z, mode));
  }
  function drapedPoly(poly, yOff, spacing) {
    const area = Math.abs(signedArea(poly));
    spacing = Math.max(spacing, Math.sqrt(area / 420));
    const pts = [];
    const n = poly.length;
    for (let i = 0; i < n; i++) {
      const a = poly[i], b = poly[(i + 1) % n];
      const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const k = Math.max(1, Math.ceil(L / spacing));
      for (let j = 0; j < k; j++) pts.push([a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k]);
    }
    let x0 = Infinity, z0 = Infinity, x1 = -Infinity, z1 = -Infinity;
    for (const q of poly) { x0 = Math.min(x0, q[0]); x1 = Math.max(x1, q[0]); z0 = Math.min(z0, q[1]); z1 = Math.max(z1, q[1]); }
    const edgeDist = (x, z) => {
      let best = Infinity;
      for (let i = 0; i < n; i++) {
        const a = poly[i], b = poly[(i + 1) % n];
        const dx = b[0] - a[0], dz = b[1] - a[1], L2 = dx * dx + dz * dz;
        let tt = L2 > 0 ? ((x - a[0]) * dx + (z - a[1]) * dz) / L2 : 0; tt = clamp(tt, 0, 1);
        const ex = a[0] + dx * tt - x, ez = a[1] + dz * tt - z;
        best = Math.min(best, ex * ex + ez * ez);
      }
      return Math.sqrt(best);
    };
    for (let x = x0 + spacing * 0.5; x < x1; x += spacing) for (let z = z0 + spacing * 0.5; z < z1; z += spacing) {
      const px = x + (hash01(x * 0.37 + z * 1.91) - 0.5) * spacing * 0.4, pz = z + (hash01(x * 1.13 + z * 0.71) - 0.5) * spacing * 0.4;
      if (pointInPoly(px, pz, poly) && edgeDist(px, pz) > spacing * 0.3) pts.push([px, pz]);
    }
    const tris = delaunay(pts);
    const pos = [];
    const ys = pts.map(q => drapeY(q[0], q[1], 'ground') + yOff);
    for (const [ia, ib, ic] of tris) {
      const A = pts[ia], B = pts[ib], C = pts[ic];
      if (!pointInPoly((A[0] + B[0] + C[0]) / 3, (A[1] + B[1] + C[1]) / 3, poly)) continue;
      // orient so the normal points up (+y): in xz, (B-A)x(C-A) must be negative for a right-handed y-up frame
      const cr = (B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0]);
      const [P1, y1, P2, y2] = cr < 0 ? [B, ys[ib], C, ys[ic]] : [C, ys[ic], B, ys[ib]];
      pos.push(A[0], ys[ia], A[1], P1[0], y1, P1[1], P2[0], y2, P2[1]);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
    g.computeVertexNormals();
    return g;
  }

  // ---- the ground registry (Round 52). Outside the core the drawn ground is a set of
  // heightfields (the four wide strips at ~25 m, the four far strips at 100 m, the NW hills
  // patch at 50 m), each registered here as it is built: its OWN vertex heights and normals,
  // so a flat laid on it can read the exact surface the mesh draws instead of a second linear
  // read of the DEM that disagrees with the first by up to half a metre (Round 47's lots
  // clipping through their sheets; codas 5 and 6 could not converge by draping denser).
  // Searched last-registered-first: the NW patch registers after the north far strip and wins
  // inside that strip's hole. A grid whose hole holds the point is passed over; a cell the
  // builder skipped (the Vine Street cut, the NW hole) answers null, and the caller falls
  // back to drapeY. Vertex (i, j) sits at x0 + (x1 - x0) * i / nx, z0 + (z1 - z0) * j / nz,
  // the builders' own expression, and cell (i, j) is the two triangles (a, c, b) over
  // u + v <= 1 and (b, c, d) over u + v >= 1 with a = (i, j), b = (i + 1, j), c = (i, j + 1)
  // and d = (i + 1, j + 1), the builders' own index order. The core is never registered:
  // its ground is under hand-built lawns, plazas and decks that keep siteY.
  const groundGrids = [];
  function registerGround(g, x0, x1, z0, z1, nx, nz, hole, skip, cell) {
    const p = g.attributes.position.array, ys = new Float32Array((nx + 1) * (nz + 1));
    for (let v = 0; v < ys.length; v++) ys[v] = p[v * 3 + 1];
    groundGrids.push({ x0, x1, z0, z1, nx, nz, ys, nrm: g.attributes.normal.array, hole, skip, cell });
  }
  function groundGridAt(x, z) {
    for (let gi = groundGrids.length - 1; gi >= 0; gi--) {
      const G = groundGrids[gi];
      if (x < G.x0 || x > G.x1 || z < G.z0 || z > G.z1) continue;
      if (G.hole && x > G.hole.x0 && x < G.hole.x1 && z > G.hole.z0 && z < G.hole.z1) continue;
      return G;
    }
    return null;
  }
  // the cell of a point on a grid and its local (u, v); the index is clamped so the grid's
  // own far edge belongs to its last cell
  function groundCell(G, x, z, out) {
    const fu = (x - G.x0) * G.nx / (G.x1 - G.x0), fv = (z - G.z0) * G.nz / (G.z1 - G.z0);
    let i = Math.floor(fu), j = Math.floor(fv);
    if (i < 0) i = 0; else if (i > G.nx - 1) i = G.nx - 1;
    if (j < 0) j = 0; else if (j > G.nz - 1) j = G.nz - 1;
    out[0] = i; out[1] = j; out[2] = fu - i; out[3] = fv - j;
    return out;
  }
  // the plane of one ground triangle at local (u, v): side 0 is (a, c, b), side 1 is (b, c, d)
  function groundPlaneY(G, i, j, side, u, v) {
    const a = j * (G.nx + 1) + i, ys = G.ys;
    if (side === 0) return ys[a] + (ys[a + 1] - ys[a]) * u + (ys[a + G.nx + 1] - ys[a]) * v;
    const d = a + G.nx + 2;
    return ys[d] + (ys[a + G.nx + 1] - ys[d]) * (1 - u) + (ys[a + 1] - ys[d]) * (1 - v);
  }
  // the barycentric blend of the three corner normals, so a sheet shades like the ground under it
  function groundPlaneN(G, i, j, side, u, v, out) {
    const a = j * (G.nx + 1) + i, b = a + 1, c = a + G.nx + 1, d = c + 1, N = G.nrm;
    let wa = 0, wb, wc, wd = 0;
    if (side === 0) { wa = 1 - u - v; wb = u; wc = v; } else { wd = u + v - 1; wb = 1 - v; wc = 1 - u; }
    let nx = N[a * 3] * wa + N[b * 3] * wb + N[c * 3] * wc + N[d * 3] * wd;
    let ny = N[a * 3 + 1] * wa + N[b * 3 + 1] * wb + N[c * 3 + 1] * wc + N[d * 3 + 1] * wd;
    let nz = N[a * 3 + 2] * wa + N[b * 3 + 2] * wb + N[c * 3 + 2] * wc + N[d * 3 + 2] * wd;
    const L = Math.hypot(nx, ny, nz) || 1;
    out[0] = nx / L; out[1] = ny / L; out[2] = nz / L;
    return out;
  }
  const _gc4 = [0, 0, 0, 0], _gn3 = [0, 1, 0];
  // the height of the drawn ground mesh at (x, z): null off every grid and on a skipped cell
  function groundMeshY(x, z) {
    const G = groundGridAt(x, z);
    if (!G) return null;
    groundCell(G, x, z, _gc4);
    const i = _gc4[0], j = _gc4[1], u = _gc4[2], v = _gc4[3];
    if (G.skip && G.skip[j * G.nx + i]) return null;
    return groundPlaneY(G, i, j, u + v <= 1 ? 0 : 1, u, v);
  }
  function groundMeshN(x, z, out) {
    const G = groundGridAt(x, z);
    if (!G) return null;
    groundCell(G, x, z, _gc4);
    const i = _gc4[0], j = _gc4[1], u = _gc4[2], v = _gc4[3];
    if (G.skip && G.skip[j * G.nx + i]) return null;
    return groundPlaneN(G, i, j, u + v <= 1 ? 0 : 1, u, v, out || _gn3);
  }
  // the road loops' read: the drawn ground where it is land, null where the mesh is water (the
  // carved Schuylkill channel, the Delaware bed, the WWB dip), so the bridge and deck logic
  // that keys off siteY and the DEM keeps the inputs it was tuned on there
  function groundMeshLandY(x, z) {
    const y = groundMeshY(x, z);
    return y !== null && y > TERRAIN.water + 0.3 ? y : null;
  }

  // ---- conformDrape (Round 52): a flat polygon laid on the registered ground so that every
  // triangle of the sheet lies inside ONE ground triangle, which puts the sheet exactly yOff
  // above the drawn mesh everywhere. Per registered grid the polygon is clipped to the grid's
  // rectangle (Sutherland-Hodgman, a convex clip; a concave subject is fine) and rasterised
  // per ROW: the piece's edges are bucketed by the rows they span, each row's centre line is
  // cut by them for the inside runs (parity), a cell no edge touches inside a run emits its
  // two ground triangles whole, a cell an edge touches is clipped to the cell rectangle, split
  // by the cell's diagonal into the two triangles' sides and each side earcut (fed as
  // Vector2(x, -z) and emitted forward, gotcha 10). Slivers and any triangle whose centroid
  // lies outside the piece (a clip can bridge two arms of a U with a zero-width slit) are
  // dropped, and everything is oriented so (B - A) x (C - A) in (x, z) is negative (+y),
  // drapedPoly's own rule. Whatever lies outside every registered grid (Fairmount's overhang
  // past the wide box, anything over the unregistered core) goes to drapedPoly as before.
  const DRAPE_STATS = { ms: 0, polys: 0, tris: 0, fallbacks: 0, logMs: 0, logPolys: 0, logTris: 0, logFallbacks: 0 };
  PERF.drape = DRAPE_STATS;   // read through ?dev's __dbg.PERF.drape
  function drapeLog(label) {
    if (!/[?&]dev\b/.test(location.search)) return;
    const S = DRAPE_STATS;
    console.log('conformDrape, ' + label + ': ' + Math.round(S.ms - S.logMs) + ' ms, ' + (S.polys - S.logPolys) + ' polygons, ' + (S.tris - S.logTris) + ' triangles, ' + (S.fallbacks - S.logFallbacks) + ' drapedPoly fallbacks (total ' + Math.round(S.ms) + ' ms)');
    S.logMs = S.ms; S.logPolys = S.polys; S.logTris = S.tris; S.logFallbacks = S.fallbacks;
  }
  // keep the side of an axis-aligned line: ax 0 = x, 1 = z; above keeps p[ax] >= val, else <= val.
  // A crossing lands exactly on the line, so cell edges shared by two cells agree to the bit
  function clipAxis(ring, ax, val, above) {
    const out = [], n = ring.length;
    for (let i = 0; i < n; i++) {
      const p = ring[i], q = ring[(i + 1) % n];
      const fp = above ? p[ax] - val : val - p[ax], fq = above ? q[ax] - val : val - q[ax];
      if (fp >= 0) out.push(p);
      if ((fp >= 0) !== (fq >= 0)) {
        const t = fp / (fp - fq), c = [p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t];
        c[ax] = val;
        out.push(c);
      }
    }
    return out;
  }
  function clipRect(ring, x0, x1, z0, z1) {
    let r = clipAxis(ring, 0, x0, true);
    if (r.length > 2) r = clipAxis(r, 0, x1, false);
    if (r.length > 2) r = clipAxis(r, 1, z0, true);
    if (r.length > 2) r = clipAxis(r, 1, z1, false);
    return r.length > 2 ? r : null;
  }
  // keep one side of a cell's diagonal u + v = 1: sgn +1 keeps u + v <= 1 (triangle a, c, b),
  // -1 keeps u + v >= 1 (triangle b, c, d); points on the diagonal belong to both
  function clipDiag(ring, xa, za, cw, ch, sgn) {
    const out = [], n = ring.length;
    const f = (p) => sgn * (1 - (p[0] - xa) / cw - (p[1] - za) / ch);
    for (let i = 0; i < n; i++) {
      const p = ring[i], q = ring[(i + 1) % n];
      const fp = f(p), fq = f(q);
      if (fp >= 0) out.push(p);
      if ((fp >= 0) !== (fq >= 0)) { const t = fp / (fp - fq); out.push([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]); }
    }
    return out.length > 2 ? out : null;
  }
  // the four convex pieces of a ring outside a rectangle (x below, x above, then the band's
  // z below and z above), for the remainders drapedPoly still owns
  function outsideRect(ring, x0, x1, z0, z1, out) {
    const push = (r) => { if (r && r.length > 2 && Math.abs(signedArea(r)) > 1e-3) out.push(r); };
    push(clipAxis(ring, 0, x0, false));
    push(clipAxis(ring, 0, x1, true));
    let band = clipAxis(ring, 0, x0, true);
    if (band.length > 2) band = clipAxis(band, 0, x1, false);
    if (band.length > 2) { push(clipAxis(band, 1, z0, false)); push(clipAxis(band, 1, z1, true)); }
  }
  // drop the repeated points a clip leaves behind
  function tidyRing(r) {
    const out = [];
    for (const p of r) { const l = out[out.length - 1]; if (!l || Math.abs(l[0] - p[0]) > 1e-7 || Math.abs(l[1] - p[1]) > 1e-7) out.push(p); }
    if (out.length > 1 && Math.abs(out[0][0] - out[out.length - 1][0]) <= 1e-7 && Math.abs(out[0][1] - out[out.length - 1][1]) <= 1e-7) out.pop();
    return out.length > 2 ? out : null;
  }
  function conformDrape(poly, yOff, spacing) {
    spacing = spacing || 20;   // the drapedPoly fallbacks' spacing (drapedPoly's cap still applies)
    const t0 = performance.now();
    let bx0 = Infinity, bz0 = Infinity, bx1 = -Infinity, bz1 = -Infinity;
    for (const q of poly) { if (q[0] < bx0) bx0 = q[0]; if (q[0] > bx1) bx1 = q[0]; if (q[1] < bz0) bz0 = q[1]; if (q[1] > bz1) bz1 = q[1]; }
    const pos = [], nor = [], covered = [];
    let tris = 0;
    const emitTri = (A, B, C, piece, G, i, j, side) => {
      const cr = (B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0]);
      if (Math.abs(cr) < 1e-6) return;
      if (!pointInPoly((A[0] + B[0] + C[0]) / 3, (A[1] + B[1] + C[1]) / 3, piece)) return;
      if (cr > 0) { const T = B; B = C; C = T; }
      const sx = G.nx / (G.x1 - G.x0), sz = G.nz / (G.z1 - G.z0);
      for (const P of [A, B, C]) {
        const u = (P[0] - G.x0) * sx - i, v = (P[1] - G.z0) * sz - j;
        pos.push(P[0], groundPlaneY(G, i, j, side, u, v) + yOff, P[1]);
        groundPlaneN(G, i, j, side, u, v, _gn3);
        nor.push(_gn3[0], _gn3[1], _gn3[2]);
      }
      tris++;
    };
    const emitRing = (r, piece, G, i, j, side) => {
      r = tidyRing(r);
      if (!r) return;
      const v2 = r.map(p => new THREE.Vector2(p[0], -p[1]));
      let tt;
      try { tt = THREE.ShapeUtils.triangulateShape(v2, []); } catch (e) { return; }
      for (const t of tt) emitTri(r[t[0]], r[t[1]], r[t[2]], piece, G, i, j, side);
    };
    const drapeOnGrid = (G, piece) => {
      const nx = G.nx, nz = G.nz, cw = (G.x1 - G.x0) / nx, ch = (G.z1 - G.z0) / nz;
      const xi = (i) => G.x0 + (G.x1 - G.x0) * i / nx, zj = (j) => G.z0 + (G.z1 - G.z0) * j / nz;
      let px0 = Infinity, pz0 = Infinity, px1 = -Infinity, pz1 = -Infinity;
      for (const q of piece) { if (q[0] < px0) px0 = q[0]; if (q[0] > px1) px1 = q[0]; if (q[1] < pz0) pz0 = q[1]; if (q[1] > pz1) pz1 = q[1]; }
      const i0 = clamp(Math.floor((px0 - G.x0) / cw), 0, nx - 1), i1 = clamp(Math.floor((px1 - G.x0) / cw), 0, nx - 1);
      const j0 = clamp(Math.floor((pz0 - G.z0) / ch), 0, nz - 1), j1 = clamp(Math.floor((pz1 - G.z0) / ch), 0, nz - 1);
      const n = piece.length;
      const rows = new Array(j1 - j0 + 1);
      for (let r = 0; r < rows.length; r++) rows[r] = [];
      for (let e = 0; e < n; e++) {
        const p = piece[e], q = piece[(e + 1) % n];
        const ja = clamp(Math.floor((Math.min(p[1], q[1]) - G.z0) / ch), j0, j1), jb = clamp(Math.floor((Math.max(p[1], q[1]) - G.z0) / ch), j0, j1);
        for (let j = ja; j <= jb; j++) rows[j - j0].push(e);
      }
      const touched = new Uint8Array(i1 - i0 + 1), xs = [];
      const ys = G.ys, N = G.nrm;
      for (let j = j0; j <= j1; j++) {
        const bucket = rows[j - j0];
        if (!bucket.length) continue;   // a row no edge spans holds no inside run either
        const za = zj(j), zb = zj(j + 1), zc = (za + zb) / 2;
        touched.fill(0); xs.length = 0;
        for (const e of bucket) {
          const p = piece[e], q = piece[(e + 1) % n];
          // the edge's x-span within THIS row's band marks the cells it touches
          let ta = 0, tb = 1;
          if (p[1] !== q[1]) {
            const u0 = (za - p[1]) / (q[1] - p[1]), u1 = (zb - p[1]) / (q[1] - p[1]);
            ta = Math.max(0, Math.min(u0, u1)); tb = Math.min(1, Math.max(u0, u1));
          }
          const xA = p[0] + (q[0] - p[0]) * ta, xB = p[0] + (q[0] - p[0]) * tb;
          const ia = clamp(Math.floor((Math.min(xA, xB) - G.x0) / cw), i0, i1), ib = clamp(Math.floor((Math.max(xA, xB) - G.x0) / cw), i0, i1);
          for (let i = ia; i <= ib; i++) touched[i - i0] = 1;
          if ((p[1] > zc) !== (q[1] > zc)) xs.push(p[0] + (q[0] - p[0]) * (zc - p[1]) / (q[1] - p[1]));
        }
        xs.sort((a, b) => a - b);
        for (let i = i0; i <= i1; i++) {
          if (G.skip && G.skip[j * nx + i]) continue;
          const xa = xi(i), xb = xi(i + 1);
          if (!touched[i - i0]) {
            const cx = (xa + xb) / 2;
            let c = 0;
            for (let s = 0; s < xs.length && xs[s] < cx; s++) c++;
            if (!(c & 1)) continue;
            // the whole cell, the ground's own two triangles a hair up
            const a = j * (nx + 1) + i, b = a + 1, cc = a + nx + 1, d = cc + 1;
            pos.push(xa, ys[a] + yOff, za, xa, ys[cc] + yOff, zb, xb, ys[b] + yOff, za);
            pos.push(xb, ys[b] + yOff, za, xa, ys[cc] + yOff, zb, xb, ys[d] + yOff, zb);
            for (const vi of [a, cc, b, b, cc, d]) nor.push(N[vi * 3], N[vi * 3 + 1], N[vi * 3 + 2]);
            tris += 2;
            continue;
          }
          const cl = clipRect(piece, xa, xb, za, zb);
          if (!cl) continue;
          const sA = clipDiag(cl, xa, za, cw, ch, 1), sB = clipDiag(cl, xa, za, cw, ch, -1);
          if (sA) emitRing(sA, piece, G, i, j, 0);
          if (sB) emitRing(sB, piece, G, i, j, 1);
        }
      }
    };
    for (let gi = groundGrids.length - 1; gi >= 0; gi--) {
      const G = groundGrids[gi];
      if (bx1 <= G.x0 || bx0 >= G.x1 || bz1 <= G.z0 || bz0 >= G.z1) continue;
      covered.push(G);
      const piece = clipRect(poly, G.x0, G.x1, G.z0, G.z1);
      if (!piece || Math.abs(signedArea(piece)) < 1e-3) continue;
      drapeOnGrid(G, piece);
    }
    let g;
    if (!covered.length) {
      DRAPE_STATS.fallbacks++;
      g = drapedPoly(poly, yOff, spacing);
    } else {
      // the remainders: whatever the registered grids do not cover, on drapedPoly as before
      let rem = [poly];
      for (const G of covered) { const next = []; for (const r of rem) outsideRect(r, G.x0, G.x1, G.z0, G.z1, next); rem = next; }
      for (const r of rem) {
        if (Math.abs(signedArea(r)) < 4) continue;
        let rg = null;
        try { rg = drapedPoly(r, yOff, spacing); } catch (e) { continue; }
        DRAPE_STATS.fallbacks++;
        const rp = rg.attributes.position.array, rn = rg.attributes.normal.array;
        for (let v = 0; v < rp.length; v++) { pos.push(rp[v]); nor.push(rn[v]); }
        tris += rp.length / 9;
      }
      g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
      g.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(nor), 3));
    }
    DRAPE_STATS.ms += performance.now() - t0; DRAPE_STATS.polys++; DRAPE_STATS.tris += tris;
    return g;
  }

  function offsetPolyline(pts, d) {
    const out = [];
    for (let i = 0; i < pts.length; i++) {
      const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[Math.min(pts.length - 1, i + 1)];
      const dx = p2[0] - p0[0], dz = p2[1] - p0[1];
      const L = Math.hypot(dx, dz) || 1;
      out.push([p1[0] - (dz / L) * d, p1[1] + (dx / L) * d]);
    }
    return out;
  }

  function flatPoly(poly, holes, y, noTerrain) {
    const g = new THREE.ShapeGeometry(shapeFromPoly(poly, holes));
    g.rotateX(-Math.PI / 2);
    g.translate(0, y, 0);
    if (!noTerrain) {
      const pa = g.attributes.position;
      for (let i = 0; i < pa.count; i++) pa.setY(i, pa.getY(i) + siteY(pa.getX(i), pa.getZ(i), 'ground'));
    }
    return g;
  }

  // ---------------------------------------------------------------- lighting & sky
  const hemi = new THREE.HemisphereLight(0xd3deea, 0x8f8166, 0.55);
  scene.add(hemi);
  const sunDir = new V3(-0.62, 0.5, 0.27).normalize(); // replaced each frame by the solar clock
  const sunWUniform = { value: sunDir };   // the facade shader reads the same vector for its reveals
  let lastAim = { cx: -120, cz: 0, extent: 640 };
  const sun = new THREE.DirectionalLight(COLORS.sun, 1.58);
  sun.castShadow = true;
  const SHADOW_RES = window.matchMedia('(pointer: coarse)').matches ? 2048 : 4096;
  sun.shadow.mapSize.set(SHADOW_RES, SHADOW_RES);
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 1.4;
  sun.shadow.camera.near = 100;
  sun.shadow.camera.far = 2600;
  scene.add(sun);
  scene.add(sun.target);

  const shadowAim = { cx: NaN, cz: NaN, extent: NaN, sun: new V3() };   // what the shadow map was last drawn for
  function aimSun(cx, cz, extent) {
    lastAim.cx = cx; lastAim.cz = cz; lastAim.extent = extent;
    const c = sun.shadow.camera;
    const texel = (extent * 2) / SHADOW_RES;
    cx = Math.round(cx / (texel * 8)) * texel * 8;
    cz = Math.round(cz / (texel * 8)) * texel * 8;
    // called every frame from applyLighting: only a moved box or a moved sun
    // costs a projection update and a shadow-map redraw
    if (cx === shadowAim.cx && cz === shadowAim.cz && extent === shadowAim.extent && shadowAim.sun.distanceToSquared(sunDir) < 1e-10) return;
    shadowAim.cx = cx; shadowAim.cz = cz; shadowAim.extent = extent; shadowAim.sun.copy(sunDir);
    sun.position.set(cx + sunDir.x * 1200, sunDir.y * 1200, cz + sunDir.z * 1200);
    sun.target.position.set(cx, 0, cz);
    c.left = -extent; c.right = extent; c.top = extent; c.bottom = -extent;
    c.updateProjectionMatrix();
    renderer.shadowMap.needsUpdate = true;
  }
  aimSun(-1450, -700, 800);

  // live-weather state (see applyWx below): cloud fraction, WMO code, rates, world wind m/s
  const WX = { cover: 0.22, ok: false, code: -1, temp: null, precip: 0, snowfall: 0, windX: 2.1, windZ: 0.9,
    tsObs: false, tsWarn: false, tsWatch: false, nwsT: 0, nwsText: '', nwsCover: 0 };   // NWS: thunder observed at an airport, a severe-storm warning, a watch
  const wxWind = new THREE.Vector2(0.0012, 0.0005);
  // per-fragment hash noise added to the sky before it is written: +/-0.5/255
  // breaks the 8-bit banding of the shallow dusk/night gradient (0 disables)
  const SKY_DITHER = 1 / 255;
  const skyMat = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
    uniforms: {
      cZenith: { value: new THREE.Color(COLORS.skyZenith) },
      cHorizon: { value: new THREE.Color(COLORS.skyHorizon) },
      cGround: { value: new THREE.Color(COLORS.skyGround) },
      uSun: { value: sunDir.clone() },
      cSun: { value: new THREE.Color(COLORS.sun) },
      uSunVis: { value: 1 },   // the disc and halo set with the horizon (the world is flat and ends; the real one curves)
      uCloud: { value: 0.22 },
      uCloudLight: { value: 1.0 },
      uCloudOff: { value: new THREE.Vector2(0, 0) },
      uMoon: { value: new THREE.Vector3(0, -1, 0) },
      uMoonU: { value: new THREE.Vector3(1, 0, 0) },
      uMoonV: { value: new THREE.Vector3(0, 0, 1) },
      uMoonK: { value: 0.5 },
      uMoonI: { value: 0 },
      uPost: postU.uPost,
      uExposure: postU.uExposure,
    },
    vertexShader:
      'varying vec3 vDir;\n' +
      'void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); gl_Position.z = gl_Position.w; }',
    fragmentShader:
      'varying vec3 vDir; uniform vec3 cZenith, cHorizon, cGround, uSun, cSun; uniform float uSunVis;\n' +
      'uniform float uCloud, uCloudLight; uniform vec2 uCloudOff;\n' +
      'uniform vec3 uMoon, uMoonU, uMoonV; uniform float uMoonK, uMoonI; uniform float uPost, uExposure;\n' +
      INV_GLSL + '\n' +
      'float chash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }\n' +
      'float cnoise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);\n' +
      '  return mix(mix(chash(i), chash(i+vec2(1.,0.)), f.x), mix(chash(i+vec2(0.,1.)), chash(i+vec2(1.,1.)), f.x), f.y); }\n' +
      'void main(){\n' +
      // normalize per fragment: the dome is coarse (32x18) and interpolated vDir
      // shrinks inside triangles, which smeared the old pow-based glow into a
      // vertical streak along the sun meridian. A round disc + radial halo on the
      // true angle reads like the actual sun.
      '  vec3 nd = normalize(vDir);\n' +
      '  float h = nd.y;\n' +
      '  vec3 col = h >= 0.0 ? mix(cHorizon, cZenith, pow(h, 0.6)) : mix(cHorizon, cGround, clamp(-h*1.5,0.,1.));\n' +
      '  float s = clamp(dot(nd, uSun), 0.0, 1.0);\n' +
      '  float sunAng = acos(s);\n' +
      '  float disc = 1.0 - smoothstep(0.0085, 0.0118, sunAng);\n' +
      '  col += cSun * ((disc * 1.7 + exp(-sunAng * sunAng * 95.0) * 0.24 + exp(-sunAng * sunAng * 9.0) * 0.07) * uSunVis + pow(s, 12.0) * 0.10 * (0.35 + 0.65 * uSunVis));\n' +
      // the Moon: a phased disc on the per-fragment normalized direction (nd,
      // never vDir — the coarse dome smears interpolated math, the sun lesson).
      // The terminator ellipse comes straight from the illuminated fraction; its
      // orientation from the world-space sun and moon vectors via uMoonU.
      '  if (uMoonI > 0.002) {\n' +
      '    float mAng = acos(clamp(dot(nd, uMoon), -1.0, 1.0));\n' +
      '    if (mAng < 0.06) {\n' +
      '      float mu = dot(nd, uMoonU) / 0.0091;\n' +
      '      float mv = dot(nd, uMoonV) / 0.0091;\n' +
      '      float mr = sqrt(mu * mu + mv * mv);\n' +
      '      float inD = 1.0 - smoothstep(0.93, 1.06, mr);\n' +
      '      float lim = sqrt(max(0.0, 1.0 - mv * mv));\n' +
      '      float ut = -(2.0 * uMoonK - 1.0) * lim;\n' +
      '      float lit = smoothstep(ut - 0.12, ut + 0.12, mu);\n' +
      '      vec3 mc = vec3(0.93, 0.94, 0.90);\n' +
      '      col = mix(col, mc * (0.11 + 0.89 * lit), inD * uMoonI);\n' +
      '    }\n' +
      '    col += vec3(0.93, 0.94, 0.90) * exp(-mAng * mAng * 2600.0) * 0.10 * uMoonI * uMoonK;\n' +
      '  }\n' +
      // cumulus: a four-octave fbm on the sky plane, its cover from the weather; a second
      // sample toward the sun lights the tops and leaves the bases in shade, the thick
      // cores a shade darker, the whole field fading into the horizon haze
      '  if (h > 0.01 && uCloud > 0.003) {\n' +
      '    vec2 cp = nd.xz / (h + 0.12) * 1.35 + uCloudOff;\n' +
      '    float f = 0.5 * cnoise(cp) + 0.25 * cnoise(cp * 2.1 + 13.1) + 0.125 * cnoise(cp * 4.3 + 41.7) + 0.0625 * cnoise(cp * 8.9 + 7.7);\n' +
      '    float cov = clamp(uCloud, 0.0, 1.0);\n' +
      '    float thr = 0.60 - cov * 0.40;\n' +
      '    float m = smoothstep(thr, thr + 0.14, f);\n' +
      '    vec2 sd = normalize(uSun.xz + vec2(1e-4, 0.0)) * 0.045;\n' +
      '    float f2 = 0.5 * cnoise(cp + sd) + 0.25 * cnoise((cp + sd) * 2.1 + 13.1) + 0.125 * cnoise((cp + sd) * 4.3 + 41.7);\n' +
      '    float lit = clamp((f2 - f) * 7.0 + 0.55, 0.0, 1.0) * clamp(uSun.y * 3.0, 0.0, 1.0);\n' +
      '    float dens = smoothstep(thr, thr + 0.34, f);\n' +
      '    vec3 cc = mix(vec3(0.60, 0.65, 0.72), vec3(0.985, 0.99, 1.0), lit) * uCloudLight;\n' +
      '    cc = mix(cc, vec3(0.74, 0.77, 0.82) * uCloudLight, dens * (0.35 + 0.4 * cov));\n' +
      // the deck overhead is the cloud plane's (see cloudDeck); the dome keeps the far band
      '    float horiz = smoothstep(0.02, 0.16, h) * (1.0 - smoothstep(0.08, 0.26, h));\n' +
      '    col = mix(col, cc, m * horiz * (0.86 + 0.1 * cov));\n' +
      '  }\n' +
      // under the post pipeline the dome hands the composite the exact pre-image of its raw
      // colour, plus an HDR sun disc that only the bloom can see
      // (alpha is the bloom mask under the post pipeline: the dome's pre-image is HDR-bright
      // but must not glow, so only the sun disc carries alpha)
      '  float skyA = 1.0;\n' +
      '  if (uPost > 0.5) { col = pUndo(col, uExposure) + cSun * disc * 3.0 * uSunVis; skyA = disc * uSunVis; }\n' +
      '  col += (fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453) - 0.5) * ' + SKY_DITHER.toFixed(7) + ';\n' +
      '  gl_FragColor = vec4(col, skyA);\n' +
      '}',
  });
  const sky = new THREE.Mesh(new THREE.SphereGeometry(5200, 32, 18), skyMat);
  sky.frustumCulled = false;
  scene.add(sky);

  // the cloud deck: cumulus with real perspective. A plane above the flight ceiling carries the
  // same fbm field the ground shadows use (so every cloud's shadow lies under it, slanted by
  // the sun), lit by a second sample toward the sun: bright rims where the puff thins toward
  // the light, grey bellies where it is thick, the whole deck warmed by the sun's colour and
  // dimmed by the sky's cloud light (night, overcast, storm gloom). The dome's own cumulus is
  // kept to the horizon band, where the deck has hazed out
  const CLOUD_ALT = 1900;
  const cloudMat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, side: THREE.DoubleSide, fog: true,
    uniforms: Object.assign(THREE.UniformsUtils.clone(THREE.UniformsLib.fog), {
      uCloud: skyMat.uniforms.uCloud, uCloudLight: skyMat.uniforms.uCloudLight, uCloudOff: skyMat.uniforms.uCloudOff,
      uSun: skyMat.uniforms.uSun, cSun: skyMat.uniforms.cSun, uPost: postU.uPost, uExposure: postU.uExposure,
    }),
    vertexShader: [
      'varying vec3 vW;',
      '#include <common>', '#include <fog_pars_vertex>', '#include <logdepthbuf_pars_vertex>',
      'void main(){ vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; vec4 mvPosition = viewMatrix * w; gl_Position = projectionMatrix * mvPosition;',
      '#include <logdepthbuf_vertex>', '#include <fog_vertex>', '}',
    ].join('\n'),
    fragmentShader: [
      'uniform float uCloud, uCloudLight, uPost, uExposure; uniform vec2 uCloudOff; uniform vec3 uSun, cSun; varying vec3 vW;',
      '#include <common>', '#include <fog_pars_fragment>', '#include <logdepthbuf_pars_fragment>',
      INV_GLSL,
      'float cdh(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }',
      'float cdn(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f); return mix(mix(cdh(i), cdh(i + vec2(1.0, 0.0)), f.x), mix(cdh(i + vec2(0.0, 1.0)), cdh(i + vec2(1.0, 1.0)), f.x), f.y); }',
      'float cfbm(vec2 p){ return 0.5 * cdn(p) + 0.25 * cdn(p * 2.1 + 13.1) + 0.125 * cdn(p * 4.3 + 41.7) + 0.0625 * cdn(p * 8.9 + 7.7)' + (isTouch ? '' : ' + 0.03 * cdn(p * 17.3 + 3.1)') + '; }',
      'void main(){',
      '  #include <logdepthbuf_fragment>',
      '  vec2 cp = vW.xz * 0.0008 + uCloudOff * 0.8;',
      '  float f = cfbm(cp);',
      '  float cov = clamp(uCloud, 0.0, 1.0); float thr = 0.60 - cov * 0.40;',
      '  float m = smoothstep(thr, thr + 0.20, f);',
      '  if (m < 0.004) discard;',
      '  float dens = smoothstep(thr, thr + 0.40, f);',
      '  float sunUp = clamp(uSun.y * 3.0, 0.0, 1.0);',
      '  vec2 sd = normalize(uSun.xz + vec2(1e-4, 0.0)) * (0.02 + 0.03 * (1.0 - clamp(uSun.y, 0.0, 1.0)));',
      '  float f2 = cfbm(cp + sd);',
      '  float lit = clamp((f2 - f) * 6.0 + 0.5, 0.0, 1.0);',
      '  float below = smoothstep(-80.0, 80.0, ' + CLOUD_ALT.toFixed(1) + ' - cameraPosition.y);',
      '  vec3 base = mix(vec3(0.66, 0.70, 0.78), vec3(0.40, 0.43, 0.50), dens * 0.95);',
      '  vec3 under = mix(base, vec3(1.0, 0.99, 0.96), (1.0 - dens) * (0.35 + 0.45 * lit) * sunUp);',
      '  vec3 top = mix(vec3(0.78, 0.81, 0.87), vec3(1.0, 1.0, 0.99), lit * sunUp);',
      '  vec3 col = mix(top, under, below) * uCloudLight * mix(vec3(1.0), cSun, 0.35);',
      '  float a = m * 0.94 * (1.0 - smoothstep(14000.0, 26000.0, length(vW.xz - cameraPosition.xz)));',
      '  gl_FragColor = vec4(col, a);',
      // the pre-image first, then the fog (whose colour is the pre-image too under the post pipeline);
      // the coverage stays the bloom mask as it is, a halved alpha halved the colour blend as well
      '  if (uPost > 0.5) gl_FragColor.rgb = pUndo(gl_FragColor.rgb, uExposure) + vec3(0.15) * (1.0 - dens) * lit * sunUp * uCloudLight;',
      '  #include <fog_fragment>',
      '}',
    ].join('\n'),
  });
  const cloudDeck = new THREE.Mesh(new THREE.PlaneGeometry(64000, 64000, 1, 1), cloudMat);
  cloudDeck.rotation.x = -Math.PI / 2; cloudDeck.position.y = CLOUD_ALT;
  cloudDeck.frustumCulled = false; cloudDeck.renderOrder = -5;
  scene.add(cloudDeck);

  // environment map for glass: sky gradient + sun glare + dark ground and
  // building silhouettes so reflections have structure; refreshed as the sun moves
  const envScene = new THREE.Scene();
  const envSky = new THREE.Mesh(new THREE.SphereGeometry(50, 16, 10), skyMat.clone());
  envSky.material.uniforms.uPost = { value: 0 };   // the environment map wants the raw dome, never the pre-image
  envScene.add(envSky);
  const envGround = new THREE.Mesh(new THREE.CircleGeometry(45, 16), new THREE.MeshBasicMaterial({ color: COLORS.skyGround }));
  envGround.rotation.x = -Math.PI / 2; envGround.position.y = -4;
  envScene.add(envGround);
  const envSun = new THREE.Mesh(new THREE.SphereGeometry(3.5, 10, 8), new THREE.MeshBasicMaterial({ color: 0xfff2d8 }));
  envScene.add(envSun);
  {
    const bm = new THREE.MeshBasicMaterial({ color: 0x23262c });
    for (let k = 0; k < 9; k++) {
      const ang = k * 0.7 + 0.3;
      const bx = new THREE.Mesh(new THREE.BoxGeometry(4 + (k % 3) * 3, 6 + (k * 7) % 18, 4), bm);
      bx.position.set(Math.cos(ang) * 28, bx.geometry.parameters.height / 2 - 4, Math.sin(ang) * 28);
      envScene.add(bx);
    }
  }
  const pmremGen = new THREE.PMREMGenerator(renderer);
  let envRT = null;
  function refreshEnv() {
    for (const k of ['cZenith', 'cHorizon', 'cGround', 'cSun']) envSky.material.uniforms[k].value.copy(skyMat.uniforms[k].value);
    envSky.material.uniforms.uSunVis.value = skyMat.uniforms.uSunVis.value;
    envSky.material.uniforms.uSun.value.copy(skyMat.uniforms.uSun.value);
    envSky.material.uniforms.uCloud.value = skyMat.uniforms.uCloud.value;
    envSky.material.uniforms.uCloudLight.value = skyMat.uniforms.uCloudLight.value;
    envSky.material.uniforms.uCloudOff.value.copy(skyMat.uniforms.uCloudOff.value);
    // the env sun ball must dim with cloud cover or overcast glass keeps a clear-sky hotspot
    envSun.material.color.set(0xfff2d8).multiplyScalar(1 - 0.65 * WX.cover);
    envGround.material.color.copy(skyMat.uniforms.cGround.value);
    envSun.position.copy(skyMat.uniforms.uSun.value).multiplyScalar(44);
    const rt = pmremGen.fromScene(envScene, 0.05);
    scene.environment = rt.texture;
    if (envRT) envRT.dispose();
    envRT = rt;
  }
  refreshEnv();

  // ---------------------------------------------------------------- data-driven build
  const D = SCENE_DATA;
  const META_L = (META && META.landmarks && META.landmarks.landmarks) || (META && META.landmarks) || [];
  const towers = D.towers || [];
  const towersCenter = new V3(0, 0, 0);
  if (towers.length) {
    const cs = new V3();
    for (const t of towers) cs.add(new V3(t.centroid[0], 0, t.centroid[1]));
    towersCenter.copy(cs.multiplyScalar(1 / towers.length));
  }

  const bounds = { minX: 1e9, maxX: -1e9, minZ: 1e9, maxZ: -1e9 };
  // the flight limit: Philadelphia's city line buffered 2 km (fetch_boundary.py ->
  // city_limit.json), clipped to the far-ring box. The camera stays inside it in every
  // mode, shared links land inside it, and SEPTA vehicles beyond it are off the map:
  // the towns across the line are scenery seen from the edge, never flown over
  const LIMIT = (typeof CITY_LIMIT !== 'undefined' && CITY_LIMIT && CITY_LIMIT.bound && CITY_LIMIT.bound.length > 3) ? CITY_LIMIT.bound : null;
  const limitIn = LIMIT && signedArea(LIMIT) > 0 ? 1 : -1;   // which side of an edge is inside
  function insideLimit(x, z) { return !LIMIT || pointInPoly(x, z, LIMIT); }
  // null when (x, z) is inside; otherwise the nearest point on the ring, 3 m in
  function clampLimit(x, z) {
    if (insideLimit(x, z)) return null;
    let best = Infinity, bx = x, bz = z, nx = 0, nz = 0;
    for (let i = 0, n = LIMIT.length; i < n; i++) {
      const a = LIMIT[i], b = LIMIT[(i + 1) % n];
      const dx = b[0] - a[0], dz = b[1] - a[1], L2 = dx * dx + dz * dz || 1e-9;
      const t = clamp(((x - a[0]) * dx + (z - a[1]) * dz) / L2, 0, 1);
      const px = a[0] + dx * t, pz = a[1] + dz * t;
      const d2 = (px - x) * (px - x) + (pz - z) * (pz - z);
      if (d2 < best) { best = d2; bx = px; bz = pz; const L = Math.sqrt(L2); nx = -dz / L * limitIn; nz = dx / L * limitIn; }
    }
    return [bx + nx * 3, bz + nz * 3];
  }
  const limitV = (v) => { const c = clampLimit(v.x, v.z); if (c) { v.x = c[0]; v.z = c[1]; } return v; };
  for (const b of D.buildings) for (const p of b.poly) {
    if (p[0] < bounds.minX) bounds.minX = p[0];
    if (p[0] > bounds.maxX) bounds.maxX = p[0];
    if (p[1] < bounds.minZ) bounds.minZ = p[1];
    if (p[1] > bounds.maxZ) bounds.maxZ = p[1];
  }

  // waterfront: the Delaware's edge runs diagonally here. Fit a line along
  // Columbus Blvd; water lies ~90m east (normal side) of it.
  const wl = { px: 380, pz: 0, dx: 0, dz: 1, nx: 1, nz: 0, off: 92 };
  {
    const pts = [];
    for (const r of D.roads) if (r.name && /columbus/i.test(r.name)) for (const p of r.pts) pts.push(p);
    if (pts.length > 3) {
      let mx = 0, mz = 0;
      for (const p of pts) { mx += p[0]; mz += p[1]; }
      mx /= pts.length; mz /= pts.length;
      let sxx = 0, sxz = 0, szz = 0;
      for (const p of pts) { const ax = p[0] - mx, az = p[1] - mz; sxx += ax * ax; sxz += ax * az; szz += az * az; }
      const ang = 0.5 * Math.atan2(2 * sxz, sxx - szz);
      wl.px = mx; wl.pz = mz;
      wl.dx = Math.cos(ang); wl.dz = Math.sin(ang);
      if (wl.dz < 0) { wl.dx = -wl.dx; wl.dz = -wl.dz; } // along-shore direction runs south
      wl.nx = -wl.dz; wl.nz = wl.dx;
      if (wl.nx < 0) { wl.nx = -wl.nx; wl.nz = -wl.nz; }
    }
  }
  // signed distance east of the waterline; > 0 means in the river
  function inWater(x, z) { return x - xShore(z); }
  // rough Delaware west-bank polyline for the whole city (meets SHORE at the core ends):
  // east of it low terrain is river (dives to the bed); west of it low terrain is
  // made-land and clamps just above the water plane instead of flooding
  const DEL_BANK = [[13500, -21700], [10500, -18500], [7300, -14500], [4300, -10500], [2500, -7200], [1500, -4480], [900, -2600], [450, -1500], [404, -520], [345, 850], [700, 2200], [1300, 3600], [2000, 4800], [2600, 6400], [3400, 7600], [5200, 9700]];
  function delawareX(z) {
    for (let i = 0; i < DEL_BANK.length - 1; i++) {
      const a = DEL_BANK[i], b = DEL_BANK[i + 1];
      if (z >= a[1] && z <= b[1]) { const t = (z - a[1]) / Math.max(1e-6, b[1] - a[1]); return a[0] + (b[0] - a[0]) * t; }
    }
    return z < DEL_BANK[0][1] ? DEL_BANK[0][0] : DEL_BANK[DEL_BANK.length - 1][0];
  }
  // the state line runs mid-Delaware: the city ring's easternmost crossing at this z
  // (city_limit.json), from the Poquessing mouth (the ring's easternmost point; above
  // it the east edge is the Bucks County line, not the river) down to Fort Mifflin;
  // null outside that band
  const CITY_RING = (typeof CITY_LIMIT !== 'undefined' && CITY_LIMIT && CITY_LIMIT.city && CITY_LIMIT.city.length > 3) ? CITY_LIMIT.city : null;
  const RING_MOUTH_Z = CITY_RING ? CITY_RING.reduce((m, q) => (q[0] > m[0] ? q : m))[1] : 0;
  const stateLineCache = new Map();
  function stateLineX(z) {
    if (!CITY_RING || z < RING_MOUTH_Z) return null;
    const key = Math.round(z / 10);
    let v = stateLineCache.get(key);
    if (v !== undefined) return v;
    v = null;
    for (let i = 0, n = CITY_RING.length; i < n; i++) {
      const a = CITY_RING[i], b = CITY_RING[(i + 1) % n];
      if ((a[1] > z) === (b[1] > z)) continue;
      const x = a[0] + (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]);
      if (v === null || x > v) v = x;
    }
    stateLineCache.set(key, v);
    return v;
  }
  // Jersey ground: more than 400 m past the state line. The rough west-bank polyline
  // drifts into Gloucester City south of the stadiums, and every low cell east of it
  // used to dive to the riverbed, so Camden's and Gloucester City's filled riverfront
  // read as open water and their low blocks were dropped as floating. Land past the
  // line now clamps to made-land the way the Philadelphia side does
  function njLand(x, z) { const sx = stateLineX(z); return sx !== null && x > sx + 400; }
  function eastOfDelaware(x, z) { return x > delawareX(z) - 120 && !njLand(x, z); }
  // rough Schuylkill centerline; within 260 m counts as its corridor (bridge territory)
  // bridge to bridge from the model's edge above Flat Rock Dam to the mouth at League Island:
  // Manayunk, East Falls, the Falls Bridge, Strawberry Mansion, Columbia, Girard, Boathouse
  // Row, the Fairmount Dam, Spring Garden, Market, University Avenue, Grays Ferry, Passyunk,
  // the refinery bend (the old trace ran a kilometre west of the river north of Center City)
  const SCHUYLKILL = [[-9150, -11780], [-8001, -10507], [-6593, -8904], [-5739, -8572], [-4502, -8074], [-3904, -7422], [-4160, -6217], [-4160, -5310], [-3947, -4425], [-3520, -3441], [-3734, -2844], [-3478, -2324], [-3220, -1775], [-3264, -1000], [-3650, 0], [-4545, 935], [-5055, 2264], [-4800, 3480], [-5015, 4585], [-4716, 5580], [-4118, 6686], [-3690, 7355]];
  // the river's real course (bake_schuylkill.py, OSM waterway=river ways): every fragment,
  // side channels included; the hand polyline above is the fallback when the bake is absent
  const SCHUYLKILL_LINES = (typeof SCHUYLKILL_DATA !== 'undefined' && SCHUYLKILL_DATA && SCHUYLKILL_DATA.lines && SCHUYLKILL_DATA.lines.length) ? SCHUYLKILL_DATA.lines : [SCHUYLKILL];
  function nearSchuylkill(x, z) {
    for (const LN of SCHUYLKILL_LINES) for (let i = 0; i < LN.length - 1; i++) {
      const a = LN[i], b = LN[i + 1];
      const dx = b[0] - a[0], dz = b[1] - a[1];
      const L2 = dx * dx + dz * dz;
      let t = L2 > 0 ? ((x - a[0]) * dx + (z - a[1]) * dz) / L2 : 0;
      t = clamp(t, 0, 1);
      const px = x - (a[0] + dx * t), pz = z - (a[1] + dz * t);
      if (px * px + pz * pz < 260 * 260) return true;
    }
    return false;
  }
  function riverCorridor(x, z) { return eastOfDelaware(x, z) || (schRaster ? schRaster(x, z) : nearSchuylkill(x, z)); }
  // the Schuylkill channel above the Fairmount Dam, 1 within 60 m of the centerline fading to
  // 0 at 95 m: the ground builders carve it to the riverbed. Above the dam the pool sits a
  // couple of metres over the tidal water plane and the 50 and 100 m elevation grids smear
  // the banks across the river, so the flat water drawn at tidal level was buried from the
  // dam to the NW hills patch (which drapes its own full-fidelity rings and is left alone)
  // The river's outline (bake_schuylkill.py, OSM natural=water): inside it the ground goes to
  // the bed, and within 40 m outside a high bank ramps down to just above the water, so the
  // shoreline is the outline itself. Before this the carve followed the centreline at a fixed
  // radius while the sheet followed the outline, and wherever the two disagreed the 25 m
  // ground grid surfaced through the water as a staircase. Inside/outside comes from a 10 m
  // scanline raster of the polygon (rows against edges once, at start), the distance and the
  // side near the edge from a 20 m grid of the edges themselves.
  const SCH_POLYS = (typeof SCHUYLKILL_DATA !== 'undefined' && SCHUYLKILL_DATA && SCHUYLKILL_DATA.polys && SCHUYLKILL_DATA.polys.length) ? SCHUYLKILL_DATA.polys : null;
  let schRaster = null, schEdges = null;
  if (SCH_POLYS) {
    const RC = 10, EC = 20;
    let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
    const rings = [];
    for (const pg of SCH_POLYS) { rings.push(pg.ring); for (const h of (pg.holes || [])) rings.push(h); for (const q of pg.ring) { if (q[0] < x0) x0 = q[0]; if (q[0] > x1) x1 = q[0]; if (q[1] < z0) z0 = q[1]; if (q[1] > z1) z1 = q[1]; } }
    const gx0 = Math.floor(x0 / RC) - 1, gz0 = Math.floor(z0 / RC) - 1, nx = Math.ceil(x1 / RC) - gx0 + 2, nz = Math.ceil(z1 / RC) - gz0 + 2;
    const mask = new Uint8Array(nx * nz);
    const xs = [];
    for (let j = 0; j < nz; j++) {   // even-odd fill of every raster row against every edge (holes included)
      const zc = (gz0 + j + 0.5) * RC;
      xs.length = 0;
      for (const r of rings) for (let k = 0, n = r.length; k < n; k++) {
        const a = r[k], b = r[(k + 1) % n];
        if ((a[1] <= zc) !== (b[1] <= zc)) xs.push(a[0] + (zc - a[1]) / (b[1] - a[1]) * (b[0] - a[0]));
      }
      xs.sort((u, v) => u - v);
      for (let m = 0; m + 1 < xs.length; m += 2) {
        const i0 = Math.max(0, Math.ceil(xs[m] / RC - 0.5) - gx0), i1 = Math.min(nx - 1, Math.floor(xs[m + 1] / RC - 0.5) - gx0);
        for (let ii = i0; ii <= i1; ii++) mask[j * nx + ii] = 1;
      }
    }
    schRaster = (x, z) => { const ii = Math.floor(x / RC) - gx0, jj = Math.floor(z / RC) - gz0; return ii >= 0 && jj >= 0 && ii < nx && jj < nz && mask[jj * nx + ii] === 1; };
    const egrid = new Map(), segs = [];
    for (const r of rings) {
      const n = r.length; let ar = 0; for (let k = 0; k < n; k++) ar += r[k][0] * r[(k + 1) % n][1] - r[(k + 1) % n][0] * r[k][1];
      const sgn = ar > 0 ? 1 : -1;   // so the edge normal below points to the ring's outside
      for (let k = 0; k < n; k++) {
        const a = r[k], b = r[(k + 1) % n], dx = b[0] - a[0], dz = b[1] - a[1], L = Math.hypot(dx, dz);
        if (L < 0.05) continue;
        const sid = segs.length; segs.push([a[0], a[1], dx / L, dz / L, L, (dz / L) * sgn, (-dx / L) * sgn]);
        for (let gx = Math.floor(Math.min(a[0], b[0]) / EC); gx <= Math.floor(Math.max(a[0], b[0]) / EC); gx++)
          for (let gz = Math.floor(Math.min(a[1], b[1]) / EC); gz <= Math.floor(Math.max(a[1], b[1]) / EC); gz++) { const key = gx + ':' + gz; let l = egrid.get(key); if (!l) { l = []; egrid.set(key, l); } l.push(sid); }
      }
    }
    // [distance to the nearest edge within 40 m (else 40), +1 outside / -1 inside by that edge]
    schEdges = (x, z) => {
      let best = 1600, side = 0;
      const gx = Math.floor(x / EC), gz = Math.floor(z / EC);
      for (let a = -2; a <= 2; a++) for (let b2 = -2; b2 <= 2; b2++) {
        const l = egrid.get((gx + a) + ':' + (gz + b2)); if (!l) continue;
        for (const sid of l) {
          const sg = segs[sid];
          const t = clamp(((x - sg[0]) * sg[2] + (z - sg[1]) * sg[3]), 0, sg[4]);
          const px = x - (sg[0] + sg[2] * t), pz = z - (sg[1] + sg[3] * t), d2 = px * px + pz * pz;
          if (d2 < best) { best = d2; side = (px * sg[5] + pz * sg[6]) >= 0 ? 1 : -1; }
        }
      }
      return [Math.sqrt(best), side];
    };
  }
  // the ground height under and beside the river: yy is the builder's height so far
  function riverCarve(x, z, yy) {
    if (!schRaster) { const kc = schuylkillCut(x, z); return kc > 0 ? Math.min(yy, yy + (TERRAIN.bed - 0.6 - yy) * kc) : yy; }
    const e = schEdges(x, z);
    const inside = e[0] < 8 ? e[1] < 0 : schRaster(x, z);
    if (inside) return Math.min(yy, TERRAIN.bed - 0.6);
    if (e[0] < 40) return Math.min(yy, TERRAIN.water + 0.9 + (yy - TERRAIN.water - 0.9) * smooth(0, 40, e[0]));
    return yy;
  }
  function schuylkillCut(x, z) {
    if (z > -2250 || z < -6600) return 0;
    let best = Infinity;
    for (const LN of SCHUYLKILL_LINES) for (let i = 0; i < LN.length - 1; i++) {
      const a = LN[i], b = LN[i + 1];
      if (b[1] > -2000 || a[1] < -7000) continue;
      const dx = b[0] - a[0], dz = b[1] - a[1];
      const L2 = dx * dx + dz * dz;
      const t = clamp(L2 > 0 ? ((x - a[0]) * dx + (z - a[1]) * dz) / L2 : 0, 0, 1);
      const px = x - (a[0] + dx * t), pz = z - (a[1] + dz * t);
      const d2 = px * px + pz * pz;
      if (d2 < best) best = d2;
    }
    return 1 - smooth(60, 95, Math.sqrt(best));
  }
  // Walt Whitman crossing corridor: the custom suspension deck owns this stretch of
  // water — packed motorway segments here rendered as a second, disjointed bridge.
  // Distance to the raw OSM alignment (only ever consulted for deck-lifted river
  // segments, so the on-land approaches keep their real ramps).
  function wwbNear(x, z, r) {
    if (typeof WWB_PTS === 'undefined' || !WWB_PTS || WWB_PTS.length < 4) return false;
    r = r || 85;
    let best = Infinity;
    for (let i = 1; i < WWB_PTS.length; i++) {
      const A = WWB_PTS[i - 1], B = WWB_PTS[i];
      const dx = B[0] - A[0], dz = B[1] - A[1], L2 = dx * dx + dz * dz || 1e-9;
      const tt = clamp(((x - A[0]) * dx + (z - A[1]) * dz) / L2, 0, 1);
      const ex = A[0] + dx * tt - x, ez = A[1] + dz * tt - z;
      const d2 = ex * ex + ez * ez;
      if (d2 < best) best = d2;
    }
    return best < r * r;
  }

  // under the Jersey viaduct: within 30 m of the alignment east of the river bank and
  // short of its landing. The packed I-76 (both carriageways and the ramp ends that
  // merge into it) would otherwise pave a flat twin of the deck through Gloucester City
  function wwbUnder(x, z) {
    if (x < 1750 || typeof WWB_PTS === 'undefined' || !WWB_PTS || WWB_PTS.length < 4) return false;
    let best = Infinity, atEnd = false;
    for (let i = 1; i < WWB_PTS.length; i++) {
      const A = WWB_PTS[i - 1], B = WWB_PTS[i];
      const dx = B[0] - A[0], dz = B[1] - A[1], L2 = dx * dx + dz * dz || 1e-9;
      const tt = clamp(((x - A[0]) * dx + (z - A[1]) * dz) / L2, 0, 1);
      const ex = A[0] + dx * tt - x, ez = A[1] + dz * tt - z;
      const d2 = ex * ex + ez * ez;
      if (d2 < best) { best = d2; atEnd = i === WWB_PTS.length - 1 && tt > 0.97; }
    }
    return best < 30 * 30 && !atEnd;
  }

  // ---------------------------------------------------------------- overpasses
  // Baked by bake_overpasses.py from the raw OSM bridge/viaduct/layer/tunnel tags
  // (the packed road formats carry none of them). el = elevated chains with a
  // solved height profile, sk = sunken expressway carriageways, cor = the open-cut
  // corridor runs of the Vine Street Expressway [[x, z, floorY, halfW], ...].
  const OVP = (typeof OVERPASSES !== 'undefined' && OVERPASSES) ? OVERPASSES : { el: [], sk: [], cor: [] };
  const ovpGrid = new Map();
  const OVP_CELL = 28;
  const ovpSegs = [];   // ax, az, bx, bz, ya, yb, hw, cls, chainId (stride 9; cls -1 open cut, -2 covered)
  const OVP_STRIDE = 9;
  {
    const add = (a, b, hw, cls, id) => {
      const idx = ovpSegs.length;
      ovpSegs.push(a[0], a[1], b[0], b[1], a[2], b[2], hw, cls, id);
      const minx = Math.floor((Math.min(a[0], b[0]) - hw) / OVP_CELL), maxx = Math.floor((Math.max(a[0], b[0]) + hw) / OVP_CELL);
      const minz = Math.floor((Math.min(a[1], b[1]) - hw) / OVP_CELL), maxz = Math.floor((Math.max(a[1], b[1]) + hw) / OVP_CELL);
      for (let gx = minx; gx <= maxx; gx++) for (let gz = minz; gz <= maxz; gz++) {
        const k = gx + ':' + gz;
        let arr = ovpGrid.get(k);
        if (!arr) { arr = []; ovpGrid.set(k, arr); }
        arr.push(idx);
      }
    };
    OVP.el.forEach((c, ci) => { for (let i = 0; i + 1 < c.p.length; i++) add(c.p[i], c.p[i + 1], c.w / 2, c.c, ci); });
    // sunken runs: -1 = open cut (digs holes, grows walls), -2 = covered tunnel
    // (suppresses the packed road but leaves the ground alone)
    OVP.sk.forEach((c, ci) => { for (let i = 0; i + 1 < c.p.length; i++) add(c.p[i], c.p[i + 1], c.w / 2 + 2, c.cov ? -2 : -1, 1000 + ci); });
  }
  // a packed road segment lying along a baked chain is the same OSM way: the
  // deck (or sunken roadway) build owns it, so the flat ribbon must not draw.
  // The radius is a FIXED 2.6 m: same-way centerlines coincide within the two
  // simplification tolerances, while parallel surface streets sit 8 m or more
  // away. (The old chainWidth/2 + 3 swept 11 m on motorways and ate the streets
  // running beside the embankments.)
  function ovpOwned(ax, az, bx, bz) {
    if (!ovpSegs.length) return false;
    let ux = bx - ax, uz = bz - az;
    const L = Math.hypot(ux, uz) || 1;
    ux /= L; uz /= L;
    const hit = (x, z) => {
      const arr = ovpGrid.get(Math.floor(x / OVP_CELL) + ':' + Math.floor(z / OVP_CELL));
      if (!arr) return false;
      for (const s of arr) {
        const sax = ovpSegs[s], saz = ovpSegs[s + 1], sbx = ovpSegs[s + 2], sbz = ovpSegs[s + 3];
        let dx = sbx - sax, dz = sbz - saz;
        const sl = Math.hypot(dx, dz) || 1;
        if (Math.abs((dx * ux + dz * uz) / sl) < 0.8) continue;
        let t = ((x - sax) * dx + (z - saz) * dz) / (sl * sl);
        t = clamp(t, 0, 1);
        const px = sax + dx * t - x, pz = saz + dz * t - z;
        if (px * px + pz * pz < 2.6 * 2.6) return true;
      }
      return false;
    };
    // both ENDPOINTS suffice: requiring the midpoint too let curved duplicates
    // escape where the simplified chain corner-cuts the arc (mid bulges ~5 m)
    return hit(ax, az) && hit(bx, bz);
  }
  // does a building footprint straddle a motorway deck or an open cut? (an OSM
  // artifact: nothing real stands across I-95 — Mike's building through the
  // viaduct). The audit proved centroid tests miss edge-on straddlers 5 times
  // out of 7, so every footprint EDGE is walked against the swath.
  function ovpCutHit(x, z) {
    const arr = ovpGrid.get(Math.floor(x / OVP_CELL) + ':' + Math.floor(z / OVP_CELL));
    if (!arr) return false;
    for (const s of arr) {
      const cls = ovpSegs[s + 7];
      if (!ovpCutClass(cls)) continue;              // motorway/trunk decks and open cuts only
      const sax = ovpSegs[s], saz = ovpSegs[s + 1], sbx = ovpSegs[s + 2], sbz = ovpSegs[s + 3], hw = ovpSegs[s + 6];
      const dx = sbx - sax, dz = sbz - saz;
      const L2 = dx * dx + dz * dz || 1e-9;
      let t = ((x - sax) * dx + (z - saz) * dz) / L2;
      t = clamp(t, 0, 1);
      const px = sax + dx * t - x, pz = saz + dz * t - z;
      const r = Math.max(2, hw - 1);
      if (px * px + pz * pz < r * r) return true;
    }
    return false;
  }
  // motorway/trunk decks (0, 1) and open cuts (-1) erase what stands across
  // them; covered tunnels (-2) and lesser decks leave the fabric alone. (The
  // old `cls > 1 && cls !== -1` test let -2 through and deleted rowhouses
  // over the covered stretches.)
  const ovpCutClass = (cls) => cls === -1 || (cls >= 0 && cls <= 1);
  // coarse occupancy bitmap over the cutting swaths: a footprint whose bbox
  // misses every marked cell needs no 3 m edge walk. 99.4% of the 293k packed
  // footprints are nowhere near a deck, and the walk cost them 9.3 M
  // string-keyed Map probes at load.
  const OVP_BIT = 32;
  let ovpBits = null, ovpBx0 = 0, ovpBz0 = 0, ovpBw = 0, ovpBh = 0;
  {
    let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
    for (let s = 0; s < ovpSegs.length; s += OVP_STRIDE) {
      if (!ovpCutClass(ovpSegs[s + 7])) continue;
      const hw = ovpSegs[s + 6] + 2;
      x0 = Math.min(x0, ovpSegs[s] - hw, ovpSegs[s + 2] - hw); x1 = Math.max(x1, ovpSegs[s] + hw, ovpSegs[s + 2] + hw);
      z0 = Math.min(z0, ovpSegs[s + 1] - hw, ovpSegs[s + 3] - hw); z1 = Math.max(z1, ovpSegs[s + 1] + hw, ovpSegs[s + 3] + hw);
    }
    if (x1 > x0) {
      ovpBx0 = x0; ovpBz0 = z0; ovpBw = Math.ceil((x1 - x0) / OVP_BIT) + 1; ovpBh = Math.ceil((z1 - z0) / OVP_BIT) + 1;
      ovpBits = new Uint8Array(ovpBw * ovpBh);
      for (let s = 0; s < ovpSegs.length; s += OVP_STRIDE) {
        if (!ovpCutClass(ovpSegs[s + 7])) continue;
        const hw = ovpSegs[s + 6] + 2;
        const c0 = Math.floor((Math.min(ovpSegs[s], ovpSegs[s + 2]) - hw - x0) / OVP_BIT), c1 = Math.floor((Math.max(ovpSegs[s], ovpSegs[s + 2]) + hw - x0) / OVP_BIT);
        const r0 = Math.floor((Math.min(ovpSegs[s + 1], ovpSegs[s + 3]) - hw - z0) / OVP_BIT), r1 = Math.floor((Math.max(ovpSegs[s + 1], ovpSegs[s + 3]) + hw - z0) / OVP_BIT);
        for (let r = r0; r <= r1; r++) for (let c = c0; c <= c1; c++) ovpBits[r * ovpBw + c] = 1;
      }
    }
  }
  function ovpNear(x0, x1, z0, z1) {
    if (!ovpBits) return false;
    const c0 = Math.max(0, Math.floor((x0 - ovpBx0) / OVP_BIT)), c1 = Math.min(ovpBw - 1, Math.floor((x1 - ovpBx0) / OVP_BIT));
    const r0 = Math.max(0, Math.floor((z0 - ovpBz0) / OVP_BIT)), r1 = Math.min(ovpBh - 1, Math.floor((z1 - ovpBz0) / OVP_BIT));
    for (let r = r0; r <= r1; r++) for (let c = c0; c <= c1; c++) if (ovpBits[r * ovpBw + c]) return true;
    return false;
  }
  function ovpStraddle(poly, cx, cz) {
    if (poly && ovpBits) {
      let x0 = cx, x1 = cx, z0 = cz, z1 = cz;
      for (let i = 0; i < poly.length; i++) { const q = poly[i]; if (q[0] < x0) x0 = q[0]; else if (q[0] > x1) x1 = q[0]; if (q[1] < z0) z0 = q[1]; else if (q[1] > z1) z1 = q[1]; }
      if (!ovpNear(x0, x1, z0, z1)) return vineCut(cx, cz, -1) !== null;
    }
    if (ovpCutHit(cx, cz)) return true;
    if (poly) {
      for (let i = 0; i < poly.length; i++) {
        const a = poly[i], b = poly[(i + 1) % poly.length];
        const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const k = Math.max(1, Math.ceil(L / 3));
        for (let j = 0; j <= k; j++) {
          const t = j / k;
          if (ovpCutHit(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)) return true;
        }
      }
    }
    return vineCut(cx, cz, -1) !== null;
  }
  // deck-top height at a point, aligned to a travel direction when one is given
  // (buses and street labels ride the deck; things merely passing beneath do not)
  function ovpDeckY(x, z, ux, uz) {
    const arr = ovpGrid.get(Math.floor(x / OVP_CELL) + ':' + Math.floor(z / OVP_CELL));
    if (!arr) return null;
    let best = null;
    for (const s of arr) {
      if (ovpSegs[s + 7] < 0) continue;            // sunken carriageways never lift
      const sax = ovpSegs[s], saz = ovpSegs[s + 1], sbx = ovpSegs[s + 2], sbz = ovpSegs[s + 3], hw = ovpSegs[s + 6];
      const dx = sbx - sax, dz = sbz - saz;
      const sl = Math.hypot(dx, dz) || 1;
      if (ux !== undefined && Math.abs((dx * ux + dz * uz) / sl) < 0.72) continue;
      let t = ((x - sax) * dx + (z - saz) * dz) / (sl * sl);
      t = clamp(t, 0, 1);
      const px = sax + dx * t - x, pz = saz + dz * t - z;
      if (px * px + pz * pz > (hw + 1.5) * (hw + 1.5)) continue;
      const y = ovpSegs[s + 4] + (ovpSegs[s + 5] - ovpSegs[s + 4]) * t;
      if (best === null || y > best) best = y;
    }
    return best;
  }
  // the Vine Street open cut: corridor membership + floor height (pad widens or,
  // negative, shrinks the tested corridor width)
  const vineBox = { x0: 1e9, x1: -1e9, z0: 1e9, z1: -1e9 };
  for (const run of OVP.cor) for (const p of run) {
    vineBox.x0 = Math.min(vineBox.x0, p[0] - p[3] - 4); vineBox.x1 = Math.max(vineBox.x1, p[0] + p[3] + 4);
    vineBox.z0 = Math.min(vineBox.z0, p[1] - p[3] - 4); vineBox.z1 = Math.max(vineBox.z1, p[1] + p[3] + 4);
  }
  function vineCut(x, z, pad) {
    if (x < vineBox.x0 || x > vineBox.x1 || z < vineBox.z0 || z > vineBox.z1) return null;
    pad = pad || 0;
    for (const run of OVP.cor) {
      for (let i = 0; i + 1 < run.length; i++) {
        const a = run[i], b = run[i + 1];
        const dx = b[0] - a[0], dz = b[1] - a[1];
        const L2 = dx * dx + dz * dz || 1e-9;
        let t = ((x - a[0]) * dx + (z - a[1]) * dz) / L2;
        t = clamp(t, 0, 1);
        const px = a[0] + dx * t - x, pz = a[1] + dz * t - z;
        const hw = a[3] + (b[3] - a[3]) * t + pad;
        if (px * px + pz * pz < hw * hw) return a[2] + (b[2] - a[2]) * t;
      }
    }
    return null;
  }
  // sunken RAMP approaches dive below grade outside the main corridor: the ground
  // must open over them too (they get their own narrow walled cuts)
  function sunkCutNear(x, z, pad) {
    const arr = ovpGrid.get(Math.floor(x / OVP_CELL) + ':' + Math.floor(z / OVP_CELL));
    if (!arr) return null;
    for (const s of arr) {
      if (ovpSegs[s + 7] !== -1) continue;
      const sax = ovpSegs[s], saz = ovpSegs[s + 1], sbx = ovpSegs[s + 2], sbz = ovpSegs[s + 3], hw = ovpSegs[s + 6];
      const dx = sbx - sax, dz = sbz - saz;
      const L2 = dx * dx + dz * dz || 1e-9;
      let t = ((x - sax) * dx + (z - saz) * dz) / L2;
      t = clamp(t, 0, 1);
      const px = sax + dx * t - x, pz = saz + dz * t - z;
      const r = hw + (pad || 0);
      if (px * px + pz * pz > r * r) continue;
      const y = ovpSegs[s + 4] + (ovpSegs[s + 5] - ovpSegs[s + 4]) * t;
      if (y < demY(x, z) - 1.2) return y;
    }
    return null;
  }
  function cutHole(x, z) {
    return vineCut(x, z, -1) !== null || sunkCutNear(x, z, 1) !== null;
  }

  // ---------------------------------------------------------------- living water
  // Every water material shares these uniforms; liquify() injects a moving sum of
  // directional gradient waves that tilts the shading normal (sun glitter, moving
  // sky reflections) plus a faint albedo shimmer so matte views from altitude read
  // too. No vertex displacement: shorelines and copings stay watertight. Amplitude
  // follows the live wind (applyWx); a distance fade keeps far water calm so the
  // ripple field never aliases into noise at the horizon.
  const waterU = { uTime: { value: 7.3 }, uWAmp: { value: 1.0 }, uWDir: { value: new THREE.Vector2(0.86, 0.5) }, uSun: { value: new THREE.Vector3(0.3, 0.8, 0.2) } };
  function liquify(mat, scale, amp, speed) {
    mat.onBeforeCompile = (sh) => {
      sh.uniforms.uTime = waterU.uTime;
      sh.uniforms.uWAmp = waterU.uWAmp;
      sh.uniforms.uWDir = waterU.uWDir;
      sh.uniforms.uSun = waterU.uSun;
      sh.uniforms.uNite = nightUniform;   // resolved at first render, after its declaration
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vWq;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nvWq = (modelMatrix * vec4(transformed, 1.0)).xyz;');
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vWq;\nuniform float uTime, uWAmp, uNite;\nuniform vec2 uWDir;\nuniform vec3 uSun;\nfloat wGlint = 0.0;\n' +
          'float whash(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }\n' +
          'float wvn(vec2 p) { vec2 i = floor(p), f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f); return mix(mix(whash(i), whash(i + vec2(1.0, 0.0)), u.x), mix(whash(i + vec2(0.0, 1.0)), whash(i + vec2(1.0, 1.0)), u.x), u.y); }\n' +
          'vec2 wgrad(vec2 p, vec2 d, float lam, float sp, float t) {\n' +
          '  float k = 6.2831853 / lam;\n' +
          '  return d * (cos(dot(p, d) * k + t * sp) * k);\n' +
          '}\n')
        .replace('#include <normal_fragment_begin>', '#include <normal_fragment_begin>\n{\n' +
          '  float wsc = ' + scale.toFixed(3) + ';\n' +
          '  float wsp = ' + speed.toFixed(3) + ';\n' +
          '  float wamp = ' + amp.toFixed(3) + ' * uWAmp;\n' +
          '  vec2 wd = normalize(uWDir);\n' +
          '  vec2 wp = vec2(-wd.y, wd.x);\n' +
          '  float wdist = length(vViewPosition);\n' +
          '  float wfade = clamp(1.35 - wdist / (2600.0 * wsc + 420.0), 0.14, 1.0);\n' +
          // the shore distance rides in the colour alpha where the sheet carries one (flatShorePoly)
          '#ifdef USE_COLOR_ALPHA\n  float wsh = vColor.a;\n#else\n  float wsh = 1.0;\n#endif\n' +
          // per-octave pixel-footprint weights: each wave set bows out before its
          // wavelength falls under a few pixels, so the regular sum can never
          // alias into the corduroy moire the old distance fade let through
          '  float fpx = max(fwidth(vWq.x), fwidth(vWq.z)) / wsc;\n' +
          '  float w1 = 1.0 - smoothstep(5.8, 23.0, fpx);\n' +
          '  float w2 = 1.0 - smoothstep(2.6, 10.5, fpx);\n' +
          '  float w3 = 1.0 - smoothstep(1.2, 4.8, fpx);\n' +
          '  float w4 = 1.0 - smoothstep(0.5, 2.1, fpx);\n' +
          // wind-gust patches: two slow crossed envelopes drift ruffled lanes and
          // glassy calms across the reach, the way real water carries cat\'s paws
          '  float wpat = 0.5 + 0.5 * sin(dot(vWq.xz, wd) * 0.011 + uTime * 0.22 * wsp) * sin(dot(vWq.xz, wp) * 0.0075 - uTime * 0.17 * wsp);\n' +
          // the surface: five octaves of value-noise slope in wind-aligned coordinates, crests
          // shorter across the wind, each octave scrolling at its own pace and fading before its
          // footprint could alias; no sine anywhere (a sum of sines read as stripes from height)
          '  vec2 wq = vec2(dot(vWq.xz, wd), dot(vWq.xz, wp) * 1.55);\n' +
          '  vec2 g = vec2(0.0);\n' +
          '  {\n' +
          '    float e = 0.35;\n' +
          '    vec2 q; float k; vec2 gg;\n' +
          '    q = wq / (34.0 * wsc) + vec2(uTime * 0.24 * wsp, 0.0); k = 0.30 * w1;\n' +
          '    gg = vec2(wvn(q + vec2(e, 0.0)) - wvn(q - vec2(e, 0.0)), wvn(q + vec2(0.0, e)) - wvn(q - vec2(0.0, e))) / (2.0 * e); g += gg * k;\n' +
          '    q = wq / (15.0 * wsc) + vec2(uTime * 0.36 * wsp, 3.7); k = 0.26 * w2;\n' +
          '    q += 0.22 * vec2(wvn(q * 0.45 + vec2(uTime * 0.09 * wsp, 5.0)) - 0.5, wvn(q * 0.45 + vec2(9.0, -uTime * 0.07 * wsp)) - 0.5);\n' +
          '    gg = vec2(wvn(q + vec2(e, 0.0)) - wvn(q - vec2(e, 0.0)), wvn(q + vec2(0.0, e)) - wvn(q - vec2(0.0, e))) / (2.0 * e); g += gg * k;\n' +
          '    q = wq / (6.5 * wsc) + vec2(uTime * 0.55 * wsp, 11.3); k = 0.2 * w3;\n' +
          '    q += 0.28 * vec2(wvn(q * 0.4 + vec2(uTime * 0.13 * wsp, 17.0)) - 0.5, wvn(q * 0.4 + vec2(23.0, -uTime * 0.11 * wsp)) - 0.5);\n' +
          '    gg = vec2(wvn(q + vec2(e, 0.0)) - wvn(q - vec2(e, 0.0)), wvn(q + vec2(0.0, e)) - wvn(q - vec2(0.0, e))) / (2.0 * e); g += gg * k;\n' +
          '    q = wq / (2.6 * wsc) + vec2(uTime * 0.55 * wsp, 27.1); k = 0.14 * w4;\n' +
          '    gg = vec2(wvn(q + vec2(e, 0.0)) - wvn(q - vec2(e, 0.0)), wvn(q + vec2(0.0, e)) - wvn(q - vec2(0.0, e))) / (2.0 * e); g += gg * k;\n' +
          '    q = wq / (1.2 * wsc) - vec2(uTime * 0.8 * wsp, 41.9); k = 0.09 * (1.0 - smoothstep(0.12, 0.55, fpx));\n' +
          '    gg = vec2(wvn(q + vec2(e, 0.0)) - wvn(q - vec2(e, 0.0)), wvn(q + vec2(0.0, e)) - wvn(q - vec2(0.0, e))) / (2.0 * e); g += gg * k;\n' +
          '  }\n' +
          '  g = wd * g.x + wp * g.y * 1.55;\n' +
          '  g *= wamp * wfade * (0.45 + 0.8 * wpat) * (0.5 + 0.5 * smoothstep(0.0, 0.25, wsh));\n' +
          '  vec3 wn = normalize(vec3(-g.x, 1.0, -g.y));\n' +
          '  normal = normalize(mix(normal, normalize(mat3(viewMatrix) * wn), 0.92));\n' +   // the PBR normal is view-space; wn stays world-space for the glint and fresnel below
          // sun glitter on the perturbed surface: the material is deliberately rough
          // (the river must not mirror the sky), so the sparkle is added explicitly
          // depth: the sheet lightens and greens toward the bank, and a band of animated foam
          // rides the shoreline itself; both read the baked shore distance
          // the shallows: the bottom shows through the first twenty metres, sand and silt under a
          // teal wash, then the channel goes deep (no foam: it read as a broken edge)
          '  vec3 wbase = diffuseColor.rgb;\n' +
          '  diffuseColor.a = opacity;\n' +
          '  vec3 wview = normalize(cameraPosition - vWq);\n' +
          // fresnel: the sheet reads as sky at grazing angles and as deep water below the eye
          '  float wfres = pow(1.0 - clamp(dot(wview, wn), 0.0, 1.0), 3.0);\n' +
          '  diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.36, 0.52, 0.68), wfres * 0.2 * (1.0 - uNite * 0.75));\n' +
          '  float wspec = pow(max(dot(wview, reflect(-normalize(uSun), wn)), 0.0), 140.0);\n' +
          // a broad low-power lobe under the sparkle: the soft sheet of light real
          // rivers throw toward the sun, not just point glitter
          '  wspec += pow(max(dot(wview, reflect(-normalize(uSun), wn)), 0.0), 14.0) * 0.08;\n' +
          // at night uSun is the MOON: keep a faint moonglade, not a sequin field
          '  wGlint = wspec * smoothstep(0.02, 0.1, uSun.y) * (0.55 + 0.45 * uWAmp) * wfade * (1.0 - uNite * 0.85);\n' +
          '}\n')
        // the sky's reflection comes back blue and dimmer than the sky itself: a wide sheet
        // seen at a grazing angle otherwise turns the colour of the horizon (pale), where the
        // game's water keeps its blue under the reflection. The body is not a Lambert floor:
        // under the noon sun a teal albedo lifted to a pale cyan (the river read milky from
        // every height), so the diffuse terms are damped and the stored colour is the water's
        // own deep blue at any sun height, the reflection and the glints on top
        .replace('#include <lights_fragment_end>', '#include <lights_fragment_end>\nreflectedLight.indirectSpecular *= vec3(0.30, 0.52, 0.95) * 0.45;\nreflectedLight.directSpecular *= 0.85;\nreflectedLight.directDiffuse *= 0.25;\nreflectedLight.indirectDiffuse *= 0.5;\n')
        .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\n' +
          'totalEmissiveRadiance += vec3(1.0, 0.93, 0.78) * wGlint * 1.4;\n');
    };
  }
  // ordered dither on the big smooth surfaces (city walls, bare ground, water):
  // ACES into an 8-bit framebuffer bands their shallow dusk gradients every
  // 15-25 px. Set at construction only, a later flip recompiles (false disables)
  const MAT_DITHER = true;
  // the outer rivers and far water polygons share one animated material
  const riverMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.15, metalness: 0.12, envMapIntensity: 0.7, dithering: MAT_DITHER });
  liquify(riverMat, 1.0, 1.0, 0.8);

  function waterPoint(along, out) {
    // along: meters along the shoreline from the towers' projection; out: meters east of the bulkhead
    const t = (towersCenter.x - wl.px) * wl.dx + (towersCenter.z - wl.pz) * wl.dz;
    return [
      wl.px + wl.dx * (t + along) + wl.nx * (wl.off + out),
      wl.pz + wl.dz * (t + along) + wl.nz * (wl.off + out),
    ];
  }

  // ---------------------------------------------------------------- terrain
  // Society Hill sits on a bluff ~10 m above the Delaware. East of Front St the
  // I-95 trench drops 8 m, then the Penn's Landing shelf sits 6.5-7.5 m below the
  // city, then the bulkhead and the river. Cap decks bridge the trench at
  // Foglietta Plaza and the Vietnam memorial; the new Park at Penn's Landing is a
  // continuous lawn sloping from Front St down to the promenade. Heights are
  // relative to the city datum (y = 0); lateral offsets are measured from the
  // fitted Columbus Blvd centerline (positive = toward the river).
  // Elevation: USGS NED 10 m grid (dem.json, meters above sea level). The datum
  // is the towers' site (8.3 m ASL) so the towers stay at y = 0; the rest of the
  // city rides the real ground — Front St ~5 m lower, 5th St ~2 m higher.
  const DEM0 = (typeof DEM !== 'undefined' && DEM && DEM.rows) ? DEM : null;
  const DEMW = (typeof DEM_WIDE !== 'undefined' && DEM_WIDE && DEM_WIDE.rows) ? DEM_WIDE : null;
  const DEMS = (typeof DEM_SOUTH !== 'undefined' && DEM_SOUTH && DEM_SOUTH.rows) ? DEM_SOUTH : null;
  const DEMC = (typeof DEM_CITY !== 'undefined' && DEM_CITY && DEM_CITY.rows) ? DEM_CITY : null;
  // NW hills patch (East Falls / Manayunk / the Wissahickon / Chestnut Hill) at
  // 50 m — dem_city's 150 m grid mushes the gorge. The patch's border samples
  // are pre-feathered toward dem_city at fetch time (fetch_dem_nw.py), so
  // sampling it first needs no seam logic here.
  const DEMN = (typeof DEM_NW !== 'undefined' && DEM_NW && DEM_NW.rows) ? DEM_NW : null;
  const CORE_EXT = { x0: -640, x1: 770, z0: -520, z1: 850 }; // the detailed extract
  function inCore(x, z) { return x >= CORE_EXT.x0 && x <= CORE_EXT.x1 && z >= CORE_EXT.z0 && z <= CORE_EXT.z1; }
  function sampleDem(G, x, z, fallback) {
    const fx = (x - G.x0) / G.cell, fz = (z - G.z0) / G.cell;
    if (fx < 0 || fz < 0 || fx > G.nx - 1 || fz > G.nz - 1) return null;
    const i = clamp(Math.floor(fx), 0, G.nx - 2), j = clamp(Math.floor(fz), 0, G.nz - 2);
    const tx = clamp(fx - i, 0, 1), tz = clamp(fz - j, 0, 1);
    const r0 = G.rows[j], r1 = G.rows[j + 1];
    const v = (a) => (a == null ? fallback : a);
    const a = v(r0[i]) * (1 - tx) + v(r0[i + 1]) * tx;
    const b = v(r1[i]) * (1 - tx) + v(r1[i + 1]) * tx;
    return a * (1 - tz) + b * tz;
  }
  function demAbs(x, z) {
    // null DEM cells (NED voids over made land) must NOT fall back to 0 ASL — that is
    // below the model's water plane and floods whole blocks (the stadium site)
    let v = DEM0 ? sampleDem(DEM0, x, z, 8.34) : null;
    if (v == null && DEMW) v = sampleDem(DEMW, x, z, 3.2);
    if (v == null && DEMS) v = sampleDem(DEMS, x, z, 3.2);
    if (v == null && DEMN) v = sampleDem(DEMN, x, z, 4.0);
    if (v == null && DEMC) v = sampleDem(DEMC, x, z, 4.0);
    if (v == null && DEMW) { // beyond the grids: clamp to the nearest edge sample
      const G = (DEMS && z > DEMW.z0 + DEMW.cell * (DEMW.nz - 1)) ? DEMS : DEMW;
      v = sampleDem(G, clamp(x, G.x0, G.x0 + G.cell * (G.nx - 1)), clamp(z, G.z0, G.z0 + G.cell * (G.nz - 1)), 0);
    }
    return v == null ? 8.34 : v;
  }
  const DATUM = demAbs(towersCenter.x, towersCenter.z);
  function demY(x, z) { return demAbs(x, z) - DATUM; }
  // constructed waterfront, relative to the datum (river ~0.5 m ASL, shelf ~3 m, I-95 ~1.5 m)
  const TERRAIN = { trenchW: 10, trenchE: 72, trenchFloor: 1.5 - DATUM, shelfLo: 2.4 - DATUM, shelfHi: 4.0 - DATUM, bulkhead: 2.8 - DATUM, water: 0.5 - DATUM, bed: -2.0 - DATUM };
  // Front St line (the city grid runs ~10 deg off my axes; I-95 hugs Front St's east side)
  const fl = { px: 140, pz: 0, dx: -0.167, dz: 0.986, nx: 0.986, nz: 0.167 };
  {
    const pts = [];
    for (const r of D.roads) if (r.name && /front street/i.test(r.name)) for (const q of r.pts) pts.push(q);
    if (pts.length > 3) {
      let mx = 0, mz = 0;
      for (const q of pts) { mx += q[0]; mz += q[1]; }
      mx /= pts.length; mz /= pts.length;
      let sxx = 0, sxz = 0, szz = 0;
      for (const q of pts) { const ax = q[0] - mx, az = q[1] - mz; sxx += ax * ax; sxz += ax * az; szz += az * az; }
      const ang = 0.5 * Math.atan2(2 * sxz, sxx - szz);
      fl.px = mx; fl.pz = mz; fl.dx = Math.cos(ang); fl.dz = Math.sin(ang);
      if (fl.dz < 0) { fl.dx = -fl.dx; fl.dz = -fl.dz; }
      fl.nx = -fl.dz; fl.nz = fl.dx;
      if (fl.nx < 0) { fl.nx = -fl.nx; fl.nz = -fl.nz; }
    }
  }
  function frontOff(x, z) { return (x - fl.px) * fl.nx + (z - fl.pz) * fl.nz; }
  function frontPt(o, z) { const t = (z - fl.pz - fl.nz * o) / fl.dz; return [fl.px + fl.nx * o + fl.dx * t, z]; }
  // the city plateau near the trench must not inherit DEM samples that fell into I-95
  function cityY(x, z) {
    const o = frontOff(x, z);
    if (o > -100) { const [rx] = frontPt(-110, z); return Math.max(demY(x, z), demY(rx, z) - 0.4); }
    return demY(x, z);
  }
  function frontDem(z) { const [rx] = frontPt(-110, z); return demY(rx, z); }
  // the Delaware's edge as a polyline x(z): Penn's Landing bulges east, the marina
  // basin is notched in, the shore pulls back south of the museum ships
  const SHORE = [[404, -3000], [404, -520], [422, -350], [422, -200], [432, -60], [432, -8], [312, -6], [312, 216], [432, 218], [432, 232], [345, 240], [345, 430], [380, 450], [380, 500], [345, 520], [345, 3500]];
  function xShore(z) {
    for (let i = 0; i < SHORE.length - 1; i++) {
      const a = SHORE[i], b = SHORE[i + 1];
      if (z >= a[1] && z <= b[1]) { const t = (z - a[1]) / Math.max(1e-6, b[1] - a[1]); return a[0] + (b[0] - a[0]) * t; }
    }
    return z < SHORE[0][1] ? SHORE[0][0] : SHORE[SHORE.length - 1][0];
  }
  const CAPS = [
    { z0: -345, z1: -201, kind: 'park' },      // Park at Penn's Landing: Chestnut -> Walnut
    { z0: -25, z1: 64, kind: 'deck', dy: 0 },  // Foglietta Plaza: Dock -> Spruce
    { z0: 64, z1: 122, kind: 'deck', dy: -1 }, // Vietnam Veterans Memorial deck
  ];
  const slips = []; // ship berths carved into the shelf: [x0, x1, z0, z1]
  for (const b of D.buildings) {
    if (b.t !== 'ship' || !b.poly || b.poly.length < 3) continue;
    let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9;
    for (const q of b.poly) { x0 = Math.min(x0, q[0]); x1 = Math.max(x1, q[0]); z0 = Math.min(z0, q[1]); z1 = Math.max(z1, q[1]); }
    slips.push([x0 - 7, x1 + 7, z0 - 7, z1 + 7]);
  }
  const extraTreeSpots = [];
  const poolTreeSpots = [];   // pool-terrace ring — planted through clear() so none land in buildings
  function inRiver(x, z) {
    if (x > xShore(z)) return true;
    for (const sl of slips) if (x > sl[0] && x < sl[1] && z > sl[2] && z < sl[3]) return true;
    return false;
  }
  function shelfY(x, z) { return clamp(demY(x, z), TERRAIN.shelfLo, TERRAIN.shelfHi); }
  function parkCapY(x, z) {
    const [xf] = frontPt(TERRAIN.trenchW, z);
    const top = frontDem(z);
    return top + (TERRAIN.bulkhead - top) * clamp((x - xf) / Math.max(20, xShore(z) - xf), 0, 1);
  }
  const PLAZA_R = 58;
  // each tower also stands on its own full-height rectangular pad: the radial feather
  // alone starts INSIDE the south tower's footprint (its SE corner is ~70 m out), so
  // the lawn dropped away under the fixed-height base and the colonnade/lobby floated
  const towerPads = towers.map(t => {
    const ang = -(t.angleRad || 0);
    return { cx: t.centroid[0], cz: t.centroid[1], hw: t.width_m / 2 + 5, hd: t.depth_m / 2 + 5, cos: Math.cos(ang), sin: Math.sin(ang) };
  });
  function plazaLift(x, z) {
    // wide smoothstep feather: the draped lawns/ribbons sample this at ~10 m, so a
    // tight linear falloff aliased into wedges that sliced across the plaza edge
    const d = Math.hypot(x - towersCenter.x, z - towersCenter.z);
    let t = d < PLAZA_R ? 1.0 : (d >= PLAZA_R + 16 ? 0 : 1 - (d - PLAZA_R) / 16);
    for (const p of towerPads) {
      if (t >= 1) break;
      const dx = x - p.cx, dz = z - p.cz;
      const u = Math.abs(dx * p.cos - dz * p.sin) - p.hw;
      const v = Math.abs(dx * p.sin + dz * p.cos) - p.hd;
      const dr = Math.max(u, v);
      const tp = dr <= 0 ? 1.0 : (dr >= 12 ? 0 : 1 - dr / 12);
      if (tp > t) t = tp;
    }
    if (t <= 0) return 0;
    if (t >= 1) return 1.0;
    return t * t * (3 - 2 * t);
  }
  const bermSpots = []; // [x, z, rx, rz, rotY] — trees must not sprout through the lawn berms
  // where things sit. mode 'ground' = objects, trees, lawns; 'road' = streets
  // (bridged over the trench, tunnelled under the park cap)
  function siteY(x, z, mode) {
    if (!inCore(x, z)) { // outer districts ride the wide DEM. Low terrain east of the
      // Delaware bank is river; low LAND west of it (stadiums, FDR, the airport — NED
      // reads made-land near 0 ASL) clamps just above the water plane instead of flooding
      const y = demY(x, z);
      if (y >= TERRAIN.water + 0.6) return y;
      return eastOfDelaware(x, z) ? TERRAIN.bulkhead : TERRAIN.water + 0.45;
    }
    if (inRiver(x, z)) return TERRAIN.bulkhead;
    const o = frontOff(x, z);
    const cap = CAPS.find(c => z > c.z0 && z < c.z1);
    if (cap && cap.kind === 'park' && o > TERRAIN.trenchW - 3) {
      if (mode === 'road') return o > TERRAIN.trenchE ? shelfY(x, z) : parkCapY(x, z) - 0.35;
      return parkCapY(x, z);
    }
    if (o < TERRAIN.trenchW) return cityY(x, z) + plazaLift(x, z);
    if (o < TERRAIN.trenchE) return (cap && cap.kind === 'deck') ? frontDem(z) + cap.dy : (mode === 'road' ? frontDem(z) : TERRAIN.trenchFloor);
    return shelfY(x, z);
  }
  function walkY(x, z) { return Math.max(siteY(x, z, 'ground'), siteY(x, z, 'road')); }

  // collision + occupancy structures (filled during build)
  const colGrid = new Map();
  const COL_CELL = 8;
  const colSegs = [];
  function colKey(cx, cz) { return cx + ':' + cz; }
  function addColSeg(ax, az, bx, bz) {
    const idx = colSegs.length;
    colSegs.push(ax, az, bx, bz);
    const minx = Math.floor(Math.min(ax, bx) / COL_CELL), maxx = Math.floor(Math.max(ax, bx) / COL_CELL);
    const minz = Math.floor(Math.min(az, bz) / COL_CELL), maxz = Math.floor(Math.max(az, bz) / COL_CELL);
    for (let gx = minx; gx <= maxx; gx++) for (let gz = minz; gz <= maxz; gz++) {
      const k = colKey(gx, gz);
      let a = colGrid.get(k);
      if (!a) { a = []; colGrid.set(k, a); }
      a.push(idx);
    }
  }
  // road segments for tree rejection (streets only; park paths keep their trees)
  const roadGrid = new Map();
  const ROAD_CELL = 12;
  function addRoadSeg(ax, az, bx, bz, hw) {
    const idx = roadSegs.length;
    roadSegs.push(ax, az, bx, bz, hw);
    const minx = Math.floor((Math.min(ax, bx) - hw) / ROAD_CELL), maxx = Math.floor((Math.max(ax, bx) + hw) / ROAD_CELL);
    const minz = Math.floor((Math.min(az, bz) - hw) / ROAD_CELL), maxz = Math.floor((Math.max(az, bz) + hw) / ROAD_CELL);
    for (let gx = minx; gx <= maxx; gx++) for (let gz = minz; gz <= maxz; gz++) {
      const k = gx + ':' + gz;
      let a = roadGrid.get(k);
      if (!a) { a = []; roadGrid.set(k, a); }
      a.push(idx);
    }
  }
  const roadSegs = [];
  function nearRoad(x, z, pad) {
    const a = roadGrid.get(Math.floor(x / ROAD_CELL) + ':' + Math.floor(z / ROAD_CELL));
    if (!a) return false;
    for (const s of a) {
      const ax = roadSegs[s], az = roadSegs[s + 1], bx = roadSegs[s + 2], bz = roadSegs[s + 3], hw = roadSegs[s + 4];
      const dx = bx - ax, dz = bz - az;
      const L2 = dx * dx + dz * dz;
      let t = L2 > 0 ? ((x - ax) * dx + (z - az) * dz) / L2 : 0;
      t = clamp(t, 0, 1);
      const px = ax + dx * t - x, pz = az + dz * t - z;
      const r = hw + pad;
      if (px * px + pz * pz < r * r) return true;
    }
    return false;
  }

  // like nearRoad, but only matches core segments running PARALLEL to (ux, uz) —
  // used to drop wide-set duplicates without notching perpendicular crossings
  function nearRoadAligned(x, z, pad, ux, uz) {
    const a = roadGrid.get(Math.floor(x / ROAD_CELL) + ':' + Math.floor(z / ROAD_CELL));
    if (!a) return false;
    for (const s of a) {
      const ax = roadSegs[s], az = roadSegs[s + 1], bx = roadSegs[s + 2], bz = roadSegs[s + 3], hw = roadSegs[s + 4];
      let dx = bx - ax, dz = bz - az;
      const L = Math.hypot(dx, dz) || 1;
      dx /= L; dz /= L;
      if (Math.abs(dx * ux + dz * uz) < 0.82) continue;
      let t = ((x - ax) * (bx - ax) + (z - az) * (bz - az)) / (L * L);
      t = clamp(t, 0, 1);
      const px = ax + (bx - ax) * t - x, pz = az + (bz - az) * t - z;
      const r = hw + pad;
      if (px * px + pz * pz < r * r) return true;
    }
    return false;
  }

  function nearBuildingEdge(x, z, r) {
    const gx = Math.floor(x / COL_CELL), gz = Math.floor(z / COL_CELL);
    for (let ix = gx - 1; ix <= gx + 1; ix++) for (let iz = gz - 1; iz <= gz + 1; iz++) {
      const a = colGrid.get(colKey(ix, iz));
      if (!a) continue;
      for (const s of a) {
        const ax = colSegs[s], az = colSegs[s + 1], bx = colSegs[s + 2], bz = colSegs[s + 3];
        const dx = bx - ax, dz = bz - az;
        const L2 = dx * dx + dz * dz;
        let t = L2 > 0 ? ((x - ax) * dx + (z - az) * dz) / L2 : 0;
        t = clamp(t, 0, 1);
        const px = ax + dx * t - x, pz = az + dz * t - z;
        if (px * px + pz * pz < r * r) return true;
      }
    }
    return false;
  }

  const buildingPolys = []; // interior tests (tree placement)
  const polyGrid = new Map();
  const POLY_CELL = 16;
  function registerPoly(poly) {
    const idx = buildingPolys.length;
    buildingPolys.push(poly);
    let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9;
    for (const p of poly) {
      if (p[0] < x0) x0 = p[0]; if (p[0] > x1) x1 = p[0];
      if (p[1] < z0) z0 = p[1]; if (p[1] > z1) z1 = p[1];
    }
    for (let gx = Math.floor(x0 / POLY_CELL); gx <= Math.floor(x1 / POLY_CELL); gx++)
      for (let gz = Math.floor(z0 / POLY_CELL); gz <= Math.floor(z1 / POLY_CELL); gz++) {
        const k = gx + ':' + gz;
        let a = polyGrid.get(k);
        if (!a) { a = []; polyGrid.set(k, a); }
        a.push(idx);
      }
  }
  function insideBuilding(x, z) {
    const a = polyGrid.get(Math.floor(x / POLY_CELL) + ':' + Math.floor(z / POLY_CELL));
    if (!a) return false;
    for (const idx of a) if (pointInPoly(x, z, buildingPolys[idx])) return true;
    return false;
  }
  const rayTargets = [];   // double-click focus raycasts only against these
  // phones die on PEAK memory, not triangle count: once the GPU holds a big
  // merged geometry we never raycast, the CPU-side typed arrays are pure waste
  function freeOnUpload(g) {
    if (!g.boundingSphere) g.computeBoundingSphere();   // frustum culling must never touch a nulled array
    for (const k in g.attributes) g.attributes[k].onUpload(function () { this.array = null; });
    if (g.index) g.index.onUpload(function () { this.array = null; });
  }
  // base64 -> bytes for the packed blobs. The charCodeAt loop is 6x faster
  // than Uint8Array.from(str, fn) (which walks the iterator path and calls the
  // mapper 7.7 M times). build.py stores the int16 blobs byte-PLANAR (16-byte
  // header, then every low byte, then every high byte: DEFLATE sees two smooth
  // streams, 22% off the gzipped page), so the body is re-interleaved here.
  function unb64(b64, name) {
    const s = atob(b64);
    const n = s.length;
    const out = new Uint8Array(n);
    const planar = typeof B64_PLANAR !== 'undefined' && B64_PLANAR && B64_PLANAR[name];
    if (!planar || n <= 16) { for (let i = 0; i < n; i++) out[i] = s.charCodeAt(i); return out; }
    for (let i = 0; i < 16; i++) out[i] = s.charCodeAt(i);
    const half = (n - 16) >> 1;
    for (let i = 0, j = 16; i < half; i++, j += 2) { out[j] = s.charCodeAt(16 + i); out[j + 1] = s.charCodeAt(16 + half + i); }
    return out;
  }
  // a real macrotask boundary that is NOT timer-clamped in hidden tabs
  // (setTimeout is held to 1 s+ there; 23 build steps of that was 23 s of sleep)
  const yieldNow = () => new Promise(r => { const ch = new MessageChannel(); ch.port1.onmessage = () => r(); ch.port2.postMessage(0); });
  // Growable typed accumulators for the packed-ring chunks. Boxed JS number
  // arrays cost ~92 B per vertex and staged a whole ring before its first
  // upload (1.35 GB measured on the far ring: the figure that kills the tab on
  // phones); these cost 24 B, and a chunk seals and uploads as soon as it
  // passes 60k vertices, so the staging peak is a few live chunks, not a ring.
  class IdxBuf {
    constructor(cap) { this.a = new Uint16Array(cap); this.n = 0; this.u16 = true; }
    push() {
      const k = arguments.length;
      if (this.n + k > this.a.length) this.grow(this.n + k);
      for (let i = 0; i < k; i++) {
        const v = arguments[i];
        if (v > 65535 && this.u16) { const b = new Uint32Array(this.a.length); b.set(this.a); this.a = b; this.u16 = false; }
        this.a[this.n++] = v;
      }
    }
    grow(min) {
      let cap = this.a.length * 2;
      while (cap < min) cap *= 2;
      const b = this.u16 ? new Uint16Array(cap) : new Uint32Array(cap);
      b.set(this.a); this.a = b;
    }
    view() { return this.a.subarray(0, this.n); }
  }
  class VBuf {
    constructor(cap) { this.n = 0; this.cap = 0; this.grow(cap); this.idx = new IdxBuf(cap * 3); }
    grow(cap) {
      const pos = new Float32Array(cap * 3), nor = new Int8Array(cap * 3), col = new Uint8Array(cap * 3);
      const sty = new Int8Array(cap), bas = new Float32Array(cap), flh = new Int8Array(cap);
      if (this.n) {
        const n = this.n;
        pos.set(this.pos.subarray(0, n * 3)); nor.set(this.nor.subarray(0, n * 3)); col.set(this.col.subarray(0, n * 3));
        sty.set(this.sty.subarray(0, n)); bas.set(this.bas.subarray(0, n)); flh.set(this.flh.subarray(0, n));
      }
      this.pos = pos; this.nor = nor; this.col = col; this.sty = sty; this.bas = bas; this.flh = flh; this.cap = cap;
    }
    push(x, y, z, nx, ny, nz, r, g, b, st, base, fh) {
      if (this.n === this.cap) this.grow(this.cap * 2);
      const i = this.n, j = i * 3;
      this.pos[j] = x; this.pos[j + 1] = y; this.pos[j + 2] = z;
      this.nor[j] = nx * 127; this.nor[j + 1] = ny * 127; this.nor[j + 2] = nz * 127;
      this.col[j] = r * 255; this.col[j + 1] = g * 255; this.col[j + 2] = b * 255;
      this.sty[i] = st; this.bas[i] = base; this.flh[i] = fh ? Math.round(fh * 10) : 0;
      return this.n++;
    }
    // exact-length views; freeOnUpload drops them once the GPU has the copy
    geometry(facade) {
      const g = new THREE.BufferGeometry(), n = this.n;
      g.setAttribute('position', new THREE.BufferAttribute(this.pos.subarray(0, n * 3), 3));
      g.setAttribute('normal', new THREE.BufferAttribute(this.nor.subarray(0, n * 3), 3, true));
      g.setAttribute('color', new THREE.BufferAttribute(this.col.subarray(0, n * 3), 3, true));
      if (facade) {
        g.setAttribute('aStyle', new THREE.BufferAttribute(this.sty.subarray(0, n), 1));
        g.setAttribute('aFloorH', new THREE.BufferAttribute(this.flh.subarray(0, n), 1));
        g.setAttribute('aBase', new THREE.BufferAttribute(this.bas.subarray(0, n), 1));
      }
      g.setIndex(new THREE.BufferAttribute(this.idx.view(), 1));
      g.computeBoundingSphere();
      freeOnUpload(g);
      this.pos = this.nor = this.col = this.sty = this.bas = this.flh = this.idx = null;
      return g;
    }
  }

  const groupCity = new THREE.Group();
  scene.add(groupCity);

  const buildSteps = [];
  function step(msg, fn) { buildSteps.push({ msg, fn }); }

  // ------------------------------------------------ ground, water, roads, parks
  step('Laying out the ground', () => {
    const groundMat = groundSurfMat();
    const Z0 = CORE_EXT.z0, Z1 = CORE_EXT.z1;
    const flat = (poly, y) => { const g = new THREE.ShapeGeometry(shapeFromPoly(poly, null)); g.rotateX(-Math.PI / 2); g.translate(0, y, 0); return g; };
    // city heightfield (12.5 m) riding the DEM, diving into the trench east of Front St
    {
      const X0 = CORE_EXT.x0, X1 = CORE_EXT.x1, ZA = CORE_EXT.z0, ZB = CORE_EXT.z1, cell = 12.5;
      const nx = Math.round((X1 - X0) / cell), nz = Math.round((ZB - ZA) / cell);
      const pos = [];
      for (let j = 0; j <= nz; j++) for (let i = 0; i <= nx; i++) {
        const x = X0 + i * cell, z = ZA + j * cell;
        // east of the trench the shelf mesh takes over; past the shoreline this
        // field must dive below the water plane or it reads as a slab on the river
        // (the -4 margin keeps interpolated cell faces from surfacing east of the bulkhead)
        const y = frontOff(x, z) < TERRAIN.trenchW ? cityY(x, z) - 0.05 : ((inWater(x, z) > -4 || inRiver(x, z)) ? TERRAIN.bed - 0.05 : TERRAIN.trenchFloor - 0.05);
        pos.push(x, y, z);
      }
      const idx = [];
      for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
        const a = j * (nx + 1) + i, b = a + 1, c = a + nx + 1, d = c + 1;
        idx.push(a, c, b, b, c, d);
      }
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
      g.setIndex(idx);
      g.computeVertexNormals();
      const city = new THREE.Mesh(g, groundMat);
      city.receiveShadow = true; groupCity.add(city); rayTargets.push(city);
      // river bed under everything; the water plane sits above it
      const far = new THREE.Mesh(flat([[-9000, -9000], [9000, -9000], [9000, 9000], [-9000, 9000]], TERRAIN.bed), new THREE.MeshStandardMaterial({ color: 0x4a4f48, roughness: 1 }));
      groupCity.add(far);
    }
    // outer districts: 25 m heightfields around the core, water where the DEM sits at river level
    {
      const W = { x0: -3700, x1: 2300, z0: -4480, z1: 6400 };
      const strips = [
        [W.x0, W.x1, W.z0, CORE_EXT.z0], [W.x0, W.x1, CORE_EXT.z1, W.z1],
        [W.x0, CORE_EXT.x0, CORE_EXT.z0, CORE_EXT.z1], [CORE_EXT.x1, W.x1, CORE_EXT.z0, CORE_EXT.z1],
      ];
      // Fairmount greening: around the Art Museum the bare heightfield is parkland,
      // not pavement — vertex-tint those cells toward park green (a ratio of park to
      // ground, a tint on the shared meadow shader), feathered 80 m
      const wideGroundMat = groundSurfMat({ vertexColors: true });
      const FMZ = { x0: -3690, x1: -2480, z0: -2950, z1: -1720 };
      const pkC = new THREE.Color(COLORS.park), gdC = new THREE.Color(COLORS.ground);
      const fmR = [pkC.r / gdC.r, pkC.g / gdC.g, pkC.b / gdC.b];
      for (const [x0, x1, z0, z1] of strips) {
        const cell = 25, nx = Math.max(1, Math.round((x1 - x0) / cell)), nz = Math.max(1, Math.round((z1 - z0) / cell));
        const pos = [];
        const col = [];
        const hole = [];   // vertices inside the Vine Street cut: their cells are skipped
        for (let j = 0; j <= nz; j++) for (let i = 0; i <= nx; i++) {
          const x = x0 + (x1 - x0) * i / nx, z = z0 + (z1 - z0) * j / nz;
          const y = demY(x, z);
          let yy = (y < TERRAIN.water + 0.6 ? (eastOfDelaware(x, z) ? TERRAIN.bed : TERRAIN.water + 0.45) : y) - 0.05;
          yy = riverCarve(x, z, yy);   // the Schuylkill's channel
          // NED reads a made-land shelf across the Delaware at the Walt Whitman
          // crossing (~3 m above water mid-river) — those cells rendered as a flat
          // gray band under the deck; between the banks, send them to the bed
          if (x > 880 && x < 1950 && y >= TERRAIN.water + 0.6 && y < TERRAIN.water + 4.5 && wwbNear(x, z, 260)) yy = TERRAIN.bed - 0.05;
          pos.push(x, yy, z);
          hole.push(cutHole(x, z) ? 1 : 0);
          const inD = Math.min(x - FMZ.x0, FMZ.x1 - x, z - FMZ.z0, FMZ.z1 - z);
          const t = clamp(inD / 80, 0, 1);
          col.push(1 + (fmR[0] - 1) * t, 1 + (fmR[1] - 1) * t, 1 + (fmR[2] - 1) * t);
        }
        const idx = [];
        const skip = new Uint8Array(nx * nz);   // the cells dropped below, for the ground registry
        let skipped = 0;
        for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
          const a = j * (nx + 1) + i, b = a + 1, c = a + nx + 1, d = c + 1;
          // the Vine Street Expressway cut is open ground: drop cells touching it
          // (index skip only — pos and col stay parallel; the collar apron built in
          // 'Raising the overpasses' hides the ragged hole rim at grade)
          if (hole[a] || hole[b] || hole[c] || hole[d]) { skip[j * nx + i] = 1; skipped++; continue; }
          idx.push(a, c, b, b, c, d);
        }
        const g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
        g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(col), 3));
        g.setIndex(idx);
        g.computeVertexNormals();
        registerGround(g, x0, x1, z0, z1, nx, nz, null, skipped ? skip : null, cell);   // the drawn surface, for conformDrape and the roads
        const m = new THREE.Mesh(g, wideGroundMat);
        groupCity.add(m); rayTargets.push(m);
      }
    }
    // trench floor
    const trench = new THREE.Mesh(flat([frontPt(TERRAIN.trenchW, Z0), frontPt(TERRAIN.trenchE, Z0), frontPt(TERRAIN.trenchE, Z1), frontPt(TERRAIN.trenchW, Z1)], TERRAIN.trenchFloor),
      new THREE.MeshStandardMaterial({ color: 0x4b4843, roughness: 0.95 }));
    trench.receiveShadow = true; groupCity.add(trench);
    // waterfront shelf: heightfield between the trench's east wall and the shoreline, 5 m rows
    {
      const rows = [], cols = 40;
      for (let z = Z0; z <= Z1; z += 5) rows.push(z);
      const pos = [];
      for (const z of rows) {
        const [xw] = frontPt(TERRAIN.trenchE - 1, z);
        const xe = xShore(z) + 2;
        for (let c = 0; c <= cols; c++) {
          const x = xw + (xe - xw) * (c / cols);
          pos.push(x, inRiver(x, z) ? TERRAIN.bed : shelfY(x, z), z);
        }
      }
      const idx = [];
      const W = cols + 1;
      for (let r = 0; r < rows.length - 1; r++) for (let c = 0; c < cols; c++) {
        const a = r * W + c, b = a + 1, cc = a + W, d = cc + 1;
        idx.push(a, cc, b, b, cc, d);
      }
      const shelfG = new THREE.BufferGeometry();
      shelfG.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
      shelfG.setIndex(idx);
      shelfG.computeVertexNormals();
      const shelf = new THREE.Mesh(shelfG, groundMat);
      shelf.receiveShadow = true; groupCity.add(shelf); rayTargets.push(shelf);
    }
    // (river bed is the global far plane; the water surface is one plane at river level)
    // vertical faces: trench walls (parapet on the Front St side), bulkhead along the shore, ship slips
    const wallParts = [];
    const vstrip = (ax, az, bx, bz, y0, y1, hex) => {
      const arr = new Float32Array([ax, y0, az, bx, y0, bz, bx, y1, bz, ax, y0, az, bx, y1, bz, ax, y1, az]);
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(arr, 3));
      g.computeVertexNormals();
      wallParts.push({ geom: g, color: new THREE.Color(hex), style: 3 });
    };
    // trench walls step with Front St's elevation; 25 m strips
    for (let z = -1200; z < 1800; z += 25) {
      const a = frontPt(TERRAIN.trenchW, z), b = frontPt(TERRAIN.trenchW, z + 25);
      vstrip(a[0], a[1], b[0], b[1], TERRAIN.trenchFloor - 0.3, frontDem(z + 12) + 1.2, '#9a978f');
      const c = frontPt(TERRAIN.trenchE, z), d = frontPt(TERRAIN.trenchE, z + 25);
      vstrip(c[0], c[1], d[0], d[1], TERRAIN.trenchFloor - 0.3, shelfY(d[0] + 3, z + 12) + 0.3, '#9a978f');
    }
    for (let i = 0; i < SHORE.length - 1; i++) vstrip(SHORE[i][0], SHORE[i][1], SHORE[i + 1][0], SHORE[i + 1][1], TERRAIN.bed, TERRAIN.bulkhead, '#6f6a62');
    for (const sl of slips) {
      vstrip(sl[0], sl[2], sl[0], sl[3], TERRAIN.bed, TERRAIN.bulkhead, '#6f6a62');
      vstrip(sl[0], sl[2], sl[1], sl[2], TERRAIN.bed, TERRAIN.bulkhead, '#6f6a62');
      vstrip(sl[0], sl[3], sl[1], sl[3], TERRAIN.bed, TERRAIN.bulkhead, '#6f6a62');
    }
    const walls = new THREE.Mesh(mergeColored(wallParts), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.9, side: THREE.DoubleSide }));
    walls.receiveShadow = true; groupCity.add(walls);
    freeOnUpload(walls.geometry);   // never raycast (focus and pick use rayTargets only)

    const waterMat = new THREE.MeshStandardMaterial({ color: COLORS.water, roughness: 0.15, metalness: 0.12, envMapIntensity: 0.7, dithering: MAT_DITHER });
    liquify(waterMat, 1.0, 1.0, 0.8);      // the Delaware breathes
    const water = new THREE.Mesh(flat([[-9000, -9000], [9000, -9000], [9000, 9000], [-9000, 9000]], TERRAIN.water), waterMat);
    water.receiveShadow = true;
    groupCity.add(water);
    const slipParts = [];
    const rectPoly = (r) => [[r[0], r[2]], [r[1], r[2]], [r[1], r[3]], [r[0], r[3]]];
    for (const sl of slips) slipParts.push({ geom: flatPoly(rectPoly(sl), null, TERRAIN.water + 0.05, true), color: new THREE.Color(COLORS.water) });
    if (slipParts.length) groupCity.add(new THREE.Mesh(mergeColored(slipParts), waterMat));
    // OSM-mapped water bodies (basins, fountains)
    const wparts = [];
    for (const a of D.areas || []) {
      if (a.kind === 'water' && a.poly.length >= 3) wparts.push({ geom: flatPoly(a.poly, null, LAYER.basin), color: new THREE.Color(COLORS.water) });
    }
    if (wparts.length) {
      const basinMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.3, metalness: 0.2 });
      liquify(basinMat, 0.12, 0.9, 2.2);   // pond-scale ripples on basins and fountains
      const wm = new THREE.Mesh(mergeColored(wparts), basinMat);
      groupCity.add(wm);
    }
    // swimming pools (OSM leisure=swimming_pool; missed by the original query)
    const POOLS = [
      [[8.25, 71.61], [6.98, 79.82], [23.46, 82.32], [24.72, 74.11]],       // Society Hill Towers pool, south of 220 Locust
      [[-1.29, 180.63], [9.59, 182.37], [10.57, 176.36], [-0.31, 174.61]],  // townhouse-court pool near Delancey
    ];
    const poolParts = [], deckParts = [];
    for (let pi = 0; pi < POOLS.length; pi++) {
      const poly = POOLS[pi];
      registerPoly(poly); // keeps trees off the water
      if (pi === 0) {
        // The towers' pool terrace sits on the plaza feather, so terrain-following
        // 4-corner planes tilt every which way and slice each other (the "odd shape").
        // Build it as one LEVEL terrace instead: a skirted slab at the highest ground
        // point under it, the pool cut in as a true hole, water sunk in-ground.
        const ob = orientedBox(poly);
        const a = obbAxis(ob);
        const m = 5;
        const rim = (e) => [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([su, sv]) => [
          ob.cx + a.ax * su * (a.hl + e) + a.px * sv * (a.hs + e),
          ob.cz + a.az * su * (a.hl + e) + a.pz * sv * (a.hs + e),
        ]);
        const deck = rim(m);
        let ref = siteY(ob.cx, ob.cz, 'ground');
        for (const q of deck) ref = Math.max(ref, siteY(q[0], q[1], 'ground'));
        const top = ref + 0.14;
        deckParts.push({ geom: buildingGeom(deck, [poly], top, ref - 1.8), color: new THREE.Color(0xb3ab9c) });
        deckParts.push({ geom: flatPoly(rim(0.9), [poly], top + 0.012, true), color: new THREE.Color(0xe9e5da) }); // flush coping
        poolParts.push({ geom: flatPoly(poly, null, top - 0.12, true), color: new THREE.Color(0x3fa9c9) });
        registerPoly(deck);
        // shade trees ringing the terrace (planted on the surrounding lawn)
        for (let side = 0; side < 4; side++) {
          const n = side % 2 === 0 ? 5 : 3;
          for (let i = 0; i < n; i++) {
            const t = (i + 0.5) / n * 2 - 1;
            const [eu, ev] = side % 2 === 0 ? [t * (a.hl + m), (side === 0 ? -1 : 1) * (a.hs + m + 3.1)]
              : [(side === 1 ? -1 : 1) * (a.hl + m + 3.1), t * (a.hs + m)];
            poolTreeSpots.push([
              ob.cx + a.ax * eu + a.px * ev + (hash01(side * 7.1 + i) - 0.5) * 1.4,
              ob.cz + a.az * eu + a.pz * ev + (hash01(side * 3.3 + i + 9) - 0.5) * 1.4,
            ]);
          }
        }
      } else {
        poolParts.push({ geom: flatPoly(poly, null, LAYER.pool), color: new THREE.Color(0x3fa9c9) });
        const obC = orientedBox(poly);
        const aC = obbAxis(obC);
        const cop = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([su, sv]) => [
          obC.cx + aC.ax * su * (aC.hl + 0.9) + aC.px * sv * (aC.hs + 0.9),
          obC.cz + aC.az * su * (aC.hl + 0.9) + aC.pz * sv * (aC.hs + 0.9),
        ]);
        deckParts.push({ geom: flatPoly(cop, null, LAYER.pool - 0.015), color: new THREE.Color(0xe9e5da) });
      }
    }
    // pool water animates, so it splits from the decks and copings
    const poolWaterMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.35, metalness: 0.15, envMapIntensity: 0.7 });
    liquify(poolWaterMat, 0.055, 0.8, 2.6);
    const poolWater = new THREE.Mesh(mergeColored(poolParts), poolWaterMat);
    poolWater.receiveShadow = true;
    groupCity.add(poolWater);
    freeOnUpload(poolWater.geometry);
    const poolMesh = new THREE.Mesh(mergeColored(deckParts),
      new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.35, metalness: 0.15, envMapIntensity: 0.7 }));
    poolMesh.receiveShadow = true;
    groupCity.add(poolMesh);
    freeOnUpload(poolMesh.geometry);
  });

  step('Shaping the waterfront', () => {
    const parts = [];
    const band = (o0, o1, z0, z1) => [frontPt(o0, z0), frontPt(o1, z0), frontPt(o1, z1), frontPt(o0, z1)];
    // cap decks over the trench: slab + edge fascia + a header beam over each
    // portal face, so I-95 visibly dives UNDER the plazas instead of sliding
    // beneath a floating carpet
    const portalFace = (z, topY, dyDrop) => {
      const a = frontPt(TERRAIN.trenchW, z), b = frontPt(TERRAIN.trenchE, z);
      const arr = new Float32Array([a[0], TERRAIN.trenchFloor - 0.4, a[1], b[0], TERRAIN.trenchFloor - 0.4, b[1], b[0], topY, b[1],
                                    a[0], TERRAIN.trenchFloor - 0.4, a[1], b[0], topY, b[1], a[0], topY, a[1]]);
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(arr, 3));
      g.computeVertexNormals();
      parts.push({ geom: g, color: new THREE.Color(0x55524d), style: 3 });
      // header beam across the opening
      let hx = b[0] - a[0], hz = b[1] - a[1];
      const hl = Math.hypot(hx, hz) || 1;
      const hg = new THREE.BoxGeometry(hl + 0.8, 1.25, 0.9);
      hg.rotateY(Math.atan2(-hz, hx));
      hg.translate((a[0] + b[0]) / 2, topY - dyDrop, (a[1] + b[1]) / 2);
      parts.push({ geom: hg, color: new THREE.Color(0x6e6b64), style: 3 });
    };
    for (const c of CAPS) {
      if (c.kind !== 'deck') continue;
      const dg = flatPoly(band(TERRAIN.trenchW - 3, TERRAIN.trenchE + 3, c.z0, c.z1), null, c.dy + 0.12, true);
      const dp = dg.attributes.position;
      for (let i = 0; i < dp.count; i++) dp.setY(i, dp.getY(i) + frontDem(dp.getZ(i)));
      parts.push({ geom: dg, color: new THREE.Color(c.dy < 0 ? 0x8f8a80 : 0x9a6a52), style: 3 });
      for (const ze of [c.z0, c.z1]) {
        const deckY = frontDem(ze) + c.dy + 0.12;
        portalFace(ze, deckY + 0.02, 0.55);
      }
    }
    // the park cap swallows I-95 too: portal faces at both lawn edges
    {
      const pk = CAPS.find(c => c.kind === 'park');
      for (const ze of [pk.z0, pk.z1]) {
        const [mx] = frontPt(40, ze);
        portalFace(ze, parkCapY(mx, ze) + 0.1, 0.6);
      }
    }
    // Park at Penn's Landing: lawn from Front St down to the promenade
    const park = CAPS.find(c => c.kind === 'park');
    {
      const poly = [frontPt(TERRAIN.trenchW - 3, park.z0), [xShore(park.z0) - 12, park.z0], [xShore(park.z1) - 12, park.z1], frontPt(TERRAIN.trenchW - 3, park.z1)];
      parts.push({ geom: drapedPoly(poly, LAYER.park, 12), color: new THREE.Color(COLORS.park), style: 3 });
      for (let i = 0; i < 70; i++) {
        const z = lerp(park.z0 + 8, park.z1 - 8, hash01(i * 2.3 + 9));
        const [xf] = frontPt(TERRAIN.trenchW + 8, z);
        extraTreeSpots.push([lerp(xf, xShore(z) - 26, hash01(i * 1.7 + 3)), z]);
      }
    }
    // riverfront promenade just inside the bulkhead
    {
      const inner = [], outer = [];
      for (let z = -1100; z <= 1700; z += 10) { inner.push([xShore(z) - 11, z]); outer.push([xShore(z) - 0.6, z]); }
      parts.push({ geom: flatPoly(inner.concat(outer.reverse()), null, 0.3), color: new THREE.Color(0xa9a49a), style: 3 });
    }
    // DoubleSide: the cap decks must read from BELOW too (driving the trench)
    const m = new THREE.Mesh(mergeColored(parts), surfMat({ vertexColors: true, roughness: 0.95, side: THREE.DoubleSide }));
    m.receiveShadow = true;
    groupCity.add(m);
    freeOnUpload(m.geometry);
  });

  step('Paving the streets', () => {
    const asphaltParts = [], brickParts = [];
    const cBrickWalk = new THREE.Color(COLORS.footway);
    const cConcWalk = new THREE.Color(0x9b968a);
    // with the outer districts loaded, core streets stop at the core boundary (the wide set draws the rest)
    const haveWide = typeof WIDE_B64 !== 'undefined' && !!WIDE_B64;
    const M = 40;
    const insideM = (q) => q[0] >= CORE_EXT.x0 - M && q[0] <= CORE_EXT.x1 + M && q[1] >= CORE_EXT.z0 - M && q[1] <= CORE_EXT.z1 + M;
    const runsOf = (pts) => {
      if (!haveWide) return [pts];
      const runs = []; let cur = [];
      for (let i = 0; i < pts.length; i++) {
        const keep = insideM(pts[i]) || (i > 0 && insideM(pts[i - 1])) || (i + 1 < pts.length && insideM(pts[i + 1]));
        if (keep) cur.push(pts[i]); else { if (cur.length > 1) runs.push(cur); cur = []; }
      }
      if (cur.length > 1) runs.push(cur);
      return runs;
    };
    // I-95 itself runs DOWN in the trench (cross streets bridge over it); without
    // this its lanes float at city level and the dark trench floor shows between
    // them as glitchy patches from above
    const motY = (x, z) => {
      // band edges must match siteY's trench band exactly, and blend down over a ramp
      // length (a binary band left 7 m vertex spikes where densified points straddled it);
      // beyond the trench mesh's z-extent the lanes climb back to grade
      const o = frontOff(x, z);
      const base = siteY(x, z, 'road');
      if (o <= TERRAIN.trenchW || o >= TERRAIN.trenchE) return base;
      const eo = Math.min(o - TERRAIN.trenchW, TERRAIN.trenchE - o) / 14;
      const ez = Math.min(z - (CORE_EXT.z0 + 4), (CORE_EXT.z1 - 4) - z) / 60;
      const t = clamp(Math.min(eo, ez), 0, 1);
      const ts = t * t * (3 - 2 * t);
      return lerp(base, TERRAIN.trenchFloor + 0.55, ts);
    };
    for (const r of D.roads) {
      if (r.pts.length < 2) continue;
      if (/Delancey|Cypress|American|Philip|Stamper|Addison|Panama|Peter's Way|Naudain|Kenilworth/i.test(r.name || '')) r.w = Math.min(r.w, 6);
      const foot = /footway|path|steps|pedestrian|cycleway/.test(r.t);
      const mot = /motorway/.test(r.t);
      const y = foot ? LAYER.footway : LAYER.road;
      const setts = /Dock Street/i.test(r.name || '') || (/2nd Street/i.test(r.name || '') && r.pts[0][1] > 250 && r.pts[0][1] < 420);
      // lane class for the paint: divided (no centre yellow) on the highways and their links,
      // no markings on service and pedestrian ways; the brick parts never carry the attribute
      const lane = foot ? null : { cls: /^(motorway|trunk)(_link)?$|^primary_link$/.test(r.t) ? 1 : (/footway|path|steps|cycleway|pedestrian|service|living_street/.test(r.t) ? 2 : 0) };
      for (const run of runsOf(r.pts)) {
        const g = ribbon(run, r.w, y, mot ? motY : null, lane);
        if (!/footway|path|steps|cycleway/.test(r.t)) {
          for (let i = 0; i < run.length - 1; i++) {
            addRoadSeg(run[i][0], run[i][1], run[i + 1][0], run[i + 1][1], r.w / 2);
            if (!/pedestrian/.test(r.t)) septaRoadAdd(run[i][0], run[i][1], run[i + 1][0], run[i + 1][1]);
          }
        }
        (foot ? brickParts : asphaltParts).push({ geom: g, color: new THREE.Color(foot ? COLORS.footway : (setts ? 0x4d4a46 : COLORS.asphalt)) });
        // sidewalks flanking real streets: brick in the rowhouse core, concrete on arterials
        if (/^(residential|tertiary|living_street|unclassified|secondary|primary)$/.test(r.t)) {
          const walkCol = /residential|tertiary|living_street/.test(r.t) ? cBrickWalk : cConcWalk;
          const off = r.w / 2 + 1.55;
          for (const s of [-1, 1]) brickParts.push({ geom: ribbon(offsetPolyline(run, off * s), 3.0, LAYER.sidewalk), color: walkCol });
        }
      }
    }
    const asphalt = new THREE.Mesh(
      mergeColored(asphaltParts),
      roadMat({ vertexColors: true, roughness: 0.95 })
    );
    asphalt.receiveShadow = true;
    groupCity.add(asphalt);
    freeOnUpload(asphalt.geometry);
    const brick = new THREE.Mesh(
      mergeColored(brickParts),
      new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.9 })
    );
    brick.receiveShadow = true;
    groupCity.add(brick);
    freeOnUpload(brick.geometry);
  });

  step('Planting parks and piers', () => {
    const parkParts = [], pierParts = [];
    for (const a of D.areas || []) {
      if (a.poly.length < 3) continue;
      if (a.kind === 'park') {
        const shade = lerp(1 - PARK_SHADE_SPREAD, 1 + PARK_SHADE_SPREAD, hash01(a.poly[0][0]));
        const c = new THREE.Color(COLORS.park).multiplyScalar(shade);
        const pa = Math.abs(signedArea(a.poly));
        GRASS_POLYS.push(a.poly);
        parkParts.push({ geom: pa > 700 ? drapedPoly(a.poly, LAYER.park, 10) : flatPoly(a.poly, null, LAYER.park), color: c });
      } else if (a.kind === 'pier') {
        const [pcx, pcz] = polyCentroid(a.poly);
        const pg = extrudePoly(a.poly, null, 1.4, 0);
        pg.translate(0, siteY(pcx, pcz, 'ground'), 0);
        pierParts.push({ geom: pg, color: new THREE.Color(COLORS.pier) });
      }
    }
    if (parkParts.length) {
      const parks = new THREE.Mesh(
        mergeColored(parkParts),
        surfMat({ vertexColors: true, roughness: 1 })
      );
      parks.receiveShadow = true;
      groupCity.add(parks);
      freeOnUpload(parks.geometry);
    }
    if (pierParts.length) {
      const piers = new THREE.Mesh(
        mergeColored(pierParts),
        new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.9 })
      );
      piers.castShadow = piers.receiveShadow = true;
      groupCity.add(piers);
      freeOnUpload(piers.geometry);
    }
  });

  // ------------------------------------------------ the city fabric
  const buildingPalette = {
    worship: [0xccb595, 0xb39b7d],
    church: [0xccb595, 0xb39b7d],
    school: [0xc0a888, 0xc9b191],
    civic: [0xc0a888, 0xc9b191],
    garage: [0x9d917e, 0xa99d85],
    parking: [0x9d917e, 0xa99d85],
    retail: [0xb3a491, 0xc0af98],
    commercial: [0xb3a491, 0xa39481],
    office: [0xb3a491, 0xa39481],
    hotel: [0xbaa891, 0xc9b59c],
    brick: [0xb16246, 0xa35843, 0xbc7452, 0x8e513d, 0xa95940, 0xb6684b],
    painted: [0xd2b79b, 0xdfc4a3, 0xbea88d],
  };
  const highrisePool = [0x8f8d84, 0x9aa0a4, 0xb3aca0, 0x83817c, 0xa39d92];
  // ---- Tier-1 facade attributes: OPA parcel classes + sampled roof palette ----
  // stored -> rendered on sunlit tops measured as R = 31.5 * S^0.423 (legacy-linear
  // lift + ACES compress darks far more than lights); invert per channel so the
  // rendered roof matches the ortho-sampled sRGB. Calibrated by canvas-pixel probe.
  const roofInv = (t) => Math.min(1, Math.pow(Math.max(t, 4) / 31.5, 2.364) / 255);
  const ROOF_PAL = (typeof FACADE_PAL !== 'undefined' && FACADE_PAL && FACADE_PAL.roof)
    ? FACADE_PAL.roof.map(cc => new THREE.Color(roofInv(cc[0]), roofInv(cc[1]), roofInv(cc[2]))) : null;
  const OPA_POOLS = {
    masOld: [0xa35843, 0xb16246, 0x8e513d, 0xa95940, 0x995742, 0xb6684b],
    mas1900: [0xb16246, 0xbc7452, 0xb07559, 0xa16248, 0xab644a],
    masPost: [0xbc7452, 0xc9855c, 0xb08567, 0xc09676, 0xa1907e],
    masMod: [0x9d684e, 0xb2947a, 0xc09f78, 0xa1968d],
    frame: [0xd2b79b, 0xdfc4a3, 0xc0b39b, 0xb0ae96, 0xc9c4b5, 0xdbcdb7],
    stone: [0x9d8e7a, 0x8c7d6a, 0xa99982, 0x7d7161],
    mixed: [0xb3a491, 0xb07559, 0xa39481, 0xc0a88d],
    com: [0xb3a491, 0xa39481, 0xc0af98, 0x958d82],
    ind: [0x9d8978, 0x8c7d70, 0xb29f8d, 0xa2624c],
  };
  // fa = [use, mat, era, stories] -> wall color pool (null = keep the type logic)
  function opaWallPool(fa) {
    const u = fa[0], m = fa[1], e = fa[2];
    if (u === 5) return OPA_POOLS.ind;
    if (u === 4 && m !== 0) return OPA_POOLS.com;
    if (m === 1) return OPA_POOLS.frame;
    if (m === 2) return OPA_POOLS.stone;
    if (m === 3) return OPA_POOLS.mixed;
    if (m === 0) return e <= 2 ? OPA_POOLS.masOld : e === 3 ? OPA_POOLS.mas1900
      : e === 4 ? OPA_POOLS.masPost : e >= 8 ? OPA_POOLS.mas1900 : OPA_POOLS.masMod;
    return null;
  }
  // the facade vocabulary (aStyle): 0 Georgian row, 1 church, 2 curtain grid, 3 blank,
  // 4 civic arches, 5 storefront, 6 loft with storefront, 7 ribbon, 8 post-war row,
  // 9 Victorian row (arched heads, cornice), 10 porch front, 11 siding or formstone,
  // 12 industrial loft, 13 new construction, 14 stone piers, 15 horizontal bands,
  // 16 precast grid, 17 pre-war stone, 18 residential slab; plus 32 x variant (bit 0
  // dark trim, bit 1 tall sashes). fa = OPA [use, mat, era, stories] or null, t the
  // packed type code (1 house, 2 apartments, 3 commercial, 4 industrial), hint the
  // Mapillary byte (trim class in bits 0-1, window class in bits 2-3, 0 unknown)
  function fabricStyle(fa, h, t, area, seed, hint) {
    const hs = hash01(seed * 4.71 + 0.3), hv = hash01(seed * 9.13 + 0.8);
    const u = fa ? fa[0] : -1, e = fa ? fa[2] : 8;
    const trim = hint ? hint & 3 : 0, wins = hint ? (hint >> 2) & 3 : 0;
    let st;
    if (u === 5 || t === 4) st = h >= 7 ? 12 : 8;
    else if (u === 3 || u === 4 || t === 3) st = h > 16 ? (e >= 6 ? 13 : 2) : (area > 400 && h > 10 ? 6 : 5);
    else if (e <= 2) st = hs < 0.55 ? 0 : 9;
    else if (e === 3) st = (t === 1 && area >= 120 && area <= 420 && h <= 13 && hs < 0.75) ? 10 : (hs < 0.55 ? 9 : 0);
    else if (e === 4 || e === 5) st = hs < 0.28 ? 11 : 8;
    else if (e === 6 || e === 7) st = hs < 0.7 ? 13 : 8;
    else st = hs < 0.42 ? 0 : hs < 0.66 ? 9 : hs < 0.84 ? 8 : 11;
    // the imagery: a face that reads light (white trim, formstone, siding, paint) wears the
    // siding style where it would have been a plain row, a face with little light trim
    // keeps its brick, and a dark-glazed face of the last thirty years is new work
    if (trim === 3 && (st === 0 || st === 8) && hv < 0.75) st = 11;
    if (trim === 2 && st === 0 && hv < 0.5) st = 9;   // brick with white cornices and trim
    if (trim === 1 && st === 11) st = 8;
    if (wins === 3 && e >= 6 && (st === 8 || st === 0)) st = 13;
    const variant = ((trim >= 2) ? 0 : (hv < 0.35 || trim === 1) ? 1 : 0) + ((e <= 3 && hash01(seed * 2.2 + 0.1) < 0.5) ? 2 : 0);
    return st + 32 * variant;
  }
  // a tower's facade when no researched spec names it: the OPA era, else the type and a draw
  function towerStyle(fa, t, seed) {
    const e = fa ? fa[2] : 8, hs = hash01(seed * 6.37 + 0.2);
    if (t === 2 && e >= 4) return 18;
    if (e <= 3) return 17;
    if (e === 4 || e === 5) return hs < 0.7 ? 16 : 2;
    if (e === 6 || e === 7) return hs < 0.5 ? 15 : 2;
    return hs < 0.4 ? 2 : hs < 0.7 ? 16 : 18;
  }
  // a researched tower's photographed hex into the stored register: linear, lifted less than a
  // rowhouse wall and with its chroma pulled in (the granite photos are sunlit and contrasty;
  // the same transfer that suits a shaded rowhouse turned Three Logan Square orange)
  const towerInv = (sr, sg, sb) => {
    let r = Math.pow(sr / 255, 2.2), g = Math.pow(sg / 255, 2.2), b = Math.pow(sb / 255, 2.2);
    const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
    const lift = Math.pow(Math.max(lum, 0.01), 0.8), gain = lift / Math.max(lum, 1e-4);
    r = lift + (r * gain - lift) * 0.62; g = lift + (g * gain - lift) * 0.62; b = lift + (b * gain - lift) * 0.62;
    return new THREE.Color(Math.min(1, Math.max(0, r)), Math.min(1, Math.max(0, g)), Math.min(1, Math.max(0, b)));
  };
  const CROWN_CUTS = { pyramid: 1, lattice: 1, ziggurat: 1, lantern: 1, mansard: 1, dome: 1, sloped: 1, notch: 1 };
  const TOWER_STYLE = { glass: 20, glass_bands: 21, glass_dark: 22, concrete_grid: 16, stone_piers: 14, deco: 17, precast_bands: 18, brick: 2 };
  // the researched Center City towers (towers.json): nearest spec within its radius
  const TOWER_SPECS = (typeof TOWERS !== 'undefined' && TOWERS && TOWERS.towers) ? TOWERS.towers : [];
  const towerGrid = new Map();
  for (const sp of TOWER_SPECS) { const kx = Math.floor(sp.x / 100), kz = Math.floor(sp.z / 100); for (let a = -1; a <= 1; a++) for (let b2 = -1; b2 <= 1; b2++) { const key = (kx + a) + ',' + (kz + b2); if (!towerGrid.has(key)) towerGrid.set(key, []); towerGrid.get(key).push(sp); } }
  function towerAt(x, z) {
    const lst = towerGrid.get(Math.floor(x / 100) + ',' + Math.floor(z / 100));
    if (!lst) return null;
    let best = null, bd = 1e9;
    for (const sp of lst) { const d = Math.hypot(sp.x - x, sp.z - z); if (d < (sp.r || 35) && d < bd) { bd = d; best = sp; } }
    return best;
  }
  function buildingColor(b, i) {
    const h = hash01(i * 7.13);
    let pool;
    const t = b.t || 'generic';
    // modern high-rises read as curtain wall / precast, never rowhouse brick
    if (b.h > 35 && t !== 'church' && t !== 'worship') pool = highrisePool;
    else if (b.fa && t !== 'church' && t !== 'worship' && t !== 'school' && t !== 'civic') pool = opaWallPool(b.fa);
    if (!pool) {
    if (buildingPalette[t]) pool = buildingPalette[t];
    else if (t === 'house' || t === 'residential' || t === 'terrace' || t === 'apartments' || t === 'detached' || t === 'semidetached_house')
      pool = h < 0.14 ? buildingPalette.painted : buildingPalette.brick;
    else if (t === 'generic') {
      const area = Math.abs(signedArea(b.poly));
      pool = area < 350 ? (h < 0.16 ? buildingPalette.painted : buildingPalette.brick) : buildingPalette.commercial;
    } else pool = buildingPalette.commercial;
    }
    const base = new THREE.Color(pool[Math.floor(hash01(i * 3.7) * pool.length) % pool.length]);
    const l = 0.92 + hash01(i * 11.3) * 0.16;
    return base.multiplyScalar(l);
  }

  // buildings with researched custom models skip the generic extruder;
  // 'recolor' specs keep generic geometry with corrected colors/heights
  const REALISM = {
    'The Ryland': { mode: 'custom' },
    'Philadelphia Marriott Old City': { mode: 'custom' },
    'Head House': { mode: 'custom' },
    'Head House Market': { mode: 'custom', open: true },
    "Merchants' Exchange Building": { mode: 'custom' },
    'City Tavern': { mode: 'custom' },
    'Hill-Physick House': { mode: 'custom' },
    'Powel House': { mode: 'custom' },
    'Man Full of Troubles Tavern': { mode: 'custom' },
    "Saint Peter's Church": { mode: 'custom' },
    'Old Pine Street Church': { mode: 'custom' },
    'Mother Bethel African Methodist Episcopal Church': { mode: 'custom' },
    "Old Saint Mary's Church": { mode: 'custom' },
    "Old Saint Joseph's Church": { mode: 'custom' },
    "Old Saint Paul's Church": { mode: 'custom' },
    'Independence Seaport Museum': { mode: 'custom' },
    'Society Hill Synagogue': { mode: 'recolor', color: 0xd2d4d0 },
    'Athenaeum of Philadelphia': { mode: 'recolor', color: 0x7b5844 },
    'Hopkinson House': { mode: 'recolor', color: 0xcfc0a4, h: 92, style: 7 },
    'One Independence Place': { mode: 'recolor', color: 0x5d4536 },
    '2 Independence Place': { mode: 'recolor', color: 0x5d4536 },
    'United States Custom House': { mode: 'custom' },
    'Man Full of Troubles Tavern': { mode: 'custom' },
    "Hilton Philadelphia at Penn's Landing": { mode: 'custom' },
    'Independence Hall': { mode: 'custom' },
    'Congress Hall': { mode: 'custom' },
    'Old City Hall': { mode: 'custom' },
    "Carpenters' Hall": { mode: 'custom' },
    'Second Bank of the United States': { mode: 'custom' },
    'First Bank of the United States': { mode: 'custom' },
    'New Market Garage': { mode: 'custom', key: 'garage' },
    'Penn Mutual Tower': { mode: 'recolor', color: 0x8f8b82 },
    'The Residences at Dockside': { mode: 'custom' },
    'The Moravian': { mode: 'recolor', color: 0x8f4a3a },
    '101 Walnut': { mode: 'recolor', color: 0x96513f },
    'Public Ledger Building': { mode: 'recolor', color: 0x8e4438 },
    'The Curtis Center': { mode: 'recolor', color: 0x8a4034 },
  };
  const upgraded = new Map(); // building object -> realism spec

  step('Raising 2,800 buildings', () => {
    // unnamed footprints identified by location (Philadelphia OPA parcels + 2017 LiDAR)
    const REALISM_NEAR = [
      { x: -140, z: 433, r: 60, minArea: 3000, spec: { mode: 'custom', key: 'abbotts' } },   // Abbotts Square
      { x: 44, z: 334, r: 30, minArea: 1500, spec: { mode: 'custom', key: 'ten410' } },      // 410 at Society Hill
      { x: -18, z: 345, r: 25, minArea: 900, spec: { mode: 'custom', key: 'newmarket' } },   // New Market Complex
      // Glory Beer Bar & Kitchen, 126 Chestnut — MID-BLOCK between Front and 2nd
      // (numbers ascend westward from Front): the deep narrow lot whose front
      // hits the address line, area-weighted centroid (115.1, -283.8)
      { x: 115.1, z: -283.8, r: 5, minArea: 100, spec: { mode: 'custom', key: 'glory' } },
      // Rotten Ralph's, 201 Chestnut — NW corner of 2nd & Chestnut. OSM maps the
      // lot as two shallow strips front-to-back; both go custom and the builder
      // spans them with one massing. The taller rear mass (the graffiti party
      // wall in photos) stays generic but recolored to its real dark brick.
      { x: 43.5, z: -334.3, r: 4, minArea: 40, spec: { mode: 'custom', key: 'ralphs' } },
      { x: 44.4, z: -339.1, r: 4, minArea: 40, spec: { mode: 'custom', key: 'ralphsMid' } },
      { x: 45.6, z: -346.8, r: 4, minArea: 100, spec: { color: '#452a20', style: 3 } },
    ];
    for (const b of D.buildings) {
      if (b.name && REALISM[b.name]) { upgraded.set(b, REALISM[b.name]); continue; }
      if (!b.name && b.poly && b.poly.length >= 3) {
        const [cx, cz] = polyCentroid(b.poly);
        const ar = Math.abs(signedArea(b.poly));
        for (const nr of REALISM_NEAR) {
          if (ar >= nr.minArea && Math.hypot(cx - nr.x, cz - nr.z) < nr.r) { upgraded.set(b, nr.spec); break; }
        }
      }
    }
    const parts = [];
    const roofPalette = [0x45423e, 0x3a3835, 0x54504a, 0x6b4a3d, 0x5d5952];
    for (let i = 0; i < D.buildings.length; i++) {
      const b = D.buildings[i];
      if (!b.poly || b.poly.length < 3) continue;
      if (b.t === 'ship') continue; // hulls are built in their own step
      const p0 = parts.length;
      const spec0 = upgraded.get(b);
      if (spec0 && spec0.mode === 'custom') {
        registerPoly(b.poly); // keeps trees out of the footprint
        if (!spec0.open) {    // open structures (market sheds) stay walkable
          for (let k = 0; k < b.poly.length; k++) {
            const p = b.poly[k], q = b.poly[(k + 1) % b.poly.length];
            addColSeg(p[0], p[1], q[0], q[1]);
          }
        }
        continue;
      }
      if (spec0 && spec0.h) b.h = spec0.h;
      if (b.h >= 45 && b.poly && b.poly.length >= 3 && !b.minH) {
        const [tgx, tgz] = polyCentroid(b.poly);
        tallGlow.push({ x: tgx, z: tgz, b: siteY(tgx, tgz, 'ground'), h: b.h, poly: b.poly });
      }
      const color = spec0 && spec0.color ? new THREE.Color(spec0.color) : buildingColor(b, i);
      const t = b.t || 'generic';
      const area = Math.abs(signedArea(b.poly));
      // paper-thin OSM slivers (party walls and alley strips mapped as buildings)
      // extrude into tall floating blades that read as broken roofs — clamp
      // anything with an effective width under ~1.7 m down to garden-wall height
      if (!b.minH && b.h > 4) {
        let perim = 0;
        for (let k2 = 0; k2 < b.poly.length; k2++) {
          const p2 = b.poly[k2], q2 = b.poly[(k2 + 1) % b.poly.length];
          perim += Math.hypot(q2[0] - p2[0], q2[1] - p2[1]);
        }
        if ((2 * area) / Math.max(1, perim) < 1.7) b.h = 3.2;
      }
      // facade vocabulary: 0 Georgian rowhouse, 1 church, 2 modern slab, 3 blank, 4 civic arched base, 5 storefront
      const tCode = (t === 'retail' || t === 'commercial' || t === 'hotel' || t === 'office') ? 3 : (t === 'industrial' || t === 'warehouse') ? 4 : t === 'apartments' ? 2 : 1;
      const style = spec0 && spec0.style != null ? spec0.style
        : (t === 'garage' || t === 'parking') ? 2
        : (t === 'church' || t === 'worship') ? 1
        : (t === 'school' || t === 'civic' || t === 'hospital' || t === 'university') ? (b.h > 16 ? 2 : 4)
        : b.h > 35 ? towerStyle(b.fa, tCode, i)
        : fabricStyle(b.fa, b.h, tCode, Math.abs(signedArea(b.poly)), i, 0);
      const trimCol = hash01(i * 2.9) < 0.62 ? new THREE.Color(0xe9e3d3) : new THREE.Color(0x3d3935);
      // roof source: LiDAR-measured form when the 2022 flight resolved one
      // (b.roof = [form, eave, ridge, ridgeRad] from lidar_core.py, form
      // 1 gable / 2 hip, [0] = measured flat — which stays flat, no lottery),
      // else the original hash-lottery guess for plausible rowhouse quads
      let quad = null;
      const mr = Array.isArray(b.roof) && !(spec0 && spec0.h) ? b.roof : null;
      const mForm = mr ? mr[0] : -1;
      const resType = ['house', 'residential', 'terrace', 'apartments', 'detached', 'semidetached_house', 'generic'].includes(t);
      // guessed gables only at true rowhouse height — 14-15 m four-story commercial
      // lofts (Old City, Chestnut St) are flat-roofed, and their long strips gabled
      // into edge-on "blade" slopes towering over the streetwall
      const wantPitch = mr ? (mForm === 1 || mForm === 2) && mr[2] - mr[1] >= 0.8
        : (resType && area < 280 && b.h < 12.5 && hash01(i * 13.7) < 0.8);
      if (wantPitch && !b.minH && (!b.holes || !b.holes.length) && area < (mr ? 650 : 280) && b.poly.length <= (mr ? 10 : 8)) {
        const sp = simplifyRing(b.poly, 0.45);
        if (sp.length === 4) {
          // gables demand an honest rowhouse quad: convex, near-rectangular
          // corners, clearly elongated, and covering the same area as the real
          // footprint. Skewed diamonds tent into leaning pyramids, squarish
          // quads read as spikes, and chopped outlines hang their roof past
          // the walls — all of Mike's "broken roofs". Anything dodgy stays a
          // flat extrusion of the TRUE footprint.
          let convex = true, sgn = 0, rect = true;
          for (let k2 = 0; k2 < 4; k2++) {
            const A2 = sp[k2], B2 = sp[(k2 + 1) % 4], C2 = sp[(k2 + 2) % 4];
            const ux2 = B2[0] - A2[0], uz2 = B2[1] - A2[1], vx2 = C2[0] - B2[0], vz2 = C2[1] - B2[1];
            const cr = ux2 * vz2 - uz2 * vx2;
            if (Math.abs(cr) > 1e-6) {
              if (sgn === 0) sgn = Math.sign(cr);
              else if (Math.sign(cr) !== sgn) { convex = false; break; }
            }
            const l1 = Math.hypot(ux2, uz2) || 1, l2 = Math.hypot(vx2, vz2) || 1;
            if (Math.abs((ux2 * vx2 + uz2 * vz2) / (l1 * l2)) > 0.35) rect = false;
          }
          const e = [0, 1, 2, 3].map(k => Math.hypot(sp[(k + 1) % 4][0] - sp[k][0], sp[(k + 1) % 4][1] - sp[k][1]));
          const span = Math.min((e[0] + e[2]) / 2, (e[1] + e[3]) / 2);
          const long = Math.max((e[0] + e[2]) / 2, (e[1] + e[3]) / 2);
          const aQ = Math.abs(signedArea(sp));
          const elMin = mForm === 2 ? 1.02 : (mr ? 1.2 : 1.35);
          if (convex && rect && Math.abs(aQ - area) <= area * 0.14 &&
            span > 3.2 && span < (mr ? 17 : 13) && long / span >= elMin && long / span < 5) quad = sp;
        }
      }
      // measured floor pitch: OPA stories against the LiDAR height (eave for pitched)
      let flhV = 0;
      if (b.fa && b.fa[3]) {
        const hEff = mr && mForm > 0 ? mr[1] : b.h;
        const r2 = hEff / b.fa[3];
        if (r2 >= 2.2 && r2 <= 5.2) flhV = Math.min(4.6, r2);
      }
      try {
        if (quad) {
          let eaveH, ridgeTop, rrad = null;
          if (mr) {
            eaveH = Math.max(2.6, mr[1]); ridgeTop = mr[2]; rrad = mr[3];
            if (ridgeTop - eaveH < 0.8) eaveH = Math.max(2.2, ridgeTop - 0.8);
          } else {
            const e = [0, 1, 2, 3].map(k => Math.hypot(quad[(k + 1) % 4][0] - quad[k][0], quad[(k + 1) % 4][1] - quad[k][1]));
            const span = Math.min((e[0] + e[2]) / 2, (e[1] + e[3]) / 2);
            let rise = clamp(span * 0.42, 1.4, 3.6);
            if (b.h - rise < 3.4) rise = Math.max(1.2, b.h - 3.4);
            eaveH = b.h - rise; ridgeTop = b.h + 0.05;
          }
          parts.push({ geom: buildingGeom(quad, null, eaveH, -1.5), color, style, flh: flhV });
          const roofCol = (b.rp != null && ROOF_PAL)
            ? ROOF_PAL[b.rp].clone().multiplyScalar(0.92 + hash01(i * 8.9) * 0.18)
            : new THREE.Color(roofPalette[Math.floor(hash01(i * 3.1) * roofPalette.length) % roofPalette.length])
              .multiplyScalar(0.9 + hash01(i * 8.9) * 0.25);
          const g = mForm === 2 ? quadHip(quad, eaveH, ridgeTop, rrad) : quadGable(quad, eaveH, ridgeTop, rrad);
          parts.push({ geom: g.slopes, color: roofCol, style: 3 });
          if (g.ends) parts.push({ geom: g.ends, color, style, flh: flhV });
          // eave boards laid exactly along the wall's eave edges
          for (const ev of g.eaves) {
            const exd = ev.b[0] - ev.a[0], ezd = ev.b[1] - ev.a[1];
            parts.push({
              geom: box(ev.len + 0.1, 0.36, 0.5,
                (ev.a[0] + ev.b[0]) / 2, eaveH - 0.1, (ev.a[1] + ev.b[1]) / 2,
                Math.atan2(-ezd, exd)),
              color: trimCol, style: 3,
            });
          }
          const nCh = hash01(i * 5.3) < 0.72 ? (hash01(i * 7.9) < 0.4 ? 2 : 1) : 0;
          const chH = Math.min(ridgeTop - eaveH, 3.8) + 1.7;
          const rl = Math.hypot(g.ridge[1][0] - g.ridge[0][0], g.ridge[1][1] - g.ridge[0][1]) || 1;
          const rdx = (g.ridge[1][0] - g.ridge[0][0]) / rl, rdz = (g.ridge[1][1] - g.ridge[0][1]) / rl;
          for (let c = 0; c < nCh; c++) {
            const rp = c === 0 ? g.ridge[0] : g.ridge[1];
            const s = c === 0 ? 1 : -1;
            parts.push({
              geom: box(0.95, chH, 0.55,
                rp[0] + rdx * s * 1.0, eaveH + chH / 2, rp[1] + rdz * s * 1.0,
                Math.atan2(-rdz, rdx)),
              color: new THREE.Color(0x6a4132).multiplyScalar(0.88 + hash01(i * 11.7) * 0.22),
            });
          }
        } else {
          // a measured pitched roof whose footprint failed the honest-quad guards
          // drops to a flat extrusion at the roof's mean surface height — never a
          // floating slope (the session's roof rule)
          const hFlat = (mr && mForm > 0) ? Math.max(3, mr[1] + 0.35 * (mr[2] - mr[1])) : b.h;
          parts.push({ geom: buildingGeom(b.poly, b.holes, hFlat, b.minH ? b.minH : -1.5), color, style, flh: flhV });
          // sampled roof color as a thin overlay cap. It must clear the cornice
          // SLAB (a solid extrusion to hFlat+0.06 whose cream top used to play
          // "roof" on every rowhouse) - 9 cm up, deterministic, never coplanar;
          // the slab edge below reads as the cornice lip.
          if (b.rp != null && ROOF_PAL && !b.minH) {
            try {
              parts.push({ geom: capGeom(b.poly, b.holes, hFlat + 0.09),
                color: ROOF_PAL[b.rp].clone().multiplyScalar(0.94 + hash01(i * 8.9) * 0.14), style: 3 });
            } catch (e2) {}
          }
          // flat-roofed rowhouses get a projecting cornice ring at the parapet
          if (resType && !b.minH && (!b.holes || !b.holes.length) && area < 320 && hFlat < 18 && b.poly.length <= 10) {
            const [ccx, ccz] = polyCentroid(b.poly);
            const ring = b.poly.map(pt => {
              const dx = pt[0] - ccx, dz = pt[1] - ccz, L = Math.hypot(dx, dz) || 1;
              return [pt[0] + (dx / L) * 0.3, pt[1] + (dz / L) * 0.3];
            });
            parts.push({ geom: extrudePoly(ring, null, hFlat + 0.06, hFlat - 0.42), color: trimCol, style: 3 });
          }
        }
      } catch (e) { continue; }
      {
        const [lx, lz] = polyCentroid(b.poly);
        const ty = siteY(lx, lz, 'ground');
        if (ty) for (let k = p0; k < parts.length; k++) { parts[k].geom.translate(0, ty, 0); parts[k].baseY = ty; }
      }
      registerPoly(b.poly);
      for (let k = 0; k < b.poly.length; k++) {
        const p = b.poly[k], q = b.poly[(k + 1) % b.poly.length];
        addColSeg(p[0], p[1], q[0], q[1]);
      }
    }
    const mesh = new THREE.Mesh(mergeColored(parts, true, true), coreMat);
    mesh.castShadow = mesh.receiveShadow = true;
    groupCity.add(mesh);
    rayTargets.push(mesh);
  });

  // procedural windows: world-space grid darkening on wall faces only
  // (shared by the generic fabric and landmark walls)
  const nightUniform = { value: 0 };
  // how far the facade detail (windows, and with them the lit windows at night) survives:
  // < 1 stretches the fade, so a phone at 1266 x 585 keeps its lit windows to about the
  // distance a 1080p desktop does instead of losing them at half of it. The masks stay
  // anti-aliased by the true pixel footprint, so past the natural range the windows soften
  // into dots rather than shimmer
  const detFarUniform = { value: isTouch ? 0.55 : 1.0 };
  let towerGlassMat = null, towerVarMat = null, rylandGlassMat = null, outerGlassMat = null;
  const groundMats = [];   // the bare-earth materials (groundSurfMat): the meadow shader forced green, never retinted
  // the fabric's overall brightness, one number: with the meadow and the water at the game's
  // depth the pale walls read washed out beside them (Mike), so every wall and roof on the
  // fabric material (all three tiers) takes this gain at the top of the facade shader; the lit
  // windows are an emissive term and keep their night glow
  // The numbers are small because of the tone curve: a sunlit wall sits near 1.5 in linear light
  // and a noon roof near 1.9, deep in the ACES shoulder, where a 0.55 gain moved the display
  // under a tenth; these bring the walls to about 150 to 180 displayed and the roofs a step
  // under them (a noon roof at 0.14 reads about 140), the game's mid tones beside its meadow
  const FACADE_GAIN = 0.22, ROOF_GAIN = 0.14;
  // the core's own pair: Society Hill's brick palette and sampled roofs sit a fifth darker and
  // redder than the outer districts' photo-sampled walls, and at one gain the core stood out as a
  // dark block from any height (Mike: jarring), so it takes a higher gain and a milder saturation
  // boost (1.0 against the tiers' 1.2) on a material of its own
  const CORE_FACADE_GAIN = 0.42, CORE_ROOF_GAIN = 0.28;
  const cityMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.92, metalness: 0, envMapIntensity: 0.9, dithering: MAT_DITHER });
  let coreMat = null;   // the core's fabric: the same shader at the core's gains (set with the hook below)
  {
    const facadeHook = (gW, gR, sat) => (shader) => {
      shader.uniforms.uSunW = sunWUniform;
      shader.uniforms.uNight = nightUniform;
      shader.uniforms.uDetFar = detFarUniform;
      cityMat.userData.shader = shader;
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nattribute float aStyle; attribute float aFloorH; attribute float aWallU; attribute float aWallL; attribute float aWallH; attribute float aBase;\nvarying vec3 vWPos; varying vec3 vWNorm; varying float vStyle; varying float vFloorH; varying float vWallU; varying float vWallL; varying float vWallH; varying float vBase;')
        .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;\nvWNorm = normalize(mat3(modelMatrix) * objectNormal);\nvStyle = aStyle; vFloorH = aFloorH; vWallU = aWallU; vWallL = aWallL; vWallH = aWallH; vBase = aBase;');
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', [
          '#include <common>',
          'uniform float uNight;',
          'uniform float uDetFar;',
          'varying vec3 vWPos; varying vec3 vWNorm; varying float vStyle; varying float vFloorH; varying float vWallU; varying float vWallL; varying float vWallH; varying float vBase;',
          'float shtLit = 0.0;',
          'float shtGlass = 0.0;',
          'uniform vec3 uSunW;',
          // a window's reveal: the jamb on the sun's side and the head throw a shadow onto the
          // glass beside them, deeper the higher the sun and the more the wall faces it, plus a
          // faint ambient rim; returns the darkening for a window rect centred c of size sz
          'float revealShade(vec2 m, vec2 c, vec2 sz, float mask, float sunT, float sunE, float sunN) {',
          '  float sgn = sunT >= 0.0 ? 1.0 : -1.0;',
          '  float dEdge = sz.x * 0.5 - sgn * (m.x - c.x);',
          '  float dHead = (c.y + sz.y * 0.5) - m.y;',
          '  float jam = 1.0 - smoothstep(0.0, 0.06 + 0.3 * abs(sunT), dEdge);',
          '  float head = 1.0 - smoothstep(0.0, 0.08 + 0.34 * sunE, dHead);',
          '  float rim = 1.0 - smoothstep(0.0, 0.1, min(dHead, dEdge));',
          '  return mask * (sunN * max(jam, head) * 0.55 + rim * 0.22);',
          '}',
          'float shtHash(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }',
          'float shtVN(vec2 p){ vec2 i = floor(p), f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f); return mix(mix(shtHash(i), shtHash(i + vec2(1.0, 0.0)), u.x), mix(shtHash(i + vec2(0.0, 1.0)), shtHash(i + vec2(1.0, 1.0)), u.x), u.y); }',
          'float rectM(vec2 m, vec2 c, vec2 s, float aa){ vec2 d = abs(m - c) - s * 0.5; return 1.0 - smoothstep(-aa, aa, max(d.x, d.y)); }',
          'float archM(vec2 m, vec2 c, float w, float h, float aa){ float r = w * 0.5; float dR = max(abs(m.x - c.x) - r, max(c.y - m.y, m.y - (c.y + h - r))); float dC = max(length(vec2(m.x - c.x, m.y - (c.y + h - r))) - r, (c.y + h - r) - m.y); return 1.0 - smoothstep(-aa, aa, min(dR, dC)); }',
        ].join('\n'))
        .replace('#include <color_fragment>', [
          '#include <color_fragment>',
          '{',
          '  diffuseColor.rgb = mix(vec3(dot(diffuseColor.rgb, vec3(0.2126, 0.7152, 0.0722))), diffuseColor.rgb, ' + sat.toFixed(2) + ');',
          '  vec3 n = normalize(vWNorm);',
          '  diffuseColor.rgb *= mix(' + gW.toFixed(2) + ', ' + gR.toFixed(2) + ', step(0.7, n.y));',
          '  float stF = vStyle + 0.5;',
          '  float variantF = floor(stF / 32.0);',
          '  int st = int(stF - variantF * 32.0);',
          '  float vDark = mod(variantF, 2.0);',
          '  float vTall = step(1.5, variantF);',
          '  float v = vWPos.y - vBase;',
          '  if (n.y > 0.7) {',
          '    float rdet = clamp(1.0 - (fwidth(vWPos.x) * uDetFar - 0.1) / 0.6, 0.0, 1.0);',
          '    float rn = shtVN(vWPos.xz * 0.9) * 0.6 + shtVN(vWPos.xz * 5.0) * 0.4;',
          '    diffuseColor.rgb *= 1.0 + rdet * 0.22 * (rn - 0.5);',
          '  }',
          '  if (abs(n.y) < 0.35 && st != 3 && v > 0.0) {',
          '    bool local = vWallL > 0.5;',
          '    float uW;',
          '    if (local) { uW = vWallU; } else { vec2 dir = normalize(n.xz); vec2 perp = vec2(-dir.y, dir.x); uW = dot(vWPos.xz, perp); }',
          '    float aa = 0.6 * max(fwidth(uW), fwidth(v)) + 0.004;',
          // detail fade keys off the vertical derivative only: fwidth(uW) explodes on
          // edge-on walls and used to blank whole facades at grazing angles. detU still
          // gates the BINARY per-column terms (shutters/doors) that would shimmer there.
          '    vec2 perpW = vec2(-normalize(n.xz).y, normalize(n.xz).x);',
          '    float sunT = dot(uSunW.xz, perpW), sunE = max(uSunW.y, 0.0), sunN = clamp(dot(n, uSunW), 0.0, 1.0);',
          '    float det = clamp(1.0 - (0.6 * fwidth(v) * uDetFar + 0.004 - 0.16) / 0.42, 0.0, 1.0);',
          '    bool tower = (st == 2 || st == 6 || st == 7 || (st >= 14 && st <= 18));',
          '    if (tower) det = max(det, clamp(1.0 - (0.6 * fwidth(v) * uDetFar - 0.5) / 1.6, 0.0, 1.0));',
          '    float detU = clamp(1.0 - (0.6 * fwidth(uW) * uDetFar + 0.004 - 0.16) / 0.42, 0.0, 1.0);',
          '    float wallTop = local ? vWallH - 0.25 : 1.0e4;',
          '    float brickish = step(diffuseColor.g * 1.12, diffuseColor.r);',
          '    vec3 frameCol = mix(vec3(0.90, 0.88, 0.82), vec3(0.17, 0.16, 0.15), vDark);',
          '    vec3 trimCol = mix(vec3(0.93, 0.91, 0.86), vec3(0.20, 0.19, 0.18), vDark);',
          '    vec3 stoneCol = vec3(0.80, 0.76, 0.68);',
          '    vec3 col = diffuseColor.rgb;',
          '    float lit = 0.0, glass = 0.0;',
          // every window/door/shutter mask below is multiplied by det, so once
          // the detail fade has reached zero (about 900 m at 58 deg / 1080 px,
          // i.e. most far-ring and outer-tier pixels of a wide view) the whole
          // chain provably contributes nothing: take the far average directly
          '    if (det < 0.002) {',
          '      vec3 farAvg0 = diffuseColor.rgb * 0.9; float farW0 = 0.35;',
          '      if (st == 2 || st == 6 || st == 7 || (st >= 14 && st <= 18)) { farAvg0 = mix(diffuseColor.rgb, vec3(0.115, 0.13, 0.155), (st == 16 || st == 17) ? 0.3 : 0.48); farW0 = 0.92; }',
          '      diffuseColor.rgb = mix(col, farAvg0, farW0);',
          '      shtLit = 0.05;',
          '    } else {',
          '    if (st == 1) {',
          '      float pitch = 4.4;',
          '      float nb = local ? max(1.0, floor(vWallL / pitch)) : 1.0e6;',
          '      float u = local ? uW - (vWallL - nb * pitch) * 0.5 : uW;',
          '      float inWall = local ? step(0.0, u) * step(u, nb * pitch) : 1.0;',
          '      float cu = floor(u / pitch);',
          '      vec2 m = vec2(u - (cu + 0.5) * pitch, v);',
          '      lit = 0.5 + 0.5 * shtHash(vec2(cu, 3.1));',
          '      vec3 gc = vec3(0.08, 0.09, 0.12) + vec3(0.10, 0.09, 0.06) * lit;',
          '      float okU = step(8.9, wallTop) * inWall * det;',
          '      float okL = step(3.2, wallTop) * inWall * det;',
          '      float fmU = archM(m, vec2(0.0, 4.85), 1.68, 3.9, aa) * okU;',
          '      float wmU = archM(m, vec2(0.0, 5.0), 1.4, 3.6, aa) * okU;',
          '      float fmL = rectM(m, vec2(0.0, 1.95), vec2(1.44, 2.14), aa) * okL;',
          '      float wmL = rectM(m, vec2(0.0, 1.95), vec2(1.2, 1.9), aa) * okL;',
          '      col = mix(col, stoneCol, (fmL - wmL) * 0.8);',
          '      col = mix(col, frameCol, (fmU - wmU) * 0.85);',
          '      glass = max(wmU, wmL);',
          '      col = mix(col, gc, glass * 0.92);',
          '      float tr = glass * max(1.0 - smoothstep(0.03, 0.03 + aa, abs(m.x)), max(1.0 - smoothstep(0.025, 0.025 + aa, abs(m.y - 6.6)), 1.0 - smoothstep(0.025, 0.025 + aa, abs(m.y - 2.0))));',
          '      col = mix(col, frameCol, tr * 0.8);',
          '    } else if (st == 2 || st == 6) {',
          '      float pitch = (st == 6) ? 3.6 : 3.0;',
          '      float fp = (st == 6) ? 3.15 : (vFloorH > 5.0 ? vFloorH * 0.1 : 2.95);',
          '      float nb = local ? max(1.0, floor(vWallL / pitch)) : 1.0e6;',
          '      float u = local ? uW - (vWallL - nb * pitch) * 0.5 : uW;',
          '      float inWall = local ? step(0.0, u) * step(u, nb * pitch) : 1.0;',
          '      vec2 cell = vec2(floor(u / pitch), floor(v / fp));',
          '      vec2 m = vec2(u - (cell.x + 0.5) * pitch, v - cell.y * fp);',
          '      float okRow = step(cell.y * fp + 2.5, wallTop) * inWall * det;',
          '      float wm = rectM(m, vec2(0.0, 1.55), vec2(pitch * 0.74, 1.95), aa) * step(0.9, v) * okRow;',
          '      lit = 0.45 + 0.55 * shtHash(cell * 1.3 + 7.0);',
          '      vec3 gc = vec3(0.10, 0.12, 0.15) + vec3(0.12, 0.11, 0.08) * lit;',
          '      if (st == 6 && v < 6.3) {',
          '        vec2 mg = vec2(u - (floor(u / 5.4) + 0.5) * 5.4, v);',
          '        float sf = rectM(mg, vec2(0.0, 3.3), vec2(4.7, 5.3), aa) * inWall * det;',
          '        float sg = rectM(mg, vec2(0.0, 3.3), vec2(4.3, 4.9), aa) * inWall * det;',
          '        col = mix(col, vec3(0.12, 0.11, 0.10), sf * 0.9);',
          '        col = mix(col, vec3(0.22, 0.25, 0.28), sg * 0.9);',
          '        wm = 0.0; glass = sg;',
          '      }',
          '      col = mix(col, gc, wm * 0.9);',
          '      col *= 1.0 - revealShade(m, vec2(0.0, 1.55), vec2(pitch * 0.74, 1.95), wm, sunT, sunE, sunN);',
          '      col = mix(col, gc * 0.6, wm * (1.0 - smoothstep(0.03, 0.03 + aa, abs(m.x))) * 0.8);',
          '      col *= 1.0 - 0.10 * det * rectM(m, vec2(0.0, 0.38), vec2(pitch, 0.44), aa);',
          '      glass = max(glass, wm);',
          '    } else if (st == 7) {',
          '      float fp = 2.75;',
          '      float nb = local ? max(1.0, floor(vWallL / 3.4)) : 1.0e6;',
          '      float u7 = local ? uW - (vWallL - nb * 3.4) * 0.5 : uW;',
          '      float inWall = local ? step(0.0, u7) * step(u7, nb * 3.4) : 1.0;',
          '      float row = floor(v / fp);',
          '      float bandV = v - row * fp;',
          '      float ok = inWall * det * step(2.0, v) * step((row + 1.0) * fp, wallTop + 1.3);',
          '      float gBand = rectM(vec2(0.0, bandV), vec2(0.0, 1.45), vec2(9999.0, 1.8), aa) * ok;',
          '      lit = 0.5 + 0.5 * shtHash(vec2(floor(u7 / 3.4), row) + 3.7);',
          '      vec3 gc7 = vec3(0.10, 0.12, 0.14) + vec3(0.10, 0.09, 0.07) * lit;',
          '      col = mix(col, gc7, gBand * 0.9);',
          '      glass = gBand;',
          '    } else if (st == 14) {',
          // stone piers: granite or limestone verticals every 3.6 m with dark glass strips between
          // them, a stone spandrel at every floor line (BNY Mellon, the Commerce Squares, PSFS)
          '      float pitch = 3.6, fp = vFloorH > 5.0 ? vFloorH * 0.1 : 3.9;',
          '      float nb = local ? max(1.0, floor(vWallL / pitch)) : 1.0e6;',
          '      float u = local ? uW - (vWallL - nb * pitch) * 0.5 : uW;',
          '      float inWall = local ? step(0.0, u) * step(u, nb * pitch) : 1.0;',
          '      vec2 cell = vec2(floor(u / pitch), floor(v / fp));',
          '      vec2 m = vec2(u - (cell.x + 0.5) * pitch, v - cell.y * fp);',
          '      float okRow = step(cell.y * fp + 1.0, wallTop) * inWall * det;',
          '      float strip = rectM(m, vec2(0.0, fp * 0.5), vec2(pitch - 1.35, fp), aa) * okRow;',
          '      float spand = rectM(m, vec2(0.0, 0.42), vec2(pitch, 0.84), aa) * okRow;',
          '      lit = 0.45 + 0.55 * shtHash(cell * 1.9 + 4.0);',
          '      vec3 gc = vec3(0.09, 0.11, 0.13) + vec3(0.11, 0.10, 0.07) * lit;',
          '      float win = strip * (1.0 - spand);',
          '      col = mix(col, gc, win * 0.92);',
          '      col = mix(col, diffuseColor.rgb * 0.82, spand * strip * 0.9);',
          '      col *= 1.0 - 0.12 * det * (1.0 - strip) * (1.0 - smoothstep(0.08, 0.08 + aa, abs(abs(m.x) - (pitch - 1.35) * 0.5 - 0.1)));',
          '      glass = win;',
          '    } else if (st == 15) {',
          // horizontal bands: a ribbon of glass and an opaque spandrel band at every floor,
          // near-continuous, the mullions barely there (PNC, Eleven Penn Center, the Liberty
          // Place podium faces, the metal-banded 1980s towers)
          '      float fp = vFloorH > 5.0 ? vFloorH * 0.1 : 3.7;',
          '      float row = floor(v / fp), bandV = v - row * fp;',
          '      float ok = det * step(0.4, v) * step((row + 1.0) * fp, wallTop + 1.2);',
          '      float gBand = rectM(vec2(0.0, bandV), vec2(0.0, fp * 0.62), vec2(9999.0, fp * 0.56), aa) * ok;',
          '      float mull = 1.0 - smoothstep(0.045, 0.045 + aa, abs(fract(uW / 1.55 + 0.5) - 0.5) * 1.55);',
          '      lit = 0.45 + 0.55 * shtHash(vec2(floor(uW / 3.1), row) + 5.3);',
          '      vec3 gc = vec3(0.10, 0.12, 0.15) + vec3(0.11, 0.10, 0.08) * lit;',
          '      col = mix(col, gc, gBand * 0.92);',
          '      col = mix(col, gc * 0.55, gBand * mull * 0.8);',
          '      col = mix(col, diffuseColor.rgb * 1.08, (1.0 - gBand) * ok * 0.5);',
          '      glass = gBand;',
          '    } else if (st == 16) {',
          // precast concrete grid: a waffle of deep square windows, the frame the wall colour,
          // a shadow line under every head (Five and Six Penn Center, Centre Square, PECO)
          '      float pitch = 3.2, fp = vFloorH > 5.0 ? vFloorH * 0.1 : 3.4;',
          '      float nb = local ? max(1.0, floor(vWallL / pitch)) : 1.0e6;',
          '      float u = local ? uW - (vWallL - nb * pitch) * 0.5 : uW;',
          '      float inWall = local ? step(0.0, u) * step(u, nb * pitch) : 1.0;',
          '      vec2 cell = vec2(floor(u / pitch), floor(v / fp));',
          '      vec2 m = vec2(u - (cell.x + 0.5) * pitch, v - cell.y * fp);',
          '      float okRow = step(cell.y * fp + 2.4, wallTop) * inWall * det * step(0.6, v);',
          '      float win = rectM(m, vec2(0.0, fp * 0.5 + 0.1), vec2(pitch - 1.0, fp - 1.15), aa) * okRow;',
          '      float shade = rectM(m, vec2(0.0, fp * 0.5 + 0.1 + (fp - 1.15) * 0.5 + 0.2), vec2(pitch - 1.0, 0.4), aa) * okRow;',
          '      lit = 0.45 + 0.55 * shtHash(cell * 2.3 + 9.0);',
          '      vec3 gc = vec3(0.07, 0.08, 0.10) + vec3(0.10, 0.09, 0.07) * lit;',
          '      col = mix(col, gc, win * 0.9);',
          '      col *= 1.0 - revealShade(m, vec2(0.0, fp * 0.5 + 0.1), vec2(pitch - 1.0, fp - 1.15), win, sunT, sunE, sunN);',
          '      col *= 1.0 - 0.28 * shade;',
          '      glass = win;',
          '    } else if (st == 17) {',
          // pre-war stone: paired narrow sashes between light piers, a darker spandrel at every
          // floor, a shadow band every eight floors where the setbacks read (One South Broad,
          // Wells Fargo, Lewis Tower, the Drake)
          '      float pitch = 4.4, fp = vFloorH > 5.0 ? vFloorH * 0.1 : 3.5;',
          '      float nb = local ? max(1.0, floor(vWallL / pitch)) : 1.0e6;',
          '      float u = local ? uW - (vWallL - nb * pitch) * 0.5 : uW;',
          '      float inWall = local ? step(0.0, u) * step(u, nb * pitch) : 1.0;',
          '      vec2 cell = vec2(floor(u / pitch), floor(v / fp));',
          '      vec2 m = vec2(u - (cell.x + 0.5) * pitch, v - cell.y * fp);',
          '      float okRow = step(cell.y * fp + 3.0, wallTop) * inWall * det * step(0.8, v);',
          '      float w1 = rectM(m, vec2(-1.0, 1.9), vec2(1.25, 2.3), aa) * okRow;',
          '      float w2 = rectM(m, vec2(1.0, 1.9), vec2(1.25, 2.3), aa) * okRow;',
          '      float win = max(w1, w2);',
          '      float spand = rectM(m, vec2(0.0, 0.32), vec2(pitch, 0.64), aa) * okRow;',
          '      lit = 0.45 + 0.55 * shtHash(cell * 1.1 + 2.0);',
          '      vec3 gc = vec3(0.08, 0.09, 0.11) + vec3(0.11, 0.10, 0.07) * lit;',
          '      col = mix(col, gc, win * 0.92);',
          '      col = mix(col, frameCol, win * (1.0 - smoothstep(0.03, 0.03 + aa, abs(m.y - 1.9))) * 0.7);',
          '      col *= 1.0 - 0.14 * spand - 0.10 * det * step(7.5, mod(cell.y, 8.0)) * (1.0 - win);',
          '      glass = win;',
          '    } else if (st == 18) {',
          // residential slab: a window band and a balcony slab line at every floor
          '      float fp = vFloorH > 5.0 ? vFloorH * 0.1 : 3.1;',
          '      float row = floor(v / fp), bandV = v - row * fp;',
          '      float ok = det * step(0.4, v) * step((row + 1.0) * fp, wallTop + 1.0);',
          '      float gBand = rectM(vec2(0.0, bandV), vec2(0.0, fp * 0.6), vec2(9999.0, fp * 0.5), aa) * ok;',
          '      float slab = rectM(vec2(0.0, bandV), vec2(0.0, 0.16), vec2(9999.0, 0.32), aa) * ok;',
          '      float post = 1.0 - smoothstep(0.09, 0.09 + aa, abs(fract(uW / 3.3 + 0.5) - 0.5) * 3.3);',
          '      lit = 0.45 + 0.55 * shtHash(vec2(floor(uW / 3.3), row) + 6.1);',
          '      vec3 gc = vec3(0.09, 0.10, 0.12) + vec3(0.12, 0.10, 0.07) * lit;',
          '      col = mix(col, gc, gBand * 0.9);',
          '      col = mix(col, diffuseColor.rgb * 0.75, gBand * post * 0.8);',
          '      col = mix(col, vec3(0.86, 0.85, 0.82), slab * 0.85);',
          '      glass = gBand;',
          '    } else if (st == 12) {',
          // industrial loft: big multi-pane sashes on a 4.2 m bay, loading doors on the ground
          '      float pitch = 4.2, fp = vFloorH > 5.0 ? vFloorH * 0.1 : 3.9;',
          '      float nb = local ? max(1.0, floor(vWallL / pitch)) : 1.0e6;',
          '      float u = local ? uW - (vWallL - nb * pitch) * 0.5 : uW;',
          '      float inWall = local ? step(0.0, u) * step(u, nb * pitch) : 1.0;',
          '      vec2 cell = vec2(floor(u / pitch), floor(v / fp));',
          '      vec2 m = vec2(u - (cell.x + 0.5) * pitch, v - cell.y * fp);',
          '      float ground = step(v, fp);',
          '      float bay = ground * step(2.5, mod(cell.x, 4.0)) * inWall * det * detU;',
          '      float okRow = step(cell.y * fp + 3.4, wallTop) * inWall * det * (1.0 - bay);',
          '      float win = rectM(m, vec2(0.0, 2.15), vec2(2.9, 2.5), aa) * okRow;',
          '      float frame = (rectM(m, vec2(0.0, 2.15), vec2(3.1, 2.7), aa) - win) * okRow;',
          '      vec2 wl = vec2((m.x + 1.45) / 2.9, (m.y - 0.9) / 2.5);',
          '      float mun = win * max(max(1.0 - smoothstep(0.02, 0.02 + aa, abs(wl.x - 0.333)), 1.0 - smoothstep(0.02, 0.02 + aa, abs(wl.x - 0.667))), max(1.0 - smoothstep(0.02, 0.02 + aa, abs(wl.y - 0.333)), 1.0 - smoothstep(0.02, 0.02 + aa, abs(wl.y - 0.667))));',
          '      lit = 0.5 + 0.5 * shtHash(cell * 1.3 + 12.0);',
          '      vec3 gc = vec3(0.07, 0.08, 0.09) + vec3(0.11, 0.10, 0.07) * lit;',
          '      col = mix(col, vec3(0.30, 0.29, 0.27), frame * 0.8);',
          '      col = mix(col, gc, win * 0.9);',
          '      col = mix(col, vec3(0.32, 0.31, 0.29), mun * 0.85);',
          '      float door = rectM(m, vec2(0.0, 1.7), vec2(2.8, 3.3), aa) * bay;',
          '      col = mix(col, vec3(0.16, 0.15, 0.14), door * 0.9);',
          '      col *= 1.0 - 0.10 * det * rectM(m, vec2(0.0, fp - 0.25), vec2(pitch, 0.3), aa) * inWall;',
          '      glass = win;',
          '    } else if (st == 13) {',
          // new construction: wide dark-framed windows, no lintels, a floor line in shadow
          '      float pitch = 2.6, fp = vFloorH > 5.0 ? vFloorH * 0.1 : 3.05;',
          '      float nb = local ? max(1.0, floor(vWallL / pitch)) : 1.0e6;',
          '      float u = local ? uW - (vWallL - nb * pitch) * 0.5 : uW;',
          '      float inWall = local ? step(0.0, u) * step(u, nb * pitch) : 1.0;',
          '      vec2 cell = vec2(floor(u / pitch), floor(v / fp));',
          '      vec2 m = vec2(u - (cell.x + 0.5) * pitch, v - cell.y * fp);',
          '      float ground = step(v, fp);',
          '      float doorCol = step(2.5, mod(cell.x, 3.0)) * ground * inWall * det * detU;',
          '      float okRow = step(cell.y * fp + 2.6, wallTop) * inWall * det * (1.0 - doorCol);',
          '      float win = rectM(m, vec2(0.0, 1.75), vec2(1.7, 2.0), aa) * okRow;',
          '      float frame = (rectM(m, vec2(0.0, 1.75), vec2(1.86, 2.16), aa) - win) * okRow;',
          '      lit = 0.5 + 0.5 * shtHash(cell * 2.1 + 13.0);',
          '      vec3 gc = vec3(0.08, 0.09, 0.11) + vec3(0.11, 0.10, 0.08) * lit;',
          '      col = mix(col, vec3(0.14, 0.14, 0.15), frame * 0.9);',
          '      col = mix(col, gc, win * 0.92);',
          '      col = mix(col, gc * 0.7, win * (1.0 - smoothstep(0.02, 0.02 + aa, abs(m.x))) * 0.6);',
          '      float door = rectM(m, vec2(0.0, 1.35), vec2(1.1, 2.4), aa) * doorCol;',
          '      col = mix(col, vec3(0.12, 0.12, 0.13), door * 0.9);',
          '      col *= 1.0 - 0.12 * det * rectM(m, vec2(0.0, fp - 0.2), vec2(pitch, 0.28), aa) * inWall;',
          '      glass = win;',
          '    } else {',
          '      float pitch = (st == 4) ? 3.0 : (st == 8 ? 2.35 : (st == 9 ? 2.25 : (st == 10 ? 3.3 : (st == 11 ? 2.05 : 1.9))));',
          '      float fp = vFloorH > 5.0 ? vFloorH * 0.1 : (st == 9 ? 3.35 : 3.05);',
          '      float nb = local ? max(1.0, floor(vWallL / pitch)) : 1.0e6;',
          '      float u = local ? uW - (vWallL - nb * pitch) * 0.5 : uW;',
          '      float inWall = local ? step(0.0, u) * step(u, nb * pitch) : 1.0;',
          '      vec2 cell = vec2(floor(u / pitch), floor(v / fp));',
          '      vec2 m = vec2(u - (cell.x + 0.5) * pitch, v - cell.y * fp);',
          '      float ground = step(v, fp);',
          '      float ww = (st == 10 ? 1.0 : (st == 9 ? 1.05 : 0.95)), wh = 1.75 + 0.3 * vTall + 0.25 * float(st == 9), sill = 0.85;',
          '      float porch = float(st == 10) * step(v, 3.3) * inWall * det;',
          '      float okRow = step(cell.y * fp + sill + wh, wallTop) * inWall * det;',
          '      lit = 0.5 + 0.5 * shtHash(cell * 1.7 + 11.0);',
          '      vec3 gc = vec3(0.06, 0.07, 0.09) + vec3(0.10, 0.09, 0.06) * lit;',
          '      float doorCol = step(2.5, mod(cell.x, 3.0));',
          '      float isDoor = ground * doorCol * float(st == 0 || st == 8) * brickish * inWall * det * detU;',
          '      float isArch = ground * float(st == 4) * inWall * det;',
          '      float isShop = ground * float(st == 5) * inWall * det;',
          '      float sashOn = (1.0 - max(isDoor, max(isArch, max(isShop, porch)))) * okRow;',
          '      float segCut = 1.0 - smoothstep(sill + wh + 0.2, sill + wh + 0.2 + aa, m.y);',
          '      float win = max(rectM(m, vec2(0.0, sill + wh * 0.5), vec2(ww, wh), aa), float(st == 9) * archM(m, vec2(0.0, sill), ww, wh + ww * 0.5, aa) * segCut) * sashOn;',
          '      float frame = (max(rectM(m, vec2(0.0, sill + wh * 0.5), vec2(ww + 0.22, wh + 0.2), aa), float(st == 9) * archM(m, vec2(0.0, sill - 0.1), ww + 0.22, wh + ww * 0.5 + 0.2, aa) * (1.0 - smoothstep(sill + wh + 0.34, sill + wh + 0.34 + aa, m.y))) - win) * sashOn;',
          '      vec2 wl = vec2((m.x + ww * 0.5) / ww, (m.y - sill) / wh);',
          '      float mun = win * max(1.0 - smoothstep(0.028, 0.028 + aa, abs(wl.x - 0.5)), max(1.0 - smoothstep(0.02, 0.02 + aa, abs(wl.y - 0.5)), max(1.0 - smoothstep(0.016, 0.016 + aa, abs(wl.y - 0.25)), 1.0 - smoothstep(0.016, 0.016 + aa, abs(wl.y - 0.75)))));',
          '      float lintel = rectM(m, vec2(0.0, sill + wh + 0.2), vec2(ww + 0.4, 0.24), aa) * sashOn * brickish * float(st != 11 && st != 9);',
          '      float sillM = rectM(m, vec2(0.0, sill - 0.08), vec2(ww + 0.26, 0.12), aa) * sashOn * (brickish + float(st == 9)) * float(st != 11);',
          '      float shut = (rectM(m, vec2(-(ww * 0.5 + 0.31), sill + wh * 0.5), vec2(0.44, wh), aa) + rectM(m, vec2(ww * 0.5 + 0.31, sill + wh * 0.5), vec2(0.44, wh), aa)) * sashOn;',
          '      float shOn = step(shtHash(vec2(cell.x * 0.37, 7.31)), 0.5) * brickish * float(st == 0) * detU;',
          '      vec3 shCol = mix(vec3(0.09, 0.13, 0.10), vec3(0.06, 0.06, 0.07), step(0.5, shtHash(vec2(cell.x, 2.17))));',
          '      col = mix(col, stoneCol, max(lintel, sillM) * 0.8);',
          '      col = mix(col, frameCol, frame * 0.9);',
          '      col = mix(col, gc, win * 0.92);',
          '      col *= 1.0 - revealShade(m, vec2(0.0, sill + wh * 0.5), vec2(ww, wh), win, sunT, sunE, sunN);',
          '      col = mix(col, frameCol, mun * 0.85);',
          '      col = mix(col, shCol, shut * shOn * 0.9);',
          '      float door = rectM(m, vec2(0.0, 1.45), vec2(1.0, 2.2), aa) * isDoor;',
          '      float dframe = (rectM(m, vec2(0.0, 1.5), vec2(1.26, 2.3), aa) - door) * isDoor;',
          '      float fan = (1.0 - smoothstep(0.52, 0.52 + aa, length(vec2(m.x, m.y - 2.55)))) * step(2.55, m.y) * isDoor;',
          '      float fanIn = (1.0 - smoothstep(0.42, 0.42 + aa, length(vec2(m.x, m.y - 2.55)))) * step(2.55, m.y) * isDoor;',
          '      float stepM = rectM(m, vec2(0.0, 0.17), vec2(1.5, 0.34), aa) * isDoor;',
          '      vec3 dCol = mix(vec3(0.10, 0.08, 0.06), vec3(0.05, 0.09, 0.13), step(0.5, shtHash(vec2(cell.x, 9.1))));',
          '      col = mix(col, frameCol, max(dframe, fan) * 0.9);',
          '      col = mix(col, dCol, door * 0.92);',
          '      col = mix(col, vec3(0.85, 0.83, 0.78) * (0.6 + 0.4 * lit), fanIn * 0.9);',
          '      col = mix(col, vec3(0.85, 0.83, 0.78), stepM * 0.85);',
          '      float archF = archM(m, vec2(0.0, 0.15), 1.9, 2.85, aa) * isArch;',
          '      float arch = archM(m, vec2(0.0, 0.15), 1.6, 2.7, aa) * isArch;',
          '      col = mix(col, frameCol, archF * 0.85);',
          '      col = mix(col, gc * 0.8, arch * 0.9);',
          '      float shopF = rectM(m, vec2(0.0, 1.7), vec2(1.66, 2.7), aa) * isShop;',
          '      float shop = rectM(m, vec2(0.0, 1.7), vec2(1.5, 2.5), aa) * isShop;',
          '      col = mix(col, vec3(0.18, 0.17, 0.16), shopF * 0.9);',
          '      col = mix(col, gc * 1.3, shop * 0.9);',
          '      float awnOn = float(st == 5) * inWall * det * step(v, 4.0);',
          '      float awn = rectM(m, vec2(0.0, 3.45), vec2(pitch * 0.94, 0.5), aa) * awnOn;',
          '      float ah = shtHash(vec2(cell.x * 0.53, 4.7));',
          '      vec3 awnCol = ah < 0.3 ? vec3(0.55, 0.12, 0.10) : (ah < 0.55 ? vec3(0.10, 0.30, 0.18) : (ah < 0.75 ? vec3(0.10, 0.18, 0.40) : vec3(0.72, 0.66, 0.50)));',
          '      col = mix(col, awnCol, awn * 0.95);',
          '      glass = max(win, max(fanIn, max(arch, shop)));',
          '      if (st == 9 || st == 11) {',
          '        float corn = (1.0 - smoothstep(0.0, aa, abs(v - (wallTop - 0.42)) - 0.42)) * float(local) * inWall * det;',
          '        float dent = float(st == 9) * corn * step(0.5, fract(u / 0.6)) * (1.0 - smoothstep(0.0, aa, abs(v - (wallTop - 0.9)) - 0.16));',
          '        col = mix(col, trimCol, max(corn, dent) * 0.9);',
          '      }',
          '      if (st == 11) {',
          '        float lap = 1.0 - smoothstep(0.03, 0.03 + aa, abs(fract(v / 0.26 + 0.5) - 0.5) * 0.26);',
          '        col *= 1.0 - 0.13 * det * lap * (1.0 - max(win, frame));',
          '      }',
          '      if (st == 10) {',
          '        float post = 1.0 - smoothstep(0.14, 0.14 + aa, abs(fract(uW / 3.3 + 0.5) - 0.5) * 3.3);',
          '        float roofL = (1.0 - smoothstep(0.0, aa, abs(v - 3.15) - 0.22)) * inWall * det;',
          '        col = mix(col, col * 0.55, porch * (1.0 - post) * 0.9);',
          '        col = mix(col, trimCol, max(porch * post, roofL) * 0.9);',
          '        float pw = rectM(m, vec2(0.0, 1.6), vec2(1.1, 1.6), aa) * porch * (1.0 - post) * step(0.5, mod(cell.x, 2.0));',
          '        col = mix(col, gc, pw * 0.85);',
          '        glass = max(glass, pw);',
          '      }',
          '    }',
          // glass: a tint per building (blue, teal, bronze, grey, green for the towers, a dark
          // blue-grey for the rows), and the window pixels turn reflective below: the sky and
          // the sun come back in every window, which is most of what makes a real tower read
          '    float bid = shtHash(vec2(floor(vWPos.x / 28.0) * 0.37, floor(vWPos.z / 28.0) * 0.91));',
          '    vec3 gTint = tower ? (bid < 0.25 ? vec3(0.10, 0.17, 0.26) : (bid < 0.45 ? vec3(0.08, 0.19, 0.20) : (bid < 0.62 ? vec3(0.17, 0.12, 0.08) : (bid < 0.82 ? vec3(0.12, 0.13, 0.15) : vec3(0.09, 0.15, 0.13))))) : vec3(0.07, 0.09, 0.12);',
          '    col = mix(col, gTint * (0.75 + 0.5 * lit), glass * 0.9);',
          '    shtGlass = glass * det * (tower ? 1.0 : 0.75);',
          '    col *= 1.0 - 0.14 * (1.0 - smoothstep(0.0, 5.0, v));',
          '    {',
          '      float wallM = 1.0 - glass;',
          '      float detT = clamp(1.0 - (fwidth(v) * uDetFar - 0.016) / 0.05, 0.0, 1.0);',
          '      col *= 0.95 + 0.10 * shtVN(vec2(uW, v) * 0.25) * det;',
          '      bool stone = (st == 14 || st == 17 || st == 4);',
          '      bool panel = (st == 2 || st == 6 || st == 16 || st == 18 || st == 15 || st == 13 || st == 7);',
          '      if (detT > 0.001 && wallM > 0.01) {',
          '        if (stone) {',
          '          float sc = floor(v / 0.55); float su = uW + mod(sc, 2.0) * 0.6;',
          '          float smh = 1.0 - smoothstep(0.01, 0.01 + aa, abs(fract(v / 0.55 + 0.5) - 0.5) * 0.55);',
          '          float smv = 1.0 - smoothstep(0.01, 0.01 + aa, abs(fract(su / 1.2 + 0.5) - 0.5) * 1.2);',
          '          float svar = shtHash(vec2(sc, floor(su / 1.2)));',
          '          col *= 1.0 + detT * wallM * 0.1 * (svar - 0.5);',
          '          col = mix(col, col * 0.72, max(smh, smv) * detT * wallM * 0.6);',
          '        } else if (panel) {',
          '          float seam = max(1.0 - smoothstep(0.012, 0.012 + aa, abs(fract(v / 3.3 + 0.5) - 0.5) * 3.3), 1.0 - smoothstep(0.012, 0.012 + aa, abs(fract(uW / 3.0 + 0.5) - 0.5) * 3.0));',
          '          col *= 1.0 - 0.2 * seam * detT * wallM;',
          '          col *= 1.0 + detT * wallM * 0.06 * (shtVN(vec2(uW, v) * 2.0) - 0.5);',
          '        } else if (brickish > 0.5) {',
          '          float course = floor(v / 0.075); float bu = uW + mod(course, 2.0) * 0.11;',
          '          float mh = 1.0 - smoothstep(0.007, 0.007 + aa, abs(fract(v / 0.075 + 0.5) - 0.5) * 0.075);',
          '          float mv = 1.0 - smoothstep(0.007, 0.007 + aa, abs(fract(bu / 0.22 + 0.5) - 0.5) * 0.22);',
          '          float bvar = shtHash(vec2(course, floor(bu / 0.22)));',
          '          col *= 1.0 + detT * wallM * 0.18 * (bvar - 0.5);',
          '          col = mix(col, vec3(0.58, 0.55, 0.50) * (0.85 + 0.15 * bvar), max(mh, mv) * detT * wallM * 0.7);',
          '        } else if (st != 11) {',
          '          col *= 0.94 + 0.12 * shtVN(vec2(uW, v) * 3.0) * detT * wallM + 0.06 * (1.0 - detT * wallM);',
          '        }',
          '      }',
          '    }',
          '    // far away the pattern averages to the true facade mix — curtain-wall',
          '    // styles are ~half glass, so they must converge to a visibly darker',
          '    // average instead of washing back to the pale wall color',
          '    vec3 farAvg = diffuseColor.rgb * 0.9; float farW = 0.35;',
          '    if (st == 2 || st == 6 || st == 7 || (st >= 14 && st <= 18)) { farAvg = mix(diffuseColor.rgb, vec3(0.115, 0.13, 0.155), (st == 16 || st == 17) ? 0.3 : 0.48); farW = 0.92; }',
          '    col = mix(col, farAvg, (1.0 - det) * farW);',
          // only about a third of windows are lit at night, at varied warmth; where the
          // pattern fades with distance the facade keeps a soft aggregate glow instead
          // of dying into a solid mass
          '    float litOn = step(0.82, lit) * (0.4 + 0.6 * fract(lit * 9.7));',
          '    // past the per-window fade the facade keeps only the soft aggregate',
          '    // glow (the 3x2-window cluster LOD read as big yellow squares that',
          '    // popped away on approach, removed at the owner\'s request)',
          '    shtLit = mix(0.05, glass * litOn, det);',
          '    diffuseColor.rgb = col;',
          '    }',
          '  }',
          '}',
        ].join('\n'))
        .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\nroughnessFactor = mix(roughnessFactor, 0.16, shtGlass);')
        .replace('#include <metalnessmap_fragment>', '#include <metalnessmap_fragment>\nmetalnessFactor = mix(metalnessFactor, 0.8, shtGlass);')
        // lit windows dim with distance (aerial perspective by night): the far ring's mass
        // of them otherwise resolves to a white band along the horizon
        .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance += vec3(1.0, 0.76, 0.46) * shtLit * uNight * 1.3 * (1.0 - 0.45 * smoothstep(1500.0, 7000.0, length(vViewPosition)));');
    };
    cityMat.onBeforeCompile = facadeHook(FACADE_GAIN, ROOF_GAIN, 1.2);
    cityMat.customProgramCacheKey = () => 'fabric';   // the two hooks share one source: keyed by hand (gotcha 15)
    coreMat = cityMat.clone();   // r149's clone drops the hook; assigned fresh
    coreMat.onBeforeCompile = facadeHook(CORE_FACADE_GAIN, CORE_ROOF_GAIN, 1.0);
    coreMat.customProgramCacheKey = () => 'fabric-core';
  }

  // ------------------------------------------------ landmark spires
  function findBuilding(nameLike) {
    const re = new RegExp(nameLike.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');
    for (const b of D.buildings) if (b.name && re.test(b.name)) return b;
    return null;
  }
  step('Setting the steeples', () => {
    const parts = [];
    for (const lm of META_L) {
      if (!lm || !lm.spire_kind || lm.spire_kind === 'none' || !lm.spire_height_m) continue;
      const b = findBuilding(lm.name);
      if (!b || upgraded.has(b)) continue; // realism step builds these itself
      const [cx, cz] = polyCentroid(b.poly);
      // measured pitched roofs carry b.h = ridge; seat the steeple at the eave so
      // its base interpenetrates the slopes instead of floating at the ridge line
      const roof = (Array.isArray(b.roof) && b.roof.length > 3) ? b.roof[1] : b.h;
      const total = Math.max(lm.spire_height_m, (Array.isArray(b.roof) && b.roof.length > 3 ? b.roof[2] : roof) + 6);
      const rise = total - roof;
      const col = new THREE.Color(lm.color_hex || '#d9d2c2');
      if (lm.spire_kind === 'steeple') {
        // masonry tower stages in the facade color, then a pale wooden spire
        const baseH = rise * 0.44, spireH = rise * 0.56;
        parts.push({ geom: box(5.4, baseH, 5.4, cx, roof + baseH / 2, cz), color: col });
        const cone = new THREE.ConeGeometry(2.7, spireH, 8);
        cone.translate(cx, roof + baseH + spireH / 2, cz);
        parts.push({ geom: cone, color: new THREE.Color(0xece8dc) });
      } else if (lm.spire_kind === 'cupola') {
        const drum = new THREE.CylinderGeometry(2.1, 2.1, rise * 0.6, 10);
        drum.translate(cx, roof + rise * 0.3, cz);
        parts.push({ geom: drum, color: col });
        const cap = new THREE.ConeGeometry(2.5, rise * 0.4, 10);
        cap.translate(cx, roof + rise * 0.8, cz);
        parts.push({ geom: cap, color: col });
      } else if (lm.spire_kind === 'dome') {
        const dome = new THREE.SphereGeometry(4.5, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2);
        dome.translate(cx, roof, cz);
        parts.push({ geom: dome, color: col });
      } else { // tower
        parts.push({ geom: box(6.5, rise * 0.82, 6.5, cx, roof + rise * 0.41, cz), color: col });
        const cap = new THREE.ConeGeometry(4.6, rise * 0.18, 4);
        cap.rotateY(Math.PI / 4);
        cap.translate(cx, roof + rise * 0.91, cz);
        parts.push({ geom: cap, color: col });
      }
    }
    if (parts.length) {
      const mesh = new THREE.Mesh(
        mergeColored(parts),
        new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85 })
      );
      mesh.castShadow = true;
      groupCity.add(mesh);
      freeOnUpload(mesh.geometry);
    }
  });

  // ------------------------------------------------ researched landmark models
  // texture anisotropy clamped to the hardware cap (nine atlases used to hardcode
  // 4/8 without asking); lazy, the renderer exists before any atlas is built
  let hwAniso = 0;
  const anisoOf = (n) => Math.min(n, hwAniso || (hwAniso = renderer.capabilities.getMaxAnisotropy() || 1));
  step('Restoring the landmarks', () => {
    const walls = [];   // gets the window shader
    const detail = [];  // roofs, spires, columns, trim — plain material
    const aw = (geom, hex, style) => walls.push({ geom, color: new THREE.Color(hex), style: style == null ? 0 : style });
    const ad = (geom, hex) => detail.push({ geom, color: new THREE.Color(hex), style: 3 });
    const get = (name) => { for (const b of upgraded.keys()) if (b.name === name) return b; return null; };
    const getKey = (key) => { for (const [b, sp] of upgraded) if (sp.key === key) return b; return null; };
    const mark = () => [walls.length, detail.length, glassParts2.length];
    const liftAt = (m, x, z) => lift(m[0], m[1], m[2], siteY(x, z, 'ground'));
    const liftB = (m, b) => { const [cx, cz] = polyCentroid(b.poly); liftAt(m, cx, cz); };
    const ryAlign = (ax, az) => Math.atan2(-az, ax);
    const glassParts2 = [];
    const lift = (w0, d0, g0, ty) => {
      if (!ty) return;
      for (let k = w0; k < walls.length; k++) { walls[k].geom.translate(0, ty, 0); walls[k].baseY = ty; }
      for (let k = d0; k < detail.length; k++) { detail[k].geom.translate(0, ty, 0); detail[k].baseY = ty; }
      for (let k = g0; k < glassParts2.length; k++) { glassParts2[k].geom.translate(0, ty, 0); glassParts2[k].baseY = ty; }
    };
    const chimney = (x, z, h0, h1, ry, hex) =>
      ad(box(0.95, h1 - h0, 0.55, x, (h0 + h1) / 2, z, ry), hex || '#6a4132');

    // simple researched form: walls to the eave + gable/hip roof + extras
    function classic(name, o) {
      const b = get(name);
      if (!b) return null;
      const ob = orientedBox(b.poly);
      if (!ob) return null;
      const a = obbAxis(ob);
      const st = o.style == null ? 0 : o.style;
      const w0 = walls.length, d0 = detail.length;
      aw(buildingGeom(b.poly, b.holes, o.eave, -1.5), o.wall, st);
      if (o.roof === 'hip') {
        ad(hipGeom(ob, o.eave, o.ridge, 0.4), o.roofCol);
      } else if (o.roof === 'gable') {
        // roofs must sit on the walls: try the footprint quad, then a looser
        // simplification for L-plans (roof covers the main mass, the ell keeps
        // its flat cap). NEVER an OBB gable — it floats beside non-rectangular
        // walls (the City Tavern chimney-side floaters).
        let sp = simplifyRing(b.poly, 0.6);
        if (sp.length !== 4) sp = simplifyRing(b.poly, 1.4);
        if (sp.length === 4) {
          const g = quadGable(sp, o.eave, o.ridge);
          ad(g.slopes, o.roofCol);
          if (o.gableEndsTrim) ad(g.ends, o.trim); else aw(g.ends, o.wall, st);
          for (const ev of g.eaves) {
            ad(box(ev.len + 0.1, 0.4, 0.55,
              (ev.a[0] + ev.b[0]) / 2, o.eave - 0.1, (ev.a[1] + ev.b[1]) / 2,
              Math.atan2(-(ev.b[1] - ev.a[1]), ev.b[0] - ev.a[0])), o.trim);
          }
        } else {
          o.dormers = null;   // no pitched roof for the dormers to sit on
        }
      }
      if (o.chimneys) {
        for (const s of [-1, 1]) {
          if (o.chimneys === 1 && s < 0) continue;
          chimney(ob.cx + a.ax * (a.hl - 1.1) * s, ob.cz + a.az * (a.hl - 1.1) * s,
            o.eave - 1, o.ridge + 1.4, ryAlign(a.ax, a.az), o.wall);
        }
      }
      if (o.dormers) {
        const side = (a.px * o.dormers[0] + a.pz * o.dormers[1]) >= 0 ? 1 : -1;
        const n = o.dormers[2];
        for (let i = 0; i < n; i++) {
          const u = (i - (n - 1) / 2) * (a.hl * 1.1 / Math.max(1, n - 1) + 1.5);
          ad(box(1.35, 1.7, 1.5,
            ob.cx + a.ax * u + a.px * side * (a.hs * 0.55),
            o.eave + 1.1,
            ob.cz + a.az * u + a.pz * side * (a.hs * 0.55),
            ryAlign(a.ax, a.az)), o.trim);
        }
      }
      lift(w0, d0, glassParts2.length, siteY(ob.cx, ob.cz, 'ground'));
      return { b, ob, a };
    }

    // Georgian & Greek Revival core
    classic('Head House', { wall: '#8a4634', trim: '#f2ede0', eave: 7.6, ridge: 10, roof: 'gable', roofCol: '#4a4c50', style: 4 });
    {
      const hh = get('Head House');
      if (hh) {
        const ob = orientedBox(hh.poly);
        const m0 = mark();
        cupolaGeoms(ob.cx, ob.cz, 9.7, 2.5, 5.2).forEach(g => ad(g, '#f2ede0'));
        liftB(m0, hh);
      }
    }
    classic('City Tavern', { wall: '#7f3d2c', trim: '#efe9d8', eave: 11, ridge: 14, roof: 'gable', roofCol: '#5b564e', chimneys: 2, dormers: [1, 0, 3] });
    classic('Hill-Physick House', { wall: '#83402e', trim: '#f1ebdc', eave: 12, ridge: 14.5, roof: 'hip', roofCol: '#3f4044', chimneys: 2 });
    classic('Powel House', { wall: '#7d3b2a', trim: '#f1ebdc', eave: 11, ridge: 13.5, roof: 'gable', roofCol: '#4d4a45', chimneys: 2, dormers: [1, 0, 2] });
    // (the tavern's generic classic() model was here; it fought the gambrel model below on the same footprint)

    // churches
    {
      const r = classic("Saint Peter's Church", { wall: '#8e4a38', trim: '#f0ede4', eave: 9.5, ridge: 13.5, roof: 'gable', roofCol: '#5e5d59', style: 1 });
      if (r) { // Strickland tower + white spire at the WEST end, apex ~64 m
        const m0 = mark();
        const e = obbEnd(r.ob, -1, 0);
        const tx = e.x - e.ax * 4.2, tz = e.z - e.az * 4.2;
        aw(box(7.5, 24, 7.5, tx, 12, tz, ryAlign(e.ax, e.az)), '#8e4a38', 1);
        ad(box(4.9, 3.2, 4.9, tx, 25.6, tz, ryAlign(e.ax, e.az)), '#e9e9e5');
        const sp = new THREE.ConeGeometry(3.1, 36.8, 8);
        sp.translate(tx, 27.2 + 18.4, tz);
        ad(sp, '#e9e9e5');
        liftB(m0, r.b);
      }
    }
    {
      const r = classic('Old Pine Street Church', { wall: '#e7d28b', trim: '#eae8df', eave: 10, ridge: 13, roof: 'gable', roofCol: '#7a7a76', gableEndsTrim: true, style: 1 });
      if (r) { // canary stucco temple; octastyle colonnade facing NORTH to Pine St
        const m0 = mark();
        const e = obbEnd(r.ob, 0, -1);
        const hw = r.a.hs - 1.4;
        const cx0 = e.x + e.ax * 1.7 - r.a.px * hw, cz0 = e.z + e.az * 1.7 - r.a.pz * hw;
        const cx1 = e.x + e.ax * 1.7 + r.a.px * hw, cz1 = e.z + e.az * 1.7 + r.a.pz * hw;
        columnRow(cx0, cz0, cx1, cz1, 8, 8.6, 0.44, 0.4).forEach(g => ad(g, '#eae8df'));
        ad(box(hw * 2 + 1.8, 1.2, 1.5, e.x + e.ax * 1.7, 9.6, e.z + e.az * 1.7, ryAlign(r.a.px, r.a.pz)), '#eae8df');
        liftB(m0, r.b);
      }
    }
    {
      const r = classic('Mother Bethel African Methodist Episcopal Church', { wall: '#cfc9bd', trim: '#8a7a66', eave: 11.6, ridge: 15, roof: 'gable', roofCol: '#4b4642', style: 1 });
      if (r) { // granite Romanesque; spired bell tower at the NW corner (6th & Addison)
        const m0 = mark();
        let mnx = 1e9, mnz = 1e9, mxz = -1e9;
        for (const p of r.b.poly) { mnx = Math.min(mnx, p[0]); mnz = Math.min(mnz, p[1]); mxz = Math.max(mxz, p[1]); }
        aw(box(6.5, 22.5, 6.5, mnx + 3.4, 11.25, mnz + 3.4, 0), '#cfc9bd', 1);
        const pyr = new THREE.ConeGeometry(4.4, 10.5, 4);
        pyr.rotateY(Math.PI / 4);
        pyr.translate(mnx + 3.4, 22.5 + 5.25, mnz + 3.4);
        ad(pyr, '#4b4642');
        aw(box(4.4, 12.5, 4.4, mnx + 2.4, 6.25, mxz - 2.6, 0), '#cfc9bd', 1);
        liftB(m0, r.b);
      }
    }
    classic("Old Saint Mary's Church", { wall: '#814238', trim: '#e8e4da', eave: 10, ridge: 14.2, roof: 'gable', roofCol: '#615f5b', style: 1 });
    classic("Old Saint Joseph's Church", { wall: '#95503a', trim: '#edeae0', eave: 9.5, ridge: 12.5, roof: 'gable', roofCol: '#5f5d58', style: 1 });
    classic("Old Saint Paul's Church", { wall: '#d8dad3', trim: '#c2c4bc', eave: 9, ridge: 13, roof: 'gable', roofCol: '#63615c', gableEndsTrim: true, style: 1 });

    // the Shambles: open market shed — two rows of brick piers under a slate gable
    {
      const b = get('Head House Market');
      if (b) {
        const m0 = mark();
        const ob = orientedBox(b.poly);
        const a = obbAxis(ob);
        const L = a.hl * 2;
        const n = Math.max(4, Math.round(L / 3.7));
        for (let i = 0; i <= n; i++) {
          const u = -a.hl + 0.6 + (i / n) * (L - 1.2);
          for (const s of [-1, 1]) {
            aw(box(0.45, 3.3, 0.45,
              ob.cx + a.ax * u + a.px * s * (a.hs - 0.55), 1.65,
              ob.cz + a.az * u + a.pz * s * (a.hs - 0.55), 0), '#8a4634', 3);
          }
        }
        const g = gableGeom(ob, 3.5, 6.3, 0.5, 0.3);
        ad(g.slopes, '#565a5e');
        ad(g.ends, '#565a5e');
        for (const s of [-1, 1]) {
          ad(box(L + 1, 0.24, 0.2,
            ob.cx + a.px * s * (a.hs + 0.35), 3.42, ob.cz + a.pz * s * (a.hs + 0.35),
            ryAlign(a.ax, a.az)), '#e8e2d4');
        }
        liftB(m0, b);
      }
    }

    // Merchants' Exchange: marble block, curved Corinthian colonnade + lantern to Dock St
    {
      const b = get("Merchants' Exchange Building");
      if (b) {
        const m0 = mark();
        aw(buildingGeom(b.poly, b.holes, 17.5, -1.5), '#d9d4c6', 1);
        const [ccx, ccz] = polyCentroid(b.poly);
        let ex = ccx, ez = ccz, best = -1e9;
        for (const p of b.poly) { if (p[0] > best) { best = p[0]; ex = p[0]; ez = p[1]; } }
        let dx = ex - ccx, dz = ez - ccz;
        const dl = Math.hypot(dx, dz) || 1;
        dx /= dl; dz /= dl;
        const arcX = ccx + dx * (dl - 10.5), arcZ = ccz + dz * (dl - 10.5);
        const base = Math.atan2(dz, dx);
        for (let i = 0; i < 8; i++) {
          const th = base + (-0.95 + (i / 7) * 1.9);
          const col = new THREE.CylinderGeometry(0.42, 0.48, 9.2, 10);
          col.translate(arcX + Math.cos(th) * 11.2, 5.2 + 4.6, arcZ + Math.sin(th) * 11.2);
          ad(col, '#d9d4c6');
        }
        const drum = new THREE.CylinderGeometry(2.9, 2.9, 7, 14);
        drum.translate(arcX, 17.5 + 3.5, arcZ);
        ad(drum, '#d9d4c6');
        const cap = new THREE.ConeGeometry(3.3, 3, 14);
        cap.translate(arcX, 24.5 + 1.5, arcZ);
        ad(cap, '#b9b4a6');
        liftB(m0, b);
      }
    }

    // The Ryland: two offset blue-glass bars — same curtain-wall family as the
    // Liberty Place shafts (it reads blue in photos, not white)
    {
      const b = get('The Ryland');
      if (b) {
        const m0 = mark();
        const ob = orientedBox(b.poly);
        const a = obbAxis(ob);
        const ry = ryAlign(a.ax, a.az);
        const L = a.hl * 2 - 0.6, S = a.hs * 2;
        const north = (a.pz < 0) ? 1 : -1; // v-sign whose direction points north
        const bars = [
          { v: north * (S / 4), d: S / 2 - 0.4, h: 110.9 },   // north bar, full height
          { v: -north * (S / 4), d: S / 2 - 0.4, h: 84 },      // south bar + amenity deck
        ];
        for (const bar of bars) {
          const bx = ob.cx + a.px * bar.v, bz = ob.cz + a.pz * bar.v;
          glassParts2.push({ geom: box(L, bar.h, bar.d, bx, bar.h / 2, bz, ry), color: new THREE.Color(0x4f7ba1) });
          // mullion grid a shade darker than the glass: verticals every ~3 m,
          // spandrel band every 3 floors — curtain-wall rhythm, not white trim
          const nV = Math.round(L / 3);
          for (let i = 0; i <= nV; i++) {
            const u = -L / 2 + (i / nV) * L;
            for (const s of [-1, 1]) {
              ad(box(0.16, bar.h, 0.14,
                bx + a.ax * u + a.px * s * (bar.d / 2), bar.h / 2,
                bz + a.az * u + a.pz * s * (bar.d / 2), ry), '#3d5a73');
            }
          }
          for (let y = 9.4; y < bar.h - 1; y += 9.4) {
            for (const s of [-1, 1]) {
              ad(box(L + 0.1, 0.55, 0.16,
                bx + a.px * s * (bar.d / 2), y,
                bz + a.pz * s * (bar.d / 2), ry), '#3d5a73');
            }
          }
        }
        // glass parapet screen on the north bar, pergola on the south roof deck
        const nb = bars[0], sb = bars[1];
        glassParts2.push({
          geom: box(L - 4, 3.2, 1.2, ob.cx + a.px * nb.v, nb.h + 1.6, ob.cz + a.pz * nb.v, ry),
          color: new THREE.Color(0x6c93b4),
        });
        ad(box(9, 2.4, 5, ob.cx + a.px * sb.v, sb.h + 1.2, ob.cz + a.pz * sb.v, ry), '#4a4a4c');
        liftB(m0, b);
      }
    }

    // Marriott Old City (ex-Sheraton): correct height, brick, dark roof, porte-cochere
    {
      const b = get('Philadelphia Marriott Old City');
      if (b) {
        const m0 = mark();
        aw(buildingGeom(b.poly, b.holes, 16.5, -1.5), '#95513f');
        ad(extrudePoly(b.poly, b.holes, 17.1, 16.5), '#3c3f44');
        let wx = 1e9, wz = 0;
        for (const p of b.poly) { if (p[0] < wx) { wx = p[0]; wz = p[1]; } }
        ad(box(14, 0.6, 7.5, wx - 3.5, 4.4, wz, 0), '#efeae0');
        for (const s of [-1, 1]) ad(box(0.6, 4.2, 0.6, wx - 6.8, 2.1, wz + s * 3.2, 0), '#95513f');
        liftB(m0, b);
      }
    }

    // Seaport Museum: pale block with the long verdigris barrel vault
    {
      const b = get('Independence Seaport Museum');
      if (b) {
        const w0 = walls.length, d0 = detail.length;
        aw(buildingGeom(b.poly, b.holes, 11.5, -1.5), '#d8d5cc', 2);
        const ob = orientedBox(b.poly);
        const vault = new THREE.CylinderGeometry(7.5, 7.5, Math.max(ob.w, ob.d) * 0.55, 16, 1, true, Math.PI, Math.PI);
        vault.rotateX(Math.PI / 2);
        vault.scale(1, 5 / 7.5, 1);
        const a = obbAxis(ob);
        vault.rotateY(Math.atan2(-a.az, a.ax) + Math.PI / 2);
        vault.translate(ob.cx, 11.5, ob.cz);
        ad(vault, '#9dbfad');
        lift(w0, d0, glassParts2.length, siteY(ob.cx, ob.cz, 'ground'));
      }
    }

    // --- skyline corrections: buildings OSM tags at the 13 m default
    {
      // US Custom House (1934): limestone base, red-brick shaft, then the white
      // stepped crown — square stage, two octagonal drums, colonnaded lantern, dome
      const b = get('United States Custom House');
      if (b) {
        const m0 = mark();
        const ob = orientedBox(b.poly);
        const ry = ryAlign(obbAxis(ob).ax, obbAxis(ob).az);
        aw(buildingGeom(b.poly, b.holes, 9, -1.5), '#b8ae97', 2);
        aw(buildingGeom(b.poly, b.holes, 40, 9), '#54302a', 2);
        aw(box(33, 9, 33, ob.cx, 40 + 4.5, ob.cz, ry), '#b5ac96', 2);
        const facet = (g) => { const f = g.toNonIndexed(); f.computeVertexNormals(); return f; };
        const oct1 = new THREE.CylinderGeometry(13.2, 14.4, 13, 8);
        oct1.rotateY(ry + Math.PI / 8); oct1.translate(ob.cx, 49 + 6.5, ob.cz);
        ad(facet(oct1), '#b2a993');
        const oct2 = new THREE.CylinderGeometry(9.2, 10.0, 11, 8);
        oct2.rotateY(ry + Math.PI / 8); oct2.translate(ob.cx, 62 + 5.5, ob.cz);
        ad(facet(oct2), '#bab19b');
        const lan = new THREE.CylinderGeometry(5.6, 6.4, 8.5, 8);
        lan.translate(ob.cx, 73 + 4.25, ob.cz);
        ad(facet(lan), '#c0b7a1');
        const dome = new THREE.CylinderGeometry(1.6, 5.8, 5.5, 8);
        dome.translate(ob.cx, 81.5 + 2.75, ob.cz);
        ad(facet(dome), '#a89f8a');
        const fin = new THREE.CylinderGeometry(0.3, 1.4, 2.8, 6);
        fin.translate(ob.cx, 87 + 1.4, ob.cz);
        ad(facet(fin), '#b2a993');
        liftB(m0, b);
      }
    }
    // Man Full of Trouble Tavern (1759): two brick floors under a gambrel roof
    // with dormers, cream pent + cornice, big end chimney — a block from the pool
    {
      const b = get('Man Full of Troubles Tavern');
      if (b) {
        const m0 = mark();
        const ob = orientedBox(b.poly);
        const a = obbAxis(ob);
        const ry = ryAlign(a.ax, a.az);
        const EAVE = 6.6, BRK = 8.8, RIDGE = 9.8, INSET = 1.9;
        aw(buildingGeom(b.poly, null, EAVE, -1.5), '#77402f', 0);
        { // gambrel: two slopes a side + pentagon gable ends (detail mat is DoubleSide)
          const hl = a.hl + 0.35, hs = a.hs + 0.3;
          const P = (u, v, y) => [ob.cx + a.ax * u + a.px * v, y, ob.cz + a.az * u + a.pz * v];
          const pos = [];
          const tri = (A, B, C) => pos.push(A[0], A[1], A[2], B[0], B[1], B[2], C[0], C[1], C[2]);
          for (const s of [-1, 1]) {
            const v0 = s * hs, v1 = s * (hs - INSET);
            tri(P(-hl, v0, EAVE), P(hl, v0, EAVE), P(hl, v1, BRK)); tri(P(-hl, v0, EAVE), P(hl, v1, BRK), P(-hl, v1, BRK));
            tri(P(-hl, v1, BRK), P(hl, v1, BRK), P(hl, 0, RIDGE)); tri(P(-hl, v1, BRK), P(hl, 0, RIDGE), P(-hl, 0, RIDGE));
          }
          for (const e of [-1, 1]) {
            const u = e * hl;
            const ring = [P(u, -hs, EAVE), P(u, -(hs - INSET), BRK), P(u, 0, RIDGE), P(u, hs - INSET, BRK), P(u, hs, EAVE)];
            for (let i2 = 1; i2 < ring.length - 1; i2++) tri(ring[0], ring[i2], ring[i2 + 1]);
          }
          const g = new THREE.BufferGeometry();
          g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
          g.computeVertexNormals();
          ad(g, '#4a3627');
        }
        const northV = (a.pz < 0) ? 1 : -1;                // v-sign toward Spruce Street
        const fx2 = a.px * northV, fz2 = a.pz * northV;
        // cream pent between the floors and cornice at the eave, street face
        ad(box(a.hl * 2 + 0.5, 0.2, 0.8, ob.cx + fx2 * (a.hs + 0.3), 3.7, ob.cz + fz2 * (a.hs + 0.3), ry), '#e9e3d0');
        ad(box(a.hl * 2 + 0.5, 0.28, 0.55, ob.cx + fx2 * (a.hs + 0.2), EAVE - 0.1, ob.cz + fz2 * (a.hs + 0.2), ry), '#e9e3d0');
        for (const du of [-0.42, 0.42]) {                  // dormers on the street slope
          const dx2 = ob.cx + a.ax * du * a.hl + fx2 * (a.hs - 1.0), dz2 = ob.cz + a.az * du * a.hl + fz2 * (a.hs - 1.0);
          ad(box(1.35, 1.6, 1.5, dx2, BRK - 0.75, dz2, ry), '#efe9dc');
          const dr = new THREE.CylinderGeometry(0.02, 1.05, 1.0, 4);
          dr.rotateY(ry + Math.PI / 4); dr.translate(dx2, BRK + 0.55, dz2);
          ad(dr, '#5b4433');
        }
        ad(box(1.5, 2.6, 1.1, ob.cx - a.ax * (a.hl * 0.42), RIDGE + 0.6, ob.cz - a.az * (a.hl * 0.42), ry), '#67382b');
        liftB(m0, b);
      }
    }
    // Glory Beer Bar & Kitchen, 126 Chestnut (mid-block, Front-2nd): one deep
    // narrow lot — dark cast-iron storefront with granite piers at the street,
    // five brick floors over it, low rear range down the lot
    {
      const bG = getKey('glory');
      if (bG) {
        const m0 = mark();
        const ob = orientedBox(bG.poly);
        const a = obbAxis(ob);
        // street face = whichever OBB face points at Chestnut (north, -z);
        // this lot's LONG axis runs back from the street
        let fdx, fdz, fext, sdx, sdz, sext;
        if (Math.abs(a.az) > Math.abs(a.pz)) {
          const s2 = a.az < 0 ? 1 : -1;
          fdx = a.ax * s2; fdz = a.az * s2; fext = a.hl;
          sdx = a.px; sdz = a.pz; sext = a.hs;
        } else {
          const s2 = a.pz < 0 ? 1 : -1;
          fdx = a.px * s2; fdz = a.pz * s2; fext = a.hs;
          sdx = a.ax; sdz = a.az; sext = a.hl;
        }
        const ryF = Math.atan2(-sdz, sdx);
        const ryD = Math.atan2(-fdz, fdx);
        // all-box massing, no pair coplanar (clears or interpenetrates at a
        // DIFFERENT width). The pier order is ENGAGED — flush with the brick
        // plane, never proud of the building — with the floor-2 glazing set
        // 0.5 m behind it and the ground floor a full 2.4 m walk-in porch.
        // Widths pull 15 cm off each lot line so nothing shimmers against
        // the neighbors' party walls.
        const segW = (back, front, y0s, y1s, w2) => box(front - back, y1s - y0s, w2,
          ob.cx + fdx * ((back + front) / 2), (y0s + y1s) / 2,
          ob.cz + fdz * ((back + front) / 2), ryD);
        const F = fext - 0.55;                              // facade plane, at the block line
        const W2 = sext * 2 - 0.3;
        aw(segW(-fext, F - 9.4, -1.5, 8.0, W2 - 0.16), '#6b4c3f', 3);      // rear range
        aw(segW(F - 10, F - 2.4, -1.5, 4.5, W2 - 0.1), '#191c1f', 3);      // porch back wall
        aw(segW(F - 10, F - 0.5, 4.25, 8.3, W2 - 0.08), '#23262b', 3);     // floor-2 glazing, recessed
        aw(segW(F - 26, F - 0.02, 7.9, 17.8, W2 - 0.06), '#74453a', 5);    // brick floors 3-5
        const wx = ob.cx + fdx * F, wz = ob.cz + fdz * F;   // pier plane = facade plane
        const across = (u) => [wx + sdx * u, wz + sdz * u];
        const half = W2 / 2 - 0.3;
        for (let i2 = 0; i2 < 5; i2++) {                    // engaged granite piers, both floors
          const [px2, pz2] = across(-half + (i2 / 4) * half * 2);
          ad(box(0.5, 8.3, 0.44, px2 - fdx * 0.23, 4.15, pz2 - fdz * 0.23, ryF), '#cfc8b8');
        }
        ad(box(W2 - 0.5, 0.45, 0.42, wx - fdx * 0.25, 4.3, wz - fdz * 0.25, ryF), '#cfc8b8');  // transom beam
        ad(box(W2 + 0.05, 0.55, 0.5, wx - fdx * 0.2, 8.1, wz - fdz * 0.2, ryF), '#c4bdae');    // cornice cap
        // "GLORY" — real lettering on a small canvas texture, heavy geometric
        // sans in red on the white board, hung over the transom
        {
          const cnv = document.createElement('canvas');
          cnv.width = 512; cnv.height = 256;
          const ctx = cnv.getContext('2d');
          ctx.fillStyle = '#f2ede2'; ctx.fillRect(0, 0, 512, 256);
          ctx.fillStyle = '#c0272d';
          ctx.font = '900 142px Futura, "Avenir Next", "Century Gothic", "Arial Black", sans-serif';
          ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
          ctx.fillText('GLORY', 256, 134);
          const tex = new THREE.CanvasTexture(cnv);
          tex.encoding = THREE.sRGBEncoding;
          tex.anisotropy = anisoOf(4);
          const sg = new THREE.Mesh(new THREE.PlaneGeometry(1.05, 0.52),
            new THREE.MeshBasicMaterial({ map: tex }));
          sg.rotation.y = Math.atan2(fdx, fdz);
          // mounted proud of the pier plane like the real board — never clipped
          const [sx3, sz3] = across(-half * 0.25);
          sg.position.set(sx3 + fdx * 0.14, siteY(wx, wz, 'ground') + 5.15, sz3 + fdz * 0.14);
          groupCity.add(sg);
        }
        {  // small weathered-green blade sign on the brick, floors 3-4
          const [bx2, bz2] = across(half * 0.9);
          ad(box(0.3, 3.2, 0.7, bx2 + fdx * 0.28, 11.0, bz2 + fdz * 0.28, ryF), '#3d5347');
        }
        // wrought-iron fence at the sidewalk in front of the porch
        ad(box(W2, 0.9, 0.07, wx + fdx * 1.7, 0.45, wz + fdz * 1.7, ryF), '#1c1e20');
        liftB(m0, bG);
      }
    }
    // Rotten Ralph's, 201 Chestnut (NW corner of 2nd & Chestnut): white-painted
    // corner building whose whole upper floor is a continuous arcade of tall
    // blue-framed round-arched windows wrapping both street faces, corbelled
    // brick parapet band on top, storefront base with striped awnings, blue
    // double door and the hanging corner board sign. Built to the photo; the
    // LiDAR parapet for the lot is ~8.5 m.
    {
      const bR = getKey('ralphs');
      if (bR) {
        const m0 = mark();
        const ob = orientedBox(bR.poly);
        const a = obbAxis(ob);
        let ux = a.ax, uz = a.az;                    // along Chestnut, made WEST
        if (ux > 0) { ux = -ux; uz = -uz; }
        let sx = a.px, sz = a.pz;                    // across, made SOUTH (street)
        if (sz < 0) { sx = -sx; sz = -sz; }
        const W = a.hl * 2;                          // ~14.9 front width
        const D = 9.7;                               // both OSM strips deep
        const Ex = ob.cx - ux * a.hl + sx * a.hs;    // east corner on the front line
        const Ez = ob.cz - uz * a.hl + sz * a.hs;
        const P = (u, d2) => [Ex + ux * u - sx * d2, Ez + uz * u - sz * d2];
        const ryF = Math.atan2(-uz, ux);             // boxes running along the front
        const ryS = Math.atan2(-sz, sx);             // boxes running along 2nd St
        const aS = Math.atan2(sx, sz);               // plane normal toward Chestnut
        const aE = Math.atan2(-ux, -uz);             // plane normal toward 2nd St
        const bx = (u, d2, y, w2, h2, dp2, ry2) => {
          const [px2, pz2] = P(u, d2);
          return box(w2, h2, dp2, px2, y, pz2, ry2 == null ? ryF : ry2);
        };
        const WALL = '#e2dccd', TRIMW = '#eae4d6', BLUE = '#2c4257',
          GLASS = '#20242a', BRICK = '#361e16', DOOR = '#1d2c3d';
        // core block, blank style — every window on it is applied geometry.
        // Its south face lands at d=0.14, east face at u=0.15; applied pieces
        // engage those planes (cross them), never sit coplanar or float.
        aw(bx(W / 2, D / 2 + 0.02, 3.56, W - 0.3, 10.12, D - 0.24), WALL, 3);
        const FS = 0.14, FE = 0.15;                  // wall face planes
        // ---- ground floor, Chestnut face: piers, glass, door ----
        aw(bx(W / 2, 0.06, 1.62, W - 1.1, 3.24, 0.14), GLASS, 3);   // glass, proud of face
        for (const u of [0.5, 4.05, 7.6, 11.15, W - 0.5])           // engaged piers
          ad(bx(u, 0.1, 1.98, 0.46, 3.95, 0.5), TRIMW);
        ad(bx(1.85, 0.03, 1.55, 1.7, 3.1, 0.14), DOOR);             // blue double door
        ad(bx(1.85, 0.08, 3.32, 2.1, 0.42, 0.14), TRIMW);           // door head
        // ground floor, 2nd St face: glass wraps the corner bay, then solid
        aw(bx(0.08, 2.35, 1.62, 3.9, 3.24, 0.14, ryS), GLASS, 3);
        ad(bx(0.02, 0.5, 1.98, 0.5, 3.95, 0.46, ryS), TRIMW);
        ad(bx(0.02, 4.35, 1.98, 0.5, 3.95, 0.46, ryS), TRIMW);
        // striped awning along the Chestnut storefront (blue/white, tilted out)
        {
          const a0 = 2.7, a1 = W - 0.6, n = 26, sw = (a1 - a0) / n;
          for (let i2 = 0; i2 < n; i2++) {
            const g = new THREE.BoxGeometry(sw + 0.01, 0.09, 1.35);
            g.rotateX(-0.5);
            g.rotateY(ryF);
            const [px2, pz2] = P(a0 + (i2 + 0.5) * sw, -0.38);
            g.translate(px2, 3.12, pz2);
            ad(g, i2 % 2 ? '#e6e1d4' : '#25384a');
          }
        }
        // white spandrel band between storefront and the arcade, both faces
        ad(bx(W / 2, 0.02, 4.25, W + 0.04, 0.6, 0.36), TRIMW);
        ad(bx(0.03, D / 2 - 0.1, 4.25, D - 0.2, 0.56, 0.36, ryS), TRIMW);
        // ---- the arcade: 9 bays on Chestnut, 5 on 2nd. (pu,pd) = unit step
        // TOWARD the street off the wall face; planes stack proud of the glass ----
        const bay = (u0, d0, faceA, pu, pd, along) => {
          const y0 = 4.85, y1 = 6.95, r = 0.46;
          const at2 = (k) => P(u0 + pu * k, d0 + pd * k);
          {
            const g = new THREE.PlaneGeometry(0.92, y1 - y0);   // dark glass, rect
            g.rotateY(faceA);
            const [gx2, gz2] = at2(0.05);
            g.translate(gx2, (y0 + y1) / 2, gz2);
            aw(g, GLASS, 3);                        // walls material = truly dark glass
            const c = new THREE.CircleGeometry(r, 12, 0, Math.PI); // arch head glass
            c.rotateY(faceA);
            c.translate(gx2, y1, gz2);
            aw(c, GLASS, 3);
          }
          {
            const rg = new THREE.RingGeometry(r - 0.03, r + 0.1, 16, 1, 0, Math.PI);
            rg.rotateY(faceA);                                   // blue arch ring
            const [rx2, rz2] = at2(0.09);
            rg.translate(rx2, y1, rz2);
            ad(rg, BLUE);
          }
          for (const s2 of [-1, 1]) {                            // blue jambs, engaged
            const ju = faceA === aS ? u0 + s2 * 0.49 : u0 + pu * 0.02;
            const jd = faceA === aS ? d0 + pd * 0.02 : d0 + s2 * 0.49;
            ad(bx(ju, jd, (y0 + y1) / 2, 0.1, y1 - y0, 0.16, along), BLUE);
          }
          const [su2, sd2] = [u0 + pu * 0.05, d0 + pd * 0.05];   // white sill
          ad(bx(su2, sd2, y0 - 0.07, 1.14, 0.13, 0.22, along), TRIMW);
        };
        for (let i2 = 0; i2 < 9; i2++)
          bay(0.72 + (i2 + 0.5) * ((W - 1.44) / 9), FS, aS, 0, -1, ryF);
        for (let i2 = 0; i2 < 5; i2++)
          bay(FE, 1.1 + (i2 + 0.5) * ((D - 1.8) / 5), aE, -1, 0, ryS);
        // ledge above the arches, then the brick parapet band + coping
        ad(bx(W / 2, 0.04, 7.68, W + 0.1, 0.26, 0.4), TRIMW);
        ad(bx(0.05, D / 2 - 0.08, 7.68, D - 0.12, 0.22, 0.4, ryS), TRIMW);
        aw(bx(W / 2, 0.08, 8.26, W + 0.02, 0.95, 0.34), BRICK, 3);
        aw(bx(0.09, D / 2 - 0.06, 8.26, D - 0.08, 0.91, 0.34, ryS), BRICK, 3);
        ad(bx(W / 2, 0.02, 8.8, W + 0.16, 0.18, 0.52), TRIMW);
        ad(bx(0.04, D / 2 - 0.06, 8.8, D + 0.04, 0.15, 0.52, ryS), TRIMW);
        // roof furniture: dark deck, bulkhead, flue
        ad(bx(W / 2, D / 2, 8.68, W - 1.0, 0.14, D - 1.0), '#2e2c28');
        ad(bx(2.6, 7.4, 9.5, 2.4, 1.55, 2.0), '#3a3835');
        {
          const fl = new THREE.CylinderGeometry(0.12, 0.12, 2.3, 8);
          const [px2, pz2] = P(5.4, 6.6);
          fl.translate(px2, 9.8, pz2);
          ad(fl, '#181818');
        }
        // the hanging corner sign: white board, blue border, stacked script
        {
          const cnv = document.createElement('canvas');
          cnv.width = 256; cnv.height = 384;
          const ctx = cnv.getContext('2d');
          ctx.fillStyle = '#f0ece0'; ctx.fillRect(0, 0, 256, 384);
          ctx.strokeStyle = '#274d73'; ctx.lineWidth = 14;
          ctx.strokeRect(10, 10, 236, 364);
          ctx.fillStyle = '#2b527a';
          ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
          ctx.font = 'italic 700 64px Georgia, "Times New Roman", serif';
          ctx.fillText('Rotten', 128, 130);
          ctx.fillText("Ralph's", 128, 230);
          ctx.font = '600 30px Georgia, serif';
          ctx.fillText('BAR', 128, 318);
          const tex = new THREE.CanvasTexture(cnv);
          tex.encoding = THREE.sRGBEncoding;
          tex.anisotropy = anisoOf(4);
          const mat = new THREE.MeshBasicMaterial({ map: tex });
          const yS2 = siteY(Ex, Ez, 'ground') + 5.5;
          const [sx3, sz3] = P(0.28, -0.62);
          for (const s2 of [0, Math.PI]) {           // printed on BOTH faces — never mirrored
            const sg = new THREE.Mesh(new THREE.PlaneGeometry(0.92, 1.42), mat);
            sg.rotation.y = Math.atan2(ux, uz) + s2;
            sg.position.set(sx3 + Math.sin(sg.rotation.y) * 0.012, yS2, sz3 + Math.cos(sg.rotation.y) * 0.012);
            groupCity.add(sg);
          }
        }
        liftB(m0, bR);
      }
    }
    {
      const b = get("Hilton Philadelphia at Penn's Landing");
      if (b) {
        const ob = orientedBox(b.poly);
        const w0 = walls.length, d0 = detail.length;
        aw(buildingGeom(b.poly, b.holes, 70, -1.5), '#d8cbb3', 2);
        ad(box(22, 4, 12, ob.cx, 72, ob.cz, ryAlign(obbAxis(ob).ax, obbAxis(ob).az)), '#b9ad98');
        lift(w0, d0, glassParts2.length, siteY(ob.cx, ob.cz, 'ground'));
      }
    }
    {
      // Independence Hall: the OSM footprint is the ENTIRE 84 m complex (main
      // block + hyphens + wings), so nothing here may scale off the raw OBB —
      // that put 100 m white bands across the facade. Explicit massing instead:
      // the 33x13.4 gable block with ridge balustrade, end chimneys and string
      // courses, hyphen arcades, two-story end wings, and the staged steeple.
      const b = get('Independence Hall');
      const obIH = b ? orientedBox(b.poly) : null;
      if (obIH) {
        const m0 = mark();
        const a = obbAxis(obIH);
        const ry = ryAlign(a.ax, a.az);
        const sV = (a.pz > 0) ? 1 : -1;
        const Sx = a.px * sV, Sz = a.pz * sV;            // unit vector pointing SOUTH
        // pt(u, s): u along the block axis from the center, s meters SOUTH of the
        // complex's north face
        const pt2 = (u, s) => [obIH.cx + a.ax * u + Sx * (s - a.hs), obIH.cz + a.az * u + Sz * (s - a.hs)];
        const BW = 16.45, BD = 13.4;                     // main block half-width / depth
        const bc = pt2(0, BD / 2);
        aw(box(BW * 2, 13.5, BD, bc[0], 5.25, bc[1], ry), '#7e4534', 0);
        {                                                // footprint-true gable roof
          const q = [pt2(-BW, 0.05), pt2(BW, 0.05), pt2(BW, BD - 0.05), pt2(-BW, BD - 0.05)];
          const g = quadGable(q, 12, 15.2);
          ad(g.slopes, '#4a463f');
          aw(g.ends, '#7e4534', 0);
          for (const ev of g.eaves) {
            ad(box(ev.len + 0.1, 0.4, 0.55,
              (ev.a[0] + ev.b[0]) / 2, 11.9, (ev.a[1] + ev.b[1]) / 2,
              Math.atan2(-(ev.b[1] - ev.a[1]), ev.b[0] - ev.a[0])), '#efeadb');
          }
        }
        ad(box(19, 0.85, 3.0, bc[0], 15.5, bc[1], ry), '#eee9da');                 // ridge-deck balustrade
        for (const s of [-1, 1]) {                                                  // paired end chimney masses
          const e2 = pt2(s * (BW - 1.0), BD / 2);
          ad(box(1.4, 3.6, 5.0, e2[0], 16.2, e2[1], ry), '#6e3c2d');
        }
        for (const s2 of [0.03, BD - 0.03]) {                                       // marble string courses
          const c2 = pt2(0, s2);
          ad(box(BW * 2 + 0.2, 0.42, 0.22, c2[0], 5.2, c2[1], ry), '#e6e0d0');
        }
        // hyphen arcades and two-story wing pavilions
        for (const s of [-1, 1]) {
          const wingU = s * (a.hl - 5.6);
          const hy0 = BW, hy1 = a.hl - 11.2;
          if (hy1 > hy0 + 1.5) {
            const hc = pt2(s * (hy0 + hy1) / 2, 4.8);
            aw(box(hy1 - hy0, 5.6, 9.4, hc[0], 2.8, hc[1], ry), '#7e4534', 4);
            ad(box(hy1 - hy0 + 0.2, 0.4, 9.7, hc[0], 5.8, hc[1], ry), '#efeadb');
          }
          const wc = pt2(wingU, 6.0);
          aw(box(11, 8.4, 12, wc[0], 3.4, wc[1], ry), '#7e4534', 0);
          ad(box(11.3, 0.45, 12.3, wc[0], 8.55, wc[1], ry), '#efeadb');
          const cap = new THREE.CylinderGeometry(0.6, 8.1, 2.6, 4);
          cap.rotateY(ry + Math.PI / 4);
          cap.translate(wc[0], 8.8 + 1.3, wc[1]);
          ad(cap, '#4a463f');
        }
        // engaged tower on the south (Independence Square) face
        const [tx, tz] = pt2(0, BD + 2.6);
        aw(box(9, 21, 9, tx, 10.5, tz, ry), '#7e4534', 1);                          // brick shaft, arched windows
        ad(box(9.9, 0.55, 9.9, tx, 21.15, tz, ry), '#efeadb');                      // cornice
        ad(box(9.1, 0.8, 9.1, tx, 21.8, tz, ry), '#efeadb');                        // balustrade
        ad(box(7.2, 6.2, 7.2, tx, 22.2 + 3.1, tz, ry), '#efeadb');                  // clock stage
        for (const [ux2, uz2] of [[a.ax, a.az], [-a.ax, -a.az], [a.px, a.pz], [-a.px, -a.pz]]) {
          const rim = new THREE.CylinderGeometry(1.7, 1.7, 0.22, 16);
          rim.rotateZ(Math.PI / 2); rim.rotateY(Math.atan2(-uz2, ux2));
          rim.translate(tx + ux2 * 3.65, 25.4, tz + uz2 * 3.65);
          ad(rim, '#3a3d3b');
          const dial = new THREE.CylinderGeometry(1.42, 1.42, 0.3, 16);
          dial.rotateZ(Math.PI / 2); dial.rotateY(Math.atan2(-uz2, ux2));
          dial.translate(tx + ux2 * 3.72, 25.4, tz + uz2 * 3.72);
          ad(dial, '#f3efe2');
        }
        ad(box(5.6, 5.4, 5.6, tx, 28.4 + 2.7, tz, ry), '#efeadb');                  // bell chamber
        for (const [ux2, uz2] of [[a.ax, a.az], [-a.ax, -a.az], [a.px, a.pz], [-a.px, -a.pz]]) {
          ad(box(2.3, 3.7, 0.24, tx + ux2 * 2.85, 30.9, tz + uz2 * 2.85, Math.atan2(-uz2, ux2)), '#2e2c28'); // open arches
        }
        ad(box(6.2, 0.7, 6.2, tx, 33.85, tz, ry), '#efeadb');                       // upper balustrade
        const bell = new THREE.CylinderGeometry(1.3, 3.95, 3.0, 8);
        bell.rotateY(ry + Math.PI / 8); bell.translate(tx, 34.2 + 1.5, tz);
        ad(bell, '#3c3933');                                                        // dark bell roof
        const drum = new THREE.CylinderGeometry(1.5, 1.7, 2.4, 8);
        drum.translate(tx, 37.2 + 1.2, tz);
        ad(drum, '#efeadb');
        const spire = new THREE.ConeGeometry(1.15, 9.5, 8);
        spire.translate(tx, 39.6 + 4.75, tz);
        ad(spire, '#efeadb');
        const orb = new THREE.SphereGeometry(0.4, 8, 6);
        orb.translate(tx, 49.4, tz);
        ad(orb, '#c8a44e');                                                         // gilt ball + vane mast
        const vane = new THREE.CylinderGeometry(0.06, 0.06, 2.4, 5);
        vane.translate(tx, 49.4 + 1.2, tz);
        ad(vane, '#d8d2c2');
        liftB(m0, b);
      }
    }
    for (const nm of ['Congress Hall', 'Old City Hall']) {
      const r = classic(nm, { wall: '#8e4a38', trim: '#f0ede4', eave: 11, ridge: 14.5, roof: 'gable', roofCol: '#4d4a45', chimneys: 2, style: 0 });
      if (r) { const m0 = mark(); cupolaGeoms(r.ob.cx, r.ob.cz, 14.2, 2.4, 5).forEach(g => ad(g, '#f0ede4')); liftB(m0, r.b); }
    }
    {
      const r = classic("Carpenters' Hall", { wall: '#8e4a38', trim: '#f0ede4', eave: 11, ridge: 14, roof: 'hip', roofCol: '#4d4a45', style: 0 });
      if (r) { const m0 = mark(); cupolaGeoms(r.ob.cx, r.ob.cz, 13.8, 2.2, 4.5).forEach(g => ad(g, '#f0ede4')); liftB(m0, r.b); }
    }
    {
      const r = classic('Second Bank of the United States', { wall: '#d9d4c6', trim: '#e6e2d8', eave: 14, ridge: 17.5, roof: 'gable', roofCol: '#6e7276', gableEndsTrim: true, style: 1 });
      if (r) { // Doric octastyle porticos on both short fronts, on marble stylobates
        const m0 = mark();
        for (const dir of [[0, -1], [0, 1]]) {
          const e = obbEnd(r.ob, dir[0], dir[1]);
          const hw = r.a.hs - 1.5;
          ad(box(hw * 2 + 3.4, 2.6, 5.2, e.x + e.ax * 2, -0.6, e.z + e.az * 2, ryAlign(r.a.px, r.a.pz)), '#ddd8ca');
          columnRow(e.x + e.ax * 2 - r.a.px * hw, e.z + e.az * 2 - r.a.pz * hw, e.x + e.ax * 2 + r.a.px * hw, e.z + e.az * 2 + r.a.pz * hw, 8, 9, 0.55, 0.6)
            .forEach(g => ad(g, '#e6e2d8'));
          ad(box(hw * 2 + 2.2, 1.6, 2.4, e.x + e.ax * 2, 10.4, e.z + e.az * 2, ryAlign(r.a.px, r.a.pz)), '#e6e2d8');
        }
        liftB(m0, r.b);
      }
    }
    {
      const r = classic('First Bank of the United States', { wall: '#9a5b45', trim: '#e6e2d8', eave: 14, ridge: 17, roof: 'hip', roofCol: '#6e7276', style: 1 });
      if (r) { // marble Corinthian portico on the 3rd St (west) front
        const m0 = mark();
        const e = obbEnd(r.ob, -1, 0);
        const hw = r.a.hs - 1.6;
        ad(box(hw * 2 + 3, 2.6, 4.8, e.x + e.ax * 1.8, -0.6, e.z + e.az * 1.8, ryAlign(r.a.px, r.a.pz)), '#ddd8ca');
        columnRow(e.x + e.ax * 1.8 - r.a.px * hw, e.z + e.az * 1.8 - r.a.pz * hw, e.x + e.ax * 1.8 + r.a.px * hw, e.z + e.az * 1.8 + r.a.pz * hw, 6, 10, 0.5, 0.5)
          .forEach(g => ad(g, '#e6e2d8'));
        ad(box(hw * 2 + 2, 1.5, 2.2, e.x + e.ax * 1.8, 11.3, e.z + e.az * 1.8, ryAlign(r.a.px, r.a.pz)), '#e6e2d8');
        liftB(m0, r.b);
      }
    }

    // --- Head House Square's big neighbors (OPA parcel + LiDAR massing)
    {
      // Abbotts Square (1982-85): L-shaped block, 8 levels on 2nd St stepping down westward along South St
      const b = getKey('abbotts');
      if (b) {
        const m0 = mark();
        const S = (x) => 464 + (x + 97) * 0.1727;   // South St face
        const N = (x) => 428 + (x + 131) * 0.1625;  // north face of the South St wing
        const brick = '#9a6646', cream = '#e7dfd0';
        const wing = (poly, h, hex, st) => aw(buildingGeom(poly, null, h, -1.5), hex, st == null ? 6 : st);
        wing([[-80, 366], [-97, 464], [-123.6, 459.4], [-106.6, 361.4]], 28.5, brick);            // 2nd St wing (square ends)
        wing([[-97, S(-97)], [-150, S(-150)], [-150, N(-150)], [-97, N(-97)]], 27, brick);            // South St wing, east third
        wing([[-150, S(-150)], [-200, S(-200)], [-200, N(-200)], [-150, N(-150)]], 23, brick);        // middle
        wing([[-200, S(-200)], [-236, S(-236)], [-236, N(-236)], [-200, N(-200)]], 20, brick);        // west end at 3rd St
        wing([[-203, S(-203) - 3], [-233, S(-233) - 3], [-233, N(-233) + 3], [-203, N(-203) + 3]], 22.2, '#e4e2dc', 2); // set-back penthouse
        wing([[-131, N(-131)], [-211, N(-211)], [-211, N(-211) - 13], [-131, N(-131) - 13]], 12.5, brick, 2); // garden-level bar inside the L
        // cream string courses at the top of the double-height retail and along the parapets
        const course = (ax, az, bx, bz, y) => ad(box(Math.hypot(bx - ax, bz - az) + 0.3, 0.45, 0.35, (ax + bx) / 2, y, (az + bz) / 2, ryAlign(bx - ax, bz - az)), cream);
        course(-80, 366, -97, 464, 6.6); course(-80, 366, -97, 464, 28.3);
        course(-97, 464, -236, 440, 6.6); course(-97, 464, -150, 454.8, 26.8); course(-150, 454.8, -200, 446.2, 22.8); course(-200, 446.2, -236, 440, 19.8);
        ad(box(6, 2.6, 6, -88, 29.8, 372, 0), '#cfcac0'); ad(box(6, 2.6, 6, -100, 29.8, 455, 0), '#cfcac0'); // elevator bulkheads
        liftAt(m0, -110, 430);
      }
    }
    {
      // 410 at Society Hill (Toll Brothers, 2015): 4 storeys of red brick with cream bays on a garage podium
      const b = getKey('ten410');
      if (b) {
        const m0 = mark();
        aw(buildingGeom(b.poly, b.holes, 16.8, -1.5), '#9c4b3f', 2);
        let mx = -1e9, mz = 1e9;
        for (const q of b.poly) { mx = Math.max(mx, q[0]); mz = Math.min(mz, q[1]); }
        ad(box(9, 4.5, 9, mx - 7, 16.8 + 2.25, mz + 8, 0), '#cfcac0');
        liftB(m0, b);
      }
    }
    {
      // The Residences at Dockside: stepped ziggurat slab on its pier — a 4-storey
      // podium, then floors that rake down long toward the shore (west) and steeply
      // toward the river, rooftop sail sculptures just east of the summit's center
      const b = get('The Residences at Dockside');
      if (b) {
        const m0 = mark();
        const ob = orientedBox(b.poly);
        const a2 = obbAxis(ob);
        const rya = ryAlign(a2.ax, a2.az);
        const eS = a2.ax > 0 ? 1 : -1;                 // +axis*eS points east (to the river)
        const FP = 2.75, POD = 4 * FP;                 // floor pitch locked to the style-7 shader grid
        const uMax = a2.hl * 0.97;
        // the footprint is Z-shaped: the slab proper is the river half's width, and the
        // extra strip on the shore half is podium only — measure both from the polygon
        const uvOf = (q) => [((q[0] - ob.cx) * a2.ax + (q[1] - ob.cz) * a2.az) * eS, (q[0] - ob.cx) * a2.px + (q[1] - ob.cz) * a2.pz];
        const span = (u0, u1) => {
          let lo = 1e9, hi = -1e9;
          for (const q of b.poly) { const [u, v] = uvOf(q); if (u < u0 || u > u1) continue; lo = Math.min(lo, v); hi = Math.max(hi, v); }
          return hi - lo > 12 ? [lo, hi] : [-a2.hs, a2.hs];
        };
        const [vLo, vHi] = span(5, 60);                // slab width (river half, clear of the east fingers)
        const [wLo, wHi] = span(-1e9, -5);             // full podium width on the shore half
        const v0 = vLo + 0.8, v1 = vHi - 0.8, vC = (vLo + vHi) / 2;
        const at = (u, v) => [ob.cx + a2.ax * eS * u + a2.px * v, ob.cz + a2.az * eS * u + a2.pz * v];
        const rect = (ue0, ue1) => [[-ue0, v0], [ue1, v0], [ue1, v1], [-ue0, v1]].map(([u, v]) => at(u, v));
        // podium: cream precast garage base with a terracotta waterline band, a dark
        // opening band, the oval-porthole band up top, and the round vent near the river end
        aw(buildingGeom(b.poly, b.holes, POD, -1.5), '#e0d2b6', 3);
        for (const [y, h, out, hex] of [[1.1, 2.3, 0.35, '#a5715f'], [5.1, 2.0, 0.15, '#6b645a'], [POD - 1.6, 1.5, 0.15, '#57514a']]) {
          for (const [u0, u1, lo, hi] of [[-uMax, 2, wLo, wHi], [2, uMax - 4, vLo, vHi]]) {
            const [px2, pz2] = at((u0 + u1) / 2, (lo + hi) / 2);
            ad(box(u1 - u0, h, hi - lo + out * 2, px2, y, pz2, rya), hex);
          }
        }
        {
          const vg = new THREE.CylinderGeometry(3.4, 3.4, vHi - vLo + 0.5, 20);
          vg.rotateX(Math.PI / 2); vg.rotateY(rya);
          const [vx, vz] = at(uMax - 10, vC);
          vg.translate(vx, POD - 4.2, vz);
          ad(vg, '#8fb4a4');                           // ship's-wheel garage vent
        }
        // tower: sheer full-height slab on the river half, ~7 two-storey terraced
        // setbacks cascading toward the shore; floors on the 2.75 m shader grid
        const uET = uMax - 6.5;                        // stop short of the pier's east fingers
        let topC = 0, topY = POD;
        for (let i = 0; i < 14; i++) {
          const uW2 = uET - 8.1 * Math.floor(i / 2);
          if (uET + uW2 < 18) break;
          const y0 = POD + FP * i, y1 = y0 + FP;
          aw(buildingGeom(rect(uW2, uET), null, y1, y0), '#d9c7a6', 7);
          const cU = (uET - uW2) / 2, len = (uET + uW2) * 0.96;
          for (const vR of [v0 - 0.7, v1 + 0.7]) {     // continuous balcony rails on both long faces
            const [rx, rz] = at(cU, vR);
            ad(box(len, 0.22, 1.4, rx, y0 + 1.15, rz, rya), '#cfc2a5');
          }
          topC = cU; topY = y1;
        }
        // three tilted ship-funnel wind scoops over the river-end roof
        for (const du of [-11, -5, 1]) {
          const fg = new THREE.CylinderGeometry(1.5, 1.8, 7.5, 12);
          fg.rotateZ(0.22 * eS); fg.rotateY(rya);
          const [fx, fz] = at(uET * 0.65 + du, vC);
          fg.translate(fx, topY + 3.4, fz);
          ad(fg, '#b6bcbf');
        }
        for (const vR of [v0 - 0.35, v1 + 0.35]) {     // seafoam glass accent on the west run
          const [gx, gz] = at(-uET * 0.55, vR);
          ad(box(4.5, 16, 0.5, gx, POD + 8, gz, rya), '#9fc4b4');
        }
        liftB(m0, b);
      }
    }
    {
      // New Market Complex (1970s): 3-storey brown brick commercial block at 2nd & Lombard
      const b = getKey('newmarket');
      if (b) { const m0 = mark(); aw(buildingGeom(b.poly, b.holes, 11.5, -1.5), '#7f4b3b', 5); liftB(m0, b); }
    }
    {
      // New Market Garage (1976): concrete parking decks with a 2-storey brick liner on 2nd St
      const b = get('New Market Garage');
      if (b) {
        const m0 = mark();
        aw(buildingGeom(b.poly, b.holes, 9.9, -1.5), '#b4b2aa', 3);
        aw(box(9, 8, 33, -75.5, 4, 334.5, 0), '#6f3b30', 5);
        aw(box(6, 13.5, 6, -90, 6.75, 345, 0), '#6f3b30', 3);
        liftB(m0, b);
      }
    }

    if (walls.length) {
      const m = new THREE.Mesh(mergeColored(walls, true, true), cityMat);
      m.castShadow = m.receiveShadow = true;
      groupCity.add(m);
      rayTargets.push(m);
    }
    if (detail.length) {
      const m = new THREE.Mesh(mergeColored(detail),
        new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.8, side: THREE.DoubleSide }));
      m.castShadow = m.receiveShadow = true;
      groupCity.add(m);
    }
    if (glassParts2.length) {
      const m = new THREE.Mesh(mergeColored(glassParts2, false, 'base'),
        new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.06, metalness: 0.85, envMapIntensity: 1.7 }));
      m.castShadow = true;
      groupCity.add(m);
      rylandGlassMat = m.material;
      // Night, photo-matched: scattered warm per-panel apartment lights and
      // fully glowing lobby/amenity glass over the lowest floors of each piece
      // (aBase carries every merged part's ground lift). A flat material-wide
      // emissive used to wash the bars to one dead tone.
      rylandGlassMat.onBeforeCompile = (shader) => {
        shader.uniforms.uNight = nightUniform;
        shader.vertexShader = shader.vertexShader
          .replace('#include <common>', '#include <common>\nattribute float aBase;\nvarying float vRyB;\nvarying vec3 vRyW;')
          .replace('#include <begin_vertex>', '#include <begin_vertex>\nvRyB = aBase;\nvRyW = (modelMatrix * vec4(transformed, 1.0)).xyz;');
        shader.fragmentShader = shader.fragmentShader
          .replace('#include <common>', '#include <common>\nuniform float uNight;\nvarying float vRyB;\nvarying vec3 vRyW;\n' +
            // sin-lattice hashes streak along the grid (lit "worms"); this
            // fract-cascade hash is uniform on integer cells
            'float ryh(vec3 p){ p = fract(p * vec3(0.1031, 0.11369, 0.13787)); p += dot(p, p.yzx + 19.19); return fract((p.x + p.y) * p.z); }')
          .replace('#include <emissivemap_fragment>',
            '#include <emissivemap_fragment>\n{\n' +
            // the lit lattice must live in FACADE space, not world axes: the
            // building sits on the rotated grid, so world-x/z cells sliced
            // diagonally across the real panels (half-lit fragments). Derive
            // the along-facade axis per fragment from the surface derivatives;
            // 3.0 m matches the mullion bays, 3.13 m the floor bands, and the
            // face normal keys each face so opposite walls light independently.
            '  float relY = vRyW.y - vRyB;\n' +
            '  vec3 fn = normalize(cross(dFdx(vRyW), dFdy(vRyW)));\n' +
            '  vec2 tanH = normalize(vec2(-fn.z, fn.x) + vec2(1e-4, 0.0));\n' +
            '  float u = dot(vRyW.xz, tanH);\n' +
            '  vec3 cell = floor(vec3(u / 3.0, relY / 3.13, dot(floor(fn.xz * 4.0), vec2(1.0, 9.0))));\n' +
            '  float lit = step(0.74, ryh(cell));\n' +
            '  vec3 warm = vec3(1.0, 0.84, 0.60) * (0.7 + 0.55 * ryh(cell + 7.0));\n' +
            '  float amen = 1.0 - smoothstep(9.2, 10.6, relY);\n' +
            '  totalEmissiveRadiance += warm * max(lit * 0.8, amen * 1.15) * uNight;\n' +
            '}');
      };
    }
  });

  // ------------------------------------------------ museum ships
  step('Mooring the ships', () => {
    const parts = [];
    const W = TERRAIN.water;
    const add = (geom, hex) => parts.push({ geom, color: new THREE.Color(hex), style: 3 });
    for (const b of D.buildings) {
      if (b.t !== 'ship' || !b.poly || b.poly.length < 3) continue;
      const ob = orientedBox(b.poly);
      if (!ob) continue;
      const a = obbAxis(ob);
      const L = a.hl * 2, B = a.hs * 2;
      const ry = Math.atan2(-a.az, a.ax);
      const name = (b.name || '').toLowerCase();
      const at = (u, v) => [ob.cx + a.ax * u + a.px * v, ob.cz + a.az * u + a.pz * v];
      if (name.includes('becuna')) {            // submarine: low black hull, sail
        add(extrudePoly(b.poly, null, W + 3.0, W - 0.3), '#26282a');
        const [sx, sz] = at(L * 0.05, 0);
        add(box(9, 8, 3.2, sx, W + 3 + 4, sz, ry), '#2a2d30');
      } else if (name.includes('moshulu')) {    // four-masted barque
        add(extrudePoly(b.poly, null, W + 8.5, W - 0.3), '#202224');
        add(box(L * 0.97, 0.9, B + 0.25, ob.cx, W + 7.9, ob.cz, ry), '#e9e6de');
        for (const f of [-0.32, -0.1, 0.14, 0.36]) {
          const [mx, mz] = at(L * f, 0);
          const mast = new THREE.CylinderGeometry(0.32, 0.5, 46, 8);
          mast.translate(mx, W + 8.5 + 23, mz);
          add(mast, '#4a4742');
          for (const yh of [18, 30, 40]) add(box(22, 0.3, 0.3, mx, W + 8.5 + yh, mz, ry + Math.PI / 2), '#3e3b37');
        }
      } else {                                   // USS Olympia: white hull, buff superstructure
        add(extrudePoly(b.poly, null, W + 8, W - 0.3), '#e8e6df');
        add(box(L * 0.5, 4, B * 0.7, ob.cx, W + 8 + 2, ob.cz, ry), '#d8c9a0');
        for (const f of [-0.12, 0.12]) {
          const [fx, fz] = at(L * f, 0);
          const fun = new THREE.CylinderGeometry(1.3, 1.4, 8, 10);
          fun.translate(fx, W + 12 + 4, fz);
          add(fun, '#cdbd93');
        }
        for (const f of [-0.3, 0.3]) {
          const [mx, mz] = at(L * f, 0);
          const mast = new THREE.CylinderGeometry(0.3, 0.45, 30, 8);
          mast.translate(mx, W + 8 + 15, mz);
          add(mast, '#4a4742');
        }
      }
    }
    if (parts.length) {
      const m = new THREE.Mesh(mergeColored(parts), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.7, side: THREE.DoubleSide }));
      m.castShadow = true;
      groupCity.add(m);
    }
  });

  // ------------------------------------------------ the three towers
  step('Casting the concrete grid', () => {
    const concreteParts = [], glassParts = [], variedParts = [];
    const cSum = new V3();
    for (const t of towers) cSum.add(new V3(t.centroid[0], 0, t.centroid[1]));
    if (towers.length) towersCenter.copy(cSum.multiplyScalar(1 / towers.length));

    for (let ti = 0; ti < towers.length; ti++) {
      const t = towers[ti];
      const W = t.width_m, Dp = t.depth_m, H = TOWER.height;
      const cx = t.centroid[0], cz = t.centroid[1], ang = -(t.angleRad || 0);
      const floors = TOWER.floors;
      const floorH = (H - TOWER.lobbyH - TOWER.parapetH) / floors; // ~2.91 m
      const gridBot = TOWER.lobbyH, gridTop = H - TOWER.parapetH;
      const gridH = gridTop - gridBot;
      const rot = new THREE.Matrix4().makeRotationY(ang).setPosition(cx, 0, cz);
      const podium = siteY(towersCenter.x, towersCenter.z, 'ground');
      const add = (arr, g, color) => { g.applyMatrix4(rot); g.translate(0, podium, 0); arr.push({ geom: g, color, baseY: podium }); }; // towers stand on the 1 m plaza podium
      const cCon = new THREE.Color(COLORS.concrete);
      const cConD = new THREE.Color(COLORS.concreteDark);

      // per facade: local +x along width, +z along depth
      const sides = [
        { len: W, off: Dp / 2, axis: 'x' },
        { len: W, off: -Dp / 2, axis: 'x' },
        { len: Dp, off: W / 2, axis: 'z' },
        { len: Dp, off: -W / 2, axis: 'z' },
      ];
      for (const s of sides) {
        const inner = s.len - 2 * TOWER.cornerW;
        // researched facade: 18 bays on the wide faces, 12 on the narrow — fixed, not
        // derived from the OSM footprint (which rounds to 17/11 on two of the towers)
        const bays = s.len >= Math.max(W, Dp) - 0.01 ? 18 : 12;
        const bayW = inner / bays;
        // vertical mullions between window bays, lobby soffit to parapet
        for (let bi = 1; bi < bays; bi++) {
          const u = -inner / 2 + bi * bayW;
          const g = s.axis === 'x'
            ? box(TOWER.mullionW, gridH, TOWER.mullionD, u, gridBot + gridH / 2, s.off)
            : box(TOWER.mullionD, gridH, TOWER.mullionW, s.off, gridBot + gridH / 2, u);
          add(concreteParts, g, cCon);
        }
        // horizontal spandrel bands at each floor line
        for (let fi = 1; fi < floors; fi++) {
          const y = gridBot + fi * floorH;
          const g = s.axis === 'x'
            ? box(inner + TOWER.mullionW, TOWER.spandrelH, TOWER.mullionD * 0.96, 0, y, s.off)
            : box(TOWER.mullionD * 0.96, TOWER.spandrelH, inner + TOWER.mullionW, s.off, y, 0);
          add(concreteParts, g, cCon);
        }
        // soffit band where the grid lands on the colonnade
        const soff = s.axis === 'x'
          ? box(s.len + TOWER.mullionD, 1.0, TOWER.mullionD + 0.12, 0, gridBot, s.off)
          : box(TOWER.mullionD + 0.12, 1.0, s.len + TOWER.mullionD, s.off, gridBot, 0);
        add(concreteParts, soff, cCon);
        // plain fascia/parapet band capping the facade
        const fas = s.axis === 'x'
          ? box(s.len + TOWER.mullionD, TOWER.parapetH + 0.5, TOWER.mullionD + 0.08, 0, H - (TOWER.parapetH + 0.5) / 2 + 0.25, s.off)
          : box(TOWER.mullionD + 0.08, TOWER.parapetH + 0.5, s.len + TOWER.mullionD, s.off, H - (TOWER.parapetH + 0.5) / 2 + 0.25, 0);
        add(concreteParts, fas, cCon);
        // recessed glass curtain behind the grid
        const gOff = s.off > 0 ? s.off - TOWER.glassInset : s.off + TOWER.glassInset;
        const gGeom = s.axis === 'x'
          ? box(inner, gridH, 0.1, 0, gridBot + gridH / 2, gOff)
          : box(0.1, gridH, inner, gOff, gridBot + gridH / 2, 0);
        add(glassParts, gGeom, new THREE.Color(COLORS.glass));
        // sparse per-window variation (curtains, blinds, interior depth)
        for (let fi = 0; fi < floors; fi++) {
          for (let bi = 0; bi < bays; bi++) {
            const r = hash01(ti * 977 + s.off * 31 + fi * 13.7 + bi * 3.1);
            if (r > 0.26) continue;
            const u = -inner / 2 + (bi + 0.5) * bayW;
            const y = gridBot + (fi + 0.5) * floorH + TOWER.spandrelH / 4;
            const wW = Math.max(0.5, bayW - TOWER.mullionW - 0.35);
            const wH = floorH - TOWER.spandrelH - 0.3;
            const shade = r < 0.075
              ? new THREE.Color(0xd6ccb4).multiplyScalar(0.85 + hash01(r * 999) * 0.3)  // curtain
              : new THREE.Color(0x2b2f38).multiplyScalar(0.85 + hash01(r * 777) * 0.5); // depth variation
            const vOff = s.off > 0 ? s.off - TOWER.glassInset + 0.07 : s.off + TOWER.glassInset - 0.07;
            const g = s.axis === 'x'
              ? box(wW, wH, 0.04, u, y, vOff)
              : box(0.04, wH, wW, vOff, y, u);
            add(variedParts, g, shade);
          }
        }
        // lobby colonnade: slender columns every Nth grid line, ends included
        const nCols = Math.round(bays / TOWER.colSpacing);
        for (let ci = 0; ci <= nCols; ci++) {
          const u = -inner / 2 + (ci / nCols) * inner;
          // columns run 0.9 m below grade like every wall — the plaza drape is not
          // perfectly at podium height everywhere, and a floating column base reads
          // as clipping at eye level
          const g = s.axis === 'x'
            ? box(0.55, gridBot + 0.9, 0.55, u, gridBot / 2 - 0.45, s.off)
            : box(0.55, gridBot + 0.9, 0.55, s.off, gridBot / 2 - 0.45, u);
          add(concreteParts, g, cCon);
        }
      }
      // solid corner piers, soffit line to roof (the grid turns the corner as an L)
      for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
        add(concreteParts,
          box(TOWER.cornerW + TOWER.mullionD, H - gridBot, TOWER.cornerW + TOWER.mullionD,
            sx * (W / 2 - TOWER.cornerW / 2), gridBot + (H - gridBot) / 2, sz * (Dp / 2 - TOWER.cornerW / 2)),
          cCon);
      }
      // roof deck + long set-back mechanical penthouse strip
      add(concreteParts, box(W - 0.8, 0.45, Dp - 0.8, 0, gridTop - 0.2, 0), cConD);
      add(concreteParts, box(W * 0.62, TOWER.penthouseH, Dp * 0.44, 0, gridTop + TOWER.penthouseH / 2, 0), cConD);
      // lobby glass, deeply recessed behind the colonnade (runs 0.8 m below grade
      // like the columns so no ground slit can ever show under it)
      add(glassParts,
        box(W - TOWER.lobbyInset * 2, gridBot + 0.55, Dp - TOWER.lobbyInset * 2, 0, (gridBot - 1.05) / 2, 0),
        new THREE.Color(COLORS.glassLobby));
      // interior mass, faintly visible through the glass
      add(concreteParts, box(W - 2.2, gridH, Dp - 2.2, 0, gridBot + gridH / 2, 0), new THREE.Color(0x514c45));

      // collision footprint
      const hw = W / 2 + 0.3, hd = Dp / 2 + 0.3;
      const cos = Math.cos(ang), sin = Math.sin(ang);
      const cor = [[-hw, -hd], [hw, -hd], [hw, hd], [-hw, hd]].map(([lx, lz]) =>
        [cx + lx * cos + lz * sin, cz - lx * sin + lz * cos]);
      for (let k = 0; k < 4; k++) addColSeg(cor[k][0], cor[k][1], cor[(k + 1) % 4][0], cor[(k + 1) % 4][1]);
      registerPoly(cor);
    }

    const conMesh = new THREE.Mesh(
      mergeColored(concreteParts, true),
      new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.82, metalness: 0, envMapIntensity: 0.3 })
    );
    conMesh.castShadow = conMesh.receiveShadow = true;
    groupCity.add(conMesh);
    rayTargets.push(conMesh);

    const glassMesh = new THREE.Mesh(
      mergeColored(glassParts),
      new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.1, metalness: 0.7, envMapIntensity: 1.4 })
    );
    groupCity.add(glassMesh);
    towerGlassMat = glassMesh.material;
    towerGlassMat.emissive = new THREE.Color(0xffd9a0);
    towerGlassMat.emissiveIntensity = 0;

    if (variedParts.length) {
      const vm = new THREE.Mesh(
        mergeColored(variedParts),
        new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.6, metalness: 0.1 })
      );
      groupCity.add(vm);
      towerVarMat = vm.material;
      towerVarMat.emissive = new THREE.Color(0xffd08a);
      towerVarMat.emissiveIntensity = 0;
    }

    // brick-paved plaza + Baskin bronze ("Old Man, Young Man, The Future", 1966)
    if (towers.length === 3) {
      // raised brick plaza over the garage, with a step ring and lawn berms around it
      const plazaMat = new THREE.MeshStandardMaterial({ color: COLORS.plaza, roughness: 0.96 });
      const plaza = new THREE.Mesh(new THREE.CylinderGeometry(PLAZA_R, PLAZA_R, 1.0 + LAYER.plaza, 48), plazaMat);
      plaza.position.set(towersCenter.x, cityY(towersCenter.x, towersCenter.z) + (1.0 + LAYER.plaza) / 2, towersCenter.z);
      plaza.receiveShadow = plaza.castShadow = true;
      groupCity.add(plaza);
      const stepRing = new THREE.Mesh(new THREE.CylinderGeometry(PLAZA_R + 2.4, PLAZA_R + 2.4, 0.5, 48),
        new THREE.MeshStandardMaterial({ color: 0xb3ab9c, roughness: 0.95 }));
      stepRing.position.set(towersCenter.x, cityY(towersCenter.x, towersCenter.z) + 0.25, towersCenter.z);
      stepRing.receiveShadow = true;
      groupCity.add(stepRing);
      const bermMat = new THREE.MeshStandardMaterial({ color: COLORS.park, roughness: 1 });
      for (let k = 0; k < 7; k++) {
        const ang = k * (Math.PI * 2 / 7) + 0.4;
        const rr = PLAZA_R + 24 + hash01(k * 3.1) * 14;
        const bx = towersCenter.x + Math.cos(ang) * rr, bz = towersCenter.z + Math.sin(ang) * rr;
        if (nearRoad(bx, bz, 6) || insideBuilding(bx, bz) || nearBuildingEdge(bx, bz, 9) || Math.hypot(bx - 16, bz - 77) < 48) continue;
        const berm = new THREE.Mesh(new THREE.SphereGeometry(1, 14, 8), bermMat);
        berm.scale.set(13 + hash01(k) * 6, 1.5, 6 + hash01(k * 7) * 3);
        berm.rotation.y = ang + Math.PI / 2;
        bermSpots.push([bx, bz, berm.scale.x, berm.scale.z, berm.rotation.y]);
        berm.position.set(bx, cityY(bx, bz) + 0.1, bz);
        berm.receiveShadow = true;
        groupCity.add(berm);
      }

      const bronzeMat = new THREE.MeshStandardMaterial({ color: COLORS.bronze, roughness: 0.45, metalness: 0.75, envMapIntensity: 0.8 });
      const sc = new THREE.Group();
      const b1 = new THREE.Mesh(new THREE.BoxGeometry(0.8, 2.0, 0.6), bronzeMat);  // young man, standing
      b1.position.set(0, 1.35, 0); b1.rotation.y = 0.4;
      const b2 = new THREE.Mesh(new THREE.BoxGeometry(0.9, 1.4, 0.9), bronzeMat);  // old man on his cube
      b2.position.set(1.6, 1.05, 0.4); b2.rotation.y = -0.3;
      const b3 = new THREE.Mesh(new THREE.BoxGeometry(1.4, 1.1, 0.5), bronzeMat);  // the winged Future
      b3.position.set(0.8, 2.1, -0.9); b3.rotation.y = 0.15;
      const base = new THREE.Mesh(new THREE.BoxGeometry(3.4, 0.7, 3.0),
        new THREE.MeshStandardMaterial({ color: 0x8a5a44, roughness: 0.9 }));
      base.position.set(0.8, 0.35, 0);
      sc.add(b1, b2, b3, base);
      sc.position.set(towersCenter.x - 16, siteY(towersCenter.x - 16, towersCenter.z + 28, 'ground') + LAYER.plaza, towersCenter.z + 28);
      sc.traverse(o => { o.castShadow = true; });
      groupCity.add(sc);
    }
  });

  // ------------------------------------------------ the outer districts
  // Center City, South Philadelphia, Northern Liberties, Fishtown/Kensington:
  // ~108k OSM footprints packed as int16 (0.2 m) and rendered as lean indexed
  // chunks — 8-bit normals/colors, no roofs or cornices, world-space windows.
  const outerMeshes = [];
  const tallGlow = [];   // buildings ≥45 m from every tier, for the night skyline points
  const GRASS_POLYS = [];   // park and lawn rings from every tier, the grass field sows on them near the camera
  const NO_SOW_RINGS = [], NO_SOW_RING_BB = [];   // rings the bare-ground tuft sow keeps off: the sports complex's sheets and lots, every water sheet (inWater knows only the Delaware's bank), the far ring's aprons, the NW creeks
  const noSow = (poly) => { NO_SOW_RINGS.push(poly); NO_SOW_RING_BB.push(bboxOf(poly)); };
  // the fill sheets' boxes: a wide road segment lying inside one is densified at 6 m instead of
  // 15, so the strip bends with the 25 m ground cells the lot sheets conform to instead of
  // cutting a chord across them
  const LOT_FILL_BB = (typeof PARKING_SOUTH !== 'undefined' && PARKING_SOUTH && PARKING_SOUTH.fill) ? PARKING_SOUTH.fill.map((fl2) => {
    let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
    for (let q = 0; q < fl2.length; q += 2) { if (fl2[q] < x0) x0 = fl2[q]; if (fl2[q] > x1) x1 = fl2[q]; if (fl2[q + 1] < z0) z0 = fl2[q + 1]; if (fl2[q + 1] > z1) z1 = fl2[q + 1]; }
    return [x0, x1, z0, z1];
  }) : [];
  const LOT_ROAD_STEP = 6, ROAD_STEP_WIDE = 15;   // road densify steps: inside a fill sheet's box, elsewhere in the wide tier
  function lotDensify(pts) {
    if (!LOT_FILL_BB.length) return densify(pts, ROAD_STEP_WIDE);
    const out = [pts[0]];
    for (let i = 0; i < pts.length - 1; i++) {
      const a = pts[i], b = pts[i + 1];
      const sx0 = Math.min(a[0], b[0]), sx1 = Math.max(a[0], b[0]), sz0 = Math.min(a[1], b[1]), sz1 = Math.max(a[1], b[1]);
      let step = ROAD_STEP_WIDE;
      for (const bb of LOT_FILL_BB) if (sx0 >= bb[0] && sx1 <= bb[1] && sz0 >= bb[2] && sz1 <= bb[3]) { step = LOT_ROAD_STEP; break; }
      const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const k = Math.max(1, Math.ceil(L / step));
      for (let j = 1; j <= k; j++) out.push([a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k]);
    }
    return out;
  }
  // ring meshes upload in batches behind the veil. A frustum-culled mesh is
  // never drawn, so it never uploads and never frees its CPU arrays; every
  // new mesh draws unculled exactly once, in flushUploads' render.
  const pendingUpload = [];
  const addChunkMesh = (g, mat) => {
    if (!g.boundingSphere) g.computeBoundingSphere();   // the frustum test would otherwise compute it from the freed arrays
    const m = new THREE.Mesh(g, mat);
    m.matrixAutoUpdate = false;
    m.frustumCulled = false;
    groupCity.add(m);
    outerMeshes.push(m);
    pendingUpload.push(m);
    return m;
  };
  const flushUploads = (all) => {
    // each flush is a full-scene draw: batch a dozen sealed chunks per render
    if (!pendingUpload.length || (!all && pendingUpload.length < 12)) return;
    // upload now, behind the veil, and free the arrays; under the post pipeline the draw goes
    // into the float target so every program compiles once, in the variant the frames use
    if (POST.on) { if (!postCam) postInit(); postSize(); renderer.setRenderTarget(postRT); renderer.render(scene, camera); renderer.setRenderTarget(null); } else renderer.render(scene, camera);
    for (const m of pendingUpload) m.frustumCulled = true;
    pendingUpload.length = 0;
  };
  step('Raising the outer districts', async () => {
    if (typeof WIDE_B64 === 'undefined' || !WIDE_B64) return;
    const bin = unb64(WIDE_B64, 'WIDE');
    WIDE_B64 = null;   // the 5 MB base64 string has served its purpose
    const hdr = new Int32Array(bin.buffer, 0, 4);
    const body = new Int16Array(bin.buffer, 16);
    const hasAttr = hdr[0] === 0x5348545A || hdr[0] === 0x5348545D;
    const roofPacked = hdr[0] === 0x5348545D;   // the roof word carries form and rise
    if (hdr[0] !== 0x53485458 && !hasAttr) return;
    let k = 0;
    // Mapillary block-face wall colours (pack_wide.py, magic 0x53485457): a palette of
    // sRGB triples as the photos show them and one byte per building record, 255 for
    // none. wallInv puts a photographed colour into the register the hand palettes
    // use (linear values, r149 legacy pipeline): a street photo's wall median is a
    // shaded, half-exposed surface, so its luminance is lifted on a 0.6 power (0.2
    // lands at 0.38, the palLow register); a cool or green cast (blue over red is
    // skylight on a shaded wall, green over both is foliage and camera balance,
    // neither is a wall) is folded to a neutral grey of the same luminance; and a
    // warm colour gets back the chroma the median lost to trim and windows (1.25),
    // while a grey stays the grey it was measured as
    const wallInv = (sr, sg, sb) => {
      let r = Math.pow(sr / 255, 2.2), g = Math.pow(sg / 255, 2.2), b = Math.pow(sb / 255, 2.2);
      const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
      const cast = Math.max(b - r, g - Math.max(r, b));
      if (cast > 0) { const f = Math.min(1, cast / Math.max(1e-4, 0.12 * lum)); r += (lum - r) * f; g += (lum - g) * f; b += (lum - b) * f; }
      const lift = Math.pow(Math.max(lum, 0.01), 0.56);
      const gain = lift / Math.max(lum, 1e-4);
      const warm = r > g && g >= b ? 1.6 : 1.0;
      r = lift + (r * gain - lift) * warm; g = lift + (g * gain - lift) * warm; b = lift + (b * gain - lift) * warm;
      return new THREE.Color(Math.min(1, Math.max(0, r)), Math.min(1, Math.max(0, g)), Math.min(1, Math.max(0, b)));
    };
    const towerHits = [], crownTrim = [];   // researched towers raised in this loop: their crowns follow the loop
    let WALLS = null;
    if (typeof WIDE_WALLS_B64 !== 'undefined' && WIDE_WALLS_B64) {
      const wb = unb64(WIDE_WALLS_B64, 'WIDE_WALLS');
      WIDE_WALLS_B64 = null;
      const wh = new Int32Array(wb.buffer, 0, 4);
      const bpr = Math.max(1, wh[3]);   // bytes per building: the palette index, then (bpr 2) the Mapillary trim/window hint
      if (wh[0] === 0x53485457 && wh[1] === hdr[1] && wh[2] > 0 && wb.length >= 16 + wh[2] * 3 + wh[1] * bpr) {
        const np = wh[2], pal = new Array(np), o = 16 + np * 3;
        for (let p = 0; p < np; p++) pal[p] = wallInv(wb[16 + p * 3], wb[17 + p * 3], wb[18 + p * 3]);
        WALLS = { pal, idx: wb.subarray(o, o + wh[1]), hint: bpr >= 2 ? wb.subarray(o + wh[1], o + 2 * wh[1]) : null };
      }
    }
    const S = 0.2;
    const CH = 700;
    const chunks = new Map(), glassChunks = new Map();
    // building chunks seal and upload as they pass 60k vertices (Uint16
    // indices, bounded staging); the few glass chunks wait for their material
    const chunkIn = (map, seal) => (x, z) => {
      const key = Math.floor(x / CH) + ':' + Math.floor(z / CH);
      let c = map.get(key);
      if (c && seal && c.n > 60000) { addChunkMesh(c.geometry(true), cityMat); c = null; }
      if (!c) { c = new VBuf(2048); map.set(key, c); }
      return c;
    };
    const getChunk = chunkIn(chunks, true), getGlassChunk = chunkIn(glassChunks, false);
    const glassPal = [0x8fb2cc, 0x9cb9c9, 0xa9bfc9, 0x7ea6c6];
    // OSM maps the suspension-bridge towers/anchorages as building footprints; the
    // bridges build their own steel, so drop any footprint sitting on them
    const BRIDGE_SKIP = [[620.8, -889.9, 60], [1148.8, -770, 60], [1037.2, 4391.6, 60], [1620.1, 4510.7, 60], [400, -940, 45], [1360, -722, 45],
      // landmark towers rebuilt with real massing below: City Hall tower, One & Two Liberty Place
      [-1603, -802, 24], [-1995, -785, 25], [-1937, -689, 20], [-1932.3, -718.2, 9],
      // Philadelphia Museum of Art — custom golden-temple rebuild below owns the hilltop
      [-3094, -2225, 130]];
    // signature curtain walls, matched by location (local metres east/south of the towers)
    const GLASS_TINTS = [
      [-1995, -785, 60, 0x6899c4],   // One Liberty Place complex — blue glass
      [-1937, -689, 55, 0x6899c4],   // Two Liberty Place
      [-1930, -714, 30, 0x6899c4],   // Liberty Place mid-rise element
      [-2087, -965, 85, 0xb4c2c8],   // Comcast Center — silver, near-mirror
      [-2224, -1064, 95, 0xa3b1b8],  // Comcast Technology Center — neutral gray glass
      [-3231, -633, 80, 0xb5d0dc],   // FMC Tower — icy blue-white
      [-3205, -1297, 90, 0x9cb8cf],  // Cira Centre
      [-1771, -622, 70, 0x53748e],   // W / Element — dark glass
      [-2548, -821, 70, 0xa5c4d4],   // Murano
      [-2334, -821, 80, 0x6f9cc0],   // 1901 Market (IBC blue)
    ];
    // named wide-ring landmarks at their researched heights (wide_landmarks_research.json).
    // Rows are [x, z, radius, h, spire, frontX, frontZ, twin] in local metres: h replaces
    // the packed body height (0 keeps it); spire is the steeple apex for churches, whose
    // LiDAR height is the spire tip and extruded whole naves as 40-74 m slabs; front is the
    // centroid-to-facade direction that moves the tower to that end (a diagonal picks the
    // corner), twin puts one at each corner. x/z are the packed footprint centroids, each
    // checked offline against wide.b64 (the research lat/lon sits up to 100 m off).
    const LANDMARK_H = [
      // Northern Liberties / Fishtown waterfront
      [445, -2340, 60, 24],                      // Schmidt's Commons: the three 7-storey bars round the Piazza (packed 22-27)
      [933.5, -1815.5, 12, 100.2],               // Waterfront Square, The Regatta (packed 106.8)
      [868.1, -1740.5, 12, 90],                  // Waterfront Square, The Peninsula (packed 100.8)
      [819.9, -1785.4, 12, 76],                  // Waterfront Square, The Reef (packed 94.8)
      [885.4, -1788.6, 8, 24],                   // Waterfront Square podium, the 7-8 storey wing: 7100 m2 packed at 106.4
      [1057.1, -2029, 15, 15],                   // Rivers Casino hall, 1-2 storeys (packed 40.8)
      [839.3, -2224.4, 10, 14],                  // The Fillmore, the Ajax Metal sheds (packed 22.8)
      [610.8, -1869.6, 8, 26],                   // 1 Brown Apartments, 8 storeys (packed 38.4)
      // churches: h = nave ridge, spire = apex; front = facade side
      [5.3, -2693.3, 10, 20, 70, -1, 0],         // St Peter the Apostle (St John Neumann shrine): 230 ft spire on the 5th St front
      [540.8, -3077.6, 10, 18, 50, -1, 0],       // St Michael the Archangel: central front tower on N 2nd (research est. 45-55)
      [-1051.8, -1837.8, 10, 18, 46.6, 0, 1, 1], // Assumption BVM: twin spires on the Spring Garden front
      [626.7, -2267.2, 10, 20, 25, 0, 1],        // Immaculate Conception NoLibs: stub rear tower, the spire never came
      [-150.4, -1113.2, 10, 18, 45],             // St Augustine (4th & New): belfry and spire (research est. 40-45, LiDAR tip 52.4)
      [-1528.5, -900.8, 10, 30, 71, -1, 1],      // Masonic Temple: 3 storeys + attic, 232 ft tower at the SW corner on Broad
      [-1548.1, -953.4, 10, 25, 65.5, -1, 1],    // Arch Street United Methodist: corner spire at Broad & Arch
      // South Philadelphia
      [-1743.5, 2509.6, 10, 22, 38.7, -1, -1],   // Epiphany of Our Lord: corner tower at 11th & Jackson
      [-938.1, 886.8, 10, 20, 36.9],             // St Mary Magdalen de Pazzi: facade campanile
      [-2751.6, 2539.3, 10, 16, 36.5],           // Trinity Lutheran (18th & Ritner): corner spire
      [-1379.6, 1648.2, 10, 20, 34.1, -1, 0],    // Annunciation BVM: flat-capped front tower on 10th
      [-2487.2, 1684.3, 10, 20, 33],             // St Thomas Aquinas (17th & Morris): corner tower (research est., LiDAR 32.8)
      [-3635.5, 2384, 10, 14, 30.2, 1, 0, 1],    // Holy Ghost Byzantine: twin onion-domed towers on 24th
      [-2641.5, 2705.5, 10, 17, 28.7, 1, 0, 1],  // St Monica (17th & Ritner): twin towers
      [-481.3, 1683.6, 10, 16, 28.3, 1, 0],      // Sacred Heart of Jesus (3rd & Reed): front tower
      [-3138.9, 2213.8, 10, 16, 28.3],           // St Edmond (21st & Mifflin): corner tower
      [-514.7, 1524.4, 10, 15, 26.2],            // St Casimir (324 Wharton): front tower
    ];
    // bbox of every row plus its radius: the per-footprint scan only runs inside it
    const LM_BOX = LANDMARK_H.reduce((b, q) => [Math.min(b[0], q[0] - q[2]), Math.max(b[1], q[0] + q[2]), Math.min(b[2], q[1] - q[2]), Math.max(b[3], q[1] + q[2])], [Infinity, -Infinity, Infinity, -Infinity]);
    // ground-contact shading for the ring fabric: every wall quad carries RING_AO of
    // its colour at the two ground verts, full colour at the eave, so the GPU draws a
    // base-to-eave gradient like the core's mergeColored ao ramp (1.0 disables)
    const RING_AO = 0.78;
    const palLow = [0xa85e44, 0x9c5540, 0xb47454, 0x8a5040, 0xa25a40, 0xbfad92, 0xb0a38b, 0x969188, 0xc8b79a, 0xa87560, 0xc2b99d, 0x9cb0b3, 0xa3ae90, 0xc6ba86, 0xb98a72, 0xa4553e];
    const palCom = [0xaba397, 0x9c9587, 0xb7b0a0, 0x908d86, 0xa7aeb3, 0xc2bbb0];
    const palInd = [0x968a7c, 0x877e75, 0xa89e92, 0x9c6350];
    // real skylines are not white: precast tan, limestone, aluminum, blue-gray steel,
    // dark curtain wall, bronze — towers draw from this instead of the pale palCom
    // the unresearched towers: limestone and precast lights, charcoal and bronze darks, blue-grey glass, brick
    const palTall = [0xa39b8b, 0x8e979e, 0x6e7681, 0x50555e, 0x5c5348, 0x8a8478, 0x9c9284, 0x42474f, 0x76664f, 0x66707c, 0x2f3338, 0xb8ad98, 0x5f7d99, 0xc2c2be, 0x6d4a3a, 0x3b4a5a];
    const c = new THREE.Color();
    const cCap = new THREE.Color();
    const v2 = [], v2pool = [];   // pooled contour points (2 M Vector2 allocations per ring otherwise)
    const pushV = (ch, x, y, z, nx, ny, nz, r, g, b, st, base, fh) => ch.push(x, y, z, nx, ny, nz, r, g, b, st, base, fh);
    const appendBuilding = (ch, poly, y0, y1, color, st, base, holes, fh, capColor, ao) => {
      const sign = signedArea(poly) > 0 ? 1 : -1;
      const n = poly.length;
      const r = color.r, g = color.g, b = color.b;
      // ao: the generic fabric only; the ground verts of each wall quad take RING_AO
      // (eave verts and the cap keep the full colour, no mid rings)
      const ra = ao ? RING_AO : 1, r0 = r * ra, g0 = g * ra, b0 = b * ra;
      const wallRing = (ring, sg) => { for (let i = 0; i < ring.length; i++) {
        const a = ring[i], q = ring[(i + 1) % ring.length];
        const dx = q[0] - a[0], dz = q[1] - a[1];
        const L = Math.hypot(dx, dz);
        if (L < 0.05) continue;
        const nx = (dz / L) * sg, nz = (-dx / L) * sg;
        const i0 = pushV(ch, a[0], y0, a[1], nx, 0, nz, r0, g0, b0, st, base, fh);
        const i1 = pushV(ch, q[0], y0, q[1], nx, 0, nz, r0, g0, b0, st, base, fh);
        const i2 = pushV(ch, q[0], y1, q[1], nx, 0, nz, r, g, b, st, base, fh);
        const i3 = pushV(ch, a[0], y1, a[1], nx, 0, nz, r, g, b, st, base, fh);
        if (((-dz) * nx + dx * nz) >= 0) ch.idx.push(i0, i1, i2, i0, i2, i3); else ch.idx.push(i0, i2, i1, i0, i3, i2);
      } };
      if (holes) for (const hl of holes) wallRing(hl, signedArea(hl) > 0 ? -1 : 1);
      wallRing(poly, sign);
      // roof cap (ring when holes are given)
      v2.length = 0;
      for (let i = 0; i < n; i++) { let p2 = v2pool[i]; if (!p2) p2 = v2pool[i] = new THREE.Vector2(); v2.push(p2.set(poly[i][0], -poly[i][1])); }
      const hv = (holes || []).map(hl => hl.map(q => new THREE.Vector2(q[0], -q[1])));
      let tris;
      try { tris = THREE.ShapeUtils.triangulateShape(v2, hv); } catch (e) { return; }
      const capStart = ch.n;
      const cr = capColor ? capColor.r : r * 0.72, cg = capColor ? capColor.g : g * 0.72, cb = capColor ? capColor.b : b * 0.72;
      for (let i = 0; i < n; i++) pushV(ch, poly[i][0], y1, poly[i][1], 0, 1, 0, cr, cg, cb, 3, base);
      for (const hl of (holes || [])) for (const q of hl) pushV(ch, q[0], y1, q[1], 0, 1, 0, cr, cg, cb, 3, base);
      // earcut emits CCW triangles in the shape plane regardless of ring winding,
      // and CCW in (x,-z) maps to up-facing — never flip by ring orientation
      for (const t of tris) ch.idx.push(capStart + t[0], capStart + t[1], capStart + t[2]);
    };
    // ---- the stadiums (south_geometry_research.json), built after the loop: LiDAR handed
    // their light-tower footprints, and one lot beside the ballpark, the 74 m of the steel
    // above them, so those records become mast positions instead of towers, and each bowl
    // is raised from the research: heights, colours, canopies, the surveyed masts, and the
    // parts that light up at night (the field, the light heads, the scoreboard, the floodlights)
    const STADIA = [
      { x: -1857, z: 4383, r: 300, baseball: true, home: [-1861, 4429], scoreboard: [-1926, 4330] },
      { x: -1946, z: 4954, r: 300, baseball: false },
    ];
    const stadia = [], stadiumMasts = [];
    const glowParts = [], flood = [], halo = [];
    const fanGeom = (ring, y) => {   // a flat fan about the centroid (earcut chokes on some OSM rings)
      const n2 = ring.length, pos = new Float32Array(n2 * 9), nor = new Float32Array(n2 * 9);
      let mx = 0, mz = 0; for (const q of ring) { mx += q[0]; mz += q[1]; } mx /= n2; mz /= n2;
      for (let j = 0; j < n2; j++) {
        const a2 = ring[j], b2 = ring[(j + 1) % n2], o = j * 9;
        pos.set([a2[0], y, a2[1], mx, y, mz, b2[0], y, b2[1]], o);
        for (let q2 = 0; q2 < 3; q2++) nor.set([0, 1, 0], o + q2 * 3);
      }
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      g.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
      return g;
    };
    const buildStadium = (sd, masts) => {
      const { poly, cx, cz, base, def } = sd;
      const chk = getChunk(cx, cz);
      const inner = poly.map(q => [cx + (q[0] - cx) * 0.55, cz + (q[1] - cz) * 0.55]);
      const ob = orientedBox(poly); const ax = obbAxis(ob);
      const cap = new THREE.Color();
      // a deck band: the outer points that pass keepFn, and the SAME indices on the inner
      // ring (a scaled copy in the same vertex order), so the band is always a proper ring.
      // Voting the inner ring separately left the two arcs unequal, the polygon crossed
      // itself and the triangulator roofed the Linc's field
      const arcIdx = (keepFn) => {
        const n2 = poly.length;
        let s0 = -1;
        for (let ii = 0; ii < n2; ii++) if (!keepFn(poly[ii])) { s0 = ii; break; }
        const out = [];
        if (s0 < 0) { for (let ii = 0; ii < n2; ii++) out.push(ii); return out; }
        for (let ii = 1; ii <= n2; ii++) { const j = (s0 + ii) % n2; if (keepFn(poly[j])) out.push(j); }
        return out;
      };
      const ringAt = (sc) => poly.map(q => [cx + (q[0] - cx) * sc, cz + (q[1] - cz) * sc]);
      const upperRing = (keepFn, y0, y1, hex, capHex, innerScale) => {
        const idx = arcIdx(keepFn);
        if (idx.length < 3 || idx.length === poly.length) return;
        const ring2 = innerScale ? ringAt(innerScale) : inner;
        const A = idx.map(j => poly[j]), B = idx.map(j => ring2[j]).reverse();
        c.set(hex);
        appendBuilding(chk, A.concat(B), base + y0, base + y1, c, 3, base, null, 0, capHex ? cap.set(capHex) : null);
        return idx;
      };
      // the night halo: additive warm sheets over the seats and the field, on with the lamps
      const haloBand = (keepFn, sc, y) => {
        const idx = arcIdx(keepFn);
        if (idx.length < 2) return;
        const ring2 = ringAt(sc);
        for (let ii = 0; ii + 1 < idx.length; ii++) {
          const a2 = poly[idx[ii]], b2 = poly[idx[ii + 1]], a3 = ring2[idx[ii]], b3 = ring2[idx[ii + 1]];
          halo.push(a2[0], base + y, a2[1], b2[0], base + y, b2[1], b3[0], base + y, b3[1], a2[0], base + y, a2[1], b3[0], base + y, b3[1], a3[0], base + y, a3[1]);
        }
      };
      const haloFan = (ring, y) => {
        const n2 = ring.length;
        for (let j = 0; j < n2; j++) { const a2 = ring[j], b2 = ring[(j + 1) % n2]; halo.push(a2[0], base + y, a2[1], cx, base + y, cz, b2[0], base + y, b2[1]); }
      };
      // a light standard: dark lattice column, a bank of heads turned to the field (lit at
      // night), and a floodlight sprite that carries across the city after dark
      const mast = (mx, mz, y0, y1, hex) => {
        c.set(hex);
        appendBuilding(chk, [[mx - 1.2, mz - 1.2], [mx + 1.2, mz - 1.2], [mx + 1.2, mz + 1.2], [mx - 1.2, mz + 1.2]], base + y0, base + y1, c, 3, base);
        const dx = cx - mx, dz = cz - mz, L = Math.hypot(dx, dz) || 1, ux = dx / L, uz = dz / L;
        glowParts.push({ geom: box(10, 5, 1.6, mx + ux * 1.4, base + y1 - 1.5, mz + uz * 1.4, Math.atan2(uz, ux) + Math.PI / 2), color: new THREE.Color(0xd9cba8), style: 3 });
        const px = -uz, pz = ux;
        for (const o of [-3.4, 0, 3.4]) flood.push(mx + ux * 2.4 + px * o, base + y1 - 1.5, mz + uz * 2.4 + pz * o);
      };
      if (def.baseball) {
        // Citizens Bank Park: brick drum in precast (15 m), the Terrace horseshoe to 40 m with
        // its seats on top, the patina canopy over the top rows, the sunken lit field, the
        // infield, the light standards where LiDAR found them, the left-field scoreboard
        const [hx, hz] = def.home;
        const dh = Math.hypot(hx - cx, hz - cz), dhx = (hx - cx) / dh, dhz = (hz - cz) / dh;
        const keepHome = (q) => ((q[0] - cx) * dhx + (q[1] - cz) * dhz) > -0.28 * Math.hypot(q[0] - cx, q[1] - cz);
        c.set(0x6e3a2e);   // brick, stored dark for the r149 pipeline (research #9C4A3A as seen)
        appendBuilding(chk, poly, base - 1.0, base + 15, c, 3, base, [inner]);
        upperRing(keepHome, 15, 40, 0x6a655a, 0x07160c);   // precast horseshoe, dark-green seats on top
        upperRing(keepHome, 40, 42, 0x3e6a52, null, 0.86);   // the patina canopy over the top rows only
        haloBand(keepHome, 0.55, 42.3); haloBand((q) => !keepHome(q), 0.55, 15.4); haloFan(inner, 2.6);
        glowParts.push({ geom: fanGeom(inner, base + 1.9), color: new THREE.Color(0x1c3f14), style: 3 });
        { // the diamond at MLB geometry: 90 ft bases, the rubber 60 ft 6 in out, the infield skin
          // cut by the 95 ft arc about the rubber, chalk foul lines to the fence, a warning
          // track along the outfield wall. u runs from home plate out to centre field, v across
          const ax2 = -dhx, az2 = -dhz, px2 = -az2, pz2 = ax2;
          const at = (u, v) => [hx + ax2 * u + px2 * v, hz + az2 * u + pz2 * v];
          const flat = (ring, y, hex) => {   // a fan about the centroid, both windings (a decal, never seen edge-on)
            c.set(hex);
            let mx2 = 0, mz2 = 0; for (const q of ring) { mx2 += q[0]; mz2 += q[1]; } mx2 /= ring.length; mz2 /= ring.length;
            const i0 = chk.n;
            for (const q of ring) pushV(chk, q[0], y, q[1], 0, 1, 0, c.r, c.g, c.b, 3, base);
            const ic = chk.n; pushV(chk, mx2, y, mz2, 0, 1, 0, c.r, c.g, c.b, 3, base);
            for (let j = 0; j < ring.length; j++) { const j1 = (j + 1) % ring.length; chk.idx.push(ic, i0 + j, i0 + j1, ic, i0 + j1, i0 + j); }
          };
          const circle = (u, v, rad, n2) => { const out = []; for (let k2 = 0; k2 < n2; k2++) out.push(at(u + Math.cos(k2 / n2 * Math.PI * 2) * rad, v + Math.sin(k2 / n2 * Math.PI * 2) * rad)); return out; };
          const DIRT = 0xa07a52, CHALK = 0xd6d2c4, GRASS = 0x1c3f14;
          const rub = 18.44, arcR = 28.96, s2 = Math.SQRT1_2;
          const tLine = (26.08 + Math.sqrt(26.08 * 26.08 + 4 * (arcR * arcR - rub * rub))) / 2;   // where a foul line meets the arc
          const skin = [at(0, 0), at(tLine * s2, tLine * s2)];
          const a0 = Math.atan2(tLine * s2, tLine * s2 - rub);
          for (let k2 = 0; k2 <= 16; k2++) { const an = a0 - (2 * a0) * k2 / 16; skin.push(at(rub + Math.cos(an) * arcR, Math.sin(an) * arcR)); }
          skin.push(at(tLine * s2, -tLine * s2));
          flat(skin, base + 2.04, DIRT);
          const cu = 19.4, sq = [[0, 0], [cu, cu], [2 * cu, 0], [cu, -cu]].map(([u, v]) => at(cu + (u - cu) * 0.88, v * 0.88));
          flat(sq, base + 2.08, GRASS);                        // the infield grass inside the base paths
          flat(circle(rub, 0, 2.75, 14), base + 2.12, DIRT);   // the mound
          flat(circle(1.2, 0, 4.0, 16), base + 2.12, DIRT);    // the plate area
          for (const sv of [-1, 1]) {                          // chalk from the plate to the corners
            const w = 0.5;
            flat([at(1.5, sv * 1.5 - w * 0), at(1.5 + w * s2, sv * (1.5 - w * s2)), at(96 * s2 + w * s2, sv * (96 * s2 - w * s2)), at(96 * s2, sv * 96 * s2)], base + 2.16, CHALK);
          }
          { // the warning track: the outfield sector of the wall, 4.5 m in toward home plate
            c.set(DIRT);
            const n2 = inner.length;
            for (let j = 0; j < n2; j++) {
              const q1 = inner[j], q2 = inner[(j + 1) % n2];
              const mid = [(q1[0] + q2[0]) / 2, (q1[1] + q2[1]) / 2];
              const du = (mid[0] - hx) * ax2 + (mid[1] - hz) * az2, dl = Math.hypot(mid[0] - hx, mid[1] - hz);
              if (dl < 60 || du < 0.42 * dl) continue;
              const inw = (q) => { const dx3 = hx - q[0], dz3 = hz - q[1], L3 = Math.hypot(dx3, dz3) || 1; return [q[0] + dx3 / L3 * 4.5, q[1] + dz3 / L3 * 4.5]; };
              const r1 = inw(q1), r2 = inw(q2), y = base + 2.0;
              const i0 = chk.n;
              pushV(chk, q1[0], y, q1[1], 0, 1, 0, c.r, c.g, c.b, 3, base); pushV(chk, q2[0], y, q2[1], 0, 1, 0, c.r, c.g, c.b, 3, base);
              pushV(chk, r2[0], y, r2[1], 0, 1, 0, c.r, c.g, c.b, 3, base); pushV(chk, r1[0], y, r1[1], 0, 1, 0, c.r, c.g, c.b, 3, base);
              chk.idx.push(i0, i0 + 1, i0 + 2, i0, i0 + 2, i0 + 3, i0, i0 + 2, i0 + 1, i0, i0 + 3, i0 + 2);
            }
          }
        }
        const spots = masts.length >= 3 ? masts : [[-0.78, -0.78], [0.78, -0.78], [0.78, 0.78], [-0.78, 0.78]].map(([su, sv]) => [ob.cx + ax.ax * ax.hl * su + ax.px * ax.hs * sv, ob.cz + ax.az * ax.hl * su + ax.pz * ax.hs * sv]);
        for (const [mx, mz] of spots) mast(mx, mz, 15, 50, 0x2c3733);
        { // Phanavision: on the left-field stands, square to the sightline from home plate
          const [sx0, sz0] = def.scoreboard;
          let bdx = sx0 - hx, bdz = sz0 - hz; const bL = Math.hypot(bdx, bdz) || 1; bdx /= bL; bdz /= bL;
          let bx2 = sx0, bz2 = sz0;
          for (let s3 = 0; s3 < 260; s3 += 2) { const qx = hx + bdx * s3, qz = hz + bdz * s3; if (!pointInPoly(qx, qz, inner)) { bx2 = qx + bdx * 9; bz2 = qz + bdz * 9; break; } }
          const ry = Math.atan2(-bdx, -bdz), qx2 = -bdz, qz2 = bdx;   // the board's long side runs across the sightline
          const rect = (w, d, ox) => [[bx2 + bdx * ox - qx2 * w / 2 - bdx * d / 2, bz2 + bdz * ox - qz2 * w / 2 - bdz * d / 2], [bx2 + bdx * ox + qx2 * w / 2 - bdx * d / 2, bz2 + bdz * ox + qz2 * w / 2 - bdz * d / 2],
            [bx2 + bdx * ox + qx2 * w / 2 + bdx * d / 2, bz2 + bdz * ox + qz2 * w / 2 + bdz * d / 2], [bx2 + bdx * ox - qx2 * w / 2 + bdx * d / 2, bz2 + bdz * ox - qz2 * w / 2 + bdz * d / 2]];
          c.set(0x2c3833);
          appendBuilding(chk, rect(30, 2.6, 0), base + 15, base + 44, c, 3, base);        // the dark support frame
          c.set(0x3b3f3c);
          appendBuilding(chk, rect(36, 1.2, -1.6), base + 26, base + 44.5, c, 3, base);   // the board's housing, proud of the frame
          glowParts.push({ geom: box(34, 16, 0.7, bx2 - bdx * 2.6, base + 35.2, bz2 - bdz * 2.6, ry), color: new THREE.Color(0x3a5d80), style: 3 });   // the video board, a cool glow after dark
        }
      } else {
        // Lincoln Financial Field: brick base, end-zone stands to 30 m, the sideline decks
        // to 46 m in precast with midnight-green seats, the two wing canopies with their white
        // fascia and floodlights along the leading edge, four corner masts, the lit field
        c.set(0x66392e);   // brick base
        appendBuilding(chk, poly, base - 1.0, base + 14, c, 3, base, [inner]);
        const endZone = (q) => Math.abs((q[0] - ob.cx) * ax.ax + (q[1] - ob.cz) * ax.az) > ax.hl * 0.55;
        upperRing(endZone, 14, 30, 0x6e7275, 0x061412);   // end zones, midnight-green seats
        haloBand(endZone, 0.55, 30.4); haloFan(inner, 2.6);
        for (const sgn of [-1, 1]) {
          const sideline = (q) => ((q[0] - ob.cx) * ax.px + (q[1] - ob.cz) * ax.pz) * sgn > ax.hs * 0.30;
          upperRing(sideline, 14, 46, 0x6e7275, 0x061412);
          haloBand(sideline, 0.55, 46.4);
          const cp = [[-ax.hl * 0.6, sgn * ax.hs * 0.72], [ax.hl * 0.6, sgn * ax.hs * 0.72], [ax.hl * 0.6, sgn * ax.hs * 1.0], [-ax.hl * 0.6, sgn * ax.hs * 1.0]]   // the wing covers the top third of the deck
            .map(([u, v]) => [ob.cx + ax.ax * u + ax.px * v, ob.cz + ax.az * u + ax.pz * v]);
          c.set(0x8a9094);   // the wing canopy
          appendBuilding(chk, cp, base + 50.5, base + 54, c, 3, base);
          const fe = [[-ax.hl * 0.6, sgn * ax.hs * 0.66], [ax.hl * 0.6, sgn * ax.hs * 0.66], [ax.hl * 0.6, sgn * ax.hs * 0.74], [-ax.hl * 0.6, sgn * ax.hs * 0.74]]
            .map(([u, v]) => [ob.cx + ax.ax * u + ax.px * v, ob.cz + ax.az * u + ax.pz * v]);
          c.set(0xe4e7e9);
          appendBuilding(chk, fe, base + 53, base + 55, c, 3, base);
          for (let u = -ax.hl * 0.55; u <= ax.hl * 0.55 + 0.01; u += ax.hl * 0.0733) {
            flood.push(ob.cx + ax.ax * u + ax.px * sgn * ax.hs * 0.70, base + 52.6, ob.cz + ax.az * u + ax.pz * sgn * ax.hs * 0.70);
          }
        }
        for (const [su, sv] of [[-0.8, -0.9], [0.8, -0.9], [0.8, 0.9], [-0.8, 0.9]]) {
          mast(ob.cx + ax.ax * ax.hl * su + ax.px * ax.hs * sv, ob.cz + ax.az * ax.hl * su + ax.pz * ax.hs * sv, 14, 66, 0x6b7175);
        }
        glowParts.push({ geom: fanGeom(inner, base + 1.9), color: new THREE.Color(0x1a3d12), style: 3 });
      }
    };
    const nb = hdr[1];
    const wxWater = wxWaterGrid(body, k, nb, hdr[2], hdr[3], hasAttr, S, -3700, -4480, 6000, 10880, 24);
    let njPoly = null;   // USS New Jersey hull outline — custom battleship below
    for (let i = 0; i < nb; i++) {
      const n = body[k++]; let h = body[k++] / 5; const mh = body[k++] / 5, t = body[k++];
      const attrW = hasAttr ? body[k++] : -1, roofW = hasAttr ? body[k++] : -1;
      const poly = new Array(n);
      for (let j = 0; j < n; j++) { poly[j] = [body[k++] * S, body[k++] * S]; }
      const [cx, cz] = polyCentroid(poly);
      if (BRIDGE_SKIP.some(q => Math.hypot(cx - q[0], cz - q[1]) < q[2])) continue;
      if (ovpStraddle(poly, cx, cz)) continue;   // nothing real stands across a motorway deck
      if (Math.hypot(cx - 996, cz - 663) < 80) {
        // the USS New Jersey berth: capture the 270 m hull outline for the custom
        // battleship (any type code — the old t===7 gate rotted when the wide
        // ring was repacked, and the hull extruded as a windowed slab afloat)
        let mnX = Infinity, mxX = -Infinity, mnZ = Infinity, mxZ = -Infinity;
        for (const q of poly) { mnX = Math.min(mnX, q[0]); mxX = Math.max(mxX, q[0]); mnZ = Math.min(mnZ, q[1]); mxZ = Math.max(mxZ, q[1]); }
        if (Math.hypot(mxX - mnX, mxZ - mnZ) > 180) { njPoly = poly; continue; }
      }
      // nothing floats: a footprint standing in this ring's own rendered water
      // is bad data (mapped barges, drowned islets, mid-water slabs) — the
      // dem/corridor test alone missed Philly-side river water
      if (wxWater(cx, cz) || (demY(cx, cz) < TERRAIN.water + 0.5 && riverCorridor(cx, cz))) continue;
      let lm = null;   // LANDMARK_H row for this footprint, if any
      if (cx > LM_BOX[0] && cx < LM_BOX[1] && cz > LM_BOX[2] && cz < LM_BOX[3]) for (const q of LANDMARK_H) if (Math.hypot(cx - q[0], cz - q[1]) < q[2]) { lm = q; break; }
      if (lm && lm[3] > 0) h = lm[3];
      const base = siteY(cx, cz, 'ground');
      const sdNear = STADIA.find(sd => Math.hypot(cx - sd.x, cz - sd.z) < sd.r);
      if (sdNear) {
        if (t === 8) { stadia.push({ poly, cx, cz, base, def: sdNear }); continue; }   // built after the loop, once the masts are known
        const area8 = Math.abs(signedArea(poly));
        if (h > 30 && area8 < 220) { stadiumMasts.push([cx, cz]); continue; }   // a light tower's footprint carrying the 74 m of its steel: the stadium raises the mast
        if (h > 30) h = 12;   // the lot beside the ballpark that LiDAR measured at 74 m
      }
      const hsh = hash01(i * 7.13);
      if (h >= 45) tallGlow.push({ x: cx, z: cz, b: base, h, poly });
      const fa = attrW >= 0 ? [attrW & 7, (attrW >> 3) & 7, (attrW >> 6) & 15, 0] : null;
      const fh = attrW >= 0 && ((attrW >> 10) & 31) > 0 ? 2.2 + (((attrW >> 10) & 31) - 1) * 0.1 : 0;
      let pool = h > 45 ? palTall : (t === 3 || t === 6 || h > 25) ? palCom : (t === 4 ? palInd : palLow);
      if (fa && h <= 45 && t <= 4) { const p2 = opaWallPool(fa); if (p2) pool = p2; }
      c.set(pool[Math.floor(hsh * pool.length) % pool.length]).multiplyScalar(h > 45 ? 0.94 + hash01(i * 11.3) * 0.12 : 0.9 + hash01(i * 11.3) * 0.2);
      // a wall Mapillary has seen takes its block face's photographed colour, three
      // parts measured to one part the building's own palette draw (a face's median is
      // one colour for the whole block; the draw gives the houses back the variety a
      // real face has), with a second jitter on top; towers and stadiums keep theirs
      if (WALLS && h <= 45 && t <= 6) { const wi = WALLS.idx[i]; if (wi < WALLS.pal.length) { c.lerp(WALLS.pal[wi], 0.75).multiplyScalar(0.94 + hash01(i * 7.9) * 0.12); WALL_N++; } }
      const hint = WALLS && WALLS.hint ? WALLS.hint[i] : 0;
      const spec = h > 45 && t !== 10 ? towerAt(cx, cz) : null;
      let style;
      if (spec) { style = TOWER_STYLE[spec.facade] || 2; if (spec.hex) { const hx2 = parseInt(spec.hex.slice(1), 16); if (style >= 20) c.set(hx2).multiplyScalar(0.66); else c.copy(towerInv(hx2 >> 16, (hx2 >> 8) & 255, hx2 & 255)); } }
      else if (h > 30) style = h > 45 ? towerStyle(fa, t, i) : 2;
      else if (t === 5) style = 1;
      else if (t === 6) style = h > 16 ? 2 : 4;
      else if (t >= 7) style = 3;
      else style = fabricStyle(fa, h, t, Math.abs(signedArea(poly)), i, hint);
      const rb = roofBits(roofW, roofPacked);
      const capC = rb[0] >= 0 && ROOF_PAL && rb[0] < ROOF_PAL.length ? cCap.copy(ROOF_PAL[rb[0]]).multiplyScalar(0.9 + hsh * 0.18) : null;
      let hTop = h;
      if (spec && !mh) {
        const cr = spec.crown;
        if (cr && CROWN_CUTS[cr.type]) hTop = Math.max(h * 0.8, h - (cr.h || 10));
        towerHits.push({ spec, poly, base, h, hTop, cx, cz, style, color: new THREE.Color().copy(c) });
      }
      if (h >= 60 && !mh && t !== 10 && (!spec || !spec.crown || spec.crown.type === 'flat' || spec.crown.type === 'custom')) {
        // the flat roof of a real tower carries a mechanical penthouse and often a mast; without
        // them every tower is a sheer box. The penthouse takes a third of the plan, set toward
        // one end, in a darker tone; a third of the towers raise a mast
        const obR = orientedBox(poly), axR = obbAxis(obR), hp = 4.5 + hash01(i * 3.3) * 3;
        const su0 = (hash01(i * 8.1) - 0.5) * 0.9, sv0 = (hash01(i * 4.4) - 0.5) * 0.6;
        const pent = [[-0.34, -0.3], [0.34, -0.3], [0.34, 0.3], [-0.34, 0.3]].map(([su, sv]) => [obR.cx + axR.ax * axR.hl * (su + su0) + axR.px * axR.hs * (sv + sv0), obR.cz + axR.az * axR.hl * (su + su0) + axR.pz * axR.hs * (sv + sv0)]);
        const cP = cCap.copy(c).multiplyScalar(0.55);
        appendBuilding(getChunk(cx, cz), pent, base + h - 0.3, base + h + hp, cP, 3, base);
        if (hash01(i * 12.7) < 0.33) { const mg = new THREE.CylinderGeometry(0.35, 0.8, 10 + hash01(i * 5.5) * 14, 6); mg.translate(obR.cx + axR.ax * axR.hl * su0, base + h + hp + 5 + hash01(i * 5.5) * 7, obR.cz + axR.az * axR.hl * su0); crownTrim.push({ geom: mg, color: new THREE.Color(0x6b7075), style: 3 }); }
      }
      if (style >= 20) {   // a researched glass tower: the reflective curtain wall in its own tint
        appendBuilding(getGlassChunk(cx, cz), poly, mh > 0 ? base + mh : base - 1.0, base + hTop, c, style, base);
        if ((i & 4095) === 4095) { loadmsg.textContent = 'Raising the outer districts, ' + Math.round(i / nb * 100) + '%'; flushUploads(); await yieldNow(); }
        continue;
      }
      if (t === 10) { // glass tower parts: reflective material, no painted windows
        c.set(glassPal[Math.floor(hsh * glassPal.length) % glassPal.length]);
        for (const gt of GLASS_TINTS) if (Math.hypot(cx - gt[0], cz - gt[1]) < gt[2]) { c.set(gt[3]); break; }
        appendBuilding(getGlassChunk(cx, cz), poly, mh > 0 ? base + mh : base - 1.0, base + h, c, 3, base);
        if ((i & 4095) === 4095) { loadmsg.textContent = 'Raising the outer districts, ' + Math.round(i / nb * 100) + '%'; flushUploads(); await yieldNow(); }
        continue;
      }
      const chk = getChunk(cx, cz);
      if (t === 9) { // Xfinity Mobile Arena: dark walls, glass entry, pale roof slab
        c.set(0x3a3e44);
        appendBuilding(chk, poly, base - 1.0, base + 21, c, 3, base);
        c.set(0x565b60);
        appendBuilding(chk, poly.map(q => [cx + (q[0] - cx) * 0.86, cz + (q[1] - cz) * 0.86]), base + 21, base + 36, c, 3, base);
        c.set(0xcfd2d4);
        appendBuilding(chk, poly.map(q => [cx + (q[0] - cx) * 0.88, cz + (q[1] - cz) * 0.88]), base + 36, base + 38.5, c, 3, base);
        { // glass rotunda + entry bar on the corner, purple screen accents on two faces
          const ob9 = orientedBox(poly); const ax9 = obbAxis(ob9);
          const ex2 = ob9.cx + ax9.ax * ax9.hl * 0.62 + ax9.px * ax9.hs * 0.5, ez2 = ob9.cz + ax9.az * ax9.hl * 0.62 + ax9.pz * ax9.hs * 0.5;
          const oct = [];
          for (let k2 = 0; k2 < 8; k2++) oct.push([ex2 + Math.cos(k2 * Math.PI / 4) * 9, ez2 + Math.sin(k2 * Math.PI / 4) * 9]);
          c.set(0x9fc0d8);
          appendBuilding(chk, oct, base - 1.0, base + 16, c, 3, base);
          c.set(0x5b3f9e);
          for (const sv of [-1, 1]) {
            const px2 = ob9.cx + ax9.px * sv * ax9.hs * 0.97, pz2 = ob9.cz + ax9.pz * sv * ax9.hs * 0.97;
            appendBuilding(chk, [[px2 - 9, pz2 - 1], [px2 + 9, pz2 - 1], [px2 + 9, pz2 + 1], [px2 - 9, pz2 + 1]], base + 22, base + 32, c, 3, base);
          }
        }
      } else {
        const rplan = mh > 0 || spec ? null : roofPlan(poly, Math.abs(signedArea(poly)), h, t, rb[1], rb[2], i * 3.17 + 0.5);
        if (rplan) raisePitched(chk, poly, base, h, rplan, c, style, fh, capC, appendBuilding);
        else {
          appendBuilding(chk, poly, mh > 0 ? base + mh : base - 1.0, base + hTop, c, style, base, null, fh, capC, mh === 0);
          if (!mh && hTop === h && !(spec && spec.crown && spec.crown.type !== 'flat') && h < 60) roofClutter((pg, y0, y1, hex, st2, holes) => { cCap.set(hex); appendBuilding(chk, pg, y0, y1, cCap, st2, base, holes); }, poly, base, h, Math.abs(signedArea(poly)), t, fa, i, c, false);
        }
      }
      if (t === 5 && mh === 0 && Math.abs(signedArea(poly)) > 350 && h < 60) {
        // church: square tower to h+9, then a pyramidal spire — the districts' skyline is their steeples.
        // A LANDMARK_H spire drives the apex instead: tower to 60% of the rise, pyramid the rest,
        // width scaled to the spire, standing at the facade end when the row gives a front
        const sp = lm && lm[4] > h + 3 ? lm[4] : 0;
        const tw = sp ? Math.max(5.5, sp * 0.11) : 5.5;
        const towerTop = base + (sp ? h + (sp - h) * 0.6 : h + 9), apex = base + (sp ? sp : h + 24);
        const spots = [[cx, cz]];
        const ob = sp && (lm[5] || lm[6]) ? orientedBox(poly) : null;
        if (ob) {
          const a = obbAxis(ob), fl = Math.hypot(lm[5], lm[6]);
          const du = (a.ax * lm[5] + a.az * lm[6]) / fl, dv = (a.px * lm[5] + a.pz * lm[6]) / fl;
          // the facade is a short end (|du| wins) or a long side; towers stand tw*0.8 inside it,
          // twins at both corners, a diagonal front picks one corner, else the middle
          const [ex, ez, eh, ox, oz, oh, dd, dp] = Math.abs(du) >= Math.abs(dv)
            ? [a.ax, a.az, a.hl, a.px, a.pz, a.hs, du, dv] : [a.px, a.pz, a.hs, a.ax, a.az, a.hl, dv, du];
          const ein = Math.max(0, eh - tw * 0.8), oin = Math.max(0, oh - tw * 0.8);
          const fx0 = ob.cx + ex * Math.sign(dd) * ein, fz0 = ob.cz + ez * Math.sign(dd) * ein;
          const sides = lm[7] ? [-1, 1] : [Math.abs(dp) > 0.35 ? Math.sign(dp) : 0];
          spots.length = 0;
          for (const s of sides) spots.push([fx0 + ox * s * oin, fz0 + oz * s * oin]);
        }
        const sc = 0.9;
        for (const [tx, tz] of spots) {
          const sq = [[tx - tw / 2, tz - tw / 2], [tx + tw / 2, tz - tw / 2], [tx + tw / 2, tz + tw / 2], [tx - tw / 2, tz + tw / 2]];
          appendBuilding(chk, sq, base, towerTop, c, 3, base);
          const i0 = chk.n;
          for (const q of sq) pushV(chk, q[0], towerTop, q[1], 0, 0.7, 0, c.r * sc, c.g * sc, c.b * sc, 3, base);
          pushV(chk, tx, apex, tz, 0, 1, 0, c.r * sc, c.g * sc, c.b * sc, 3, base);
          // outward: (base, apex, next) with the ring CCW in (x, z), the sense the wall loop uses
          chk.idx.push(i0, i0 + 4, i0 + 1, i0 + 1, i0 + 4, i0 + 2, i0 + 2, i0 + 4, i0 + 3, i0 + 3, i0 + 4, i0);
        }
      }
      if ((i & 4095) === 4095) { loadmsg.textContent = 'Raising the outer districts, ' + Math.round(i / nb * 100) + '%'; flushUploads(); await yieldNow(); }
    }
    // -------- crowns for the researched towers (towers.json): the body stopped short of
    // the spec's crown height above, and the crown takes the last metres in its own form.
    // Rectangle pyramids and frusta over the footprint's oriented box, stepped tiers that
    // keep the facade style, open lattices of bars, lit lanterns, masts and roof signs
    if (towerHits.length) {
      const rectOf = (ob, ax, sc) => [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([su, sv]) => [ob.cx + ax.ax * ax.hl * sc * su + ax.px * ax.hs * sc * sv, ob.cz + ax.az * ax.hl * sc * su + ax.pz * ax.hs * sc * sv]);
      const pyrRect = (ob, ax, y0, y1, topSc) => {   // a pyramid (topSc 0) or frustum over the oriented box
        const lo = rectOf(ob, ax, 1.0), hi = topSc > 0 ? rectOf(ob, ax, topSc) : null;
        const t = [];
        for (let k2 = 0; k2 < 4; k2++) {
          const a2 = lo[k2], b2 = lo[(k2 + 1) % 4];
          if (hi) { const a3 = hi[k2], b3 = hi[(k2 + 1) % 4]; t.push(a2[0], y0, a2[1], b2[0], y0, b2[1], b3[0], y1, b3[1], a2[0], y0, a2[1], b3[0], y1, b3[1], a3[0], y1, a3[1]); }
          else t.push(a2[0], y0, a2[1], b2[0], y0, b2[1], ob.cx, y1, ob.cz);
        }
        if (hi) t.push(hi[0][0], y1, hi[0][1], hi[1][0], y1, hi[1][1], hi[2][0], y1, hi[2][1], hi[0][0], y1, hi[0][1], hi[2][0], y1, hi[2][1], hi[3][0], y1, hi[3][1]);
        const g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(t), 3));
        g.computeVertexNormals();
        return g;
      };
      const bar = (a2, b2, rad) => {   // a round bar from a2 to b2 ([x, y, z])
        const d = new THREE.Vector3(b2[0] - a2[0], b2[1] - a2[1], b2[2] - a2[2]); const L = d.length(); d.normalize();
        const g = new THREE.CylinderGeometry(rad, rad, L, 6);
        g.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), d));
        g.translate((a2[0] + b2[0]) / 2, (a2[1] + b2[1]) / 2, (a2[2] + b2[2]) / 2);
        return g;
      };
      let nCrowns = 0;
      for (const th of towerHits) {
        const cr = th.spec.crown;
        if (!cr || !cr.type || cr.type === 'flat' || cr.type === 'custom' || cr.type === 'stepped') continue;
        const ob = orientedBox(th.poly), ax = obbAxis(ob);
        const y0 = th.base + th.hTop, y1 = th.base + th.h, hc = Math.max(2, y1 - y0);
        const lit = th.spec.lit ? new THREE.Color(parseInt(th.spec.lit.slice(1), 16)) : null;
        const dark = th.color.clone().multiplyScalar(0.72);
        const chk2 = getChunk(th.cx, th.cz);
        nCrowns++;
        switch (cr.type) {
          case 'pyramid':
            if (lit) glowParts.push({ geom: pyrRect(ob, ax, y0, y1, 0), color: lit.clone().multiplyScalar(0.42), style: 3 });
            else crownTrim.push({ geom: pyrRect(ob, ax, y0, y1, 0), color: dark, style: 3 });
            break;
          case 'mansard':
            crownTrim.push({ geom: pyrRect(ob, ax, y0, y1, 0.55), color: new THREE.Color(0x51565b), style: 3 });
            break;
          case 'dome': {
            const g = new THREE.SphereGeometry(Math.min(ax.hl, ax.hs) * 0.9, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2);
            g.translate(ob.cx, y0, ob.cz);
            crownTrim.push({ geom: g, color: new THREE.Color(0xc9ccc4), style: 3 });
            break;
          }
          case 'lattice': {   // an open steel pyramid: the four hips and two rings of purlins, floodlit
            const lo = rectOf(ob, ax, 1.0), apex = [ob.cx, y1, ob.cz], col = lit ? lit.clone().multiplyScalar(0.5) : new THREE.Color(0xbfc6cc);
            const push = (g) => (lit ? glowParts : crownTrim).push({ geom: g, color: col, style: 3 });
            for (let k2 = 0; k2 < 4; k2++) push(bar([lo[k2][0], y0, lo[k2][1]], apex, 0.7));
            for (const f of [0.33, 0.66]) {
              const r2 = rectOf(ob, ax, 1.0 - f), y = y0 + hc * f;
              for (let k2 = 0; k2 < 4; k2++) push(bar([r2[k2][0], y, r2[k2][1]], [r2[(k2 + 1) % 4][0], y, r2[(k2 + 1) % 4][1]], 0.45));
            }
            push(bar([ob.cx, y1 - 0.5, ob.cz], [ob.cx, y1 + hc * 0.35, ob.cz], 0.5));
            break;
          }
          case 'ziggurat': {   // stepped tiers that keep the facade
            const steps = cr.steps || 3, dh = hc / steps;
            for (let k2 = 0; k2 < steps; k2++) {
              c.copy(th.color);
              appendBuilding(chk2, rectOf(ob, ax, 1.0 - 0.13 * (k2 + 1)), y0 + k2 * dh, y0 + (k2 + 1) * dh + 0.01, c, th.style >= 20 ? 17 : th.style, th.base);
            }
            if (lit) glowParts.push({ geom: box(ax.hl * 2 * 0.5, 1.2, ax.hs * 2 * 0.5, ob.cx, y1 + 0.6, ob.cz, Math.atan2(-ax.az, ax.ax)), color: lit.clone().multiplyScalar(0.45), style: 3 });
            break;
          }
          case 'lantern': {   // a lit box on the roof, a smaller dark frame around it
            const gl = lit ? lit.clone().multiplyScalar(0.5) : new THREE.Color(0x6f7c86);
            glowParts.push({ geom: box(ax.hl * 2 * 0.62, hc, ax.hs * 2 * 0.62, ob.cx, y0 + hc / 2, ob.cz, Math.atan2(-ax.az, ax.ax)), color: gl, style: 3 });
            c.copy(th.color);
            appendBuilding(chk2, rectOf(ob, ax, 0.72), y0, y0 + hc * 0.35, c, 3, th.base);
            break;
          }
          case 'notch':
          case 'sloped': {   // the top floors keep only part of the plan
            const keep = 0.62, half = [[-1, -1], [2 * keep - 1, -1], [2 * keep - 1, 1], [-1, 1]].map(([su, sv]) => [ob.cx + ax.ax * ax.hl * su + ax.px * ax.hs * sv, ob.cz + ax.az * ax.hl * su + ax.pz * ax.hs * sv]);
            c.copy(th.color);
            if (th.style >= 20) appendBuilding(getGlassChunk(th.cx, th.cz), half, y0 - 0.5, y1, c, th.style, th.base);
            else appendBuilding(chk2, half, y0 - 0.5, y1, c, th.style, th.base);
            if (lit) glowParts.push({ geom: box(ax.hl * 2 * keep * 0.9, 1.4, ax.hs * 2 * 0.9, ob.cx + ax.ax * ax.hl * (keep - 1), y1 + 0.7, ob.cz + ax.az * ax.hl * (keep - 1), Math.atan2(-ax.az, ax.ax)), color: lit.clone().multiplyScalar(0.45), style: 3 });
            break;
          }
          case 'spire': {   // a mast, and a lit sign on the roof where the spec lights one
            const g = new THREE.CylinderGeometry(0.5, 1.2, hc, 8); g.translate(ob.cx, y1 + hc / 2, ob.cz);
            crownTrim.push({ geom: g, color: new THREE.Color(0x8c9196), style: 3 });
            if (lit) glowParts.push({ geom: box(Math.min(16, ax.hl * 1.2), 5, 1.2, ob.cx + ax.px * (ax.hs - 1.5), y1 + 3.2, ob.cz + ax.pz * (ax.hs - 1.5), Math.atan2(-ax.az, ax.ax)), color: lit.clone().multiplyScalar(0.55), style: 3 });
            break;
          }
          default: nCrowns--;
        }
      }
      TOWER_CROWN_N = nCrowns;
    }
    // the stadiums, now that every light-tower record in their blocks has been read
    for (const sd of stadia) buildStadium(sd, stadiumMasts.filter(m => Math.hypot(m[0] - sd.cx, m[1] - sd.cz) < 240));
    if (glowParts.length) {   // fields, light heads and the video board: their own colour by day, glowing after dark
      const g = mergeColored(glowParts); freeOnUpload(g);
      const gm = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, side: THREE.DoubleSide });
      gm.onBeforeCompile = (sh) => {
        sh.uniforms.uNight = nightUniform;
        sh.fragmentShader = sh.fragmentShader
          .replace('#include <common>', '#include <common>\nuniform float uNight;')
          .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance += diffuseColor.rgb * uNight * 2.4;');
      };
      groupCity.add(new THREE.Mesh(g, gm));
    }
    if (flood.length) {   // floodlight sprites: additive, screen-sized, on with the streetlamps (updateLights)
      const fg = new THREE.BufferGeometry();
      fg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(flood), 3));
      floodMat = new THREE.PointsMaterial({ color: 0xfff6dc, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false, sizeAttenuation: false, size: renderer.getPixelRatio() });
      floodMat.onBeforeCompile = (sh) => {
        sh.vertexShader = sh.vertexShader.replace('gl_PointSize = size;', 'gl_PointSize = size * clamp(4800.0 / max(1.0, -mvPosition.z), 3.0, 18.0);');
        sh.fragmentShader = sh.fragmentShader.replace('#include <color_fragment>', '#include <color_fragment>\n\tdiffuseColor.a *= smoothstep(0.5, 0.15, length(gl_PointCoord - vec2(0.5)));');
      };
      postRaw(floodMat);
      floodPts = new THREE.Points(fg, floodMat);
      floodPts.frustumCulled = false; floodPts.renderOrder = 11; floodPts.visible = false;
      groupCity.add(floodPts);
    }
    if (halo.length) {   // the warm sheets: a faint additive glow over each bowl and its field after dark
      const hg = new THREE.BufferGeometry();
      hg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(halo), 3));
      haloMat = new THREE.MeshBasicMaterial({ color: 0xffd9a0, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide, toneMapped: false });
      postRaw(haloMat);
      haloMesh = new THREE.Mesh(hg, haloMat);
      haloMesh.frustumCulled = false; haloMesh.renderOrder = 10; haloMesh.visible = false;
      groupCity.add(haloMesh);
    }
    // outer streets. Continuity work: endpoint-snapped heights (no steps at OSM way
    // splits), joint fans at bends, real bridge decks over the rivers, aligned-only
    // duplicate dropping, and a lift blend at the core seam.
    const rc = { pos: [], col: [], idx: [], n: 0, lane: new Float32Array(1 << 20), label: 'wide' };
    const roadCol = [0x3b3833, 0x3b3833, 0x3f3c37, 0x3f3c37, 0x43403b, 0x45423d, 0x7c584a];
    // aLane (u, s, hw, cls) for vertex v, in a growable Float32Array (a boxed array here
    // would stage the whole tier at ~92 B a vertex, the phone killer, see IdxBuf)
    const rcLane = (v, u, s, hw, cls) => {
      if (v * 4 + 4 > rc.lane.length) { const b = new Float32Array(rc.lane.length * 2); b.set(rc.lane); rc.lane = b; }
      rc.lane[v * 4] = u; rc.lane[v * 4 + 1] = s; rc.lane[v * 4 + 2] = hw; rc.lane[v * 4 + 3] = cls;
    };
    const yMapW = new Map();
    const ySnap = (map, x, z, y) => {
      const key = Math.round(x * 2) + ':' + Math.round(z * 2);
      const v = map.get(key);
      if (v !== undefined) return v;
      map.set(key, y);
      return y;
    };
    // the joint fan sits 2 cm below its strip so the strip's paint wins the overlap; its
    // aLane rides the averaged heading (ddx, ddz) at the bend: rim u = offset . n, s = sA + offset . d
    const rcFan = (x, y, z, hw, cr, cg, cb, sA, ddx, ddz, cls) => {
      const c0 = rc.n;
      y -= 0.02;
      rc.pos.push(x, y, z);
      rc.col.push(cr, cg, cb);
      rcLane(rc.n, 0, sA, hw, cls);
      rc.n++;
      for (let s6 = 0; s6 < 7; s6++) {
        const ang = s6 / 6 * Math.PI * 2;
        const ox = Math.cos(ang) * hw, oz = Math.sin(ang) * hw;
        rc.pos.push(x + ox, y, z + oz);
        rc.col.push(cr, cg, cb);
        rcLane(rc.n, -ox * ddz + oz * ddx, sA + ox * ddx + oz * ddz, hw, cls);
        rc.n++;
      }
      for (let s6 = 0; s6 < 6; s6++) rc.idx.push(c0, c0 + 1 + s6, c0 + 2 + s6);
    };
    for (let i = 0; i < hdr[2]; i++) {
      const n = body[k++], w = body[k++] / 10, t = body[k++];
      let pts = new Array(n);
      for (let j = 0; j < n; j++) pts[j] = [body[k++] * S, body[k++] * S];
      if (t <= 5) for (let j = 0; j + 1 < pts.length; j++) septaRoadAdd(pts[j][0], pts[j][1], pts[j + 1][0], pts[j + 1][1]);
      pts = lotDensify(pts);   // 6 m inside the sports complex's fill sheets, 15 m elsewhere
      c.set(roadCol[t] || 0x3b3833);
      const hw = w / 2;
      const cls = t <= 1 ? 1 : (t === 6 || w < 5.5 || (t === 5 && w > 10)) ? 2 : 0;   // lane class: divided, two-way, or unmarked
      const thr = TERRAIN.water + 0.6;
      let sAcc = 0;   // distance along the densified polyline (the lane paint's s)
      for (let j = 0; j < pts.length - 1; j++) {
        const a = pts[j], q = pts[j + 1];
        let dx = q[0] - a[0], dz = q[1] - a[1];
        const L = Math.hypot(dx, dz); if (L < 0.01) continue;
        const sA = sAcc; sAcc += L;
        dx /= L; dz /= L;
        const mx = (a[0] + q[0]) / 2, mz = (a[1] + q[1]) / 2;
        const aLow = demY(a[0], a[1]) < thr, qLow = demY(q[0], q[1]) < thr;
        let deck = 0;
        if ((aLow || qLow) && riverCorridor(mx, mz)) {
          if (t > 2) { if (aLow && qLow) continue; }         // minor roads don't bridge rivers
          else deck = t === 0 ? 20 : 13;                     // major roads become bridge decks
        }
        if (deck && wwbNear(mx, mz)) continue;               // the custom WWB deck owns its crossing
        if (ovpOwned(a[0], a[1], q[0], q[1])) continue;      // a baked overpass deck or sunken roadway owns it
        // a wide segment lying ALONG a core street is a duplicate and would z-fight it
        if (a[0] > CORE_EXT.x0 - 38 && a[0] < CORE_EXT.x1 + 38 && a[1] > CORE_EXT.z0 - 38 && a[1] < CORE_EXT.z1 + 38 &&
            q[0] > CORE_EXT.x0 - 38 && q[0] < CORE_EXT.x1 + 38 && q[1] > CORE_EXT.z0 - 38 && q[1] < CORE_EXT.z1 + 38 &&
            nearRoadAligned(a[0], a[1], 3.5, dx, dz) && nearRoadAligned(q[0], q[1], 3.5, dx, dz) &&
            nearRoadAligned(mx, mz, 2.5, dx, dz)) continue;
        const px = -dz * hw, pz = dx * hw;
        // class-separated lifts, blended down to the core formula near the seam
        const dOut = Math.max(CORE_EXT.x0 - mx, mx - CORE_EXT.x1, CORE_EXT.z0 - mz, mz - CORE_EXT.z1, 0);
        const bl = clamp(dOut / 60, 0, 1);
        const jr = lerp(LAYER.road + hash01(i * 3.7 + 1.1) * 0.06,
          LAYER.road + (6 - Math.min(t, 6)) * 0.055 + hash01(i * 3.7 + 1.1) * 0.1, bl);
        let ya0 = groundMeshLandY(a[0], a[1]) ?? siteY(a[0], a[1], 'road'), yb0 = groundMeshLandY(q[0], q[1]) ?? siteY(q[0], q[1], 'road');
        if (deck) {
          ya0 = Math.max(ya0, TERRAIN.water + (aLow ? deck : deck * 0.35));
          yb0 = Math.max(yb0, TERRAIN.water + (qLow ? deck : deck * 0.35));
        }
        const ya = ySnap(yMapW, a[0], a[1], ya0 + jr), yb = ySnap(yMapW, q[0], q[1], yb0 + jr);
        const b0 = rc.n;
        rc.pos.push(a[0] + px, ya, a[1] + pz, q[0] + px, yb, q[1] + pz, q[0] - px, yb, q[1] - pz, a[0] - px, ya, a[1] - pz);
        for (let m = 0; m < 4; m++) rc.col.push(c.r * 255, c.g * 255, c.b * 255);
        rcLane(b0, hw, sA, hw, cls); rcLane(b0 + 1, hw, sAcc, hw, cls); rcLane(b0 + 2, -hw, sAcc, hw, cls); rcLane(b0 + 3, -hw, sA, hw, cls);
        rc.n += 4;
        rc.idx.push(b0, b0 + 1, b0 + 2, b0, b0 + 2, b0 + 3);
        if (j > 0) { // joint fan where the heading bends (quad strips leave notches)
          const p0 = pts[j - 1];
          let ux0 = a[0] - p0[0], uz0 = a[1] - p0[1];
          const L0 = Math.hypot(ux0, uz0) || 1;
          ux0 /= L0; uz0 /= L0;
          if (ux0 * dx + uz0 * dz < 0.99) {
            let ddx = ux0 + dx, ddz = uz0 + dz;
            const dl = Math.hypot(ddx, ddz) || 1;
            rcFan(a[0], ya, a[1], hw, c.r * 255, c.g * 255, c.b * 255, sA, ddx / dl, ddz / dl, cls);
          }
        }
      }
    }
    // -------- landmark rebuilds: City Hall tower + One & Two Liberty Place --------
    // (their OSM parts were skipped above; research-backed massing/colors)
    const lmGlass = [], lmTrim = [];
    {
      const ryG = Math.atan2(-fl.nz, fl.nx);           // rotate local +x onto the grid's east-west
      const sqPoly = (cx, cz, w, d) => [[-w / 2, -d / 2], [w / 2, -d / 2], [w / 2, d / 2], [-w / 2, d / 2]]
        .map(([u, v]) => [cx + fl.nx * u + fl.dx * v, cz + fl.nz * u + fl.dz * v]);
      const gPrism = (cx, cz, w, len, eaveY, apexY, alongNS) => {
        // gable prism: ridge through the center, sloping to eaves on both sides
        const hw = w / 2, hl = len / 2;
        const t = [
          -hl, eaveY, -hw, hl, apexY, 0, hl, eaveY, -hw, -hl, eaveY, -hw, -hl, apexY, 0, hl, apexY, 0,
          hl, eaveY, hw, -hl, apexY, 0, -hl, eaveY, hw, hl, eaveY, hw, hl, apexY, 0, -hl, apexY, 0,
          hl, eaveY, -hw, hl, apexY, 0, hl, eaveY, hw,
          -hl, eaveY, hw, -hl, apexY, 0, -hl, eaveY, -hw,
        ];
        const g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(t), 3));
        g.computeVertexNormals();
        g.rotateY(ryG + (alongNS ? Math.PI / 2 : 0));
        g.translate(cx, 0, cz);
        return g;
      };
      const pyr4 = (cx, cz, w, y0, y1, rT) => {
        const g = new THREE.CylinderGeometry(rT || 0.01, w * 0.707, y1 - y0, 4, 1);
        g.rotateY(Math.PI / 4 + ryG);
        g.translate(cx, (y0 + y1) / 2, cz);
        return g;
      };
      const crown = (cx, cz, base, tiers, gc, wc) => {
        for (const [w, wallTop, apex] of tiers) {
          lmGlass.push({ geom: gPrism(cx, cz, w, w, base + wallTop, base + apex, false), color: gc, style: 3 });
          lmGlass.push({ geom: gPrism(cx, cz, w, w, base + wallTop, base + apex, true), color: gc, style: 3 });
          // white trim: eave band + crossed ridge caps read as the nested chevrons
          lmTrim.push({ geom: box(w + 0.9, 1.3, w + 0.9, cx, base + wallTop + 0.2, cz, ryG), color: wc, style: 3 });
          for (const ns of [0, 1]) {
            const rg = box(w, 0.75, 0.75, 0, 0, 0, 0);
            rg.rotateY(ryG + ns * Math.PI / 2);
            rg.translate(cx, base + apex - 0.2, cz);
            lmTrim.push({ geom: rg, color: wc, style: 3 });
          }
        }
      };
      const cWhite = new THREE.Color(0xdce9f1), cSilver = new THREE.Color(0xcfd6db);
      // --- One Liberty Place (17th & Market): sheer blue shaft, four gabled tiers, needle spire
      {
        const cx = -1995, cz = -785, base = siteY(cx, cz, 'ground');
        const gc = new THREE.Color(0x4f7897), gcCrown = new THREE.Color(0x35679a);
        c.set(0x9c9186);
        appendBuilding(getChunk(cx, cz), sqPoly(cx, cz, 56, 56), base - 1, base + 12, c, 5, base);
        c.copy(gc);
        appendBuilding(getGlassChunk(cx, cz), sqPoly(cx, cz, 48.5, 48.5), base - 1, base + 212, c, 3, base);
        for (const [w, top] of [[36, 223], [26, 233], [17, 242]]) {
          appendBuilding(getGlassChunk(cx, cz), sqPoly(cx, cz, w, w), base + 180, base + top, c, 3, base);
        }
        crown(cx, cz, base, [[48.5, 212, 226], [36, 223, 237], [26, 233, 244], [17, 242, 251]], gcCrown, cWhite);
        lmTrim.push({ geom: pyr4(cx, cz, 8, base + 251, base + 258, 1.0), color: cSilver, style: 3 });
        const mast = new THREE.CylinderGeometry(0.7, 1.0, 23, 8); mast.translate(cx, base + 258 + 11.5, cz);
        lmTrim.push({ geom: mast, color: cSilver, style: 3 });
        const ndl = new THREE.CylinderGeometry(0.05, 0.4, 7, 6); ndl.translate(cx, base + 281 + 3.5, cz);
        lmTrim.push({ geom: ndl, color: cSilver, style: 3 });
      }
      // --- Two Liberty Place (16th & Chestnut): squatter, two big gable tiers, white finial
      {
        const cx = -1937, cz = -689, base = siteY(cx, cz, 'ground');
        const gc = new THREE.Color(0x4a7ba3), gcCrown = new THREE.Color(0x35679a);
        c.copy(gc);
        appendBuilding(getGlassChunk(cx, cz), sqPoly(cx, cz, 38.5, 38.5), base - 1, base + 150, c, 3, base);
        appendBuilding(getGlassChunk(cx, cz), sqPoly(cx, cz, 36, 36), base + 148, base + 185, c, 3, base);
        appendBuilding(getGlassChunk(cx, cz), sqPoly(cx, cz, 34, 34), base + 183, base + 207, c, 3, base);
        appendBuilding(getGlassChunk(cx, cz), sqPoly(cx, cz, 22, 22), base + 205, base + 224, c, 3, base);
        crown(cx, cz, base, [[34, 207, 228], [22, 224, 253]], gcCrown, cWhite);
        lmTrim.push({ geom: pyr4(cx, cz, 5, base + 253, base + 258, 0.4), color: cWhite, style: 3 });
      }
      // --- City Hall: the full Second Empire block (its outline was dropped at pack
      // time for containing part centroids, and the wings were never mapped as parts,
      // so the tower used to rise from bare ground), plus the ornate tower and Penn
      {
        const cx = -1603, cz = -802, base = siteY(cx, cz, 'ground');
        const bx = cx + fl.dx * 55, bz = cz + fl.dz * 55;    // block center: tower on the north face
        const cStone = new THREE.Color(0xb3aa99);
        const cSlate = new THREE.Color(0x51565b);
        const cTower = new THREE.Color(0xc4bdb0);
        const cWhiteM = new THREE.Color(0xdde0e2);           // painted metal above the masonry limit
        const cDome = new THREE.Color(0xbfc9d3);
        const cPenn = new THREE.Color(0x4c4536);             // weathered bronze, warm dark
        // hollow square around the courtyard, arched-window facade style, mansard wings
        c.copy(cStone);
        appendBuilding(getChunk(bx, bz), sqPoly(bx, bz, 148, 143), base - 1, base + 27, c, 1, base, [sqPoly(bx, bz, 64, 59)]);
        for (const [du, dv, ns] of [[0, -50.5, false], [0, 50.5, false], [-53, 0, true], [53, 0, true]]) {
          const wx = bx + fl.nx * du + fl.dx * dv, wz = bz + fl.nz * du + fl.dz * dv;
          lmTrim.push({ geom: gPrism(wx, wz, 40, ns ? 139 : 144, base + 26.9, base + 33.5, ns), color: cSlate, style: 3 });
        }
        for (const su of [-1, 1]) for (const sv of [-1, 1]) { // corner pavilions with steep caps
          const px2 = bx + fl.nx * su * 62 + fl.dx * sv * 59.5, pz2 = bz + fl.nz * su * 62 + fl.dz * sv * 59.5;
          c.copy(cStone);
          appendBuilding(getChunk(px2, pz2), sqPoly(px2, pz2, 25, 25), base - 1, base + 32, c, 1, base);
          lmTrim.push({ geom: pyr4(px2, pz2, 21, base + 32, base + 43, 3.0), color: cSlate, style: 3 });
        }
        for (const [du, dv] of [[74, 0], [-74, 0], [0, 71.5]]) { // center pavilions (E/W/S; N is the tower)
          const px2 = bx + fl.nx * du + fl.dx * dv, pz2 = bz + fl.nz * du + fl.dz * dv;
          c.copy(cStone);
          appendBuilding(getChunk(px2, pz2), sqPoly(px2, pz2, du === 0 ? 30 : 22, du === 0 ? 22 : 30), base - 1, base + 31, c, 1, base);
          lmTrim.push({ geom: pyr4(px2, pz2, 19, base + 31, base + 41, 2.6), color: cSlate, style: 3 });
        }
        // tower: arched-window masonry shaft to the 337 ft masonry limit, in stages
        c.copy(cTower);
        appendBuilding(getChunk(cx, cz), sqPoly(cx, cz, 26, 26), base - 1, base + 40, c, 1, base);
        appendBuilding(getChunk(cx, cz), sqPoly(cx, cz, 22, 22), base + 38, base + 96, c, 1, base);
        appendBuilding(getChunk(cx, cz), sqPoly(cx, cz, 19, 19), base + 94, base + 102.7, c, 1, base);
        // white cast-iron clock stage with corner turrets
        c.copy(cWhiteM);
        appendBuilding(getChunk(cx, cz), sqPoly(cx, cz, 16.5, 16.5), base + 102.7, base + 124, c, 1, base);
        for (const su of [-1, 1]) for (const sv of [-1, 1]) {
          const tx = cx + fl.nx * su * 8 + fl.dx * sv * 8, tz = cz + fl.nz * su * 8 + fl.dz * sv * 8;
          const tur = new THREE.CylinderGeometry(1.5, 1.5, 23, 8); tur.translate(tx, base + 103 + 11.5, tz);
          lmTrim.push({ geom: tur, color: cWhiteM, style: 3 });
          const tc = new THREE.CylinderGeometry(0.1, 1.5, 3.2, 8); tc.translate(tx, base + 126.5 + 1.6, tz);
          lmTrim.push({ geom: tc, color: cDome, style: 3 });
        }
        for (const ns of [0, 1]) for (const s of [-1, 1]) {   // amber clock faces on dark surrounds
          const ux = ns ? fl.dx : fl.nx, uz = ns ? fl.dz : fl.nz;
          const rim = new THREE.CylinderGeometry(4.6, 4.6, 0.4, 20);
          rim.rotateZ(Math.PI / 2);
          rim.rotateY(ryG + ns * Math.PI / 2);
          rim.translate(cx + ux * s * 8.3, base + 116, cz + uz * s * 8.3);
          lmTrim.push({ geom: rim, color: new THREE.Color(0x474c50), style: 3 });
          const disc = new THREE.CylinderGeometry(3.95, 3.95, 0.6, 20);
          disc.rotateZ(Math.PI / 2);
          disc.rotateY(ryG + ns * Math.PI / 2);
          disc.translate(cx + ux * s * 8.45, base + 116, cz + uz * s * 8.45);
          lmTrim.push({ geom: disc, color: new THREE.Color(0xe9dca6), style: 3 });
        }
        // ogee dome as stacked frustums, then the lantern
        for (const [w0, w1, y0, y1] of [[16.5, 12.5, 124, 133], [12.5, 7.5, 133, 143], [7.5, 3.6, 143, 151.5]]) {
          const f = new THREE.CylinderGeometry(w1 * 0.707, w0 * 0.707, y1 - y0, 4, 1);
          f.rotateY(Math.PI / 4 + ryG);
          f.translate(cx, base + (y0 + y1) / 2, cz);
          lmTrim.push({ geom: f, color: cDome, style: 3 });
        }
        const lant = new THREE.CylinderGeometry(2.0, 2.6, 4.3, 8); lant.translate(cx, base + 151.5 + 2.15, cz);
        lmTrim.push({ geom: lant, color: cWhiteM, style: 3 });
        // William Penn — 37 ft figure sculpted from primitives: stockinged calves under
        // a knee-length coat flaring at the hem, broad shoulders, brimmed hat, left arm
        // extended northeast (toward Penn Treaty Park). Reads as the statue, not a post.
        const y0 = base + 155.8;
        const pennAt = (g, dx2, y, dz2) => { g.translate(cx + dx2, y, cz + dz2); lmTrim.push({ geom: g, color: cPenn, style: 3 }); };
        const s2 = Math.SQRT1_2;
        const nex = (fl.nx - fl.dx) * s2, nez = (fl.nz - fl.dz) * s2;   // northeast, unit
        const pex = -nez, pez = nex;                                     // perpendicular (NW)
        pennAt(new THREE.CylinderGeometry(1.35, 1.55, 0.5, 10), 0, y0 + 0.25, 0);            // base plinth
        for (const sgn of [-1, 1])                                                            // calves
          pennAt(new THREE.CylinderGeometry(0.30, 0.36, 1.7, 6), pex * sgn * 0.44, y0 + 0.85, pez * sgn * 0.44);
        pennAt(new THREE.CylinderGeometry(1.02, 1.58, 5.0, 10), 0, y0 + 3.9, 0);             // coat, flared hem
        pennAt(new THREE.CylinderGeometry(1.24, 1.02, 2.9, 10), 0, y0 + 7.85, 0);            // torso to shoulders
        pennAt(new THREE.CylinderGeometry(0.46, 0.52, 0.7, 6), 0, y0 + 9.45, 0);             // neck + cravat
        pennAt(new THREE.SphereGeometry(0.66, 8, 6), 0, y0 + 10.15, 0);                      // head (long hair)
        pennAt(new THREE.CylinderGeometry(1.12, 1.12, 0.16, 10), 0, y0 + 10.62, 0);          // hat brim
        pennAt(new THREE.CylinderGeometry(0.72, 0.64, 0.62, 8), 0, y0 + 10.95, 0);           // hat crown
        {                                                                                     // left arm, extended NE
          const arm = new THREE.CylinderGeometry(0.24, 0.30, 2.5, 6);
          arm.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new V3(0, 1, 0), new V3(nex, -0.34, nez).normalize()));
          pennAt(arm, nex * 1.55, y0 + 8.35, nez * 1.55);
          pennAt(new THREE.SphereGeometry(0.30, 6, 5), nex * 2.75, y0 + 7.9, nez * 2.75);     // hand
        }
        {                                                                                     // right arm, down along the coat with the charter
          const arm = new THREE.CylinderGeometry(0.24, 0.28, 2.4, 6);
          arm.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new V3(0, 1, 0), new V3(-nex * 0.30, 1, -nez * 0.30).normalize()));
          pennAt(arm, -nex * 1.25, y0 + 7.5, -nez * 1.25);
          pennAt(new THREE.BoxGeometry(0.85, 1.05, 0.5), -nex * 1.55, y0 + 6.1, -nez * 1.55); // charter scroll
        }
      }
      // --- Philadelphia Museum of Art: golden Kasota-stone U on Fairmount hill,
      // blue tile gable roofs, central temple portico, wing pediments, court
      // fountain, and the Rocky steps cascading toward Eakins Oval. The OSM
      // footprint (a flat 10 m extrusion) is skipped via BRIDGE_SKIP above.
      {
        const O = [-3112, -2242];                          // center of the central block
        const fu = [0.717, 0.697];                         // unit axis toward the steps (SE, down the Parkway)
        const pv = [-0.697, 0.717];                        // across-axis unit (same handedness as the grid frame)
        const pt = (u, v) => [O[0] + fu[0] * u + pv[0] * v, O[1] + fu[1] * u + pv[1] * v];
        const quad = (u0, u1, v0, v1) => [pt(u0, v0), pt(u1, v0), pt(u1, v1), pt(u0, v1)];
        let T = -1e9;
        for (const q of [pt(-70, -95), pt(-70, 95), pt(55, 95), pt(55, -95), pt(0, 0)]) T = Math.max(T, siteY(q[0], q[1], 'ground'));
        T += 1.0;                                          // terrace deck level
        const chk = getChunk(O[0], O[1]);
        const cGold = new THREE.Color(0x8a744c);           // Kasota limestone (legacy pipeline lifts ~2.2x)
        const cGoldL = new THREE.Color(0x97814f);          // columns, a shade lighter
        const cStone = new THREE.Color(0x6f6455);          // terrace + steps
        const cCourt = new THREE.Color(0x7d7264);          // forecourt paving
        const cRoofM = new THREE.Color(0x2e3d47);          // blue-gray tile
        const cRed = new THREE.Color(0x5e2f26);            // tympanum brick-red
        const roof = (cu, cv, w, len, eave, apex, alongU, col) => {
          // gable prism in the museum's own frame (gPrism is grid-locked)
          const hl = len / 2, hw = w / 2;
          const t = [
            -hl, eave, -hw, hl, apex, 0, hl, eave, -hw, -hl, eave, -hw, -hl, apex, 0, hl, apex, 0,
            hl, eave, hw, -hl, apex, 0, -hl, eave, hw, hl, eave, hw, hl, apex, 0, -hl, apex, 0,
            hl, eave, -hw, hl, apex, 0, hl, eave, hw,
            -hl, eave, hw, -hl, apex, 0, -hl, eave, -hw,
          ];
          const pos = [];
          for (let i2 = 0; i2 < t.length; i2 += 3) {
            const lu = t[i2], lv = t[i2 + 2];
            const w2 = alongU ? pt(cu + lu, cv + lv) : pt(cu - lv, cv + lu); // rotate, never mirror
            pos.push(w2[0], t[i2 + 1], w2[1]);
          }
          const g = new THREE.BufferGeometry();
          g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
          g.computeVertexNormals();
          lmTrim.push({ geom: g, color: col || cRoofM, style: 3 });
        };
        const colAt = (u, v, r2, y0c, y1c) => {
          const g = new THREE.CylinderGeometry(r2, r2 * 1.06, y1c - y0c, 8);
          const w2 = pt(u, v);
          g.translate(w2[0], (y0c + y1c) / 2, w2[1]);
          lmTrim.push({ geom: g, color: cGoldL, style: 3 });
        };
        // terrace plinth (skirted well below the hilltop) and forecourt paving
        c.copy(cStone);
        appendBuilding(chk, quad(-70, 55, -95, 95), T - 9, T, c, 3, T - 9);
        c.copy(cCourt);
        appendBuilding(chk, quad(-15, 55, -45, 45), T, T + 0.12, c, 3, T);
        // main masses: central temple block, rear range, forward wings — style-1
        // walls give them the tall arched fenestration
        c.copy(cGold);
        appendBuilding(chk, quad(-40, 15, -40, 40), T - 1, T + 25, c, 1, T);
        appendBuilding(chk, quad(-70, -40, -95, 95), T - 1, T + 19, c, 1, T);
        appendBuilding(chk, quad(-40, 58, 48, 95), T - 1, T + 19, c, 1, T);
        appendBuilding(chk, quad(-40, 58, -95, -48), T - 1, T + 19, c, 1, T);
        roof(-12.5, 0, 80, 55, T + 25, T + 34, true);      // central ridge, pediment ends fore/aft
        roof(-55, 0, 30, 190, T + 19, T + 25, false);      // rear range, gable ends face NE/SW
        roof(9, 71.5, 47, 98, T + 19, T + 26, true);       // wings — pediment ends face the steps
        roof(9, -71.5, 47, 98, T + 19, T + 26, true);
        // central portico: stepped podium, 8 columns, entablature, pediment + red tympanum
        c.copy(cStone);
        appendBuilding(chk, quad(15, 29, -17, 17), T, T + 3.5, c, 3, T);
        appendBuilding(chk, quad(15, 25, -16, 16), T + 3.5, T + 7, c, 3, T);
        for (let i2 = 0; i2 < 8; i2++) colAt(19.5, -14 + 4 * i2, 0.95, T + 7, T + 19.5);
        c.copy(cGold);
        appendBuilding(chk, quad(12, 24, -17, 17), T + 19.5, T + 21.5, c, 3, T);
        // golden pediment shell with the brick-red tympanum nested inside: the red
        // prism is narrower and lower so only its end triangles poke past the shell
        roof(18, 0, 34, 12, T + 21.5, T + 27.5, true, cGold);
        roof(18, 0, 29, 12.6, T + 22.0, T + 26.6, true, cRed);
        // wing-end porticos facing the forecourt steps
        for (const sv of [-1, 1]) {
          c.copy(cStone);
          appendBuilding(chk, quad(54, 64, sv * 71.5 - 19, sv * 71.5 + 19), T, T + 6.5, c, 3, T);
          for (let i2 = 0; i2 < 6; i2++) colAt(59, sv * 71.5 - 16 + 6.4 * i2, 0.8, T + 6.5, T + 17.5);
          c.copy(cGold);
          appendBuilding(chk, quad(56, 61, sv * 71.5 - 18, sv * 71.5 + 18), T + 17.5, T + 19, c, 3, T);
        }
        // court fountain: octagonal stone ring + water
        {
          const w2 = pt(38, 0);
          const ring = new THREE.CylinderGeometry(10.5, 10.8, 0.9, 8);
          ring.translate(w2[0], T + 0.45, w2[1]);
          lmTrim.push({ geom: ring, color: new THREE.Color(0x8d8272), style: 3 });
          const water = new THREE.CylinderGeometry(8.8, 8.8, 0.5, 16);
          water.translate(w2[0], T + 0.55, w2[1]);
          lmTrim.push({ geom: water, color: new THREE.Color(0x2e6f8a), style: 3 });
        }
        // the Rocky steps: eight broad flights descending the hill toward the
        // Oval. Terrain-safe: the DEM hill bulges above the straight descent
        // line, so each flight tops out just above the ground beneath it and the
        // run never rises downhill — the hillside used to poke through between
        // flights and read as bare white stripes.
        {
          const bot = pt(105, 0);
          const yBot = siteY(bot[0], bot[1], 'ground') + 0.6;
          c.copy(cStone);
          const yT = [];
          for (let i2 = 0; i2 < 8; i2++) {
            let y = T + 0.5 + (yBot - (T + 0.5)) * (i2 + 1) / 8;
            for (const uv of [[6.3 * i2, -34], [6.3 * i2, 34], [6.3 * (i2 + 1), -34], [6.3 * (i2 + 1), 34], [6.3 * (i2 + 0.5), 0]]) {
              const q = pt(55 + uv[0], uv[1]);
              y = Math.max(y, siteY(q[0], q[1], 'ground') + 0.22);
            }
            yT.push(y);
          }
          for (let i2 = 6; i2 >= 0; i2--) yT[i2] = Math.max(yT[i2], yT[i2 + 1] + 0.2);
          for (let i2 = 0; i2 < 8; i2++) {
            appendBuilding(chk, quad(55 + 6.3 * i2, 55 + 6.3 * (i2 + 1) + 0.4, -34, 34), yT[i2] - 7, yT[i2], c, 3, yT[i2] - 7);
          }
        }
        // (the Fairmount greening itself lives in the wide-heightfield builder —
        // the ground cells there are vertex-tinted to park green; a draped lawn
        // here rode above the road ribbons on the bumpy hill and was removed)
      }
      // --- Battleship New Jersey (BB-62), moored on the Camden shore: the OSM
      // hull outline is extruded as the real haze-gray hull, then superstructure,
      // three triple 16-inch turrets, funnels, and masts go on in the hull frame
      if (njPoly) {
        const ob = orientedBox(njPoly);
        const a = obbAxis(ob);
        const W0 = TERRAIN.water;
        let wP = 0, nP = 0, wM = 0, nM = 0;
        for (const q of njPoly) {
          const du = (q[0] - ob.cx) * a.ax + (q[1] - ob.cz) * a.az;
          const dv = (q[0] - ob.cx) * a.px + (q[1] - ob.cz) * a.pz;
          if (du > a.hl * 0.7) { wP += Math.abs(dv); nP++; }
          if (du < -a.hl * 0.7) { wM += Math.abs(dv); nM++; }
        }
        const bow = (wP / Math.max(1, nP)) < (wM / Math.max(1, nM)) ? 1 : -1; // pointier end
        const hx = a.ax * bow, hz = a.az * bow;            // unit vector toward the bow
        const ryS = Math.atan2(-hz, hx);
        const SC = a.hl / 135;                             // hull frame vs the real 270 m
        const at2 = (u, v) => [ob.cx + hx * u * SC + a.px * v, ob.cz + hz * u * SC + a.pz * v];
        const chkN = getChunk(ob.cx, ob.cz);
        const cHull = new THREE.Color(0x383d42);
        c.copy(cHull);
        appendBuilding(chkN, njPoly, W0 - 1.5, W0 + 8.7, c, 3, W0);
        const gray = new THREE.Color(0x484d53), turret = new THREE.Color(0x43474c), barrelC = new THREE.Color(0x393d42);
        const shipBox = (u, v, y, len, h2, wid, col) => {
          const [x2, z2] = at2(u, v);
          lmTrim.push({ geom: box(len, h2, wid, x2, y, z2, ryS), color: col, style: 3 });
        };
        const shipCyl = (u, v, y0c, y1c, r0, r1, col, seg) => {
          const [x2, z2] = at2(u, v);
          const g = new THREE.CylinderGeometry(r0, r1, y1c - y0c, seg || 8);
          g.translate(x2, (y0c + y1c) / 2, z2);
          lmTrim.push({ geom: g, color: col, style: 3 });
        };
        const D0 = W0 + 8.7;                               // main deck
        shipBox(-4, 0, D0 + 2.2, 84, 4.4, 17, gray);       // 01 level
        shipBox(-3, 0, D0 + 6.0, 56, 3.4, 13.5, gray);     // 02 level
        shipBox(22, 0, D0 + 10.5, 10, 5.6, 9, gray);       // forward tower
        shipBox(22, 0, D0 + 15.0, 6, 3.4, 6, gray);        // fire control
        shipCyl(22, 0, D0 + 16.7, D0 + 22.5, 1.5, 1.8, gray);
        shipCyl(16, 0, D0 + 18, D0 + 34, 0.55, 0.8, new THREE.Color(0x33373c), 6);  // main mast
        for (const [fu] of [[2], [-16]]) {                 // funnels with black caps
          shipCyl(fu, 0, D0 + 7.5, D0 + 14.5, 2.5, 3.2, gray);
          shipCyl(fu, 0, D0 + 14.5, D0 + 16.0, 2.6, 2.6, new THREE.Color(0x16181a));
        }
        shipBox(-30, 0, D0 + 8.6, 8, 5.2, 7.5, gray);      // aft tower
        shipCyl(-30, 0, D0 + 11.2, D0 + 24, 0.5, 0.7, new THREE.Color(0x33373c), 6); // aft mast
        const turretAt = (u, y, dir) => {
          shipBox(u, 0, y + 1.7, 14, 3.4, 11, turret);
          for (const v of [-2.7, 0, 2.7]) {
            const g = new THREE.CylinderGeometry(0.42, 0.6, 16.5, 6);
            g.rotateZ(Math.PI / 2 - 0.09);                 // horizontal, tipped up slightly
            g.rotateY(ryS + (dir < 0 ? Math.PI : 0));
            const [x2, z2] = at2(u + dir * 14, v);
            g.translate(x2, y + 2.6, z2);
            lmTrim.push({ geom: g, color: barrelC, style: 3 });
          }
        };
        turretAt(62, D0, 1);                                // turret 1, main deck
        shipBox(43, 0, D0 + 1.6, 13, 3.2, 11.5, gray);      // turret 2 barbette
        turretAt(43, D0 + 3.2, 1);                          // turret 2, superfiring
        turretAt(-58, D0, -1);                              // turret 3, facing aft
      }
    }
    // parks, water, piers (water splits out onto the animated river material)
    const areaParts = [], waterAreaParts = [];
    for (let i = 0; i < hdr[3]; i++) {
      const n = body[k++], kind = body[k++];
      const poly = new Array(n);
      for (let j = 0; j < n; j++) poly[j] = [body[k++] * S, body[k++] * S];
      const [acx, acz] = polyCentroid(poly);
      // the stadium/arena builders own their interiors — OSM's pitch/park drapes
      // in there just z-fight the bowls
      if (kind === 0 && (Math.hypot(acx + 1869, acz - 4375) < 140 || Math.hypot(acx + 1920, acz - 4932) < 150 || Math.hypot(acx + 2327, acz - 4880) < 120)) continue;
      // the Art Museum build owns its hilltop: OSM's paved/park drapes there lie
      // per-vertex on the steep hill and rendered as sheared slabs over the steps
      if (kind !== 1 && Math.hypot(acx + 3080, acz + 2210) < 190) continue;
      // and its Fairmount lawn owns the wider grounds: the white paved-area flats
      // (parking aprons, plazas) blanketed the hill at +1.2 over the grass —
      // any-vertex test, since a big apron's centroid can sit outside the zone
      if (kind > 1 && poly.some((q) => q[0] > -3850 && q[0] < -2480 && q[1] > -2950 && q[1] < -1720)) continue;
      // the Walt Whitman's OSM outline maps as a paved area — it rendered as a
      // flat gray slab floating on the river under the real suspension deck
      if (kind !== 1 && wwbNear(acx, acz)) continue;
      try {
        if (kind === 0) {
          GRASS_POLYS.push(poly);
          // conformed to the drawn ground (conformDrape); a playground inside a park rises a
          // little above it by area so the 403 nested rings never sit coplanar (gotcha 6)
          const pa = Math.abs(signedArea(poly));
          areaParts.push({ geom: pa > 200 ? conformDrape(poly, LAYER.park + 0.03 * (1 - Math.min(1, pa / 20000)), 20) : flatPoly(poly, null, LAYER.park), color: new THREE.Color(COLORS.park).multiplyScalar(lerp(1 - PARK_SHADE_SPREAD, 1 + PARK_SHADE_SPREAD, hash01(i))), style: 3 });
        }
        else if (kind === 1) { noSow(poly); const wcc = polyCentroid(poly); if (!(schRaster && schRaster(wcc[0], wcc[1]))) waterAreaParts.push({ geom: flatShorePoly(poly, null, TERRAIN.water + 0.55, Math.abs(signedArea(poly)) > 20000 ? 2 : 1), color: new THREE.Color(COLORS.water), style: 3 }); }
        else { noSow(poly); areaParts.push({ geom: flatPoly(poly, null, 1.2), color: new THREE.Color(COLORS.pier), style: 3 }); }
      } catch (e) { /* degenerate polygon */ }
    }
    loadmsg.textContent = 'Raising the outer districts, uploading';
    await yieldNow();
    for (const ch of glassChunks.values()) {
      const g = ch.geometry(false);
      if (!outerGlassMat) {
        outerGlassMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.12, metalness: 0.7, envMapIntensity: 1.15 });
        outerGlassMat.emissive = new THREE.Color(0xffdca6);
        outerGlassMat.emissiveIntensity = 0;
        // curtain-wall rhythm: darker spandrel band at each floor line, thin vertical
        // mullions between panels — world-space, anti-aliased, fading with distance
        outerGlassMat.onBeforeCompile = (sh) => {
          sh.uniforms.uDetFar = detFarUniform;
          sh.vertexShader = sh.vertexShader
            .replace('#include <common>', '#include <common>\nattribute float aStyle; varying vec3 vGWp; varying vec3 vGNm; varying float vGSt;')
            .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvGWp = (modelMatrix * vec4(transformed, 1.0)).xyz;\nvGNm = normalize(mat3(modelMatrix) * objectNormal);\nvGSt = aStyle;');
          sh.fragmentShader = sh.fragmentShader
            .replace('#include <common>', '#include <common>\nuniform float uDetFar;\nvarying vec3 vGWp; varying vec3 vGNm; varying float vGSt;\nfloat gWall = 0.0; float gLit = 0.0; float gSpand = 0.0;')
            .replace('#include <color_fragment>', '#include <color_fragment>\n{\n' +
              '  vec3 nn = normalize(vGNm);\n' +
              '  float wall = step(abs(nn.y), 0.35);\n' +
              '  vec2 dirH = (abs(nn.x) + abs(nn.z)) > 1e-4 ? normalize(nn.xz) : vec2(1.0, 0.0);\n' +
              '  float u = dot(vGWp.xz, vec2(-dirH.y, dirH.x));\n' +
              '  float aaU = fwidth(u) + 1e-4, aaV = fwidth(vGWp.y) + 1e-4;\n' +
              '  float det = clamp(1.0 - (max(aaU, aaV) * uDetFar - 0.8) / 2.2, 0.0, 1.0) * wall;\n' +
              '  diffuseColor.rgb *= mix(0.72, 1.12, clamp(vGWp.y / 220.0, 0.0, 1.0));\n' +
              // the curtain-wall variants: 21 silver spandrel bands (the Liberty Place family),
              // 22 dark glass with a bare floor line, 23 a light concrete grid holding the glass
              '  float gv = floor(vGSt + 0.5);\n' +
              '  float fpG = (gv == 22.0) ? 3.6 : ((gv == 23.0) ? 3.5 : 4.0);\n' +
              '  float spW = (gv == 21.0) ? 0.9 : ((gv == 22.0) ? 0.3 : ((gv == 23.0) ? 0.55 : 0.5));\n' +
              '  float muP = (gv == 22.0) ? 1.2 : ((gv == 23.0) ? 3.2 : 1.5);\n' +
              '  float muW = (gv == 23.0) ? 0.45 : 0.05;\n' +
              '  float dv = abs(fract(vGWp.y / fpG + 0.5) - 0.5) * fpG;\n' +
              '  float spand = 1.0 - smoothstep(spW, spW + aaV, dv);\n' +
              '  float du = abs(fract(u / muP + 0.5) - 0.5) * muP;\n' +
              '  float mull = 1.0 - smoothstep(muW, muW + aaU, du);\n' +
              '  if (gv == 21.0) { diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.62, 0.66, 0.70), det * spand * 0.8); diffuseColor.rgb *= 1.0 - det * mull * 0.2; }\n' +
              '  else if (gv == 22.0) { diffuseColor.rgb *= (1.0 - det * (spand * 0.4 + mull * 0.25)) * 0.72; }\n' +
              '  else if (gv == 23.0) { diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.70, 0.69, 0.66), det * max(spand, mull) * 0.9); }\n' +
              '  else { diffuseColor.rgb *= 1.0 - det * (spand * 0.38 + mull * 0.22); }\n' +
              '  vec2 pid = vec2(floor(u / muP), floor(vGWp.y / fpG));\n' +
              '  float ph = fract(sin(dot(pid, vec2(127.1, 311.7))) * 43758.5453);\n' +
              // ~28% of curtain-wall panels glow at night, varied; past the per-panel
              // fade the tower keeps only its soft average (the panel-cluster LOD
              // read as big square lights from distance, removed at the owner's request)
              '  gWall = wall;\n' +
              '  gSpand = spand;\n' +
              '  gLit = mix(0.10, step(0.72, ph) * (0.4 + 0.6 * fract(ph * 7.3)), det);\n' +
              '}')
            .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance *= gWall * gLit * (1.0 - gSpand * 0.85) * 3.2;');
        };
      }
      addChunkMesh(g, outerGlassMat);
    }
    if (lmGlass.length && outerGlassMat) {   // Liberty Place crowns share the curtain-wall glass
      const g = mergeColored(lmGlass); freeOnUpload(g);
      addChunkMesh(g, outerGlassMat).castShadow = true;
    }
    for (const cp of crownTrim) lmTrim.push(cp);
    if (lmTrim.length) {                     // white chevron trim, masts, City Hall metalwork + Penn
      const g = mergeColored(lmTrim); freeOnUpload(g);
      addChunkMesh(g, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.5, metalness: 0.3 })).castShadow = true;
    }
    for (const ch of chunks.values()) addChunkMesh(ch.geometry(true), cityMat);
    flushUploads(true);
    await yieldNow();
    if (rc.n) {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(rc.pos), 3));
      g.setAttribute('color', new THREE.BufferAttribute(new Uint8Array(rc.col), 3, true));
      if (rc.lane) g.setAttribute('aLane', new THREE.BufferAttribute(rc.lane.subarray(0, rc.n * 4), 4));
      g.setIndex(rc.idx);
      g.computeVertexNormals();
      g.computeBoundingSphere();
      freeOnUpload(g);
      if (/[?&]dev\b/.test(location.search)) console.info('roads: ' + rc.label + ' rc.n = ' + rc.n + (rc.lane ? ' with aLane' : ' without aLane'));
      rc.pos = rc.col = rc.idx = rc.lane = null;
      groupCity.add(new THREE.Mesh(g, roadMat({ vertexColors: true, roughness: 0.95, side: THREE.DoubleSide })));
    }
    // the sports complex is mostly asphalt: the surface lots from OSM (fetch_parking.py),
    // laid a hair above the lawn colour the ground would otherwise show.
    // The lot tunables, in one place: stored-dark colours (the legacy pipeline lifts a stored
    // value, so these read as dark asphalt beside the roads' 0x3b3833; the lead picks the final
    // pair by rendered swatch against the CS2 frame) and the lifts over the plaza layer. The
    // fill sheet and the lots are an exact pair now (both conform to the same ground), so the
    // gap between them is wider than the old 1.5 cm, and the stripes sit above both
    const LOT_FILL_COL = 0x0b0b0a, LOT_COL = 0x0e0d0c;
    const LOT_FILL_UP = 0.02, LOT_UP = 0.06, LOT_STRIPE_UP = 0.09;   // over LAYER.plaza
    const LOT_STRIPE_OPACITY = 0.5;
    if (typeof PARKING_SOUTH !== 'undefined' && PARKING_SOUTH && PARKING_SOUTH.polys) {
      const toRing = (fl2) => { const pp = new Array(fl2.length >> 1); for (let q = 0; q < pp.length; q++) pp[q] = [fl2[q * 2], fl2[q * 2 + 1]]; return pp; };
      // the district sheet first (the convex hull of the complex's lots: there is no lawn in
      // it), then each lot on top; both CONFORMED to the drawn ground (conformDrape: every
      // sheet triangle lies inside one ground triangle, so the sheet is exactly its lift above
      // the mesh everywhere). Draping them densely never converged: the ground mesh and a
      // drape are two different linear reads of one surface, off by up to half a metre, and
      // the facets showed as jagged green blobs through the asphalt
      for (const fl2 of (PARKING_SOUTH.fill || [])) {
        const pp = toRing(fl2);
        NO_SOW_RINGS.push(pp); NO_SOW_RING_BB.push(bboxOf(pp));
        try { areaParts.push({ geom: conformDrape(pp, LAYER.plaza + LOT_FILL_UP, 8), color: new THREE.Color(LOT_FILL_COL), style: 3 }); } catch (e) { /* degenerate */ }
      }
      const seg = [];
      const yAt = (x, z) => (groundMeshY(x, z) ?? drapeY(x, z, 'ground')) + LAYER.plaza + LOT_STRIPE_UP;
      for (const fl2 of PARKING_SOUTH.polys) {
        const pp = toRing(fl2);
        NO_SOW_RINGS.push(pp); NO_SOW_RING_BB.push(bboxOf(pp));
        try { areaParts.push({ geom: conformDrape(pp, LAYER.plaza + LOT_UP, 10), color: new THREE.Color(LOT_COL), style: 3 }); } catch (e) { continue; }
        // the stalls, as they read from above: double rows 18.5 m apart, each with its two
        // stall-front lines running the row's length and ticks every 2.7 m between them.
        // Rows follow the street grid (whichever grid axis the lot's long side is nearer),
        // and every line is clipped to the lot. The lines are polylines of 3 m samples, each
        // sample on the drawn ground, so a line bends with the lot instead of cutting a
        // chord under it; the ticks split at their midpoint for the same reason
        const pc = polyCentroid(pp);
        const ob = orientedBox(pp), ax = obbAxis(ob);
        const alongNS = Math.abs(ax.ax * fl.dx + ax.az * fl.dz) > 0.707;
        const ux = alongNS ? fl.dx : fl.nx, uz = alongNS ? fl.dz : fl.nz, vx = -uz, vz = ux;
        let hl = 0, hs = 0;
        for (const q of pp) { hl = Math.max(hl, Math.abs((q[0] - pc[0]) * ux + (q[1] - pc[1]) * uz)); hs = Math.max(hs, Math.abs((q[0] - pc[0]) * vx + (q[1] - pc[1]) * vz)); }
        if (hl < 12 || hs < 12) continue;
        for (let v = -hs + 9.5; v < hs - 3; v += 18.5) {
          for (const side of [-5.5, 5.5]) {   // the stall fronts
            let run = null, px = 0, pz = 0, py = 0, runSeg = [];
            for (let u = -hl; u <= hl + 3; u += 3) {
              const x = pc[0] + ux * u + vx * (v + side), z = pc[1] + uz * u + vz * (v + side);
              const inside = u <= hl && pointInPoly(x, z, pp);
              if (inside) {
                const y = yAt(x, z);
                if (!run) { run = [x, z]; runSeg = []; }
                else runSeg.push(px, py, pz, x, y, z);   // one segment per 3 m sample
                px = x; pz = z; py = y;
              } else if (run) {
                if (Math.hypot(px - run[0], pz - run[1]) > 4) for (const sv of runSeg) seg.push(sv);
                run = null;
              }
            }
          }
          for (let u = -hl + 1.5; u < hl; u += 2.7) {   // the ticks
            const qx = pc[0] + ux * u + vx * v, qz = pc[1] + uz * u + vz * v;
            const x0 = qx - vx * 5.5, z0 = qz - vz * 5.5, x1 = qx + vx * 5.5, z1 = qz + vz * 5.5;
            if (!pointInPoly(x0, z0, pp) || !pointInPoly(x1, z1, pp)) continue;
            const ym = yAt(qx, qz);
            seg.push(x0, yAt(x0, z0), z0, qx, ym, qz, qx, ym, qz, x1, yAt(x1, z1), z1);
          }
        }
      }
      if (seg.length) {
        const lg = new THREE.BufferGeometry();
        lg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(seg), 3));
        lotStripes = new THREE.LineSegments(lg, new THREE.LineBasicMaterial({ color: 0xb8b3a8, transparent: true, opacity: LOT_STRIPE_OPACITY }));
        lotStripes.frustumCulled = false; lotStripes.renderOrder = 3;
        lotStripes.userData.op = LOT_STRIPE_OPACITY;   // the frame loop fades it with distance
        groupCity.add(lotStripes);
      }
    }
    drapeLog('the outer districts');
    if (areaParts.length) { const g = mergeColored(areaParts); freeOnUpload(g); groupCity.add(new THREE.Mesh(g, surfMat({ vertexColors: true, roughness: 0.95 }))); }
    if (waterAreaParts.length) { const g = mergeWater(waterAreaParts); freeOnUpload(g); groupCity.add(new THREE.Mesh(g, riverMat)); }
    // widen the world: camera clamps and fog
    bounds.minX = -3700; bounds.maxX = 2300; bounds.minZ = -4480; bounds.maxZ = 6400;
    fogBase.near = 5000; fogBase.far = 20000;

    // Benjamin Franklin Bridge (1926): suspension span from the 5th St anchorage to Camden
    {
      const A = [400, -940], B = [1360, -722];           // anchorages (Philadelphia -> Camden), per OSM way 575987106
      const dx = B[0] - A[0], dz = B[1] - A[1], L = Math.hypot(dx, dz);
      const ux = dx / L, uz = dz / L, ry = Math.atan2(-uz, ux);
      const yA = siteY(A[0], A[1], 'ground') + 12, yMid = TERRAIN.water + 41;
      const pry = Math.atan2(-ux, -uz);                  // frame whose local x runs across the deck
      const parts = [];
      const addP = (geom, hex) => parts.push({ geom, color: new THREE.Color(hex), style: 3 });
      const STEEL = '#8fb4c6', CABLE = '#7c9bac', STONE = '#b0a99e';
      const deckY = (t) => yA + (yMid - yA) * Math.sin(Math.PI * t) * 0.85 + (yMid - yA) * 0.15 * (1 - Math.abs(2 * t - 1));
      const segs = 40;
      for (let i = 0; i < segs; i++) {
        const t0 = i / segs, t1 = (i + 1) / segs;
        const x0 = A[0] + dx * t0, z0 = A[1] + dz * t0, x1 = A[0] + dx * t1, z1 = A[1] + dz * t1;
        const y0 = deckY(t0), y1 = deckY(t1);
        const len = L / segs;
        const slope = Math.atan2(y1 - y0, len);
        const seg = (g) => { g.rotateZ(slope); g.rotateY(ry); g.translate((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2); addP(g, STEEL); };
        seg(box(len + 0.5, 1.5, 39, 0, 0, 0, 0));                       // roadway (PATCO tracks + walkways outboard)
        for (const s of [-1, 1]) {
          seg(box(len + 0.5, 0.9, 0.9, 0, -8, s * 18.5, 0));            // stiffening-truss bottom chords
          const dl = Math.hypot(len, 7);
          const dg = box(dl, 0.7, 0.7, 0, 0, 0, 0);
          dg.rotateZ((i & 1 ? -1 : 1) * Math.atan2(7, len));            // truss diagonals, alternating
          dg.translate(0, -4.4, s * 18.5);
          seg(dg);
          seg(box(0.7, 8, 0.7, len / 2, -4.4, s * 18.5, 0));            // truss verticals
        }
      }
      // steel lattice towers: paired legs on masonry piers, X-braced above the roadway
      const topY = TERRAIN.water + 117;
      const tw = [0.23, 0.78];
      for (const t of tw) {
        const x = A[0] + dx * t, z = A[1] + dz * t;
        const dY = deckY(t);
        addP(box(46, 14, 20, x, TERRAIN.water + 3, z, pry), '#b78771'); // warm granite pier at the waterline
        for (const s of [-1, 1]) {
          addP(box(6.5, topY - TERRAIN.water - 8, 8, x - uz * s * 15.5, (TERRAIN.water + 8 + topY) / 2, z + ux * s * 15.5, pry), STEEL);
        }
        // portal struts: above the roadway, mid-height, and the cap
        const sy = [dY + 7, (dY + 7 + topY - 4) / 2, topY - 4];
        for (const yv of sy) addP(box(34, 4, 5.5, x, yv, z, pry), STEEL);
        addP(box(37, 5, 8, x, topY - 0.5, z, pry), STEEL);              // cap beam carrying the saddles
        // two X-brace panels between the struts, one more below deck to the pier
        const xPanel = (y0, y1, w2) => {
          const h = y1 - y0, dl = Math.hypot(31, h), an = Math.atan2(h, 31);
          for (const sg of [-1, 1]) {
            const g = box(dl, 1.2, 1.2, 0, 0, 0, 0);
            g.rotateZ(sg * an); g.rotateY(pry);
            g.translate(x, (y0 + y1) / 2, z);
            addP(g, STEEL);
          }
        };
        xPanel(sy[0] + 2, sy[1] - 2);
        xPanel(sy[1] + 2, sy[2] - 2);
        xPanel(TERRAIN.water + 11, dY - 3);
      }
      // granite anchorages: 50 m masonry towers the roadway threads through (DRPA: 61 x 50 m)
      for (const [ex, ez] of [A, B]) {
        const g0 = siteY(ex, ez, 'ground');
        addP(box(61, 36 - (g0 - 2), 46, ex, (g0 - 2 + 36) / 2, ez, ry), STONE);
        addP(box(42, 16, 42, ex, 42, ez, ry), '#a89f93');
        addP(box(30, 5, 38, ex, 52.5, ez, ry), '#998f82');
      }
      const cableY = (t) => { // catenary-ish: tower tops at t=0.30/0.70, sag to deck+6 at mid and ends
        if (t < 0.23) return deckY(0) + 8 + (topY - deckY(0) - 8) * Math.pow(t / 0.23, 2);
        if (t > 0.78) return deckY(1) + 8 + (topY - deckY(1) - 8) * Math.pow((1 - t) / 0.22, 2);
        const u = (t - 0.505) / 0.275; return yMid + 6 + (topY - yMid - 6) * u * u;
      };
      for (let i = 0; i < 80; i++) {
        const t0 = i / 80, t1 = (i + 1) / 80;
        for (const s of [-1, 1]) {
          const x0 = A[0] + dx * t0 - uz * s * 15.5, z0 = A[1] + dz * t0 + ux * s * 15.5, x1 = A[0] + dx * t1 - uz * s * 15.5, z1 = A[1] + dz * t1 + ux * s * 15.5;
          const y0 = cableY(t0), y1 = cableY(t1);
          const seg = Math.hypot(L / 80, y1 - y0);
          const g = box(seg + 0.3, 0.9, 0.9, 0, 0, 0, 0);
          g.rotateZ(Math.atan2(y1 - y0, L / 80));
          g.rotateY(ry);
          g.translate((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
          addP(g, CABLE);
          if (t0 > 0.05 && t0 < 0.95) addP(box(0.3, Math.max(0.5, y0 - deckY(t0)), 0.3, x0, (y0 + deckY(t0)) / 2, z0, 0), CABLE);
        }
      }
      const m = new THREE.Mesh(mergeColored(parts), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.6, metalness: 0.3 }));
      m.castShadow = true;
      groupCity.add(m);
      // traffic rides the real roadway (deckY gives deck center; the box is 1.5 thick)
      BRIDGE_DECKS.push({
        pts: [[A[0], A[1]], [B[0], B[1]]], cum: [0, L], halfW: 20,
        minX: Math.min(A[0], B[0]), maxX: Math.max(A[0], B[0]),
        minZ: Math.min(A[1], B[1]), maxZ: Math.max(A[1], B[1]),
        yAt: (s) => deckY(clamp(s / L, 0, 1)) + 0.9,
      });
    }
    // Walt Whitman Bridge (1957): suspension span on OSM's alignment, Packer Ave approach to Gloucester City
    if (typeof WWB_PTS !== 'undefined' && WWB_PTS && WWB_PTS.length > 3) {
      const line = densify(WWB_PTS, 20);
      const cum = [0];
      for (let i = 1; i < line.length; i++) cum.push(cum[i - 1] + Math.hypot(line[i][0] - line[i - 1][0], line[i][1] - line[i - 1][1]));
      // mid-span at (1318.6, 4454.4); towers 609.6 m apart, side spans 234.7 m (DRPA)
      let mi = 0, best = Infinity;
      for (let i = 0; i < line.length; i++) { const dd = Math.hypot(line[i][0] - 1318.6, line[i][1] - 4454.4); if (dd < best) { best = dd; mi = i; } }
      // The crossing is dead straight on the real bridge, but OSM's motorway line
      // hops between carriageways mid-river (a 15 m right-angle jog at mid-span)
      // and wiggles at the NJ anchorage — the deck built along it came out
      // disjointed. Project the whole span onto its straight chord, then
      // re-measure arc lengths.
      {
        const ptAt = (sv) => {
          let i = 1; while (i < cum.length - 1 && cum[i] < sv) i++;
          const tt = clamp((sv - cum[i - 1]) / Math.max(1e-6, cum[i] - cum[i - 1]), 0, 1);
          return [line[i - 1][0] + (line[i][0] - line[i - 1][0]) * tt, line[i - 1][1] + (line[i][1] - line[i - 1][1]) * tt];
        };
        const sA = cum[mi] - 660, sB = cum[mi] + 660;
        const A = ptAt(sA), B = ptAt(sB);
        for (let i = 0; i < line.length; i++) {
          if (cum[i] > sA && cum[i] < sB) {
            const tt = (cum[i] - sA) / (sB - sA);
            line[i] = [A[0] + (B[0] - A[0]) * tt, A[1] + (B[1] - A[1]) * tt];
          }
        }
        for (let i = 1; i < line.length; i++) cum[i] = cum[i - 1] + Math.hypot(line[i][0] - line[i - 1][0], line[i][1] - line[i - 1][1]);
        best = Infinity;
        for (let i = 0; i < line.length; i++) { const dd = Math.hypot(line[i][0] - 1318.6, line[i][1] - 4454.4); if (dd < best) { best = dd; mi = i; } }
      }
      {
        const mid = cum[mi], half = 304.8, side = 234.7;
        const W0 = TERRAIN.water;
        // the profile in arc length: the suspended span, the side spans, then the approaches.
        // wwb.json is one carriageway from the Schuylkill Expressway to the point where OSM's
        // bridge tag ends in Gloucester City, so the Jersey viaduct (~1 km past the cable
        // end) descends to the street there and the packed I-76 carries on at grade; the
        // Packer Avenue side stays elevated to the interchange, as it is
        const sEnd = cum[cum.length - 1], sCab = mid + half + side;
        // the landing: the last LAND metres run as one straight grade from the viaduct down
        // to a metre above the HIGHEST ground under them. Sampling the 150 m DEM point by
        // point there (a per-point floor) pitched every 20 m box up or down a few metres
        // against its neighbours, and the end of the deck read as a pile of tilted slabs
        const LAND = 400, sLand = sEnd - LAND;
        let gTop = -Infinity, jLand = -1;
        for (let i = 0; i < line.length; i++) if (cum[i] >= sLand) { if (jLand < 0) jLand = i; gTop = Math.max(gTop, siteY(line[i][0], line[i][1], 'ground')); }
        if (jLand < 0) jLand = line.length - 1;
        const yEnd = gTop + 1.0;
        const profY = (sv) => {
          const dd = Math.abs(sv - mid);
          if (dd <= half) return W0 + 49 - 6 * (dd / half) * (dd / half);
          if (dd <= half + side) return W0 + 43 - 6 * (dd - half) / side;
          if (sv > mid) return W0 + 37 + (yEnd - W0 - 37) * clamp((sv - sCab) / Math.max(1, sEnd - sCab), 0, 1);
          return W0 + 37 - 0.02 * (dd - half - side);
        };
        const yLand = Math.max(profY(cum[jLand]), siteY(line[jLand][0], line[jLand][1], 'ground') + 6, yEnd);
        // never below the ground it crosses; the landing grade is straight and monotone
        const deckYAt = (sv, x, z) => sv >= sLand ? yLand + (yEnd - yLand) * clamp((sv - sLand) / LAND, 0, 1) : Math.max(profY(sv), siteY(x, z, 'ground') + 6);
        const deckAt = (i) => deckYAt(cum[i], line[i][0], line[i][1]);
        const parts = [];
        const addP = (geom, hex) => parts.push({ geom, color: new THREE.Color(hex), style: 3 });
        for (let i = 0; i < line.length - 1; i++) {
          const a = line[i], b = line[i + 1];
          const ya = deckAt(i), yb = deckAt(i + 1);
          const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
          const g = box(L + 0.4, 8, 28, 0, 0, 0, 0); // roadway on its 8 m stiffening truss
          g.rotateZ(Math.atan2(yb - ya, L));
          g.rotateY(Math.atan2(-(b[1] - a[1]), b[0] - a[0]));
          g.translate((a[0] + b[0]) / 2, (ya + yb) / 2 - 4, (a[1] + b[1]) / 2);
          addP(g, '#75a889');
        }
        const at = (sv) => { // point + direction along the line at arc length sv
          let i = 1; while (i < cum.length - 1 && cum[i] < sv) i++;
          const tt = (sv - cum[i - 1]) / Math.max(1e-6, cum[i] - cum[i - 1]);
          const a = line[i - 1], b = line[i];
          const ux = (b[0] - a[0]) / Math.max(1e-6, cum[i] - cum[i - 1]), uz = (b[1] - a[1]) / Math.max(1e-6, cum[i] - cum[i - 1]);
          return { x: a[0] + (b[0] - a[0]) * tt, z: a[1] + (b[1] - a[1]) * tt, ux, uz, ry: Math.atan2(-uz, ux) };
        };
        const topY = W0 + 115.2;
        const idxAt = (sv) => { let i = 1; while (i < cum.length - 1 && cum[i] < sv) i++; return i; };
        for (const ts of [mid - half, mid + half]) {
          const q = at(ts);
          addP(box(53, 4, 19.5, q.x, W0 - 0.5, q.z, q.ry), '#a8a59e'); // concrete tower pier at the waterline
          for (const sg of [-1, 1]) addP(box(6, 117, 4.5, q.x - q.uz * sg * 14, W0 - 2 + 58.5, q.z + q.ux * sg * 14, q.ry), '#75a889');
          addP(box(5, 9, 32, q.x, W0 + 109, q.z, q.ry), '#75a889'); // deep top portal below the saddles
          addP(box(4, 6, 32, q.x, W0 + 36, q.z, q.ry), '#75a889');  // portal strut below the deck — legs are clean between

        }
        for (const ts of [mid - half - side - 30, mid + half + side + 30]) { // concrete anchorage blocks
          const q = at(ts);
          addP(box(61, 39.6, 36.6, q.x, deckAt(idxAt(ts)) - 30 + 19.8, q.z, q.ry), '#a8a59e');
        }
        const cableY = (sv) => {
          const dd = Math.abs(sv - mid);
          if (dd <= half) { const u = dd / half; return W0 + 48 + (topY - W0 - 48) * u * u; }
          const e = Math.min(1, (dd - half) / side);
          return topY - (topY - (W0 + 40)) * (1 - (1 - e) * (1 - e));
        };
        const c0 = mid - half - side, c1 = mid + half + side;
        for (let sv = c0; sv < c1; sv += 15) {
          for (const sg of [-1, 1]) {
            const q0 = at(sv), q1 = at(Math.min(c1, sv + 15));
            const y0 = cableY(sv), y1 = cableY(Math.min(c1, sv + 15));
            const x0 = q0.x - q0.uz * sg * 15, z0 = q0.z + q0.ux * sg * 15, x1 = q1.x - q1.uz * sg * 15, z1 = q1.z + q1.ux * sg * 15;
            const seg = Math.hypot(Math.hypot(x1 - x0, z1 - z0), y1 - y0);
            const g = box(seg + 0.3, 0.8, 0.8, 0, 0, 0, 0);
            g.rotateZ(Math.atan2(y1 - y0, Math.hypot(x1 - x0, z1 - z0)));
            g.rotateY(Math.atan2(-(z1 - z0), x1 - x0));
            g.translate((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
            addP(g, '#6b9478');
            if (Math.round(sv / 15) % 2 === 0) {
              let i = 1; while (i < cum.length - 1 && cum[i] < sv) i++;
              const dy = deckAt(i);
              if (y0 - dy > 2) addP(box(0.3, y0 - dy, 0.3, x0, (y0 + dy) / 2, z0, 0), '#6b9478');
            }
          }
        }
        const m = new THREE.Mesh(mergeColored(parts), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.6, metalness: 0.3 }));
        m.castShadow = true;
        groupCity.add(m);
        const qm = at(mid);
        labels.push({ el: (() => { const el = document.createElement('div'); el.className = 'lbl'; el.textContent = 'Walt Whitman Bridge'; labelsRoot.appendChild(el); return el; })(), pos: new V3(qm.x, W0 + 125, qm.z), visible: false, far: true });
        {  // traffic rides the deck (deckAt's profile, arc-length form; box top = deckAt)
          let mnX = Infinity, mxX = -Infinity, mnZ = Infinity, mxZ = -Infinity;
          for (const q of line) { mnX = Math.min(mnX, q[0]); mxX = Math.max(mxX, q[0]); mnZ = Math.min(mnZ, q[1]); mxZ = Math.max(mxZ, q[1]); }
          BRIDGE_DECKS.push({
            pts: line, cum, halfW: 16, minX: mnX, maxX: mxX, minZ: mnZ, maxZ: mxZ,
            yAt: (sv) => {
              const s2 = clamp(sv, 0, sEnd), q = at(s2);
              return deckYAt(s2, q.x, q.z) + 0.55;   // the same profile the deck was built on
            },
          });
        }
      }
    }
    for (const [nm, x, z, hh] of [['Lincoln Financial Field', -1920, 4932, 50], ['Citizens Bank Park', -1869, 4375, 58], ['Xfinity Mobile Arena (Wells Fargo Center)', -2327, 4880, 50]]) {
      const el = document.createElement('div'); el.className = 'lbl'; el.textContent = nm; labelsRoot.appendChild(el);
      labels.push({ el, pos: new V3(x, siteY(x, z, 'ground') + hh, z), visible: false, far: true });
    }
    // labels for the tallest named outer buildings
    if (typeof WIDE_NAMES !== 'undefined' && WIDE_NAMES) {
      for (const q of WIDE_NAMES.filter(w => w.h >= 140).slice(0, 16)) {
        const el = document.createElement('div');
        el.className = 'lbl';
        el.textContent = q.n;
        labelsRoot.appendChild(el);
        labels.push({ el, pos: new V3(q.x, siteY(q.x, q.z, 'ground') + q.h + 10, q.z), visible: false, far: true });
      }
    }
  });

  // ------------------------------------------------ the far ring: the rest of Philadelphia
  // ---- the two packed rings share one decoder: the far ring (city.b64, 0.7 m units,
  // facade attributes) and the towns across the city line (outskirts.b64, 1.0 m units,
  // no attributes). raiseRing() decodes buildings, roads and areas into staged chunks;
  // the far-ring step builds the terrain between the two; uploadRing() hands the rest to the GPU
  const RING_W = { x0: -12000, x1: 16500, z0: -21700, z1: 9700 };   // pack_city.py CITY: the far-ring box, the terrain's extent
  const WIDEB = { x0: -3700, x1: 2300, z0: -4480, z1: 6400 };
  // the NW hills patch (must match fetch_dem_nw.py) — everything inside gets
  // the 50 m terrain treatment; absent dem_nw.json, all of this stays off
  const P = DEMN ? { x0: -10600, x1: -2600, z0: -15600, z1: -6600 } : null;
  const inP = (x, z) => P && x > P.x0 && x < P.x1 && z > P.z0 && z < P.z1;
  const bboxOf = (poly) => {
    let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9;
    for (const q of poly) { if (q[0] < x0) x0 = q[0]; if (q[0] > x1) x1 = q[0]; if (q[1] < z0) z0 = q[1]; if (q[1] > z1) z1 = q[1]; }
    return [x0, x1, z0, z1];
  };
  const hitsP = (bb) => P && bb[0] < P.x1 && bb[1] > P.x0 && bb[2] < P.z1 && bb[3] > P.z0;
  // a park touching the Schuylkill's pool reach is draped finely so it dips into the channel
  const poolTouch = (poly) => { const bb = bboxOf(poly); return bb[1] > -4500 && bb[0] < -3500 && bb[3] > -6750 && bb[2] < -2250; };
  const withinP = (bb) => P && bb[0] > P.x0 && bb[1] < P.x1 && bb[2] > P.z0 && bb[3] < P.z1;
  async function raiseRing(bin, S, label, wideSeam) {
    const hdr = new Int32Array(bin.buffer, 0, 4);
    const hasAttr = hdr[0] === 0x5348545B || hdr[0] === 0x5348545C;
    const roofPacked = hdr[0] === 0x5348545C;   // the roof word carries form and rise
    if (hdr[0] !== 0x53485459 && !hasAttr) return null;
    const body = new Int16Array(bin.buffer, 16);
    let k = 0;
    const CH = 2400;
    // ground-contact shading, the wide ring's RING_AO mirrored for this closure: wall
    // quads carry this share of their colour at the two ground verts (1.0 disables)
    const RING_AO = 0.78;
    const chunks = new Map();
    const getChunk = (x, z) => {
      const key = Math.floor(x / CH) + ':' + Math.floor(z / CH);
      let ch = chunks.get(key);
      if (ch && ch.n > 60000) { addChunkMesh(ch.geometry(true), cityMat); ch = null; }   // seal: Uint16 indices, bounded staging
      if (!ch) { ch = new VBuf(2048); chunks.set(key, ch); }
      return ch;
    };
    const palLow = [0xa85e44, 0x9c5540, 0xb47454, 0x8a5040, 0xa25a40, 0xbfad92, 0xb0a38b, 0x969188, 0xc8b79a, 0xa87560, 0xc2b99d, 0x9cb0b3, 0xa3ae90, 0xc6ba86, 0xb98a72, 0xa4553e];
    const palCom = [0xaba397, 0x9c9587, 0xb7b0a0, 0x908d86, 0xa7aeb3, 0xc2bbb0];
    const palInd = [0x968a7c, 0x877e75, 0xa89e92, 0x9c6350];
    // the unresearched towers: limestone and precast lights, charcoal and bronze darks, blue-grey glass, brick
    const palTall = [0xa39b8b, 0x8e979e, 0x6e7681, 0x50555e, 0x5c5348, 0x8a8478, 0x9c9284, 0x42474f, 0x76664f, 0x66707c, 0x2f3338, 0xb8ad98, 0x5f7d99, 0xc2c2be, 0x6d4a3a, 0x3b4a5a];
    const c = new THREE.Color();
    const cCap = new THREE.Color();
    const v2 = [], v2pool = [];   // pooled contour points (2 M Vector2 allocations per ring otherwise)
    const pushV = (ch, x, y, z, nx, ny, nz, r, g, b, st, base, fh) => ch.push(x, y, z, nx, ny, nz, r, g, b, st, base, fh);
    const appendB = (ch, poly, y0, y1, color, st, base, fh, capColor, ao) => {
      const n = poly.length, r = color.r, g = color.g, b = color.b;
      const sign = signedArea(poly) > 0 ? 1 : -1;
      // ao: the generic fabric only; ground verts take RING_AO, eave verts and cap keep full colour
      const ra = ao ? RING_AO : 1, r0 = r * ra, g0 = g * ra, b0 = b * ra;
      for (let i = 0; i < n; i++) {
        const a = poly[i], q = poly[(i + 1) % n];
        const dx = q[0] - a[0], dz = q[1] - a[1];
        const L = Math.hypot(dx, dz);
        if (L < 0.05) continue;
        const nx = (dz / L) * sign, nz = (-dx / L) * sign;
        const i0 = pushV(ch, a[0], y0, a[1], nx, 0, nz, r0, g0, b0, st, base, fh);
        const i1 = pushV(ch, q[0], y0, q[1], nx, 0, nz, r0, g0, b0, st, base, fh);
        const i2 = pushV(ch, q[0], y1, q[1], nx, 0, nz, r, g, b, st, base, fh);
        const i3 = pushV(ch, a[0], y1, a[1], nx, 0, nz, r, g, b, st, base, fh);
        if (((-dz) * nx + dx * nz) >= 0) ch.idx.push(i0, i1, i2, i0, i2, i3); else ch.idx.push(i0, i2, i1, i0, i3, i2);
      }
      v2.length = 0;
      for (let i = 0; i < n; i++) { let p2 = v2pool[i]; if (!p2) p2 = v2pool[i] = new THREE.Vector2(); v2.push(p2.set(poly[i][0], -poly[i][1])); }
      let tris;
      try { tris = THREE.ShapeUtils.triangulateShape(v2, []); } catch (e) { return; }
      const capStart = ch.n;
      const cr = capColor ? capColor.r : r * 0.72, cg = capColor ? capColor.g : g * 0.72, cb = capColor ? capColor.b : b * 0.72;
      for (let i = 0; i < n; i++) pushV(ch, poly[i][0], y1, poly[i][1], 0, 1, 0, cr, cg, cb, 3, base);
      // earcut emits CCW triangles in the shape plane regardless of ring winding
      // (pack_city rings arrive in shapely's CW convention — flipping by ring
      // orientation culled every merged roof); always emit forward = up-facing
      for (const t of tris) ch.idx.push(capStart + t[0], capStart + t[1], capStart + t[2]);
    };
    // buildings (merged block strips + solo talls/churches)
    const nb = hdr[1];
    const wxWater = wxWaterGrid(body, k, nb, hdr[2], hdr[3], hasAttr, S, -12200, -21900, 28900, 31800, 30);
    for (let i = 0; i < nb; i++) {
      const n = body[k++], h = body[k++] / 5, mh = body[k++] / 5, t = body[k++];
      const attrW = hasAttr ? body[k++] : -1, roofW = hasAttr ? body[k++] : -1;
      const poly = new Array(n);
      for (let j = 0; j < n; j++) { poly[j] = [body[k++] * S, body[k++] * S]; }
      const [cx, cz] = polyCentroid(poly);
      if (ovpStraddle(poly, cx, cz)) { if ((i & 4095) === 4095) { loadmsg.textContent = label + ', ' + Math.round(i / nb * 100) + '%'; flushUploads(); await yieldNow(); } continue; }
      if (wxWater(cx, cz) || (demY(cx, cz) < TERRAIN.water + 0.5 && riverCorridor(cx, cz))) continue;   // nothing floats mid-river
      let base = siteY(cx, cz, 'ground');
      if (inP(cx, cz)) {
        // hillside blocks (Manayunk, Roxborough): a merged rowhouse strip on the
        // sharpened 50 m terrain settles to its LOWEST corner — a centroid base
        // leaves the downhill wall floating in air
        for (let j = 0; j < n; j++) { const b2 = siteY(poly[j][0], poly[j][1], 'ground'); if (b2 < base) base = b2; }
      }
      const hsh = hash01(i * 5.31 + 0.7);
      if (h >= 45) tallGlow.push({ x: cx, z: cz, b: base, h, poly });
      const fa = attrW >= 0 ? [attrW & 7, (attrW >> 3) & 7, (attrW >> 6) & 15, 0] : null;
      const fh = attrW >= 0 && ((attrW >> 10) & 31) > 0 ? 2.2 + (((attrW >> 10) & 31) - 1) * 0.1 : 0;
      let pool = h > 45 ? palTall : (t === 3 || t === 6 || h > 25) ? palCom : (t === 4 ? palInd : palLow);
      if (fa && h <= 45 && t <= 4) { const p2 = opaWallPool(fa); if (p2) pool = p2; }
      c.set(pool[Math.floor(hsh * pool.length) % pool.length]).multiplyScalar(h > 45 ? 0.94 + hash01(i * 13.7) * 0.12 : 0.9 + hash01(i * 13.7) * 0.2);
      let style;
      if (h > 30) style = h > 45 ? towerStyle(fa, t, i) : 2;
      else if (t === 5) style = 1;
      else if (t === 6) style = h > 16 ? 2 : 4;
      else if (t >= 7) style = 3;
      else style = fabricStyle(fa, h, t, Math.abs(signedArea(poly)), i, 0);
      const rb = roofBits(roofW, roofPacked);
      const capC = rb[0] >= 0 && ROOF_PAL && rb[0] < ROOF_PAL.length ? cCap.copy(ROOF_PAL[rb[0]]).multiplyScalar(0.9 + hsh * 0.18) : null;
      const rplan = mh > 0 ? null : roofPlan(poly, Math.abs(signedArea(poly)), h, t, rb[1], rb[2], i * 3.17 + 0.5);
      if (rplan) raisePitched(getChunk(cx, cz), poly, base, h, rplan, c, style, fh, capC, (ch2, p2, y0, y1, col, st2, b2, holes, fh2, cap2, ao2) => appendB(ch2, p2, y0, y1, col, st2, b2, fh2, cap2, ao2));
      else {
        appendB(getChunk(cx, cz), poly, mh > 0 ? base + mh : base - 1.0, base + h, c, style, base, fh, capC, mh === 0);
        if (!mh && h < 60) roofClutter((pg, y0, y1, hex, st2, holes) => { if (holes) return; cCap.set(hex); appendB(getChunk(cx, cz), pg, y0, y1, cCap, st2, base); }, poly, base, h, Math.abs(signedArea(poly)), t, fa, i, c, true);
      }
      if (t === 5 && Math.abs(signedArea(poly)) > 350 && h < 60) {
        const chk = getChunk(cx, cz);
        const tw = 5.5, towerTop = base + h + 9, apex = base + h + 24;
        const sq = [[cx - tw / 2, cz - tw / 2], [cx + tw / 2, cz - tw / 2], [cx + tw / 2, cz + tw / 2], [cx - tw / 2, cz + tw / 2]];
        appendB(chk, sq, base, towerTop, c, 3, base);
        const i0 = chk.n;
        for (const q of sq) pushV(chk, q[0], towerTop, q[1], 0, 0.7, 0, c.r * 0.9, c.g * 0.9, c.b * 0.9, 3, base);
        pushV(chk, cx, apex, cz, 0, 1, 0, c.r * 0.9, c.g * 0.9, c.b * 0.9, 3, base);
        // outward: (base, apex, next) with the ring CCW in (x, z), the sense the wall loop uses
        chk.idx.push(i0, i0 + 4, i0 + 1, i0 + 1, i0 + 4, i0 + 2, i0 + 2, i0 + 4, i0 + 3, i0 + 3, i0 + 4, i0);
      }
      if ((i & 4095) === 4095) { loadmsg.textContent = label + ', ' + Math.round(i / nb * 100) + '%'; flushUploads(); await yieldNow(); }
    }
    // far roads — same continuity treatment as the wide set: endpoint-snapped heights,
    // bend fans, bridge decks over the river corridors
    // the far ring skips aLane on phones (its lines are under a pixel at phone distances,
    // and the attribute is 16 B a vertex); the shader's guard makes the missing attribute safe
    const rc = { pos: [], col: [], idx: [], n: 0, lane: isTouch ? null : new Float32Array(1 << 21), label };
    const roadCol = [0x3b3833, 0x3b3833, 0x3f3c37, 0x3f3c37, 0x43403b, 0x45423d, 0x7c584a];
    const rcLane = (v, u, s, hw, cls) => {   // see the wide tier's rcLane
      if (!rc.lane) return;
      if (v * 4 + 4 > rc.lane.length) { const b = new Float32Array(rc.lane.length * 2); b.set(rc.lane); rc.lane = b; }
      rc.lane[v * 4] = u; rc.lane[v * 4 + 1] = s; rc.lane[v * 4 + 2] = hw; rc.lane[v * 4 + 3] = cls;
    };
    // pack_wide carries roads 200 m past its box (runs_of(..., 200)); a 30 m
    // margin here left a 170 m band where both tiers paved the same streets
    const inWide = (p) => p[0] > WIDEB.x0 - 200 && p[0] < WIDEB.x1 + 200 && p[1] > WIDEB.z0 - 200 && p[1] < WIDEB.z1 + 200;
    const yMapF = new Map();
    const ySnapF = (x, z, y) => {
      const key = Math.round(x * 2) + ':' + Math.round(z * 2);
      const v = yMapF.get(key);
      if (v !== undefined) return v;
      yMapF.set(key, y);
      return y;
    };
    const rcFanF = (x, y, z, hw, cr, cg, cb, sA, ddx, ddz, cls) => {   // 2 cm below its strip, like the wide rcFan
      const c0 = rc.n;
      y -= 0.02;
      rc.pos.push(x, y, z); rc.col.push(cr, cg, cb); rcLane(rc.n, 0, sA, hw, cls); rc.n++;
      for (let s6 = 0; s6 < 7; s6++) {
        const ang = s6 / 6 * Math.PI * 2;
        const ox = Math.cos(ang) * hw, oz = Math.sin(ang) * hw;
        rc.pos.push(x + ox, y, z + oz);
        rc.col.push(cr, cg, cb); rcLane(rc.n, -ox * ddz + oz * ddx, sA + ox * ddx + oz * ddz, hw, cls); rc.n++;
      }
      for (let s6 = 0; s6 < 6; s6++) rc.idx.push(c0, c0 + 1 + s6, c0 + 2 + s6);
    };
    // the roads are DECODED here and PAVED at upload (uploadRing calls paveRoads once the far
    // strips and the NW patch are in the ground registry), so their heights read the drawn
    // ground like the sheets do (groundMeshLandY); paved here they read the DEM, and a park
    // conformed to the 100 m mesh cut through the street over it wherever the hill's mesh sat
    // above the DEM's bilinear read (Roxborough, Manayunk, the Wissahickon slopes)
    const roadRecs = [];
    for (let i = 0; i < hdr[2]; i++) {
      const n = body[k++], w = body[k++] / 10, t = body[k++];
      const pts = new Array(n);
      for (let j = 0; j < n; j++) pts[j] = [body[k++] * S, body[k++] * S];
      if (t <= 5) for (let j = 0; j + 1 < pts.length; j++) septaRoadAdd(pts[j][0], pts[j][1], pts[j + 1][0], pts[j + 1][1]);
      roadRecs.push({ pts: densify(pts, 30), w, t, i });
    }
    const paveRoads = async () => {
      for (let ri = 0; ri < roadRecs.length; ri++) {
      const { pts, w, t, i } = roadRecs[ri];
      c.set(roadCol[t] || 0x3b3833);
      const hw = w / 2;
      const cls = t <= 1 ? 1 : (t === 6 || w < 5.5 || (t === 5 && w > 10)) ? 2 : 0;   // lane class: divided, two-way, or unmarked; runways (45 m) and taxiways (16 m) ride class 5
      const thr = TERRAIN.water + 0.6;
      let sAcc = 0;   // distance along the densified polyline (the lane paint's s)
      for (let j = 0; j < pts.length - 1; j++) {
        const a = pts[j], q = pts[j + 1];
        let dx = q[0] - a[0], dz = q[1] - a[1];
        const L = Math.hypot(dx, dz); if (L < 0.01) continue;
        const sA = sAcc; sAcc += L;
        dx /= L; dz /= L;
        const mx = (a[0] + q[0]) / 2, mz = (a[1] + q[1]) / 2;
        const aLow = demY(a[0], a[1]) < thr, qLow = demY(q[0], q[1]) < thr;
        let deck = 0;
        if ((aLow || qLow) && riverCorridor(mx, mz)) {
          if (t > 2) { if (aLow && qLow) continue; }
          else deck = t === 0 ? 20 : 13;
        }
        if (deck && wwbNear(mx, mz)) continue;         // the custom WWB deck owns its crossing
        if (t <= 1 && wwbUnder(mx, mz)) continue;      // and its Jersey viaduct: no flat twin beneath
        if (wideSeam && inWide(a) && inWide(q)) continue;   // the wide set paves there (the far ring only: the outskirts packer already cedes the wide box, and the wide data ends at lat 39.890 while this margin runs to z 6600)
        if (ovpOwned(a[0], a[1], q[0], q[1])) continue; // a baked overpass deck owns it
        const px = -dz * hw, pz = dx * hw;
        const jr = LAYER.road + (6 - Math.min(t, 6)) * 0.055 + hash01(i * 2.9 + 0.4) * 0.1;
        let ya0 = groundMeshLandY(a[0], a[1]) ?? siteY(a[0], a[1], 'road'), yb0 = groundMeshLandY(q[0], q[1]) ?? siteY(q[0], q[1], 'road');
        if (deck) {
          ya0 = Math.max(ya0, TERRAIN.water + (aLow ? deck : deck * 0.35));
          yb0 = Math.max(yb0, TERRAIN.water + (qLow ? deck : deck * 0.35));
        }
        const ya = ySnapF(a[0], a[1], ya0 + jr), yb = ySnapF(q[0], q[1], yb0 + jr);
        const b0 = rc.n;
        rc.pos.push(a[0] + px, ya, a[1] + pz, q[0] + px, yb, q[1] + pz, q[0] - px, yb, q[1] - pz, a[0] - px, ya, a[1] - pz);
        for (let m = 0; m < 4; m++) rc.col.push(c.r * 255, c.g * 255, c.b * 255);
        rcLane(b0, hw, sA, hw, cls); rcLane(b0 + 1, hw, sAcc, hw, cls); rcLane(b0 + 2, -hw, sAcc, hw, cls); rcLane(b0 + 3, -hw, sA, hw, cls);
        rc.n += 4;
        rc.idx.push(b0, b0 + 1, b0 + 2, b0, b0 + 2, b0 + 3);
        if (j > 0) {
          const p0 = pts[j - 1];
          let ux0 = a[0] - p0[0], uz0 = a[1] - p0[1];
          const L0 = Math.hypot(ux0, uz0) || 1;
          ux0 /= L0; uz0 /= L0;
          if (ux0 * dx + uz0 * dz < 0.99) {
            let ddx = ux0 + dx, ddz = uz0 + dz;
            const dl = Math.hypot(ddx, ddz) || 1;
            rcFanF(a[0], ya, a[1], hw, c.r * 255, c.g * 255, c.b * 255, sA, ddx / dl, ddz / dl, cls);
          }
        }
      }
      if ((ri & 2047) === 2047) await yieldNow();
      }
      roadRecs.length = 0;
    };
    // far areas (water splits out onto the animated river material). The parks and the
    // aprons are only COLLECTED here: they conform to the far ground (conformDrape), and the
    // far strips are built after this pass, so uploadRing builds them (ringAreaParts)
    const areaPolys = [], waterAreaParts = [];
    const nwParks = [], nwWaters = [];   // patch-intersecting polys steer the 50 m ground
    for (let i = 0; i < hdr[3]; i++) {
      const n = body[k++], kind = body[k++];
      const poly = new Array(n);
      for (let j = 0; j < n; j++) poly[j] = [body[k++] * S, body[k++] * S];
      if (kind !== 1) {
        const [acx, acz] = polyCentroid(poly);
        if (wwbNear(acx, acz)) continue;               // the WWB deck owns its crossing
      }
      try {
        if (kind === 0) {
          GRASS_POLYS.push(poly);
          const big = Math.abs(signedArea(poly)) > 40000;
          if (P) {
            const bb = bboxOf(poly);
            if (hitsP(bb)) {
              nwParks.push(poly);
              // inside the patch the tinted ground IS the park: a big one adds nothing
              // over the woodland tint but a second sheet across the sharpened gorge
              if (big && withinP(bb)) continue;
            }
          }
          areaPolys.push({ poly, kind, i });
        } else if (kind === 1) { noSow(poly); const wcc = polyCentroid(poly); if (!(schRaster && schRaster(wcc[0], wcc[1]))) waterAreaParts.push({ geom: flatShorePoly(poly, null, TERRAIN.water + 0.55, Math.abs(signedArea(poly)) > 20000 ? 2 : 1), color: new THREE.Color(COLORS.water), style: 3 }); }
        else { noSow(poly); areaPolys.push({ poly, kind, i }); }
      } catch (e) { /* degenerate */ }
    }
    return { chunks, rc, paveRoads, areaPolys, waterAreaParts, nwParks, nwWaters, label };
  }
  // the far ring's parks (kind 0) and aprons (kind 2) as sheets on the drawn far ground: built
  // at upload, when the far strips and the NW patch exist in the ground registry (the far step
  // builds them between raiseRing and uploadRing; the outskirts inherit them). A park over
  // 1,000 m2 conforms (conformDrape), smaller ones stay flat on their perimeter; the nested
  // rings rise by area like the wide tier's so nothing sits coplanar (gotcha 6). The Schuylkill
  // pool reach keeps its finer spacing, now only in conformDrape's drapedPoly fallback
  const RING_PARK_CONFORM_AREA = 1000, RING_APRON_CONFORM_AREA = 1000;
  function ringAreaParts(R) {
    const areaParts = [];
    for (const { poly, kind, i } of R.areaPolys) {
      const pa = Math.abs(signedArea(poly));
      try {
        if (kind === 0) areaParts.push({ geom: pa > RING_PARK_CONFORM_AREA ? conformDrape(poly, LAYER.park + 0.03 * (1 - Math.min(1, pa / 20000)), poolTouch(poly) ? 30 : 60) : flatPoly(poly, null, LAYER.park), color: new THREE.Color(COLORS.park).multiplyScalar(lerp(1 - PARK_SHADE_SPREAD, 1 + PARK_SHADE_SPREAD, hash01(i))), style: 3 });
        else areaParts.push({ geom: pa > RING_APRON_CONFORM_AREA ? conformDrape(poly, LAYER.plaza, 60) : flatPoly(poly, null, LAYER.plaza), color: new THREE.Color(0x9a978e), style: 3 });
      } catch (e) { /* degenerate */ }
    }
    drapeLog(R.label || 'the far ring');
    return areaParts;
  }
  async function uploadRing(R) {
    const { chunks, rc, waterAreaParts } = R;
    await yieldNow();
    for (const ch of chunks.values()) addChunkMesh(ch.geometry(true), cityMat);
    flushUploads(true);
    await yieldNow();
    if (R.paveRoads) await R.paveRoads();   // the streets read the drawn far ground, registered by now
    if (rc.n) {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(rc.pos), 3));
      g.setAttribute('color', new THREE.BufferAttribute(new Uint8Array(rc.col), 3, true));
      if (rc.lane) g.setAttribute('aLane', new THREE.BufferAttribute(rc.lane.subarray(0, rc.n * 4), 4));
      g.setIndex(rc.idx);
      g.computeVertexNormals();
      g.computeBoundingSphere();
      freeOnUpload(g);
      if (/[?&]dev\b/.test(location.search)) console.info('roads: ' + rc.label + ' rc.n = ' + rc.n + (rc.lane ? ' with aLane' : ' without aLane'));
      rc.pos = rc.col = rc.idx = rc.lane = null;
      groupCity.add(new THREE.Mesh(g, roadMat({ vertexColors: true, roughness: 0.95, side: THREE.DoubleSide })));
    }
    const areaParts = ringAreaParts(R);
    if (areaParts.length) { const g = mergeColored(areaParts); freeOnUpload(g); groupCity.add(new THREE.Mesh(g, surfMat({ vertexColors: true, roughness: 0.95 }))); }
    if (waterAreaParts.length) { const g = mergeWater(waterAreaParts); freeOnUpload(g); groupCity.add(new THREE.Mesh(g, riverMat)); }
  }
  step('Raising the rest of Philadelphia', async () => {
    if (typeof CITY_B64 === 'undefined' || !CITY_B64) return;
    const bin = unb64(CITY_B64, 'CITY');
    CITY_B64 = null;   // 7 MB of base64 freed
    const R = await raiseRing(bin, 0.7, 'Raising the rest of Philadelphia', true);
    if (!R) return;
    const { nwParks, nwWaters, waterAreaParts } = R;
    const W = RING_W;
    // far ground: 100 m strips around the wide box, down to the riverbed over
    // water. With dem_nw present the NW hills get their own 50 m heightfield —
    // its footprint is cut from the north strip along that strip's own grid
    // lines, so the two meshes butt exactly (T-junction verts only, no overlap)
    const farGroundMat = groundSurfMat();
    let nwGroundMat = null, nwParkAt = null, nwWaterAt = null;
    if (P) {
      nwGroundMat = groundSurfMat({ vertexColors: true });   // woodland tint rides vertex color as a ratio against the shared meadow
      // official PPR parkland boundaries (nw_parks.json): the central Wissahickon
      // has no park polygon in the OSM extract (a nature_reserve relation the
      // city fetch never pulled), so the woodland tint reads the City's own lines
      if (typeof NW_PARKS !== 'undefined' && NW_PARKS && NW_PARKS.polys) {
        for (const fl2 of NW_PARKS.polys) {
          const pp = new Array(fl2.length >> 1);
          for (let q = 0; q < pp.length; q++) pp[q] = [fl2[q * 2], fl2[q * 2 + 1]];
          nwParks.push(pp);
        }
      }
      // full-fidelity water rings (nw_water.json), draped on the NED water
      // surface — the creek descends its real stepped profile. The packed
      // 90-vert rings zigzag when draped, so those stay flat (and end up
      // buried under the sharpened terrain inside the patch); these replace
      // them here. siteY clamps any below-plane dip back to the tidal level.
      if (typeof NW_WATER !== 'undefined' && NW_WATER && NW_WATER.polys) {
        for (const fl2 of NW_WATER.polys) {
          const pp = new Array(fl2.length >> 1);
          for (let q = 0; q < pp.length; q++) pp[q] = [fl2[q * 2], fl2[q * 2 + 1]];
          nwWaters.push(pp); noSow(pp);
          try { waterAreaParts.push({ geom: drapedPoly(pp, 0.75, 30), color: new THREE.Color(COLORS.water), style: 3 }); } catch (e) { /* degenerate */ }
        }
      }
      const GCELL = 250;
      const mkPolyGrid = (polys) => {
        const grid = new Map();
        for (let pi = 0; pi < polys.length; pi++) {
          const bb = bboxOf(polys[pi]);
          for (let gx = Math.floor(bb[0] / GCELL); gx <= Math.floor(bb[1] / GCELL); gx++)
            for (let gz = Math.floor(bb[2] / GCELL); gz <= Math.floor(bb[3] / GCELL); gz++) {
              const k2 = gx + ':' + gz;
              let a = grid.get(k2);
              if (!a) { a = []; grid.set(k2, a); }
              a.push(pi);
            }
        }
        return (x, z) => {
          const a = grid.get(Math.floor(x / GCELL) + ':' + Math.floor(z / GCELL));
          if (a) for (const pi of a) if (pointInPoly(x, z, polys[pi])) return true;
          return false;
        };
      };
      nwParkAt = mkPolyGrid(nwParks);
      nwWaterAt = mkPolyGrid(nwWaters);
    }
    const pkC2 = new THREE.Color(WOODLAND), gdC2 = new THREE.Color(COLORS.ground);
    const nwR = [pkC2.r / gdC2.r, pkC2.g / gdC2.g, pkC2.b / gdC2.b];
    const mkFarGround = (x0, x1, z0, z1, cell, hole, tint) => {
      const nx = Math.max(1, Math.round((x1 - x0) / cell)), nz = Math.max(1, Math.round((z1 - z0) / cell));
      const pos = [];
      for (let j = 0; j <= nz; j++) for (let i = 0; i <= nx; i++) {
        const x = x0 + (x1 - x0) * i / nx, z = z0 + (z1 - z0) * j / nz;
        const y = demY(x, z);
        let yy = (y < TERRAIN.water + 0.6 ? (eastOfDelaware(x, z) ? TERRAIN.bed : TERRAIN.water + 0.45) : y) - 0.07;
        yy = riverCarve(x, z, yy);   // the Schuylkill's channel
        if (tint && nwWaterAt(x, z)) yy -= 3.0;   // bed under the draped creek/canal/river
        pos.push(x, yy, z);
      }
      let col = null;
      if (tint) {
        // park membership blurred once so the woodland green feathers over a
        // cell instead of stair-stepping at the 50 m grid
        const t0 = new Float32Array((nx + 1) * (nz + 1));
        for (let j = 0; j <= nz; j++) for (let i = 0; i <= nx; i++)
          t0[j * (nx + 1) + i] = nwParkAt(x0 + (x1 - x0) * i / nx, z0 + (z1 - z0) * j / nz) ? 1 : 0;
        col = new Float32Array(3 * (nx + 1) * (nz + 1));
        for (let j = 0; j <= nz; j++) for (let i = 0; i <= nx; i++) {
          let s = 0, m = 0;
          for (let dj = -1; dj <= 1; dj++) for (let di = -1; di <= 1; di++) {
            const ii = i + di, jj = j + dj;
            if (ii < 0 || jj < 0 || ii > nx || jj > nz) continue;
            s += t0[jj * (nx + 1) + ii]; m++;
          }
          const t = s / m;
          const o = (j * (nx + 1) + i) * 3;
          col[o] = 1 + (nwR[0] - 1) * t; col[o + 1] = 1 + (nwR[1] - 1) * t; col[o + 2] = 1 + (nwR[2] - 1) * t;
        }
      }
      const xi = (i) => x0 + (x1 - x0) * i / nx, zj = (j) => z0 + (z1 - z0) * j / nz;
      const idx = [];
      const skip = hole ? new Uint8Array(nx * nz) : null;   // the hole's cells, for the ground registry
      for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
        if (hole && xi(i) >= hole.x0 - 0.01 && xi(i + 1) <= hole.x1 + 0.01 && zj(j) >= hole.z0 - 0.01 && zj(j + 1) <= hole.z1 + 0.01) { skip[j * nx + i] = 1; continue; }
        const a = j * (nx + 1) + i, b = a + 1, d = a + nx + 1, e = d + 1;
        idx.push(a, d, b, b, d, e);
      }
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
      if (col) g.setAttribute('color', new THREE.BufferAttribute(col, 3));
      g.setIndex(idx);
      g.computeVertexNormals();
      // the drawn surface, for conformDrape and the tufts; the NW patch registers after the
      // strip whose hole it fills, so it is searched first there
      registerGround(g, x0, x1, z0, z1, nx, nz, hole, skip, cell);
      const m = new THREE.Mesh(g, tint ? nwGroundMat : farGroundMat);
      m.matrixAutoUpdate = false;
      groupCity.add(m);
    };
    // patch hole snapped to the north strip's grid (the strip containing it)
    let nwHole = null;
    if (P) {
      const sx0 = W.x0, sx1 = W.x1, sz0 = W.z0, sz1 = WIDEB.z0;
      const nxN = Math.max(1, Math.round((sx1 - sx0) / 100)), nzN = Math.max(1, Math.round((sz1 - sz0) / 100));
      const cw = (sx1 - sx0) / nxN, chz = (sz1 - sz0) / nzN;
      const i0 = Math.ceil((P.x0 - sx0) / cw), i1 = Math.floor((P.x1 - sx0) / cw);
      const j0 = Math.ceil((P.z0 - sz0) / chz), j1 = Math.floor((P.z1 - sz0) / chz);
      if (i1 - i0 > 1 && j1 - j0 > 1) nwHole = { x0: sx0 + i0 * cw, x1: sx0 + i1 * cw, z0: sz0 + j0 * chz, z1: sz0 + j1 * chz };
    }
    for (const [x0, x1, z0, z1] of [
      [W.x0, W.x1, W.z0, WIDEB.z0], [W.x0, W.x1, WIDEB.z1, W.z1],
      [W.x0, WIDEB.x0, WIDEB.z0, WIDEB.z1], [WIDEB.x1, W.x1, WIDEB.z0, WIDEB.z1],
    ]) mkFarGround(x0, x1, z0, z1, 100, nwHole, false);
    if (nwHole) mkFarGround(nwHole.x0, nwHole.x1, nwHole.z0, nwHole.z1, 50, null, true);
    // the apron: dark ground from the world's edge out to 60 km, well under the
    // river beds so nothing fights it. From altitude the city used to end in a
    // hard diagonal against the sky dome's below-horizon band; now it ends in
    // fog, the way ground does. Same material as the far strips, so the day and
    // night retint, the mottle and the weather pass all apply.
    {
      const APRON = 60000, ax = (W.x0 + W.x1) / 2, az = (W.z0 + W.z1) / 2;
      const ag = new THREE.PlaneGeometry(APRON * 2, APRON * 2);
      ag.rotateX(-Math.PI / 2);
      const apron = new THREE.Mesh(ag, farGroundMat);
      apron.position.set(ax, TERRAIN.bed - 8, az);
      apron.frustumCulled = false;
      apron.renderOrder = -1;   // drawn first: it is behind everything and never coplanar with anything
      groupCity.add(apron);
    }
    // the Schuylkill's pool between the outer districts' box and the NW hills patch: the
    // river is an OSM multipolygon whose member ways carry no tags, so no packed tier holds
    // a ring for it, and the outer districts show it only because their water plane lies
    // under the carved channel. A flat sheet at the same level under this reach does the
    // same here; the banks hide all of it but the channel
    if (SCH_POLYS) {
      // the Schuylkill from the Fairmount dam to East Falls (bake_schuylkill.py): OSM maps this
      // reach as a riverbank multipolygon neither packed tier carries, and the far ring's polygon
      // stops at the wide box, so the river through the park was a carved, dry channel. The baked
      // sheet is the real course buffered to the bank, islands as holes, a hand below the area
      // sheets so a tier's own polygon draws over it without a fight
      for (const w of SCH_POLYS) { try { R.waterAreaParts.push({ geom: flatShorePoly(w.ring, w.holes && w.holes.length ? w.holes : null, TERRAIN.water + 0.5, 2), color: new THREE.Color(COLORS.water), style: 3 }); } catch (e) { /* a degenerate ring */ } }
    }
    loadmsg.textContent = 'Raising the rest of Philadelphia, uploading';
    await uploadRing(R);
    // the world is now the whole city
    bounds.minX = -12200; bounds.maxX = 16700; bounds.minZ = -21900; bounds.maxZ = 9900;
    // clear air is clear (Mike): the haze starts 8 km out and closes at 40 km, past the world's
    // edge, so the whole city stands in a clear sky from any height unless the weather says fog,
    // rain or snow (those still shrink it) or it is night (the far windows still need the short air)
    fogBase.near = 8000; fogBase.far = 40000;
    // the baked neighborhood layer owns these names when present; the airport
    // keeps its HTML label (a place, not a neighborhood)
    const hasNb = typeof PLACES !== 'undefined' && PLACES && PLACES.nb;
    for (const [nm, lx, lz, lh] of [
      ['Philadelphia International Airport', -8334, 7857, 40],
      ...(hasNb ? [] : [
        ['University City', -4300, -600, 90],
        ['Manayunk', -6803, -8950, 60],
        ['Germantown', -4900, -8500, 60],
        ['Frankford', 5561, -7845, 60],
        ['Northeast Philadelphia', 11499, -15760, 60],
      ]),
    ]) {
      const el = document.createElement('div');
      el.className = 'lbl';
      el.textContent = nm;
      labelsRoot.appendChild(el);
      labels.push({ el, pos: new V3(lx, siteY(lx, lz, 'ground') + lh, lz), visible: false, far: true });
    }
    // citywide landmark labels (Round 44): every quarter of the city carries its
    // anchors — lat/lon through the SEPTA frame, height hand-set per landmark.
    // (Core towers keep their WIDE_NAMES tags; the stadium trio, PHL and the
    // bridges are labeled where they are built.)
    for (const [nm, la, lo, lh] of [
      ['Independence Hall', 39.94883, -75.15003, 46],
      ['Philadelphia City Hall', 39.95258, -75.16352, 172],
      ['Reading Terminal Market', 39.95331, -75.15908, 28],
      ["Elfreth's Alley", 39.95296, -75.14243, 22],
      ['Christ Church', 39.95012, -75.14335, 62],
      ['National Constitution Center', 39.95307, -75.14893, 26],
      ['Philadelphia Museum of Art', 39.96562, -75.18101, 42],
      ['Eastern State Penitentiary', 39.96833, -75.17265, 32],
      ['The Franklin Institute', 39.95815, -75.17284, 32],
      ['Boathouse Row', 39.96895, -75.18754, 18],
      ['The Met Philadelphia', 39.96851, -75.15852, 32],
      ['Divine Lorraine Hotel', 39.96993, -75.15977, 42],
      ['Girard College', 39.97316, -75.16659, 32],
      ['Penn Treaty Park', 39.9657, -75.1293, 18],
      ['Frankford Arsenal', 40.01464, -75.0684, 28],
      ['30th Street Station', 39.95562, -75.1819, 42],
      ['University of Pennsylvania', 39.95219, -75.1979, 50],
      ['Drexel University', 39.95664, -75.18987, 46],
      ['Penn Museum', 39.94915, -75.19107, 24],
      ['Philadelphia Zoo', 39.97151, -75.19555, 26],
      ['Please Touch Museum', 39.9796, -75.20991, 30],
      ['The Mann Center', 39.97847, -75.2215, 26],
      ["Saint Joseph's University", 39.99506, -75.2394, 36],
      ["Bartram's Garden", 39.93269, -75.21285, 20],
      ['Navy Yard', 39.88938, -75.17771, 36],
      ['FDR Park', 39.90424, -75.18293, 20],
      ['Italian Market', 39.93933, -75.15843, 22],
      ['Fort Mifflin', 39.87487, -75.21287, 18],
      ['Temple University', 39.98072, -75.15551, 50],
      ['Laurel Hill Cemetery', 39.99801, -75.18709, 22],
      ['La Salle University', 40.03771, -75.15521, 36],
      ['Einstein Medical Center', 40.0368, -75.1415, 40],
      ['Cliveden', 40.05147, -75.17851, 22],
      ['Valley Green Inn', 40.05285, -75.21669, 18],
      ['Morris Arboretum', 40.08858, -75.22252, 22],
      ['Chestnut Hill College', 40.06345, -75.21868, 30],
      ['Fox Chase Cancer Center', 40.07162, -75.09, 34],
      ['Northeast Philadelphia Airport', 40.0819, -75.01062, 30],
      ['Pennypack Park', 40.06427, -75.0561, 20],
      ['Adventure Aquarium', 39.9448, -75.1312, 22],
      ['Freedom Mortgage Pavilion', 39.93446, -75.1292, 26],
      ['USS New Jersey (BB-62)', 39.93951, -75.13309, 38],
      ['Benjamin Franklin Bridge', 39.95299, -75.13444, 58],
    ]) {
      const lx = (lo - SEPTA_GEO.lon0) * SEPTA_GEO.mx, lz = -(la - SEPTA_GEO.lat0) * SEPTA_GEO.mz;
      const el = document.createElement('div');
      el.className = 'lbl';
      el.textContent = nm;
      labelsRoot.appendChild(el);
      labels.push({ el, pos: new V3(lx, siteY(lx, lz, 'ground') + lh, lz), visible: false, far: true });
    }
  });

  step('Raising the towns across the line', async () => {
    // Gloucester City, Camden's south wards, Pennsauken, Cheltenham, Springfield and the
    // Navy Yard's south half: the strips of the far-ring box the older fetches never
    // covered (pack_outskirts.py). Scenery beyond the flight limit, so the world no
    // longer ends at the river or the county line
    if (typeof OUTSKIRTS_B64 === 'undefined' || !OUTSKIRTS_B64) return;
    const bin = unb64(OUTSKIRTS_B64, 'OUTSKIRTS');
    OUTSKIRTS_B64 = null;
    const R = await raiseRing(bin, 1.0, 'Raising the towns across the line', false);
    if (!R) return;
    loadmsg.textContent = 'Raising the towns across the line, uploading';
    await uploadRing(R);
  });
  // ---- the paved ground (Round 52 coda 2). Since Round 52 every unbuilt surface is the
  // meadow, and the port terminals, the rail yards, the big-box and industrial lots and every
  // surface parking lot in the city were green where life has asphalt, concrete or ballast.
  // These are OSM's surface lots, the industrial, port, commercial and retail yards, the rail
  // yards and the airport aprons (fetch_paved.py, pack_paved.py into PAVED_B64), each laid on
  // the drawn ground the way the sports complex's lots are. The blob is little-endian int16:
  // [magic 0x5056 'PV', version 1, nPolys low word, nPolys high word], then per ring n, kind,
  // x0, z0 .. xn-1, zn-1 in whole metres of the model frame, closed implicitly, CCW in (x, z);
  // kinds 1 lot, 2 yard, 3 rail yard, 4 apron. Absent the blob the step is a no-op (a build
  // with --allow-missing) and the meadow stays.
  // The tunables, in one place. Stored-dark colours (the legacy pipeline lifts a stored value,
  // gotcha 11, so pick these by rendered swatch): the lots are the sports lots' asphalt
  // (LOT_COL, about 114 displayed against the streets' 200), the yards a touch lighter and
  // greyer (asphalt and concrete mixed), the rail yards a warm ballast grey, the aprons
  // concrete. The lifts are metres above the drawn ground mesh, under every park (LAYER.park
  // 0.06 and up, so a park inside a yard still shows), under the sports complex's sheets
  // (LAYER.plaza + 0.02) and the streets (LAYER.road plus the class lifts); the lots ride
  // 5 mm over the yards so a lot inside a yard draws above it (pack_paved.py unions each kind,
  // so nothing of one kind is ever coplanar with itself, and both kinds conform to the same
  // ground triangles, so the gap is exact everywhere, gotcha 17)
  const PAVED_COL = { 1: 0x0e0d0c, 2: 0x151412, 3: 0x1b1916, 4: 0x1c1c1a };
  const PAVED_UP = { 1: 0.05, 2: 0.045, 3: 0.045, 4: 0.045 };
  const PAVED_KIND = { 1: 'lots', 2: 'yards', 3: 'rail yards', 4: 'aprons' };
  step('Paving the lots and yards', () => {
    if (typeof PAVED_B64 === 'undefined' || !PAVED_B64) return;
    let v;
    try {
      const u8 = unb64(PAVED_B64, 'PAVED');
      PAVED_B64 = null;   // free the base64 source
      v = new Int16Array(u8.buffer, u8.byteOffset, u8.byteLength >> 1);
    } catch (err) { console.error('paved ground decode failed', err); return; }
    if (v.length < 4 || v[0] !== 0x5056 || v[1] !== 1) { console.error('paved ground: bad magic or version', v[0], v[1]); return; }
    const nPolys = (v[2] & 0xffff) | ((v[3] & 0xffff) << 16);   // the words are unsigned; int16 reads a count past 32767 negative
    const cols = {};
    for (const k in PAVED_COL) cols[k] = new THREE.Color(PAVED_COL[k]);   // mergeColored copies the colour per vertex, one object per kind is enough
    const parts = [], counts = { 1: 0, 2: 0, 3: 0, 4: 0 };
    let p = 4, skipped = 0, unknown = 0;
    for (let i = 0; i < nPolys; i++) {
      if (p + 2 > v.length) { console.error('paved ground: ring ' + i + ' of ' + nPolys + ' runs past the end of the blob'); break; }
      const n = v[p], kind = v[p + 1];
      p += 2;
      if (n < 3 || p + n * 2 > v.length) { console.error('paved ground: ring ' + i + ' has ' + n + ' vertices, past the end of the blob'); break; }
      const poly = new Array(n);
      for (let q = 0; q < n; q++) poly[q] = [v[p + q * 2], v[p + q * 2 + 1]];
      p += n * 2;
      if (PAVED_UP[kind] === undefined) { unknown++; continue; }   // a kind this build does not draw
      let geom;
      try { geom = conformDrape(poly, PAVED_UP[kind], 20); } catch (e) { skipped++; continue; }   // a degenerate ring
      parts.push({ geom, color: cols[kind], style: 3 });
      noSow(poly);   // the tuft field keeps off asphalt
      counts[kind]++;
    }
    if (parts.length) {
      const g = mergeColored(parts);
      freeOnUpload(g);
      const m = new THREE.Mesh(g, surfMat({ vertexColors: true, roughness: 0.95 }));
      m.receiveShadow = true;
      groupCity.add(m);
    }
    PERF.paved = counts;   // read through ?dev's __dbg.PERF.paved
    drapeLog('the lots and yards');
    if (/[?&]dev\b/.test(location.search)) console.info('paved ground: ' + Object.keys(counts).map(k => counts[k] + ' ' + PAVED_KIND[k]).join(', ') + ' of ' + nPolys + ' rings' + (skipped ? ', ' + skipped + ' degenerate' : '') + (unknown ? ', ' + unknown + ' of an unknown kind' : ''));
  });
  step('Dressing the storefronts', () => {
    // Tier 2 of the facade plan: OSM's shops, cafes, bars, banks and the rest, each on the
    // facade edge of its building that faces the street (bake_storefronts.py). A glazed
    // front proud of the wall (full height, or the lower half for banks, clinics and
    // theatres), an awning in the trade's colour where a shop would hang one, a signboard
    // above it; the glass and the sign glow after dark. 8 int16 per storefront: x/0.2, z/0.2,
    // outward-normal angle*1000, width*10, kind, colour, floor height*10, flags
    if (typeof STOREFRONTS_B64 === 'undefined' || !STOREFRONTS_B64) return;
    const bin = unb64(STOREFRONTS_B64, 'STOREFRONTS');
    STOREFRONTS_B64 = null;
    const hdr = new Int32Array(bin.buffer, 0, 4);
    if (hdr[0] !== 0x53485446) return;
    const body = new Int16Array(bin.buffer, 16), n = hdr[1];
    const AWNING = [0x5a1a14, 0x14331e, 0x142a4a, 0x3a3a3a, 0x6b5a2e, 0x4a1f3a, 0x1e4a4a, 0x5a3a14, 0x2b2b2b, 0x60232b, 0x1f3b2a, 0x22334f, 0x4d3b1a, 0x333b44, 0x5c2a1e, 0x1a2f22].map((h2) => new THREE.Color(h2));
    const SIGN = [0x7a2a20, 0x1e4a2c, 0x1e3a66, 0x555555, 0x8a7a44, 0x66305a, 0x2a6666, 0x7a5220, 0x444444, 0x80333c, 0x2c5a3c, 0x33486e, 0x6a5228, 0x4a5560, 0x7a3c2c, 0x2a4a34].map((h2) => new THREE.Color(h2));
    const cGlass = new THREE.Color(0x0e1216), cLit = new THREE.Color(0x6a5a3c), cFrame = new THREE.Color(0x2a2724);
    const parts = [], glow = [];
    let made = 0;
    for (let i = 0; i < n; i++) {
      const o = i * 8;
      const x = body[o] * 0.2, z = body[o + 1] * 0.2, ang = body[o + 2] / 1000, w = body[o + 3] / 10, kind = body[o + 4], col = body[o + 5] & 15, fh = body[o + 6] / 10, flags = body[o + 7];
      if (w < 2.5 || fh < 2.5) continue;
      const nx = Math.cos(ang), nz = Math.sin(ang), ry = Math.atan2(-nx, -nz);   // box length along the facade tangent (-nz, nx)
      const gy = siteY(x, z, 'ground');
      const glassH = (flags & 4) ? fh - 0.6 : fh * 0.55;
      const mk = (bw, bh, bd, off, y, tilt) => { const g = new THREE.BoxGeometry(bw, bh, bd); if (tilt) g.rotateX(tilt); g.rotateY(ry); g.translate(x + nx * off, y, z + nz * off); return g; };
      // the frame band (dark) then the glass, both just proud of the wall, so the pattern shader's windows stop at the shop
      parts.push({ geom: mk(w - 0.2, glassH + 0.5, 0.10, 0.12, gy + 0.25 + (glassH + 0.5) / 2, 0), color: cFrame, style: 3 });
      glow.push({ geom: mk(w - 0.7, glassH, 0.14, 0.14, gy + 0.45 + glassH / 2, 0), color: cGlass, style: 3, lit: cLit });
      if (flags & 1) parts.push({ geom: mk(w - 0.5, 0.12, 1.1, 0.62, gy + fh + 0.05, -0.32), color: AWNING[col], style: 3 });
      if (flags & 2) glow.push({ geom: mk(w - 0.8, 0.7, 0.10, 0.14, gy + fh + 0.85 + ((flags & 1) ? 0.25 : 0), 0), color: SIGN[col], style: 3, lit: SIGN[col] });
      made++;
    }
    if (parts.length) { const g = mergeColored(parts); freeOnUpload(g); groupCity.add(new THREE.Mesh(g, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.7, metalness: 0.05 }))); }
    if (glow.length) {   // glass and signs: their own dark colour by day, lit by their `lit` colour after dark
      const gm = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.25, metalness: 0.15 });
      const lit = glow.map((p2) => ({ geom: p2.geom, color: p2.lit, style: 3 }));
      const g = mergeColored(glow); const gl = mergeColored(lit);
      g.setAttribute('aLit', gl.getAttribute('color')); freeOnUpload(g); gl.dispose();
      gm.onBeforeCompile = (sh) => {
        sh.uniforms.uNight = nightUniform;
        sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nattribute vec3 aLit; varying vec3 vLit;').replace('#include <begin_vertex>', '#include <begin_vertex>\nvLit = aLit;');
        sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nuniform float uNight; varying vec3 vLit;').replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance += vLit * uNight * 2.2;');
      };
      groupCity.add(new THREE.Mesh(g, gm));
    }
    STOREFRONT_N = made;
  });
  step('Raising the overpasses', () => {
    if (!OVP.el.length && !OVP.cor.length && !OVP.sk.length) return;
    const parts = [];
    // stored DARK for the legacy color pipeline (flats render ~2.5x lighter)
    const cTop = [0x3b3833, 0x3b3833, 0x3f3c37, 0x3f3c37, 0x43403b, 0x45423d, 0x8f8c85];
    const cConc = 0x6e6b64, cParapet = 0x7d7a73, cPier = 0x6b6760, cCap = 0x5c5852;
    const cWall = 0x5a5751, cCope = 0x7d7a73, cFloor = 0x262421, cGutter = 0x504d47, cLine = 0x8a887f;
    const tint = (hex, m) => new THREE.Color(hex).multiplyScalar(m);
    const dens3 = (pts, step3) => {
      const out = [pts[0].slice()];
      for (let i = 0; i + 1 < pts.length; i++) {
        const a = pts[i], b = pts[i + 1];
        const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const k = Math.max(1, Math.ceil(L / step3));
        for (let j = 1; j <= k; j++) {
          const t = j / k;
          out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]);
        }
      }
      return out;
    };
    const norms = (pts) => {
      const nrm = [];
      for (let i = 0; i < pts.length; i++) {
        const a = pts[Math.max(0, i - 1)], b = pts[Math.min(pts.length - 1, i + 1)];
        let dx = b[0] - a[0], dz = b[1] - a[1];
        const L = Math.hypot(dx, dz) || 1;
        nrm.push([-dz / L, dx / L]);
      }
      return nrm;
    };
    // closed box ribbon: top at y+dyT, bottom at bots[i] (or y+dyB), both sides.
    // seg gate (i) can suppress individual segments (parapet gaps at ramp mouths).
    const boxRibbon = (pts, hw, dyT, dyB, colTop, colSide, bots, gate) => {
      const nrm = norms(pts);
      const top = [], side = [];
      for (let i = 0; i + 1 < pts.length; i++) {
        if (gate && !gate(i)) continue;
        const a = pts[i], b = pts[i + 1], na = nrm[i], nb = nrm[i + 1];
        const aL = [a[0] + na[0] * hw, a[1] + na[1] * hw], aR = [a[0] - na[0] * hw, a[1] - na[1] * hw];
        const bL = [b[0] + nb[0] * hw, b[1] + nb[1] * hw], bR = [b[0] - nb[0] * hw, b[1] - nb[1] * hw];
        const aT = a[2] + dyT, bT = b[2] + dyT;
        const aB = bots ? bots[i] : a[2] + dyB, bB = bots ? bots[i + 1] : b[2] + dyB;
        top.push(aL[0], aT, aL[1], bL[0], bT, bL[1], bR[0], bT, bR[1],
                 aL[0], aT, aL[1], bR[0], bT, bR[1], aR[0], aT, aR[1]);
        side.push(aL[0], aB, aL[1], bL[0], bB, bL[1], bR[0], bB, bR[1],
                  aL[0], aB, aL[1], bR[0], bB, bR[1], aR[0], aB, aR[1]);
        for (const [p0, p1] of [[aL, bL], [aR, bR]]) {
          side.push(p0[0], aT, p0[1], p0[0], aB, p0[1], p1[0], bB, p1[1],
                    p0[0], aT, p0[1], p1[0], bB, p1[1], p1[0], bT, p1[1]);
        }
      }
      const mk = (arr, col) => {
        if (!arr.length) return;
        const g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(arr), 3));
        g.computeVertexNormals();
        parts.push({ geom: g, color: col, style: 3 });
      };
      mk(top, colTop);
      mk(side, colSide);
    };
    const boxAt = (cx, cz, ux, uz, along, across, y0, y1, col) => {
      const g = new THREE.BoxGeometry(along, y1 - y0, across);
      g.rotateY(Math.atan2(-uz, ux));
      g.translate(cx, (y0 + y1) / 2, cz);
      parts.push({ geom: g, color: col, style: 3 });
    };
    const crossingRoadNear = (x, z, r, ux, uz) => {
      const gx = Math.floor(x / SEPTA_RG_CELL), gz = Math.floor(z / SEPTA_RG_CELL);
      for (let cx2 = gx - 1; cx2 <= gx + 1; cx2++) for (let cz2 = gz - 1; cz2 <= gz + 1; cz2++) {
        const a = septaRoadGrid.get(cx2 + ':' + cz2);
        if (!a) continue;
        for (let i = 0; i < a.length; i += 4) {
          const ax = a[i], az = a[i + 1], dx = a[i + 2] - ax, dz = a[i + 3] - az;
          const L2 = dx * dx + dz * dz || 1e-9;
          let tt = ((x - ax) * dx + (z - az) * dz) / L2;
          tt = tt < 0 ? 0 : tt > 1 ? 1 : tt;
          const ex = ax + dx * tt - x, ez = az + dz * tt - z;
          if (ex * ex + ez * ez > r * r) continue;
          const L = Math.sqrt(L2);
          if (Math.abs((dx * ux + dz * uz) / L) < 0.82) return true;
        }
      }
      return false;
    };
    // ------- junction mouths: where one chain's end lands on another's deck -------
    // Parapets and barriers must BREAK there (never a rail across a ramp exit),
    // and the joining deck noses 6 m into the through deck so nothing butts.
    const juncGrid = new Map();
    const JC = 30;
    const juncAdd = (p, q, hw) => {
      // p = chain end, q = the point before it (gives the approach direction)
      let dx = p[0] - q[0], dz = p[1] - q[1];
      const L = Math.hypot(dx, dz) || 1;
      const e = { x: p[0], z: p[1], y: p[2], hw, dx: dx / L, dz: dz / L };
      const k = Math.floor(p[0] / JC) + ':' + Math.floor(p[1] / JC);
      let a = juncGrid.get(k);
      if (!a) { a = []; juncGrid.set(k, a); }
      a.push(e);
    };
    for (const c of OVP.el.concat(OVP.sk)) {
      const e = c.e || [0, 0];
      if (e[0] === 1 && c.p.length > 1) juncAdd(c.p[0], c.p[1], c.w / 2);
      if (e[1] === 1 && c.p.length > 1) juncAdd(c.p[c.p.length - 1], c.p[c.p.length - 2], c.w / 2);
    }
    // is there a ramp mouth at (x,z,y) on the side whose outward normal is (nx,nz)?
    // omit the normal to test both sides (median barriers)
    const mouthAt = (x, z, y, nx, nz, self) => {
      const gx = Math.floor(x / JC), gz = Math.floor(z / JC);
      for (let cx2 = gx - 1; cx2 <= gx + 1; cx2++) for (let cz2 = gz - 1; cz2 <= gz + 1; cz2++) {
        const a = juncGrid.get(cx2 + ':' + cz2);
        if (!a) continue;
        for (const jp of a) {
          if (jp === self) continue;
          const dd = Math.hypot(jp.x - x, jp.z - z);
          if (dd > jp.hw + 6.5 || Math.abs(jp.y - y) > 3.2) continue;
          if (nx === undefined) return true;
          // the mouth opens toward where the ramp came FROM
          if (-(jp.dx * nx + jp.dz * nz) > 0.1 || dd < jp.hw + 1.5) return true;
        }
      }
      return false;
    };
    // another chain's deck at a similar height covering this point (braided ramps,
    // junction noses): parapets must not stab up through the overlapping deck
    const deckOverlapAt = (x, z, y, selfId) => {
      const arr = ovpGrid.get(Math.floor(x / OVP_CELL) + ':' + Math.floor(z / OVP_CELL));
      if (!arr) return false;
      for (const s2 of arr) {
        if (ovpSegs[s2 + 7] < 0 || ovpSegs[s2 + 8] === selfId) continue;
        const sax = ovpSegs[s2], saz = ovpSegs[s2 + 1], sbx = ovpSegs[s2 + 2], sbz = ovpSegs[s2 + 3], hw2 = ovpSegs[s2 + 6];
        const dx = sbx - sax, dz = sbz - saz;
        const L2 = dx * dx + dz * dz || 1e-9;
        let t = ((x - sax) * dx + (z - saz) * dz) / L2;
        t = clamp(t, 0, 1);
        const px = sax + dx * t - x, pz = saz + dz * t - z;
        const r = hw2 - 0.4;
        if (r <= 0 || px * px + pz * pz > r * r) continue;
        const y2 = ovpSegs[s2 + 4] + (ovpSegs[s2 + 5] - ovpSegs[s2 + 4]) * t;
        if (Math.abs(y2 - y) < 2.5) return true;
      }
      return false;
    };
    // another chain's deck passing between the ground and this soffit: a pier
    // must not punch down through a lower roadway (stacked interchanges)
    const deckBetween = (x, z, yLo, yHi, selfId) => {
      const arr = ovpGrid.get(Math.floor(x / OVP_CELL) + ':' + Math.floor(z / OVP_CELL));
      if (!arr) return false;
      for (const s2 of arr) {
        if (ovpSegs[s2 + 7] < 0 || ovpSegs[s2 + 8] === selfId) continue;
        const sax = ovpSegs[s2], saz = ovpSegs[s2 + 1], sbx = ovpSegs[s2 + 2], sbz = ovpSegs[s2 + 3], hw2 = ovpSegs[s2 + 6];
        const dx = sbx - sax, dz = sbz - saz;
        const L2 = dx * dx + dz * dz || 1e-9;
        let t = ((x - sax) * dx + (z - saz) * dz) / L2;
        t = clamp(t, 0, 1);
        const px = sax + dx * t - x, pz = saz + dz * t - z;
        const r = hw2 + 1;
        if (px * px + pz * pz > r * r) continue;
        const y2 = ovpSegs[s2 + 4] + (ovpSegs[s2 + 5] - ovpSegs[s2 + 4]) * t;
        if (y2 > yLo && y2 < yHi) return true;
      }
      return false;
    };
    const shapePts = (c) => {
      const pts = dens3(c.p, 13);
      const e = c.e || [0, 0];
      for (const side of [0, 1]) {
        if ((side ? e[1] : e[0]) !== 1) continue;
        const a = side ? pts[pts.length - 1] : pts[0];
        const b = side ? pts[pts.length - 2] : pts[1];
        let dx = a[0] - b[0], dz = a[1] - b[1];
        const L = Math.hypot(dx, dz) || 1;
        const ext = [a[0] + dx / L * 6, a[1] + dz / L * 6, a[2]];
        if (side) pts.push(ext); else pts.unshift(ext);
      }
      return pts;
    };
    // ---------------- elevated chains: deck box, parapets, piers ----------------
    for (let ci = 0; ci < OVP.el.length; ci++) {
      const c = OVP.el[ci];
      const e = c.e || [0, 0];
      const hw = Math.max(1.6, c.w / 2);
      const dep = c.c <= 1 ? 1.7 : (c.c === 6 ? 0.5 : 1.15);
      const pts = shapePts(c);
      const jit = 0.92 + hash01(ci * 2.13) * 0.16;
      const bots = pts.map((p) => {
        const gy = siteY(p[0], p[1], 'ground');
        return p[2] - gy < 2.2 ? Math.min(p[2] - dep, gy - 0.4) : p[2] - dep;
      });
      boxRibbon(pts, hw, 0, -dep, tint(cTop[c.c] || 0x3b3833, 1), tint(cConc, jit), bots);
      // parapets: fade in past the ends, break at every ramp mouth on their side
      const nrm = norms(pts);
      const ss = [0];
      for (let i = 1; i < pts.length; i++) ss.push(ss[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
      const total = ss[ss.length - 1];
      const pOff = hw - (c.c === 6 ? 0.16 : 0.36);
      const pT = c.c === 6 ? 1.15 : 1.02, pW = c.c === 6 ? 0.09 : 0.17;
      const lead0 = e[0] === 1 ? 6.5 : 14, lead1 = e[1] === 1 ? 6.5 : 14;
      for (const s of [1, -1]) {
        const edge = pts.map((p, i) => [p[0] + nrm[i][0] * pOff * s, p[1] + nrm[i][1] * pOff * s, p[2]]);
        boxRibbon(edge, pW, pT, -0.25, tint(cParapet, jit), tint(cParapet, jit * 0.94), null, (i) => {
          const sm = (ss[i] + ss[i + 1]) / 2;
          if (sm < lead0 || sm > total - lead1) return false;
          const mx = (edge[i][0] + edge[i + 1][0]) / 2, mz = (edge[i][1] + edge[i + 1][1]) / 2;
          const my = (pts[i][2] + pts[i + 1][2]) / 2;
          if (deckOverlapAt(mx, mz, my, ci)) return false;
          return !mouthAt(mx, mz, my, nrm[i][0] * s, nrm[i][1] * s);
        });
      }
      // piers wherever there is clearance and no street crossing beneath
      const gap = c.c <= 1 ? 26 : (c.c === 6 ? 15 : 21);
      let acc = gap * 0.6;
      for (let i = 0; i + 1 < pts.length; i++) {
        const a = pts[i], b = pts[i + 1];
        acc += Math.hypot(b[0] - a[0], b[1] - a[1]);
        if (acc < gap) continue;
        acc = 0;
        const x = (a[0] + b[0]) / 2, z = (a[1] + b[1]) / 2, y = (a[2] + b[2]) / 2;
        let ux = b[0] - a[0], uz = b[1] - a[1];
        const uL = Math.hypot(ux, uz) || 1;
        ux /= uL; uz /= uL;
        const vf = vineCut(x, z, -1);
        const wet = demY(x, z) < TERRAIN.water + 0.6 && riverCorridor(x, z);
        const gy = vf !== null ? vf : (wet ? TERRAIN.bed - 1.2 : siteY(x, z, 'ground'));
        const capBot = y - dep - (c.c === 6 ? 0 : 1.25);
        if (capBot - gy < 2.0) continue;
        if (crossingRoadNear(x, z, 7.5, ux, uz)) continue;
        if (deckBetween(x, z, gy + 0.5, capBot - 0.2, ci)) continue;
        const ps = wet ? 1.6 : 1;
        if (c.c <= 1) {
          boxAt(x, z, ux, uz, 2.3, c.w * 0.92, y - dep - 1.35, y - dep + 0.15, tint(cCap, jit));
          const px = -uz * c.w * 0.24, pz = ux * c.w * 0.24;
          boxAt(x + px, z + pz, ux, uz, 1.5 * ps, 2.0 * ps, gy - 2, capBot + 0.3, tint(cPier, jit));
          boxAt(x - px, z - pz, ux, uz, 1.5 * ps, 2.0 * ps, gy - 2, capBot + 0.3, tint(cPier, jit));
        } else if (c.c === 6) {
          boxAt(x, z, ux, uz, 0.7, 0.7, gy - 2, y - dep + 0.2, tint(cPier, jit));
        } else {
          boxAt(x, z, ux, uz, 1.9, c.w * 0.62, y - dep - 1.15, y - dep + 0.15, tint(cCap, jit));
          boxAt(x, z, ux, uz, 1.35 * ps, 1.8 * ps, gy - 2, capBot + 0.3, tint(cPier, jit));
        }
      }
    }
    // ---------------- the Vine Street cut: walls, floor, portals ----------------
    const collarParts = [];
    const wallQuad = (q, arr) => arr.push(...q);
    for (const run of OVP.cor) {
      const nrm = norms(run);
      const wl = run.map((p, i) => [p[0] + nrm[i][0] * p[3], p[1] + nrm[i][1] * p[3], p[2]]);
      const wr = run.map((p, i) => [p[0] - nrm[i][0] * p[3], p[1] - nrm[i][1] * p[3], p[2]]);
      const gl = wl.map((p) => siteY(p[0], p[1], 'ground'));
      const gr = wr.map((p) => siteY(p[0], p[1], 'ground'));
      const quads = [], copes = [];
      const segGap = (w0, w1, i) => {
        // break the wall where a sunken ramp passes through it (its portal)
        const mx = (w0[i][0] + w0[i + 1][0]) / 2, mz = (w0[i][1] + w0[i + 1][1]) / 2;
        let wx = w0[i + 1][0] - w0[i][0], wz = w0[i + 1][1] - w0[i][1];
        const L = Math.hypot(wx, wz) || 1;
        wx /= L; wz /= L;
        const arr = ovpGrid.get(Math.floor(mx / OVP_CELL) + ':' + Math.floor(mz / OVP_CELL));
        if (!arr) return false;
        for (const s of arr) {
          if (ovpSegs[s + 7] !== -1) continue;
          const sax = ovpSegs[s], saz = ovpSegs[s + 1], sbx = ovpSegs[s + 2], sbz = ovpSegs[s + 3], shw = ovpSegs[s + 6];
          let dx = sbx - sax, dz = sbz - saz;
          const sl = Math.hypot(dx, dz) || 1;
          if (Math.abs((dx * wx + dz * wz) / sl) > 0.85) continue;    // parallel: the mainline itself
          const L2 = sl * sl;
          let t = ((mx - sax) * dx + (mz - saz) * dz) / L2;
          t = clamp(t, 0, 1);
          const px = sax + dx * t - mx, pz = saz + dz * t - mz;
          if (px * px + pz * pz < (shw + 2.5) * (shw + 2.5)) return true;
        }
        return false;
      };
      for (let i = 0; i + 1 < run.length; i++) {
        if (!segGap(wl, wl, i)) {
          wallQuad([wl[i][0], wl[i][2] - 0.6, wl[i][1], wl[i + 1][0], wl[i + 1][2] - 0.6, wl[i + 1][1],
                    wl[i + 1][0], gl[i + 1] + 0.55, wl[i + 1][1],
                    wl[i][0], wl[i][2] - 0.6, wl[i][1], wl[i + 1][0], gl[i + 1] + 0.55, wl[i + 1][1],
                    wl[i][0], gl[i] + 0.55, wl[i][1]], quads);
          copes.push([wl[i], wl[i + 1], gl[i], gl[i + 1]]);
        }
        if (!segGap(wr, wr, i)) {
          wallQuad([wr[i][0], wr[i][2] - 0.6, wr[i][1], wr[i + 1][0], wr[i + 1][2] - 0.6, wr[i + 1][1],
                    wr[i + 1][0], gr[i + 1] + 0.55, wr[i + 1][1],
                    wr[i][0], wr[i][2] - 0.6, wr[i][1], wr[i + 1][0], gr[i + 1] + 0.55, wr[i + 1][1],
                    wr[i][0], gr[i] + 0.55, wr[i][1]], quads);
          copes.push([wr[i], wr[i + 1], gr[i], gr[i + 1]]);
        }
      }
      const wg = new THREE.BufferGeometry();
      wg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(quads), 3));
      wg.computeVertexNormals();
      parts.push({ geom: wg, color: new THREE.Color(cWall), style: 3 });
      // coping caps ride the wall tops (a light parapet band, slightly proud)
      for (const [a, b, ga, gb] of copes) {
        let dx = b[0] - a[0], dz = b[1] - a[1];
        const L = Math.hypot(dx, dz) || 1;
        const ex = (a[0] + b[0]) / 2, ez = (a[1] + b[1]) / 2;
        boxAt(ex, ez, dx / L, dz / L, L + 0.05, 0.55, (ga + gb) / 2 + 0.4, (ga + gb) / 2 + 1.0, tint(cCope, 1));
      }
      // floor slab wall to wall, with lighter gutter strips along each wall base
      const fq = [], gq = [];
      for (let i = 0; i + 1 < run.length; i++) {
        fq.push(wl[i][0], run[i][2], wl[i][1], wl[i + 1][0], run[i + 1][2], wl[i + 1][1], wr[i + 1][0], run[i + 1][2], wr[i + 1][1],
                wl[i][0], run[i][2], wl[i][1], wr[i + 1][0], run[i + 1][2], wr[i + 1][1], wr[i][0], run[i][2], wr[i][1]);
        for (const [w0, s] of [[wl, 1], [wr, -1]]) {
          const g0 = [w0[i][0] - nrm[i][0] * s * 1.1, w0[i][1] - nrm[i][1] * s * 1.1];
          const g1 = [w0[i + 1][0] - nrm[i + 1][0] * s * 1.1, w0[i + 1][1] - nrm[i + 1][1] * s * 1.1];
          gq.push(w0[i][0], run[i][2] + 0.03, w0[i][1], w0[i + 1][0], run[i + 1][2] + 0.03, w0[i + 1][1], g1[0], run[i + 1][2] + 0.03, g1[1],
                  w0[i][0], run[i][2] + 0.03, w0[i][1], g1[0], run[i + 1][2] + 0.03, g1[1], g0[0], run[i][2] + 0.03, g0[1]);
        }
      }
      for (const [arr, col] of [[fq, cFloor], [gq, cGutter]]) {
        const g2 = new THREE.BufferGeometry();
        g2.setAttribute('position', new THREE.BufferAttribute(new Float32Array(arr), 3));
        g2.computeVertexNormals();
        parts.push({ geom: g2, color: new THREE.Color(col), style: 3 });
      }
      // portal faces + header beams where the cut meets a covered section
      for (const e2 of [0, run.length - 1]) {
        const gm = (gl[e2] + gr[e2]) / 2;
        const pg = [wl[e2][0], run[e2][2] - 0.6, wl[e2][1], wr[e2][0], run[e2][2] - 0.6, wr[e2][1],
                    wr[e2][0], gm + 0.55, wr[e2][1],
                    wl[e2][0], run[e2][2] - 0.6, wl[e2][1], wr[e2][0], gm + 0.55, wr[e2][1],
                    wl[e2][0], gm + 0.55, wl[e2][1]];
        const g2 = new THREE.BufferGeometry();
        g2.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pg), 3));
        g2.computeVertexNormals();
        parts.push({ geom: g2, color: new THREE.Color(cWall), style: 3 });
        let hx = wr[e2][0] - wl[e2][0], hz = wr[e2][1] - wl[e2][1];
        const hl = Math.hypot(hx, hz) || 1;
        boxAt((wl[e2][0] + wr[e2][0]) / 2, (wl[e2][1] + wr[e2][1]) / 2, hx / hl, hz / hl,
              hl + 1.2, 1.1, gm - 0.25, gm + 0.85, tint(cCope, 1));
      }
      // grade collar apron hides the ragged heightfield hole around the cut
      for (const s of [1, -1]) {
        const off = run.map((p, i) => [p[0] + nrm[i][0] * (p[3] + 16.5) * s, p[1] + nrm[i][1] * (p[3] + 16.5) * s]);
        collarParts.push({ geom: ribbon(off, 34, 0.07, (x, z) => siteY(x, z, 'ground')), color: new THREE.Color(COLORS.ground), style: 3 });
      }
      // median barrier down the cut, broken at every ramp mouth
      const med = [];
      for (const p of run) {
        if (p[3] < 20 && !mouthAt(p[0], p[1], p[2] + 0.45)) med.push([p[0], p[1], p[2]]);
        else if (med.length > 2) { boxRibbon(med.slice(), 0.26, 0.85, -0.1, tint(cCope, 1), tint(cCope, 0.94)); med.length = 0; }
        else med.length = 0;
      }
      if (med.length > 2) boxRibbon(med, 0.26, 0.85, -0.1, tint(cCope, 1), tint(cCope, 0.94));
    }
    // ------- sunken carriageways and ramps: roadway, edge lines, ramp-cut walls ----
    for (const c of OVP.sk) {
      const pts = shapePts(c);
      const hw = Math.max(1.6, c.w / 2);
      boxRibbon(pts, hw, 0, -0.5, tint(0x33312d, 1), tint(0x2b2926, 1));
      // pale edge lines read as lane striping from altitude
      const nrm = norms(pts);
      for (const s of [1, -1]) {
        const edge = pts.map((p, i) => [p[0] + nrm[i][0] * (hw - 0.45) * s, p[1] + nrm[i][1] * (hw - 0.45) * s, p[2]]);
        boxRibbon(edge, 0.09, 0.03, -0.01, tint(cLine, 1), tint(cLine, 1));
      }
      // outside the main corridor an OPEN sunken ramp runs in its own narrow
      // walled cut; covered tunnels stay under the untouched ground
      const rq = [];
      for (let i = 0; c.cov !== 1 && i + 1 < pts.length; i++) {
        const mx = (pts[i][0] + pts[i + 1][0]) / 2, mz = (pts[i][1] + pts[i + 1][1]) / 2;
        const my = (pts[i][2] + pts[i + 1][2]) / 2;
        if (vineCut(mx, mz, 2) !== null) continue;
        if (demY(mx, mz) - my < 1.0) continue;
        for (const s of [1, -1]) {
          const a = [pts[i][0] + nrm[i][0] * (hw + 0.7) * s, pts[i][1] + nrm[i][1] * (hw + 0.7) * s];
          const b = [pts[i + 1][0] + nrm[i + 1][0] * (hw + 0.7) * s, pts[i + 1][1] + nrm[i + 1][1] * (hw + 0.7) * s];
          const ga = siteY(a[0], a[1], 'ground'), gb = siteY(b[0], b[1], 'ground');
          rq.push(a[0], pts[i][2] - 0.6, a[1], b[0], pts[i + 1][2] - 0.6, b[1], b[0], gb + 0.5, b[1],
                  a[0], pts[i][2] - 0.6, a[1], b[0], gb + 0.5, b[1], a[0], ga + 0.5, a[1]);
        }
      }
      if (rq.length) {
        const g2 = new THREE.BufferGeometry();
        g2.setAttribute('position', new THREE.BufferAttribute(new Float32Array(rq), 3));
        g2.computeVertexNormals();
        parts.push({ geom: g2, color: new THREE.Color(cWall), style: 3 });
        const off1 = pts.map((p, i) => [p[0] + nrm[i][0] * (hw + 12), p[1] + nrm[i][1] * (hw + 12)]);
        const off2 = pts.map((p, i) => [p[0] - nrm[i][0] * (hw + 12), p[1] - nrm[i][1] * (hw + 12)]);
        collarParts.push({ geom: ribbon(off1, 24, 0.07, (x, z) => siteY(x, z, 'ground')), color: new THREE.Color(COLORS.ground), style: 3 });
        collarParts.push({ geom: ribbon(off2, 24, 0.07, (x, z) => siteY(x, z, 'ground')), color: new THREE.Color(COLORS.ground), style: 3 });
      }
    }
    if (parts.length) {
      const ovpMat = surfMat({ vertexColors: true, roughness: 0.92, side: THREE.DoubleSide });
      const mesh = new THREE.Mesh(mergeColored(parts), ovpMat);
      mesh.castShadow = !isTouch;   // phone GPUs skip the deck shadow pass
      mesh.receiveShadow = true;
      groupCity.add(mesh);
      rayTargets.push(mesh);
    }
    if (collarParts.length) {
      const collarMat = groundSurfMat({ side: THREE.DoubleSide });
      const collar = new THREE.Mesh(mergeColored(collarParts), collarMat);
      collar.receiveShadow = true;
      groupCity.add(collar);
    }
  });

  // ------------------------------------------------ trees
  // -------------------------------------------------------------- street trees
  // The real city forest: PPR Tree Inventory 2025 (OpenDataPhilly), baked by
  // fetch_trees.py / pack_trees.py into TREES_B64 (int16, 0.2 m units) and
  // TREE_NAMES (species + latin + canopy group). Every tree is a surveyed
  // street or park tree at its true position, sized by its measured trunk
  // diameter. The old procedural scatter survives below as the fallback when
  // the baked data is absent, so the page always builds.
  let treeInv = null, pickedTree = null;
  const treePickGrid = new Map();
  const TREE_CELL = 24;
  // per-group canopy styling: hue, sat, lit, breadth, height, size mult, shape.
  // Shapes: 0 round crown, 1 conifer spire, 2 vase (zelkova/elm), 3 pyramid
  // (linden). Palettes are pushed well apart so species read at a glance:
  // khaki planetrees, chartreuse ginkgo columns, pale low ornamental puffs,
  // deep oak domes, blue-green conifers.
  // (lightness stored DARK: the legacy color pipeline + ACES lifts flats ~2.5x,
  // so judge these by rendered swatch, never by hex — handoff gotcha)
  // Species separation must live in HUE and SATURATION: the daylight pipeline
  // (strong sun + hemi + ACES) flattens albedo-lightness differences to almost
  // nothing, so chroma carries the identity.
  const TREE_STYLE = [
    [0.26, 0.44, 0.15, 1.0, 1.0, 1.0, 0],      // 0 shade tree / unknown: neutral green
    [0.20, 0.28, 0.16, 1.35, 0.88, 1.25, 0],   // 1 planetree, sycamore: grayed khaki-tan
    [0.33, 0.70, 0.13, 1.0, 1.1, 1.0, 0],      // 2 maple: vivid pure green
    [0.30, 0.60, 0.085, 1.22, 1.02, 1.15, 0],  // 3 oak: deep bottle-green dome
    [0.22, 0.68, 0.165, 1.12, 0.60, 0.72, 0],  // 4 ornamental: bright spring yellow-green puff
    [0.19, 0.55, 0.16, 1.2, 0.72, 0.95, 0],    // 5 locust: warm golden-olive, flat-topped
    [0.36, 0.50, 0.13, 1.0, 1.0, 1.05, 2],     // 6 elm form: cool teal-green vase
    [0.14, 0.68, 0.17, 0.55, 1.55, 0.95, 0],   // 7 ginkgo: unmistakable yellow column
    [0.27, 0.58, 0.145, 1.0, 1.15, 1.0, 3],    // 8 linden: fresh mid-green pyramid
    [0.42, 0.45, 0.075, 1.0, 1.0, 0.92, 1],    // 9 conifer: dark blue-green spire
    [0.30, 0.16, 0.19, 0.72, 1.40, 1.0, 0],    // 10 tall broadleaf: silvery gray-green column
    [0.24, 0.40, 0.15, 1.05, 0.92, 1.0, 0],    // 11 urban misc: dusty olive
  ];
  function treeChipColor(g) {
    const s = TREE_STYLE[g] || TREE_STYLE[0];
    return 'hsl(' + Math.round(s[0] * 360) + ',' + Math.round(s[1] * 100) + '%,' + Math.round((s[2] + 0.13) * 100) + '%)';
  }
  function treeCard(i) {
    const ni = treeInv.ni[i];
    const g = ni >= 0 ? (TREE_NAMES.g[ni] || 0) : 0;
    const name = ni >= 0 ? TREE_NAMES.names[ni] : 'Shade Tree';
    const latin = ni >= 0 ? (TREE_NAMES.latin[ni] || '') : '';
    const dbh = treeInv.dbh[i];
    vehinfoBody.innerHTML =
      '<span class="vroute" style="background:' + treeChipColor(g) + '">' + dbh + '&Prime;</span>' +
      '<span class="vdest">' + septaEsc(name) + '</span>' +
      (latin ? '<div class="vmeta">' + septaEsc(latin) + '</div>' : '') +
      '<div class="vmeta">' + dbh + '-Inch Trunk</div>' +
      '<div class="vmeta">' + (ni >= 0 ? 'PPR Tree Inventory 2025' : 'OpenStreetMap Mapped Tree') + '</div>';
  }
  function updateTreePick() {
    if (pickedTree == null || !treeInv) return;
    _ssv.set(treeInv.x[pickedTree], treeInv.gy[pickedTree] + 3.5, treeInv.z[pickedTree]).project(camera);
    if (_ssv.z > 1 || _ssv.z < -1) vehinfoEl.style.opacity = '0';
    else {
      vehinfoEl.style.opacity = '1';
      vehinfoEl.style.transform = 'translate(-50%,-100%) translate(' +
        ((_ssv.x * 0.5 + 0.5) * window.innerWidth).toFixed(1) + 'px,' +
        ((-_ssv.y * 0.5 + 0.5) * window.innerHeight).toFixed(1) + 'px)';
    }
  }
  function groundPointAt(cx, cy) {
    // march the pick ray to the walkable ground: cheap log-stepped scan, then
    // a short bisection — no raycast against 49k tree instances
    septaNdc.set((cx / window.innerWidth) * 2 - 1, -(cy / window.innerHeight) * 2 + 1);
    septaRay.setFromCamera(septaNdc, camera);
    const o = septaRay.ray.origin, dr = septaRay.ray.direction;
    let t0 = 0;
    for (let t = 10; t < 9000; t *= 1.22) {
      if (o.y + dr.y * t <= walkY(o.x + dr.x * t, o.z + dr.z * t) + 0.5) {
        let lo = t0, hi = t;
        for (let k = 0; k < 12; k++) {
          const m = (lo + hi) / 2;
          if (o.y + dr.y * m <= walkY(o.x + dr.x * m, o.z + dr.z * m) + 0.5) hi = m; else lo = m;
        }
        return [o.x + dr.x * hi, o.z + dr.z * hi];
      }
      t0 = t;
    }
    return null;
  }
  step('Painting the meadow', () => {
    texU.uGrass.value = paintGrassTex(isTouch ? 512 : 1024);
    tuftTex = paintTuftTex(256);
    leafTex = paintLeafTex(isTouch ? 256 : 512);
  });
  step('Planting the street trees', () => {
    if (typeof TREES_B64 === 'undefined' || !TREES_B64 || typeof TREE_NAMES === 'undefined' || !TREE_NAMES) { plantProceduralTrees(); return; }
    let head, v;
    try {
      const buf = unb64(TREES_B64, 'TREES');
      TREES_B64 = null;
      head = new Int32Array(buf.buffer, 0, 4);
      if (head[0] !== 0x53485454) throw new Error('bad tree magic');
      v = new Int16Array(buf.buffer, 16);
    } catch (err) { console.error('tree inventory decode failed', err); plantProceduralTrees(); return; }
    const nAll = head[1];
    const WB = { x0: -3700, x1: 2300, z0: -4480, z1: 6400 };  // wide tier (pack_wide.py)
    const inCore = (x, z) => x > CORE_EXT.x0 && x < CORE_EXT.x1 && z > CORE_EXT.z0 && z < CORE_EXT.z1;
    const X = new Float32Array(nAll + 512), Z = new Float32Array(nAll + 512), GY = new Float32Array(nAll + 512);
    const CR = new Float32Array(nAll + 512), CY = new Float32Array(nAll + 512);
    const DBH = new Uint8Array(nAll + 512), NI = new Int16Array(nAll + 512);
    const CORE = new Uint8Array(nAll + 512);
    let n = 0;
    const keepTree = (x, z, dbh, ni, core) => {
      if (vineCut(x, z, 2) !== null) return;   // no trees floating over the expressway cut
      const g = ni >= 0 ? (TREE_NAMES.g[ni] || 0) : 0;
      const st = TREE_STYLE[g] || TREE_STYLE[0];
      X[n] = x; Z[n] = z; DBH[n] = dbh; NI[n] = ni; CORE[n] = core ? 1 : 0;
      GY[n] = siteY(x, z, 'ground');
      CR[n] = clamp((1.1 + dbh * 0.14) * st[5], 1.3, 7.5);
      CY[n] = GY[n] + clamp(2.4 + dbh * 0.1, 2.6, 5.2) * 0.75 + CR[n] * st[4] * 0.72;
      const k = Math.floor(x / TREE_CELL) + ':' + Math.floor(z / TREE_CELL);
      let cell = treePickGrid.get(k);
      if (!cell) { cell = []; treePickGrid.set(k, cell); }
      cell.push(n);
      n++;
    };
    const nearKept = (x, z, r) => {
      const gx = Math.floor(x / TREE_CELL), gz = Math.floor(z / TREE_CELL);
      for (let ix = gx - 1; ix <= gx + 1; ix++) for (let iz = gz - 1; iz <= gz + 1; iz++) {
        const cell = treePickGrid.get(ix + ':' + iz);
        if (!cell) continue;
        for (const ti of cell) {
          const dx = X[ti] - x, dz = Z[ti] - z;
          if (dx * dx + dz * dz < r * r) return true;
        }
      }
      return false;
    };
    const bermHit = (x, z) => {
      for (const [bx, bz, rx, rz, th] of bermSpots) {
        const dx = x - bx, dz = z - bz, cth = Math.cos(th), sth = Math.sin(th);
        const u = dx * cth - dz * sth, w = dx * sth + dz * cth;
        if ((u / rx) * (u / rx) + (w / rz) * (w / rz) < 1.25) return true;
      }
      return false;
    };
    for (let i = 0; i < nAll; i++) {
      const x = v[i * 4] / 5, z = v[i * 4 + 1] / 5;
      const core = inCore(x, z);
      if (!core && isTouch && (i & 1)) continue;          // touch keeps half the wide forest
      if (inWater(x, z) > -2) continue;
      if (core) {
        // the core's landmarks were rebuilt by hand and differ from the city
        // footprints the bake rejected against, so re-check here
        if (insideBuilding(x, z) || nearBuildingEdge(x, z, 0.8)) continue;
        if (nearRoad(x, z, -1.2)) continue;               // >1.2 m INSIDE a road ribbon only
        if (bermHit(x, z)) continue;
      } else if (septaSnapRoad(x, z, 2.4)) continue;      // wide tier: centerline strip only
      keepTree(x, z, clamp(v[i * 4 + 2], 1, 60), v[i * 4 + 3], core);
    }
    const nInv = n;
    // curated grounds the survey doesn't cover: the towers' lawns, pool
    // terraces, and OSM-mapped courtyard trees — only where no surveyed tree
    // already stands within 6 m
    const extras = [];
    for (const t of D.trees || []) extras.push([t[0], t[1], 10]);
    for (const sp of poolTreeSpots) extras.push([sp[0], sp[1], 14]);
    for (const sp of extraTreeSpots) extras.push([sp[0], sp[1], 14]);
    for (let i = 0; i < 90; i++) {
      const ang = hash01(i * 1.9 + 2) * Math.PI * 2, rr = PLAZA_R + 6 + hash01(i * 3.7) * 50;
      extras.push([towersCenter.x + Math.cos(ang) * rr, towersCenter.z + Math.sin(ang) * rr, 12 + Math.round(hash01(i * 7.1) * 10)]);
    }
    for (const [x, z, dbh] of extras) {
      if (n >= X.length) break;
      if (nearKept(x, z, 6)) continue;
      if (inWater(x, z) > -2) continue;
      if (insideBuilding(x, z) || nearBuildingEdge(x, z, 1.6)) continue;
      if (nearRoad(x, z, 1.2)) continue;
      if (bermHit(x, z)) continue;
      keepTree(x, z, dbh, -1, inCore(x, z));
    }
    treeInv = { x: X, z: Z, gy: GY, cr: CR, cy: CY, dbh: DBH, ni: NI, n };
    // ---- instancing: full trees in the core, light trees in 3x3 wide chunks
    // the crowns are lumpy, flat-shaded blobs: every vertex of the unit icosahedron steps in
    // or out by a hash of its position (seeded per tree), so a crown is a low-poly puff with
    // facets that catch the sun instead of a smooth ball showing through its leaf cards, and
    // a three-octave mottle breaks each facet into leaf clusters. The sway is shared with the
    // cards (canopySway); the displacement is the crown's alone (a card must stay a quad)
    const canMat = new THREE.MeshStandardMaterial({ roughness: 1, envMapIntensity: 0.25, flatShading: true });   // matte: the sky's sheen read as a second object
    const canopySway = (sh) => {   // the leaves move: a slow sway from the wind, per tree, plus a flutter; the crown is lit on top and dark underneath
      sh.uniforms.uTime = waterU.uTime;
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', '#include <common>\nvarying float vCY;')
        .replace('#include <color_fragment>', '#include <color_fragment>\n{ float tp = smoothstep(-0.9, 0.9, vCY); diffuseColor.rgb *= mix(vec3(0.52, 0.60, 0.48), vec3(1.12, 1.08, 0.92), tp); }');
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nuniform float uTime; varying float vCY;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nvCY = position.y;\n{\n  vec4 tw = instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0);\n  float ph = tw.x * 0.07 + tw.z * 0.05;\n  float sw = sin(uTime * 1.1 + ph) * 0.6 + sin(uTime * 2.3 + ph * 3.1) * 0.25;\n  float up = clamp(position.y * 0.5 + 0.5, 0.0, 1.0);\n  transformed.x += sw * 0.07 * up; transformed.z += sw * 0.035 * up; transformed.y += sin(uTime * 3.1 + ph * 5.0 + position.x * 2.0) * 0.02 * up;\n}');
      cloudShadowPatch(sh, 'cameraPosition - vViewPosition * mat3(viewMatrix)');
    };
    canMat.onBeforeCompile = (sh) => {
      canopySway(sh);
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vOP;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\n{ float vh = fract(sin(dot(position + vec3(instanceMatrix[3].x, 0.0, instanceMatrix[3].z) * 0.037, vec3(12.9898, 78.233, 37.719))) * 43758.5453); transformed *= 0.79 + 0.42 * vh; }\nvOP = position * 5.0 + vec3(instanceMatrix[3].x, 0.0, instanceMatrix[3].z) * 0.73;');
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vOP;\nfloat ch3(vec3 p){ p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }\nfloat cn3(vec3 x){ vec3 i = floor(x), f = fract(x); f = f * f * (3.0 - 2.0 * f); return mix(mix(mix(ch3(i), ch3(i + vec3(1, 0, 0)), f.x), mix(ch3(i + vec3(0, 1, 0)), ch3(i + vec3(1, 1, 0)), f.x), f.y), mix(mix(ch3(i + vec3(0, 0, 1)), ch3(i + vec3(1, 0, 1)), f.x), mix(ch3(i + vec3(0, 1, 1)), ch3(i + vec3(1, 1, 1)), f.x), f.y), f.z); }')
        .replace('#include <color_fragment>', '#include <color_fragment>\n{ float cN = 0.6 * cn3(vOP) + 0.3 * cn3(vOP * 2.3 + 7.1) + 0.1 * cn3(vOP * 5.1 + 3.3); diffuseColor.rgb *= 0.7 + 0.5 * cN; }');
    };
    const trunkMat = new THREE.MeshStandardMaterial({ color: COLORS.trunk, roughness: 1 });
    const trunkCoreG = new THREE.CylinderGeometry(0.17, 0.28, 3.6, 6);
    trunkCoreG.translate(0, 1.0, 0);   // extends below grade so raised layers never slice the base
    const trunkWideG = new THREE.CylinderGeometry(0.18, 0.27, 3.6, 5);
    trunkWideG.translate(0, 1.0, 0);
    const canCoreG = new THREE.IcosahedronGeometry(1, 1);
    const canWideG = new THREE.IcosahedronGeometry(1, isTouch ? 0 : 1);
    // leaf cards (desktop): a ring of alpha-cut leaf-cluster quads round a shrunken core, each
    // card's normal the crown's own sphere direction lifted toward up so undersides keep light;
    // the sway shader and the cloud shade are the canopy's. Touch keeps the faceted blobs.
    const CARDS = isTouch ? 0 : 32;
    const canK = CARDS ? 0.7 : 1;
    // n cards scattered through the crown, every one facing its own random way (an outward
    // ring read as a wreath from above); the lighting normal is the crown sphere's, lifted
    const cardGeom = (n, seed) => {
      const pos = [], nor = [], uv = [], idxA = [];
      const up = new V3(0, 1, 0), nn = new V3(), u = new V3(), vv = new V3(), cc = new V3(), p = new V3(), pn = new V3();
      for (let k = 0; k < n; k++) {
        const y = 1 - 2 * (k + 0.5) / n, r = Math.sqrt(Math.max(0, 1 - y * y)), ph = k * 2.399963 + seed;
        cc.set(Math.cos(ph) * r, y * 0.85, Math.sin(ph) * r).multiplyScalar(0.60 * (0.7 + 0.3 * hash01(k * 1.3 + seed)));
        const th = hash01(k * 7.1 + seed) * Math.PI * 2, cz = hash01(k * 2.9 + seed) * 2 - 1, sz = Math.sqrt(Math.max(0, 1 - cz * cz));
        nn.set(Math.cos(th) * sz, cz, Math.sin(th) * sz);
        u.crossVectors(nn, Math.abs(nn.y) > 0.9 ? new V3(1, 0, 0) : up).normalize();
        vv.crossVectors(nn, u).normalize();
        const s = 0.42 + 0.14 * hash01(k * 5.1 + seed);
        const base = pos.length / 3;
        for (const [a, b] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) {
          p.copy(cc).addScaledVector(u, a * s).addScaledVector(vv, b * s);
          pos.push(p.x, p.y, p.z);
          pn.copy(p).normalize().lerp(up, 0.4).normalize();
          nor.push(pn.x, pn.y, pn.z);
          uv.push(a > 0 ? 1 : 0, b > 0 ? 1 : 0);
        }
        idxA.push(base, base + 1, base + 2, base, base + 2, base + 3);
      }
      const g2 = new THREE.BufferGeometry();
      g2.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
      g2.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
      g2.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
      g2.setIndex(idxA);
      return g2;
    };
    const cardG = CARDS ? cardGeom(CARDS, 0.7) : null;          // the core's crowns
    const cardWideG = CARDS ? cardGeom(14, 2.3) : null;         // the outer districts' (a third of the fill)
    const leafMat = CARDS ? new THREE.MeshStandardMaterial({ map: leafTex, alphaTest: 0.5, side: THREE.DoubleSide, roughness: 1, envMapIntensity: 0.25 }) : null;
    if (leafMat) leafMat.onBeforeCompile = (sh) => {   // lit as a shell on the crown's normal: no faceDirection flip, or half the cards show their dark backs
      canopySway(sh);
      sh.fragmentShader = sh.fragmentShader.replace('#include <normal_fragment_begin>', THREE.ShaderChunk.normal_fragment_begin.replace('normal = normal * faceDirection;', ''));
    };
    const coneG = new THREE.ConeGeometry(1, 1, 7);
    coneG.translate(0, 0.5, 0);
    // species silhouettes beyond the sphere: a zelkova/elm vase (flaring cup
    // with a low crown cap) and a linden pyramid, both unit-sized like the ico
    const concatGeo = (list) => {
      const parts2 = list.map((g2) => (g2.index ? g2.toNonIndexed() : g2));
      let total = 0;
      for (const g2 of parts2) total += g2.attributes.position.count;
      const pos2 = new Float32Array(total * 3), nor2 = new Float32Array(total * 3);
      let o2 = 0;
      for (const g2 of parts2) {
        pos2.set(g2.attributes.position.array, o2 * 3);
        nor2.set(g2.attributes.normal.array, o2 * 3);
        o2 += g2.attributes.position.count;
      }
      const out = new THREE.BufferGeometry();
      out.setAttribute('position', new THREE.BufferAttribute(pos2, 3));
      out.setAttribute('normal', new THREE.BufferAttribute(nor2, 3));
      return out;
    };
    const vaseG = concatGeo([
      new THREE.CylinderGeometry(1.0, 0.3, 1.3, 7).translate(0, -0.25, 0),
      new THREE.IcosahedronGeometry(1, 0).scale(1.02, 0.5, 1.02).translate(0, 0.42, 0),
    ]);
    const pyrG = new THREE.ConeGeometry(1, 1.7, 7);
    const CHN = 3;
    const chunkOf = (x, z) => {
      const cx2 = clamp(Math.floor((x - WB.x0) / ((WB.x1 - WB.x0) / CHN)), 0, CHN - 1);
      const cz2 = clamp(Math.floor((z - WB.z0) / ((WB.z1 - WB.z0) / CHN)), 0, CHN - 1);
      return cx2 * CHN + cz2;
    };
    // instance transforms don't grow a shared geometry's unit-sized bounding
    // sphere, so every mesh gets its own cloned geometry with a hand-set
    // sphere over its real extent — wide chunks still frustum-cull as wholes
    const instMesh = (base, mat2, count, sx2, sz2, rad) => {
      const g2 = base.clone();
      g2.boundingSphere = new THREE.Sphere(new V3(sx2, 10, sz2), rad);
      g2.isCanopyCore = base === canCoreG || base === canWideG || base === vaseG || base === pyrG;
      return new THREE.InstancedMesh(g2, mat2, count);
    };
    // the species colour as a tint on the painted leaves: normalised on green, eased to white;
    // the crown's core and lumps take the same tint (times the sprite's mean) so a ginkgo is
    // one yellow object, not green cards round a yellow ball
    const white = new THREE.Color(1, 1, 1);
    const cardTint = (i, st, out) => {
      out.setHSL(st[0] + (hash01(i * 4.9) - 0.5) * 0.045, Math.min(1, st[1]), 0.32 + (hash01(i * 8.3) - 0.5) * 0.08);
      out.multiplyScalar(1 / Math.max(0.05, out.g));
      out.r = Math.min(out.r, 1.6); out.b = Math.min(out.b, 1.6);
      return out.lerp(white, 0.30).multiplyScalar(0.8 + hash01(i * 2.3) * 0.3);
    };
    const paintCards = (idx, sx2, sz2, rad, full, geom, conifer) => {
      const mesh = instMesh(geom || cardG, leafMat, idx.length, sx2, sz2, rad);
      for (let k = 0; k < idx.length; k++) {
        const i = idx[k];
        const g = NI[i] >= 0 ? (TREE_NAMES.g[NI[i]] || 0) : 0;
        const st = TREE_STYLE[g] || TREE_STYLE[0];
        q.setFromAxisAngle(_sup, hash01(i * 9.1) * Math.PI * 2);
        if (conifer) {   // a column of boughs up the spire
          const h = clamp(3 + DBH[i] * 0.25, 3.5, 14), r = clamp(0.8 + DBH[i] * 0.06, 1, 3.5);
          m.compose(new V3(X[i], GY[i] + h * 0.5, Z[i]), q, new V3(r * 1.2, h * 0.5, r * 1.2));
        } else {
          const cy = canopyAt(i, st);
          m.compose(new V3(X[i], cy, Z[i]), q, new V3(CR[i] * st[3], CR[i] * st[4] * (0.9 + hash01(i * 7.7) * 0.25), CR[i] * st[3]));
        }
        mesh.setMatrixAt(k, m);
        mesh.setColorAt(k, cardTint(i, st, cCan));
      }
      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      mesh.castShadow = !!full; mesh.receiveShadow = false;
      groupCity.add(mesh);
    };
    const coreCX = (CORE_EXT.x0 + CORE_EXT.x1) / 2, coreCZ = (CORE_EXT.z0 + CORE_EXT.z1) / 2;
    const coreR = Math.hypot(CORE_EXT.x1 - CORE_EXT.x0, CORE_EXT.z1 - CORE_EXT.z0) / 2 + 40;
    const chW = (WB.x1 - WB.x0) / CHN, chD = (WB.z1 - WB.z0) / CHN;
    const chR = Math.hypot(chW, chD) / 2 + 40;
    const chCX = (c) => WB.x0 + (Math.floor(c / CHN) + 0.5) * chW;
    const chCZ = (c) => WB.z0 + ((c % CHN) + 0.5) * chD;
    const wideR = Math.hypot(WB.x1 - WB.x0, WB.z1 - WB.z0) / 2 + 40;
    // canopies split by shape (round crowns keep the core/wide chunk split;
    // vases, pyramids and conifer spires draw citywide in one mesh each), and
    // every non-conifer tree gets its trunk from the tier trunk meshes
    const buckets = { core: [], cones: [], vases: [], pyrs: [], wide: [], tCore: [], tWide: [] };
    for (let c = 0; c < CHN * CHN; c++) { buckets.wide.push([]); buckets.tWide.push([]); }
    for (let i = 0; i < n; i++) {
      const g = NI[i] >= 0 ? (TREE_NAMES.g[NI[i]] || 0) : 0;
      const shape = (TREE_STYLE[g] || TREE_STYLE[0])[6];
      if (shape === 1) { buckets.cones.push(i); continue; }
      if (CORE[i]) buckets.tCore.push(i); else buckets.tWide[chunkOf(X[i], Z[i])].push(i);
      if (shape === 2) buckets.vases.push(i);
      else if (shape === 3) buckets.pyrs.push(i);
      else if (CORE[i]) buckets.core.push(i);
      else buckets.wide[chunkOf(X[i], Z[i])].push(i);
    }
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), cCan = new THREE.Color();
    const trunkScale = (dbh) => {
      const r = clamp(dbh * 0.0127, 0.06, 0.55) / 0.28;
      const h = clamp(2.4 + dbh * 0.1, 2.6, 5.2) / 3.6;
      return [r, h];
    };
    const canopyAt = (i, st) => {
      // crown base clears head height; center rises with the crown's own
      // vertical extent so puffs sit low and columns ride high
      const th = clamp(2.4 + DBH[i] * 0.1, 2.6, 5.2);
      return GY[i] + th * 0.75 + CR[i] * st[4] * 0.72;
    };
    const paint = (mesh, idx, canopy, full) => {
      for (let k = 0; k < idx.length; k++) {
        const i = idx[k];
        const g = NI[i] >= 0 ? (TREE_NAMES.g[NI[i]] || 0) : 0;
        const st = TREE_STYLE[g] || TREE_STYLE[0];
        q.setFromAxisAngle(_sup, hash01(i * 9.1) * Math.PI * 2);
        if (canopy) {
          const cy = canopyAt(i, st);
          const kk = mesh.geometry.isCanopyCore ? canK : 1;   // round crowns shrink under their cards
          m.compose(new V3(X[i], cy, Z[i]), q, new V3(CR[i] * st[3] * kk, CR[i] * st[4] * (0.9 + hash01(i * 7.7) * 0.25) * kk, CR[i] * st[3] * kk));
          mesh.setMatrixAt(k, m);
          if (kk !== 1) cardTint(i, st, cCan).multiply(texU.leafNorm).multiplyScalar(0.06);   // the core wears the cards' own colour, at the sprite's mean
          else cCan.setHSL(st[0] + (hash01(i * 4.9) - 0.5) * 0.045, Math.min(1, (st[1] + (hash01(i * 6.1) - 0.5) * 0.12) * 1.15), st[2] + 0.015 + (hash01(i * 8.3) - 0.5) * 0.05);
          mesh.setColorAt(k, cCan);
        } else {
          const [rs, hs] = trunkScale(DBH[i]);
          const oT = frontOff(X[i], Z[i]);
          const capLift = (CORE[i] && oT > TERRAIN.trenchW - 1 && oT < TERRAIN.trenchE + 1) ? 0.82 : 0;
          m.compose(new V3(X[i], GY[i] + capLift, Z[i]), q, new V3(rs, hs, rs));
          mesh.setMatrixAt(k, m);
        }
      }
      mesh.instanceMatrix.needsUpdate = true;
      if (canopy && mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      mesh.castShadow = !!full;
      mesh.receiveShadow = false;
      groupCity.add(mesh);
    };
    // core: trunks + faceted canopies + two extra lobes each, with shadows
    if (buckets.tCore.length) paint(instMesh(trunkCoreG, trunkMat, buckets.tCore.length, coreCX, coreCZ, coreR), buckets.tCore, false, true);
    const ci = buckets.core;
    if (ci.length) {
      paint(instMesh(canCoreG, canMat, ci.length, coreCX, coreCZ, coreR), ci, true, true);
      const lumps = instMesh(canCoreG, canMat, ci.length * 2, coreCX, coreCZ, coreR);
      for (let k = 0; k < ci.length; k++) {
        const i = ci[k];
        const g = NI[i] >= 0 ? (TREE_NAMES.g[NI[i]] || 0) : 0;
        const st = TREE_STYLE[g] || TREE_STYLE[0];
        const cy = canopyAt(i, st);
        for (let l = 0; l < 2; l++) {
          const a = hash01(i * 3.3 + l * 17.1) * Math.PI * 2;
          const r = CR[i] * (0.45 + 0.25 * hash01(i * 4.1 + l)) * canK;
          const ls = CR[i] * (0.5 + 0.25 * hash01(i * 6.3 + l * 5)) * canK;
          m.compose(new V3(X[i] + Math.cos(a) * r, cy - CR[i] * 0.15 + hash01(i + l * 3) * CR[i] * 0.35, Z[i] + Math.sin(a) * r), q, new V3(ls, ls * 0.9, ls));
          lumps.setMatrixAt(k * 2 + l, m);
          if (canK !== 1) cardTint(i, st, cCan).multiply(texU.leafNorm).multiplyScalar(0.055 + 0.01 * l);
          else cCan.setHSL(st[0] + (hash01(i * 4.9) - 0.5) * 0.04, st[1] - 0.06, st[2] + 0.05 + 0.02 * l);
          lumps.setColorAt(k * 2 + l, cCan);
        }
      }
      lumps.instanceMatrix.needsUpdate = true;
      if (lumps.instanceColor) lumps.instanceColor.needsUpdate = true;
      lumps.castShadow = true;
      groupCity.add(lumps);
      if (cardG) paintCards(ci, coreCX, coreCZ, coreR, true);
    }
    // wide tier: one light trunk + canopy pair per chunk so whole chunks cull
    for (let c = 0; c < CHN * CHN; c++) {
      const ti = buckets.tWide[c];
      if (ti.length) paint(instMesh(trunkWideG, trunkMat, ti.length, chCX(c), chCZ(c), chR), ti, false, false);
      const wi = buckets.wide[c];
      if (wi.length) paint(instMesh(canWideG, canMat, wi.length, chCX(c), chCZ(c), chR), wi, true, false);
      // (the wide tier carried a second lobe per crown for a round; the lumpy displacement
      // gives every crown its asymmetry now, and the lobes were 3.2M triangles a frame)
      if (wi.length && cardG) paintCards(wi, chCX(c), chCZ(c), chR, false, cardWideG);
    }
    // species silhouettes, citywide: zelkova/elm vases and linden pyramids
    if (buckets.vases.length) paint(instMesh(vaseG, canMat, buckets.vases.length, (WB.x0 + WB.x1) / 2, (WB.z0 + WB.z1) / 2, wideR), buckets.vases, true, false);
    if (buckets.pyrs.length) paint(instMesh(pyrG, canMat, buckets.pyrs.length, (WB.x0 + WB.x1) / 2, (WB.z0 + WB.z1) / 2, wideR), buckets.pyrs, true, false);
    if (cardG && buckets.vases.length) paintCards(buckets.vases, (WB.x0 + WB.x1) / 2, (WB.z0 + WB.z1) / 2, wideR, false, cardWideG);
    if (cardG && buckets.pyrs.length) paintCards(buckets.pyrs, (WB.x0 + WB.x1) / 2, (WB.z0 + WB.z1) / 2, wideR, false, cardWideG);
    // conifers: cones straight from the ground, both tiers in one mesh
    const ki = buckets.cones;
    if (ki.length) {
      const cones = instMesh(coneG, canMat, ki.length, (WB.x0 + WB.x1) / 2, (WB.z0 + WB.z1) / 2, wideR);
      for (let k = 0; k < ki.length; k++) {
        const i = ki[k];
        const h = clamp(3 + DBH[i] * 0.25, 3.5, 14), r = clamp(0.8 + DBH[i] * 0.06, 1, 3.5);
        q.setFromAxisAngle(_sup, hash01(i * 9.1) * Math.PI * 2);
        m.compose(new V3(X[i], GY[i], Z[i]), q, new V3(r, h, r));
        cones.setMatrixAt(k, m);
        cCan.setHSL(0.36 + (hash01(i * 4.9) - 0.5) * 0.03, 0.4, (cardG ? 0.075 : 0.14) + (hash01(i * 8.3) - 0.5) * 0.03);
        cones.setColorAt(k, cCan);
      }
      cones.instanceMatrix.needsUpdate = true;
      if (cones.instanceColor) cones.instanceColor.needsUpdate = true;
      cones.castShadow = true;
      groupCity.add(cones);
      if (cardG) paintCards(ki, (WB.x0 + WB.x1) / 2, (WB.z0 + WB.z1) / 2, wideR, false, cardWideG, true);
    }
    console.log('planted', nInv, 'surveyed trees +', n - nInv, 'curated,',
      buckets.cones.length, 'conifers,', buckets.vases.length, 'vases,', buckets.pyrs.length, 'pyramids');
  });
  function plantProceduralTrees() {
    const spots = [];
    const minD2 = 6 * 6;
    function clear(x, z) {
      if (inWater(x, z) > -8) return false;
      if (nearBuildingEdge(x, z, 2.4)) return false;
      if (insideBuilding(x, z)) return false;
      if (nearRoad(x, z, 1.2)) return false;
      for (const [bx, bz, rx, rz, th] of bermSpots) {
        const dx = x - bx, dz = z - bz, cth = Math.cos(th), sth = Math.sin(th);
        const u = dx * cth - dz * sth, v = dx * sth + dz * cth;
        if ((u / rx) * (u / rx) + (v / rz) * (v / rz) < 1.25) return false;
      }
      for (let i = spots.length - 1; i >= 0 && i > spots.length - 40; i--) {
        const dx = spots[i][0] - x, dz = spots[i][1] - z;
        if (dx * dx + dz * dz < minD2) return false;
      }
      return true;
    }
    for (const r of D.roads) {
      if (!/residential|living_street|pedestrian|tertiary/.test(r.t)) continue;
      const off = r.w / 2 + 2.4;
      let acc = 0;
      for (let i = 0; i < r.pts.length - 1; i++) {
        const ax = r.pts[i][0], az = r.pts[i][1], bx = r.pts[i + 1][0], bz = r.pts[i + 1][1];
        const segL = Math.hypot(bx - ax, bz - az);
        if (segL < 0.5) continue;
        const ux = (bx - ax) / segL, uz = (bz - az) / segL;
        for (let d = acc; d < segL; d += 13) {
          const px = ax + ux * d, pz = az + uz * d;
          const j = (hash01(px * 0.37 + pz * 1.91) - 0.5) * 4;
          for (const sgn of [-1, 1]) {
            const x = px - uz * (off * sgn) + ux * j, z = pz + ux * (off * sgn) + uz * j;
            if (hash01(x * 3.1 + z * 0.7) < 0.55 && clear(x, z)) spots.push([x, z]);
          }
        }
        acc = 0;
      }
    }
    for (const a of D.areas || []) {
      if (a.kind !== 'park' || a.poly.length < 3) continue;
      let bx0 = 1e9, bx1 = -1e9, bz0 = 1e9, bz1 = -1e9;
      for (const p of a.poly) { bx0 = Math.min(bx0, p[0]); bx1 = Math.max(bx1, p[0]); bz0 = Math.min(bz0, p[1]); bz1 = Math.max(bz1, p[1]); }
      const n = Math.min(40, Math.floor(Math.abs(signedArea(a.poly)) / 220));
      for (let i = 0; i < n * 4 && spots.length < 1700; i++) {
        const x = lerp(bx0, bx1, hash01(i * 1.3 + bx0));
        const z = lerp(bz0, bz1, hash01(i * 2.7 + bz1));
        if (pointInPoly(x, z, a.poly) && clear(x, z)) spots.push([x, z]);
      }
    }
    for (const t of D.trees || []) if (clear(t[0], t[1])) spots.push([t[0], t[1]]);
    // mature trees around the towers' lawns
    for (let i = 0; i < 90 && spots.length < 2300; i++) {
      const ang = hash01(i * 1.9 + 2) * Math.PI * 2, rr = PLAZA_R + 6 + hash01(i * 3.7) * 50;
      const x = towersCenter.x + Math.cos(ang) * rr, z = towersCenter.z + Math.sin(ang) * rr;
      if (clear(x, z)) spots.push([x, z]);
    }
    for (const sp of poolTreeSpots) if (clear(sp[0], sp[1]) && spots.length < 2400) spots.push(sp);
    for (const sp of extraTreeSpots) if (spots.length < 2400) spots.push(sp);

    const N = Math.min(spots.length, 2400);
    if (!N) return;
    const trunkG = new THREE.CylinderGeometry(0.17, 0.28, 3.6, 6);
    trunkG.translate(0, 1.0, 0);   // extends 0.8 m below grade so raised layers never slice the base
    const canG = new THREE.IcosahedronGeometry(1, 1);
    const trunks = new THREE.InstancedMesh(trunkG, new THREE.MeshStandardMaterial({ color: COLORS.trunk, roughness: 1 }), N);
    const cans = new THREE.InstancedMesh(canG, new THREE.MeshStandardMaterial({ roughness: 0.95 }), N);
    const m = new THREE.Matrix4();
    const q = new THREE.Quaternion();
    const cCan = new THREE.Color();
    for (let i = 0; i < N; i++) {
      const [x, z] = spots[i];
      const s = 2.1 + hash01(i * 5.77) * 1.5;
      q.setFromAxisAngle(new V3(0, 1, 0), hash01(i * 9.1) * Math.PI * 2);
      const ty = siteY(x, z, 'ground');
      // over the trench cap decks the below-grade extension would dangle into the
      // I-95 tunnel — lift those trunks so their base sits at the deck surface
      const oT = frontOff(x, z);
      const capLift = (oT > TERRAIN.trenchW - 1 && oT < TERRAIN.trenchE + 1) ? 0.82 : 0;
      m.compose(new V3(x, ty + capLift, z), q, new V3(1, 0.9 + hash01(i * 2.3) * 0.35, 1));
      trunks.setMatrixAt(i, m);
      m.compose(new V3(x, ty + 2.6 + s * 0.72, z), q, new V3(s, s * (0.92 + hash01(i * 7.7) * 0.3), s));
      cans.setMatrixAt(i, m);
      cCan.setHSL(0.26 + hash01(i * 4.9) * 0.05, 0.46 + hash01(i * 6.1) * 0.14, 0.17 + hash01(i * 8.3) * 0.06);
      cans.setColorAt(i, cCan);
    }
    // secondary lobes make the canopies read as foliage rather than balloons
    const lumps = new THREE.InstancedMesh(canG, cans.material, N * 2);
    for (let i = 0; i < N; i++) {
      const [x, z] = spots[i];
      const s = 2.1 + hash01(i * 5.77) * 1.5;
      const baseY = siteY(x, z, 'ground') + 2.6 + s * 0.72;
      for (let k = 0; k < 2; k++) {
        const a = hash01(i * 3.3 + k * 17.1) * Math.PI * 2;
        const r = s * (0.45 + 0.25 * hash01(i * 4.1 + k));
        const ls = s * (0.55 + 0.25 * hash01(i * 6.3 + k * 5));
        m.compose(new V3(x + Math.cos(a) * r, baseY - s * 0.15 + hash01(i + k * 3) * s * 0.4, z + Math.sin(a) * r), q, new V3(ls, ls * 0.9, ls));
        lumps.setMatrixAt(i * 2 + k, m);
        cCan.setHSL(0.26 + hash01(i * 4.9) * 0.045, 0.38 + hash01(i * 6.1) * 0.12, 0.24 + hash01(i * 8.3) * 0.07 + 0.02 * k);
        lumps.setColorAt(i * 2 + k, cCan);
      }
    }
    trunks.castShadow = true;
    cans.castShadow = true;
    lumps.castShadow = true;
    groupCity.add(trunks, cans, lumps);
  }

  // ---------------------------------------------------------------- labels
  const labels = [];
  // ---- the grass. An instanced field of tufts (two crossed quads wearing the painted tuft
  // sprite, alpha-cut, lit with the ground's own up normal so they sit in the meadow instead
  // of standing on it) sown on the park and lawn rings within GRASS_R of the camera, re-sown
  // as the camera moves, a few thousand a frame so nothing hitches; they sway in the vertex
  // shader on the water's clock and darken under the cloud field. Desktop 28k, touch 9k.
  const GRASS_N = isTouch ? 9000 : 28000, GRASS_R = isTouch ? 140 : 160;
  // the bare ground sows too (Round 52): outside the core the meadow beside a park is the same
  // ground cover, so a park in a tuft field beside a bare meadow would still show its boundary.
  // A second source, the disc outside CORE_EXT, at this share of the park density; samples on a
  // park (it sows itself), a road, the water or a sports-complex lot are rejected. There is no
  // building test outside the core (colGrid is core-only): a tuft inside a closed building is
  // invisible, one at a wall base pokes a blade through, accepted
  const BARE_TUFT_W = 0.4;
  let grassMesh = null, grassAt = null, grassQueue = [], grassCursor = 0, grassBusy = false, grassNear = [], noSowNear = [];
  const grassPolyBB = [];
  function bareGroundAt(x, z) {
    if (inCore(x, z)) return false;
    for (const pi of grassNear) { const bb = grassPolyBB[pi]; if (x >= bb[0] && x <= bb[1] && z >= bb[2] && z <= bb[3] && pointInPoly(x, z, GRASS_POLYS[pi])) return false; }
    for (const li of noSowNear) { const bb = NO_SOW_RING_BB[li]; if (x >= bb[0] && x <= bb[1] && z >= bb[2] && z <= bb[3] && pointInPoly(x, z, NO_SOW_RINGS[li])) return false; }
    return true;
  }
  function grassInit() {
    if (!GRASS_POLYS.length) return;
    for (const pg of GRASS_POLYS) grassPolyBB.push(bboxOf(pg));
    const pos = [], nor = [], uv = [];
    const quad = (ang) => {   // one unit card, 1 m wide and tall, rooted at the origin, in the local frame
      const c = Math.cos(ang), s2 = Math.sin(ang), w = 0.5;
      const v = [[-w * c, 0, -w * s2], [w * c, 0, w * s2], [w * c, 1, w * s2], [-w * c, 1, -w * s2]];
      const t = [[0, 0], [1, 0], [1, 1], [0, 1]];
      for (const k of [0, 1, 2, 0, 2, 3]) { pos.push(v[k][0], v[k][1], v[k][2]); nor.push(0, 1, 0); uv.push(t[k][0], t[k][1]); }
    };
    quad(0); quad(Math.PI / 2);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
    g.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(nor), 3));
    g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(uv), 2));
    g.boundingSphere = new THREE.Sphere(new V3(0, 0, 0), 1e6);
    const mat = new THREE.MeshStandardMaterial({ map: tuftTex, alphaTest: 0.4, roughness: 0.95, side: THREE.DoubleSide, vertexColors: false });
    mat.onBeforeCompile = (sh) => {
      sh.uniforms.uTime = waterU.uTime;
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nuniform float uTime;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\n{\n  vec4 gw = instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0);\n  float ph = gw.x * 0.31 + gw.z * 0.23;\n  float sw = sin(uTime * 1.7 + ph) * 0.55 + sin(uTime * 3.1 + ph * 2.7) * 0.3;\n  float up = position.y * position.y;\n  transformed.x += sw * 0.28 * up; transformed.z += sw * 0.12 * up;\n}');
      cloudShadowPatch(sh, 'cameraPosition - vViewPosition * mat3(viewMatrix)');
    };
    grassMesh = new THREE.InstancedMesh(g, mat, GRASS_N);
    grassMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    grassMesh.frustumCulled = false;
    grassMesh.castShadow = false; grassMesh.receiveShadow = true;
    grassMesh.count = 0;
    groupCity.add(grassMesh);
    const zero = new THREE.Matrix4().makeScale(0, 0, 0);
    for (let i = 0; i < GRASS_N; i++) grassMesh.setMatrixAt(i, zero);
    grassMesh.instanceMatrix.needsUpdate = true;
  }
  const _gm = new THREE.Matrix4(), _gq = new THREE.Quaternion(), _gv = new V3(), _gs = new V3(), _gc = new THREE.Color(), _gWhite = new THREE.Color(1, 1, 1);
  function grassSow(cx, cz) {
    // the polygons in reach, each weighted by the area of its box inside the circle
    grassQueue = []; grassNear = [];
    let wsum = 0;
    for (let i = 0; i < GRASS_POLYS.length; i++) {
      const bb = grassPolyBB[i];
      if (bb[0] > cx + GRASS_R || bb[1] < cx - GRASS_R || bb[2] > cz + GRASS_R || bb[3] < cz - GRASS_R) continue;
      grassNear.push(i);
      const x0 = Math.max(bb[0], cx - GRASS_R), x1 = Math.min(bb[1], cx + GRASS_R), z0 = Math.max(bb[2], cz - GRASS_R), z1 = Math.min(bb[3], cz + GRASS_R);
      const w = Math.max(0, x1 - x0) * Math.max(0, z1 - z0);
      if (w < 4) continue;
      grassQueue.push([i, x0, x1, z0, z1, w]); wsum += w;
    }
    {   // the bare ground: the disc's box less its overlap with the core, weighted down
      const x0 = cx - GRASS_R, x1 = cx + GRASS_R, z0 = cz - GRASS_R, z1 = cz + GRASS_R;
      noSowNear = [];
      for (let li = 0; li < NO_SOW_RINGS.length; li++) { const bb = NO_SOW_RING_BB[li]; if (bb[0] <= x1 && bb[1] >= x0 && bb[2] <= z1 && bb[3] >= z0) noSowNear.push(li); }
      const ix = Math.max(0, Math.min(x1, CORE_EXT.x1) - Math.max(x0, CORE_EXT.x0)), iz = Math.max(0, Math.min(z1, CORE_EXT.z1) - Math.max(z0, CORE_EXT.z0));
      const w = ((x1 - x0) * (z1 - z0) - ix * iz) * BARE_TUFT_W;
      if (w >= 4) { grassQueue.push([-1, x0, x1, z0, z1, w]); wsum += w; }
    }
    for (const qn of grassQueue) qn[5] = Math.max(8, Math.round(GRASS_N * qn[5] / Math.max(1, wsum) * 1.3));
    grassCursor = 0; grassBusy = true;
    grassAt = [cx, cz];
  }
  function grassStep() {
    if (!grassMesh || !grassBusy) return;
    let placed = 0, budget = 5000, k = grassCursor;
    const [cx, cz] = grassAt;
    const tEnd = performance.now() + 2.5;   // a sow spreads over frames, never over one
    while (grassQueue.length && budget > 0 && k < GRASS_N && performance.now() < tEnd) {
      const qn = grassQueue[0];
      const pg = qn[0] >= 0 ? GRASS_POLYS[qn[0]] : null;   // null: the bare-ground source
      let tries = 0;
      while (qn[5] > 0 && budget > 0 && k < GRASS_N && tries < 4) {
        qn[5]--; budget--; tries++;
        const x = qn[1] + Math.random() * (qn[2] - qn[1]), z = qn[3] + Math.random() * (qn[4] - qn[3]);
        const dx = x - cx, dz = z - cz, d2 = dx * dx + dz * dz;
        if (d2 > GRASS_R * GRASS_R) continue;
        if (pg ? !pointInPoly(x, z, pg) : !bareGroundAt(x, z)) continue;
        if (septaSnapRoad(x, z, 4)) continue;
        if (inWater(x, z) > -2) continue;
        // on the drawn ground where a grid is registered (the sheets conform to it), drapeY in the core
        const y = (groundMeshY(x, z) ?? drapeY(x, z, 'ground')) + (pg ? LAYER.park : 0) + 0.02;
        const dd = Math.sqrt(d2), fade = 1 - smooth(GRASS_R * 0.55, GRASS_R, dd);
        if (Math.random() < smooth(10, 45, camera.position.y - y)) continue;   // seen from height the tufts thin out, the meadow carries the read
        if (Math.random() > 0.3 + 0.7 * fade) continue;   // toward the rim the field thins rather than shrinks
        // a bare tuft tops out under 0.295, the lowest street lift: the road reject is 4 m from the
        // centreline, so the shoulders of a wide street (and a runway) take bare tufts under the asphalt
        const h = (pg ? 0.16 + Math.random() * 0.2 : 0.12 + Math.random() * 0.14) * (0.8 + 0.2 * fade);
        _gq.setFromAxisAngle(_sup, Math.random() * Math.PI * 2);
        _gs.set(0.65 + Math.random() * 0.5, h, 0.65 + Math.random() * 0.5);
        _gm.compose(_gv.set(x, y, z), _gq, _gs);
        grassMesh.setMatrixAt(k, _gm);
        // a tint on the painted tuft: hue drift, normalised on green, eased to white
        _gc.setHSL(0.24 + (Math.random() - 0.5) * 0.05, 0.5, 0.5);
        _gc.multiplyScalar(1 / Math.max(0.05, _gc.g)).lerp(_gWhite, 0.6).multiplyScalar(0.9 + Math.random() * 0.35);
        grassMesh.setColorAt(k, _gc);
        k++; placed++; tries = 0;
      }
      if (qn[5] <= 0) grassQueue.shift();
    }
    const zero = _gm.makeScale(0, 0, 0);
    if (!grassQueue.length || k >= GRASS_N) {
      for (let i = k; i < grassMesh.count; i++) grassMesh.setMatrixAt(i, zero);
      grassMesh.count = k; grassBusy = false;
    } else if (k > grassMesh.count) grassMesh.count = k;
    grassCursor = k;
    grassMesh.instanceMatrix.needsUpdate = true;
    if (grassMesh.instanceColor) grassMesh.instanceColor.needsUpdate = true;
  }
  function grassUpdate() {
    if (!grassMesh) return;
    const p = camera.position;
    // from 90 m up every tuft is rejected anyway: no sow, no field, sow again on the way down
    if (p.y - drapeY(p.x, p.z, 'ground') > 90) { if (grassMesh.count) grassMesh.count = 0; grassBusy = false; grassAt = null; return; }
    if (!grassAt || Math.hypot(p.x - grassAt[0], p.z - grassAt[1]) > 70) { if (!grassBusy || Math.hypot(p.x - grassAt[0], p.z - grassAt[1]) > 140) grassSow(p.x, p.z); }
    grassStep();
  }
  step('Sowing the grass', grassInit);
  step('Lettering the landmarks', () => {
    function addLabel(text, x, y, z, cls) {
      const el = document.createElement('div');
      el.className = 'lbl' + (cls ? ' ' + cls : '');
      el.textContent = text;
      labelsRoot.appendChild(el);
      labels.push({ el, pos: new V3(x, y + siteY(x, z, 'ground'), z), visible: false });
    }
    const wanted = [
      ["Saint Peter's Church", "St. Peter's Church"],
      ['Old Pine Street Church', 'Old Pine Street Church'],
      ["Merchants' Exchange", "Merchants' Exchange"],
      ['Head House', 'Head House Square'],
      ['Mother Bethel', 'Mother Bethel A.M.E.'],
      ['Hopkinson House', 'Hopkinson House'],
      ['Society Hill Synagogue', 'Society Hill Synagogue'],
      ['Old Saint Mary', "Old St. Mary's"],
      ['City Tavern', 'City Tavern'],
      ['Hill-Physick', 'Physick House'],
      ['Athenaeum', 'Athenaeum'],
      ['Residences at Dockside', 'Dockside'],
      ['One Independence Place', 'Independence Place'],
      ['The Ryland', 'The Ryland, 1 Dock Street'],
      ['Philadelphia Marriott Old City', 'Marriott Old City'],
      ['Independence Seaport Museum', 'Seaport Museum'],
    ];
    for (const [pat, text] of wanted) {
      const b = findBuilding(pat);
      if (!b) continue;
      const [cx, cz] = polyCentroid(b.poly);
      let h = b.h + 7;
      const lm = META_L.find(l => l.name && l.name.toLowerCase().includes(pat.toLowerCase().slice(0, 8)));
      if (lm && lm.spire_height_m) h = Math.max(h, lm.spire_height_m + 6);
      addLabel(text, cx, h, cz);
    }
    // (the towers carried address labels here; removed at Mike's request)
    const riv = waterPoint(0, 210);
    addLabel('Delaware River', riv[0], 12, riv[1], '');
    const pl = waterPoint(-230, -45);
    addLabel("Penn's Landing", pl[0], 10, pl[1], '');
  });

  let labelsOn = false;   // landmark tags start hidden; Aa button / L key turn them on
  const tmpV = new V3();
  function updateLabels() {
    const w = window.innerWidth, h = window.innerHeight;
    for (const l of labels) {
      if (!labelsOn) { if (l.visible) { l.el.style.opacity = '0'; l.visible = false; } continue; }
      tmpV.copy(l.pos).project(camera);
      const dist = camera.position.distanceTo(l.pos);
      const behind = tmpV.z > 1 || tmpV.z < -1;
      const off = tmpV.x < -1.05 || tmpV.x > 1.05 || tmpV.y < -1.1 || tmpV.y > 1.1;
      const f0 = l.far ? 4200 : LABEL_FADE[0], f1 = l.far ? 6800 : LABEL_FADE[1];
      let op = 1 - clamp((dist - f0) / (f1 - f0), 0, 1);
      if (dist < 26) op = Math.min(op, (dist - 12) / 14);
      if (behind || off || op <= 0.02) {
        if (l.visible) { l.el.style.opacity = '0'; l.visible = false; }
        continue;
      }
      const x = (tmpV.x * 0.5 + 0.5) * w, y = (-tmpV.y * 0.5 + 0.5) * h;
      l.el.style.transform = 'translate(-50%,-100%) translate(' + x.toFixed(1) + 'px,' + y.toFixed(1) + 'px)';
      l.el.style.opacity = op.toFixed(2);
      l.visible = true;
    }
  }

  // ---------------------------------------------------------------- controls
  const MODE = { ORBIT: 0, WALK: 1, FLY: 2 };
  let mode = MODE.ORBIT;
  let introSpin = true; // the attract loop: spins behind the veil and keeps
                        // spinning after Enter, until the first interaction
                        // hands the controls over to fly mode
  let orbitSpin = false;   // a search result circles its spot (orbitAround) until the first input takes flight

  const orbit = {
    // the veil shows Center City whole from high in the east; Enter glides in
    // to a slow circle of City Hall, and the first touch takes flight from
    // wherever the circle happens to be. Orbit is no longer a selectable mode.
    target: new V3(-1603, 78, -802), goalTarget: new V3(-1603, 78, -802),
    r: 3400, goalR: 2600,
    theta: -0.38, goalTheta: 0.52, // azimuth on xz: 0 = +x (east)
    phi: 1.32, goalPhi: 1.22,      // polar from +y
  };
  applyOrbit(0);   // place the camera NOW: the mid-build veil renders must show
                   // the wide Center City shot, not the default pose at the
                   // towers' origin (the old "loads on SHT, then cuts" glitch)
  const walk = {
    pos: new V3(0, 1.7, 0),
    yaw: 0, pitch: 0,
    vel: new V3(),
    keys: {},
    locked: false,
    dragLook: false,
  };
  // fly mode shares walk's look state (yaw/pitch/keys) but moves freely in 3D
  const fly = { pos: new V3(0, 260, 420), vel: new V3(), speed: 90 };

  function applyOrbit(dt) {
    const k = 1 - Math.exp(-dt * 5.2);
    orbit.r = lerp(orbit.r, orbit.goalR, k);
    orbit.theta = lerp(orbit.theta, orbit.goalTheta, k);
    orbit.phi = lerp(orbit.phi, orbit.goalPhi, k);
    orbit.target.lerp(orbit.goalTarget, k);
    const sp = Math.sin(orbit.phi), cp = Math.cos(orbit.phi);
    camera.position.set(
      orbit.target.x + orbit.r * sp * Math.cos(orbit.theta),
      orbit.target.y + orbit.r * cp,
      orbit.target.z + orbit.r * sp * Math.sin(orbit.theta)
    );
    if (orbitSpin) limitV(camera.position);   // a search circle near the edge slides along the limit instead of crossing it
    camera.lookAt(orbit.target);
  }

  const _wf = new V3(), _wr = new V3(), _wish = new V3(), _wtmp = new V3();
  function applyWalk(dt) {
    const speed = walk.keys['shift'] ? 9.5 : 3.6;
    const f = _wf.set(Math.sin(walk.yaw), 0, -Math.cos(walk.yaw));  // yaw 0 -> north (-z)
    const r = _wr.set(-f.z, 0, f.x);
    const wish = _wish.set(0, 0, 0);
    if (walk.keys['w'] || walk.keys['arrowup']) wish.add(f);
    if (walk.keys['s'] || walk.keys['arrowdown']) wish.sub(f);
    if (walk.keys['d'] || walk.keys['arrowright']) wish.add(r);
    if (walk.keys['a'] || walk.keys['arrowleft']) wish.sub(r);
    if (joy.active) { wish.add(_wtmp.copy(f).multiplyScalar(-joy.y)).add(_wtmp.copy(r).multiplyScalar(joy.x)); }
    if (wish.lengthSq() > 0) {
      wish.normalize().multiplyScalar(speed);
      walk.vel.x = lerp(walk.vel.x, wish.x, 1 - Math.exp(-dt * 9));
      walk.vel.z = lerp(walk.vel.z, wish.z, 1 - Math.exp(-dt * 9));
    } else {
      const d = Math.exp(-dt * 8);
      walk.vel.x *= d; walk.vel.z *= d;
    }
    let nx = walk.pos.x + walk.vel.x * dt;
    let nz = walk.pos.z + walk.vel.z * dt;
    // collide with building edges: push out
    for (let iter = 0; iter < 2; iter++) {
      const gx = Math.floor(nx / COL_CELL), gz = Math.floor(nz / COL_CELL);
      for (let ix = gx - 1; ix <= gx + 1; ix++) for (let iz = gz - 1; iz <= gz + 1; iz++) {
        const a = colGrid.get(colKey(ix, iz));
        if (!a) continue;
        for (const s of a) {
          const ax = colSegs[s], az = colSegs[s + 1], bx = colSegs[s + 2], bz = colSegs[s + 3];
          const dx = bx - ax, dz = bz - az;
          const L2 = dx * dx + dz * dz;
          let t = L2 > 0 ? ((nx - ax) * dx + (nz - az) * dz) / L2 : 0;
          t = clamp(t, 0, 1);
          const px = nx - (ax + dx * t), pz = nz - (az + dz * t);
          const d2 = px * px + pz * pz;
          const R = 0.55;
          if (d2 < R * R && d2 > 1e-9) {
            const d = Math.sqrt(d2);
            nx += (px / d) * (R - d);
            nz += (pz / d) * (R - d);
          }
        }
      }
    }
    const wd = inWater(nx, nz);
    if (wd > -2) nx -= (wd + 2);
    nx = clamp(nx, bounds.minX - 60, bounds.maxX + 200);
    nz = clamp(nz, bounds.minZ - 60, bounds.maxZ + 60);
    { const c = clampLimit(nx, nz); if (c) { nx = c[0]; nz = c[1]; } }
    walk.pos.x = nx; walk.pos.z = nz;
    walk.pos.y = walkY(nx, nz) + 1.7;
    camera.position.copy(walk.pos);
    const cp = Math.cos(walk.pitch);
    camera.lookAt(
      walk.pos.x + Math.sin(walk.yaw) * cp,
      walk.pos.y + Math.sin(walk.pitch),
      walk.pos.z - Math.cos(walk.yaw) * cp
    );
  }

  function applyFly(dt) {
    const boost = walk.keys['shift'] ? 3.2 : 1;
    const cp0 = Math.cos(walk.pitch);
    const f = _wf.set(Math.sin(walk.yaw) * cp0, Math.sin(walk.pitch), -Math.cos(walk.yaw) * cp0);
    const r = _wr.set(Math.cos(walk.yaw), 0, Math.sin(walk.yaw));
    const wish = _wish.set(0, 0, 0);
    if (walk.keys['w'] || walk.keys['arrowup']) wish.add(f);
    if (walk.keys['s'] || walk.keys['arrowdown']) wish.sub(f);
    if (walk.keys['d'] || walk.keys['arrowright']) wish.add(r);
    if (walk.keys['a'] || walk.keys['arrowleft']) wish.sub(r);
    if (walk.keys['e'] || walk.keys[' '] || flyTouch.up) wish.y += 1;
    if (walk.keys['q'] || walk.keys['c'] || flyTouch.down) wish.y -= 1;
    if (joy.active) wish.add(_wtmp.copy(f).multiplyScalar(-joy.y)).add(_wtmp.copy(r).multiplyScalar(joy.x));
    if (wish.lengthSq() > 0) {
      // on touch the stick doubles as the throttle: past the ring it pushes to
      // ~2.4x cruise, so mobile can actually cross the city (no scroll wheel)
      const jm = joy.active ? Math.max(0.3, Math.min(2.4, Math.hypot(joy.x, joy.y))) : 1;
      wish.normalize().multiplyScalar(fly.speed * boost * jm);
      fly.vel.lerp(wish, 1 - Math.exp(-dt * 6));
    } else {
      fly.vel.multiplyScalar(Math.exp(-dt * 5));
    }
    fly.pos.addScaledVector(fly.vel, dt);
    fly.pos.x = clamp(fly.pos.x, bounds.minX - 400, bounds.maxX + 600);
    fly.pos.z = clamp(fly.pos.z, bounds.minZ - 400, bounds.maxZ + 400);
    limitV(fly.pos);
    const floorY = Math.max(siteY(fly.pos.x, fly.pos.z, 'ground') + 2.5, TERRAIN.water + 2);
    fly.pos.y = clamp(fly.pos.y, floorY, 1600);
    camera.position.copy(fly.pos);
    const cp = Math.cos(walk.pitch);
    camera.lookAt(
      fly.pos.x + Math.sin(walk.yaw) * cp,
      fly.pos.y + Math.sin(walk.pitch),
      fly.pos.z - Math.cos(walk.yaw) * cp
    );
  }

  // pointer / touch input
  let dragging = false, dragBtn = 0, lastX = 0, lastY = 0, interacted = false, touchArmed = false;
  let panelTap = false;   // the current press began with a bottom panel open
  window.addEventListener('pointerup', () => { panelTap = false; });   // (after the canvas handler consumed it)
  window.addEventListener('pointercancel', () => { panelTap = false; });
  const joy = { active: false, id: -1, ox: 0, oy: 0, x: 0, y: 0 };
  const lookTouch = { id: -1, x: 0, y: 0 };
  const pinch = { d: 0, x: 0, y: 0 };

  canvas.addEventListener('pointerdown', (e) => {
    if (e.pointerType === 'touch') return; // touch handled separately
    // a press with a panel open waits: a tap only dismisses the panel (pointerup),
    // a drag flies as any press would (pointermove)
    panelTap = !!openPanelName();
    if (!panelTap) { interacted = true; introSpin = false; autoFly(); }
    if (mode === MODE.WALK || mode === MODE.FLY) {
      // always start a drag so looking works even where pointer lock is
      // unavailable (sandboxed iframes) or on cooldown; lock upgrades it
      dragging = true; lastX = e.clientX; lastY = e.clientY;
      canvas.setPointerCapture(e.pointerId);
      if (!walk.locked && !panelTap) requestLock();
      return;
    }
    dragging = true; dragBtn = e.button;
    lastX = e.clientX; lastY = e.clientY;
    canvas.setPointerCapture(e.pointerId);
  });
  window.addEventListener('pointermove', (e) => {
    if (e.pointerType === 'touch') return;
    if (panelTap && dragging && Math.hypot(e.clientX - vpDownX, e.clientY - vpDownY) > 8) {
      // the press over an open panel became a drag: fly as a plain press would have
      panelTap = false; interacted = true; introSpin = false; autoFly();
      dragging = true; lastX = e.clientX; lastY = e.clientY;
    }
    if (mode === MODE.WALK || mode === MODE.FLY) {
      if (walk.locked) return; // movementX path
      if (dragging) {
        walk.yaw += (e.clientX - lastX) * 0.0032;
        walk.pitch = clamp(walk.pitch - (e.clientY - lastY) * 0.0032, -1.45, 1.45);
        lastX = e.clientX; lastY = e.clientY;
      }
      return;
    }
    if (!dragging) return;
    const dx = e.clientX - lastX, dy = e.clientY - lastY;
    lastX = e.clientX; lastY = e.clientY;
    if (dragBtn === 2 || dragBtn === 1 || e.shiftKey) {
      panOrbit(dx, dy);
    } else {
      orbit.goalTheta += dx * 0.0052;
      orbit.goalPhi = clamp(orbit.goalPhi - dy * 0.0042, 0.06, 1.52);
    }
  });
  window.addEventListener('pointerup', () => { dragging = false; });
  canvas.addEventListener('contextmenu', (e) => e.preventDefault());
  canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    interacted = true; introSpin = false;
    autoFly();
    if (mode === MODE.FLY) { fly.speed = clamp(fly.speed * Math.exp(-e.deltaY * 0.0012), 10, 500); return; }
    if (mode !== MODE.ORBIT) return;
    orbit.goalR = clamp(orbit.goalR * Math.exp(e.deltaY * 0.0011), 14, 2800);
  }, { passive: false });

  function panOrbit(dx, dy) {
    const s = orbit.goalR * 0.0012;
    const fx = Math.cos(orbit.theta), fz = Math.sin(orbit.theta);
    // grab-style pan: the world follows the cursor.
    // ground-projected screen axes: right = (fz, -fx), up = (-fx, -fz)
    orbit.goalTarget.x += (-fz * dx - fx * dy) * s;
    orbit.goalTarget.z += (fx * dx - fz * dy) * s;
    orbit.goalTarget.x = clamp(orbit.goalTarget.x, bounds.minX - 200, bounds.maxX + 400);
    orbit.goalTarget.z = clamp(orbit.goalTarget.z, bounds.minZ - 200, bounds.maxZ + 200);
    limitV(orbit.goalTarget);
  }

  canvas.addEventListener('dblclick', (e) => {
    if (mode !== MODE.ORBIT) return;
    const ray = new THREE.Raycaster();
    ray.setFromCamera(new THREE.Vector2(
      (e.clientX / window.innerWidth) * 2 - 1,
      -(e.clientY / window.innerHeight) * 2 + 1
    ), camera);
    const hits = ray.intersectObjects(rayTargets, false);
    if (hits.length) {
      const p = hits[0].point;
      orbit.goalTarget.set(p.x, Math.max(4, Math.min(p.y, 60)), p.z);
      orbit.goalR = Math.max(60, orbit.goalR * 0.55);
    }
  });

  // touch
  canvas.addEventListener('touchstart', (e) => {
    panelTap = e.touches.length === 1 && !!openPanelName();   // tap dismisses, drag flies (see pointerdown)
    if (!panelTap) { interacted = true; introSpin = false; autoFly(); }
    if (mode === MODE.WALK || mode === MODE.FLY) {
      for (const t of e.changedTouches) {
        if (t.clientX < window.innerWidth / 2 && !joy.active) {
          joy.active = true; joy.id = t.identifier; joy.ox = t.clientX; joy.oy = t.clientY; joy.x = joy.y = 0;
          stick.style.display = 'block';
          const pr = padL.getBoundingClientRect();   // the stick docks on the Move pad; the drag is relative to the finger either way
          if (pr.width > 0) { stick.style.left = (pr.left + pr.width / 2 - 54) + 'px'; stick.style.top = (pr.top + pr.height / 2 - 54) + 'px'; padL.classList.add('active'); }
          else { stick.style.left = (t.clientX - 54) + 'px'; stick.style.top = (t.clientY - 54) + 'px'; }
        } else if (lookTouch.id === -1) {
          lookTouch.id = t.identifier; lookTouch.x = t.clientX; lookTouch.y = t.clientY;
          padR.classList.add('active');
        }
      }
      e.preventDefault();
      return;
    }
    if (e.touches.length === 1) {
      const t = e.touches[0];
      lastX = t.clientX; lastY = t.clientY; touchArmed = true;
    } else if (e.touches.length === 2) {
      const [a, b] = e.touches;
      pinch.d = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
      pinch.x = (a.clientX + b.clientX) / 2; pinch.y = (a.clientY + b.clientY) / 2;
    }
    e.preventDefault();
  }, { passive: false });
  canvas.addEventListener('touchmove', (e) => {
    if (panelTap) {
      const t = e.touches[0];
      if (t && Math.hypot(t.clientX - vpDownX, t.clientY - vpDownY) > 8) { panelTap = false; interacted = true; introSpin = false; autoFly(); }
    }
    if (mode === MODE.WALK || mode === MODE.FLY) {
      for (const t of e.changedTouches) {
        if (t.identifier === joy.id) {
          const dx = t.clientX - joy.ox, dy = t.clientY - joy.oy;
          // magnitude runs past the ring to 2.4 — fly reads it as a throttle;
          // walk normalizes the vector so its speed is unaffected
          const m = Math.min(2.4, Math.hypot(dx, dy) / 44);
          const a = Math.atan2(dy, dx);
          joy.x = Math.cos(a) * m; joy.y = Math.sin(a) * m;
          const vis = Math.min(1, m);
          stickNub.style.transform = 'translate(' + (Math.cos(a) * vis * 30) + 'px,' + (Math.sin(a) * vis * 30) + 'px)';
        } else if (t.identifier === lookTouch.id) {
          walk.yaw += (t.clientX - lookTouch.x) * 0.0042;
          walk.pitch = clamp(walk.pitch - (t.clientY - lookTouch.y) * 0.0042, -1.45, 1.45);
          lookTouch.x = t.clientX; lookTouch.y = t.clientY;
        }
      }
      e.preventDefault();
      return;
    }
    if (e.touches.length === 1) {
      const t = e.touches[0];
      if (!touchArmed) { touchArmed = true; lastX = t.clientX; lastY = t.clientY; return; }
      orbit.goalTheta += (t.clientX - lastX) * 0.006;
      orbit.goalPhi = clamp(orbit.goalPhi - (t.clientY - lastY) * 0.005, 0.06, 1.52);
      lastX = t.clientX; lastY = t.clientY;
    } else if (e.touches.length === 2) {
      const [a, b] = e.touches;
      const d = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
      if (pinch.d > 0) orbit.goalR = clamp(orbit.goalR * (pinch.d / d), 14, 2800);
      const cx = (a.clientX + b.clientX) / 2, cy = (a.clientY + b.clientY) / 2;
      panOrbit(cx - pinch.x, cy - pinch.y);
      pinch.d = d; pinch.x = cx; pinch.y = cy;
    }
    e.preventDefault();
  }, { passive: false });
  function onTouchEnd(e) {
    for (const t of e.changedTouches) {
      if (t.identifier === joy.id) { joy.active = false; joy.id = -1; joy.x = joy.y = 0; stick.style.display = 'none'; stickNub.style.transform = ''; padL.classList.remove('active'); }
      if (t.identifier === lookTouch.id) { lookTouch.id = -1; padR.classList.remove('active'); }
    }
    if (e.touches.length < 2) pinch.d = 0;
    if (e.touches.length === 1) { lastX = e.touches[0].clientX; lastY = e.touches[0].clientY; }
  }
  canvas.addEventListener('touchend', onTouchEnd);
  canvas.addEventListener('touchcancel', onTouchEnd);

  // pointer lock (dragLook only informs the hint text; dragging always works)
  function requestLock() {
    try {
      const p = canvas.requestPointerLock && canvas.requestPointerLock();
      if (p && p.catch) p.catch(() => { walk.dragLook = true; setHint(); });
    } catch (e) { walk.dragLook = true; setHint(); }
  }
  document.addEventListener('pointerlockchange', () => {
    walk.locked = document.pointerLockElement === canvas;
    if (walk.locked) walk.dragLook = false;
    setHint();
  });
  document.addEventListener('pointerlockerror', () => { walk.dragLook = true; setHint(); });
  document.addEventListener('mousemove', (e) => {
    if (!walk.locked || (mode !== MODE.WALK && mode !== MODE.FLY)) return;
    if (glide) glideCancel();   // a locked-mouse look is input too
    walk.yaw += e.movementX * 0.0021;
    walk.pitch = clamp(walk.pitch - e.movementY * 0.0021, -1.45, 1.45);
  });

  window.addEventListener('keydown', (e) => {
    const k = e.key.toLowerCase();
    if (e.metaKey || e.ctrlKey || e.altKey) return;   // browser chords (Cmd+F, Ctrl+P, Cmd+A) are not layer hotkeys
    if (k === 'escape') {
      // ahead of the field guard: Escape must work from a panel's own buttons and inputs
      if (flyTips && flyTips.classList.contains('show')) { hideFlyTips(); return; }
      if (openPanelName() === 'search') septaSetFilter(null);   // Escape on the search panel drops the route filter too
      if (closePanels()) return;
    }
    const tag = e.target && e.target.tagName;
    if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return;
    // a focused HUD button keeps Space/Enter (its own activation); every other
    // key is a shortcut. Bailing on ANY key from a BUTTON left W A S D dead after
    // every mouse click on the HUD until the user happened to click the canvas.
    if ((k === ' ' || k === 'enter') && tag !== 'BODY' && tag !== 'CANVAS' && tag !== 'HTML') return;   // a focused control keeps its own activation keys
    if (!veil.classList.contains('hidden')) return;      // no shortcuts under the intro veil
    if (about.classList.contains('open')) {              // panel gets the keyboard while open
      if (k === 'escape' || k === 'i') closeAbout();
      return;
    }
    if (k === 'l') toggleLabels();
    else if (k === 't') toggleTimePanel();
    else if (k === 'v') toggleTransit();
    else if (k === 'n') toggleStreets();
    else if (k === 'f') toggleLayers();
    else if (k === 'b') toggleIndego();
    else if (k === 'x') toggleFlights();
    else if (k === 'h') toggleShips();
    else if (k === 'p') togglePlaces();
    else if (k === 'r') toggleTraffic();
    else if (k === 'g') toggleLightsLayer();
    else if (k === '/') { toggleSearch(true); e.preventDefault(); }   // the local name index works everywhere
    else if (k === 'escape') { glideCancel(); /* nothing open: the browser releases pointer lock */ }
    else {
      // a movement key is as clear an intent to fly as a drag is
      if (['w', 'a', 's', 'd', 'e', 'q', ' '].includes(k) || k.indexOf('arrow') === 0) { interacted = true; introSpin = false; autoFly(); }
      walk.keys[k] = true;
    }
    if (['w', 'a', 's', 'd', ' ', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(k)) e.preventDefault();
  });
  window.addEventListener('keyup', (e) => { walk.keys[e.key.toLowerCase()] = false; });
  window.addEventListener('blur', () => { walk.keys = {}; dragging = false; });
  // a mouse click parks focus on the button it hit (Chrome, Edge, non-Mac
  // Firefox), so the keyboard stays with the HUD; drop it after a real click.
  // detail === 0 is keyboard activation, which keeps its focus ring.
  document.addEventListener('click', (e) => {
    if (e.detail > 0 && e.target && e.target.closest) { const b = e.target.closest('button'); if (b) b.blur(); }
  });

  // ---------------------------------------------------------------- modes & viewpoints
  const flyCtl = document.getElementById('flyctl');
  const flyTouch = { up: false, down: false };
  function setHint() {
    if (mode === MODE.ORBIT) {
      // the attract loop's only job is to invite the first touch
      hintEl.textContent = isTouch
        ? 'Touch the city to take flight.'
        : 'Drag, scroll, or press W A S D to take flight.';
    } else if (mode === MODE.FLY) {
      if (isTouch) hintEl.textContent = 'Left thumb flies, push farther for faster. Right thumb looks. ▲▼ climb.';
      else if (walk.locked || walk.dragLook) hintEl.textContent = 'WASD to fly. E and Q for up and down. Shift to boost. Scroll sets speed.';
      else hintEl.textContent = 'Click the scene to take the controls';
    } else {
      if (isTouch) hintEl.textContent = 'Left thumb to move. Right thumb to look.';
      else if (walk.locked) hintEl.textContent = 'WASD to move. Shift to run. Esc releases the mouse.';
      else if (walk.dragLook) hintEl.textContent = 'WASD to move. Drag to look. Shift to run.';
      else hintEl.textContent = 'Click the scene to take the controls';
    }
  }
  function setMode(m, noLock) {
    if (m === mode) return;
    const prev = mode;
    mode = m;
    introSpin = false;
    orbitSpin = false;
    // a search result flies the camera mid-typing: leave the box focused, or
    // the next keystrokes land on the layer shortcuts
    if (document.activeElement && document.activeElement.blur && document.activeElement !== searchInput) document.activeElement.blur();
    // drop any in-flight gesture so the new mode doesn't read stale coordinates
    dragging = false; touchArmed = false; pinch.d = 0;
    joy.active = false; joy.id = -1; joy.x = joy.y = 0; lookTouch.id = -1;
    stick.style.display = 'none'; stickNub.style.transform = '';
    padL.classList.remove('active'); padR.classList.remove('active');
    crosshair.style.display = (m === MODE.WALK || m === MODE.FLY) && !isTouch ? 'block' : 'none';
    flyCtl.classList.toggle('show', m === MODE.FLY && isTouch);
    document.body.classList.toggle('touchfly', m === MODE.FLY && isTouch);   // the Move and Look pads
    flyTouch.up = flyTouch.down = false;
    if (m === MODE.WALK) {
      // drop to the ground near where the camera was looking, default to the plaza
      const t = prev === MODE.FLY ? fly.pos : orbit.target;
      let px = clamp(t.x, bounds.minX, bounds.maxX), pz = clamp(t.z, bounds.minZ, bounds.maxZ);
      const wd = inWater(px, pz);
      if (wd > -10) px -= (wd + 10);
      if (!walkSpawned) {
        walk.pos.set(towersCenter.x - 8, 1.7, towersCenter.z + 16);
        walk.yaw = Math.atan2(towersCenter.x + 9 - walk.pos.x, -(towersCenter.z - 41 - walk.pos.z));
        walk.pitch = 0.32;
        walkSpawned = true;
      } else if (Math.hypot(px - walk.pos.x, pz - walk.pos.z) > 220) {
        walk.pos.set(px, 1.7, pz);
      }
      if (!isTouch && !noLock) requestLock();
    } else if (m === MODE.FLY) {
      // take off from the current camera pose
      camera.getWorldDirection(tmpV);
      walk.yaw = Math.atan2(tmpV.x, -tmpV.z);
      walk.pitch = clamp(Math.asin(clamp(tmpV.y, -1, 1)), -1.45, 1.45);
      fly.pos.copy(camera.position);
      fly.pos.x = clamp(fly.pos.x, bounds.minX - 400, bounds.maxX + 600);
      fly.pos.z = clamp(fly.pos.z, bounds.minZ - 400, bounds.maxZ + 400);
      limitV(fly.pos);
      fly.pos.y = clamp(Math.max(fly.pos.y, siteY(fly.pos.x, fly.pos.z, 'ground') + (prev === MODE.WALK ? 35 : 6)), TERRAIN.water + 2, 1600);
      fly.vel.set(0, 0, 0);
      if (!isTouch && !noLock) requestLock();
    } else {
      if (walk.locked && document.exitPointerLock) document.exitPointerLock();
      const p = prev === MODE.FLY ? fly.pos : walk.pos;
      orbit.goalTarget.set(p.x, prev === MODE.FLY ? Math.max(20, p.y - 120) : 20, p.z);
      orbit.goalR = Math.max(orbit.goalR, 180);
    }
    setHint();
  }
  let walkSpawned = false;
  // orbit and walk retired as user-facing modes (Round 35): no mode bar, no
  // 1/2/3 keys. Orbit remains the attract loop; walk stays reachable only via
  // the ?dev goWalk hook.
  const flyTips = document.getElementById('flytips');
  const flyTipsOk = document.getElementById('flyTipsOk');
  let flyTipsSeen = false;
  function showFlyTips() {
    flyTips.classList.add('show'); flyTipsSeen = true;
    flyTipsOk.focus();   // after setMode's blur: Enter takes Okay, Escape dismisses (keydown)
  }
  function hideFlyTips() {
    flyTipsSeen = true;
    flyTips.classList.remove('show');
    setMode(MODE.FLY);
  }
  function autoFly() {
    // the first real interaction — drag, wheel, movement key, touch — takes
    // flight from wherever the City Hall circle happens to be
    glideCancel();   // any input ends a glide and the tour
    if (mode === MODE.ORBIT) setMode(MODE.FLY);
    else if (mode !== MODE.FLY) return;
    // the touch primer follows the first touch, even when a share link skipped the orbit
    if (isTouch && !flyTipsSeen && flyTips) showFlyTips();
  }
  if (flyTips) flyTipsOk.addEventListener('click', hideFlyTips);
  // touch fly: hold ▲/▼ to climb and descend (E/Q have no finger equivalent)
  for (const [bid, key] of [['flyUp', 'up'], ['flyDown', 'down']]) {
    const b = document.getElementById(bid);
    const on = (e) => { flyTouch[key] = true; interacted = true; e.preventDefault(); };
    const off = () => { flyTouch[key] = false; };
    b.addEventListener('touchstart', on, { passive: false });
    b.addEventListener('touchend', off);
    b.addEventListener('touchcancel', off);
    b.addEventListener('mousedown', on);
    b.addEventListener('mouseup', off);
    b.addEventListener('mouseleave', off);
  }

  const viewpoints = [];
  function addViewpoint(name, fn) { viewpoints.push({ name, fn }); }
  // ---------------------------------------------------------------- camera glides & the tour
  // One eased camera move at a time, polled from frame() (no second rAF loop):
  // the 'Take me to' rows, the tour and the compass all ride it. Any real input
  // (autoFly, a locked-mouse look, Escape) cancels the glide and ends the tour.
  let glide = null;
  const TOUR_DWELL = 9000;
  const tour = { on: false, i: -1, nextT: 0 };
  const btnTour = document.getElementById('btnTour');
  const easeInOut = (t) => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  const wrapPi = (a) => ((a + Math.PI) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2) - Math.PI;
  function glideFly(px, py, pz, yaw, pitch, ms, done) {
    // fly-space glide to a pose: the yaw takes the short way round, and long
    // hops arc upward so the path clears the towers instead of threading them
    interacted = true; introSpin = false;
    setMode(MODE.FLY, true);
    const d = Math.hypot(px - fly.pos.x, pz - fly.pos.z);
    glide = { kind: 'fly', t0: performance.now(), ms, done, arc: Math.min(400, d * 0.12),
      fx: fly.pos.x, fy: fly.pos.y, fz: fly.pos.z, fyaw: walk.yaw, fpitch: walk.pitch,
      tx: px, ty: py, tz: pz, tyaw: walk.yaw + wrapPi(yaw - walk.yaw), tpitch: clamp(pitch, -1.45, 1.45) };
  }
  function faceNorth() {
    // the compass: orbit eases its azimuth to PI/2 (camera due south of the
    // target, see applyOrbit), fly and walk ease their shared yaw to 0 (applyFly)
    if (!veil.classList.contains('hidden')) return;
    glideCancel();   // a compass tap is input: it ends a tour rather than stranding it mid-glide
    interacted = true; introSpin = false; orbitSpin = false;   // and a search result's circle, or the spin would undo the turn
    const t0 = performance.now(), ms = 600;
    if (mode === MODE.ORBIT) glide = { kind: 'orbit', t0, ms, from: orbit.goalTheta, to: orbit.goalTheta + wrapPi(Math.PI / 2 - orbit.goalTheta) };
    else glide = { kind: 'yaw', t0, ms, from: walk.yaw, to: walk.yaw - wrapPi(walk.yaw) };
  }
  document.getElementById('compass').addEventListener('click', faceNorth);
  function glideCancel() { glide = null; if (tour.on) tourStop(); }
  function stepGlide(now) {
    if (!glide) return;
    const g = glide, k = easeInOut(clamp((now - g.t0) / g.ms, 0, 1));
    if (g.kind === 'orbit') orbit.goalTheta = lerp(g.from, g.to, k);
    else if (g.kind === 'yaw') walk.yaw = lerp(g.from, g.to, k);
    else {
      if (mode !== MODE.FLY) { glideCancel(); return; }   // something switched modes underneath
      fly.pos.set(lerp(g.fx, g.tx, k), lerp(g.fy, g.ty, k) + Math.sin(k * Math.PI) * g.arc, lerp(g.fz, g.tz, k));
      fly.vel.set(0, 0, 0);
      walk.yaw = lerp(g.fyaw, g.tyaw, k);
      walk.pitch = lerp(g.fpitch, g.tpitch, k);
    }
    if (k < 1) return;
    glide = null;
    if (g.kind === 'fly') updateHash(now, true);   // the link follows each landing
    if (g.done) g.done(now);
  }
  function syncTourBtn() {
    if (!btnTour) return;
    btnTour.textContent = tour.on ? 'Stop Tour' : 'Tour the City';
    btnTour.setAttribute('aria-pressed', tour.on ? 'true' : 'false');
  }
  function tourStop() {
    if (!tour.on) return;
    tour.on = false; tour.i = -1;
    syncTourBtn();
    setHint();
  }
  function tourNext(now) {
    tour.i++;
    if (tour.i >= viewpoints.length) { tourStop(); return; }
    const v = viewpoints[tour.i];
    tour.nextT = Infinity;                    // waits for the landing, then dwells
    v.fn((t) => { tour.nextT = t + TOUR_DWELL; });
    hintEl.textContent = 'City tour, stop ' + (tour.i + 1) + ' of ' + viewpoints.length + ': ' + v.name + '. Touch anything to stop.';
  }
  function tourStart() {
    if (!viewpoints.length || tour.on) return;
    closePanels();                            // the city, not the panel, is the show
    tour.on = true; tour.i = -1;
    syncTourBtn();
    tourNext(performance.now());
  }
  function stepTour(now) { if (tour.on && !glide && now >= tour.nextT) tourNext(now); }
  // ---------------------------------------------------------------- preferences, share links, panels
  // One localStorage blob (philly3d.prefs) remembers the nine layer flags and a
  // pinned clock; the URL hash carries a whole view (camera, clock, layers) and
  // wins over the blob. Every storage and history call is wrapped: sandboxed
  // frames throw. Both are read once, before build(), and the flags are seeded
  // flag-only: every step still builds its layer, so a saved-off one can come back.
  const PREFS_KEY = 'philly3d.prefs';
  // layer bitmask, low bit first (the hash's l= uses it): 1 SEPTA, 2 Indego,
  // 4 flights, 8 ships, 16 traffic, 32 streetlights, 64 street names,
  // 128 landmark labels, 256 neighborhood names
  const LAYER_KEYS = ['septa', 'indego', 'flights', 'ships', 'traffic', 'lights', 'streets', 'labels', 'places'];
  const LAYER_DEFAULTS = { septa: true, indego: true, flights: true, ships: true, traffic: true, lights: true, streets: true, labels: false, places: true };
  let prefsReady = false, prefsTimer = 0;
  let hashClock = false, clockTouched = false;   // a shared link's pinned clock is not saved until the user changes the time
  function layerFlags() {
    return { septa: SEPTA.on, indego: INDEGO.on, flights: FLIGHTS.on, ships: SHIPS.on, traffic: TRAFFIC.on, lights: LIGHTS.on, streets: stOn, labels: labelsOn, places: placesOn };
  }
  function setLayerFlags(f) {
    if ('septa' in f) SEPTA.on = !!f.septa;
    if ('indego' in f) INDEGO.on = !!f.indego;
    if ('flights' in f) FLIGHTS.on = !!f.flights;
    if ('ships' in f) SHIPS.on = !!f.ships;
    if ('traffic' in f) TRAFFIC.on = !!f.traffic;
    if ('lights' in f) LIGHTS.on = !!f.lights;
    if ('streets' in f) { stOn = !!f.streets; if (stMesh) stMesh.visible = stOn; }
    if ('labels' in f) labelsOn = !!f.labels;
    if ('places' in f) { placesOn = !!f.places; if (nbMesh) nbMesh.visible = false; }   // applyLighting re-shows it by altitude
  }
  function layerMask() { const f = layerFlags(); let m = 0; LAYER_KEYS.forEach((k, i) => { if (f[k]) m |= 1 << i; }); return m; }
  function layersFromMask(m) { const f = {}; LAYER_KEYS.forEach((k, i) => { f[k] = !!(m & (1 << i)); }); return f; }
  function syncLayerBtns() { syncTransitBtn(); syncIndegoBtn(); syncFlightsBtn(); syncShipsBtn(); syncTrafficBtn(); syncLightsBtn(); syncStreetsBtn(); syncLabelsBtn(); syncPlacesBtn(); }
  function syncLayerBtn(btn, on) {
    // every layer row: the check mark, the pressed state for readers, and the blob
    if (btn) { btn.classList.toggle('on', on); btn.setAttribute('aria-pressed', on ? 'true' : 'false'); }
    savePrefs();
  }
  function savePrefs() {
    if (!prefsReady) return;   // the init syncs run before the seed and must not clobber the blob
    clearTimeout(prefsTimer);
    prefsTimer = setTimeout(writePrefs, 500);
  }
  function writePrefs() {
    // layer flags only: the clock is never remembered (Mike: every load is the exact time
    // in Philadelphia), and only a copied link carries a pinned clock
    const o = layerFlags();
    try { localStorage.setItem(PREFS_KEY, JSON.stringify(o)); } catch (e) { }
  }
  function loadPrefs() {
    try { const s = localStorage.getItem(PREFS_KEY); return s ? JSON.parse(s) : null; } catch (e) { return null; }
  }
  function clearPrefs() {
    clearTimeout(prefsTimer);
    try { localStorage.removeItem(PREFS_KEY); } catch (e) { }
  }
  function applyClock(y, m, d, minutes) {
    if (!(y >= 1900 && y <= 2200 && m >= 1 && m <= 12 && d >= 1 && d <= 31 && minutes >= 0 && minutes <= 1439)) return false;
    clock.live = false; clock.y = y; clock.m = m; clock.d = d; clock.minutes = Math.round(minutes);
    return true;
  }
  // the share hash: #p=x,y,z,yaw,pitch&t=YYYYMMDD,minutes&l=mask (metres to 0.1,
  // radians to 0.001; t only while the clock is pinned). Anything malformed is ignored.
  function parseHash() {
    const out = {};
    try {
      for (const kv of location.hash.replace(/^#/, '').split('&')) {
        const i = kv.indexOf('=');
        if (i < 1 || i === kv.length - 1) continue;
        const k = kv.slice(0, i), v = kv.slice(i + 1).split(',').map((f) => /^-?\d+(\.\d+)?$/.test(f) ? +f : NaN);   // an empty field is malformed, not 0
        if (!v.every((n) => isFinite(n))) continue;
        if (k === 'p' && v.length === 5) out.p = v;
        else if (k === 't' && v.length === 2) out.t = v;
        else if (k === 'l' && v.length === 1) out.l = v[0] & 511;
      }
    } catch (e) { }
    return out;
  }
  function viewState(withClock) {
    camera.getWorldDirection(tmpV);
    const yaw = Math.atan2(tmpV.x, -tmpV.z), pitch = Math.asin(clamp(tmpV.y, -1, 1)), p = camera.position;
    let s = 'p=' + p.x.toFixed(1) + ',' + p.y.toFixed(1) + ',' + p.z.toFixed(1) + ',' + yaw.toFixed(3) + ',' + pitch.toFixed(3);
    // the address bar never carries the clock (a reopened tab must wake to the real time);
    // a copied link does, when it is pinned
    if (withClock && !clock.live) s += '&t=' + (clock.y * 10000 + clock.m * 100 + clock.d) + ',' + clock.minutes;
    return s + '&l=' + layerMask();
  }
  let hashT = 0, hashLast = '';
  function updateHash(now, force) {
    // replaceState only: the address bar follows the flight without growing history;
    // nothing while the veil is up or the attract loop is still circling
    if (!force && (introSpin || orbitSpin || !veil.classList.contains('hidden') || now < hashT)) return;
    hashT = now + 500;
    const s = viewState();
    if (s === hashLast) return;
    hashLast = s;
    try { history.replaceState(null, '', '#' + s); } catch (e) { }
  }
  function applyHashView(v) {
    // a shared link lands in fly mode at its exact pose: no orbit intro, no lock request
    setMode(MODE.FLY, true);
    fly.pos.set(clamp(v[0], bounds.minX - 400, bounds.maxX + 600), clamp(v[1], TERRAIN.water + 2, 1600), clamp(v[2], bounds.minZ - 400, bounds.maxZ + 400));
    limitV(fly.pos);
    fly.vel.set(0, 0, 0);
    walk.yaw = v[3]; walk.pitch = clamp(v[4], -1.45, 1.45);
    interacted = true; introSpin = false;   // Enter must not restart the circle
    applyFly(0);   // place the camera before the first render
  }
  // one bottom panel at a time: layers, search and time share the strip above the bar
  const btnTime = document.getElementById('btnTime');
  const PANEL_NAMES = ['layers', 'search', 'time'];
  function panelOf(n) { return n === 'layers' ? layersPanel : n === 'search' ? searchPanel : timePanel; }
  function panelBtn(n) { return n === 'layers' ? btnLayers : n === 'search' ? btnSearch : btnTime; }
  function openPanel(name, open) {
    const want = open !== undefined ? !!open : !panelOf(name).classList.contains('open');
    for (const n of PANEL_NAMES) {
      const el = panelOf(n), on = n === name && want;
      if (!on && el.classList.contains('open') && el.contains(document.activeElement)) document.activeElement.blur();
      el.classList.toggle('open', on);
      panelBtn(n).setAttribute('aria-expanded', on ? 'true' : 'false');
    }
    return want;
  }
  function openPanelName() { for (const n of PANEL_NAMES) if (panelOf(n).classList.contains('open')) return n; return null; }
  function closePanels() {
    const n = openPanelName();
    if (!n) return false;
    if (n === 'search') toggleSearch(false); else openPanel(n, false);   // search also cancels its query
    if (n === 'search' && SEPTA.filter) hintEl.textContent = 'Showing route ' + SEPTA.filterLabel + ' only. Turn the SEPTA layer off to clear.';
    return true;
  }

  // ---------------------------------------------------------------- live SEPTA transit
  // Real-time vehicles from SEPTA's public API. Neither api.septa.org nor www3 sends
  // CORS headers, but both honor JSONP (?callback=), so each poll is a short-lived
  // <script> tag — live on GitHub Pages / localhost; under the artifact CSP the tags
  // never load and the layer stays silently empty. STREET VEHICLES ONLY by Mike's
  // request (buses + the bus-like street trolleys): rail is skipped — the subway
  // rows (L1/B1–B3) are schedule placeholders with no real fix anyway, and the
  // Regional Rail / NHSL layer was removed 2026-08-25 ("mostly underground and
  // not easy to track"). TrainView is no longer polled.
  const SEPTA_GEO = { lat0: 39.945473644755005, lon0: -75.14474803850973 };  // scene.json origin
  SEPTA_GEO.mx = 111320 * Math.cos(SEPTA_GEO.lat0 * Math.PI / 180); SEPTA_GEO.mz = 110574;
  const SEPTA = { on: true, ok: false, fails: 0, hinted: false, busy: false, lastT: -1e9, filter: null, filterLabel: '' };   // filter: one route id on the map (a route search)
  const SEPTA_HOSTS = ['https://api.septa.org/api', 'https://www3.septa.org/api'];
  const SEPTA_POLL = isTouch ? 25000 : 15000;          // TransitViewAll is ~370 KB a pull
  // the VPS bakes TransitViewAll into a filtered, gzipped septa.json every 10 s
  // (ops/septa_bake.py): ~16 KB a pull instead of 343 KB, and one upstream
  // request a cycle however many viewers. The JSONP rotation stays as the
  // fallback whenever the file is missing or stale (baker down).
  const SEPTA_BAKED = 'https://philly3d.com/septa.json';
  // the feed's timestamps are the server's clock: judge staleness against its Date header, not the viewer's clock
  const serverNow = (r) => { const t = Date.parse(r.headers.get('date') || ''); return t > 0 ? t / 1000 : Date.now() / 1000; };
  let septaBakedOk = true, septaBakedRetryT = 0;
  function septaFetchBaked(cb) {
    const ctl = typeof AbortController !== 'undefined' ? new AbortController() : null;
    const timer = ctl ? setTimeout(() => ctl.abort(), 12000) : 0;
    const miss = () => { clearTimeout(timer); septaBakedOk = false; septaBakedRetryT = performance.now() + 300000; cb(null); };
    fetch(SEPTA_BAKED, { cache: 'no-store', signal: ctl ? ctl.signal : undefined })
      .then((r) => { if (!r.ok) throw new Error('http ' + r.status); return r.json().then((d) => ({ d, now: serverNow(r) })); })
      .then(({ d, now: sNow }) => {
        if (!d || !(d.t > 0) || sNow - d.t > 90) { miss(); return; }   // stale file: the baker is down
        clearTimeout(timer);
        cb(d);
      })
      .catch(miss);
  }
  const SEPTA_BOX = { la0: 39.855, la1: 40.145, lo0: -75.30, lo1: -74.94 };  // modeled city
  const septaCanFetch = !/claude|usercontent/i.test(location.hostname);
  const septaVeh = new Map();
  const SEPTA_KIND = {                                  // stored dark for the legacy-color lift
    bus: { l: 12.2, w: 2.6, h: 3.1, c: 0x7e858a },
    trolley: { l: 15.3, w: 2.6, h: 3.4, c: 0x2e7448 },
  };
  const SEPTA_TINT = { G1: 0x8a7f2f, D1: 0x7c4767, D2: 0x7c4767 };  // Girard gold, Delco violet
  let septaCbN = 0, septaHost = 0, septaSolid = null, septaBadge = null, septaReady = false, septaHintT = 0;
  const septaMats = {};
  const septaPickS = [], septaPickB = [];
  const btnTransit = document.getElementById('btnTransit');
  const vehinfoEl = document.getElementById('vehinfo');
  const vehinfoBody = document.getElementById('vehinfoBody');
  let pickedVeh = null;
  const septaEsc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  // upload only the live instances of a fleet mesh, not its whole buffer. three
  // resets updateRange after every upload, so a wrong count costs one full
  // upload, never a stale one. Nothing to send at count 0.
  function septaKindOf(r) {
    // rail is out by request (and the subway rows carry no real GPS anyway):
    // only street vehicles — buses and the bus-like street trolleys — render
    if (r === 'L1' || r === 'B1' || r === 'B2' || r === 'B3' || r === 'M1') return null;
    if (/^[TGD]\d$/.test(r)) return 'trolley';
    return 'bus';
  }
  function septaRouteLabel(r) {
    if (r === 'M1_BUS') return 'M1';
    if (r === 'BLVDDIR') return 'BLVD';
    if (r.indexOf('LUCY') === 0) return 'LUCY';
    return r;
  }
  // Approximate underground zone: T-trolleys inside the subway–surface tunnel
  // (40th St portals → 13th) simply aren't drawn — no vehicles under buildings.
  function septaUnder(kind, route, lat, lon) {
    if (kind === 'trolley' && route.charCodeAt(0) === 84)
      return lon > -75.2045 && lon < -75.158 && lat > 39.9465 && lat < 39.9575;
    return false;
  }
  function septaYawFromCompass(deg) {
    const r = deg * Math.PI / 180;
    return Math.atan2(Math.cos(r), Math.sin(r));   // x = east, z = south, rotY 0 = +x
  }
  function septaJsonp(path, cb) {
    let done = false, timer = 0;
    const name = '__septaCb' + (septaCbN++);
    const script = document.createElement('script');
    const fin = (data) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      try { delete window[name]; } catch (e) { window[name] = undefined; }
      if (script.parentNode) script.parentNode.removeChild(script);
      cb(data);
    };
    window[name] = fin;
    script.async = true;
    script.onerror = () => fin(null);
    timer = setTimeout(() => fin(null), 18000);
    script.src = SEPTA_HOSTS[septaHost] + path + '?callback=' + name;
    document.head.appendChild(script);
  }
  function septaUpsert(id, kind, route, lat, lon, apiHdg, info) {
    const x = (lon - SEPTA_GEO.lon0) * SEPTA_GEO.mx, z = -(lat - SEPTA_GEO.lat0) * SEPTA_GEO.mz;
    const under = septaUnder(kind, route, lat, lon);
    const now = performance.now();
    let v = septaVeh.get(id);
    if (!v) {
      v = { id, kind, route, routeLabel: septaRouteLabel(route), tint: SEPTA_TINT[route] || SEPTA_KIND[kind].c,
            info, fx: x, fz: z, tx: x, tz: z, x, z, t0: 0, yaw: 0, yawT: 0, ug: under, lastSeen: now };
      const c = new THREE.Color(v.tint);
      c.r = Math.min(1, c.r * 1.9 + 0.18); c.g = Math.min(1, c.g * 1.9 + 0.18); c.b = Math.min(1, c.b * 1.9 + 0.18);
      v.tintHex = '#' + c.getHexString();
      v.bobP = ((id.charCodeAt(id.length - 1) || 0) * 37 + id.length * 91) % 63 / 10;
      v.snT = now - hash01(v.bobP) * 120;   // per-vehicle phase: road snaps spread across frames, not one
      if (apiHdg) v.yaw = v.yawT = septaYawFromCompass(apiHdg);
      septaVeh.set(id, v);
      return;
    }
    v.fx = v.x; v.fz = v.z;
    v.tx = x; v.tz = z; v.t0 = now;
    const mdx = x - v.fx, mdz = z - v.fz, moved = Math.hypot(mdx, mdz);
    if (moved > 420) { v.fx = x; v.fz = z; v.x = x; v.z = z; }   // data jump — snap, don't sprint
    if (apiHdg) v.yawT = septaYawFromCompass(apiHdg);
    else if (moved > 6) v.yawT = Math.atan2(-mdz, mdx);          // derive heading from motion
    v.ug = under; v.info = info; v.lastSeen = now;
  }
  function septaFeedFail() {
    SEPTA.fails++;                                    // keeps counting across host flips: 3+ is an outage
    if (SEPTA.fails % 3 === 0) septaHost = 1 - septaHost;
    if (SEPTA.fails >= 3) SEPTA.ok = false;
    septaPrune(); septaStatus();                      // unseen 50 s = gone, even while the feed is down
  }
  function septaGotTV(d) {
    let routes = d && d.routes;
    if (Array.isArray(routes)) routes = routes[0];
    if (!routes || typeof routes !== 'object') { septaFeedFail(); return; }
    const nowS = Date.now() / 1000;
    for (const rid in routes) {
      const list = routes[rid];
      if (!Array.isArray(list)) continue;
      const kind = septaKindOf(rid);
      if (!kind) continue;
      for (const b of list) {
        const vid = String(b.VehicleID || '');
        if (!vid || vid === '0' || vid === 'None' || vid.indexOf('schedBased') >= 0) continue;
        const ts = +b.timestamp || 0;
        if (ts < 1e9 || nowS - ts > 300) continue;               // placeholder or stale fix
        const lat = +b.lat, lon = +b.lng;
        if (!(lat > SEPTA_BOX.la0 && lat < SEPTA_BOX.la1 && lon > SEPTA_BOX.lo0 && lon < SEPTA_BOX.lo1)) continue;
        septaUpsert('v' + vid, kind, rid, lat, lon, +b.heading || 0,
          { dest: b.destination || '', late: +b.late, next: b.next_stop_name || '' });
      }
    }
    SEPTA.ok = true; SEPTA.fails = 0;
    septaPrune(); septaStatus();
  }
  function septaPrune() {
    const now = performance.now();
    septaVeh.forEach((v, id) => { if (now - v.lastSeen > 50000) septaVeh.delete(id); });
    if (pickedVeh && !septaVeh.has(pickedVeh.id)) { pickedVeh = null; vehinfoEl.hidden = true; }
    else if (pickedVeh) septaCard(pickedVeh);        // keep late/next-stop fresh
  }
  function septaStatus() {
    const off = SEPTA.fails >= 3;
    let n = 0, onRoute = 0;   // vehicles out past the map are not counted (v.off, set by the road snap)
    septaVeh.forEach((v) => { if (v.off) return; n++; if (SEPTA.filter && !v.ug && v.route === SEPTA.filter) onRoute++; });
    const shown = SEPTA.filter ? onRoute + ' of ' + n : n + ' Live';   // the badge is small; the route name rides the title and the chip
    btnTransit.title = 'Live SEPTA Vehicles (V): ' + (off ? 'Feed Offline' : SEPTA.filter ? shown : n + ' Tracked Now');
    const tc = document.getElementById('transitCount');
    if (tc) tc.textContent = off ? 'Offline' : n ? shown : '';
    if (!SEPTA.hinted && n > 0 && !tour.on && veil.classList.contains('hidden')) {
      SEPTA.hinted = true;
      hintEl.textContent = n + ' SEPTA vehicles are live on the map. Tap a pin for its route. V toggles.';
      clearTimeout(septaHintT);
      septaHintT = setTimeout(setHint, 8000);
    }
  }
  function septaPoll(force) {
    if (!SEPTA.on || !septaCanFetch || !septaReady) return;
    if (document.hidden && !force) return;
    const now = performance.now();
    if (SEPTA.busy || (!force && now - SEPTA.lastT < 5000)) return;   // one pull in flight; unforced pulls never faster than 5 s
    SEPTA.busy = true; SEPTA.lastT = now;
    if (!septaBakedOk && now >= septaBakedRetryT) septaBakedOk = true;   // give the baker another try every 5 min
    const viaJsonp = () => septaJsonp('/TransitViewAll/index.php', (d) => { SEPTA.busy = false; septaGotTV(d); });
    if (septaBakedOk) septaFetchBaked((d) => { if (d) { SEPTA.busy = false; septaGotTV(d); } else viaJsonp(); });
    else viaJsonp();
  }
  function septaCard(v) {
    const late = v.info.late;
    const status = (late == null || isNaN(late) || late >= 900) ? '' :
      late > 0 ? late + ' Min Late' : late < 0 ? (-late) + ' Min Early' : 'On Time';
    const bits = [v.kind === 'bus' ? 'Bus' : 'Trolley'];
    if (status) bits.push(status);
    vehinfoBody.innerHTML =
      '<span class="vroute" style="background:' + v.tintHex + '">' + septaEsc(v.routeLabel) + '</span>' +
      '<span class="vdest">' + (v.info.dest ? 'To ' + septaEsc(v.info.dest) : 'Destination unknown') + '</span>' +
      '<div class="vmeta">' + septaEsc(bits.join(', ')) + '</div>' +
      (v.info.next ? '<div class="vmeta">Next Stop: ' + septaEsc(v.info.next) + '</div>' : '');
  }
  function syncTransitBtn() { syncLayerBtn(btnTransit, SEPTA.on); }
  function toggleTransit() {
    if (!septaCanFetch) return;
    SEPTA.on = !SEPTA.on;
    syncTransitBtn();
    if (SEPTA.on) septaPoll(true);
    else { septaSetFilter(null); if (pickedVeh) { pickedVeh = null; vehinfoEl.hidden = true; } }   // off also clears a route filter; only a SEPTA card closes, a plane or ship keeps its own
  }
  btnTransit.addEventListener('click', toggleTransit);
  document.getElementById('vehinfoX').addEventListener('click', () => { pickedVeh = null; pickedStation = null; pickedPlane = null; pickedShip = null; pickedTree = null; vehinfoEl.hidden = true; });
  // tap/click picking (orbit mode, or any touch tap): a short press on a vehicle
  const septaRay = new THREE.Raycaster(), septaNdc = new THREE.Vector2();
  const septaOccRay = new THREE.Raycaster();
  let vpDownX = 0, vpDownY = 0, vpDownT = 0, vpWasLocked = false;
  function isShortTap(e) { return Math.hypot(e.clientX - vpDownX, e.clientY - vpDownY) <= 8 && performance.now() - vpDownT <= 500; }
  canvas.addEventListener('pointerdown', (e) => { vpDownX = e.clientX; vpDownY = e.clientY; vpDownT = performance.now(); vpWasLocked = walk.locked; });
  canvas.addEventListener('pointerup', (e) => {
    if (panelTap) {
      // the press began with a panel open: a tap only dismisses it (a drag kept it)
      panelTap = false;
      if (isShortTap(e)) { closePanels(); return; }
    }
    const sAct = septaReady && SEPTA.on && septaSolid.count > 0;
    const iAct = indegoReady && INDEGO.on && indegoBadge.count > 0;
    const fAct = flightReady && FLIGHTS.on && (flightMesh.count > 0 || heliMesh.count > 0);
    const shAct = shipReady && SHIPS.on && shipMesh.count > 0;
    const tAct = !!treeInv;                            // the forest picks with every live layer off
    if (!sAct && !iAct && !fAct && !shAct && !tAct) return;
    // Works in every mode. Under pointer lock (desktop walk/fly look-around) the
    // cursor doesn't exist, so a click picks whatever's under the crosshair —
    // screen center. Unlocked (orbit, drag-look, touch), a short tap picks at
    // the pointer; drags are filtered out.
    let cx, cy;
    if (vpWasLocked && (mode === MODE.WALK || mode === MODE.FLY)) {
      cx = window.innerWidth / 2;
      cy = window.innerHeight / 2;
    } else {
      if (!isShortTap(e)) return;
      cx = e.clientX;
      cy = e.clientY;
    }
    septaNdc.set((cx / window.innerWidth) * 2 - 1, -(cy / window.innerHeight) * 2 + 1);
    septaRay.setFromCamera(septaNdc, camera);
    // occlusion gate: nothing picks through the city. The segment from the eye
    // to a candidate must clear the same buildings and terrain the double-click
    // focus used to raycast (rayTargets) plus the outer-district chunks.
    const pickOccluded = (tx, ty, tz) => {
      _ssv.set(tx, ty, tz).sub(camera.position);
      const L = _ssv.length();
      if (L < 3) return false;
      septaOccRay.set(camera.position, _ssv.multiplyScalar(1 / L));
      septaOccRay.far = L - 1.6;
      if (septaOccRay.intersectObjects(rayTargets, false).length > 0) return true;
      // The outer-district chunks CANNOT be raycast: freeOnUpload hands their
      // vertex arrays to the GPU and nulls the CPU side, so intersectObjects
      // threw the moment a sight line clipped a freed chunk's bounding sphere
      // — and that one uncaught throw killed every tooltip in the city (the
      // Round 37 verification never crossed a freed sphere; its street-level
      // refusal short-circuited on rayTargets). Out in the far districts the
      // occluder that actually matters is terrain — the NW gorge walls above
      // all — so march the sight line against demY instead.
      const o = camera.position, d = _ssv;
      for (let t = 30, tEnd = L - 12; t < tEnd; t += 40) {
        if (o.y + d.y * t < demY(o.x + d.x * t, o.z + d.z * t) - 0.5) return true;
      }
      return false;
    };
    const targets = [];
    if (sAct) targets.push(septaSolid, septaBadge);
    if (iAct) targets.push(indegoSolid, indegoBike, indegoBadge);
    if (fAct) targets.push(flightMesh, flightPin, heliMesh, flightPinH);
    if (shAct) targets.push(shipMesh, shipAnchor);
    const hits = septaRay.intersectObjects(targets, false);
    if (hits.length && hits[0].instanceId != null && !pickOccluded(hits[0].point.x, hits[0].point.y, hits[0].point.z)) {
      const h = hits[0];
      let v = null, hitSt = null;
      if (h.object === flightMesh || h.object === flightPin || h.object === heliMesh || h.object === flightPinH) {
        const p = (h.object === heliMesh || h.object === flightPinH) ? heliPick[h.instanceId] : flightPick[h.instanceId];
        if (p) { pickedVeh = null; pickedStation = null; pickedTree = null; pickedShip = null; pickedPlane = p; flightCard(p); vehinfoEl.hidden = false; return; }
      }
      if (h.object === shipMesh || h.object === shipAnchor) {
        const p = shipPick[h.instanceId];
        if (p) { pickedVeh = null; pickedStation = null; pickedTree = null; pickedPlane = null; pickedShip = p; shipCard(p); vehinfoEl.hidden = false; return; }
      }
      if (h.object === septaSolid) v = septaPickS[h.instanceId];
      else if (h.object === septaBadge) v = septaPickB[h.instanceId];
      else if (h.object === indegoSolid) hitSt = indegoPickS[h.instanceId];
      else if (h.object === indegoBike) hitSt = indegoPickK[h.instanceId];
      else if (h.object === indegoBadge) hitSt = indegoPickB[h.instanceId];
      if (v) { pickedStation = null; pickedTree = null; pickedPlane = null; pickedShip = null; pickedVeh = v; septaCard(v); vehinfoEl.hidden = false; return; }
      if (hitSt) { pickedVeh = null; pickedTree = null; pickedPlane = null; pickedShip = null; pickedStation = hitSt; indegoCard(hitSt); vehinfoEl.hidden = false; return; }
    }
    // forgiving fallback: the nearest vehicle or bike dock within reach of the
    // tap point (a little wider under the crosshair, where aiming is coarser)
    let bestV = null, bestS = null, bestD = (vpWasLocked ? 46 : 30) ** 2;
    if (sAct) septaVeh.forEach((v) => {
      if (v.off) return;   // not drawn, not pickable
      if (SEPTA.filter && v.route !== SEPTA.filter) return;   // not drawn, not pickable
      if (v.ug) return;
      _ssv.set(v.dx != null ? v.dx : v.x, (v.gy || 0) + 3, v.dz != null ? v.dz : v.z).project(camera);
      if (_ssv.z > 1 || _ssv.z < -1) return;
      const dx = (_ssv.x * 0.5 + 0.5) * window.innerWidth - cx;
      const dy = (-_ssv.y * 0.5 + 0.5) * window.innerHeight - cy;
      const d2 = dx * dx + dy * dy;
      if (d2 < bestD) { bestD = d2; bestV = v; }
    });
    if (iAct) for (const st of indegoLive) {
      _ssv.set(st.x, st.y + 2.6, st.z).project(camera);
      if (_ssv.z > 1 || _ssv.z < -1) continue;
      const dx = (_ssv.x * 0.5 + 0.5) * window.innerWidth - cx;
      const dy = (-_ssv.y * 0.5 + 0.5) * window.innerHeight - cy;
      const d2 = dx * dx + dy * dy;
      if (d2 < bestD) { bestD = d2; bestS = st; bestV = null; }
    }
    if (bestV && pickOccluded(bestV.dx != null ? bestV.dx : bestV.x, (bestV.gy || 0) + 2.5, bestV.dz != null ? bestV.dz : bestV.z)) bestV = null;
    if (bestS && pickOccluded(bestS.x, bestS.y + 2, bestS.z)) bestS = null;
    if (bestV) { pickedStation = null; pickedTree = null; pickedPlane = null; pickedShip = null; pickedVeh = bestV; septaCard(bestV); vehinfoEl.hidden = false; return; }
    if (bestS) { pickedVeh = null; pickedTree = null; pickedPlane = null; pickedShip = null; pickedStation = bestS; indegoCard(bestS); vehinfoEl.hidden = false; return; }
    // no vehicle or dock: try the forest. First march the pick ray against the
    // canopy spheres (tapping a crown is the natural gesture), then fall back
    // to the nearest tree around the tapped ground point (trunk-level taps)
    if (treeInv) {
      let bestT = -1;
      const o = septaRay.ray.origin, dr = septaRay.ray.direction;
      for (let t = 5; t < 700 && bestT < 0; t += 6) {
        const px = o.x + dr.x * t, py = o.y + dr.y * t, pz = o.z + dr.z * t;
        const gx = Math.floor(px / TREE_CELL), gz = Math.floor(pz / TREE_CELL);
        for (let ix = gx - 1; ix <= gx + 1; ix++) for (let iz = gz - 1; iz <= gz + 1; iz++) {
          const cell = treePickGrid.get(ix + ':' + iz);
          if (!cell) continue;
          for (const ti of cell) {
            const dx = treeInv.x[ti] - px, dy2 = treeInv.cy[ti] - py, dz = treeInv.z[ti] - pz;
            const rr = Math.max(2.5, treeInv.cr[ti] + 0.6);
            if (dx * dx + dy2 * dy2 + dz * dz < rr * rr) { bestT = ti; break; }
          }
          if (bestT >= 0) break;
        }
      }
      if (bestT < 0) {
        const gp = groundPointAt(cx, cy);
        if (gp) {
          let bestD2 = 0;
          const gx = Math.floor(gp[0] / TREE_CELL), gz = Math.floor(gp[1] / TREE_CELL);
          for (let ix = gx - 1; ix <= gx + 1; ix++) for (let iz = gz - 1; iz <= gz + 1; iz++) {
            const cell = treePickGrid.get(ix + ':' + iz);
            if (!cell) continue;
            for (const ti of cell) {
              const dx = treeInv.x[ti] - gp[0], dz = treeInv.z[ti] - gp[1];
              const d2 = dx * dx + dz * dz;
              const r = Math.max(3.5, treeInv.cr[ti] + 0.8);
              if (d2 < r * r && (bestT < 0 || d2 < bestD2)) { bestT = ti; bestD2 = d2; }
            }
          }
        }
      }
      if (bestT >= 0 && pickOccluded(treeInv.x[bestT], treeInv.cy[bestT], treeInv.z[bestT])) bestT = -1;
      if (bestT >= 0) { pickedVeh = null; pickedStation = null; pickedPlane = null; pickedShip = null; pickedTree = bestT; treeCard(bestT); vehinfoEl.hidden = false; return; }
    }
    if (pickedVeh || pickedStation || pickedPlane || pickedShip || pickedTree != null) { pickedVeh = null; pickedStation = null; pickedPlane = null; pickedShip = null; pickedTree = null; vehinfoEl.hidden = true; }
  });
  // Road-network spatial hash for snapping live street vehicles onto their
  // streets: raw GPS scatters ±10 m and the straight tween between fixes cuts
  // corners, both of which parked buses inside buildings. Fed by all three road
  // passes (core / wide / far) with drivable classes, queried per vehicle a few
  // times a second and smoothed.
  const septaRoadGrid = new Map();
  const SEPTA_RG_CELL = 36;
  function septaRoadAdd(ax, az, bx, bz) {
    const x0 = Math.floor(Math.min(ax, bx) / SEPTA_RG_CELL), x1 = Math.floor(Math.max(ax, bx) / SEPTA_RG_CELL);
    const z0 = Math.floor(Math.min(az, bz) / SEPTA_RG_CELL), z1 = Math.floor(Math.max(az, bz) / SEPTA_RG_CELL);
    for (let gx = x0; gx <= x1; gx++) for (let gz = z0; gz <= z1; gz++) {
      const key = gx + ':' + gz;
      let a = septaRoadGrid.get(key);
      if (!a) { a = []; septaRoadGrid.set(key, a); }
      a.push(ax, az, bx, bz);
    }
  }
  function septaSnapRoad(x, z, maxD) {
    const gx = Math.floor(x / SEPTA_RG_CELL), gz = Math.floor(z / SEPTA_RG_CELL);
    let bd = maxD * maxD, bx2 = 0, bz2 = 0, bdx = 1, bdz = 0, found = false;
    for (let cx2 = gx - 1; cx2 <= gx + 1; cx2++) for (let cz2 = gz - 1; cz2 <= gz + 1; cz2++) {
      const a = septaRoadGrid.get(cx2 + ':' + cz2);
      if (!a) continue;
      for (let i = 0; i < a.length; i += 4) {
        const ax = a[i], az = a[i + 1], dx = a[i + 2] - ax, dz = a[i + 3] - az;
        const L2 = dx * dx + dz * dz || 1e-9;
        let tt = ((x - ax) * dx + (z - az) * dz) / L2;
        tt = tt < 0 ? 0 : tt > 1 ? 1 : tt;
        const ex = ax + dx * tt - x, ez = az + dz * tt - z;
        const d2 = ex * ex + ez * ez;
        if (d2 < bd) { bd = d2; bx2 = ax + dx * tt; bz2 = az + dz * tt; bdx = dx; bdz = dz; found = true; }
      }
    }
    if (!found) return null;
    const L3 = Math.hypot(bdx, bdz) || 1;
    return [bx2, bz2, bdx / L3, bdz / L3];   // point + street axis, for position AND heading alignment
  }
  function septaMerge(parts) {
    let total = 0;
    parts.forEach((g) => { total += g.attributes.position.count; });
    const pos = new Float32Array(total * 3), nor = new Float32Array(total * 3), col = new Float32Array(total * 3), glo = new Float32Array(total);
    let o = 0;
    for (const g of parts) {
      pos.set(g.attributes.position.array, o * 3);
      nor.set(g.attributes.normal.array, o * 3);
      col.set(g.attributes.color.array, o * 3);
      if (g.attributes.aGlow) glo.set(g.attributes.aGlow.array, o);
      o += g.attributes.position.count;
    }
    const out = new THREE.BufferGeometry();
    out.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    out.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
    out.setAttribute('color', new THREE.BufferAttribute(col, 3));
    out.setAttribute('aGlow', new THREE.BufferAttribute(glo, 1));
    return out;
  }
  function septaColored(g, cr, cg, cb, glow) {
    const gg = g.index ? g.toNonIndexed() : g;
    const n = gg.attributes.position.count;
    const col = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { col[i * 3] = cr; col[i * 3 + 1] = cg; col[i * 3 + 2] = cb; }
    gg.setAttribute('color', new THREE.BufferAttribute(col, 3));
    const glo = new Float32Array(n);
    if (glow) glo.fill(1);
    gg.setAttribute('aGlow', new THREE.BufferAttribute(glo, 1));
    return gg;
  }
  function septaVehGeom(withBand) {
    // unit vehicle: length along x in [-.5,.5], base y=0..1, width z; scaled per
    // class. Vertex colors multiply the per-instance line color, so trim parts
    // are near-black (glass, wheels) or near-white (body) multipliers.
    const parts = [];
    const boxPart = (sx, sy, sz, cx, cy, cz, cr, cg, cb, glow) =>
      parts.push(septaColored(new THREE.BoxGeometry(sx, sy, sz).translate(cx, cy, cz), cr, cg, cb, glow));
    boxPart(0.98, 0.94, 0.94, 0, 0.53, 0, 1, 1, 1);                       // body (takes instance color)
    if (withBand) {
      boxPart(0.9, 0.36, 1.02, 0, 0.72, 0, 0.14, 0.15, 0.17, 1);         // glass band, proud — lit at night
      boxPart(0.99, 0.1, 0.9, 0, 0.07, 0, 0.2, 0.21, 0.22);              // dark undercarriage skirt
      boxPart(0.05, 0.3, 0.8, 0.475, 0.71, 0, 0.13, 0.14, 0.16, 1);      // windshield, engaging the nose
      boxPart(0.5, 0.09, 0.66, -0.05, 1.03, 0, 0.7, 0.72, 0.74);         // roof HVAC unit
      for (const wx of [-0.3, 0.3]) for (const wz of [-0.44, 0.44]) {
        boxPart(0.13, 0.17, 0.1, wx, 0.085, wz, 0.09, 0.09, 0.1);        // wheel blocks, proud of the sides
      }
    }
    return septaMerge(parts);
  }
  function septaPinGeom() {
    // floating map pin: inverted cone + ball, tinted by instance color
    const cone = new THREE.ConeGeometry(1.05, 2.7, 9);
    cone.rotateX(Math.PI);
    cone.translate(0, 1.75, 0);
    const ball = new THREE.SphereGeometry(1.35, 10, 8);
    ball.translate(0, 3.6, 0);
    return septaMerge([septaColored(cone, 0.78, 0.78, 0.78), septaColored(ball, 1, 1, 1)]);
  }
  function septaBadgeTexture() {
    // bus pins wear the SEPTA mark: a marker badge drawn once into a canvas —
    // official geometry from the agency's logo SVG (Wikimedia SEPTA.svg, 500x369
    // box), Path2D-filled under the badge's rounded frame + pointer tip
    const cv = document.createElement('canvas');
    cv.width = 256; cv.height = 320;
    const g = cv.getContext('2d');
    const bw = 240, bh = 200, bx = 8, by = 8, rad = 34;
    const rr = () => {
      g.beginPath();
      g.moveTo(bx + rad, by);
      g.arcTo(bx + bw, by, bx + bw, by + bh, rad);
      g.arcTo(bx + bw, by + bh, bx, by + bh, rad);
      g.arcTo(bx, by + bh, bx, by, rad);
      g.arcTo(bx, by, bx + bw, by, rad);
      g.closePath();
    };
    g.fillStyle = '#fdfbf6';
    g.strokeStyle = 'rgba(28,26,22,0.6)';
    g.lineWidth = 7;
    g.beginPath();                                   // pointer tip first, badge overlaps it
    g.moveTo(128 - 30, by + bh - 6);
    g.lineTo(128, 312);
    g.lineTo(128 + 30, by + bh - 6);
    g.closePath();
    g.fill(); g.stroke();
    rr(); g.fill(); g.stroke();
    const s2 = (bw - 40) / 500;
    g.translate(bx + 20, by + (bh - 369.109 * s2) / 2);
    g.scale(s2, s2);
    g.fillStyle = '#f14728';
    g.fill(new Path2D('M441.775,14.666H340.441L180.888,127.332h148.665l115.779,115.333L333.556,355.107h108.22c25.555,0,44.221-25.332,44.221-43.331V58.221C485.996,39.998,467.33,14.666,441.775,14.666z'));
    g.fill(new Path2D('M206.443,137.998H192.22l87.111,87.107c4.001,3.338,7.11,7.336,13.999,6.893h14.89l-87.555-86.889C216.665,140.664,213.776,137.998,206.443,137.998z'));
    g.fillStyle = '#1f4fa3';
    g.fill(new Path2D('M58.666,355.107h101.111l159.554-112.219H170.887L54.666,127.332L167.11,14.666H58.666c-25.778,0-44,25.332-44,43.776v253.555C14.666,329.775,32.888,355.107,58.666,355.107z'));
    const tex = new THREE.CanvasTexture(cv);
    tex.encoding = THREE.sRGBEncoding;
    tex.anisotropy = anisoOf(4);
    return tex;
  }
  const _sm = new THREE.Matrix4(), _sq = new THREE.Quaternion(), _sqB = new THREE.Quaternion(), _sp = new V3(), _ss = new V3(), _sc = new THREE.Color(), _sup = new V3(0, 1, 0), _ssv = new V3();
  function updateTransit(now, dt) {
    if (!septaReady) return;
    if (!SEPTA.on) {
      if (septaSolid.count || septaBadge.count) { septaSolid.count = 0; septaBadge.count = 0; }
      return;
    }
    let si = 0, bi = 0;
    const cap = 2.6 * dt;
    _sqB.copy(camera.quaternion);                      // badges billboard the camera
    septaVeh.forEach((v) => {
      const k = v.t0 ? Math.min(1, (now - v.t0) / (SEPTA_POLL + 1500)) : 1;
      v.x = v.fx + (v.tx - v.fx) * k;
      v.z = v.fz + (v.tz - v.fz) * k;
      // street vehicles snap to the nearest drivable centerline (refreshed a few
      // times a second, staggered) and glide to it — GPS scatter and corner-cut
      // tweens no longer drive buses through building walls
      let wx = v.x, wz = v.z;
      if (!v.ug && (v.kind === 'bus' || v.kind === 'trolley')) {
        if (v.snT === undefined || now - v.snT > 120) {
          v.snT = now;
          const sn = septaSnapRoad(v.x, v.z, 20);
          if (sn) { v.snx = sn[0]; v.snz = sn[1]; v.sdx = sn[2]; v.sdz = sn[3]; v.off = !insideLimit(v.x, v.z); }
          else { v.snx = null; v.off = !insideLimit(v.x, v.z) || !septaSnapRoad(v.x, v.z, 140); }   // beyond the flight limit, or no drawn street within 140 m: off the map
        }
        if (v.snx != null) { wx = v.snx; wz = v.snz; }
      }
      if (v.dx === undefined) { v.dx = wx; v.dz = wz; }
      const kS = 1 - Math.exp(-dt * 7);
      v.dx += (wx - v.dx) * kS;
      v.dz += (wz - v.dz) * kS;
      // heading: align to the snapped street's axis (signed to match the API/
      // displacement heading) so GPS heading noise never parks a bus diagonally
      // across its street; unsnapped vehicles keep the raw heading
      let yawGoal = v.yawT;
      if (v.snx != null) {
        const ry = Math.atan2(-v.sdz, v.sdx);
        let dAx = ry - v.yawT;
        dAx = wrapPi(dAx);
        yawGoal = Math.abs(dAx) <= Math.PI / 2 ? ry : ry + Math.PI;
      }
      let dyaw = yawGoal - v.yaw;
      dyaw = wrapPi(dyaw);
      v.yaw += Math.abs(dyaw) <= cap ? dyaw : Math.sign(dyaw) * cap;
      if (v.ug) return;                 // tunnel trolleys aren't drawn — nothing under buildings
      if (v.off) return;   // a suburban tail of a route has nothing to stand on here
      if (SEPTA.filter && v.route !== SEPTA.filter) return;   // a route search shows that route alone (the pick arrays fill below, so they stay in step)
      if (v.gy === undefined || Math.abs(v.dx - v.gx) + Math.abs(v.dz - v.gz) > 2.5) {
        v.gx = v.dx; v.gz = v.dz;
        v.gy = siteY(v.dx, v.dz, 'road');
        // a vehicle on a bridge street rides the deck, not the ground beneath it
        // (aligned to its snapped street axis so passing under a viaduct never lifts)
        if (v.sdx || v.sdz) {
          const oy = ovpDeckY(v.dx, v.dz, v.sdx, v.sdz);
          if (oy !== null && oy > v.gy) v.gy = oy;
        }
      }
      const spec = SEPTA_KIND[v.kind];
      if (si < 1600) {
        _ss.set(spec.l, spec.h, spec.w);
        _sq.setFromAxisAngle(_sup, v.yaw);
        _sp.set(v.dx, v.gy + 0.22, v.dz);
        _sm.compose(_sp, _sq, _ss);
        septaSolid.setMatrixAt(si, _sm);
        septaSolid.setColorAt(si, _sc.setHex(v.tint));
        septaPickS[si++] = v;
      }
      // floating marker, scaled with distance so it stays findable: buses fly
      // the SEPTA-badge billboard, trolleys keep the line-colored lollipop pin
      // every vehicle — bus, trolley, el — wears the SEPTA badge now: the
      // line-colored lollipops read as a different system from the air
      if (bi < 1024) {
        const py0 = v.gy + spec.h + 0.6;
        _sp.set(v.dx, py0, v.dz);
        const s = clamp(camera.position.distanceTo(_sp) / 135, 2.2, 14);
        _sp.y += Math.sin(now * 0.003 + v.bobP) * 0.5 * Math.min(s, 2);
        _ss.set(s, s, s);
        _sm.compose(_sp, _sqB, _ss);
        septaBadge.setMatrixAt(bi, _sm);
        septaPickB[bi++] = v;
      }
    });
    septaSolid.count = si;
    septaBadge.count = bi;
    flushInst(septaSolid);
    flushInst(septaBadge);
    if (pickedVeh) {
      const spec = SEPTA_KIND[pickedVeh.kind];
      _ssv.set(pickedVeh.dx, pickedVeh.gy + spec.h + 7, pickedVeh.dz).project(camera);
      if (_ssv.z > 1 || _ssv.z < -1) vehinfoEl.style.opacity = '0';
      else {
        vehinfoEl.style.opacity = '1';
        vehinfoEl.style.transform = 'translate(-50%,-100%) translate(' +
          ((_ssv.x * 0.5 + 0.5) * window.innerWidth).toFixed(1) + 'px,' +
          ((-_ssv.y * 0.5 + 0.5) * window.innerHeight).toFixed(1) + 'px)';
      }
    }
  }

  // ---------------------------------------------------------------- layers panel
  // The three layer toggles (SEPTA vehicles, street names, landmark labels) live
  // as rows in one panel behind the Layers bar button; V/N/L stay as shortcuts.
  const btnLayers = document.getElementById('btnLayers');
  const layersPanel = document.getElementById('layerspanel');
  function toggleLayers(open) { openPanel('layers', open); }
  btnLayers.addEventListener('click', () => toggleLayers());
  // panel footer: back to the shipped layers, and a link to this exact view
  document.getElementById('btnResetLayers').addEventListener('click', () => {
    // through the real toggles, so the live polls start and stop with the flags
    const toggles = { septa: toggleTransit, indego: toggleIndego, flights: toggleFlights, ships: toggleShips, traffic: toggleTraffic, lights: toggleLightsLayer, streets: toggleStreets, labels: toggleLabels, places: togglePlaces };
    const f = layerFlags();
    for (const k of LAYER_KEYS) if (f[k] !== LAYER_DEFAULTS[k]) toggles[k]();
    setLapse(false);
    if (!clock.live) { clock.live = true; setClockToNow(); refreshTimeUI(); }
    clearPrefs();   // defaults are not remembered; the next change is
  });
  const btnCopyLink = document.getElementById('btnCopyLink');
  const copyLabel = btnCopyLink.textContent;
  btnCopyLink.addEventListener('click', () => {
    updateHash(performance.now(), true);   // the link carries this pose, not the last 500 ms tick
    const url = location.origin + location.pathname + location.search + '#' + viewState(true);   // with the pinned clock, if any
    const done = () => { btnCopyLink.textContent = 'Copied'; setTimeout(() => { btnCopyLink.textContent = copyLabel; }, 1500); };
    const legacy = () => {
      // no async clipboard (plain http, older WebKit): select a throwaway field and copy
      const inp = document.createElement('input');
      inp.value = url; inp.setAttribute('readonly', ''); inp.style.cssText = 'position:fixed;top:0;left:0;opacity:0';
      document.body.appendChild(inp); inp.select();
      try { if (document.execCommand('copy')) done(); } catch (e) { }
      inp.remove();
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(done, legacy);
    else legacy();
  });

  // ---------------------------------------------------------------- street names
  // Ground-painted street labels: placements baked offline by
  // bake_street_labels.py (the packed wide/far road formats carry no names) and
  // shipped as ST_LABELS; every unique name is drawn once into a canvas atlas
  // and all ~4,700 labels merge into ONE textured quad mesh lying flat on the
  // roadways. Toggle: the St button / N key.
  let stMesh = null, stMat = null, stOn = true;
  const btnStreets = document.getElementById('btnStreets');
  function syncStreetsBtn() { syncLayerBtn(btnStreets, stOn); }
  function toggleStreets() {
    stOn = !stOn;
    if (stMesh) stMesh.visible = stOn;
    syncStreetsBtn();
  }
  btnStreets.addEventListener('click', toggleStreets);
  step('Lettering the streets', async () => {
    if (typeof ST_LABELS === 'undefined' || !ST_LABELS || !ST_LABELS.names) { btnStreets.style.display = 'none'; return; }
    // Preferred path: the offline signed-distance-field atlas (bake_street_sdf.py).
    // A raster atlas magnified 5-9x at street level reads pixelated however its
    // edges are filtered; in an SDF the 0.5 level-set IS the glyph outline, so a
    // per-pixel threshold stays crisp at any zoom. Falls back to the old canvas
    // atlas if the baked data is missing.
    let AW = 4096, AH = 2048, FS = 27, RH = 34;
    const PAD = 9;
    let tex = null, rects = null, sdfMode = false;
    if (typeof ST_SDF !== 'undefined' && ST_SDF && ST_SDF.png) {
      sdfMode = true;
      AW = ST_SDF.w; AH = ST_SDF.h; RH = ST_SDF.rowH; FS = ST_SDF.fs;
      rects = ST_SDF.rects;
      let img = new Image();
      await new Promise((res) => { img.onload = res; img.onerror = res; img.src = 'data:image/png;base64,' + ST_SDF.png; });
      ST_SDF = null;   // the atlas PNG lives in the texture now
      const cv = document.createElement('canvas');
      cv.width = AW; cv.height = AH;
      const g = cv.getContext('2d');
      g.drawImage(img, 0, 0);
      img = null;
      // R channel in 256-row bands: one getImageData of the whole atlas was a
      // 36.8 MB RGBA spike on top of the decoded image, the kind phones die on
      const lum = new Uint8Array(AW * AH);
      for (let y = 0; y < AH; y += 256) {
        const rows = Math.min(256, AH - y);
        const px = g.getImageData(0, y, AW, rows).data;
        for (let i = 0, o = y * AW; i < rows * AW; i++) lum[o + i] = px[i * 4];
      }
      cv.width = cv.height = 0;   // release the canvas backing store
      tex = new THREE.DataTexture(lum, AW, AH, THREE.RedFormat, THREE.UnsignedByteType);  // R8: WebGL2 mipmappable (LUMINANCE is not)
      tex.magFilter = THREE.LinearFilter;
      tex.minFilter = THREE.LinearMipmapLinearFilter;
      tex.generateMipmaps = true;
      tex.flipY = true;                    // the UV math below assumes canvas orientation
      tex.anisotropy = anisoOf(16);   // ground-draped street atlas: grazing angles want the full cap
      tex.needsUpdate = true;
    } else {
      try { await document.fonts.load('italic 600 27px "Montserrat"'); } catch (e) { /* fall back to the stack */ }
      const cv = document.createElement('canvas');
      cv.width = AW; cv.height = AH;
      const g = cv.getContext('2d');
      // street lettering: Montserrat semibold italic, map-style
      g.font = 'italic 600 ' + FS + 'px "Montserrat", "Avenir Next", "Segoe UI", sans-serif';
      g.fillStyle = '#fff';
      g.textBaseline = 'middle';
      rects = [];
      let ax = PAD, ay = 0;
      for (const nm of ST_LABELS.names) {
        const w = Math.min(Math.ceil(g.measureText(nm).width), 560);
        if (ax + w + PAD > AW) { ax = PAD; ay += RH; }
        if (ay + RH > AH) { rects.push(null); continue; }
        g.fillText(nm, ax, ay + RH / 2, 560);
        rects.push([ax, ay, w, RH]);
        ax += w + PAD * 2;
      }
      tex = new THREE.CanvasTexture(cv);
      tex.encoding = THREE.sRGBEncoding;
      tex.anisotropy = anisoOf(16);
    }
    const L2 = ST_LABELS.l;
    const pos = [], uv = [], idx = [];
    const LIFT = [0.66, 0.5, 0.38];        // over siteY(road): major / minor / core (clears ribbon lifts)
    const TH = [7.0, 5.6, 4.4];            // text height in meters per class
    for (let i = 0; i + 4 < L2.length; i += 5) {
      const r = rects[L2[i]];
      if (!r) continue;
      const x = L2[i + 1], z = L2[i + 2], br = L2[i + 3] * Math.PI / 180, cls = L2[i + 4];
      const inCutName = /expressway/i.test(ST_LABELS.names[L2[i]] || '');   // only the mainline name sinks into the cut
      const dx = Math.cos(br), dz = Math.sin(br);
      const ux = dz, uz = -dx;             // glyph-up in world = left of travel (north-up read)
      const th = TH[cls], hw = th * (r[2] / FS) / 2, hh = th * (RH / FS) / 2;
      const u0 = r[0] / AW, u1 = (r[0] + r[2]) / AW;
      const v1 = 1 - r[1] / AH, v0 = 1 - (r[1] + r[3]) / AH;
      // drape the label along the street profile: a flat quad at one height sank
      // an end into the pavement wherever the road slopes (Front St, the trench
      // shoulders), so sample the road height every ~7 m along the text instead
      const cols = Math.max(2, Math.min(10, Math.round(hw / 3.5)));
      // pass 1: column heights (decks lift them, the Vine cut sinks its own name)
      const colY = [];
      for (let c2 = 0; c2 <= cols; c2++) {
        const t2 = c2 / cols * 2 - 1;
        const cxw = x + dx * t2 * hw, czw = z + dz * t2 * hw;
        let ycs = siteY(cxw, czw, 'road');
        const oyc = ovpDeckY(cxw, czw, dx, dz);
        if (oyc !== null && oyc > ycs) ycs = oyc;
        else if (inCutName) {
          const vyc = vineCut(cxw, czw, -2);
          if (vyc !== null) ycs = vyc + 0.45;
        }
        colY.push(ycs);
      }
      // buried roads get no label: under the trench caps the roadway runs below
      // ground (the half-swallowed Delaware Expressway name at Foglietta)
      const midY = colY[Math.floor(cols / 2)];
      if (siteY(x, z, 'ground') - midY > 2.5 && vineCut(x, z, -2) === null) continue;
      // label ends must never climb a trench wall or bank: cap the rise between
      // neighboring columns (steep streets stay legible, walls stop swallowing text)
      for (let c2 = 1; c2 <= cols; c2++) colY[c2] = Math.min(colY[c2], colY[c2 - 1] + 1.0);
      for (let c2 = cols - 1; c2 >= 0; c2--) colY[c2] = Math.min(colY[c2], colY[c2 + 1] + 1.0);
      const i0 = pos.length / 3;
      for (let c2 = 0; c2 <= cols; c2++) {
        const t2 = c2 / cols * 2 - 1;
        const cxw = x + dx * t2 * hw, czw = z + dz * t2 * hw;
        const yc = colY[c2] + LIFT[cls];
        pos.push(cxw - ux * hh, yc, czw - uz * hh, cxw + ux * hh, yc, czw + uz * hh);
        const uc = u0 + (u1 - u0) * (c2 / cols);
        uv.push(uc, v0, uc, v1);
      }
      for (let c2 = 0; c2 < cols; c2++) {
        const a2 = i0 + c2 * 2;
        idx.push(a2, a2 + 2, a2 + 3, a2, a2 + 3, a2 + 1);
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
    geo.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(uv), 2));
    geo.setIndex(idx);
    if (sdfMode) {
      // luminance SDF rides in the alphaMap (.g); the 0.5 level-set is the true
      // outline, thresholded with fwidth-scaled AA — crisp at every zoom
      stMat = new THREE.MeshBasicMaterial({ alphaMap: tex, transparent: true, depthWrite: false, color: 0x2c2822 });
      stMat.onBeforeCompile = (shader) => {
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <alphamap_fragment>',
          '{\n' +
          '  float sd = texture2D(alphaMap, vUv).r;\n' +   // R8: the SDF rides in .r
          '  float w = clamp(fwidth(sd) * 1.1, 0.002, 0.35);\n' +
          '  diffuseColor.a *= smoothstep(0.5 - w, 0.5 + w, sd);\n' +
          '}');
      };
    } else {
      stMat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, color: 0x2c2822 });
      // Alpha-tested magnification fallback: bilinear coverage approximates a
      // distance field near edges; re-threshold with fwidth AA to cut the blocks.
      stMat.onBeforeCompile = (shader) => {
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <map_fragment>',
          '#include <map_fragment>\n{\n' +
          '  float w = clamp(fwidth(diffuseColor.a) * 1.4, 0.02, 0.49);\n' +
          '  diffuseColor.a = smoothstep(0.42 - w, 0.42 + w, diffuseColor.a);\n' +
          '}');
      };
    }
    stMesh = new THREE.Mesh(geo, stMat);
    stMesh.renderOrder = 5;
    stMesh.visible = stOn;
    groupCity.add(stMesh);
    syncStreetsBtn();
  });

  // ---------------------------------------------------------------- places
  // Historic districts and neighborhood names (OpenDataPhilly, baked by
  // fetch_places.py / bake_places.py into PLACES). The sixteen Philadelphia
  // Register districts draw as bronze boundary inlays on the ground, Society
  // Hill first among them; the neighborhood names fade in from altitude as
  // the district-level complement to the painted street names. One toggle
  // covers all of it: the P key.
  let placesOn = true, nbMesh = null, nbMat = null;
  const btnPlaces = document.getElementById('btnPlaces');
  function syncPlacesBtn() { syncLayerBtn(btnPlaces, placesOn); }
  function togglePlaces() {
    placesOn = !placesOn;
    if (nbMesh) nbMesh.visible = false;      // applyLighting re-shows it by altitude
    syncPlacesBtn();
  }
  btnPlaces.addEventListener('click', togglePlaces);
  // (the historic-district bronze street inlays and their labels were removed
  // at the owner's request — "janky gold lines"; the district data stays in
  // places.json if they are ever wanted back. The P toggle now governs the
  // neighborhood names alone.)
  step('Naming the neighborhoods', async () => {
    if (typeof PLACES === 'undefined' || !PLACES || !PLACES.nb || !PLACES.nb.names) { btnPlaces.style.display = 'none'; return; }
    const AW = 2048, AH = 1024, FS = 30, RH = 38, PAD = 8;
    try { await document.fonts.load('600 30px "Montserrat"'); } catch (e) { /* fall back to the stack */ }
    const cv = document.createElement('canvas');
    cv.width = AW; cv.height = AH;
    const g = cv.getContext('2d');
    g.font = '600 ' + FS + 'px "Montserrat", "Avenir Next", "Segoe UI", sans-serif';
    g.fillStyle = '#fff';
    g.textBaseline = 'middle';
    let ax = PAD, ay = 0;
    const put = (nm, haloed) => {
      const w = Math.min(Math.ceil(g.measureText(nm).width), 520);
      if (ax + w + PAD > AW) { ax = PAD; ay += RH; }
      if (ay + RH > AH) return null;
      if (haloed) {
        // cartographic halo baked in final colors: a pale casing around a dark
        // core stays readable over the pale noon city AND the night ground
        // (a flat tint washed out at noon — Mike's ghost-text screenshot)
        g.lineJoin = 'round';
        g.strokeStyle = 'rgba(248,244,233,0.95)';
        g.lineWidth = 7;
        g.strokeText(nm, ax, ay + RH / 2, 520);
        g.fillStyle = '#2e2a22';
        g.fillText(nm, ax, ay + RH / 2, 520);
        g.fillStyle = '#fff';
      } else {
        g.fillText(nm, ax, ay + RH / 2, 520);
      }
      const r = [ax, ay, w, RH];
      ax += w + PAD * 2;
      return r;
    };
    const nbRects = PLACES.nb.names.map((nm) => put(nm, true));
    const tex = new THREE.CanvasTexture(cv);
    tex.encoding = THREE.sRGBEncoding;
    tex.anisotropy = anisoOf(16);   // ground-draped neighborhood labels
    const makeMesh = (entries, mat) => {
      // flat north-up quads draped in 4 columns so long names ride the terrain
      const pos = [], uv = [], idx = [];
      for (const [r, x, z, textH, lift] of entries) {
        if (!r) continue;
        const hw = textH * (r[2] / FS) / 2, hh = textH * (RH / FS) / 2;
        const u0 = r[0] / AW, u1 = (r[0] + r[2]) / AW;
        const v1 = 1 - r[1] / AH, v0 = 1 - (r[1] + r[3]) / AH;
        const cols = 4;
        const i0 = pos.length / 3;
        for (let c = 0; c <= cols; c++) {
          const cx = x + (c / cols * 2 - 1) * hw;
          const yc = walkY(cx, z) + lift;
          pos.push(cx, yc, z + hh, cx, yc, z - hh);
          const uc = u0 + (u1 - u0) * (c / cols);
          uv.push(uc, v0, uc, v1);
        }
        for (let c = 0; c < cols; c++) {
          const a = i0 + c * 2;
          idx.push(a, a + 2, a + 3, a, a + 3, a + 1);
        }
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
      geo.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(uv), 2));
      geo.setIndex(idx);
      const mesh = new THREE.Mesh(geo, mat);
      mesh.renderOrder = 5;
      groupCity.add(mesh);
      return mesh;
    };
    // 24 m up: painted at grade the names drown under rowhouse roofs and tree
    // canopies (street names live on open roadway; neighborhoods don't) — a
    // gentle lift clears the fabric while the towers still punch through
    const NB_TH = [110, 80, 55];              // text height by area class
    const L = PLACES.nb.l;
    const nbEntries = [];
    for (let i = 0; i + 3 < L.length; i += 4) nbEntries.push([nbRects[L[i]], L[i + 1], L[i + 2], NB_TH[L[i + 3]] || 55, 24]);
    // no depth test: a neighborhood's name is never blocked by its buildings
    // (Mike's rule) — badges at renderOrder 12 still paint over the names
    nbMat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, depthTest: false, color: 0xffffff, opacity: 0 });
    nbMat.toneMapped = false;   // the atlas carries its own halo colors
    postRaw(nbMat, { mask: true });   // a label, not a light: no bloom
    nbMesh = makeMesh(nbEntries, nbMat);
    nbMesh.renderOrder = 11;
    nbMesh.visible = false;                   // fades in from altitude
  });

  // ---------------------------------------------------------------- address search
  // The model's own names first (landmarks, neighborhoods, districts, buildings,
  // streets: a local index, no network), then a live bus route, then Nominatim
  // (OpenStreetMap) geocoding bounded to the modeled city box: free, key-less,
  // CORS-open, but blocked under the artifact CSP like every other live fetch,
  // where the local index still works. Results fly the camera to the spot and
  // drop a bronze pin + label for 20 s.
  const btnSearch = document.getElementById('btnSearch');
  const searchPanel = document.getElementById('searchpanel');
  const searchInput = document.getElementById('searchInput');
  const searchOut = document.getElementById('searchOut');
  let searchMark = null, searchBusy = false, searchSeq = 0;
  function toggleSearch(open) {
    const want = open !== undefined ? open : !searchPanel.classList.contains('open');
    openPanel('search', want);   // one bottom panel at a time
    if (want) searchInput.focus();
    else { searchInput.blur(); searchSeq++; searchBusy = false; }   // closing cancels an in-flight query
  }
  function searchShortName(s) {
    return String(s || '').split(',').slice(0, 3).join(',');
  }
  function searchFlyTo(x, y, z, dist, noOrbit) {
    glideCancel();   // a tour or a stop in flight would overwrite the pose next frame
    if (walk.locked && document.exitPointerLock) document.exitPointerLock();   // a locked look cancels a glide on its first movement
    // glide to a vantage looking down on the target, approaching from whichever side
    // the camera already is, then circle it (orbitAround) until the first input takes
    // flight. A live bus is followed in fly mode instead: its spot moves. No pointer
    // lock: the cursor stays free for the result list; clicking the scene takes the controls.
    const dx = camera.position.x - x, dz = camera.position.z - z;
    const L = Math.hypot(dx, dz) || 1;
    const vx = x + dx / L * dist, vy = y + dist * 0.55, vz = z + dz / L * dist;
    const yaw = Math.atan2(x - vx, -(z - vz)), pitch = -Math.atan2(vy - y, dist);
    const hop = Math.hypot(vx - camera.position.x, vz - camera.position.z);
    glideFly(vx, vy, vz, yaw, pitch, clamp(500 + hop * 0.3, 900, 2600), noOrbit ? null : () => orbitAround(x, y, z));
    setHint();
  }
  function orbitAround(x, y, z) {
    // circle the spot from where the glide parked the camera; any drag, wheel or key
    // takes flight from wherever the circle happens to be (autoFly), as after Enter
    { const c = clampLimit(x, z); if (c) { x = c[0]; z = c[1]; } }   // never a spot beyond the flight limit
    setMode(MODE.ORBIT, true);
    const p = camera.position, r = Math.max(30, Math.hypot(p.x - x, p.y - y, p.z - z));
    orbit.target.set(x, y, z); orbit.goalTarget.set(x, y, z);
    orbit.r = orbit.goalR = r;
    orbit.theta = orbit.goalTheta = Math.atan2(p.z - z, p.x - x);
    orbit.phi = orbit.goalPhi = Math.acos(clamp((p.y - y) / r, -1, 1));
    orbitSpin = !reducedMotion;
    applyOrbit(0);
    setHint();
  }
  function searchGoTo(lat, lon, name) {
    const x = (lon - SEPTA_GEO.lon0) * SEPTA_GEO.mx, z = -(lat - SEPTA_GEO.lat0) * SEPTA_GEO.mz;
    const gy = siteY(x, z, 'ground');
    searchFlyTo(x, gy + 12, z, 300);
    placeSearchMark(x, gy, z, name);
    if (isTouch) toggleSearch(false);       // free the screen; desktop keeps the result list up
  }
  function placeSearchMark(x, gy, z, name) {
    clearSearchMark();
    const mesh = new THREE.Mesh(septaPinGeom(), new THREE.MeshBasicMaterial({ vertexColors: true, color: 0xc89b5e, transparent: true, depthWrite: false, depthTest: false }));
    mesh.renderOrder = 12;                    // the search pin is a marker too
    mesh.frustumCulled = false;
    groupCity.add(mesh);
    const el = document.createElement('div');
    el.className = 'lbl smark';
    el.textContent = name;
    labelsRoot.appendChild(el);
    searchMark = { mesh, el, x, y: gy + 1.4, z, until: performance.now() + 20000 };
  }
  function clearSearchMark() {
    if (!searchMark) return;
    groupCity.remove(searchMark.mesh);
    searchMark.mesh.geometry.dispose();
    searchMark.mesh.material.dispose();
    searchMark.el.remove();
    searchMark = null;
  }
  function updateSearchMark(now) {
    if (!searchMark) return;
    if (now > searchMark.until) { clearSearchMark(); return; }
    const s = clamp(camera.position.distanceTo(_ssv.set(searchMark.x, searchMark.y, searchMark.z)) / 240, 1, 8);
    searchMark.mesh.position.set(searchMark.x, searchMark.y + Math.sin(now * 0.004) * 0.5, searchMark.z);
    searchMark.mesh.scale.setScalar(s);
    _ssv.set(searchMark.x, searchMark.y + 5.2 * s + 2, searchMark.z).project(camera);
    if (_ssv.z > 1 || _ssv.z < -1) { searchMark.el.style.opacity = '0'; return; }
    searchMark.el.style.opacity = '1';
    searchMark.el.style.transform = 'translate(-50%,-100%) translate(' +
      ((_ssv.x * 0.5 + 0.5) * window.innerWidth).toFixed(1) + 'px,' +
      ((-_ssv.y * 0.5 + 0.5) * window.innerHeight).toFixed(1) + 'px)';
  }
  // ---------------------------------------------------------------- live scores
  // A bubble over each team's venue while its game is on, home or away, and for an hour
  // after the final (Mike): ESPN's public scoreboards (CORS-open, cached a few seconds at
  // their end) for the Phillies over the ballpark, the Eagles over the Linc, the Flyers and
  // 76ers over the arena. Polled once a minute while the tab is visible; the bubble carries
  // the Philadelphia side first, the team colour on its border, the clock or inning, and
  // "away" when they are on the road. A final's hour runs from the moment the feed turned
  // it final, or, for a page that arrived later, from the start time plus a typical length.
  const SCORES = { nextT: 0, busy: false, fails: 0, games: [], els: [], pins: [], ended: {}, seenLive: {} };
  const SCORE_LEN = { mlb: 3.0 * 3600000, nfl: 3.3 * 3600000, nhl: 2.6 * 3600000, nba: 2.4 * 3600000 };
  // h: where the bubble hangs; top: the roof the pin drops to
  const SCORE_VENUES = {
    mlb: { x: -1857, z: 4383, h: 135, top: 44 }, nfl: { x: -1946, z: 4954, h: 150, top: 57 },
    nhl: { x: -2327, z: 4892, h: 115, top: 40 }, nba: { x: -2327, z: 4892, h: 115, top: 40 },
  };
  const SCORE_KEYS = ['mlb', 'nfl', 'nhl', 'nba'];
  const SCORE_URL = (k) => 'https://site.api.espn.com/apis/site/v2/sports/' + ({ mlb: 'baseball/mlb', nfl: 'football/nfl', nhl: 'hockey/nhl', nba: 'basketball/nba' })[k] + '/scoreboard';
  const _scv = new V3();
  function scoresPoll(now) {
    if (document.hidden || SCORES.busy || now < SCORES.nextT) return;
    SCORES.busy = true;
    SCORES.nextT = now + Math.min(300000, (SCORES.games.some((g) => g.live) ? 45000 : 90000) * (1 + SCORES.fails));
    Promise.all(SCORE_KEYS.map((k) => fetch(SCORE_URL(k), { signal: AbortSignal.timeout(12000) }).then((r) => (r && r.ok ? r.json() : null)).catch(() => null)))
      .then((res) => {
        const games = [];
        const nowMs = Date.now();
        let ok = 0;
        res.forEach((d, i) => {
          if (!d || !Array.isArray(d.events)) return;
          ok++;
          const k = SCORE_KEYS[i];
          for (const e of d.events) {
            const c = e.competitions && e.competitions[0];
            const st = e.status && e.status.type;
            if (!c || !st) continue;
            const us = (c.competitors || []).find((t) => t.team && t.team.abbreviation === 'PHI');
            if (!us) continue;
            const them = (c.competitors || []).find((t) => t !== us);
            const id = k + ':' + (e.id || e.date);
            const live = st.state === 'in';
            let show = live, detail = st.shortDetail || '';
            if (live) SCORES.seenLive[id] = nowMs;
            else if (st.state === 'post' || st.completed) {
              let end = SCORES.ended[id];
              if (!end) { end = SCORES.seenLive[id] ? nowMs : (Date.parse(e.date) || 0) + SCORE_LEN[k]; SCORES.ended[id] = end; }
              show = nowMs < end + 3600000;
              detail = st.shortDetail || 'Final';
            }
            if (!show) continue;
            games.push({ k, live, us: us.team.abbreviation, uscore: us.score, them: them && them.team ? them.team.abbreviation : '', tscore: them ? them.score : '', color: us.team.color, logo: us.team.logo || '', detail: detail + (us.homeAway === 'home' ? '' : ', away') });
          }
        });
        SCORES.fails = ok ? 0 : SCORES.fails + 1;
        if (ok) scoresSet(games);
        SCORES.busy = false;
      });
  }
  function scoresSet(games) {
    for (const el of SCORES.els) el.remove();
    for (const o of SCORES.pins) { groupCity.remove(o); o.geometry.dispose(); o.material.dispose(); }
    SCORES.els = []; SCORES.pins = [];
    SCORES.games = games;
    games.forEach((g, i) => {
      const el = document.createElement('div');
      el.className = 'lbl score' + (g.live ? '' : ' final');
      const ok = /^[0-9a-f]{6}$/i.test(g.color || '');
      const logo = /^https:\/\/[a-z0-9.-]*espncdn\.com\//i.test(g.logo || '') ? '<img class="logo" alt="" src="' + septaEsc(g.logo) + '" onerror="this.remove()">' : '';
      el.innerHTML = logo + '<span class="txt"><span class="live"></span>' + septaEsc(g.us + ' ' + g.uscore + ', ' + g.them + ' ' + g.tscore) + '<br>' + septaEsc(g.detail) + '</span>';
      if (ok) el.style.borderColor = '#' + g.color;
      labelsRoot.appendChild(el);
      SCORES.els.push(el);
      const v = SCORE_VENUES[g.k];
      const gy = siteY(v.x, v.z, 'ground');
      g.y = gy + v.h + (games.slice(0, i).some((o) => SCORE_VENUES[o.k] === v) ? 22 : 0);   // two at the arena stack
      // the pin: a line from the bubble down to the roof, a small ball where it lands
      const col = ok ? '#' + g.color : 0xc89b5e;
      const lg = new THREE.BufferGeometry();
      lg.setAttribute('position', new THREE.BufferAttribute(new Float32Array([v.x, g.y, v.z, v.x, gy + v.top, v.z]), 3));
      const line = new THREE.Line(lg, new THREE.LineBasicMaterial({ color: col, transparent: true, opacity: 0.9, depthTest: false, depthWrite: false }));
      line.renderOrder = 12; line.frustumCulled = false;
      const ball = new THREE.Mesh(new THREE.SphereGeometry(2.4, 10, 8), new THREE.MeshBasicMaterial({ color: col, depthTest: false, depthWrite: false }));
      ball.position.set(v.x, gy + v.top, v.z); ball.renderOrder = 12;
      groupCity.add(line); groupCity.add(ball);
      SCORES.pins.push(line, ball);
    });
  }
  function scoresRender() {
    for (let i = 0; i < SCORES.games.length; i++) {
      const g = SCORES.games[i], el = SCORES.els[i], v = SCORE_VENUES[g.k];
      _scv.set(v.x, g.y, v.z);
      const far = camera.position.distanceTo(_scv) > 14000;
      _scv.project(camera);
      if (far || _scv.z > 1 || _scv.z < -1 || _scv.x < -1.1 || _scv.x > 1.1 || _scv.y < -1.2 || _scv.y > 1.2) { el.style.opacity = '0'; continue; }
      el.style.opacity = '1';
      el.style.transform = 'translate(-50%,-100%) translate(' + ((_scv.x * 0.5 + 0.5) * window.innerWidth).toFixed(1) + 'px,' + ((-_scv.y * 0.5 + 0.5) * window.innerHeight).toFixed(1) + 'px)';
    }
  }
  function searchGoToBus(v) {
    const x = v.dx != null ? v.dx : v.x, z = v.dz != null ? v.dz : v.z;
    searchFlyTo(x, (v.gy || siteY(x, z, 'road')) + 6, z, 220, true);
    septaSetFilter(v.route, v.routeLabel);   // the map shows this route alone until the search is cleared
    pickedVeh = v;
    septaCard(v);
    vehinfoEl.hidden = false;
    if (isTouch) toggleSearch(false);
  }
  // the route filter chip: one route on the map until the search is cleared,
  // Escape closes the panel, or the chip itself is tapped
  function septaSetFilter(route, label) {
    const f = route || null;
    if (f === SEPTA.filter) return;
    SEPTA.filter = f; SEPTA.filterLabel = f ? (label || route) : '';
    const old = document.getElementById('routeChip');
    if (old) old.remove();
    if (f) {
      const el = document.createElement('div');
      el.id = 'routeChip'; el.className = 'schip'; el.setAttribute('role', 'button'); el.tabIndex = 0;
      el.textContent = 'Showing route ' + SEPTA.filterLabel + ' only, tap to clear';
      el.addEventListener('click', () => septaSetFilter(null));
      el.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); septaSetFilter(null); } });
      searchOut.prepend(el);
      if (veil.classList.contains('hidden')) {
        hintEl.textContent = 'Showing route ' + SEPTA.filterLabel + ' only. Clear it from the search panel.';
        clearTimeout(septaHintT);
        septaHintT = setTimeout(setHint, 8000);
      }
    }
    if (septaReady) septaStatus();
  }
  // the local name index: every lettered landmark, the neighborhoods and historic
  // districts, the named buildings and towers, and the painted street names, all
  // already in scene metres. Built once, on the first search.
  let nameIx = null;
  const KIND_RANK = { landmark: 0, neighborhood: 1, district: 2, building: 3, street: 4 };
  const KIND_LABEL = { landmark: 'Landmark', neighborhood: 'Neighborhood', district: 'Historic District', building: 'Building', street: 'Street' };
  function buildNameIx() {
    const ix = [], seen = new Set();
    const add = (name, x, z, kind) => {
      if (!name || !isFinite(x) || !isFinite(z)) return;
      const s = String(name), key = kind + '|' + s.toLowerCase();
      if (seen.has(key)) return;
      seen.add(key);
      ix.push({ name: s, lc: s.toLowerCase(), x, z, kind });
    };
    for (const l of labels) add(l.el.textContent, l.pos.x, l.pos.z, 'landmark');
    for (const lm of META_L) {
      const b = lm && lm.name ? findBuilding(lm.name) : null;
      if (b) { const c = polyCentroid(b.poly); add(lm.name, c[0], c[1], 'landmark'); }
    }
    if (typeof PLACES !== 'undefined' && PLACES) {
      for (const h of PLACES.hd || []) if (h && h.lbl) add(h.n, h.lbl[0], h.lbl[1], 'district');
      if (PLACES.nb && PLACES.nb.names) {
        const L = PLACES.nb.l || [];
        for (let i = 0; i + 3 < L.length; i += 4) add(PLACES.nb.names[L[i]], L[i + 1], L[i + 2], 'neighborhood');
      }
    }
    if (typeof WIDE_NAMES !== 'undefined' && WIDE_NAMES) for (const w of WIDE_NAMES) add(w.n, w.x, w.z, 'building');
    for (const b of D.buildings) if (b.name) { const c = polyCentroid(b.poly); add(b.name, c[0], c[1], 'building'); }
    if (typeof ST_LABELS !== 'undefined' && ST_LABELS && ST_LABELS.names) {
      // one point per street, the middle of its placements, so a long avenue lands mid-run
      const L = ST_LABELS.l || [], at = new Map();
      for (let i = 0; i + 4 < L.length; i += 5) { let a = at.get(L[i]); if (!a) at.set(L[i], a = []); a.push(L[i + 1], L[i + 2]); }
      at.forEach((a, ni) => { const m = (a.length >> 2) * 2; add(ST_LABELS.names[ni], a[m], a[m + 1], 'street'); });
    }
    return ix;
  }
  function searchLocal(q) {
    // prefix matches first, then substrings; within each, landmark > neighborhood
    // > district > building > street, shorter names first
    if (!nameIx) nameIx = buildNameIx();
    const lc = q.toLowerCase(), hits = [];
    for (const e of nameIx) {
      const p = e.lc.startsWith(lc) ? 0 : e.lc.includes(lc) ? 1 : -1;
      if (p >= 0) hits.push([p, KIND_RANK[e.kind], e.lc.length, e]);
    }
    hits.sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]);
    return hits.slice(0, 5).map((h) => h[3]);
  }
  function searchGoToLocal(e) {
    const gy = siteY(e.x, e.z, 'ground');
    const wide = e.kind === 'neighborhood' || e.kind === 'district';   // an area reads from higher up and needs no pin
    searchFlyTo(e.x, gy + (e.kind === 'landmark' ? 30 : 8), e.z, wide ? 600 : e.kind === 'landmark' ? 250 : 220);
    if (wide) clearSearchMark(); else placeSearchMark(e.x, gy, e.z, e.name);
    if (isTouch) toggleSearch(false);
  }
  function searchLocalSubmit(qy) {
    if (/^\d+$/.test(qy)) return false;      // a bare number is a route or a house number, never a name
    const hits = searchLocal(qy);
    if (!hits.length) return false;
    searchOut.innerHTML = '';
    for (const e of hits) {
      const el = document.createElement('div');
      el.className = 'srow';
      el.textContent = e.name + ', ' + KIND_LABEL[e.kind];
      el.addEventListener('click', () => searchGoToLocal(e));
      searchOut.appendChild(el);
    }
    searchGoToLocal(hits[0]);
    return true;
  }
  function searchRoute(rid) {
    // a bus/trolley route ("33", "G1", "route 47"): list its live vehicles, nearest first
    const live = [];
    septaVeh.forEach((v) => {
      if (!v.ug && !v.off && (v.routeLabel.toUpperCase() === rid || v.route.toUpperCase() === rid)) live.push(v);   // off: beyond the limit or off the drawn streets, neither drawn nor listed
    });
    if (!live.length) return false;
    live.forEach((v) => {
      const x = v.dx != null ? v.dx : v.x, z = v.dz != null ? v.dz : v.z;
      v._sd = (x - camera.position.x) * (x - camera.position.x) + (z - camera.position.z) * (z - camera.position.z);
    });
    live.sort((a2, b2) => a2._sd - b2._sd);
    searchOut.innerHTML = '<div class="smsg">Route ' + septaEsc(rid) + ': ' + live.length + ' Live, Nearest First</div>';
    for (const v of live.slice(0, 8)) {
      const el = document.createElement('div');
      el.className = 'srow';
      el.textContent = v.routeLabel + ' To ' + (v.info.dest || 'Unknown') + (v.info.next ? ', Next: ' + v.info.next : '');
      el.addEventListener('click', () => searchGoToBus(v));
      searchOut.appendChild(el);
    }
    searchGoToBus(live[0]);
    return true;
  }
  function searchSubmit() {
    const qy = searchInput.value.trim();
    if (!qy || searchBusy) return;
    septaSetFilter(null);                    // a new query drops the route filter; a route hit sets it again
    const rid = qy.toUpperCase().replace(/^(ROUTE|RT|BUS)\s+/, '');
    const routeish = /^[A-Z]?\d{1,3}[A-Z]?$/.test(rid);   // "33", "G1", "47M": a live route outranks a street named 33rd
    if (routeish && searchRoute(rid)) return;
    if (searchLocalSubmit(qy)) return;
    if (!routeish && searchRoute(rid)) return;
    if (!septaCanFetch) { searchOut.innerHTML = '<div class="smsg">No match in the model. Address lookup needs the live site.</div>'; return; }
    searchBusy = true;
    const seq = ++searchSeq;                // a later submit or a closed panel orphans this reply
    searchOut.innerHTML = '<div class="smsg">Searching&hellip;</div>';
    fetch('https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5&bounded=1&viewbox=-75.30,40.145,-74.94,39.855&q=' + encodeURIComponent(qy))
      .then((r) => (r && r.ok ? r.json() : null))
      .then((rows) => {
        if (seq === searchSeq) searchBusy = false;
        if (seq !== searchSeq || !searchPanel.classList.contains('open')) return;
        if (!rows) { searchOut.innerHTML = '<div class="smsg">Search failed. Try again in a moment.</div>'; return; }
        // the bounding box spans the rivers, and a name test alone lets "Philadelphia Avenue,
        // Bensalem" or the Philadelphia Country Club in Gladwyne through: keep the city
        // proper, inside the flight limit
        rows = rows.filter((r) => /philadelphia/i.test(r.display_name || '') && insideLimit((+r.lon - SEPTA_GEO.lon0) * SEPTA_GEO.mx, -(+r.lat - SEPTA_GEO.lat0) * SEPTA_GEO.mz));
        if (!rows.length) { searchOut.innerHTML = '<div class="smsg">No match inside Philadelphia.</div>'; return; }
        searchOut.innerHTML = '';
        for (const r of rows) {
          const el = document.createElement('div');
          el.className = 'srow';
          el.textContent = searchShortName(r.display_name);
          el.addEventListener('click', () => searchGoTo(+r.lat, +r.lon, el.textContent));
          searchOut.appendChild(el);
        }
        searchGoTo(+rows[0].lat, +rows[0].lon, searchShortName(rows[0].display_name));
      })
      .catch(() => {
        if (seq !== searchSeq) return;
        searchBusy = false;
        if (searchPanel.classList.contains('open')) searchOut.innerHTML = '<div class="smsg">Search failed. Try again in a moment.</div>';
      });
  }
  // wired everywhere: the local index needs no network (only Nominatim is gated above)
  btnSearch.addEventListener('click', () => toggleSearch());
  document.getElementById('searchGo').addEventListener('click', searchSubmit);
  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') searchSubmit();
    else if (e.key === 'Escape') { septaSetFilter(null); toggleSearch(false); }
    e.stopPropagation();
  });
  searchInput.addEventListener('input', () => {
    // an emptied box clears the results, and the route filter with them
    if (!searchInput.value.trim()) { septaSetFilter(null); searchOut.innerHTML = ''; }
  });

  // The Market–Frankford El's real alignment (OSM railway=subway elevated + approach
  // ways reduced to one centerline per corridor, local meters): Callowhill portal →
  // Frankford TC, and the West Market leg, 46th St portal → 69th St. Each chain
  // STARTS at its tunnel portal, so the deck ramps up out of the ground there.
  const EL_TRACK = [[286,-830,280,-933,277,-1033,283,-1167,295,-1296,315,-1434,336,-1550,370,-1683,409,-1794,432,-1847,501,-1984,602,-2143,620,-2178,641,-2237,895,-3302,1092,-4498,1099,-4515,1110,-4529,1125,-4541,1481,-4793,1632,-4905,1729,-4974,1790,-5013,2786,-5724,3276,-6069,3311,-6097,4649,-7050,4686,-7079,4711,-7107,4728,-7137,4852,-7383,5530,-8335,5584,-8412,5633,-8492,5746,-8647,5753,-8665,5751,-8687,5742,-8705,5720,-8726],[-5528,-1449,-5572,-1451,-5802,-1445,-5835,-1447,-8807,-1924,-8864,-1939,-8914,-1962,-8947,-1985,-9010,-2044,-9045,-2064,-9073,-2073,-9229,-2108,-9274,-2115,-9313,-2117,-9354,-2112,-9399,-2099,-9435,-2081,-9460,-2065,-9535,-2007,-9659,-1896,-9667,-1889,-9682,-1882,-9701,-1882,-9839,-1898,-9857,-1907,-9898,-1944,-9917,-1950,-9926,-1949,-9944,-1942,-9958,-1922,-9962,-1906]];
  step('Raising the Frankford El', () => {
    const parts = [];
    const steel = new THREE.Color(0x2a2f2b), steelDark = new THREE.Color(0x232724), railC = new THREE.Color(0x353b35);
    const boxAt = (sx, sy, sz, x, y, z, yaw, pitch, col) => {
      const g = new THREE.BoxGeometry(sx, sy, sz);
      if (pitch) g.rotateZ(pitch);
      g.rotateY(yaw);
      g.translate(x, y, z);
      parts.push({ geom: g, color: col });
    };
    for (const flat of EL_TRACK) {
      const pts = [];
      for (let i = 0; i + 3 < flat.length; i += 2) {
        const ax = flat[i], az = flat[i + 1], bx = flat[i + 2], bz = flat[i + 3];
        const n = Math.max(1, Math.round(Math.hypot(bx - ax, bz - az) / 13));
        for (let s = 0; s < n; s++) pts.push([ax + (bx - ax) * s / n, az + (bz - az) * s / n]);
      }
      pts.push([flat[flat.length - 2], flat[flat.length - 1]]);
      const ys = pts.map((p) => siteY(p[0], p[1], 'ground') + 9.2);
      for (let pass = 0; pass < 2; pass++) {           // smooth the deck profile
        const s0 = ys.slice();
        for (let i = 0; i < ys.length; i++) {
          let a = 0, n = 0;
          for (let j = Math.max(0, i - 3); j <= Math.min(ys.length - 1, i + 3); j++) { a += s0[j]; n++; }
          ys[i] = a / n;
        }
      }
      let acc = 0;                                     // portal ramp on the chain's first 170 m
      for (let i = 0; i < pts.length; i++) {
        if (i) acc += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
        if (acc >= 170) break;
        const t = smooth(10, 170, acc);
        const gy = siteY(pts[i][0], pts[i][1], 'ground');
        ys[i] = (gy - 3.4) * (1 - t) + ys[i] * t;
      }
      let bentAcc = 18;
      for (let i = 0; i + 1 < pts.length; i++) {
        const ax = pts[i][0], az = pts[i][1], bx = pts[i + 1][0], bz = pts[i + 1][1];
        const L = Math.hypot(bx - ax, bz - az);
        if (L < 0.6) continue;
        const mx = (ax + bx) / 2, mz = (az + bz) / 2, my = (ys[i] + ys[i + 1]) / 2;
        const yaw = Math.atan2(-(bz - az), bx - ax);
        const pitch = Math.atan2(ys[i + 1] - ys[i], L);
        boxAt(L + 0.55, 1.25, 8.4, mx, my - 0.62, mz, yaw, pitch, steel);       // deck
        const lx = Math.sin(yaw), lz = Math.cos(yaw);                           // lateral unit
        boxAt(L + 0.55, 0.95, 0.32, mx - lx * 3.95, my + 0.45, mz - lz * 3.95, yaw, pitch, railC);
        boxAt(L + 0.55, 0.95, 0.32, mx + lx * 3.95, my + 0.45, mz + lz * 3.95, yaw, pitch, railC);
        bentAcc += L;
        if (bentAcc >= 24) {                           // steel bents down to the street
          bentAcc = 0;
          const gy = siteY(mx, mz, 'ground');
          const top = my - 1.15;
          if (top - gy > 3.4) {
            const hcol = top - gy + 1.2;
            boxAt(0.62, hcol, 0.62, mx - lx * 3.5, gy - 0.8 + hcol / 2, mz - lz * 3.5, yaw, 0, steelDark);
            boxAt(0.62, hcol, 0.62, mx + lx * 3.5, gy - 0.8 + hcol / 2, mz + lz * 3.5, yaw, 0, steelDark);
            boxAt(0.7, 0.85, 7.9, mx, my - 1.55, mz, yaw, pitch, steelDark);    // cross girder
          }
        }
      }
    }
    const el = new THREE.Mesh(mergeColored(parts), new THREE.MeshLambertMaterial({ vertexColors: true }));
    el.castShadow = true;
    el.receiveShadow = true;
    groupCity.add(el);
  });

  step('Rolling out the SEPTA fleet', () => {
    if (!septaCanFetch) { btnTransit.style.display = 'none'; return; }
    // Night look: only the glass band + windshield glow (aGlow mask), the body
    // keeps a faint presence — a flat material-wide emissive washed every bus
    // to a solid white brick after dark.
    const bodyMat = new THREE.MeshLambertMaterial({ vertexColors: true });
    bodyMat.onBeforeCompile = (shader) => {
      shader.uniforms.uNight = nightUniform;
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nattribute float aGlow;\nvarying float vGlow;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nvGlow = aGlow;');
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', '#include <common>\nuniform float uNight;\nvarying float vGlow;')
        .replace('#include <emissivemap_fragment>',
          '#include <emissivemap_fragment>\ntotalEmissiveRadiance += (vec3(1.0, 0.85, 0.62) * vGlow * 0.8 + vec3(0.30, 0.29, 0.27) * 0.10) * uNight;');
    };
    septaMats.body = bodyMat;
    // markers are wayfinding, not scenery: no depth test, so a pin or badge is
    // never swallowed by the skyline (Mike's rule; the vehicles themselves stay
    // solid and occludable)
    // buildings occlude the fleet markers (Mike reversed the x-ray call, Aug 25 evening)
    const badgeMat = new THREE.MeshBasicMaterial({ map: septaBadgeTexture(), transparent: true, depthWrite: false });
    septaSolid = new THREE.InstancedMesh(septaVehGeom(true), bodyMat, 1600);
    septaBadge = new THREE.InstancedMesh(new THREE.PlaneGeometry(4.6, 5.75).translate(0, 2.95, 0), badgeMat, 1024);
    for (const m of [septaSolid, septaBadge]) {
      m.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      m.count = 0;
      m.frustumCulled = false;                         // instance bounds don't follow the fleet
      if (m !== septaBadge) {                          // the badge keeps its texture colors
        m.setColorAt(0, _sc.setRGB(1, 1, 1));          // allocates instanceColor
        m.instanceColor.setUsage(THREE.DynamicDrawUsage);
      }
    }
    septaSolid.castShadow = true;
    septaSolid.receiveShadow = true;
    septaBadge.renderOrder = 12;                       // transparent cutout, after the opaques
    groupCity.add(septaSolid);
    groupCity.add(septaBadge);
    septaReady = true;
    syncTransitBtn();
    setInterval(() => septaPoll(false), SEPTA_POLL);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) septaPoll(false); });
    septaPoll(true);
  });

  // ---------------------------------------------------------------- live Indego bike share
  // Station status from Indego's public feed (Bicycle Transit Systems' worker;
  // CORS-open, server-cached 60 s), the bike-share counterpart to the SEPTA
  // fleet: fixed docks on their real sidewalks, each rack filled with its
  // actual bikes — classic and electric — and a count badge overhead. Same
  // hostname gate as SEPTA: silently absent under the claude.ai artifact CSP.
  const INDEGO_URL = 'https://bts-status.bicycletransit.workers.dev/phl';
  const INDEGO_POLL = 60000;                        // the feed itself is cached 60 s
  const INDEGO_CAP = { st: 400, bk: 2600 };
  const INDEGO = { on: true, ok: false, fails: 0, nextT: 0, busy: false, nFeat: 0, sig: '' };
  const indegoSt = new Map();
  const indegoList = [];                            // badge-tile order, stable per session
  const indegoTile = new Map();                     // id -> list entry: a station back from a dropout keeps its tile
  let indegoLive = [];                              // filtered draw order, rebuilt per poll
  let indegoReady = false, indegoDirty = false, indegoSolid = null, indegoBike = null, indegoBadge = null;
  let indegoTex = null, indegoCtx = null, pickedStation = null;
  const indegoPickS = [], indegoPickK = [], indegoPickB = [];
  const btnIndego = document.getElementById('btnIndego');
  const _iq = new THREE.Quaternion(), _iqB = new THREE.Quaternion();
  function indegoStationGeom() {
    // unit dock along x (1.0 scales to the rack's length); y/z in meters.
    // Platform slab + low rack spine + kiosk pylon whose screen glows at night
    // through the fleet material's aGlow term.
    const parts = [];
    const box = (sx, sy, sz, cx, cy, cz, cr, cg, cb, glow) =>
      parts.push(septaColored(new THREE.BoxGeometry(sx, sy, sz).translate(cx, cy, cz), cr, cg, cb, glow));
    box(1.0, 0.08, 2.1, 0, 0.04, 0, 0.58, 0.56, 0.51);          // platform slab
    box(0.94, 0.07, 0.12, 0, 0.34, 0, 1, 1, 1);                 // rack spine (instance color)
    box(0.02, 0.26, 0.1, -0.24, 0.17, 0, 0.45, 0.46, 0.47);     // spine legs
    box(0.02, 0.26, 0.1, 0.24, 0.17, 0, 0.45, 0.46, 0.47);
    box(0.035, 1.85, 0.42, -0.485, 0.93, 0.62, 0.5, 0.49, 0.45); // kiosk pylon
    box(0.03, 0.34, 0.3, -0.47, 1.38, 0.62, 0.95, 0.93, 0.82, 1); // kiosk screen
    return septaMerge(parts);
  }
  function indegoBikeGeom() {
    // ~90-tri parked bike facing +x: two wheels, frame tubes, seat, bars
    const parts = [];
    const wheel = (cx) => {
      const c = new THREE.CylinderGeometry(0.3, 0.3, 0.045, 7);
      c.rotateX(Math.PI / 2);
      c.translate(cx, 0.3, 0);
      parts.push(septaColored(c, 0.12, 0.12, 0.13));
    };
    wheel(-0.42);
    wheel(0.42);
    const box = (sx, sy, sz, cx, cy, cz, cr, cg, cb) =>
      parts.push(septaColored(new THREE.BoxGeometry(sx, sy, sz).translate(cx, cy, cz), cr, cg, cb));
    const g1 = new THREE.BoxGeometry(0.72, 0.055, 0.045);        // down tube, hub to hub
    g1.rotateZ(0.16);
    g1.translate(0, 0.52, 0);
    parts.push(septaColored(g1, 1, 1, 1));
    box(0.05, 0.34, 0.045, -0.34, 0.72, 0, 1, 1, 1);             // seat post
    box(0.05, 0.42, 0.045, 0.38, 0.78, 0, 1, 1, 1);              // head tube
    box(0.2, 0.045, 0.06, -0.36, 0.9, 0, 0.14, 0.14, 0.15);      // saddle
    box(0.05, 0.045, 0.42, 0.4, 1.0, 0, 0.14, 0.14, 0.15);       // handlebar
    return septaMerge(parts);
  }
  function indegoBolt(g, x, y, s) {
    g.beginPath();
    g.moveTo(x + 0.45 * s, y - 0.95 * s);
    g.lineTo(x - 0.35 * s, y + 0.12 * s);
    g.lineTo(x + 0.02 * s, y + 0.12 * s);
    g.lineTo(x - 0.3 * s, y + 0.95 * s);
    g.lineTo(x + 0.5 * s, y - 0.12 * s);
    g.lineTo(x + 0.1 * s, y - 0.12 * s);
    g.closePath();
    g.fill();
  }
  function indegoDrawTiles() {
    // one shared 128 px-tile atlas (32x16 slots), repainted whole each poll:
    // paper coin + live count, ring in Indego blue, amber bolt for e-bikes
    if (!indegoCtx) return;
    // the 4096x2048 atlas is a 33 MB re-upload: skip it when no count moved
    // (the badge font joins the key so its late arrival still repaints)
    let sig = '';
    try { sig = document.fonts.check('700 44px "Montserrat"') ? 'F' : 'f'; } catch (e) { /* stack fallback */ }
    for (const st of indegoList) if (indegoSt.has(st.id)) sig += st.tile + (st.act ? 'a' : 'x') + st.bikes + '|' + st.ebikes + ';';
    if (sig === INDEGO.sig) return;
    INDEGO.sig = sig;
    const g = indegoCtx;
    g.clearRect(0, 0, 4096, 2048);
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    for (const st of indegoList) {
      if (!indegoSt.has(st.id)) continue;
      const tx = (st.tile % 32) * 128 + 64, ty = ((st.tile / 32) | 0) * 128;
      g.strokeStyle = 'rgba(28,26,22,0.6)';
      g.fillStyle = '#fdfbf6';
      g.lineWidth = 6;
      g.beginPath();                                  // pointer tip, coin overlaps it
      g.moveTo(tx - 13, ty + 88);
      g.lineTo(tx, ty + 120);
      g.lineTo(tx + 13, ty + 88);
      g.closePath();
      g.fill();
      g.stroke();
      g.beginPath();
      g.arc(tx, ty + 48, 40, 0, Math.PI * 2);
      g.fill();
      g.strokeStyle = st.act ? (st.bikes ? '#0ea3c4' : '#98a0a4') : '#565b5e';
      g.stroke();
      g.fillStyle = '#22201c';
      const hasE = st.act && st.ebikes > 0;
      g.font = '700 44px "Montserrat", "Avenir Next", "Segoe UI", sans-serif';
      g.fillText(st.act ? String(st.bikes) : '–', tx, ty + (hasE ? 40 : 49));
      if (hasE) {
        g.fillStyle = '#b97a17';
        indegoBolt(g, tx - 12, ty + 71, 10);
        g.font = '600 24px "Montserrat", "Avenir Next", "Segoe UI", sans-serif';
        g.fillText(String(st.ebikes), tx + 10, ty + 72);
      }
    }
    indegoTex.needsUpdate = true;
  }
  function indegoGot(d) {
    const feats = d && d.features;
    if (!Array.isArray(feats) || !feats.length) { indegoFail(); return; }
    // a payload under half the last one is a truncated feed, not a mass closure:
    // count it as a miss and keep the docks (three misses running and we believe it)
    if (feats.length < INDEGO.nFeat / 2 && INDEGO.fails < 3) { indegoFail(); return; }
    INDEGO.nFeat = feats.length;
    const alive = new Set();
    for (const f of feats) {
      const p = f && f.properties, c = f && f.geometry && f.geometry.coordinates;
      if (!p || !c) continue;
      const lon = +c[0], lat = +c[1];
      if (!(lat > SEPTA_BOX.la0 && lat < SEPTA_BOX.la1 && lon > SEPTA_BOX.lo0 && lon < SEPTA_BOX.lo1)) continue;
      const id = String(p.kioskId || p.id || p.name || '');
      if (!id) continue;
      alive.add(id);
      let st = indegoSt.get(id);
      if (!st && indegoTile.has(id) && indegoSt.size < INDEGO_CAP.st) { st = indegoTile.get(id); indegoSt.set(id, st); }
      if (!st) {
        if (indegoSt.size >= INDEGO_CAP.st || indegoList.length >= 512) continue;
        const x = (lon - SEPTA_GEO.lon0) * SEPTA_GEO.mx, z = -(lat - SEPTA_GEO.lat0) * SEPTA_GEO.mz;
        if (!isFinite(x) || !isFinite(z)) continue;
        // orientation only from the road grid — the surveyed position is right,
        // the dock just wants to sit parallel to its street
        const sn = septaSnapRoad(x, z, 30);
        st = { id, x, z, y: siteY(x, z, 'ground'), dx: sn ? sn[2] : 1, dz: sn ? sn[3] : 0, tile: indegoList.length };
        indegoList.push(st);
        indegoTile.set(id, st);
        indegoSt.set(id, st);
      }
      st.name = p.name || 'Indego Station';
      st.addr = p.addressStreet || '';
      st.bikes = +p.bikesAvailable || 0;
      st.classic = +p.classicBikesAvailable || 0;
      st.ebikes = +p.electricBikesAvailable || 0;
      st.docksOpen = +p.docksAvailable || 0;
      st.docks = +p.totalDocks || 0;
      st.act = p.kioskPublicStatus === 'Active';
      st.slots = Array.isArray(p.bikes) ? p.bikes : null;
      let bSum = 0, bN = 0;
      if (st.slots) for (const b of st.slots) if (b && b.isElectric && b.isAvailable && b.battery != null) { bSum += +b.battery || 0; bN++; }
      st.eAvg = bN ? Math.round(bSum / bN) : null;
    }
    indegoSt.forEach((st, id) => {
      if (!alive.has(id)) {
        indegoSt.delete(id);
        if (pickedStation === st) { pickedStation = null; vehinfoEl.hidden = true; }
      }
    });
    INDEGO.ok = true; INDEGO.fails = 0; INDEGO.nextT = performance.now() + 20000;   // floor under the tab-return re-poll
    indegoDirty = true;
    indegoDrawTiles();
    indegoStatus();
    if (pickedStation) indegoCard(pickedStation);
  }
  function indegoFail() {
    INDEGO.fails++;
    INDEGO.nextT = performance.now() + INDEGO_POLL * Math.min(8, Math.pow(2, INDEGO.fails));
  }
  function indegoPoll(force) {
    if (!INDEGO.on || !septaCanFetch || !indegoReady) return;
    if (document.hidden && !force) return;
    if (!force && performance.now() < INDEGO.nextT) return;
    if (INDEGO.busy) return;                          // one fetch in flight
    INDEGO.busy = true;
    const ctl = new AbortController();
    const tm = setTimeout(() => ctl.abort(), 15000);
    fetch(INDEGO_URL, { signal: ctl.signal })
      .then((r) => (r && r.ok ? r.json() : null))
      .then((d) => { clearTimeout(tm); INDEGO.busy = false; if (d) indegoGot(d); else indegoFail(); })
      .catch(() => { clearTimeout(tm); INDEGO.busy = false; indegoFail(); });
  }
  function indegoCard(st) {
    const lines = [st.classic + ' Classic, ' + st.ebikes + ' Electric, ' + st.docksOpen + (st.docksOpen === 1 ? ' Dock Open' : ' Docks Open')];
    if (st.eAvg != null) lines.push('E-Bikes Average ' + st.eAvg + '% Charge');
    if (!st.act) lines.push('Station Unavailable');
    else if (!st.docksOpen) lines.push('Station Full, No Docks Open');
    if (st.addr) lines.push(st.addr);
    vehinfoBody.innerHTML =
      '<span class="vroute" style="background:#1289a8">' + (st.act ? st.bikes : '–') + '</span>' +
      '<span class="vdest">' + septaEsc(st.name) + '</span>' +
      lines.map((l) => '<div class="vmeta">' + septaEsc(l) + '</div>').join('');
  }
  function indegoStatus() {
    let bikes = 0;
    indegoSt.forEach((st) => { bikes += st.bikes; });
    btnIndego.title = 'Indego Bike Share (B): ' + bikes + ' Bikes At ' + indegoSt.size + ' Stations';
    const ic = document.getElementById('indegoCount');
    if (ic) ic.textContent = indegoSt.size ? String(bikes) : '';
  }
  function syncIndegoBtn() { syncLayerBtn(btnIndego, INDEGO.on); }
  function toggleIndego() {
    if (!septaCanFetch) return;
    INDEGO.on = !INDEGO.on;
    syncIndegoBtn();
    if (INDEGO.on) { indegoDirty = true; indegoPoll(true); }
    else if (pickedStation) { pickedStation = null; vehinfoEl.hidden = true; }
  }
  btnIndego.addEventListener('click', toggleIndego);
  function indegoRebuild() {
    // matrices move only when the data does — this runs per poll, not per frame
    indegoLive = [];
    let si = 0, ki = 0;
    for (const st of indegoList) {
      if (!indegoSt.has(st.id) || si >= INDEGO_CAP.st) continue;
      const rackL = clamp((st.docks || 12) * 0.42, 4, 20);
      st.rackL = rackL;
      const yaw = Math.atan2(-st.dz, st.dx);
      _iq.setFromAxisAngle(_sup, yaw);
      _sp.set(st.x, st.y, st.z);
      _ss.set(rackL, 1, 1);
      _sm.compose(_sp, _iq, _ss);
      indegoSolid.setMatrixAt(si, _sm);
      indegoSolid.setColorAt(si, _sc.setHex(st.act ? (st.bikes ? 0x11758c : 0x565e63) : 0x3a3f42));
      indegoPickS[si] = st;
      indegoBadge.geometry.attributes.aTile.setXY(si, (st.tile % 32) / 32, 1 - (((st.tile / 32) | 0) + 1) / 16);
      indegoPickB[si] = st;
      indegoLive.push(st);
      si++;
      if (st.slots) {
        for (const b of st.slots) {
          if (!b || ki >= INDEGO_CAP.bk) continue;
          const dn = clamp(+b.dockNumber || 1, 1, Math.max(1, st.docks || 1));
          const t = (dn - 0.5) / Math.max(1, st.docks || 1) - 0.5;
          const side = dn % 2 ? 1 : -1;
          const nx = -st.dz * side, nz = st.dx * side;
          _iq.setFromAxisAngle(_sup, Math.atan2(-nz, nx));
          _sp.set(st.x + st.dx * t * rackL + nx * 0.58, st.y + 0.06, st.z + st.dz * t * rackL + nz * 0.58);
          _ss.set(1, 1, 1);
          _sm.compose(_sp, _iq, _ss);
          indegoBike.setMatrixAt(ki, _sm);
          indegoBike.setColorAt(ki, _sc.setHex(b.isAvailable === false ? 0x4b4f52 : b.isElectric ? 0x2c8ca3 : 0x11758c));
          indegoPickK[ki] = st;
          ki++;
        }
      }
    }
    indegoSolid.count = si;
    indegoBike.count = ki;
    indegoBadge.count = si;
    flushInst(indegoSolid);
    flushInst(indegoBike);
    indegoBadge.geometry.attributes.aTile.needsUpdate = true;
  }
  function updateIndego(now, dt) {
    if (!indegoReady) return;
    if (!INDEGO.on) {
      if (indegoSolid.count || indegoBike.count || indegoBadge.count) {
        indegoSolid.count = 0; indegoBike.count = 0; indegoBadge.count = 0;
      }
      return;
    }
    if (indegoDirty) { indegoDirty = false; indegoRebuild(); }
    // badges billboard the camera every frame; no bob — docks are furniture,
    // bobbing is the vehicles' signature. Own quaternion copy: _sqB is only
    // fresh while the SEPTA layer is on.
    _iqB.copy(camera.quaternion);
    for (let i = 0; i < indegoLive.length; i++) {
      const st = indegoLive[i];
      _sp.set(st.x, st.y + 3.1, st.z);
      const s = clamp(camera.position.distanceTo(_sp) / 135, 2.2, 14);
      _ss.set(s, s, s);
      _sm.compose(_sp, _iqB, _ss);
      indegoBadge.setMatrixAt(i, _sm);
    }
    flushInst(indegoBadge);
    if (pickedStation) {
      _ssv.set(pickedStation.x, pickedStation.y + 6, pickedStation.z).project(camera);
      if (_ssv.z > 1 || _ssv.z < -1) vehinfoEl.style.opacity = '0';
      else {
        vehinfoEl.style.opacity = '1';
        vehinfoEl.style.transform = 'translate(-50%,-100%) translate(' +
          ((_ssv.x * 0.5 + 0.5) * window.innerWidth).toFixed(1) + 'px,' +
          ((-_ssv.y * 0.5 + 0.5) * window.innerHeight).toFixed(1) + 'px)';
      }
    }
  }
  step('Docking the Indego bikes', () => {
    if (!septaCanFetch) { btnIndego.style.display = 'none'; return; }
    const cv = document.createElement('canvas');
    cv.width = 4096; cv.height = 2048;
    indegoCtx = cv.getContext('2d');
    indegoTex = new THREE.CanvasTexture(cv);
    indegoTex.encoding = THREE.sRGBEncoding;
    indegoTex.anisotropy = anisoOf(4);
    try { document.fonts.load('700 44px "Montserrat"').catch(() => {}); } catch (e) { /* stack fallback */ }
    const badgeMat = new THREE.MeshBasicMaterial({ map: indegoTex, transparent: true, depthWrite: false });  // occluded by buildings like the SEPTA markers
    badgeMat.onBeforeCompile = (shader) => {
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nattribute vec2 aTile;')
        .replace('#include <uv_vertex>', 'vUv = uv * vec2(0.03125, 0.0625) + aTile;');
    };
    const bodyMat = septaMats.body || new THREE.MeshLambertMaterial({ vertexColors: true });
    indegoSolid = new THREE.InstancedMesh(indegoStationGeom(), bodyMat, INDEGO_CAP.st);
    indegoBike = new THREE.InstancedMesh(indegoBikeGeom(), bodyMat, INDEGO_CAP.bk);
    const bg = new THREE.PlaneGeometry(4.4, 4.4).translate(0, 2.6, 0);
    const aTile = new THREE.InstancedBufferAttribute(new Float32Array(INDEGO_CAP.st * 2), 2);
    aTile.setUsage(THREE.DynamicDrawUsage);
    bg.setAttribute('aTile', aTile);
    indegoBadge = new THREE.InstancedMesh(bg, badgeMat, INDEGO_CAP.st);
    for (const m of [indegoSolid, indegoBike, indegoBadge]) {
      m.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      m.count = 0;
      m.frustumCulled = false;                        // instance bounds don't follow the docks
      if (m !== indegoBadge) {
        m.setColorAt(0, _sc.setRGB(1, 1, 1));         // allocates instanceColor
        m.instanceColor.setUsage(THREE.DynamicDrawUsage);
      }
    }
    indegoSolid.castShadow = true;
    indegoSolid.receiveShadow = true;
    indegoBike.castShadow = true;
    indegoBadge.renderOrder = 12;
    groupCity.add(indegoSolid);
    groupCity.add(indegoBike);
    groupCity.add(indegoBadge);
    indegoReady = true;
    syncIndegoBtn();
    setInterval(() => indegoPoll(false), INDEGO_POLL);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) indegoPoll(false); });
    indegoPoll(true);
  });

  step('Charting the viewpoints', () => {
    // city-scale stops for the 'Take me to' rows and the tour (the old Society
    // Hill orbit set is retired; addViewpoint still feeds the tour in order).
    // Scene-local metres: a camera a few hundred metres back [x, z, height
    // above its ground] aimed at a target [x, z, height above its ground]; yaw
    // and pitch fall out of the delta the way applyFly reads them (yaw 0 north,
    // pitch up positive).
    const tc = towersCenter;
    const geo = (la, lo) => [(lo - SEPTA_GEO.lon0) * SEPTA_GEO.mx, -(la - SEPTA_GEO.lat0) * SEPTA_GEO.mz];
    const ih = geo(39.94883, -75.15003);      // Independence Hall, the label's fix
    const bb = geo(39.93951, -75.13309);      // USS New Jersey at her Camden moorings
    const STOPS = [
      ['cityhall', 'City Hall', [-1560, -280, 140], [-1603, -802, 95]],                          // up Broad Street from the south
      ['schuylkill', 'Schuylkill Skyline', [-3150, -900, 80], [-2250, -950, 150]],                // from the river, looking east
      ['artmuseum', 'Art Museum Steps', [-2823, -1966, 70], [-3112, -2242, 30]],                  // up the Parkway
      ['towers', 'Society Hill Towers', [470, 120, 160], [tc.x, tc.z, 60]],                        // from over the Delaware
      ['indhall', 'Independence Hall', [ih[0], ih[1] - 420, 100], [ih[0], ih[1], 25]],           // across the Mall, looking south
      ['battleship', 'Battleship New Jersey', [bb[0] - 330, bb[1] + 200, 80], [bb[0], bb[1], 12]],   // from mid-river
      ['airport', 'Airport Approach', [-6934, 8107, 210], [-8334, 7857, 15]],                     // on final from the east
      ['wissahickon', 'The Wissahickon', [-6800, -8950, 260], [-5866, -9346, 40]],                // over Manayunk into the gorge
    ];
    const poseOf = ([, , [px, pz, ph], [tx, tz, th]]) => {
      const py = siteY(px, pz, 'ground') + ph, ty = siteY(tx, tz, 'ground') + th;
      const dx = tx - px, dz = tz - pz;
      return { px, py, pz, yaw: Math.atan2(dx, -dz), pitch: Math.atan2(ty - py, Math.hypot(dx, dz)) };
    };
    for (const s of STOPS) {
      addViewpoint(s[1], (onLand) => {
        const p = poseOf(s);
        const d = Math.hypot(p.px - camera.position.x, p.pz - camera.position.z);
        glideFly(p.px, p.py, p.pz, p.yaw, p.pitch, 2500 + Math.min(2500, d * 0.2), onLand);   // ~2.5 s, up to 5 s across the city
      });
      const vp = viewpoints[viewpoints.length - 1];
      const row = layersPanel.querySelector('[data-stop="' + s[0] + '"]');
      if (row) row.addEventListener('click', () => {
        tourStop();
        vp.fn();
        if (isTouch) closePanels();   // free the screen; desktop keeps the list up
      });
    }
    if (btnTour) btnTour.addEventListener('click', () => { if (tour.on) glideCancel(); else tourStart(); });   // cancel the hop in flight too
  });

  // labels + about wiring
  const btnLabels = document.getElementById('btnLabels');
  function syncLabelsBtn() { syncLayerBtn(btnLabels, labelsOn); }
  function toggleLabels() {
    labelsOn = !labelsOn;
    syncLabelsBtn();
  }
  btnLabels.addEventListener('click', toggleLabels);
  syncLabelsBtn();
  const about = document.getElementById('about');
  function syncAboutInert() { try { about.inert = !about.classList.contains('open'); } catch (e) { } }
  function toggleAbout() { about.classList.toggle('open'); syncAboutInert(); }
  function openAbout() { about.classList.add('open'); syncAboutInert(); }
  function closeAbout() { about.classList.remove('open'); syncAboutInert(); }
  syncAboutInert();
  document.getElementById('btnAbout').addEventListener('click', toggleAbout);
  document.getElementById('btnCloseAbout').addEventListener('click', closeAbout);
  // the i button stays hidden; the credit line's "credits" link is the way in
  // (Escape and the close button still close it, see the keydown handler)
  const creditsLink = document.getElementById('creditsLink');
  if (creditsLink) creditsLink.addEventListener('click', (e) => { e.preventDefault(); openAbout(); });


  // ---------------------------------------------------------------- live flights
  // Real ADS-B traffic over the city and into PHL, from the adsb.fi community
  // feed (open data, but no CORS headers), fetched through a passthrough.
  // Aug 2026: the free public passthroughs have all but died out (allorigins
  // and codetabs 522 from dead backends, corsproxy.io paywalled), so the
  // reliable path is a personal proxy. Since Round 31 that's Mike's own VPS:
  // nginx on philly3d.com fronts the same adsb.fi query with an 8 s shared
  // cache and ACAO *, feeding this page on BOTH homes (philly3d.com is
  // same-origin; GitHub Pages rides the CORS header). 10 s cadence. If that
  // box ever goes away, flight-proxy-worker.js is the paste-ready fallback.
  // Silent under the artifact CSP like every live layer.
  const FLIGHT_PROXY = 'https://philly3d.com/adsb';
  const FLIGHT_TGT = 'https://opendata.adsb.fi/api/v2/lat/39.872/lon/-75.241/dist/30';
  // the public passthroughs stay in rotation behind the proxy slot: dead as of
  // Aug 2026 but they have a habit of resurrecting — rotate to the next after
  // two straight failures (one blip on the proxy must not walk the whole dead
  // list, ~50 s of dead reckoning) and stay with whichever answers
  const FLIGHT_HOSTS = [
    FLIGHT_PROXY,
    'https://api.allorigins.win/raw?url=' + encodeURIComponent(FLIGHT_TGT),
    'https://api.codetabs.com/v1/proxy?quest=' + encodeURIComponent(FLIGHT_TGT),
  ].filter(Boolean);
  const FLIGHTS = { on: true, ok: false, fails: 0, hostFails: 0, nextT: 0, busy: false, host: 0 };
  const flightMap = new Map();
  let flightMesh = null, flightStrobe = null, flightPin = null, flightPinH = null, heliMesh = null, heliRotor = null, flightReady = false, pickedPlane = null;
  const flightPick = [], heliPick = [];
  const _fqSpin = new THREE.Quaternion(), _fqR = new THREE.Quaternion();
  const FLIGHT_UP = new THREE.Vector3(0, 1, 0);
  const FLIGHT_CAP = 80;
  const btnFlights = document.getElementById('btnFlights');
  const _fq = new THREE.Quaternion(), _fe = new THREE.Euler();
  // one upload helper for every InstancedMesh (SEPTA, Indego, flights, ships,
  // cars): upload only the live instances. three's default range is the whole
  // capacity buffer and it snaps back to "all" after every ranged upload, so
  // the range is restated before each flag. colorFrom omitted ships every live
  // instanceColor; colorFrom >= 0 ships from that slot up; -1 skips colours.
  // A zero count skips entirely (a 0-length range means "everything" on WebGL2).
  function flushInst(m, colorFrom) {
    const n = m.count;
    if (!n) return;
    m.instanceMatrix.updateRange.offset = 0;
    m.instanceMatrix.updateRange.count = n * 16;
    m.instanceMatrix.needsUpdate = true;
    const from = colorFrom === undefined ? 0 : colorFrom;
    if (from >= 0 && from < n && m.instanceColor) {
      m.instanceColor.updateRange.offset = from * 3;
      m.instanceColor.updateRange.count = (n - from) * 3;
      m.instanceColor.needsUpdate = true;
    }
  }
  // the flight and ship cards rebuild every frame; innerHTML only re-parses
  // when the text actually changes. Keyed on the picked object and the string,
  // plus the node we wrote: any other card (bus, station, tree) landing in the
  // same element between two picks of the same object invalidates it.
  let cardObj = null, cardHtml = '', cardNode = null;
  function cardSet(obj, html) {
    if (obj === cardObj && html === cardHtml && vehinfoBody.firstChild === cardNode) return;
    cardObj = obj; cardHtml = html;
    vehinfoBody.innerHTML = html;
    cardNode = vehinfoBody.firstChild;
  }
  const FLIGHT_LEN = { A1: 12, A2: 24, A3: 38, A4: 48, A5: 64, A7: 12 };
  // rotorcraft: ADS-B category A7 when broadcast, else the common type codes
  // (police, medevac, news, tours — the Delaware corridor sees plenty)
  const HELI_TYPES = new Set(['R22', 'R44', 'R66', 'B06', 'B06T', 'B105', 'B212', 'B407', 'B412', 'B429', 'B430', 'B505',
    'EC20', 'EC30', 'EC35', 'EC45', 'EC55', 'EC75', 'EC120', 'EC130', 'EC135', 'EC145', 'EC155', 'EC175',
    'H125', 'H130', 'H135', 'H145', 'H155', 'H160', 'H269', 'H500', 'H60', 'UH1', 'UH1Y', 'UH60',
    'S61', 'S64', 'S70', 'S76', 'S92', 'A109', 'A119', 'A129', 'A139', 'A149', 'A169', 'A189',
    'AS32', 'AS50', 'AS55', 'AS65', 'MD52', 'MD60', 'EN28', 'EN48']);
  function flightGeom() {
    // ~120-tri airliner, nose toward +x, unit length 1 (instance scale = meters)
    const parts = [];
    const box = (sx, sy, sz, cx, cy, cz, r, g, b, glow, ry) => {
      const bg = new THREE.BoxGeometry(sx, sy, sz);
      if (ry) bg.rotateY(ry);
      bg.translate(cx, cy, cz);
      parts.push(septaColored(bg, r, g, b, glow || 0));
    };
    box(1.0, 0.085, 0.085, 0, 0, 0, 0.80, 0.81, 0.84);            // fuselage
    box(0.14, 0.07, 0.075, 0.47, 0.008, 0, 0.35, 0.38, 0.44);     // cockpit
    box(0.56, 0.02, 0.09, 0.03, 0.012, 0, 1, 0.93, 0.72, 1);      // cabin glow band
    box(0.15, 0.012, 0.5, 0.03, -0.02, 0.24, 0.72, 0.73, 0.76, 0, -0.5);   // wings, swept
    box(0.15, 0.012, 0.5, 0.03, -0.02, -0.24, 0.72, 0.73, 0.76, 0, 0.5);
    box(0.1, 0.045, 0.05, 0.1, -0.055, 0.17, 0.5, 0.51, 0.54);    // engines
    box(0.1, 0.045, 0.05, 0.1, -0.055, -0.17, 0.5, 0.51, 0.54);
    box(0.08, 0.01, 0.16, -0.44, 0.02, 0.09, 0.72, 0.73, 0.76, 0, -0.4);   // tailplane
    box(0.08, 0.01, 0.16, -0.44, 0.02, -0.09, 0.72, 0.73, 0.76, 0, 0.4);
    box(0.14, 0.15, 0.012, -0.45, 0.1, 0, 0.68, 0.70, 0.74, 0, 0); // fin
    return septaMerge(parts);
  }
  function heliGeom() {
    // light helicopter, nose toward +x, unit length 1 (instance scale = meters):
    // cabin pod, canopy, boom, fin, skids — the main rotor is its own spinning
    // InstancedMesh, so it is NOT part of this geometry
    const parts = [];
    const box = (sx, sy, sz, cx, cy, cz, r, g, b, glow) => {
      const bg = new THREE.BoxGeometry(sx, sy, sz);
      bg.translate(cx, cy, cz);
      parts.push(septaColored(bg, r, g, b, glow || 0));
    };
    box(0.4, 0.17, 0.17, 0.09, 0, 0, 0.88, 0.88, 0.9);             // cabin pod
    box(0.13, 0.13, 0.15, 0.3, 0.005, 0, 0.16, 0.18, 0.22, 1);     // canopy glass, lit at night
    box(0.15, 0.055, 0.11, -0.02, 0.1, 0, 0.55, 0.57, 0.6);        // engine cowl
    box(0.02, 0.06, 0.02, 0.06, 0.135, 0, 0.2, 0.2, 0.22);         // rotor mast
    box(0.42, 0.04, 0.04, -0.3, 0.035, 0, 0.8, 0.8, 0.83);         // tail boom
    box(0.055, 0.15, 0.012, -0.485, 0.08, 0, 0.72, 0.2, 0.18);     // tail fin, warning red
    box(0.012, 0.12, 0.018, -0.5, 0.1, 0.028, 0.25, 0.25, 0.28);   // tail rotor
    for (const sz of [-0.085, 0.085]) {
      box(0.34, 0.013, 0.016, 0.06, -0.12, sz, 0.35, 0.36, 0.4);   // skids
      box(0.012, 0.06, 0.014, -0.04, -0.09, sz, 0.35, 0.36, 0.4);  // struts
      box(0.012, 0.06, 0.014, 0.17, -0.09, sz, 0.35, 0.36, 0.4);
    }
    return septaMerge(parts);
  }
  function heliRotorGeom() {
    // two crossed blades; spun about local Y each frame by updateFlights
    const a = new THREE.BoxGeometry(0.92, 0.008, 0.04);
    const b = new THREE.BoxGeometry(0.04, 0.008, 0.92);
    a.translate(0.06, 0.165, 0); b.translate(0.06, 0.165, 0);
    return septaMerge([septaColored(a, 0.16, 0.16, 0.18, 0), septaColored(b, 0.16, 0.16, 0.18, 0)]);
  }
  function flightPinTexture(kind) {
    // aircraft pins share one badge casing (the SEPTA marker's shape, navy body
    // in a warm-white frame — the Round 29c pale-halo trick that reads against
    // noon sky and midnight alike). Fixed wing wears a generic top-view
    // airplane (the layers-panel glyph, so panel and sky agree); rotorcraft
    // wear a chunky side-view helicopter. Both bold white with one sky-blue
    // accent — no lettering, nothing to squint at from across the model.
    const cv = document.createElement('canvas');
    cv.width = 256; cv.height = 320;
    const g = cv.getContext('2d');
    const bw = 240, bh = 200, bx = 8, by = 8, rad = 34;
    g.fillStyle = '#12294a';
    g.strokeStyle = '#fdfbf6';
    g.lineWidth = 10;
    g.beginPath();                                   // pointer tip first, badge overlaps it
    g.moveTo(128 - 30, by + bh - 6);
    g.lineTo(128, 312);
    g.lineTo(128 + 30, by + bh - 6);
    g.closePath();
    g.fill(); g.stroke();
    g.beginPath();
    g.moveTo(bx + rad, by);
    g.arcTo(bx + bw, by, bx + bw, by + bh, rad);
    g.arcTo(bx + bw, by + bh, bx, by + bh, rad);
    g.arcTo(bx, by + bh, bx, by, rad);
    g.arcTo(bx, by, bx + bw, by, rad);
    g.closePath();
    g.fill(); g.stroke();
    if (kind === 'heli') {
      // bold shapes only — the badge holds ~34 px on screen, so no filigree
      g.fillStyle = '#fdfbf6';
      g.fillRect(30, 52, 172, 10);                   // main rotor
      g.fillRect(110, 40, 12, 8);                    // rotor hub
      g.fillRect(110, 62, 12, 18);                   // mast
      g.beginPath();                                 // cabin, nose to the left
      g.ellipse(112, 112, 50, 34, 0, 0, Math.PI * 2);
      g.fill();
      g.beginPath();                                 // tail boom, tapering right
      g.moveTo(150, 100); g.lineTo(216, 96); g.lineTo(216, 106); g.lineTo(150, 118);
      g.closePath(); g.fill();
      g.fillRect(208, 66, 9, 36);                    // tail rotor
      g.fillRect(198, 96, 12, 14);                   // tail fin root
      g.fillRect(84, 150, 76, 8);                    // skid
      g.fillRect(96, 140, 7, 12); g.fillRect(136, 140, 7, 12);
      g.save();                                      // sky-blue canopy over the nose
      g.beginPath();
      g.ellipse(112, 112, 50, 34, 0, 0, Math.PI * 2);
      g.clip();
      g.fillStyle = '#4fb0e8';
      g.beginPath();
      g.moveTo(62, 78); g.lineTo(112, 78); g.lineTo(94, 124); g.lineTo(58, 124);
      g.closePath(); g.fill();
      g.restore();
    } else {
      // the material "flight" path the layers panel already uses, scaled up
      const plane = new Path2D('M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z');
      g.save();
      g.translate(128 - 79, 108 - 82);
      g.scale(6.6, 6.6);
      g.fillStyle = '#fdfbf6';
      g.fill(plane);
      g.save();                                      // sky-blue nose, the heli-canopy accent
      g.beginPath(); g.rect(0, 0, 24, 6.2); g.clip();
      g.fillStyle = '#4fb0e8';
      g.fill(plane);
      g.restore();
      g.restore();
    }
    const tex = new THREE.CanvasTexture(cv);
    tex.encoding = THREE.sRGBEncoding;
    tex.anisotropy = anisoOf(4);
    return tex;
  }
  function flightsInit() {
    flightMesh = new THREE.InstancedMesh(flightGeom(), septaMats.body, FLIGHT_CAP);
    flightMesh.frustumCulled = false;
    flightMesh.count = 0;
    groupCity.add(flightMesh);
    heliMesh = new THREE.InstancedMesh(heliGeom(), septaMats.body, FLIGHT_CAP);
    heliMesh.frustumCulled = false;
    heliMesh.count = 0;
    groupCity.add(heliMesh);
    heliRotor = new THREE.InstancedMesh(heliRotorGeom(), septaMats.body, FLIGHT_CAP);
    heliRotor.frustumCulled = false;
    heliRotor.count = 0;
    groupCity.add(heliRotor);
    const sg = new THREE.OctahedronGeometry(0.8, 0);
    flightStrobe = new THREE.InstancedMesh(sg, new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.9, depthWrite: false }), FLIGHT_CAP);
    flightStrobe.frustumCulled = false;
    flightStrobe.count = 0;
    flightStrobe.renderOrder = 12;
    groupCity.add(flightStrobe);
    const mkPin = (kind) => {
      const pin = new THREE.InstancedMesh(
        new THREE.PlaneGeometry(4.6, 5.75).translate(0, 2.95, 0),
        // fog + tonemap exempt (the Round 29c label rule): a pin 11 km out over
        // PHL must punch through the haze, or distance visibility is the joke
        postRaw(new THREE.MeshBasicMaterial({ map: flightPinTexture(kind), transparent: true, depthWrite: false, fog: false, toneMapped: false }), { mask: true }), FLIGHT_CAP);
      pin.frustumCulled = false;
      pin.count = 0;
      pin.renderOrder = 12;
      groupCity.add(pin);
      return pin;
    };
    flightPin = mkPin();          // fixed wing: the phl wordmark
    flightPinH = mkPin('heli');   // rotorcraft: a helicopter silhouette
    flightReady = true;
  }
  function flightPoll() {
    if (!septaCanFetch || !FLIGHTS.on || FLIGHTS.busy || document.hidden) return;
    FLIGHTS.busy = true;
    // 15 s cap on the proxy: a dead passthrough behind Cloudflare hangs ~20 s
    // before its 522, and an untimed fetch can stall the whole rotation for
    // minutes. The public fallbacks get 6 s: they are probes, not the feed.
    const hostMs = FLIGHT_HOSTS[FLIGHTS.host] === FLIGHT_PROXY ? 15000 : 6000;
    fetch(FLIGHT_HOSTS[FLIGHTS.host], { signal: AbortSignal.timeout ? AbortSignal.timeout(hostMs) : undefined })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error('http ' + r.status))))
      .then((js) => {
        FLIGHTS.busy = false;
        if (!js || (!js.aircraft && !js.ac)) throw new Error('bad payload');
        FLIGHTS.ok = true;
        FLIGHTS.fails = 0;
        FLIGHTS.hostFails = 0;
        const seen = new Set();
        const now = performance.now();
        for (const a of (js && js.aircraft) || (js && js.ac) || []) {
          if (a.lat == null || a.lon == null) continue;
          const ground = a.alt_baro === 'ground';
          const altFt = ground ? 0 : (a.alt_geom != null ? a.alt_geom : a.alt_baro);
          if (altFt == null || altFt > 20000) continue;
          const x = (a.lon - SITE.lon) * 111320 * Math.cos(SITE.lat * DEG);
          const z = -(a.lat - SITE.lat) * 110574;
          if (x < -12500 || x > 17000 || z < -22000 || z > 10000) continue;
          const hex = a.hex || (a.flight || '').trim();
          if (!hex) continue;
          seen.add(hex);
          let p = flightMap.get(hex);
          if (!p) { p = { hex }; flightMap.set(hex, p); }
          p.ground = ground;
          p.fy = ground ? siteY(x, z, 'ground') + 1.2 : altFt * 0.3048 - 8.34;
          p.fx = x; p.fz = z; p.ft = now;
          const tr = (a.track != null ? a.track : (a.true_heading != null ? a.true_heading : (p.trk || 0)));
          p.trk = tr;
          const gms = (a.gs || 0) * 0.5144;
          p.vx = Math.sin(tr * DEG) * gms;
          p.vz = -Math.cos(tr * DEG) * gms;
          p.vy = ground ? 0 : ((a.geom_rate != null ? a.geom_rate : (a.baro_rate || 0)) * 0.00508);
          p.gs = a.gs || 0;
          p.call = (a.flight || '').trim() || (a.r || '').trim() || hex.toUpperCase();
          p.type = (a.desc || a.t || 'Aircraft');
          // ownOp is deliberately NOT shown: for leased metal it names the
          // trustee bank (BANK OF UTAH TRUSTEE), not an airline — noise
          p.len = FLIGHT_LEN[a.category] || (a.category === 'A0' ? 20 : 32);
          p.heli = p.heli || a.category === 'A7' || HELI_TYPES.has(String(a.t || '').toUpperCase());
          if (p.heli) p.len = FLIGHT_LEN.A7;
          p.landed = false;
          if (p.dx === undefined || Math.hypot(x - p.dx, z - p.dz) > 3200) { p.dx = x; p.dz = z; p.dy = p.fy; }
        }
        for (const [hex, p] of flightMap) if (!seen.has(hex)) { flightMap.delete(hex); if (pickedPlane === p) { pickedPlane = null; vehinfoEl.hidden = true; } }
        flightStatus();
      })
      .catch(() => {
        FLIGHTS.busy = false; FLIGHTS.fails++;
        // two consecutive misses on the same host before rotating; a lone
        // blip on the proxy just retries it in 8 s
        if (++FLIGHTS.hostFails >= 2) { FLIGHTS.hostFails = 0; FLIGHTS.host = (FLIGHTS.host + 1) % FLIGHT_HOSTS.length; }
        FLIGHTS.nextT = performance.now() + (FLIGHTS.fails > FLIGHT_HOSTS.length * 3 ? 180000 : 8000);
        if (!FLIGHTS.ok && FLIGHTS.fails === FLIGHT_HOSTS.length * 3) console.warn('Live flights: every CORS passthrough failed — deploy 3d-model/flight-proxy-worker.js (free, ~5 min) and set FLIGHT_PROXY in app.js');
        flightStatus();
      });
  }
  function flightTest() {
    const now = performance.now();
    const mk = (hex, x, z, altFt, trk, gs, vr, call, type, len, ground) => {
      const p = { hex, ground: !!ground, fx: x, fz: z, ft: now,
        fy: ground ? siteY(x, z, 'ground') + 1.2 : altFt * 0.3048 - 8.34,
        trk, gs, vx: Math.sin(trk * DEG) * gs * 0.5144, vz: -Math.cos(trk * DEG) * gs * 0.5144,
        vy: ground ? 0 : vr * 0.00508, call, type, len, dx: x, dz: z };
      p.dy = p.fy;
      flightMap.set(hex, p);
    };
    mk('test1', 1200, 900, 1800, 262, 145, -700, 'AAL1776', 'Airbus A321', 44);
    mk('test2', -300, -600, 4200, 45, 250, 1400, 'UAL88', 'Boeing 737-800', 39);
    mk('test3', -8200, 7700, 0, 90, 12, 0, 'DAL401', 'Boeing 757-200', 47, true);
    mk('test4', 350, 420, 900, 200, 60, 0, 'PD1', 'Eurocopter EC135', 12);
    flightMap.get('test4').heli = true;
    flightStatus();
    return flightMap.size;
  }
  function flightStatus() {
    if (!btnFlights) return;
    // never-fed and out of hosts: say why instead of a lying zero
    btnFlights.title = (!FLIGHTS.ok && FLIGHTS.fails >= FLIGHT_HOSTS.length * 3)
      ? 'Live Flights (X): Feed Unreachable. Set FLIGHT_PROXY In app.js (See flight-proxy-worker.js)'
      : 'Live Flights (X): ' + flightMap.size + ' Aircraft Tracked';
    const fc = document.getElementById('flightCount');
    if (fc) fc.textContent = flightMap.size ? String(flightMap.size) : '';
  }
  function flightCard(p) {
    const alt = p.ground ? 'On The Ground' : Math.round((p.dy + 8.34) / 0.3048 / 25) * 25 + ' ft, ' +
      (p.vy > 2 ? 'Climbing' : p.vy < -2 ? 'Descending' : 'Level');
    cardSet(p,
      '<span class="vroute" style="background:#3a6ea5">' + septaEsc(p.call) + '</span>' +
      '<span class="vdest">' + septaEsc(p.type) + '</span>' +
      '<div class="vmeta">' + septaEsc(alt + ', ' + Math.round(p.gs) + ' kt') + '</div>' +
      (p.est ? '<div class="vmeta">Estimated Track, Awaiting Signal</div>' : ''));
  }
  function syncFlightsBtn() { syncLayerBtn(btnFlights, FLIGHTS.on); }
  function toggleFlights() {
    if (!septaCanFetch) return;
    FLIGHTS.on = !FLIGHTS.on;
    syncFlightsBtn();
    if (FLIGHTS.on) { FLIGHTS.nextT = 0; }
    else if (pickedPlane) { pickedPlane = null; vehinfoEl.hidden = true; }
  }
  if (btnFlights) btnFlights.addEventListener('click', toggleFlights);
  syncFlightsBtn();
  function updateFlights(now, dt) {
    if (!septaCanFetch) { if (btnFlights) btnFlights.style.display = 'none'; return; }
    if (!flightReady) { if (septaMats.body) flightsInit(); return; }
    if (now >= FLIGHTS.nextT) {
      FLIGHTS.nextT = now + (FLIGHT_PROXY && FLIGHTS.host === 0 ? 10000 : 90000);
      flightPoll();
    }
    if (!FLIGHTS.on) {
      if (flightMesh.count || heliMesh.count) { flightMesh.count = 0; heliMesh.count = 0; heliRotor.count = 0; flightStrobe.count = 0; flightPin.count = 0; flightPinH.count = 0; flightMesh.instanceMatrix.needsUpdate = true; heliMesh.instanceMatrix.needsUpdate = true; heliRotor.instanceMatrix.needsUpdate = true; flightStrobe.instanceMatrix.needsUpdate = true; flightPin.instanceMatrix.needsUpdate = true; flightPinH.instanceMatrix.needsUpdate = true; }
      return;
    }
    let i = 0, iF = 0, iH = 0;
    const night = nightUniform.value;
    _sqB.copy(camera.quaternion);                    // pins billboard the camera
    const gone = [];
    for (const p of flightMap.values()) {
      if (i >= FLIGHT_CAP) break;
      // dead reckoning: jets cross a block between polls, so fly the last known
      // velocity and ease toward each fresh fix. The feed can go quiet for
      // minutes behind the public passthroughs, so planes KEEP FLYING their
      // track instead of freezing: arrivals settle onto the field, everything
      // else exits the model, and long-stale traffic despawns.
      const age = (now - p.ft) / 1000;
      if (age > 300) { gone.push(p.hex); continue; }
      let px = p.fx + p.vx * age, pz = p.fz + p.vz * age, py = p.fy + p.vy * age;
      if (px < -12500 || px > 17000 || pz < -22000 || pz > 10000) { gone.push(p.hex); continue; }
      if (!p.ground) {
        const gY = siteY(px, pz, 'ground');
        if (py <= gY + 7) { py = gY + 5; p.landed = true; }
        if (p.landed && age > 90) { gone.push(p.hex); continue; }
      }
      const k = 1 - Math.exp(-dt / 0.8);
      p.dx += (px - p.dx) * k;
      p.dz += (pz - p.dz) * k;
      p.dy += (py - p.dy) * k;
      p.est = age > 25;
      const yaw = Math.atan2(-p.vz, p.vx) || 0;
      const pitch = (p.ground || p.landed) ? 0 : clamp(Math.atan2(p.vy, Math.max(30, Math.hypot(p.vx, p.vz))), -0.21, 0.21);
      _fe.set(0, yaw, pitch, 'YZX');
      _fq.setFromEuler(_fe);
      _sp.set(p.dx, p.dy, p.dz);
      _ss.set(p.len, p.len, p.len);
      _sm.compose(_sp, _fq, _ss);
      if (p.heli) {
        heliMesh.setMatrixAt(iH, _sm);
        heliPick[iH] = p;
        // main rotor: same pose with a per-airframe phase spun about local Y
        _fqSpin.setFromAxisAngle(FLIGHT_UP, now * 0.0165 + (p.hex.charCodeAt(0) || 0));
        _fqR.multiplyQuaternions(_fq, _fqSpin);
        _sm.compose(_sp, _fqR, _ss);
        heliRotor.setMatrixAt(iH, _sm);
      } else {
        flightMesh.setMatrixAt(iF, _sm);
        flightPick[iF] = p;
      }
      // white anti-collision strobe: a sharp double-blink, phase by airframe
      const ph = ((now * 0.001 + ((parseInt(String(p.hex).replace(/[^0-9a-z]/gi, ''), 36) || 0) % 97) * 0.13) % 1.2) / 1.2;
      const blink = (ph < 0.05 || (ph > 0.12 && ph < 0.17)) ? 1 : 0;
      const ssc = blink * (1.2 + 2.2 * night) * Math.max(0.6, p.len / 32);
      _sp.set(p.dx, p.dy + 0.5, p.dz);
      _ss.set(ssc || 0.0001, ssc || 0.0001, ssc || 0.0001);
      _sm.compose(_sp, _fq, _ss);
      flightStrobe.setMatrixAt(i, _sm);
      // pin, billboarded and distance-scaled to hold ~34 px on screen so
      // traffic reads from across the model (the SEPTA bus-badge recipe);
      // helicopters fly the rotor silhouette, fixed wing the airplane glyph
      _sp.set(p.dx, p.dy + p.len * 0.14 + 1.5, p.dz);
      const ps = clamp(camera.position.distanceTo(_sp) / 135, 2.2, 190);
      _ss.set(ps, ps, ps);
      _sm.compose(_sp, _sqB, _ss);
      if (p.heli) flightPinH.setMatrixAt(iH++, _sm);
      else flightPin.setMatrixAt(iF++, _sm);
      i++;
    }
    if (gone.length) {
      for (const hx of gone) { const p = flightMap.get(hx); flightMap.delete(hx); if (pickedPlane === p) { pickedPlane = null; vehinfoEl.hidden = true; } }
      flightStatus();
    }
    flightMesh.count = iF;
    heliMesh.count = iH;
    heliRotor.count = iH;
    flightStrobe.count = i;
    flightPin.count = iF;
    flightPinH.count = iH;
    flushInst(flightMesh);
    flushInst(heliMesh);
    flushInst(heliRotor);
    flushInst(flightStrobe);
    flushInst(flightPin);
    flushInst(flightPinH);
    if (pickedPlane) {
      flightCard(pickedPlane);
      _ssv.set(pickedPlane.dx, pickedPlane.dy + pickedPlane.len * 0.12 + 6, pickedPlane.dz).project(camera);
      if (_ssv.z > 1 || _ssv.z < -1) vehinfoEl.style.opacity = '0';
      else {
        vehinfoEl.style.opacity = '1';
        vehinfoEl.style.transform = 'translate(-50%,-100%) translate(' +
          ((_ssv.x * 0.5 + 0.5) * window.innerWidth).toFixed(1) + 'px,' +
          ((-_ssv.y * 0.5 + 0.5) * window.innerHeight).toFixed(1) + 'px)';
      }
    }
  }


  // ---------------------------------------------------------------- live ships
  // Real AIS traffic on the rivers via the aisstream.io WebSocket (free key,
  // and WebSockets have no CORS wall, so the page connects DIRECTLY — no
  // passthrough needed, unlike the flight feed). The layer stays hidden until
  // a key is pasted into AIS_KEY. Ships dead-reckon between reports (they are
  // slow, so a few-second cadence renders glassy smooth), moored and anchored
  // vessels hold station, and the card knows a tug from a tanker.
  const AIS_KEY = 'f9148033287fd7b2fd6c82142e0b78ac0f1906cf';   // aisstream.io, Mike's free key
  // The free key streams to ONE client at a time, so a direct socket makes the
  // layer single-viewer. ops/ais_relay.py holds that one socket on the VPS and
  // writes ais.json every 4 s for everyone; the page polls it and falls back
  // to the direct socket only while the relay is unavailable. Once the relay
  // is live the key above is to be rotated and removed.
  const AIS_RELAY = 'https://philly3d.com/ais.json';
  const SHIPS = { on: true, ok: false, sock: null, retryT: 0, relay: false, relayT: 0, relayBusy: false, relayFails: 0 };
  const shipMap = new Map();
  let shipMesh = null, shipAnchor = null, shipReady = false, pickedShip = null;
  const shipPick = [];
  const _aqB = new THREE.Quaternion();
  function shipPinTexture() {
    // vessels wear the shared badge casing with a bold white fouled anchor
    const cv = document.createElement('canvas');
    cv.width = 256; cv.height = 320;
    const g = cv.getContext('2d');
    const bw = 240, bh = 200, bx = 8, by = 8, rad = 34;
    g.fillStyle = '#12294a';
    g.strokeStyle = '#fdfbf6';
    g.lineWidth = 10;
    g.beginPath();                                   // pointer tip first, badge overlaps it
    g.moveTo(128 - 30, by + bh - 6);
    g.lineTo(128, 312);
    g.lineTo(128 + 30, by + bh - 6);
    g.closePath();
    g.fill(); g.stroke();
    g.beginPath();
    g.moveTo(bx + rad, by);
    g.arcTo(bx + bw, by, bx + bw, by + bh, rad);
    g.arcTo(bx + bw, by + bh, bx, by + bh, rad);
    g.arcTo(bx, by + bh, bx, by, rad);
    g.arcTo(bx, by, bx + bw, by, rad);
    g.closePath();
    g.fill(); g.stroke();
    g.strokeStyle = '#fdfbf6';
    g.lineCap = 'round';
    g.lineWidth = 15;
    g.beginPath(); g.arc(128, 52, 16, 0, Math.PI * 2); g.stroke();   // ring
    g.beginPath(); g.moveTo(128, 68); g.lineTo(128, 176); g.stroke();  // shank
    g.beginPath(); g.moveTo(92, 92); g.lineTo(164, 92); g.stroke();    // stock
    g.beginPath(); g.arc(128, 122, 58, Math.PI * 0.16, Math.PI * 0.84); g.stroke();  // arms
    g.fillStyle = '#fdfbf6';
    for (const s of [-1, 1]) {                        // flukes
      const fx = 128 + s * 54, fy = 154;
      g.beginPath();
      g.moveTo(fx, fy + 14); g.lineTo(fx - s * 16, fy - 10); g.lineTo(fx + s * 12, fy - 6);
      g.closePath(); g.fill();
    }
    const tex = new THREE.CanvasTexture(cv);
    tex.anisotropy = anisoOf(4);
    return tex;
  }
  const SHIP_CAP = 48;
  const btnShips = document.getElementById('btnShips');
  // AIS type code to a card name; the hull keeps the geometry's own scheme
  const SHIP_TYPE = (t) => t >= 80 && t < 90 ? 'Tanker' : t >= 70 && t < 80 ? 'Cargo Ship'
    : t >= 60 && t < 70 ? 'Passenger Vessel' : (t === 31 || t === 32 || t === 52) ? 'Tug'
    : t === 30 ? 'Fishing Vessel' : (t === 36 || t === 37) ? 'Pleasure Craft'
    : t === 35 ? 'Military Vessel' : 'Vessel';
  function shipGeom() {
    // unit hull: length 1 along +x, unit beam along z, scaled per instance
    const parts = [];
    const box = (sx, sy, sz, cx, cy, cz, r, g, b, glow, ry) => {
      const bg = new THREE.BoxGeometry(sx, sy, sz);
      if (ry) bg.rotateY(ry);
      bg.translate(cx, cy, cz);
      parts.push(septaColored(bg, r, g, b, glow || 0));
    };
    // no rotated parts: a rotation baked before the per-instance non-uniform
    // scale (length x beam) shears into a detached blade — the bow tapers in
    // axis-aligned steps instead
    box(0.85, 0.5, 1.0, -0.075, 0.13, 0, 0.15, 0.16, 0.18);       // hull
    box(0.10, 0.5, 0.72, 0.40, 0.13, 0, 0.15, 0.16, 0.18);        // bow step 1
    box(0.06, 0.46, 0.4, 0.475, 0.15, 0, 0.15, 0.16, 0.18);       // bow step 2
    box(0.86, 0.06, 1.01, -0.07, 0.02, 0, 0.45, 0.16, 0.13);      // waterline stripe
    box(0.5, 0.3, 0.8, 0.03, 0.5, 0, 0.38, 0.36, 0.33);           // deck cargo block
    box(0.16, 0.5, 0.7, -0.36, 0.55, 0, 0.78, 0.78, 0.76);        // superstructure
    box(0.17, 0.09, 0.72, -0.36, 0.77, 0, 1, 0.93, 0.72, 1);      // bridge glow band
    box(0.06, 0.2, 0.28, -0.41, 0.9, 0, 0.2, 0.2, 0.22);          // funnel
    box(0.03, 0.05, 0.05, 0.44, 0.45, 0, 1, 0.95, 0.8, 1);        // masthead light
    return septaMerge(parts);
  }
  function shipsInit() {
    shipMesh = new THREE.InstancedMesh(shipGeom(), septaMats.body, SHIP_CAP);
    shipMesh.frustumCulled = false;
    shipMesh.count = 0;
    // neutral instance tint written once: the geometry carries its own scheme
    for (let k = 0; k < SHIP_CAP; k++) shipMesh.setColorAt(k, _sc.setRGB(1, 1, 1));
    shipMesh.instanceColor.needsUpdate = true;
    groupCity.add(shipMesh);
    // anchor badge, billboarded and distance-scaled like the aircraft pins
    shipAnchor = new THREE.InstancedMesh(
      new THREE.PlaneGeometry(4.6, 5.75).translate(0, 2.95, 0),
      postRaw(new THREE.MeshBasicMaterial({ map: shipPinTexture(), transparent: true, depthWrite: false, fog: false, toneMapped: false }), { mask: true }), SHIP_CAP);
    shipAnchor.frustumCulled = false;
    shipAnchor.count = 0;
    shipAnchor.renderOrder = 12;
    groupCity.add(shipAnchor);
    shipReady = true;
  }
  const shipDecoder = new TextDecoder();
  function shipMsg(ev) {
    // aisstream delivers binary frames: with binaryType 'arraybuffer' they
    // decode synchronously (JSON.parse on a Blob fails silently)
    let d;
    try { d = JSON.parse(typeof ev.data === 'string' ? ev.data : shipDecoder.decode(ev.data)); } catch (e) { return; }
    const meta = d.MetaData || {};
    const mmsi = meta.MMSI;
    if (!mmsi) return;
    let v = shipMap.get(mmsi);
    // stamped at birth so a vessel that never fixes inside the box still ages out
    if (!v) { v = { mmsi, ft: performance.now(), len: 30, beam: 8, tn: 'Vessel', sog: 0, cog: 0, moored: false }; shipMap.set(mmsi, v); }
    if (meta.ShipName && meta.ShipName.trim()) v.name = meta.ShipName.trim();
    if (d.MessageType === 'PositionReport' && d.Message && d.Message.PositionReport) {
      const m = d.Message.PositionReport;
      const x = (m.Longitude - SITE.lon) * 111320 * Math.cos(SITE.lat * DEG);
      const z = -(m.Latitude - SITE.lat) * 110574;
      if (x < -12500 || x > 17000 || z < -22000 || z > 10000) return;
      v.fx = x; v.fz = z; v.ft = performance.now();
      v.sog = m.Sog || 0;
      const hd = (m.TrueHeading != null && m.TrueHeading < 360) ? m.TrueHeading : (m.Cog != null ? m.Cog : v.cog);
      v.cog = m.Cog != null ? m.Cog : hd;
      v.hdg = hd;
      v.moored = m.NavigationalStatus === 1 || m.NavigationalStatus === 5 || v.sog < 0.25;
      const gms = v.sog * 0.5144;
      v.vx = Math.sin((v.cog || 0) * DEG) * gms;
      v.vz = -Math.cos((v.cog || 0) * DEG) * gms;
      if (v.dx === undefined) { v.dx = x; v.dz = z; shipStatus(); }   // first fix inside the box: now it counts
      else if (Math.hypot(x - v.dx, z - v.dz) > 1500) { v.dx = x; v.dz = z; }
      SHIPS.ok = true;
    } else if (d.MessageType === 'ShipStaticData' && d.Message && d.Message.ShipStaticData) {
      const s = d.Message.ShipStaticData;
      if (s.Name && s.Name.trim()) v.name = s.Name.trim();
      if (s.Dimension) {
        const L = (s.Dimension.A || 0) + (s.Dimension.B || 0), B = (s.Dimension.C || 0) + (s.Dimension.D || 0);
        if (L > 4) v.len = clamp(L, 8, 340);
        if (B > 1) v.beam = clamp(B, 3, 52);
      }
      if (s.Type) v.tn = SHIP_TYPE(s.Type);
      if (s.Destination && s.Destination.trim()) v.dest = s.Destination.trim();
    }
  }
  // one relay record -> the same vessel state shipMsg builds from the stream.
  // The fix time rides along, so dead reckoning runs from the fix, not the poll.
  function shipUpsertRelay(s, nowP, nowS) {
    if (!s || !s.mmsi || s.lat == null || s.lon == null) return;
    let v = shipMap.get(s.mmsi);
    if (!v) { v = { mmsi: s.mmsi, ft: nowP, len: 30, beam: 8, tn: 'Vessel', sog: 0, cog: 0, moored: false }; shipMap.set(s.mmsi, v); }
    if (s.name) v.name = String(s.name).trim() || v.name;
    if (s.type > 0) v.tn = SHIP_TYPE(s.type);
    if (s.len > 4) v.len = clamp(s.len, 8, 340);
    if (s.beam > 1) v.beam = clamp(s.beam, 3, 52);
    if (s.dest) v.dest = String(s.dest).trim();
    const x = (s.lon - SITE.lon) * 111320 * Math.cos(SITE.lat * DEG);
    const z = -(s.lat - SITE.lat) * 110574;
    if (x < -12500 || x > 17000 || z < -22000 || z > 10000) return;
    if (s.t > 0 && nowS - s.t > 1500) return;   // older than the despawn threshold: do not create it only to prune it
    const age = s.t > 0 ? clamp(nowS - s.t, 0, 1500) : 0;
    v.fx = x; v.fz = z; v.ft = nowP - age * 1000;
    v.sog = s.sog || 0;
    const hd = (s.hdg != null && s.hdg < 360) ? s.hdg : (s.cog != null ? s.cog : v.cog);
    v.cog = s.cog != null ? s.cog : hd;
    v.hdg = hd;
    v.moored = s.nav === 1 || s.nav === 5 || v.sog < 0.25;
    const gms = v.sog * 0.5144;
    v.vx = Math.sin((v.cog || 0) * DEG) * gms;
    v.vz = -Math.cos((v.cog || 0) * DEG) * gms;
    if (v.dx === undefined) { v.dx = x; v.dz = z; shipStatus(); }
    else if (Math.hypot(x - v.dx, z - v.dz) > 1500) { v.dx = x; v.dz = z; }
  }
  function shipRelayPoll(now) {
    if (!septaCanFetch || SHIPS.relayBusy || now < SHIPS.relayT) return;
    SHIPS.relayBusy = true;
    // 4 s while it answers; after a miss, back off up to 5 min before asking again
    SHIPS.relayT = now + (SHIPS.relay ? 4000 : Math.min(300000, 15000 * Math.pow(2, Math.min(SHIPS.relayFails, 4))));
    const ctl = typeof AbortController !== 'undefined' ? new AbortController() : null;
    const timer = ctl ? setTimeout(() => ctl.abort(), 8000) : 0;
    const miss = () => { clearTimeout(timer); SHIPS.relayBusy = false; SHIPS.relayFails++; SHIPS.relay = false; };
    fetch(AIS_RELAY, { cache: 'no-store', signal: ctl ? ctl.signal : undefined })
      .then((r) => { if (!r.ok) throw new Error('http ' + r.status); return r.json().then((d) => ({ d, now: serverNow(r) })); })
      .then(({ d, now: sNow }) => {
        clearTimeout(timer);
        // stale write time = relay down; a fresh write with an old upstream time = the
        // relay alive but its aisstream socket dead (bad key, outage): fall back too
        if (!d || !Array.isArray(d.ships) || !(d.t > 0) || sNow - d.t > 60 || (d.src > 0 && sNow - d.src > 900)) { miss(); return; }
        SHIPS.relayBusy = false; SHIPS.relayFails = 0;
        if (!SHIPS.relay) { SHIPS.relay = true; shipRelease(); }   // the relay owns the feed: drop the direct socket
        const nowP = performance.now(), nowS = Date.now() / 1000;
        for (const rec of d.ships) shipUpsertRelay(rec, nowP, nowS);
        SHIPS.ok = true;
      })
      .catch(miss);
  }
  function shipConnect() {
    if (!SHIPS.on || !AIS_KEY || !septaCanFetch || SHIPS.sock || SHIPS.relay) return;
    try {
      const ws = new WebSocket('wss://stream.aisstream.io/v0/stream');
      ws.binaryType = 'arraybuffer';
      SHIPS.sock = ws;
      ws.onopen = () => {
        try {
          ws.send(JSON.stringify({ APIKey: AIS_KEY, BoundingBoxes: [[[39.80, -75.45], [40.08, -74.82]]], FilterMessageTypes: ['PositionReport', 'ShipStaticData'] }));
        } catch (e) { /* closed */ }
      };
      ws.onmessage = (ev) => { SHIPS.backoff = 15000; shipMsg(ev); };
      ws.onclose = () => {
        SHIPS.sock = null;
        SHIPS.backoff = Math.min((SHIPS.backoff || 15000) * 2, 240000);
        SHIPS.retryT = performance.now() + SHIPS.backoff * (0.7 + Math.random() * 0.6);
      };
      ws.onerror = () => { try { ws.close(); } catch (e) {} };
    } catch (e) {
      SHIPS.sock = null;
      SHIPS.retryT = performance.now() + 60000;
    }
  }
  function shipTest() {
    const now = performance.now();
    const mk = (mmsi, x, z, hdg, sog, len, beam, name, tn, dest, moored) => {
      const gms = sog * 0.5144;
      shipMap.set(mmsi, { mmsi, fx: x, fz: z, ft: now, dx: x, dz: z, sog, cog: hdg, hdg,
        vx: Math.sin(hdg * DEG) * gms, vz: -Math.cos(hdg * DEG) * gms,
        len, beam, name, tn, dest, moored: !!moored });
    };
    mk(1001, 620, -250, 12, 9, 182, 28, 'MSC ALTAIR', 'Cargo Ship', 'PHILADELPHIA');
    mk(1002, 680, 2500, 195, 5, 28, 9, 'DELAWARE RESPONDER', 'Tug', 'ASSIST');
    mk(1003, 760, 1400, 90, 0, 224, 32, 'OVERSEAS LUNA', 'Tanker', 'PAULSBORO', true);
    shipStatus();
    return shipMap.size;
  }
  function shipStatus() {
    if (!btnShips) return;
    // only vessels with a fix inside the model box count; the stream's bounding
    // box also hears river traffic 10 km out that never renders
    let n = 0;
    for (const v of shipMap.values()) if (v.fx !== undefined) n++;
    btnShips.title = 'Live Ships (H): ' + n + ' Vessels Tracked';
    const sc = document.getElementById('shipCount');
    if (sc) sc.textContent = n ? String(n) : '';
  }
  function shipCard(v) {
    const move = v.moored ? 'Moored' : Math.round(v.sog * 10) / 10 + ' kt';
    cardSet(v,
      '<span class="vroute" style="background:#1f4f7a">' + septaEsc(v.tn) + '</span>' +
      '<span class="vdest">' + septaEsc(v.name || 'MMSI ' + v.mmsi) + '</span>' +
      '<div class="vmeta">' + septaEsc(move + ', ' + Math.round(v.len) + ' m') + '</div>' +
      (v.dest ? '<div class="vmeta">' + septaEsc('Bound For ' + v.dest) + '</div>' : ''));
  }
  function syncShipsBtn() { syncLayerBtn(btnShips, SHIPS.on); }
  function shipRelease() {
    // the key allows one stream: give it up whenever this tab cannot use it
    if (SHIPS.sock) { const s = SHIPS.sock; SHIPS.sock = null; try { s.onclose = null; s.close(); } catch (e) {} }
  }
  function toggleShips() {
    if (!septaCanFetch || (!AIS_KEY && !AIS_RELAY)) return;   // the relay works without a key
    SHIPS.on = !SHIPS.on;
    syncShipsBtn();
    // off parks the retry clock too: shipRelease nulls onclose, so nothing
    // else would ever push retryT past the next frame
    if (!SHIPS.on) { shipRelease(); SHIPS.retryT = Infinity; if (pickedShip) { pickedShip = null; vehinfoEl.hidden = true; } }
    else { SHIPS.backoff = 15000; SHIPS.retryT = 0; }
  }
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) shipRelease();
    else if (SHIPS.on) { SHIPS.backoff = 15000; SHIPS.retryT = performance.now() + 1200; }
  });
  if (btnShips) btnShips.addEventListener('click', toggleShips);
  syncShipsBtn();
  function updateShips(now, dt) {
    if (!btnShips) return;
    if (!shipReady) { if (septaMats.body) shipsInit(); return; }
    // without a key the layer stays out of the panel, but injected test
    // vessels (__dbg.shipTest) still render so the pipeline stays provable
    if (!septaCanFetch || (!AIS_KEY && !AIS_RELAY)) { btnShips.style.display = 'none'; if (!shipMap.size) return; }
    if (!SHIPS.on) {
      if (shipMesh.count) { shipMesh.count = 0; shipMesh.instanceMatrix.needsUpdate = true; shipAnchor.count = 0; shipAnchor.instanceMatrix.needsUpdate = true; }
      return;
    }
    if (!document.hidden) {   // only while the layer is on
      shipRelayPoll(now);
      if (!SHIPS.relay && !SHIPS.sock && now >= SHIPS.retryT) shipConnect();
    }
    _aqB.copy(camera.quaternion);   // fresh billboard pose for the anchor badges
    // the age prune is its own pass: the draw loop stops at SHIP_CAP, and a
    // vessel heard but never fixed inside the box must age out too
    const gone = [];
    for (const v of shipMap.values()) {
      const age = (now - v.ft) / 1000;
      if (age > 1800) { gone.push(v.mmsi); continue; }
      if (v.dx === undefined) continue;
      const px = v.moored ? v.fx : v.fx + v.vx * Math.min(age, 600);
      const pz = v.moored ? v.fz : v.fz + v.vz * Math.min(age, 600);
      if (px < -12500 || px > 17000 || pz < -22000 || pz > 10000) gone.push(v.mmsi);   // sailed out of the model
    }
    for (const m of gone) shipMap.delete(m);
    gone.length = 0;
    let i = 0;
    for (const v of shipMap.values()) {
      if (i >= SHIP_CAP) break;
      const age = (now - v.ft) / 1000;
      if (v.dx === undefined) continue;
      const px = v.moored ? v.fx : v.fx + v.vx * Math.min(age, 600);
      const pz = v.moored ? v.fz : v.fz + v.vz * Math.min(age, 600);
      const k = 1 - Math.exp(-dt / 1.6);
      v.dx += (px - v.dx) * k;
      v.dz += (pz - v.dz) * k;
      const hd = (v.hdg != null && v.hdg < 360) ? v.hdg : v.cog;
      const hx = Math.sin(hd * DEG), hz = -Math.cos(hd * DEG);
      _fe.set(0, Math.atan2(-hz, hx), 0, 'YZX');
      _fq.setFromEuler(_fe);
      _sp.set(v.dx, TERRAIN.water + 0.1, v.dz);
      _ss.set(v.len, clamp(v.len * 0.09, 2.5, 16), v.beam);
      _sm.compose(_sp, _fq, _ss);
      shipMesh.setMatrixAt(i, _sm);
      // the anchor pin floats above the masthead, holding size like the aircraft badges
      _sp.set(v.dx, TERRAIN.water + clamp(v.len * 0.09, 2.5, 16) + 2, v.dz);
      const aps = clamp(camera.position.distanceTo(_sp) / 135, 2.2, 190);
      _ss.set(aps, aps, aps);
      _sm.compose(_sp, _aqB, _ss);
      shipAnchor.setMatrixAt(i, _sm);
      shipPick[i] = v;
      i++;
    }
    if (gone.length) {
      for (const g of gone) { const v = shipMap.get(g); shipMap.delete(g); if (pickedShip === v) { pickedShip = null; vehinfoEl.hidden = true; } }
      shipStatus();
    }
    shipMesh.count = i;
    flushInst(shipMesh, -1);     // tints are written once in shipsInit
    shipAnchor.count = i;
    flushInst(shipAnchor, -1);
    if (pickedShip) {
      shipCard(pickedShip);
      _ssv.set(pickedShip.dx, TERRAIN.water + clamp(pickedShip.len * 0.09, 2.5, 16) + 6, pickedShip.dz).project(camera);
      if (_ssv.z > 1 || _ssv.z < -1) vehinfoEl.style.opacity = '0';
      else {
        vehinfoEl.style.opacity = '1';
        vehinfoEl.style.transform = 'translate(-50%,-100%) translate(' +
          ((_ssv.x * 0.5 + 0.5) * window.innerWidth).toFixed(1) + 'px,' +
          ((-_ssv.y * 0.5 + 0.5) * window.innerHeight).toFixed(1) + 'px)';
      }
    }
  }

  // ---------------------------------------------------------------- traffic
  // Typical vehicle traffic: synthesized cars at PennDOT's measured street
  // volumes (RMSTRAFFIC AADT conflated onto the OSM grid by bake_traffic.py),
  // shaped by an urban diurnal curve on the model clock. Rush hour thickens to
  // a stated 1:N sample of the true count; the small hours run at genuine 1:1
  // density. These are VOLUMES, not live positions — no public feed of live
  // cars exists, and the About panel says so. Fully baked: no fetch, no key,
  // the one moving layer that also works inside the artifact sandbox.
  const TRAFFIC = { on: true, cap: isTouch ? 550 : 2200, n: 0, scale: 1 };
  const btnTraffic = document.getElementById('btnTraffic');
  const TRAFFIC_SPEED = [88, 64, 40, 34, 30, 22];       // km/h by class 0-5
  const TRAFFIC_UP = new THREE.Vector3(0, 1, 0);
  // hour-of-day shares of daily volume (normalized below): urban weekday with
  // AM/PM commute shoulders, flatter weekend with a midday plateau
  const TRAFFIC_WD = [.008, .005, .004, .004, .006, .015, .035, .062, .071, .055, .048, .050, .053, .052, .055, .065, .073, .078, .062, .045, .035, .028, .020, .012];
  const TRAFFIC_WE = [.014, .010, .008, .005, .005, .008, .015, .025, .038, .050, .060, .066, .070, .070, .068, .066, .064, .062, .058, .050, .042, .035, .028, .020];
  for (const tbl of [TRAFFIC_WD, TRAFFIC_WE]) {
    const s = tbl.reduce((a, b) => a + b, 0);
    for (let i = 0; i < 24; i++) tbl[i] /= s;
  }
  // paint-shop reality, stored dark for the legacy-color lift; silver/white weighted
  const CAR_PAL = [0x7e8287, 0x9a9a96, 0x1d1f24, 0x54565b, 0x7e8287, 0x9a9a96, 0x1d1f24, 0x6e2b28, 0x2c4363, 0x6e6353, 0x2e4a38];
  const CAR_OFFW = [4.6, 3.6, 2.7, 2.3, 2.0, 1.6];      // lane offset from centerline by class
  const trafficRuns = [];
  const carSlot = [];   // which car sits in each instance slot, so tints are rewritten only when a slot changes hands
  let carMesh = null, carLights = null, trafficReady = false, trafficCars = 0;
  let trafficNextRecon = 0, trafficLastMin = -1, trafficLastDate = '', trafficFrame = 0;
  function carGeom() {
    // ~4.5 m sedan from three boxes, nose toward +x, built at real meters so
    // the instance scale stays uniform (the ship shear gotcha never applies)
    const parts = [];
    const box = (sx, sy, sz, cx, cy, cz, r, g, b) =>
      parts.push(septaColored(new THREE.BoxGeometry(sx, sy, sz).translate(cx, cy, cz), r, g, b, 0));
    box(4.4, 0.6, 1.74, 0, 0.62, 0, 1, 1, 1);                 // body (takes instance tint)
    box(2.25, 0.5, 1.56, -0.25, 1.12, 0, 0.13, 0.14, 0.16);   // cabin glass
    box(4.24, 0.2, 1.62, 0, 0.16, 0, 0.1, 0.1, 0.11);         // skirt in wheel shadow
    return septaMerge(parts);
  }
  function carLightGeom() {
    // headlight pair (warm white, +x nose) and taillight pair (red), fully
    // PROUD of the body — flush lamps sat inside the body box and the depth
    // test swallowed them from every angle but dead ahead (the "no headlights"
    // bug). A separate MeshBasic mesh, NOT aGlow: septaMats.body's night
    // emissive is fixed warm-white, so red taillights can't ride it.
    const parts = [];
    const lamp = (cx, cz, r, g, b) =>
      parts.push(septaColored(new THREE.BoxGeometry(0.22, 0.2, 0.4).translate(cx, 0.62, cz), r, g, b, 0));
    lamp(2.32, 0.55, 1.0, 0.94, 0.75);
    lamp(2.32, -0.55, 1.0, 0.94, 0.75);
    lamp(-2.32, 0.55, 1.0, 0.12, 0.07);
    lamp(-2.32, -0.55, 1.0, 0.12, 0.07);
    return septaMerge(parts);
  }
  step('Setting the traffic flowing', () => {
    if (typeof TRAFFIC_B64 === 'undefined' || !TRAFFIC_B64) { if (btnTraffic) btnTraffic.style.display = 'none'; return; }
    const bin = unb64(TRAFFIC_B64, 'TRAFFIC');
    TRAFFIC_B64 = null;
    const hdr = new Int32Array(bin.buffer, 0, 4);
    if (hdr[0] !== 0x53485454) return;
    const body = new Int16Array(bin.buffer, 16);
    let k = 0;
    for (let wI = 0; wI < hdr[1]; wI++) {
      const n = body[k++], flags = body[k++], aadt = body[k++] * 10;
      const cls = flags & 7, oneway = !!(flags & 8);
      let pts = new Array(n);
      for (let j = 0; j < n; j++) pts[j] = [body[k++] * 0.2, body[k++] * 0.2];
      pts = densify(pts, 20);
      // per-vertex height with the full terrain story — trench, bridge decks,
      // viaducts, sunken carriageways — split into sub-runs at dead water
      let cur = null;
      const runs = [];
      for (let j = 0; j < pts.length; j++) {
        const x = pts[j][0], z = pts[j][1];
        const jn = pts[Math.min(j + 1, pts.length - 1)], jp = pts[Math.max(j - 1, 0)];
        let ux = jn[0] - jp[0], uz = jn[1] - jp[1];
        const uL = Math.hypot(ux, uz) || 1; ux /= uL; uz /= uL;
        let dead = false;
        const core = inCore(x, z);
        let y = siteY(x, z, 'road');
        if (cls === 0 && core) {
          // I-95 rides DOWN in the trench (the road step's motY blend, replicated)
          const o = frontOff(x, z);
          if (o > TERRAIN.trenchW && o < TERRAIN.trenchE) {
            const eo = Math.min(o - TERRAIN.trenchW, TERRAIN.trenchE - o) / 14;
            const ez = Math.min(z - (CORE_EXT.z0 + 4), (CORE_EXT.z1 - 4) - z) / 60;
            const t = clamp(Math.min(eo, ez), 0, 1);
            y = lerp(y, TERRAIN.trenchFloor + 0.55, t * t * (3 - 2 * t));
          }
        }
        let lift = core ? LAYER.road + 0.04 : LAYER.road + (6 - Math.min(cls, 6)) * 0.055 + 0.05;
        const bY = bridgeDeckLift(x, z);   // the custom spans (BFB, WWB) carry traffic on their real decks
        if (bY !== null && bY > y) { y = bY; lift = 0.12; }
        else if (!core) {
          const low = demY(x, z) < TERRAIN.water + 0.6;
          if (low && riverCorridor(x, z)) {
            if (cls > 1) dead = true;   // minor roads don't bridge
            else y = Math.max(y, TERRAIN.water + (cls === 0 ? 20 : 13));
          }
        }
        const oy = ovpDeckY(x, z, ux, uz);
        if (oy !== null && oy > y) { y = oy; lift = 0.1; }
        else if (cls <= 1) {
          const sy = sunkCutNear(x, z, 1);
          if (sy !== null && sy < y - 0.5) { y = sy; lift = 0.35; }
        }
        if (dead) { if (cur && cur.xs.length > 1) runs.push(cur); cur = null; continue; }
        if (!cur) cur = { xs: [], zs: [], ys: [] };
        cur.xs.push(x); cur.zs.push(z); cur.ys.push(y + lift);
      }
      if (cur && cur.xs.length > 1) runs.push(cur);
      for (const r of runs) {
        const m = r.xs.length;
        const cum = new Float32Array(m);
        let L = 0;
        for (let j = 1; j < m; j++) { L += Math.hypot(r.xs[j] - r.xs[j - 1], r.zs[j] - r.zs[j - 1]); cum[j] = L; }
        if (L < 25) continue;
        // chunk long ways to ~400 m so the camera-local budget resolves finely
        // (one 3 km I-95 way must not be all-in or all-out of the radius)
        const pieces = Math.max(1, Math.round(L / 400));
        let j0 = 0;
        for (let pc = 1; pc <= pieces; pc++) {
          let j1 = m - 1;
          if (pc < pieces) { const target = L * pc / pieces; j1 = j0 + 1; while (j1 < m - 1 && cum[j1] < target) j1++; }
          if (j1 <= j0) continue;
          const n2 = j1 - j0 + 1;
          const c2 = new Float32Array(n2);
          for (let q = 1; q < n2; q++) c2[q] = cum[j0 + q] - cum[j0];
          const len = c2[n2 - 1];
          if (len >= 25) {
            let mid = 0;
            while (mid < n2 - 1 && c2[mid] < len / 2) mid++;
            trafficRuns.push({ xs: Float32Array.from(r.xs.slice(j0, j1 + 1)), zs: Float32Array.from(r.zs.slice(j0, j1 + 1)),
              ys: Float32Array.from(r.ys.slice(j0, j1 + 1)), cum: c2, len, cls, oneway, aadt,
              mx: r.xs[j0 + mid], mz: r.zs[j0 + mid], want: 0, cars: [] });
          }
          j0 = j1;
        }
      }
    }
    // stitch the run graph: runs sharing an endpoint (same OSM node) connect,
    // so a car reaching the end of its street flows on through the
    // intersection instead of blinking out — the single biggest de-jarring fix
    const joints = new Map();
    const jkey = (x, z) => Math.round(x * 2) + ':' + Math.round(z * 2);
    for (let ri = 0; ri < trafficRuns.length; ri++) {
      const r = trafficRuns[ri], n = r.xs.length;
      for (let end = 0; end < 2; end++) {
        const k = jkey(end ? r.xs[n - 1] : r.xs[0], end ? r.zs[n - 1] : r.zs[0]);
        let arr = joints.get(k);
        if (!arr) { arr = []; joints.set(k, arr); }
        arr.push(ri, end);
      }
    }
    for (let ri = 0; ri < trafficRuns.length; ri++) {
      const r = trafficRuns[ri], n = r.xs.length;
      r.conn = [null, null];
      for (let end = 0; end < 2; end++) {
        const arr = joints.get(jkey(end ? r.xs[n - 1] : r.xs[0], end ? r.zs[n - 1] : r.zs[0]));
        const out = [];
        for (let q = 0; q < arr.length; q += 2) if (arr[q] !== ri) out.push(arr[q], arr[q + 1]);
        if (out.length) r.conn[end] = out;
      }
    }
    const carMat = septaMats.body || new THREE.MeshLambertMaterial({ vertexColors: true });
    carMesh = new THREE.InstancedMesh(carGeom(), carMat, TRAFFIC.cap);
    carMesh.frustumCulled = false;
    carMesh.count = 0;
    carMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    carMesh.setColorAt(0, new THREE.Color(1, 1, 1));    // allocate instanceColor before first draw
    carMesh.instanceColor.setUsage(THREE.DynamicDrawUsage);
    carMesh.castShadow = !isTouch;
    carMesh.receiveShadow = true;
    groupCity.add(carMesh);
    carLights = new THREE.InstancedMesh(carLightGeom(),
      // additive: light pairs bloom against dark asphalt instead of drawing
      // as gray boxes, and daytime opacity 0 costs nothing
      postRaw(new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, opacity: 0, depthWrite: false, toneMapped: false, blending: THREE.AdditiveBlending })), TRAFFIC.cap);
    carLights.frustumCulled = false;
    carLights.count = 0;
    carLights.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    carLights.renderOrder = 11;
    groupCity.add(carLights);
    trafficReady = true;
  });
  function trafficFrac() {
    const dow = new Date(Date.UTC(clock.y, clock.m - 1, clock.d)).getUTCDay();
    const we = dow === 0 || dow === 6;
    const tbl = we ? TRAFFIC_WE : TRAFFIC_WD;
    const h = clock.minutes / 60;
    const h0 = Math.floor(h) % 24, f = h - Math.floor(h);
    return { frac: (tbl[h0] + (tbl[(h0 + 1) % 24] - tbl[h0]) * f) * (we ? 0.85 : 1), dow };
  }
  function carOffset(r, j) {
    // right-hand traffic: two-way runs offset right of travel; one-way
    // carriageways spread across their own width
    return r.oneway ? (j * 2 - 1) * CAR_OFFW[r.cls] * 0.7 : CAR_OFFW[r.cls] * (0.75 + j * 0.5);
  }
  function carSpawn(r, now) {
    const jit = 0.85 + Math.random() * 0.3, offJit = Math.random();
    // spawn out of sight when possible: of three candidate spots keep the one
    // farthest from the camera, so cars enter the world where nobody watches
    let s = Math.random() * r.len, bd = -1;
    for (let t = 0; t < 3; t++) {
      const cs = Math.random() * r.len;
      let g = 0;
      while (g < r.cum.length - 2 && r.cum[g + 1] < cs) g++;
      const dx2 = r.xs[g] - camera.position.x, dz2 = r.zs[g] - camera.position.z;
      const d2 = dx2 * dx2 + dz2 * dz2;
      if (d2 > bd) { bd = d2; s = cs; }
    }
    return { s, dir: r.oneway ? 1 : (Math.random() < 0.5 ? 1 : -1), off: carOffset(r, offJit), offJit, jit, seg: 0,
      v: TRAFFIC_SPEED[r.cls] / 3.6 * jit,
      col: CAR_PAL[(Math.random() * CAR_PAL.length) | 0],
      born: now, die: 0, fr: 0 };
  }
  function carTransfer(r, cIdx, car) {
    // the car reached the end of its run: continue through the joint onto a
    // connecting run. Weighted by the next street's volume and by how straight
    // the movement is; hard U-turns are refused (fade out at a true dead end).
    const end = car.dir > 0 ? 1 : 0;
    const conn = r.conn && r.conn[end];
    if (!conn) return null;
    const n = r.xs.length;
    let hx = end ? r.xs[n - 1] - r.xs[n - 2] : r.xs[0] - r.xs[1];
    let hz = end ? r.zs[n - 1] - r.zs[n - 2] : r.zs[0] - r.zs[1];
    const hL = Math.hypot(hx, hz) || 1; hx /= hL; hz /= hL;
    let total = 0, pickR = null, pickEnd = 0;
    for (let q = 0; q < conn.length; q += 2) {
      const r2 = trafficRuns[conn[q]], e2 = conn[q + 1];
      if (e2 === 1 && r2.oneway) continue;             // can't enter a one-way at its far end
      const m = r2.xs.length;
      let ux = e2 ? r2.xs[m - 1] - r2.xs[m - 2] : r2.xs[1] - r2.xs[0];
      let uz = e2 ? r2.zs[m - 1] - r2.zs[m - 2] : r2.zs[1] - r2.zs[0];
      const L2 = Math.hypot(ux, uz) || 1;
      let dot = (hx * ux + hz * uz) / L2;
      if (e2) dot = -dot;                              // entering at the far end runs backwards
      if (dot < -0.55) continue;
      const w = r2.aadt * (0.25 + Math.max(0, dot));   // busy and straight pulls hardest
      total += w;
      if (Math.random() * total < w) { pickR = r2; pickEnd = e2; }
    }
    if (!pickR) return null;
    r.cars.splice(cIdx, 1);
    car.dir = pickEnd ? -1 : 1;
    car.s = pickEnd ? pickR.len : 0;
    car.seg = pickEnd ? pickR.cum.length - 2 : 0;
    car.v = TRAFFIC_SPEED[pickR.cls] / 3.6 * car.jit;
    car.off = carOffset(pickR, car.offJit);
    pickR.cars.push(car);
    return pickR;
  }
  function trafficReconcile(now) {
    const { frac } = trafficFrac();
    // the car budget follows the camera: full weight within 1.5 km of the eye,
    // gone past 4 km — a car four kilometres out is under a pixel, so the cap
    // is spent where it can be seen and the streets you look at actually flow
    const cx = camera.position.x, cy = camera.position.y, cz = camera.position.z;
    let implied = 0;
    for (const r of trafficRuns) {
      const dx = r.mx - cx, dz = r.mz - cz;
      const d = Math.sqrt(dx * dx + dz * dz + cy * cy);
      const w = d < 1500 ? 1 : d > 4000 ? 0 : (4000 - d) / 2500;
      r.want = w ? r.aadt * frac / TRAFFIC_SPEED[r.cls] * (r.len / 1000) * w : 0;
      implied += r.want;
    }
    TRAFFIC.scale = Math.min(1, TRAFFIC.cap / Math.max(1, implied));
    let n = 0;
    for (let i = 0; i < trafficRuns.length; i++) {
      const r = trafficRuns[i];
      const tgt = Math.min(60, Math.floor(r.want * TRAFFIC.scale + hash01(i * 7.3)));
      while (r.cars.length < tgt) r.cars.push(carSpawn(r, now));
      let extra = r.cars.length - tgt;
      if (extra > 0) {
        // retire the farthest-from-camera first, so churn stays out of sight
        const alive = r.cars.filter((c2) => !c2.die);
        alive.sort((a2, b2) => {
          const da = (r.xs[a2.seg] - cx) ** 2 + (r.zs[a2.seg] - cz) ** 2;
          const db = (r.xs[b2.seg] - cx) ** 2 + (r.zs[b2.seg] - cz) ** 2;
          return db - da;
        });
        for (let q = 0; q < alive.length && extra > 0; q++) { alive[q].die = now; extra--; }
      }
      n += Math.min(r.cars.length, tgt);
    }
    trafficCars = Math.min(n, TRAFFIC.cap);
    trafficStatus();
  }
  const TRAFFIC_DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  function trafficStatus() {
    if (!btnTraffic) return;
    const { dow } = trafficFrac();
    const h = Math.floor(clock.minutes / 60), m12 = ((h + 11) % 12) + 1, ap = h < 12 ? 'AM' : 'PM';
    const sc = TRAFFIC.scale < 0.85 ? ' · 1:' + Math.max(2, Math.round(1 / TRAFFIC.scale)) + ' Sample Nearby' : '';
    btnTraffic.title = 'Typical Traffic (R): ' + trafficCars + ' Cars · ' + TRAFFIC_DAYS[dow] + ' ' + m12 + ' ' + ap + sc;
    const el = document.getElementById('trafficCount');
    if (el) el.textContent = trafficCars ? String(trafficCars) : '';
  }
  function syncTrafficBtn() { syncLayerBtn(btnTraffic, TRAFFIC.on); }
  function toggleTraffic() { TRAFFIC.on = !TRAFFIC.on; syncTrafficBtn(); if (TRAFFIC.on) trafficNextRecon = 0; }
  if (btnTraffic) btnTraffic.addEventListener('click', toggleTraffic);
  syncTrafficBtn();
  function updateTraffic(now, dt) {
    if (!trafficReady) return;
    if (!TRAFFIC.on) {
      if (carMesh.count) { carMesh.count = 0; carLights.count = 0; carMesh.instanceMatrix.needsUpdate = true; carLights.instanceMatrix.needsUpdate = true; }
      return;
    }
    // reconcile on a cadence, and instantly when the clock jumps (slider drags)
    const dkey = clock.y + '-' + clock.m + '-' + clock.d;
    const dmin = Math.abs(clock.minutes - trafficLastMin);
    if (now >= trafficNextRecon || trafficLastDate !== dkey || (dmin > 2 && dmin < 1437)) {
      trafficNextRecon = now + 600;
      trafficLastMin = clock.minutes; trafficLastDate = dkey;
      trafficReconcile(now);
    }
    const night = clamp((nightUniform.value - 0.06) / 0.25, 0, 1);
    carLights.material.opacity = night;
    trafficFrame++;
    let i = 0, cDirty = -1;   // lowest slot that changed hands this frame; tints upload from there
    for (const r of trafficRuns) {
      const cars = r.cars;
      for (let c = cars.length - 1; c >= 0; c--) {
        const car = cars[c];
        if (car.fr === trafficFrame) continue;   // already handled after a transfer
        car.fr = trafficFrame;
        car.s += car.v * dt * car.dir;
        let fade = Math.min(1, (now - car.born) / 900);
        if (car.die) fade = Math.min(fade, Math.max(0, 1 - (now - car.die) / 900));
        if (car.die && fade <= 0) { cars.splice(c, 1); continue; }
        let rr = r;
        if (car.s < 0 || car.s > r.len) {
          if (car.die) { cars.splice(c, 1); continue; }
          const t = carTransfer(r, c, car);
          if (t) rr = t;
          else { car.s = clamp(car.s, 0, r.len); car.die = now; }   // true dead end: ease out in place
        }
        if (i >= TRAFFIC.cap) continue;
        let seg = car.seg;
        const last = rr.cum.length - 2;
        if (seg > last) seg = last;
        while (seg < last && car.s > rr.cum[seg + 1]) seg++;
        while (seg > 0 && car.s < rr.cum[seg]) seg--;
        car.seg = seg;
        const segL = (rr.cum[seg + 1] - rr.cum[seg]) || 1e-6;
        const tt = (car.s - rr.cum[seg]) / segL;
        const ux = (rr.xs[seg + 1] - rr.xs[seg]) / segL, uz = (rr.zs[seg + 1] - rr.zs[seg]) / segL;
        const hx = ux * car.dir, hz = uz * car.dir;
        _sp.set(rr.xs[seg] + (rr.xs[seg + 1] - rr.xs[seg]) * tt - hz * car.off,
                rr.ys[seg] + (rr.ys[seg + 1] - rr.ys[seg]) * tt,
                rr.zs[seg] + (rr.zs[seg + 1] - rr.zs[seg]) * tt + hx * car.off);
        _sq.setFromAxisAngle(TRAFFIC_UP, Math.atan2(-hz, hx));
        _ss.set(fade, fade, fade);
        _sm.compose(_sp, _sq, _ss);
        carMesh.setMatrixAt(i, _sm);
        // slots are dealt in iteration order, which shifts on every spawn, death
        // and transfer (any frame, not just reconcile): retint only a slot whose
        // occupant changed, and nothing on a frame where none did
        if (carSlot[i] !== car) {
          carSlot[i] = car;
          carMesh.setColorAt(i, _sc.setHex(car.col));
          if (cDirty < 0) cDirty = i;
        }
        if (night > 0) {
          // the lamp pair grows with distance so it never falls under a couple
          // of pixels — headlights read from blocks away, sheet metal doesn't
          const ls = fade * clamp(camera.position.distanceTo(_sp) / 150, 1, 5);
          _ss.set(ls, ls, ls);
          _sm.compose(_sp, _sq, _ss);
          carLights.setMatrixAt(i, _sm);
        }
        i++;
      }
    }
    carMesh.count = i;
    carLights.count = night > 0 ? i : 0;
    flushInst(carMesh, cDirty);
    if (night > 0) flushInst(carLights);   // daylight lamps are invisible at opacity 0: no upload
    TRAFFIC.n = i;
  }

  // ---------------------------------------------------------------- streetlights
  // Every city-maintained lamp: the Streets Department's Street_Poles inventory
  // (OpenDataPhilly, 200k poles citywide), baked by fetch_poles.py /
  // pack_poles.py into POLES_B64 (int16, 0.7 m units). At night each pole
  // carries one additive glow point — PSIP's LED conversions burn warm white,
  // the sodium remainder amber — sized with a screen-pixel floor so the whole
  // city glitters from altitude the way it does from a real approach path.
  // Near the camera the lamps also get instanced pole meshes (desktop only).
  const LIGHTS = { on: true, ready: false };
  const btnLights = document.getElementById('btnLights');
  const POLE_MESH_CAP = isTouch ? 0 : 1600;
  const POLE_MESH_R = 1000;
  let poleGlow = null, poleMesh = null, poleInv = null, poleMat = null;
  let towerGlow = null, towerMat = null;
  let floodPts = null, floodMat = null;   // the stadiums' floodlights (built with the outer districts)
  let haloMesh = null, haloMat = null;     // and their night halo
  let STOREFRONT_N = 0;                    // storefronts dressed (perf readout)
  let WALL_N = 0;   // outer-district buildings that took a Mapillary wall colour (__dbg.walls)
  let TOWER_CROWN_N = 0;   // researched tower crowns raised (__dbg.towers)
  let lotStripes = null;                   // the sports complex's stall lines (shown within 3.5 km, they alias into noise beyond)
  const LOT_CENTER = new V3(-2050, 20, 4650);
  let poleReconAt = 0;
  const poleLastCam = new THREE.Vector3(1e9, 0, 0);
  const _plm = new THREE.Matrix4(), _plq = new THREE.Quaternion(), _pls = new THREE.Vector3(), _plp = new THREE.Vector3();
  step('Lighting the streetlamps', () => {
    if (typeof POLES_B64 === 'undefined' || !POLES_B64) { if (btnLights) btnLights.style.display = 'none'; return; }
    let head, v;
    try {
      const buf = unb64(POLES_B64, 'POLES');
      POLES_B64 = null;   // free the base64 source
      head = new Int32Array(buf.buffer, 0, 4);
      if (head[0] !== 0x53485450) throw new Error('bad pole magic');
      v = new Int16Array(buf.buffer, 16);
    } catch (err) { console.error('street pole decode failed', err); if (btnLights) btnLights.style.display = 'none'; return; }
    const nAll = head[1];
    const X = new Float32Array(nAll), Z = new Float32Array(nAll), GY = new Float32Array(nAll), HM = new Float32Array(nAll);
    const pos = new Float32Array(nAll * 3), pcol = new Float32Array(nAll * 3);
    const cells = new Map();   // 400 m buckets for the near-mesh reconcile
    for (let i = 0; i < nAll; i++) {
      const x = v[i * 3] * 0.7, z = v[i * 3 + 1] * 0.7, pk = v[i * 3 + 2];
      const kind = pk & 3, hft = (pk >> 2) & 127, lum2 = (pk >> 9) & 1;
      const gy = siteY(x, z, 'ground');
      const hm = clamp(hft * 0.3048, 3.5, 15);
      X[i] = x; Z[i] = z; GY[i] = gy; HM[i] = hm;
      pos[i * 3] = x; pos[i * 3 + 1] = gy + hm; pos[i * 3 + 2] = z;
      // lamp color IS the light (additive, tone mapping off): LED warm white,
      // sodium amber; unknowns (mostly wood alley poles) lean dim, some amber
      let r, g2, b;
      if (kind === 1) { r = 1.0; g2 = 0.52; b = 0.16; }
      else if (kind === 2) { const amber = hash01(i * 7.3) < 0.3; r = 1.0; g2 = amber ? 0.58 : 0.78; b = amber ? 0.2 : 0.48; }
      else { r = 1.0; g2 = 0.8; b = 0.55; }
      const amp = (0.9 + hash01(i * 3.7 + 1.1) * 0.25) * (lum2 ? 1.25 : 1) * (hft >= 38 ? 1.35 : hft <= 16 ? 0.65 : 1);
      pcol[i * 3] = r * amp; pcol[i * 3 + 1] = g2 * amp; pcol[i * 3 + 2] = b * amp;
      const ck = Math.floor(x / 400) + ':' + Math.floor(z / 400);
      let arr = cells.get(ck);
      if (!arr) { arr = []; cells.set(ck, arr); }
      arr.push(i);
    }
    const pg = new THREE.BufferGeometry();
    pg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    pg.setAttribute('color', new THREE.BufferAttribute(pcol, 3));
    poleMat = new THREE.PointsMaterial({ vertexColors: true, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false, sizeAttenuation: false, size: renderer.getPixelRatio() });
    poleMat.onBeforeCompile = (shader) => {
      // perspective size with a floor: a lamp never falls under ~2 physical px,
      // so the far city reads as a carpet of lights (same trick as headlights)
      shader.vertexShader = shader.vertexShader.replace('gl_PointSize = size;',
        'gl_PointSize = size * clamp(1600.0 / max(1.0, -mvPosition.z), 2.0, 9.0);');
      shader.fragmentShader = shader.fragmentShader.replace('#include <color_fragment>',
        '#include <color_fragment>\n\tdiffuseColor.a *= smoothstep(0.5, 0.18, length(gl_PointCoord - vec2(0.5)));');
    };
    postRaw(poleMat);
    poleGlow = new THREE.Points(pg, poleMat);
    poleGlow.frustumCulled = false;
    poleGlow.renderOrder = 11;
    poleGlow.visible = false;
    groupCity.add(poleGlow);
    if (POLE_MESH_CAP > 0) {
      // one instanced pole: tapered shaft + arm + head, 9 m reference height,
      // y-scaled per pole (uniform-in-plane, so the rotation gotcha never bites)
      const mergePlain = (list) => {
        const parts2 = list.map((g3) => (g3.index ? g3.toNonIndexed() : g3));
        let total = 0;
        for (const g3 of parts2) total += g3.attributes.position.count;
        const p2 = new Float32Array(total * 3), n2 = new Float32Array(total * 3);
        let o2 = 0;
        for (const g3 of parts2) {
          p2.set(g3.attributes.position.array, o2 * 3);
          n2.set(g3.attributes.normal.array, o2 * 3);
          o2 += g3.attributes.position.count;
        }
        const out = new THREE.BufferGeometry();
        out.setAttribute('position', new THREE.BufferAttribute(p2, 3));
        out.setAttribute('normal', new THREE.BufferAttribute(n2, 3));
        return out;
      };
      const poleGeo = mergePlain([
        new THREE.CylinderGeometry(0.07, 0.13, 9, 5).translate(0, 4.5, 0),
        new THREE.CylinderGeometry(0.05, 0.05, 1.7, 4).rotateZ(Math.PI / 2).translate(0.8, 8.84, 0),
        new THREE.BoxGeometry(0.62, 0.14, 0.26).translate(1.5, 8.88, 0),
      ]);
      poleMesh = new THREE.InstancedMesh(poleGeo, new THREE.MeshStandardMaterial({ color: 0x2a2a2c, roughness: 0.9, metalness: 0.15 }), POLE_MESH_CAP);
      poleMesh.count = 0;
      poleMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      poleMesh.frustumCulled = false;
      groupCity.add(poleMesh);
    }
    poleInv = { X, Z, GY, HM, cells, n: nAll };
    const el = document.getElementById('lightsCount');
    if (el) el.textContent = Math.round(nAll / 1000) + 'k';
    LIGHTS.ready = true;
  });
  step('Lighting the skyline', () => {
    // tall buildings wear lit windows that survive distance: additive points
    // scattered on the shaft perimeter with the same screen-px floor as the
    // streetlamps, so the night skyline reads as towers of light instead of
    // black slabs ringed by lamps. The size term fades the points OUT under
    // ~450 m — up close the painted facade windows take over — and every
    // hash is seeded, so the same offices burn every night.
    if (!tallGlow.length) return;
    const tp = [], tc = [];
    for (let bi = 0; bi < tallGlow.length; bi++) {
      const tg = tallGlow[bi];
      const np2 = tg.poly.length;
      const nP = Math.min(56, Math.max(5, Math.round(tg.h / 5)));
      for (let q2 = 0; q2 < nP; q2++) {
        const sd = bi * 131.7 + q2 * 17.3;
        if (hash01(sd + 0.4) < 0.42) continue;   // dark offices stay dark
        const e2 = Math.floor(hash01(sd + 1.1) * np2);
        const p0 = tg.poly[e2], p1 = tg.poly[(e2 + 1) % np2];
        const tt = hash01(sd + 2.2);
        let px2 = p0[0] + (p1[0] - p0[0]) * tt, pz2 = p0[1] + (p1[1] - p0[1]) * tt;
        const ox = px2 - tg.x, oz2 = pz2 - tg.z, ol = Math.hypot(ox, oz2) || 1;
        px2 += (ox / ol) * 0.8; pz2 += (oz2 / ol) * 0.8;   // proud of the wall so depth keeps them
        tp.push(px2, tg.b + tg.h * (0.18 + 0.76 * hash01(sd + 3.3)), pz2);
        const cool = hash01(sd + 4.4) < 0.16;
        const amp2 = 0.55 + hash01(sd + 5.5) * 0.5;
        tc.push((cool ? 0.72 : 1.0) * amp2, (cool ? 0.84 : 0.86) * amp2, (cool ? 1.0 : 0.6) * amp2);
      }
    }
    const tg2 = new THREE.BufferGeometry();
    tg2.setAttribute('position', new THREE.BufferAttribute(new Float32Array(tp), 3));
    tg2.setAttribute('color', new THREE.BufferAttribute(new Float32Array(tc), 3));
    towerMat = new THREE.PointsMaterial({ vertexColors: true, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false, sizeAttenuation: false, size: renderer.getPixelRatio() });
    towerMat.onBeforeCompile = (shader) => {
      shader.vertexShader = shader.vertexShader.replace('gl_PointSize = size;',
        'gl_PointSize = size * clamp(1300.0 / max(1.0, -mvPosition.z), ' + (isTouch ? '2.2' : '1.5') + ', 4.5) * smoothstep(' + (isTouch ? '200.0, 620.0' : '420.0, 1150.0') + ', -mvPosition.z);');   // phones: in from 200 m, never under 2.2 px
      shader.fragmentShader = shader.fragmentShader.replace('#include <color_fragment>',
        '#include <color_fragment>\n\tdiffuseColor.a *= smoothstep(0.5, 0.2, length(gl_PointCoord - vec2(0.5)));');
    };
    postRaw(towerMat);
    towerGlow = new THREE.Points(tg2, towerMat);
    towerGlow.frustumCulled = false;
    towerGlow.renderOrder = 11;
    towerGlow.visible = false;
    groupCity.add(towerGlow);
  });
  function poleReconcile() {
    const cx = camera.position.x, cz = camera.position.z;
    const cellR = Math.ceil(POLE_MESH_R / 400);
    const gx0 = Math.floor(cx / 400), gz0 = Math.floor(cz / 400);
    const cand = [];
    for (let gx = gx0 - cellR; gx <= gx0 + cellR; gx++) for (let gz = gz0 - cellR; gz <= gz0 + cellR; gz++) {
      const arr = poleInv.cells.get(gx + ':' + gz);
      if (arr) for (const i of arr) {
        const dx = poleInv.X[i] - cx, dz = poleInv.Z[i] - cz;
        const d2 = dx * dx + dz * dz;
        if (d2 < POLE_MESH_R * POLE_MESH_R) cand.push([d2, i]);
      }
    }
    if (cand.length > POLE_MESH_CAP) cand.sort((a2, b2) => a2[0] - b2[0]);
    const nUse = Math.min(POLE_MESH_CAP, cand.length);
    for (let q = 0; q < nUse; q++) {
      const i = cand[q][1];
      _plp.set(poleInv.X[i], poleInv.GY[i], poleInv.Z[i]);
      _plq.setFromAxisAngle(TRAFFIC_UP, hash01(i * 1.7 + 0.3) * Math.PI * 2);
      _pls.set(1, poleInv.HM[i] / 9, 1);
      _plm.compose(_plp, _plq, _pls);
      poleMesh.setMatrixAt(q, _plm);
    }
    poleMesh.count = nUse;
    poleMesh.instanceMatrix.needsUpdate = true;
  }
  function syncLightsBtn() { syncLayerBtn(btnLights, LIGHTS.on); }
  function toggleLightsLayer() { LIGHTS.on = !LIGHTS.on; syncLightsBtn(); }
  if (btnLights) btnLights.addEventListener('click', toggleLightsLayer);
  syncLightsBtn();
  function updateLights(now) {
    // lamps come on at civil dusk, a beat before the headlights
    const night = clamp((nightUniform.value - 0.02) / 0.2, 0, 1);
    // tower windows are building light, not street light — they ignore the G
    // layer and outlive a missing pole blob
    if (towerGlow) {
      towerGlow.visible = night > 0.01;
      if (towerGlow.visible) towerMat.opacity = night;
      if (floodPts) { floodPts.visible = night > 0.01; floodMat.opacity = night * 0.95; }
      if (haloMesh) { haloMesh.visible = night > 0.01; haloMat.opacity = night * 0.16; }
    }
    if (!LIGHTS.ready) return;
    const show = LIGHTS.on && night > 0.01;
    poleGlow.visible = show;
    if (show) poleMat.opacity = night;
    if (poleMesh) {
      poleMesh.visible = LIGHTS.on;
      if (LIGHTS.on && (now >= poleReconAt || camera.position.distanceToSquared(poleLastCam) > 220 * 220)) {
        poleReconAt = now + 900;
        poleLastCam.copy(camera.position);
        poleReconcile();
      }
    }
  }

  // ---------------------------------------------------------------- solar clock
  // NOAA solar position for the towers' latitude/longitude; Philadelphia local
  // time with US daylight-saving rules. Drives sun, sky, fog, and the lit windows.
  const SITE = { lat: 39.9455, lon: -75.1447 };
  const DEG = Math.PI / 180;
  function nthSunday(year, month0, nth) { // month0: 0-based; returns UTC ms at 02:00 local-ish (date part only matters)
    const first = new Date(Date.UTC(year, month0, 1));
    const dow = first.getUTCDay();
    const day = 1 + ((7 - dow) % 7) + (nth - 1) * 7;
    return Date.UTC(year, month0, day);
  }
  function tzOffsetMin(y, m, d) { // minutes to add to UTC to get Philadelphia local time
    const t = Date.UTC(y, m - 1, d);
    const start = nthSunday(y, 2, 2), end = nthSunday(y, 10, 1);
    return (t >= start && t < end) ? -240 : -300;
  }
  function solar(utcMs) {
    const JD = utcMs / 86400000 + 2440587.5;
    const T = (JD - 2451545) / 36525;
    const L0 = ((280.46646 + T * (36000.76983 + T * 0.0003032)) % 360 + 360) % 360;
    const M = 357.52911 + T * (35999.05029 - 0.0001537 * T);
    const e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T);
    const C = Math.sin(M * DEG) * (1.914602 - T * (0.004817 + 0.000014 * T)) + Math.sin(2 * M * DEG) * (0.019993 - 0.000101 * T) + Math.sin(3 * M * DEG) * 0.000289;
    const omega = 125.04 - 1934.136 * T;
    const lambda = L0 + C - 0.00569 - 0.00478 * Math.sin(omega * DEG);
    const eps0 = 23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60) / 60;
    const eps = eps0 + 0.00256 * Math.cos(omega * DEG);
    const dec = Math.asin(Math.sin(eps * DEG) * Math.sin(lambda * DEG));
    const y = Math.tan(eps * DEG / 2) ** 2;
    const eot = 4 * (y * Math.sin(2 * L0 * DEG) - 2 * e * Math.sin(M * DEG) + 4 * e * y * Math.sin(M * DEG) * Math.cos(2 * L0 * DEG) - 0.5 * y * y * Math.sin(4 * L0 * DEG) - 1.25 * e * e * Math.sin(2 * M * DEG)) / DEG;
    const utcMin = (utcMs / 60000) % 1440;
    const tst = (utcMin + eot + 4 * SITE.lon + 1440) % 1440;
    const H = (tst / 4 - 180) * DEG;
    const lat = SITE.lat * DEG;
    const E = -Math.cos(dec) * Math.sin(H);
    const N = Math.sin(dec) * Math.cos(lat) - Math.cos(dec) * Math.cos(H) * Math.sin(lat);
    const U = Math.sin(dec) * Math.sin(lat) + Math.cos(dec) * Math.cos(H) * Math.cos(lat);
    return { elev: Math.asin(clamp(U, -1, 1)) / DEG, dir: new V3(E, U, -N).normalize() };
  }
  // the real Moon over Philadelphia: Schlyter's lunar theory (position to ~1-2
  // arcmin here, plenty for a sky disc), topocentric, plus phase from the
  // Sun-Moon elongation. Same az/el -> world mapping as solar().
  function lunar(utcMs) {
    const R = DEG;
    // Schlyter's epoch is "2000 Jan 0.0" = 1999-12-31 00:00 UT, NOT J2000.0 —
    // the 1.5 day difference is a 20 degree lunar longitude error
    const d = utcMs / 86400000 - 10956.0;
    const rev = (a) => ((a % 360) + 360) % 360;
    const Nm = rev(125.1228 - 0.0529538083 * d);
    const im = 5.1454 * R;
    const wm = rev(318.0634 + 0.1643573223 * d);
    const em = 0.0549;
    const Mm = rev(115.3654 + 13.0649929509 * d);
    const ws = rev(282.9404 + 4.70935e-5 * d);
    const Ms = rev(356.047 + 0.9856002585 * d);
    let E = Mm + (em / R) * Math.sin(Mm * R) * (1 + em * Math.cos(Mm * R));
    for (let i = 0; i < 4; i++) E = E - (E - (em / R) * Math.sin(E * R) - Mm) / (1 - em * Math.cos(E * R));
    const xv = 60.2666 * (Math.cos(E * R) - em);
    const yv = 60.2666 * Math.sqrt(1 - em * em) * Math.sin(E * R);
    const v = Math.atan2(yv, xv) / R;
    let r = Math.sqrt(xv * xv + yv * yv);
    const u = (v + wm) * R;
    const xh = r * (Math.cos(Nm * R) * Math.cos(u) - Math.sin(Nm * R) * Math.sin(u) * Math.cos(im));
    const yh = r * (Math.sin(Nm * R) * Math.cos(u) + Math.cos(Nm * R) * Math.sin(u) * Math.cos(im));
    const zh = r * Math.sin(u) * Math.sin(im);
    let lon = Math.atan2(yh, xh) / R;
    let lat = Math.atan2(zh, Math.sqrt(xh * xh + yh * yh)) / R;
    // the Sun's true longitude (for perturbations and phase)
    let Es = Ms + (0.016709 / R) * Math.sin(Ms * R) * (1 + 0.016709 * Math.cos(Ms * R));
    const xs = Math.cos(Es * R) - 0.016709, ys = Math.sqrt(1 - 0.016709 * 0.016709) * Math.sin(Es * R);
    const slon = rev(Math.atan2(ys, xs) / R + ws);
    // major lunar perturbations (Schlyter's series; D and the sidereal base use
    // the Sun's MEAN longitude, the phase uses the true one)
    const Lsun = rev(Ms + ws);
    const Lm = rev(Mm + wm + Nm), D2 = rev(Lm - Lsun), F = rev(Lm - Nm);
    lon += -1.274 * Math.sin((Mm - 2 * D2) * R) + 0.658 * Math.sin(2 * D2 * R) - 0.186 * Math.sin(Ms * R)
         - 0.059 * Math.sin((2 * Mm - 2 * D2) * R) - 0.057 * Math.sin((Mm - 2 * D2 + Ms) * R)
         + 0.053 * Math.sin((Mm + 2 * D2) * R) + 0.046 * Math.sin((2 * D2 - Ms) * R)
         + 0.041 * Math.sin((Mm - Ms) * R) - 0.035 * Math.sin(D2 * R) - 0.031 * Math.sin((Mm + Ms) * R)
         - 0.015 * Math.sin((2 * F - 2 * D2) * R) + 0.011 * Math.sin((Mm - 4 * D2) * R);
    lat += -0.173 * Math.sin((F - 2 * D2) * R) - 0.055 * Math.sin((Mm - F - 2 * D2) * R)
         - 0.046 * Math.sin((Mm + F - 2 * D2) * R) + 0.033 * Math.sin((F + 2 * D2) * R) + 0.017 * Math.sin((2 * Mm + F) * R);
    r += -0.58 * Math.cos((Mm - 2 * D2) * R) - 0.46 * Math.cos(2 * D2 * R);
    const ecl = (23.4393 - 3.563e-7 * d) * R;
    const xg = Math.cos(lon * R) * Math.cos(lat * R), yg = Math.sin(lon * R) * Math.cos(lat * R), zg = Math.sin(lat * R);
    const xe = xg, ye = yg * Math.cos(ecl) - zg * Math.sin(ecl), ze = yg * Math.sin(ecl) + zg * Math.cos(ecl);
    const ra = rev(Math.atan2(ye, xe) / R), dec = Math.atan2(ze, Math.sqrt(xe * xe + ye * ye)) / R;
    const utH = ((utcMs % 86400000) + 86400000) % 86400000 / 3600000;
    const LSTdeg = rev(rev(Lsun + 180) + utH * 15 + SITE.lon);
    let ha = LSTdeg - ra;
    ha = ((ha % 360) + 540) % 360 - 180;
    const lat0 = SITE.lat * R;
    const sinEl = Math.sin(lat0) * Math.sin(dec * R) + Math.cos(lat0) * Math.cos(dec * R) * Math.cos(ha * R);
    let el = Math.asin(clamp(sinEl, -1, 1));
    el -= Math.asin(1 / r) * Math.cos(el);                    // topocentric parallax
    const Ea = -Math.cos(dec * R) * Math.sin(ha * R);
    const Na = Math.sin(dec * R) * Math.cos(lat0) - Math.cos(dec * R) * Math.cos(ha * R) * Math.sin(lat0);
    const az = rev(Math.atan2(Ea, Na) / R);
    const dir = new V3(Math.sin(az * R) * Math.cos(el), Math.sin(el), -Math.cos(az * R) * Math.cos(el)).normalize();
    const elong = Math.acos(clamp(Math.cos(lat * R) * Math.cos((lon - slon) * R), -1, 1));
    return { dir, el: el / R, az, k: (1 - Math.cos(elong)) / 2, wax: Math.sin((lon - slon) * R) > 0 };
  }
  const clock = { y: 2026, m: 8, d: 23, minutes: 720, live: true };
  function clockUtcMs(c, minutes) { return Date.UTC(c.y, c.m - 1, c.d) + (minutes - tzOffsetMin(c.y, c.m, c.d)) * 60000; }
  function setClockToNow() {
    const now = new Date();
    // two passes: the offset belongs to the LOCAL date, and from ~19:00 on the
    // two transition evenings the UTC date is already tomorrow's
    let off = tzOffsetMin(now.getUTCFullYear(), now.getUTCMonth() + 1, now.getUTCDate());
    let loc = new Date(now.getTime() + off * 60000);
    off = tzOffsetMin(loc.getUTCFullYear(), loc.getUTCMonth() + 1, loc.getUTCDate());
    loc = new Date(now.getTime() + off * 60000);
    clock.y = loc.getUTCFullYear(); clock.m = loc.getUTCMonth() + 1; clock.d = loc.getUTCDate();
    clock.minutes = loc.getUTCHours() * 60 + loc.getUTCMinutes();
  }
  function sunTimes(c) { // local minutes of sunrise / sunset (elevation crossing -0.833 deg)
    let rise = null, set = null, prev = null;
    for (let mnt = 0; mnt <= 1440; mnt += 2) {
      const el = solar(clockUtcMs(c, mnt)).elev;
      if (prev !== null) {
        if (prev < -0.833 && el >= -0.833) rise = mnt;
        if (prev >= -0.833 && el < -0.833) set = mnt;
      }
      prev = el;
    }
    return { rise, set };
  }
  function fmtTime(mnt) {
    if (mnt == null) return '';
    let h = Math.floor(mnt / 60) % 24; const mm = Math.round(mnt % 60);
    const ap = h >= 12 ? 'PM' : 'AM'; h = h % 12; if (h === 0) h = 12;
    return h + ':' + (mm < 10 ? '0' : '') + mm + ' ' + ap;
  }
  // ---- live weather (Open-Meteo). The claude.ai artifact sandbox blocks external
  // fetches, so there we keep the fair-weather default; on GitHub Pages / local /
  // philly3d.com it pulls real Philadelphia conditions every 15 minutes. The WMO
  // weather code classifies into rain / snow / sleet / fog / thunderstorm, which
  // drives the particle boxes, storm gloom, lightning and weather fog below.
  // (WX itself is declared before the sky material — refreshEnv reads it at init.)
  function applyWx(js) {
    const cur = js && js.current;
    if (!cur) return;
    WX.code = cur.weather_code == null ? -1 : cur.weather_code;
    WX.temp = cur.temperature_2m == null ? null : cur.temperature_2m;
    WX.precip = Math.max(cur.precipitation || 0, (cur.rain || 0) + (cur.showers || 0));
    WX.snowfall = cur.snowfall || 0;
    WX.cover = clamp((cur.cloud_cover == null ? 22 : cur.cloud_cover) / 100, 0, 1);
    if (WX.precip > 0.1) WX.cover = Math.max(WX.cover, 0.85);
    if (WX.snowfall > 0.02) WX.cover = Math.max(WX.cover, 0.8);
    if (WX.code === 45 || WX.code === 48) WX.cover = Math.max(WX.cover, 0.55);
    if (WX.code >= 95) WX.cover = Math.max(WX.cover, 0.97);
    if (WX.nwsCover && performance.now() - WX.nwsT < 20 * 60000) WX.cover = Math.max(WX.cover, WX.nwsCover);
    const spd = (cur.wind_speed_10m == null ? 8 : cur.wind_speed_10m) / 3.6;
    const dir = ((cur.wind_direction_10m == null ? 250 : cur.wind_direction_10m) + 180) * Math.PI / 180;
    WX.windX = Math.sin(dir) * spd; WX.windZ = -Math.cos(dir) * spd;   // world m/s, the clouds' heading
    const drift = 0.0008 + spd * 0.00035;
    wxWind.set(Math.sin(dir) * drift, -Math.cos(dir) * drift);
    // the water chop follows the real wind: calm glass at 0, whitecap energy by ~9 m/s
    waterU.uWAmp.value = clamp(0.5 + spd * 0.14, 0.5, 1.8);
    waterU.uWDir.value.set(Math.sin(dir) || 0.86, -Math.cos(dir) || 0.5);
    WX.ok = true;
    wxSetTargets();
    lastEnvEl = 999;   // rebake glass reflections with the new cloud deck
    refreshTimeUI();
  }
  const wxCanFetch = !/claude|usercontent/i.test(location.hostname);
  // ?wx=<preset> pins conditions for demos and testing (it works even in the
  // artifact, where live fetches are walled off); __dbg.wx('storm') from the
  // ?dev console does the same at runtime.
  const WX_PRESETS = {
    clear: { cloud_cover: 8, weather_code: 0, wind_speed_10m: 10, temperature_2m: 74 },
    overcast: { cloud_cover: 92, weather_code: 3, wind_speed_10m: 14, temperature_2m: 66 },
    fog: { cloud_cover: 70, weather_code: 45, wind_speed_10m: 4, temperature_2m: 57 },
    drizzle: { cloud_cover: 88, precipitation: 0.4, weather_code: 53, wind_speed_10m: 12, temperature_2m: 61 },
    rain: { cloud_cover: 95, precipitation: 3.2, weather_code: 63, wind_speed_10m: 22, temperature_2m: 63 },
    downpour: { cloud_cover: 100, precipitation: 11, weather_code: 65, wind_speed_10m: 30, temperature_2m: 65 },
    storm: { cloud_cover: 100, precipitation: 9, weather_code: 95, wind_speed_10m: 42, temperature_2m: 72 },
    hail: { cloud_cover: 100, precipitation: 13, weather_code: 96, wind_speed_10m: 46, temperature_2m: 68 },
    snow: { cloud_cover: 94, snowfall: 1.1, weather_code: 73, wind_speed_10m: 14, temperature_2m: 28 },
    blizzard: { cloud_cover: 100, snowfall: 3.4, weather_code: 75, wind_speed_10m: 38, temperature_2m: 21 },
    sleet: { cloud_cover: 96, precipitation: 1.4, weather_code: 66, wind_speed_10m: 18, temperature_2m: 31 },
  };
  const wxForced = (/[?&]wx=([a-z]+)/i.exec(location.search) || [])[1];
  // a miss retries on its own clock, 60 s doubling to the 15 min cadence, one
  // pending timer at a time; a success drops it. Hidden tabs skip the fetch
  // and catch up on return once the last good report is 15 min stale.
  let wxOkT = -Infinity, wxRetry = 0, wxBackoff = 60000;
  function fetchWeather() {
    if (!wxCanFetch || WX_PRESETS[wxForced] || document.hidden) return;
    if (wxRetry) { clearTimeout(wxRetry); wxRetry = 0; }
    try {
      fetch('https://api.open-meteo.com/v1/forecast?latitude=39.9455&longitude=-75.1447&current=cloud_cover,precipitation,rain,showers,snowfall,weather_code,temperature_2m,wind_speed_10m,wind_direction_10m&temperature_unit=fahrenheit',
        { signal: AbortSignal.timeout ? AbortSignal.timeout(15000) : undefined })
        .then(r => (r && r.ok ? r.json() : Promise.reject(new Error('http ' + (r && r.status)))))
        .then((js) => { wxOkT = performance.now(); wxBackoff = 60000; applyWx(js); })
        .catch(() => {
          wxRetry = setTimeout(fetchWeather, wxBackoff);
          wxBackoff = Math.min(wxBackoff * 2, 15 * 60 * 1000);
        });
    } catch (e) { /* sandboxed */ }
  }
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && performance.now() - wxOkT > 15 * 60 * 1000) fetchWeather();
    if (!document.hidden && performance.now() - WX.nwsT > 5 * 60 * 1000) fetchNws();
  });
  // the National Weather Service: the latest METAR-style observation at PHL and
  // Northeast Airport (presentWeather carries TS when thunder is heard there)
  // and the active alerts for the site. The API is CORS-open; nothing is keyed.
  const NWS_STATIONS = ['KPHL', 'KPNE'];
  // Real lightning: ops/lightning_relay.py keeps one subscription to the
  // Blitzortung community relay and writes lightning.json every 2 s (strikes
  // within 110 km for 15 min). The page polls it every 4 s and draws a bolt at
  // each new strike's real position, so the storm over New Jersey shows from
  // here. While the feed is live the synthetic random bolts stand down.
  const LIGHTNING_URL = (location.hostname === 'localhost' || location.hostname === '127.0.0.1') ? '/lightning.json' : 'https://philly3d.com/lightning.json';
  const LTN = { live: false, ok: false, busy: false, fails: 0, nextT: 0, lastSeen: 0, queue: [], n10: 0, nearestKm: null, n: 0, drawn: 0, nextDraw: 0 };
  const LTN_DRAW_KM = 80;   // 50 miles
  function ltnPoll(now) {
    if (!wxCanFetch || WX_PRESETS[wxForced] || LTN.busy || now < LTN.nextT || document.hidden) return;
    LTN.busy = true;
    LTN.nextT = now + (LTN.live ? 4000 : Math.min(300000, 20000 * Math.pow(2, Math.min(LTN.fails, 4))));
    const ctl = typeof AbortController !== 'undefined' ? new AbortController() : null;
    const timer = ctl ? setTimeout(() => ctl.abort(), 8000) : 0;
    const miss = () => { clearTimeout(timer); LTN.busy = false; LTN.fails++; if (LTN.fails >= 2 && LTN.live) { LTN.live = false; wxSetTargets(); } };
    fetch(LIGHTNING_URL, { cache: 'no-store', signal: ctl ? ctl.signal : undefined })
      .then((r) => { if (!r.ok) throw new Error('http ' + r.status); return r.json().then((d) => ({ d, now: serverNow(r) })); })
      .then(({ d, now: sNow }) => {
        clearTimeout(timer);
        if (!d || !Array.isArray(d.strikes) || !(d.t > 0) || sNow - d.t > 30) { miss(); return; }   // stale: the relay is down
        LTN.busy = false; LTN.fails = 0; LTN.ok = true;
        const wasLive = LTN.live, wasN = LTN.n10;
        LTN.live = true;
        LTN.n = d.strikes.length; LTN.n10 = d.n10 || 0; LTN.nearestKm = d.nearest_km == null ? null : d.nearest_km;
        // queue only what is new; a first poll (or a long gap) shows the last few, not the backlog
        // a storm cell flickers many times a minute; the page shows one strike at a
        // time, the nearest of what arrived, so a busy night reads as lightning
        // in the distance rather than a strobe
        const fresh = d.strikes.filter((st) => st[0] > LTN.lastSeen && st[3] <= LTN_DRAW_KM);
        if (fresh.length) { fresh.sort((a, b) => a[3] - b[3]); LTN.queue = fresh.slice(0, 2); }
        for (const st of d.strikes) if (st[0] > LTN.lastSeen) LTN.lastSeen = st[0];
        if (!wasLive || (wasN >= 3) !== (LTN.n10 >= 3)) { wxSetTargets(); refreshTimeUI(); }
      })
      .catch(miss);
  }
  let nwsBusy = false;
  function fetchNws() {
    if (!wxCanFetch || WX_PRESETS[wxForced] || document.hidden || nwsBusy) return;
    nwsBusy = true;
    const opts = { headers: { Accept: 'application/geo+json' }, signal: AbortSignal.timeout ? AbortSignal.timeout(15000) : undefined };
    const get = (u) => fetch(u, opts).then((r) => (r && r.ok ? r.json() : null)).catch(() => null);
    Promise.all([...NWS_STATIONS.map((st) => get('https://api.weather.gov/stations/' + st + '/observations/latest')),
      get('https://api.weather.gov/alerts/active?point=39.9455,-75.1447')]).then((rs) => {
      nwsBusy = false;
      const obs = rs.slice(0, NWS_STATIONS.length), al = rs[NWS_STATIONS.length];
      let any = false, tsObs = false, text = '', nwsCover = 0;
      for (const o of obs) {
        const pr = o && o.properties;
        if (!pr) continue;
        any = true;
        const age = pr.timestamp ? (Date.now() - Date.parse(pr.timestamp)) / 60000 : 999;
        if (age > 75) continue;   // an hourly report older than that says nothing about now
        const pw = Array.isArray(pr.presentWeather) ? pr.presentWeather : [];
        const ts = pw.some((w) => /thunder/i.test(w.weather || '') || /TS/.test(w.rawString || '')) || /thunder/i.test(pr.textDescription || '');
        if (ts) tsObs = true;
        for (const cl of (pr.cloudLayers || [])) { const a = String(cl.amount || ''); if (a === 'OVC') nwsCover = Math.max(nwsCover, 0.97); else if (a === 'BKN') nwsCover = Math.max(nwsCover, 0.8); }
        if (!text && pr.textDescription) text = pr.textDescription;
      }
      let warn = false, watch = false;
      if (al && Array.isArray(al.features)) {
        any = true;
        for (const f of al.features) {
          const ev = String((f.properties || {}).event || '');
          if (/Severe Thunderstorm Warning|Tornado Warning/i.test(ev)) warn = true;
          else if (/Severe Thunderstorm Watch|Tornado Watch/i.test(ev)) watch = true;
          else if (/Special Weather Statement/i.test(ev) && /thunder|lightning/i.test(String((f.properties || {}).description || ''))) watch = true;
        }
      }
      if (!any) return;   // both calls failed: keep the last facts until they expire
      WX.tsObs = tsObs; WX.tsWarn = warn; WX.tsWatch = watch; WX.nwsText = text; WX.nwsT = performance.now(); WX.nwsCover = nwsCover;
      if (nwsCover > WX.cover) WX.cover = nwsCover;   // an observed overcast deck beats the model's cloud estimate
      if (WX.ok) { wxSetTargets(); refreshTimeUI(); }
    }).catch(() => { nwsBusy = false; });
  }
  function wxLabel() {
    const c = WX.code;
    return c === 45 || c === 48 ? 'Fog' : c >= 51 && c <= 55 ? 'Drizzle'
      : c === 56 || c === 57 ? 'Freezing drizzle' : c === 61 || c === 80 ? 'Light rain'
      : c === 63 || c === 81 ? 'Rain' : c === 65 || c === 82 ? 'Heavy rain'
      : c === 66 || c === 67 ? 'Freezing rain' : c === 71 || c === 77 || c === 85 ? 'Light snow'
      : c === 73 ? 'Snow' : c === 75 || c === 86 ? 'Heavy snow'
      : c === 95 ? 'Thunderstorm' : c === 96 || c === 99 ? 'Thunderstorm, hail' : '';
  }
  function wxLabelFull() {   // the readout: the NWS storm state wins over the model code
    const base = wxLabel();
    if (!WXFX.storm || WX.code >= 95) return base;
    const why = WX.tsWarn ? 'Severe Thunderstorm Warning' : WX.tsObs ? 'Thunderstorm' : 'Thunderstorm Watch';
    return base ? base + ', ' + why : why;
  }

  // ---- weather FX. Two camera-following particle boxes (rain streaks as line
  // pairs, snowflakes as soft points) advect in world space and wrap through a
  // box around the camera via mod(), so flying through a storm streams it past
  // correctly instead of carrying it along. Strengths ease toward the targets
  // wxSetTargets derives from the WMO code; applyLighting reads gloom/flash/fog
  // to bend the sky, sun, hemisphere and scene fog. prefers-reduced-motion keeps
  // the sky and fog response but drops the particles and the lightning strobe.
  const WXFX = {
    rain: 0, snow: 0, gloom: 0, fog: 0, hail: 0, snowGround: 0, wet: 0,
    tRain: 0, tSnow: 0, tGloom: 0, tFog: 0, tHail: 0, tSnowGround: 0, tWet: 0,
    storm: false, seeded: false, flash: 0, nextBolt: 0, boltEnd: 0, boltFlash: 0, boltSoft: false, dayF: 1, boltGap: [2600, 9000],
  };
  function wxSetTargets() {
    const F = WXFX, c = WX.code;
    F.tFog = (c === 45 || c === 48) ? 1 : 0;
    const snowCode = (c >= 71 && c <= 77) || c === 85 || c === 86;
    const iceCode = c === 56 || c === 57 || c === 66 || c === 67;
    const rainCode = (c >= 51 && c <= 65 && !iceCode) || (c >= 80 && c <= 82);
    // WMO intensity steps, lifted further by the measured rate when it is larger
    let rainI = c === 55 || c === 65 || c === 82 ? 1 : c === 53 || c === 63 || c === 81 ? 0.6 : c === 51 || c === 61 || c === 80 ? 0.3 : 0;
    // Open-Meteo's current code is a model estimate and rarely says 95 while it
    // is actually thundering, so the NWS decides too: thunder observed at PHL or
    // PNE within the hour, a Severe Thunderstorm (or Tornado) Warning, or a
    // Severe Thunderstorm Watch while it is raining. NWS facts expire after 20 min.
    const nwsFresh = WX.nwsT > 0 && performance.now() - WX.nwsT < 20 * 60 * 1000;
    const raining = rainCode || WX.precip > 0.3 || rainI >= 0.6;
    const nwsStorm = nwsFresh && (WX.tsObs || WX.tsWarn || (WX.tsWatch && raining));
    // real strikes: three or more within 40 km in the last ten minutes is a storm here
    const ltnStorm = LTN.live && LTN.n10 >= 3 && LTN.nearestKm != null && LTN.nearestKm <= 40;
    F.storm = (c >= 95 && c <= 99) || nwsStorm || ltnStorm;
    // bolts come thick under a warning or observed thunder, sparser under a watch
    F.boltGap = (c >= 95 && c <= 99) || (nwsFresh && (WX.tsObs || WX.tsWarn)) ? [2600, 9000] : [7000, 18000];
    if ((c >= 95 && c <= 99) || nwsStorm) rainI = Math.max(rainI, c >= 96 ? 1 : 0.6);   // lightning alone does not make it rain here
    F.tRain = (rainCode || F.storm || (!snowCode && !iceCode && WX.precip > 0.1))
      ? clamp(Math.max(rainI, WX.precip / 6), 0.18, 1) : 0;
    const snowI = c === 75 || c === 86 ? 1 : c === 73 ? 0.65 : c === 71 || c === 77 || c === 85 ? 0.35 : 0;
    F.tSnow = (snowCode || WX.snowfall > 0.02) ? clamp(Math.max(snowI, WX.snowfall / 2.5), 0.2, 1) : 0;
    if (iceCode) { F.tRain = Math.max(F.tRain, 0.45); F.tSnow = Math.max(F.tSnow, 0.25); }   // sleet: both at once
    F.tHail = c === 96 || c === 99 ? 1 : 0;
    F.tGloom = F.storm ? clamp(0.55 + 0.45 * F.tRain, 0, 1) : 0.5 * F.tRain;
    F.tSnowGround = F.tSnow > 0.02 ? clamp(0.35 + 0.5 * F.tSnow, 0, 0.85) : 0;
    if (WX.temp != null && WX.temp > 38) F.tSnowGround *= 0.25;   // too warm to stick: slush at best
    F.tWet = (F.tRain > 0.02 || iceCode) ? clamp(0.35 + 0.65 * F.tRain, 0, 1) : 0;
    if (!F.seeded) {   // first report of the session: land in the ongoing weather, don't fade into it
      F.seeded = true;
      F.rain = F.tRain; F.snow = F.tSnow; F.gloom = F.tGloom; F.fog = F.tFog; F.hail = F.tHail;
      F.snowGround = F.tSnowGround; F.wet = F.tWet;
    }
  }
  // ---- weather on surfaces: snow lies on whatever faces up (roofs, roads,
  // parks, bridge decks, tree crowns), rain varnishes the same faces — one
  // shared fragment patch across the static standard materials, weighted by
  // the view-space normal's world-up component so walls stay dry brick. The
  // world-position hash breaks the blanket into patches; wet gloss favors
  // dark surfaces so asphalt shines harder than pale roofs. Applied after
  // build: chained onto cityMat's facade shader (its replace keeps the
  // literal includes), plain-assigned everywhere hookless; water (liquify),
  // vehicles, glass, street text and poles keep their own programs, which
  // also keeps moving things from wearing the weather.
  const wxSurfU = { uSnowAcc: { value: 0 }, uWet: { value: 0 } };
  // ground cover for the bare-earth planes: the single pale tone blanketing
  // every block interior and riverside flat read as permanent snow from the
  // air. A two-octave world-space mottle now breaks them into grass and dry
  // earth. The tones are MULTIPLIERS (darker than 1), so applyLighting's
  // day/night retint still owns the base color and the snow/wet pass layers
  // cleanly on top; the fine grain fades by pixel footprint so far ground
  // stays calm instead of sparkling (the water lesson).
  // the flat surfaces' texture: three scales of value noise in world space, blotches, tufts
  // and blades on anything green (parks, lawns), a quieter mottle and a fine speckle on the
  // greys (roads, decks, plazas); the finer scales fade with their pixel footprint
  // ---- painted textures. The ground, the grass field and the tree canopies carry albedos
  // painted into canvases at load (nothing downloaded, nothing to license): a tileable meadow
  // for every green flat, a tuft sprite for the grass, a leaf cluster for the tree cards. They
  // are sampled as sRGB, so they are painted in real dark albedo tones, not the stored-dark
  // hex convention the flat colours use; the flat's own colour survives as a tint.
  // the meadow's overall brightness, one number: the game's grass is a deep olive and the painted
  // tile plus the lift read a fifth too light beside it; the stored colours cannot do this (the
  // tint ratio is clamped and ACES compresses it, a 20 percent darker stored green moved the
  // display 7 percent), so the gain sits on the painted meadow itself
  const MEADOW_GAIN = 0.72;
  const texU = { uGrass: { value: null }, uGrassK: { value: 1 } };
  let tuftTex = null, leafTex = null;
  function prng(seed) { let s = (seed >>> 0) || 1; return () => { s += 0x6D2B79F5; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  // a tileable value-noise field over a W x W tile: octaves of [cells across the tile, weight]
  function noiseField(W, oct, seed) {
    const out = new Float32Array(W * W);
    const rnd = prng(seed);
    let wsum = 0;
    for (const [Pc, wgt] of oct) {
      const lat = new Float32Array(Pc * Pc);
      for (let i = 0; i < Pc * Pc; i++) lat[i] = rnd();
      const sc = Pc / W;
      for (let y = 0; y < W; y++) {
        const fy = y * sc, iy = Math.floor(fy), ty = fy - iy, sy = ty * ty * (3 - 2 * ty), y0 = (iy % Pc) * Pc, y1 = ((iy + 1) % Pc) * Pc;
        for (let x = 0; x < W; x++) {
          const fx = x * sc, ix = Math.floor(fx), tx = fx - ix, sx = tx * tx * (3 - 2 * tx), x0 = ix % Pc, x1 = (ix + 1) % Pc;
          const a = lat[y0 + x0] + (lat[y0 + x1] - lat[y0 + x0]) * sx, b = lat[y1 + x0] + (lat[y1 + x1] - lat[y1 + x0]) * sx;
          out[y * W + x] += (a + (b - a) * sy) * wgt;
        }
      }
      wsum += wgt;
    }
    for (let i = 0; i < W * W; i++) out[i] /= wsum;
    return out;
  }
  const sm01 = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
  const texOf = (c, srgb) => {
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    if (srgb) t.encoding = THREE.sRGBEncoding;
    t.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
    t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter;
    return t;
  };
  // the meadow tile: lush green drifting to dry olive on a slow noise, bare earth where it thins,
  // a clumpy light/dark mottle, fine grain, then tens of thousands of blade strokes (dark and
  // light), brighter tufts and a few flower specks, every stroke wrapped so the tile seams hide
  function paintGrassTex(W) {
    const c = document.createElement('canvas'); c.width = c.height = W;
    const ctx = c.getContext('2d');
    const img = ctx.createImageData(W, W), d = img.data;
    const n1 = noiseField(W, [[3, 0.5], [6, 0.3], [12, 0.15], [24, 0.05]], 1);
    const n2 = noiseField(W, [[16, 0.5], [32, 0.3], [64, 0.2]], 2);
    const n3 = noiseField(W, [[64, 0.6], [128, 0.4]], 3);
    for (let i = 0; i < W * W; i++) {
      const a = n1[i], b = n2[i], g3 = n3[i];
      const dry = sm01(0.55, 0.82, a), dirt = 1 - sm01(0.14, 0.30, a);
      const lum = 0.74 + 0.5 * b + 0.3 * (g3 - 0.5);
      let r = (54 + 34 * dry) * lum, g = (72 + 20 * dry) * lum, bl = (26 + 12 * dry) * lum;
      const el = 0.85 + 0.3 * g3;
      r += (98 * el - r) * dirt; g += (80 * el - g) * dirt; bl += (54 * el - bl) * dirt;
      d[i * 4] = r; d[i * 4 + 1] = g; d[i * 4 + 2] = bl; d[i * 4 + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
    const rnd = prng(7), k = W / 1024;
    ctx.lineCap = 'round';
    const stroke = (x, y, len, ang, col, w) => {
      ctx.strokeStyle = col; ctx.lineWidth = w;
      const dx = Math.cos(ang) * len, dy = Math.sin(ang) * len;
      const near = x < 12 || y < 12 || x > W - 12 || y > W - 12;
      for (const [ox, oy] of (near ? [[0, 0], [W, 0], [-W, 0], [0, W], [0, -W]] : [[0, 0]])) {
        ctx.beginPath(); ctx.moveTo(x + ox, y + oy); ctx.lineTo(x + ox + dx, y + oy + dy); ctx.stroke();
      }
    };
    const nStroke = Math.round(W * W / 32);
    for (let i = 0; i < nStroke; i++) {
      const x = rnd() * W, y = rnd() * W;
      const a = n1[Math.floor(x) + Math.floor(y) * W];
      const dry = sm01(0.55, 0.82, a);
      const dark = rnd() < 0.5;
      const lum = dark ? 0.74 + rnd() * 0.16 : 1.08 + rnd() * 0.22;
      const r = (54 + 34 * dry) * lum, g = (72 + 20 * dry) * lum, bl = (26 + 12 * dry) * lum;
      stroke(x, y, (2 + rnd() * 6) * k, -Math.PI / 2 + (rnd() - 0.5) * 1.7, 'rgba(' + (r | 0) + ',' + (g | 0) + ',' + (bl | 0) + ',0.55)', k * (0.8 + rnd() * 0.8));
    }
    for (let i = 0; i < W * W / 900; i++) {
      const x = rnd() * W, y = rnd() * W, n = 5 + Math.floor(rnd() * 4);
      for (let j = 0; j < n; j++) {
        const ang = -Math.PI / 2 + (j / (n - 1) - 0.5) * 1.5 + (rnd() - 0.5) * 0.3;
        stroke(x, y, (5 + rnd() * 7) * k, ang, 'rgba(' + (96 + rnd() * 22 | 0) + ',' + (112 + rnd() * 20 | 0) + ',44,0.6)', k);
      }
    }
    for (let i = 0; i < W * W / 16000; i++) {
      ctx.fillStyle = rnd() < 0.55 ? 'rgba(210,200,120,0.7)' : 'rgba(220,218,200,0.6)';
      ctx.fillRect(rnd() * W, rnd() * W, 1.6 * k, 1.6 * k);
    }
    // the tile's mean linear luminance: the shader normalises the macro copy by it
    const px = ctx.getImageData(0, 0, W, W).data;
    const lin = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    let lum = 0;
    for (let i = 0; i < W * W; i += 7) lum += 0.30 * lin(px[i * 4]) + 0.59 * lin(px[i * 4 + 1]) + 0.11 * lin(px[i * 4 + 2]);
    texU.uGrassK.value = 1 / Math.max(1e-4, lum / Math.ceil(W * W / 7));
    return texOf(c, true);
  }
  // a grass tuft: a fan of tapered blades from one root, dark at the foot, lit at the tips
  function paintTuftTex(W) {
    const c = document.createElement('canvas'); c.width = c.height = W;
    const ctx = c.getContext('2d');
    const rnd = prng(3);
    const bx = W / 2, by = W * 0.985, n = 14;
    for (let i = 0; i < n; i++) {
      const ang = -Math.PI / 2 + ((i + 0.5) / n - 0.5) * 1.6 + (rnd() - 0.5) * 0.3;
      const h = W * (0.42 + rnd() * 0.5), w0 = W * (0.007 + rnd() * 0.010);
      const tipX = bx + Math.cos(ang) * h, tipY = by + Math.sin(ang) * h;
      const bend = (rnd() - 0.5) * W * 0.25;
      const cx1 = bx + Math.cos(ang) * h * 0.5 + bend, cy1 = by + Math.sin(ang) * h * 0.5;
      const grad = ctx.createLinearGradient(bx, by, tipX, tipY);
      const dry = rnd() < 0.3;
      grad.addColorStop(0, dry ? 'rgb(88,90,42)' : 'rgb(72,88,38)');
      grad.addColorStop(0.55, dry ? 'rgb(150,146,76)' : 'rgb(116,128,58)');
      grad.addColorStop(1, dry ? 'rgb(182,174,108)' : 'rgb(156,162,88)');
      ctx.fillStyle = grad;
      const px = -Math.sin(ang), py = Math.cos(ang);
      ctx.beginPath();
      ctx.moveTo(bx - px * w0, by - py * w0);
      ctx.quadraticCurveTo(cx1 - px * w0 * 0.55, cy1 - py * w0 * 0.55, tipX, tipY);
      ctx.quadraticCurveTo(cx1 + px * w0 * 0.55, cy1 + py * w0 * 0.55, bx + px * w0, by + py * w0);
      ctx.closePath(); ctx.fill();
    }
    // the sprite goes up from its own pixels: a canvas premultiplies its clear texels to black
    // and the mips bled that into every blade edge (the tufts read as dark specks from height)
    const id = ctx.getImageData(0, 0, W, W), q = id.data;
    for (let i = 0; i < W * W; i++) if (q[i * 4 + 3] < 24) { q[i * 4] = 116; q[i * 4 + 1] = 128; q[i * 4 + 2] = 58; }
    const t = new THREE.DataTexture(q, W, W, THREE.RGBAFormat);
    t.flipY = true; t.encoding = THREE.sRGBEncoding; t.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
    t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter;
    t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping; t.needsUpdate = true;
    return t;
  }
  // a leaf cluster for the tree cards: a few hundred pointed leaves piled into a ragged disc,
  // lit from the upper left, dark leaves underneath, so every card reads as a bough
  function paintLeafTex(W) {
    const c = document.createElement('canvas'); c.width = c.height = W;
    const ctx = c.getContext('2d');
    const rnd = prng(5);
    const cx = W / 2, cy = W / 2, R = W * 0.46;
    const leaf = (x, y, len, wid, ang, col) => {
      ctx.save(); ctx.translate(x, y); ctx.rotate(ang); ctx.fillStyle = col;
      ctx.beginPath(); ctx.moveTo(0, -len / 2);
      ctx.quadraticCurveTo(wid / 2, 0, 0, len / 2); ctx.quadraticCurveTo(-wid / 2, 0, 0, -len / 2);
      ctx.closePath(); ctx.fill(); ctx.restore();
    };
    // a dark backing disc with a ragged edge fills the bough; the leaves lie on it
    ctx.fillStyle = 'rgb(16,34,12)';
    ctx.beginPath();
    for (let i = 0; i <= 48; i++) {
      const a = i / 48 * Math.PI * 2, rr = R * (0.55 + 0.10 * Math.sin(a * 5 + 1.3) + 0.05 * Math.sin(a * 11 + 0.4));
      if (i) ctx.lineTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr); else ctx.moveTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr);
    }
    ctx.closePath(); ctx.fill();
    for (let pass = 0; pass < 2; pass++) {
      const N = pass ? 1100 : 600;
      for (let i = 0; i < N; i++) {
        const rr = R * Math.pow(rnd(), 0.6) * (pass ? 1.0 : 0.9) * (0.9 + 0.12 * rnd()), a = rnd() * Math.PI * 2;
        const x = cx + Math.cos(a) * rr, y = cy + Math.sin(a) * rr;
        // a bright heart and a dark rim (the card faces any way, so the light cannot have a side)
        const lit = 1.0 - 0.55 * rr / R;
        const lum = (pass ? 0.7 + 0.75 * lit : 0.4 + 0.3 * lit) * (0.8 + rnd() * 0.4);
        const hue = rnd();
        const r = (26 + 14 * hue) * lum, g = (70 + 6 * hue) * lum, b = (24 + 4 * hue) * lum;
        leaf(x, y, W * (0.035 + rnd() * 0.03), W * (0.016 + rnd() * 0.014), rnd() * Math.PI, 'rgb(' + (r | 0) + ',' + (g | 0) + ',' + (b | 0) + ')');
      }
    }
    // the sprite's mean colour, normalised on green: the crown cores are tinted by it
    const q = ctx.getImageData(0, 0, W, W).data;
    const lin = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    let mr = 0, mg = 0, mb = 0, mn = 0;
    for (let i = 0; i < W * W; i += 3) if (q[i * 4 + 3] > 0) { mr += lin(q[i * 4]); mg += lin(q[i * 4 + 1]); mb += lin(q[i * 4 + 2]); mn++; }
    texU.leafNorm = new THREE.Color(mr / Math.max(1e-6, mg), 1, mb / Math.max(1e-6, mg));
    const t = texOf(c, true); t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping;
    return t;
  }

  // the flats' shader: every green (parks, lawns, bare ground) becomes the painted meadow with
  // one mottle, everything else gets a neutral mottle. `opt === true` forces the meadow branch
  // (the bare ground, whose vertex tints must never fall out of the green test); r149 passes the
  // WebGLRenderer as the second argument, so opt is tested for identity, never truthiness
  function surfTexPatch(shader, opt) {
    const forced = opt === true;
    shader.uniforms.uGrass = texU.uGrass; shader.uniforms.uGrassK = texU.uGrassK;
    shader.fragmentShader = shader.fragmentShader
      .replace('void main() {', [
        'uniform sampler2D uGrass; uniform float uGrassK;',
        'float sth(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }',
        'float stn(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);',
        '  return mix(mix(sth(i), sth(i + vec2(1.0, 0.0)), f.x), mix(sth(i + vec2(0.0, 1.0)), sth(i + vec2(1.0, 1.0)), f.x), f.y); }',
        'void main() {',
      ].join('\n'))
      .replace('#include <color_fragment>', '#include <color_fragment>\n' + [
        'vec3 sWP = cameraPosition - vViewPosition * mat3(viewMatrix);',
        'float sfw = max(fwidth(sWP.x), fwidth(sWP.z));',
        'float sn1 = stn(sWP.xz * 0.05);',
        // every footprint-gated noise fades to its MEAN (0.5), not to zero: fading to zero made the
        // mean brightness fall with the pixel footprint, a dark front that moved with the camera
        'float sn2 = mix(0.5, stn(sWP.xz * 0.5), 1.0 - smoothstep(1.0, 4.0, sfw));',
        'float sn3 = mix(0.5, stn(sWP.xz * 4.0), 1.0 - smoothstep(0.08, 0.4, sfw));',
        'float isGreen = ' + (forced ? '1.0;' : 'step(diffuseColor.r * 1.15, diffuseColor.g);'),
        'vec3 am = vec3((0.96 + 0.08 * sn1) * (0.97 + 0.06 * sn2) * (1.0 + 0.08 * (sn3 - 0.5)));',
        // the meadow: the painted tile at 6.5 m, a rotated 47 m copy as the macro tone, the
        // world-space mottle as the block-to-block drift; the flat's own colour is a tint
        'vec3 gTex = mix(texture2D(uGrass, sWP.xz * 0.1538).rgb, texture2D(uGrass, vec2(sWP.x * 0.9397 + sWP.z * 0.342, -sWP.x * 0.342 + sWP.z * 0.9397) * 0.0885 + 0.37).rgb, 0.5);',
        'vec3 gMac = texture2D(uGrass, vec2(sWP.x * 0.866 - sWP.z * 0.5, sWP.x * 0.5 + sWP.z * 0.866) * 0.02128).rgb;',
        'float gMacL = dot(gMac, vec3(0.30, 0.59, 0.11)) * uGrassK;',
        // the game's blotches: darker patches at 83 m and 22 m over the meadow, a fine grain at
        // 3 m near the eye, never lighter than the base (tune the two vec3s and the 0.16 here)
        'float gtn1 = stn(sWP.xz * 0.012);',
        'float gtn2 = mix(0.5, stn(sWP.xz * 0.045), 1.0 - smoothstep(8.0, 30.0, sfw));',
        'float gtn3 = mix(0.5, stn(sWP.xz * 0.35), 1.0 - smoothstep(1.0, 4.0, sfw));',
        'float gt = smoothstep(0.30, 0.70, gtn1 * 0.7 + gtn2 * 0.3);',
        'vec3 gMul = mix(vec3(0.60, 0.66, 0.50), vec3(1.0), gt) * (0.92 + 0.16 * gtn3);',
        'vec3 grass = gTex * mix(1.0, gMacL, 0.55) * (0.88 + 0.24 * sn1) * gMul * ' + MEADOW_GAIN.toFixed(2) + ';',
        'vec3 gTint = clamp(diffuseColor.rgb / vec3(0.141, 0.22, 0.094), 0.3, 1.6);',
        'diffuseColor.rgb = mix(diffuseColor.rgb * am, grass * gTint, isGreen);',
      ].join('\n'));
    cloudShadowPatch(shader, 'cameraPosition - vViewPosition * mat3(viewMatrix)');
  }
  // hooks are assigned at creation, once; `userData.wxSurf` marks the material for the post-build
  // weather wrap (the hookup at the end of build() keys the wrapped program, gotcha 15)
  const surfMat = (o) => { const m = new THREE.MeshStandardMaterial(o); m.userData.wxSurf = true; m.onBeforeCompile = surfTexPatch; return m; };
  // the bare ground: the same meadow as the parks, forced green (its vertex tints ride as ratios),
  // one material per tier with no clone (r149's copy() drops onBeforeCompile and the cache key)
  const groundSurfMat = (o) => {
    const m = new THREE.MeshStandardMaterial({ color: COLORS.ground, roughness: 0.96, metalness: 0, dithering: MAT_DITHER, ...o });
    m.userData.wxSurf = true;
    m.onBeforeCompile = (sh, r) => surfTexPatch(sh, true);
    m.customProgramCacheKey = () => 'ground';
    groundMats.push(m);
    return m;
  };

  // cloud shadows: a world-space fbm with the sky's cover threshold, drifting with the same
  // wind offset as the sky's clouds; the surfaces and the trees darken under it by day
  const cloudShU = { uCloudOff: skyMat.uniforms.uCloudOff, uCloudCov: skyMat.uniforms.uCloud, uCloudSh: { value: 0 }, uCloudSlant: { value: new THREE.Vector2() } };
  function cloudShadowPatch(shader, worldExpr) {
    if (shader.fragmentShader.indexOf('float cloudShade(') !== -1) return;   // chained patches each ask for it; once is enough
    shader.uniforms.uCloudOff = cloudShU.uCloudOff; shader.uniforms.uCloudCov = cloudShU.uCloudCov; shader.uniforms.uCloudSh = cloudShU.uCloudSh; shader.uniforms.uCloudSlant = cloudShU.uCloudSlant;
    shader.fragmentShader = shader.fragmentShader
      .replace('void main() {', [
        'uniform vec2 uCloudOff, uCloudSlant; uniform float uCloudCov, uCloudSh;',
        'float cshh(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }',
        'float cshn(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f); return mix(mix(cshh(i), cshh(i + vec2(1.0, 0.0)), f.x), mix(cshh(i + vec2(0.0, 1.0)), cshh(i + vec2(1.0, 1.0)), f.x), f.y); }',
        'float cloudShade(vec2 wp){ vec2 cp = (wp + uCloudSlant) * 0.0008 + uCloudOff * 0.8; float f = 0.5 * cshn(cp) + 0.25 * cshn(cp * 2.1 + 13.1) + 0.125 * cshn(cp * 4.3 + 41.7) + 0.0625 * cshn(cp * 8.9 + 7.7); float thr = 0.60 - clamp(uCloudCov, 0.0, 1.0) * 0.40; return smoothstep(thr, thr + 0.14, f) * uCloudSh; }',
        'void main() {',
      ].join('\n'))
      .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ndiffuseColor.rgb *= 1.0 - 0.45 * cloudShade((' + worldExpr + ').xz);');
  }
  function wxSurfacePatch(shader) {
    shader.uniforms.uSnowAcc = wxSurfU.uSnowAcc;
    shader.uniforms.uWet = wxSurfU.uWet;
    shader.fragmentShader = shader.fragmentShader
      .replace('void main() {', 'uniform float uSnowAcc; uniform float uWet;\nvoid main() {')
      .replace('#include <color_fragment>', '#include <color_fragment>\n' + [
        'float wxUpW = smoothstep(0.55, 0.85, clamp(dot(normalize(vNormal), (viewMatrix * vec4(0.0, 1.0, 0.0, 0.0)).xyz), 0.0, 1.0));',
        'vec3 wxWP = cameraPosition - vViewPosition * mat3(viewMatrix);',
        'float wxN = fract(sin(dot(floor(wxWP.xz * 0.9), vec2(127.1, 311.7))) * 43758.5453);',
        'float wxSnowW = uSnowAcc * max(wxUpW, 0.14) * (0.78 + 0.22 * wxN);',
        'float wxDark = 1.0 - clamp(dot(diffuseColor.rgb, vec3(0.55)), 0.0, 1.0);',
        'float wxWetW = uWet * wxUpW * (1.0 - wxSnowW);',
        'diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.88, 0.90, 0.93), wxSnowW);',
        'diffuseColor.rgb *= 1.0 - 0.45 * wxWetW;',
      ].join('\n'))
      .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\n' + [
        'roughnessFactor = mix(roughnessFactor, 0.18, wxWetW * (0.45 + 0.55 * wxDark));',
        'roughnessFactor = mix(roughnessFactor, 0.92, wxSnowW);',
      ].join('\n'))
      .replace('#include <metalnessmap_fragment>', '#include <metalnessmap_fragment>\n' + [
        // the wet-street cheat: a touch of metalness makes the whole sky sheet
        // across the asphalt at any view angle, where dielectric fresnel only
        // gleams at grazing ones (ACES shoulder swallows plain darkening)
        'metalnessFactor = mix(metalnessFactor, 0.32, wxWetW * (0.4 + 0.6 * wxDark));',
      ].join('\n'));
    cloudShadowPatch(shader, 'cameraPosition - vViewPosition * mat3(viewMatrix)');
  }
  // decorrelated per-particle gate so density scales without bunching to one side of the box
  const wxGateGLSL = 'float wxGate(vec3 s){ return fract(sin(dot(s, vec3(12.9898, 78.233, 45.164))) * 43758.5453); }\n';
  const RAIN_N = 16000;   // short drops need numbers: the eye reads density, not length
  const rainU = {
    uBox: { value: new THREE.Vector3(90, 80, 90) },
    uOff: { value: new THREE.Vector3() },
    uCam: { value: new THREE.Vector3() },
    uVelN: { value: new THREE.Vector3(0, -1, 0) },
    uFrac: { value: 0 }, uLen: { value: 1.7 }, uAlpha: { value: 0.3 },
    uCol: { value: new THREE.Color(0.62, 0.66, 0.74) },
    uPost: postU.uPost, uExposure: postU.uExposure,   // the streaks write display colour: under the post pipeline, its pre-image
  };
  let rainMesh, snowMesh;
  {
    const seed = new Float32Array(RAIN_N * 6), tip = new Float32Array(RAIN_N * 2);
    for (let i = 0; i < RAIN_N; i++) {
      const a = Math.random(), b = Math.random(), c = Math.random(), o = i * 6;
      seed[o] = seed[o + 3] = a; seed[o + 1] = seed[o + 4] = b; seed[o + 2] = seed[o + 5] = c;
      tip[i * 2 + 1] = 1;   // second vertex of each pair extends along the fall direction
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(seed, 3));   // position carries the box seed
    g.setAttribute('aTip', new THREE.BufferAttribute(tip, 1));
    const m = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, fog: false, uniforms: rainU,
      vertexShader:
        'uniform vec3 uBox, uOff, uCam, uVelN; uniform float uFrac, uLen, uAlpha;\n' +
        'attribute float aTip; varying float vA;\n' +
        '#include <common>\n' +
        '#include <logdepthbuf_pars_vertex>\n' +
        wxGateGLSL +
        'void main(){\n' +
        '  if (wxGate(position) > uFrac) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); vA = 0.0; return; }\n' +
        '  vec3 p = position * 2.0 * uBox + uOff - uCam;\n' +
        '  p = mod(p, 2.0 * uBox) - uBox;\n' +
        '  float r = clamp(length(p.xz) / uBox.x, 0.0, 1.0);\n' +
        '  p += uCam + uVelN * (aTip * uLen);\n' +
        '  vec4 mv = modelViewMatrix * vec4(p, 1.0);\n' +
        '  gl_Position = projectionMatrix * mv;\n' +
        '  vA = uAlpha * (1.0 - 0.7 * r * r) * (1.0 - 0.55 * aTip);\n' +
        '  #include <logdepthbuf_vertex>\n' +
        '}',
      fragmentShader:
        'uniform vec3 uCol; varying float vA; uniform float uPost, uExposure;\n' +
        '#include <common>\n' +
        '#include <logdepthbuf_pars_fragment>\n' +
        INV_GLSL + '\n' +
        'void main(){\n' +
        '  #include <logdepthbuf_fragment>\n' +
        '  if (vA < 0.004) discard;\n' +
        '  gl_FragColor = vec4(uPost > 0.5 ? pUndo(uCol, uExposure) : uCol, vA);\n' +
        '}',
    });
    rainMesh = new THREE.LineSegments(g, m);
    rainMesh.frustumCulled = false; rainMesh.renderOrder = 50; rainMesh.visible = false;
    scene.add(rainMesh);
  }
  const SNOW_N = 11000;
  const snowU = {
    uBox: { value: new THREE.Vector3(80, 70, 80) },
    uOff: { value: new THREE.Vector3() },
    uCam: { value: new THREE.Vector3() },
    uFrac: { value: 0 }, uSize: { value: 0.6 }, uAlpha: { value: 0.8 }, uTime: { value: 0 },
    uCol: { value: new THREE.Color(0.93, 0.95, 0.99) },
    uPost: postU.uPost, uExposure: postU.uExposure,
  };
  {
    const seed = new Float32Array(SNOW_N * 3), ph = new Float32Array(SNOW_N);
    for (let i = 0; i < SNOW_N; i++) { seed[i * 3] = Math.random(); seed[i * 3 + 1] = Math.random(); seed[i * 3 + 2] = Math.random(); ph[i] = Math.random(); }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(seed, 3));
    g.setAttribute('aPh', new THREE.BufferAttribute(ph, 1));
    const m = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, fog: false, uniforms: snowU,
      vertexShader:
        'uniform vec3 uBox, uOff, uCam; uniform float uFrac, uSize, uAlpha, uTime;\n' +
        'attribute float aPh; varying float vA;\n' +
        '#include <common>\n' +
        '#include <logdepthbuf_pars_vertex>\n' +
        wxGateGLSL +
        'void main(){\n' +
        '  if (wxGate(position) > uFrac) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 1.0; vA = 0.0; return; }\n' +
        '  vec3 adv = uOff; adv.y *= 0.65 + 0.7 * aPh;\n' +
        '  vec3 p = position * 2.0 * uBox + adv - uCam;\n' +
        '  p = mod(p, 2.0 * uBox) - uBox;\n' +
        '  float r = clamp(length(p.xz) / uBox.x, 0.0, 1.0);\n' +
        '  p += uCam;\n' +
        '  float sw = 1.2 + aPh * 2.2;\n' +
        '  p.x += sin(uTime * (0.6 + position.z * 0.7) + aPh * 6.2832) * sw;\n' +
        '  p.z += cos(uTime * (0.45 + position.x * 0.6) + aPh * 4.7) * sw;\n' +
        '  vec4 mv = modelViewMatrix * vec4(p, 1.0);\n' +
        '  gl_Position = projectionMatrix * mv;\n' +
        '  gl_PointSize = clamp(uSize * (0.55 + 0.45 * aPh) * 340.0 / max(1.0, -mv.z), 1.0, 13.0);\n' +
        '  vA = uAlpha * (1.0 - 0.65 * r * r);\n' +
        '  #include <logdepthbuf_vertex>\n' +
        '}',
      fragmentShader:
        'uniform vec3 uCol; varying float vA; uniform float uPost, uExposure;\n' +
        '#include <common>\n' +
        '#include <logdepthbuf_pars_fragment>\n' +
        INV_GLSL + '\n' +
        'void main(){\n' +
        '  #include <logdepthbuf_fragment>\n' +
        '  float d = length(gl_PointCoord - vec2(0.5));\n' +
        '  float a = vA * smoothstep(0.5, 0.16, d);\n' +
        '  if (a < 0.004) discard;\n' +
        '  gl_FragColor = vec4(uPost > 0.5 ? pUndo(uCol, uExposure) : uCol, a);\n' +
        '}',
    });
    snowMesh = new THREE.Points(g, m);
    snowMesh.frustumCulled = false; snowMesh.renderOrder = 50; snowMesh.visible = false;
    scene.add(snowMesh);
  }
  // lightning: a jagged polyline rebuilt per strike out beyond the skyline,
  // shown ~240 ms with a triple-flicker flash that applyLighting spreads over
  // the sky, cloud deck and hemisphere light
  const BOLT_MAX = 44;
  const boltPos = new Float32Array(BOLT_MAX * 6);
  const boltGeo = new THREE.BufferGeometry();
  boltGeo.setAttribute('position', new THREE.BufferAttribute(boltPos, 3));
  boltGeo.setDrawRange(0, 0);
  const boltMat = new THREE.LineBasicMaterial({ color: 0xeaeeff, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, fog: false });
  const boltMesh = new THREE.LineSegments(boltGeo, boltMat);
  boltMesh.frustumCulled = false; boltMesh.renderOrder = 60; boltMesh.visible = false;
  scene.add(boltMesh);
  function spawnBolt(now) {   // a synthetic strike, for storm mode without a lightning feed (and __dbg.bolt)
    const az = Math.random() * Math.PI * 2, dist = 1300 + Math.random() * 2800;
    spawnBoltAt(now, camera.position.x + Math.sin(az) * dist, camera.position.z + Math.cos(az) * dist);
    WXFX.nextBolt = now + WXFX.boltGap[0] + Math.random() * WXFX.boltGap[1];
  }
  // a real strike: lat/lon through the SEPTA frame; anything past the apron's
  // edge is pulled in along its bearing from the world's centre so the bolt
  // still stands on ground at the horizon instead of in the void
  const LTN_CENTER = { x: 2250, z: -6000 }, LTN_CLAMP = 55000;
  function spawnStrike(now, st) {
    let x = (st[2] - SEPTA_GEO.lon0) * SEPTA_GEO.mx, z = -(st[1] - SEPTA_GEO.lat0) * SEPTA_GEO.mz;
    const dx = x - LTN_CENTER.x, dz = z - LTN_CENTER.z, d = Math.hypot(dx, dz);
    if (d > LTN_CLAMP) { x = LTN_CENTER.x + dx / d * LTN_CLAMP; z = LTN_CENTER.z + dz / d * LTN_CLAMP; }
    spawnBoltAt(now, x, z);
    LTN.drawn++;
  }
  function spawnBoltAt(now, px, pz) {
    const dist = Math.hypot(px - camera.position.x, pz - camera.position.z);
    let py = 950 + Math.random() * 520;
    const drop = py / 11;
    let n = 0;
    const put = (x1, y1, z1, x2, y2, z2) => { if (n >= BOLT_MAX) return; const o = n * 6; boltPos[o] = x1; boltPos[o + 1] = y1; boltPos[o + 2] = z1; boltPos[o + 3] = x2; boltPos[o + 4] = y2; boltPos[o + 5] = z2; n++; };
    const branchAt = 3 + (Math.random() * 5 | 0), branch = Math.random() < 0.5;
    for (let i = 0; i < 12 && py > -20; i++) {
      const nx = px + (Math.random() - 0.5) * 130, nz = pz + (Math.random() - 0.5) * 130;
      const ny = py - drop * (0.7 + Math.random() * 0.6);
      put(px, py, pz, nx, ny, nz);
      if (branch && i === branchAt) {
        let qx = px, qy = py, qz = pz;
        const bdx = (Math.random() - 0.5) * 160, bdz = (Math.random() - 0.5) * 160;
        for (let j = 0; j < 4; j++) {
          const rx = qx + bdx * 0.5 + (Math.random() - 0.5) * 90, rz = qz + bdz * 0.5 + (Math.random() - 0.5) * 90;
          const ry = qy - drop * (0.5 + Math.random() * 0.5);
          put(qx, qy, qz, rx, ry, rz);
          qx = rx; qy = ry; qz = rz;
        }
      }
      px = nx; py = ny; pz = nz;
    }
    put(px, py, pz, px + (Math.random() - 0.5) * 60, -25, pz + (Math.random() - 0.5) * 60);
    boltGeo.attributes.position.needsUpdate = true;
    boltGeo.setDrawRange(0, n * 2);
    WXFX.boltEnd = now + 240;
    WXFX.boltFlash = clamp(1100 / dist, 0.05, 1);   // a strike overhead lights the world; one 40 km out barely flickers the deck
    WXFX.boltSoft = dist > 9000;                     // far off: one soft pulse instead of the triple strobe
  }
  const _wxc = new THREE.Color();
  const rainVel = new THREE.Vector3(), rainOff = new THREE.Vector3();
  const snowVel = new THREE.Vector3(), snowOff = new THREE.Vector3();
  function updateWeatherFX(now, dt) {
    const F = WXFX;
    const e = 1 - Math.exp(-dt / 1.8);
    F.rain += (F.tRain - F.rain) * e;
    F.snow += (F.tSnow - F.snow) * e;
    F.gloom += (F.tGloom - F.gloom) * e;
    F.fog += (F.tFog - F.fog) * e;
    F.hail += (F.tHail - F.hail) * e;
    F.wet += (F.tWet - F.wet) * (1 - Math.exp(-dt / (F.tWet > F.wet ? 25 : 300)));   // streets darken fast, dry slowly
    // accumulation settles in about a minute of snowfall; melts off slowly, faster above freezing
    const sgTau = F.tSnowGround > F.snowGround ? 40 : (WX.temp != null && WX.temp > 38 ? 180 : 600);
    F.snowGround += (F.tSnowGround - F.snowGround) * (1 - Math.exp(-dt / sgTau));
    wxSurfU.uSnowAcc.value = F.snowGround;
    wxSurfU.uWet.value = F.wet * (0.45 + 0.55 * F.dayF);
    if (reducedMotion) return;   // sky, fog and surfaces still answer the weather; no particles, no strobe
    const cy = camera.position.y;
    const hi = smooth(120, 1100, cy);         // altitude grows the box and streaks so it still reads
    const vis = 1 - smooth(350, 1000, cy);    // rain is not a thing you see from a kilometre up: it fades out, the fog and gloom carry it
    rainMesh.visible = F.rain > 0.02 && vis > 0.02;
    if (rainMesh.visible) {
      // real fall speed at street level; faster with altitude so a streak seen from above
      // still reads as falling rain instead of a slow drift
      rainVel.set(WX.windX * 0.75, -(8.5 + 4 * F.rain + 9 * F.hail) * (1 + 2.2 * hi), WX.windZ * 0.75);
      rainOff.addScaledVector(rainVel, dt);
      rainU.uOff.value.copy(rainOff);
      // small box at street level so the near field is dense enough to read
      rainU.uBox.value.set(45 + 740 * hi, 40 + 415 * hi, 45 + 740 * hi);
      rainU.uCam.value.copy(camera.position);
      rainU.uCam.value.y += rainU.uBox.value.y * 0.25;   // bias the box upward: rain arrives from above
      // drops, not spaghetti: a 0.9 m dash at street level (a falling drop over one frame),
      // stretching to 2.3 m from altitude so it still reads as rain rather than dust
      rainU.uLen.value = (0.9 + 1.4 * hi) * (1 - 0.4 * F.hail);
      rainU.uVelN.value.copy(rainVel).normalize();
      rainU.uFrac.value = 0.12 + 0.88 * F.rain;
      rainU.uAlpha.value = (0.9 - 0.35 * hi) * vis * (0.30 + 0.70 * F.dayF) * Math.min(1, 0.5 + F.rain);
      rainU.uCol.value.setRGB(0.62, 0.66, 0.74).lerp(_wxc.setRGB(0.93, 0.95, 0.99), F.hail);
    }
    snowMesh.visible = F.snow > 0.02 && vis > 0.02;
    if (snowMesh.visible) {
      snowVel.set(WX.windX * 0.4, -(1.5 + 1.3 * F.snow), WX.windZ * 0.4);
      snowOff.addScaledVector(snowVel, dt);
      snowU.uTime.value += dt;
      snowU.uOff.value.copy(snowOff);
      snowU.uBox.value.set(40 + 675 * hi, 35 + 360 * hi, 40 + 675 * hi);
      snowU.uCam.value.copy(camera.position);
      snowU.uCam.value.y += snowU.uBox.value.y * 0.25;
      snowU.uSize.value = 0.8 + 5.2 * hi;
      snowU.uFrac.value = 0.15 + 0.85 * F.snow;
      snowU.uAlpha.value = 0.95 * vis * (0.45 + 0.55 * F.dayF);
    }
    ltnPoll(now);
    if (LTN.queue.length && now >= LTN.nextDraw) { spawnStrike(now, LTN.queue.shift()); LTN.nextDraw = now + 2500 + Math.random() * 2500; }   // real strikes, one every 2.5 to 5 s at most
    else if (F.storm && !LTN.live) {   // no lightning feed: the synthetic bolts stand in
      if (!F.nextBolt) F.nextBolt = now + 1200 + Math.random() * F.boltGap[1] * 0.5;
      if (now >= F.nextBolt) spawnBolt(now);
    } else F.nextBolt = 0;
    if (now < F.boltEnd) {
      const t = (now - (F.boltEnd - 240)) / 240;
      const fl = F.boltSoft ? 0.8 * Math.exp(-(t - 0.35) * (t - 0.35) * 26) : Math.max(
        Math.exp(-(t - 0.07) * (t - 0.07) * 80),
        0.75 * Math.exp(-(t - 0.45) * (t - 0.45) * 55),
        0.45 * Math.exp(-(t - 0.82) * (t - 0.82) * 45));
      F.flash = fl * F.boltFlash;
      boltMat.opacity = clamp(fl * (F.boltSoft ? 1.2 : 1.7) - 0.25, 0, F.boltSoft ? 0.6 : 1);
      boltMesh.visible = boltMat.opacity > 0.02;
    } else {
      boltMesh.visible = false;
      if (F.flash > 0) { F.flash *= Math.exp(-12 * dt); if (F.flash < 0.002) F.flash = 0; }
    }
  }
  const PAL = {
    night: { z: new THREE.Color(0x070c1a), h: new THREE.Color(0x121a2e), g: new THREE.Color(0x0a0a0e) },
    twi: { z: new THREE.Color(0x34456e), h: new THREE.Color(0xf3a468), g: new THREE.Color(0x3a322c) },
    day: { z: new THREE.Color(COLORS.skyZenith), h: new THREE.Color(COLORS.skyHorizon), g: new THREE.Color(COLORS.skyGround) },
  };
  const moonDir = new V3(0.35, 0.62, 0.45).normalize();   // live lunar position (applyLighting)
  const moonHigh = new V3(0.35, 0.62, 0.45).normalize();  // moonless-night fill direction
  const glintDir = new V3(0.3, 0.8, 0.2);                 // what the water sparkles toward
  const _vA = new THREE.Vector3();
  let moonNow = { el: -90, az: 0, k: 0.5, wax: true };
  let lastEnvEl = 999, envGap = 0, envNextT = 0;   // envGap: a floor between PMREM rebakes (the time-lapse sets it)
  const _c1 = new THREE.Color(), _c2 = new THREE.Color(), _c3 = new THREE.Color();
  const _pz = new THREE.Color(), _ph = new THREE.Color(), _pg = new THREE.Color();   // the frame's sky palette
  let _ephMs = NaN, _ephSun = null, _ephMoon = null;   // solar()/lunar() memo: the clock moves once a minute
  const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
  function applyLighting() {
    const ms = clockUtcMs(clock, clock.minutes);
    if (ms !== _ephMs) { _ephMs = ms; _ephSun = solar(ms); _ephMoon = lunar(ms); }
    const sp = _ephSun, mp = _ephMoon;
    moonNow = mp;
    moonDir.copy(mp.dir);
    const el = sp.elev;
    const dayF = smooth(-4, 10, el);
    const twi = Math.exp(-Math.pow((el + 1) / 7, 2)) * (1 - dayF * 0.6);
    const night = 1 - smooth(-9, 1, el);
    WXFX.dayF = dayF;   // the particle boxes dim toward night with the sky
    if (el > -3) {
      sunDir.copy(sp.dir);
      sun.intensity = 2.0 * smooth(-3, 15, el) * (1 - 0.72 * WX.cover - 0.16 * smooth(0.75, 1.0, WX.cover)) * (1 - 0.55 * WXFX.gloom);
      sun.color.copy(_c1.set(0xff9a55)).lerp(_c2.set(COLORS.sun), smooth(-2, 28, el));
      glintDir.copy(sp.dir);
    } else if (mp.el > 2) {
      // moonlight follows the real moon: direction, and strength by phase
      sunDir.copy(moonDir);
      sun.intensity = (0.05 + 0.13 * mp.k) * (1 - 0.6 * WX.cover);
      sun.color.set(0x8ea0c0);
      glintDir.copy(moonDir);
    } else {
      sunDir.copy(moonHigh);
      sun.intensity = 0.05;
      sun.color.set(0x8ea0c0);
      glintDir.set(0, -1, 0);              // no moon, no moonglade
    }
    aimSun(lastAim.cx, lastAim.cz, lastAim.extent);
    skyMat.uniforms.uSun.value.copy(sp.dir);
    skyMat.uniforms.uSunVis.value = smooth(-1.1, 0.4, el);   // below the horizon the disc is gone, only the glow lingers
    envSun.visible = el > -0.6;
    // the phased moon disc: bright-limb tangent from the world sun/moon vectors
    skyMat.uniforms.uMoon.value.copy(mp.dir);
    _vA.copy(sp.dir).addScaledVector(mp.dir, -sp.dir.dot(mp.dir));
    if (_vA.lengthSq() < 1e-6) _vA.set(0, 1, 0).addScaledVector(mp.dir, -mp.dir.y);
    _vA.normalize();
    skyMat.uniforms.uMoonU.value.copy(_vA);
    skyMat.uniforms.uMoonV.value.crossVectors(mp.dir, _vA);
    skyMat.uniforms.uMoonK.value = mp.k;
    skyMat.uniforms.uMoonI.value = smooth(-0.5, 5, mp.el) * (1 - smooth(-7, 1, el)) * (1 - 0.85 * WX.cover);
    const mixPal = (k, out) => out.copy(PAL.night[k]).lerp(PAL.twi[k], twi).lerp(PAL.day[k], dayF);
    const cz = mixPal('z', _pz), ch = mixPal('h', _ph), cg = mixPal('g', _pg);
    // overcast grays the sky toward a flat deck
    // a broken sky stays blue-gray; past 75% cover the dome goes to a neutral overcast gray
    // (Mike: a 92% day still read as blue)
    const heavy = smooth(0.75, 1.0, WX.cover);
    cz.lerp(_c2.set(0x93a5b4).lerp(_c3.set(0x8c9399), heavy).multiplyScalar(0.15 + 0.85 * dayF), WX.cover * (0.55 + 0.42 * heavy));
    ch.lerp(_c2.set(0xc4ccd2).lerp(_c3.set(0xb3b8bc), heavy).multiplyScalar(0.15 + 0.85 * dayF), WX.cover * (0.5 + 0.45 * heavy));
    if (WXFX.gloom > 0.003) {   // storm gloom: the whole deck sinks toward charcoal slate
      cz.lerp(_c2.set(0x353d49).multiplyScalar(0.10 + 0.90 * dayF), WXFX.gloom * 0.72);
      ch.lerp(_c2.set(0x525b66).multiplyScalar(0.10 + 0.90 * dayF), WXFX.gloom * 0.62);
    }
    const snowSky = Math.max(WXFX.snow * 0.55, WXFX.snowGround * 0.3);
    if (snowSky > 0.003) {      // snow days read milk, not blue — during the fall and while cover lies
      cz.lerp(_c2.set(0xb6bec8).multiplyScalar(0.15 + 0.85 * dayF), snowSky);
      ch.lerp(_c2.set(0xd6dade).multiplyScalar(0.15 + 0.85 * dayF), snowSky * 0.9);
    }
    if (WXFX.flash > 0.003) {   // lightning: sky and cloud deck flare blue-white
      cz.lerp(_c2.set(0xdfe6ff), WXFX.flash * 0.55);
      ch.lerp(_c2.set(0xeef2ff), WXFX.flash * 0.6);
    }
    skyMat.uniforms.cZenith.value.copy(cz);
    skyMat.uniforms.cHorizon.value.copy(ch);
    skyMat.uniforms.cGround.value.copy(cg);
    skyMat.uniforms.uCloud.value = WX.cover;
    // a full deck is darker than fair-weather cumulus: dimming it with cover
    // also calms the env-map wash that read as "snow on the ground" on
    // overcast days (the bright white dome was over-lighting every flat)
    skyMat.uniforms.uCloudLight.value = (0.10 + 0.95 * dayF + twi * 0.25) * (1 - 0.15 * WX.cover) * (1 - 0.55 * WXFX.gloom) + WXFX.flash * 2.2;
    skyMat.uniforms.cSun.value.copy(_c1.set(0xff8a40)).lerp(_c2.set(COLORS.sun), smooth(0, 20, el));
    scene.fog.color.copy(ch);
    // weather visibility: rain, snow and storm thicken the haze; true fog collapses it
    const murk = Math.max(WXFX.rain * 0.4, WXFX.snow * 0.6, WXFX.gloom * 0.5);
    scene.fog.color.lerp(_c2.set(0xbfc6cc).multiplyScalar(0.12 + 0.88 * dayF), Math.max(WXFX.fog * 0.9, WXFX.snow * 0.4, WXFX.snowGround * 0.3));
    // night air is shorter: the clear-air 16 km let the far ring's lit windows mass into a
    // white band on the horizon (the post target resolves its edges in linear light, where a
    // half-covered 1.3 window averages to white, not grey); by night the haze closes to 2.5..9 km
    // and the far city sinks into the sky the way the game's does
    // (the clear day air runs 8 to 40 km since Round 52; the night factors keep the night at
    // about 2.8 to 16 km, the reach Round 51 settled on, or the far windows band the horizon again)
    scene.fog.near = fogBase.near * (1 - 0.65 * night) * (1 - 0.75 * murk) * (1 - WXFX.fog) + 55 * WXFX.fog;
    scene.fog.far = fogBase.far * (1 - 0.6 * night) * (1 - 0.62 * murk) * (1 - WXFX.fog) + 850 * WXFX.fog;
    hemi.color.copy(_c1.set(0x1a2238)).lerp(_c2.set(0xdde7f2), dayF).lerp(_c1.set(0xf0b080), twi * 0.35);
    if (WXFX.flash > 0.003) hemi.color.lerp(_c2.set(0xdfe6ff), WXFX.flash * 0.7);
    hemi.groundColor.copy(_c1.set(0x0c0c10)).lerp(_c2.set(0x9c8e74), dayF);
    cloudShU.uCloudSh.value = 0.85 * dayF * (1 - 0.5 * WXFX.gloom);
    cloudShU.uCloudSlant.value.set(sunDir.x, sunDir.z).multiplyScalar(CLOUD_ALT / Math.max(sunDir.y, 0.25));   // a cloud's shadow lies where its sun ray lands
    hemi.intensity = (0.10 + 0.36 * dayF) * (1 - 0.18 * WX.cover) * (1 - 0.4 * WXFX.gloom) + WXFX.flash * 1.6;
    renderer.toneMappingExposure = 0.94 + 0.11 * dayF;
    postU.uExposure.value = renderer.toneMappingExposure;
    if (POST.on) pUndoColor(scene.fog.color, postU.uExposure.value);   // the fog mixes in the linear target: its colour goes in as the pre-image
    // the bright pass sees linear light: by day only the sun, the glints and the cloud rims clear
    // it (a sunlit white wall or snow cover sits near 2), by night the lamps and the lit windows do
    if (postBright) postBright.uniforms.uThr.value = 1.25 + 1.2 * dayF;
    nightUniform.value = night;
    // (bus night glow lives in bodyMat's aGlow shader term, driven by uNight)
    if (stMat) stMat.color.copy(_c1.set(0x2c2822)).lerp(_c2.set(0xa8a296), night);  // street text: dark on day roads, pale at night
    if (nbMat) {
      const nbFade = placesOn ? smooth(420, 1000, camera.position.y) : 0;   // names live at altitude
      nbMat.opacity = nbFade * 0.96;
      nbMesh.visible = nbFade > 0.02;
    }
    if (Math.abs(el - lastEnvEl) > 3 && (!envGap || performance.now() >= envNextT)) { lastEnvEl = el; envNextT = performance.now() + envGap; refreshEnv(); }
    if (towerGlassMat) towerGlassMat.emissiveIntensity = night * 0.16;
    if (towerVarMat) towerVarMat.emissiveIntensity = night * 0.9;
    // (core glass night lighting lives in rylandGlassMat's panel shader, via uNight)
    if (outerGlassMat) outerGlassMat.emissiveIntensity = night * 0.55;
    return el;
  }
  // --- time panel
  const timePanel = document.getElementById('timepanel');
  const timeDate = document.getElementById('timeDate');
  const timeSlider = document.getElementById('timeSlider');
  const timeClockEl = document.getElementById('timeClock');
  const timeSunEl = document.getElementById('timeSun');
  let sunCache = { key: '', rise: null, set: null };
  function clockDateStr() { return clock.y + '-' + (clock.m < 10 ? '0' : '') + clock.m + '-' + (clock.d < 10 ? '0' : '') + clock.d; }
  function refreshTimeUI() {
    const key = clockDateStr();
    if (sunCache.key !== key) { const t = sunTimes(clock); sunCache = { key, rise: t.rise, set: t.set }; }
    if (document.activeElement !== timeDate) timeDate.value = key;
    timeSlider.value = String(clock.minutes);
    const dst = tzOffsetMin(clock.y, clock.m, clock.d) === -240;
    timeClockEl.textContent = fmtTime(clock.minutes) + ' ' + (dst ? 'EDT' : 'EST') + (clock.live ? ' (Live)' : '');
    const mp = lunar(clockUtcMs(clock, clock.minutes));
    const phase = mp.k < 0.02 ? 'New Moon' : mp.k > 0.98 ? 'Full Moon'
      : Math.abs(mp.k - 0.5) < 0.035 ? (mp.wax ? 'First Quarter' : 'Last Quarter')
      : mp.k < 0.5 ? (mp.wax ? 'Waxing Crescent' : 'Waning Crescent')
      : (mp.wax ? 'Waxing Gibbous' : 'Waning Gibbous');
    const oct = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'][Math.round(mp.az / 45) % 8];
    timeSunEl.textContent = '↑ ' + fmtTime(sunCache.rise) + '  ↓ ' + fmtTime(sunCache.set)
      + (WX.ok ? '   ☁ ' + Math.round(WX.cover * 100) + '%' + (WX.temp == null ? '' : ' ' + Math.round(WX.temp) + '°F') + (wxLabelFull() ? ' ' + wxLabelFull() : '') : '')
      + (LTN.live && LTN.n10 > 0 ? '   ⚡ ' + LTN.n10 + (LTN.n10 === 1 ? ' strike' : ' strikes') + ' in 10 min, nearest ' + Math.max(1, Math.round(LTN.nearestKm * 0.6214)) + ' mi' : '')
      + '   ☾ ' + phase + ' ' + Math.round(mp.k * 100) + '%' + (mp.el > 0 ? ', Up ' + oct : ', Set');
  }
  function toggleTimePanel(open) { openPanel('time', open); }
  btnTime.addEventListener('click', () => toggleTimePanel());
  timeSlider.addEventListener('input', () => { setLapse(false); clockTouched = true; clock.live = false; clock.minutes = parseInt(timeSlider.value, 10); refreshTimeUI(); savePrefs(); });
  timeDate.addEventListener('change', () => {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(timeDate.value);
    if (!m) return;
    setLapse(false);
    clock.live = false; clock.y = +m[1]; clock.m = +m[2]; clock.d = +m[3];
    refreshTimeUI(); clockTouched = true; savePrefs();
  });
  document.getElementById('timeNow').addEventListener('click', () => { setLapse(false); clockTouched = true; clock.live = true; setClockToNow(); refreshTimeUI(); savePrefs(); });
  for (const btn of timePanel.querySelectorAll('[data-preset]')) {
    btn.addEventListener('click', () => {
      setLapse(false);
      clock.live = false;
      const t = sunTimes(clock);
      const p = btn.getAttribute('data-preset');
      clock.minutes = p === 'dawn' ? Math.max(0, (t.rise == null ? 360 : t.rise) - 12)
        : p === 'noon' ? 750
        : p === 'dusk' ? Math.min(1439, (t.set == null ? 1140 : t.set) + 8)
        : 1320;
      refreshTimeUI(); clockTouched = true; savePrefs();
    });
  }
  // --- sun time-lapse: ~2 clock minutes a frame (dt-scaled), the readout at
  // 4 Hz, the glass rebaked at most every 1.5 s (envGap), the clock pinned so
  // prefs and the hash carry the moment it stops on
  const timePlay = document.getElementById('timePlay');
  const lapse = { on: false, acc: 0, uiT: 0 };
  function setLapse(on) {
    on = !!on && !reducedMotion;
    if (on === lapse.on) return;
    lapse.on = on; lapse.acc = 0;
    envGap = on ? 1500 : 0;
    if (on) clock.live = false;
    timePlay.textContent = on ? 'Pause' : 'Play';
    timePlay.setAttribute('aria-pressed', on ? 'true' : 'false');
    refreshTimeUI(); clockTouched = true; savePrefs();
  }
  function stepLapse(now, dt) {
    if (!lapse.on) return;
    lapse.acc += dt * 120;                   // 2 min a frame at 60 fps, whatever the frame rate
    const n = Math.floor(lapse.acc);
    if (!n) return;
    lapse.acc -= n;
    clock.minutes += n;
    if (clock.minutes > 1439) {              // past midnight: the next day, date input included
      clock.minutes -= 1440;
      const d = new Date(Date.UTC(clock.y, clock.m - 1, clock.d + 1));
      clock.y = d.getUTCFullYear(); clock.m = d.getUTCMonth() + 1; clock.d = d.getUTCDate();
    }
    if (now - lapse.uiT > 250) { lapse.uiT = now; refreshTimeUI(); }
  }
  if (reducedMotion) timePlay.hidden = true;   // no racing sun for reduced-motion readers
  else timePlay.addEventListener('click', () => setLapse(!lapse.on));
  setClockToNow();
  refreshTimeUI();
  let lastMinuteTick = -1;
  // --- screenshot: the GL frame alone (no HUD) with a small stamp, offered to
  // the share sheet on touch where files are shareable, saved as a download elsewhere
  const btnShot = document.getElementById('btnShot');
  btnShot.addEventListener('click', () => {
    if (!veil.classList.contains('hidden')) return;
    frame(performance.now(), true);          // a fresh render, read back in this same tick (no preserveDrawingBuffer)
    const w = canvas.width, h = canvas.height;
    if (!w || !h) return;
    const cv = document.createElement('canvas');
    cv.width = w; cv.height = h;
    const g = cv.getContext('2d');
    g.drawImage(canvas, 0, 0);
    const s = Math.max(1, h / 900), pad = 16 * s;
    const site = 'philly3d.com', when = clockDateStr() + ', ' + timeClockEl.textContent.replace(' (Live)', '');
    const fSite = '600 ' + Math.round(21 * s) + 'px "Montserrat", "Avenir Next", "Segoe UI", sans-serif';
    const fWhen = '500 ' + Math.round(12 * s) + 'px "Montserrat", "Avenir Next", "Segoe UI", sans-serif';
    g.font = fSite; const w1 = g.measureText(site).width;
    g.font = fWhen; const w2 = g.measureText(when).width;
    const bw = Math.max(w1, w2) + pad * 2, bh = 56 * s, bx = pad, by = h - pad - bh;
    g.fillStyle = 'rgba(23,21,18,0.62)';
    g.fillRect(bx, by, bw, bh);
    g.textBaseline = 'alphabetic';
    g.fillStyle = '#c89b5e'; g.font = fSite; g.fillText(site, bx + pad, by + 26 * s);
    g.fillStyle = 'rgba(239,233,220,0.9)'; g.font = fWhen; g.fillText(when, bx + pad, by + 45 * s);
    const hh = Math.floor(clock.minutes / 60), mm = Math.round(clock.minutes % 60);
    const name = 'philly3d-' + clockDateStr() + '-' + (hh < 10 ? '0' : '') + hh + (mm < 10 ? '0' : '') + mm + '.png';
    cv.toBlob((blob) => {
      if (!blob) return;
      let file = null;
      try { file = new File([blob], name, { type: 'image/png' }); } catch (e) { }
      if (isTouch && file && navigator.share && navigator.canShare && navigator.canShare({ files: [file] })) {
        navigator.share({ files: [file], title: 'Philly3D' }).catch(() => { });
        return;
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = name;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    }, 'image/png');
  });

  // ---------------------------------------------------------------- build & loop
  const BEACON_STEPS = new Set(['Raising the outer districts', 'Raising the rest of Philadelphia', 'Raising the towns across the line', 'Planting the street trees']);
  async function build() {
    let failures = 0;
    for (const s of buildSteps) {
      loadmsg.textContent = s.msg;
      await yieldNow();
      const t0 = performance.now();
      try { const r = s.fn(); if (r && typeof r.then === 'function') await r; } catch (err) { failures++; PERF.failed.push([s.msg, String(err && err.message || err)]); console.error('build step failed:', s.msg, err); try { flushUploads(true); } catch (e2) { /* nothing staged */ } }
      PERF.steps.push([s.msg, Math.round(performance.now() - t0)]);
      if (BEACON_STEPS.has(s.msg)) beacon('step:' + s.msg, { ms: PERF.steps[PERF.steps.length - 1][1] });
    }
    PERF.ready = Math.round(performance.now() - PERF.t0);
    beacon('ready', { ms: PERF.ready, fail: failures });
    loadmsg.textContent = failures ? 'Ready (some detail could not be built)' : 'Ready';
    loadmsg.classList.add('done');   // the pulse stops with the wait
    btnEnter.disabled = false;
    btnEnter.textContent = 'Enter the City';
  }

  btnEnter.addEventListener('click', () => {
    btnEnter.blur();   // #veil.hidden is opacity only; a focused Enter button would swallow every key
    beacon('enter', { ms: Math.round(performance.now()) });
    setTimeout(() => { const p = perfStats(); beacon('perf', { p50: p.p50, p95: p.p95, calls: p.calls, tris: p.tris, dpr: p.dpr.toFixed(2), mode }); }, 60000);
    veil.classList.add('hidden');
    if (mode === MODE.ORBIT) orbit.goalR = 700;   // glide in from the veil's wide shot
    if (reducedMotion) {
      orbit.r = orbit.goalR; orbit.theta = orbit.goalTheta; orbit.phi = orbit.goalPhi;
    } else if (!interacted) {
      introSpin = true;
    }
    setHint();
  });

  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setPixelRatio(DPR.cur);
    renderer.setSize(window.innerWidth, window.innerHeight);
  });
  canvas.addEventListener('webglcontextlost', (e) => {
    e.preventDefault();
    const el = document.getElementById('nogl');
    el.style.display = 'flex';
    el.firstElementChild.innerHTML = 'The 3D view was interrupted (graphics memory pressure).<br>Reload the page to continue exploring.';
  });

  // THREE.Fog saturates at fog.far, so a chunk whose every point lies deeper
  // than that renders as a flat fog-coloured silhouette over fog-coloured
  // ground: skip it. The test is in VIEW depth (fog is view-z, not radial), so
  // nothing at the frame edge blinks; the outer meshes carry the identity
  // matrix, so their bounding spheres are already world space. In rain and
  // snow fog.far shrinks 62%, and true fog pulls it to 850 m: then nearly all
  // 279 chunks drop out.
  const _cullD = new V3(), _cullF = new V3();
  function cullFogged() {
    const far = scene.fog.far, cp = camera.position;
    camera.getWorldDirection(_cullF);
    for (const m of outerMeshes) {
      const bs = m.geometry.boundingSphere;
      if (!bs) continue;
      m.visible = _cullD.copy(bs.center).sub(cp).dot(_cullF) - bs.radius < far;
    }
  }
  let last = performance.now();
  let shadowMode = -1;
  let lastBearing = null;
  let frameNo = 0, lastCasterSig = -1;
  let devHud = null, devHudT = 0;   // the ?dev readout (built with the rest of __dbg)
  function perfStats() {
    const n = Math.min(PERF.rn, 600);
    const a = Array.from(PERF.ring.subarray(0, n)).sort((x, y) => x - y);
    const info = renderer.info;
    return { readyMs: PERF.ready || null, steps: PERF.steps, failed: PERF.failed, frames: n,
      p50: n ? +a[Math.floor(n * 0.5)].toFixed(1) : null, p95: n ? +a[Math.floor(n * 0.95)].toFixed(1) : null,
      calls: POST.on ? POST.calls : info.render.calls, tris: POST.on ? POST.tris : info.render.triangles, programs: info.programs.length, geometries: info.memory.geometries, textures: info.memory.textures,
      dpr: DPR.cur, heapMB: performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : null };
  }
  function perfLine() {
    const p = perfStats();
    return 'p50 ' + p.p50 + ' ms  p95 ' + p.p95 + ' ms  |  ' + p.calls + ' calls  ' + (p.tris / 1e6).toFixed(2) + ' M tris  ' + p.programs + ' prog  |  dpr ' + p.dpr.toFixed(2) + (p.heapMB ? '  heap ' + p.heapMB + ' MB' : '') + '  |  ready ' + (p.readyMs / 1000).toFixed(1) + ' s';
  }
  function frame(now, once) {
    if (!once) requestAnimationFrame(frame);
    const rawMs = now - last;
    const dt = Math.min(rawMs / 1000, 0.05);
    last = now;
    frameNo++;
    if (!once && rawMs < 500) { PERF.ring[PERF.ri] = rawMs; PERF.ri = (PERF.ri + 1) % 600; PERF.rn++; }
    if (devHud && now - devHudT > 1000) { devHudT = now; devHud.textContent = perfLine(); }
    // adaptive resolution: 30-frame windows; a >250 ms gap is a stall or a
    // throttled tab, not a slow frame, and is not counted
    if (!once && !DPR.pinned && rawMs < 250 && !document.hidden) {
      DPR.ring[DPR.i++] = rawMs;
      if (DPR.i === 30) {
        DPR.i = 0;
        DPR.tmp.set(DPR.ring); DPR.tmp.sort();
        const med = DPR.tmp[15];
        if (med > 22) { DPR.fast = 0; if (DPR.cur > DPR.min) applyDPR(Math.max(DPR.min, DPR.cur * 0.85)); }
        else if (med < 13) { if (++DPR.fast >= 4 && DPR.cur < DPR.cap) { DPR.fast = 0; applyDPR(Math.min(DPR.cap, DPR.cur / 0.85)); } }
        else DPR.fast = 0;
      }
    }
    if (introSpin && !interacted) orbit.goalTheta += dt * 0.045;
    else if (orbitSpin && mode === MODE.ORBIT) orbit.goalTheta += dt * 0.12;   // a search result's slow circle, ~50 s a lap
    if (clock.live) {
      const nowMin = Math.floor(Date.now() / 60000);
      if (nowMin !== lastMinuteTick) { lastMinuteTick = nowMin; setClockToNow(); refreshTimeUI(); }
    }
    stepLapse(now, dt);
    updateWeatherFX(now, dt);
    applyLighting();
    stepTour(now);
    stepGlide(now);
    if (mode === MODE.ORBIT) applyOrbit(dt);
    else if (mode === MODE.WALK) applyWalk(dt);
    else applyFly(dt);

    // the shadow box rides with the camera: tight on foot, growing with altitude in flight,
    // re-aimed a little ahead of the view only after a good move so the depth pass stays rare
    camera.getWorldDirection(tmpV);
    {
      const onFoot = mode === MODE.WALK;
      const px = onFoot ? walk.pos.x : camera.position.x, pz = onFoot ? walk.pos.z : camera.position.z;
      const ext = onFoot ? 300 : Math.round(clamp(320 + camera.position.y * 0.9, 300, 900) / 100) * 100;
      const c = sun.target.position;
      if (ext !== lastAim.extent || Math.hypot(px - c.x, pz - c.z) > ext * 0.35) aimSun(px + tmpV.x * ext * 0.35, pz + tmpV.z * ext * 0.35, ext);
    }

    // compass: rotation = -bearing of camera forward (write only on change)
    const bearing = Math.round(Math.atan2(tmpV.x, -tmpV.z) * 1800 / Math.PI) / 10;
    if (bearing !== lastBearing) {
      lastBearing = bearing;
      needle.setAttribute('transform', 'rotate(' + (-bearing) + ' 17 17)');
    }

    // fabric chunks wholly beyond the fog wall would shade to flat fog colour
    if ((frameNo & 3) === 2) cullFogged();
    // shadow map (autoUpdate is off): vehicles moving through the box get a
    // fresh depth pass every 4th frame; a changed static caster set (docks
    // arriving with the first Indego poll) gets one immediately
    const movers = (septaReady && SEPTA.on && septaSolid && septaSolid.count > 0) || (!isTouch && TRAFFIC.on && TRAFFIC.n > 0);
    const casterSig = (indegoReady && indegoSolid ? indegoSolid.count + (indegoBike ? indegoBike.count * 4096 : 0) : 0) + (movers ? 1 << 30 : 0);   // bikes cast too; movers switching off needs one last redraw
    if ((movers && (frameNo & 3) === 0) || casterSig !== lastCasterSig) { lastCasterSig = casterSig; renderer.shadowMap.needsUpdate = true; }
    sky.position.copy(camera.position);
    cloudDeck.position.x = camera.position.x; cloudDeck.position.z = camera.position.z;
    skyMat.uniforms.uCloudOff.value.addScaledVector(wxWind, dt);
    if (!reducedMotion) waterU.uTime.value += dt;
    grassUpdate();
    waterU.uSun.value.copy(glintDir);
    updateTransit(now, dt);
    updateIndego(now, dt);
    updateFlights(now, dt);
    updateShips(now, dt);
    updateTraffic(now, dt);
    updateLights(now);
    updateTreePick();
    updateSearchMark(now);
    scoresPoll(now); scoresRender();
    if (lotStripes) {
      // the stall lines are 1 px lines: past a few hundred metres they alias into moire over
      // the whole lot, so they fade out between 500 and 1500 m instead of cutting at 3.5 km
      const dLot = camera.position.distanceTo(LOT_CENTER);
      lotStripes.visible = dLot < 1500;
      lotStripes.material.opacity = lotStripes.userData.op * (1 - smooth(500, 1500, dLot));
    }
    updateLabels();
    updateHash(now);
    if (POST.on) renderPost(scene, camera); else renderer.render(scene, camera);
  }

  setHint();
  if (WX_PRESETS[wxForced]) applyWx({ current: WX_PRESETS[wxForced] });
  fetchWeather();
  setInterval(fetchWeather, 15 * 60 * 1000);
  fetchNws();
  setInterval(fetchNws, 5 * 60 * 1000);   // the NWS caches its answers ~5 min anyway
  // remembered layers and clock, then the share hash on top of them; the rows
  // are synced now so the panel matches before the first frame (flag-only:
  // every step still builds; the camera pose waits for build, it needs terrain)
  const hashView = parseHash();
  {
    const p = loadPrefs(), f = {};
    if (p && typeof p === 'object') {
      for (const k of LAYER_KEYS) if (typeof p[k] === 'boolean') f[k] = p[k];
      const m = p.live === false && typeof p.date === 'string' ? /^(\d{4})-(\d{2})-(\d{2})$/.exec(p.date) : null;
      if (m) applyClock(+m[1], +m[2], +m[3], +p.minutes);
    }
    if (hashView.l !== undefined) Object.assign(f, layersFromMask(hashView.l));
    if (hashView.t && applyClock(Math.floor(hashView.t[0] / 10000), Math.floor(hashView.t[0] / 100) % 100, hashView.t[0] % 100, hashView.t[1])) hashClock = true;
    setLayerFlags(f);
    syncLayerBtns();
    refreshTimeUI();
  }
  build().then(() => {
    // weather-surface pass. The materials already compiled during build (flushUploads renders
    // the scene behind the veil); the hooks assigned here land through the first frame's
    // refreshEnv (lastEnvEl starts at 999), which swaps scene.environment and makes r149
    // refetch every program. Chain cityMat (facade shader first, then the weather); WRAP the
    // flats that carry `userData.wxSurf` (surfMat, groundSurfMat and any hook built on them),
    // so the shader runs their own patch first and the snow lands over it (the later replace
    // lands earlier in the shader), keyed on the wrapped hook (gotcha 15); then every hookless
    // standard material in the built scene. Other materials with their own onBeforeCompile
    // (water, vehicles, glass, street text, poles) are left alone, as is anything created
    // later (planes, ships, live vehicles).
    {
      const prevCity = cityMat.onBeforeCompile;
      cityMat.onBeforeCompile = (sh, r) => { prevCity(sh, r); wxSurfacePatch(sh); };
      cityMat.customProgramCacheKey = () => 'fabric|wx';
      const prevCore = coreMat.onBeforeCompile;
      coreMat.onBeforeCompile = (sh, r) => { prevCore(sh, r); wxSurfacePatch(sh); };
      coreMat.customProgramCacheKey = () => 'fabric-core|wx';
      const seen = new Set([cityMat, coreMat]);
      scene.traverse((o) => {
        const ms = o.material;
        for (const m of Array.isArray(ms) ? ms : ms ? [ms] : []) {
          if (!m.isMeshStandardMaterial || seen.has(m)) continue;
          seen.add(m);
          if (m.userData.wxSurf) {
            const prev = m.onBeforeCompile;
            m.onBeforeCompile = (sh, r) => { wxSurfacePatch(sh); prev(sh, r); };
            m.customProgramCacheKey = () => 'wx|' + prev.toString();
            continue;
          }
          if (Object.prototype.hasOwnProperty.call(m, 'onBeforeCompile')) continue;
          if (m.flatShading) continue;
          m.onBeforeCompile = wxSurfacePatch;
        }
      });
    }
    if (/[?&]dev\b/.test(location.search)) {
      devHud = document.createElement('div');
      devHud.id = 'devhud';
      devHud.style.cssText = 'position:fixed;left:8px;top:8px;z-index:30;padding:4px 8px;font:11px/1.4 ui-monospace,Menlo,monospace;color:#efe9dc;background:rgba(23,21,18,.72);border-radius:3px;pointer-events:none;white-space:pre';
      document.body.appendChild(devHud);
      window.__dbg = { orbit, walk, fly, camera, renderer, scene, WX, WXFX, detFar: detFarUniform, storefronts: () => STOREFRONT_N, walls: () => WALL_N, towers: () => ({ specs: TOWER_SPECS.length, crowns: TOWER_CROWN_N }), roofPlan, roofQuad, scores: () => ({ games: SCORES.games, fails: SCORES.fails }), scoreTest: () => { SCORES.nextT = performance.now() + 600000; scoresSet([{ k: 'mlb', live: true, us: 'PHI', uscore: '4', them: 'NYM', tscore: '2', color: 'e81828', logo: 'https://a.espncdn.com/i/teamlogos/mlb/500/phi.png', detail: 'Bot 7th, away' }, { k: 'nfl', live: true, us: 'PHI', uscore: '17', them: 'DAL', tscore: '10', color: '06424d', logo: 'https://a.espncdn.com/i/teamlogos/nfl/500/phi.png', detail: '3rd 8:41' }, { k: 'nhl', live: false, us: 'PHI', uscore: '2', them: 'PIT', tscore: '3', color: 'f74902', logo: 'https://a.espncdn.com/i/teamlogos/nhl/500/phi.png', detail: 'Final/OT' }]); }, wxSurfU, waterU, flightTest, shipTest, DPR, PERF, perf: perfStats, fetchWeather, fetchNws, lightning: () => ({ live: LTN.live, ok: LTN.ok, fails: LTN.fails, n: LTN.n, n10: LTN.n10, nearestKm: LTN.nearestKm, queued: LTN.queue.length, drawn: LTN.drawn }), strike: (lat, lon) => spawnStrike(performance.now(), [Date.now() / 1000, lat, lon, 0]),
      wx: (n) => applyWx({ current: WX_PRESETS[n] || { weather_code: +n || 0, cloud_cover: 90, precipitation: 2, temperature_2m: 60 } }),
      bolt: () => spawnBolt(performance.now()), ships: () => ({ n: shipMap.size, ok: SHIPS.ok, sock: !!SHIPS.sock, list: [...shipMap.values()].map((v) => ({ name: v.name || v.mmsi, tn: v.tn, x: Math.round(v.dx || v.fx || 0), z: Math.round(v.dz || v.fz || 0), sog: v.sog, len: v.len })) }), flights: () => ({ n: flightMap.size, ok: FLIGHTS.ok, fails: FLIGHTS.fails, host: FLIGHTS.host }), indego: () => ({ n: indegoSt.size, drawn: indegoLive.length, ok: INDEGO.ok, fails: INDEGO.fails }), traffic: () => ({ runs: trafficRuns.length, drawn: TRAFFIC.n, scale: +TRAFFIC.scale.toFixed(3), km: Math.round(trafficRuns.reduce((a, r) => a + r.len, 0) / 1000) }), post: POST, postMats: () => ({ bright: postBright, blur: postBlur, comp: postComp }), postU, envSky, refreshEnv, cloudDeck, skyMat, sunLight: sun, hemi, frameOnce: () => frame(performance.now(), true), goWalk: (x, z, yaw) => { setMode(MODE.WALK); walk.pos.set(x, 1.7, z); walk.yaw = yaw; walk.pitch = 0.12; }, goFly: (x, y, z, yaw, pitch) => { setMode(MODE.FLY); fly.pos.set(x, y, z); walk.yaw = yaw; walk.pitch = pitch || 0; } };
    }
    if (hashView.p) applyHashView(hashView.p);
    prefsReady = true;   // the init syncs inside the build steps must not write the blob
    requestAnimationFrame(frame);
  });
})();
