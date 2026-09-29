// page-side capture helper: await __cap(name, x, y, z, yaw, pitch, frames) flies the camera, drives N frames and POSTs
// the canvas to the capture sink on 127.0.0.1:8934 (a jpeg, or a png when the name ends in .png).
// Inject this file's text through javascript_tool; it is not loaded by the page.
// Never await between the last frameOnce() and toBlob: the compositor can clear the buffer and you get a black jpeg.
// Round 167: every frame but the last is its own task (a MessageChannel yield, which no hidden-pane clamp slows), because
// on WebGL 2 the pins' depth image is read back behind a fence and a fence passes only between tasks: frames driven in
// one task judge the pins against the image of the pose before. So __cap is async: await each one, and never start a
// second before the first resolves (their frames would interleave). __dbg.pinAsync(false) instead forces the synchronous
// read the page made before Round 167.
window.__task = function () {
  return new Promise(function (r) { var c = new MessageChannel(); c.port1.onmessage = function () { r(); }; c.port2.postMessage(0); });
};
window.__cap = async function (name, x, y, z, yaw, pitch, frames) {
  __dbg.goFly(x, y, z, yaw, pitch);
  var n = frames || 6;
  for (var i = 0; i < n - 1; i++) { __dbg.frameOnce(); await __task(); }
  __dbg.frameOnce();
  var blob = await new Promise(function (res) {   // toBlob is called in this same task, straight after the last frame
    __dbg.renderer.domElement.toBlob(res, /\.png$/i.test(name) ? 'image/png' : 'image/jpeg', 0.92);
  });
  if (!blob) throw new Error('no blob');
  var r = await fetch('http://127.0.0.1:8934/cap?name=' + encodeURIComponent(name), { method: 'POST', body: blob });
  return { name: name, ok: r.ok, bytes: blob.size };
};
// n frames, each its own task (await it)
window.__frames = async function (n) { for (var i = 0; i < n; i++) { __dbg.frameOnce(); await __task(); } return n; };
'cap helper ready';
