// One word, on paper: forms, meanings, examples, collocations, notes; on the side the related words,
// the word family, the grammar topics the word itself belongs to, and its topics.
import { TYPE_DE, KIND_DE, KIND_ORDER, TOPIC_DE, forms, notes } from '../daten.js';
import { h, raw, link, speakButton, freqDots, safeUrl } from '../hilfe.js';
import { button as notizKnopf } from '../notizen.js';


export function render(D, [id]) {
  const e = D.byId.get(id);
  if (!e) return { title: 'Nicht gefunden', view: h`<div class="loading">Dieses Wort steht nicht im Regal. <a href="${link.vokabular()}">Zum Vokabular</a></div>` };
  const fam = e.family_root && D.families.find(([r]) => r === e.family_root);
  const rel = {};
  for (const r of e.related || []) (rel[r.kind] = rel[r.kind] || []).push(r);
  const gram = [...(D.wordGrammar.get(e.id) || new Map()).values()];
  const ns = notes(e.notes);
  const f = forms(e);
  const freq = e.dwds && e.dwds.freq;

  const view = h`
  <nav class="path" aria-label="Pfad"><a href="${link.vokabular()}">Vokabular</a> › <a href="${link.vokabular({ niveau: e.level })}">${e.level}</a> › <span class="here">${e.word}</span></nav>
  <article class="paper px entry">
    <div>
      <header class="head">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap"><h1 class="de">${e.word}</h1>${speakButton(e.word, 'Wort anhören')}</div>
        ${f ? h`<div class="de" style="font-size:20px;color:var(--ink2)">${f}</div>` : ''}
        <div class="meta">
          <span class="lv">${e.level}</span><span>${TYPE_DE[e.type] || e.type}</span>
          ${e.preposition ? h`<span class="de" style="color:var(--ink)">mit ${e.preposition}</span>` : ''}
          ${e.dwds && e.dwds.url ? h`<a href="${safeUrl(e.dwds.url)}" target="_blank" rel="noopener">DWDS ↗</a>` : ''}
          ${freq !== undefined && freq !== null ? h`<span title="Häufigkeit laut DWDS, 0 bis 6" style="letter-spacing:2px;color:var(--ink)">${freqDots(freq)}</span><span>Häufigkeit</span>` : ''}
        </div>
      </header>

      <section>
        <h2 class="sec">Bedeutungen</h2>
        <ol class="defs">${(e.definitions || []).map((d, i) => h`
          <li><span class="vt" style="font-size:22px;color:var(--ink2)">${i + 1}.</span>
            <span><span class="en" style="font-size:19px">${d.meaning}</span>${d.note ? h` <span class="de" style="font-size:15px;color:var(--ink2)">(${d.note})</span>` : ''}</span>
            ${i === 0 && e.definition_de ? h`<span></span><span class="de" style="font-size:16px"><b class="dlab">DE</b>${e.definition_de}</span>` : ''}
          </li>`)}</ol>
      </section>

      ${(e.examples || []).length ? h`<section>
        <h2 class="sec">Beispiele</h2>
        ${e.examples.map(x => h`<div class="ex">${speakButton(x.de, 'Satz anhören')}<span class="de" style="font-size:18px">${x.de}</span><span></span><span class="en" style="font-size:16px">${x.en}</span></div>`)}
      </section>` : ''}

      ${(e.collocations || []).length ? h`<section>
        <h2 class="sec">Kollokationen</h2>
        ${e.collocations.map(c => h`<div class="coll">
          <div><span class="de" style="font-size:18px;font-weight:600">${c.de}</span> ${speakButton(c.de, 'anhören')} <span class="en" style="font-size:16px">${c.en}</span></div>
          ${c.example ? h`<div class="de" style="font-size:16px">${c.example.de} <span class="en" style="font-size:15px">${c.example.en}</span></div>` : ''}
        </div>`)}
      </section>` : ''}

      ${ns.length ? h`<section>
        <h2 class="sec">Notizen</h2>
        <ul class="notes">${ns.map(n => h`<li>${n}</li>`)}</ul>
      </section>` : ''}
    </div>

    <aside>
      <section>
        <h2 class="sec">Verwandte Wörter</h2>
        ${Object.keys(rel).length ? '' : h`<div style="font-size:14px;color:var(--ink2)">Keine.</div>`}
        ${KIND_ORDER.filter(k => rel[k]).map(k => h`<div style="display:flex;flex-direction:column;gap:4px">
          <div class="rlab">${KIND_DE[k]}</div>
          <div class="chips">${rel[k].map(r => { const t = D.byWord.get(r.word);
            return t ? h`<a class="pchip de" href="${link.wort(t.id)}">${r.word}<span class="vt">${t.level}</span></a>`
                     : h`<span class="pchip de" style="border-style:dashed">${r.word}</span>`; })}</div>
        </div>`)}
        ${fam ? h`<a href="${link.familie(fam[0])}" style="font-size:15px;margin-top:4px">Wortfamilie <b class="de">${fam[0]}</b> (${fam[1].length} Wörter) →</a>` : ''}
      </section>
      ${gram.length ? h`<section>
        <h2 class="sec">In der Grammatik</h2>
        ${gram.map(g => h`<a href="${link.thema(g.topic, g.cells[0])}" style="font-size:15px">${g.name}: <span class="de">${g.cells.slice(0, 3).join(' / ')}</span> →</a>`)}
      </section>` : ''}
      ${(e.topics || []).length ? h`<section>
        <h2 class="sec">Thema</h2>
        <div class="chips">${e.topics.map(t => h`<a class="pchip plain" href="${link.vokabular({ thema: t })}">${TOPIC_DE[t] || t}</a>`)}</div>
      </section>` : ''}
      <section>${notizKnopf({ wo: 'wort', id: e.id, label: e.word }, 'Notiz zu diesem Wort')}</section>
    </aside>
  </article>`;
  return { title: e.word, view };
}
