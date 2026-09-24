// Copies the built page (../3d-model/society-hill-towers.html, from `python3 build.py`) into www/index.html for Capacitor.
// The page is one self-contained file, so this is the whole web bundle. Run `npm run sync` after every page build.
import { copyFileSync, mkdirSync, statSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, '../../3d-model/society-hill-towers.html');
const out = resolve(here, '../www/index.html');
mkdirSync(dirname(out), { recursive: true });
copyFileSync(src, out);
console.log('www/index.html <- 3d-model/society-hill-towers.html (' + (statSync(out).size / 1e6).toFixed(2) + ' MB)');
