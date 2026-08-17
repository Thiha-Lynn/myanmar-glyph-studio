# Shaping validation report

Fonts under test: **Myanmar Glyph Sans** Light / Regular / Bold / VF and
**Glyph Studio Sample** Regular **and VF**, as committed in `projects/`
(build of 2026-08-17). Method: every string of the shaping specification corpus —
`pipeline/spec_corpus.txt`, 1 486 clusters across test Blocks A–O — is
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
(CC BY 4.0). (For scale context: the Myanmar OCR literature counts
1 881+ theoretically composable glyph shapes from 75 characters; real
vocabulary uses the 1 213 measured here.)

A third corpus is the **whole** of that vocabulary — all 12 450 words,
not the cover drawn from it. It is fetched rather than committed, since
vendoring somebody else's dataset raises a licensing question this repo
does not need to answer:

```bash
cd pipeline
pip install pyarrow
python3 fetch_vocab.py                    # 41 MB, writes build-vocab/
python3 validate_spec.py ../projects/myanmar-glyph-sans/MyanmarGlyphSans-Regular.ttf \
        --corpus build-vocab/mwg_vocab_corpus.txt
```

The wide sweep exists to test the *cover*, not the font: if 711 words
chosen for cluster coverage really do stand in for 12 450, the two runs
have to agree. They do — the full vocabulary has never produced a
finding the cover missed. That is a result about corpus design, and it
is why CI still gates on the small offline one.

## Result summary

**0 FAIL and 0 WARN findings in all six fonts, on all three corpora** —
every cluster shapes and positions inside the measured
bands with full clearances, in every weight. For calibration,
the identical harness was run over the fonts the big platforms render
Myanmar with. Ours is the only one that clears both corpora clean:

| Font (engine context) | Spec corpus | Word corpus | Full 12 450-word vocabulary |
| :--- | :--- | :--- | :--- |
| **Myanmar Glyph Sans** (all weights + VF) | **0 FAIL, 0 WARN** | **0 FAIL, 0 WARN** | **0 FAIL, 0 WARN** |
| **Glyph Studio Sample** (Regular + VF) | **0 FAIL, 0 WARN** | **0 FAIL, 0 WARN** | **0 FAIL, 0 WARN** |
| Padauk 6.000 (SIL reference) | 7 FAIL — 5 mark collisions in ြ+ှ clusters, 2 unattached tone dots after ဌ | 1 FAIL | 5 FAIL |
| Noto Sans Myanmar (Google Docs/Android family) | 4 FAIL | 0 FAIL | not run — font not on the test machine |
| Myanmar Text 1.10 (Microsoft Word/Windows font) | 7 FAIL | 4 FAIL | not run — font not on the test machine |
| PDA18-Stone (legacy PUA-ligature font) | 267 FAIL | 142 FAIL | 2 219 FAIL |

Benchmark numbers use each font's own OS/2 clipping metrics and are
read with the caveat that some checks (attachment distance, wrap
overhang) are calibrated to this pipeline's conventions; the corpus is
strict enough to catch real defects in professional fonts, and these
fonts clear it.

| Block | What it exercises | Cases | Myanmar Glyph Sans Regular |
| :--- | :--- | ---: | :--- |
| A | basic consonant + vowel/medial | 66 | **PASS** |
| B | descender bases + side-form vowels (နု ရု) | 66 | **PASS** |
| C | medial ya + below vowel (ကျု ကျူ) | 66 | **PASS** |
| D | ra-wrap narrow/wide/tall variants | 34 | **PASS** |
| E | stacked consonants, all types | 43 | **PASS** |
| F | kinzi, all combinations | 24 | **PASS** |
| G | anusvara + dot-below + vowel stacking | 132 | **PASS** |
| H | "left-side vowel" rows (see §spec issues) | 134 | **PASS** — all rows SPEC-invalid |
| I | tall-aa rule (ခါ vs ကာ) | 38 | **PASS** |
| J | complex multi-mark clusters | 9 | **PASS** |
| K | Mon / Shan / S'gaw Karen | 50 | **PASS** |
| L | torture sentences, all rules combined | 7 | **PASS** |
| M | complete consonant × vowel matrix | 429 | **PASS** |
| N | complete medial combination matrix | 258 | **PASS** |
| O | asat on every stack type | 130 | **PASS** |

## How the last WARNs were engineered away

The first clean-FAIL build still carried ~195 WARNs per font (more in
Bold); each class was closed at the source rather than by relaxing a
check:

* **Wrap heights.** The wrap is the script's one legitimate
  ascender-breaker (its hook must rise around the ring it wraps), so the
  spec now carries an explicit **wrap band of 935** — measured on
  Padauk, whose wraps top at 932–933 — for ြ variants and the wrap-sweep
  letters ဩ ဪ. The wrap and ဩ/ဪ drawings were also lowered 6 units so
  every master, Bold included, fits the band (Regular 924, Bold ≈934).
