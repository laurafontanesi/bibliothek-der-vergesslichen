"""Check exercise sentences before they go into words.json or grammar.json.

Used for every gap-fill sentence: the verb exercises of a word (words.json) and the sentences of the
grammar topics (grammar.json), written by hand, taken from the examples or generated. Each sentence
comes with the hidden words in [square brackets]:

    Gestern [nahm] ich den Schirm [mit].

What is checked, per slot:
  praet / praes   the bracketed words are exactly the stored verb form; a separable particle closes its clause;
                  a verb without particle is not followed by a clause-final particle (that would be another verb)
  part            the auxiliary (a form of haben or sein, as the verb takes) and the participle as stored,
                  both bracketed, in the same clause
  refl            mich/dich (accusative) or mir/dir (dative), with ich/du as subject in the same clause
  dekl / dekl_pl  one bracket around determiner (or none) + adjective + this noun; the adjective is a form of
                  the base given in "adj"; the phrase agrees in the requested case and number (Morphy
                  full-form lexicon) and fits a preposition directly before it
  prep            the preposition + article of a verb, noun or adjective with a fixed preposition
  pc              a connector: the word appears once and is the only thing bracketed
  all             length, current spelling, unsuitable content, English present, not a copy of a used sentence

Results are "ok", "check" (could not be verified automatically: a person looks at it) or "error".

The verb exercises (praet, part, praes, refl) are the ones a word gets in words.json; dekl, prep and
pc are the grammar topics. Also here: which verb exercises a word gets (slots_for), finding them in
sentences that already exist (find_in), and the instructions for generating the missing ones
(generation_prompt). Needs private/sources/morphy/dictionary.dump (see README, "Data sources").

"""
import collections
import json
import os
import re

from .paths import MORPHY as DICT_PATH

TOKEN = re.compile(r"[A-Za-zÄÖÜäöüß]+")
OLD_SPELLING = re.compile(r"\b(daß|muß\w*|wuß\w*|gewußt|läßt|paßt|bißchen|Schluß|Fluß|Kuß|Haß|naß|"
                          r"eßt|ißt|mißt|vergißt|Prozeß|Streß|Paß|faßt|küßt|mußt|müßt|letztemal|nächstemal|"
                          r"Photo\w*|(?:heute|gestern|morgen) nacht|um so (?:mehr|weniger|besser|schlimmer))\b")
UNSUITABLE = re.compile(r"(?i)\b(sex\w*|nackt\w*|vergewaltig\w*|selbstmord\w*|umbring\w*|drogen|kokain|"
                        r"ermord\w*|leiche\w*|töten|tötete|nazi\w*|hitler|bombe\w*)\b")
AUX_HABEN = {"habe", "hast", "hat", "haben", "habt", "hatte", "hattest", "hatten", "hattet", "hätte", "hättest",
             "hätten", "hättet", "hab"}
AUX_SEIN = {"bin", "bist", "ist", "sind", "seid", "war", "warst", "waren", "wart", "wäre", "wären", "sein"}
PARTICLES = {"ab", "an", "auf", "aus", "bei", "ein", "fest", "fort", "her", "hin", "los", "mit", "nach",
             "vor", "weg", "zu", "zurück", "zusammen", "um", "durch", "über", "unter", "wieder", "teil",
             "heraus", "herum", "hinaus", "vorbei", "kennen", "statt", "fern", "frei", "hoch", "nieder"}

DER_TYPE = {"der", "die", "das", "dies", "jen", "jed", "welch", "manch", "solch"}
EIN_TYPE = {"ein", "kein", "mein", "dein", "sein", "ihr", "unser", "euer"}
QUANT = {"viel", "wenig", "einig", "mehrer", "zwei", "drei", "vier", "fünf"}

SUBORD = {"dass", "weil", "wenn", "ob", "als", "obwohl", "nachdem", "bevor", "während", "seit", "seitdem",
          "sobald", "damit", "falls", "da", "bis", "indem", "sodass", "solange", "wie", "wo", "warum"}
PREP_DAT = {"mit", "bei", "von", "zu", "aus", "nach", "seit", "gegenüber", "außer"}
PREP_AKK = {"für", "durch", "gegen", "ohne", "um"}
PREP_GEN = {"wegen", "trotz", "während", "aufgrund", "infolge", "statt", "anstelle", "innerhalb",
            "außerhalb", "angesichts", "anhand"}
PREP_TWO_WAY = {"in", "an", "auf", "unter", "über", "vor", "hinter", "neben", "zwischen"}


def toks(s):
    return TOKEN.findall(s)


def bare(word):
    return re.sub(r"^(der|die|das|der/die|sich)\s+", "", word).strip()


# ── bracket parsing ───────────────────────────────────────────────────────────

def parse_bracketed(text):
    """'Gestern [nahm] ich ihn [mit].' -> ('Gestern nahm ich ihn mit.', [[8,12],[22,25]], ['nahm','mit'])."""
    plain, spans, marked = "", [], []
    pos = 0
    for m in re.finditer(r"\[([^\[\]]+)\]", text):
        plain += text[pos:m.start()]
        a = len(plain)
        plain += m.group(1)
        spans.append([a, len(plain)]); marked.append(m.group(1))
        pos = m.end()
    plain += text[pos:]
    return plain, spans, marked


