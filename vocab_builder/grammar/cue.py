"""The front of a gap card (grammar cards, and the verb cards):

    Nächste Woche nehme ich ________ Sprachkurs in Zürich teil.
    Präposition + unbestimmter Artikel · 2 Wörter
    Next week I am taking part {in a} language course in Zurich.

- one gap per group of answer words that stand next to each other; words apart in the sentence
  get a gap each (________ du deinen Pass ________?);
- the cue names the kinds of words, in German, and how many;
- the English translation with the part to translate between { }, shown highlighted.

The highlight is found automatically where the English of the gap can be located in the
translation (gap_en.py). A sentence can set its own
with "en_hl" (the English with { }), written by hand where the English says it differently
(Das Essen schmeckt mir -> {I} do not like the food); "en_hl": "" means no highlight.
"""
import re

from . import gap_en

GAP = "________"

PERSONAL = {"ich", "du", "er", "sie", "es", "wir", "ihr", "man", "mich", "dich", "ihn", "uns", "euch",
            "mir", "dir", "ihm", "ihnen", "jemand", "niemand"}
CONTRACTED = {"zum", "zur", "beim", "vom", "im", "am", "ins", "ans", "aufs", "fürs", "durchs", "ums"}
NUMBERS = {"zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn", "zwölf", "hundert"}
EN_PREPS = {"in", "on", "at", "to", "for", "of", "about", "with", "from", "into", "onto", "over", "after",
            "by", "against", "towards", "upon", "under", "through", "around", "without", "like", "as"}

# connectors: which kind of word (the Konnektoren topic)
PREPOSITIONS = {"neben", "laut", "wegen", "aufgrund", "infolge", "trotz", "vor", "entgegen"}


def words(n):
    return f"{n} Wort" if n == 1 else f"{n} Wörter"


ENDINGS = ("", "e", "en", "em", "er", "es")


def det_kind(tok):
    """The German name of a determiner, or None (exact forms only: Meinung is not mein-)."""
    t = tok.lower()
    if t in ("der", "die", "das", "den", "dem", "des"):
        return "bestimmter Artikel"
    if t in ("ein", "eine", "einen", "einem", "einer", "eines"):
        return "unbestimmter Artikel"
    if t in {"kein" + e for e in ENDINGS}:
        return "Negativartikel"
    if t in {p + e for p in ("mein", "dein", "sein", "ihr", "unser", "eur") for e in ENDINGS} | {"euer"}:
        return "Possessivartikel"
    if t in {"dies" + e for e in ENDINGS[1:]}:
        return "Demonstrativartikel"
    if t in {"welch" + e for e in ENDINGS[1:]}:
        return "Frageartikel"
    if t in {p + e for p in ("jed", "all", "manch", "einig", "mehrer", "viel", "wenig", "jen", "beid", "solch")
             for e in ENDINGS[1:]}:
        return "Artikelwort"
    if t in NUMBERS:
        return "Zahlwort"
    return None


# ── gaps ──────────────────────────────────────────────────────────────────────

def answer_spans(tid, s):
    """The character spans of the answer, in order (the preposition counts for Feste Präpositionen)."""
    spans = list(s["blanks"])
    if tid == "prep_fixed" and s.get("prep_span"):
        spans = [s["prep_span"]] + spans
    return sorted(spans)


def groups(de, spans):
    """Spans that stand next to each other (only spaces between) become one group."""
    out = []
    for a, b in sorted(spans):
        if out and de[out[-1][1]:a].strip() == "":
            out[-1][1] = b
        else:
            out.append([a, b])
    return out


def gapped(de, spans):
    """(sentence with gaps, sentence with the answer marked, answer)."""
    satz, ganz, last = "", "", 0
    for a, b in groups(de, spans):
        satz += de[last:a] + GAP
        ganz += de[last:a] + '<span class="hl">' + de[a:b] + "</span>"
        last = b
    answer = " ".join(de[a:b] for a, b in sorted(spans))
    return satz + de[last:], ganz + de[last:], answer


# ── cue ───────────────────────────────────────────────────────────────────────

def phrase_parts(toks):
    """Determiner + adjective(s) + noun, in German: ['Possessivartikel', 'Adjektiv', 'Nomen']."""
    parts = []
    for i, t in enumerate(toks):
        d = det_kind(t) if i == 0 else None
        if d:
            parts.append(d)
        elif t[:1].isupper() and i == len(toks) - 1:
            parts.append("Nomen")
        else:
            parts.append("Adjektiv")
    return parts