* **Fixed anchors across weights.** Anchors are now measured on the
  unscaled reference drawing, so Light/Regular/Bold derive identical
  attachment coordinates — Bold's marks no longer ride 10–20 units
  higher than Regular's, which is what had pushed them past the band.
* **Clearances in every weight.** The below-mark side chain steps 55
  units (protocol 50 + margin), and horizontal chain gaps grow with the
  pen (+19 at Bold) so the *ink* gap meets the protocol in Bold too
  (ွ-ု in မွို: was 42, now 57 in Regular and 55+ in Bold).

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

## Defects found and fixed (2026-08-17)

### The variable fonts were shipping the pre-fix build

Every fix listed above landed in the static TTFs and **not** in the two
committed variable fonts, which had last been rebuilt on 2026-08-15.
They stayed that way for three days: stacks sinking past usWinDescent,
asat detaching, kinzi colliding — 437 FAILs across the full vocabulary,
79 on the spec corpus. This table said "all weights + VF: 0 FAIL, 0
WARN". It was measured; it was measured on files that were not the ones
being shipped.

Nothing was wrong with the corpora — either of them would have caught
this on the first run. The gate simply never pointed at those two files:
`SHIPPED` in `tests/test_spec_validation.py` was a hand-written list of
four statics. A shipped font that is not on the list is not tested, and
nothing anywhere said the list had to be complete.

The list is now a glob over `projects/`, so a font cannot be shipped
without being tested — only deleted. A companion test names the six
files that must be discovered, because a glob that matches nothing turns
every parametrised test below it into a silent pass.

### ကွှု kept the curl while ကျှု took the tall stroke

Found by the showcase's row-by-row comparison against Padauk
(`pipeline/make_showcase.py`), not by either corpus: both report 0 FAIL
here, because the wrong vowel *form* is still perfectly positioned, and
the combination appears in **0 of the 12 450** vocabulary words.

The tall-stroke rule (below) is supposed to reach through an intervening
ha. It did after a medial ya and not after a medial wa. Two reasons,
both introduced when the fused medials were traced:

* `medialWa-myanmar.ha` was missing from the blws context class, so once
  pres fused wa+ha there was no `medialWa-myanmar` left to match.
* Adding it to the class was not enough. The wa medials are **marks**,
  and a `UseMarkFilteringSet` skips every mark outside it — so a fused
  wa the rule needs to match on must be in the *set* as well. The ya
  ligatures needed no such entry: they are spacing glyphs, which a
  filtering set cannot hide. That asymmetry is exactly why half the rule
  worked and hid the other half.

Now regression-tested on both halves, and the full ျ/ွ/ှ × ု/ူ matrix —
14 combinations — agrees with Padauk on which form each takes.

### One syllable running into the next

Every check above measures a cluster against itself, and that is how a
whole class of defect stayed invisible: **50 of the 12,450 vocabulary
words had one syllable's ink drawn through the next one's.** Reported by
a reader looking at rendered words, not by any test here.

Two causes, both now fixed, and the count is down to **11 against
Padauk's 7** — four of our eleven being words Padauk fails on too
(ဂန္ထန္တရ, ဉက္ကာပျံ, ရွှံ့ဗွက်, ဝင်္ကန္တဉာဏ်):

1. **ဉ had no narrow form.** The letter carries 838 units of ink inside a
   555 advance, so its tail simply ran into whatever followed —
   `စဉ်ကြယ်`, `ငါးရှဉ့်ပုန်း`. Padauk swaps in **uni1025** before the
   asat, a below-vowel or a subjoined letter, and leaves ဉွ ဉျ ဉံ ဉီ on
   the plain letter. We now do the same, and the glyph was already drawn.
   It needs its own lookup rather than joining the shared side-base one:
   its trigger list includes the **asat**, and na's swap has to fire
   *across* an asat (ကျွန်ုပ်) — a filtering set containing asat makes it
   visible and blocks that match. 27 of the 50 were this.
2. **အောက်မြစ် reserved no room.** The dot is placed *beside* its
   cluster's ink, not under it, so on a narrow letter it lands past the
   advance — and the next syllable's ြ wrap brings its under-sweep down
   into exactly that band. `မျှု့ကြ`, `ဖြုံ့ဖြုံ့`, `ရွှေ့ပြောင်း`.
   Padauk answers with the `dist` feature, widening the glyph that
   carries the dot (its uni102F goes 144 → 409); we had no `dist` at all.
   Ours is now generated, with the number *derived* rather than copied:
   place the dot on each base's own bottom anchor — and on the `side`
   anchor of every below-mark it might chain onto, which is what carries
   it out in ဖြုံ့ — and ask for the overshoot back plus the 50-unit
   protocol. Per weight, so Bold gets more than Light.

   The advance cannot go on the dot itself: HarfBuzz zeroes the advance
   of GDEF marks, the same trap that governs the medial-ra wrap.

