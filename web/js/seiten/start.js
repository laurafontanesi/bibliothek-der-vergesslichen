// The entrance: picture, word search in both directions, the two doors with their levels,
// the newest words and the largest families.
import { LEVELS, forms, meaning, allMeanings, norm, TYPE_DE } from '../daten.js';
import { h, raw, html, hero, seg, link } from '../hilfe.js';
import { cover } from './familien.js';

export function render(D) {
  const words = Object.fromEntries(LEVELS.map(l => [l, D.W.filter(e => e.level === l).length]));
  const maxw = Math.max(...Object.values(words));
  const gmax = Math.max(...LEVELS.map(l => D.gramLevels[l].active + D.gramLevels[l].planned));
  const types = {}; D.W.forEach(e => { types[e.type] = (types[e.type] || 0) + 1; });
  const other = D.W.length - (types.verb || 0) - (types.noun || 0) - (types['adj/adv'] || 0);
  const nActive = [...D.topics.values()].filter(t => t.status === 'active').length;
  const newest = D.W.slice().sort((a, b) => (b.added || '').localeCompare(a.added || '')).slice(0, 8);

  const search = h`
    <div class="segs" role="group" aria-label="Suchrichtung" id="dirs">${seg([['de', 'Deutsch → Englisch'], ['en', 'Englisch → Deutsch']], 'de', 'dir')}</div>
    <div style="position:relative;margin-top:-4px">
      <label for="q" class="vh">Wort suchen</label>
      <input id="q" class="search" type="search" autocomplete="off" placeholder="Deutsches Wort, z. B. Aufzug" style="height:50px">
      <div id="results"></div>
    </div>`;

  const view = h`
  ${hero('start', 'Bibliothek der Vergesslichen', `${D.W.length} Wörter und ${D.topics.size} Grammatikthemen.`, search, 84)}
  <div class="grid2">
    <section class="panel">
      <div style="display:flex;justify-content:space-between;align-items:baseline">
        <h2 class="vt" style="margin:0;font-size:42px"><a href="${link.vokabular()}" style="color:var(--tx);text-decoration:none">Vokabular →</a></h2>
        <span class="lab">${D.W.length} Wörter</span>
      </div>
      ${LEVELS.map(L => h`
      <a class="levelrow" href="${link.vokabular({ niveau: L })}">
        <span class="lv">${L}</span>
        <span class="bar"><span class="fill" style="width:${Math.round(100 * words[L] / maxw)}%"></span></span>
        <span style="font-size:14px;text-align:right"><span class="vt" style="font-size:22px">${words[L]}</span> Wörter</span>
      </a>`)}
      <div class="lab" style="margin-top:8px;line-height:1.5">${types.verb || 0} Verben · ${types.noun || 0} Nomen · ${types['adj/adv'] || 0} Adjektive und Adverbien · ${other} Ausdrücke, Konnektoren und Konstruktionen</div>
    </section>
    <section class="panel">
      <div style="display:flex;justify-content:space-between;align-items:baseline">
        <h2 class="vt" style="margin:0;font-size:42px"><a href="${link.grammatik()}" style="color:var(--tx);text-decoration:none">Grammatik →</a></h2>
        <span class="lab">${D.topics.size} Themen, ${nActive} davon mit Übungen</span>
      </div>
      ${LEVELS.map(L => { const g = D.gramLevels[L]; return h`
      <a class="levelrow" href="${link.grammatik()}" style="grid-template-columns:44px minmax(0,1fr) auto">
        <span class="lv">${L}</span>
        <span class="bar" style="background:none"><span class="fill" style="width:${(100 * g.active / gmax).toFixed(1)}%"></span><span class="plan" style="width:${(100 * g.planned / gmax).toFixed(1)}%"></span></span>
        <span style="font-size:14px;text-align:right"><span class="vt" style="font-size:22px">${g.active}</span> geübt · ${g.planned} geplant</span>
      </a>`; })}
      <div class="legend lab" style="margin-top:8px">
        <span><span class="sw" style="width:14px;height:10px;background:var(--acc)"></span>schon geübt</span>
        <span><span class="sw" style="width:14px;height:10px;border:1px dashed var(--dim)"></span>geplant</span>
        <span>Strukturen pro Niveau</span>
      </div>
    </section>
  </div>

  <section style="display:flex;flex-direction:column;gap:12px">
    <div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap"><h2 class="sec">Neu im Regal</h2><a href="${link.vokabular({ ordnung: 'neu' })}" style="font-size:14px">alle, die neuesten zuerst →</a></div>
    <div class="grid4">${newest.map(e => h`
      <a class="card slip" href="${link.wort(e.id)}">
        <span style="display:flex;justify-content:space-between;align-items:flex-start;gap:6px"><span class="de" style="font-size:19px;font-weight:600;line-height:1.15">${e.word}</span><span class="lv">${e.level}</span></span>
        <span class="de" style="font-size:13px;color:var(--muted)">${forms(e)}</span>
        <span class="en-d" style="font-size:15px">${meaning(e)}</span>
      </a>`)}</div>
  </section>

  <section style="display:flex;flex-direction:column;gap:12px">
    <div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap"><h2 class="sec">Große Wortfamilien</h2><a href="${link.familien()}" style="font-size:14px">alle ${D.families.length} Familien →</a></div>
    <div class="chips">${D.families.slice(0, 8).map(([r, es]) => h`<a href="${link.familie(r)}" style="display:inline-flex;align-items:center;gap:8px;padding:6px 12px 6px 8px;border:1px solid var(--line);background:var(--panel);color:var(--tx);text-decoration:none"><img src="${cover(D, r)}" alt="" width="21" height="27" style="image-rendering:pixelated"><span class="de" style="font-size:17px">${r}</span><span class="vt" style="font-size:20px;color:var(--muted)">${es.length}</span></a>`)}</div>
  </section>`;
  return { title: '', view, mount: el => mountSearch(el, D) };
}

