"""
The word cards: the exercise registry, the builders and the fields of each word's cards.
"""
import random
import re
from .. import checks as EX
from ..grammar import cue
from .config import DETERMINERS, SLOTS, STAMMFORMEN_FIELD
from .text import (ausfuellen_html, bare, blank_phrase, englisch_frage, englisch_kurz, not_meant, stammformen,
                   strip_punct, quelle)


# ── exercise builders ─────────────────────────────────────────────────────────
# Each returns a dict with the keys Frage, Antwort, Ganz, GanzEN, Hinweis,
# or None when the word's data does not support that exercise.

# Sentence exercises come from the `exercises` field of words.json (checked by vocab_builder/checks.py);
# these builders only turn one of them into card fields.

# Determiners: the contrast card makes "determiner + noun" one gap and names the kind of determiner
# ("bestimmter Artikel + Anzug / Aufzug"), so the article does not give the noun away.
DET_BASE = [('ein', 'ein'), ('kein', 'kein'), ('mein', 'mein'), ('dein', 'dein'), ('sein', 'sein'),
            ('ihr', 'ihr'), ('unser', 'unser'), ('euer', 'euer'), ('eur', 'euer'), ('dies', 'dieser'),
            ('jed', 'jeder'), ('welch', 'welcher'), ('viel', 'viele'), ('einig', 'einige'),
            ('mehrer', 'mehrere'), ('wenig', 'wenige'), ('all', 'alle'), ('manch', 'manche')]
DEFINITE = {'der', 'die', 'das', 'den', 'dem', 'des'}
NUMBERS = {'zwei', 'drei', 'vier', 'fünf', 'sechs', 'sieben', 'acht', 'neun', 'zehn', 'zwölf', 'hundert'}


def determiner_base(tok):
    t = tok.lower()
    if t in DEFINITE:
        return 'der/die/das'
    if t in NUMBERS:
        return t
    if t in ('ein', 'eine', 'einen', 'einem', 'einer', 'eines'):
        return 'ein'
    for stem, base in DET_BASE[1:]:
        if t.startswith(stem) and len(t) <= len(stem) + 2:
            return base
    return None


DET_LABEL = {'der/die/das': 'bestimmter Artikel', 'ein': 'unbestimmter Artikel', 'kein': 'Negativartikel',
             'mein': 'Possessivartikel', 'dein': 'Possessivartikel', 'sein': 'Possessivartikel',
             'ihr': 'Possessivartikel', 'unser': 'Possessivartikel', 'euer': 'Possessivartikel',
             'dieser': 'Demonstrativartikel', 'welcher': 'Frageartikel'}


def det_label(tok):
    """The kind of determiner, in German: 'bestimmter Artikel', 'Possessivartikel', 'ohne Artikel' ..."""
    base = determiner_base(tok) if tok else None
    if tok.lower() == 'viel':                         # viel Arbeit
        return 'Artikelwort'
    if base in NUMBERS:
        return 'Zahlwort'
    return DET_LABEL.get(base, 'Artikelwort') if base else 'ohne Artikel'


# The verb form asked on a contrast card, from the full-form lexicon: "denken / glauben · Präsens"
AUX_FORMS = {'habe', 'hast', 'hat', 'haben', 'habt', 'hatte', 'hatten', 'hätte', 'bin', 'bist', 'ist', 'sind',
             'seid', 'war', 'waren', 'wäre', 'wird', 'werden', 'wurde', 'wurden', 'worden'}
# words after which (or before which) the verb stands in the infinitive: modals, werden, lassen, gehen
INF_TRIGGERS = {'kann', 'kannst', 'können', 'könnt', 'konnte', 'konnten', 'muss', 'musst', 'müssen', 'musste',
                'mussten', 'will', 'willst', 'wollen', 'wollte', 'wollten', 'soll', 'sollst', 'sollen', 'sollte',
                'sollten', 'darf', 'darfst', 'dürfen', 'durfte', 'möchte', 'möchtest', 'möchten', 'werde', 'wirst',
                'wird', 'werden', 'würde', 'würdest', 'würden', 'lässt', 'lassen', 'lasse', 'gehe', 'gehst', 'geht',
                'gehen', 'ging', 'solltest', 'solltet', 'könnte', 'könntest', 'könnten', 'müsste', 'müssten',
                'dürfte', 'wolltest', 'konntest', 'musstest'}
