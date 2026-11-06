"""Where things are. Every path in the package comes from here.

  web/data/          the published data: words.json, grammar.json, schema.json and the generated
                     karten.json and grammar_cards.json
  private/sources/   downloads from others (Morphy, DWDS, Wiktionary, Tatoeba, ...), never in git
  private/personal/  personal files (the private fields of grammar.json, notes, where the API key is), never in git
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
PUBLIC = os.path.join(WEB, "data")
PRIVATE = os.path.join(ROOT, "private")
SOURCES = os.path.join(PRIVATE, "sources")
PERSONAL = os.path.join(PRIVATE, "personal")

WORDS = os.path.join(PUBLIC, "words.json")
GRAMMAR = os.path.join(PUBLIC, "grammar.json")
GRAMMAR_CARDS = os.path.join(PUBLIC, "grammar_cards.json")   # generated: python -m vocab_builder grammar cards
SCHEMA = os.path.join(PUBLIC, "schema.json")
GRAMMAR_PRIVATE = os.path.join(PERSONAL, "grammar_private.json")
MORPHY = os.path.join(SOURCES, "morphy", "dictionary.dump")
WIKTIONARY = os.path.join(SOURCES, "wiktionary", "de-extract.jsonl")

# The API key for `add`: the ANTHROPIC_API_KEY environment variable, or a .env file. Where that
# file is can be written in private/personal/api_env.txt (one line, a path relative to the
# repository folder or absolute), so the key can live outside the repository. A .env in the
# repository folder works too (it is in .gitignore).
def _env_paths():
    out, cfg = [], os.path.join(PERSONAL, "api_env.txt")
    if os.path.exists(cfg):
        with open(cfg, encoding="utf-8") as f:
            line = f.readline().strip()
        if line:
            out.append(os.path.normpath(os.path.join(ROOT, os.path.expanduser(line))))
    return out + [os.path.join(ROOT, ".env")]


ENV_PATHS = _env_paths()
