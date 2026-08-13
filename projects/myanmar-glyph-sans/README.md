# Myanmar Glyph Sans

A complete, monolinear Myanmar + Latin typeface — **459 glyphs**, three
weights and a variable font, free under the SIL Open Font License.

| | |
|---|---|
| Weights | Light 300 · Regular 400 · Bold 700 |
| Variable | `variable/MyanmarGlyphSans-VF.ttf`, `wght` 300–700 |
| License | [SIL Open Font License 1.1](OFL.txt) |
| Source | [`MyanmarGlyphSans.glyphstudio.json`](MyanmarGlyphSans.glyphstudio.json) — open it in the [studio](https://thiha-lynn.github.io/myanmar-glyph-studio/) and edit any glyph |

## What it covers

* **The entire Myanmar block** (U+1000–109F, 160 characters) — Burmese plus
  Pali/Sanskrit, Mon, S'gaw & Pwo Karen, Kayah, Shan, Rumai Palaung,
  Khamti and Aiton
* **Myanmar Extended-A and Extended-B** — Khamti Shan, Aiton, Tai Laing,
  Shan Pali (63 more characters)
* **Full English**: A–Z, a–z, 0–9 and punctuation
* **Western European**: every accented Latin-1 letter (Café, naïve,
  Ünïcodé, Ñ, Ø, ß …), typographic quotes, dashes, fractions, currency
  (€ £ ¥ ¢) and symbols (© ® ™ ° ± × ÷)
* **U+25CC dotted circle**, so isolated vowel signs display properly

Shaping is complete: subjoined stacks (က္က), kinzi (င်္က), all four
medials including the wide medial-ra, short u/uu variants, and GPOS
mark/mkmk positioning. It shapes the project's whole test corpus with
zero missing glyphs, and passes fontbakery's universal profile with no
failures in every weight.

## Install and use it

Download a weight above, then:

* **Windows** right-click → Install · **macOS** double-click → Install Font
  · **Linux** copy to `~/.local/share/fonts` and run `fc-cache -f`
* **Web**: `@font-face { font-family: "Myanmar Glyph Sans"; src: url("MyanmarGlyphSans-Regular.ttf"); }`
* **Video, design and documents**: it is an ordinary TrueType font, so
  Premiere, After Effects, DaVinci Resolve, Canva, Figma, Photoshop,
  Illustrator, InDesign, Word and Google Docs all accept it, and it
  embeds into PDFs like any other font.
* **Apps and games**: Unity, Godot, Unreal, Android, iOS and Flutter — see
  the studio's in-app **Help** for the per-platform steps.

The variable font gives every weight between 300 and 700 from one file:

```css
@font-face {
  font-family: "Myanmar Glyph Sans VF";
  src: url("variable/MyanmarGlyphSans-VF.ttf") format("truetype-variations");
  font-weight: 300 700;
}
h1 { font-family: "Myanmar Glyph Sans VF"; font-variation-settings: "wght" 620; }
```

## How it was made, and what that means for credit

Every glyph is a **stroke skeleton** — a centre-line and a pen width — not
an outline copied from anywhere. The skeletons were extracted from
[Padauk](https://software.sil.org/padauk/) by shaping each character with
HarfBuzz, rasterising it, thinning the ink to one-pixel centre-lines and
tracing those into studio strokes; the pipeline then re-expands them into
new curves. That is why the three weights exist at all: the pen is thinned
for Light and fattened for Bold, and nothing is redrawn.

It is therefore a **Modified Version of Padauk** under the OFL, and it
carries no reserved font name. Padauk is Copyright (c) 2002–2025 SIL
International; full terms in [OFL.txt](OFL.txt). Please keep that credit
in anything you build from this.

## Rebuild it

```sh
# regenerate the drawing from Padauk (the bundled guide font)
python3 pipeline/make_sample.py web/fonts/Padauk-Regular.ttf \
  projects/myanmar-glyph-sans/MyanmarGlyphSans.glyphstudio.json \
  --font-name "Myanmar Glyph Sans"

# all three weights plus the variable font
python3 pipeline/make_variable.py \
  projects/myanmar-glyph-sans/MyanmarGlyphSans.glyphstudio.json build/
```

Or open the project file in the studio, redraw any glyph by hand, and
build your own family from it — that is the point of the toolkit.
