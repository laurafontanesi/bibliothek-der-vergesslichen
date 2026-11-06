// Notes on what should change: on a card in Üben, on a word page, on a grammar page. Each note says where it was made (the card with your answer, the word, the topic), a few
// ready-made reasons and your own text. Kept in this browser; #notizen lists them
// and saves them as a file.
import { h, html, esc } from './hilfe.js';
import { keep } from './lernstand.js';

const KEY = 'gv-notizen';
export const RICHTIG = 'Meine Antwort war auch richtig';
export const TAGS = {
  karte: [RICHTIG, 'Fehler in der Karte', 'Hinweis unklar', 'Übersetzung passt nicht', 'Satz klingt unnatürlich', 'Rückseite: zu viel oder zu wenig'],
  wort: ['Fehler', 'Bedeutung fehlt oder ungenau', 'Beispiel fehlt oder passt nicht', 'Notiz überarbeiten', 'Verwandtes Wort fehlt'],
  grammatik: ['Fehler', 'Regel unklar', 'Beispiel fehlt oder passt nicht', 'Tabelle unklar', 'Fehlt in diesem Thema'],
};

export function all() {
  try { const x = JSON.parse(localStorage.getItem(KEY) || '[]'); return Array.isArray(x) ? x : []; } catch (e) { return []; }
}
function put(list) {
  keep();
  try { localStorage.setItem(KEY, JSON.stringify(list)); return true; } catch (e) { return false; }
}
export function remove(id) { put(all().filter(n => n.id !== id)); badge(); }
export function clear() { put([]); badge(); }

// The count in the header: only shown when there are notes
export function badge() {
  const a = document.getElementById('nnav');
  if (!a) return;
  const n = all().length;
  a.hidden = !n;
  a.querySelector('span').textContent = n ? `(${n})` : '';
}

// The button; `ref` says where the note belongs (wo: karte | wort | grammatik, ids, a label)
export function button(ref, label) {
  return h`<button type="button" class="nbtn" data-notiz="${JSON.stringify(ref)}">${label}</button>`;
}

function form(ref) {
  const el = document.createElement('div');
  el.className = 'nform';
  el.setAttribute('role', 'group');
  el.setAttribute('aria-label', 'Notiz');
  el.innerHTML = html(h`
    <div class="nlab">Was sollte sich ändern?</div>
    <div class="segs wrap">${(TAGS[ref.wo] || TAGS.wort).map(t => h`<button type="button" class="seg" data-ntag="${t}" aria-pressed="false">${t}</button>`)}</div>
    <label class="vh" for="ntext">Deine Notiz</label>
    <textarea id="ntext" rows="3" placeholder="Was ist falsch, was fehlt, was würdest du anders machen?"></textarea>
    <div class="nact"><button type="button" class="go" data-nact="save">Speichern</button><button type="button" class="seg" data-nact="cancel">Abbrechen</button><span class="nmsg" aria-live="polite"></span></div>`);
  return el;
}

document.addEventListener('click', e => {
  const b = e.target.closest('[data-notiz]');
  if (b) {
    const open = b.nextElementSibling && b.nextElementSibling.classList.contains('nform') ? b.nextElementSibling : null;
    if (open) { open.remove(); return; }
    const ref = JSON.parse(b.dataset.notiz);
    const f = form(ref);
    b.insertAdjacentElement('afterend', f);
    f.querySelector('textarea').focus({ preventScroll: true });
    f.scrollIntoView({ block: 'nearest' });
    return;
  }
  const t = e.target.closest('[data-ntag]');
  if (t) { const on = t.getAttribute('aria-pressed') !== 'true'; t.setAttribute('aria-pressed', String(on)); t.classList.toggle('on', on); return; }
  const a = e.target.closest('[data-nact]');
  if (!a) return;
  const f = a.closest('.nform'), btn = f.previousElementSibling;
  if (a.dataset.nact === 'cancel') { f.remove(); return; }
  const tags = [...f.querySelectorAll('[data-ntag][aria-pressed="true"]')].map(x => x.dataset.ntag);
  const text = f.querySelector('textarea').value.trim();
  if (!tags.length && !text) { f.querySelector('.nmsg').textContent = 'Wähle einen Grund oder schreib etwas.'; return; }
  const note = { id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6), wann: new Date().toISOString(),
    ...JSON.parse(btn.dataset.notiz), gruende: tags, text };
  const list = all(); list.push(note);
  const saved = put(list);
  badge();
  const done = document.createElement('div');
  done.className = 'nmsg ndone';
  done.innerHTML = saved ? html(h`Notiz gespeichert · <a href="#notizen">alle Notizen (${list.length})</a>`)
    : 'Dieser Browser speichert nichts (privates Fenster?): die Notiz ging verloren.';
  f.replaceWith(done);
  btn.dispatchEvent(new CustomEvent('notiz', { detail: note, bubbles: true }));
});

export function label(n) { return esc(n.label || n.id || ''); }
