"""
Text helpers for the cards: notes, principal parts, English meanings, hiding the word.
"""
from ..lexicon import changes_stem
import re
from .config import PUNCT


# ── small helpers ─────────────────────────────────────────────────────────────


def bare(word):
    return re.sub(r'^(der|die|das|sich)\s+', '', (word or '')).strip()


def ausfuellen_html(cue):
    """The "Bitte ausfüllen" box, for a cue that lives inside another field (Produzieren)."""
    return ('<div class="ausfuellen"><span class="aus-label">Bitte ausfüllen</span>'
            f'<span class="aus-cue">{cue}</span></div>')


# words ending in a full stop that do not end a sentence
ABBREVIATIONS = {'jmdn', 'jmdm', 'jmds', 'jdn', 'jdm', 'jds', 'etw', 'bzw', 'usw', 'ugs', 'geh', 'vs', 'ca',
                 'Akk', 'Dat', 'Gen', 'Nom', 'Pl', 'Sg', 'Präp', 'Adj', 'Adv', 'e.g', 'i.e', 'etc', 'z', 'B', 'd',
                 'h', 'o', 'Ä', 'sth', 'sb', 'lit', 'approx', 'Nr', 'St', 'Dr', 'Hr', 'Fr'}


def notiz(text):
    """A note with several points as a bullet list: a new point after each ";" and after each
    full stop, both only outside brackets, so "Auszug (moving out; statement)"
    stays together, and not after an abbreviation (jmdn., etw., z. B.)."""
    text = (text or '').strip()
    parts, depth, cur = [], 0, ''
    for i, ch in enumerate(text):
        if ch in '([':
            depth += 1
        elif ch in ')]' and depth:
            depth -= 1
        if depth == 0 and ch == ';':
            parts.append(cur)
            cur = ''
            continue
        cur += ch
        if depth == 0 and ch == '.' and text[i + 1:i + 2] == ' ':
            last = re.findall(r'([\wäöüÄÖÜß.]+)\.$', cur)
            if not (last and (last[0] in ABBREVIATIONS or len(last[0]) == 1)):
                parts.append(cur)
                cur = ''
    parts = [x.strip() for x in parts + [cur] if x.strip()]
    if len(parts) < 2:
        return text
    return '<ul>' + ''.join(f'<li>{x}</li>' for x in parts) + '</ul>'


def strip_punct(tok):
    return tok.strip(PUNCT)


def blank_phrase(sentence, phrase):
    """Replace phrase with a gap, one gap per word it contained."""
    gap = ' '.join(['___'] * len(phrase.split()))
    return sentence.replace(phrase, gap, 1)


# ── the three descriptive fields ──────────────────────────────────────────────


def stammformen(w):
    """'meiden, mied, hat gemieden'; reflexive: 'sich freuen, freute sich, hat sich gefreut'. With a
    stem change the er-form comes last, on a line of its own on the card:
    'nehmen, nahm, hat genommen' and below it 'er nimmt, nimm!' (the imperative too, when the
    word has one); the voice reads all of it, with a pause.
    '' for other words."""
    if w.get('type') != 'verb' or not w.get('past_tense') or not w.get('past_participle'):
        return ''
    out = [w['word'], w['past_tense']]
    aux = {'haben': 'hat', 'sein': 'ist'}.get(w.get('auxiliary'), 'hat')
    out.append(aux + (' sich ' if w.get('reflexive') else ' ') + w['past_participle'])
    html = ', '.join(out)
    # the second line: the er-form when the stem changes, then the imperative
    second = []
    if changes_stem(w['word'], w.get('present_3sg'), w.get('prefix'), w.get('is_separable')):
        second.append('er ' + w['present_3sg'])
    if w.get('imperative'):
        second.append(w['imperative'] + '!')
    if second:
        html += '<span class="praes"><span class="komma">, </span>' + ', '.join(second) + '</span>'
    return html


GAP = '<span class="gap">___</span>'
SMALL = {'auf', 'an', 'aus', 'bei', 'für', 'mit', 'nach', 'über', 'um', 'von', 'vor', 'zu', 'in', 'ab', 'ein',
         'der', 'die', 'das', 'den', 'dem', 'des', 'sich', 'etw', 'jmdn', 'jmdm', 'jdn', 'jdm', 'es'}


def word_forms(w):
    """Lower-case spellings of the word itself (endings included), to hide it on the English side."""
    base = re.sub(r'^(sich|der|die|das)\s+', '', w['word'].strip(), flags=re.I)
    toks = [t for t in re.findall(r"[\wäöüß]+", base.lower()) if t not in SMALL and len(t) > 2]
    for k in ('past_tense', 'past_participle', 'present_3sg', 'imperative', 'plural'):
        for v in re.split(r'[\s/,]+', str(w.get(k) or '').lower()):
            if len(v) > 2 and v not in SMALL and v != '-':
                toks.append(v.lstrip('-'))
    forms = set(toks)
    for v in re.split(r'[\s/,]+', str(w.get('plural') or '').lower()):     # dative plural: Aufzügen
        if len(v) > 2 and v not in SMALL and not v.endswith(('n', 's')):
            forms.add(v + 'n')
    t = w.get('type')
    for tok in toks[:1] if toks else []:
        if t == 'verb':
            pfx = (w.get('prefix') or '').strip('-').lower() if w.get('is_separable') else ''
            stems = {re.sub(r'e?n$', '', tok)}
            if pfx and tok.startswith(pfx):
                stems.add(re.sub(r'e?n$', '', tok[len(pfx):]))
                forms.add(pfx + 'zu' + tok[len(pfx):])
            for st in stems:
                forms |= {st + e for e in ('', 'e', 'st', 't', 'en', 'et', 'est', 'te', 'test', 'ten', 'tet', 'end')}
        elif t == 'noun':
            forms |= {tok + e for e in ('s', 'es', 'n', 'en', 'e', 'er', 'ern')}
        else:
            forms |= {tok + e for e in ('e', 'en', 'er', 'es', 'em')}
            if tok.endswith('e'):                                   # gerne / gern
                forms.add(tok[:-1])
    return {f for f in forms if len(f) > 2}