def token_index_at(plain, start):
    for k, m in enumerate(TOKEN.finditer(plain)):
        if m.start() == start:
            return k
    return None


def clause_of_index(plain, k):
    """Token indexes of the clause (between punctuation) containing token k."""
    pos = [m.start() for m in TOKEN.finditer(plain)]
    for seg in re.finditer(r'[^,.;:!?„“"–—]+', plain):
        ks = [i for i, p in enumerate(pos) if seg.start() <= p < seg.end()]
        if k in ks:
            return ks
    return []


# ── morphology ────────────────────────────────────────────────────────────────

class Morph:
    """Full-form lookup in the Morphy/LanguageTool dump: {form: [(lemma, tag)]}, one file pass per batch."""

    def __init__(self, path=DICT_PATH):
        self.path = path
        self.cache = {}

    def load(self, forms):
        need = {f for f in forms if f not in self.cache}
        need |= {f[:1].lower() + f[1:] for f in need}     # sentence-initial capitals
        need = {f for f in need if f not in self.cache}
        if not need:
            return
        found = collections.defaultdict(list)
        keys = {f.encode("utf-8") for f in need}
        with open(self.path, "rb") as fh:
            for line in fh:
                p = line.rstrip(b"\n").split(b"_", 2)
                if len(p) == 3 and p[1] in keys:
                    found[p[1].decode("utf-8")].append((p[0].decode("utf-8"), p[2].decode("utf-8")))
        for f in need:
            self.cache[f] = found.get(f, [])

    def get(self, form):
        r = list(self.cache.get(form, []))
        if form[:1].isupper():                              # sentence start: Sein/sein, Ihre/ihre
            r += self.cache.get(form[:1].lower() + form[1:], [])
        return r


def with_suffixes(forms):
    """Forms plus the endings of capitalised words, so compounds missing from the lexicon (Spielfilm)
    can be looked up through their last element (Film)."""
    out = set(forms)
    for f in forms:
        if f[:1].isupper():
            out |= {f[k:].capitalize() for k in range(1, len(f) - 2)}
    return out


_DMN = {("DAT", "SIN", "MAS"), ("DAT", "SIN", "NEU")}
CONTRACTION_PREP = {"zum": "zu", "zur": "zu", "im": "in", "am": "an", "vom": "von", "beim": "bei",
                    "ins": "in", "ans": "an", "aufs": "auf"}
CONTRACTIONS = {"zum": _DMN, "im": _DMN, "am": _DMN, "vom": _DMN, "beim": _DMN,
                "zur": {("DAT", "SIN", "FEM")},
                "ins": {("AKK", "SIN", "NEU")}, "ans": {("AKK", "SIN", "NEU")}, "aufs": {("AKK", "SIN", "NEU")}}


def det_readings(morph, det):
    """{(case, num, gen)} and declension type for a determiner token."""
    if det.lower() in CONTRACTIONS:                         # zur = zu der, ins = in das
        return set(CONTRACTIONS[det.lower()]), "DEF"
    out, kind = set(), None
    for lemma, tag in morph.get(det):
        t = tag.split(":")
        if t[0] == "ART" or (t[0] == "PRO" and t[1] in ("POS", "DEM", "IND", "INR", "RIN") and "STV" not in t):
            if len(t) >= 5:
                out.add((t[2], t[3], t[4]))
                lem = lemma.lower()
                kind = "DEF" if (lem in DER_TYPE or t[1] == "DEF") else ("IND" if lem in EIN_TYPE else kind)
    had_pro = bool(out)
    for lemma, tag in morph.get(det):                   # viele, einige, zwei...
        t = tag.split(":")
        if t[0] in ("ADJ", "ZAL") and (lemma.lower() in QUANT or lemma.lower() == "solch"):
            # with pronoun readings as well (einigen: DAT PLU), add only the strong singular ones
            # (einigen Trost, viel Geld) so they are not lost
            if had_pro and not tag.endswith(":SOL"):
                continue
            if len(t) >= 4 and t[1] in ("NOM", "AKK", "DAT", "GEN"):
                out.add((t[1], t[2], t[3])); kind = kind or "SOL"
        if det.lower() in QUANT:
            kind = "SOL"
    return out, kind


# adjective endings by declension (SOL strong, DEF weak after der-words, IND mixed after ein-words)
CASES, GENS = ("NOM", "AKK", "DAT", "GEN"), ("MAS", "FEM", "NEU")
ENDING = {
    "SOL": {"NOM": ("er", "e", "es", "e"), "AKK": ("en", "e", "es", "e"),
            "DAT": ("em", "er", "em", "en"), "GEN": ("en", "er", "en", "er")},
    "DEF": {"NOM": ("e", "e", "e", "en"), "AKK": ("en", "e", "e", "en"),
            "DAT": ("en", "en", "en", "en"), "GEN": ("en", "en", "en", "en")},
    "IND": {"NOM": ("er", "e", "es", "en"), "AKK": ("en", "e", "es", "en"),
            "DAT": ("en", "en", "en", "en"), "GEN": ("en", "en", "en", "en")},
}


