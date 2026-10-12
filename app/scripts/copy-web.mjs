// Copies the built page (../3d-model/society-hill-towers.html, from `python3 build.py`) into www/index.html for Capacitor,
// and the generated art beside it (../3d-model/art/ into www/art/, Round 184: the page loads those images on demand by
// relative path, so the app carries them and never fetches them). Run `npm run sync` after every page build.
import { copyFileSync, cpSync, mkdirSync, readdirSync, rmSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, '../../3d-model/society-hill-towers.html');
const out = resolve(here, '../www/index.html');
mkdirSync(dirname(out), { recursive: true });
copyFileSync(src, out);
console.log('www/index.html <- 3d-model/society-hill-towers.html (' + (statSync(out).size / 1e6).toFixed(2) + ' MB)');

// the art: replaced whole, so the app holds only what this page names (the bakes prune 3d-model/art/ the same way)
const artSrc = resolve(here, '../../3d-model/art');
const artOut = resolve(here, '../www/art');
rmSync(artOut, { recursive: true, force: true });
cpSync(artSrc, artOut, { recursive: true });
let n = 0, bytes = 0;
const walk = (d) => { for (const e of readdirSync(d, { withFileTypes: true })) { const p = join(d, e.name); if (e.isDirectory()) walk(p); else { n++; bytes += statSync(p).size; } } };
walk(artOut);
console.log('www/art <- 3d-model/art (' + n + ' files, ' + (bytes / 1e6).toFixed(1) + ' MB)');
