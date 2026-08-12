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
  off. `json_to_ufo.py` places starting-point anchors only; open the UFO
  in a font editor and nudge the `top`/`bottom` anchors.

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

## Release QA: fontbakery

Before publishing a font (and eventually for the Google Fonts onboarding
path), run [fontbakery](https://fontbakery.readthedocs.io):

```bash
pip install fontbakery
fontbakery check-universal build/MyFont-Regular.ttf
```

Early builds will collect warnings (vertical metrics, name table entries,
hinting). Read the report as a release punch list, not as build failures —
shaping correctness is what proof.py and the corpus already covered.
