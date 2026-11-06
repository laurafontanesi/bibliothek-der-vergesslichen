// Vokabular: the word list with search (both directions), filters, order, 40 at a time.
// The filters live in the address (#vokabular?niveau=B1&thema=time), so a filtered list can be linked.
import { LEVELS, TOPIC_DE, TYPE_DE, forms, meaning, allMeanings, norm } from '../daten.js';
import { h, raw, html, hero, seg, link } from '../hilfe.js';

const TYPES = [['verb', 'Verben'], ['noun', 'Nomen'], ['adj/adv', 'Adjektive, Adverbien'], ['prep/conj', 'Präpositionen, Konjunktionen'],
  ['construction', 'Konstruktionen'], ['expression', 'Ausdrücke']];
// verbs only: the conjugation, and whether a prefix comes off
const KONJ = [['regular', 'regelmäßig'], ['irregular', 'unregelmäßig'], ['mixed', 'gemischt']];
const PREFIX = [['sep', 'trennbar'], ['insep', 'untrennbar']];
// the DWDS frequency class (0 rare to 6 very frequent), in four groups
const FREQ = [['5', 'sehr häufig'], ['4', 'häufig'], ['3', 'mittel'], ['2', 'selten']];
const freqOf = e => { const f = e.dwds && e.dwds.freq; return f === undefined || f === null ? '' : f >= 5 ? '5' : f <= 2 ? '2' : String(f); };
const prefixOf = e => e.type !== 'verb' || !e.prefix ? '' : e.is_separable ? 'sep' : 'insep';
const SORTS = [['az', 'A bis Z'], ['za', 'Z bis A'], ['neu', 'neueste zuerst'], ['alt', 'älteste zuerst'], ['oft', 'häufigste zuerst']];
const STEP = 40;

function fromQuery(q) {
  const list = k => (q.get(k) || '').split(',').filter(Boolean);
  return { q: q.get('q') || '', dir: q.get('richtung') === 'en' ? 'en' : 'de', lv: list('niveau'), ty: list('art'),
    topic: q.get('thema') || null, konj: list('konjugation'), pre: list('praefix'), freq: list('haeufigkeit'), fam: q.has('familie'),
    letter: q.get('buchstabe') || null, sort: q.get('ordnung') || 'az', shown: STEP, filt: false };
}
function toQuery(s) {
  const o = {};
  if (s.q) o.q = s.q;
  if (s.dir === 'en') o.richtung = 'en';
  if (s.lv.length) o.niveau = s.lv.join(',');
  if (s.ty.length) o.art = s.ty.join(',');
  if (s.topic) o.thema = s.topic;
  if (s.konj.length) o.konjugation = s.konj.join(',');
  if (s.pre.length) o.praefix = s.pre.join(',');
  if (s.freq.length) o.haeufigkeit = s.freq.join(',');
  if (s.fam) o.familie = '';
  if (s.letter) o.buchstabe = s.letter;
  if (s.sort !== 'az') o.ordnung = s.sort;
  return new URLSearchParams(o).toString().replace(/=(&|$)/g, '$1');
}

let fams = new Set();
function matches(e, s, skip, q, re) {
  return (skip === 'lv' || !s.lv.length || s.lv.includes(e.level)) &&
    (skip === 'ty' || !s.ty.length || s.ty.includes(e.type)) &&
    (skip === 'topic' || !s.topic || (e.topics || []).includes(s.topic)) &&
    (!s.konj.length || s.konj.includes(e.verb_class)) &&
    (!s.pre.length || s.pre.includes(prefixOf(e))) &&
    (!s.freq.length || s.freq.includes(freqOf(e))) &&
    (!s.fam || fams.has(e.family_root)) &&
    (skip === 'letter' || !s.letter || e._key[0] === s.letter) &&
    (!q || (s.dir === 'de' ? e._key.includes(q) : norm(allMeanings(e)).split(/[·,;()/]/).some(m => re.test(m.trim()))));
}

export function render(D, args, query) {
  const s = fromQuery(query);
  const view = h`
  ${hero('vokabular', 'Vokabular', '', h`<div style="display:flex;flex-direction:column;gap:6px;max-width:460px">
      <div class="segs" role="group" aria-label="Suchrichtung" id="dirs"></div>
      <label for="vq" class="vh">Im Vokabular suchen</label>
      <input id="vq" class="search" type="search" autocomplete="off" value="${s.q}">
    </div>`)}
  <div class="side">
    <aside class="filters closed" aria-label="Filter" id="filters"></aside>
    <section style="display:flex;flex-direction:column;gap:12px;min-width:0">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap">
        <div id="count"></div>
        <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap"><span class="lab">Ordnen:</span><span class="chips" id="sorts"></span></div>
      </div>
      <div class="card wl" id="list"></div>
      <button type="button" class="more" id="more" hidden></button>
    </section>
  </div>`;
  return { title: 'Vokabular', view, mount: el => mount(el, D, s) };
}

