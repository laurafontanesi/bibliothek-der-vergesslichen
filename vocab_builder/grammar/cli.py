"""vocab_builder grammar: look after grammar.json, the curriculum and the grammar topics.

  python -m vocab_builder grammar status            curriculum per level, topics and how full their cells are
  python -m vocab_builder grammar cells dekl        the cells of a topic with the sentences on cards
  python -m vocab_builder grammar check [topic]     run the checker again on every sentence (after a code change)
  python -m vocab_builder grammar add konnektoren <word> "sentence with the [word]" "English"
  python -m vocab_builder grammar add prep_fixed <word> "sentence with [prep] [article]" "English"
                                      a grammar sentence for a connector or a fixed preposition of a
                                      word in words.json (checked like the others; it goes on a card,
                                      and in a full cell the last card goes to reserve), then run cards
  python -m vocab_builder grammar cards             write grammar_cards.json, the grammar cards for the website
                                      (run it after every change to grammar.json, then commit both)
"""
import sys

from .. import checks as EX
from ..model import load as load_words
from . import dekl, fromwords, kasus, model

CHECKERS = {"dekl": dekl, "kasus": kasus, "konnektoren": fromwords, "prep_fixed": fromwords}


def cmd_status(args):
    g = model.load()
    print("Curriculum")
    for lv in model.LEVELS[:5]:
        ss = [s for s in g["structures"] if s["level"] == lv]
        by = {}
        for s in ss:
            by[s["status"]] = by.get(s["status"], 0) + 1
        print(f"  {lv}: {len(ss):>3} structures  " + ", ".join(f"{n} {k}" for k, n in sorted(by.items())))
    print("\nTopics (grammar cards)")
    for t in sorted(g["topics"], key=lambda t: t["order"]):
        n = len(t.get("cells", []))
        if n:
            full = sum(1 for c in t["cells"] if model.on_cards(c))
            cards = sum(len(model.on_cards(c)) for c in t["cells"])
            extra = f"{cards} cards, {full}/{n} cells with cards"
        else:
            extra = "no cells"
        print(f"  {t['order']:>2}. {t['name']:<45} {t['status']:<8} {extra}")


def cmd_cells(args):
    g = model.load()
    t = model.topic(g, args[0] if args else "dekl")
    for c in t["cells"]:
        use = model.on_cards(c)
        print(f"{c['id']:<24} {len(use)} + {len(c.get('sentences', [])) - len(use)} in reserve")
        for s in use:
            mod = CHECKERS.get(t["id"])
            h = mod.hint(s, c.get("det")) if mod else ""
            print(f"    {s['de']}   [{h}]")


def cmd_check(args):
    g = model.load()
    words = {w["id"]: w for w in load_words()}
    topics = [model.topic(g, args[0])] if args else [t for t in g["topics"] if t["id"] in CHECKERS]
    morph = EX.Morph()
    morph.load(EX.with_suffixes({tok for t in topics for c in t["cells"] for s in c.get("sentences", [])
                                 for tok in EX.toks(s["de"])}))
    changed = 0
    for t in topics:
        mod = CHECKERS[t["id"]]
        for c in t["cells"]:
            for s in c.get("sentences", []):
                status, problems = mod.check(s, words.get(s.get("word_id")), morph, c)
                if status != s.get("status"):
                    changed += 1
                    print(f"  {c['id']}: {s.get('status')} -> {status}  {s['de']}  {'; '.join(problems)}")
                    s["status"] = status
            mod.choose(c["sentences"], c)
    model.save(g)
    print(f"{changed} sentence(s) changed status")


