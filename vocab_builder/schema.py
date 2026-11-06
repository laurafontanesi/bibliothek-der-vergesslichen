"""The lists shared by Python and the website, from web/data/schema.json: the levels,
the word types, the kinds of related word and the topics (with the definitions the AI sees). The
website gets them as web/js/schema.js, written by python -m vocab_builder karten and
checked by the smoke test, so a list is changed in one place only."""
import io
import json
import os

from .paths import SCHEMA
_cache = None


def load():
    global _cache
    if _cache is None:
        with io.open(SCHEMA, encoding="utf-8") as fh:
            _cache = json.load(fh)
    return _cache


def js():
    """web/js/schema.js: the same lists as JavaScript constants, with their German names."""
    s = load()
    dump = lambda x: json.dumps(x, ensure_ascii=False)
    lv = s["levels"]
    return "\n".join([
        "// Generated from schema.json by the build (vocab_builder/schema.py, python -m vocab_builder karten).",
        "// Do not edit here: change schema.json and build again; the smoke test checks they agree.",
        f"export const LEVELS = {dump(lv['goethe'] + [lv['above']])};",
        f"export const TYPE_DE = {dump(s['word_types'])};",
        f"export const KIND_DE = {dump(s['related_kinds'])};",
        f"export const KIND_ORDER = {dump(list(s['related_kinds']))};",
        f"export const TOPIC_DE = {dump({k: v['de'] for k, v in s['topics'].items()})};",
        "",
    ])


def write_js(web):
    path = os.path.join(web, "js", "schema.js")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(js())
    return path
