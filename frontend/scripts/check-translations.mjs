// Checks that gu.json and hi.json have the same keys as en.json.
// Runs automatically before "npm run build". Run by hand: node scripts/check-translations.mjs
import { readFileSync } from 'node:fs';

const load = (lang) => JSON.parse(readFileSync(new URL(`../src/i18n/${lang}.json`, import.meta.url), 'utf8'));

function keys(obj, prefix = '') {
  return Object.entries(obj).flatMap(([k, v]) =>
    v && typeof v === 'object' ? keys(v, `${prefix}${k}.`) : [`${prefix}${k}`],
  );
}

const english = new Set(keys(load('en')));
let problems = 0;
for (const lang of ['gu', 'hi']) {
  const other = new Set(keys(load(lang)));
  for (const key of english) if (!other.has(key)) { console.log(`${lang}.json is missing: ${key}`); problems++; }
  for (const key of other) if (!english.has(key)) { console.log(`${lang}.json has an extra key not in en.json: ${key}`); problems++; }
}
if (problems) {
  console.log(`\n${problems} translation problem(s) found.`);
  process.exit(1);
}
console.log('Translations OK: en, gu and hi have the same keys.');
