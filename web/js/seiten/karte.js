// One card of the study room, front and back. What is asked and the answer come from
// web/data/karten.json (python -m vocab_builder karten); everything about the word comes from
// words.json: the numbered meanings with the German definition, the related words in groups, the
// conjugation table of a form card, two words side by side.
import { h, raw, html, link, speakButton, freqDots, safeUrl } from '../hilfe.js';
import { notes } from '../daten.js';
import { warum } from './warum.js';
import { text, field } from '../pruefen.js';
import { KIND_DE, KIND_ORDER } from '../schema.js';

const tmp = document.createElement('template');
const GAP = /_{3,}/g;
const PERSONS = ['ich', 'du', 'er/sie/es', 'wir', 'ihr', 'sie/Sie'];
const FORM_CARDS = ['Praes', 'Praet', 'Part', 'Refl'];
const REL = KIND_ORDER.map(k => [k, KIND_DE[k]]);

// "Präteritum · 1 Wort" -> ["Präteritum", "(1 Wort)"]: the cue in small capitals, on two lines
function cueOf(hint) {
  const parts = (hint || '').split(/\s+·\s+/).map(s => s.replace(/\s+/g, ' ').trim()).filter(Boolean);
  if (parts.length > 1 && /Wort|Wörter/.test(parts[parts.length - 1])) { const last = parts.pop(); return [parts.join(' · '), `(${last})`]; }
  return [parts.join(' · '), ''];
}

// What the card asks: the cue, the word or English shown, the sentence with its gaps, the field to type
export function ask(c) {
  const f = c.n.felder;
  if (c.n.typ === 'Grammatik') return { cue: cueOf(f.Hinweis), satz: f.Satz, en: f.SatzEN, field: field(c), ganz: f.Ganz, ganzEn: f.SatzEN, quelle: f.Quelle };
  if (c.n.typ === 'Kollokation') return { cue: cueOf(f.Hinweis), prompt: h`<div class="ken gross">${f.Englisch}</div>`, field: field(c) };
  if (c.key === 'Bedeutung') return { cue: ['kurze englische Bedeutung', ''], prompt: h`<div class="kwort de">${raw(f.Wort)}</div>`, field: field(c) };
  if (c.key === 'Produzieren') {
    tmp.innerHTML = f.EnglischFrage || '';
    const cue = tmp.content.querySelector('.aus-cue');
    const cueText = cue ? cue.textContent : '';
    tmp.content.querySelectorAll('.ausfuellen').forEach(x => x.remove());
    return { cue: [cueText, ''], prompt: h`<div class="ken gross">${raw(tmp.innerHTML)}</div>`, field: field(c) };
  }
  const k = c.key;
  return { cue: cueOf(f[k + '_Hinweis']), satz: f[k + '_Frage'], en: f[k + '_GanzEN'], field: field(c), ganz: f[k + '_Ganz'], ganzEn: f[k + '_GanzEN'], quelle: f[k + '_Quelle'] };
}

// ── the front ────────────────────────────────────────────────────────────────
const INPUT = 'type="text" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" enterkeyhint="done" aria-label="Deine Antwort"';
export function front(c) {
  const q = ask(c);
  let satz = '', below = true;
  if (q.satz) {
    const n = (q.satz.match(GAP) || []).length;
    if (n === 1) { satz = q.satz.replace(GAP, `<input id="kin" class="kin inline" ${INPUT}>`); below = false; }
    else satz = q.satz.replace(GAP, '<span class="kgap">______</span>');
  }
  return html(h`<div class="kblatt px kfront">
    <div class="kcue"><div class="vt kcue-l">Bitte ausfüllen:</div>
      ${q.cue[0] ? h`<div class="kcue-a">${q.cue[0]}</div>` : ''}${q.cue[1] ? h`<div class="kcue-a">${q.cue[1]}</div>` : ''}</div>
    ${q.prompt || ''}
    ${satz ? h`<div class="ksatz de">${raw(satz)}</div>` : ''}
    ${q.en ? h`<div class="ken">${raw(q.en)}</div>` : ''}
    ${below ? raw(`<input id="kin" class="kin" ${INPUT}>`) : ''}
  </div>`);
}

