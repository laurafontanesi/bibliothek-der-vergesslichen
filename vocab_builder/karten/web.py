"""The cards of the website's study room: web/data/karten.json, and the shared lists as web/js/schema.js.

    python -m vocab_builder karten

Word cards from words.json (word_cards.py), collocation and grammar cards from words.json and
grammar.json (grammar_cards.py). The website draws them in its own layout (web/js/seiten/karte.js), with what else it needs from
words.json.
Only the fields the website uses are written (FIELDS below).

karten.json:
    "typen":   {"Deutsch" | "Kollokation" | "Grammatik": [{"key", "name"}]}
    "eintraege": [{"typ", "id", "karten": [keys], "felder": {non-empty fields}, ...}]
      Deutsch:     "wort" (id in words.json), "niveau", "freq", "neu" (date added), "alt" (English
                   meanings that also count on the Bedeutung card)
                   "partner" (the other word of "Welches Wort passt?"), "konj" (Präsens and
                   Präteritum tables for the backs of the form cards, from private/sources/morphy)
      Kollokation: "wort", "niveau", "freq", "neu"
      Grammatik:   "thema" (topic id in grammar.json), "wort" when the sentence belongs to a word
No date or random value goes into the file, so a build without changes writes the same file.
"""
import html
import io
import json
import os
import random
import re

from .word_cards import CARD_ORDER, EXERCISES, word_fields
from .text import bare, englisch_kurz

from ..paths import WEB


