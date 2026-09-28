// Raises the build number every store upload needs (TestFlight and Play refuse a number they have seen): the iOS target's
// CURRENT_PROJECT_VERSION (both configurations) and Android's versionCode, to one past the higher of the two, so the two
// stores' numbers stay the same. The marketing version (1.0) is left alone. usage: npm run bump
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const pbx = resolve(here, '../ios/App/App.xcodeproj/project.pbxproj');
const gradle = resolve(here, '../android/app/build.gradle');
let p = readFileSync(pbx, 'utf8'), g = readFileSync(gradle, 'utf8');
const ios = [...p.matchAll(/CURRENT_PROJECT_VERSION = (\d+);/g)].map((m) => +m[1]);
const and = (g.match(/versionCode (\d+)/) || [])[1];
if (!ios.length || and === undefined) throw new Error('build numbers not found in ' + pbx + ' or ' + gradle);
const next = Math.max(...ios, +and) + 1;
p = p.replace(/CURRENT_PROJECT_VERSION = \d+;/g, 'CURRENT_PROJECT_VERSION = ' + next + ';');
g = g.replace(/versionCode \d+/, 'versionCode ' + next);
writeFileSync(pbx, p); writeFileSync(gradle, g);
console.log('build number ' + next + ' (iOS CURRENT_PROJECT_VERSION x' + ios.length + ', Android versionCode)');
