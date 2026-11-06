"""
lexicon.py: look up German word forms in the Morphy / LanguageTool full-form
lexicon (CC BY-SA 4.0, https://danielnaber.de/morphologie/).

The lexicon is a plain-text export with one line per inflected form:

    nehmen_nimmt_VER:3:SIN:PRÄ:NON
    lemma _form  _tags

How to produce it (once): see README, section "Data sources". The file is
expected at private/sources/morphy/dictionary.dump in the repository (about 250 MB, keep it out
of git). If it is missing, every function returns None and vocab_builder falls back
to the model's suggestions.

Tag documentation: https://danielnaber.de/download/wklassen.pdf
  VER:3:SIN:PRT:SFT   verb, 3rd person singular, Präteritum, weak (SFT)
  VER:3:SIN:PRÄ:NON   verb, 3rd person singular, Präsens, not weak (NON)
  VER:PA2:SFT         past participle
  ...:NEB             subordinate-clause form of a separable verb (mitnahm)
  SUB:DAT:PLU:MAS     noun, dative plural, masculine
"""

import os
import re

from .paths import MORPHY, WIKTIONARY

DEFAULT_PATH = MORPHY
VOWELS = re.compile(r"[aeiouäöüy]+")
GENDER = {"MAS": "der", "FEM": "die", "NEU": "das"}

# Verbs whose one-word Konjunktiv II is in everyday use. For all other verbs
# people say "würde + infinitive" (würde lesen, not läse), so no form is stored.
# Curated from standard grammar descriptions; extend by hand if needed.
KONJ2_IN_USE = {
    "haben": "hätte", "sein": "wäre", "werden": "würde",
    "können": "könnte", "müssen": "müsste", "dürfen": "dürfte", "sollen": "sollte",
    "wollen": "wollte", "mögen": "möchte",
    "kommen": "käme", "gehen": "ginge", "geben": "gäbe", "wissen": "wüsste",
    "lassen": "ließe", "finden": "fände", "bleiben": "bliebe", "halten": "hielte",
    "liegen": "läge", "stehen": "stünde", "tun": "täte", "heißen": "hieße",
    "brauchen": "bräuchte",
}


