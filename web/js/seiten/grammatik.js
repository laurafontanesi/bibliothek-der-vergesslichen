// Grammatik: the topics by area or by level; practised topics first, planned ones greyed out.
import { LEVELS, AREAS, PRACTISED, level } from '../daten.js';
import { h, html, hero, seg, link } from '../hilfe.js';

export function render(D) {
  const T = D.topics;
  const nActive = [...T.values()].filter(t => t.status === 'active').length;
  const ctrl = h`<div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap">
      <div class="segs" role="group" aria-label="Anordnung" id="gview"></div>
      <label class="check" style="color:var(--tx);background:rgba(27,21,22,0.75);padding:6px 10px"><input type="checkbox" id="gonly">nur mit Übungen</label>
    </div>`;
  const view = h`
    ${hero('grammatik', 'Grammatik', `${T.size} Themen. ${nActive} davon mit Übungen, die anderen stehen schon im Plan.`, ctrl)}
    <div class="legend lab">
      <span><span class="sw" style="background:var(--acc)"></span>mit Übungen: Karten im Lernzimmer</span>
      <span><span class="sw" style="border:1px dashed var(--dim)"></span>geplant</span>
      <span><span class="sw" style="border:1px dotted var(--dim)"></span>später</span>
    </div>
    <div id="gcols"></div>`;
  return { title: 'Grammatik', view, mount: el => {
    const s = { view: 'bereich', only: false };
    const rank = t => ({ active: 0, planned: 1, later: 2 })[t.status] ?? 1;
    const str = n => `${n} ${n === 1 ? 'Struktur' : 'Strukturen'}`;
    const item = (t, lvl) => {
      const act = t.status === 'active', later = t.status === 'later';
      let info;
      if (lvl) {
        // by level: the topic's structures on this level, practised and planned, as on the entrance
        const ss = t.structures.filter(x => level(x.level) === lvl), a = ss.filter(PRACTISED).length;
        info = act ? `${str(ss.length)} auf ${lvl}` + (a < ss.length ? ` · ${a} geübt, ${ss.length - a} geplant` : ' · geübt')
          : `${later ? 'später' : 'geplant'} · ${str(ss.length)}`;
      } else {
        info = act ? `${t.cards.length} Karten · ${t.cells.length} Formen` : `${later ? 'später' : 'geplant'} · ${str(t.nstruct)}`;
      }
      return h`<a class="topic${act ? ' active' : ''}${later ? ' later' : ''}" href="${link.thema(t.id)}">
        <span style="display:flex;flex-direction:column;gap:3px;min-width:0"><span style="font-size:16px;font-weight:600;line-height:1.25">${t.name}</span><span style="font-size:13px;color:var(--muted)">${info}</span></span>
        <span style="display:flex;gap:3px;flex-wrap:wrap;justify-content:flex-end;max-width:120px">${lvl ? '' : t.levels.map(l => h`<span class="lv">${l}</span>`)}</span></a>`;
    };
    const draw = () => {
      el.querySelector('#gview').innerHTML = html(h`${seg([['bereich', 'nach Bereich'], ['niveau', 'nach Niveau']], s.view, 'view')}`);
      const ok = t => !s.only || t.status === 'active';
      const cols = s.view === 'bereich'
        ? AREAS.map(([name, ids]) => { const ts = ids.map(i => T.get(i)).filter(Boolean);
            return { title: name, sub: `${ts.filter(t => t.status === 'active').length} von ${ts.length} mit Übungen`, items: ts.filter(ok).sort((a, b) => rank(a) - rank(b)).map(t => item(t, null)) }; })
        : LEVELS.map(l => { const ts = [...T.values()].filter(t => t.bylevel[l] && ok(t)).sort((a, b) => rank(a) - rank(b));
            const g = D.gramLevels[l], x = D.looseLevels[l];
            return { title: l, sub: `${g.active} geübt · ${g.planned} geplant`, items: ts.map(t => item(t, l)),
              foot: x.active + x.planned ? `Dazu ${x.active ? str(x.active) + ' auf den Wortkarten geübt (Verbformen, Plural und Ähnliches)' : ''}${x.active && x.planned ? ' und ' : ''}${x.planned ? str(x.planned) + ' ohne eigenes Thema geplant (auf den Wortkarten, fürs Schreiben, fürs Lesen oder für später)' : ''}.` : '' }; });
      el.querySelector('#gcols').innerHTML = html(h`<div class="${s.view === 'bereich' ? 'grid3' : 'grid4'}" style="gap:16px;align-items:start">${cols.map(c => h`
        <section class="card" style="padding:16px 16px 12px;display:flex;flex-direction:column;gap:6px">
          <div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px;border-bottom:1px solid var(--line);padding-bottom:8px;margin-bottom:4px">
            <h2 class="sec" style="font-size:32px">${c.title}</h2><span class="lab">${c.sub}</span></div>
          ${c.items.length ? c.items : h`<div class="lab" style="padding:8px 0">Keine Themen mit Übungen.</div>`}
          ${c.foot ? h`<div class="lab" style="padding:8px 2px 0;line-height:1.45;border-top:1px solid var(--line2);margin-top:4px">${c.foot}</div>` : ''}
        </section>`)}</div>`);
    };
    el.addEventListener('click', e => { const b = e.target.closest('[data-view]'); if (b) { s.view = b.dataset.view; draw(); } });
    el.querySelector('#gonly').addEventListener('change', e => { s.only = e.target.checked; draw(); });
    draw();
  } };
}
