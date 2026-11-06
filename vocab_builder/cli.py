"""
vocab_builder — the German vocabulary manager (code: vocab_builder/cli.py)
Usage:
  python -m vocab_builder list                  show all words
  python -m vocab_builder list --topic work     filter by topic
  python -m vocab_builder list --type verb      filter by word type
  python -m vocab_builder show nehmen           show full entry for a word
  python -m vocab_builder add                   add a new word (AI-assisted)
  python -m vocab_builder add --manual          add a word without AI
  python -m vocab_builder edit nehmen           edit an existing entry
  python -m vocab_builder delete nehmen         delete a word
  python -m vocab_builder topics                show all topics
  python -m vocab_builder family nehmen         show a verb family
  python -m vocab_builder exercises nehmen      check / fill / replace the exercise sentences of a word
  python -m vocab_builder dwds                  DWDS link and frequency class for every word, from the
                                        downloaded lemma list in private/sources/dwds/ (offline)
  python -m vocab_builder levels                CEFR level of every word (A1, A2, B1 from the Goethe lists
                                        in private/sources/goethe/, else B2+) and the counts per level
  python -m vocab_builder links                 keep the related links consistent: drop links to missing words,
                                        add the missing back-links (--dry-run: only report)
  python -m vocab_builder lexikon nehmen        the entry of a word in the full-form lexicon (private/sources/morphy)
  python -m vocab_builder karten                the website's cards (web/data/karten.json, web/js/schema.js) from
                                        words.json and grammar.json; run after changing either
"""
from datetime import datetime
import re
import sys
from .deps import EX, EX_OK, LEXICON, german_definition
from .model import (GENDERS, RELATED_KINDS, TOPICS, VERB_CLASSES, WORD_TYPES, clean_topics, find, form_candidates, load, make_bidirectional, make_id, norm_reflexive, normalise, save)
from .claude import ai_enrich, load_api_key
from .ui import ask, ask_choice, confirm_or_edit, print_entry
from .exercises import build_exercises, root_added, root_removed
from . import dwds, levels


def level_tag(entry: dict) -> None:
    """The word's CEFR level from the Goethe lists (A1, A2, B1, else B2+), unless set by hand."""
    if levels.available() and not entry.get("level_manual"):
        entry["level"] = levels.lookup(entry)


def dwds_link(entry: dict) -> None:
    """The DWDS link and frequency class, from the downloaded lemma list (no request to DWDS)."""
    if not dwds.available() or (entry.get("dwds") or {}).get("manual"):
        return
    got = dwds.lookup(entry)
    if got:
        entry["dwds"] = got
        print(f"  DWDS: {got['url']}" + (f"  (frequency class {got['freq']} of 6)" if "freq" in got else ""))
    else:
        entry.pop("dwds", None)
        print("  DWDS: not in the lemma list")


def ask_collocations(entry: dict) -> None:
    """Collocations become Kollokation cards (English -> German). One per line as
    'German = English' or 'German = English = note'; an empty line ends the list."""
    print("\n  Collocations (one per line: German = English [= note]; Enter to finish)")
    out = list(entry.get("collocations") or [])
    while True:
        line = ask("   ")
        if not line:
            break
        parts = [p.strip() for p in line.split("=", 2)]
        if len(parts) < 2 or not parts[0] or not parts[1]:
            print("    write it as: eine Frage stellen = to ask a question")
            continue
        if any(x["de"].lower() == parts[0].lower() for x in out):
            print("    already there")
            continue
        k = {"de": parts[0], "en": parts[1]}
        if len(parts) > 2 and parts[2]:
            k["note"] = parts[2]
        out.append(k)
    if out:
        entry["collocations"] = out


def edit_collocations(entry: dict) -> None:
    """List the collocations; remove some by number, then add new ones."""
    col = list(entry.get("collocations") or [])
    print("\n  Current collocations:")
    for i, k in enumerate(col, 1):
        print(f"    {i}. {k['de']} = {k['en']}" + (f"  ({k['note']})" if k.get("note") else ""))
    if not col:
        print("    (none)")
    drop = ask("Numbers to remove (e.g. 2,4; Enter for none)")
    gone = {int(x) for x in re.findall(r"\d+", drop)}
    entry["collocations"] = [k for i, k in enumerate(col, 1) if i not in gone]
    ask_collocations(entry)
    if not entry["collocations"]:
        entry.pop("collocations", None)