def adj_stems(word):
    """Stems an attributive form can be built on: sensibel -> sensibl, teuer -> teur, nächste -> nächst."""
    w = word.lower()
    out = {w}
    if w.endswith("e"):
        out.add(w[:-1])
    if re.search(r"([^aeiouäöü]|eu|au)e[lr]$", w):
        out.add(w[:-2] + w[-1])
    if w.endswith("ch") and w[:-2].endswith("o"):
        out.add(w[:-2] + "h")                            # hoch -> hoh
    return out


def adj_ending(token, word=None):
    """The inflection ending of an attributive adjective, or None. With `word`, the stem must be that word."""
    t = token.lower()
    for e in ("en", "em", "er", "es", "e"):
        if t.endswith(e):
            stem = t[:-len(e)]
            if word is None:
                if len(stem) >= 3:
                    return e
            elif stem in adj_stems(word):
                return e
    return None


def adj_readings(morph, adj, decl, word=None):
    """{(case, num, gen)} an attributive adjective can stand for after a determiner of type `decl`."""
    e = adj_ending(adj, word)
    if e is None:
        return set()
    out = set()
    for d in ([decl] if decl else ENDING):
        for c in CASES:
            row = ENDING[d][c]
            for gi, g in enumerate(GENS):
                if row[gi] == e:
                    out.add((c, "SIN", g))
            if row[3] == e:
                out |= {(c, "PLU", g) for g in GENS}
    return out


def noun_readings(morph, noun, lemma=None, suffixes=True):
    """{(case, num, gen)} for a noun form; compounds missing from the lexicon go through their last element."""
    for k in range(0, max(1, len(noun) - 2) if suffixes else 1):
        form = noun if k == 0 else noun[k:].capitalize()
        out = set()
        for lem, tag in morph.get(form):
            t = tag.split(":")
            if t[0] == "SUB" and len(t) >= 4 and t[1] in CASES and \
                    (lemma is None or lemma.lower().endswith(lem.lower())):
                out.add((t[1], t[2], t[3]))
        if out:
            return out
    return set()


def entry_noun_readings(entry, form):
    """Fallback when the lexicon does not know the noun (Entscheidungsfindung) or lists only its singular
    (Abgas for die Abgase): build the readings from the article and plural stored in words.json."""
    m = re.match(r"(der|die|das)\s+(.+)", entry.get("word", ""))
    if not m:
        return set()
    gen = {"der": "MAS", "die": "FEM", "das": "NEU"}[m.group(1)]
    sing = m.group(2).strip()
    pl = bare(entry.get("plural") or "") or None
    if entry.get("plural") and entry["plural"].strip() == entry["word"].strip():
        sing = None                                       # plural-only noun (die Fallzahlen)
    out = set()
    if sing and form == sing:
        out |= {(c, "SIN", gen) for c in ("NOM", "AKK", "DAT")} | ({("GEN", "SIN", gen)} if gen == "FEM" else set())
    if sing and gen != "FEM" and form in (sing + "s", sing + "es"):
        out.add(("GEN", "SIN", gen))
    if pl and form == pl:
        out |= {(c, "PLU", gen) for c in ("NOM", "AKK", "GEN")} | ({("DAT", "PLU", gen)} if pl[-1] in "ns" else set())
    if pl and pl[-1] not in "ns" and form == pl + "n":
        out.add(("DAT", "PLU", gen))
    return out


def np_agreement(morph, det, adjs, noun, noun_lemma=None, noun_reads=None):
    """Readings shared by determiner, adjectives and noun; empty = they do not agree."""
    def norm(rs):                                        # plural: gender plays no role (Eltern = NOG)
        return {(c, n, "*" if n == "PLU" else g) for c, n, g in rs}
    d, kind = det_readings(morph, det) if det else (set(), "SOL")
    r = norm(noun_reads if noun_reads is not None else noun_readings(morph, noun, noun_lemma))
    if det:
        r &= norm(d)
    for a in adjs:
        r &= norm(adj_readings(morph, a, kind))
    return r, kind


def governing_cases(tokens, i):
    """Cases a preposition directly before the noun phrase at token i allows (None: no preposition).
    Two-way prepositions (in, an, auf…) allow dative or accusative."""
    if i == 0:
        return None
    p = tokens[i - 1].lower()
    # not a preposition here: "um … zu" + infinitive (um dem Verkehr auszuweichen), and the second
    # part of von … aus / an / her (von Natur aus ein großzügiger Mensch)
    if p == "um" and any(t.lower() == "zu" or re.match(r"^[a-zäöü]+zu[a-zäöü]+en$", t) for t in tokens[i:]):
        return None
    if p in ("aus", "an", "her", "auf") and "von" in [t.lower() for t in tokens[max(0, i - 4):i - 1]]:
        return None
    for preps, cases in ((PREP_DAT, {"DAT"}), (PREP_AKK, {"AKK"}), (PREP_GEN, {"GEN"}),
                         (PREP_TWO_WAY, {"DAT", "AKK"})):
        if p in preps:
            return cases
    return None