def plain(s):
    """Plain text of a field: tags removed, entities decoded, spaces collapsed (as web/js/pruefen.js text)."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", "", s or ""))).strip()


def alternatives(w):
    """The English meanings of a word as short answers: 'to develop, to evolve' -> develop, evolve."""
    out = []
    for d in w.get("definitions") or []:
        m = d.get("meaning") or ""
        if ":" in m:                                   # "sich entwickeln: to develop" -> the English part
            m = m.split(":", 1)[1]
        if " — " in m:                                 # "jdn./etw. satt haben — to be fed up with" -> the English
            m = m.split(" — ", 1)[1]
        m = re.sub(r"\([^)]*\)", "", m)
        for part in re.split(r"[,;/]", m):
            p = re.sub(r"\s+", " ", part).strip().lower()
            p = re.sub(r"^to ", "", p).rstrip(".!?").strip()   # as the website compares (web/js/pruefen.js)
            if p and p not in out:
                out.append(p)
    return out


PERSONS = [("1", "SIN"), ("2", "SIN"), ("3", "SIN"), ("1", "PLU"), ("2", "PLU"), ("3", "PLU")]


def conjugations(verbs):
    """{word id: {"praes": [6 forms], "praet": [6 forms]}} from the Morphy lexicon (private/sources/morphy), for the
    tables on the backs of the Präsens and Präteritum cards. Each form as in a main clause (nahm auf,
    freue mich); two forms of one person joined with " / ". Empty when the lexicon is missing."""
    from ..deps import LEXICON
    if not LEXICON or not LEXICON.ok or not verbs:
        return {}
    info = {}
    for w in verbs:
        lemma = re.sub(r"^sich\s+", "", w["word"]).strip()
        pfx = (w.get("prefix") or "").strip("-")
        last = (w.get("past_tense") or "").split(" ")[-1]
        if not pfx and w.get("is_separable") and " " in (w.get("past_tense") or "") and lemma.startswith(last):
            pfx = last                                   # sich anmaßen: maßte sich an
        info[w["id"]] = (lemma, pfx, lemma[len(pfx):] if pfx and lemma.startswith(pfx) else lemma)
    found = LEXICON.entries(*sorted({x for l, _p, c in info.values() for x in (l, c)}))
    PRON = {"akk": ["mich", "dich", "sich", "uns", "euch", "sich"], "dat": ["mir", "dir", "sich", "uns", "euch", "sich"]}
    out = {}
    for w in verbs:
        lemma, pfx, core = info[w["id"]]
        # the lexicon marks a separable verb by its subordinate-clause forms (mitnahm), even where
        # words.json does not say so
        if not (w.get("is_separable") or any(":NEB" in tg and f.startswith(pfx) for f, tg in found.get(lemma, []) if pfx)):
            pfx, core = "", lemma
        refl = w["word"].startswith("sich ")
        p3 = (w.get("present_3sg") or "").split(" ")[0]
        p3stem = re.sub(r"e?t$", "", p3) if p3 else ""
        pron = PRON.get(w.get("reflexive") if w.get("reflexive") in PRON else "akk")
        heads = [h.strip().split(" ")[0] for h in (w.get("past_tense") or "").split("/") if h.strip()]
        table = {}
        for tense, key in (("PRÄ", "praes"), ("PRT", "praet")):
            rows = []
            for i, (person, num) in enumerate(PERSONS):
                forms = []
                def add(form):
                    if form and form not in forms:
                        forms.append(form)
                for src, from_base in ((found.get(lemma, []), False), (found.get(core, []), True)):
                    for form, tags in src:
                        tags = tags.replace("VER:MOD:", "VER:").replace("VER:AUX:", "VER:")
                        if not form[:1].islower() or not tags.startswith(f"VER:{person}:{num}:{tense}"):
                            continue
                        if pfx and not from_base:
                            if ":NEB" not in tags or not form.startswith(pfx):
                                continue
                            form = form[len(pfx):]
                        elif ":NEB" in tags:
                            continue
                        if tense == "PRT" and heads and not any(form.startswith(h.rstrip("e")) for h in heads):
                            continue
                        add(form)
                    if forms:
                        break
                # old spellings (läßt) and the short ich-form (meid) only when nothing else is there
                forms = [f for f in forms if not ("ß" in f and f.replace("ß", "ss") in forms)] or forms
                if person == "1" and num == "SIN" and tense == "PRÄ":
                    forms = [f for f in forms if f.endswith("e")] or forms
                if num == "SIN" and person in "23" and tense == "PRÄ" and p3stem:
                    forms = [f for f in forms if f.startswith(p3stem)] or forms      # wächst, not wachst
                tail = (" " + pron[i] if refl else "") + (" " + pfx if pfx else "")
                rows.append(" / ".join(f + tail for f in forms))
            if all(rows):
                table[key] = rows
        if table:
            out[w["id"]] = table
    return out


# The fields the website reads (web/js/seiten/karte.js, ueben.js, warum.js, pruefen.js); the sources
# (Quelle) are shown under the sentence on the back of the card.
FIELDS = {
    "Deutsch": ["Wort", "EnglischFrage", "EnglischKurz", "Stammformen"]
               + [f"{k}_{s}" for k in CARD_ORDER[2:] for s in ("Frage", "Antwort", "Ganz", "GanzEN", "Hinweis", "Quelle")],
    "Kollokation": ["Kollokation", "Englisch", "Hinweis", "Notiz", "Beispiel", "BeispielEN"],
    "Grammatik": ["Thema", "Zelle", "Satz", "SatzEN", "Hinweis", "Antwort", "Ganz", "Regel", "Quelle"],
}


def _clean(dicts):
    """Only the markup the build writes reaches a card (vocab_builder/sanitize.py): no script, no other tags,
    links to https only."""
    from ..sanitize import clean
    for d in dicts:
        for k, v in d.items():
            if isinstance(v, str) and not k.startswith("_"):
                d[k] = clean(v)


def word_rows(db):
    """One row of fields per word (word_cards.word_fields), with the partner of "Welches Wort passt?"."""
    ctx = {"rng": random.Random(42), "by_word": {w["word"]: w for w in db}}
    rows = []
    for w in db:
        r = word_fields(w, ctx)
        r["_id"] = w["id"]
        partners = [x["word"] for x in w.get("related", [])
                    if isinstance(x, dict) and x["kind"] in ("contrast", "antonym")
                    and ctx["by_word"].get(x["word"], {}).get("type") == w.get("type")
                    and bare(x["word"]) != bare(w["word"])]
        r["_partner"] = ctx["by_word"][partners[0]]["id"] if partners else None
        rows.append(r)
    return rows


def build(db=None, web=WEB):
    """Write web/data/karten.json and web/js/schema.js; returns (entries, cards)."""
    from ..deps import require_morphy
    from ..grammar import model as gmodel
    from ..model import load
    from .grammar_cards import collocation_cards, sentence_cards
    require_morphy("The website's cards (conjugation tables, noun forms, sentence checks)")
    db = db if db is not None else load()
    rows = word_rows(db)
    g = gmodel.load()
    nb, nk = sentence_cards(g, db), collocation_cards(db)
    _clean(rows)
    _clean(n[0] for n in nb)
    _clean(n[0] for n in nk)
    return write_web(rows, nk, nb, db, g, web)


def write_web(rows, colls, grams, db, g, web=WEB):
    by_id = {w["id"]: w for w in db}
    labels = {k: label for k, label, *_ in EXERCISES}
    labels.update(Produzieren="Produzieren", Bedeutung="Bedeutung")
    used = {k for r in rows for k in CARD_ORDER[2:] if r.get(f"{k}_Frage")}
    typen = {
        "Deutsch": [{"key": k, "name": labels[k]} for k in CARD_ORDER if k in ("Bedeutung", "Produzieren") or k in used],
        "Kollokation": [{"key": "Kollokation", "name": "Kollokation"}],
        "Grammatik": [{"key": "Grammatik", "name": "Grammatik"}],
    }

    def meta(w):
        return {"niveau": w.get("level"), "freq": (w.get("dwds") or {}).get("freq"), "neu": str(w.get("added") or "")[:10]}

    def felder(typ, f):
        return {c: f[c] for c in FIELDS[typ] if f.get(c)}

    eintraege = []
    konj = conjugations([by_id[r["_id"]] for r in rows if r.get("Praes_Frage") or r.get("Praet_Frage")])
    for r in rows:
        w = by_id[r["_id"]]
        karten = ["Bedeutung", "Produzieren"] + [k for k in CARD_ORDER[2:] if r.get(f"{k}_Frage")]
        n = {"typ": "Deutsch", "id": w["id"], "wort": w["id"], "karten": karten,
             "felder": felder("Deutsch", r), **meta(w), "alt": alternatives(w)}
        if r.get("_partner") and "Kontrast" in karten:
            n["partner"] = r["_partner"]                  # the other word of "Welches Wort passt?"
        if w["id"] in konj:
            n["konj"] = konj[w["id"]]
        eintraege.append(n)
    for f, key, wid in colls:
        eintraege.append({"typ": "Kollokation", "id": key, "wort": wid, "karten": ["Kollokation"],
                        "felder": felder("Kollokation", f), **meta(by_id[wid])})
    # the word a grammar sentence belongs to (a fixed preposition, a connector, the noun of a declension)
    word_of, cell_of = {}, {}
    for t in g.get("topics", []):
        for c in t.get("cells", []):
            for s in c.get("sentences", []):
                word_of[f"{c['id']}|{s['de']}"] = s.get("word_id") or c.get("word_id")
                cell_of[f"{c['id']}|{s['de']}"] = (t["id"], c)
    for f, thema, key, *_ in grams:
        n = {"typ": "Grammatik", "id": key, "thema": thema, "karten": ["Grammatik"], "felder": felder("Grammatik", f)}
        if word_of.get(key) in by_id:
            n["wort"] = word_of[key]
        tid, cell = cell_of.get(key, ("", {}))
        if tid == "konnektoren":
            # for the line under a wrong answer (web/js/seiten/warum.js), as plain text: the connector
            # with its English, and its part of speech with the word order
            w = by_id.get(cell.get("word_id"))
            n["konnektor"] = {"gloss": plain(f"{cell.get('word', '')}: {englisch_kurz(w) if w else ''}"),
                              "wortart": plain((cell.get("regel") or {}).get("wortart", ""))}
        eintraege.append(n)

    os.makedirs(web, exist_ok=True)
    from ..schema import write_js
    write_js(web)                                         # web/js/schema.js, the shared lists
    os.makedirs(os.path.join(web, "data"), exist_ok=True)
    with io.open(os.path.join(web, "data", "karten.json"), "w", encoding="utf-8") as fh:
        json.dump({"typen": typen, "eintraege": eintraege}, fh, ensure_ascii=False, separators=(",", ":"))
    return len(eintraege), sum(len(n["karten"]) for n in eintraege)
