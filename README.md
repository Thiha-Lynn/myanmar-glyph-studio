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
2. **Test** — the test-drive box previews your drawn letters live, and
   **Export draft TTF** gives an installable font in one click.
3. **Build** — save your project file and run the pipeline to get proper
   UFO sources and a shaping-capable font (stacked consonants, kinzi,
   mark positioning) via the industry-standard `fontmake` toolchain.

## Run the studio

No build step, no install — it is plain HTML/JS:

```bash
cd web && python3 -m http.server 8321
```

Then open <http://localhost:8321>. (Opening `index.html` directly also works
in most browsers.) Your work autosaves to the browser's local storage;
**Save project** downloads the portable JSON you should keep and commit.

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
| ~90 base characters (consonants, vowels, signs, digits, punctuation) | glyph encoding, metrics, UFO packaging |
| ~34 subjoined (stacked) forms — guided by stacks like က္က | `blwf` substitutions so ္ + က renders your stack form |
| kinzi, wide medial-ra, short u/uu variants | `rphf` / `pres` / `blws` contextual rules |
| nothing else | mark positioning (GPOS) from auto-placed anchors |

## Project structure

```
web/        the Glyph Studio drawing app (static, no dependencies to build)
pipeline/   project JSON → UFO → fontmake build, with feature generation
docs/       background research and design notes
```

## Contributing

All skill levels welcome — drawing a single glyph is a real contribution.
See [CONTRIBUTING.md](CONTRIBUTING.md). Fonts produced with this toolkit
are meant to be released under the
[SIL Open Font License 1.1](https://openfontlicense.org); the toolkit code
is [MIT](LICENSE).

## Roadmap

- [ ] Anchor editing in the studio (drag mark attachment points)
- [ ] SVG import (scan pipeline for paper sketches, Calligraphr-style)
- [ ] Mon / Shan / Karen / Kayah glyph groups (Extended-A/B/C blocks)
- [ ] Shared HarfBuzz shaping test corpus, verified against Padauk
- [ ] Gallery site of community fonts with live preview
- [ ] fontbakery QA in CI for font submissions

## Acknowledgements

Standing on the shoulders of [SIL Padauk](https://github.com/silnrsi/font-padauk),
the [Noto Myanmar](https://github.com/notofonts/myanmar) project,
[opentype.js](https://github.com/opentypejs/opentype.js),
[fontmake](https://github.com/googlefonts/fontmake) /
[ufoLib2](https://github.com/fonttools/ufoLib2), and the
[Microsoft Myanmar script development spec](https://learn.microsoft.com/en-us/typography/script-development/myanmar).
