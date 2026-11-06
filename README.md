# Bibliothek der Vergesslichen

A personal German vocabulary app — a live website for browsing and practising words, backed by a JSON database managed from the command line.

**Live site:** https://laurafontanesi.github.io/bibliothek-der-vergesslichen/

---

## Project structure

```
bibliothek-der-vergesslichen/
├── README.md, LICENSE (code, MIT), LICENSE-DATA.md (data CC BY-SA 4.0, pictures CC0), .gitignore
├── .github/workflows/pages.yml  ← publishes web/ as the site on every push
├── web/                    ← everything that is published: the website "Bibliothek der Vergesslichen"
│   ├── index.html, css/, js/, fonts/, img/
│   └── data/
│       ├── words.json          the vocabulary (all entries)
│       ├── grammar.json        the grammar curriculum and the topics of the grammar cards
│       ├── schema.json         the lists Python and the website share: levels, word types, kinds of related word, topics
│       ├── karten.json         the practice cards (generated: python -m vocab_builder karten)
│       └── grammar_cards.json  the grammar cards for the grammar pages (generated: python -m vocab_builder grammar cards)
├── vocab_builder/          ← the tools: python -m vocab_builder <command> (list: python -m vocab_builder help)
│   ├── __main__.py         the entry point: the word commands, and after "grammar" the grammar commands
│   ├── paths.py            where everything is
│   ├── schema.py           reads schema.json, writes web/js/schema.js
│   ├── model.py            words.json: load, save, ids, topics, links, families
│   ├── lexicon.py          Morphy full-form lexicon and German Wiktionary lookups
│   ├── dwds.py             DWDS link and frequency class per word, from the downloaded lemma list
│   ├── levels.py           CEFR level per word (Goethe lists, else B2+)
│   ├── sanitize.py         the whitelist cleaner for the HTML in the card fields
│   ├── links.py            keeping the related links consistent (links)
│   ├── checks.py           sentence checker, which exercises a word gets, generation prompts
│   ├── deps.py             the Morphy lexicon and the checker, loaded once
│   ├── claude.py           Claude API calls
│   ├── ui.py               terminal questions and printing an entry
│   ├── exercises.py        filling and checking a word's exercises
│   ├── cli.py              the word commands
│   ├── grammar/            grammar.json: model, one module per topic (dekl, kasus, fromwords),
│   │                       the card fronts (cue: gaps, German cue, English highlight),
│   │                       the English of a gap (gap_en), the grammar commands (cli)
│   └── karten/             the practice cards: config, text, word_cards, grammar_cards
│                           (grammar and collocation cards), web (writes web/data/karten.json)
├── tests/
│   ├── smoke.py            run after a code change: imports, cards up to date, website tests, sentence verdicts
│   ├── verdicts.json       the recorded verdict of every exercise sentence
│   └── web/                the website tests (node --test 'tests/web/*.test.js', Node 22 or later; run by smoke.py)
└── private/                ← never in git
    ├── sources/            downloads from others, one folder per source with its LICENCE.md (see Data sources)
    └── personal/           personal files: the private fields of grammar.json, notes, api_env.txt
```

---

## The website (web/)

The library, "Bibliothek der Vergesslichen". It reads `web/data/words.json`,
`grammar.json` and `grammar_cards.json` directly, so it is always up to date with the data; there is
no build step for the pages. Online at https://laurafontanesi.github.io/bibliothek-der-vergesslichen/.

Locally: `python3 -m http.server` in `web/`, then http://localhost:8000/.

| Address | Page |
|---|---|
| `#start` | the entrance: picture, word search (Deutsch → Englisch, Englisch → Deutsch), levels, newest words, largest families |
| `#vokabular` | the word list: search, filters (level; word type; for verbs regular, irregular, mixed, separable, inseparable; frequency class from DWDS; in a word family; topic; letter), order (also most frequent first), 40 at a time. The filters are kept in the address: `#vokabular?niveau=B1&konjugation=irregular` |
| `#wort/<id>` | one word, with its id from `words.json` (`#wort/der-aufzug`) |
| `#familien`, `#familie/<root>` | the word families with at least two words, and one family (`#familie/nehmen`) |
| `#grammatik`, `#grammatik/<topic>`, `#grammatik/<topic>/<form>` | the grammar topics; one topic as an overview of all its forms in tables, with a filter (`#grammatik/dekl`); one form on paper, with its table beside it (`#grammatik/konnektoren/seitdem`) |
| `#ueben` | the exercises, without login: the word cards, the collocations and the grammar topics, chosen by kind, level and order (random, most frequent first, newest first), 10, 20 or 50 at a time; at the end the mistakes, to practise again |

