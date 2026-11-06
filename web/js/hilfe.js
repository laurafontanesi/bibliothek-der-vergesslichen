// Small helpers shared by the pages: escaping, links, the speaker, the header picture.

export function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}
// Tagged template: values are escaped unless they were made by h`` or raw(). Markup is recognised by
// its class, which only this module can create: data read from JSON or from the browser's storage can
// never pass for markup (an object with a property of the same name could).
class Markup { constructor(s) { this.s = s; } }
const put = v => v instanceof Markup ? v.s : esc(v);
export function h(strings, ...vals) {
  let out = strings[0];
  vals.forEach((v, i) => {
    out += Array.isArray(v) ? v.map(put).join('') : put(v);
    out += strings[i + 1];
  });
  return new Markup(out);
}
export function raw(s) { return new Markup(s ?? ''); }
// a link target from the data: only https (and links within the site)
export function safeUrl(u) { u = String(u || '').trim(); return /^https:\/\//i.test(u) || u.startsWith('#') ? u : '#'; }
export function html(x) { return x instanceof Markup ? x.s : esc(x); }

export const link = {
  start: () => '#start',
  vokabular: (q) => '#vokabular' + (q ? '?' + new URLSearchParams(q) : ''),
  wort: id => '#wort/' + encodeURIComponent(id),
  familien: () => '#familien',
  familie: root => '#familie/' + encodeURIComponent(root),
  grammatik: () => '#grammatik',
  thema: (id, cell) => '#grammatik/' + encodeURIComponent(id) + (cell ? '/' + encodeURIComponent(cell) : ''),
};

// The speaker: the browser's German voice (Web Speech API). Buttons carry data-say="...".
export const SPEAKER = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" aria-hidden="true"><path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/></svg>';
export function speakButton(text, label = 'anhören', cls = 'say') {
  return h`<button type="button" class="${cls}" data-say="${text}" aria-label="${label}" title="${label}">${raw(SPEAKER)}</button>`;
}
let voice = null, chosen = null;
try { chosen = localStorage.getItem('gv-stimme'); } catch (e) { /* no storage */ }
// the German voices of this device; one chosen in Üben is kept for the next visit
export function voices() {
  return window.speechSynthesis ? speechSynthesis.getVoices().filter(v => v.lang && v.lang.startsWith('de')) : [];
}
function pickVoice() {
  const vs = voices();
  voice = (chosen && vs.find(v => v.name === chosen)) || vs.find(v => /Anna|Premium|Enhanced/.test(v.name)) || vs[0] || null;
}
export function setVoice(name) {
  chosen = name || null;
  try { if (chosen) localStorage.setItem('gv-stimme', chosen); else localStorage.removeItem('gv-stimme'); } catch (e) { /* no storage */ }
  pickVoice();
}
export function chosenVoice() { return chosen; }
if (typeof window !== 'undefined' && window.speechSynthesis) { pickVoice(); speechSynthesis.onvoiceschanged = pickVoice; }
export function speak(text) {
  if (!window.speechSynthesis) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = 'de-DE'; if (voice) u.voice = voice; u.rate = 0.95;
  speechSynthesis.speak(u);
}
// (only in the browser: the tests in tests/web/ import this module in Node)
if (typeof document !== 'undefined') document.addEventListener('click', e => {
  const b = e.target.closest('[data-say]');
  if (b) { e.preventDefault(); speak(b.dataset.say); }
});

// The header picture, never cropped. On the phone a darker picture of its own, with the title on top.
// The pixel pictures, with their original file names.
const PHONE_SHELF = ['img/pxArt_worfamilien_konnectoren_mobile_fadeout.png', 1200, 750];
export const PICTURES = {
  start: ['img/pxArt_main_web.png', 4000, 1640, 'Eine dunkle Bibliothek bei Nacht: hohe Bücherregale mit Lichterketten und Pflanzen, eine Tischlampe, ein kleiner Tisch mit Tee, ein blauer Ohrensessel mit Decke und ein roter Teppich', ['img/pxArt_main_mobile_gradient.png', 1000, 750]],
  vokabular: ['img/pxArt_vocabulary_web.png', 4000, 1039, 'Bücherregale mit Lichterketten, eine Tischlampe und eine große Pflanze in einem blauen Topf', ['img/pxArt_vocabulary_mobile_fadeout.png', 1000, 750]],
  grammatik: ['img/pxArt_grammar_web.png', 4000, 1039, 'Bücherregale mit Lichterketten, eine Tischlampe und Pflanzen in Töpfen auf einem roten Teppich', ['img/pxArt_grammar_mobile_fadeout.png', 1000, 750]],
  familien: ['img/pxArt_wortfamilien_web.png', 4000, 1039, 'Ein Bücherregal mit Lichterketten und Pflanzen', PHONE_SHELF],
  konnektoren: ['img/pxArt_konnectoren_web.png', 4000, 1039, 'Ein Bücherregal mit Lichterketten', PHONE_SHELF],
};

export function hero(key, title, sub, extra, top = 44) {
  const [src, w, hgt, alt, [ps, pw, ph]] = PICTURES[key];
  return h`<section class="hero" style="aspect-ratio:${w}/${hgt}">
    <img class="hero-ph" src="${ps}" alt="" width="${pw}" height="${ph}">
    <div class="hero-img"><img src="${src}" alt="${alt}" width="${w}" height="${hgt}"><div class="shade"></div></div>
    <div class="hero-in" style="top:${top}px">
      <h1 class="vt hero-t">${title}</h1>
      ${sub ? h`<p class="hero-sub">${sub}</p>` : ''}
      ${extra || ''}
    </div>
  </section>`;
}

// A row of toggle buttons
export function seg(options, current, attr) {
  return options.map(([id, label]) =>
    h`<button type="button" class="seg${id === current ? ' on' : ''}" data-${raw(attr)}="${id}" aria-pressed="${String(id === current)}">${label}</button>`);
}

export function freqDots(f) {
  f = f || 0;
  return '●'.repeat(f) + '○'.repeat(Math.max(0, 6 - f));
}
