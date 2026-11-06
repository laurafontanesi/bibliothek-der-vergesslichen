// The learning state in the browser (web/js/lernstand.js), with a stand-in for localStorage.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { data } from './daten.js';

const store = new Map();
let full = false;
globalThis.localStorage = {
  getItem: k => store.has(k) ? store.get(k) : null,
  setItem: (k, v) => { if (full) throw new Error('QuotaExceededError'); store.set(k, String(v)); },
};
const LS = await import('../../web/js/lernstand.js');
const T = Date.UTC(2030, 10, 4, 9);
const ID = 'Deutsch|nehmen|Praet';

test('an answer is kept and gives a state', () => {
  assert.ok(LS.isNew(ID));
  assert.equal(LS.status(ID), 'neu');
  assert.equal(LS.answer(ID, 3, T), true);
  assert.deepEqual(LS.answers(ID), [[T, 3]]);
  assert.ok(!LS.isNew(ID) && LS.state(ID).s > 0);
  assert.equal(LS.status(ID), 'lernen');
  assert.ok(JSON.parse(store.get('gv-lernstand')).karten[ID]);
});

test('merge takes only what looks right', () => {
  const r = LS.merge({ karten: {
    'Deutsch|geben|Praes': [[T, 3], [T + 1000, 4, 'extra'], [T + 2000, 2], [T, 3]],
    'Grammatik|x|Grammatik': [[T, 0], [T, 5], [1.5e12 + 0.5, 3], [999, 3], ['1', 3], 'x', [T, 3.5]],
    'Kollokation|y': [[T, 3]],
    'Fremd|z|k': [[T, 3]],
    '__proto__': [[T, 3]],
    'Deutsch|a|b': 'not a list',
  } });
  assert.equal(r.added, 3);
  assert.equal(r.saved, true);
  assert.deepEqual(LS.answers('Deutsch|geben|Praes'), [[T, 3], [T + 1000, 4], [T + 2000, 2]]);
  assert.deepEqual(LS.answers('Grammatik|x|Grammatik'), []);
  assert.equal(LS.answers('Fremd|z|k').length, 0);
  assert.equal(Object.getPrototypeOf(LS.exportData().karten), Object.prototype);
});

test('merging the same file again adds nothing', () => {
  assert.equal(LS.merge(LS.exportData()).added, 0);
  assert.equal(LS.merge(null).added, 0);
  assert.equal(LS.merge({ karten: 'x' }).added, 0);
});

test('every card id of the website is accepted by merge', () => {
  const { K } = data();
  const ids = K.cards.map(c => LS.cardId(c));
  assert.equal(new Set(ids).size, ids.length, 'card ids are unique');
  const file = { karten: Object.fromEntries(ids.map(id => [id, [[T + 5000, 3]]])) };
  assert.equal(LS.merge(file).added, ids.length);
});

test('a full storage is reported, not hidden', () => {
  full = true;
  assert.equal(LS.answer(ID, 3, T + D()), false);
  assert.equal(LS.merge({ karten: { 'Deutsch|neu|Praet': [[T, 3]] } }).saved, false);
  full = false;
});
function D() { return 86400000; }
