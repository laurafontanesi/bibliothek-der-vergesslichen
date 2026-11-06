"""The English of a grammar gap, used to find the part of the translation to highlight (cue.py),
written like this:

    [the friendly social interaction: 3 words] im Team gefällt mir sehr.
    Nächste Woche nehme ich an [a: 1 word] Sprachkurs in Zürich teil.

It is made from what the sentence already holds (the adjective and noun in English for Deklination,
the English sentence for prepositions and connectors). A sentence can set its own with "gap_en".
"""
import re

DET_EN = [  # first word of the gap (lower case, by prefix) -> English
    (('der', 'die', 'das', 'den', 'dem', 'des'), 'the'),
    (('ein',), 'a'),
    (('kein',), 'no'),
    (('mein',), 'my'), (('dein',), 'your (du)'), (('euer', 'eure'), 'your (ihr)'),
    (('unser',), 'our'),
    (('dies',), 'this'), (('jen',), 'that'), (('jed',), 'every'), (('welch',), 'which'),
    (('alle',), 'all'), (('mehrere',), 'several'), (('viele',), 'many'), (('wenige',), 'few'),
    (('zwei',), 'two'), (('drei',), 'three'), (('unzählige',), 'countless'),
]
EXACT_DET = {'der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'einen', 'einem', 'einer', 'eines'}

PRONOUN_EN = {'mich': 'me', 'mir': 'me', 'dich': 'you (du)', 'dir': 'you (du)', 'ihn': 'him', 'ihm': 'him',
              'uns': 'us', 'euch': 'you (ihr)', 'ihnen': 'them'}
QUESTION_EN = {'wer': 'who', 'wen': 'who', 'wem': 'who', 'wessen': 'whose'}
INDEF_EN = {'jemand': 'someone', 'niemand': 'nobody', 'einer': 'one', 'keiner': 'none'}
PREP_EN = {'für': ['for'], 'durch': ['through'], 'gegen': ['against', 'into'], 'ohne': ['without'],
           'um': ['around'], 'aus': ['out of', 'from'], 'bei': ['at', 'with'], 'mit': ['with'],
           'nach': ['after', 'to'], 'seit': ['since', 'for'], 'von': ['from', 'of'], 'zu': ['to'],
           'gegenüber': ['opposite'], 'wegen': ['because of'], 'trotz': ['despite', 'in spite of'],
           'während': ['during'], 'statt': ['instead of'], 'aufgrund': ['because of', 'due to'],
           'innerhalb': ['within', 'inside'], 'außerhalb': ['outside']}
CONTRACTED = {'zum': 'zu', 'zur': 'zu', 'beim': 'bei', 'vom': 'von', 'im': 'in', 'am': 'an', 'ins': 'in'}
IRREGULAR_PL = {'child': 'children', 'person': 'people', 'man': 'men', 'woman': 'women', 'foot': 'feet',
                'tooth': 'teeth', 'mouse': 'mice'}


def gap_text(s):
    a, b = s['blanks'][0]
    return s['de'][a:b]


def n_words(s):
    return sum(len(s['de'][a:b].split()) for a, b in s['blanks'])


def in_sentence(options, en):
    low = ' ' + re.sub(r'[^\w\s\']', ' ', (en or '').lower()) + ' '
    for o in options:
        if f' {o.lower()} ' in low:
            return o
    return None


def det_en(tok, en='', pl=False):
    t = tok.lower()
    if pl and t.startswith('dies'):
        return 'these'
    if pl and t.startswith('jen'):
        return 'those'
    if t.startswith('sein'):
        return in_sentence(['his', 'its'], en) or 'his'
    if t.startswith('ihr'):
        found = in_sentence(['her', 'their', 'your'], en) or ('your' if tok[0] == 'I' else 'her')
        return 'your (Sie)' if found == 'your' else found
    for prefixes, eng in DET_EN:
        if any(t.startswith(p) for p in prefixes) and (eng not in ('the', 'a') or t in EXACT_DET):
            return eng
    return None


def plural(noun):
    words = noun.split()
    last = words[-1]
    if last in IRREGULAR_PL:
        last = IRREGULAR_PL[last]
    elif re.search(r'(s|x|z|ch|sh)$', last):
        last += 'es'
    elif re.search(r'[^aeiou]y$', last):
        last = last[:-1] + 'ies'
    else:
        last += 's'
    return ' '.join(words[:-1] + [last])


def a_or_an(text):
    return re.sub(r'\ba ([aeiouAEIOU])', r'an \1', text)


def dekl(cell, s):
    toks = gap_text(s).split()
    parts = []
    pl = cell.get('gender') in ('pl', 'p')
    d = det_en(toks[0], s.get('en'), pl)
    if d:
        parts.append(d)
    if s.get('adj_en') and s['adj_en'] != d:
        parts.append(s['adj_en'])
    noun = s.get('noun_en') or ''
    if pl and noun:
        last = noun.split()[-1]
        if last.endswith('s') or last in IRREGULAR_PL.values():
            pass                                   # already plural in English
        elif in_sentence([plural(noun)], s.get('en')):
            noun = plural(noun)
        else:
            noun += ' (plural)'
    parts.append(noun)
    return a_or_an(' '.join(p for p in parts if p))


def kasus(cell, s, by_id):
    g = gap_text(s)
    low = g.lower()
    k = cell['kind']
    if k == 'pron':
        return {'Sie': 'you (Sie)', 'sie': 'her', 'sie_pl': 'them', 'es': 'it'}.get(cell['base']) \
            or PRONOUN_EN.get(low, low)
    if k == 'frage':
        return QUESTION_EN.get(low, low)
    if k == 'indef':
        return INDEF_EN.get(cell['base'], cell['base'])
    if k == 'datv':
        if low in PRONOUN_EN or low in ('ihr', 'ihnen'):
            return 'you (Sie)' if g == 'Ihnen' else PRONOUN_EN.get(low, 'her' if low == 'ihr' else low)
        return det_en(g, s.get('en')) or g
    # prep: preposition + article, or a contraction
    toks = low.split()
    prep = CONTRACTED.get(toks[0], toks[0])
    p_en = in_sentence(PREP_EN.get(prep, []), s.get('en')) or (PREP_EN.get(prep) or [prep])[0]
    art = 'the' if toks[0] in CONTRACTED else (det_en(toks[1], s.get('en')) if len(toks) > 1 else '')
    return a_or_an(f'{p_en} {art}'.strip())


def prep_fixed(cell, s):
    return a_or_an(det_en(gap_text(s), s.get('en')) or gap_text(s))


def konnektor(cell, s, by_id):
    w = by_id.get(cell.get('word_id'), {})
    glosses = []
    for d in w.get('definitions', []):
        for x in re.split(r'[,;/]', re.sub(r'\([^)]*\)', '', d.get('meaning') or '')):
            x = x.strip()
            if x and len(x) < 30:
                glosses.append(x)
    glosses.sort(key=len, reverse=True)
    return in_sentence(glosses, s.get('en')) or (glosses[-1] if glosses else 'connector')


def english(topic_id, cell, s, by_id):
    if s.get('gap_en'):
        return s['gap_en']
    if topic_id == 'dekl':
        return dekl(cell, s)
    if topic_id == 'kasus':
        return kasus(cell, s, by_id)
    if topic_id == 'prep_fixed':
        return prep_fixed(cell, s)
    if topic_id == 'konnektoren':
        return konnektor(cell, s, by_id)
    return ''


def bracket(topic_id, cell, s, by_id):
    """The sentence with the gap as [English: n words]."""
    n = n_words(s)
    en = english(topic_id, cell, s, by_id)
    a, b = s['blanks'][0]
    if a == 0 or s['de'][:a].rstrip().endswith(('.', '?', '!')):
        en = en[:1].upper() + en[1:]
    label = f'[{en}: {n} word{"s" if n != 1 else ""}]'
    out = s['de'][:a] + label
    last = b
    for a2, b2 in s['blanks'][1:]:             # any further gap is a plain ___
        out += s['de'][last:a2] + '___'
        last = b2
    return out + s['de'][last:]
