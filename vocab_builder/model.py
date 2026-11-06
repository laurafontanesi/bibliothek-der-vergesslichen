"""
The word list: loading and saving words.json, ids, topics, related-word links,
families and words related by their spelling. No user interaction here.
"""
import json
import os
import re
from .paths import WORDS


VERB_CLASSES = ["regular", "irregular", "mixed"]


def norm_reflexive(v):
    """Reflexive is "akk", "dat" or False. Accepts booleans and typed answers."""
    if v in (None, False, "", "no", "n", "false", "False", "—", "-"):
        return False
    v = str(v).strip().lower()
    if v.startswith("d"):
        return "dat"
    if v.startswith(("a", "y", "t")):          # akk, yes, true -> accusative (the usual case)
        return "akk"
    return False


def reflexive_label(v):
    return {"akk": "sich + Akk.", "dat": "sich + Dat."}.get(norm_reflexive(v), "")

from .schema import load as _schema   # noqa: E402  (the lists shared with the website: schema.json)

WORD_TYPES = list(_schema()["word_types"])
GENDERS    = ["der", "die", "das"]
# Closed list of topics. A word gets 0 to 2 of them, and only when it is clearly
# ABOUT the domain. Core vocabulary (brauchen, bekommen, liegen) has no topic;
# "no topic" is a deliberate answer, not a gap. The FIRST definition decides; a
# secondary meaning earns a topic only if one of the examples illustrates it.
# The definitions below are what the model sees, so keep the exclusions sharp.
# The definitions are in schema.json ("topics"), with the German names the website shows.
TOPICS = {k: v["definition"] for k, v in _schema()["topics"].items()}


def clean_topics(raw) -> list:
    """Keep only topics from the closed list, in canonical order, max 2."""
    if isinstance(raw, str):
        raw = [t.strip() for t in raw.split(",")]
    wanted = {str(t).strip().lower() for t in (raw or [])}
    return [t for t in TOPICS if t in wanted][:2]


def family_members(words: list, verb: dict) -> list:
    """Verbs in the dictionary whose root verb is `verb` (aufräumen, einräumen for räumen)."""
    if verb.get("type") != "verb":
        return []
    root = re.sub(r"^sich\s+", "", verb["word"]).strip()
    return [w for w in words if w is not verb and w.get("type") == "verb"
            and re.sub(r"^sich\s+", "", (w.get("family_root") or "")).strip() == root
            and re.sub(r"^sich\s+", "", w["word"]).strip() != root]


# ── helpers ────────────────────────────────────────────────────────────────────

def load() -> list:
    if not os.path.exists(WORDS):
        return []
    with open(WORDS, encoding="utf-8") as f:
        return json.load(f)

def save(words: list):
    with open(WORDS, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Saved — {len(words)} entries in database.")

def make_id(word: str) -> str:
    word = word.lower().strip()
    word = re.sub(r'[äöü]', lambda m: {'ä':'ae','ö':'oe','ü':'ue'}[m.group()], word)
    word = re.sub(r'ß', 'ss', word)
    word = re.sub(r'[^a-z0-9]+', '-', word)
    return word.strip('-')

def find(words: list, query: str):
    q = query.lower().strip()
    for w in words:
        if w["word"].lower() == q or w["id"] == make_id(query):
            return w
    return None



# ── related word linking ───────────────────────────────────────────────────────

def normalise(word: str) -> str:
    w = word.lower().strip()
    w = re.sub(r"^(der|die|das|sich|ein|eine|einen|einem)\s+", "", w)
    return w.strip()

RELATED_KINDS = list(_schema()["related_kinds"])

def related_words(entry: dict) -> set:
    return {r["word"] for r in entry.get("related", []) if isinstance(r, dict)}

def make_bidirectional(words: list, entry: dict) -> int:
    """Ensure every link from `entry` also exists on the target, with the same kind."""
    updated = 0
    by_word = {w["word"]: w for w in words}
    for r in entry.get("related", []):
        tgt = by_word.get(r["word"])
        if not tgt or tgt["id"] == entry["id"]:
            continue
        if entry["word"] not in related_words(tgt):
            tgt.setdefault("related", []).append({"word": entry["word"], "kind": r["kind"]})
            updated += 1
    return updated


# ── words related by their spelling (proposals for vocab_builder add) ─────────────

_FOLD = str.maketrans("äöüß", "aous")


def _stem(word: str) -> str:
    return re.sub(r"^(der|die|das|sich)\s+", "", (word or "").lower().strip()).translate(_FOLD)


def form_candidates(words: list, entry: dict, limit: int = 10) -> list:
    """Words of the database that look related by their spelling, as proposals for `related`, found
    without the AI: in the same word class one at the start or end of the other (das Bild / der
    Bildschirm: compound); in another word class the same beginning (wählen / die Wahl: derived).
    Verbs of one family (nehmen / mitnehmen) are left out: family_root links them already. Only
    proposals: you confirm each one."""
    n, out = _stem(entry["word"]), []
    if len(n) < 4 or " " in n:
        return out
    for w in words:
        o = _stem(w["word"])
        if w is entry or o == n or len(o) < 4 or " " in o:
            continue
        same_type = w.get("type") == entry.get("type")
        short_, long_ = sorted((o, n), key=len)
        if same_type and w.get("type") != "verb" and len(long_) - len(short_) >= 3 \
                and (long_.startswith(short_) or long_.endswith(short_)):
            out.append({"word": w["word"], "kind": "compound"})       # das Bild / der Bildschirm
            continue
        if not same_type:                                             # wählen / die Wahl
            k = 0
            while k < len(short_) and o[k] == n[k]:
                k += 1
            if k >= 4 and k >= min(5, len(short_) - 1):
                out.append({"word": w["word"], "kind": "derived"})
    return out[:limit]