function mount(el, D, s) {
  fams = new Set(D.families.map(([r]) => r));
  const $ = id => el.querySelector('#' + id);
  const topicNames = Object.keys(TOPIC_DE);
  const draw = () => {
    history.replaceState(null, '', '#vokabular' + (toQuery(s) ? '?' + toQuery(s) : ''));
    const q = norm(s.q.trim());
    const re = new RegExp('(^|\\W)' + q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    let list = D.W.filter(e => matches(e, s, null, q, re));
    const byKey = (a, b) => a._key.localeCompare(b._key);
    if (s.sort === 'az') list.sort(byKey);
    if (s.sort === 'za') list.sort((a, b) => -byKey(a, b));
    if (s.sort === 'neu') list.sort((a, b) => (b.added || '').localeCompare(a.added || '') || byKey(a, b));
    if (s.sort === 'oft') list.sort((a, b) => ((b.dwds && b.dwds.freq) ?? -1) - ((a.dwds && a.dwds.freq) ?? -1) || byKey(a, b));
    if (s.sort === 'alt') list.sort((a, b) => (a.added || '').localeCompare(b.added || '') || byKey(a, b));
    const forTopics = D.W.filter(e => matches(e, s, 'topic', q, re)), tcount = {};
    forTopics.forEach(e => (e.topics || []).forEach(t => { tcount[t] = (tcount[t] || 0) + 1; }));
    const lset = new Set(D.W.filter(e => matches(e, s, 'letter', q, re)).map(e => e._key[0]));
    const any = s.lv.length || s.ty.length || s.topic || s.konj.length || s.pre.length || s.freq.length || s.fam || s.letter;
    const showAll = s.dir === 'en' && q;

    $('dirs').innerHTML = html(h`${seg([['de', 'Deutsch → Englisch'], ['en', 'Englisch → Deutsch']], s.dir, 'dir')}`);
    $('vq').placeholder = s.dir === 'de' ? 'Deutsches Wort, z. B. Aufzug' : 'Englisches Wort, z. B. lift';
    const all = key => h`<button type="button" class="chip${s[key].length ? '' : ' on'}" data-clear="${key}" aria-pressed="${String(!s[key].length)}">Alle</button>`;
    const f = $('filters');
    f.classList.toggle('closed', !s.filt);
    f.innerHTML = html(h`
      <button type="button" class="toggle" data-act="filt" aria-expanded="${String(s.filt)}"><span>Filter${any ? ' (aktiv)' : ''}</span><span>${s.filt ? '▴' : '▾'}</span></button>
      <div class="fbody">
        <div><h3>Niveau</h3><div class="chips">${all('lv')}${LEVELS.map(l => h`<button type="button" class="chip lvchip${s.lv.includes(l) ? ' on' : ''}" data-lv="${l}" aria-pressed="${String(s.lv.includes(l))}">${l}</button>`)}</div></div>
        <div><h3>Wortart</h3><div class="chips">${all('ty')}${TYPES.map(([id, label]) => h`<button type="button" class="chip${s.ty.includes(id) ? ' on' : ''}" data-ty="${id}" aria-pressed="${String(s.ty.includes(id))}">${label}</button>`)}</div></div>
        <div><h3>Verben</h3>
          <div class="chips">${all('konj')}${KONJ.map(([id, label]) => h`<button type="button" class="chip${s.konj.includes(id) ? ' on' : ''}" data-multi="konj" data-val="${id}" aria-pressed="${String(s.konj.includes(id))}">${label}</button>`)}</div>
          <div class="chips" style="margin-top:6px">${all('pre')}${PREFIX.map(([id, label]) => h`<button type="button" class="chip${s.pre.includes(id) ? ' on' : ''}" data-multi="pre" data-val="${id}" aria-pressed="${String(s.pre.includes(id))}">${label}</button>`)}</div></div>
        <div><h3>Häufigkeit <span class="lab" style="font-weight:400">laut DWDS</span></h3><div class="chips">${all('freq')}${FREQ.map(([id, label]) =>
          h`<button type="button" class="chip${s.freq.includes(id) ? ' on' : ''}" data-multi="freq" data-val="${id}" aria-pressed="${String(s.freq.includes(id))}">${label}</button>`)}</div></div>
        <div>
          <label class="check"><input type="checkbox" data-flag="fam" ${raw(s.fam ? 'checked' : '')}>in einer Wortfamilie</label>
        </div>
        <div><h3><label for="thema">Thema</label></h3>
          <select id="thema" class="select">
            <option value="">Alle Themen (${forTopics.length})</option>
            ${topicNames.filter(t => tcount[t] || s.topic === t).sort((a, b) => (tcount[b] || 0) - (tcount[a] || 0))
              .map(t => h`<option value="${t}" ${raw(s.topic === t ? 'selected' : '')}>${TOPIC_DE[t]} (${tcount[t] || 0})</option>`)}
          </select></div>
        <div><h3>Buchstabe</h3><div class="letters"><button type="button" class="${s.letter ? '' : 'on'}" data-clear="letter" aria-pressed="${String(!s.letter)}" style="grid-column:span 2;font-family:'Roboto Condensed',sans-serif;font-size:14px">Alle</button>${'abcdefghijklmnopqrstuvwxyz'.split('').map(c =>
          h`<button type="button" class="${s.letter === c ? 'on' : ''}" data-letter="${c}" aria-pressed="${String(s.letter === c)}" ${raw(!lset.has(c) && s.letter !== c ? 'disabled' : '')}>${c.toUpperCase()}</button>`)}</div></div>
        ${any ? h`<button type="button" class="textlink" data-act="reset" style="align-self:flex-start">Alle Filter zurücksetzen</button>` : ''}
      </div>`);
    $('count').innerHTML = html(h`<span class="vt" style="font-size:32px">${list.length}</span> <span style="font-size:15px;color:var(--tx2)">${list.length === 1 ? 'Wort' : 'Wörter'}</span>`);
    $('sorts').innerHTML = html(h`${SORTS.map(([id, label]) => h`<button type="button" class="chip${s.sort === id ? ' on' : ''}" data-sort="${id}" aria-pressed="${String(s.sort === id)}">${label}</button>`)}`);
    $('list').innerHTML = list.length ? html(h`${list.slice(0, s.shown).map(e => {
      const m = showAll ? allMeanings(e) : meaning(e);
      return h`<a class="wrow" href="${link.wort(e.id)}">
        <span style="display:flex;flex-direction:column;gap:1px;min-width:0"><span class="de w">${e.word}</span><span class="de f">${forms(e)}</span><span class="en-d m-phone" style="font-size:15px">${m}</span></span>
        <span class="en-d r-hide" style="font-size:16px">${m}</span>
        <span class="r-hide" style="font-size:13px;color:var(--muted)">${TYPE_DE[e.type] || e.type}</span>
        <span class="lv" style="justify-self:end">${e.level}</span></a>`; })}`)
      : '<div style="padding:24px 0;color:var(--muted);font-size:15px">Keine Wörter mit diesen Filtern.</div>';
    const rest = list.length - s.shown;
    $('more').hidden = rest <= 0;
    $('more').textContent = `Weitere ${Math.min(STEP, rest)} zeigen (von ${rest})`;
  };
  const toggle = (key, v) => { s[key] = s[key].includes(v) ? s[key].filter(x => x !== v) : s[key].concat([v]); s.shown = STEP; draw(); };
  el.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    const d = b.dataset;
    if (d.dir) { s.dir = d.dir; s.shown = STEP; }
    else if (d.clear) { s[d.clear] = d.clear === 'letter' ? null : []; s.shown = STEP; }
    else if (d.lv) return toggle('lv', d.lv);
    else if (d.ty) return toggle('ty', d.ty);
    else if (d.letter) { s.letter = s.letter === d.letter ? null : d.letter; s.shown = STEP; }
    else if (d.sort) s.sort = d.sort;
    else if (d.act === 'filt') s.filt = !s.filt;
    else if (d.multi) return toggle(d.multi, d.val);
    else if (d.act === 'reset') Object.assign(s, { lv: [], ty: [], topic: null, konj: [], pre: [], freq: [], fam: false, letter: null, shown: STEP });
    else if (b.id === 'more') s.shown += STEP;
    else return;
    draw();
  });
  el.addEventListener('change', e => {
    if (e.target.id === 'thema') { s.topic = e.target.value || null; s.shown = STEP; draw(); }
    if (e.target.dataset.flag) { s[e.target.dataset.flag] = e.target.checked; s.shown = STEP; draw(); }
  });
  $('vq').addEventListener('input', e => { s.q = e.target.value; s.shown = STEP; draw(); });
  draw();
}