- `web/js/daten.js` loads the data and derives the numbers; one file per page in `web/js/seiten/`; the look is in `web/css/bibliothek.css`.
- The pixel pictures in `web/img/` (`pxArt_*`) were made by Laura Fontanesi with Gemini (Google's AI) and turned into pixel art with [Pixel It](https://giventofly.github.io/pixelit/), with their original file names, never cropped: `pxArt_*_web.png` on the computer, the darker `pxArt_*_mobile*.png` on the phone. `buch-1.svg` to `buch-8.svg` (the books of the word families) and the pictures in `web/img/praep/` were made with Claude (AI).
- The speaker buttons use the browser's German voice.
- Security: values are escaped unless they are markup made by the page code itself (`h` and `raw` in `web/js/hilfe.js`; data read from JSON or from the browser's storage can never pass for markup); the card fields are cleaned by the build (`vocab_builder/sanitize.py`: only the build's own tags, links to https only); links from the data go through `safeUrl`; a content security policy in `web/index.html` allows only the site's own scripts, styles and fonts; the fonts are served from `web/fonts/` (no request to Google); the page asks not to be listed by search engines (`noindex`); text and data mining is not reserved, since the open licences of the data and pictures allow it.
- Planned grammar topics show only how many structures are planned per level: the names of the planned structures stay private (they follow the reference checklists the list is based on).
- The exercises come from `web/data/karten.json`, written by `python -m vocab_builder karten` (`vocab_builder/karten/`; see "The cards"): every entry with the fields the website uses, the conjugation tables of the Präsens and Präteritum cards from `private/sources/morphy`, the partner of each "Welches Wort passt?" card, and the source of a sentence that is not ours (Tatoeba, shown under the sentence). The website draws the cards in its own layout (`web/js/seiten/karte.js`): no menu while practising, a progress bar with the time, a voice menu; on the front the cue in small capitals and the box inside the gap; on the back your answer, then one sheet with the principal parts and the level, the numbered meanings with the German definition, the note, the examples (the card's own sentence first), the table of a form card with the row of the sentence, the two words of "Welches Wort passt?" side by side, the related words in groups and the links. The typed answer counts when it matches, except that case does not count and on Bedeutung any listed English meaning counts. The smoke test says when `web/data/karten.json` is out of date.
- The schedule: FSRS-6 with its default parameters (`web/js/fsrs.js`; [open-spaced-repetition](https://github.com/open-spaced-repetition)). Every answer is kept per card in the browser (`web/js/lernstand.js`); the state of a card (stability, difficulty, when due) is always computed again from its answers. Wrong = Again, right = Good, right with "War leicht" = Easy; a card answered wrong comes back once more in the round. The order "fällige, dann neue" shows the due cards first. A saved Lernstand file is loaded with "Lernstand laden"; loading again only adds what is new. "Lernstand als Datei sichern" saves everything, to keep or to move to another device.
- Under a wrong answer, one line says why the right answer is right (`web/js/seiten/warum.js`), from rules and from what was typed: an irregular verb with its principal parts, a stem change in the present, the auxiliary of the Perfekt, the case of a reflexive pronoun, the wrong form for the person, a separable prefix, the gender or the plural of a noun, another word of the library typed instead (with its meaning), the case and the adjective ending of a declension (and the preposition that asks for the case), a fixed preposition, the meaning and word class of a connector. Where no rule applies, the cue is shown again.
- Notes on what should change (`web/js/notizen.js`, `#notizen`): a button on the back of every card, on every word page and on every grammar page, with ready-made reasons and your own text; on a card the note keeps your answer, the expected one and the verdict, and "Meine Antwort war auch richtig" counts the card as right. Kept in the browser; `#notizen` saves them as a file.

---

## Adding words — `vocab_builder`

Requires Python 3.10+ and an Anthropic API key (see API key setup).

```bash
# Add a new word (AI-assisted — looks up grammar, definitions, examples)
python -m vocab_builder add

# Add without AI (fully manual)
python -m vocab_builder add --manual

# Edit an existing entry (definitions, examples, notes, grammar fields…)
python -m vocab_builder edit "die Erinnerung"

# List all words
python -m vocab_builder list

# Filter by type or topic
python -m vocab_builder list --type verb
python -m vocab_builder list --topic emotions   # substring match, so 'emotions' finds 'emotions & character'

# Show full entry for a word
python -m vocab_builder show aufhören

# Show all members of a verb family
python -m vocab_builder family nehmen

# Check a word's exercise sentences, fill empty ones, replace the ones you do not like
python -m vocab_builder exercises nehmen

# Show all topics and word counts
python -m vocab_builder topics

# DWDS link and frequency class for every word, from the downloaded lemma list (offline;
# vocab_builder add and edit do it for one word by themselves)
python -m vocab_builder dwds

# CEFR level of every word (A1, A2, B1 from the Goethe lists in private/sources/goethe/, else B2+),
# with the counts per level (offline; add and edit do it for one word)
python -m vocab_builder levels

# The website's cards (web/data/karten.json, web/js/schema.js), after any change to words.json or grammar.json
python -m vocab_builder karten

# Keep the related links consistent (report only with --dry-run)
python -m vocab_builder links

# The entry of a word in the full-form lexicon (private/sources/morphy)
python -m vocab_builder lexikon nehmen

# Delete a word (asks for confirmation)
python -m vocab_builder delete aufhören
```

### AI-assisted add

After the word and its type, you are asked for **your own sentence**: the one where you met the word (Enter to skip). It is sent along to the model, so the first definition follows the meaning the word has in *your* sentence; the model also checks it and offers a correction if needed. Your sentence becomes the first example, marked `"source": "own"`, and is preferred as an exercise sentence when it contains the right form.

Then the script calls the Claude API to suggest:
- Canonical form (gender for nouns, infinitive for verbs)
- Word type, auxiliary, past tense, past participle
- Whether it's separable, reflexive, or requires a preposition
- Family root and prefix (for compound verbs)
- English definitions with usage notes
- Two natural example sentences
- Topics (0 to 2 from a closed list, often none)
- Notes, including register when it is not neutral

You confirm or override each suggestion before saving. Related words are proposed from your own database only, and linked bidirectionally.

If `private/` holds the reference files (see Data sources), the script also checks the model against them: verb forms against the lexicon (it asks when they disagree), noun gender and plural, and it fills `present_3sg`, `verb_class`, `imperative`, `konjunktiv_2` and the German definition by itself.

### Exercise sentences

`vocab_builder edit <word>`, option 9, lists, removes and adds collocations. Before the exercises, a noun asks for its **collocations**, one per line as `German = English` (optionally `= note`):
`eine Frage stellen = to ask a question`. Each becomes a Kollokation card (English to German).

Last, before the preview, the script fills the word's `exercises`: only the verb forms (Präteritum, Perfekt, Präsens, reflexive pronoun). Declension, fixed prepositions and connectors are grammar card topics in `grammar.json`, so `vocab_builder` does not write those sentences (a new connector or fixed preposition gets its grammar sentences in `grammar.json`). In this order:

1. exercises the word already has, if they still fit (only when editing);
2. **your own sentence**, if it contains a testable form (the Präteritum, the Perfekt…);
3. the other example sentences;
4. for whatever is still empty, one request to the API with fixed rules (B1/B2, 6 to 14 words, the exact form, the gap marked in brackets).

Every sentence goes through the checker (`vocab_builder/checks.py`): right verb form, a separable particle at the end of the main clause, the right auxiliary (*haben*/*sein*) for the Perfekt, determiner + adjective + noun agreeing in the case and number asked, the case required by the preposition, current spelling, length. A generated sentence that fails is sent back once with the reason. Then you see the list:

```
  Exercises:
    1. Präteritum                   Gestern [nahm] ich meinen Schirm nicht [mit].   (own)
    2. Perfekt                      [Hast] du deinen Pass [mitgenommen]?   (generated)
    3. Präsens, er/sie/es           Sie [nimmt] immer ein Buch in den Urlaub [mit].   (generated)
  Enter to keep; numbers to replace or fill (e.g. 2,4):
```

Typing a number lets you write your own sentence, with the gap in [brackets] (it is checked too), or ask the API for a new one. Without an API key, or with `--manual`, steps 1 to 3 still run and you write the rest yourself or leave them empty.

When you edit examples, verb forms, noun gender/plural or the word type, `vocab_builder edit` offers to re-check the exercises: the ones that no longer fit the new forms are replaced. `python -m vocab_builder exercises <word>` does the same at any time.

### API key setup

`vocab_builder add` needs an Anthropic API key, found in this order:

1. the `ANTHROPIC_API_KEY` environment variable;
2. a `.env` file (`ANTHROPIC_API_KEY=sk-ant-...`) at the path written in `private/personal/api_env.txt` (one line,
   relative to this folder or absolute), so the key can live outside the repository, where it cannot
   be committed by accident and tools that only see this folder cannot read it;
3. a `.env` next to `words.json` (listed in `.gitignore`).

---

## The data model

Each entry in `words.json` is a JSON object. All entries share these fields:

| Field | Type | Description |
|---|---|---|
| `id` | string | URL-safe identifier (auto-generated) |
| `word` | string | The German word in canonical form |
| `type` | string | `noun`, `verb`, `adj/adv`, `prep/conj`, `expression`, `construction`, `other` |
| `definitions` | list | `[{meaning, note}]` — always in English. A meaning may start with a German phrase (`den Tisch decken: to set the table`); where English is the prompt (*Produzieren*, EN → DE), the word itself is shown as ___ in that German part and in the notes, so it does not give the answer away |
| `examples` | list | `[{de, en}]` — German sentence + translation. The first example in which the word is found becomes its "Welches Wort passt?" card, so it should be a sentence where only this word of its contrast group fits (see *The cards*). Optional `tense`: the verb form named on that card when the lexicon gets it wrong (`"Infinitiv"`). |
| `topics` | list | 0 to 2 entries from the closed list below; empty for core vocabulary |
| `compound_parts` | list | Optional, for compound nouns and adjectives: the parts in order, nouns with article, linking elements as their own item: `["die Kündigung", "-s-", "die Frist"]`. Shown as one chip (Kündigung + -s- + Frist); parts that are in the database are clickable and get a `compound` link. Source: German Wiktionary's word-formation notes |
| `definition_de` | string | German definition matched to the first English meaning: from German Wiktionary (added automatically by `vocab_builder add`), or from [DWDS](https://www.dwds.de) or written by hand when Wiktionary has no matching sense. Shown on the website card. Optional |
| `notes` | string | One-sentence personal note, or null. Register goes here when it is not neutral (`Register: umgangssprachlich.`) |
| `related` | list | `[{word, kind}]` — semantic links, always bidirectional. `kind` is one of `synonym`, `antonym`, `contrast` (easily confused), `derived` (same stem, other word class), `compound` (one word is part of the other). Verb families are **not** stored here; see `family_root`. |
| `collocations` | list | Phrases with this word, one Kollokation card each (English to German): `[{de, en, note?, example?}]`, e.g. `{"de": "eine Frage stellen", "en": "to ask a question"}`. The answer is `de`; the case after a preposition and other variants go in `note`. `example`: `{de, en}`, a sentence with the collocation, shown and read aloud on the back. A collocation hangs on the noun of the phrase  |
| `level` | string | CEFR level: `A1`, `A2` or `B1` when the word is in that Goethe-Zertifikat word list (downloaded from DWDS, `private/sources/goethe/`, `vocab_builder/levels.py`), `B2+` when it is in none of them (there is no Goethe list for B2 and above: mostly B2 words, also phrases, compounds and Swiss words). The lists themselves are protected by copyright and only used to tag your words. `python -m vocab_builder levels` fills it; `vocab_builder add` and `edit` set it. A level set by hand with `"level_manual": true` is kept |
| `dwds` | object | `{url, freq}`: the [DWDS](https://www.dwds.de) article and its frequency class, 0 (rare) to 6 (very frequent; *und*), from the DWDS lemma list in `private/sources/dwds/` (`vocab_builder/dwds.py`). Missing for the about 50 words DWDS has no lemma for (most phrases and constructions). When several DWDS entries share the spelling (*die Bank*), the link opens the page with all of them. A link added by hand with `"manual": true` is never overwritten. Shown as a "DWDS" link on the website |
| `added` | string | Date added (YYYY-MM-DD) |
| `exercises` | list | Gap-fill sentences for the verb cards, **only `praet`, `part`, `praes`, `refl`** (declension, fixed prepositions and connectors are grammar cards, in `grammar.json`): `[{slot, label, de, en, blanks, source}]`. `blanks` are character spans in `de` (`[[4, 8]]` hides *nahm* in "Ich nahm ein Taxi…"). Only what cannot be predicted from a rule is practised. `slot` says what is tested: `praet` (irregular and mixed verbs: *nahm*, *dachte*; `verb_en` is the English verb shown in the hint, as for `praes` and `part`), `part` (auxiliary + participle, *[ist] … [gereist]*, with `verb_en`, the English participle shown in the hint, and optionally `not`, words that would also fit the English; irregular and mixed verbs, and every verb with *sein*; regular verbs with *haben* get no Perfekt card), `praes` (only stem-changing verbs), `refl` (only reflexive verbs). A verb whose root verb is also in the dictionary (vornehmen, with nehmen) gets only `part` (and `refl`): its Präteritum and Präsens repeat the root's. `vocab_builder` keeps this in sync: adding a root verb removes the Präteritum/Präsens exercises of its family members, and deleting one offers to write them again. `source` is `own`, `example`, `tatoeba:<sentence id>` or `generated`. Every generated sentence passed the checker (`vocab_builder/checks.py`) |

**Extra fields for nouns:**

| Field | Description |
|---|---|
| `gender` | `der`, `die`, or `das` |
| `plural` | Plural form with article |
| `preposition` | Fixed preposition + case (`vor + DAT` for *die Angst*), or absent. Practised on the grammar cards (Feste Präpositionen) once it has a sentence there: `python -m vocab_builder grammar add prep_fixed …` |
| `plural_card` | `false` when a plural should not be asked on the Produzieren card: rare (*die Aufwände*), with another meaning (*die Mängel* = defects), or a pattern another noun already practises (*die Putzkräfte* next to *die Kräfte*). `vocab_builder` asks when you add a noun with an irregular plural |

**Extra fields for verbs:**

| Field | Description |
|---|---|
| `auxiliary` | `haben` or `sein` |
| `past_tense` | Simple past (Präteritum), main-clause form, with `sich` for reflexive headwords (`nahm mit`, `freute sich`) |
| `past_participle` | Past participle, without `sich` |
| `present_3sg` | er/sie/es form, same format as `past_tense` (`nimmt mit`, `freut sich`). Shown on cards only when the stem changes (`nimmt`, `fährt`, `weiß`) |
| `imperative` | du-imperative, only when the stem changes (`nimm mit`, `benimm dich`); `fahr!` is regular and not stored |
| `konjunktiv_2` | one-word Konjunktiv II, only for the verbs where it is in everyday use (`käme`, `wüsste`, `bräuchte`; list in `lexicon.KONJ2_IN_USE`). Other verbs use *würde* + infinitive |
| `verb_class` | `regular` (kaufte, gekauft), `irregular` (nahm, genommen) or `mixed` (dachte, gedacht: weak endings, changed stem) |
| `is_separable` | `true` / `false` |
| `reflexive` | `"akk"` (ich freue **mich**), `"dat"` (ich nehme **mir** etwas vor) or `false`. Reflexive means the verb cannot drop *sich*, or changes meaning with it; those have *sich* in the headword. Verbs that merely *can* take *sich* (waschen, umdrehen) are not reflexive. When a verb has a second object, the pronoun moves to the dative (ich ziehe **mir** die Jacke an); that goes in the meaning's note |
| `preposition` | Fixed preposition + case, e.g. `an + DAT`; several separated by ` / ` (`auf + AKK / über + AKK` for *sich freuen*). Each one can get a grammar card (Feste Präpositionen, `vocab_builder grammar add prep_fixed`). A bare case (`DAT` for *vertrauen*) is kept as information but gets no exercise. A verb with a fixed preposition is stored as the verb alone (*zählen*, `auf + AKK`), not as *zählen auf* |
| `family_root` | Root verb (e.g. `nehmen` for `mitnehmen`) |
| `prefix` | Separable prefix e.g. `mit-` |

**Extra fields for adj/adv:**

| Field | Description |
|---|---|
| `usage` | `both`, `adjective only`, or `adverb only` |
| `derived_from` | source verb for participle-adjectives e.g. `entspannen` for *entspannt* |
| `preposition` | Fixed preposition + case (`auf + AKK` for *neugierig*), or absent. Practised on the grammar cards, as for nouns |

Adjectives are stored in their base form, without an ending (*bedingt*, not *bedingte*).

**Extra fields for prep/conj:**

| Field | Description |
|---|---|
| `usage` | `both`, `preposition only`, or `conjunction only` |

### Topics

A topic says what a word is **about**. Rules:

- 0 to 2 topics per word. Core vocabulary (*brauchen, bekommen, liegen, nötig*) has an empty list, and that is the correct answer, not a gap. About 100 words are deliberately without a topic.
- The **first definition decides**. A secondary meaning (*drehen* "to shoot a film", *brechen* "to vomit") earns a topic only if one of the stored examples illustrates it.
- The list is closed and lives in `vocab_builder/model.py` (`TOPICS`), together with the definition the model sees when it proposes topics for a new word. `vocab_builder topics` prints it with counts.
- Register (formal, colloquial, Swiss) is not a topic and not a field: it goes into `notes`.

| Topic | Definition and boundary |
|---|---|
| home & objects | Housing, rooms, furnishings, household objects, clothing, cleaning and domestic maintenance. Exclude general physical actions merely illustrated with a household object. |
| food & drink | Food, beverages, preparation, eating, drinking and dining. Include verbs only when a food-related meaning is explicitly recorded. |
| body & health | Anatomy, bodily functions, physical sensations, illness, treatment, hygiene, recovery, sport. Include physical exhaustion; distinguish it from emotional distress. |
| thinking & perception | Knowledge, memory, attention, reasoning, judgement, decisions and sensory perception. Include looking and noticing; exclude general comparisons between objects. |
| emotions & character | Feelings, moods, preferences, temperament and personal dispositions. Exclude general usefulness, size or quality unless the meaning concerns a person's character. |
| people & relationships | Personal relationships, encounters, trust, cooperation, interpersonal behaviour and social interaction. Exclude actions simply because a person performs them. |
| language & communication | Speaking, writing, listening, naming, conveying information, stance adverbs and conventional conversational acts. An idiom belongs here only when its function is communicative. |
| work & jobs | Employment, occupations, workplace arrangements, professional responsibilities, vocational training and working conditions. Exclude generic effort, success or activity. |
| science & academia | Research, academic study, scientific methods, evidence, and scholarly institutions or outputs. Exclude general concepts merely because researchers use them. |
| technology & media | Devices, technical systems, digital tools, broadcasting, and media production or distribution. Not every act of reporting and not every artificial object. |
| money & shopping | Prices, payment, wealth, ownership, buying, selling and economic transactions. Exclude general exchange, receipt or waste without a financial meaning. |
| society & politics | Public institutions, law, governance, collective social structures, rights and public affairs. Distinguish from individual interpersonal relationships. |
| culture & arts | Literature, visual and performing arts, creative practices, cultural works and their creators. Exclude general attractiveness or beauty. |
| nature & weather | Animals, plants, landscapes, natural environments, weather and environmental processes. Exclude physical properties that apply equally to manufactured objects. |
| travel & movement | Journeys, transport, routes, destinations, navigation, locomotion and directional movement. Exclude manipulating an object solely because the object moves. |
| time | Temporal location, duration, frequency, sequence, deadlines and speed of occurrence. Exclude events merely because they occur in time. |
| quantity & comparison | Amount, extent, sufficiency, scarcity, similarity, difference and comparative scale. |
| materials & physical properties | Materials and observable physical characteristics: shape, texture, surface, structural integrity, physical force. Exclude generic handling actions. |
| change & development | Alteration, growth, decline, increase, decrease, transformation and persistence of a state. Exclude mere movement to a different place. |
| goals, effort & outcomes | Intentional aims, attempts, effort, obstacles, giving up, achievement and reward. Exclude ordinary actions, events, and evaluative adjectives such as useful or suitable. |
| connectors & constructions | Connectives, discourse particles, prepositions and reusable grammatical patterns that relate clauses or sentence elements. A grammatical category; not abstract vocabulary. |

---

## Related words — what goes in, what stays out

`related` holds **semantic** neighbours only, each with a kind:

```json
"related": [
  {"word": "wissen",          "kind": "contrast"},
  {"word": "kennenlernen",    "kind": "contrast"}
]
```

| kind | meaning | example |
|---|---|---|
| `contrast` | easily confused, worth telling apart | kennen / wissen |
| `antonym` | opposite | billig / teuer |
| `synonym` | same or near meaning | rasch / zügig |
| `derived` | same stem, different word class | wählen / die Wahl |
| `compound` | one word is a part of the other | das Bild / der Bildschirm |

On the website the related words are grouped under these labels: *Leicht zu verwechseln*, *Gleiche Bedeutung*, *Gegenteil*, *Gleicher Stamm*, *Zusammensetzung*. The German labels are in `schema.json` (`related_kinds`).

Verb family members are linked only when the link is the point: real opposites (abnehmen / zunehmen) or classic confusions (senken / sinken, suchen / versuchen).

Verb families (`nehmen`, `mitnehmen`, `teilnehmen`…) are deliberately **not** linked here.
They are already encoded by `family_root`, and `vocab_builder family nehmen` lists them.

When you add a word, two sources propose links, and you confirm or adjust them: the AI names
related German words without seeing your list, and only those already in the database are kept;
and words that look related by their spelling (one inside the other: *das Bild / der Bildschirm*;
the same beginning in another word class: *wählen / die Wahl*) are found offline. Your word list is
never sent to the AI. `contrast` and `antonym` links feed the "Welches Wort passt?"
cards: every word with such a link gets a card with its own sentence.

### Keeping links consistent — `python -m vocab_builder links`

```bash
python -m vocab_builder links --dry-run   # report only
python -m vocab_builder links             # drop dangling links, add back-links
```

Safe to run any time. It never invents links; it only removes broken ones and mirrors
existing ones.

---

## Data sources

Reference files live in `private/sources/`, one subfolder per source, each with a `LICENCE.md` stating the terms as read and how the project uses the source; `private/README.md` is the index. They are not part of the website, so `private/` is in `.gitignore`.

**Morphy / LanguageTool lexicon** (`private/sources/morphy/dictionary.dump`, CC BY-SA 4.0, [danielnaber.de/morphologie](https://danielnaber.de/morphologie/)). Every inflected form of about 400,000 German words, one per line: `nehmen_nimmt_VER:3:SIN:PRÄ:NON`. `vocab_builder/lexicon.py` reads it; `vocab_builder add` uses it to check verb forms, fill `present_3sg` and `verb_class`, and check noun gender and plural. Without the file, `add`, `edit` and `exercises` skip these checks and say so; `karten` and the smoke test's sentence check need it. To produce it (once; needs Java 8 or later):

```bash
# 1. download LanguageTool stand-alone (for its libs/ folder) and the german-pos-dict repo
# 2. from the german-pos-dict folder:
java -cp "/path/to/LanguageTool-6.6/libs/*" morfologik.tools.DictDecompile \
     -i src/main/resources/org/languagetool/resource/de/german.dict -o dictionary.dump
# 3. move dictionary.dump into private/sources/morphy/
```

(LanguageTool's own export script needs Java 17. The command above uses the Morfologik decompiler directly and runs on older Java.)

**German Wiktionary** (`private/sources/wiktionary/de-extract.jsonl`, CC BY-SA, [kaikki.org/dewiktionary](https://kaikki.org/dewiktionary/)). `vocab_builder add` looks up a German definition for each new word (about 15 s, with `grep`), and the file also holds pronunciation (IPA), synonyms, antonyms and idioms.

**Tatoeba sentences** (`private/sources/tatoeba/deu-eng.tsv`, the "Sentence pairs" download German-English saved under this name; `private/sources/tatoeba/deu_sentences.tsv`, CC BY 2.0 FR, [tatoeba.org/downloads](https://tatoeba.org/en/downloads)). Human-written example sentences, used as a source for exercise sentences. For English translations, the custom export "Sentence pairs" German to English. Exercise sentences taken from Tatoeba keep their sentence id (`source: "tatoeba:699936"`, and `en_source` when the English is Tatoeba's translation too), which is the attribution the licence asks for: the sentence is at `https://tatoeba.org/en/sentences/show/699936`, and the card shows the credit under the sentence.

**DWDS lemma list** (`private/sources/dwds/dwds_lemmata_<date>.json`, the "Lemmadatenbank" download from [dwds.de](https://www.dwds.de/d/api), terms in `private/sources/dwds/LICENCE.md`). Part of speech, frequency class and article link of 281,971 lemmas. `vocab_builder/dwds.py` looks words up in the file, offline: no request goes to the DWDS website. Source: „Lemmadatenbank", in: DWDS – Digitales Wörterbuch der deutschen Sprache, hrsg. v. d. Berlin-Brandenburgischen Akademie der Wissenschaften, heruntergeladen am 30.10.2026.

The Goethe A1 to B1 word lists (`private/sources/goethe/`, downloaded from DWDS; copyright Goethe-Institut) give each word its `level`; they are used only for that and not shown.

The grammar checklists and books in `private/sources/` (Einlang, DeutschAcademy, deutschlernerblog.de) were references for the curriculum; the ids, grouping and order in `grammar.json` are this project's own.

---

## Grammar: `grammar.json`

The grammar cards are built from `grammar.json`, not from the word list. It holds:

- **structures**: the curriculum, one entry per grammar structure from A1 to C1 (178), with ids
  of the form `<topic>-<n>` (`pronomen-01`; our own numbering and order), based on reference checklists and books (`sources.structures` in the file) and the levels A1 and A2 checked
  against the Goethe inventories (`goethe_level` where they differ). Each has a `thread` (structures that come back at several levels share one refresher), the
  planned card type and a `status`: `active` (grammar cards), `planned`, `word-cards` (practised on the word
  cards), `writing` (website only), `reading`, `later`.
- **threads**: name and refresher (the card back) per thread.
- **topics**: what the grammar cards are built from. A topic covers some structures and names its cells; each cell
  holds sentences, the same shape as the exercises in `words.json` plus `word_id` (the lemma it practises),
  `source`, `status` from the checker and `use` (on cards, or kept in reserve for cells you get wrong often).

Topics with sentences:

- **Deklination** (`vocab_builder/grammar/dekl.py`): 88 cells (determiner type × case × gender), two sentences per
  cell on cards, 176 cards, all checked.
- **Kasus** (`vocab_builder/grammar/kasus.py`): the mixed case drill, 76 cells, 104 cards: personal pronouns,
  wer / wen / wem / wessen, preposition + article (or zum, zur, beim, vom), verbs with a Dativ object,
  jemand / niemand / einer / keiner. All checked.
- **Konnektoren** (`vocab_builder/grammar/fromwords.py`): one cell per connector in `words.json`, 24 cells,
  95 cards. The gap is the connector, shown with its meaning; the back has the rule and two more
  examples.
- **Feste Präpositionen** (`prep_fixed`, same module): one cell per fixed preposition of a word,
  86 cells, 86 cards. Two gaps: the preposition, and the article in English
  (Nächste Woche nehme ich ___ [a] Sprachkurs in Zürich teil. → an einem); the hint is the word.
  This is the only card that asks which preposition a word takes.

These two use the same checker as the word exercises. Each cell names its word (`word_id`), so a new connector
or preposition gets its sentence with `python -m vocab_builder grammar add` (below).

`grammar.json` holds the whole curriculum:
`python -m vocab_builder grammar status` counts per level the structures that are `active` (with cards),
`planned` or `later`, and lists the 26 topics. Each planned structure
has the card it needs: `gap`, `choice`,
`build` (word order) or `transform` (active to passive and the like).

```bash
python -m vocab_builder grammar status        # curriculum per level, topics and how full their cells are
python -m vocab_builder grammar cells dekl    # the cells of a topic with the sentences on cards and their hints
python -m vocab_builder grammar check         # run the checker again on every grammar sentence
python -m vocab_builder grammar add konnektoren seitdem "[Seitdem] wohnt sie in Basel." "Since then she has lived in Basel."
python -m vocab_builder grammar add prep_fixed "sich freuen" "Ich freue mich [auf] [den] Urlaub." "I am looking forward to the holiday."
                                # a grammar sentence for a connector or a word's fixed preposition, checked
python -m vocab_builder grammar cards         # write grammar_cards.json for the website (after any change to grammar.json
                                # or words.json; the smoke test says when it is out of date)
```

---

## The cards (`web/data/karten.json`)

`python -m vocab_builder karten` writes `web/data/karten.json` and `web/js/schema.js` from `words.json` and
`grammar.json` (`vocab_builder/karten/`); run it after changing either, and commit both. The smoke test says
when they are out of date.

- **Word cards** (`word_cards.py`): Bedeutung and Produzieren (the answer asks for the plural too, for
  every noun that has one: *die Wurst, die Würste*; not where `plural_card` is false; never for a
  preposition, which has its own grammar card), the verb forms, Reflexiv and Welches Wort passt?
  - Every card that asks you to type something shows **Bitte ausfüllen** and a cue in German
    (`vocab_builder/grammar/cue.py`): what the gap holds and how many words (*Präteritum · 1 Wort*,
    *Präposition und Artikel in einem Wort · 1 Wort*).
  - The gap cards (verb forms, grammar) show the sentence with one gap per group of words and the
    English with the part to translate highlighted. The highlight is placed automatically from the
    English of the gap; where that fails, the sentence carries it by hand as `en_hl`, with the part
    in braces (*I like reading books {by young Swiss authors}.*). A sentence can set its own cue
    with `cue`. Reflexive cards have no highlight.
  - Welches Wort passt?: the cue names the options and what else the gap holds: for nouns the
    article type or *nur das Nomen*, and Singular or Plural; for verbs the form (Präsens,
    Präteritum, Partizip II, Infinitiv, Infinitiv mit zu, Imperativ); for adjectives only Komparativ
    or Superlativ; then the number of words, left out when the options differ in length
    (*noch / immer noch*). A word is found in its examples by its first letters, then by its exact
    spelling, its lemma in the full-form lexicon (*gesagt*, *weiß*), as a phrase, as a separable
    verb split in two (*fängt … an*: two gaps) or as a two-part connector (*weder … noch*).
- **Collocation cards** (`grammar_cards.py`, English to German) come from the words' `collocations`. The
  cue names the kinds of words instead of the host word (*unbestimmter Artikel + Nomen + Verb im
  Infinitiv · 3 Wörter*); the answer has no end punctuation. The back has the collocation's
  `example` (`{de, en}`), read aloud.
- **Grammar cards** (`grammar_cards.py`): one card per sentence of the active topics in `grammar.json`.
  The back shows the sentence with the answer marked and the rule (*Regel*), in German:
  - Deklination: the whole declension of the card's own noun phrase in its gender (or the plural),
    with the three kinds of article, the asked cell marked and the noun's own endings (Genitiv -s,
    Dativ Plural -n, n-Deklination) in red. The noun forms come from the full-form lexicon.
  - Prepositions (Feste Präpositionen, the prepositions among the Konnektoren, the Kasus
    preposition cards): the preposition's case with each kind of article, for each gender and the
    plural, plain and with an adjective, always with the same four nouns (Kaffee, Suppe, Brot,
    Kekse).
  - Konnektoren: the word with its English meaning, then *Wortart* (with the word order or the
    case), *Gebrauch* and, where useful, *Achtung* (what it is confused with): the cell's `regel`
    in grammar.json; two more examples.

## Deploying changes

The site is hosted on GitHub Pages: on every push, `.github/workflows/pages.yml` publishes the folder `web/`, within about a minute.

```bash
# After adding words or making any change: the cards, then the smoke test
python -m vocab_builder karten          # web/data/karten.json and web/js/schema.js
python -m vocab_builder grammar cards         # grammar_cards.json (after a change to grammar.json or words.json)
python tests/smoke.py           # imports, cards up to date, website tests, every sentence verdict; no API needed
git add web/data/
git commit -m "add: Schadenfreude, Weltschmerz"
git push

# After a batch of additions, check the links are consistent:
python -m vocab_builder links
```
