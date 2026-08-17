#!/usr/bin/env python3
"""Generate the data behind web/showcase.html.

The showcase answers one question a proof sheet cannot: *does the font we
generated from sketches actually render Burmese the way Burmese is
written?* So every row on that page carries its own evidence — which
shaping rule fired, which glyphs came out, and how far the result sits
from Padauk, the font the outlines were traced over.

    python3 make_showcase.py                       # -> web/data/showcase.js
    python3 make_showcase.py --font MyFont.ttf --reference Padauk-Regular.ttf

The comparison is by MEASUREMENT, never by glyph name. Two fonts solve
the same cluster with differently-named glyphs — our ကြု is
`uni103C.u.wide` plus a zero-width ghost, Padauk's is a single
`uni103C102F.wide` — and a name diff would scream about a difference no
reader can see. What a reader sees is the advance and the ink, so that
is what gets compared, in units of a 1000 em.

Dependencies: fontTools, uharfbuzz  (pip install -r requirements.txt)
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repo_paths import repo_root  # noqa: E402

try:
    import uharfbuzz as hb
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.ttLib import TTFont
except ImportError as exc:                                  # pragma: no cover
    sys.exit(f"Missing dependency ({exc}).  pip install fonttools uharfbuzz")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FONT = ROOT / "projects" / "myanmar-glyph-sans" / \
    "MyanmarGlyphSans-Regular.ttf"
DEFAULT_REFERENCE = ROOT / "web" / "fonts" / "Padauk-Regular.ttf"
DEFAULT_OUT = ROOT / "web" / "data" / "showcase.js"

# A row differs enough to be worth a human's eye when any edge of the ink,
# or the advance, is this far from the reference. 40/1000 em is about the
# thickness of a stroke — below it two fonts are simply drawn differently.
NOTABLE = 40


# ---------------------------------------------------------------------------
# The showcase itself
# ---------------------------------------------------------------------------
# Grouped by the RULE each row exercises, because that is what makes a
# showcase a test rather than a poster: if a row looks wrong, its group
# names the lookup to go and read.

FAMILIES = [
    {
        "id": "below-vowel",
        "title": "တစ်ချောင်းငင် ု / နှစ်ချောင်းငင် ူ — four different shapes",
        "titleMy": "အောက်မြစ်သရ လေးမျိုးသော ပုံသဏ္ဌာန်",
        "note": "The same two characters, drawn four ways depending on what "
                "precedes them: a curl under a plain base, a side form beside "
                "a descender, a tall spacing stroke after a medial ya or wa, "
                "and a bar standing inside a medial-ra wrap.",
        "rows": [
            ("ကု", "curl under a plain base"),
            ("ကူ", "curl under a plain base"),
            ("ခု", "curl, narrow base"),
            ("နု", "side form — the base swaps to န.alt, vowel beside the leg"),
            ("ရု", "side form — ရ.alt before ု only"),
            ("ရွ", "…but ရ stays plain before ွ — Padauk's own split"),
            ("ရှု", "curl after ha: ha blocks the tall-stroke context"),
            ("ကျု", "tall spacing stroke after medial ya"),
            ("ကျူ", "tall spacing stroke after medial ya"),
            ("ကွု", "tall spacing stroke after medial wa"),
            ("ကွူ", "tall spacing stroke after medial wa"),
            ("လျှု", "tall stroke fires THROUGH an intervening ha"),
            ("မွှူ", "tall stroke fires THROUGH an intervening ha"),
            ("ကြု", "fused wrap+u — the sweep retracts, the bar stands in it"),
            ("ပြု", "fused wrap+u, narrow wrap"),
            ("ကြူ", "ူ after a wrap becomes a spacing form after the cluster"),
            ("ပြူ", "ူ after a wrap becomes a spacing form after the cluster"),
            ("ကြွု", "wrap + wa fused, then the tall stroke"),
        ],
    },
    {
        "id": "wrap",
        "title": "Medial ra ြ — narrow, wide and tall wraps",
        "titleMy": "ရရစ် — ကျဉ်း၊ ကျယ်၊ မြင့်",
        "note": "The wrap variant is chosen by MEASURING the base against the "
                "wrap's reach, not from a list of letters. A tall above-mark "
                "raises the wrap again.",
        "rows": [
            ("ပြ", "narrow — ပ fits inside the plain wrap"),
            ("ခြ", "narrow"),
            ("မြ", "narrow"),
            ("နြ", "narrow"),
            ("ဂြ", "narrow"),
            ("ကြ", "wide — က overhangs the narrow wrap"),
            ("တြ", "wide"),
            ("ဘြ", "wide"),
            ("ဆြ", "wide"),
            ("ပြဲ", "tall wrap — ဲ is a RA_TALL_TRIGGER"),
            ("ပြီ", "tall wrap"),
            ("သြဲ", "tall + wide"),
            ("ကြီး", "tall + wide, with the visarga"),
            ("မြို့", "tall wrap, small vowel inside, dot beside"),
        ],
    },
    {
        "id": "medials",
        "title": "Stacked medials — ျ ြ ွ ှ in combination",
        "titleMy": "ဗျည်းတွဲများ ပေါင်းစပ်ခြင်း",
        "note": "Where the medials meet, the font uses the fused forms traced "
                "off Padauk rather than stacking the parts.",
        "rows": [
            ("ပွှ", "fused wa+ha"),
            ("လွှ", "fused wa+ha"),
            ("ကွှ", "fused wa+ha"),
            ("ကျွ", "ya tucks under the base, wa beside it"),
            ("လျှ", "fused ya+ha"),
            ("ကြွ", "wa shrinks to .small inside the wrap"),
            ("ကြွှ", "wa and ha both .small inside the wrap"),
            ("ညှ", "ha under the two-legged ည"),
            ("ကျွန်ုပ်", "the pronoun — ya.wa fusion plus a side-form base"),
            ("ရွှေ", "wa+ha under ရ with the left vowel"),
            ("လွှဲ", "wa+ha with a tone mark above"),
        ],
    },
    {
        "id": "marks",
        "title": "Marks above and below",
        "titleMy": "အထက်နှင့် အောက် သင်္ကေတများ",
        "note": "Every mark below is placed by GPOS from anchors the pipeline "
                "measured off the drawing — including the rule that a second "
                "below-mark lands BESIDE the first, never under it.",
        "rows": [
            ("ပဲ", "tone above a plain base"),
            ("ကိံ", "i + anusvara, a drawn ligature"),
            ("ကျို့", "dot lands beside the tall stroke, not under it"),
            ("ရွှံ့", "the deepest cluster in ordinary use"),
            ("နို့", "side-form base, vowel and dot"),
            ("လွံ့", "wa, anusvara and dot"),
            ("ဩ", "independent vowel — its own wrap band"),
            ("ဪ", "independent vowel with tone"),
        ],
    },
    {
        "id": "stacks",
        "title": "Stacked consonants and kinzi",
        "titleMy": "ပါဌ်ဆင့်နှင့် ကင်းစီး",
        "note": "The virama is consumed by blwf; stacks sit in their own band "
                "and the kinzi hooks to the right so a following vowel lands "
                "beside it instead of on top.",
        "rows": [
            ("က္က", "plain stack"),
            ("စက္ကူ", "stack with a spacing vowel beside it"),
            ("န္န", "stack under a descender base"),
            ("ဇ္ဈ", "the stack that is really a side form"),
            ("က္ကွိ", "stack, then a medial and a vowel"),
            ("အင်္ကျီ", "kinzi + medial ya — kinzi shifts left to clear it"),
            ("သင်္ချိုင်း", "kinzi with a full cluster after it"),
            ("ခန္ဓာ", "stack plus a post-base vowel"),
            ("ကမ္မဋ္ဌာန်း", "two stacks in one word"),
        ],
    },
]

# Real words, straight from the vocabulary the font is validated against.
# Chosen to be ordinary prose rather than torture tests — the showcase has
# to look like Burmese, not like a QA sheet.
WORDS = [
    "မြန်မာစာ", "ကျေးဇူးတင်ပါတယ်", "ဘာသာစကား", "ကွန်ပျူတာ",
    "ရွှေတိဂုံဘုရား", "ကျောင်းသား", "နိုင်ငံတော်", "အင်္ဂလိပ်စာ",
    "ဆွေမျိုးများ", "လှပသောမြို့", "ကမ္ဘာကြီး", "သင်္ချိုင်းကုန်း",
    "ပညာရေး", "ကျွန်တော်တို့", "မြို့တော်ခန်းမ", "ဖွံ့ဖြိုးတိုးတက်ရေး",
]

PANGRAM = "သီဟိုဠ်မှ ဉာဏ်ကြီးရှင်သည် အာယုဝဍ္ဎနဆေးညွှန်းစာကို ဇလွန်ဈေးဘေး ဗာဒံပင်ထက် အဓိဋ္ဌာန်လျက် ဟောလေသည်။"

VOCAB_CORPUS = Path(__file__).resolve().parent / "build-vocab" / \
    "mwg_vocab_corpus.txt"
DEFAULT_VOCAB_OUT = ROOT / "web" / "data" / "vocabulary.js"

# The whole word list travels with the page: 364 KB of text, 62 KB over the
# wire, smaller than the font it demonstrates. Loading it live from the
# Hugging Face API instead means 498 paged requests, which rate-limits
# partway through and leaves the demo half-drawn — measured, not guessed.
# So the page renders all 12,450 offline and uses the API only to spot-check
# that this copy still matches the source.
#
# Kept in its own file with its own licence header rather than folded into
# showcase.js: the code here is MIT, this is somebody else's CC BY / CC BY-SA
# data, and the boundary should be visible in the repository, not just in a
# credits line.
VOCAB_HEADER = """\
/*
 * The Myanmar Word Glyphs vocabulary — 12,450 real Burmese words.
 *
 * NOT part of this project's MIT-licensed source. Redistributed here under
 * the terms of its own licences, with attribution:
 *
 *   Dataset: DatarrX — Myanmar Word Glyphs (MWG)
 *            https://huggingface.co/datasets/DatarrX/myanmar-word-glyphs
 *            CC BY 4.0
 *   Source vocabulary: Myanmar Wiktionary (my.wiktionary.org) contributors
 *            CC BY-SA
 *
 * Only the `text` labels are reproduced; the dataset's glyph images are not.
 * GENERATED by pipeline/make_showcase.py from a fetch_vocab.py download —
 * regenerate rather than hand-editing.
 */
