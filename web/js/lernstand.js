// The learning state: every answer per card, kept in this browser. The state of a card (FSRS: stability, difficulty, when due) is computed from its
// answers (js/fsrs.js). Answers come from Üben and from a saved Lernstand file ("Lernstand laden");
// both are merged by time, so loading again adds only what is new. Card ids: "<typ>|<entry id>|<card key>".
import { replay, dueMs, day } from './fsrs.js';

const KEY = 'gv-lernstand';
let L = null;
const cache = new Map();

function data() {
  if (L) return L;
  try { L = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (e) { L = null; }
  // a damaged entry (karten missing, null or a list) starts again empty instead of breaking the page
  if (!L || typeof L.karten !== 'object' || L.karten === null || Array.isArray(L.karten)) L = { karten: {} };
  return L;
}
// Ask the browser once to keep this site's storage even when space runs low or the site is not
// visited for a while (navigator.storage.persist; the browser decides, nothing is asked of the user).
let asked = false;
export function keep() {
  if (asked || !(navigator.storage && navigator.storage.persist)) return;
  asked = true;
  navigator.storage.persist().catch(() => {});
}
function save() {
  keep();
  try { localStorage.setItem(KEY, JSON.stringify(data())); return true; } catch (e) { return false; }
}

export const cardId = c => `${c.n.typ}|${c.n.id}|${c.key}`;
export function answers(id) { const k = data().karten; return Object.hasOwn(k, id) ? k[id] : []; }
export function state(id) {
  const a = answers(id);
  const hit = cache.get(id);
  if (hit && hit.n === a.length) return hit.st;
  const st = a.length ? replay(a) : null;
  cache.set(id, { n: a.length, st });
  return st;
}
// what the state would be after this answer, without saving it (for "Nächste Wiederholung")
export function preview(id, grade, ms = Date.now()) { return replay([...answers(id), [ms, grade]]); }

export function answer(id, grade, ms = Date.now()) {
  const k = data().karten;
  k[id] = [...answers(id), [ms, grade]];
  cache.delete(id);
  return save();                       // false when the browser could not store it (storage full, private window)
}

export function isDue(id, now = Date.now()) { const st = state(id); return !!st && dueMs(st) <= now; }
export function isNew(id) { return !answers(id).length; }
// neu, lernen (next review less than 21 days away), gefestigt (21 days or more)
export function status(id) {
  const st = state(id);
  if (!st) return 'neu';
  return st.lastGrade !== 1 && (day(dueMs(st)) - day(st.last)) >= 21 ? 'gefestigt' : 'lernen';
}

// merge answers from a file (a saved Lernstand). Only what looks right is taken:
// a card id of the website, a time in ms (after 2001), a grade from 1 to 4. Returns how many answers
// were new and whether they could be saved.
const ID = /^(Deutsch|Kollokation|Grammatik)\|[^|]+\|.+$/;
export function merge(file) {
  const k = data().karten;
  let added = 0;
  const src = (file && typeof file.karten === 'object' && file.karten) || {};
  for (const id of Object.keys(src)) {
    if (!ID.test(id) || id === '__proto__' || !Array.isArray(src[id])) continue;
    const have = new Set((Object.hasOwn(k, id) ? k[id] : []).map(x => x[0]));
    const fresh = src[id].filter(x => Array.isArray(x) && Number.isInteger(x[0]) && x[0] > 1e12 && Number.isInteger(x[1])
      && x[1] >= 1 && x[1] <= 4 && !have.has(x[0]) && have.add(x[0])).map(x => [x[0], x[1]]);
    if (!fresh.length) continue;
    k[id] = [...(Object.hasOwn(k, id) ? k[id] : []), ...fresh].sort((a, b) => a[0] - b[0]);
    added += fresh.length;
    cache.delete(id);
  }
  return { added, saved: added ? save() : true };
}
export function exportData() {
  return { quelle: 'Bibliothek der Vergesslichen', gespeichert: new Date().toISOString(), karten: data().karten };
}
export function total() { return Object.values(data().karten).reduce((n, a) => n + a.length, 0); }