def confirm_related(words: list, proposed: list) -> list:
    """Show the AI's proposed links, keep only those that exist, let the user adjust."""
    by_word = {w["word"]: w for w in words}
    by_norm = {normalise(w["word"]): w for w in words}
    kept = []
    for r in proposed or []:
        if not isinstance(r, dict):
            continue
        tgt = by_word.get(r.get("word", "")) or by_norm.get(normalise(r.get("word", "")))
        kind = r.get("kind", "contrast")
        if tgt and kind in RELATED_KINDS and tgt["word"] not in {k["word"] for k in kept}:
            kept.append({"word": tgt["word"], "kind": kind})
    if kept:
        print("\n  Related words proposed:")
        for i, r in enumerate(kept, 1):
            print(f"    {i}. {r['word']:<26} ({r['kind']})")
        print("  Enter to keep, numbers to drop (e.g. 2,3), or '+word:kind' to add.")
    else:
        print("\n  No related words proposed. Type '+word:kind' to add, or Enter to skip.")
    while True:
        val = input("  > ").strip()
        if not val:
            return kept
        if val.startswith("+"):
            name, _, kind = val[1:].partition(":")
            tgt = by_word.get(name.strip()) or by_norm.get(normalise(name))
            kind = (kind or "contrast").strip()
            if not tgt:
                print(f"    '{name}' is not in the database.")
            elif kind not in RELATED_KINDS:
                print(f"    kind must be one of {', '.join(RELATED_KINDS)}")
            else:
                kept.append({"word": tgt["word"], "kind": kind})
                print(f"    added {tgt['word']} ({kind})")
        else:
            drop = {int(x) for x in re.findall(r"\d+", val)}
            kept = [r for i, r in enumerate(kept, 1) if i not in drop]
            print(f"    kept {len(kept)}")


# ── commands ───────────────────────────────────────────────────────────────────

def cmd_list(args):
    words = load()
    topic_filter = None
    type_filter  = None
    for i, a in enumerate(args):
        if a == "--topic" and i + 1 < len(args):
            topic_filter = args[i + 1].lower()
        if a == "--type" and i + 1 < len(args):
            type_filter = args[i + 1].lower()

    results = words
    if topic_filter:
        results = [w for w in results if any(topic_filter in t.lower() for t in w.get("topics", []))]
    if type_filter:
        results = [w for w in results if w["type"] == type_filter]

    if not results:
        print("  No entries found.")
        return

    print(f"\n  {'WORD':<30} {'TYPE':<14} {'TOPICS'}")
    print(f"  {'─'*30} {'─'*14} {'─'*30}")
    for w in sorted(results, key=lambda x: x["word"].lower()):
        topics = ", ".join(w.get("topics", []))
        print(f"  {w['word']:<30} {w['type']:<14} {topics}")
    print(f"\n  {len(results)} entry/entries.\n")


def cmd_show(args):
    if not args:
        print("  Usage: python -m vocab_builder show <word>")
        return
    words = load()
    w = find(words, " ".join(args))
    if not w:
        print(f"  X '{' '.join(args)}' not found.")
        return
    print_entry(w)


def cmd_topics(args):
    words = load()
    all_topics = {}
    for w in words:
        for t in w.get("topics", []):
            all_topics[t] = all_topics.get(t, 0) + 1
    print("\n  Topics in your vocabulary:\n")
    for topic, desc in TOPICS.items():
        print(f"  . {topic:<34} {all_topics.get(topic, 0):>4}   {desc.split('.')[0]}")
    for topic, count in sorted(all_topics.items()):
        if topic not in TOPICS:
            print(f"  ! {topic:<28} {count:>4}   (not in the closed list)")
    print(f"  . {'(no topic)':<28} {sum(1 for w in words if not w.get('topics')):>4}")
    print()


def cmd_family(args):
    if not args:
        print("  Usage: python -m vocab_builder family <root-verb>")
        return
    root = " ".join(args).lower()
    words = load()
    members = [w for w in words if w.get("family_root", "").lower() == root]
    if not members:
        print(f"  No family found for '{root}'.")
        return
    print(f"\n  Verb family: {root}\n")
    for m in sorted(members, key=lambda x: x["word"]):
        prefix  = f"  [{m.get('prefix','')}]" if m.get("prefix") else "  [root]"
        meaning = m["definitions"][0]["meaning"] if m.get("definitions") else ""
        print(f"  {prefix:<12} {m['word']:<25} {meaning}")
    print()


