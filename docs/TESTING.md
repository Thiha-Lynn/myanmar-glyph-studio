# Testing a built font

A font that installs is not yet a font that *shapes*: stacks, kinzi and
medials only appear if the generated GSUB/GPOS rules fire the way the
shaping engine expects (background: [DESIGN.md](DESIGN.md)). This is the
practical checklist — render a proof sheet, read it, get a second opinion
from the HarfBuzz CLI, compare against Padauk, and run release QA.

## Render a proof sheet

`pipeline/proof.py` shapes test strings with HarfBuzz — the engine used by
Android, Chrome, Linux and LibreOffice — and rasterizes the positioned
glyphs straight from your TTF. No system text stack is involved, so font
fallback can't sneak in and hide a missing glyph or a dead rule.

```bash
cd pipeline
pip install fonttools uharfbuzz pillow    # once, in your build venv
python3 proof.py build/MyFont-Regular.ttf test_corpus.txt proof.png
python3 proof.py build/MyFont-Regular.ttf "ကျွန်ုပ်တို့ မြန်မာစာ" quick.png --size 128
```

For a graded, measured pass over the much larger specification corpus
(1 486 clusters, collision detection included) run
`python3 validate_spec.py build/MyFont-Regular.ttf` — checks and
severities in [SHAPING_SPEC.md](SHAPING_SPEC.md) §6, symptom-by-symptom
triage in [DEBUGGING.md](DEBUGGING.md).

`test_corpus.txt` is the shared shaping corpus: the 33-consonant pangram,
stacks, kinzi, all four medials singly and combined, every vowel position,
digits, punctuation, and natural sentences — one row per line, with a
comment above each line saying what it exercises. Alongside the PNG,
proof.py prints each row's shaped glyph sequence in hb-shape style
(`name=cluster@x_offset,y_offset+x_advance`):

    [02] က္က ဗုဒ္ဓ မန္တလေး
         ka-myanmar=0+790|ka-myanmar.sub=0@-708,20+0|...

## Reading the proof

* **Hollow boxes** are characters your font doesn't map yet. Normal for a
  work-in-progress font — that's the to-draw list, not an error.
* **Stacks (က္က, ဗုဒ္ဓ)** — the second consonant sits small, directly
  *below* the first. If you see base + virama sign + full-size consonant
  in a row, `blwf` didn't fire: draw both the base and its `.sub` form and
  rebuild. In the stdout, `virama-myanmar` surviving in the output is this
  exact failure.
* **Kinzi (သင်္ဘော, အင်္ဂါ)** — the င်္ becomes a small mark *above* the
  following consonant. A visible full-size င + asat + virama means `rphf`
  didn't fire (the kinzi glyph isn't drawn yet).
* **Medials (ကျ ကြ ကွ ကှ)** — ya hooks to the right, ra *wraps around* the
  base (the base sits inside the ြ), wa and ha hang below. Combined forms
  (ကျွ, မြွှ) must not collide. Wide bases like ခ and မ should take the
  wide ြ variant if you drew it (`pres`).
* **Pre-base vowel (ကေ, မြေ)** — the ေ renders to the *left* of the
  consonant even though it is stored after it. If it shows up on the
  right, the text was not shaped as Myanmar at all — check that the build
  emitted the `mym2` features.
* **Below vowels (ကု ကူ), tall aa (ခါ vs ကာ), tones (ကား ကတ် ကံ့)** — marks
  attach centered, clear of descenders; ခ ဂ င ဒ ပ ဝ take the tall ါ.
* **Marks piled on one spot or floating far away** — anchor positions are
  off. Fix them without leaving the browser: the studio's **⚓ Anchors**
  mode shows every attachment point over your ink — drag it, save, rebuild.
  (Dragged positions live in the project JSON and override the automatic
  placement; a font editor on the UFO still works for finer control.)

Quick regression check without opening the image:

```bash
python3 proof.py build/MyFont-Regular.ttf test_corpus.txt proof.png | grep -E "virama|notdef"
```

