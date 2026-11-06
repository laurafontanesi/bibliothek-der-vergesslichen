// One grammar topic.
//   #grammatik/<topic>          the overview: every form of the topic in tables, with a filter on the left
//   #grammatik/<topic>/<form>   one form on paper (refresher, example sentences, the card), with the
//                               part of the overview it belongs to on the left
// Planned topics show only what is planned, as counts: the names of the planned structures stay
// private.
import { LEVELS } from '../daten.js';
import { h, raw, html, hero, link, speakButton } from '../hilfe.js';
import { button as notizKnopf } from '../notizen.js';

const CASE_DE = { NOM: 'Nominativ', AKK: 'Akkusativ', DAT: 'Dativ', GEN: 'Genitiv' };
const CASE_SHORT = { NOM: 'Nom', AKK: 'Akk', DAT: 'Dat', GEN: 'Gen' };
const GEN_DE = { m: 'maskulin', f: 'feminin', n: 'neutral', pl: 'Plural' };
const CASES = ['NOM', 'AKK', 'DAT', 'GEN'];
const GENDERS = ['m', 'f', 'n', 'pl'];

// Konnektoren by meaning and by sentence form (our grouping)
const K_ROWS = [
  ['Grund', { neben: ['weil', 'da'], haupt: ['denn'], prep: ['wegen', 'aufgrund', 'infolge'] }],
  ['Gegensatz, Einschränkung', { neben: ['obwohl', 'wobei'], haupt: [], prep: ['trotz', 'entgegen'] }],
  ['Zeit', { neben: ['sobald', 'nachdem', 'bevor', 'solange', 'während', 'seit', 'seitdem'], haupt: ['seitdem'], prep: ['während', 'seit', 'vor'] }],
  ['Zweck, Folge', { neben: ['damit', 'sodass'], haupt: [], prep: [] }],
  ['Bedingung, Art und Weise', { neben: ['falls', 'indem'], haupt: [], prep: [] }],
  ['Quelle, Zusatz', { neben: [], haupt: [], prep: ['laut', 'neben'] }],
];
const K_CASE = { wegen: 'Gen', aufgrund: 'Gen', infolge: 'Gen', trotz: 'Gen', entgegen: 'Dat', während: 'Gen', seit: 'Dat', vor: 'Dat', laut: 'Gen/Dat', neben: 'Dat/Akk' };
const K_COLS = [['neben', 'Nebensatz', 'Verb am Ende'], ['haupt', 'Hauptsatz', 'Verb auf Position 2'], ['prep', 'Präposition', '+ Nomen im Kasus']];

const DETS = [['der', 'der', 'bestimmter Artikel'], ['dieser', 'dieser', 'wie der'], ['ein', 'ein', 'unbestimmter Artikel'],
  ['kein', 'kein', 'wie ein, mit Plural'], ['mein', 'mein', 'Possessivartikel, wie kein'], ['ohne', 'ohne Artikel', 'das Adjektiv zeigt das Signal']];
const KIND_DE = { pron: 'Personalpronomen', frage: 'Fragewort', indef: 'Indefinitpronomen', prep: 'Präpositionen', datv: 'Verben mit Dativ' };
const PERSON = { sie_pl: 'sie (Plural)' };

const INTRO = {
  dekl: 'Die Endung des Adjektivs hängt vom Artikelwort ab. Jede Tabelle zeigt ein Artikelwort in allen vier Fällen und für alle Geschlechter, mit einem Beispiel aus deinen Karten. Ein Feld öffnet die Regel und die Sätze dazu.',
  kasus: 'Welcher Fall nach welchem Wort: Personalpronomen, das Fragewort wer, Indefinitpronomen, Präpositionen und Verben mit Dativ.',
  prep_fixed: 'Verben, Nomen und Adjektive mit fester Präposition, nach Präposition und Fall geordnet.',
  konnektoren: 'Konnektoren verbinden zwei Gedanken. Wichtig ist nicht nur, was sie bedeuten, sondern was sie mit dem Satz machen: Nach einer Konjunktion steht das Verb am Ende. Nach einem Adverb oder nach denn bleibt es auf Position 2. Nach einer Präposition kommt kein Satz, sondern ein Nomen im richtigen Kasus.',
};