`validate_spec.py` now checks this as a **neighbour** finding — WARN, not
FAIL, because Padauk trips it too (3 spec rows, 1 word row, 7 of the
vocabulary) and a gate here would fail the reference implementation. What
matters is that our count stays beside its count.

### Still open: the ဋ္ဌ stack needs artwork

`ကမ္မဋ္ဌာန်း`, `ကိလိဋ္ဌဒေါသ` and the rest of the ဋ ဌ ဍ ဠ family still
render as a tangle, and **no anchor change can fix it**:

* ဋ descends to −431 and ဌ to −436 across the letter's *whole width* —
  the bowl is the descender, so there is no clear column to slide a
  subjoined form into at any probe width.
* A subjoined letter is ~340 units tall. Below a tail at −436 it would
  need −821. `usWinDescent` is −750. It does not fit vertically either.
* Padauk's answer is `uni100B100C`: ဋ္ဌ **drawn as one fused glyph, 458
  units wide** — the footprint of a single letter, not a base with
  something hanging off it.

So the fix is traced artwork plus a GSUB ligature, exactly the pattern
already used for the wrap+u forms. A leg-avoidance scan for the stack
anchor was written, measured, and reverted when it turned out to move the
glyph by almost nothing.

## Letterform parity: တစ်ချောင်းငင် by context

A user report against the rendered output caught a *form* gap the
geometry checks cannot see: after medials and inside wraps, Burmese
writes ု as the tall **straight stroke**, not the curl. Measured across
Padauk and matched (all regression-tested):

| Context | Correct form | Mechanism |
| :--- | :--- | :--- |
| ကု ကူ | curl below the base | mark, unchanged |
| နု ရု (side-form bases) | curl beside the leg | unchanged |
| ကျု ကျူ / မွု (after ja, wa) | tall spacing stroke standing after the medial | `blws` medial_vowels → the `.alt` forms |
| ရှု (ha directly after a base) | curl beside the hook, ra still swaps to ရ.alt across the ha | ra's own `side_bases_ra` lookup |
| လျှု ကျှု မွှူ (ha inside a ja/wa cluster) | tall stroke — the medial context fires through the ha | ha absent from the medial_vowels filter |
| ကြု မြို (u inside a wrap) | the traced fused wrap+u drawing — retracted sweep, bar in the opening | `psts` two-step fusion (+ invisible ghost); synthesized bar as fallback |
| ကျွ လျှ ကျွှ | the traced woven ligatures (Padauk's uni103B103D / 103E / 103D103E) | `pres` ya_fuse |
| ကွှ ရွှ ရှု ရှူ | one fused hook per pair (uni103D103E, uni103E102F, uni103E1030) | `pres` wa_fuse / ha_fuse |
| ကြွ ပြွ ကြွီ | the wa nested inside the wrap's sweep (uni103C103D set) | `psts` wrap fusion + ghost |
| ကြွှ မြွှေ | plain wrap + the small fused hook — Padauk's own choice when both medials are present | the wa_fuse cascade keeps the wrap fusion off |
| ကြူ (uu after a wrap) | tall spacing stroke after the cluster | `psts` → `uu.alt` |

The narrow/wide wrap selection was also re-audited letter by letter:
our measured split agrees with Padauk's hand-curated one on 32 of 33
consonants (ပြ ခြ မြ … narrow; ကြ တြ လြ ဘြ … wide). The one divergence,
ဠြ, is deliberate: our ဠ measures 5 units *inside* the narrow wrap's
reach (nothing to widen for), and the combination does not occur in the
12,451-word vocabulary.

## Spec-file issues found (reported as SPEC, not failures)

The test document itself contains malformed rows, which the harness
quarantines so they can never mask a real bug:

* **All 134 Block H rows** ("Left-Side Vowels") are written with ေ
  *before* the consonant (ေက). Unicode stores dependent vowels after
  their consonant (ကေ); the reordering is the renderer's job — which
  Block M's ~100 correctly-ordered ေ-cases verify. Every shaper shows
  these rows with a dotted circle; so does Padauk.
* ~~**9 Block K "S'gaw Karen" rows** use U+A930–A938 — Rejang script, not
  Myanmar S'gaw Karen.~~ **Fixed 2026-08-17.** They were replaced with the
  characters S'gaw Karen actually adds to the Myanmar block — U+1061 SHA,
  U+1062 vowel EU, U+1063 tone HATHI, U+1064 tone KE PHO — in the
  combinations they really occur in (တၢ်, ယွၤ, ပှၤ, အိၣ်, မ့ၢ်). Block K
  is now 50 rows and the shipped family passes all of them, so the block
  finally tests what its label claims. The DirectWrite check is what
  surfaced it: Windows reported nine "disagreements" that turned out to be
  a corpus bug, not an engine one.
* Block G's အံု (vowel stored after the anusvara) and Block L's ပ marked
  with the Western Pwo Karen tone U+106A carry dotted circles for the
  same storage-order reason.

## Performance

Shaping the full corpus (4 775 glyphs from 1 486 clusters), Apple
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
