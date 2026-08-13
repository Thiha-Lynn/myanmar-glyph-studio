# Myanmar Glyph Studio · မြန်မာဖောင့် ရေးဆွဲကိရိယာ

**Sketch your own Myanmar font, glyph by glyph, over dimmed guide characters — then build a real, installable, Unicode-correct font.**

An open-source toolkit for the Myanmar fonts community. Anyone who can draw
can make a font: the studio shows each Myanmar character (and the combined
forms like stacked consonants) as a dimmed guide, you trace your own style
over it, and the toolchain turns your sketches into a working font.

> ဖောင့်တစ်လုံး ဖန်တီးဖို့ စာလုံးတိုင်းကို ရေးဆွဲစရာမလိုပါ —
> အခြေခံစာလုံး ~၁၅၀ နဲ့ ပုံစံကွဲအချို့ကိုသာ ရေးဆွဲပြီး
> ကျန်တာကို OpenType shaping စနစ်က ပေါင်းစပ်ပေးပါတယ်။

## How it works

```
 ┌───────────────┐     ┌──────────────────┐     ┌──────────────────────┐
 │  web/          │     │ project JSON      │     │ pipeline/             │
 │  Glyph Studio  │ ──► │ (.glyphstudio.json│ ──► │ json_to_ufo.py        │
 │  draw in the   │     │  = your source    │     │ → UFO sources         │
 │  browser       │     │  of truth)        │     │ → fontmake → real TTF │
 └───────────────┘     └──────────────────┘     └──────────────────────┘
        │
        └──► one-click **draft TTF** straight from the browser (for quick testing)
```

1. **Draw** — open the studio, pick a glyph (က ခ ဂ …), and sketch over the
   dimmed guide. Combined forms are guided too: for the stack က္က you draw
   only the small lower letter; for vowel signs you draw only the mark next
   to the dotted circle ◌.

   Built for real drawing hands: works on phone, tablet, and desktop;
   **Apple Pencil / stylus pressure** varies your stroke width; once a pen
   is detected, fingers pan and zoom while the pen draws (palm rejection);
   pinch or scroll to **zoom** into details (a precision grid appears);
   a **stabilizer** steadies shaky lines; **focus mode** (⛶) hides
   everything but the canvas.
2. **Test** — the test-drive box previews your drawn letters live, and
   **Export font** gives an installable TTF in one click. The in-app
   **Help** explains how to use it everywhere: install on
   Windows/macOS/Linux, ship it in Unity/Godot/Unreal games, bundle it in
   Android/iOS/Flutter apps, or serve it on the web with `@font-face`.
   **⚓ Anchor mode** shows where vowel signs will attach — drag the
   points to fix mark positioning without a font editor. **Import SVG**
   brings vectorized paper sketches (Inkscape/Illustrator trace) straight
   onto a glyph.
3. **Build** — save your project file and run the pipeline to get proper
   UFO sources and a shaping-capable font (stacked consonants, kinzi,
   mark/mkmk positioning) via the industry-standard `fontmake` toolchain.
   Finished fonts appear in the community **[gallery](web/gallery.html)**
   with live preview.

## Run the studio

No build step, no install — it is plain HTML/JS:

```bash
cd web && python3 -m http.server 8321
```

Then open <http://localhost:8321>. (Opening `index.html` directly also works
in most browsers.) Your work autosaves to the browser's local storage;
**Save** downloads the portable project JSON you should keep and commit.

