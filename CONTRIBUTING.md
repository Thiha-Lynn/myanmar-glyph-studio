# Contributing

ကြိုဆိုပါတယ် — welcome! This project runs on small contributions:
a single well-drawn glyph, a bug report, a translated hint, a test sentence.

## Ways to contribute

### 1. Draw glyphs for a community font
Open the studio, draw, click **Save**, and open a pull request that
adds or updates your `.glyphstudio.json` under `projects/<font-name>/`
(create the folder on first contribution).

**No Git? No problem.** Draw a glyph, press **⚙ → Copy glyph**, and
paste the text snippet into a GitHub issue or Discussion — a maintainer
will land it in the family with your name in the credits. (Anyone can
paste a snippet back into their own studio with **⚙ → Paste glyph**.)
Every glyph also has a shareable address (the `#g=…` in the URL), so an
issue can point you at exactly the letter it needs. One font family = one folder =
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

## If you have write access

Everything lands through a pull request — `main` is protected and the
`build` check must pass, so pushing to it directly will be refused. The
flow is the same as for anyone else, just without the fork:

```bash
git checkout -b my-change
# …work…
git push -u origin my-change
gh pr create
```

Run the gates locally first; CI runs the same ones and takes ~2.5 minutes:

```bash
pip install -e ".[dev]"        # once
python3 -m pytest pipeline/tests/ -q          # unit + corpus regressions
mgs-validate projects/*/MyanmarGlyphSans-Regular.ttf   # 1,484-cluster audit
mgs-validate <font> --corpus pipeline/word_corpus.txt  # 711 real words
fontbakery check-universal --succinct -l FAIL <font>   # release QA
```

On a Mac you also get Apple's engine for free — `pytest` runs the
CoreText/HarfBuzz diff automatically once the shaper is built
(`pipeline/coretext/README.md`).

**If you change anything in `pipeline/` or a project file, rebuild and
commit the fonts.** The TTFs in `projects/` are checked in, and the
corpus tests run against those files, not against a fresh build:

```bash
python3 pipeline/make_variable.py projects/<family>/<name>.glyphstudio.json build/
python3 pipeline/postbuild.py build/*.ttf
cp build/<Family>-{Regular,Light,Bold}.ttf projects/<family>/
```

Two conventions worth knowing before you touch the shaping code:

* `pipeline/json_to_ufo.py` and `web/js/anchors.js` mirror each other —
  the studio previews what the pipeline will build. Change both or
  neither.
* Calibration values are **measured against Padauk**, not chosen. If you
  adjust one, say what you measured and how in the commit message; the
  existing comments show the format.

## Contributing with an AI assistant

Welcome, and read [CLAUDE.md](CLAUDE.md) first — point your assistant at
it too. It lists the invariants that are not obvious from the code: the
two files that must change together, which data files are generated,
when the committed fonts have to be rebuilt, and the shaping behaviour
that looks like a bug and is not. The house rule it opens with applies
to everyone, tool or not: **measure a typography claim against Padauk
before implementing it.**

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
