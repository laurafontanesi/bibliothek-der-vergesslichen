"""The CEFR level of a word, from the Goethe-Zertifikat word lists A1, A2 and B1 that DWDS offers
for download (private/sources/goethe/DWDS_<level>_liste.csv; dwds.de/d/api, "Listen Wortschatz Goethe-Zertifikat").

The lists are protected by copyright (Goethe-Institut, as the DWDS API page says): they are used
here only to tag the words already in words.json, and are not copied into the project or shown on the
website (private/sources/goethe/LICENCE.md). Each lemma is in one list only, the level where it first appears.

A word in words.json gets
    "level": "A1" | "A2" | "B1" | "B2+"
"B2+" means "not in the A1 to B1 lists": mostly B2 words, but also phrases, compounds and Swiss
words; there is no Goethe list for B2 and above. A level set by hand, with "level_manual": true, is
kept.

    python -m vocab_builder levels      fills or refreshes every entry and prints the counts per level
"""
import csv
import io
import os

from .dwds import headword
from .paths import SOURCES

GOETHE_DIR = os.path.join(SOURCES, "goethe")
from .schema import load as _schema   # noqa: E402

LEVELS = _schema()["levels"]["goethe"]   # A1, A2, B1 (schema.json)
ABOVE = _schema()["levels"]["above"]     # B2+

# our word types -> the parts of speech of the lists that fit
POS = {
    "noun": {"Substantiv"},
    "verb": {"Verb"},
    # deshalb, trotzdem are Konjunktion in the lists; eher, nächst Komparativ and Superlativ
    "adj/adv": {"Adjektiv", "Adverb", "partizipiales Adjektiv", "Pronominaladverb", "Partikel", "Konjunktion",
                "Komparativ", "Superlativ"},
    "prep/conj": {"Präposition", "Konjunktion", "Pronominaladverb", "Adverb"},
    "expression": {"Mehrwortausdruck", ""},
    "construction": {"Mehrwortausdruck", ""},
}

_index = None


def available():
    return all(os.path.exists(os.path.join(GOETHE_DIR, f"DWDS_{lv}_liste.csv")) for lv in LEVELS)


def key(lemma):
    """kennen lernen / kennenlernen and so dass / sodass are the same word (old and new spelling)."""
    return lemma.replace(" ", "").lower()


def load():
    """{key: [(level, part of speech, article)]}."""
    global _index
    if _index is None:
        _index = {}
        for lv in LEVELS:
            path = os.path.join(GOETHE_DIR, f"DWDS_{lv}_liste.csv")
            if not os.path.exists(path):
                continue
            for r in csv.DictReader(io.open(path, encoding="utf-8")):
                _index.setdefault(key(r["Lemma"]), []).append((lv, r["Wortart"], r["Artikel"]))
    return _index


def lookup(w):
    """'A1', 'A2' or 'B1' when the word is in a list with a fitting part of speech, else 'B2+'."""
    found = load().get(key(headword(w["word"])), [])
    # a list entry without a part of speech fits any type (allein, seit, während); a different one
    # does not (laut the adjective is not laut the preposition; das Treffen is not treffen)
    fits = [x for x in found if not x[1] or x[1] in POS.get(w.get("type"), set())]
    if w.get("type") in ("expression", "construction", "other"):
        fits = found                             # zum Beispiel, auf jeden Fall: any part of speech
    if w.get("type") == "noun" and w["word"].split()[0] in ("der", "die", "das"):
        same = [x for x in fits if not x[2] or x[2] == w["word"].split()[0]]
        fits = same or fits                      # der Leiter / die Leiter: the article decides
    levels = sorted({x[0] for x in fits}, key=LEVELS.index)
    return levels[0] if levels else ABOVE


def fill(words):
    """Set or refresh `level` on every entry; returns (changed, {level: count})."""
    changed, counts = 0, {lv: 0 for lv in LEVELS + [ABOVE]}
    for w in words:
        if not w.get("level_manual"):
            got = lookup(w)
            if w.get("level") != got:
                w["level"] = got
                changed += 1
        counts[w["level"]] = counts.get(w["level"], 0) + 1
    return changed, counts
