# The website

A single page with plain JavaScript modules and no build step. It reads the JSON files in `data/` directly, so it is always up to date with the data.

Locally: `python3 -m http.server` in this folder, then http://localhost:8000/.

## Pages

The address after `#` chooses the page (`js/main.js`); each page has its file in `js/seiten/`.

| Address | Page |
|---|---|
| `#start` | the entrance: word search in both directions, levels, newest words, word families |
| `#vokabular` | the word list with search, filters and order; the filters stay in the address (`#vokabular?niveau=B1`) |
| `#wort/<id>` | one word, by its id in `words.json` (`#wort/der-aufzug`) |
| `#familien`, `#familie/<root>` | the word families, and one family (`#familie/nehmen`) |
| `#grammatik`, `#grammatik/<topic>`, `#grammatik/<topic>/<form>` | the grammar topics, one topic, one form |
| `#ueben` | the practice cards |
| `#notizen` | your notes on what should change |
| `#quellen` | sources, licences, terms of use, privacy |

## Files

- `js/daten.js` loads the data and derives what the pages count and list.
- `js/schema.js` holds the lists shared with Python (levels, word types, kinds of related word, topics). It is generated from `data/schema.json` by `python -m vocab_builder karten`; do not edit it by hand.
- `js/hilfe.js` has the small helpers every page uses, among them the escaping of values (see Security).
- `css/bibliothek.css` is the whole look; `fonts/` the fonts, served from the site ([fonts/README.md](fonts/README.md)).
- `img/` the pictures: the pixel pictures (`pxArt_*`) were made by Laura Fontanesi with Gemini (Google's AI) and turned into pixel art with [Pixel It](https://giventofly.github.io/pixelit/); the books of the word families (`buch-*.svg`) and the pictures in `img/praep/` were made with Claude (AI).

## Practising

- The cards come from `data/karten.json` (word and collocation cards) and `data/grammar_cards.json` (grammar cards), both written by `vocab_builder`.
- `js/seiten/ueben.js` chooses the cards; `js/seiten/karte.js` draws a card; `js/pruefen.js` checks the typed answer (case does not count, and on the Bedeutung card any listed English meaning counts).
- Under a wrong answer, one line says why the right answer is right (`js/seiten/warum.js`).
- The schedule is FSRS-6 with its default parameters (`js/fsrs.js`; [open-spaced-repetition](https://github.com/open-spaced-repetition)). Every answer is kept per card in the browser (`js/lernstand.js`), and the state of a card is always computed again from its answers. "Lernstand als Datei sichern" saves the answers as a file; "Lernstand laden" adds the ones from a file that are new.
- Notes on what should change (`js/notizen.js`) can be written on every card, word page and grammar page; they stay in the browser and can be saved as a file from `#notizen`.
- The speaker buttons use the browser's German voice.

## Security

- Values are escaped unless they are markup made by the page code itself (`h` and `raw` in `js/hilfe.js`): text from the data or from the browser's storage can never pass for markup.
- The card fields are cleaned when the cards are built (`vocab_builder/sanitize.py`): only the build's own tags, and links to https only. Links from the data go through `safeUrl`.
- A content security policy in `index.html` allows only the site's own scripts, styles and fonts.
- The page asks not to be listed by search engines (`noindex`).

## Tests

`node --test 'tests/web/*.test.js'` from the repository root (Node 22 or later). The smoke test runs them too.