# ── Perfekt and Deklination helpers ──────────────────────────────────────────

def aux_forms(entry):
    """Forms of the verb's auxiliary that a Perfekt card accepts: the one in words.json, as in German
    German (hat gestanden; the Swiss "ist gestanden" is mentioned in the word's note only)."""
    return AUX_SEIN if (entry.get("auxiliary") or "haben").lower().startswith("sein") else AUX_HABEN


# adjectives that never take an ending: lila, rosa, prima, and city/country adjectives in -er
INDECLINABLE = {"lila", "rosa", "prima", "orange", "beige", "super"}


def indeclinable(tok):
    return tok.lower() in INDECLINABLE or (tok[:1].isupper() and tok.endswith("er"))


def plural_kind(entry):
    """'none', 'only' (plural-only noun), 'regular' (predictable from gender and ending) or 'irregular'."""
    word, pl = entry.get("word", "").strip(), (entry.get("plural") or "").strip()
    if not pl or pl in ("-", "—"):
        return "none"
    if pl == word:
        return "only"
    m = re.match(r"(der|die|das)\s+(.+)", word)
    s, p = (m.group(2) if m else word), bare(pl)
    gen = m.group(1) if m else ""
    if (gen == "die" and (p in (s + "n", s + "en") or (s.endswith("in") and p == s + "nen"))) \
            or (s.endswith("nis") and p == s + "se") \
            or (gen in ("der", "das") and p == s + "e") \
            or (gen in ("der", "das") and re.search(r"(er|el|en|chen|lein)$", s) and p == s) \
            or (gen == "der" and s.endswith("e") and p == s + "n"):
        return "regular"
    return "irregular"


NUMBERS = {"zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn", "zwölf", "hundert"}


def check_dekl(entry, slot, form, adj, plain, ts, spans, marked, morph, warnings):
    """Determiner (or none) + adjective(s) + this noun, in the requested case and number."""
    problems = []
    if not spans or len(spans) != 1:
        return problems
    case, num = form.split(":")
    if (slot == "dekl_pl") != (num == "PLU"):
        problems.append(f"{slot} needs the {'plural' if slot == 'dekl_pl' else 'singular'}")
    k0 = token_index_at(plain, spans[0][0])
    pt = toks(marked[0])
    if pt[0].lower() in CONTRACTIONS:
        return problems + [f"«{pt[0]}» contains the preposition: write it out or leave the preposition outside"]
    noun = pt[-1]
    if not noun[:1].isupper():
        return problems + [f"«{noun}»: the phrase must end with the noun"]
    if pt[0].lower() in NUMBERS:                           # zwei volle Krüge: like no determiner
        det, middle = None, pt[1:-1]
    else:
        det = pt[0] if det_readings(morph, pt[0])[0] and not adj_ending_of_any(pt[0], adj) else None
        middle = pt[1:-1] if det else pt[:-1]
    if not middle:
        return problems + ["no adjective in the phrase"]
    bases = [b.strip() for b in adj.split(",") if b.strip()]
    declined = []
    for t in middle:
        if indeclinable(t) and any(t.lower() == b.lower() for b in bases):
            continue
        if bases and not any(adj_ending(t, b) for b in bases):
            problems.append(f"«{t}» is not a form of {' / '.join(bases) or 'the adjective'}")
        elif not bases and not adj_ending(t):
            problems.append(f"«{t}» is not an inflected adjective")
        declined.append(t)
    if not bases:
        problems.append("the adjective's base form is missing (\"adj\")")
    lemma = bare(entry["word"])
    reads = noun_readings(morph, noun, lemma, suffixes=False) or entry_noun_readings(entry, noun) \
        or noun_readings(morph, noun, lemma)
    if lemma.endswith("e") and noun != lemma and adj_ending(noun.lower(), lemma[:-1].lower()) \
            and is_adjective(morph, lemma[:-1].lower()):
        # adjective used as a noun (der Fremde, ein Fremder): it declines like the adjective
        gens = {"der": {"MAS"}, "die": {"FEM"}, "das": {"NEU"}}.get(entry["word"].split()[0], {"MAS", "FEM"})
        reads = {(c, n, g) for c in CASES for n in ("SIN", "PLU") for g in gens}
        declined.append(noun)
    if not reads:
        return problems + [f"«{noun}» is not a form of «{lemma}»"]
    agree, _ = np_agreement(morph, det, declined, noun, lemma, reads)
    fits = {(c, n) for c, n, _ in agree}
    if not agree:
        problems.append(f"«{marked[0]}» does not agree")
    elif (case, num) not in fits:
        problems.append(f"asked for {case} {num}, the phrase can only be "
                        + ", ".join(f"{c} {n}" for c, n in sorted(fits)))
    else:
        gs = governing_cases(ts, k0)
        if gs and case not in gs:
            problems.append(f"«{ts[k0 - 1]}» requires {'/'.join(sorted(gs))}")
        elif len({c for c, n in fits if n == num and (not gs or c in gs)}) > 1:
            warnings.append("case depends on the verb: check by eye")
    return problems


