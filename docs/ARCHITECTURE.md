# Architecture — a map of the whole repository

What lives where, how a sketch becomes a font, and the places where two
files must change together. [DESIGN.md](DESIGN.md) explains *why* the
toolkit is shaped this way; this file is the *where*.

## The data flow

```
   draw in the browser                build on any machine                prove it
  ─────────────────────   ──────────────────────────────────────   ─────────────────────
   web/ (Glyph Studio)     pipeline/json_to_ufo.py                  pipeline/validate_spec.py
   strokes, anchors,   →   project JSON → UFO + generated       →   1,486-cluster spec corpus
   metadata as             mym2 GSUB/GPOS features                  + 711-word real-text corpus
   .glyphstudio.json       ↓                                        + fontbakery, CoreText,
                           fontmake → TTF                           DirectWrite comparisons
                           pipeline/make_variable.py                ↓
                           weight masters → statics + VF            pipeline/make_showcase.py
                                                                    make_gallery.py, make_book.py
                                                                    → web showcase / gallery /
                                                                      reading-proof pages
```

The studio and the pipeline never talk over a server. The **project JSON
file is the only interface** between them: the studio exports it, the
pipeline reads it. That is what lets contributors draw on a phone with no
install, and lets the build run identically in CI.

## `web/` — the Glyph Studio (static, zero build step)

| page | what it is |
| --- | --- |
| `index.html` | the drawing studio itself (PWA, works offline, `#g=<glyphName>` deep links) |
| `gallery.html` | download the built fonts, copy-ready `@font-face` kits, test-drive box |
| `showcase.html` | every hard cluster measured against Padauk; the full glyph inventory; the whole 12,450-word vocabulary as a browsable atlas |
| `book.html` | reading proof — a real Burmese orthography primer paged in the built font |
| `specimen.html` | type specimen set in Burmese |
| `devicetest.html` | self-service shaping test for readers on any device, writes a paste-ready report |

| module | job |
| --- | --- |
| `js/app.js` | boots the studio, sidebar, presets, project meta |
| `js/editor.js` | canvas, pointer routing, brush/line/rect/circle/eraser tools, undo (`ed._preSnapshot` → `ed.pushUndo()`) |
| `js/vectools.js` | select / direct-edit / bézier pen tools; bez strokes carry `bez` + `closed`, and `points` is always the flattened polyline the pipeline reads |
| `js/outline.js` | stroke → outline expansion (**mirrored in `pipeline/json_to_ufo.py`**), superellipse pen nibs |
| `js/anchors.js` | mark-anchor defaults and roles (**mirrored in `pipeline/json_to_ufo.py`**) |
| `js/fontexport.js` | quick in-browser TTF export via `vendor/opentype.min.js` (no shaping rules — the pipeline build is the real one) |
| `js/guidefont.js` | the dimmed tracing guide: bundled Padauk by default, or any font file the contributor loads (kept in IndexedDB, never uploaded) |
| `js/store.js` | project persistence, import/export, `fromJSON` restores the pen |
| `js/svgimport.js` | import filled SVG contours as `{fill:true}` strokes |
| `js/i18n.js` | UI languages; community packs land in `js/lang/` via `I18N.register` ([TRANSLATING.md](TRANSLATING.md)) |
| `js/gallery.js` | renders the gallery from `gallery-data/fonts.json` |
| `js/install.js` | PWA install prompt |
| `sw.js` | offline cache — **bump `VERSION` and extend `ASSETS` whenever any web file changes** |

`web/fonts/Padauk-Regular.ttf` is the unmodified SIL Padauk 6.000 (OFL
permits redistribution; it must never be subset or converted in place).
`web/gallery-data/` is a build product of `make_gallery.py`, not committed.

## `web/data/` — GENERATED files (regenerate, never hand-edit)

| file | generator |
| --- | --- |
| `glyphs.js` | hand-maintained core inventory (the one exception) |
| `glyphs-extended.js`, `glyphs-extended-ab.js` | `pipeline/gen_inventory.py` from the Unicode Character Database |
| `glyphs-latin.js`, `glyphs-latin-extra.js` | `pipeline/gen_inventory.py` |
| `showcase.js`, `vocabulary.js` | `pipeline/make_showcase.py` (vocabulary carries its own CC BY / CC BY-SA licence header — it is dataset text, not project source) |
| `book.js` | `pipeline/make_book.py` (Wikisource text, CC BY-SA header) |

## `pipeline/` — the build (a normal Python package)

