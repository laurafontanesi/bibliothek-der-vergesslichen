"""Two grammar topics built around words of words.json:

  konnektoren   the Konnektor cards (pc1 to pc4): a sentence with the preposition or conjunction as
                the gap, the meaning as the hint. One cell per word, all four sentences on cards.
                Cell: konnektoren::<word id>.
  prep_fixed    case after a fixed preposition (prep1, prep2 of verbs, nouns, adjectives): the
                preposition stays in the sentence, the article is the gap, the hint is the word and
                its preposition (hoffen auf). Whether a word takes a preposition, and which case, is
                practised on the word cards (it is part of the Produzieren answer). Cell: prep_fixed::<word id>::<n>.

Both use the sentence checker (vocab_builder/checks.py, slots pc and prep).
"""
from .. import checks as EX

PER_CELL = {"konnektoren": 4, "prep_fixed": 1}


def _shown(s, blanks):
    out, last = "", 0
    for a, b in blanks:
        out += s["de"][last:a] + "[" + s["de"][a:b] + "]"
        last = b
    return out + s["de"][last:]


def check(s, entry, morph, cell=None):
    """The sentence check (vocab_builder/checks.py), with both gaps for prep."""
    if s["slot"].startswith("pc"):
        slot, form, blanks = s["slot"], entry["word"], s["blanks"]
    else:
        slot, form, blanks = s["slot"], s.get("form"), [s["prep_span"]] + s["blanks"]
    r = EX.check(entry, slot, form, {"de": _shown(s, blanks), "en": s.get("en") or "-"}, morph)
    return r["status"], list(r["problems"])


def choose(cell_sentences, cell=None):
    n = PER_CELL.get((cell or {}).get("topic"), 1)
    ok = [s for s in cell_sentences if s.get("status") in ("ok", "check")]
    for s in cell_sentences:
        s["use"] = any(s is k for k in ok[:n])


def hint(s, det=None):
    return s.get("hint", "")
