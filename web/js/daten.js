// The data of the library: words.json, grammar.json and grammar_cards.json from web/data/,
// loaded once, with the lookups and the derived numbers the pages need.

// The levels, word types, kinds of related word and topics with their German names: the same lists
// as in Python, from schema.json (generated, see web/js/schema.js)
import { LEVELS, TOPIC_DE, TYPE_DE, KIND_DE, KIND_ORDER } from './schema.js';
export { LEVELS, TOPIC_DE, TYPE_DE, KIND_DE, KIND_ORDER };
// The grammar topics by area (our grouping)
export const AREAS = [
  ['Artikel, Nomen, Pronomen', ['dekl', 'nomen', 'pronomen', 'komparation', 'adverbien', 'nominal']],
  ['Kasus und Präpositionen', ['kasus', 'prep_fixed', 'wechsel', 'lokal', 'da_wo']],
  ['Verben', ['verben', 'modal', 'werden', 'passiv', 'konj2', 'konj1', 'lassen', 'infinitiv', 'partizip']],
  ['Satzbau', ['satzbau', 'nebensatz', 'relativ', 'zeit', 'partikeln']],
  ['Konnektoren', ['konnektoren']],
];
// a structure counts as practised when it has cards: in a topic of its own (active) or on the
// word cards (word-cards); everything else is planned (also later, writing, reading)
export const PRACTISED = s => s.status === 'active' || s.status === 'word-cards';

export function bare(word) { return (word || '').replace(/^(der|die|das|sich) /, ''); }
export function norm(s) {
  return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ß/g, 'ss');
}
export function sortkey(word) { return norm(bare(word)); }
export function level(l) { return ['B2', 'C1', 'C2'].includes(l) ? 'B2+' : l; }

// The forms shown under a word: plural of a noun, principal parts of a verb
export function forms(e) {
  if (e.type === 'noun') return e.plural || '';
  if (e.type === 'verb' && e.present_3sg && e.past_tense && e.past_participle) {
    return `${e.present_3sg}, ${e.past_tense}, ${e.auxiliary === 'sein' ? 'ist' : 'hat'} ${e.past_participle}`;
  }
  return '';
}
// A note as a list: a new point after each ";" and each full stop, both only outside brackets and
// not after an abbreviation (the same rule as the cards, vocab_builder/karten/text.py notiz; the smoke test checks that both
// give the same points on every word)
const ABBR = new Set(['jmdn', 'jmdm', 'jmds', 'jdn', 'jdm', 'jds', 'etw', 'bzw', 'usw', 'ugs', 'geh', 'vs', 'ca',
  'Akk', 'Dat', 'Gen', 'Nom', 'Pl', 'Sg', 'Präp', 'Adj', 'Adv', 'e.g', 'i.e', 'etc', 'z', 'B', 'd',
  'h', 'o', 'Ä', 'sth', 'sb', 'lit', 'approx', 'Nr', 'St', 'Dr', 'Hr', 'Fr']);
export function notes(text) {
  text = (text || '').trim();
  const parts = []; let depth = 0, cur = '';
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if ('(['.includes(ch)) depth++;
    else if (')]'.includes(ch) && depth) depth--;
    if (depth === 0 && ch === ';') { parts.push(cur); cur = ''; continue; }
    cur += ch;
    if (depth === 0 && ch === '.' && text[i + 1] === ' ') {
      const m = cur.match(/([\wäöüÄÖÜß.]+)\.$/);
      if (!(m && (ABBR.has(m[1]) || m[1].length === 1))) { parts.push(cur); cur = ''; }
    }
  }
  return parts.concat([cur]).map(x => x.trim()).filter(x => x && !x.startsWith('DWDS:'));
}

export function meaning(e) { return (e.definitions && e.definitions[0] && e.definitions[0].meaning) || ''; }
export function allMeanings(e) { return (e.definitions || []).map(d => d.meaning).join(' · '); }

async function load(name) {
  const r = await fetch(new URL('../data/' + name, import.meta.url));
  if (!r.ok) throw new Error(name + ': ' + r.status);
  return r.json();
}

export async function loadAll() {
  const [W, G, GC] = await Promise.all([load('words.json'), load('grammar.json'), load('grammar_cards.json')]);
  const byId = new Map(W.map(e => [e.id, e]));
  const byWord = new Map(W.map(e => [e.word, e]));
  for (const e of W) e._key = sortkey(e.word);

  // word families: every family_root with at least two words
  const fam = new Map();
  for (const e of W) if (e.family_root) { if (!fam.has(e.family_root)) fam.set(e.family_root, []); fam.get(e.family_root).push(e); }
  const families = [...fam.entries()].filter(([, es]) => es.length >= 2)
    .sort((a, b) => b[1].length - a[1].length || sortkey(a[0]).localeCompare(sortkey(b[0])));
  const familyIndex = new Map(families.map(([r], i) => [r, i]));

  // grammar: topics with their levels and cards
  const str = new Map(G.structures.map(s => [s.id, s]));
  const cardsBy = new Map();
  for (const c of GC) { if (!cardsBy.has(c.topic)) cardsBy.set(c.topic, []); cardsBy.get(c.topic).push(c); }
  const topics = new Map();
  for (const t of G.topics) {
    const ss = t.structures.map(id => str.get(id)).filter(Boolean);
    const bylevel = {};
    for (const s of ss) bylevel[level(s.level)] = (bylevel[level(s.level)] || 0) + 1;
    topics.set(t.id, { id: t.id, name: t.name, status: t.status, cells: t.cells, cards: (cardsBy.get(t.id) || []),
      levels: LEVELS.filter(l => bylevel[l]), bylevel, nstruct: ss.length, structures: ss });
  }
  // structures per level, practised (active or on the word cards) and planned
  const gramLevels = Object.fromEntries(LEVELS.map(l => [l, { active: 0, planned: 0 }]));
  for (const s of G.structures) gramLevels[level(s.level)][PRACTISED(s) ? 'active' : 'planned']++;

  // structures that belong to no topic: practised on the word cards, or for writing, reading, later
  const inTopic = new Set(G.topics.flatMap(t => t.structures));
  const looseLevels = Object.fromEntries(LEVELS.map(l => [l, { active: 0, planned: 0 }]));
  for (const s of G.structures) if (!inTopic.has(s.id)) looseLevels[level(s.level)][PRACTISED(s) ? 'active' : 'planned']++;

  // word -> the grammar topics it is itself part of (a connector, a fixed preposition ...)
  const wordGrammar = new Map();
  for (const t of G.topics) for (const c of t.cells) {
    if (!c.word_id) continue;
    if (!wordGrammar.has(c.word_id)) wordGrammar.set(c.word_id, new Map());
    const m = wordGrammar.get(c.word_id);
    if (!m.has(t.id)) m.set(t.id, { topic: t.id, name: t.name, cells: [] });
    const lab = c.word || c.id.split('::').pop();
    if (!m.get(t.id).cells.includes(lab)) m.get(t.id).cells.push(lab);
  }
  return { W, G, GC, byId, byWord, families, familyIndex, topics, gramLevels, looseLevels, wordGrammar };
}