// ── the back ─────────────────────────────────────────────────────────────────
function headOf(D, K, w, c) {
  if (c.n.typ === 'Kollokation') return c.n.felder.Kollokation;
  const note = K.byId.get(w.id);
  return (note && (note.felder.Stammformen || note.felder.Wort)) || w.word;
}
function headLines(D, K, w) {
  if (w.type === 'verb' && w.past_tense && w.past_participle)
    return [w.word, w.past_tense, `${w.auxiliary === 'sein' ? 'ist' : 'hat'} ${w.past_participle}`];
  const note = K.byId.get(w.id);
  return text((note && note.felder.Wort) || w.word).split(', ');
}
function meanings(w, hit) {
  return h`<ol class="kdefs">${(w.definitions || []).map((d, i) => h`<li${i === hit ? raw(' class="hit"') : ''}>
    <span class="ken-i">${d.meaning}${i === hit ? ' ✓' : ''}</span>${d.note ? h` <span class="kdnote">(${d.note})</span>` : ''}
    ${i === 0 && w.definition_de ? h`<div class="kdde"><b>DE</b>${w.definition_de}</div>` : ''}</li>`)}</ol>`;
}
// which meaning the typed answer was (Bedeutung): the first whose alternatives contain it
function hitIndex(w, typed) {
  const t = typed.toLowerCase().trim().replace(/^to /, '');
  if (!t) return -1;
  return (w.definitions || []).findIndex(d => (d.meaning || '').toLowerCase().replace(/\([^)]*\)/g, '').split(/[,;/:]/)
    .some(p => p.trim().replace(/^to /, '') === t));
}

const AUX = {
  Perfekt: { haben: ['habe', 'hast', 'hat', 'haben', 'habt', 'haben'], sein: ['bin', 'bist', 'ist', 'sind', 'seid', 'sind'] },
  Plusquamperfekt: { haben: ['hatte', 'hattest', 'hatte', 'hatten', 'hattet', 'hatten'], sein: ['war', 'warst', 'war', 'waren', 'wart', 'waren'] },
  'Konjunktiv II der Vergangenheit': { haben: ['hätte', 'hättest', 'hätte', 'hätten', 'hättet', 'hätten'], sein: ['wäre', 'wärst', 'wäre', 'wären', 'wärt', 'wären'] },
};
const PRON = { akk: ['mich', 'dich', 'sich', 'uns', 'euch', 'sich'], dat: ['mir', 'dir', 'sich', 'uns', 'euch', 'sich'] };
const SUBJ = { ich: [0], du: [1], er: [2], es: [2], man: [2], wir: [3], ihr: [4], sie: [2, 5] };

// The table of a form card (Präsens, Präteritum, Perfekt, reflexive pronoun), with the row of the sentence
function formTable(c, w, q) {
  const f = c.n.felder, k = c.key;
  const refl = w.word.startsWith('sich ');
  const pron = PRON[w.reflexive === 'dat' ? 'dat' : 'akk'];
  let label = '', rows = null;
  if (k === 'Praes' && c.n.konj) { label = 'Präsens'; rows = c.n.konj.praes; }
  if (k === 'Praet' && c.n.konj) { label = 'Präteritum'; rows = c.n.konj.praet; }
  if (k === 'Part') {
    label = Object.keys(AUX).find(x => (f.Part_Hinweis || '').startsWith(x)) || 'Perfekt';
    const aux = AUX[label][w.auxiliary === 'sein' ? 'sein' : 'haben'];
    rows = aux.map((a, i) => `${a}${refl ? ' ' + pron[i] : ''} ${w.past_participle || ''}`.trim());
  }
  if (k === 'Refl') { label = `Reflexivpronomen (${w.reflexive === 'dat' ? 'Dativ' : 'Akkusativ'})`; rows = pron; }
  if (!rows) return '';
  // the row: the first word of the answer (the finite verb, the auxiliary, the pronoun), and when
  // several persons share it, the subject of the sentence
  const first = text(f[q.field] || '').split(' ')[0].toLowerCase();
  let on = rows.map((r, i) => r.split(' / ').some(x => x.split(' ')[0].toLowerCase() === first) ? i : -1).filter(i => i >= 0);
  if (on.length > 1) {
    const words = text(q.ganz || '').toLowerCase().split(/[^a-zäöüß]+/);
    const subj = [...new Set(words.flatMap(x => SUBJ[x] || []))].filter(i => on.includes(i));
    if (subj.length) on = subj;
  }
  return h`<hr class="krule"><div class="ksec vt">${label}</div>
    <div class="ktab">${rows.map((r, i) => h`<span class="kp">${PERSONS[i]}</span><span class="kf de${on.includes(i) ? ' on' : ''}">${r}</span>`)}</div>`;
}

