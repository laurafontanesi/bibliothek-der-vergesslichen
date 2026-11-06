"""
The gap-fill exercises of a verb: which ones it gets, filling them from your own sentences,
the examples or the API, and checking every sentence with vocab_builder.checks.
"""
import re
from .deps import EX, EX_OK, changes_stem
from .model import family_members
from .claude import call_claude
from .ui import ask


# ── exercise sentences ─────────────────────────────────────────────────────────
# Each verb gets a fixed set of gap-fill exercises (see README, field `exercises`). They are filled in
# this order: exercises the word already has (if they still pass the check), your own sentence, the
# other examples, and only then sentences written by the API. Every sentence goes through
# the sentence checker (vocab_builder/checks.py) before it is kept.

def stem_changes(entry: dict) -> bool:
    if changes_stem is None:
        return False
    return changes_stem(entry["word"], entry.get("present_3sg"), entry.get("prefix"), entry.get("is_separable"))


def _spec_form(entry: dict, slot: str, form=None):
    """The form a slot tests, as the checker expects it."""
    if slot == "praet":
        return entry.get("past_tense")
    if slot == "praes":
        return entry.get("present_3sg")
    if slot == "part":
        return (entry.get("past_participle") or "").split("/")[0].strip()
    if slot == "refl":
        return "mir/dir" if entry.get("reflexive") == "dat" else "mich/dich"
    return form


def _exercise(spec: dict, r: dict, source: str, extra: dict = None) -> dict:
    """`extra`: the API answer, with the English verb for the hint (verb_en).
    Without it the card falls back to the word's short meaning."""
    ex = {"slot": spec["slot"], "label": spec["label"], "de": r["de"], "en": r["en"],
          "blanks": r["blanks"], "source": source}
    extra = extra or {}
    if spec["slot"] in ("part", "praet", "praes") and extra.get("verb_en"):
        ex["verb_en"] = extra["verb_en"]
    return ex


def _generate(entry, specs, morph, api_key, used, feedback=None):
    """Ask the API for the given slots; returns {slot: exercise} for the ones that pass, and problems."""
    text = call_claude(EX.generation_prompt(entry, specs, used, feedback), api_key)
    if not text:
        return {}, {}
    answers = {a.get("id", "").split("|")[-1]: a for a in EX.read_answers_text(text)}
    morph.load(EX.with_suffixes({t for a in answers.values() for t in EX.toks(a.get("de", "").replace("[", "").replace("]", ""))}))
    got, problems = {}, {}
    for spec in specs:
        a = answers.get(spec["slot"])
        if not a:
            problems[spec["slot"]] = ["no answer"]
            continue
        if "skip" in a:
            problems[spec["slot"]] = [f"skipped: {a['skip']}"]
            continue
        sp = dict(spec)
        r = EX.check(entry, sp["slot"], _spec_form(entry, sp["slot"], sp["form"]), a, morph, used)
        if r["status"] in ("ok", "check"):
            got[spec["slot"]] = _exercise(sp, r, "generated", a)
            used.append(r["de"])
        else:
            problems[spec["slot"]] = r["problems"]
    return got, problems


def _own_exercise(entry, spec, morph, used):
    """Let the learner type a sentence with [brackets]; returns an exercise or None."""
    while True:
        de = input("    your sentence with [brackets] (Enter: skip): ").strip()
        if not de:
            return None
        morph.load(EX.with_suffixes(set(EX.toks(de.replace("[", "").replace("]", "")))))
        r = EX.check(entry, spec["slot"], _spec_form(entry, spec["slot"], spec["form"]),
                     {"de": de, "en": "-"}, morph, used, min_words=3)
        if r["status"] not in ("ok", "check"):
            print("    ✗ " + "; ".join(r["problems"]))
            continue
        if r["problems"]:
            print("    (note: " + "; ".join(r["problems"]) + ")")
        r["en"] = ask("  English")
        return _exercise(spec, r, "own")