The guides render from whatever Myanmar font your system has
(Padauk, Myanmar MN, Noto Sans Myanmar, Myanmar Text). For the best guides,
install [Padauk](https://software.sil.org/padauk/) (free, OFL).

## Build a real font from your project

```bash
cd pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./build.sh ~/Downloads/MyFont.glyphstudio.json build/
```

This writes UFO sources (editable in [Fontra](https://fontra.xyz),
FontForge, Glyphs, …) and compiles a TTF with auto-generated `mym2`
shaping features and mark anchors. Verify shaping with HarfBuzz:

```bash
hb-view build/*.ttf "ကျွန်ုပ်တို့ မြန်မာစာ" --output-file proof.png
```

## What you draw (and what you don't)

Myanmar is a complex script: the text engine composes syllables at render
time, so a font needs **parts + rules**, not a glyph per syllable.

| You draw | The build system handles |
|---|---|
| 74 core Burmese characters (consonants, vowels, signs, digits, punctuation) | glyph encoding, metrics, UFO packaging |
| ~34 subjoined (stacked) forms — guided by stacks like က္က | `blwf` substitutions so ္ + က renders your stack form |
| kinzi, wide medial-ra, short u/uu variants | `rphf` / `pres` / `blws` contextual rules |
| the invisible virama — never; it's synthesized automatically | mark positioning (GPOS `mark`/`mkmk`) from anchors — auto-placed, draggable in ⚓ anchor mode |

**Coverage is complete — and then some.** The inventory spans the **entire
Myanmar Unicode block U+1000–109F** — every Burmese character plus
Pali/Sanskrit, Mon, S'gaw & Pwo Karen, Kayah, Shan (letters, tones,
digits, symbols), Rumai Palaung, Khamti and Aiton — plus **Myanmar
Extended-A** (Khamti Shan, Aiton) and **Extended-B** (Tai Laing, Shan
Pali) and the ◌ dotted circle (U+25CC): 223 encoded characters and 38
shaping variants. Draw the core Burmese groups for a usable font; the
ethnic groups extend it as far as you want to go.

**English is optional.** The A–Z / a–z / 0–9 / punctuation groups let one
font cover Myanmar *and* English — but they are marked "(optional)":
leave them empty and your font is simply Myanmar-only. Mark
classification and codepoints for the extended groups are generated from
the Unicode Character Database, not hand-typed.

## The sample font — see the whole pipeline work

[`projects/sample/`](projects/sample/) contains **Glyph Studio Sample**, a
complete 110-glyph font generated by skeletonizing Padauk (OFL) through this
exact stroke pipeline — the same path your hand-drawn font takes. It proves
stacks (က္က), kinzi (င်္), medial wraps (ကြ) and mark positioning all work:
see [proof.png](projects/sample/proof.png), install
[the built TTF](projects/sample/GlyphStudioSample-Regular.ttf), or
regenerate it yourself:

```bash
python3 pipeline/make_sample.py Padauk-Regular.ttf projects/sample/GlyphStudioSample.glyphstudio.json
```

## Project structure

```
web/        the Glyph Studio drawing app (static, no dependencies to build)
pipeline/   project JSON → UFO → fontmake build, feature generation,
            make_sample.py (sample generator), proof.py (visual proof sheets),
            test_corpus.txt (shaping test sentences)
projects/   community font projects — one folder per family
docs/       design notes and the font testing guide
```

The studio can be hosted for free on GitHub Pages
(`.github/workflows/pages.yml` deploys `web/` — enable Pages → GitHub Actions
in the repo settings), so contributors need nothing but a browser.

## Contributing & community

All skill levels welcome — drawing a single glyph is a real contribution.
See [CONTRIBUTING.md](CONTRIBUTING.md) for the ways in (drawing, tools,
testing, translation), [projects/README.md](projects/README.md) for the
font-family folder layout, and [docs/LAUNCH.md](docs/LAUNCH.md) for the
maintainer playbook. We follow the
[Contributor Covenant](CODE_OF_CONDUCT.md); report security issues per
[SECURITY.md](SECURITY.md).

Fonts produced with this toolkit are meant to be released under the
[SIL Open Font License 1.1](https://openfontlicense.org) (each family
folder carries the OFL text); the toolkit code is [MIT](LICENSE).
Tagged releases ship ready-to-install zips (TTF + WOFF2 + proof sheet)
for every family.

## Roadmap

- [x] Shared HarfBuzz shaping test corpus + visual proof tool
      (`pipeline/test_corpus.txt`, `pipeline/proof.py`)
- [x] Complete sample font demonstrating the full pipeline
- [x] Full Myanmar block U+1000–109F (Mon, Karen, Kayah, Shan, Pali,
      Palaung, Khamti, Aiton) + optional Latin groups
- [x] Anchor editing in the studio (⚓ — drag mark attachment points,
      stored in the project JSON, honored by the build)
- [x] SVG import (vectorized paper sketches → filled contours on the
      current glyph; studio SVG exports round-trip exactly)
- [x] Myanmar Extended-A + Extended-B blocks (Khamti Shan, Aiton, Tai
      Laing, Shan Pali) — generated from the UCD by
      `pipeline/gen_inventory.py`
- [x] Dotted-circle (U+25CC) support glyph in the inventory
- [x] Gallery site of community fonts with live preview
      ([web/gallery.html](web/gallery.html), auto-built on deploy)
- [x] fontbakery QA in CI (universal profile, FAIL-gated) + HarfBuzz
      shaping regression on the sample font
- [ ] Myanmar Extended-C block (U+116D0–116FF, Unicode 16) — the pipeline
      already accepts its uXXXXX names; waiting on guide-font coverage
- [ ] Kerning (`kern`) and GDEF mark-class refinement
- [ ] In-studio component reuse (draw once, place many times)

## Acknowledgements

Standing on the shoulders of [SIL Padauk](https://github.com/silnrsi/font-padauk),
the [Noto Myanmar](https://github.com/notofonts/myanmar) project,
[opentype.js](https://github.com/opentypejs/opentype.js),
[fontmake](https://github.com/googlefonts/fontmake) /
[ufoLib2](https://github.com/fonttools/ufoLib2), and the
[Microsoft Myanmar script development spec](https://learn.microsoft.com/en-us/typography/script-development/myanmar).
