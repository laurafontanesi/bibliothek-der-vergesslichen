"""
Fixed settings of the cards: the fields of an exercise card and word lists.
"""

# the fields of every exercise card: <key>_Frage, <key>_Antwort, ...
SLOTS = ['Frage', 'Antwort', 'Ganz', 'GanzEN', 'Hinweis', 'Quelle']

# The principal parts of a verb (meiden, mied, hat gemieden), shown and read aloud on the backs of
# Bedeutung and Produzieren.
STAMMFORMEN_FIELD = 'Stammformen'

ARTICLES = {'der', 'die', 'das', 'den', 'dem', 'des',
            'ein', 'eine', 'einen', 'einem', 'einer', 'eines'}
POSSESSIVES = {'mein', 'meine', 'meinen', 'meinem', 'meiner',
               'sein', 'seine', 'seinen', 'seinem', 'seiner',
               'ihr', 'ihre', 'ihren', 'ihrem', 'ihrer',
               'kein', 'keine', 'keinen', 'keinem', 'keiner',
               'dieser', 'diese', 'dieses', 'diesen', 'diesem'}
DETERMINERS = ARTICLES | POSSESSIVES
PUNCT = '.,:;!?»«""„“()'
