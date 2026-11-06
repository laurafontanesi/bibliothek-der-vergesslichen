// Checking a typed answer, without the browser: plain text of a field, and whether an answer counts.
// Kept apart from the pages so the tests (tests/web/, run by tests/smoke.py) can run it in Node.

const ENT = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };
// The text of a field from web/data/karten.json: tags removed, entities decoded, spaces collapsed. Gives
// the same as the browser's textContent on every field of karten.json.
export function text(s) {
  return String(s || '').replace(/<[^>]*>/g, '')
    .replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => e[0] === '#'
      ? String.fromCodePoint(parseInt(e[1].toLowerCase() === 'x' ? e.slice(2) : e.slice(1), e[1].toLowerCase() === 'x' ? 16 : 10))
      : ENT[e.toLowerCase()] ?? m)
    .replace(/\s+/g, ' ').trim();
}

// Case does not count, nor a full stop at the end; on Bedeutung any listed English
// meaning counts, with or without "to".
export const norm = s => text(s).normalize('NFC').toLowerCase().replace(/[.!?]+$/, '').trim();
const noTo = s => s.replace(/^to /, '');
export function right(c, typed, expected) {
  const a = norm(typed);
  if (!a) return false;
  if (a === norm(expected)) return true;
  if (c.key === 'Bedeutung') return noTo(a) === noTo(norm(expected)) || (c.n.alt || []).some(x => noTo(norm(x)) === noTo(a));
  return false;
}

// The field of a card that holds its answer (web/data/karten.json)
export function field(c) {
  if (c.n.typ === 'Grammatik') return 'Antwort';
  if (c.n.typ === 'Kollokation') return 'Kollokation';
  if (c.key === 'Bedeutung') return 'EnglischKurz';
  if (c.key === 'Produzieren') return 'Wort';
  return c.key + '_Antwort';
}
