#!/usr/bin/env python3
"""Quick checks after a code change. Run from the repository root:

    python tests/smoke.py

1. the package and its commands still import (vocab_builder.cli, .grammar.cli, .checks, .lexicon);
2. the website's cards (web/data/karten.json, web/js/schema.js) build into a temporary folder and are the
   same as the committed ones;
3. grammar_cards.json is up to date;
4. every stored exercise sentence (words.json) and every grammar sentence (grammar.json) still gets
   the same verdict as recorded in tests/verdicts.json (written the first time, or with --update
   after a change you meant to make);
5. the website tests (tests/web/*.test.js: escaping, answer check, scheduler, learning state, the
   line under a wrong answer, karten.json against words.json, the notes split as on the cards), with
   Node.js (node --test); skipped when Node is not installed.

No network, no API key. Needs private/sources/morphy/dictionary.dump for part 4; without it that part is skipped.
"""
import glob
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
VERDICTS = os.path.join(ROOT, "tests", "verdicts.json")


def step(msg):
    print(f"· {msg}")


def main():
    update = "--update" in sys.argv
    ok = True

    step("imports")
    import vocab_builder.cli  # noqa: F401
    import vocab_builder.grammar.cli  # noqa: F401
    from vocab_builder import checks as EX
    from vocab_builder import lexicon  # noqa: F401
    from vocab_builder.exercises import _spec_form
    from vocab_builder.model import load

    step("web/karten.json and web/js/schema.js")
    from vocab_builder.karten.web import build
    with tempfile.TemporaryDirectory() as tmp:
        web_tmp = os.path.join(tmp, "web")
        try:
            n_entries, n_cards = build(web=web_tmp)
        except SystemExit as e:
            print(f"  !{e}")
            return False
        stale = []
        for f in (os.path.join("data", "karten.json"), os.path.join("js", "schema.js")):
            mine, built = os.path.join(ROOT, "web", f), os.path.join(web_tmp, f)
            if not os.path.exists(mine) or \
                    io.open(mine, encoding="utf-8").read() != io.open(built, encoding="utf-8").read():
                stale.append(f)
        if stale:
            print(f"  ! out of date: {', '.join(stale)}: run  python -m vocab_builder karten  and commit web/data/karten.json and web/js/schema.js")
            ok = False
        else:
            print(f"  up to date ({n_entries} entries, {n_cards} cards)")

    step("grammar_cards.json")
    from vocab_builder.grammar.cli import cards_json
    from vocab_builder.paths import GRAMMAR_CARDS
    current = io.open(GRAMMAR_CARDS, encoding="utf-8").read() if os.path.exists(GRAMMAR_CARDS) else ""
    if current != cards_json():
        print("  ! grammar_cards.json is out of date: run  python -m vocab_builder grammar cards  and commit it")
        ok = False
    else:
        n = current.count('"topic":')
        print(f"  up to date ({n} grammar cards)")

    ok = web_tests() and ok

    if not EX.available():
        step("sentence check skipped: private/sources/morphy/dictionary.dump not found")
        return ok
    step("sentence verdicts")
    db = load()
    morph = EX.Morph()
    morph.load(EX.with_suffixes({t for w in db for e in w.get("exercises", []) for t in EX.toks(e["de"])}))
    now = {}
    for w in db:
        for i, e in enumerate(w.get("exercises", [])):
            res = EX.check(w, e["slot"], _spec_form(w, e["slot"], e.get("form")),
                           {"de": EX.show(e), "en": e.get("en") or "-", "adj": e.get("adj")}, morph)
            now[f"{w['id']}|{i}|{e['slot']}"] = res["status"]
    from vocab_builder.grammar import model as gmodel
    from vocab_builder.grammar.cli import CHECKERS
    g = gmodel.load()
    by_id = {w["id"]: w for w in db}
    for t in g["topics"]:
        mod = CHECKERS.get(t["id"])
        if not mod or not t.get("cells"):
            continue
        morph.load(EX.with_suffixes({tok for c in t["cells"] for x in c["sentences"] for tok in EX.toks(x["de"])}))
        for c in t["cells"]:
            for i, x in enumerate(c["sentences"]):
                now[f"grammar|{c['id']}|{i}"] = mod.check(x, by_id.get(x.get("word_id")), morph, c)[0]
    if update or not os.path.exists(VERDICTS):
        json.dump(now, io.open(VERDICTS, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
        print(f"  {len(now)} verdicts written to tests/verdicts.json")
        return ok
    before = json.load(io.open(VERDICTS, encoding="utf-8"))
    changed = sorted(k for k in set(now) | set(before) if now.get(k) != before.get(k))
    for k in changed[:20]:
        print(f"  ! {k}: {before.get(k)} -> {now.get(k)}")
    print(f"  {len(now)} sentences, {len(changed)} changed")
    return ok and not changed


def web_tests():
    step("website tests")
    node = shutil.which("node")
    if not node:
        print("  skipped: Node.js not found (https://nodejs.org)")
        return True
    files = sorted(glob.glob(os.path.join(ROOT, "tests", "web", "*.test.js")))
    # the notes split by Python (the cards), for tests/web/notizen.test.js to compare with the website
    import re
    from vocab_builder.karten.text import notiz
    from vocab_builder.model import load as load_words
    split = {}
    for w in load_words():
        r = notiz(w.get("notes") or "")
        split[w["id"]] = re.findall(r"<li>(.*?)</li>", r, re.S) if r.startswith("<ul>") else ([r] if r else [])
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "notes_py.json")
        json.dump(split, io.open(path, "w", encoding="utf-8"), ensure_ascii=False)
        r = subprocess.run([node, "--test", *files], capture_output=True, text=True, cwd=ROOT,
                           env={**os.environ, "NOTES_PY": path})
    count = {k: v for k, v in (l[2:].split(" ", 1) for l in r.stdout.splitlines()
                               if l.startswith(("# pass ", "# fail ")))}
    if r.returncode != 0:
        for l in r.stdout.splitlines():
            if l.startswith("not ok") or l.strip().startswith(("error:", "+ ", "- ", "'")):
                print("  ! " + l.strip())
        print(f"  {count.get('pass', '?')} passed, {count.get('fail', '?')} failed: run  node --test tests/web/*.test.js  for details")
        return False
    print(f"  {count.get('pass', '?')} passed")
    return True


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
