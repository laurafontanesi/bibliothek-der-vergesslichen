// The short line under a wrong answer ("meiden ist unregelmäßig."): why the right answer is right, from rules and from what was typed. Only where a
// rule applies; otherwise the back shows the cue.
import { text } from '../pruefen.js';

const n = s => (s || '').toLowerCase().replace(/[.!?,]+$/, '').replace(/\s+/g, ' ').trim();
const bare = s => n(s).replace(/^(der|die|das|sich) /, '');
const GENUS = { der: 'maskulin', die: 'feminin', das: 'neutral' };
const PERSONS = ['ich', 'du', 'er/sie/es', 'wir', 'ihr', 'sie/Sie'];
const HABEN = ['habe', 'hast', 'hat', 'haben', 'habt', 'hatte', 'hattest', 'hatten', 'hattet', 'hätte', 'hättest', 'hätten', 'hättet'];
const SEIN = ['bin', 'bist', 'ist', 'sind', 'seid', 'war', 'warst', 'waren', 'wart', 'wäre', 'wärst', 'wären', 'wärt'];
const CASE = { Dat: 'Dativ', Akk: 'Akkusativ', Gen: 'Genitiv', Nom: 'Nominativ' };
const PREP = {
  Dativ: ['aus', 'bei', 'beim', 'mit', 'nach', 'seit', 'von', 'vom', 'zu', 'zum', 'zur', 'gegenüber'],
  Akkusativ: ['für', 'durch', 'gegen', 'ohne', 'um'],
  Genitiv: ['wegen', 'trotz', 'während', 'statt', 'anstatt', 'innerhalb', 'außerhalb'],
  Wechsel: ['an', 'am', 'ans', 'auf', 'hinter', 'in', 'im', 'ins', 'neben', 'über', 'unter', 'vor', 'zwischen'],
};
const vowels = s => (s.match(/[aeiouäöü]+/g) || []).join('');

// another word of the library typed instead (sinken for senken): what it means
function otherWord(D, w, typed) {
  const t = bare(typed);
  if (!t) return '';
  const e = (D.W || []).find(x => x.id !== (w && w.id) && bare(x.word) === t);
  if (!e) return '';
  const m = (e.definitions && e.definitions[0] && e.definitions[0].meaning) || '';
  return `${e.word} heißt „${m}“.`;
}

// the English typed belongs to another word (Bedeutung)
function otherMeaning(K, c, typed) {
  const t = n(typed).replace(/^to /, '');
  if (!t) return '';
  for (const x of K.byId.values()) if (x.id !== c.n.id && (x.alt || []).includes(t)) return `„${t}“ ist ${text(x.felder.Wort)}.`;
  return '';
}

function verbLine(w) {
  return `${w.word}, ${w.past_tense}, ${w.auxiliary === 'sein' ? 'ist' : 'hat'} ${w.past_participle}`;
}

function rowOf(rows, typed) {
  const t = n(typed);
  return rows.findIndex(r => r.split(' / ').some(x => n(x) === t || n(x).split(' ')[0] === t));
}

function verbForm(c, w, typed, ans) {
  const k = c.key, t = n(typed), a = n(ans);
  const pfx = w.is_separable ? (w.prefix || '').replace(/-$/, '') : '';
  if (pfx && a.includes(' ') && !t.includes(' ') && t.startsWith(pfx))
    return `${w.word} ist trennbar: „${pfx}“ steht am Satzende.`;
  if (k === 'Praet' || k === 'Praes') {
    const rows = c.n.konj && c.n.konj[k === 'Praet' ? 'praet' : 'praes'];
    if (rows) {
      const j = rowOf(rows, typed), right = rowOf(rows, ans);
      if (j >= 0 && j !== right) return `„${typed.trim()}“ ist die Form für ${PERSONS[j]}.`;
    }
    if (k === 'Praet' && ['irregular', 'mixed'].includes(w.verb_class))
      return `${w.word} ist unregelmäßig: ${verbLine(w)}.`;
    if (k === 'Praes' && rows && vowels(rows[0].split(' ')[0]) !== vowels(rows[2].split(' ')[0]))
      return `${w.word} ändert im Präsens den Vokal: du ${rows[1]}, er ${rows[2]}.`;
  }
  if (k === 'Part') {
    const [ta, ...tp] = t.split(' '), [aa] = a.split(' ');
    const auxT = HABEN.includes(ta) ? 'haben' : SEIN.includes(ta) ? 'sein' : '';
    const auxA = HABEN.includes(aa) ? 'haben' : SEIN.includes(aa) ? 'sein' : '';
    if (auxT && auxA && auxT !== auxA) return `${w.word} bildet das Perfekt mit ${auxA}: ${verbLine(w)}.`;
    if (tp.length && n(tp[tp.length - 1]) !== n(w.past_participle))
      return `Partizip II von ${w.word}: ${w.past_participle}${['irregular', 'mixed'].includes(w.verb_class) ? ' (unregelmäßig)' : ''}.`;
  }
  if (k === 'Refl') {
    const akk = ['mich', 'dich', 'uns', 'euch'], dat = ['mir', 'dir', 'uns', 'euch'];
    const want = w.reflexive === 'dat' ? 'Dativ' : 'Akkusativ';
    if ((want === 'Dativ' && akk.includes(t) && !dat.includes(t)) || (want === 'Akkusativ' && dat.includes(t) && !akk.includes(t)))
      return `${w.word} steht mit dem ${want}: ${ans}.`;
  }
  return '';
}

