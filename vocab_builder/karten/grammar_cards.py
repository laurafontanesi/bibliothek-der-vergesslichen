"""
The grammar cards: one card per sentence of grammar.json; and the collocation cards.

A grammar card shows the sentence with its gaps, the cue in German ([Präposition + unbestimmter
Artikel · 2 Wörter]) and the English with the part to translate highlighted; you type the answer.
The back is the refresher for the topic, with the asked form marked in its table. Card ids come from the
cell and the sentence, so a sentence keeps its learning history as long as it is not changed.
"""
from .. import checks as EX
from ..grammar import cue, kasus, model as gmodel
import re

from .text import englisch_kurz, notiz, quelle as quelle_of

CASES = ['NOM', 'AKK', 'DAT', 'GEN']
CASE_DE = {'NOM': 'Nominativ', 'AKK': 'Akkusativ', 'DAT': 'Dativ', 'GEN': 'Genitiv'}
GENDER_DE = {'m': 'maskulin', 'f': 'feminin', 'n': 'neutral', 'pl': 'Plural', 'p': 'Plural'}
DER = {'NOM': ('der', 'die', 'das', 'die'), 'AKK': ('den', 'die', 'das', 'die'),
       'DAT': ('dem', 'der', 'dem', 'den'), 'GEN': ('des', 'der', 'des', 'der')}
EIN = {'NOM': ('ein', 'eine', 'ein', 'keine'), 'AKK': ('einen', 'eine', 'ein', 'keine'),
       'DAT': ('einem', 'einer', 'einem', 'keinen'), 'GEN': ('eines', 'einer', 'eines', 'keiner')}
COLS = ['m', 'f', 'n', 'pl']


# ── small HTML helpers ────────────────────────────────────────────────────────

def table(head, rows, on=None):
    """rows: [(label, [cells])]; on: (row index, column index) to mark."""
    h = '<tr><th></th>' + ''.join(f'<th>{x}</th>' for x in head) + '</tr>'
    body = ''
    for i, (label, cells) in enumerate(rows):
        body += f'<tr><th>{label}</th>' + ''.join(
            f'<td class="on">{c}</td>' if on == (i, j) else f'<td>{c}</td>' for j, c in enumerate(cells)) + '</tr>'
    return f'<table class="tab">{h}{body}</table>'


def para(lines):
    return ''.join(f'<p>{x}</p>' for x in lines if x)


def signal(word):
    """der -> de<b>r</b>: the signal letter in bold."""
    return word[:-1] + f'<b>{word[-1]}</b>' if word else word


# ── refreshers ────────────────────────────────────────────────────────────────

DIESER = {'NOM': ('dieser', 'diese', 'dieses', 'diese'), 'AKK': ('diesen', 'diese', 'dieses', 'diese'),
          'DAT': ('diesem', 'dieser', 'diesem', 'diesen'), 'GEN': ('dieses', 'dieser', 'dieses', 'dieser')}
KEIN = {'NOM': ('kein', 'keine', 'kein', 'keine'), 'AKK': ('keinen', 'keine', 'kein', 'keine'),
        'DAT': ('keinem', 'keiner', 'keinem', 'keinen'), 'GEN': ('keines', 'keiner', 'keines', 'keiner')}
MEIN = {k: tuple('m' + x[1:] for x in v) for k, v in KEIN.items()}
EIN_SG = {k: v[:3] + ('–',) for k, v in EIN.items()}
WEAK = {'NOM': ('e', 'e', 'e', 'en'), 'AKK': ('en', 'e', 'e', 'en'), 'DAT': ('en',) * 4, 'GEN': ('en',) * 4}
MIXED = {'NOM': ('er', 'e', 'es', 'en'), 'AKK': ('en', 'e', 'es', 'en'), 'DAT': ('en',) * 4, 'GEN': ('en',) * 4}
STRONG = {'NOM': ('er', 'e', 'es', 'e'), 'AKK': ('en', 'e', 'es', 'e'), 'DAT': ('em', 'er', 'em', 'en'),
          'GEN': ('en', 'er', 'en', 'er')}