PRONOUNS = {'ich', 'du', 'er', 'sie', 'es', 'wir', 'ihr', 'man'}


def morph(ctx):
    """The full-form lexicon, loaded once with every word of every example (None without the file)."""
    if 'morph' not in ctx:
        ctx['morph'] = None
        if EX.available():
            m = EX.Morph()
            m.load({strip_punct(t) for x in ctx['by_word'].values()
                    for e in x.get('examples', []) for t in e['de'].split()})
            ctx['morph'] = m
    return ctx['morph']


def noun_number(w, form, det, ctx, first=False):
    """'Singular' or 'Plural' for the noun in the gap, from the plural in words.json and, when the two
    forms are the same (der Lehrer, die Lehrer), from the lexicon: the readings of article and noun
    must agree in case, number and gender, and an article at the start of the sentence is taken as
    nominative ("Der Maler hat ..."). '' when it cannot be told."""
    sing = bare(w['word'])
    plural = bare(w['plural']) if w.get('plural') else ''
    if w.get('plural') == w['word']:      # entered in the plural: die Abgase
        return 'Plural'
    if plural and plural != sing:
        if form in (plural, plural + 'n'):
            return 'Plural'
        if form.startswith(sing):
            return 'Singular'
    if not plural:                       # no plural in words.json: das Vertrauen, die Wucht
        return 'Singular' if form.startswith(sing) else ''
    m = morph(ctx)
    if not m:
        return ''
    reads = {tuple(t.split(':')[1:4]) for lem, t in m.get(form) if t.startswith('SUB:') and len(t.split(':')) > 3}
    if det:                              # die Lehrer: the article narrows it down
        dreads = {tuple(t.split(':')[2:5]) for lem, t in m.get(det) if t.split(':')[0] in ('ART', 'PRO')
                  and len(t.split(':')) > 4}
        reads = reads & dreads or reads
        if first:
            reads = {r for r in reads if r[0] == 'NOM'} or reads
    nums = {r[1] for r in reads}
    return {'SIN': 'Singular', 'PLU': 'Plural'}.get(nums.pop(), '') if len(nums) == 1 else ''


def adjective(tok, ctx):
    """'Adjektiv (groß, Superlativ)' for the adjective inside a noun gap ("ihr größtes Geheimnis")."""
    m = morph(ctx)
    reads = [(lem, t) for lem, t in (m.get(tok) if m else []) if t.split(':')[0] in ('ADJ', 'PA2')]
    reads = [r for r in reads if ':PRD' not in r[1]] or reads     # before a noun: schöner is not a comparative
    if not reads:
        return None
    lem = reads[0][0]
    degree = {'KOM': 'Komparativ', 'SUP': 'Superlativ'}
    found = [degree[d] for d in ('SUP', 'KOM') if any(d in t.split(':') for _, t in reads)]
    return f"Adjektiv ({lem}{', ' + found[0] if found else ''})"


def adjective_form(tok, lemma, nxt, ctx):
    """'Komparativ' or 'Superlativ' when the adjective in the gap is one, else ''. The ending of the
    base form is the declension the card practises, so it is not named: "ernster"
    in "ein sehr ernster Mensch" is ernst with an ending, and its hint says nothing more. Before a
    noun the attributive readings count, so that "ernster" there is not taken for the comparative."""
    m = morph(ctx)
    if not m or tok.lower() == lemma.lower():
        return ''
    reads = [t.split(':') for lem, t in m.get(tok) if lem.lower() == lemma.lower()
             and t.split(':')[0] in ('ADJ', 'PA1', 'PA2')]
    attributive = nxt[:1].isupper()
    pick = [t for t in reads if ('PRD' in t) != attributive] or reads
    if any('SUP' in t for t in pick):
        return 'Superlativ'
    if any('KOM' in t for t in pick):
        return 'Komparativ'
    return ''


