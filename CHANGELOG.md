# Changelog

All notable changes to Myanmar Glyph Studio are documented here. The
format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions are git tags with installable font zips on the
[releases page](https://github.com/Thiha-Lynn/myanmar-glyph-studio/releases).

## [Unreleased]

### Added
- **Rendering showcase** ([web/showcase.html](web/showcase.html), data from
  [`pipeline/make_showcase.py`](pipeline/make_showcase.py)): 60 hard
  clusters — the four shapes of တစ်ချောင်းငင်, narrow/wide/tall ရရစ် wraps,
  fused medials, stacks and kinzi — rendered in the generated webfont
  beside the font its outlines were traced over, plus real words and a
  free-typing box. Every row carries the glyphs the shaper actually
  produced, the cluster's advance and ink box, and the distance to the
  reference in units of a 1000 em; the eleven rows more than 40 units out
  are highlighted rather than hidden, because at that size the difference
  is a drawing decision and a reader should get to judge it. Comparison is
  by measurement, never by glyph name — the two fonts solve the same
  cluster with differently-named glyphs, and a name diff would report
  differences nobody can see.
- **Full-vocabulary sweep** ([`pipeline/fetch_vocab.py`](pipeline/fetch_vocab.py),
  `mgs-fetch-vocab`): downloads all 12,450 words of the DatarrX Myanmar
  Word Glyphs vocabulary and writes them as a corpus `validate_spec.py`
  can read. CI still gates on the committed 711-word cover; this exists to
  test *the cover*, and so far it has never found anything the cover
  missed. Not committed and not in the gating path — the parquet is 41 MB
  and vendoring someone else's dataset raises a licensing question this
  repo does not need to answer.
- **DirectWrite verified automatically — the last engine that needed a
  human** ([pipeline/directwrite/](pipeline/directwrite/)): issue #14 asks
  that the fonts be checked on HarfBuzz, CoreText and DirectWrite, and
  DirectWrite was recorded as unreachable by automation. It is not:
  GitHub's `windows-latest` runner is a real Windows box with the real
  engine and MSVC already installed. `DirectWriteShape.cpp` calls
  `IDWriteTextAnalyzer::GetGlyphs` + `GetGlyphPlacements` — the actual
  OpenType shaping engine, the path `IDWriteTextLayout` uses internally —
  and `directwrite_check.py` diffs its glyph run against HarfBuzz's on
  every pull request. Result for the shipped family: **6,363 cluster
  comparisons across both corpora in all three weights, zero rendering
  differences.** Going through the analyzer rather than a layout keeps the
  font under test the only font in play, so a character it lacks comes
  back as glyph 0 and compares straight against HarfBuzz's `.notdef`.
- The cross-engine comparison moved into
  [`pipeline/shaping_diff.py`](pipeline/shaping_diff.py), shared by the
  CoreText and DirectWrite checkers, and its exclusion rules are now unit
  tested on every platform — including the Linux runner, where neither
  engine exists. Two new rules came out of what Windows actually did:
  a **blank where HarfBuzz draws `.notdef`** is the two engines saying
  "this font has no glyph here" differently, and a **blank inserted where
  HarfBuzz inserted nothing** is repair for malformed input in a font with
  no U+25CC glyph. Both are gated so that a blank replacing real ink, or
  one that shifts the rest of the cluster along, is still reported.

### Fixed
- **The two variable fonts were shipping the pre-2026-08-16 build.** Every
  anchor fix from that day landed in the static TTFs and in neither VF,
  and they stayed committed that way for three days: stacks sinking past
  usWinDescent, asat detaching from its base, kinzi colliding with the
  vowel — **437 FAILs across the full vocabulary, 79 on the spec corpus**.
  VALIDATION.md claimed "all weights + VF: 0 FAIL, 0 WARN" the whole time.
  Both are rebuilt and both now measure clean on all three corpora.

  Neither corpus was at fault — either would have caught this on the first
  run. `SHIPPED` in `tests/test_spec_validation.py` was a hand-written
  list of four statics, and a shipped font that is not on the list is not
  tested. It is now a glob over `projects/`, so a font can be forgotten
  only by being deleted, with a companion test naming the six files that
  must be discovered — a glob that matches nothing would otherwise turn
  every parametrised test below it into a silent pass.
- **ကွှု kept the curl where ကျှု correctly took the tall stroke.** After
  a medial ya or wa, ု/ူ is the tall spacing stroke, and the rule is meant
  to reach through an intervening ha. It did so after ya and not after wa,
  because the fused `medialWa-myanmar.ha` was missing from the blws
  context — and adding it there was only half the fix: the wa medials are
  **marks**, and a `UseMarkFilteringSet` skips every mark outside it, so a
  fused wa the rule matches on has to be in the set too. The ya ligatures
  never needed that entry, being spacing glyphs no filtering set can hide,
  which is precisely how half the rule worked and concealed the other
  half. The whole ျ/ွ/ှ × ု/ူ matrix — 14 combinations — now agrees with
  Padauk on which form each takes.

  Found by the showcase's comparison, not by either corpus: both score
  0 FAIL here, since a vowel in the wrong contextual form is still
  perfectly positioned, and the combination occurs in **0 of the 12,450**
  vocabulary words. Geometry checks cannot see a form error.
- **A missing hyphen was being excused as "not Myanmar text".** The
  validator sorted every uncovered non-Myanmar character into a SPEC
  bucket meaning *the test datum is malformed* — a rule that exists
  because the corpus once carried Rejang letters. Punctuation is the
  opposite case: Burmese prose contains hyphens (၈-ပါး), full stops and
  dashes, so a font that cannot draw one renders a tofu box a reader
  actually sees. Letters from another script still report SPEC; shared
  punctuation and digits now report GAP, which is what they are. This
  surfaced two real, previously hidden gaps — U+002D in the sample font
  and U+2012 FIGURE DASH in Myanmar Glyph Sans.
- **Block K now tests S'gaw Karen instead of Rejang.** The nine spec-corpus
  rows labelled "S'gaw Karen" carried U+A930–A938 — Rejang letters, a
  different script on a different continent, which no Myanmar font should
  cover. They tested nothing. Replaced with the characters S'gaw Karen
  actually adds to the Myanmar block (U+1061 SHA, U+1062 vowel EU, U+1063
  tone HATHI, U+1064 tone KE PHO) in the combinations they occur in —
  တၢ်, ယွၤ, ပှၤ, အိၣ်, မ့ၢ်. Block K is 50 rows and the shipped family
  passes all of them, so a block that was documented as partly untestable
  now tests what its label claims. The DirectWrite check surfaced it: the
  old rows looked like nine Windows disagreements and were a corpus bug.
- The engine reports print in UTF-8, so a Windows console can show the
  Myanmar cluster it is reporting instead of dying on `cp1252`.

### Added
- **Kerning, measured from the drawn outlines** (`mgs-kerning`): the fonts
  carry full Latin next to Myanmar — Burmese runs with English words in
  it constantly — and shipped with none, which fontbakery flagged
  (`lacks-kern-info`). The generator walks both outlines band by band,
  finds where two letters actually face each other, and compares that
  with the air a flat-sided control pair (HH) leaves; open shapes get
  pulled in by the difference. 101 pairs in Myanmar Glyph Sans. Two
  guards learned the hard way: corrections are scaled by how much of the
  taller glyph the two actually face (without it a period tucks under a
  P's bowl), and **digits are excluded** because these figures are
  tabular and kerning them breaks column alignment. Myanmar itself is
  never kerned — fixed advances plus mark attachment.

## [0.4.0] — 2026-08-16

### Added
- **Shaping specification + validation harness**: the full shaping model
  is now written down ([docs/SHAPING_SPEC.md](docs/SHAPING_SPEC.md)) and
  machine-checked — `pipeline/validate_spec.py` shapes a 1,486-cluster
  corpus (`pipeline/spec_corpus.txt`, Blocks A–O: every consonant × vowel
  × medial combination, stacks, kinzi, tall-aa, torture sentences,
  Mon/Shan/Karen) with HarfBuzz and *measures* every cluster: coverage,
  virama consumption, kinzi fusion, e-vowel reordering, wrap geometry,
  mark attachment, Windows clipping limits, and pairwise mark collision
  (50-unit protocol). Findings are graded FAIL / WARN / GAP / SPEC so a
  malformed test string can never mask a real bug. Wired into pytest and
  CI; results in [docs/VALIDATION.md](docs/VALIDATION.md), triage tables
  in [docs/DEBUGGING.md](docs/DEBUGGING.md).
- **The pipeline is an installable package**: `pip install
  myanmar-glyph-studio` gives nine console tools — `mgs-build`,
  `mgs-variable`, `mgs-proof`, `mgs-validate`, `mgs-sample`,
  `mgs-gallery`, `mgs-inventory`, `mgs-postbuild`, `mgs-i18n-check`.
  Full PEP 621 metadata with an SPDX license expression; both shaping
  corpora ship inside the wheel, so `mgs-validate <font>` works from any
  directory with no checkout. The modules stay in `pipeline/`, so every
  documented clone-and-run invocation keeps working unchanged.
- **Device shaping test page** (`web/devicetest.html`): renders the 25
  clusters this project has ever got wrong, says what correct looks like
  for each, and writes a paste-ready bug report — the DirectWrite and
  CoreText check CI can never do ([#14]). Works offline; phone-friendly.
- **Translation checker** (`mgs-i18n-check`): untranslated keys fall back
  to English silently, so a half-finished language looks complete; this
  prints the gap per language and `--todo <lang>` emits a paste-ready
  stub of what is missing ([#13]).
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
- CI: the required `build` check now runs on every pull request. It was
  filtered to `projects/**` and `pipeline/**`, so a web- or docs-only PR
  never produced the check branch protection required — and a required
  check that never runs blocks the merge forever.
- **The Padauk medial fusion set is complete**: nine more traced fused
  glyphs finish the job the previous six started — the wrap+wa set
  (ကြွ ပြွ ကြွီ, `uni103C103D`, the wa nested inside the sweep instead of
  drawn on top of it), the wa+ha hook and its in-wrap copy (ကွှ ရွှ လွှ
  ညွှန်း ရွှံ့ / မြွှေ ကြွှ, `uni103D103E`), ha+vowel (ရှု ရှူ,
  `uni103E102F` / `uni103E1030`) and the ja+wa+ha triple (ကျွှ,
  `uni103B103D103E`). The three fusion lookups cascade in a fixed order —
  wa+ha, then ja, then ha+vowel — which is what makes ကြွှ keep Padauk's
  plain wrap and လျှု keep its tall vowel; the side-form base swap now
  also fires in front of the fused hook (ရွှ ညွှန်း ရွှံ့). Sixteen
  reference clusters now match Padauk's structure glyph for glyph.
- **Six traced fused glyphs for the woven clusters** (user-reported
  rendering quality): overlaying separately-drawn pieces crossed their
  strokes, so the clusters Padauk hand-fuses are now traced as fused
  drawings too — the four wrap+u forms (ပြု ကြု မြို ကြို: retracted
  sweep with the u bar standing in the opening, substituted in two psts
  steps with an invisible ghost consuming the ု) and the two ja
  ligatures (ကျွ လျှ: hook, leg and medial as one woven drawing, fused
  in pres). Editable in the studio like any variant; fonts without them
  fall back to the previous synthesized forms.
- **တစ်ချောင်းငင် takes its correct form in every context** (user-reported
  form gap): after ja/wa the vowel is now the tall straight stroke
  standing after the medial (ကျု မွု — Padauk's spacing uni102F), inside
  wraps it is a straight bar hanging from the under-sweep (ကြု မြို —
  Padauk's fused uni103C102F, reproduced by one synthesized mark), and
  ူ after a wrap stands tall after the cluster (ကြူ). ja/wa clusters carrying a ha take the tall
  stroke too (လျှု ကျှု မွှူ, as Padauk does), while true curl contexts
  stay curls (ကု, နု ရု, ရှု — where ရ now also swaps to its side form
  across the ha, matching Padauk). Narrow/wide wrap selection re-audited: 32/33
  agree with Padauk; ဠြ deliberately narrow (measured fit, and absent
  from the vocabulary).
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

[#13]: https://github.com/Thiha-Lynn/myanmar-glyph-studio/issues/13
[#14]: https://github.com/Thiha-Lynn/myanmar-glyph-studio/issues/14
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
