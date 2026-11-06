"""DWDS lemma list (private/sources/dwds/dwds_lemmata_<date>.json): the article link and the frequency class
of a word, looked up offline.

The file is the DWDS "Lemmadatenbank" download (281,971 lemmas: part of speech, frequency class
0 to 6, article type, URL). DWDS offers it for download; the terms forbid automated querying of
the website, not use of the download (private/sources/dwds/LICENCE.md). Frequency class 6 is the most
frequent (und, sein), 0 the rarest; n/a for entries without one.

A word in words.json gets
    "dwds": {"url": "https://www.dwds.de/wb/Haus", "freq": 5}
(freq left out when DWDS has none). A link set by hand, with "manual": true, is never changed.
When the list has several entries with the same spelling and
part of speech (die Bank: bench and bank), the link goes to the page that holds them all and the
class is the higher one; which one is meant is not in the list.

    python -m vocab_builder dwds        fills or refreshes every entry and lists the words not found
"""
import glob
import io
import json
import os
import re

from .paths import SOURCES

DWDS_DIR = os.path.join(SOURCES, "dwds")

# our word types -> DWDS parts of speech that fit
POS = {
    "noun": {"Substantiv"},
    "verb": {"Verb"},
    "adj/adv": {"Adjektiv", "Adverb", "partizipiales Adjektiv", "Partikel"},
    "prep/conj": {"Präposition", "Konjunktion", "Pronominaladverb", "Präposition + Artikel", "Adverb"},
    "expression": {"Mehrwortausdruck"},
    "construction": {"Mehrwortausdruck"},
}

# when several entries fit, the fuller article wins
TYPE_RANK = {"Vollartikel": 0, "Basisartikel": 1, "Basisartikel-D": 2, "Minimalartikel": 3, "Verweisartikel": 4}

_index = None
_variants = None
_file = None


def lemma_file():
    files = sorted(glob.glob(os.path.join(DWDS_DIR, "dwds_lemmata_*.json")))
    return files[-1] if files else None


def available():
    return lemma_file() is not None


def load():
    """{lemma: [entries]}. The spellings in `other_lemmata` (old or wrong spellings that point to
    the entry: Endscheidung, Author) go to a second index, used only when no lemma matches."""
    global _index, _variants, _file
    if _index is None:
        _file = lemma_file()
        _index, _variants = {}, {}
        if _file:
            for x in json.load(io.open(_file, encoding="utf-8")):
                _index.setdefault(x["lemma"], []).append(x)
                for lem in x.get("other_lemmata", []):
                    _variants.setdefault(lem, []).append(x)
    return _index


def file_date():
    """The download date in the file name (YYYY-MM-DD), for the citation."""
    load()
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(_file or ""))
    return m.group(1) if m else None


def headword(word):
    """How DWDS spells the lemma: no article, no sich (die Angst -> Angst, sich ausruhen -> ausruhen)."""
    w = re.sub(r"^(der/die|der|die|das)\s+", "", (word or "").strip())
    w = re.sub(r"^sich\s+", "", w)
    return w.strip()


def lookup(w):
    """{'url': ..., 'freq': n} for an entry of words.json, or None when DWDS has no such lemma."""
    hw = headword(w["word"])
    found = load().get(hw) or _variants.get(hw)
    if not found:
        return None
    fits = [x for x in found if x.get("pos") in POS.get(w.get("type"), set())] or found
    fits = sorted(fits, key=lambda x: TYPE_RANK.get(x.get("type"), 9))
    pages = {x["url"].split("#")[0] for x in fits}
    if len(fits) == 1:
        url = fits[0]["url"]
    elif len(pages) == 1:                 # homographs on one page (Bank#1, Bank#2): the whole page
        url = pages.pop()
    else:
        url = fits[0]["url"]
    out = {"url": url}
    freqs = [x["freq"] for x in fits if isinstance(x.get("freq"), int)]
    if freqs:
        out["freq"] = max(freqs)
    return out


def fill(words):
    """Set or refresh `dwds` on every entry; returns (changed, missing words)."""
    changed, missing = 0, []
    for w in words:
        if (w.get("dwds") or {}).get("manual"):      # set by hand: kept as it is
            continue
        got = lookup(w)
        if got is None:
            missing.append(w["word"])
            if "dwds" in w:
                del w["dwds"]
                changed += 1
            continue
        if w.get("dwds") != got:
            w["dwds"] = got
            changed += 1
    return changed, missing