class Lexicon:
    def __init__(self, path: str = DEFAULT_PATH):
        self.path = path
        self.ok = os.path.exists(path)
        self._cache = {}

    # ── raw access ───────────────────────────────────────────────────────────
    def entries(self, *lemmas):
        """All (form, tags) for each lemma, in one pass over the file."""
        todo = [l for l in lemmas if l not in self._cache]
        if todo and self.ok:
            keys = {l.encode("utf-8"): l for l in todo}
            found = {l: [] for l in todo}
            with open(self.path, "rb") as f:
                for line in f:
                    lem = line.split(b"_", 1)[0]
                    if lem in keys:
                        parts = line.decode("utf-8").rstrip("\n").split("_", 2)
                        if len(parts) == 3:
                            found[keys[lem]].append((parts[1], parts[2]))
            self._cache.update(found)
        return {l: self._cache.get(l, []) for l in lemmas}

    # ── verbs ────────────────────────────────────────────────────────────────
    def verb(self, word, prefix=None, separable=False, hint_past=None, hint_participle=None,
             reflexive_case=None):
        """
        Returns {past_tense, past_participle, present_3sg, verb_class, alternatives,
                 imperative (du-form, only if the stem changes: "nimm mit"), konjunktiv_2 (all forms)}
        in the same format as words.json ("nahm mit", "freute sich", "zog sich an"),
        or None if the verb is not in the lexicon.
        verb_class: regular (weak), irregular (strong), mixed (weak endings, changed stem: dachte).
        hint_past / hint_participle: the forms already stored, used to pick the right
        conjugation when a verb has two by meaning (schaffte / schuf).
        """
        if not self.ok:
            return None
        lemma = re.sub(r"^sich\s+", "", word).strip()
        reflexive = word.startswith("sich ")
        bare_hint = lambda h: (h or "").split("/")[0].replace(" sich", "").replace("ß", "ss").split(" ")[0].strip()
        pfx = (prefix or "").strip("-") if separable else ""
        core = lemma[len(pfx):] if pfx and lemma.startswith(pfx) else lemma

        own, base = self.entries(lemma, core).values() if core != lemma else (self.entries(lemma)[lemma], [])
        prt, prs, pa2 = {}, {}, []

        def collect(F, add_pfx):
            for form, tags in F:
                if not form[:1].islower():
                    continue
                m = re.match(r"VER:3:SIN:(PRT|PRÄ):(SFT|NON)", tags)
                if m:
                    if ":NEB" in tags:                 # mitnahm: only useful to recover the main-clause form
                        if not (pfx and form.startswith(pfx)):
                            continue
                        form = form[len(pfx):]
                    elif add_pfx:
                        pass
                    elif pfx:
                        continue                       # lexicon gives NEB forms for separable verbs
                    (prt if m.group(1) == "PRT" else prs).setdefault(form, set()).add(m.group(2))
                elif tags.startswith("VER:PA2"):
                    pa2.append((pfx + form) if add_pfx else form)

        collect(own, add_pfx=False)
        if pfx and not prt:                            # compound missing from lexicon: use the base verb
            collect(base, add_pfx=True)
        if not prt:
            return None

        def main_clause(head):
            return head + (" sich" if reflexive else "") + ((" " + pfx) if pfx else "")

        # prefer weak forms for a weak verb and vice versa; ß-forms of old spelling last
        def rank(item):
            form, flags = item
            return (bool(hint_past) and form.replace("ß", "ss") != bare_hint(hint_past),
                    ("ß" in form and form.replace("ß", "ss") in prt), form)
        prt_sorted = sorted(prt.items(), key=rank)
        head, flags = prt_sorted[0]
        core_stem = re.sub(r"(e?n)$", "", core)
        if head.endswith("te"):
            # weak ending: regular if the stem is unchanged (lernte), mixed if it changed (kannte, dachte)
            cls = "regular" if head[:-2].rstrip("e") == core_stem.rstrip("e") else "mixed"
        else:
            cls = "irregular"
        p3 = next((f for f, fl in prs.items() if ("SFT" in fl) == (cls == "regular")), None) \
            or next(iter(prs), None)
        ins = (prefix or "").strip("-")
        pa2 = sorted(set(pa2), key=lambda f: (
            bool(hint_participle) and f.replace("ß", "ss") != bare_hint(hint_participle).replace("ß", "ss"),
            (not separable) and bool(ins) and f.startswith(ins + "ge"),   # übersetzt, not übergesetzt
            f.endswith("t") != (cls in ("regular", "mixed")),             # schaffte -> geschafft
            "ß" in f and f.replace("ß", "ss") in pa2, f))
        # du-imperative, only when the stem changes (nimm!, gib!, lies!); fahr! is regular
        src = base if (pfx and base) else own
        imps = sorted({f for f, t in src if t.startswith("VER:IMP:SIN") and f[:1].islower()
                       and not f.endswith("e") and "ß" not in f.replace("ß", "", 0) or
                       (t.startswith("VER:IMP:SIN") and f.endswith("ß") and f[:1].islower())})
        stem_v = VOWELS.findall(core_stem)
        imp = next((f for f in imps if VOWELS.findall(f) != stem_v and not f.endswith("ß")
                    or (VOWELS.findall(f) != stem_v and f.replace("ß", "ss") not in imps)), None)
        imperative = None
        if imp:
            pron = " dir" if reflexive_case == "dat" else " dich"
            imperative = imp + (pron if reflexive else "") + ((" " + pfx) if pfx else "")
        kj2 = sorted({f for f, t in src if re.match(r"VER:3:SIN:KJ2", t) and ":NEB" not in t
                      and f[:1].islower() and not ("ß" in f and f.replace("ß", "ss") in [g for g, _ in src])})
        k2 = KONJ2_IN_USE.get(lemma)
        return {
            "imperative": imperative,
            "konjunktiv_2_common": (k2 + (" sich" if reflexive else "")) if k2 else None,
            "konjunktiv_2": [main_clause(f) for f in kj2],
            "past_tense": main_clause(head),
            "past_participle": pa2[0] if pa2 else None,
            "present_3sg": main_clause(p3) if p3 else None,
            "verb_class": cls,
            "alternatives": [main_clause(f) for f, _ in prt_sorted[1:] if "ß" not in f or f.replace("ß", "ss") not in prt],
        }

    # ── nouns ────────────────────────────────────────────────────────────────
    def noun(self, word):
        """Returns {genders, plurals, forms} or None. Compounds fall back to their last element."""
        if not self.ok:
            return None
        lemma = re.sub(r"^(der|die|das)\s+", "", word).strip()
        F = [(f, t) for f, t in self.entries(lemma)[lemma] if t.startswith("SUB:")]
        head_prefix = ""
        if not F:                                       # Fußboden -> Boden
            for i in range(1, len(lemma) - 2):
                tail = lemma[i].upper() + lemma[i + 1:]
                F = [(f, t) for f, t in self.entries(tail)[tail] if t.startswith("SUB:")]
                if F:
                    head_prefix = lemma[:i]
                    F = [(head_prefix + f[0].lower() + f[1:], t) for f, t in F]
                    break
        if not F:
            return None
        genders = sorted({GENDER[t.split(":")[3]] for f, t in F
                          if len(t.split(":")) > 3 and t.split(":")[3] in GENDER})
        plurals = sorted({f for f, t in F if t.startswith("SUB:NOM:PLU")})
        forms = {}
        for f, t in F:
            p = t.split(":")
            forms.setdefault(f"{p[1]}:{p[2]}", set()).add(f)
        return {"genders": genders, "plurals": plurals,
                "forms": {k: sorted(v) for k, v in forms.items()}}