DET_TABLE = {'der': (DER, WEAK), 'dieser': (DIESER, WEAK), 'ein': (EIN_SG, MIXED), 'kein': (KEIN, MIXED),
             'mein': (MEIN, MIXED), 'ohne': (None, STRONG)}
# The rules on the backs are in German, in short B1 sentences.
DET_NOTE = {
    'der': 'der, die, das zeigen das Signal schon. Das Adjektiv bekommt nur -e oder -en.',
    'dieser': 'dieser, jener, jeder, welcher und alle enden wie der, die, das. Sie zeigen das Signal, '
              'also bekommt das Adjektiv nur -e oder -en.',
    'ein': 'ein hat an drei Stellen keine Endung: Nominativ maskulin, Nominativ und Akkusativ neutral. '
           'Dort zeigt das Adjektiv das Signal (ein alter Mann, ein altes Auto). Sonst bekommt es -e oder -en. '
           'ein hat keinen Plural: alte Freunde, wie ohne Artikel.',
    'kein': 'kein geht wie ein, hat aber einen Plural (keine). Wo kein keine Endung hat, zeigt das Adjektiv '
            'das Signal (kein guter Plan, kein neues Auto). Sonst bekommt es -e oder -en.',
    'mein': 'mein, dein, sein, ihr, unser, euer und Ihr gehen wie kein. Wo sie keine Endung haben, zeigt das '
            'Adjektiv das Signal (mein alter Freund, unser neues Auto). Sonst bekommt es -e oder -en.',
    'ohne': 'Ohne Artikel zeigt das Adjektiv das Signal selbst (kalter Kaffee, mit kaltem Wasser). Ausnahme: '
            'Genitiv maskulin und neutral hat -en (trotz starken Regens), weil das Nomen schon das -s hat. '
            'Nach Zahlen und nach viele, mehrere, einige, wenige: genauso.',
}
SIGNAL_EINMAL = 'Jede Nominalgruppe zeigt das Signal genau einmal, vor dem Nomen. Rot: die Endung des Nomens selbst.'


def noun_note(c, s, by_id):
    """Nomen: Bildhauer → des Bildhauers (Genitiv: -s). Only when the noun changes."""
    w = by_id.get(s.get('word_id') or '', {})
    if w.get('type') != 'noun':
        return ''
    gap = s['de'][s['blanks'][0][0]:s['blanks'][0][1]].split()
    form = gap[-1] if gap else ''
    pl = c['gender'] in ('pl', 'p')
    base = re.sub(r'^(der|die|das)\s+', '', (w.get('plural') if pl else w['word']) or '')
    if not form or not base or form == base:
        return ''
    if pl and form == base + 'n':
        why = 'Dativ Plural: + n'
    elif not pl and c['case'] == 'GEN' and form in (base + 's', base + 'es'):
        why = 'Genitiv maskulin und neutral: + s oder + es'
    elif not pl and form in (base + 'n', base + 'en'):
        why = 'n-Deklination: + n oder + en in allen Fällen außer Nominativ Singular'
    else:
        why = ''
    return f'Nomen: {base} → {form}' + (f' ({why})' if why else '')


# ── noun forms from the full-form lexicon (private/sources/morphy) ───────────────────────

_NOUN_FORMS = {}


def load_noun_forms(lemmas):
    """{lemma: {(case, number, gender): {forms}}}, one pass over the lexicon for all lemmas at once."""
    want = {l.encode('utf-8') for l in lemmas if l and l not in _NOUN_FORMS}
    if not want or not EX.available():
        return
    for l in want:
        _NOUN_FORMS[l.decode('utf-8')] = {}
    with open(EX.DICT_PATH, 'rb') as fh:
        for line in fh:
            p = line.rstrip(b'\n').split(b'_', 2)
            if len(p) == 3 and p[0] in want and p[2].startswith(b'SUB:') and not p[2].endswith(b':ADJ'):
                t = p[2].decode('utf-8').split(':')
                if len(t) >= 4:
                    _NOUN_FORMS[p[0].decode('utf-8')].setdefault((t[1], t[2], t[3]), set()).add(p[1].decode('utf-8'))