// The nine Wechselpräpositionen as pictures (our own pixel scenes, img/praep/): moving there, wohin? +
// Akkusativ, and being there, wo? + Dativ. The part with the preposition is in braces.
const WECHSEL = [
  ['in', 'in', 'Er wirft den Ball {in die Kiste}.', 'Der Ball liegt {in der Kiste}.'],
  ['an', 'an', 'Sie hängt das Bild {an die Wand}.', 'Das Bild hängt {an der Wand}.'],
  ['auf', 'auf', 'Er wirft den Ball {auf die Kiste}.', 'Der Ball liegt {auf der Kiste}.'],
  ['ueber', 'über', 'Er wirft den Ball {über den Tisch}.', 'Die Lampe hängt {über dem Tisch}.'],
  ['unter', 'unter', 'Er rollt den Ball {unter den Tisch}.', 'Der Ball liegt {unter dem Tisch}.'],
  ['vor', 'vor', 'Er rollt den Ball {vor die Kiste}.', 'Der Ball liegt {vor der Kiste}.'],
  ['hinter', 'hinter', 'Er wirft den Ball {hinter die Kiste}.', 'Der Ball liegt {hinter der Kiste}.'],
  ['neben', 'neben', 'Er rollt den Ball {neben die Kiste}.', 'Der Ball liegt {neben der Kiste}.'],
  ['zwischen', 'zwischen', 'Er legt den Ball {zwischen die Kisten}.', 'Der Ball liegt {zwischen den Kisten}.'],
];
const braces = t => raw(html(h`${t}`).replace(/\{(.+?)\}/, '<b class="hl">$1</b>'));
function wechselTafel() {
  return h`<section class="card wtafel" aria-label="Die neun Wechselpräpositionen in Bildern">
    <div class="wtr whead"><span></span><span><b>wohin?</b> + Akkusativ<br><span class="lab">Bewegung zu einem Ziel</span></span><span><b>wo?</b> + Dativ<br><span class="lab">schon da, ohne Bewegung</span></span></div>
    ${WECHSEL.map(([k, p, a, d]) => h`<div class="wtr">
      <span class="vt wprep">${p}</span>
      <figure><img src="img/praep/${k}-wohin.svg" alt="" width="160" height="120"><figcaption class="de">${braces(a)} ${speakButton(a.replace(/[{}]/g, ''), 'anhören', 'say dark')}</figcaption></figure>
      <figure><img src="img/praep/${k}-wo.svg" alt="" width="160" height="120"><figcaption class="de">${braces(d)} ${speakButton(d.replace(/[{}]/g, ''), 'anhören', 'say dark')}</figcaption></figure>
    </div>`)}
  </section>`;
}

// The sentence with the answer marked (blanks are [start, end] in the German sentence)
function marked(c) {
  let out = '', pos = 0;
  for (const [a, b] of c.blanks || []) { out += html(h`${c.de.slice(pos, a)}<span class="hl">${c.de.slice(a, b)}</span>`); pos = b; }
  return raw(out + html(h`${c.de.slice(pos)}`));
}
const lowerFirst = s => s ? s[0].toLowerCase() + s.slice(1) : s;
const answerOf = c => {
  const s = (c.sentences || []).find(x => x.use !== false) || (c.sentences || [])[0];
  if (!s) return '';
  return s.answer || (s.blanks || []).map(([a, b]) => s.de.slice(a, b)).join(' … ');
};

// filters: data-f-<name>="value" on sections and links; a section whose value is not chosen is
// hidden, a link whose value is not chosen is dimmed
const f = (name, value) => raw(`data-f-${name}="${String(value).replace(/"/g, '')}"`);

