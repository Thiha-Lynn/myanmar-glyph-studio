# Changelog

All notable changes to Myanmar Glyph Studio are documented here. The
format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions are git tags with installable font zips on the
[releases page](https://github.com/Thiha-Lynn/myanmar-glyph-studio/releases).

## [Unreleased]

### Added
- **Shaping specification + validation harness**: the full shaping model
  is now written down ([docs/SHAPING_SPEC.md](docs/SHAPING_SPEC.md)) and
  machine-checked — `pipeline/validate_spec.py` shapes a 1,484-cluster
  corpus (`pipeline/spec_corpus.txt`, Blocks A–O: every consonant × vowel
  × medial combination, stacks, kinzi, tall-aa, torture sentences,
  Mon/Shan/Karen) with HarfBuzz and *measures* every cluster: coverage,
  virama consumption, kinzi fusion, e-vowel reordering, wrap geometry,
  mark attachment, Windows clipping limits, and pairwise mark collision
  (50-unit protocol). Findings are graded FAIL / WARN / GAP / SPEC so a
  malformed test string can never mask a real bug. Wired into pytest and
  CI; results in [docs/VALIDATION.md](docs/VALIDATION.md), triage tables
  in [docs/DEBUGGING.md](docs/DEBUGGING.md).
- **Real-vocabulary corpus** (`pipeline/word_corpus.txt`): 711 genuine
  Burmese words covering all 1,213 syllable clusters of the 12,451-word
  Myanmar Wiktionary vocabulary (via the CC-BY DatarrX Myanmar Word
  Glyphs dataset), validated alongside the spec corpus in CI. The
  harness was also run over the fonts the big platforms use — Padauk,
  Noto Sans Myanmar, Microsoft's Myanmar Text — and the shipped fonts
  are the only ones clearing both corpora with zero FAIL findings; a
  browser-engine (HarfBuzz+Skia) side-by-side against Padauk confirmed
  identical cluster structure end to end.

### Changed
- **Zero-WARN geometry pass**: the residual design-band and clearance
  warnings were closed at the source — an explicit wrap band (935,
  measured on Padauk) for ြ variants and ဩ ဪ with the wrap drawings
  lowered 6 units so Bold fits too; anchors measured on the unscaled
  reference drawing so every weight derives identical attachment
  coordinates (Bold marks no longer ride higher than Regular's); and
  pen-compensated side-chain gaps (55 + ~19 at Bold) so ink clearances
  meet the 50-unit protocol in every weight. All five shipped fonts now
  validate **0 FAIL, 0 WARN** on both corpora. Independent vowels gained
  proper AGL production names (uni1029/uni102A).

### Fixed
- **Seven anchor-engine defects found by the new corpora** (0 FAIL findings
  after; the same harness reports 7 in Padauk itself): stacks under
  descender bases sank into the next line (န္န at −890 — now clamped to
  the −50 floor, side-form swap extended to fire before subjoined forms);
  the long stack-vowels hung as marks (စက္ကူ's ူ at −1341 — now spacing
  glyphs beside the cluster, like Padauk's); full-height subjoined forms
  buried (ဇ္ဈ — now a spacing side-form, decided by measurement); marks
  after ာ/ါ floated off the cluster or past usWinAscent (ကော် ခေါ် ကာံ —
  spacing signs are now mark bases with a fixed-height top); vowels
  stacked ON the kinzi were clipped on Windows (သင်္ကြီ at 1345 — the
  kinzi now chains the next mark beside its hook like Padauk's fused
  glyphs); medials hung under stacks (က္ကွိ at −814 — stack marks now
  chain sideways); and — caught only by the real-vocabulary corpus — the
  kinzi collided with the vowel in kinzi+ya words (အင်္ကျီ: the vowel
  belongs to the ya, restarting the mark chain, so a synthesized
  `kinzi.left` variant substituted in abvs moves the kinzi clear, the
  way Padauk's fused glyphs do). Studio anchor preview mirrors the
  anchor changes; both shipped families rebuilt.
- **Padauk-parity shaping variants** ([#19]): six new drawable glyphs and
  the contextual rules that drive them — tall medial-ra wraps
  (`medialRa.tall` / `.tall.wide`, picked when ိ/ီ/ဲ sits over the
  wrapped base, so ကြီး's ring no longer crowds the hook), side-form
  bases (`na/nnya/ra-myanmar.alt`, the leg-free letters Padauk swaps in
  before below-marks: နု ညှ ရု), and the fused ိ+ံ ligature (ကိံ). All
  traced automatically by `make_sample.py`; both shipped fonts rebuilt
  with them.
- **Medial-cluster engine**: below-marks now chain *beside* each other
  (side/_side anchors) instead of stacking underneath; synthesized
  `.small` (in-wrap) and ya-tuck variants place ကျွ ကြွ ကျု လွှ ရွှံ့
  မြို့ correctly with no extra drawing. Base bottom anchors slide off
  descending tails (ညှန်).
- **Webfont kits in the gallery**: every font card now offers a WOFF2
  download and a *"</> Use on your site"* panel with a copy-ready
  `@font-face` snippet — correct `unicode-range` from the font's real
  coverage, and one variable-weight file when a VF build exists.
- Test-drive preset chips for the tricky medial clusters (studio and
  gallery), so a font's shaping rules can be exercised in one tap.

[#19]: https://github.com/Thiha-Lynn/myanmar-glyph-studio/issues/19
- **Contribute without Git**: ⚙ → *Copy glyph* turns the current glyph
  into a text snippet you can paste into an issue or chat; *Paste glyph*
  imports one — so a drawing can travel from any contributor to any
  project file with no repository knowledge.
- **Shareable glyph links**: the URL always carries `#g=<glyph>`, so an
  issue can send someone straight to the exact letter to draw.
- **Community language framework**: `I18N.register()` lets a single file
  under `web/js/lang/` add a full interface language (Mon, Shan, S'gaw
  Karen, …) with English fallback for missing strings — see
  `docs/TRANSLATING.md`. The language button now cycles through every
  registered language.
- Test-drive presets for Mon, Shan and S'gaw Karen sample text, and a
  five-minute real-device testing guide in `docs/TESTING.md`.

## [0.3.0] — 2026-08-13

### Added
- **Professional drawing tools** in the studio, Illustrator-style, while
  keeping the same portable project format (schema version 1):
  - Bézier **pen tool** (P): click corners, drag smooth curves, close
    paths, optional filled shapes; paths stay editable point by point
    (nodes are stored in an optional `bez` field, the flattened outline
    stays in `points`, so the pipeline reads old and new projects alike).
  - **Selection tool** (V): click or marquee, move, scale and rotate with
    handles, Shift constraints, Alt-drag duplicate, arrow-key nudges,
    flip, smooth, simplify, stroke re-widthing, and copy/paste that works
    **across glyphs**.
  - **Node editor** (D): drag anchor points and curve handles, add and
    delete points, corner/smooth toggle, reverse winding.
  - **Rectangle tool** (M), grid + metric-guide **snapping**, and a
    two-mode **eraser** (partial rub-through that splits strokes, or
    whole-stroke removal) with a size ring.
  - New UI: vertical tool rail with SVG icons, a contextual options bar
    per tool, a collapsible settings panel, Space/middle-drag panning —
    fully translated (English/Burmese) and responsive on phones.
- Community assets: this changelog, `CITATION.cff`, `SUPPORT.md`,
  a Burmese README (`README.my.md`), feature-request and shaping-report
  issue templates, grouped Dependabot updates.

## [0.2.0] — 2026-08-13

### Added
- **Myanmar Glyph Sans** — a complete 459-glyph community font family
  (Light/Regular/Bold + weight-variable), covering the whole Myanmar
  block, Extended-A/B, and full Latin-1, published in the gallery.
- Smooth cubic-curve outlines with adaptive decimation and corner
  detection (replacing dense polygon output).
- **Weight-variable font builds** from a single drawing
  (`pipeline/make_variable.py` scales the pen into masters).
- Explicit GDEF classes and kerning support in the pipeline.
- PWA install prompt; the studio works fully offline.

### Fixed
- Medial ra (ြ) rendering: the base consonant fell outside the wrap;
  wide-variant selection is now measurement-based and verified against
  Padauk's advances with uharfbuzz.
- Variable/static font naming so fontbakery passes both families.
- Per-family CI checks (each font family is validated separately).

## [0.1.0] — 2026-08-13

### Added
- First public release: the browser **Glyph Studio** (guided tracing over
  dimmed Padauk guides, stylus pressure, palm rejection, anchors editing,
  SVG import/export, draft TTF export, EN/MY interface, PWA offline).
- The **Python pipeline**: project JSON → UFO → fontmake TTF/WOFF2 with
  auto-generated mym2 shaping (blwf/rphf/pres/blws, GPOS mark/mkmk),
  virama synthesis, automatic mark anchors, HarfBuzz proof sheets.
- Complete glyph inventory: full Myanmar block U+1000–109F plus
  Extended-A/B (generated from the UCD) and optional Latin groups.
- CI quality gates: pipeline unit tests, a HarfBuzz shaping regression,
  fontbakery (universal profile, FAIL-gated); tagged releases ship
  installable zips (TTF + WOFF2 + proof sheet).
- The reproducible **sample font** (Padauk skeletonized through the same
  stroke pipeline a human uses) proving stacks, kinzi, medial wraps and
  mark positioning end to end.
- Community health files, the contributor guide, the gallery site, and
  GitHub Pages deployment.

[0.3.0]: https://github.com/Thiha-Lynn/myanmar-glyph-studio/releases/tag/v0.3.0
[0.2.0]: https://github.com/Thiha-Lynn/myanmar-glyph-studio/releases/tag/v0.2.0
[0.1.0]: https://github.com/Thiha-Lynn/myanmar-glyph-studio/releases/tag/v0.1.0