def build_exercises(entry: dict, api_key: str | None, interactive: bool = True, words: list | None = None) -> None:
    """Fill entry["exercises"]: keep what still fits, use your sentences, generate the rest, let you review.
    `words` (the whole dictionary) tells whether a verb's root verb is in it: then only its Perfekt
    is practised (EX.slots_for says which exercises a word gets)."""
    if not EX_OK:
        print("  (exercises skipped: private/sources/morphy/dictionary.dump not found)")
        return
    specs = EX.slots_for(entry, stem_changes, {w["word"] for w in (words or []) if w is not entry})
    if not specs:
        entry.pop("exercises", None)
        return
    print("\n  Exercises: checking the sentences you have…")
    morph = EX.Morph()
    examples = sorted(entry.get("examples", []), key=lambda e: e.get("source") != "own")
    old = entry.get("exercises", [])
    morph.load(EX.with_suffixes({t for x in examples + old for t in EX.toks(x["de"])}))
    chosen, used = {}, []

    # 1. exercises the word already has, if they still pass (forms may have been edited)
    for e in old:
        spec = next((s for s in specs if s["slot"] == e["slot"]), None)
        if not spec:
            continue
        r = EX.check(entry, e["slot"], _spec_form(entry, e["slot"], spec["form"]),
                     {"de": EX.show(e), "en": e.get("en") or "-"}, morph, min_words=3)
        if r["status"] in ("ok", "check"):
            chosen[e["slot"]] = e
            used.append(e["de"])
        else:
            print(f"  ! {spec['label']}: «{EX.show(e)}» no longer fits ({'; '.join(r['problems'])})")

    # 2. your own sentence, then the other examples (each sentence serves one exercise)
    for spec in specs:
        if spec["slot"] in chosen:
            continue
        for ex in examples:
            if ex["de"] in used:
                continue
            sp = dict(spec)
            r = EX.find_in(entry, sp, ex["de"], ex.get("en", ""), morph, used)
            if not r:
                continue
            chosen[spec["slot"]] = _exercise(sp, r, "own" if ex.get("source") == "own" else "example")
            used.append(ex["de"])
            break

    # 3. the API writes the rest; one retry for the ones that fail the check
    missing = [s for s in specs if s["slot"] not in chosen]
    problems = {}
    if missing and api_key:
        print(f"  Writing {len(missing)} exercise sentence(s) with AI…")
        used_all = used + [e["de"] for e in examples]
        got, problems = _generate(entry, missing, morph, api_key, used_all)
        chosen.update(got)
        retry = [s for s in missing if s["slot"] in problems and not problems[s["slot"]][0].startswith("skipped")]
        if retry:
            fb = [f"{s['slot']}: {'; '.join(problems[s['slot']])}" for s in retry]
            got, problems2 = _generate(entry, retry, morph, api_key, used_all, feedback=fb)
            chosen.update(got)
            problems = {k: v for k, v in {**problems, **problems2}.items() if k not in chosen}
    elif missing:
        print(f"  ({len(missing)} exercise(s) need a sentence; no API key, so write them yourself below)")

    # 4. review
    def ordered():
        return [chosen[s["slot"]] for s in specs if s["slot"] in chosen]

    while interactive:
        print("\n  Exercises:")
        for i, s in enumerate(specs, 1):
            e = chosen.get(s["slot"])
            if e:
                print(f"    {i}. {e['label']:<28} {EX.show(e)}   ({e['source']})")
            else:
                why = "; ".join(problems.get(s["slot"], [])) or "no sentence yet"
                print(f"    {i}. {s['label']:<28} —  ({why})")
        val = input("  Enter to keep; numbers to replace or fill (e.g. 2,4): ").strip()
        if not val:
            break
        for n in sorted({int(x) for x in re.findall(r"\d+", val) if 1 <= int(x) <= len(specs)}):
            spec = specs[n - 1]
            print(f"  {n}. {spec['label']}")
            e = _own_exercise(entry, spec, morph, used)
            if not e and api_key and input("    generate a new one with AI instead? (y/n) [y]: ").strip().lower() in ("", "y"):
                old_s = chosen.get(spec["slot"])
                fb = [f"the learner did not want: «{old_s['de']}»"] if old_s else None
                got, pr = _generate(entry, [spec], morph, api_key, used + [e2["de"] for e2 in examples], fb)
                e = got.get(spec["slot"])
                if not e:
                    print("    ✗ " + "; ".join(pr.get(spec["slot"], ["no answer"])))
            if e:
                chosen[spec["slot"]] = e
    entry["exercises"] = ordered()
    empty = len(specs) - len(entry["exercises"])
    print(f"  {len(entry['exercises'])} exercise(s)" + (f", {empty} without a sentence" if empty else ""))


def root_added(words: list, verb: dict) -> None:
    """A new root verb: its family members now only practise the Perfekt (their Präteritum and
    Präsens repeat the root's), so those exercises are removed from them."""
    for m in family_members(words, verb):
        before = len(m.get("exercises", []))
        m["exercises"] = [e for e in m.get("exercises", []) if e["slot"] not in ("praet", "praes")]
        if len(m["exercises"]) < before:
            print(f"  {m['word']}: Präteritum/Präsens exercises removed (its root {verb['word']} is now in the dictionary)")


def root_removed(words: list, verb: dict, api_key: str | None) -> None:
    """A deleted root verb: its family members need their own Präteritum and Präsens again."""
    members = family_members(words, verb)
    if not members:
        return
    names = ", ".join(m["word"] for m in members)
    print(f"  {verb['word']} was the root of: {names}. They need their own Präteritum/Präsens exercises again.")
    if EX_OK and ask("Write them now? (y/n)", "y").lower() == "y":
        rest = [w for w in words if w is not verb]
        for m in members:
            print(f"\n  -- {m['word']}")
            build_exercises(m, api_key, interactive=True, words=rest)
    else:
        print(f"  Later: python -m vocab_builder exercises <word> for each of them.")
