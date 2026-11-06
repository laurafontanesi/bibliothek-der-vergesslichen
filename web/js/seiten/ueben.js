// Üben (#ueben): the cards of words, collocations and grammar. What is asked comes
// from web/data/karten.json (python -m vocab_builder karten); the card itself is drawn in
// js/seiten/karte.js. The answers are kept in this browser (js/lernstand.js), with the last choice
// of cards and the voice.
import { h, html, raw, link, seg, speak, voices, setVoice, chosenVoice } from '../hilfe.js';
import { LEVELS } from '../daten.js';
import { button as notizKnopf, RICHTIG } from '../notizen.js';
import { front, back, ask } from './karte.js';
import { text, right } from '../pruefen.js';
import * as LS from '../lernstand.js';
import { dueDays, dueMs } from '../fsrs.js';

// ── the data ────────────────────────────────────────────────────────────────
let K = null;
async function load() {
  if (K) return K;
  const r = await fetch(new URL('../../data/karten.json', import.meta.url));
  if (!r.ok) throw new Error('karten.json: ' + r.status);
  const data = await r.json();
  const tpl = {};
  for (const [typ, list] of Object.entries(data.typen)) for (const c of list) tpl[typ + '|' + c.key] = c;
  const cards = [], byId = new Map();
  for (const n of data.eintraege) {
    if (n.typ === 'Deutsch') byId.set(n.id, n);
    for (const key of n.karten) cards.push({ n, key, t: tpl[n.typ + '|' + key] });
  }
  K = { cards, byId };
  return K;
}

// What to practise: one group per kind of card (only the groups that have cards are shown)
const VERBFORMEN = ['Praes', 'Praet', 'Part', 'Refl'];
function groupOf(c) {
  if (c.n.typ === 'Grammatik') return 'g:' + c.n.thema;
  if (c.n.typ === 'Kollokation') return 'kollokation';
  if (VERBFORMEN.includes(c.key)) return 'verbformen';
  return { Bedeutung: 'bedeutung', Produzieren: 'produzieren', Kontrast: 'kontrast' }[c.key] || c.key.toLowerCase();
}
const GROUP_NAMES = { bedeutung: 'Bedeutung (Deutsch → Englisch)', produzieren: 'Produzieren (Englisch → Deutsch)',
  verbformen: 'Verbformen', kontrast: 'Welches Wort passt?', kollokation: 'Kollokationen' };
const GROUP_ORDER = ['bedeutung', 'produzieren', 'verbformen', 'kontrast', 'kollokation'];
function groups(cards) {
  const m = new Map();
  for (const c of cards) {
    const g = groupOf(c);
    if (!m.has(g)) m.set(g, { id: g, name: GROUP_NAMES[g] || c.n.felder.Thema || c.t.name, n: 0, grammar: c.n.typ === 'Grammatik' });
    m.get(g).n++;
  }
  return [...m.values()].sort((a, b) => (a.grammar - b.grammar)
    || ((GROUP_ORDER.indexOf(a.id) + 1 || 99) - (GROUP_ORDER.indexOf(b.id) + 1 || 99)) || a.name.localeCompare(b.name));
}

// ── settings (kept in this browser) ─────────────────────────────────────────
const KEY = 'gv-ueben';
const DEFAULTS = { groups: ['bedeutung', 'produzieren'], level: 'alle', order: 'faellig', n: 20, vorlesen: true };
// the saved choice, each value checked against the defaults' type (a damaged entry falls back to them)
function loadSettings() {
  let s = {};
  try { s = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { /* private window or damaged */ }
  const out = { ...DEFAULTS };
  for (const [k, v] of Object.entries(DEFAULTS)) {
    const x = s[k];
    if (Array.isArray(v) ? Array.isArray(x) && x.every(y => typeof y === 'string') : typeof x === typeof v) out[k] = x;
  }
  return out;
}
function saveSettings(s) { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) { /* private window */ } }

