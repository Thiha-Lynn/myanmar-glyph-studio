#!/usr/bin/env python3
"""Romanized Pali -> Burmese-script Pali, letter-perfect to the canon.

The reader page (web/tipitaka.html) shows the Tipiṭaka in this project's
fonts. Its text comes from SuttaCentral's Mahāsaṅgīti root edition,
which is published in ROMAN script and dedicated to the public domain —
so getting Burmese-script text with clean licensing means writing the
transliteration ourselves rather than copying a Burmese edition.

Burmese Pali orthography is fully regular, which makes this a small,
testable program:

    consonants  k→က kh→ခ … ḷ→ဠ, the geminates ss→ဿ and ññ→ည
    vowels      inherent a; ā→ာ (ါ after ခ ဂ ပ ဝ and the ဒ္ဓ conjunct,
                and only when the cluster carries no medial), i→ိ ī→ီ
                u→ု ū→ူ e→ေ o→ေ+ာ/ါ; independents at word start
    clusters    C₁+virama+C₂ stacks, except: second-member y r v → the
                medials ျ ြ ွ; h after y v m n l ḷ ṇ ñ → ှ; and ṅ before
                a consonant becomes the kinzi င်္
    niggahīta   ṃ (ISO) and ṁ (SuttaCentral) → ံ

Verified, not assumed: run against the Vipassana Research Institute's
own parallel roman/Burmese XML of five canonical books spanning all
three baskets (fetch_tipitaka.py downloads them), it reproduces the
VRI Burmese text for 62,729 of 62,729 aligned words — including the
tall-ာ split this module's TALL_AFTER rule encodes, which was fitted
from that corpus (Pali ဒ takes plain ာ, unlike native Burmese; the ဒ္ဓ
stack takes ါ).

    python3 pali_translit.py "namo tassa bhagavato"
    python3 pali_translit.py --file sutta.txt

Only stdlib is required.
"""

import argparse
import re
import sys

CONSONANTS = {
    "k": "က", "kh": "ခ", "g": "ဂ", "gh": "ဃ", "ṅ": "င",
    "c": "စ", "ch": "ဆ", "j": "ဇ", "jh": "ဈ", "ñ": "ဉ",
    "ṭ": "ဋ", "ṭh": "ဌ", "ḍ": "ဍ", "ḍh": "ဎ", "ṇ": "ဏ",
    "t": "တ", "th": "ထ", "d": "ဒ", "dh": "ဓ", "n": "န",
    "p": "ပ", "ph": "ဖ", "b": "ဗ", "bh": "ဘ", "m": "မ",
    "y": "ယ", "r": "ရ", "l": "လ", "v": "ဝ", "s": "သ",
    "h": "ဟ", "ḷ": "ဠ",
}
INDEPENDENT = {"a": "အ", "ā": "အာ", "i": "ဣ", "ī": "ဤ",
               "u": "ဥ", "ū": "ဦ", "e": "ဧ", "o": "ဩ"}
VOWEL_SIGNS = {"a": "", "i": "ိ", "ī": "ီ", "u": "ု", "ū": "ူ", "e": "ေ"}
MEDIALS = {"y": "ျ", "r": "ြ", "v": "ွ", "h": "ှ"}
H_TAKERS = {"y", "v", "m", "n", "l", "ḷ", "ṇ", "ñ"}
# Letters whose plain form takes the tall ါ — fitted from the canon:
# 195/195 tall after these four, 0 tall anywhere else except ဒ္ဓ.
TALL_AFTER = {"ခ", "ဂ", "ပ", "ဝ"}
VOWELS = set("aāiīuūeo")
KINZI = "င်္"
VIRAMA = "္"

TOKEN = re.compile(
    r"kh|gh|ch|jh|ṭh|ḍh|th|dh|ph|bh|[kgcjṭḍtdpbmyrlvshṅñṇḷn]|[aāiīuūeo]|ṃ")

DIGITS = str.maketrans("0123456789", "၀၁၂၃၄၅၆၇၈၉")