def verb_tense(tok, toks, i, ctx, override=None, lemma=''):
    """'Präsens', 'Präteritum', 'Partizip II', 'Infinitiv' or 'Imperativ' for the verb in the gap
    (an example can set its own with "tense")."""
    if override is not None:
        return override
    m = morph(ctx)
    if not m:
        return ''
    tags = [t for _, t in m.get(tok)]
    lower = [strip_punct(x).lower() for x in toks]
    prev = lower[i - 1] if i > 0 else ''
    nxt = lower[i + 1] if i + 1 < len(lower) else ''
    if lower[0] == 'bitte' and nxt == 'sie':
        return 'Imperativ (Sie)'                    # Bitte folgen Sie mir
    infinitive_here = (prev == 'zu' or nxt in INF_TRIGGERS or any(x in INF_TRIGGERS for x in lower[:i])
                       or lower[0] == 'bitte')          # Bitte nicht berühren!
    if not tags:                                    # not in the lexicon (vorhabe, hinauffahren)
        if i == 0 and nxt not in PRONOUNS:
            return 'Imperativ'
        return 'Infinitiv' if tok.lower() == lemma.lower() else 'Präsens'
    if any(':EIZ' in t for t in tags):
        return 'Infinitiv mit zu'                   # auszuschalten
    if any('INF' in t for t in tags) and infinitive_here:
        return 'Infinitiv'
    if any('PA2' in t for t in tags) and any(x in AUX_FORMS for x in lower):
        return 'Partizip II'
    if any('PRT' in t for t in tags):
        return 'Präteritum'
    if i == 0 and nxt not in PRONOUNS and any(':IMP:SIN' in t for t in tags):
        return 'Imperativ'
    if any('PRÄ' in t for t in tags):
        return 'Präsens'
    if any('INF' in t for t in tags):
        return 'Infinitiv'
    if any('PA2' in t for t in tags):
        return 'Partizip II'
    return ''


def ex_slot(slot):
    """A verb card from the word's exercise sentence: the gaps, the cue ([Präteritum · 1 Wort]) and
    the English with the verb highlighted (vocab_builder/grammar/cue.py)."""
    def build(w, ctx):
        ex = next((e for e in w.get('exercises', []) if e['slot'] == slot and e.get('blanks')), None)
        if not ex:
            return None
        satz, ganz, antwort = cue.gapped(ex['de'], ex['blanks'])
        en_hl, _ = cue.verb_highlight(ex)
        return dict(Frage=satz, Antwort=antwort, Ganz=ganz, GanzEN=cue.html(en_hl or ex.get('en', '')),
                    Hinweis=cue.verb_cue(ex), Quelle=quelle(ex))
    return build


def ex_kontrast(w, ctx):
    """Up to three confusable partners. The hint gives the words to choose from, what else the gap
    holds and how many words it has:
        nouns       "unbestimmter Artikel + Adjektiv (dunkel) + Anzug / Aufzug · Singular · 3 Wörter",
                    "Gedächtnis / Erinnerung · nur das Nomen, Plural · 1 Wort"
        verbs       "denken / glauben · Präsens · 1 Wort"
        adjectives  "schnell / langsam · Komparativ · 1 Wort" only for a comparative or superlative;
                    the ending of the base form is not named
    The number of words is left out when the options differ in length (noch / immer noch): it
    would give the answer away.

    The word is looked for in its examples by its first letters (denk- in dachte would be missed);
    a word not found that way is looked for, in this order, by the exact word (da, vor), by the lexicon's lemma (gesagt, weiß),
    as a fixed phrase (immer noch), as a separable verb split in two (fängt … an: two gaps), as a
    two-part connector (weder … noch: two gaps) and, for "sein + zu + Infinitiv" and its partners,
    by the finite verb."""
    # a partner spelled the same without sich (halten / sich halten) would give two equal options
    partners = [x['word'] for x in w.get('related', [])
                if isinstance(x, dict) and x['kind'] in ('contrast', 'antonym')
                and ctx['by_word'].get(x['word'], {}).get('type') == w.get('type')
                and bare(x['word']) != bare(w['word'])]
    if not partners:
        return None
    word = bare(w['word'])
    stem = word[:max(4, len(word) - 3)].lower()
    got = scan(w, ctx, partners, ctx['rng'], lambda c: len(c) >= 4 and c.lower().startswith(stem))
    if got:
        return got
    rng = random.Random(w['word'])            # the option order of the other cards stays the same
    if ' ' not in word:
        got = scan(w, ctx, partners, rng, lambda c: c.lower() == word.lower())
        m = morph(ctx)
        if not got and m and w.get('type') == 'verb':
            got = scan(w, ctx, partners, rng, lambda c: any(
                lem.lower() == word.lower() for lem, t in m.get(c) if t.startswith(('VER', 'PA2'))))
        return got or split_verb(w, ctx, partners, rng)
    if '+ zu +' in word:
        return zu_infinitive(w, ctx, partners, rng)
    if '…' in word or re.fullmatch(r'[\w ]+', word):
        return phrase_gaps(w, ctx, partners, rng)
    return None                               # X ist aus Y: the form would give it away


