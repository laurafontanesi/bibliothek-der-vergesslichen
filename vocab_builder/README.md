# vocab_builder

The Python tools that maintain the data in `web/data/`: adding and editing words, checking exercise sentences, the grammar topics, and building the cards for the website. Run them from the repository root:

```bash
python -m vocab_builder help                 # all word commands
python -m vocab_builder grammar <command>    # the grammar commands (below)
```

Needs Python 3.10 or later. Adding words with AI needs an Anthropic API key; the checks and the card build need the Morphy lexicon (see Setup).

## Words

```bash
python -m vocab_builder add                # add a word, with AI suggestions you confirm one by one
python -m vocab_builder add --manual       # add a word without AI
python -m vocab_builder edit nehmen        # edit an entry (meanings, examples, notes, forms, collocations)
python -m vocab_builder show nehmen        # the full entry
python -m vocab_builder list --type verb   # list words, also by --topic
python -m vocab_builder family nehmen      # the words of a verb family
python -m vocab_builder exercises nehmen   # check the exercise sentences of a word, fill or replace them
python -m vocab_builder delete nehmen
```

**Adding a word.** First the word and your own sentence, the one where you met it (optional). The AI then suggests the canonical form, the word type and its forms, the meanings, two examples, topics and a note; your sentence decides which meaning comes first and becomes the first example. You confirm or change each suggestion. With the files in `private/sources/`, the forms are checked against the lexicon and the German definition, the DWDS link and the level are filled in by themselves.

**Related words.** The AI names related German words without seeing your list, and only those already in `words.json` are kept; words related by their spelling (*das Bild / der Bildschirm*) are proposed offline. Links are always kept in both directions: `python -m vocab_builder links` drops links to missing words and adds missing back-links (`--dry-run` only reports).

**Exercise sentences.** Verbs get gap-fill sentences for the forms that cannot be predicted from a rule (Präteritum, Perfekt, Präsens with a stem change, the reflexive pronoun). They are taken, in this order, from the exercises the word already has, your own sentence, the other examples, and only then from the AI. Every sentence goes through the checker (`checks.py`) before it is kept; you see the list and can replace any sentence.

## Grammar

```bash
python -m vocab_builder grammar status      # the curriculum per level and the topics
python -m vocab_builder grammar cells dekl  # the cells of a topic with their sentences
python -m vocab_builder grammar check       # run the checker again on every grammar sentence
python -m vocab_builder grammar add prep_fixed "sich freuen" "Ich freue mich [auf] [den] Urlaub." "I am looking forward to the holiday."
python -m vocab_builder grammar cards       # write web/data/grammar_cards.json
```

`grammar add` adds a checked sentence for a connector (`konnektoren`) or for a word's fixed preposition (`prep_fixed`); the part to hide goes in [brackets].

## The cards and the checks

```bash
python -m vocab_builder karten   # web/data/karten.json and web/js/schema.js
python tests/smoke.py            # imports, cards up to date, website tests, every sentence verdict
```

Run both after any change to `words.json` or `grammar.json`, and commit the generated files with the data. The smoke test says when a generated file is out of date and needs no API key.

Other commands: `dwds` (DWDS link and frequency class of every word), `levels` (the level of every word), `lexikon <word>` (a word's entry in the lexicon), `topics`.

## Code

| Where | What |
|---|---|
| `cli.py`, `__main__.py` | the word commands |
| `model.py`, `paths.py`, `schema.py` | loading and saving `words.json`, where the files are, the lists shared with the website |
| `claude.py` | the calls to the AI |
| `checks.py`, `exercises.py`, `deps.py` | the sentence checker and the exercises of a word |
| `lexicon.py`, `dwds.py`, `levels.py` | the lexicon and Wiktionary lookups, the DWDS link, the level |
| `links.py` | keeping the related links consistent |
| `sanitize.py` | the whitelist cleaner for the HTML in the card fields |
| `grammar/` | `grammar.json`: one module per topic (`dekl`, `kasus`, `fromwords`), the card fronts (`cue`, `gap_en`) and the grammar commands |
| `karten/` | the cards for the website: `word_cards`, `grammar_cards` (grammar and collocation cards), `web` (writes the files) |

## Setup

**API key.** Looked up in this order: the `ANTHROPIC_API_KEY` environment variable; a `.env` file (`ANTHROPIC_API_KEY=sk-ant-...`) at the path written in `private/personal/api_env.txt`, so the key can live outside the repository; a `.env` next to `words.json` (ignored by git).

**Sources.** `private/sources/` holds one folder per downloaded source, each with a `LICENCE.md`; `private/README.md` is the index. The sources themselves are described in [web/data/README.md](../web/data/README.md). The Morphy lexicon has to be produced once (Java 8 or later):

```bash
# from the german-pos-dict folder, with LanguageTool stand-alone downloaded for its libs/ folder:
java -cp "/path/to/LanguageTool/libs/*" morfologik.tools.DictDecompile \
     -i src/main/resources/org/languagetool/resource/de/german.dict -o dictionary.dump
# then move dictionary.dump into private/sources/morphy/
```

Without it, `add`, `edit` and `exercises` skip the checks and say so; `karten` and the smoke test stop with a message.
