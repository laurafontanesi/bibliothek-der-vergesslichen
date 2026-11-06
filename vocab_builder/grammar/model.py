"""grammar.json: the curriculum and the grammar topics.

Layout:

  structures   one entry per grammar structure of the curriculum (A1 to C1, ids <topic>-<n>), with
               the thread it belongs to, the card type and its status; the name, the English title
               and the rating are private (below).
  threads      structures that come back at several levels share a thread and one refresher.
  topics       what the grammar cards are built from. A topic covers one or more structures, names its cells
               and holds the sentences per cell.

A sentence is a dict like the exercises in words.json (de, en, blanks, plus what the card needs:
adj, adj_en, noun_en for declension), with word / word_id (the lemma it practises), source,
status ("ok" or "check" from the checker) and use (True: on cards; False: kept in reserve).
"""
import io
import json
import os

from ..paths import GRAMMAR

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]


# Fields of a structure that stay private: the names and English titles follow
# the reference checklists (private use only), and the ratings and notes are personal.
# They live in private/personal/grammar_private.json (private/ is not in git); load() puts them back on each structure,
# save() takes them out again, so the tools see whole structures and the public grammar.json has neither.
PRIVATE_FIELDS = ("term", "en", "rating", "have")
from ..paths import GRAMMAR_PRIVATE as PRIVATE  # noqa: E402


def load(path=GRAMMAR, private=PRIVATE):
    if not os.path.exists(path):
        return {"structures": [], "threads": {}, "topics": []}
    g = json.load(io.open(path, encoding="utf-8"))
    if private and os.path.exists(private):
        extra = json.load(io.open(private, encoding="utf-8")).get("structures", {})
        for s in g.get("structures", []):
            for k, v in extra.get(s["id"], {}).items():
                s.setdefault(k, v)
    return g


def save(g, path=GRAMMAR, private=PRIVATE):
    import copy
    pub = copy.deepcopy(g)
    extra = {}
    for s in pub.get("structures", []):
        mine = {k: s.pop(k) for k in PRIVATE_FIELDS if k in s}
        if mine:
            extra[s["id"]] = mine
    if private and extra:
        old = json.load(io.open(private, encoding="utf-8")).get("structures", {}) if os.path.exists(private) else {}
        old.update(extra)
        with io.open(private, "w", encoding="utf-8") as f:
            json.dump({"note": "Private fields of grammar.json (vocab_builder/grammar/model.py): names and English titles (they "
                               "follow reference checklists for private use) and the learner's ratings. Not in git.",
                       "structures": old}, f, ensure_ascii=False, indent=1)
            f.write("\n")
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(pub, f, ensure_ascii=False, indent=1)
        f.write("\n")


def topic(g, tid):
    return next((t for t in g["topics"] if t["id"] == tid), None)


def structure(g, sid):
    return next((s for s in g["structures"] if s["id"] == sid), None)


def cell(t, cid):
    return next((c for c in t["cells"] if c["id"] == cid), None)


def on_cards(c):
    """The sentences of a cell that are on cards."""
    return [s for s in c.get("sentences", []) if s.get("use")]