GENDER_TAG = {'m': 'MAS', 'f': 'FEM', 'n': 'NEU'}


def noun_form(lemma, case, gender, plural=None):
    """The noun in a case: from the lexicon, else by rule (Genitiv maskulin and neutral + s or es,
    Dativ Plural + n). `plural`: the plural form, for the plural rows."""
    pl = gender in ('pl', 'p')
    forms = set()
    for (c, n, gd), fs in _NOUN_FORMS.get(lemma, {}).items():
        if c == case and n == ('PLU' if pl else 'SIN') and (pl or gd == GENDER_TAG[gender]):
            forms |= fs
    if pl and plural:                      # der Brand: Brände (fire), not Brands (brand names)
        forms = {f for f in forms if f.startswith(plural)} or forms
    if forms:
        return min(forms, key=lambda f: (len(f), f))
    base = plural if pl and plural else lemma
    if pl:
        return base + 'n' if case == 'DAT' and not base.endswith(('n', 's')) else base
    if case == 'GEN' and gender in ('m', 'n'):
        return base + ('es' if base.endswith(('s', 'ß', 'x', 'z', 'sch')) else 's')
    return base


def mark_noun(form, base):
    """Umgangs -> Umgang<span class="sfx">s</span>: the noun's own ending in red."""
    if form != base and form.startswith(base):
        return base + f'<span class="sfx">{form[len(base):]}</span>'
    return form


def with_signal(det):
    """der -> de<b>r</b>; ein, kein, mein without ending stay as they are."""
    if not det or det in ('ein', 'kein', 'mein', 'dein', 'sein', 'ihr', 'unser', 'euer'):
        return det
    return det[:-1] + f'<b>{det[-1]}</b>'


# the three kinds of article in the declension table: the card's own determiner takes its column
DER_COL = {'der': ('bestimmter Artikel', DER), 'dieser': ('dieser', DIESER)}
EIN_COL = {'ein': ('unbestimmter Artikel', EIN_SG), 'kein': ('kein', KEIN), 'mein': ('mein, dein …', MEIN)}


def det_forms(word, pattern, stem_len):
    """The determiner the sentence uses, in every case: jede -> jeder, jede, jedes ... (like dieser);
    unser -> unser, unsere, unseren ... (like kein). `stem_len`: the length of the pattern's stem."""
    stem = word
    bare_forms = ('mein', 'dein', 'sein', 'ihr', 'unser', 'euer', 'kein')
    for e in [] if word.lower() in bare_forms else sorted({f[stem_len:] for row in pattern.values() for f in row if f != '–'}, key=len, reverse=True):
        if e and word.lower().endswith(e) and len(word) - len(e) >= 2:
            stem = word[:-len(e)]
            break
    stem = stem.lower()
    out = {}
    for case, row in pattern.items():
        forms = []
        for f in row:
            end = f[stem_len:]
            forms.append(('eur' if stem == 'euer' and end else stem) + end if f != '–' else '–')
        out[case] = tuple(forms)
    return stem, out


def dekl_columns(det, plural, word=''):
    """The three columns: der-type, ein-type, no article. The sentence's own determiner (jede, alle,
    unser, seine) takes its column, in all its forms."""
    first = DER_COL.get(det, DER_COL['der'])
    if det == 'dieser' and word:
        stem, forms = det_forms(word, DIESER, 4)
        first = (stem + ('e' if plural else 'er'), forms)
    if plural:                                   # ein has no plural: kein (or mein) stands in for it
        second = EIN_COL['mein'] if det == 'mein' else EIN_COL['kein']
    else:
        second = EIN_COL.get(det, EIN_COL['ein'])
    if det in ('mein', 'kein') and word:
        stem, forms = det_forms(word, KEIN, 4)
        second = (stem, forms)
    on = 0 if det in DER_COL else 2 if det == 'ohne' else 1
    return [(first[0], first[1], WEAK), (second[0], second[1], MIXED), ('ohne Artikel', None, STRONG)], on