| script | console command | job |
| --- | --- | --- |
| `json_to_ufo.py` | `mgs-build` | project JSON → UFO, generated `mym2` shaping (blwf/rphf/pres/blws/psts/abvs/dist), mark anchors, kerning hookup |
| `make_variable.py` | `mgs-variable` | weight masters by pen scaling → statics + variable font (the committed Regular/Light/Bold/VF all come from its `dist/<name>/variable/` output) |
| `make_sample.py` | `mgs-sample` | regenerate the sample/Sans projects from traced artwork; `--weight`, `--squircle`, `--pen` knobs |
| `make_kerning.py` | `mgs-kerning` | kerning measured band-by-band from the drawn outlines vs an HH control |
| `validate_spec.py` | `mgs-validate` | the shaping audit: FAIL/WARN/GAP/SPEC per cluster over both corpora |
| `shaping_diff.py` | — | shared engine-comparison logic + exclusion rules (unit-tested everywhere) |
| `coretext/` + `coretext_check.py` | — | Apple CoreText vs HarfBuzz diff (macOS only, pytest-gated) |
| `directwrite/` + `directwrite_check.py` | — | Microsoft DirectWrite vs HarfBuzz diff (Windows, runs in CI) |
| `fetch_vocab.py` | `mgs-fetch-vocab` | download the MWG dataset → 12,450-word sweep corpus (not committed — CC BY over CC BY-SA) |
| `make_showcase.py` | — | measure hard clusters vs Padauk → `web/data/showcase.js` + `vocabulary.js` |
| `make_gallery.py` | `mgs-gallery` | WOFF2 webfont kits + `fonts.json` manifest for the gallery |
| `make_book.py` | `mgs-book` | page a Wikisource book → `web/data/book.js` |
| `make_pdf.py` | — | typeset a Burmese book as a PDF in a built font |
| `make_reference.py` | — | build a reference corpus from a whole Wikisource category |
| `proof.py` | `mgs-proof` | visual shaping proof sheet (PNG) |
| `gen_inventory.py` | `mgs-inventory` | regenerate the extended glyph data files |
| `postbuild.py` | `mgs-postbuild` | post-fontmake TTF fixes |
| `i18n_check.py` | `mgs-i18n-check` | per-language translation gaps, `--todo` stubs, `--strict` for CI |
| `tests/` | `pytest` | the full suite CI gates on |

`spec_corpus.txt` (1,486 rows, blocks A–O) and `word_corpus.txt` (711 real
words — a greedy cover of all 1,213 syllable clusters in the vocabulary)
travel inside the wheel so `mgs-validate` works anywhere.

## `projects/` — the fonts themselves

One folder per family, each holding the project JSON (the source of truth),
`OFL.txt`, and the committed builds: `sample/` (the pipeline demo),
`myanmar-glyph-sans/` (468 glyphs, Light/Regular/Bold + VF, whole Myanmar
block + Ext-A/B + Latin-1), `bagan-display/` (squircle display face).

**When any shaping rule changes, rebuild every project's statics and VF via
`make_variable.py` and copy all four files out of `dist/<name>/variable/`** —
committed fonts going stale against the pipeline is a bug class this repo
has already shipped once (caught by `test_discovery_found_every_shipped_font`,
which finds every committed TTF by glob so none can be silently forgotten).

## Two files that must change together

These pairs are deliberately mirrored so the studio previews what the
pipeline will build. Change both or neither:

| if you touch | also touch |
| --- | --- |
| stroke→outline expansion, pen nibs (`web/js/outline.js`) | `pipeline/json_to_ufo.py` |
| anchor defaults or roles (`web/js/anchors.js`) | `pipeline/json_to_ufo.py` |
| metrics (1000 UPM, baseline 0, body 550, asc +900, desc −600) | both sides |
| any file under `web/` | `web/sw.js` (`VERSION` + `ASSETS`) |
| either corpus `.txt` | the per-engine comparison counts quoted in TESTING.md, VALIDATION.md, OSS_APPLICATION.md, README, CHANGELOG |
| shaping rules in `json_to_ufo.py` | rebuild the committed fonts in `projects/` |

## CI (`.github/workflows/`)

| workflow | what it gates |
| --- | --- |
| `build.yml` — `build` job | pytest (incl. the 1,486-cluster audit on every committed font), fontbakery universal FAILs, sample-font shaping with 0 missing glyphs. Required by branch protection. |
| `build.yml` — `directwrite` job | DirectWrite vs HarfBuzz on `windows-latest`, 0 differences required for Myanmar Glyph Sans |
| `pages.yml` | deploys `web/` to GitHub Pages |
| `release.yml` | release artifacts |

## Where to start

- **You draw**: open the studio, pick a glyph with a dotted guide, trace
  it. The showcase's *Every glyph* grid shows what nobody has drawn yet —
  each ✎ link opens that exact glyph. Export your project JSON and open a
  PR (or paste single glyphs with the ⚙ Copy/Paste snippets).
- **You speak a language the UI doesn't**: [TRANSLATING.md](TRANSLATING.md),
  then `mgs-i18n-check --todo <lang>` prints a paste-ready stub.
- **You know fonts or Python**: `pip install -e ".[dev]"`, run `pytest`,
  read [SHAPING_SPEC.md](SHAPING_SPEC.md) for the anchor formulas and GSUB
  order, [DEBUGGING.md](DEBUGGING.md) for the symptom table, and
  [VALIDATION.md](VALIDATION.md) for what "correct" is measured against.
