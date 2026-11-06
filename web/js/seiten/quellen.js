// #quellen: where the data comes from, under which terms, how the site may be used, and what it
// stores (required by the licences of Wiktionary, Tatoeba, Morphy and the fonts).
import { h, link } from '../hilfe.js';

const EXT = (url, text) => h`<a href="${url}" target="_blank" rel="noopener">${text} ↗</a>`;

const QUELLEN = [
  ['DWDS – Digitales Wörterbuch der deutschen Sprache', 'https://www.dwds.de/', 'Berlin-Brandenburgische Akademie der Wissenschaften',
    'Häufigkeitsklasse und Link jedes Worts (aus der Lemmadatenbank, offline); bei einzelnen Wörtern die deutsche Definition, als Zitat mit Link.',
    'Nutzungsbedingungen des DWDS; Zitate mit Quellenangabe'],
  ['Wiktionary (deutsche Ausgabe)', 'https://de.wiktionary.org/', 'über kaikki.org',
    'Die meisten deutschen Definitionen.', 'CC BY-SA 3.0 und GFDL'],
  ['Morphy / LanguageTool', 'https://danielnaber.de/morphologie/', 'Daniel Naber',
    'Prüfung der Verb- und Nomenformen, Konjugationstabellen auf den Karten.', 'CC BY-SA 4.0'],
  ['Tatoeba', 'https://tatoeba.org/', 'Tatoeba-Gemeinschaft',
    'Ein Teil der Übungssätze; jeder mit seiner Tatoeba-Nummer und einem Link.', 'CC BY 2.0 FR'],
  ['Goethe-Zertifikat Wortlisten A1 bis B1', 'https://www.dwds.de/lemma/wortschatz-goethe-zertifikat', 'Goethe-Institut, über das DWDS',
    'Nur das Niveau (A1, A2, B1) eines Worts. Die Listen selbst sind nicht Teil der Bibliothek.', 'urheberrechtlich geschützt (Goethe-Institut)'],
  ['Schriften: VT323, Zilla Slab, Roboto Condensed, Source Code Pro', 'https://fonts.google.com/', 'über Google Fonts, auf dieser Seite selbst gespeichert',
    'Die Schriften der Seite.', 'SIL Open Font License 1.1'],
];

export function render() {
  const view = h`
    <nav class="path" aria-label="Pfad"><a href="${link.start()}">Bibliothek</a> › <span class="here">Quellen und Nutzung</span></nav>
    <section class="panel uset qtext">
      <h1 class="sec">Quellen und Nutzung</h1>
      <p>Die Bibliothek der Vergesslichen ist ein privates Lernprojekt ohne kommerziellen Zweck: eine wachsende Sammlung deutscher Wörter und Grammatik, mit Übungen.</p>

      <h2 class="sec">Quellen</h2>
      <div class="qlist">${QUELLEN.map(([name, url, wer, was, lizenz]) => h`<div class="qrow">
        <div>${EXT(url, name)} <span class="lab">${wer}</span></div>
        <div>${was}</div>
        <div class="lab">Lizenz: ${lizenz}</div></div>`)}</div>
      <p><b>Mit KI erstellt:</b> viele englische Bedeutungen, Notizen, Beispiel- und Übungssätze und Kollokationen wurden mit einem KI-Modell (Claude, Anthropic) geschrieben und danach geprüft, aber nicht alle von Hand. Sie können Fehler enthalten.</p>
      <p><b>Bilder:</b> die Pixelbilder der Bibliothek hat Laura Fontanesi mit Gemini (KI von Google) erstellt und mit ${EXT('https://giventofly.github.io/pixelit/', 'Pixel It')} in Pixelgrafik umgewandelt; die Bücher der Wortfamilien und die Bilder zu den Präpositionen wurden mit Claude (KI) gemacht.</p>

      <h2 class="sec">Lizenz</h2>
      <p>Die Wort- und Grammatikdaten stehen unter ${EXT('https://creativecommons.org/licenses/by-sa/4.0/deed.de', 'CC BY-SA 4.0')} (Namensnennung, Weitergabe unter gleichen Bedingungen), der Programmcode unter der MIT-Lizenz. Die Bilder sind frei verwendbar (CC0, gemeinfrei); die Schriften stehen unter der SIL Open Font License. Einzelheiten im ${EXT('https://github.com/laurafontanesi/bibliothek-der-vergesslichen', 'Repository')} (LICENSE, LICENSE-DATA.md).</p>

      <h2 class="sec">Nutzung</h2>
      <p>Alle Inhalte sind ohne Gewähr: die Bibliothek ist ein Lernwerkzeug, kein geprüftes Wörterbuch. Wer die Daten weiterverwendet, nennt die Quelle und gibt Änderungen unter derselben Lizenz weiter.</p>
      <p>Diese Seite soll nicht in Suchmaschinen erscheinen; sie teilt das Suchmaschinen mit, ob sie sich daran halten, liegt bei ihnen. Die Daten und Bilder dürfen unter ihren Lizenzen weiterverwendet werden, auch automatisiert.</p>

      <h2 class="sec">Datenschutz</h2>
      <p>Die Seite setzt keine Cookies, zählt keine Besuche und lädt nichts von anderen Anbietern: Schriften und Daten kommen von dieser Seite selbst. Die Seite wird von GitHub Pages ausgeliefert; GitHub verarbeitet dabei technische Daten wie die IP-Adresse (${EXT('https://docs.github.com/de/site-policy/privacy-policies/github-general-privacy-statement', 'Datenschutzerklärung von GitHub')}).</p>
      <p>Notizen, Lernstand und Einstellungen bleiben in deinem Browser, auf deinem Gerät. Sie werden nirgendwohin gesendet; du kannst sie als Datei sichern oder in den Einstellungen des Browsers löschen. Das Vorlesen nutzt die Stimmen deines Geräts; manche Online-Stimmen schicken den vorgelesenen Text an ihren Anbieter.</p>
    </section>`;
  return { title: 'Quellen und Nutzung', view };
}
