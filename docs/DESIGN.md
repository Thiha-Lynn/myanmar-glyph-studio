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
full build has 949; a Burmese-only font is ~400–650. Our inventory: 112
core glyphs cover Burmese, the extended groups add the rest of U+1000–109F
(Mon, Karen, Kayah, Shan, Pali, Palaung, Khamti, Aiton), and Extended-A/B
(Khamti Shan, Tai Laing, Shan Pali) plus U+25CC and optional Latin bring
the full sidebar to 343 entries. `pipeline/gen_inventory.py` generates the
extension data from the Unicode Character Database — regenerate, don't
hand-edit.

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
registered under the DFLT/mym2/mymr language systems, and places default
mark anchors — `top`/`bottom` on bases, `_top`/`_bottom` plus a stacking
anchor on marks — so ufo2ft emits GPOS `mark` *and* `mkmk`. Contributors
only draw; the build system does the shaping, and the studio's anchor mode
lets them adjust attachment points without a font editor. Verified in CI:
the build workflow shapes the whole test corpus with HarfBuzz against
every built TTF, fails if the sample font drops a glyph, and runs
fontbakery's universal profile.

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
