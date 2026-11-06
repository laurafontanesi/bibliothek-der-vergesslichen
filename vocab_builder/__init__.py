"""
vocab_builder: the tools behind the website data (python -m vocab_builder help lists the commands).

  paths       where everything is (web/data/, private/)
  model       words.json: load, save, ids, topics, links, families
  lexicon     Morphy full-form lexicon and German Wiktionary
  checks      the sentence checker, which exercises a word gets, generation prompts
  deps        optional parts (lexicon, checker) loaded once
  claude      Claude API calls
  ui          terminal questions and printing
  exercises   filling and checking the exercises of a word
  cli         the vocab_builder commands
  karten/     the website's cards, web/data/karten.json (config, text, word_cards, grammar_cards, web)
  schema      the lists shared with the website (schema.json)

Started with python -m vocab_builder (__main__.py): the word commands in cli.py, the grammar commands
in grammar/cli.py.
"""
