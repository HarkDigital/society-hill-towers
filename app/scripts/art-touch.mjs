// Which of the page's generated art the app carries (Round 225, Stage 1 of the Nov 10 plan: the app carries only the art
// a phone can ask for). Inside the app the page always takes the phone path (app.js: IN_APP forces isTouch), and its one
// selector, `artSrc = (full, half) => (isTouch && half ? half : full)`, answers the half copy wherever a record has one. So
// a full-size file that has a half copy is never requested by the app: measured on Nov 10, 365 of the 782 files the page
// names, 33,411,772 of 43,584,928 bytes, which copy-web.mjs used to put in the bundle all the same.
//
// The rule here works on the file names alone. The bakes (art_files.py) write a record's half copy as `<name>-half` beside
// `<name>` in the same art/<kind>/ folder, so a file is left out when its `-half` twin is named too. That this is artSrc's
// own rule, record by record over the shipped manifests, is what 3d-model/tests/test_app_art.py proves by running the page's
// artSrc line itself; the same test refuses an art request in app.js that does not go through artSrc. It is the guard: a
// phone path that asked for a file the app does not hold would fall silently to the procedural look (artImage answers null).

// The art kinds (the folder under art/) whose full-size files the app carries beside their half copies. Empty today, when
// no phone path reads a full-size file that has a half. It is keyed by kind so the full-size pictures can come back one
// kind at a time, 'fronts', 'storefronts', 'towers', 'tiles', if GPU-compressed textures are later spent on sharpness in
// the app (the plan's GEOMEM-2, policy ii). Adding a kind here only puts the files in the bundle: the page must also ask
// for them, which is a change to artSrc's call for that kind and to the test beside it.
export const KEEP_FULL = new Set([]);

// 'art/<kind>/<name>.<hash>.<ext>': the kind, and the folder and name without the hash, which is what a twin shares
const artKind = (p) => p.split('/')[1];
const artStem = (p) => { const cut = p.lastIndexOf('/') + 1; return p.slice(0, cut) + p.slice(cut).split('.')[0]; };

// Every art path a built page names, sorted: any quoted string that begins art/, which is build.py's own rule for the
// manifests it inlines (art_paths), so the list is what THIS page can ask for and nothing else
export function artNamed(page) {
  const set = new Set();
  for (const m of page.matchAll(/"(art\/[^"\\]+)"/g)) set.add(m[1]);
  return [...set].sort();
}

// The named files split into what the app carries and what it leaves out: a file is left out when its -half twin is named
// too and its kind keeps no full-size files
export function artTouch(named, keepFull = KEEP_FULL) {
  const stems = new Set(named.map(artStem));
  const carry = [], leave = [];
  for (const p of named) (stems.has(artStem(p) + '-half') && !keepFull.has(artKind(p)) ? leave : carry).push(p);
  return { carry, leave };
}