def lexicon_verb(entry: dict) -> None:
    """Compare the verb forms in `entry` with the lexicon; fill present_3sg and verb_class.
    The lexicon is right far more often than the model, but it cannot know which meaning
    you mean when a verb has two conjugations (schaffte / schuf), so you decide."""
    if not (LEXICON and LEXICON.ok):
        return
    v = LEXICON.verb(entry["word"], entry.get("prefix"), entry.get("is_separable"),
                     entry.get("past_tense"), entry.get("past_participle"),
                     reflexive_case=norm_reflexive(entry.get("reflexive")))
    if not v:
        print("  (lexicon: verb not found, keeping the forms above)")
        return
    for field in ("past_tense", "past_participle", "present_3sg", "verb_class"):
        mine, lex = entry.get(field), v[field]
        # exact comparison: ß and ss are NOT interchangeable (vergaß, not vergass).
        # The lexicon already prefers current spelling over old forms like schloß.
        if not lex or (mine or "") == lex:
            entry[field] = mine or lex
            continue
        if not mine:
            entry[field] = lex
            continue
        print(f"  ! {field}: you have '{mine}', the lexicon says '{lex}'")
        entry[field] = lex if ask("    Use the lexicon form? (y/n)", "y").lower() == "y" else mine
    # filled silently: both come straight from the lexicon and need no judgement
    if v.get("imperative"):
        entry["imperative"] = v["imperative"]
    if v.get("konjunktiv_2_common"):
        entry["konjunktiv_2"] = v["konjunktiv_2_common"]
    if v["alternatives"]:
        print(f"  (lexicon: also conjugated as {', '.join(v['alternatives'])} in another meaning)")
    extra = "".join(f" · {x}" for x in (entry.get("imperative") and entry["imperative"] + "!",
                                         entry.get("konjunktiv_2") and "Konj. II " + entry["konjunktiv_2"]) if x)
    print(f"  lexicon: {entry['verb_class']} · er {entry['present_3sg']} · {entry['past_tense']} · {entry['past_participle']}{extra}")


def own_example(sentence: str, s: dict) -> dict | None:
    """Turn the learner's sentence into the first example, marked source='own'.
    If the model flagged it as incorrect, offer the corrected version."""
    if not sentence:
        return None
    if s.get("context_ok") is False and s.get("context_fix"):
        print(f"\n  Your sentence:   {sentence}")
        print(f"  Suggested fix:   {s['context_fix']}")
        if ask("  Use the corrected sentence? (y/n)", "y").lower() == "y":
            sentence = s["context_fix"]
    en = s.get("context_en") or ""
    en = confirm_or_edit("English for your sentence", en) if en else ask("English for your sentence")
    return {"de": sentence, "en": en, "source": "own"}


def wiktionary_definition(entry: dict) -> None:
    """Look up a German definition (German Wiktionary) matching the English meaning."""
    if not german_definition or entry.get("definition_de"):
        return
    meanings = [d["meaning"] for d in entry.get("definitions", [])]
    print("  (looking up a German definition in Wiktionary…)")
    g = german_definition(entry["word"], entry.get("type"), meanings)
    if g:
        g = confirm_or_edit("German definition (Enter to keep, '-' to drop)", g)
        if g and g.strip() != "-":
            entry["definition_de"] = g


def lexicon_noun(entry: dict) -> None:
    """Warn if gender or plural disagree with the lexicon."""
    if not (LEXICON and LEXICON.ok):
        return
    n = LEXICON.noun(entry["word"])
    if not n:
        print("  (lexicon: noun not found)")
        return
    if entry.get("gender") and n["genders"] and entry["gender"] not in n["genders"]:
        print(f"  ! gender: you have '{entry['gender']}', the lexicon says {' / '.join(n['genders'])}")
        if ask("    Use the lexicon gender? (y/n)", "y").lower() == "y":
            entry["gender"] = n["genders"][0]
            entry["word"] = entry["gender"] + " " + re.sub(r"^(der|die|das)\s+", "", entry["word"])
    pl = re.sub(r"^die\s+", "", entry.get("plural") or "")
    if pl and n["plurals"] and pl not in n["plurals"]:
        print(f"  ! plural: you have '{pl}', the lexicon has {' / '.join(n['plurals'])} (some nouns have two)")


def ask_preposition(entry: dict, suggested=None) -> None:
    """The fixed preposition of a verb, noun or adjective (denken an + AKK, die Angst vor + DAT,
    stolz auf + AKK), for the grammar topic of fixed prepositions."""
    if suggested and str(suggested) not in ("—", "None", "null"):
        prep = confirm_or_edit("Fixed preposition", suggested)
    else:
        prep = ask("Fixed preposition + case, e.g. vor + DAT (or Enter for none)")
    if prep and str(prep) not in ("—", "None", "null"):
        entry["preposition"] = prep


def ask_plural_card(entry: dict) -> None:
    """An irregular plural (die Wände, die Bilder) is asked on the Produzieren card; ask whether it
    should be, since some plurals are rare or mean something else (die Mängel = defects)."""
    if EX_OK and EX.plural_kind(entry) == "irregular":
        if ask(f"Irregular plural ({entry.get('plural')}): ask it on the Produzieren card? (y/n)", "y").lower() != "y":
            entry["plural_card"] = False