def adj_stem(adj):
    """The stem the endings go on: dunkel -> dunkl, teuer -> teur, hoch -> hoh, böse -> bös."""
    if adj == 'hoch':
        return 'hoh'
    if adj.endswith('e'):
        return adj[:-1]
    if adj.endswith('el') and len(adj) > 3:
        return adj[:-2] + 'l'
    if adj.endswith(('euer', 'auer')):
        return adj[:-2] + 'r'
    return adj


def adjectives(adj, ending):
    """'jung, Schweizer' + 'er' -> junger Schweizer: adjectives from place names do not decline."""
    out = []
    for a in [x.strip() for x in (adj or '').split(',') if x.strip()]:
        out.append(a if a[:1].isupper() and a.endswith('er') else f'{adj_stem(a)}<b>{ending}</b>')
    return ' '.join(out)


def dekl_phrase_table(c, s, w):
    """The whole declension of the card's noun phrase in its gender (or the plural), with the three
    kinds of article: der freundliche Umgang, ein freundlicher Umgang, freundlicher Umgang ... The
    asked cell is marked; the noun's own endings (Genitiv -s, Dativ Plural -n, n-Deklination) are red."""
    gender = 'pl' if c['gender'] in ('pl', 'p') else c['gender']
    j = COLS.index(gender)
    plural_word = re.sub(r'^(der|die|das)\s+', '', w.get('plural') or '') if w else ''
    lemma = re.sub(r'^(der|die|das)\s+', '', (w or {}).get('word') or s.get('word') or '')
    if not lemma:
        return ''
    adj = s.get('adj') or ''
    first = s['de'][s['blanks'][0][0]:s['blanks'][0][1]].split()[0] if s.get('blanks') else ''
    cols, on_col = dekl_columns(c['det'], gender == 'pl', first)
    if c['det'] == 'ohne' and first[:1].islower() and adj and not first.lower().startswith(adj_stem(adj.split(',')[0])):
        cols[2] = (f'ohne Artikel, auch nach {first}', None, STRONG)      # zwei volle Krüge, mehrere große Brände
    base = noun_form(lemma, 'NOM', gender, plural_word)
    head = ''.join(f'<th>{lab}</th>' for lab, *_ in cols)
    rows = ''
    for case in CASES:
        cells = ''
        for ci, (lab, dets, ends) in enumerate(cols):
            d = dets[case][j] if dets else ''
            if d == '–':
                cells += '<td class="leer">–</td>'
                continue
            noun = mark_noun(noun_form(lemma, case, gender, plural_word), base)
            a = adjectives(adj, ends[case][j]) + ' ' if adj else ''
            on = ' class="on"' if (ci == on_col and case == c['case']) else ''
            cells += f'<td{on}>{(with_signal(d) + " ") if d else ""}{a}{noun}</td>'
        rows += f'<tr><th>{CASE_DE[case][:3]}</th>{cells}</tr>'
    return f'<div class="tabwrap"><table class="tab"><tr><th></th>{head}</tr>{rows}</table></div>'


# the same four nouns on every preposition card, so only the preposition and the case change
PREP_NOUNS = [('m', 'Kaffee', ''), ('f', 'Suppe', ''), ('n', 'Brot', ''), ('pl', 'Keks', 'Kekse')]
PREP_ADJ = 'frisch'


def prep_table(prep, case):
    """über + Akkusativ with each kind of article, for each gender and the plural; in each cell the
    article + noun and, below, article + adjective + noun (über den Kaffee / über den frischen Kaffee).
    Without an article the genitive needs the adjective (wegen frischen Kaffees), so the plain form is –."""
    head = '<th>bestimmter Artikel</th><th>unbestimmter Artikel</th><th>ohne Artikel</th>'
    rows = ''
    for gender, lemma, plural in PREP_NOUNS:
        j = COLS.index(gender)
        base = noun_form(lemma, 'NOM', gender, plural)
        noun = mark_noun(noun_form(lemma, case, gender, plural), base)
        cells = ''
        for dets, ends in [(DER, WEAK), (KEIN if gender == 'pl' else EIN_SG, MIXED), (None, STRONG)]:
            d = with_signal(dets[case][j]) if dets else ''
            art = (d + ' ') if d else ''
            # the preposition is in the title (über + Akkusativ): in the cells it would make the
            # table too wide for a phone
            plain = '–' if (not dets and case == 'GEN') else f'{art}{noun}'
            adj = f'{art}{PREP_ADJ}<b>{ends[case][j]}</b> {noun}'
            cells += f'<td>{plain}<br><span class="mit-adj">{adj}</span></td>'
        rows += f'<tr><th>{"Pl" if gender == "pl" else gender}</th>{cells}</tr>'
    return (f'<p class="tabtitel">{prep} + {CASE_DE[case]}</p>'
            f'<div class="tabwrap"><table class="tab"><tr><th></th>{head}</tr>{rows}</table></div>')


