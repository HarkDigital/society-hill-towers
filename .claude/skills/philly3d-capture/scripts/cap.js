// page-side capture helper: __cap(name, x, y, z, yaw, pitch, frames) flies the camera,
// drives N frames synchronously and POSTs the canvas to the capture sink on 127.0.0.1:8934.
// Inject this file's text through javascript_tool; it is not loaded by the page.
// Never await between the last frameOnce() and toBlob: the compositor can clear the buffer and you get a black jpeg.
window.__cap = function (name, x, y, z, yaw, pitch, frames) {
  return new Promise(function (resolve, reject) {
    __dbg.goFly(x, y, z, yaw, pitch);
    for (var i = 0; i < (frames || 6); i++) __dbg.frameOnce();
    __dbg.renderer.domElement.toBlob(function (blob) {
      if (!blob) { reject(new Error('no blob')); return; }
      fetch('http://127.0.0.1:8934/cap?name=' + encodeURIComponent(name), { method: 'POST', body: blob })
        .then(function (r) { resolve({ name: name, ok: r.ok, bytes: blob.size }); }, reject);
    }, 'image/jpeg', 0.92);
  });
};
window.__frames = function (n) { for (var i = 0; i < n; i++) __dbg.frameOnce(); return n; };
'cap helper ready';