def cmd_add(args):
    """vocab_builder grammar add <topic> <word> <sentence with [gaps]> <English>"""
    if len(args) != 4 or args[0] not in ("konnektoren", "prep_fixed"):
        print('  Usage: python -m vocab_builder grammar add konnektoren seitdem "[Seitdem] wohnt sie in Basel." "Since then ..."')
        print('         python -m vocab_builder grammar add prep_fixed "sich freuen" "Ich freue mich [auf] [den] Urlaub." "I ..."')
        return
    tid, word, text, en = args
    words = load_words()
    w = next((x for x in words if x["word"] == word), None)
    if not w:
        print(f"  ! «{word}» is not in words.json (add it with vocab_builder first)")
        return
    de, spans, marked = EX.parse_bracketed(text)
    g = model.load()
    t = model.topic(g, tid)
    if tid == "konnektoren":
        if len(spans) != 1:
            print("  ! mark the connector, and only the connector, in [brackets]")
            return
        cid = f"konnektoren::{w['id']}"
        s = {"de": de, "en": en, "blanks": spans, "slot": "pc1", "answer": marked[0], "word": w["word"],
             "word_id": w["id"], "source": "own"}
        new_cell = {"id": cid, "topic": tid, "word": w["word"], "word_id": w["id"], "rule": w.get("notes") or "",
                    "sentences": []}
    else:
        preps = EX.verb_preps(w)
        if len(spans) != 2 or not preps:
            print("  ! mark the preposition and the article: ... [auf] [den] ...; the word needs a preposition in words.json")
            return
        n = next((i for i, (p, _) in enumerate(preps, 1) if p == marked[0].lower()), None)
        if not n:
            print(f"  ! «{marked[0]}» is not the preposition of {w['word']} ({w.get('preposition')})")
            return
        prep, case = preps[n - 1]
        cid = f"prep_fixed::{w['id']}::prep{n}"
        s = {"de": de, "en": en, "blanks": [spans[1]], "slot": f"prep{n}", "form": f"{prep} + {case}",
             "prep_span": spans[0], "answer": marked[1], "hint": f"{w['word']} {prep}", "word": w["word"],
             "word_id": w["id"], "source": "own"}
        new_cell = {"id": cid, "topic": tid, "word": w["word"], "word_id": w["id"], "form": f"{prep} + {case}",
                    "sentences": []}
    bare = EX.bare(w["word"]).replace("sich ", "").lower()
    stems = {bare[:max(4, len(bare) - 3)]}
    if w.get("family_root"):
        stems.add(w["family_root"].lower()[:max(4, len(w["family_root"]) - 3)])
    for k in ("past_tense", "past_participle", "present_3sg"):      # dachte, gedacht, denkt
        for form in (w.get(k) or "").replace("sich", "").split():
            if len(form) > 3:
                stems.add(form.lower())
    if tid == "prep_fixed" and not any(tok.lower().startswith(st) for tok in EX.toks(de) for st in stems):
        print(f"  ! «{w['word']}» is not in the sentence")
        return
    c = next((c for c in t["cells"] if c["id"] == cid), None)
    if c is None:
        c = new_cell
        t["cells"].append(c)
    morph = EX.Morph()
    morph.load(EX.with_suffixes(set(EX.toks(de))))
    s["status"], problems = fromwords.check(s, w, morph, c)
    if s["status"] not in ("ok", "check"):
        print(f"  ! not added: {'; '.join(problems)}")
        if not c["sentences"]:
            t["cells"].remove(c)
        return
    if any(x["de"] == de for x in c["sentences"]):
        print("  ! this sentence is already in the cell")
        return
    # your own sentence goes on a card: first in the list, so choose() picks it; if the cell was
    # full, its last card goes to reserve
    c["sentences"].insert(0, s)
    fromwords.choose(c["sentences"], c)
    model.save(g)
    print(f"  added to {cid} ({'on a card' if s.get('use') else 'in reserve'}). Now: python -m vocab_builder grammar cards")


def cards_json(g=None):
    """The text of grammar_cards.json for the current grammar.json and words.json."""
    import json
    from ..karten.grammar_cards import card_records
    from ..sanitize import clean
    recs = card_records(g or model.load(), load_words())
    for r in recs:                      # only the markup the build writes (vocab_builder/sanitize.py)
        for k, v in r.items():
            if isinstance(v, str):
                r[k] = clean(v)
    return json.dumps(recs, ensure_ascii=False, indent=1) + "\n"


def cmd_cards(args):
    from ..paths import GRAMMAR_CARDS
    text = cards_json()
    with open(GRAMMAR_CARDS, "w", encoding="utf-8") as f:
        f.write(text)
    n = text.count('"topic":')
    print(f"grammar_cards.json written: {n} grammar cards")


COMMANDS = {"status": cmd_status, "cells": cmd_cells, "check": cmd_check, "cards": cmd_cards, "add": cmd_add}


def main():
    args = sys.argv[1:]
    if not args or args[0] not in COMMANDS:
        print(__doc__)
        return
    COMMANDS[args[0]](args[1:])
