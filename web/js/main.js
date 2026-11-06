// The library: one page, the address after # says what is shown.
//   #start                        the entrance
//   #vokabular?niveau=B1&thema=…  the word list
//   #wort/<id>                    one word
//   #familien, #familie/<root>    the word families
//   #grammatik, #grammatik/<topic>[/<cell>]
//   #ueben                        the cards: words, collocations, grammar
//   #notizen                      the notes on what should change (cards, words, grammar)
//   #quellen                      sources, licences, terms of use, privacy
import { loadAll } from './daten.js';
import { html } from './hilfe.js';
import * as start from './seiten/start.js';
import * as vokabular from './seiten/vokabular.js';
import * as wort from './seiten/wort.js';
import * as familien from './seiten/familien.js';
import * as grammatik from './seiten/grammatik.js';
import * as thema from './seiten/thema.js';
import * as ueben from './seiten/ueben.js';
import * as notizen from './seiten/notizen.js';
import * as quellen from './seiten/quellen.js';
import { badge } from './notizen.js';

const app = document.getElementById('app');
let D = null;

function parse() {
  const raw = location.hash.replace(/^#/, '') || 'start';
  const [path, query] = raw.split('?');
  const parts = path.split('/').map(decodeURIComponent);
  return { parts, query: new URLSearchParams(query || '') };
}

const ROUTES = {
  start: { page: start, nav: 'start' },
  vokabular: { page: vokabular, nav: 'vokabular' },
  wort: { page: wort, nav: 'vokabular' },
  familien: { page: familien, nav: 'vokabular' },
  familie: { page: familien, nav: 'vokabular' },
  grammatik: { page: null, nav: 'grammatik' },
  ueben: { page: ueben, nav: 'ueben' },
  notizen: { page: notizen, nav: 'notizen' },
  quellen: { page: quellen, nav: 'quellen' },
};

function show() {
  document.body.classList.remove('uebung');      // the practice screen hides the menu until the next page
  try {
    // inside the try: a broken address (#wort/%E0) shows the "not found" page instead of nothing
    const { parts, query } = parse();
    const route = ROUTES[parts[0]] || ROUTES.start;
    let page = route.page;
    if (parts[0] === 'grammatik') page = parts[1] ? thema : grammatik;
    document.querySelectorAll('[data-nav]').forEach(a => a.classList.toggle('on', a.dataset.nav === route.nav));
    const out = page.render(D, parts.slice(1), query);
    // a fresh element per page, so the listeners of the page before go with it
    const root = document.createElement('div');
    root.className = 'view';
    root.innerHTML = html(out.view);
    app.replaceChildren(root);
    document.title = (out.title ? out.title + ' · ' : '') + 'Bibliothek der Vergesslichen';
    if (out.mount) out.mount(root);
  } catch (err) {
    console.error(err);
    app.innerHTML = '<div class="loading">Diese Seite gibt es nicht. <a href="#start">Zum Eingang</a></div>';
  }
}

window.addEventListener('hashchange', () => { window.scrollTo(0, 0); show(); });

badge();
loadAll().then(d => { D = d; show(); }).catch(err => {
  console.error(err);
  app.innerHTML = '<div class="loading">Die Daten konnten nicht geladen werden. Öffne die Seite über einen Webserver '
    + '(im Ordner web: <code>python3 -m http.server</code>, dann http://localhost:8000/).</div>';
});
