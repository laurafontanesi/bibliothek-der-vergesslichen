# Bibliothek der Vergesslichen

A library for learning German: a collection of words and grammar topics, with pages to browse them and cards to practise them.

**Live site:** https://laurafontanesi.github.io/bibliothek-der-vergesslichen/

## What is where

| Folder | What it holds | More |
|---|---|---|
| `web/` | the website, published as it is (no build step) | [web/README.md](web/README.md) |
| `web/data/` | the data: `words.json`, `grammar.json`, `schema.json`, and the generated `karten.json` and `grammar_cards.json` | [web/data/README.md](web/data/README.md) |
| `vocab_builder/` | the Python tools that add words, check sentences and build the cards | [vocab_builder/README.md](vocab_builder/README.md) |
| `tests/` | the smoke test (`python tests/smoke.py`) and the website tests | |
| `private/` | downloads from others and personal files; never in git | |

## Run it locally

```bash
cd web && python3 -m http.server     # then open http://localhost:8000/
```

After a change to the data, rebuild the cards and run the smoke test:

```bash
python -m vocab_builder karten
python -m vocab_builder grammar cards
python tests/smoke.py
```

Every push to `main` publishes `web/` as the site (`.github/workflows/pages.yml`).

## Licences and sources

- Code: MIT ([LICENSE](LICENSE)).
- Data in `web/data/`: CC BY-SA 4.0; pictures in `web/img/`: CC0 ([LICENSE-DATA.md](LICENSE-DATA.md)).
- Fonts: SIL Open Font License ([web/fonts/README.md](web/fonts/README.md)).
- The sources of the data, and which parts are written with AI: the page "Quellen und Nutzung" on the site, and [web/data/README.md](web/data/README.md).