def translit_word(word):
    """One roman Pali word -> Burmese script, or None if it is not Pali."""
    word = word.lower().replace("ṁ", "ṃ")
    tokens = TOKEN.findall(word)
    if "".join(tokens) != word:
        return None
    if not any(t in VOWELS or t == "ṃ" for t in tokens):
        return None            # "SN", "pts" — a citation, not a Pali word
    out = []
    i = 0
    prev_vowel = True          # word start behaves like after a vowel
    last_base = ""             # the cluster's visible letter (stack bottom)
    stack_top = ""             # the letter above it, "" when unstacked
    has_medial = False
    while i < len(tokens):
        tok = tokens[i]
        if tok == "ṃ":
            out.append("ံ")
            prev_vowel = True
            i += 1
            continue
        if tok in VOWELS:
            if prev_vowel:
                out.append(INDEPENDENT[tok])
                last_base, stack_top, has_medial = "အ", "", False
            else:
                tall = (not has_medial
                        and (last_base in TALL_AFTER
                             or (stack_top == "ဒ" and last_base == "ဓ")))
                aa = "ါ" if tall else "ာ"
                if tok == "ā":
                    out.append(aa)
                elif tok == "o":
                    out.append("ေ" + aa)
                else:
                    out.append(VOWEL_SIGNS[tok])
            prev_vowel = True
            i += 1
            continue
        # a consonant; look ahead to see whether it opens a cluster
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        in_cluster = nxt is not None and nxt not in VOWELS and nxt != "ṃ"
        if in_cluster:
            if tok == "ṅ":
                out.append(KINZI)
                prev_vowel = False
                last_base, stack_top, has_medial = "", "", False
                i += 1
                continue
            if (nxt in ("y", "r", "v")
                    or (nxt == "h" and tok in H_TAKERS)):
                # the following consonants are medials on this base
                out.append(CONSONANTS[tok])
                last_base, stack_top, has_medial = CONSONANTS[tok], "", False
                i += 1
                while i < len(tokens) and tokens[i] in ("y", "r", "v", "h"):
                    out.append(MEDIALS[tokens[i]])
                    has_medial = True
                    i += 1
                prev_vowel = False
                continue
            if tok == "s" and nxt == "s":
                out.append("ဿ")            # the geminate has its own letter
                last_base, stack_top, has_medial = "ဿ", "", False
                prev_vowel = False
                i += 2
                continue
            if tok == "ñ" and nxt == "ñ":
                out.append("ည")            # likewise ññ
                last_base, stack_top, has_medial = "ည", "", False
                prev_vowel = False
                i += 2
                continue
            # a true stack: this letter above, the next below
            out.append(CONSONANTS[tok] + VIRAMA)
            stack_top = CONSONANTS[tok]
            i += 1
            below = tokens[i]
            out.append(CONSONANTS[below])
            last_base, has_medial = CONSONANTS[below], False
            i += 1
            while i < len(tokens) and (
                    tokens[i] in ("y", "r", "v")
                    or (tokens[i] == "h" and below in H_TAKERS)):
                out.append(MEDIALS[tokens[i]])
                has_medial = True
                i += 1
            prev_vowel = False
            continue
        out.append(CONSONANTS[tok])
        last_base, stack_top, has_medial = CONSONANTS[tok], "", False
        prev_vowel = False
        i += 1
    return "".join(out)


WORD = re.compile(r"[a-zA-ZāīūṅñṭḍṇḷṃĀĪŪṄÑṬḌṆḶṂṁ]+")


def translit(text):
    """A sentence or paragraph: words transliterated, the rest mapped.

    Sentence punctuation follows the Burmese editions — the full stop
    becomes ။, comma and semicolon become ၊ — and ASCII digits become
    Myanmar digits. Anything unrecognised (quotes, dashes, brackets)
    passes through unchanged, and a word that is not Pali (a reference
    code, a Latin abbreviation) is kept as it came.
    """
    def repl(m):
        burmese = translit_word(m.group(0))
        return burmese if burmese is not None else m.group(0)

    text = WORD.sub(repl, text)
    text = text.replace(".", "။").replace(",", "၊").replace(";", "၊")
    return text.translate(DIGITS)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Transliterate romanized Pali into Burmese script.")
    ap.add_argument("text", nargs="?", help="text to transliterate")
    ap.add_argument("--file", type=argparse.FileType("r", encoding="utf-8"),
                    help="read the text from a file instead")
    args = ap.parse_args(argv)
    if args.file:
        sys.stdout.write(translit(args.file.read()))
    elif args.text:
        print(translit(args.text))
    else:
        ap.error("give TEXT or --file")


if __name__ == "__main__":
    main()
