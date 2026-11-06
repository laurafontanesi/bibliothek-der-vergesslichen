"""The full-form lexicon (private/sources/morphy/dictionary.dump, not in git: README, "Data sources") and the
sentence checker that needs it. Without it vocab_builder can still list, show and edit words, but says
so where it skips the lexicon checks and the exercise sentences; the website's cards
(vocab_builder karten) and the smoke test's sentence check need it and stop or say so."""
try:                                   # full-form lexicon, see README "Data sources"
    from .lexicon import Lexicon, changes_stem, german_definition
    LEXICON = Lexicon()
except ImportError:
    Lexicon = changes_stem = german_definition = None
    LEXICON = None

try:                                   # exercise sentences: needs private/sources/morphy/dictionary.dump as well
    from . import checks as EX
    EX_OK = EX.available()
except ImportError:
    EX, EX_OK = None, False

MORPHY_OK = bool(LEXICON and LEXICON.ok)
MISSING = "private/sources/morphy/dictionary.dump is missing (README, \"Data sources\", says how to make it)"


def require_morphy(what):
    """Stop with a clear message when the lexicon is missing and `what` cannot work without it."""
    if not MORPHY_OK:
        raise SystemExit(f"  {what} needs the full-form lexicon: {MISSING}.")


def warn_morphy(what):
    """Say once that `what` is skipped because the lexicon is missing."""
    if not MORPHY_OK:
        print(f"  Note: {MISSING}: {what} skipped.")
