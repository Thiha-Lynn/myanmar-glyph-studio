# Claude for Open Source — application material

Prepared answers for <https://claude.com/contact-sales/claude-for-oss>.
Copy the sections you need into the form; keep every claim linked to
something public. Update the numbers (marked `‹…›`) on the day you submit.

**Repository:** <https://github.com/Thiha-Lynn/myanmar-glyph-studio>
**Live tool:** <https://thiha-lynn.github.io/myanmar-glyph-studio/>
**Gallery:** <https://thiha-lynn.github.io/myanmar-glyph-studio/gallery.html>
**Maintainer:** Thiha Lynn (GitHub `@Thiha-Lynn`)
**Licenses:** MIT (toolkit) · SIL OFL 1.1 (all fonts produced)

## Which category do you fit?

The program's five lanes, checked against this repo (verified against the
program page 2026-08-13 — it offers 6 months of Claude Max 20x):

| Lane | Bar | Us today | Fit? |
|---|---|---|---|
| Maintainers / library authors | 500+ dependent repos, 100+ dependent packages, or 200k+ monthly downloads | Not a registry package | ✗ |
| Core contributors | Committer on CPython/Rust/Node/Apache/CNCF-class projects | — | ✗ |
| Active contributors | 100+ merged PRs into repos you don't own, 12 mo | Check your own profile before claiming | likely ✗ |
| Community builders | 20+ unique external contributors merged, 12 mo | 0 external contributors yet | ✗ (goal) |
| Critical infrastructure | OpenSSF criticality ≥ 0.4 | Repo is days old; score will be ~0 | ✗ |

The program adds, verbatim: *"If you maintain something the ecosystem
quietly depends on, apply anyway and tell us about it."* **That is our
lane.** Answer honestly under it, and re-check the Community-builder lane
once the contributor count is real (see the checklist at the bottom).

Do **not** claim the download/dependent-count lanes — this is an
application and toolchain, not a package on npm/PyPI.

## One-paragraph pitch

> Myanmar Glyph Studio is the only browser-based font-creation tool for
> the Myanmar script. Myanmar script serves roughly 40 million readers
> across Burmese, Mon, Shan, S'gaw and Pwo Karen, Kayah, Pa'O, Palaung,
> Khamti and Aiton, yet the community has only a handful of free Unicode
> fonts and is still recovering from the Zawgyi/Unicode split that
> fragmented Burmese digital text for over a decade. Making a Myanmar
> font normally demands expert OpenType knowledge — the script needs
> contextual substitutions and mark positioning (`blwf`, `rphf`, `pres`,
> `blws`, GPOS `mark`/`mkmk`) before a single syllable renders correctly.
> This project removes that barrier: contributors trace ~150 glyph parts
> over dimmed guides in a browser (phone, tablet with Apple Pencil, or
> desktop), and the toolchain generates the shaping rules, mark anchors
> and UFO sources automatically, compiling with the same industry
> standard stack Google Fonts expects (fontmake, fontTools, fontbakery,
> HarfBuzz-verified proofs). Every font ships under the SIL Open Font
> License, so the output is permanently free for the whole community.

## Why it matters / who depends on it

* **An underserved writing system.** Compare ecosystem support: Latin has
  thousands of free fonts; Myanmar script has a handful (Padauk, Noto
  Myanmar, Pyidaungsu). Ethnic-minority languages of Myanmar are worse
  served still — this tool covers the entire Myanmar Unicode block plus
  Extended-A/B, so Shan, Mon, Karen, Kayah and Khamti communities can
  make their own typefaces.
* **No alternative exists.** Browser font editors (Glyphr Studio,
  FontStruct, Calligraphr) cannot produce complex-script shaping;
  professional tools (FontForge, Glyphs, FontLab) require expert
  OpenType work and desktop installs. Fontra is a strong browser editor
  but needs a local server and does not generate shaping rules.
* **Digital sovereignty.** Fonts are infrastructure: without them,
  publishing, education, and government material in these languages
  depend on a small number of foreign-maintained families.