# prepositions among the connectors (Konnektoren): their case, for the table
CONNECTOR_PREP_CASES = {'während': ['GEN'], 'wegen': ['GEN'], 'trotz': ['GEN'], 'aufgrund': ['GEN'],
                        'infolge': ['GEN'], 'laut': ['DAT'], 'seit': ['DAT'], 'entgegen': ['DAT'],
                        'neben': ['DAT', 'AKK'], 'vor': ['DAT', 'AKK']}


def regel_dekl(g, c, s=None, by_id=None):
    det = c['det']
    dets, ends = DET_TABLE[det]
    on = (CASES.index(c['case']), COLS.index(c['gender'] if c['gender'] != 'p' else 'pl'))

    def cell(k, j):
        d = dets[k][j] if dets else ''
        if d == '–':
            return f'(alt<b>{STRONG[k][j]}</b>)'
        return (d + ' ' if d else '') + f'alt<b>{ends[k][j]}</b>'
    tab = table(['m', 'f', 'n', 'Pl'], [(CASE_DE[k][:3], [cell(k, j) for j in range(4)]) for k in CASES], on)
    if s:                                         # the card's own noun phrase, in all cases and articles
        w = (by_id or {}).get(s.get('word_id') or '', {})
        tab = dekl_phrase_table(c, s, w) or tab
    nn = noun_note(c, s, by_id or {}) if s else ''
    return para([DET_NOTE[det]]) + tab + para(([nn] if nn else []) + [SIGNAL_EINMAL])


PRON_ROWS = [('ich', 'mich', 'mir'), ('du', 'dich', 'dir'), ('er', 'ihn', 'ihm'), ('sie', 'sie', 'ihr'),
             ('es', 'es', 'ihm'), ('wir', 'uns', 'uns'), ('ihr', 'euch', 'euch'), ('sie (Pl.)', 'sie', 'ihnen'),
             ('Sie', 'Sie', 'Ihnen')]
PRON_KEY = {'ich': 0, 'du': 1, 'er': 2, 'sie': 3, 'es': 4, 'wir': 5, 'ihr': 6, 'sie_pl': 7, 'Sie': 8}
DATIVE_VERBS = ('helfen, danken, gefallen, gehören, gratulieren, vertrauen, antworten, folgen, schmecken, '
                'passen, fehlen, glauben (jemandem), zuhören')


def regel_kasus(c):
    k, case = c['kind'], c['case']
    if k == 'pron':
        on = (PRON_KEY[c['base']], 1 if case == 'AKK' else 2)
        return para(['Akkusativ: das direkte Objekt (wen? was?). Dativ: die Person, der man etwas gibt oder für '
                     'die man etwas tut (wem?), und nach Verben und Präpositionen mit Dativ.']) + \
            table(['Nom', 'Akk', 'Dat'], [(r[0], list(r)) for r in PRON_ROWS], on)
    if k == 'frage':
        return table(['Frage'], [(CASE_DE[x][:3], [w]) for x, w in kasus.QUESTION.items()],
                     (CASES.index(case), 0)) + para(['wessen fragt nach dem Besitzer: Wessen Jacke? Annas Jacke.'])
    if k == 'prep':
        groups = []
        for cs, preps in kasus.PREPS.items():
            names = ', '.join(f'<b>{p}</b>' if p == c['prep'] else p for p, _ in preps)
            groups.append(f'{CASE_DE[cs]}: {names}')
        return para(groups + ['Verschmolzen: zum (zu dem), zur (zu der), beim (bei dem), vom (von dem), '
                              'im (in dem), am (an dem), ins (in das).']) + prep_table(c['prep'], case)
    if k == 'datv':
        return para([f'Verben mit Dativobjekt: {DATIVE_VERBS}.']) + \
            table(['m', 'f', 'n', 'Pl'], [('Dat', [signal(x) for x in DER['DAT']])])
    forms = {'jemand': ('jemand', 'jemanden', 'jemandem'), 'niemand': ('niemand', 'niemanden', 'niemandem'),
             'einer': ('einer', 'einen', 'einem'), 'keiner': ('keiner', 'keinen', 'keinem')}
    on = (list(forms).index(c['base']), 1 if case == 'AKK' else 2)
    return table(['Nom', 'Akk', 'Dat'], [(b, list(f)) for b, f in forms.items()], on) + \
        para(['einer, keiner als Pronomen: Die Tabelle zeigt maskulin. Feminin: eine, keine. Neutral: eins, keins.'])