// a sentence with its English; the source when the sentence is not ours (Tatoeba, CC BY: named and
// linked, in a new tab so the session stays)
function example(de, en, quelle) {
  return h`<div class="kex"><div class="de">${raw(de)} ${speakButton(text(de), 'Satz anhören')}</div>${en ? h`<div class="ken-i">${raw(en)}</div>` : ''}${quelle ? h`<div class="kquelle">${raw(quelle.replace(/<a /g, '<a target="_blank" rel="noopener" '))}</div>` : ''}</div>`;
}

function related(D, w, skip) {
  const groups = REL.map(([kind, lab]) => [lab, (w.related || []).filter(r => r.kind === kind && !skip.includes(r.word))]).filter(([, rs]) => rs.length);
  const fam = w.family_root && D.families.find(([r]) => r === w.family_root);
  if (!groups.length && !fam) return '';
  return h`<hr class="krule"><div class="ksec vt">Verwandte Wörter</div><div class="krel">
    ${groups.map(([lab, rs]) => h`<div class="urelz"><span class="klab">${lab}</span><span class="kwords">${rs.map(r => {
      const t = D.byWord.get(r.word);
      return t ? h`<a class="de" href="${link.wort(t.id)}" target="_blank" rel="noopener">${r.word}</a>` : h`<span class="de">${r.word}</span>`; })}</span></div>`)}
    ${fam ? h`<div class="urelz"><span class="klab">Wortfamilie</span><span class="kwords"><a class="de" href="${link.familie(fam[0])}" target="_blank" rel="noopener">${fam[0]}</a> <span class="kall">(${fam[1].length} Wörter)</span></span></div>` : ''}
  </div>`;
}

function dwds(w, label) {
  if (!w.dwds || !w.dwds.url) return '';
  const f = w.dwds.freq;
  return h`<span class="knw"><a href="${safeUrl(w.dwds.url)}" target="_blank" rel="noopener">${label} ↗</a>${f !== undefined && f !== null ? h`<span class="kfreq" title="Häufigkeitsklasse ${f} von 6 (DWDS)">${freqDots(f)}</span>` : ''}</span>`;
}

function entry(D, K, w, c, opts) {
  return h`<div class="kentry">
    <div class="ukopf"><span class="de ktitel">${raw(headOf(D, K, w, c))} ${speakButton(text(headOf(D, K, w, c)), 'anhören')}</span><span class="klv">${w.level || ''}</span></div>
    ${opts.meanings ? h`<hr class="krule">${meanings(w, opts.hit)}` : ''}
  </div>`;
}