function overview(D, t, label) {
  const a = (topicCell, text, cls = 'gcell') => {
    const lab = label.get(topicCell.id);
    return lab ? h`<a class="${cls}" href="${link.thema(t.id, lab)}" data-label="${lab}">${text}</a>` : h`<span class="${cls} none">${text}</span>`;
  };
  if (t.id === 'dekl') {
    const by = new Map(t.cells.map(c => [`${c.det}|${c.case}|${c.gender}`, c]));
    return {
      filters: [['det', 'Artikelwort', DETS.map(([id, l]) => [id, l])], ['case', 'Fall', CASES.map(c => [c, CASE_DE[c]])], ['gender', 'Geschlecht', GENDERS.map(g => [g, GEN_DE[g]])]],
      sections: DETS.map(([det, name, note]) => ({ key: det, attrs: { det }, html: h`
        <section class="gsec" ${f('det', det)}>
          <h3 class="gsec-t"><span class="de">${name}</span> <span class="lab">${note}</span></h3>
          <div class="gtable" style="--cols:4" role="table" aria-label="${name}">
            <div role="row" class="gtr ghead"><div role="columnheader"></div>${GENDERS.map(g => h`<div role="columnheader" ${f('gender', g)}>${GEN_DE[g]}</div>`)}</div>
            ${CASES.map(cs => h`<div role="row" class="gtr" ${f('case', cs)}><div role="rowheader" class="gth">${CASE_SHORT[cs]}</div>
              ${GENDERS.map(g => { const c = by.get(`${det}|${cs}|${g}`);
                return h`<div role="cell" ${f('gender', g)} ${f('case', cs)}>${c ? a(c, lowerFirst(answerOf(c))) : h`<span class="gcell none">–</span>`}</div>`; })}</div>`)}
          </div>
        </section>` })),
    };
  }
  if (t.id === 'kasus') {
    const cells = kind => t.cells.filter(c => c.kind === kind);
    const table = (kind, rowsOf, cols) => {
      const rows = [...new Set(cells(kind).map(rowsOf))];
      const by = new Map(cells(kind).map(c => [rowsOf(c) + '|' + c.case, c]));
      return h`<div class="gtable" style="--cols:${cols.length}" role="table">
        <div role="row" class="gtr ghead"><div role="columnheader"></div>${cols.map(cs => h`<div role="columnheader" ${f('case', cs)}>${CASE_DE[cs]}</div>`)}</div>
        ${rows.map(r => h`<div role="row" class="gtr"><div role="rowheader" class="gth de">${PERSON[r] || r}</div>
          ${cols.map(cs => { const c = by.get(r + '|' + cs); return h`<div role="cell" ${f('case', cs)}>${c ? a(c, lowerFirst(answerOf(c)) || r) : h`<span class="gcell none">–</span>`}</div>`; })}</div>`)}
      </div>`;
    };
    const preps = cs => [...new Map(cells('prep').filter(c => c.case === cs).map(c => [c.prep, c])).values()];
    const sec = (kind, body) => ({ key: kind, html: h`<section class="gsec" ${f('kind', kind)}><h3 class="gsec-t">${KIND_DE[kind]}</h3>${body}</section>` });
    return {
      filters: [['kind', 'Was', Object.entries(KIND_DE)], ['case', 'Fall', CASES.map(c => [c, CASE_DE[c]])]],
      sections: [
        sec('pron', table('pron', c => c.base, ['AKK', 'DAT'])),
        sec('frage', table('frage', c => c.base, CASES)),
        sec('indef', table('indef', c => c.base, ['AKK', 'DAT'])),
        sec('prep', h`<div class="gcols">${['AKK', 'DAT', 'GEN'].map(cs => h`<div ${f('case', cs)}><div class="lab" style="margin-bottom:6px">mit ${CASE_DE[cs]}</div><div class="chips">${preps(cs).map(c => a(c, c.prep, 'gcell chipcell'))}</div></div>`)}</div>`),
        sec('datv', h`<div class="chips">${cells('datv').map(c => h`<span ${f('case', c.case)}>${a(c, c.verb, 'gcell chipcell')}</span>`)}</div>`),
      ],
    };
  }
  if (t.id === 'prep_fixed') {
    const typeOf = c => { const e = D.byId.get(c.word_id); const ty = e ? e.type : ''; return ty === 'verb' ? 'verb' : ty === 'noun' ? 'noun' : 'adj'; };
    const parse = c => { const [p, cs] = c.form.split(' + '); return { p, cs }; };
    const preps = [...new Set(t.cells.map(c => parse(c).p))].sort((x, y) => t.cells.filter(c => parse(c).p === y).length - t.cells.filter(c => parse(c).p === x).length);
    return {
      filters: [['case', 'Fall', [['AKK', 'Akkusativ'], ['DAT', 'Dativ']]], ['type', 'Wortart', [['verb', 'Verben'], ['noun', 'Nomen'], ['adj', 'Adjektive']]]],
      sections: [{ key: 'all', html: h`<section class="gsec">
        <div class="gtable" style="--cols:2" role="table" aria-label="Feste Präpositionen">
          <div role="row" class="gtr ghead"><div role="columnheader"></div><div role="columnheader" ${f('case', 'AKK')}>+ Akkusativ</div><div role="columnheader" ${f('case', 'DAT')}>+ Dativ</div></div>
          ${preps.map(p => h`<div role="row" class="gtr"><div role="rowheader" class="gth de" style="font-size:18px">${p}</div>
            ${['AKK', 'DAT'].map(cs => h`<div role="cell" class="chips" ${f('case', cs)}>${t.cells.filter(c => parse(c).p === p && parse(c).cs === cs)
              .map(c => h`<span ${f('type', typeOf(c))}>${a(c, c.word, 'gcell chipcell')}</span>`)}</div>`)}</div>`)}
        </div></section>` }],
    };
  }
  if (t.id === 'konnektoren') {
    const byWord = new Map(t.cells.map(c => [c.word, c]));
    return {
      filters: [],
      sections: [{ key: 'all', html: h`<section class="gsec">
        <div role="table" aria-label="Konnektoren nach Bedeutung und Satzbau" class="ktable">
          <div role="row" class="khead"><div role="columnheader" style="padding-left:14px">Bedeutung</div>${K_COLS.map(([, x, y]) => h`<div role="columnheader">${x}<br><span style="color:var(--tx2)">${y}</span></div>`)}</div>
          ${K_ROWS.map(([lab, d]) => h`<div role="row" class="krow"><div role="rowheader" class="kmean">${lab}</div>
            ${K_COLS.map(([k, x, y]) => h`<div role="cell" class="kcell${d[k].length ? '' : ' kempty'}" data-label="${x}, ${y}">${d[k].map(w => byWord.get(w)
              ? a(byWord.get(w), h`${w}${k === 'prep' && K_CASE[w] ? h`<small>${K_CASE[w]}</small>` : ''}`, 'gcell kbtn') : '')}</div>`)}</div>`)}
        </div></section>` }],
    };
  }
  // any other topic with cards: the forms as a list
  const seen = new Set();
  return { filters: [], sections: [{ key: 'all', html: h`<section class="gsec"><div class="chips">${t.cells.filter(c => label.has(c.id) && !seen.has(label.get(c.id)) && seen.add(label.get(c.id)))
    .map(c => a(c, label.get(c.id), 'gcell chipcell'))}</div></section>` }] };
}