def cmd_add(args):
    manual  = "--manual" in args
    words   = load()
    api_key = load_api_key()

    print("\n  -- Add a new word --\n")

    word = ask("Word (German)")
    if not word:
        print("  Cancelled.")
        return

    existing = find(words, word)
    if existing:
        print(f"\n  X '{word}' already exists. Use 'show' to view it.")
        return

    # ── ask word type FIRST so AI gets the right context ─────────────────────
    print()
    word_type = ask_choice("Word type", WORD_TYPES)

    # ── the learner's own sentence (optional) ───────────────────────────────
    # Asked before the lookup, so the definition follows the meaning in YOUR sentence.
    print()
    my_sentence = ask("Your sentence with this word (where you met it; Enter to skip)")

    # ── AI enrichment ─────────────────────────────────────────────────────────
    suggestion = None
    if not manual and api_key:
        print(f"\n  Looking up '{word}' as {word_type} with AI...\n")
        suggestion = ai_enrich(word, api_key, word_type=word_type, context=my_sentence or None)
        if suggestion:
            # override type from AI with what the user chose
            suggestion["type"] = word_type
            print("  AI suggestions ready. Press Enter to accept each, or type to override.\n")
        else:
            print("  AI lookup failed — falling back to manual entry.\n")
    elif not manual and not api_key:
        print("  (No API key found in .env — using manual entry)\n")

    s = suggestion or {}

    # canonical word form — AI may suggest a better form for the chosen type
    canonical = s.get("word", word)
    if canonical and canonical != word:
        print(f"  AI suggests canonical form: {canonical}")
        use_can = ask("  Use this? (y/n)", "y")
        if use_can.lower() == "y":
            word = canonical

    # if reflexive verb, auto-suggest 'sich' prefix
    if word_type == 'verb':
        is_reflexive = s.get('reflexive', False) if suggestion else False
        if is_reflexive and not word.lower().startswith('sich '):
            suggested = 'sich ' + word
            print(f"  Reflexive verb — canonical form should be '{suggested}'")
            use_sich = ask("  Add 'sich' prefix? (y/n)", "y")
            if use_sich.lower() == 'y':
                word = suggested

    word_id = make_id(word)

    entry = {
        "id":          word_id,
        "word":        word,
        "type":        word_type,
        "definitions": [],
        "examples":    [],
        "topics":      [],
        "notes":       None,
        "added":       datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # ── type-specific fields ──────────────────────────────────────────────────
    if word_type == "noun":
        if suggestion:
            entry["gender"] = confirm_or_edit("Gender", s.get("gender"), GENDERS)
            entry["plural"] = confirm_or_edit("Plural", s.get("plural"))
        else:
            entry["gender"] = ask_choice("Gender", GENDERS)
            entry["plural"] = ask("Plural form (e.g. die Erinnerungen)")
        lexicon_noun(entry)
        ask_preposition(entry, s.get("preposition") if suggestion else None)
        ask_plural_card(entry)

    elif word_type == "verb":
        if suggestion:
            entry["auxiliary"]       = confirm_or_edit("Auxiliary", s.get("auxiliary"), ["haben", "sein"])
            entry["past_tense"]      = confirm_or_edit("Past tense", s.get("past_tense"))
            entry["past_participle"] = confirm_or_edit("Past participle", s.get("past_participle"))
            entry["present_3sg"]     = s.get("present_3sg")
            entry["verb_class"]      = s.get("verb_class") if s.get("verb_class") in VERB_CLASSES else None
            entry["is_separable"]    = confirm_or_edit("Separable?", s.get("is_separable", False))
            entry["reflexive"]       = norm_reflexive(confirm_or_edit(
                "Reflexive (akk / dat / no)", norm_reflexive(s.get("reflexive")) or "no"))
            prep = confirm_or_edit("Preposition", s.get("preposition"))
            if prep and str(prep) not in ("—", "None", "null"):
                entry["preposition"] = prep
            family = confirm_or_edit("Family root", s.get("family_root"))
            if family and str(family) not in ("—", "None", "null", word):
                entry["family_root"] = family
                prefix = confirm_or_edit("Prefix", s.get("prefix"))
                if prefix and str(prefix) not in ("—", "None", "null"):
                    entry["prefix"] = prefix
            else:
                entry["family_root"] = word
        else:
            entry["auxiliary"]       = ask_choice("Auxiliary", ["haben", "sein"])
            entry["past_tense"]      = ask("Simple past (Präteritum)")
            entry["past_participle"] = ask("Past participle")
            entry["present_3sg"]     = None
            entry["verb_class"]      = None
            entry["is_separable"]    = ask("Separable? (y/n)", "n").lower() == "y"
            entry["reflexive"]       = norm_reflexive(ask("Reflexive (akk / dat / no)", "no"))
            prep = ask("Preposition + case (or Enter to skip)")
            if prep:
                entry["preposition"] = prep
            family = ask("Family root verb (or Enter if this IS the root)")
            if family:
                entry["family_root"] = family
                prefix = ask("Prefix (e.g. mit-)")
                if prefix:
                    entry["prefix"] = prefix
            else:
                entry["family_root"] = word
        # prefix is known only now, so the lexicon check comes last
        lexicon_verb(entry)
        if not entry.get("present_3sg"):
            entry["present_3sg"] = ask("er/sie/es form, present (e.g. nimmt mit)")
        if entry.get("verb_class") not in VERB_CLASSES:
            entry["verb_class"] = ask_choice("Verb class", VERB_CLASSES, "regular")

    elif word_type == "adj/adv":
        USAGE_OPTIONS = ["both", "adjective only", "adverb only"]
        if suggestion:
            entry["usage"] = confirm_or_edit("Usage", s.get("usage", "both"), USAGE_OPTIONS)
        else:
            entry["usage"] = ask_choice("Usage", USAGE_OPTIONS, "both")

        # ── derived_from detection ────────────────────────────────────────────
        # Check if this adj/adv looks like a past or present participle of a verb
        bare = word.lower().strip()
        is_participle_shape = bool(re.match(
            r'^(ge[a-zäöüß]{3,}(t|en)|'   # ge- + stem(3+) + -t/-en
            r'[a-zäöüß]{4,}iert|'          # -iert (4+ chars before)
            r'(ver|zer|be|er|ent|miss|über|unter|ab|an|auf|aus|durch|nach|vor|zu)'
            r'[a-zäöüß]{3,}(t|en)|'        # prefix + stem(3+) + -t/-en
            r'[a-zäöüß]{4,}end)$',         # -end present participle (4+ chars)
            bare
        ))

        derived_from = None
        if is_participle_shape:
            # First: look for a verb in DB whose past_participle matches exactly
            db_match = None
            for w_db in words:
                if w_db.get("type") != "verb":
                    continue
                pp = (w_db.get("past_participle") or "").lower().strip()
                verb_bare = re.sub(r"^sich\s+", "", w_db["word"].lower()).strip()
                if pp == bare or verb_bare == bare:
                    db_match = w_db["word"]
                    break

            if db_match:
                print(f"\n  ✦ '{word}' looks like a participle-adjective.")
                print(f"    Found in database: derived from '{db_match}'")
                use_it = ask("  Set derived_from to this verb? (y/n/other)", "y").strip().lower()
                if use_it == "y":
                    derived_from = db_match
                elif use_it not in ("n", ""):
                    # they typed something else — use it as the derived_from value
                    derived_from = use_it
            else:
                # Not in DB — if it looks like a participle, ask anyway
                print(f"\n  ✦ '{word}' looks like it could be a participle-adjective.")
                source = ask("  Derived from which verb? (or Enter to skip)").strip()
                if source:
                    derived_from = source

        else:
            # Not a participle shape — still offer the field in case user knows
            source = ask("  Derived from a verb? (e.g. entspannen → entspannt, or Enter to skip)").strip()
            if source:
                derived_from = source

        if derived_from:
            entry["derived_from"] = derived_from
        ask_preposition(entry, s.get("preposition") if suggestion else None)

    elif word_type == "prep/conj":
        USAGE_OPTIONS = ["both", "preposition only", "conjunction only"]
        if suggestion:
            entry["usage"] = confirm_or_edit("Usage", s.get("usage", "both"), USAGE_OPTIONS)
        else:
            entry["usage"] = ask_choice("Usage", USAGE_OPTIONS, "both")

    # ── definitions ───────────────────────────────────────────────────────────
    if suggestion and s.get("definitions"):
        print(f"\n  Definitions:")
        for i, d in enumerate(s["definitions"], 1):
            note = f" ({d['note']})" if d.get("note") else ""
            print(f"    {i}. {d['meaning']}{note}")
        action = input("\n  [keep / edit / add more]: ").strip().lower() or "keep"
        if action == "keep":
            entry["definitions"] = s["definitions"]
        elif action == "edit":
            entry["definitions"] = []
            print("  Enter definitions (empty to stop):")
            while True:
                m = ask("  Meaning")
                if not m:
                    break
                n = ask("  Note (or Enter)")
                entry["definitions"].append({"meaning": m, "note": n or None})
        else:
            entry["definitions"] = s["definitions"]
            print("  Add more (empty to stop):")
            while True:
                m = ask("  Meaning")
                if not m:
                    break
                n = ask("  Note (or Enter)")
                entry["definitions"].append({"meaning": m, "note": n or None})
    else:
        print("\n  Definitions (empty to stop):")
        while True:
            m = ask("  Meaning")
            if not m:
                break
            n = ask("  Note (or Enter)")
            entry["definitions"].append({"meaning": m, "note": n or None})

    # ── examples ──────────────────────────────────────────────────────────────
    own = own_example(my_sentence, s if suggestion else {})
    if suggestion and s.get("examples"):
        print(f"\n  Example sentences:")
        for ex in s["examples"]:
            print(f"    > {ex['de']}")
            print(f"      {ex['en']}")
        action = input("\n  [keep / edit / add more]: ").strip().lower() or "keep"
        if action == "keep":
            entry["examples"] = s["examples"]
        elif action == "edit":
            entry["examples"] = []
            print("  Enter examples (empty German to stop):")
            while True:
                de = ask("  German")
                if not de:
                    break
                en = ask("  English")
                entry["examples"].append({"de": de, "en": en})
        else:
            entry["examples"] = s["examples"]
            print("  Add more (empty to stop):")
            while True:
                de = ask("  German")
                if not de:
                    break
                en = ask("  English")
                entry["examples"].append({"de": de, "en": en})
    else:
        print("\n  Examples (empty German to stop):")
        while True:
            de = ask("  German")
            if not de:
                break
            en = ask("  English")
            entry["examples"].append({"de": de, "en": en})

    if own:
        entry["examples"].insert(0, own)

    if word_type in ("noun", "adj/adv") and suggestion and s.get("compound_parts"):
        cp = confirm_or_edit("Compound parts (comma-separated, '-' for none)", ", ".join(s["compound_parts"]))
        parts = [x.strip() for x in (cp if isinstance(cp, str) else ", ".join(cp)).split(",") if x.strip()]
        if parts and parts != ["-"]:
            entry["compound_parts"] = parts
    wiktionary_definition(entry)
    dwds_link(entry)
    level_tag(entry)

    # ── topics, notes ─────────────────────────────────────────
    print()
    proposed = clean_topics(s.get("topics")) if suggestion else []
    entry["topics"] = clean_topics(confirm_or_edit("Topics (0-2, or 'none')", ", ".join(proposed) or "none"))
    if suggestion and set(proposed) != set(entry["topics"]):
        print(f"    (kept: {', '.join(entry['topics']) or 'none'})")

    sn = s.get("notes") if suggestion else None
    if sn and sn not in (None, "null", "None"):
        entry["notes"] = confirm_or_edit("Notes", sn)
    else:
        n = ask("Personal note (or Enter to skip)")
        if n:
            entry["notes"] = n

    # ── related words: typed semantic links proposed by the AI ───────────────
    # the AI's ideas (kept only when the word is in words.json) and words that look related by their
    # spelling (form_candidates); the word list itself is never sent to the AI
    proposed = (s.get("related", []) if suggestion else []) + form_candidates(words, entry)
    entry["related"] = confirm_related(words, proposed)

    # ── collocations (nouns): typed in by you, one per line ───────────────────
    if entry.get("type") == "noun":
        ask_collocations(entry)

    # ── exercise sentences: yours first, then the examples, then generated ───
    build_exercises(entry, api_key if not manual else None, words=words)

    # ── preview & save ────────────────────────────────────────────────────────
    print()
    print_entry(entry)
    confirm = ask("Save this entry? (y/n)", "y")
    if confirm.lower() != "y":
        print("  Cancelled.")
        return

    words.append(entry)
    root_added(words, entry)

    n_linked = make_bidirectional(words, entry)
    if n_linked > 0:
        print(f"  Linked back from {n_linked} existing entry/entries.")

    save(words)
    print(f"  '{word}' added successfully!\n")


def cmd_edit(args):
    if not args:
        print("  Usage: python -m vocab_builder edit <word>")
        return
    words = load()
    query = " ".join(args)
    w = find(words, query)
    if not w:
        print(f"  X '{query}' not found.")
        return

    print_entry(w)
    print("  What would you like to edit?\n")
    print("    1) definitions")
    print("    2) examples")
    print("    3) notes")
    print("    4) topics")
    print("    5) related words")
    if w["type"] == "noun":
        print("    6) gender / plural")
    elif w["type"] == "verb":
        print("    6) verb forms (past tense, participle, auxiliary…)")
    elif w["type"] == "adj/adv":
        print("    6) usage (adjective only / adverb only / both)")
    elif w["type"] == "prep/conj":
        print("    6) usage (preposition only / conjunction only / both)")
    print("    7) word type")
    print("    8) exercise sentences")
    print("    9) collocations")
    print("    0) cancel")
    print()

    choice = ask("Choose").strip()

    if choice == "0" or not choice:
        print("  Cancelled.")
        return

    elif choice == "1":
        print(f"\n  Current definitions:")
        for i, d in enumerate(w.get("definitions", []), 1):
            note = f" ({d['note']})" if d.get("note") else ""
            print(f"    {i}. {d['meaning']}{note}")
        print("\n  Options: [add / replace / remove]")
        action = ask("Action", "add").lower()
        if action == "add":
            meaning = ask("New meaning")
            if meaning:
                note = ask("Note (or Enter to skip)")
                w.setdefault("definitions", []).append({"meaning": meaning, "note": note or None})
        elif action == "replace":
            idx = ask("Replace which number?")
            if idx.isdigit() and 1 <= int(idx) <= len(w.get("definitions", [])):
                i = int(idx) - 1
                meaning = ask("New meaning", w["definitions"][i]["meaning"])
                note = ask("Note (or Enter to skip)", w["definitions"][i].get("note") or "")
                w["definitions"][i] = {"meaning": meaning, "note": note or None}
        elif action == "remove":
            idx = ask("Remove which number?")
            if idx.isdigit() and 1 <= int(idx) <= len(w.get("definitions", [])):
                removed = w["definitions"].pop(int(idx) - 1)
                print(f"  Removed: {removed['meaning']}")

    elif choice == "2":
        print(f"\n  Current examples:")
        for i, e in enumerate(w.get("examples", []), 1):
            print(f"    {i}. {e['de']}")
            print(f"       {e['en']}")
        print("\n  Options: [add / replace / remove]")
        action = ask("Action", "add").lower()
        if action == "add":
            de = ask("German sentence")
            if de:
                en = ask("English translation")
                w.setdefault("examples", []).append({"de": de, "en": en})
        elif action == "replace":
            idx = ask("Replace which number?")
            if idx.isdigit() and 1 <= int(idx) <= len(w.get("examples", [])):
                i = int(idx) - 1
                de = ask("German sentence", w["examples"][i]["de"])
                en = ask("English translation", w["examples"][i]["en"])
                w["examples"][i] = {"de": de, "en": en}
        elif action == "remove":
            idx = ask("Remove which number?")
            if idx.isdigit() and 1 <= int(idx) <= len(w.get("examples", [])):
                removed = w["examples"].pop(int(idx) - 1)
                print(f"  Removed: {removed['de']}")

    elif choice == "3":
        current = w.get("notes") or ""
        print(f"\n  Current note: {current or '—'}")
        new_note = ask("New note (or Enter to clear)")
        w["notes"] = new_note if new_note else None

    elif choice == "4":
        current = ", ".join(w.get("topics", []))
        print(f"\n  Current topics: {current or '—'}")
        print("  Allowed: " + ", ".join(TOPICS))
        new_topics = ask("New topics (comma-separated, max 2)", current)
        w["topics"] = clean_topics(new_topics)

    elif choice == "5":
        w["related"] = confirm_related(words, w.get("related", []))
        n_linked = make_bidirectional(words, w)
        if n_linked > 0:
            print(f"  Linked back from {n_linked} existing entry/entries.")

    elif choice == "6":
        if w["type"] == "noun":
            w["gender"] = ask_choice("Gender", GENDERS, w.get("gender", ""))
            w["plural"] = ask("Plural form", w.get("plural", "") or "")
            w.pop("plural_card", None)
            ask_plural_card(w)
            w["preposition"] = ask("Fixed preposition + case, e.g. vor + DAT (or Enter for none)",
                                   w.get("preposition", "") or "") or None
        elif w["type"] == "verb":
            w["auxiliary"]       = ask_choice("Auxiliary", ["haben", "sein"], w.get("auxiliary", "haben"))
            w["past_tense"]      = ask("Past tense", w.get("past_tense", "") or "")
            w["past_participle"] = ask("Past participle", w.get("past_participle", "") or "")
            w["present_3sg"]     = ask("er/sie/es, present", w.get("present_3sg", "") or "")
            w["verb_class"]      = ask_choice("Verb class", VERB_CLASSES, w.get("verb_class", "regular"))
            sep = ask("Separable? (y/n)", "y" if w.get("is_separable") else "n")
            w["is_separable"] = sep.lower() == "y"
            w["reflexive"] = norm_reflexive(ask("Reflexive (akk / dat / no)", norm_reflexive(w.get("reflexive")) or "no"))
            w["preposition"] = ask("Preposition + case (or Enter to clear)", w.get("preposition", "") or "") or None
            w["family_root"]    = ask("Family root", w.get("family_root", "") or "")
            w["prefix"]         = ask("Prefix (or Enter to clear)", w.get("prefix", "") or "") or None
            lexicon_verb(w)
        elif w["type"] == "adj/adv":
            USAGE_OPTIONS = ["both", "adjective only", "adverb only"]
            w["usage"] = ask_choice("Usage", USAGE_OPTIONS, w.get("usage", "both"))
            w["preposition"] = ask("Fixed preposition + case, e.g. auf + AKK (or Enter for none)",
                                   w.get("preposition", "") or "") or None
        elif w["type"] == "prep/conj":
            USAGE_OPTIONS = ["both", "preposition only", "conjunction only"]
            w["usage"] = ask_choice("Usage", USAGE_OPTIONS, w.get("usage", "both"))
        if w.get("preposition") is None:
            w.pop("preposition", None)

    elif choice == "7":
        w["type"] = ask_choice("Word type", WORD_TYPES, w.get("type", "other"))

    elif choice == "8":
        build_exercises(w, load_api_key(), words=words)

    elif choice == "9":
        edit_collocations(w)

    else:
        print("  Invalid choice.")
        return

    dwds_link(w)          # the word or its type may have changed
    level_tag(w)

    # examples, forms and word type decide the exercises: re-check them
    if choice in ("2", "6", "7") and EX_OK:
        if ask("Update the exercise sentences too? (y/n)", "y").lower() == "y":
            build_exercises(w, load_api_key(), words=words)

    print()
    print_entry(w)
    confirm = ask("Save changes? (y/n)", "y")
    if confirm.lower() != "y":
        print("  Cancelled.")
        return

    # update in list
    for i, entry in enumerate(words):
        if entry["id"] == w["id"]:
            words[i] = w
            break

    save(words)
    print(f"  '{w['word']}' updated.\n")


def cmd_delete(args):
    if not args:
        print("  Usage: python -m vocab_builder delete <word>")
        return
    words = load()
    query = " ".join(args)
    w = find(words, query)
    if not w:
        print(f"  X '{query}' not found.")
        return

    print_entry(w)
    confirm = ask(f"Delete '{w['word']}'? This cannot be undone. (y/n)", "n")
    if confirm.lower() != "y":
        print("  Cancelled.")
        return

    deleted_word = w["word"]
    root_removed(words, w, load_api_key())
    words = [x for x in words if x["id"] != w["id"]]

    # remove deleted word from all related lists
    cleaned = 0
    for entry in words:
        before = len(entry.get("related", []))
        entry["related"] = [r for r in entry.get("related", []) if r.get("word") != deleted_word]
        if len(entry["related"]) < before:
            cleaned += 1

    if cleaned:
        print(f"  Removed '{deleted_word}' from {cleaned} related list(s).")

    save(words)
    print(f"  '{deleted_word}' deleted.\n")


def cmd_levels(args):
    words = load()
    if not levels.available():
        print("  ! private/sources/goethe/DWDS_A1_liste.csv (A2, B1) not found (see private/sources/goethe/LICENCE.md)")
        return
    changed, counts = levels.fill(words)
    print("  " + ", ".join(f"{lv}: {n}" for lv, n in counts.items()) + f"  ({len(words)} words)")
    print("  B2+ = not in the Goethe lists A1 to B1 (there is none for B2): mostly B2, also phrases,")
    print('  compounds and Swiss words. A level set by hand, with "level_manual": true, is kept.')
    if changed:
        save(words)
    else:
        print("  nothing changed")


def cmd_dwds(args):
    """Fill or refresh the DWDS link and frequency class of every word, offline."""
    if not dwds.available():
        print("  ! private/sources/dwds/dwds_lemmata_<date>.json not found (see private/sources/dwds/LICENCE.md)")
        return
    words = load()
    changed, missing = dwds.fill(words)
    print(f"  {len(words) - len(missing)} words found in the DWDS lemma list ({dwds.file_date()}), "
          f"{changed} changed, {len(missing)} not found:")
    for m in missing:
        print(f"    {m}")
    print('  (a link you add by hand, as "dwds": {"url": ..., "manual": true}, is kept)')
    if changed and ask("Save? (y/n)", "y").lower() == "y":
        save(words)


def cmd_exercises(args):
    """Check one word's exercises against its current forms, fill the empty ones, replace any you choose."""
    if not args:
        print("  Usage: python -m vocab_builder exercises <word>")
        return
    words = load()
    w = find(words, " ".join(args))
    if not w:
        print(f"  X '{' '.join(args)}' not found.")
        return
    build_exercises(w, load_api_key(), words=words)
    if ask("Save? (y/n)", "y").lower() == "y":
        save(words)


def cmd_links(args):
    import json
    from .links import fix
    words = load()
    before = json.dumps(words, ensure_ascii=False)
    fix(words)
    if json.dumps(words, ensure_ascii=False) == before:
        print("  nothing to change")
    elif "--dry-run" in args:
        print("  (dry run, nothing written)")
    else:
        save(words)


def cmd_lexikon(args):
    from .deps import LEXICON, require_morphy
    require_morphy("The lexicon lookup")
    w = args[0] if args else "mitnehmen"
    print(LEXICON.verb(w) or LEXICON.noun(w) or f"  '{w}' is not in the lexicon")


def cmd_karten(args):
    from .karten.web import build
    n_entries, n_cards = build()
    print(f"  web/data/karten.json: {n_entries} entries, {n_cards} cards; web/js/schema.js")


# ── entry point ────────────────────────────────────────────────────────────────

COMMANDS = {
    "list":   cmd_list,
    "show":   cmd_show,
    "add":    cmd_add,
    "edit":   cmd_edit,
    "delete": cmd_delete,
    "topics": cmd_topics,
    "family": cmd_family,
    "exercises": cmd_exercises,
    "dwds":   cmd_dwds,
    "levels": cmd_levels,
    "karten": cmd_karten,
    "links":  cmd_links,
    "lexikon": cmd_lexikon,
}

def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return
    cmd = args[0].lower()
    if cmd not in COMMANDS:
        print(f"  Unknown command '{cmd}'. Try: {', '.join(COMMANDS)}")
        sys.exit(1)
    if cmd in ("add", "edit", "exercises"):
        from .deps import warn_morphy
        warn_morphy("the lexicon checks and the exercise sentences")
    COMMANDS[cmd](args[1:])
