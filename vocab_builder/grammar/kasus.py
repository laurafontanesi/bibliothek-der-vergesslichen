"""Topic Kasus: the mixed case drill. One gap per card; the hint gives the base form, you type the
form the case needs. Cards of all cases are mixed, so the card type does not give the case away.

Cells (kind, then what is asked):
  pron    personal pronouns in Akkusativ and Dativ          kasus::pron::dat::ich      -> mir
  frage   wer, wen, wem, wessen                              kasus::frage::akk          -> wen
  prep    preposition + article (or contraction)            kasus::prep::mit::m        -> mit dem
  datv    the Dativ object of helfen, danken, gefallen ...   kasus::datv::helfen        -> dem / mir
  indef   jemand, niemand, einer, keiner                     kasus::indef::jemand::dat  -> jemandem

Possessives and articles with an adjective are practised in Deklination, not here.
"""

from .. import checks as EX

CASE_DE = {"NOM": "Nominativ", "AKK": "Akkusativ", "DAT": "Dativ", "GEN": "Genitiv"}

PRONOUNS = {"ich": ("mich", "mir"), "du": ("dich", "dir"), "er": ("ihn", "ihm"), "sie": ("sie", "ihr"),
            "es": ("es", "ihm"), "wir": ("uns", "uns"), "ihr": ("euch", "euch"),
            "sie_pl": ("sie", "ihnen"), "Sie": ("Sie", "Ihnen")}
QUESTION = {"NOM": "wer", "AKK": "wen", "DAT": "wem", "GEN": "wessen"}
PREPS = {"AKK": [("für", "mf"), ("durch", "fn"), ("gegen", "mp"), ("ohne", "nf"), ("um", "mn")],
         "DAT": [("aus", "nf"), ("bei", "mf"), ("mit", "mp"), ("nach", "nf"), ("seit", "mf"), ("von", "mf"),
                 ("zu", "mf"), ("gegenüber", "nf")],
         "GEN": [("wegen", "nm"), ("trotz", "mf"), ("während", "fp"), ("statt", "mn"), ("aufgrund", "fn"),
                 ("innerhalb", "fn"), ("außerhalb", "fp")]}
VERB_STEMS = {"helfen": ("helf", "hilf", "half", "holf"), "danken": ("dank",), "gefallen": ("gefall", "gefäll", "gefiel"),
              "gehören": ("gehör",), "gratulieren": ("gratulier",), "vertrauen": ("vertrau",)}
INDEF = {"jemand": ("jemanden", "jemandem"), "niemand": ("niemanden", "niemandem"),
         "einer": ("einen", "einem"), "keiner": ("keinen", "keinem")}
PER_CELL = {"pron": 2, "frage": 2, "prep": 1, "datv": 2, "indef": 1}
GENDER = {"m": "MAS", "f": "FEM", "n": "NEU", "p": "PLU"}
CONTRACT = {("zu", "m"): "zum", ("zu", "n"): "zum", ("zu", "f"): "zur", ("bei", "m"): "beim",
            ("bei", "n"): "beim", ("von", "m"): "vom", ("von", "n"): "vom"}


def gap(s):
    a, b = s["blanks"][0]
    return s["de"][a:b]


def expected(cell):
    """The forms the gap may hold, or None when it depends on the noun (prep, datv with a noun)."""
    k, case = cell["kind"], cell["case"]
    if k == "pron":
        return {PRONOUNS[cell["base"]][0 if case == "AKK" else 1]}
    if k == "frage":
        return {QUESTION[case]}
    if k == "indef":
        return {INDEF[cell["base"]][0 if case == "AKK" else 1]}
    return None


def _article_fits(morph, art, case, gender):
    reads, _ = EX.det_readings(morph, art)
    want = ("PLU", None) if gender == "p" else ("SIN", GENDER[gender])
    return any(c == case and n == want[0] and (want[1] is None or g == want[1]) for c, n, g in reads)


def check(s, entry, morph, cell=None):
    """Length, spelling and content as for every sentence; the gap is what the cell asks for:
    the right pronoun or question word, or a preposition + article of the cell's case and gender."""
    problems = []
    plain = s["de"]
    ts = EX.toks(plain)
    if not 3 <= len(ts) <= 16:
        problems.append(f"{len(ts)} words")
    if EX.OLD_SPELLING.search(plain):
        problems.append("old spelling")
    if EX.UNSUITABLE.search(plain):
        problems.append("unsuitable content")
    g = gap(s)
    if g.lower() != (s.get("answer") or "").lower():
        problems.append(f"the gap holds «{g}», the answer is «{s.get('answer')}»")
    if cell:
        want = expected(cell)
        if want is not None and g.lower() not in {w.lower() for w in want} | ({"Sie", "Ihnen"} if cell.get("base") == "Sie" else set()):
            problems.append(f"«{g}» is not {' / '.join(sorted(want))}")
        if cell["kind"] == "pron" and cell["base"] == "Sie" and g not in ("Sie", "Ihnen"):
            problems.append("Sie and Ihnen are written with a capital")
        if cell["kind"] == "prep":
            parts = g.split()
            prep, gender = cell["prep"], cell["gender"]
            contracted = CONTRACT.get((prep, gender))
            if len(parts) == 1:
                if parts[0].lower() != contracted:
                    problems.append(f"«{g}»: expected {prep} + article")
            elif parts[0].lower() != prep:
                problems.append(f"«{g}» does not start with {prep}")
            elif not _article_fits(morph, parts[1], cell["case"], gender):
                problems.append(f"«{parts[1]}» is not {CASE_DE[cell['case']]} {gender}")
            elif contracted and parts[1].lower() in ("dem", "der"):
                problems.append(f"usually contracted: {contracted}")
        if cell["kind"] == "datv":
            if not any(st in plain.lower() for st in VERB_STEMS[cell["verb"]]):
                problems.append(f"«{cell['verb']}» is not in the sentence")
            if g.lower() not in {"mir", "dir", "ihm", "ihr", "uns", "euch", "ihnen"}:
                reads, _ = EX.det_readings(morph, g)
                if not any(c == "DAT" for c, n, gg in reads):
                    problems.append(f"«{g}» is not a Dativ form")
    status = "error" if problems else "ok"
    return status, problems


def choose(cell_sentences, cell=None):
    n = PER_CELL.get((cell or {}).get("kind"), 1)
    ok = [s for s in cell_sentences if s.get("status") in ("ok", "check")]
    keep = ok[:n]
    for s in cell_sentences:
        s["use"] = any(s is k for k in keep)


def hint(s, det=None):
    return s.get("hint", "")
