// The data of the website, read from the repository as the pages read it (web/js/daten.js, ueben.js),
// for the tests in this folder.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const json = f => JSON.parse(fs.readFileSync(path.join(ROOT, f), 'utf8'));

let cache = null;
export function data() {
  if (cache) return cache;
  const W = json('web/data/words.json'), KJ = json('web/data/karten.json');
  const D = { W, byId: new Map(W.map(e => [e.id, e])) };
  const cards = [], byId = new Map();
  for (const n of KJ.eintraege) {
    if (n.typ === 'Deutsch') byId.set(n.id, n);
    for (const key of n.karten) cards.push({ n, key });
  }
  cache = { D, K: { cards, byId }, KJ };
  return cache;
}
export const card = (id, key) => data().K.cards.find(c => c.n.id === id && c.key === key);