function pick(cards, s) {
  let cs = cards.filter(c => s.groups.includes(groupOf(c))
    && (s.level === 'alle' || c.n.typ === 'Grammatik' || c.n.niveau === s.level));
  cs = shuffle(cs);
  // due first (the most overdue first), then new cards; cards learnt and not due yet wait
  if (s.order === 'faellig') {
    const now = Date.now();
    const due = cs.filter(c => LS.isDue(LS.cardId(c), now)).sort((a, b) => dueMs(LS.state(LS.cardId(a))) - dueMs(LS.state(LS.cardId(b))));
    return [...due, ...cs.filter(c => LS.isNew(LS.cardId(c)))];
  }
  if (s.order === 'haeufig') cs.sort((a, b) => (b.n.freq ?? -1) - (a.n.freq ?? -1));
  if (s.order === 'neu') cs.sort((a, b) => String(b.n.neu || '').localeCompare(String(a.n.neu || '')));
  return cs;
}
function shuffle(a) {
  a = a.slice();
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}

// ── the page ────────────────────────────────────────────────────────────────
export function render(D) {
  const view = h`
    <nav class="path" aria-label="Pfad"><a href="${link.start()}">Bibliothek</a> › <span class="here">Üben</span></nav>
    <div id="ueben"><div class="loading">Die Karten werden geholt …</div></div>`;
  return { title: 'Üben', view, mount: root => mount(root, D) };
}

function mount(root, D) {
  const box = root.querySelector('#ueben');
  const s = loadSettings();
  load().then(k => setup(box, D, k, s)).catch(err => {
    console.error(err);
    box.innerHTML = '<div class="loading">Die Karten konnten nicht geladen werden (web/data/karten.json fehlt: <code>python -m vocab_builder karten</code>).</div>';
  });
}