## Second opinion: hb-shape / hb-view

The HarfBuzz CLI shows the same thing with none of this repo's code
involved (`brew install harfbuzz` on macOS, `apt install libharfbuzz-bin`
on Debian/Ubuntu):

```bash
hb-shape build/MyFont-Regular.ttf "က္က"
# [ka-myanmar=0+790|ka-myanmar.sub=0@-708,20+0]   <- virama consumed: good
hb-view build/MyFont-Regular.ttf "သင်္ဘော" --font-size 96 --output-file kinzi.png
```

`hb-view --text-file test_corpus.txt` works too, but renders the `#`
comment lines literally — proof.py skips them, which is why it is the
default here.

## Compare against Padauk

[Padauk](https://software.sil.org/padauk/) (free, OFL) is the reference
for Myanmar shaping behaviour. Run the identical corpus through both fonts
and put the sheets side by side:

```bash
python3 proof.py build/MyFont-Regular.ttf test_corpus.txt proof-mine.png
python3 proof.py /path/to/Padauk-Regular.ttf test_corpus.txt proof-padauk.png
```

Glyph *names* in the stdout will differ (Padauk has its own naming
scheme). What must match, row by row, is the visual structure: the same
things stacked, the same marks above and below, the e-vowel reordered to
the same place.

For the comparison in a form you can read rather than squint at, build
the showcase page:

```bash
python3 make_showcase.py            # -> ../web/data/showcase.js
python3 make_gallery.py             # -> ../web/gallery-data/ (the webfonts)
```

`web/showcase.html` then renders 60 hard clusters in your font beside the
reference, each row carrying the glyphs the shaper produced and how far
the ink sits from the reference in units of a 1000 em. Rows more than 40
units out are highlighted — that is a *drawing* difference, not
necessarily a bug, which is why the page shows them instead of grading
them.

This catches a class the corpora cannot. `validate_spec.py` measures
whether a mark is attached, clear and inside the band; it has no opinion
on whether the shaper picked the *right form*. A vowel in the wrong
contextual shape is still perfectly positioned, so it scores 0 FAIL —
and if the combination happens to be absent from the vocabulary, the
word corpus never sees it either. The 2026-08-17 ကွှု fix came from this
page, not from the corpora.

## Sweeping the whole vocabulary

CI gates on `word_corpus.txt`, 711 words chosen by greedy set cover to
contain all 1 213 syllable clusters in the source vocabulary. To check
the cover against the thing it covers, fetch the full 12 450 words:

```bash
pip install pyarrow
python3 fetch_vocab.py
python3 validate_spec.py ../projects/myanmar-glyph-sans/MyanmarGlyphSans-Regular.ttf \
        --corpus build-vocab/mwg_vocab_corpus.txt
```

It runs in about half a second once fetched. The download is 41 MB and
the corpus is not committed, so this is a local check rather than a CI
step — and so far it has never reported anything the 711-word cover
missed, which is the result it exists to produce.

## The deep sweep: a corpus from real books

The two committed corpora are hand-built. `pipeline/make_reference.py`
builds one from the wild instead — point it at a Wikisource category and
it fetches every page, segments the text into syllable clusters exactly as
HarfBuzz does, and greedily keeps the fewest passages that still contain
every cluster it saw:

```bash
python3 make_reference.py                 # -> jataka_corpus.txt
python3 validate_spec.py <font.ttf> --corpus jataka_corpus.txt
```

The shipped `jataka_corpus.txt` comes from ကဏ္ဍ:ဇာတ်နိပါတ်, the 538 Jātaka
stories: 3.66 million characters of classical narrative, **1,605 distinct
clusters** — a third more than the 1,213 in the DatarrX vocabulary — held
in 556 passages.

It is not a CI gate: 18 seconds per font against 0.3 for the spec corpus,
which is what happens when passages are paragraphs rather than words. Run
it when shaping rules change. It earns that on its first run — it found
the ိံ/kinzi collision that all three other corpora score as passing.

Expect a handful of SPEC rows from any corpus drawn from scanned text.
Twelve of these 556 passages contain a mark typed twice in a row
(ကောာလိက, ကင််); `validate_spec` reports those as `repeated-mark` rather
than grading a transcription slip as a font defect.

## Reading it as a book, and as a PDF

```bash
python3 make_book.py                      # -> ../web/data/book.js
python3 make_pdf.py --font ../projects/bagan-display/BaganDisplay-Bold.ttf
```

`web/book.html` sets the book page by page, optionally beside Padauk.
`make_pdf.py` writes a real PDF — and does it by shaping with HarfBuzz and
drawing every positioned glyph as a vector path, because **a PDF reader
has no shaping engine**. Embedding a Myanmar font and handing it a string
gets you storage order with no reordering and no mark positioning. If you
ever need to check that claim, open a PDF produced any other way and look
at a ေ.

## Release QA: fontbakery

Every pipeline build is checked in CI with
[fontbakery](https://fontbakery.readthedocs.io)'s universal profile — the
build workflow fails on FAIL-level findings and prints WARNs as a punch
list. Run the same check locally (fontbakery is in
`pipeline/requirements.txt`):

```bash
fontbakery check-universal --succinct -l WARN build/MyFont-Regular.ttf
```

The pipeline already produces fonts that pass clean: a visible `.notdef`
box, space + no-break space, valid production glyph names
(`public.postscriptNames`), explicit GDEF classes
(`public.openTypeCategories`), zero-width non-spacing marks, gasp records,
and the smart-dropout `prep` program (`pipeline/postbuild.py`). The
remaining WARNs are honest ones: strokes that overlap by design (Myanmar letters are built from overlapping circles;
TrueType's nonzero winding renders them correctly).

CI also renders the proof sheet for every built font and fails if the
*sample* font shapes with any missing glyph — the toolchain's own
regression test.

## Variable fonts

`make_variable.py` refuses to write a designspace whose masters disagree on
glyph count, and `pipeline/tests/` asserts that masters stay
interpolation-compatible point for point. After building, check the axis
landed:

```bash
python3 -c "from fontTools.ttLib import TTFont; f=TTFont('build/MyFont-VF.ttf'); \
print([(a.axisTag, a.minValue, a.maxValue) for a in f['fvar'].axes])"
```

Then look at the extremes: `hb-view MyFont-VF.ttf --variations=wght=700`
should be visibly heavier with the same letterforms, no collapsed counters
and no crossed outlines.

## All three engines, checked automatically

Myanmar text is composed by the text engine, not the font, so the same
font can render differently on different platforms. There are three
engines that matter, and every one of them is now diffed against the
others automatically:

| Engine | Used by | Checked by |
|---|---|---|
| **HarfBuzz** | Android, Chrome, Linux, LibreOffice | CI, every push and PR |
| **CoreText** | macOS, iOS, Safari, Apple apps | `pipeline/coretext/` — pytest on any Mac |
| **DirectWrite** | Windows, Word, Edge, Office, WPF | `pipeline/directwrite/` — CI, `windows-latest` |

Each platform checker shapes the whole corpus with its own engine and
with HarfBuzz, then compares the glyph sequence and the placements,
reporting only differences that would change what a reader sees. On macOS:

```bash
cd pipeline/coretext && swiftc -O CoreTextShape.swift -o coretext-shape
python3 pipeline/coretext_check.py projects/*/MyanmarGlyphSans-Regular.ttf
```

On Windows (from a Developer Command Prompt, so `cl.exe` is on PATH):

```bat
cd pipeline\directwrite && cl /EHsc /O2 /std:c++17 DirectWriteShape.cpp
python pipeline\directwrite_check.py projects\myanmar-glyph-sans\MyanmarGlyphSans-Regular.ttf
```

Current result for the shipped family, in every weight, across both
corpora: **6,363 cluster comparisons against CoreText and 6,363 against
DirectWrite, zero rendering differences either way.** Both run under
`pytest` and skip on the platforms they do not apply to, so a Mac or
Windows contributor covers their engine without doing anything extra.

What the comparison deliberately ignores, because none of it is a font
bug — the rules live in
[`pipeline/shaping_diff.py`](../pipeline/shaping_diff.py) and are unit
tested on every platform:

* **Marks reordered but identically placed.** HarfBuzz's Myanmar shaper
  puts the tone dot before the asat; the platform engines keep storage
  order. The two attach to different anchors, so the picture is the same
  — verified by coordinate, never assumed.
* **Malformed input.** A dotted circle means both engines are *repairing*
  a cluster that is not in Unicode storage order, and how much each
  salvages is engine-defined.
* **Characters the font does not cover.** The three engines say "no glyph
  here" three different ways: HarfBuzz draws `.notdef`, CoreText
  substitutes another font for the run, DirectWrite emits the font's
  blank. All three mean the same thing.

One limit worth knowing: a font with **no U+25CC glyph** cannot draw the
repair mark, so each engine substitutes something of its own and those
choices cannot be compared. The bundled sample font is in that position,
which is why the gate covers the complete family.

## Test on a real device (issue #14 — anyone can do this)

Automation now covers all three engines' *geometry*. What it cannot judge
is whether the result **looks right** to a reader of Burmese, on real
hardware, at real sizes — or how the font behaves in an app that still
uses the older Uniscribe path. This is a five-minute contribution that
needs no coding at all:

**Open <https://thiha-lynn.github.io/myanmar-glyph-studio/devicetest.html>
on the device you want to test.** It renders every cluster this project
has ever got wrong, says what correct looks like for each, and writes the
report for you — tap ✓ or ✗ per row, then *Copy report*. Works offline
once the studio is installed.

Doing it by hand instead:

1. Download a font zip from the
   [latest release](https://github.com/Thiha-Lynn/myanmar-glyph-studio/releases/latest)
   and install the TTF (Windows: right-click → Install · macOS:
   double-click → Install Font · Android/iOS: a font-install app or a
   word processor that accepts custom fonts).
2. Set it as the font in the apps you actually use — Word, Google Docs,
   a browser, a chat app, a design tool.
3. Paste these lines (each one exercises a different shaping trap):

   ```text
   စက္ကူ ဗုဒ္ဓ မန္တလေး          ← stacked consonants
   သင်္ဘော အင်္ဂါ               ← kinzi
   ကျောင်း ကြီး ကျွန် မြွှေ      ← medials (ya, ra wrap, wa, ha)
   ကုန် ပူ နူး ကူး              ← below-base vowels
   ၀၁၂၃၄၅၆၇၈၉ ၊ ။           ← digits & punctuation
   သီဟိုဠ်မှ ဉာဏ်ကြီးရှင်သည် အာယုဝဍ္ဎနဆေးညွှန်းစာကို ဇလွန်ဈေးဘေး
   ဗာဒံပင်ထက် အဓိဋ္ဌာန်လျက် ဂဃနဏဖတ်ခဲ့သည်။   ← the pangram
   လိက်ဂကူမန် ပၠန်              ← Mon
   မႂ်ႇသုင်ၶႃႈ လိၵ်ႈတႆး          ← Shan
   ပှၤကညီ                    ← S'gaw Karen
   ```

4. Anything look wrong — overlapping marks, a consonant outside its
   ra-wrap, dotted circles that shouldn't be there? File a
   [shaping report](https://github.com/Thiha-Lynn/myanmar-glyph-studio/issues/new?template=shaping-report.md)
   with a screenshot, the exact text, and your OS + app. A report that
   says "correct everywhere" is valuable too — leave it on
   [issue #14](https://github.com/Thiha-Lynn/myanmar-glyph-studio/issues/14).

The same lines are one tap away inside the studio's test-drive box
(the preset chips), so you can also eyeball your own drawings with them.