def options(w, partners, rng):
    """The words to choose from, shuffled, and whether they all have the same number of words."""
    opts = [bare(w['word'])] + [bare(p) for p in partners[:3]]
    opts = [re.sub(r'\s*…$', '', o) for o in opts]           # "weder … noch …" -> "weder … noch"
    rng.shuffle(opts)
    same = len({len(o.split()) for o in opts}) == 1
    return ' / '.join(opts), same


def scan(w, ctx, partners, rng, match):
    """The card from the first example word for which match(word) is true; None if there is none."""
    for ex in w.get('examples', []):
        toks = ex['de'].split()
        for i, tok in enumerate(toks):
            cand = strip_punct(tok)
            if not cand or not match(cand):
                continue
            prev = strip_punct(toks[i - 1]) if i > 0 else ''
            prev2 = strip_punct(toks[i - 2]) if i > 1 else ''
            # options without articles: the article would be a second giveaway. A word with several
            # confusable partners gets them all (up to four options).
            choice, same = options(w, partners, rng)
            start, adj = i, None
            def is_det(t):
                return t.lower() in DETERMINERS or determiner_base(t) is not None
            if w.get('type') == 'noun':
                if is_det(prev):
                    start = i - 1
                elif is_det(prev2) and prev[:1].islower() and re.search(r'(e|en|em|er|es)$', prev):
                    # "ein ausgezeichnetes Gedächtnis": the adjective ending would give the gender
                    # away, so determiner + adjective + noun are one gap
                    base = re.sub(r'(en|em|er|es|e)$', '', prev)
                    if re.search(r'[^aeiouäöü][lr]$', base):          # dunkl -> dunkel, (sauber stays)
                        base = base[:-1] + 'e' + base[-1]
                    elif base.endswith('eur'):                         # teur -> teuer
                        base = base[:-1] + 'er'
                    elif base == 'hoh':
                        base = 'hoch'
                    adj = f'Adjektiv ({base})'
                    start = i - 2
            if adj:
                adj = adjective(prev, ctx) or adj
            nxt = strip_punct(toks[i + 1]) if i + 1 < len(toks) and tok == cand else ''
            if start == i:                          # the word alone
                info = []
                if w.get('type') == 'verb':         # the tense asked: "denken / glauben · Präsens"
                    info.append(verb_tense(cand, toks, i, ctx, ex.get('tense'), bare(w['word'])))
                elif w.get('type') == 'noun':
                    number = noun_number(w, cand, '', ctx)
                    info.append('nur das Nomen' + (', ' + number if number else ''))
                elif w.get('type') == 'adj/adv':
                    info.append(adjective_form(cand, bare(w['word']), nxt, ctx))
                hint = ' · '.join([choice.replace(' / ', '  /  ')] + [x for x in info if x]
                                  + ([cue.words(1)] if same else []))
                # the gap replaces the word only, so "Konto." keeps its full stop
                return dict(Frage=blank_phrase(ex['de'], tok).replace('___', '___' + tok[len(tok.rstrip('.,;:!?')):], 1)
                            if tok != cand else blank_phrase(ex['de'], tok), Antwort=cand, Ganz=ex['de'],
                            GanzEN=ex.get('en', ''), Hinweis=hint)
            phrase = ' '.join(toks[start:i + 1])
            tail = tok[len(tok.rstrip('.,;:!?')):]                 # keep "." after the noun
            parts = [det_label(strip_punct(toks[start]))]
            if adj:
                parts.append(adj)
            parts.append(choice)
            number = noun_number(w, cand, strip_punct(toks[start]), ctx, first=start == 0)
            hint = ' · '.join([' + '.join(parts)] + ([number] if number else [])
                              + ([cue.words(i + 1 - start)] if same else []))
            return dict(Frage=ex['de'].replace(phrase, '______' + tail, 1),
                        Antwort=' '.join(strip_punct(t) for t in toks[start:i + 1]),
                        Ganz=ex['de'], GanzEN=ex.get('en', ''), Hinweis=hint)
    return None


