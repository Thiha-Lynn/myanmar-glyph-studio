# Shaping validation report

Fonts under test: **Myanmar Glyph Sans** Light / Regular / Bold / VF and
**Glyph Studio Sample** Regular, as committed in `projects/` (build of
2026-08-16). Method: every string of the shaping specification corpus —
`pipeline/spec_corpus.txt`, 1 484 clusters across test Blocks A–O — is
shaped with HarfBuzz and measured by `pipeline/validate_spec.py` per the
checks in [SHAPING_SPEC.md §6](SHAPING_SPEC.md). Reference font for every
disputed judgement: SIL Padauk 6.000.

Regenerate this data any time:

```bash
cd pipeline
python3 validate_spec.py ../projects/myanmar-glyph-sans/MyanmarGlyphSans-Regular.ttf --verbose
```

A second corpus grounds the synthetic blocks in real usage:
`pipeline/word_corpus.txt` (Block W) — 711 genuine Burmese words chosen
by greedy set cover so that together they contain **all 1 213 distinct
syllable clusters** found in the 12 451-word Myanmar Wiktionary
vocabulary of the [DatarrX Myanmar Word Glyphs
dataset](https://huggingface.co/datasets/DatarrX/myanmar-word-glyphs)
(CC BY 4.0). The full 12 450-word vocabulary was also run once in full
during triage. (For scale context: the Myanmar OCR literature counts
1 881+ theoretically composable glyph shapes from 75 characters; real
vocabulary uses the 1 213 measured here.)

## Result summary

**0 FAIL findings in all five fonts, on both corpora.** For calibration,
the identical harness was run over the fonts the big platforms render
Myanmar with. Ours is the only one that clears both corpora clean:

| Font (engine context) | Spec corpus | Word corpus |
| :--- | :--- | :--- |
| **Myanmar Glyph Sans Regular** | **0 FAIL** | **0 FAIL** |
| Padauk 6.000 (SIL reference) | 7 FAIL — 5 mark collisions in ြ+ှ clusters, 2 unattached tone dots after ဌ | 1 FAIL |
| Noto Sans Myanmar (Google Docs/Android family) | 4 FAIL | 0 FAIL |
| Myanmar Text 1.10 (Microsoft Word/Windows font) | 7 FAIL | 4 FAIL |
| PDA18-Stone (legacy PUA-ligature font) | 267 FAIL | 142 FAIL |

Benchmark numbers use each font's own OS/2 clipping metrics and are
read with the caveat that some checks (attachment distance, wrap
overhang) are calibrated to this pipeline's conventions; the corpus is
strict enough to catch real defects in professional fonts, and these
fonts clear it.

| Block | What it exercises | Cases | Myanmar Glyph Sans Regular |
| :--- | :--- | ---: | :--- |
| A | basic consonant + vowel/medial | 66 | **PASS** (6 wrap-height notes) |
| B | descender bases + side-form vowels (နု ရု) | 66 | **PASS** |
| C | medial ya + below vowel (ကျု ကျူ) | 66 | **PASS** |
| D | ra-wrap narrow/wide/tall variants | 34 | **PASS** (design-band notes, §below) |
| E | stacked consonants, all types | 43 | **PASS** |
| F | kinzi, all combinations | 24 | **PASS** |
| G | anusvara + dot-below + vowel stacking | 132 | **PASS** |
| H | "left-side vowel" rows (see §spec issues) | 134 | **PASS** — all rows SPEC-invalid |
| I | tall-aa rule (ခါ vs ကာ) | 38 | **PASS** |
| J | complex multi-mark clusters | 9 | **PASS** |
| K | Mon / Shan / S'gaw Karen | 48 | **PASS** (9 rows are not Myanmar script) |
| L | torture sentences, all rules combined | 7 | **PASS** |
| M | complete consonant × vowel matrix | 429 | **PASS** |
| N | complete medial combination matrix | 258 | **PASS** |
| O | asat on every stack type | 130 | **PASS** |

Light and VF match Regular exactly (195 WARN / 145 SPEC / 0 FAIL each).
Bold reports the same statuses with 312 WARNs — the heavier pen pushes
wrap and kinzi ink a few units further past the *design* ascender (940
vs 930), all still ~160 units inside the clipping box.

## What the WARNs are

* **Design-band exceedances (182).** Every ra-wrap variant tops out at
  927–931 against the 900 design ascender. Padauk's own wraps sit at
  932–933; this is a property of the script's geometry, not a defect.
  Nothing in any font approaches the real limits (+1100/−750).
* **Tight clearances (13).** ွ vs ု in the ...ွို stacks measure 42
  units against the spec's 50 (Padauk's equivalent clusters measure
  similarly); one 43-unit gap in က္ကွိ. Cosmetic tuning candidates.

## Defects found by these corpora and fixed (2026-08-16)