def is_adjective(morph, form):
    morph.load({form})
    return any(t.startswith("ADJ") for _, t in morph.get(form))


def adj_ending_of_any(tok, adj):
    """True when `tok` is a form of one of the adjectives in `adj` (so it is not the determiner)."""
    return any(adj_ending(tok, b.strip()) for b in adj.split(",") if b.strip())


# ── the check ─────────────────────────────────────────────────────────────────

def verb_parts(form):
    """'nahm sich mit' -> ['nahm', 'mit'];  'sandte / sendete' -> alternatives handled by the caller."""
    return [p for p in form.split() if p != "sich"]


def check(entry, slot, form, answer, morph, used=(), min_words=5):
    """Returns dict(status, problems, de, en, blanks). `form` as in the inventory ('nahm mit', 'DAT:PLU'...)."""
    problems, warnings = [], []
    if "skip" in answer:
        return dict(status="skip", problems=[answer["skip"]], de=None, en=None, blanks=[])
    plain, spans, marked = parse_bracketed(answer.get("de", ""))
    en = (answer.get("en") or "").strip()
    ts = toks(plain)
    word = entry["word"]

    # general
    if not spans:
        problems.append("nothing in brackets")
    if not en:
        problems.append("English translation missing")
    if "[" in en or "]" in en:
        problems.append("brackets in the English")
    if not min_words <= len(ts) <= 16:
        problems.append(f"{len(ts)} words")
    elif len(ts) > 14:
        warnings.append(f"{len(ts)} words (long)")
    if OLD_SPELLING.search(plain):
        problems.append("old spelling")
    bad = UNSUITABLE.search(plain)
    if bad and not bad.group(0).lower().startswith(bare(word).lower()[:4]):   # the word itself (töten) is fine
        problems.append("unsuitable content")
    if plain.strip() in {u.strip() for u in used}:
        problems.append("same as a sentence already used")
    idx = [token_index_at(plain, a) for a, _ in spans]
    if slot.startswith("dekl"):                          # one bracket around the whole noun phrase
        if len(spans) != 1 or idx[0] is None or not re.fullmatch(r"[A-Za-zÄÖÜäöüß]+( [A-Za-zÄÖÜäöüß]+)+",
                                                                 marked[0]):
            problems.append("mark the whole phrase (determiner, adjective, noun) with one pair of brackets")
    elif any(i is None for i in idx) or any(not re.fullmatch(TOKEN.pattern, m) for m in marked):
        problems.append("a bracket does not hold exactly one word")
    if problems:
        return dict(status="error", problems=problems + warnings, de=plain, en=en, blanks=spans)

    if slot in ("praet", "praes"):
        alts = [verb_parts(a.strip()) for a in form.split("/")] if "/" in form else [verb_parts(form)]
        sep = entry.get("is_separable")
        ok_alt = None
        joined = False
        for parts in alts:
            want = parts if (sep and len(parts) > 1) else parts[:1]
            if [m.lower() for m in marked] == [p.lower() for p in want]:
                ok_alt = parts
            elif sep and len(parts) > 1 and [m.lower() for m in marked] == [(parts[-1] + parts[0]).lower()]:
                ok_alt, joined = parts, True                  # ..., als ich ihn [kennenlernte]
        if ok_alt is not None and joined:
            clause = clause_of_index(plain, idx[0])
            if not clause or clause[-1] != idx[0]:
                problems.append(f"«{marked[0]}» is the joined form: it must close a subordinate clause")
        elif ok_alt is None:
            problems.append(f"brackets {marked} but the form is «{form}»")
        else:
            head_k = idx[0]
            clause = clause_of_index(plain, head_k)
            last = clause[-1] if clause else None
            if sep and len(ok_alt) > 1:
                c0 = ts[clause[0]].lower() if clause else ""
                nxt = ts[clause[0] + 1] if clause and clause[0] + 1 < len(ts) else ""
                as_prep = c0 in {"während", "seit", "bis", "als", "wie"} and \
                    (det_readings(morph, nxt)[0] or (nxt[:1].isupper() and nxt not in {"Sie", "Ihr"}))
                if c0 in SUBORD and not as_prep:
                    problems.append(f"subordinate clause («{ts[clause[0]]}»): the verb would be joined "
                                    f"(«{ok_alt[-1]}{ok_alt[0]}»), not split")
                elif idx[-1] != last:
                    problems.append("the separable particle does not close the clause")
            elif last is not None and last != head_k and ts[last].lower() in PARTICLES \
                    and ts[last].lower() not in {p.lower() for p in ok_alt}:
                warnings.append(f"clause ends with «{ts[last]}»: maybe another verb")
            if sum(1 for t in ts if t.lower() == ok_alt[0].lower()) != 1:
                problems.append("the verb form appears more than once")
            k = idx[0]
            nxt_cap = k + 1 < len(ts) and ts[k + 1][:1].isupper() and ts[k + 1] not in {"Sie", "Ihnen", "Ihr", "Ich"}
            if k > 0 and det_readings(morph, ts[k - 1])[0] and nxt_cap:
                problems.append(f"«{ts[k - 1]} {ts[k]} {ts[k + 1]}»: an adjective here, not the verb")
            elif k == 0 and nxt_cap and not plain.rstrip().endswith("?"):
                problems.append(f"«{ts[0]} {ts[1]}» at the start: an adjective, not the verb")

    elif slot == "part":
        # the auxiliary and the participle are both hidden: [ist] … [gereist], or … gereist [ist]
        low = [m.lower() for m in marked]
        pk = [k for k, m in enumerate(low) if m == form.lower()]
        if len(marked) != 2 or len(pk) != 1:
            problems.append(f"brackets {marked}: expected the auxiliary and the participle «{form}», "
                            f"e.g. [hat] … [{form}]")
        else:
            a = low[1 - pk[0]]
            if a not in aux_forms(entry):
                problems.append(f"«{marked[1 - pk[0]]}» is not a form of "
                                f"«{entry.get('auxiliary') or 'haben'}» (Perfekt or Plusquamperfekt)")
            elif clause_of_index(plain, idx[0]) != clause_of_index(plain, idx[1]):
                problems.append("the auxiliary and the participle are not in the same clause")
            if sum(1 for t in ts if t.lower() == form.lower()) != 1:
                problems.append("the participle appears more than once")

    elif slot == "refl":
        allowed = {"mir": "ich", "dir": "du"} if entry.get("reflexive") == "dat" else {"mich": "ich", "dich": "du"}
        if len(marked) != 1 or marked[0] not in allowed:
            problems.append(f"brackets {marked}, expected one of {sorted(allowed)}")
        else:
            clause = clause_of_index(plain, idx[0])
            if allowed[marked[0]] not in {ts[k].lower() for k in clause}:
                problems.append(f"«{marked[0]}» without «{allowed[marked[0]]}» as subject in the same clause")

    elif slot.startswith("dekl"):
        problems += check_dekl(entry, slot, form, answer.get("adj") or "", plain, ts, spans, marked, morph,
                               warnings)

    elif slot.startswith("prep"):
        prep, case = [x.strip() for x in form.split("+")]
        low = [m.lower() for m in marked]
        k = None
        if len(marked) == 1 and low[0] in CONTRACTIONS and CONTRACTION_PREP[low[0]] == prep:
            dets, k = CONTRACTIONS[low[0]], idx[0]           # [am] Türgriff
        elif len(marked) == 2 and low[0] == prep and idx[1] == idx[0] + 1:
            dets, k = det_readings(morph, ts[idx[1]])[0], idx[1]
            if not dets:
                problems.append(f"«{marked[1]}» is not an article or determiner")
        else:
            problems.append(f"brackets {marked}: expected the preposition «{prep}» and its article, "
                            f"e.g. [{prep}] [den], or a contraction like [am]")
        if k is not None and not problems:
            n = k + 1
            while n < len(ts) and ts[n][:1].islower() and adj_ending(ts[n]):
                n += 1
            noun = ts[n] if n < len(ts) and ts[n][:1].isupper() else None
            reads = noun_readings(morph, noun) if noun else set()
            if noun and reads:
                if len(marked) == 1:                       # contraction: its article is der/das (weak adjectives)
                    norm = lambda rs: {(c, x, "*" if x == "PLU" else g) for c, x, g in rs}
                    agree = norm(reads) & norm(dets)
                    for a in ts[k + 1:n]:
                        agree &= norm(adj_readings(morph, a, "DEF"))
                else:
                    agree, _ = np_agreement(morph, ts[k], ts[k + 1:n], noun, noun_reads=reads)
                cases = {c for c, _, _ in agree}
            else:
                cases = {c for c, _, _ in dets}
                warnings.append("noun not recognised: case checked on the article only")
            if case not in cases:
                problems.append(f"«{prep}» takes the {CASE_NAME.get(case, case).lower()} here, "
                                f"but the phrase is {'/'.join(sorted(cases)) or 'not readable'}")
            elif len(cases) > 1:
                warnings.append("the article fits more than one case: check by eye")
            if sum(1 for t in ts if t.lower() == prep) > 1:
                warnings.append(f"«{prep}» appears twice")

    elif slot.startswith("pc"):
        if [m.lower() for m in marked] != [word.lower()]:
            problems.append(f"brackets {marked}, expected «{word}»")
        elif sum(1 for t in ts if t.lower() == word.lower()) != 1:
            problems.append(f"«{word}» appears more than once")


    status = "error" if problems else ("check" if warnings else "ok")
    return dict(status=status, problems=problems + warnings, de=plain, en=en, blanks=spans)