function setup(box, D, k, s) {
  document.body.classList.remove('uebung');
  const cards = k.cards, gs = groups(cards);
  s.groups = s.groups.filter(g => gs.some(x => x.id === g));
  let msg = '';
  const draw = () => {
    const n = pick(cards, s).length;
    const now = Date.now(), ids = cards.map(LS.cardId).filter(id => !LS.isNew(id));
    const lern = { gelernt: ids.length, faellig: ids.filter(id => LS.isDue(id, now)).length, gefestigt: ids.filter(id => LS.status(id) === 'gefestigt').length };
    lern.faelligHier = s.order === 'faellig' ? pick(cards, s).filter(c => !LS.isNew(LS.cardId(c))).length : 0;
    const chips = list => list.map(g => h`<button type="button" class="seg${s.groups.includes(g.id) ? ' on' : ''}" data-g="${g.id}" aria-pressed="${String(s.groups.includes(g.id))}">${g.name} <span class="cnt">${g.n}</span></button>`);
    box.innerHTML = html(h`
      <section class="panel uset">
        <h1 class="sec">Üben</h1>
        <p class="lab">Wörter, Kollokationen und Grammatik. Dein Lernstand bleibt in diesem Browser: sichere ihn ab und zu als Datei.</p>
        <div class="urow"><span class="ulab">Lernstand</span><div class="ustand">
          <span>${lern.gelernt} Karten gelernt · <b>${lern.faellig}</b> heute fällig · ${lern.gefestigt} gefestigt</span>
          <div class="segs wrap"><label class="seg ufile">Lernstand laden<input type="file" id="laden" accept=".json,application/json" hidden></label>
            <button type="button" class="seg" id="sichern" ${lern.gelernt ? '' : 'disabled'}>Lernstand als Datei sichern</button></div>
          <span class="lab" id="lmsg" aria-live="polite">${msg}</span></div></div>
        <div class="urow"><span class="ulab">Wörter</span><div class="segs wrap">${chips(gs.filter(g => !g.grammar))}</div></div>
        <div class="urow"><span class="ulab">Grammatik</span><div class="segs wrap">${chips(gs.filter(g => g.grammar))}</div></div>
        <div class="urow"><span class="ulab">Niveau</span><div class="segs">${seg([['alle', 'Alle'], ...LEVELS.map(l => [l, l])], s.level, 'lv')}</div></div>
        <div class="urow"><span class="ulab">Reihenfolge</span><div class="segs wrap">${seg([['faellig', 'fällige, dann neue'], ['zufall', 'zufällig'], ['haeufig', 'häufigste zuerst'], ['neu', 'neueste zuerst']], s.order, 'ord')}</div></div>
        <div class="urow"><span class="ulab">Karten</span><div class="segs">${seg([['10', '10'], ['20', '20'], ['50', '50']], String(s.n), 'num')}</div></div>
        <p class="lab">${s.level !== 'alle' && s.groups.some(g => g.startsWith('g:')) ? 'Die Grammatikkarten haben kein Niveau: sie sind immer dabei. ' : ''}${s.order === 'faellig' ? `${lern.faelligHier} fällig und ${n - lern.faelligHier} neu in dieser Auswahl.` : `${n} Karten passen zu dieser Auswahl.`}</p>
        <div><button type="button" class="go" id="go" ${n ? '' : 'disabled'}>Los</button></div>
      </section>`);
  };
  draw();
  box.onclick = e => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.dataset.g) { const g = b.dataset.g; s.groups = s.groups.includes(g) ? s.groups.filter(x => x !== g) : [...s.groups, g]; }
    else if (b.dataset.lv) s.level = b.dataset.lv;
    else if (b.dataset.ord) s.order = b.dataset.ord;
    else if (b.dataset.num) s.n = +b.dataset.num;
    else if (b.id === 'go') { saveSettings(s); return session(box, D, k, s, pick(cards, s).slice(0, s.n)); }
    else if (b.id === 'sichern') {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([JSON.stringify(LS.exportData())], { type: 'application/json' }));
      a.download = 'lernstand_' + new Date().toISOString().slice(0, 10) + '.json'; a.click(); return;
    }
    else return;
    saveSettings(s); draw();
  };
  box.onchange = e => {
    if (e.target.id !== 'laden' || !e.target.files[0]) return;
    e.target.files[0].text().then(t => {
      const r = LS.merge(JSON.parse(t));
      msg = r.saved ? `${r.added} Antworten dazugeladen.` : `${r.added} Antworten gelesen, aber der Browser konnte sie nicht speichern (Speicher voll?).`;
    }).catch(() => { msg = 'Diese Datei konnte nicht gelesen werden.'; }).then(draw);
  };
}

const label = c => c.n.typ === 'Grammatik' ? `${c.n.felder.Thema}: ${text(c.n.felder.Ganz || '')}`
  : text(c.n.felder.Kollokation || c.n.felder.Wort || '');