"""


def read_vocabulary():
    """The full word list, if fetch_vocab.py has been run."""
    if not VOCAB_CORPUS.is_file():
        return []
    return [line.split("\t")[-1]
            for line in VOCAB_CORPUS.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]


def write_vocabulary(words, out_path):
    body = json.dumps(words, ensure_ascii=False, separators=(",", ":"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        VOCAB_HEADER + "(function () {\n  \"use strict\";\n"
        f"  window.MWG_VOCABULARY = {body};\n}}());\n", encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------

class Shaper:
    """One font, ready to shape and measure at a 1000-unit em."""

    def __init__(self, path):
        self.path = Path(path)
        blob = hb.Blob.from_file_path(str(path))
        self.hb_font = hb.Font(hb.Face(blob))
        self.tt = TTFont(path, lazy=True)
        self.glyph_set = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.scale = 1000.0 / self.tt["head"].unitsPerEm
        self.family = self.tt["name"].getDebugName(1) or self.path.stem
        self._bounds = {}

    def ink(self, name):
        if name not in self._bounds:
            pen = BoundsPen(self.glyph_set)
            self.glyph_set[name].draw(pen)
            self._bounds[name] = pen.bounds
        return self._bounds[name]

    def measure(self, text):
        """Shape `text` and return its glyph names, advance and ink box."""
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb_font, buf)

        s = self.scale
        names, boxes, pen = [], [], 0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            name = self.order[info.codepoint]
            names.append(name)
            bounds = self.ink(name)
            if bounds:
                x0, y0, x1, y1 = bounds
                ox = (pen + pos.x_offset) * s
                oy = pos.y_offset * s
                boxes.append((x0 * s + ox, y0 * s + oy,
                              x1 * s + ox, y1 * s + oy))
            pen += pos.x_advance

        ink = [round(min(b[0] for b in boxes)), round(min(b[1] for b in boxes)),
               round(max(b[2] for b in boxes)), round(max(b[3] for b in boxes))
               ] if boxes else None
        return {"glyphs": names, "advance": round(pen * s), "ink": ink,
                "notdef": ".notdef" in names}


def compare(font, reference, text):
    """Measure one string in both fonts and score the difference."""
    mine = font.measure(text)
    row = {
        "text": text,
        "cps": " ".join(f"U+{ord(c):04X}" for c in text),
        "glyphs": mine["glyphs"],
        "advance": mine["advance"],
        "ink": mine["ink"],
    }
    if mine["notdef"]:
        row["notdef"] = True

    if reference is None:
        return row

    theirs = reference.measure(text)
    if theirs["notdef"] or not (mine["ink"] and theirs["ink"]):
        row["ref"] = {"unavailable": True}
        return row

    edges = [a - b for a, b in zip(mine["ink"], theirs["ink"])]
    d_adv = mine["advance"] - theirs["advance"]
    row["ref"] = {
        "glyphs": theirs["glyphs"],
        "advance": theirs["advance"],
        "ink": theirs["ink"],
        "dAdvance": d_adv,
        "dInk": edges,
        # The single number the page sorts and colours by.
        "worst": max([abs(d_adv)] + [abs(e) for e in edges]),
    }
    row["ref"]["notable"] = row["ref"]["worst"] > NOTABLE
    return row


def build(font, reference):
    families = []
    for family in FAMILIES:
        rows = []
        for text, rule in family["rows"]:
            row = compare(font, reference, text)
            row["rule"] = rule
            rows.append(row)
        families.append({**{k: v for k, v in family.items() if k != "rows"},
                         "rows": rows})

    return {
        "font": {"family": font.family, "file": font.path.name},
        "reference": ({"family": reference.family, "file": reference.path.name}
                      if reference else None),
        "notable": NOTABLE,
        "families": families,
        "words": [compare(font, reference, w) for w in WORDS],
        "pangram": PANGRAM,
    }


def render(data):
    """Write the payload the way web/data/*.js files are written here."""
    body = json.dumps(data, ensure_ascii=False, indent=1)
    return (
        "/*\n"
        " * Data for showcase.html: every cluster on that page with the\n"
        " * glyphs it shapes to, its advance and ink box, and the same\n"
        " * measurements from the reference font it was traced over.\n"
        " *\n"
        " * GENERATED by pipeline/make_showcase.py — regenerate rather than\n"
        " * hand-editing, and regenerate whenever the shaping rules change.\n"
        " */\n"
        "(function () {\n"
        '  "use strict";\n'
        f"  window.SHOWCASE = {body};\n"
        "}());\n"
    )


