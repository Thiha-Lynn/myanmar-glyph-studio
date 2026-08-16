# Debugging Myanmar shaping

The systematic companion to [TESTING.md](TESTING.md)'s proof-sheet
workflow: symptom → cause → fix, for fonts built with this pipeline.
Terminology and rule order: [SHAPING_SPEC.md](SHAPING_SPEC.md).

## Start here: measure, don't squint

```bash
cd pipeline
# every spec case, graded, deduplicated, with coordinates:
python3 validate_spec.py build/MyFont-Regular.ttf --verbose
# one suspicious cluster, positioned glyph by positioned glyph:
python3 proof.py build/MyFont-Regular.ttf "ကြိုး" debug.png --size 200
# what did the reference font do?
python3 validate_spec.py build/MyFont-Regular.ttf --reference ../web/fonts/Padauk-Regular.ttf
```

`validate_spec.py` severities tell you whose bug it is: **FAIL** = the
font's rules/anchors, **GAP** = a glyph you haven't drawn, **SPEC** =
the *input text* is malformed (dotted circles from a vowel stored before
its consonant are correct behaviour — check with Padauk before "fixing"
the font).

## Symptom table

| Symptom | Diagnosis | Fix |
| :--- | :--- | :--- |
| base + ္ + full-size consonant in a row | `blwf` didn't fire: the `.sub` form isn't drawn, or the virama glyph carries ink | draw the `.sub`; never draw ink for U+1039 (the pipeline discards it) |
| full-size င + ် + ္ visible | `rphf` didn't fire | draw `kinzi-myanmar` |
| ေ renders to the right of its consonant | the run wasn't shaped as Myanmar at all | check the build emitted `mym2` (`languagesystem` lines in features.fea); check the app tagged the text Myanmar |
| base sits ON the wrap's left stem | ြ advance became 0 — it was classified GDEF mark | ြ must be GDEF *base* (HarfBuzz zeroes mark advances); check `public.openTypeCategories` |
| base pokes far out of the wrap | wide-wrap selection wrong | the wide set is measured (overhang > wrap reach + 100); draw `medialRa-myanmar.wide` or check the wrap's own ink width |
| mark piled on the base's head, offset (0,0) | no GPOS pair: base lacks `top`/`bottom` or mark lacks `_top`/`_bottom` | open ⚓ Anchors in the studio — both glyphs need their anchor role |
| marks of one cluster on one spot | both marks attach to the same base anchor instead of chaining | the *first* mark carries the chain anchor (`side` for below-marks); check it wasn't deleted by a manual drag |
| below-mark buried below −600 | something chained *underneath* a deep glyph | below/stack marks chain BESIDE (side/_side), never under; stacks clamp to the −50 floor — see SHAPING_SPEC §3.2 |
| vowel clipped at the top of the line (Windows/browsers) | positioned ink past usWinAscent (+1100) | above-marks must chain sideways at height (kinzi) or use the fixed-height `top` (spacing signs); never stack two full marks |
| ကျွ stops tucking after editing features | a later lookup inherited an earlier lookup's `lookupflag` — it is STICKY across named lookups within one feature block | open every lookup with explicit `lookupflag 0;` unless it needs a filter |
| kinzi overlaps the vowel in kinzi+ya words (အင်္ကျီ) | the vowel belongs to the ya (a base — the mark chain restarts), so it cannot chain beside the kinzi | the abvs kinzi→kinzi.left substitution handles it; check the rule survived a features edit |
| စက္ကူ loses its long vowel after editing features | the blws filtering set lost the `.sub` glyphs — the context must SEE them | keep `.sub` glyphs + the vowels in `UseMarkFilteringSet` |
| stack works alone but breaks after ိ or ် | filtering set includes too much/too little: intervening marks must be invisible to the context, triggers visible | compare with the generated `side_bases` lookup |
| everything right in hb-view, wrong in an app | app-side itemization or a legacy engine | test `mymr` script tag; on Windows check DirectWrite with the real app, file per TESTING.md §real devices |
| glyphs from another font appear | font fallback hid a GAP | run `validate_spec.py`; hollow boxes in proof.py are the honest view |

## Reading a cluster dump

`proof.py` prints hb-shape style: `name=cluster@x_offset,y_offset+x_advance`.

```
uni1000=0+979 | uni103B.beforewa=0+158 | uni103D=0@-687,28+0
```

* offsets `@x,y` present → GPOS moved it (attached); a mark with no
  offset and `+0` advance did *not* attach.
* virama `uni1039` surviving in the stream = dead `blwf`.
* `uni25CC` in the stream = HarfBuzz repaired ill-formed input — the
  *text* is wrong, not the font (verify against Padauk).
* cluster numbers group the syllable; a mark with a different cluster
  number than its base means the input had an intervening character.

## Anchor bugs: the four load-bearing conventions

Most positioning regressions in this pipeline's history broke one of
these (each now regression-tested in `pipeline/tests/`):

1. **Below-marks chain beside, not below** (`side`/`_side`, tops
   aligned) — ရွှံ့, လွှ, ရှု.
2. **Everything below the baseline clamps to the −50 floor** — stacks
   and vowels both; the leg-free `.alt` base swap handles the leg.
3. **Above-marks never stack twice** — the second above-mark goes
   beside (kinzi) or the ligature exists (ိံ).
4. **Spacing signs are mark bases with a fixed-height top** — ကော် ကာံ.

When a manual anchor drag in the studio conflicts with these, the drag
wins — which is occasionally the *cause*: `validate_spec.py --block <X>`
before and after removing the stored anchor tells you.

## Language-specific failures (Block K)

* Mon/Shan/Karen text misbehaving in one app only: the app may not pass
  the `mnw`/`shn`/`ksw` language tag; all rules currently register under
  `dflt`, so tag differences should be invisible — if they are not, a
  future per-language override was added; check its `exclude_dflt`.
* Shan/Karen marks attaching oddly: extension marks classify by Unicode
  category and auto-anchor by drawn position (above/below the body
  midline) — redraw the mark clearly above/below, or drag its anchor.
* Karen test text showing boxes in *every* font: check the codepoints —
  the spec document's "S'gaw Karen" rows use Rejang codepoints
  (U+A930…), which no Myanmar font maps.

## When the pipeline itself is suspect

```bash
python3 -m pytest tests/ -q            # 49 checks incl. the spec corpus
python3 json_to_ufo.py proj.json out/  # rebuild UFO, read features.fea
ttx -t GDEF -o - build/MyFont-Regular.ttf | less   # classes as compiled
```

Change anchors or rules in `json_to_ufo.py` and `web/js/anchors.js`
**together** — the studio previews what the pipeline will build, and the
pair drifting apart is itself a bug.