def token_spans(de):
    """[(word without punctuation, start, end)] for a sentence."""
    out = []
    for m in re.finditer(r'\S+', de):
        t = m.group()
        a = len(t) - len(t.lstrip('.,;:!?„“"\'(—–'))
        b = len(t.rstrip('.,;:!?„“"\')—–'))
        if b > a:
            out.append((t[a:b], m.start() + a, m.start() + b))
    return out


def gap_card(ex, spans, hint):
    satz, ganz, answer = cue.gapped(ex['de'], spans)
    return dict(Frage=satz.replace(cue.GAP, '___'), Antwort=answer, Ganz=ganz,
                GanzEN=ex.get('en', ''), Hinweis=hint)


PARTICLES = ('zurück', 'durch', 'heraus', 'herunter', 'hinauf', 'kennen', 'nach', 'fest', 'weg', 'auf',
             'aus', 'ein', 'los', 'mit', 'vor', 'her', 'hin', 'an', 'ab', 'um', 'zu')


def split_verb(w, ctx, partners, rng):
    """A separable verb that every example splits (Wann fängt der Film an?): two gaps, or one when
    the two parts stand together (Sie fing an zu weinen)."""
    word, m = bare(w['word']), morph(ctx)
    part = next((p for p in PARTICLES if word.startswith(p) and len(word) > len(p) + 3), None)
    if not part or not m:
        return None
    rest = word[len(part):]
    for ex in w.get('examples', []):
        toks = token_spans(ex['de'])
        for i, (t, a, b) in enumerate(toks):
            if not any(lem.lower() == rest for lem, tag in m.get(t) if tag.startswith('VER')):
                continue
            j = next((k for k in range(i + 1, len(toks)) if toks[k][0].lower() == part), None)
            if j is None:
                continue
            choice, same = options(w, partners, rng)
            tense = verb_tense(t, [x[0] for x in toks], i, ctx, ex.get('tense'), word)
            hint = ' · '.join([choice.replace(' / ', '  /  ')] + ([tense] if tense else []) + [cue.words(2)])
            return gap_card(ex, [(a, b), (toks[j][1], toks[j][2])], hint)
    return None


def phrase_gaps(w, ctx, partners, rng):
    """A fixed phrase (immer noch) as one gap, a two-part connector (weder … noch) as two."""
    word = bare(w['word'])
    pieces = [x.strip() for x in word.split('…') if x.strip()]
    for ex in w.get('examples', []):
        spans, pos = [], 0
        for piece in pieces:
            hit = re.compile(r'\b' + r'\s+'.join(map(re.escape, piece.split())) + r'\b', re.I).search(ex['de'], pos)
            if not hit:
                break
            spans.append((hit.start(), hit.end()))
            pos = hit.end()
        if len(spans) != len(pieces):
            continue
        choice, same = options(w, partners, rng)
        n = sum(len(p.split()) for p in pieces)
        hint = ' · '.join([choice.replace(' / ', '  /  ')] + ([cue.words(n)] if same else []))
        return gap_card(ex, spans, hint)
    return None


def zu_infinitive(w, ctx, partners, rng):
    """'sein + zu + Infinitiv' and its partners: the finite verb is the gap, the options are the verbs
    (Das Problem ___ leicht zu lösen. sein / haben (+ zu + Infinitiv) · Präsens · 1 Wort)."""
    m = morph(ctx)
    verb = bare(w['word']).split('+')[0].split()[-1]
    if not m:
        return None
    for ex in w.get('examples', []):
        toks = token_spans(ex['de'])
        for i, (t, a, b) in enumerate(toks):
            if not any(lem == verb for lem, tag in m.get(t) if tag.startswith('VER')):
                continue
            verbs = [verb] + [bare(p).split('+')[0].split()[-1] for p in partners[:3]]
            rng.shuffle(verbs)
            tense = verb_tense(t, [x[0] for x in toks], i, ctx, ex.get('tense'), verb)
            hint = ' · '.join([' / '.join(verbs).replace(' / ', '  /  ') + ' (+ zu + Infinitiv)']
                              + ([tense] if tense else []) + [cue.words(1)])
            return gap_card(ex, [(a, b)], hint)
    return None