def regel_prep(c, s):
    form = (s.get('form') or '').replace('AKK', 'Akk').replace('DAT', 'Dat').replace('GEN', 'Gen')
    case = {'Akk': 'AKK', 'Dat': 'DAT', 'Gen': 'GEN'}.get(form.split('+')[-1].strip())
    out = para([f'<b>{c["word"]} {form}</b>'])
    prep = form.split('+')[0].strip()
    if case and prep:
        out += prep_table(prep, case)
    return out


def regel_konnektor(c, mean):
    """The word and its English meaning, then in German: the part of speech with its word order or
    case (Wortart), how it is used (Gebrauch), what it is easily confused with (Achtung); the
    preposition table for prepositions; two more examples. Cells without the German texts show
    their `rule`."""
    r = c.get('regel') or {}
    if r:
        lines = [f"<b>{c['word']}</b>: {mean}", f"<i>Wortart:</i> {r['wortart']}", r.get('gebrauch', '')]
        if r.get('achtung'):
            lines.append(f"<i>Achtung:</i> {r['achtung']}")
    else:
        lines = [f"<b>{c['word']}</b>: {mean}", c.get('rule', '')]
    out = para(lines)
    for case in CONNECTOR_PREP_CASES.get(c['word'], []):
        out += prep_table(c['word'], case)
    ex = c.get('examples') or []
    if ex:
        out += '<ul class="bsp">' + ''.join(f'<li>{e["de"]} <i>{e["en"]}</i></li>' for e in ex) + '</ul>'
    return out


# ── the cards ─────────────────────────────────────────────────────────────────

def cell_label(t, c):
    tid = t['id']
    if tid == 'dekl':
        return f"{c['det']} · {CASE_DE[c['case']]} · {GENDER_DE[c['gender']]}"
    if tid == 'kasus':
        k = c['kind']
        if k == 'pron':
            return f"Pronomen · {CASE_DE[c['case']]}"
        if k == 'frage':
            return f"Fragewort · {CASE_DE[c['case']]}"
        if k == 'prep':
            return f"{c['prep']} · {CASE_DE[c['case']]}"
        if k == 'datv':
            return f"{c['verb']} · Dativ"
        return f"{c['base']} · {CASE_DE[c['case']]}"
    if tid == 'konnektoren':
        return c['word']
    if tid == 'prep_fixed':
        form = (c.get('form') or '').replace('AKK', 'Akk').replace('DAT', 'Dat').replace('GEN', 'Gen')
        return f"{c['word']} {form}".strip()
    return c['id']