# ── which exercises a word gets ───────────────────────────────────────────────

CASE_NAME = {"AKK": "accusative", "DAT": "dative", "GEN": "genitive", "NOM": "nominative"}


PREP_OBJ = re.compile(r"^\s*(an|auf|aus|bei|für|gegen|in|mit|nach|über|um|unter|von|vor|zu|zwischen)\s*\+\s*(AKK|DAT)\b", re.I)


def verb_preps(entry):
    """Fixed prepositions of a verb from its `preposition` field: 'auf + AKK / über + AKK' ->
    [('auf', 'AKK'), ('über', 'AKK')]. A bare case ('DAT') is not a preposition and gives nothing."""
    out = []
    for part in re.split(r"\s*/\s*|\s*,\s*|\s*;\s*", entry.get("preposition") or ""):
        m = PREP_OBJ.match(part)
        if m:
            out.append((m.group(1).lower(), m.group(2).upper()))
    return out


def has_root_in(entry, roots):
    """A family member (vornehmen, bekommen) whose root verb (nehmen, kommen) is also in the dictionary."""
    fam = re.sub(r"^sich\s+", "", (entry.get("family_root") or "").strip())
    word = re.sub(r"^sich\s+", "", entry.get("word", "").strip())
    return bool(roots) and fam and fam != word and (fam in roots or "sich " + fam in roots)