const ICON_BACK = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M19 12H5M11 6l-6 6 6 6"/></svg>';
const ICON_ON = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" aria-hidden="true"><path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/></svg>';
const ICON_OFF = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" aria-hidden="true"><path d="M11 5 6 9H3v6h3l5 4z"/><path d="m16 9 5 6M21 9l-5 6"/></svg>';
const clock = ms => { const t = Math.floor(ms / 1000); return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`; };

function session(box, D, k, s, deck) {
  // the practice screen has no menu: the header comes back with the next page
  document.body.classList.add('uebung');
  window.scrollTo(0, 0);
  const results = [];
  const start = Date.now();
  let i = 0, phase = 'vorne', typed = '', ok = false, shownAt = 0, say = '', easy = false, warned = false;
  const again = new Set();          // a card answered wrong comes back once more in the round
  box.innerHTML = html(h`
    <section class="usess" tabindex="-1">
      <div class="ubar">
        <button type="button" class="iconbtn" id="stop" aria-label="Übung beenden" title="Übung beenden">${raw(ICON_BACK)}</button>
        <button type="button" class="iconbtn" id="vor" aria-pressed="${String(s.vorlesen)}" aria-label="Rückseite automatisch vorlesen" title="Rückseite automatisch vorlesen"></button>
        <select class="voice" id="stimme" aria-label="Stimme"></select>
        <span class="uprog vt" id="prog"></span>
      </div>
      <div class="ubarre" aria-hidden="true"><div id="barre"></div></div>
      <div id="karte" class="ukarte"></div>
      <div class="kbar" id="knoepfe"></div>
    </section>`);
  const sess = box.querySelector('.usess'), cardEl = box.querySelector('#karte'), knoepfe = box.querySelector('#knoepfe');
  const vor = box.querySelector('#vor'), stimme = box.querySelector('#stimme');
  const drawVor = () => { vor.innerHTML = s.vorlesen ? ICON_ON : ICON_OFF; vor.classList.toggle('on', s.vorlesen); vor.setAttribute('aria-pressed', String(s.vorlesen)); };
  const drawVoices = () => {
    const vs = voices(), c = chosenVoice();
    stimme.innerHTML = html(h`<option value="">Stimme: automatisch</option>${vs.map(v => h`<option value="${v.name}"${v.name === c ? raw(' selected') : ''}>${v.name}</option>`)}`);
    stimme.hidden = !vs.length;
  };
  drawVor(); drawVoices();
  if (window.speechSynthesis) speechSynthesis.addEventListener('voiceschanged', drawVoices);
  stimme.addEventListener('change', () => { setVoice(stimme.value); if (say) speak(say); });
  const timer = setInterval(() => {
    if (!sess.isConnected) { clearInterval(timer); return; }
    box.querySelector('#prog').textContent = `${i + 1} / ${deck.length} · ${clock(Date.now() - start)}`;
  }, 1000);

  const field = c => ask(c).field;
  const show = () => {
    const c = deck[i];
    box.querySelector('#prog').textContent = `${i + 1} / ${deck.length} · ${clock(Date.now() - start)}`;
    box.querySelector('#barre').style.width = `${100 * i / deck.length}%`;
    if (phase === 'vorne') {
      say = '';
      cardEl.innerHTML = front(c);
      knoepfe.innerHTML = '<button type="button" class="ubtn" id="check">Prüfen</button><p class="khint">Groß- und Kleinschreibung zählt nicht. Weißt du es nicht, lass das Feld leer.</p>';
      const inp = cardEl.querySelector('#kin');
      if (inp) { inp.focus({ preventScroll: true }); inp.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); check(); } }); }
    } else {
      drawBack();
      const ref = { wo: 'karte', typ: c.n.typ, id: c.n.id, karte: c.key, kartenname: c.n.typ === 'Grammatik' ? c.n.felder.Thema : c.t.name,
        wort: c.n.wort, thema: c.n.thema, label: label(c), eingabe: typed, erwartet: text(c.n.felder[field(c)] || ''), urteil: ok ? 'richtig' : 'falsch' };
      knoepfe.innerHTML = html(h`<p class="khint" id="naechste">${nextNote()}</p>
        <div class="kbar-row">${notizKnopf(ref, 'Notiz zur Karte')}${ok ? h`<button type="button" class="nbtn" id="leicht" aria-pressed="false">War leicht</button>` : ''}<button type="button" class="ubtn" id="next">${i + 1 < deck.length || (!ok && !again.has(c)) ? 'Weiter' : 'Zur Zusammenfassung'}</button></div>`);
      shownAt = Date.now();
      sess.focus({ preventScroll: true });
      window.scrollTo(0, 0);
      if (s.vorlesen && say) speak(say);
    }
  };
  const drawBack = () => {
    const out = back(D, k, deck[i], typed, ok);
    cardEl.innerHTML = out.html;
    say = out.say;
  };
  // FSRS: wrong = Again, right = Good, right + "War leicht" = Easy; Hard is not used
  const grade = () => ok ? (easy ? 4 : 3) : 1;
  const nextNote = () => {
    const st = LS.preview(LS.cardId(deck[i]), grade());
    if (!ok) return 'Kommt in dieser Runde noch einmal, dann wieder heute oder morgen';
    const d = dueDays(st);
    return `Nächste Wiederholung: in ${d === 1 ? 'einem Tag' : `etwa ${d} Tagen`}`;
  };
  // a note saying the answer was right too: the card counts as right
  box.addEventListener('notiz', e => {
    if (phase === 'hinten' && !ok && (e.detail.gruende || []).includes(RICHTIG)) {
      results[results.length - 1].ok = true; ok = true; drawBack();
      const n = box.querySelector('#naechste'); if (n) n.textContent = nextNote();
    }
  });
  const check = () => {
    const c = deck[i], inp = cardEl.querySelector('#kin');
    typed = inp ? inp.value : '';
    ok = right(c, typed, c.n.felder[field(c)] || ''); easy = false;
    results.push({ c, ok });
    phase = 'hinten'; show();
  };
  const next = () => {
    // the answer counts when you go on, so "War leicht" and a note can still change it
    const c = deck[i];
    if (!LS.answer(LS.cardId(c), grade()) && !warned) {
      warned = true;
      box.querySelector('.ubar').insertAdjacentHTML('afterend', '<p class="khint" role="alert">Dein Lernstand konnte nicht gespeichert werden (Speicher voll oder privates Fenster). Sichere ihn nach der Runde als Datei.</p>');
    }
    if (!ok && !again.has(c)) { again.add(c); deck.splice(Math.min(deck.length, i + 5), 0, c); }
    if (i + 1 < deck.length) { i++; phase = 'vorne'; show(); } else done();
  };
  sess.addEventListener('keydown', e => {
    if (e.key === 'Enter' && phase === 'hinten' && !e.repeat && Date.now() - shownAt > 250 && !e.target.closest('button, a, textarea, select')) { e.preventDefault(); next(); }
  });
  const done = () => {
    clearInterval(timer);
    document.body.classList.remove('uebung');
    if (window.speechSynthesis) speechSynthesis.cancel();
    const wrong = [...new Map(results.filter(r => !r.ok).map(r => [r.c, r])).values()];   // a card once, even if it came back
    box.innerHTML = html(h`
      <section class="panel uset">
        <h1 class="sec">Fertig</h1>
        <p class="ubig vt">${results.length - wrong.length} von ${results.length} richtig · ${clock(Date.now() - start)}</p>
        ${wrong.length ? h`<div><div class="ulab">Noch einmal anschauen</div>
          <ul class="uwrong">${wrong.map(r => h`<li><a href="${r.c.n.typ === 'Grammatik' ? link.thema(r.c.n.thema) : link.wort(r.c.n.wort)}">${label(r.c)}</a> <span class="lab">${r.c.n.typ === 'Grammatik' ? r.c.n.felder.Thema : r.c.t.name}</span></li>`)}</ul></div>` : ''}
        <div class="uknoepfe">
          ${wrong.length ? h`<button type="button" class="go" id="again">Die Fehler noch einmal</button>` : ''}
          <button type="button" class="${wrong.length ? 'seg' : 'go'}" id="new">Neue Runde</button>
          <button type="button" class="seg" id="stop">Auswahl ändern</button>
        </div>
      </section>`);
    box.onclick = e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.id === 'again') session(box, D, k, s, shuffle(wrong.map(r => r.c)));
      else if (b.id === 'new') session(box, D, k, s, pick(k.cards, s).slice(0, s.n));
      else if (b.id === 'stop') setup(box, D, k, s);
    };
  };
  box.onclick = e => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.id === 'check') check();
    else if (b.id === 'next') next();
    else if (b.id === 'leicht') { easy = !easy; b.classList.toggle('on', easy); b.setAttribute('aria-pressed', String(easy)); box.querySelector('#naechste').textContent = nextNote(); }
    else if (b.id === 'vor') { s.vorlesen = !s.vorlesen; saveSettings(s); drawVor(); if (s.vorlesen && say) speak(say); else if (window.speechSynthesis) speechSynthesis.cancel(); }
    else if (b.id === 'stop') { clearInterval(timer); if (window.speechSynthesis) speechSynthesis.cancel(); setup(box, D, k, s); }
  };
  show();
}