def main():
    ap = argparse.ArgumentParser(
        description="Generate web/data/showcase.js from the built fonts.")
    ap.add_argument("--font", type=Path, default=DEFAULT_FONT)
    ap.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE,
                    help="font to compare against (default: bundled Padauk)")
    ap.add_argument("--no-reference", action="store_true",
                    help="skip the comparison column")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--vocab-out", type=Path, default=DEFAULT_VOCAB_OUT,
                    help="where to write the bundled word list")
    args = ap.parse_args()
    repo_root("mgs-showcase")   # generates web/data/showcase.js

    if not args.font.is_file():
        sys.exit(f"font not found: {args.font}")
    font = Shaper(args.font)
    reference = None
    if not args.no_reference:
        if args.reference.is_file():
            reference = Shaper(args.reference)
        else:
            print(f"reference not found, skipping comparison: {args.reference}")

    data = build(font, reference)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(data), encoding="utf-8")

    vocab = read_vocabulary()
    if vocab:
        out = write_vocabulary(vocab, args.vocab_out)
        print(f"{out}: {len(vocab)} words "
              f"({out.stat().st_size / 1024:.0f} KB)")
    elif args.vocab_out.is_file():
        print(f"  {args.vocab_out.name} left as it is — "
              f"run fetch_vocab.py to regenerate it")
    else:
        print("  no vocabulary bundled — run fetch_vocab.py first")

    rows = sum(len(f["rows"]) for f in data["families"]) + len(data["words"])
    notable = [r["text"] for f in data["families"] for r in f["rows"]
               if r.get("ref", {}).get("notable")]
    missing = [r["text"] for f in data["families"] for r in f["rows"]
               if r.get("notdef")]
    print(f"{args.out}: {rows} rows, {len(data['families'])} families")
    if missing:
        print(f"  .notdef in {len(missing)}: {', '.join(missing)}")
    if notable:
        print(f"  differs from {reference.family} by >{NOTABLE} units "
              f"in {len(notable)}: {', '.join(notable)}")
    else:
        print(f"  every row within {NOTABLE} units of the reference")


if __name__ == "__main__":
    main()
