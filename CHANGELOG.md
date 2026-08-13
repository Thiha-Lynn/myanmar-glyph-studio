# Changelog

All notable changes to Myanmar Glyph Studio are documented here. The
format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions are git tags with installable font zips on the
[releases page](https://github.com/Thiha-Lynn/myanmar-glyph-studio/releases).

## [Unreleased]

### Added
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