function noun(w, typed, ans) {
  const t = n(typed).split(/,\s*/), a = n(ans).split(/,\s*/), orig = ans.split(/,\s*/);
  const [ta, ...tn] = t[0].split(' '), [aa, ...an] = a[0].split(' ');
  if (GENUS[aa] && tn.join(' ') === an.join(' ') && ta !== aa) return `${orig[0].split(' ').slice(1).join(' ')} ist ${GENUS[aa]}: ${orig[0]}.`;
  if (a[1] && t[0] === a[0] && t[1] !== a[1]) return `Plural: ${orig[1]}.`;
  return '';
}

// the grammar cards
function grammar(K, c, typed, ans) {
  const f = c.n.felder, th = c.n.thema, z = text(f.Zelle || '');
  if (th === 'prep_fixed') return z.replace(/\+ (Dat|Akk|Gen)\b/, (m, x) => '+ ' + CASE[x]) + '.';
  if (th === 'konnektoren') {
    // gloss and part of speech as plain text from the build (vocab_builder/karten/web.py)
    const gloss = x => (x.konnektor && x.konnektor.gloss) || '';
    const wort = (c.n.konnektor && c.n.konnektor.wortart) || '';
    const other = [...new Set(K.cards.filter(x => x.n.thema === 'konnektoren' && n(text(x.n.felder.Zelle)) === n(typed)).map(x => gloss(x.n)))][0];
    return (other ? other + '. ' : '') + gloss(c.n) + (wort ? ' · ' + wort : '') + '.';
  }
  if (th === 'kasus') {
    const [what, kasus] = z.split(' · ');
    if (what === 'Pronomen') return kasus === 'Akkusativ' ? 'Akkusativ: das direkte Objekt (wen? was?).'
      : kasus === 'Dativ' ? 'Dativ: die Person, der man etwas gibt oder für die man etwas tut (wem?).' : `${kasus}.`;
    return `${what} steht mit dem ${kasus}.`;
  }
  if (th === 'dekl') {
    const [det, kasus, genus] = z.split(' · ');
    const DET = { der: 'bestimmter Artikel', ein: 'unbestimmter Artikel', kein: 'kein' };
    // a preposition right before the gap: the reason for the case
    const p = n(text((f.Satz || '').split(/_{3,}/)[0]).split(' ').filter(Boolean).pop() || '');
    const why = (PREP[kasus] || []).includes(p) ? `„${p}“ verlangt den ${kasus}.`
      : PREP.Wechsel.includes(p) && ['Dativ', 'Akkusativ'].includes(kasus) ? `„${p}“ mit ${kasus}: ${kasus === 'Dativ' ? 'wo?' : 'wohin?'}` : '';
    const tt = n(typed).split(' '), aa = n(ans).split(' ');
    let rest = `${kasus}, ${genus}${DET[det] ? ', ' + DET[det] : ''}: ${ans}.`;
    if (tt.length === aa.length && aa.length >= 2 && tt[0] === aa[0] && tt[1] !== aa[1]) {
      const end = (aa[1].match(/(en|em|er|es|e)$/) || [''])[0];
      if (end) rest = `${kasus}, ${genus}: nach „${ans.split(' ')[0]}“ bekommt das Adjektiv -${end}.`;
    }
    return why ? `${why} ${rest}` : rest;
  }
  return '';
}

export function warum(D, K, c, typed, ans) {
  if (!n(typed)) return '';
  const w = c.n.wort && D.byId.get(c.n.wort);
  if (c.n.typ === 'Grammatik') return grammar(K, c, typed, ans);
  if (!w) return '';
  if (c.key === 'Bedeutung') return otherMeaning(K, c, typed);
  const other = otherWord(D, w, typed);
  if (['Praes', 'Praet', 'Part', 'Refl'].includes(c.key)) return verbForm(c, w, typed, ans) || other;
  if (c.key === 'Kontrast') {
    if (other) return other;
    const stem = bare(w.word).slice(0, Math.max(3, bare(w.word).length - 3));
    if (n(typed).startsWith(stem)) return `Richtiges Wort, falsche Form.`;
    return '';
  }
  if (c.key === 'Produzieren') return (w.type === 'noun' ? noun(w, typed, ans) : '') || other;
  return other;
}