def connector_kind(c, s):
    w = c["word"]
    a, b = s["blanks"][0]
    after = s["de"][b:].split()
    nxt = after[0].strip(".,;:!?") if after else ""
    if w in PREPOSITIONS:
        return "Präposition"
    if w in ("während", "seit"):
        follows_phrase = bool(det_kind(nxt)) or nxt[:1].isupper() or nxt[:1].isdigit() or nxt.lower() in CONTRACTED
        return "Präposition" if follows_phrase else "Konjunktion"
    if w == "seitdem":
        follows_subject = nxt.lower() in PERSONAL or bool(det_kind(nxt)) or nxt[:1].isupper()
        return "Konjunktion" if follows_subject else "Adverb"
    return "Konjunktion"


def cue(tid, c, s):
    """'Präposition + unbestimmter Artikel · 2 Wörter'; a sentence can set its own ("cue")."""
    if s.get("cue"):
        return s["cue"].strip("[]")
    spans = answer_spans(tid, s)
    toks = " ".join(s["de"][a:b] for a, b in spans).split()
    n = len(toks)
    if tid == "dekl":
        parts = phrase_parts(toks)
    elif tid == "prep_fixed":
        rest = phrase_parts(toks[1:]) if len(toks) > 1 else []
        parts = ["Präposition"] + rest
    elif tid == "kasus":
        k = c["kind"]
        if k == "pron":
            parts = ["Personalpronomen"]
        elif k == "frage":
            parts = ["Fragewort"]
        elif k == "indef":
            parts = ["Indefinitpronomen"]
        elif k == "prep":
            if toks[0].lower() in CONTRACTED:
                parts = ["Präposition und Artikel in einem Wort"]
            else:
                parts = ["Präposition"] + phrase_parts(toks[1:])
        else:                                   # datv: the dative object's determiner or pronoun
            parts = ["Personalpronomen"] if toks[0].lower() in PERSONAL or toks[0] == "Ihnen" else phrase_parts(toks)
    elif tid == "konnektoren":
        parts = [connector_kind(c, s)]
    else:
        parts = []
    return " + ".join(parts) + " · " + words(n)


# ── highlight ─────────────────────────────────────────────────────────────────

def find_all(phrase, en):
    phrase = re.sub(r"\s*\([^)]*\)", "", phrase or "").strip()
    if not phrase:
        return []
    pat = r"(?<![\w'])" + re.escape(phrase).replace(r"\ ", r"\s+") + r"(?![\w'])"
    return [m.span() for m in re.finditer(pat, en, re.I)]


def mark(en, spans):
    out, last = "", 0
    for a, b in sorted(spans):
        out += en[last:a] + "{" + en[a:b] + "}"
        last = b
    return out + en[last:]


def auto_highlight(tid, c, s, by_id):
    """The English with { } around the part to translate, or None when it cannot be placed safely."""
    en = s.get("en") or ""
    if tid == "prep_fixed":
        art = gap_en.det_en(s["de"][s["blanks"][0][0]:s["blanks"][0][1]], en) or ""
        hits = []
        for a, b in find_all(art, en):
            before = re.search(r"([A-Za-z]+)\s+$", en[:a])
            if before and before.group(1).lower() in EN_PREPS:
                hits.append((before.start(1), b))
        return mark(en, hits) if len(hits) == 1 else None
    target = gap_en.english(tid, c, s, by_id)
    hits = find_all(target, en)
    if len(hits) == 1:
        return mark(en, hits)
    return None


def highlight(tid, c, s, by_id):
    """(English with { }, 'hand' | 'auto' | None)."""
    if "en_hl" in s:
        return s["en_hl"], "hand"
    got = auto_highlight(tid, c, s, by_id)
    return got, ("auto" if got else None)


def html(en_hl):
    """{in a} -> <span class="hl-en">in a</span>"""
    return re.sub(r"\{([^}]*)\}", r'<span class="hl-en">\1</span>', en_hl or "")


# ── the verb cards (exercises in words.json) ────────────────────────

PAST_AUX = {"hatte", "hattest", "hatten", "hattet", "war", "warst", "waren", "wart"}
KONJ_AUX = {"hätte", "hättest", "hätten", "hättet", "wäre", "wärst", "wären", "wärt"}
EN_AUX = r"have|has|had|'ve|'d|'s"


def verb_cue(ex):
    """'Perfekt: Hilfsverb + Partizip II · 2 Wörter', 'Präteritum · 1 Wort' ..."""
    if ex.get("cue"):
        return ex["cue"].strip("[]")
    words_ = [ex["de"][a:b] for a, b in ex["blanks"]]
    n = sum(len(x.split()) for x in words_)
    slot = ex["slot"]
    if slot == "part":
        auxes = {x.lower() for x in words_}
        if auxes & PAST_AUX:
            name = "Plusquamperfekt"
        elif auxes & KONJ_AUX:
            name = "Konjunktiv II der Vergangenheit"
        else:
            name = "Perfekt"
        return f"{name}: Hilfsverb + Partizip II · {words(n)}"
    name = {"praet": "Präteritum", "praes": "Präsens", "refl": "Reflexivpronomen"}[slot]
    return f"{name} · {words(n)}"