The first run against the previously shipped fonts reported **794
FAILs**; six root causes in the anchor engine, plus a seventh that only
the real-vocabulary corpus caught. All now regression-tested
(`pipeline/tests/`):

1. **Stacks under descender bases** (န္န at −890, ဋ္ဌ at −831 …): the
   stack anchor followed the base's leg. Now clamped to the same −50
   floor the below-vowels use, and the side-form base swap (နု→န.alt)
   extended to fire before subjoined forms as Padauk does.
2. **Long stack-vowels treated as marks** (စက္ကူ's ူ at −1341): the
   body-height `u/uu.alt` forms are now spacing glyphs standing beside
   the cluster (Padauk's spacing uni1030, advance 288).
3. **Full-height "subjoined" forms buried** (ဇ္ဈ at −916): a `.sub`
   drawn at body height is now a spacing side-form, decided by
   measurement.
4. **Marks after spacing signs floating** (ကော်'s ် 262 units off the
   cluster; ကာံ): ာ ါ etc. now carry top/bottom anchors — with a fixed
   `top` height, because following ါ's stem put the asat at 1303, past
   usWinAscent (ခေါ် ပေါ် — Windows clipped it).
5. **Above-marks stacked over the kinzi** (သင်္ကြီ's ီ at 1345,
   clipped): the kinzi now chains the next mark beside its hook, to the
   right, as Padauk's fused kinzi+vowel glyphs do.
6. **Medials hung under stacks** (က္ကွိ's ွ at −814): stack marks now
   chain sideways like every other below-form.
7. **Kinzi colliding with the vowel in kinzi+ya clusters** (အင်္ကျီ
   "shirt", သင်္ချိုင်း — found only by the word corpus, in 19 common
   words): the vowel attaches to the ya, a *base* glyph, so the mark
   chain restarts and the vowel cannot chain beside the kinzi — the two
   marks overlapped by ~40 units. A synthesized `kinzi.left` variant
   (same ink, attachment anchor offset so GPOS pulls it 250 units left),
   substituted in `abvs` when a ya follows, reproduces the geometry of
   Padauk's fused kinzi+vowel glyphs.

Every fix was verified against Padauk's shaped geometry before/after,
and the studio's anchor preview (`web/js/anchors.js`) mirrors them all.

## Spec-file issues found (reported as SPEC, not failures)

The test document itself contains malformed rows, which the harness
quarantines so they can never mask a real bug:

* **All 134 Block H rows** ("Left-Side Vowels") are written with ေ
  *before* the consonant (ေက). Unicode stores dependent vowels after
  their consonant (ကေ); the reordering is the renderer's job — which
  Block M's ~100 correctly-ordered ေ-cases verify. Every shaper shows
  these rows with a dotted circle; so does Padauk.
* **9 Block K "S'gaw Karen" rows** use U+A930–A938 — Rejang script, not
  Myanmar S'gaw Karen (U+1060s/Ext-A). No Myanmar font can shape them.
* Block G's အံု (vowel stored after the anusvara) and Block L's ပ marked
  with the Western Pwo Karen tone U+106A carry dotted circles for the
  same storage-order reason.

## Performance

Shaping the full corpus (4 837 glyphs from 1 484 clusters), Apple
Silicon, uharfbuzz 0.56:

| Metric | Value |
| :--- | :--- |
| Whole-corpus shaping time | 9 ms |
| **Per 1 000 glyphs** | **1.9 ms** |
| Full geometry validation (collision pass included) | ~5 s |

## Edge-case confirmations

Measured in the shipped Regular (spot values, font units):

* ကျု — the vowel sits beside the ya leg at dy +30, not hanging (was −392)
* ကျွ = ျ.beforewa + ွ at dx 450: tucked under the base
* ကြီး = ြ.tall.wide, advances 168 / 979 / 0 / 254
* နု = န.alt; ရု = ရ.alt but ရွ stays plain (Padauk's split)
* ကိံ = the drawn ိံ ligature; မြို့ = ြ.tall + ု.small
* ရွှံ့ — tone dot at dy +32 (once −748); လွှ — ha beside wa, tops aligned
* ZWNJ/ZWSP sequences: glyph-for-glyph identical to Padauk

## Production-engine rendering check

Beyond uharfbuzz, the shipped Regular was rendered side by side with
Padauk through a real browser text stack (Chromium: HarfBuzz + Skia — the
same shaping-and-rasterizing pipeline Google Docs text renders through)
via `@font-face`, across the fixed clusters, the wrap narrow/wide split,
kinzi+ya words, and the torture sentences. Every row matched Padauk's
cluster structure; the GSUB/GPOS tables drive the production engine the
same way they drive the CLI shaper.

Real-device verification (DirectWrite, CoreText) remains a manual step —
[issue #14](https://github.com/Thiha-Lynn/myanmar-glyph-studio/issues/14)
— since only HarfBuzz runs in CI.
