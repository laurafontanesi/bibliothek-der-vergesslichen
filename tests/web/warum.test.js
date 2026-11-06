// The line under a wrong answer (web/js/seiten/warum.js), on real cards of web/data/karten.json. If a word
// used here is changed in words.json, the expected line may need to follow.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { warum } from '../../web/js/seiten/warum.js';
import { text, field } from '../../web/js/pruefen.js';
import { data, card } from './daten.js';

const why = (id, key, typed) => {
  const { D, K } = data(), c = card(id, key);
  assert.ok(c, `no card ${id} ${key}`);
  return warum(D, K, c, typed, text(c.n.felder[field(c)]));
};

test('verb forms', () => {
  assert.match(why('nehmen', 'Praet', 'nehmte'), /^nehmen ist unregelmäßig: nehmen, nahm, hat genommen\.$/);
  assert.equal(why('nehmen', 'Praet', 'nahmst'), '„nahmst“ ist die Form für du.');
  assert.match(why('fahren', 'Part', 'habe gefahren'), /bildet das Perfekt mit sein/);
  assert.equal(why('geben', 'Praes', 'gebt'), '„gebt“ ist die Form für ihr.');
  assert.match(why('sich-beeilen', 'Refl', 'mir'), /steht mit dem Akkusativ/);
});

test('nouns: the gender', () => {
  assert.equal(why('die-angst', 'Produzieren', 'der Angst'), 'Angst ist feminin: die Angst.');
});

test('grammar cards get a reason', () => {
  const { D, K } = data();
  for (const th of ['dekl', 'kasus', 'prep_fixed', 'konnektoren']) {
    const c = K.cards.find(x => x.n.typ === 'Grammatik' && x.n.thema === th);
    assert.ok(c, th);
    const line = warum(D, K, c, 'xyz', text(c.n.felder.Antwort));
    assert.ok(line.length > 3 && !/undefined|NaN/.test(line), `${th}: ${line}`);
  }
});

test('nothing typed, nothing said; no line breaks the page on any card', () => {
  const { D, K } = data();
  assert.equal(why('nehmen', 'Praet', '  '), '');
  for (const c of K.cards) {
    const ans = text(c.n.felder[field(c)]);
    const line = warum(D, K, c, 'xyz', ans);
    assert.equal(typeof line, 'string');
    assert.ok(!/undefined|NaN|\[object/.test(line), `${c.n.id} ${c.key}: ${line}`);
  }
});