export function render(D, [id, cellArg]) {
  const t = D.topics.get(id);
  if (!t) return { title: 'Nicht gefunden', view: h`<div class="loading">Dieses Thema gibt es nicht. <a href="${link.grammatik()}">Zur Grammatik</a></div>` };
  const sub = h`<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><span style="display:flex;gap:4px">${t.levels.map(l => h`<span class="lv" style="background:rgba(27,21,22,0.75)">${l}</span>`)}</span>
    <span style="font-size:14px;color:var(--tx);background:rgba(27,21,22,0.75);padding:3px 8px">${t.status === 'active'
      ? h`<span class="vt" style="font-size:22px;color:var(--acc)">${t.cards.length}</span> Karten im Lernzimmer · ${t.cells.length} Formen`
      : (t.status === 'later' ? 'für später' : 'geplant') + ` · ${t.nstruct} ${t.nstruct === 1 ? 'Struktur' : 'Strukturen'}`}</span></div>`;

  if (t.status !== 'active' || !t.cards.length) {
    return { title: t.name, view: h`<nav class="path" aria-label="Pfad"><a href="${link.grammatik()}">Grammatik</a> › <span class="here">${t.name}</span></nav>
      ${hero('konnektoren', t.name, '', sub)}
      <section class="card" style="padding:20px 22px;display:flex;flex-direction:column;gap:10px;max-width:760px">
        <h2 class="sec">${t.status === 'later' ? 'Für später' : 'Geplant'}</h2>
        <p style="margin:0;color:var(--tx2);line-height:1.5">Zu diesem Thema gibt es noch keine Übungen. Im Plan stehen ${t.nstruct} ${t.nstruct === 1 ? 'Struktur' : 'Strukturen'}:</p>
        <div style="display:flex;gap:16px;flex-wrap:wrap">${LEVELS.filter(l => t.bylevel[l]).map(l => h`<span><span class="lv">${l}</span> <span class="vt" style="font-size:22px">${t.bylevel[l]}</span></span>`)}</div>
      </section>
      ${t.id === 'wechsel' ? wechselTafel() : ''}
      <div>${notizKnopf({ wo: 'grammatik', thema: t.id, label: t.name }, 'Notiz zu diesem Thema')}</div>` };
  }

  // each form of the topic (a cell of grammar.json) belongs to one card label, found by its sentences
  const cardLabel = new Map(t.cards.map(c => [c.de, c.cell]));
  const label = new Map();
  for (const c of t.cells) for (const s of c.sentences || []) if (cardLabel.has(s.de)) { label.set(c.id, cardLabel.get(s.de)); break; }
  const cards = new Map();
  for (const c of t.cards) { if (!cards.has(c.cell)) cards.set(c.cell, []); cards.get(c.cell).push(c); }
  const ov = overview(D, t, label);

  if (!cellArg || !cards.has(cellArg)) {
    // the overview
    const view = h`<nav class="path" aria-label="Pfad"><a href="${link.grammatik()}">Grammatik</a> › <span class="here">${t.name}</span></nav>
      ${hero('konnektoren', t.name, '', sub)}
      ${INTRO[t.id] ? h`<p class="de intro">${INTRO[t.id]}</p>` : ''}
      <div class="${ov.filters.length ? 'side' : ''}">
        ${ov.filters.length ? h`<aside class="filters closed" aria-label="Filter" id="gfilt">
          <button type="button" class="toggle" data-act="filt" aria-expanded="false"><span>Filter</span><span>▾</span></button>
          <div class="fbody">${ov.filters.map(([name, title, opts]) => h`<div><h3>${title}</h3><div class="chips"><button type="button" class="chip on" data-fall="${name}" aria-pressed="true">Alle</button>${opts.map(([v, l]) =>
            h`<button type="button" class="chip" data-fname="${name}" data-fval="${v}" aria-pressed="false">${l}</button>`)}</div></div>`)}
            <button type="button" class="textlink" data-act="reset" style="align-self:flex-start" hidden>Filter zurücksetzen</button>
          </div></aside>` : ''}
        <div class="gsecs${t.id === 'dekl' ? ' two' : ''}" id="gsecs">${ov.sections.map(s => s.html)}</div>
      </div>
      <div>${notizKnopf({ wo: 'grammatik', thema: t.id, label: t.name }, 'Notiz zu diesem Thema')}</div>`;
    return { title: t.name, view, mount: el => mountFilter(el) };
  }

  // one form: the part of the overview it belongs to on the left, the form on paper on the right
  const list = cards.get(cellArg);
  const own = t.cells.filter(c => label.get(c.id) === cellArg);
  const wid = own.map(c => c.word_id).find(Boolean);
  const w = wid && D.byId.get(wid);
  const mark = `data-label="${html(h`${cellArg}`)}"`;
  const sections = ov.sections.filter(s => html(s.html).includes(mark));
  const left = (sections.length ? sections : ov.sections.slice(0, 1)).map(s => html(s.html)).join('')
    .split(mark).join(mark + ' aria-current="true"');
  const view = h`<nav class="path" aria-label="Pfad"><a href="${link.grammatik()}">Grammatik</a> › <a href="${link.thema(t.id)}">${t.name}</a> › <span class="here">${cellArg}</span></nav>
    <div class="split">
      <div style="display:flex;flex-direction:column;gap:12px;min-width:0">
        <a href="${link.thema(t.id)}" style="font-size:15px">← Überblick: ${t.name}</a>
        <div class="gsecs">${raw(left)}</div>
      </div>
      <article class="paper px rulecard" id="regel">
        <header>
          <div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap"><h1 class="de" style="margin:0;font-size:${cellArg.length > 18 ? 26 : 38}px;font-weight:600">${cellArg}</h1>${w ? h`<span class="lv" style="margin-left:auto">${w.level}</span>` : ''}</div>
          <div style="font-size:14px;color:var(--ink2)">${list.length} ${list.length === 1 ? 'Karte' : 'Karten'} im Lernzimmer</div>
        </header>
        <div class="regel">${raw(list[0].regel || '')}</div>
        <section style="display:flex;flex-direction:column;gap:8px">
          <h2 class="sec">Beispiele</h2>
          ${list.map(c => h`<div class="ex">${speakButton(c.de, 'Satz anhören')}<span class="de" style="font-size:17px">${marked(c)}</span><span></span><span class="en" style="font-size:15px">${raw(c.en_html || '')}</span>${c.quelle ? h`<span></span><span class="kquelle" style="font-size:12px;color:var(--ink2)">${raw(c.quelle.replace(/<a /g, '<a target="_blank" rel="noopener" '))}</span>` : ''}</div>`)}
        </section>
        <section style="display:flex;flex-direction:column;gap:8px">
          <h2 class="sec">So sieht die Karte aus</h2>
          ${list.slice(0, 2).map(c => h`<div class="sample"><div class="de" style="font-size:16px">${c.front}</div><div style="font-size:12px;color:var(--ink2)">${c.hint} · Lösung: <b class="de" style="font-size:14px;color:var(--ink)">${c.answer}</b></div></div>`)}
        </section>
        ${w ? h`<a href="${link.wort(w.id)}" style="font-size:15px;align-self:flex-start">Zum Wort im Vokabular →</a>` : ''}
        <div>${notizKnopf({ wo: 'grammatik', thema: t.id, zelle: cellArg, label: cellArg + ' · ' + t.name }, 'Notiz zu dieser Form')}</div>
      </article>
    </div>`;
  return { title: cellArg + ' · ' + t.name, view, mount: el => {
    // on the phone the form is below its table: go straight to it
    if (window.matchMedia('(max-width: 760px)').matches) el.querySelector('#regel').scrollIntoView({ block: 'start' });
  } };
}

