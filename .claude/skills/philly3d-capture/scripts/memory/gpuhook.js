(function(){
  var G = window.__gpu = { buf: 0, tex: 0, rb: 0, peak: 0, peakAt: '', heapPeak: 0, heapPeakAt: '', log: [] };
  var bsz = new WeakMap(), tsz = new WeakMap(), rsz = new WeakMap();
  function msg() { var lm = document.getElementById('loadmsg'); return lm ? lm.textContent.slice(0, 40) : ''; }
  function bump() { var t = G.buf + G.tex + G.rb; if (t > G.peak) { G.peak = t; G.peakAt = msg(); } }
  function bpe(type) { return type === 0x1406 ? 4 : (type === 0x140B || type === 0x8D61 || type === 0x1403 || type === 0x1402) ? 2 : 1; }   // FLOAT, HALF_FLOAT(s), USHORT, SHORT
  function chans(fmt) { return fmt === 0x1908 || fmt === 0x8D99 ? 4 : fmt === 0x1907 ? 3 : fmt === 0x8227 || fmt === 0x8228 ? 2 : 1; }
  [window.WebGLRenderingContext, window.WebGL2RenderingContext].forEach(function (C) {
    if (!C) return; var P = C.prototype;
    var bd = P.bufferData;
    P.bufferData = function (target, data) {
      var b = this.getParameter(target === this.ELEMENT_ARRAY_BUFFER ? this.ELEMENT_ARRAY_BUFFER_BINDING : this.ARRAY_BUFFER_BINDING);
      var n = typeof data === 'number' ? data : (data && data.byteLength) || 0;
      if (b) { G.buf += n - (bsz.get(b) || 0); bsz.set(b, n); bump(); }
      return bd.apply(this, arguments);
    };
    var db = P.deleteBuffer;
    P.deleteBuffer = function (b) { if (b && bsz.has(b)) { G.buf -= bsz.get(b); bsz.delete(b); } return db.apply(this, arguments); };
    var ti = P.texImage2D;
    P.texImage2D = function () {
      var a = arguments, t = this.getParameter(this.TEXTURE_BINDING_2D) || this.getParameter(this.TEXTURE_BINDING_CUBE_MAP), lvl = a[1], n = 0;
      if (a.length >= 8 && typeof a[3] === 'number') n = a[3] * a[4] * chans(a[6]) * bpe(a[7]);
      else if (a.length === 6) { var s = a[5]; var w = s && (s.width || s.videoWidth || 0), h = s && (s.height || s.videoHeight || 0); n = w * h * chans(a[3]) * bpe(a[4]); }
      if (t) { var m = tsz.get(t) || {}; var k = a[0] + ':' + lvl; G.tex += n - (m[k] || 0); m[k] = n; tsz.set(t, m); bump(); }
      return ti.apply(this, arguments);
    };
    if (P.texStorage2D) { var ts = P.texStorage2D; P.texStorage2D = function (target, levels, ifmt, w, h) { var t = this.getParameter(this.TEXTURE_BINDING_2D); var n = w * h * 4 * (levels > 1 ? 1.33 : 1) * (ifmt === 0x881A || ifmt === 0x8814 ? 2 : 1); if (t) { var m = tsz.get(t) || {}; G.tex += n - (m.s || 0); m.s = n; tsz.set(t, m); bump(); } return ts.apply(this, arguments); }; }
    var gm = P.generateMipmap; P.generateMipmap = function (target) { var t = this.getParameter(this.TEXTURE_BINDING_2D); if (t) { var m = tsz.get(t) || {}; var base = m[target + ':0'] || 0; var add = base * 0.33; G.tex += add - (m.mip || 0); m.mip = add; tsz.set(t, m); bump(); } return gm.apply(this, arguments); };
    var dt = P.deleteTexture; P.deleteTexture = function (t) { var m = t && tsz.get(t); if (m) { for (var k in m) G.tex -= m[k]; tsz.delete(t); } return dt.apply(this, arguments); };
    var rs = P.renderbufferStorage; P.renderbufferStorage = function (target, fmt, w, h) { var r = this.getParameter(this.RENDERBUFFER_BINDING); var n = w * h * 4; if (r) { G.rb += n - (rsz.get(r) || 0); rsz.set(r, n); bump(); } return rs.apply(this, arguments); };
    if (P.renderbufferStorageMultisample) { var rm = P.renderbufferStorageMultisample; P.renderbufferStorageMultisample = function (target, samples, fmt, w, h) { var r = this.getParameter(this.RENDERBUFFER_BINDING); var n = w * h * 4 * samples; if (r) { G.rb += n - (rsz.get(r) || 0); rsz.set(r, n); bump(); } return rm.apply(this, arguments); }; }
  });

  // the ANGLE Metal audit: every attribute pointer whose stride or offset is not 4-aligned is copied into a padded
  // buffer (4 B a vertex, 8 B for 16-bit triples) and kept; sum those copies by the source buffer's size
  G.mis = {}; G.misBytes = 0; var misSeen = new WeakMap();
  [window.WebGLRenderingContext, window.WebGL2RenderingContext].forEach(function (C) {
    if (!C) return; var P = C.prototype, vp = P.vertexAttribPointer;
    P.vertexAttribPointer = function (idx, size, type, norm, stride, offset) {
      var bpe2 = (type === 0x1400 || type === 0x1401) ? 1 : (type === 0x1402 || type === 0x1403 || type === 0x140B) ? 2 : 4;
      var eff = stride || size * bpe2;
      if (eff % 4 || offset % 4) {
        var b = this.getParameter(this.ARRAY_BUFFER_BINDING);
        var key = size + 'x' + bpe2 + (norm ? 'n' : '') + ' stride ' + eff + ' off ' + offset;
        if (b && !misSeen.has(b)) { misSeen.set(b, 1); var sz = bsz.get(b) || 0; var verts = Math.floor(sz / eff); var copy = verts * (bpe2 === 2 && size === 3 ? 8 : 4); G.misBytes += copy; G.mis[key] = (G.mis[key] || 0) + copy; }
      }
      return vp.apply(this, arguments);
    };
  });
  // the JS heap, sampled at every macrotask boundary (a MessageChannel ping is not timer-clamped)
  var ch = new MessageChannel(), last = 0;
  ch.port1.onmessage = function () {
    var now = performance.now();
    if (now - last > 40 && performance.memory) { last = now; var h = performance.memory.usedJSHeapSize; if (h > G.heapPeak) { G.heapPeak = h; G.heapPeakAt = msg(); } if (G.log.length < 4000) G.log.push([Math.round(now), Math.round(h / 1048576), Math.round((G.buf + G.tex + G.rb) / 1048576), msg()]); }
    if (!G.stop) setTimeout(function () { ch.port2.postMessage(0); }, 0);
  };
  ch.port2.postMessage(0);
})();