# ── the registry ──────────────────────────────────────────────────────────────
# key, German label shown on the card, builder

EXERCISES = [
    ('Praet',    'Präteritum',             ex_slot('praet')),
    ('Part',     'Perfekt',                ex_slot('part')),
    ('Praes',    'Präsens (er/sie/es)',    ex_slot('praes')),
    ('Refl',     'Reflexivpronomen',       ex_slot('refl')),
    ('Kontrast', 'Welches Wort passt?',    ex_kontrast),
]

# card order within a word: first recognise it (Bedeutung), then produce it (Produzieren), then
# its forms, and last the card that needs it to be known well (Welches Wort passt?)
CARD_ORDER = ['Bedeutung', 'Produzieren', 'Praes', 'Refl', 'Part', 'Praet', 'Kontrast']
assert sorted(CARD_ORDER) == sorted([k for k, *_ in EXERCISES] + ['Bedeutung', 'Produzieren'])


def asks_plural(w):
    """Produzieren asks for the plural of every noun that has one, except where `plural_card` is false
    (rare, or another meaning: die Mängel) and for nouns entered in the plural (die Abgase)."""
    return (w.get('type') == 'noun' and bool(w.get('plural')) and w.get('plural') != w['word']
            and w.get('plural_card') is not False)


def wort_answer(w):
    """What Produzieren asks you to type: the word, plus its plural (der Krug, die Krüge;
    die Spüle, die Spülen). Which preposition a word takes is its own grammar card (Feste
    Präpositionen), not part of this answer."""
    out = w['word']
    if asks_plural(w):
        out += ', ' + w['plural']
    return out


def answer_hint(w):
    """What the answer includes, in the "Bitte ausfüllen" box above the answer box, as on the other
    cards: Nomen mit Artikel, mit Plural / Verb im Infinitiv, mit sich ..."""
    t = w.get('type')
    if t == 'noun':
        if asks_plural(w):
            cue = 'Nomen mit Artikel, mit Plural'
        elif w.get('plural') == w['word']:
            cue = 'Nomen mit Artikel, im Plural'              # die Abgase
        elif not w.get('plural'):
            cue = 'Nomen mit Artikel, ohne Plural'            # das Vertrauen
        else:
            cue = 'Nomen mit Artikel'                         # plural_card false: die Mängel
    elif t == 'verb':
        cue = 'Verb im Infinitiv' + (', mit sich' if w['word'].startswith('sich ') else '')
    elif t == 'adj/adv':
        cue = 'Adjektiv oder Adverb'
    elif t == 'prep/conj':
        cue = 'Präposition oder Konjunktion'
    else:
        cue = 'Ausdruck'
    return ausfuellen_html(cue)


# ── one word's fields ─────────────────────────────────────────────────────────

def word_fields(w, ctx):
    """The fields of a word's cards: what Bedeutung and Produzieren ask and answer, the principal
    parts, and the fields of every exercise card the word gets (<key>_Frage, _Antwort, ...)."""
    r = {'Wort': wort_answer(w),
         'EnglischFrage': answer_hint(w) + englisch_frage(w, tilde=True) + not_meant(w, ctx),
         'EnglischKurz': englisch_kurz(w),
         STAMMFORMEN_FIELD: stammformen(w)}          # read aloud on Bedeutung and Produzieren
    for key, _label, builder in EXERCISES:
        got = builder(w, ctx)
        if not got:
            continue
        if key == 'Kontrast' and got.get('Antwort') and 'class="hl"' not in got.get('Ganz', ''):
            got['Ganz'] = got['Ganz'].replace(got['Antwort'], f'<span class="hl">{got["Antwort"]}</span>', 1)
        for slot in SLOTS:
            r[f'{key}_{slot}'] = got.get(slot, '')
    return r
