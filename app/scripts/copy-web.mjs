// Copies the built page (../3d-model/society-hill-towers.html, from `python3 build.py`) into www/index.html for Capacitor,
// and beside it the generated art the app can ask for (../3d-model/art/ into www/art/, Round 184: the page loads those
// images on demand by relative path, so the app carries them and never fetches them). Run `npm run sync` after every page build.
//
// Round 225: only the art a phone can ask for. The app always takes the phone path, where artSrc answers a record's half
// copy, so the 365 full-size files that have one (33.4 of the folder's 43.6 MB on Nov 10) were bundled and never read:
// art-touch.mjs has the rule and its table of kinds that keep their full size. The list comes from the page being copied,
// every file on it is checked before anything is written, and the folder is brought to the list by name (a file already
// there with its source's bytes is left alone: the old delete and recopy rewrote 43 MB inside Dropbox on every sync).
// SHT_APP_SRC and SHT_APP_WWW point it at another page folder and another www (the tests' way in).
//
// The review of Round 225 closed three ways this could go wrong in silence, each now a FATAL before the first write:
// a www that is, or reaches into, the source folder (the sync removes what is not on the list, and with SHT_APP_WWW set to
// the source it removed the source's own full-size files); art on disk the page's scan did not find (a path the scan
// cannot see, say a manifest inlined through JSON.parse('...'), left its files out with only a note, and a phone asking
// for them draws the procedural look); and a file already in www with the right name and size but the wrong bytes, which
// was kept for good and is now compared with its source and copied again.
import { copyFileSync, mkdirSync, readFileSync, readdirSync, realpathSync, rmSync, rmdirSync, statSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { artNamed, artTouch } from './art-touch.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const from = process.env.SHT_APP_SRC ? resolve(process.env.SHT_APP_SRC) : resolve(here, '../../3d-model');
const www = process.env.SHT_APP_WWW ? resolve(process.env.SHT_APP_WWW) : resolve(here, '../www');
const src = join(from, 'society-hill-towers.html');
const out = join(www, 'index.html');
const fatal = (msg) => { console.error('FATAL (copy-web): ' + msg); process.exit(1); };
const mb = (b, d) => (b / 1e6).toFixed(d);
// every file under a folder, as 'art/...' paths
const walk = (dir, list = []) => {
  let ents = [];
  try { ents = readdirSync(dir, { withFileTypes: true }); } catch (e) { return list; }
  for (const e of ents) { const p = join(dir, e.name); if (e.isDirectory()) walk(p, list); else list.push(p); }
  return list;
};
const artPath = (root, file) => 'art/' + relative(join(root, 'art'), file).split(sep).join('/');
// where a path really is, links followed, for a path that may not exist yet (its nearest existing folder, then the rest)
const real = (p) => {
  const rest = [];
  for (let at = p; ; at = dirname(at)) {
    try { return join(realpathSync.native(at), ...rest); } catch (e) { /* not there yet */ }
    if (dirname(at) === at) return p;
    rest.unshift(basename(at));
  }
};
const within = (a, b) => a === b || a.startsWith(b + sep);

// www is never the source, nor its art folder the source's (a link counts): what the list does not hold is REMOVED from
// www/art below, so a www that reaches the source would delete the bakes' own files and write index.html over 3d-model's
const realArt = [real(join(www, 'art')), real(join(from, 'art'))];
if (real(out) === real(src) || real(www) === real(from) || within(realArt[0], realArt[1]) || within(realArt[1], realArt[0])) {
  fatal('the app folder ' + real(www) + ' is, or reaches into, the source folder ' + real(from) + ': the sync removes files from www/art, so it will not run there');
}

// the list, and every file on it, before anything is written: a failed check leaves the app's folder as it was
// (the page is read once and those bytes are what www gets: several sessions share the checkout, and a build.py finishing
// between a read and a later copy would ship a page the list was not read from)
let page;
try { page = readFileSync(src); } catch (e) { fatal('no built page at ' + src + ': run python3 build.py first'); }
const named = artNamed(page.toString('utf8'));
if (!named.length) fatal('the page names no art at all, so the list cannot be trusted: is ' + src + ' a built page?');
const odd = named.filter((p) => !/^art(\/[A-Za-z0-9_.-]+)+$/.test(p) || p.includes('..'));
if (odd.length) fatal(odd.length + ' art path(s) the page names are not plain paths under art/, first ' + odd[0]);
const size = new Map();
const missing = [];
for (const p of named) {
  let st = null;
  try { st = statSync(join(from, p)); } catch (e) { /* missing */ }
  if (st && st.isFile() && st.size > 0) size.set(p, st.size); else missing.push(p);
}
if (missing.length) fatal(missing.length + ' art file(s) the page names are missing or empty under ' + from + ', first ' + missing[0] + ' (a page older than its art? run python3 build.py)');
const { carry, leave } = artTouch(named);
const bytes = (list) => list.reduce((a, p) => a + size.get(p), 0);
// The page and its folder agree exactly, or nothing ships: the bakes prune art/ and build.py refuses a missing file, so
// a file here the scan did not find is art newer than the page or a name the scan cannot see, and either way the app
// would be short of something its page asks for. (The Finder's dotfiles are not art.)
const unnamed = walk(join(from, 'art')).filter((f) => !basename(f).startsWith('.')).map((f) => artPath(from, f)).filter((p) => !size.has(p));
if (unnamed.length) fatal(unnamed.length + ' file(s) under art/ are not named by this page, first ' + unnamed[0] + ': the page and its art do not agree (art newer than the page? run python3 build.py; if the page does name it, artNamed in art-touch.mjs cannot see how)');

mkdirSync(www, { recursive: true });
writeFileSync(out, page);
console.log('www/index.html <- 3d-model/society-hill-towers.html (' + mb(page.length, 2) + ' MB)');

// the art, by name: what the list no longer holds goes, what is missing or not its source's bytes is copied, the rest stays
// (the compare reads the app's 10 MB twice over and writes nothing)
const keep = new Set(carry);
let removed = 0, copied = 0;
for (const f of walk(join(www, 'art'))) if (!keep.has(artPath(www, f))) { rmSync(f, { force: true }); removed++; }
const prune = (dir) => {
  for (const e of readdirSync(dir, { withFileTypes: true })) if (e.isDirectory()) prune(join(dir, e.name));
  if (!readdirSync(dir).length) rmdirSync(dir);
};
try { prune(join(www, 'art')); } catch (e) { /* no folder yet */ }
for (const p of carry) {
  const to = join(www, p);
  let st = null;
  try { st = statSync(to); } catch (e) { /* not there yet */ }
  if (st && st.isFile() && st.size === size.get(p) && readFileSync(to).equals(readFileSync(join(from, p)))) continue;
  mkdirSync(dirname(to), { recursive: true });
  copyFileSync(join(from, p), to);
  copied++;
}
// the folder is the list, file for file and byte for byte (each was compared or copied above), or the sync has failed
const held = walk(join(www, 'art'));
const heldBytes = held.reduce((a, f) => a + statSync(f).size, 0);
if (held.length !== carry.length || heldBytes !== bytes(carry)) fatal('www/art holds ' + held.length + ' files, ' + heldBytes + ' bytes, against the list\'s ' + carry.length + ' and ' + bytes(carry));
console.log('www/art <- 3d-model/art: the ' + carry.length + ' files a phone can ask for, ' + mb(bytes(carry), 1) + ' MB (' + copied + ' copied, ' + (carry.length - copied) + ' already there, ' + removed + ' removed)');
console.log('left out: ' + leave.length + ' full-size files with a half copy, ' + mb(bytes(leave), 1) + ' MB, of the ' + named.length + ' files, ' + mb(bytes(named), 1) + ' MB, the page names');
