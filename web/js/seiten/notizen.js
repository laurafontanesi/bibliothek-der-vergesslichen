// #notizen: the notes made on cards, words and grammar pages (js/notizen.js), newest first, to delete
// one by one or save as a file. They stay in this browser.
import { h, html, link } from '../hilfe.js';
import { all, remove, clear } from '../notizen.js';

const WO = { karte: 'Karte', wort: 'Wort', grammatik: 'Grammatik' };
const when = s => { try { return new Date(s).toLocaleString('de-CH', { dateStyle: 'medium', timeStyle: 'short' }); } catch (e) { return s; } };
function where(n) {
  if (n.wo === 'wort') return link.wort(n.id);
  if (n.wo === 'grammatik') return link.thema(n.thema, n.zelle);
  return n.thema ? link.thema(n.thema) : link.wort(n.wort);
}
function asText(list) {
  return list.map(n => [`${when(n.wann)} · ${WO[n.wo] || n.wo}: ${n.label}${n.karte ? ' (' + n.kartenname + ')' : ''}`,
    n.gruende && n.gruende.length ? '  Gründe: ' + n.gruende.join(', ') : '',
    n.text ? '  ' + n.text : '',
    n.wo === 'karte' ? `  Deine Antwort: ${n.eingabe || '(leer)'} · erwartet: ${n.erwartet} · ${n.urteil}` : ''].filter(Boolean).join('\n')).join('\n\n');
}

export function render() {
  const view = h`
    <nav class="path" aria-label="Pfad"><a href="${link.start()}">Bibliothek</a> › <span class="here">Notizen</span></nav>
    <section class="panel uset" id="nliste"></section>`;
  return { title: 'Notizen', view, mount };
}

function mount(root) {
  const box = root.querySelector('#nliste');
  let sure = false;
  const draw = () => {
    const list = all().slice().reverse();
    box.innerHTML = html(h`
      <h1 class="sec">Notizen</h1>
      <p class="lab">Was sich an Karten, Wörtern und Grammatikseiten ändern sollte. Deine Notizen bleiben in diesem Browser: Handy und Computer haben je ihre eigene Liste. Mit „Als Datei speichern“ behältst du sie oder gibst sie weiter.</p>
      ${list.length ? h`<div class="uknoepfe" style="justify-content:flex-start">
          <button type="button" class="go" data-a="datei">Als Datei speichern</button>
          <button type="button" class="seg" data-a="kopieren">Als Text kopieren</button>
          <button type="button" class="seg" data-a="leeren">${sure ? 'Wirklich alle löschen?' : 'Alle löschen'}</button>
          <span class="nmsg" id="nmsg" aria-live="polite"></span></div>
        <ul class="nlist">${list.map(n => h`<li>
          <div class="nhead"><span class="lab">${when(n.wann)} · ${WO[n.wo] || n.wo}</span>
            <button type="button" class="nx" data-del="${n.id}" aria-label="Notiz löschen" title="löschen">✕</button></div>
          <div><a class="de" href="${where(n)}">${n.label}</a>${n.kartenname ? h` <span class="lab">${n.kartenname}</span>` : ''}</div>
          ${n.gruende && n.gruende.length ? h`<div class="segs wrap">${n.gruende.map(g => h`<span class="ntag">${g}</span>`)}</div>` : ''}
          ${n.text ? h`<div class="ntext">${n.text}</div>` : ''}
          ${n.wo === 'karte' ? h`<div class="lab">Deine Antwort: <span class="mono">${n.eingabe || '(leer)'}</span> · erwartet: <span class="mono">${n.erwartet}</span> · ${n.urteil}</div>` : ''}
        </li>`)}</ul>` : h`<p class="lab">Noch keine Notizen. Auf jeder Karte im Üben, auf jeder Wortseite und auf jeder Grammatikseite gibt es einen Knopf dafür.</p>`}`);
  };
  draw();
  box.onclick = e => {
    const d = e.target.closest('[data-del]');
    if (d) { remove(d.dataset.del); sure = false; draw(); return; }
    const b = e.target.closest('[data-a]'); if (!b) return;
    const list = all();
    if (b.dataset.a === 'datei') {
      const blob = new Blob([JSON.stringify({ gespeichert: new Date().toISOString(), notizen: list }, null, 1)], { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob); a.download = 'notizen_' + new Date().toISOString().slice(0, 10) + '.json'; a.click();
    } else if (b.dataset.a === 'kopieren') {
      const s = asText(list);
      (navigator.clipboard ? navigator.clipboard.writeText(s) : Promise.reject()).then(
        () => { box.querySelector('#nmsg').textContent = 'Kopiert'; }, () => { box.querySelector('#nmsg').textContent = 'Kopieren ging nicht: speichere die Datei.'; });
    } else if (b.dataset.a === 'leeren') {
      if (sure) { clear(); sure = false; } else sure = true;
      draw();
    }
  };
}
