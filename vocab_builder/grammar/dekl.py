"""Topic Deklination: determiner (or none) + adjective + noun, typed as one phrase.

A cell is one determiner type, one case and one gender (or the plural), for example
dekl::ein::dat::m (einem alten Mann). The determiner types follow a common declension table:

  der      der, die, das (definite article)
  dieser   dieser, jener, jeder, welcher, alle (same endings as der)
  ein      ein, eine (no plural)
  kein     kein, keine (like ein, with a plural)
  mein     the possessives mein, dein, sein, ihr, unser, euer, Ihr (like kein)
  ohne     no article, also after numbers and viele, einige, mehrere

6 types x 4 cases x 4 genders, minus ein in the plural and kein in the genitive (rare): 88 cells.
Two sentences per cell go on cards; the others are kept in reserve.
"""
import re

from .. import checks as EX

GENDER_OF = {"der": "m", "die": "f", "das": "n"}
DET_EN = {"der": "definite article", "dieser": "dieser", "ein": "indefinite article",
          "kein": "kein", "mein": "possessive", "ohne": "no article"}
PER_CELL = 2

_DER = {"der", "die", "das", "den", "dem", "des"}
_DIESER = re.compile(r"^(dies|jen|jed|welch|manch|solch|all)(e|er|es|em|en)$")
_EIN = {"ein", "eine", "einen", "einem", "einer", "eines"}
_KEIN = re.compile(r"^kein(e|en|em|er|es)?$")
_POSS = re.compile(r"^(mein|dein|sein|ihr|unser|euer|eur)(e|en|em|er|es)?$", re.I)


def cell_id(det, case, gender):
    return f"dekl::{det}::{case.lower()}::{gender}"


def det_type(token):
    t = token.lower()
    if t in _DER:
        return "der"
    if _DIESER.match(t):
        return "dieser"
    if t in _EIN:
        return "ein"
    if _KEIN.match(t):
        return "kein"
    if _POSS.match(token):
        return "mein"
    return "ohne"


def phrase(s):
    a, b = s["blanks"][0]
    return s["de"][a:b]


def gender_of(entry, number):
    if number == "PLU":
        return "pl"
    return GENDER_OF.get((entry.get("gender") or entry["word"].split()[0]))


def cell_of(s, entry):
    """The cell a sentence belongs to, from its phrase and the noun's gender."""
    det = det_type(phrase(s).split()[0])
    case, number = s["form"].split(":")
    return cell_id(det, case, gender_of(entry, number))


def check(s, entry, morph, cell=None):
    """The words.json checker (agreement, case after a preposition, spelling, length) plus: the
    determiner type, case, gender and number of the phrase are those of the cell."""
    slot = "dekl_pl" if s["form"].endswith("PLU") else "dekl"
    shown = s["de"][:s["blanks"][0][0]] + "[" + phrase(s) + "]" + s["de"][s["blanks"][0][1]:]
    r = EX.check(entry, slot, s["form"], {"de": shown, "en": s.get("en") or "-", "adj": s.get("adj")}, morph)
    problems = list(r["problems"])
    status = r["status"]
    if cell:
        want = cell["id"]
        got = cell_of(s, entry)
        if got != want:
            problems.append(f"the phrase is {got}, the cell is {want}")
            status = "error"
    return status, problems


def choose(cell_sentences, cell=None):
    """Mark which sentences go on cards: the first PER_CELL that pass, in their order, preferring
    sentences written or chosen by hand (own, example) over generated ones."""
    def rank(s):
        src = s.get("source", "")
        return 0 if ("own" in src or "example" in src) else 1
    ok = [s for s in cell_sentences if s.get("status") in ("ok", "check")]
    keep = sorted(ok, key=rank)[:PER_CELL]
    for s in cell_sentences:
        s["use"] = any(s is k for k in keep)


def hint(s, det):
    """'definite article + old + lift'; for kein and the possessives the
    determiner itself is given (kein, my)."""
    first = phrase(s).split()[0]
    if det in ("kein", "dieser"):
        label = re.sub(r"(e|er|es|em|en)$", "", first.lower()) or first.lower()
        label = {"dies": "dieser", "jen": "jener", "jed": "jeder", "welch": "welcher", "all": "alle",
                 "manch": "mancher", "solch": "solcher"}.get(label, label)
    elif det == "mein":
        stem = _POSS.match(first).group(1).lower()
        label = {"mein": "my", "dein": "your (du)", "sein": "his / its", "ihr": "her / their",
                 "unser": "our", "euer": "your (ihr)", "eur": "your (ihr)"}[stem]
        if first[:1].isupper() and stem == "ihr" and not s["de"].startswith(first):
            label = "your (Sie)"
    elif det == "ohne":
        t = first.lower()
        label = t if (t in EX.NUMBERS or t.startswith(("viel", "einig", "mehrer", "wenig"))) else "no article"
    else:
        label = DET_EN[det]
    noun = s.get("noun_en")
    if noun and s["form"].endswith("PLU"):
        noun += " (Plural)"
    return " + ".join(x for x in (label, s.get("adj_en") or s.get("adj"), noun) if x)