def slots_for(entry, stem_changes=None, roots=None):
    """[{slot, label, form}] for one verb (other words get none). `stem_changes(entry)` says whether the present tense changes
    the stem (lexicon.changes_stem); without it, the Präsens slot is left out. `roots` is the set of
    words in the dictionary: a verb whose root verb is among them keeps only the Perfekt card, since
    its Präteritum and Präsens repeat the root's.

    Only what cannot be predicted is practised: Präteritum for irregular and mixed verbs (nahm,
    dachte), Perfekt (auxiliary + participle) for those and for verbs with «sein» (ist gereist);
    regular verbs with «haben» (machte, hat gemacht) get neither. Stem-changing verbs get Präsens,
    reflexive verbs the reflexive pronoun."""
    out = []
    if entry.get("type") == "verb":
        derived = has_root_in(entry, roots)
        irregular = entry.get("verb_class") != "regular"
        with_sein = (entry.get("auxiliary") or "").lower().startswith("sein")
        if entry.get("past_tense") and not derived and irregular:
            out.append(dict(slot="praet", label="Präteritum", form=entry["past_tense"]))
        pa = (entry.get("past_participle") or "").split("/")[0].strip()
        if pa and (irregular or with_sein):
            out.append(dict(slot="part", label="Perfekt", form=pa))
        if entry.get("present_3sg") and stem_changes and stem_changes(entry) and not derived:
            out.append(dict(slot="praes", label="Präsens, er/sie/es", form=entry["present_3sg"]))
        r = entry.get("reflexive")
        if r in ("akk", "dat"):
            out.append(dict(slot="refl", label=f"Reflexivpronomen ({'Dat.' if r == 'dat' else 'Akk.'})",
                            form="mir/dir" if r == "dat" else "mich/dich"))
    return out


# ── finding exercises in sentences you already have ──────────────────────────

def bracket(plain, picks):
    """picks: token indexes -> the sentence with those tokens in [brackets]."""
    pos = [(m.start(), m.end()) for m in TOKEN.finditer(plain)]
    out, last = "", 0
    for k in sorted(picks):
        a, b = pos[k]
        out += plain[last:a] + "[" + plain[a:b] + "]"; last = b
    return out + plain[last:]


def find_in(entry, spec, plain, en, morph, used=()):
    """Can this existing sentence serve the exercise `spec`? Returns a checked exercise or None."""
    ts = toks(plain)
    slot, form = spec["slot"], spec["form"]
    picks = None
    if slot in ("praet", "praes"):
        alts = [verb_parts(a.strip()) for a in form.split("/")]
        for parts in alts:
            ks = [k for k, t in enumerate(ts) if t.lower() == parts[0].lower()]
            if len(ks) != 1:
                continue
            picks = ks
            if entry.get("is_separable") and len(parts) > 1:
                clause = clause_of_index(plain, ks[0])
                if not clause or ts[clause[-1]] != parts[-1]:
                    picks = None; continue
                picks = [ks[0], clause[-1]]
            break
    elif slot == "part":
        ks = [k for k, t in enumerate(ts) if t.lower() == form.lower()]
        if len(ks) == 1:
            clause = clause_of_index(plain, ks[0])
            aux = [k for k in clause if ts[k].lower() in aux_forms(entry)]
            picks = sorted([aux[-1] if aux[-1] < ks[0] else aux[0], ks[0]]) if aux else None
    elif slot == "refl":
        prons = ("mir", "dir") if form == "mir/dir" else ("mich", "dich")
        ks = [k for k, t in enumerate(ts) if t in prons]
        picks = ks if len(ks) == 1 else None
    if not picks:
        return None
    r = check(entry, slot, form, {"de": bracket(plain, picks), "en": en or "-"}, morph, used, min_words=3)
    if r["status"] == "ok":
        r["form"] = form
        return r
    return None


