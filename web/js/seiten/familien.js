// Word families: the list (#familien) and one family (#familie/<root>), each with its pixel book.
import { LEVELS, forms, meaning, sortkey, norm } from '../daten.js';
import { h, html, hero, seg, link, speakButton } from '../hilfe.js';

const STEP = 24;
export const cover = (D, root) => `img/buch-${(D.familyIndex.get(root) ?? 0) % 8 + 1}.svg`;

function split(e) {
  const pre = (e.prefix || '').replace(/-$/, '');
  const refl = e.word.startsWith('sich ');
  const core = refl ? e.word.slice(5) : e.word;
  return pre && core.startsWith(pre) ? { refl, pre, rest: core.slice(pre.length) } : { refl, pre: '', rest: core };
}

export function render(D, args) {
  return args.length && args[0] ? detail(D, args[0]) : list(D);
}

function list(D) {
  const ctrl = h`<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
    <label for="fq" class="vh">Familie suchen</label>
    <input id="fq" class="search" type="search" placeholder="Grundwort, z. B. halten" style="width:230px;height:40px;font-size:15px">
    <div class="segs" id="fsort"></div></div>`;
  const view = h`
    <nav class="path" aria-label="Pfad"><a href="${link.vokabular()}">Vokabular</a> › <span class="here">Wortfamilien</span></nav>
    ${hero('familien', 'Wortfamilien', `${D.families.length} Familien mit mindestens zwei Wörtern im Regal`, ctrl)}
    <div class="grid4" id="fams"></div>
    <button type="button" class="more" id="more" hidden></button>`;
  return { title: 'Wortfamilien', view, mount: el => {
    const s = { q: '', sort: 'gross', shown: STEP };
    const draw = () => {
      const q = norm(s.q.trim());
      let fams = D.families.filter(([r]) => !q || norm(r).includes(q));
      if (s.sort === 'az') fams = fams.slice().sort((a, b) => sortkey(a[0]).localeCompare(sortkey(b[0])));
      el.querySelector('#fsort').innerHTML = html(h`${seg([['gross', 'größte zuerst'], ['az', 'A bis Z']], s.sort, 'sort')}`);
      el.querySelector('#fams').innerHTML = fams.length ? html(h`${fams.slice(0, s.shown).map(([r, es]) => {
        const base = es.find(e => e.word === r || e.word === 'sich ' + r);
        const others = es.filter(e => e !== base).map(e => e.word);
        const more = others.length - 4;
        return h`<a class="card fam" href="${link.familie(r)}">
          <img src="${cover(D, r)}" alt="" width="42" height="54">
          <span style="display:flex;justify-content:space-between;align-items:baseline;gap:8px"><span class="de" style="font-size:21px;font-weight:600">${r}</span><span class="vt" style="font-size:24px;color:var(--muted)">${es.length}</span></span>
          <span class="en-d" style="font-size:15px">${base ? meaning(base) : ''}</span>
          <span class="de" style="font-size:13px;color:var(--muted);line-height:1.35">${others.slice(0, 4).join(', ')}${more > 0 ? ` und ${more} mehr` : ''}</span>
        </a>`; })}`) : '<div style="color:var(--tx2);font-size:15px">Keine Familie mit diesem Grundwort.</div>';
      const rest = fams.length - s.shown, m = el.querySelector('#more');
      m.hidden = rest <= 0; m.textContent = `Weitere ${Math.min(STEP, rest)} zeigen (von ${rest})`;
    };
    el.querySelector('#fq').addEventListener('input', e => { s.q = e.target.value; s.shown = STEP; draw(); });
    el.addEventListener('click', e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.sort) { s.sort = b.dataset.sort; draw(); }
      if (b.id === 'more') { s.shown += STEP; draw(); }
    });
    draw();
  } };
}

function detail(D, root) {
  const fam = D.families.find(([r]) => r === root);
  if (!fam) return { title: 'Nicht gefunden', view: h`<div class="loading">Diese Wortfamilie gibt es nicht. <a href="${link.familien()}">Alle Wortfamilien</a></div>` };
  const es = fam[1].slice().sort((a, b) => LEVELS.indexOf(a.level) - LEVELS.indexOf(b.level) || a._key.localeCompare(b._key));
  const base = es.find(e => e.word === root || e.word === 'sich ' + root);
  const rest = es.filter(e => e !== base);
  const groups = [
    ['trennbar', 'Das Präfix geht ans Satzende: Ich nehme dich mit.', rest.filter(e => e.type === 'verb' && e.is_separable)],
    ['untrennbar', 'Das Präfix bleibt am Verb: Ich übernehme das.', rest.filter(e => e.type === 'verb' && !e.is_separable && e.prefix)],
    ['andere Wörter', 'Weitere Wörter aus derselben Familie.', rest.filter(e => e.type !== 'verb' || !e.prefix)],
  ].filter(g => g[2].length);
  const view = h`
    <nav class="path" aria-label="Pfad"><a href="${link.vokabular()}">Vokabular</a> › <a href="${link.familien()}">Wortfamilien</a> › <span class="here">${root}</span></nav>
    <header class="famhead">
      <img src="${cover(D, root)}" alt="" width="84" height="108">
      <div style="display:flex;flex-direction:column;gap:4px">
        <div class="lab">Wortfamilie</div>
        <h1 class="de" style="margin:0;font-size:56px;font-weight:600;line-height:1;color:var(--title)">${root}</h1>
      </div>
      ${base ? h`<div style="display:flex;flex-direction:column;gap:2px;padding-bottom:6px">
        <span class="de" style="font-size:18px;color:var(--tx2)">${forms(base)}</span>
        <span class="en-d" style="font-size:18px">${meaning(base)}</span>
        <a href="${link.wort(base.id)}" style="font-size:14px">zum Wort →</a>
      </div>` : ''}
      <div style="margin-left:auto;padding-bottom:6px;text-align:right"><span class="vt" style="font-size:40px">${es.length}</span> <span style="color:var(--tx2)">Wörter im Regal</span></div>
    </header>
    ${groups.map(([title, hint, items]) => h`<section style="display:flex;flex-direction:column;gap:12px">
      <div class="grouphead"><h2 class="sec" style="font-size:34px">${title}</h2><span class="vt" style="font-size:24px;color:var(--muted)">${items.length}</span><span class="de" style="font-size:16px;color:var(--tx2)">${hint}</span></div>
      <div class="grid3">${items.map(e => { const p = split(e); return h`<a class="card member" href="${link.wort(e.id)}">
        <span style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">
          <span class="de" style="font-size:22px;line-height:1.1">${p.refl ? h`<span style="color:var(--muted)">sich </span>` : ''}<b class="pre">${p.pre}</b>${p.rest}</span>
          <span class="lv">${e.level}</span></span>
        <span class="de" style="font-size:13px;color:var(--muted)">${forms(e)}</span>
        <span class="en-d" style="font-size:16px">${meaning(e)}</span></a>`; })}</div>
    </section>`)}
    <a href="${link.familien()}" style="font-size:15px">← alle Wortfamilien</a>`;
  return { title: 'Wortfamilie ' + root, view };
}