// The back: your answer on the dark, then one sheet. Returns the html and the text read aloud first.
export function back(D, K, c, typed, ok) {
  const q = ask(c), f = c.n.felder;
  const expected = text(f[q.field] || '');
  const why = ok ? '' : warum(D, K, c, typed, expected);
  const verdict = ok
    ? h`<div class="kurteil"><span class="mono kok">✓ ${typed}</span></div>`
    : h`<div class="kurteil"><div><span class="mono kbad">${typed || '…'}</span> <span class="kpfeil">→</span> <span class="mono kok">${expected}</span></div>
        ${why ? h`<div class="kwarum">${why}</div>` : q.cue[0] ? h`<div class="kwarum">${q.cue.filter(Boolean).join(' ')}</div>` : ''}</div>`;
  const w = c.n.wort && D.byId.get(c.n.wort);
  const partner = c.key === 'Kontrast' && c.n.partner && D.byId.get(c.n.partner);
  const isForm = FORM_CARDS.includes(c.key);
  let sheet = [], say = '';

  if (partner) {
    // Welches Wort passt?: the two words side by side, principal parts one per line, meanings only
    const col = x => h`<div class="kcol"><div class="ukopf"><span class="de ktitel klines">${headLines(D, K, x).map(l => h`<span>${l}</span>`)}</span><span class="klv">${x.level || ''}</span></div>${meanings(x, -1)}</div>`;
    sheet.push(h`<div class="kcols">${col(w)}${col(partner)}</div>`);
    say = w.word;
  } else if (w && c.n.typ === 'Kollokation') {
    // a collocation: its own English, then a line to the word it belongs to
    sheet.push(h`<div class="kentry"><div class="ukopf"><span class="de ktitel">${f.Kollokation} ${speakButton(f.Kollokation, 'anhören')}</span><span class="klv">${w.level || ''}</span></div>
      <hr class="krule"><ol class="kdefs"><li><span class="ken-i">${f.Englisch}</span></li></ol>
      <div class="kall">zu <a class="de" href="${link.wort(w.id)}" target="_blank" rel="noopener">${w.word}</a></div></div>`);
    say = f.Kollokation;
  } else if (w) {
    sheet.push(entry(D, K, w, c, { meanings: !isForm, hit: ok && c.key === 'Bedeutung' ? hitIndex(w, typed) : -1 }));
    say = text(headOf(D, K, w, c));
    if (isForm) sheet.push(formTable(c, w, q));
  }
  if (c.n.typ === 'Grammatik' && f.Regel) sheet.push(h`<hr class="krule"><div class="ksec vt">Regel</div><div class="regel">${raw(f.Regel)}</div>`);

  // the note: of the collocation, else of the word
  const ns = c.n.typ === 'Kollokation' ? (f.Notiz ? [text(f.Notiz)] : []) : (w && !partner ? notes(w.notes) : []);
  if (ns.length) sheet.push(h`<hr class="krule"><div class="knotiz"><b>Notiz</b>${ns.length === 1 ? h` ${ns[0]}` : h`<ul>${ns.map(n => h`<li>${n}</li>`)}</ul>`}</div>`);

  // the examples: the card's own sentence first, with the solution marked; then the word's examples
  const exs = [];
  if (q.ganz) exs.push(example(q.ganz, q.ganzEn, q.quelle));
  if (c.n.typ === 'Kollokation' && f.Beispiel) exs.push(example(f.Beispiel, f.BeispielEN));
  if (w && !partner && !isForm && c.n.typ !== 'Kollokation') {
    const own = text(q.ganz || '');
    for (const x of (w.examples || [])) if (text(x.de) !== own) exs.push(example(html(h`${x.de}`), html(h`${x.en || ''}`)));
  }
  if (exs.length) sheet.push(h`<hr class="krule"><div class="ksec vt">Beispiele</div>${exs}`);
  if (q.ganz) say = text(q.ganz);

  if (w && !partner) sheet.push(related(D, w, []));

  // the links: the library (in a new tab, so the session stays), DWDS with the frequency dots
  const links = [];
  if (c.n.typ === 'Grammatik') links.push(h`<span class="knw"><a href="${link.thema(c.n.thema)}" target="_blank" rel="noopener">Grammatik: ${f.Thema} ↗</a></span>`);
  if (w) links.push(h`<span class="knw"><a href="${link.wort(w.id)}" target="_blank" rel="noopener">${partner ? 'Kontrast' : 'In der Bibliothek'} ↗</a></span>`);
  if (partner) { links.push(dwds(w, 'DWDS: ' + w.word), dwds(partner, 'DWDS: ' + partner.word)); }
  else if (w) links.push(dwds(w, 'DWDS'));
  sheet.push(h`<hr class="krule"><div class="klinks">${links}</div>`);

  return { html: html(h`${verdict}<div class="kblatt px kback">${sheet}</div>`), say };
}
