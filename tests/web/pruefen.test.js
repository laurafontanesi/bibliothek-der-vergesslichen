// Checking a typed answer (web/js/pruefen.js), and every card of web/data/karten.json against it.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { text, norm, right, field } from '../../web/js/pruefen.js';
import { data } from './daten.js';

test('text: tags removed, entities decoded, spaces collapsed', () => {
  assert.equal(text('<b>der</b>  <i>Tisch</i>'), 'der Tisch');
  assert.equal(text('a&nbsp;b &amp; c &gt; d &#246; &#xFC;'), 'a b & c > d ö ü');
  assert.equal(text('<span class="x">\n ich  </span>'), 'ich');
  assert.equal(text('&unknown;'), '&unknown;');
  assert.equal(text(null), '');
});

test('case and a final full stop do not count', () => {
  const c = { n: { typ: 'Deutsch' }, key: 'Praet' };
  assert.ok(right(c, 'Nahm', 'nahm'));
  assert.ok(right(c, ' nahm. ', '<b>nahm</b>'));
  assert.ok(!right(c, 'nahmen', 'nahm'));
  assert.ok(!right(c, '', 'nahm'));
  assert.ok(!right(c, '   ', ''));
});

test('Bedeutung: with or without "to", and every listed meaning', () => {
  const c = { n: { typ: 'Deutsch', alt: ['take', 'grab'] }, key: 'Bedeutung' };
  assert.ok(right(c, 'take', 'to take'));
  assert.ok(right(c, 'to grab', 'to take'));
  assert.ok(right(c, 'Grab', 'to take'));
  assert.ok(!right(c, 'give', 'to take'));
  // only on Bedeutung
  assert.ok(!right({ n: { typ: 'Deutsch', alt: ['take'] }, key: 'Produzieren' }, 'take', 'nehmen'));
});

test('umlauts typed as one or two code points count the same', () => {
  const c = { n: { typ: 'Deutsch' }, key: 'Produzieren' };
  assert.ok(right(c, 'die Ängste', 'die Ängste'));
});

test('every card has an answer, and typing it counts as right', () => {
  const { K } = data();
  const empty = [], wrong = [];
  for (const c of K.cards) {
    const exp = c.n.felder[field(c)];
    if (!text(exp)) { empty.push(`${c.n.id} ${c.key}`); continue; }
    if (!right(c, text(exp), exp)) wrong.push(`${c.n.id} ${c.key}`);
    if (c.key === 'Bedeutung') for (const a of c.n.alt || []) if (!right(c, a, exp)) wrong.push(`${c.n.id} alt "${a}"`);
  }
  assert.deepEqual(empty, [], 'cards without an answer');
  assert.deepEqual(wrong, [], 'answers that would not count');
  assert.ok(K.cards.length > 4000);
});

test('norm', () => { assert.equal(norm('<b>Ist</b> gefahren!'), 'ist gefahren'); });
