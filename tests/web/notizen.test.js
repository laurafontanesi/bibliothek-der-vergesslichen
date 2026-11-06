// The notes split into points: the website (web/js/daten.js notes) must give the same points as the
// cards (vocab_builder/karten/text.py notiz). The smoke test writes Python's points for every word to a file and
// passes its path in NOTES_PY; run alone, this test is skipped.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { notes } from '../../web/js/daten.js';
import { data } from './daten.js';

test('a note splits after ";" and full stops, not inside brackets or after abbreviations', () => {
  assert.deepEqual(notes('Auszug (moving out; statement). Plural: Auszüge'), ['Auszug (moving out; statement).', 'Plural: Auszüge']);
  assert.deepEqual(notes('jmdn. etw. fragen; z. B. nach dem Weg'), ['jmdn. etw. fragen', 'z. B. nach dem Weg']);
  assert.deepEqual(notes('one. DWDS: x'), ['one.']);
  assert.deepEqual(notes(''), []);
});

test('the same points as Python on every word', { skip: !process.env.NOTES_PY && 'run by python tests/smoke.py' }, () => {
  const py = JSON.parse(fs.readFileSync(process.env.NOTES_PY, 'utf8'));
  const { D } = data(), diff = [];
  for (const w of D.W) {
    const want = (py[w.id] || []).filter(x => !x.startsWith('DWDS:'));
    if (JSON.stringify(notes(w.notes)) !== JSON.stringify(want)) diff.push(w.id);
  }
  assert.deepEqual(diff, []);
});