def changes_stem(word, present_3sg, prefix=None, separable=False):
    """True if er/sie/es changes the stem vowel (nimmt, fährt, weiß)."""
    if not present_3sg:
        return False
    lemma = re.sub(r"^sich\s+", "", word).split(" ")[0]          # "zählen auf" -> zählen
    pfx = (prefix or "").strip("-") if separable else ""
    core = re.sub(r"(e?n)$", "", lemma[len(pfx):] if pfx else lemma)
    form = present_3sg.split(" ")[0]
    return VOWELS.findall(core) != VOWELS.findall(re.sub(r"(e?t|st)$", "", form))




# ── German Wiktionary (kaikki.org extract) ───────────────────────────────────
# private/sources/wiktionary/de-extract.jsonl from https://kaikki.org/dewiktionary/ (CC BY-SA). Used
# only for the German definition of new words; about 15 s per lookup on 3 GB.

WIKT_PATH = WIKTIONARY
_WPOS = {"noun": {"noun"}, "verb": {"verb"}, "adj/adv": {"adj", "adv"},
         "prep/conj": {"prep", "conj", "adv"}}
_STOP = {"to", "a", "an", "the", "of", "be", "something", "someone", "oneself", "sth", "sb",
         "one", "or", "and", "in", "on", "up", "out", "for", "with", "at"}


def _toks(s):
    return {t for t in re.findall(r"[a-z]+", (s or "").lower()) if t not in _STOP and len(t) > 2}


def german_definition(word, word_type, english_meanings, path=WIKT_PATH):
    """Return the German Wiktionary definition whose English translations best match
    `english_meanings` (list of strings, first = main meaning), or None.
    Falls back to the first sense only when the entry has a single sense."""
    import json, subprocess
    if not os.path.exists(path):
        return None
    lemma = re.sub(r"^(der|die|das|sich)\s+", "", word).strip()
    try:
        out = subprocess.run(["grep", "-F", f'"word": "{lemma}", "pos"', path],
                             capture_output=True, text=True, timeout=120).stdout
    except Exception:
        return None
    main = _toks(english_meanings[0] if english_meanings else "")
    every = _toks(" ".join(english_meanings))
    best, n_senses = None, 0
    for line in out.splitlines():
        d = json.loads(line)
        if d.get("word") != lemma or d.get("lang_code") != "de":
            continue
        if _WPOS.get(word_type) and d.get("pos") not in _WPOS[word_type]:
            continue
        tr = {}
        for t in d.get("translations", []):
            if t.get("lang_code") == "en" and t.get("sense_index"):
                for si in re.findall(r"\d+", t["sense_index"]):
                    tr.setdefault(si, set()).update(_toks(t.get("word")))
        for i, s in enumerate(d.get("senses", [])):
            if s.get("form_of") or not s.get("glosses"):
                continue
            n_senses += 1
            si = (re.findall(r"\d+", s.get("sense_index") or "") or [str(i + 1)])[0]
            score = 2 * len(tr.get(si, set()) & main) + len(tr.get(si, set()) & every)
            gloss = re.sub(r"\s+", " ", re.sub(r"\[\d+[a-z]?\]", "", s["glosses"][0])).strip(" ;,")
            if best is None or (score, -i) > best[:2]:
                best = (score, -i, gloss)
    if not best or (best[0] == 0 and n_senses > 1):
        return None
    g = best[2]
    return g.split(";")[0].strip() if len(g) > 90 and ";" in g else g
