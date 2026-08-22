"""The transliterator against words whose Burmese spellings are known.

The wide verification runs against the VRI parallel XML (62,729/62,729
words across five books, all three baskets — see pali_translit.py's
docstring); it needs a download, so CI pins the rules with this fixed
table instead. Every rule the module implements has a word here that
fails if the rule breaks.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pali_translit import translit, translit_word  # noqa: E402

KNOWN = [
    # plain CV syllables and independent vowels
    ("namo", "နမော"),
    ("ekaṁ", "ဧကံ"),                          # SC's ṁ normalises to ṃ
    ("isipatane", "ဣသိပတနေ"),
    ("upāli", "ဥပါလိ"),
    # the tall-aa split, fitted from the canon
    ("bhagavā", "ဘဂဝါ"),                      # ဝ takes ါ
    ("pālī", "ပါလီ"),                          # ပ takes ါ
    ("dānaṃ", "ဒာနံ"),                         # Pali ဒ takes PLAIN ာ
    ("buddhā", "ဗုဒ္ဓါ"),                      # …but the ဒ္ဓ stack ါ
    ("gantvā", "ဂန္တွာ"),                      # a medial forces plain ာ
    ("pāmojjaṃ", "ပါမောဇ္ဇံ"),
    # stacks, geminate letters, kinzi
    ("mettā", "မေတ္တာ"),
    ("dhammacakkappavattana", "ဓမ္မစက္ကပ္ပဝတ္တန"),
    ("tassa", "တဿ"),                           # ss is one letter
    ("paññā", "ပညာ"),                          # ññ is one letter
    ("saṅgho", "သင်္ဃော"),                     # ṅ + C = kinzi
    ("kaṅkhā", "ကင်္ခါ"),
    # medials
    ("seyyathā", "သေယျထာ"),                    # second y = ျ
    ("brāhmaṇo", "ဗြာဟ္မဏော"),                 # r = ြ, then hm stacks
    ("tvaṃ", "တွံ"),                            # v = ွ
    ("dve", "ဒွေ"),
    ("mayhaṃ", "မယှံ"),                         # h after y v m n l ḷ ṇ ñ = ှ
    ("jivhā", "ဇိဝှာ"),
    ("amhākaṃ", "အမှာကံ"),
    ("taṇhā", "တဏှာ"),
    ("bhavañhi", "ဘဝဉှိ"),
    ("daḷha", "ဒဠှ"),                           # the fused ဠှ the fonts draw
    ("indriya", "ဣန္ဒြိယ"),                     # stack + medial together
]


@pytest.mark.parametrize("roman,burmese", KNOWN, ids=[r for r, _ in KNOWN])
def test_known_words(roman, burmese):
    assert translit_word(roman) == burmese


def test_sentence_punctuation_and_digits():
    assert (translit("Ekaṁ samayaṁ bhagavā, viharati.")
            == "ဧကံ သမယံ ဘဂဝါ၊ ဝိဟရတိ။")
    assert translit("1. namo") == "၁။ နမော"


def test_non_pali_words_pass_through():
    # reference codes and Latin abbreviations must survive untouched
    assert translit_word("xyz123") is None
    assert translit("SN 56.11 dhammacakka") == "SN ၅၆။၁၁ ဓမ္မစက္က"
