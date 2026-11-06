"""
Terminal helpers: questions with defaults, choices, and printing a word entry.
"""
from .deps import EX
from .model import reflexive_label


def ask(prompt: str, default: str = "") -> str:
    val = input(f"  {prompt}" + (f" [{default}]" if default else "") + ": ").strip()
    return val if val else default


def ask_choice(prompt: str, options: list, default: str = "") -> str:
    print(f"  {prompt}")
    for i, opt in enumerate(options, 1):
        print(f"    {i}) {opt}")
    while True:
        val = input(f"  Choose 1-{len(options)}" + (f" [{default}]" if default else "") + ": ").strip()
        if not val and default:
            return default
        if val.isdigit() and 1 <= int(val) <= len(options):
            return options[int(val) - 1]
        print(f"  Please enter a number between 1 and {len(options)}.")


def confirm_or_edit(label: str, value, options: list = None):
    """Show a suggested value and let the user confirm or override."""
    if value is None or value == [] or value == "null":
        display = "—"
    elif isinstance(value, list):
        display = ", ".join(str(v) for v in value)
    elif isinstance(value, bool):
        display = "yes" if value else "no"
    else:
        display = str(value)

    if options:
        override = input(f"  {label} [{display}] (Enter to keep, or number to change): ").strip()
        if override.isdigit() and 1 <= int(override) <= len(options):
            return options[int(override) - 1]
        return value
    else:
        override = input(f"  {label} [{display}]: ").strip()
        if not override:
            return value
        if isinstance(value, bool):
            return override.lower() in ("y", "yes", "true", "1")
        if isinstance(value, list):
            return [v.strip() for v in override.split(",") if v.strip()]
        return override

def print_entry(w: dict):
    print()
    print(f"  ┌─ {w['word']}  [{w['type']}]")

    if w["type"] == "noun":
        print(f"  │  gender: {w.get('gender','?')}   plural: {w.get('plural','?')}"
              + (f"   · {w['preposition']}" if w.get("preposition") else ""))
    elif w["type"] == "verb":
        aux  = w.get("auxiliary", "")
        pt   = w.get("past_tense", "")
        pp   = w.get("past_participle", "")
        sep  = "separable" if w.get("is_separable") else "inseparable"
        ref  = f" · {reflexive_label(w.get('reflexive'))}" if w.get("reflexive") else ""
        prep = f" · {w['preposition']}" if w.get("preposition") else ""
        cls  = f"{w['verb_class']} · " if w.get("verb_class") else ""
        p3   = f"er {w['present_3sg']} · " if w.get("present_3sg") else ""
        print(f"  │  {cls}{p3}{aux} · {pt} · {pp}   ({sep}{ref}{prep})")
        if w.get("imperative") or w.get("konjunktiv_2"):
            bits = [w["imperative"] + "!" if w.get("imperative") else "", "Konj. II " + w["konjunktiv_2"] if w.get("konjunktiv_2") else ""]
            print(f"  │  {' · '.join(b for b in bits if b)}")
        if w.get("family_root") and w["family_root"] != w["word"]:
            print(f"  │  family: {w['family_root']}  (prefix: {w.get('prefix','')})")

    if w.get("usage"):
        print(f"  │  usage: {w['usage']}" + (f"   · {w['preposition']}" if w["type"] == "adj/adv"
                                              and w.get("preposition") else ""))

    print(f"  │")
    for i, d in enumerate(w.get("definitions", []), 1):
        note = f"  -> {d['note']}" if d.get("note") else ""
        print(f"  │  {i}. {d['meaning']}{note}")
    if w.get("definition_de"):
        print(f"  │  DE: {w['definition_de']}")

    if w.get("examples"):
        print(f"  │")
        for ex in w["examples"]:
            print(f"  │  > {ex['de']}")
            print(f"  │    {ex['en']}")

    if w.get("topics"):
        print(f"  │  topics:  {', '.join(w['topics'])}")
    if w.get("related"):
        rel = ", ".join(f"{r['word']} ({r['kind']})" if isinstance(r, dict) else str(r)
                        for r in w["related"])
        print(f"  │  related: {rel}")
    for k in w.get("collocations") or []:
        print(f"  │  colloc:  {k['de']} = {k['en']}" + (f"  ({k['note']})" if k.get("note") else ""))
    if w.get("notes"):
        print(f"  │  note: {w['notes']}")
    if w.get("exercises") and EX:
        print(f"  │")
        for e in w["exercises"]:
            print(f"  │  ▢ {e['label']:<26} {EX.show(e)}")

    print(f"  └─ added: {w.get('added','?')}")
    print()
