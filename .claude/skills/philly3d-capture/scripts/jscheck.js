ObjC.import('Foundation');
function run(argv) {
  var src = ObjC.unwrap($.NSString.stringWithContentsOfFileEncodingError($(argv[0]), $.NSUTF8StringEncoding, null));
  try { new Function(src); return 'syntax ok: ' + src.length + ' chars'; } catch (e) { return 'SYNTAX ERROR: ' + e + '\n' + (e.line || '') + ' ' + (e.stack || '').slice(0, 300); }
}