# ── asking the model for the missing ones ────────────────────────────────────

def task_text(entry, spec):
    """The instruction for one missing exercise."""
    slot, form = spec["slot"], spec["form"]
    if slot in ("praet", "praes"):
        what = ("Präteritum, exactly the form «{f}» (ich or er/sie/es)" if slot == "praet"
                else "Präsens, 3rd person singular, exactly «{f}»")
        if " / " in form:
            alts = [a.strip() for a in form.split("/")]
            return what.format(f=alts[0]) + f" (or «{alts[1]}»). Mark the verb form, e.g. [{alts[0]}]."
        parts = verb_parts(form)
        note = " The verb is reflexive: use the pronoun that fits the subject (mich, dich, sich...), unmarked." \
            if "sich" in form.split() else ""
        if len(parts) > 1 and entry.get("is_separable"):
            mark = " and ".join(f"[{p}]" for p in parts)
            return (what.format(f=" ... ".join(parts)) + ". Separable verb: the particle goes to the end of the "
                    f"main clause, never split it in a subordinate clause.{note} Mark {mark}.")
        if len(parts) > 1:
            return (what.format(f=parts[0]) + f", used with the preposition «{' '.join(parts[1:])}».{note} "
                    f"Mark only [{parts[0]}].")
        return what.format(f=parts[0]) + f".{note} Mark only [{parts[0]}]."
    if slot == "part":
        aux = entry.get("auxiliary") or "haben"
        return (f"Perfekt or Plusquamperfekt with «{aux}», participle «{form}» (active voice, not passive). "
                f"Mark the form of {aux} and the participle, e.g. [{'ist' if aux == 'sein' else 'hat'}] ... [{form}].")
    if slot == "refl":
        case = "dative (mir/dir)" if form == "mir/dir" else "accusative (mich/dich)"
        return (f"Reflexive verb, pronoun in the {case}. Use ich or du as subject so the pronoun is not «sich». "
                f"Mark only the reflexive pronoun, e.g. [mich].")
    raise ValueError(slot)


RULES = """Rules for every sentence:
1. One sentence, 6 to 14 words, natural standard German as a teacher would write it (use ß where standard German does).
2. Use the word in the meaning given; if it has several, use the first unless the task says otherwise.
3. The target form appears exactly once, exactly as the task names it.
4. Mark with square brackets only what the task says to mark, whole words only: Gestern [nahm] ich den Schirm [mit].
5. The context makes the answer unambiguous.
6. Everyday, concrete situations (work, home, travel, friends, health, weather, studying). No famous people,
   no violence, sex, drugs or politics. Vary subjects and situations.
7. Do not copy the sentences listed as already used.
8. Natural English translation, no brackets.
9. If a task cannot be done naturally, answer {"id": ..., "skip": "short reason"} instead."""


def generation_prompt(entry, specs, used, feedback=None):
    meanings = " / ".join(d["meaning"] for d in entry.get("definitions", []) if d.get("meaning")) or "(see word)"
    lines = [f"- {entry['id']}|{s['slot']}: {task_text(entry, s)}" for s in specs]
    fb = ""
    if feedback:
        fb = "\n\nYour previous attempt had these problems; avoid them:\n" + "\n".join(f"- {f}" for f in feedback)
    used_txt = "\n".join(f"- {u}" for u in dict.fromkeys(used)) or "- (none)"
    return f"""Write German gap-fill exercise sentences for a vocabulary trainer, for adult learners at about level B1/B2: the sentence must fit the word and the exercise.

Word: {entry['word']} ({entry.get('type')}; {meanings})

{RULES}

Already used (do not copy):
{used_txt}

Tasks:
{chr(10).join(lines)}{fb}

Return ONLY JSON Lines, one line per task, in the same order, nothing else:
{{"id": "<task id>", "de": "German sentence with [brackets]", "en": "English translation"}}
Präteritum, Präsens and Perfekt tasks also "verb_en": the English verb in the sense of this sentence, in the past ("avoided"), the present
("takes") or as a past participle ("locked", "posted (a letter)")."""


def read_answers_text(s):
    """Parse JSON objects written one after another (JSON Lines, or several on one line)."""
    s = re.sub(r"^```[a-z]*\n?|\n?```$", "", s.strip())
    dec, i, out = json.JSONDecoder(), 0, []
    while i < len(s):
        while i < len(s) and s[i] not in "{":
            i += 1
        if i >= len(s):
            break
        try:
            o, i = dec.raw_decode(s, i)
            out.append(o)
        except json.JSONDecodeError:
            i += 1
    return out


def show(ex):
    """'Gestern [nahm] ich …' for display."""
    d, out, last = ex["de"], "", 0
    for a, b in ex["blanks"]:
        out += d[last:a] + "[" + d[a:b] + "]"; last = b
    return out + d[last:]


def available():
    return os.path.exists(DICT_PATH)