// The search: German word (without article) or any English meaning, best matches first
export function searchWords(D, q, dir, n = 9) {
  q = norm(q.trim());
  if (q.length < 2) return null;
  const hits = [];
  for (const e of D.W) {
    let rank = 0;
    if (dir === 'de') { const k = e._key; rank = k === q ? 1 : k.startsWith(q) ? 2 : k.includes(q) ? 3 : 0; }
    else {
      const ms = norm(allMeanings(e)).split(/[·,;()/]/).map(x => x.trim().replace(/^(to|a|an|the) /, ''));
      const re = new RegExp('\\b' + q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
      rank = ms.some(m => m === q) ? 1 : ms.some(m => m.startsWith(q)) ? 2 : ms.some(m => re.test(m)) ? 3 : 0;
    }
    if (rank) hits.push([rank, e]);
  }
  hits.sort((a, b) => a[0] - b[0] || a[1].word.length - b[1].word.length);
  return hits.slice(0, n).map(x => x[1]);
}

function mountSearch(el, D) {
  let dir = 'de';
  const input = el.querySelector('#q'), out = el.querySelector('#results'), dirs = el.querySelector('#dirs');
  const draw = () => {
    const res = searchWords(D, input.value, dir);
    if (!res) { out.innerHTML = ''; return; }
    out.innerHTML = html(res.length ? h`<div class="results">${res.map(e => h`
      <a href="${link.wort(e.id)}"><span class="de" style="font-size:17px;font-weight:600">${e.word}</span><span class="vt" style="font-size:18px;color:var(--ink2);text-align:right">${e.level}</span>
      <span class="en" style="font-size:14px;grid-column:1 / -1">${allMeanings(e)}</span></a>`)}</div>`
      : h`<div class="results"><div class="none">Nichts gefunden: dieses Wort steht nicht im Regal.</div></div>`);
  };
  input.addEventListener('input', draw);
  input.addEventListener('keydown', e => { if (e.key === 'Enter') { const a = out.querySelector('a'); if (a) location.hash = a.getAttribute('href'); } });
  dirs.addEventListener('click', e => {
    const b = e.target.closest('[data-dir]'); if (!b) return;
    dir = b.dataset.dir;
    dirs.innerHTML = html(h`${seg([['de', 'Deutsch → Englisch'], ['en', 'Englisch → Deutsch']], dir, 'dir')}`);
    input.placeholder = dir === 'de' ? 'Deutsches Wort, z. B. Aufzug' : 'Englisches Wort, z. B. lift';
    draw(); input.focus();
  });
}