## Engineering evidence (all public and linkable)

* **A written shaping specification, machine-checked.**
  [`docs/SHAPING_SPEC.md`](SHAPING_SPEC.md) states the model — anchor
  formulas with coordinates, glyph classes, GSUB order, a 50-unit
  collision protocol — and `pipeline/validate_spec.py` *measures* a font
  against it: two corpora, **1,486 synthetic clusters** (every consonant ×
  vowel × medial, stacks, kinzi, tall-aa, torture text, Mon/Shan/Karen)
  and **711 real Burmese words covering all 1,213 syllable clusters** in a
  12,451-word Wiktionary vocabulary. Findings are graded so a malformed
  test string can never mask a real defect. Results:
  [`docs/VALIDATION.md`](VALIDATION.md).
* **Verified on every shaping engine that matters, automatically.**
  Myanmar is composed by the text engine, not the font, so the same file
  can render differently on each platform. All three are now diffed
  against each other in software: HarfBuzz in CI (Android, Chrome, Linux);
  **CoreText** via a Swift shaper that runs as a test on any Mac
  (`pipeline/coretext/`); and **DirectWrite** via a C++ shaper calling
  `IDWriteTextAnalyzer` on a `windows-latest` runner, so Windows is
  covered on every pull request (`pipeline/directwrite/`). Chromium/Skia
  is checked through the browser. Current result: **6,363 cluster
  comparisons against Apple's engine and 6,363 against Microsoft's, zero
  rendering differences either way.** What is left for a person is
  judgement, not geometry — whether it *looks* right to a reader of
  Burmese — and the repo ships a
  [device-test page](https://thiha-lynn.github.io/myanmar-glyph-studio/devicetest.html)
  that walks anyone through it and writes the report.
* **Automated quality gates on every push and PR:** 62 tests
  (`pipeline/tests/`), both shaping corpora, a HarfBuzz regression that
  fails the build if the reference font drops any glyph, and fontbakery's
  universal profile gated on FAIL. See the
  [Actions tab](https://github.com/Thiha-Lynn/myanmar-glyph-studio/actions).
* **Real font engineering, not a wrapper:** stroke→outline expansion
  mirrored in JS and Python, generated `mym2` feature code, automatic
  mark anchors with in-browser anchor editing, virama synthesis,
  production glyph names, smart-dropout hinting, WOFF2 output.
* **Reproducible reference font:** `projects/sample/` is generated by
  skeletonizing Padauk through the same stroke pipeline a human uses —
  it proves stacks, kinzi, medial wraps and mark positioning end to end,
  with a committed proof sheet.
* **Letterform parity with the reference implementation.** Fifteen fused
  forms are traced from Padauk and driven by contextual rules, so the
  clusters Myanmar actually writes as one shape are drawn as one shape —
  wrap+vowel, wrap+wa, wa+ha, ha+vowel, the ja ligatures and the
  ja+wa+ha triple. Sixteen reference clusters now match Padauk's shaped
  structure glyph for glyph, verified by measurement rather than by eye.
* **Benchmarked, not self-graded.** The same harness run over the fonts
  the major platforms ship reports findings in each of them — Padauk 7,
  Noto Sans Myanmar 4, Microsoft's Myanmar Text 7 — while the fonts here
  clear both corpora at **0 FAIL, 0 WARN in every weight**. The corpus is
  strict enough to catch real defects in professional fonts.
* **Community-ready:** Code of Conduct, security policy with private
  reporting, Dependabot (grouped weekly updates), four issue templates
  (bug, shaping report, glyph claim, feature request), PR template,
  contributor guide, a full Burmese README (`README.my.md`), SUPPORT.md,
  CHANGELOG.md, CITATION.cff, per-family OFL compliance, topical labels,
  and tagged releases with installable font zips — GitHub community
  profile at 100%.
* **Installable software, not a folder of scripts:** `pip install
  myanmar-glyph-studio` gives ten command-line tools (build, variable
  build, proof, validate, CoreText diff, kerning, i18n check, …) with
  PEP 621 metadata and an SPDX licence expression; both corpora ship
  inside the wheel, so any font anywhere can be audited with one command.
* **A real editor, not a toy:** the studio ships professional vector
  tools (Bézier pen with permanently editable paths, selection with
  transform handles, node editing, cross-glyph copy/paste, snapping,
  partial eraser) in vanilla JS with no build step, fully translated
  into Burmese, working offline as a PWA on phones and tablets.

## How Claude would be used

* Extending shaping coverage to the remaining scripts and features that
  need expert OpenType work: GDEF mark classes, Myanmar Extended-C, and
  per-language shaping tests for Mon/Shan/Karen. (Kerning is done —
  measured from the drawn outlines, with tabular figures correctly
  excluded.)
* Reviewing community font submissions — reading proof sheets and
  fontbakery output to give contributors specific, kind feedback quickly
  (slow first-PR review is the main reason new contributors disappear).
* Writing Burmese-language documentation and tutorials; font-making
  education in Burmese barely exists.
* Building the accessibility and testing work the ecosystem needs:
  variable-font support, automated visual regression of glyph rendering.

## Metrics to fill in on submission day

| Metric | Where to read it | Value |
|---|---|---|
| Unique external contributors (12 mo) | Insights → Contributors | ‹…› |
| Merged PRs from non-owners | `is:pr is:merged -author:Thiha-Lynn` | ‹…› |
| Stars / forks / watchers | repo header | ‹…› |
| Fonts published in the gallery | `projects/` | ‹…› |
| Repository collaborators | Settings → Collaborators | ‹…› |
| Cluster comparisons passing, 3 engines | `docs/VALIDATION.md` | 6,363 / 6,363 |
| Release downloads | Releases page | ‹…› |
| Your own merged PRs to other repos (12 mo) | `is:pr is:merged author:Thiha-Lynn` | ‹…› |

## Before you submit — strengthen the application

1. ~~**Ship the first release**~~ ✅ Done — v0.1.0 … v0.4.0 tagged with
   installable font zips.
2. **Get external contributors.** The single highest-value action: run a
   glyph drive (see [LAUNCH.md](LAUNCH.md) §5). Even 3–5 merged glyph PRs
   from strangers changes the story from "personal project" to
   "community infrastructure"; 20 puts you in the Community-builder lane
   outright. **This is the main open gap — 4 `good first issue` tasks
   (#11–14) are staged and waiting for the visibility push.**
3. **Show usage:** a second community font family in the gallery, or a
   real product/site using a font made with the tool, is worth more than
   any adjective in the pitch. (Myanmar Glyph Sans exists but is
   maintainer-made — a font by someone else is the proof.)

   **Write the application from the engineering, not from the counters.**
   The verifiable claims are the strong part: a written specification a
   machine checks, two corpora totalling 2,195 clusters, three shaping
   engines in agreement, parity with the reference implementation
   measured cluster by cluster, and benchmark numbers that are better
   than the fonts the major platforms ship. None of that depends on
   star counts, and a reviewer can reproduce every one of them from a
   clean checkout in about five minutes.

   Do **not** pad the history to look busier — no synthetic commits, no
   commits authored under other people's accounts, no issues closed
   without the work behind them. A reviewer opens Insights first, and
   manufactured activity is both easy to spot and fatal to the honest
   case above. The repo's real weakness (young, one maintainer) is one
   the program explicitly invites you to state plainly; a padded history
   turns a candid application into a discredited one.
4. **Be candid about stage.** Say plainly that the project is days old,
   that you built it to fill a gap you personally hit, and what you will
   do with the support. The program explicitly invites this case — the
   age is only fatal if you hide it.
5. **Let the repo age a few weeks with visible activity** (merged PRs,
   answered Discussions, gallery growth) before submitting: every
   reviewer will open the Insights tab first.
