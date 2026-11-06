// web/data/karten.json against words.json: every card belongs to a word that exists and has a known card type.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { data } from './daten.js';

test('cards point to words that exist', () => {
  const { D, KJ } = data();
  const missing = KJ.eintraege.filter(n => n.wort && !D.byId.has(n.wort)).map(n => `${n.typ} ${n.id} -> ${n.wort}`);
  assert.deepEqual(missing, []);
  const deutsch = KJ.eintraege.filter(n => n.typ === 'Deutsch');
  assert.ok(deutsch.every(n => D.byId.has(n.id)), 'a word card without its word');
});

test('every card key has its card type', () => {
  const { KJ } = data();
  const keys = new Set(Object.entries(KJ.typen).flatMap(([typ, l]) => l.map(c => typ + '|' + c.key)));
  const bad = KJ.eintraege.flatMap(n => n.karten.filter(k => !keys.has(n.typ + '|' + k)).map(k => `${n.id} ${k}`));
  assert.deepEqual(bad, []);
});