def verb_auto_highlight(ex):
    en = ex.get("en") or ""
    if ex["slot"] == "refl":
        return en                                   # English has no word for the pronoun: no highlight
    target = re.sub(r"\s*\([^)]*\)", "", ex.get("verb_en") or "").strip()
    hits = find_all(target, en)
    if len(hits) != 1:
        # a separable particle may stand apart in English too: "took ... along"
        parts = target.split()
        if len(parts) == 2:
            h1, h2 = find_all(parts[0], en), find_all(parts[1], en)
            if len(h1) == 1 and len(h2) == 1 and h1[0][1] < h2[0][0]:
                hits = h1 + h2
            else:
                return None
        else:
            return None
    spans = list(hits)
    if ex["slot"] == "part":
        # the English auxiliary, if the English uses one: "Have you {taken}", "I {have} {forgotten}"
        before = en[:hits[0][0]]
        m = None
        for m in re.finditer(r"(?<![\w'])(" + EN_AUX + r")(?![\w])", before, re.I):
            pass
        if m and len(before[m.end():].split()) <= 3:
            spans.insert(0, m.span())
    return mark(en, spans)


def verb_highlight(ex):
    if "en_hl" in ex:
        return ex["en_hl"], "hand"
    got = verb_auto_highlight(ex)
    return got, ("auto" if got is not None else None)


# ── the collocation cards ────────────────────────────────────────────

GERMAN_PREPS = {"an", "auf", "aus", "bei", "mit", "nach", "von", "zu", "in", "über", "unter", "vor", "hinter",
                "neben", "zwischen", "für", "gegen", "ohne", "um", "durch", "seit", "während", "wegen", "trotz",
                "bis", "ab", "gegenüber", "außer"}
INDEF_PRON = {"jemanden", "jemandem", "jemand", "jemandes", "etwas", "niemanden", "niemandem"}


def collocation_cue(de, morph=None):
    """'unbestimmter Artikel + Nomen + Verb im Infinitiv · 3 Wörter' for 'eine Entscheidung treffen'.
    A contracted form is one word: 'Präposition und Artikel in einem Wort + Nomen + Verb im Infinitiv
    · 3 Wörter' for 'ins Gedächtnis einprägen'."""
    toks = [t.strip(".,;:!?") for t in de.split()]
    toks = [t for t in toks if t]
    parts = []
    for i, t in enumerate(toks):
        low = t.lower()
        tags = [x for _, x in morph.get(t)] if morph else []
        last = i == len(toks) - 1
        if low == "sich":
            parts.append("Reflexivpronomen")
        elif low == "sein" and (last or not toks[i + 1][:1].isupper()):
            parts.append("Verb im Infinitiv")
        elif low == "wie":
            parts.append("wie")
        elif low in CONTRACTED:
            parts.append("Präposition und Artikel in einem Wort")      # ins = in das
        elif low in GERMAN_PREPS and last and i > 0 and morph and not any(
                "INF" in x for _, x in morph.get(toks[i - 1])) and toks[i - 1][:1].islower():
            parts.append("Verbpartikel")             # das Schiff legt ab
        elif low in GERMAN_PREPS and not (low == "zu" and not last and i + 1 < len(toks)
                                          and toks[i + 1][:1].islower() and i + 1 == len(toks) - 1):
            parts.append("Präposition")
        elif low == "zu":
            parts.append("zu")
        elif low in INDEF_PRON:
            parts.append("Indefinitpronomen")
        elif low in ("dass", "ob", "wenn", "weil", "als"):
            parts.append("Konjunktion")
        elif low == "nicht":
            parts.append("nicht")
        elif det_kind(t) and i + 1 < len(toks):
            parts.append(det_kind(t))
        elif t[:1].isupper() and i > 0 or (i == 0 and t[:1].isupper() and not tags):
            parts.append("Nomen")
        elif t[:1].isupper():
            parts.append("Nomen")
        elif any("INF" in x for x in tags) and (last or i == len(toks) - 2):
            parts.append("Verb im Infinitiv")
        elif any(x.startswith("PA2") or ":PA2" in x for x in tags):
            parts.append("Partizip II")
        elif any(x.startswith("ADJ") for x in tags):
            parts.append("Adjektiv")
        elif any(x.startswith("ADV") for x in tags):
            parts.append("Adverb")
        elif any("INF" in x for x in tags):
            parts.append("Verb im Infinitiv")
        elif any(x.startswith("VER") for x in tags):
            parts.append("Verb")
        elif any(x.startswith("PRO") for x in tags):
            parts.append("Pronomen")
        elif last and re.search(r"(en|ern|eln)$", low):
            parts.append("Verb im Infinitiv")       # not in the lexicon: rausbringen
        else:
            parts.append("Wort")
    return " + ".join(parts) + " · " + words(len(toks))
