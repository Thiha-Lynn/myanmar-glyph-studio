# Design notes

Why this toolkit is shaped the way it is. Full background research (ecosystem
survey, glyph-count measurements, precedent analysis) lives in the project
blueprint; the load-bearing facts are summarized here.

## You don't draw syllables — you draw parts

Myanmar is a complex script. The shaping engine (HarfBuzz, DirectWrite,
CoreText) reorders each syllable cluster and asks the font for substitutions
(GSUB) and mark positions (GPOS). ကု is base + mark anchor; ကျ is a post-base
substitution; ကြ is engine reordering plus width variants; က္က is a `blwf`
subjoined substitution. Reference: the
[Microsoft Myanmar script spec](https://learn.microsoft.com/en-us/typography/script-development/myanmar).

Measured budgets (from official release binaries): SIL Padauk 6.000 covers
the entire script area — 40+ languages — with 827 glyphs; Noto Sans Myanmar
full build has 949; a Burmese-only font is ~400–650. Our starter inventory
(112 glyphs) covers Burmese; ethnic-language groups are roadmap.

## Why project JSON + UFO, not a custom binary

The `.glyphstudio.json` file keeps sketches portable and reviewable in PRs.
The pipeline converts it to UFO (one XML file per glyph — the git-native
industry standard), which unlocks the whole mature toolchain for free:
fontmake compiling, fontbakery QA, editing in Fontra/FontForge/Glyphs, and
the Google Fonts onboarding path (OFL 1.1 + fontbakery checks).

## Why the shaping rules are generated, not hand-written per font

The OpenType feature logic is the expert-level part and it is nearly the
same for every font. `json_to_ufo.py` generates the `mym2` starter rules
(`blwf`, `rphf`, `pres`, `blws`) from whichever glyphs a contributor drew,
and places default mark anchors so ufo2ft emits GPOS `mark`/`mkmk`.
Contributors only draw; the build system does the shaping. Verified in CI
spirit by shaping test strings with HarfBuzz against the built TTF.

## Style consistency

Every precedent that worked (Noto's reviewed foundry model, template-master
workshops, crowd-averaging experiments) solved style drift structurally.
Ours: dimmed guide skeletons at fixed metrics (trace = proportions match by
construction) plus the lead-designer rule in CONTRIBUTING.md.

## Metrics

1000 UPM; baseline 0; body height 550 (the height of the base letter circle,
≈ what x-height is to Latin); ascender +900; descender −600 (Myanmar stacks
go deep). Mirrored in `web/js/editor.js`, `web/js/store.js`, and
`pipeline/json_to_ufo.py` — change all three together or not at all.