def hide_word(text, forms):
    """The word, its forms, and the word inside a longer word (krankheits___, Regen___, die ___in)."""
    longer = sorted((f for f in forms if len(f) >= 4), key=len, reverse=True)

    def rep(m):
        t = m.group()
        low = t.lower()
        if low in forms:
            return GAP
        for f in longer:
            i = low.find(f)
            if i >= 0 and len(low) > len(f) + 1:
                return t[:i] + GAP + t[i + len(f):]
        return t
    return re.sub(r"[\wäöüß]+", rep, text)


def englisch_frage(w, ask_prep=False, tilde=False):
    """Englisch for the Produzieren front: the German word itself is hidden (___) where it appears in
    a German phrase of a meaning ("den Tisch decken: to set the table") or in a note
    ("e.g. Ich bin gerade zurückgekommen"). Plain English meanings are left alone (stehen: "to stand").

    tilde: the hidden word is shown as ~, the dictionary sign for the headword, so a
    pattern (~ für + AKK) does not look like a gap to fill. ask_prep: the answer asks for the
    preposition and case, so the notes and German phrases that name them are left out."""
    forms = word_forms(w)
    defs = w.get('definitions', [])
    prep = (w.get('preposition') or '').split('+')[0].strip().lower()
    names_case = re.compile(r'\b(AKK|DAT|GEN|NOM|dative|accusative|genitive)\b', re.I)

    def gives_away(t):
        low = t.lower()
        return bool(names_case.search(t)) or (prep and re.search(r'\b' + re.escape(prep) + r'\b', low) and
                                                any(f in low for f in forms))
    lines = []
    for i, d in enumerate(defs, 1):
        m = (d.get('meaning') or '').strip()
        sep = re.search(r'\s[—–]\s|:\s|\s=\s', m)
        if sep:
            german = m[:sep.start()]
            if ask_prep and gives_away(german):
                m = m[sep.end():]
            else:
                m = hide_word(german, forms) + m[sep.start():]
        n = d.get('note')
        if ask_prep and n and gives_away(n):
            n = None
        lines.append((f'{i}. ' if len(defs) > 1 else '')
                     + m + (f' <i>({hide_word(n, forms)})</i>' if n else ''))
    out = '<br>'.join(lines)
    return out.replace(GAP, '~') if tilde else out


def not_meant_list(w, ctx):
    """Other words in the list with the same short English answer, or linked as synonyms
    (der Aufzug / der Fahrstuhl)."""
    if 'kurz_index' not in ctx:
        idx = {}
        for x in ctx['by_word'].values():
            k = englisch_kurz(x).lower()
            if k:
                idx.setdefault((x.get('type'), k), []).append(x['word'])
        ctx['kurz_index'] = idx
    alts = [r['word'] for r in w.get('related', []) if isinstance(r, dict) and r.get('kind') == 'synonym'
            and ctx['by_word'].get(r['word'], {}).get('type') == w.get('type')]
    k = englisch_kurz(w).lower()
    alts += ctx['kurz_index'].get((w.get('type'), k), []) if k else []
    return [a for a in dict.fromkeys(alts) if a != w['word']]


def not_meant(w, ctx):
    """The English side names the words not meant, so it is clear which word is asked."""
    alts = not_meant_list(w, ctx)
    if not alts:
        return ''
    return ('<div class="nicht">nicht: '
            + ', '.join(alts) + '</div>')


def englisch_kurz(w):
    """One short, typeable answer: first meaning, first alternative."""
    m = ''
    for d in w.get('definitions', []):
        m = (d.get('meaning') or '').strip()
        if m:
            break
    if not m:
        return ''
    m = re.sub(r'\s*\([^)]*\)?\s*$', '', m)
    m = re.sub(r'\s*\([^)]*\)\s*', ' ', m)
    m = re.split(r'\s+[—–-]\s+', m)[0]
    if ': ' in m:                                 # "sich fügen: to comply" -> the English part
        m = m.split(': ', 1)[1]
    m = re.split(r'[,;/]|\s+or\s+', m)[0].strip()
    if w.get('type') in ('verb', 'expression', 'construction'):
        m = re.sub(r'^to\s+', '', m, flags=re.I)
    elif w.get('type') == 'noun':
        m = re.sub(r'^(the|a|an)\s+', '', m, flags=re.I)
    m = m.replace('…', '...')
    m = re.sub(r'\s*\.\.\.\s*', ' ... ', m)       # one consistent spacing
    return re.sub(r'\s{2,}', ' ', m).strip()


def quelle(item):
    """The credit line of a sentence from Tatoeba (CC BY 2.0 FR: each sentence is attributed by its id
    and a link to its page), with the English when it is Tatoeba's translation too (`en_source`);
    empty for our own sentences. `item` is an exercise or a grammar sentence."""
    import re as _re
    m = _re.search(r'tatoeba:(\d+)', item.get('source') or '')
    if not m:
        return ''
    link = lambda i: f'<a href="https://tatoeba.org/en/sentences/show/{i}">#{i}</a>'
    out = f'Satz von Tatoeba {link(m.group(1))}'
    e = _re.search(r'tatoeba:(\d+)', item.get('en_source') or '')
    if e:
        out += f', Übersetzung {link(e.group(1))}'
    return out + ' (CC BY 2.0 FR)'
