# Contributing

ကြိုဆိုပါတယ် — welcome! This project runs on small contributions:
a single well-drawn glyph, a bug report, a translated hint, a test sentence.

## Ways to contribute

### 1. Draw glyphs for a community font
Open the studio, draw, click **Save**, and open a pull request that
adds or updates your `.glyphstudio.json` under `projects/<font-name>/`
(create the folder on first contribution). One font family = one folder =
one style owner (see below). You can also draw on paper: vectorize the
scan (Inkscape/Illustrator trace) and use **Import SVG**. If a vowel sign
sits wrong, fix it yourself with the **⚓ Anchors** mode — no font editor
needed. CI builds every project, renders a HarfBuzz proof sheet, and runs
fontbakery; families with a committed TTF appear in the
[gallery](web/gallery.html) with live preview.

### 2. Improve the tools
The studio is dependency-free vanilla JS (`web/`), the pipeline is small
Python (`pipeline/`). Good first issues: kerning support, GDEF mark-class
refinement, Myanmar Extended-C once guide fonts exist, in-studio component
reuse, better outline expansion.

### 3. Review and test
Install a draft TTF, type real Burmese/Mon/Shan text, and file issues with
screenshots. Shaping reports (HarfBuzz `hb-view` output) are gold.

### 4. Translate and teach
Burmese-language hints, tutorials, and videos are as valuable as code —
font-making education in Burmese barely exists. `web/data/glyphs.js`
holds every hint string.

## Style consistency: the lead-designer rule

Free-form crowds don't converge on a style, so every font family in
`projects/` has a **style owner** — usually whoever started it. The owner
draws the key glyphs (က ခ တ န မ set a Myanmar font's DNA), writes a short
style note in the folder's README, and reviews glyph PRs for fit. Tool PRs
are reviewed by the repo maintainers.

## Licensing

- **Toolkit code:** MIT (see [LICENSE](LICENSE)).
- **Fonts and glyph sketches:** by opening a PR that adds glyph data or font
  sources you agree your contribution is released under the
  [SIL Open Font License 1.1](https://openfontlicense.org), with your name
  added to the font's copyright/credits. This is the standard license of the
  open font world (Padauk, Noto, Google Fonts) and keeps every font free to
  use, modify, and redistribute forever.

## Ground rules

Be kind, be patient with beginners, credit generously. Technical arguments
are settled by what renders correctly (HarfBuzz output) and what the style
owner decides for their family.
