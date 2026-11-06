"""
Calls to the Claude API: the API key, the enrichment prompt for a new word, and the raw call.
"""
import json
import os
import re
import urllib.error
from .paths import ENV_PATHS
from .model import TOPICS


MODEL = "claude-sonnet-5-5"


# ── env / api key ──────────────────────────────────────────────────────────────

def load_api_key() -> str | None:
    """Load ANTHROPIC_API_KEY: environment variable first, then the .env files in ENV_PATHS."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"].strip()
    for path in ENV_PATHS:
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


# ── AI enrichment ──────────────────────────────────────────────────────────────

def ai_enrich(word: str, api_key: str, word_type: str = None, context: str = None) -> dict | None:
    """
    Call Claude API to get structured info about a German word.
    Returns a dict with suggested fields, or None on failure.
    The word list is not sent: the model proposes related German words freely, and vocab_builder keeps
    only those already in words.json (cli.confirm_related).
    """
    context_block = ""
    if context:
        context_block = (
            f"\n\nI met this word in this sentence: \"{context}\"\n"
            "Put the meaning the word has IN THIS SENTENCE first in \"definitions\". "
            "Also add three fields: \"context_en\": an English translation of my sentence; "
            "\"context_ok\": true if my sentence is correct, natural German, else false; "
            "\"context_fix\": the corrected sentence if context_ok is false, else null. "
            "Your two \"examples\" should show other uses than my sentence.")
    topic_lines = "\n".join(f"- {t}: {d}" for t, d in TOPICS.items())
    type_hint = f"\n\nIMPORTANT: Treat this word strictly as a {word_type}. Fill in all fields accordingly." if word_type else ""
    prompt = f"""You are a German language expert. I am learning German and want to add the word "{word}" to my vocabulary database.

Please analyse this word and return a JSON object with the following fields. Be precise and use only English for definitions and translations (never another language in the meaning field).

Return ONLY valid JSON, no explanation, no markdown, no code fences.{type_hint}

{{
  "word": "the word in its canonical form (e.g. with gender for nouns: 'die Sehnsucht', infinitive for verbs: 'erinnern'; reflexive verbs MUST include 'sich': 'sich erinnern'; adjectives in the base form without ending: 'bedingt', not 'bedingte'; a verb with a fixed preposition is the verb alone, 'zählen', with the preposition in the \"preposition\" field, never 'zählen auf')",
  "type": "one of: noun, verb, adj/adv, prep/conj, expression, construction, other",
  "usage": "for adj/adv: adjective only, adverb only, or both; for prep/conj: preposition only, conjunction only, or both — else null",
  "gender": "der/die/das — only for nouns, else null",
  "plural": "plural form with article e.g. 'die Sehnsüchte' — only for nouns, else null",
  "auxiliary": "haben or sein — only for verbs, else null",
  "past_tense": "simple past (Präteritum) e.g. 'erinnerte' — only for verbs, else null",
  "past_participle": "e.g. 'erinnert' — only for verbs, else null",
  "present_3sg": "er/sie/es form in the present, in the same format as past_tense, e.g. 'nimmt mit', 'freut sich' — only for verbs, else null",
  "verb_class": "regular (weak: kaufte, gekauft), irregular (strong: nahm, genommen) or mixed (weak endings with a changed stem: dachte, gedacht) — only for verbs, else null",
  "is_separable": true or false — only for verbs, else null,
  "reflexive": "akk" if the reflexive pronoun is accusative (ich freue mich), "dat" if dative (ich nehme mir etwas vor), false if the verb is not reflexive. Only verbs that cannot drop sich, or whose meaning changes with sich, are reflexive; waschen (sich waschen = wash oneself) is NOT. Only for verbs, else null,
  "preposition": "the fixed preposition with its case, of a verb (denken: 'an + AKK'), a noun (die Angst: 'vor + DAT') or an adjective (stolz: 'auf + AKK'); several separated by ' / ' (sich freuen: 'auf + AKK / über + AKK'); only real prepositional objects that belong to the word, not places or times; else null",
  "family_root": "the root verb — for compounds e.g. 'nehmen' for 'mitnehmen'; for root verbs use the word itself e.g. 'schlafen' for 'schlafen' (never null for verbs)",
  "prefix": "the prefix e.g. 'mit-' for 'mitnehmen', else null",
  "definitions": [
    {{"meaning": "primary English meaning", "note": "optional note e.g. 'used with an + AKK' or null"}},
    {{"meaning": "secondary meaning if exists", "note": null}}
  ],
  "examples": [
    {{"de": "A natural German example sentence", "en": "English translation"}},
    {{"de": "A second example showing a different use", "en": "English translation"}}
  ],
  (for a separable verb, one of the two examples uses the infinitive, with zu or a modal verb: "Ich muss morgen früh aufstehen.")
  "compound_parts": "for a compound noun or adjective, its parts in order as a list, nouns with article, linking elements as separate items: [\"die Kündigung\", \"-s-\", \"die Frist\"]; null if not a compound",
  "topics": ["0 to 2 topics from the list below, ONLY if the word is clearly about that domain; core vocabulary like brauchen or bekommen gets an empty list"],
  "notes": "one sentence max — only if there is something genuinely important to note, e.g. easy confusion with another word, or a non-neutral register (umgangssprachlich, gehoben, Schweizerdeutsch), or null",
  "related": [
    {{"word": "a related German word, as a dictionary headword (nouns with article)", "kind": "one of: synonym, antonym, contrast, derived, compound"}}
  ]
}}

"related" kinds: synonym = same meaning; antonym = opposite; contrast = easily confused,
worth telling apart (e.g. kennen / wissen); derived = same stem, different word class
(e.g. wählen / die Wahl); compound = one word is a part of the other (der Staub / der Staubsauger,
das Bild / der Bildschirm). Up to 10 words, the most useful for a B1/B2 learner first; only words
with a real relationship; no verb-family members (same root, different prefix) unless they are
genuinely confusable in meaning.

Topics (use the names exactly as written). Rules: 0 to 2 topics; the FIRST definition
decides; a secondary meaning earns a topic only if one of your example sentences
illustrates it; core vocabulary gets an empty list, which is the correct answer for
words like brauchen, bekommen, liegen, nötig.
{topic_lines}

Word to analyse: {word}{type_hint}{context_block}"""

    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 1500,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
            raw = data["content"][0]["text"].strip()
            raw = re.sub(r'^```[a-z]*\n?', '', raw)
            raw = re.sub(r'\n?```$', '', raw)
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        print(f"  ✗ API error {e.code}: {e.read().decode()}")
        return None
    except Exception as e:
        print(f"  ✗ Could not reach API: {e}")
        return None


def call_claude(prompt: str, api_key: str, max_tokens: int = 2000) -> str | None:
    """Plain text answer from the API, or None (the reason is printed)."""
    payload = json.dumps({"model": MODEL, "max_tokens": max_tokens,
                          "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=payload, headers={
        "Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())["content"][0]["text"]
    except urllib.error.HTTPError as e:
        print(f"  ✗ API error {e.code}: {e.read().decode()}")
    except Exception as e:
        print(f"  ✗ Could not reach API: {e}")
    return None