function mountFilter(el) {
  const chosen = {};
  const apply = () => {
    const ok = node => Object.entries(chosen).every(([n, set]) => !set.size || !node.hasAttribute('data-f-' + n) || set.has(node.getAttribute('data-f-' + n)));
    el.querySelectorAll('.gsec').forEach(s => { s.hidden = !ok(s); });
    el.querySelectorAll('#gsecs [data-f-case], #gsecs [data-f-gender], #gsecs [data-f-type]').forEach(n => n.classList.toggle('dim', !ok(n)));
    const any = Object.values(chosen).some(s => s.size);
    el.querySelectorAll('[data-fall]').forEach(b => { const on = !(chosen[b.dataset.fall] && chosen[b.dataset.fall].size);
      b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on)); });
    const r = el.querySelector('[data-act=reset]'); if (r) r.hidden = !any;
    const t = el.querySelector('.toggle span'); if (t) t.textContent = 'Filter' + (any ? ' (aktiv)' : '');
  };
  el.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.dataset.fname) {
      const set = chosen[b.dataset.fname] = chosen[b.dataset.fname] || new Set();
      set.has(b.dataset.fval) ? set.delete(b.dataset.fval) : set.add(b.dataset.fval);
      b.classList.toggle('on', set.has(b.dataset.fval)); b.setAttribute('aria-pressed', String(set.has(b.dataset.fval)));
      apply();
    } else if (b.dataset.fall) {
      if (chosen[b.dataset.fall]) chosen[b.dataset.fall].clear();
      el.querySelectorAll(`[data-fname="${b.dataset.fall}"]`).forEach(x => { x.classList.remove('on'); x.setAttribute('aria-pressed', 'false'); });
      apply();
    } else if (b.dataset.act === 'reset') {
      for (const k in chosen) chosen[k].clear();
      el.querySelectorAll('[data-fname]').forEach(x => { x.classList.remove('on'); x.setAttribute('aria-pressed', 'false'); });
      apply();
    } else if (b.dataset.act === 'filt') {
      const a = el.querySelector('#gfilt'); a.classList.toggle('closed'); b.setAttribute('aria-expanded', String(!a.classList.contains('closed')));
    }
  });
}