def grammar_card(g, t, c, s, by_id):
    """Front: the sentence with one gap per group of answer words, the cue in German
    ([Präposition + unbestimmter Artikel · 2 Wörter]) and the English with the part to translate
    highlighted (vocab_builder/grammar/cue.py). Back: the sentence with the answer marked, and the refresher."""
    tid = t['id']
    satz, ganz, antwort = cue.gapped(s['de'], cue.answer_spans(tid, s))
    en_hl, _ = cue.highlight(tid, c, s, by_id)
    if tid == 'dekl':
        regel = regel_dekl(g, c, s, by_id)
    elif tid == 'kasus':
        regel = regel_kasus(c)
    elif tid == 'konnektoren':
        w = by_id.get(c['word_id'], {})
        regel = regel_konnektor(c, englisch_kurz(w) if w else '')
    else:
        regel = regel_prep(c, s)
    quelle = quelle_of(s)
    fields = dict(Thema=t['name'], Zelle=cell_label(t, c), Satz=satz, SatzEN=cue.html(en_hl or s.get('en', '')),
                  Hinweis=cue.cue(tid, c, s), Antwort=antwort, Ganz=ganz, Regel=regel, Quelle=quelle)
    return fields


def sentence_cards(g, words):
    """[(fields, topic id, key, topic order, cell index)] for every sentence on cards, topics in order."""
    by_id = {w['id']: w for w in words}
    nouns = {re.sub(r'^(der|die|das)\s+', '', w['word']) for w in words if w.get('type') == 'noun'}
    load_noun_forms(nouns | {n for _, n, _ in PREP_NOUNS})
    out = []
    for t in sorted(g['topics'], key=lambda t: t['order']):
        if t.get('status') != 'active':
            continue
        for ci, c in enumerate(t.get('cells', [])):
            for s in gmodel.on_cards(c):
                out.append((grammar_card(g, t, c, s, by_id), t['id'], f"{c['id']}|{s['de']}", t['order'], ci))
    return out


def collocation_cards(words):
    """[(fields, key, word id)]: one card per entry in a word's collocations, EN -> DE. The cue names the
    kinds of words and how many: [unbestimmter Artikel + Nomen + Verb im Infinitiv · 3 Wörter]."""
    cols = [(w, k) for w in words for k in (w.get('collocations') or [])]
    morph = None
    if EX.available():
        morph = EX.Morph()
        morph.load({t.strip('.,;:!?') for _, k in cols for t in k['de'].split()})
    out = []
    for w, k in cols:
        # the answer without the end punctuation ("keine Sorge!" -> keine Sorge)
        ex = k.get('example') or {}
        fields = dict(Kollokation=k['de'].rstrip('.!?'), Englisch=k['en'],
                      Hinweis=cue.collocation_cue(k['de'], morph), Notiz=notiz(k.get('note')),
                      Beispiel=ex.get('de', ''), BeispielEN=ex.get('en', ''))
        out.append((fields, f"{w['id']}|{k['de']}", w['id']))
    return out


def interleave(cards):
    """Order of the grammar cards: topics take turns, and within a topic the cells take turns, so
    the list mixes declension, cases, prepositions and connectors."""
    by_topic = {}
    for n in cards:
        by_topic.setdefault(n[3], {}).setdefault(n[4], []).append(n)
    queues = []
    for order in sorted(by_topic):
        cells = [list(v) for _, v in sorted(by_topic[order].items())]
        q = []
        while any(cells):
            for cl in cells:
                if cl:
                    q.append(cl.pop(0))
        queues.append(q)
    out = []
    while any(queues):
        for q in queues:
            if q:
                out.append(q.pop(0))
    return out


def card_records(g, words):
    """The grammar cards for the grammar pages (grammar_cards.json): per card the front (the sentence
    with its gaps), the cue, the English with the part to translate highlighted (HTML), the answer
    spans of the full sentence, the refresher and the source, in the order of the grammar cards."""
    names = {t['id']: t['name'] for t in g['topics']}
    out = []
    for fields, tid, key, order, ci in interleave(sentence_cards(g, words)):
        cell_id, de = key.split('|', 1)
        t = next(t for t in g['topics'] if t['id'] == tid)
        c = next(c for c in t['cells'] if c['id'] == cell_id)
        s = next(s for s in c['sentences'] if s['de'] == de)
        out.append(dict(topic=tid, topic_name=names[tid], cell=fields['Zelle'], de=de, en=s.get('en', ''),
                        blanks=cue.answer_spans(tid, s), front=fields['Satz'], hint=fields['Hinweis'],
                        en_html=fields['SatzEN'], answer=fields['Antwort'], regel=fields['Regel'],
                        quelle=fields['Quelle']))
    return out
