"""Keep the typed `related` links in words.json consistent (python -m vocab_builder links).

`related` is a list of {"word": ..., "kind": ...} with kind in schema.json ("related_kinds"). Verb
families are NOT stored here; they are already encoded by `family_root`. This:
  1. drops links whose target is not in the database
  2. makes every link bidirectional, copying the kind
  3. reports words that have no links at all (so you can add some)
"""
import re

from .model import RELATED_KINDS

KINDS = set(RELATED_KINDS)
ORDER = ['contrast', 'antonym', 'synonym', 'derived', 'compound']   # the order of the links in words.json


def normalise(word):
    return re.sub(r'^(der|die|das|sich)\s+', '', word.lower().strip()).strip()


def fix(db):
    """Repair the links of all entries in place and print what changed."""
    by_word = {w['word']: w for w in db}
    by_norm = {normalise(w['word']): w for w in db}

    dropped, added = [], []
    for w in db:
        clean = []
        for r in w.get('related', []):
            tgt = by_word.get(r.get('word', '')) or by_norm.get(normalise(r.get('word', '')))
            if not tgt or tgt['id'] == w['id'] or r.get('kind') not in KINDS:
                dropped.append((w['word'], r.get('word'))); continue
            clean.append({'word': tgt['word'], 'kind': r['kind']})
        w['related'] = clean

    # Some spellings belong to two entries (vermessen: verb and adjective). A link
    # to such a spelling counts as mirrored if ANY entry with that spelling links back;
    # if none does, the back-link is NOT guessed but reported for a manual decision.
    all_by_word = {}
    for w in db:
        all_by_word.setdefault(w['word'], []).append(w)
    ambiguous = []
    for w in db:
        for r in w['related']:
            targets = all_by_word[r['word']]
            if any(w['word'] in {x['word'] for x in t['related']} for t in targets):
                continue
            if len(targets) > 1:
                ambiguous.append((w['word'], r['word'])); continue
            tgt = targets[0]
            tgt['related'].append({'word': w['word'], 'kind': r['kind']})
            added.append((tgt['word'], w['word'], r['kind']))

    for w in db:
        w['related'].sort(key=lambda x: (ORDER.index(x['kind']), x['word']))

    lonely = [w['word'] for w in db if not w['related']]
    print(f'  {len(db)} entries')
    print(f'  {len(dropped)} dangling links dropped')
    for a, b in dropped[:20]:
        print(f'      {a}  ->  {b}')
    print(f'  {len(added)} back-links added')
    for a, b in ambiguous:
        print(f'  ! {a} -> {b}: "{b}" is two entries; add the back-link by hand to the right one')
    print(f'  {len(lonely)} words without any related link')

    return len(dropped) + len(added)
