# Five faces from one set of skeletons

Five families were added in one sitting without drawing a single new
glyph. They are the argument this toolkit makes, made concrete: a font is
centre lines plus a pen, so changing the pen — or the lines — gives you a
different face for free.

They are **not** hand-drawn, and nothing here pretends otherwise. Nobody
traced them and no contributor is credited for them; they are machine
variations of the same skeletons, and their value is as a demonstration
and as usable text faces, not as evidence of a community that does not
exist yet.

## The recipes

| Family | Weight | Skeleton warp | Nib | Width | y |
|---|---|---|---|---|---|
| **Shwe Hair** | 0.70 | 2 (round) | 2 (round) | 1.00 | 1.00 |
| **Mandalay Slab** | 1.30 | 2 (round) | 8 (slab) | 1.10 | 0.97 |
| **Inle Geometric** | 1.10 | 6 (squared) | 4 (squircle) | 0.84 | 1.00 |
| **Thanlwin Black** | 2.05 | 2 (round) | 2 (round) | 1.00 | 0.88 |
| **Sagaing Square** | 1.45 | 8 (max squared) | 8 (slab) | 0.86 | 0.97 |

Weight and skeleton warp come from `mgs-sample`; the nib is `meta.pen` in
the project file; width and the vertical scale are affine transforms on
the skeleton — every point, every bezier control, every anchor, and the
advance together, so spacing stays proportional and marks stay attached.

```bash
mgs-sample web/fonts/Padauk-Regular.ttf ShweHair.glyphstudio.json \
    --font-name "Shwe Hair" --weight 0.70 --squircle 2
# then set meta.pen in the JSON, and build:
./pipeline/build.sh projects/shwe-hair/ShweHair.glyphstudio.json build/
```

## Two things this set taught, both by measurement

**The nib alone does not make a face.** The first five differed only in
weight, nib and warp — and rendered as one face at five weights. A
superellipse nib squares the *terminals*; Myanmar's character is in its
*bowls*, which stay round. Width is what separated them at a glance, and
it is why three of the five carry a width scale.

**Condensing squeezes what a stack needs.** At x0.78 Sagaing Square
failed the word corpus outright: `uni1018.sub` overlapped the below-dot in
ကမ္ဘာ့တန်ဆာ, because narrowing the glyphs narrows the gap a subjoined form
and a mark need between them. 0.86 clears it and still reads as condensed.
The spec corpus did not catch this — only the 711 real words did, which is
the corpus design working exactly as intended.

**A slab nib overshoots the wrap band.** With `pen = 8`, medial ra ends at
y=940 against the 935 ceiling this project designs to — and 319 of Sagaing
Square's original 323 warnings were that one glyph, counted once per
cluster it appears in. Compressing those two faces to y×0.97 took them to
3 and 25. It is the same class of problem Bagan Display met when bolding
lifted its marks, and it has the same fix.

## What they had to pass

The same gate as everything else: `validate_spec` over 1,486 spec clusters
and 711 real Burmese words, **0 FAIL on every face**, plus fontbakery's
universal profile in CI. Warning counts (3, 14, 16, 6, 25) sit in the range
the existing families occupy, and are the usual `bounds`/`neighbour`
findings that extreme weights and widths produce.

A face that does not clear the corpus does not ship — a showcase carrying
hundreds of geometry warnings would quietly contradict the thing this
project's validation story asserts.

## Three more (2026-08-18)

| Family | Weight | Skeleton warp | Nib | Width | y |
|---|---|---|---|---|---|
| **Nway Oo Display** | 1.60 | 3 | 3 | 0.92 | 0.96 |
| **Metta Round** | 1.90 | 2 (round) | 2 (round) | 1.15 | 0.90 |
| **Inwa Light** | 0.85 | 4 (squircle) | 4 (squircle) | 0.90 | 1.00 |

Same rules, same honesty: machine variations of the same skeletons, nobody
credited, each separated by the axis the first five proved actually
separates faces — width, spread here from 0.90 to 1.15 across a weight
range of 0.85 to 1.90.

**Nway Oo Display** (နွေဦး — the season of new starts) is the poster cut:
bold, compact, gently squared. **Metta Round** (မေတ္တာ, loving-kindness)
is the bubble face — the heaviest weight in the collection on the widest
stance, every terminal round, for stickers and celebration banners.
**Inwa Light** is the quiet one: light, slightly squared, a little
condensed — the closest a monolinear pen comes to the restraint of
East-Asian gothic typography. True brush contrast — the modulated stroke
of Chinese calligraphic type — needs width variation along the stroke
that a centre-line-plus-pen model cannot express, so no face here
pretends to it.

**The mark-lift lesson repeated on cue.** Metta Round's first cut used
y 0.94 and came back with 314 spec warnings — asat at y=901–905 and kinzi
at 909–913, just past the 900 design ascender, once per cluster they
appear in. It is the identical failure Bagan Display and the slab faces
met: bolding raises marks because their anchors follow the base's ink.
The identical fix (y 0.90, Bagan's own value at this weight class) took
it to 15. The knob interactions are predictable enough now that the
second guess is usually right, which is itself worth recording.

Validation, spec / words, 0 FAIL everywhere: Nway Oo 11 / 33 WARN,
Metta Round 15 / 9, Inwa Light 3 / 3 — the usual `bounds`/`neighbour`
findings, inside the range the existing families occupy.

## And two more, same day

| Family | Weight | Skeleton warp | Nib | Width | y |
|---|---|---|---|---|---|
| **Taunggyi Wide** | 1.05 | 2 (round) | 2 (round) | 1.28 | 1.00 |
| **Pathein Poster** | 1.75 | 2 (round) | 2 (round) | 0.88 | 0.92 |

**Taunggyi Wide** is the banner cut — the widest stance in the
collection at an easy medium weight, width doing almost all of the
talking, named for the town of the balloon festival. **Pathein Poster**
is the round condensed black: Nway Oo Display's warmer, hand-painted
counterpart, named for the town of the painted umbrellas. Validation,
spec / words, 0 FAIL: Taunggyi 14 / 3 WARN, Pathein 4 / 7.

Every machine face — these ten plus Bagan Display — also carries the
traced fused forms the hand projects gained (ဋ္ဌ, ဏ္ဍ, ါ်, and U+2012),
merged at each face's own width and height from a fresh trace, then
rebuilt and re-validated. A recipe is a first-class citizen: when the
shared inventory grows, every face grows with it.

## The adventure cut

| Family | Weight | Skeleton warp | Nib | Width | y |
|---|---|---|---|---|---|
| **Myeik Treasure** | 1.85 | 5 | 8 (slab) | 1.08 | 0.90 |

Requested as "pirate-comic lettering": heavy, wide, flat-ended, squared
— treasure maps and ship names. The knobs' interaction table earned its
keep again: weight 2.0 with the slab nib tripped **95** spec warnings
(the slab-overshoot class at black weight), while 1.85 validates at
14 / 9 with 0 FAIL — and a slab nib reads a step heavier than its number
anyway, because the flat terminals carry more ink. Textures, outlines
and gold bevels are poster effects for a graphics tool; the letterforms
are the part a font can honestly carry, and this is that part.

## The corsair cut

| Family | Weight | Skeleton warp | Nib | Width | y | Post-process |
|---|---|---|---|---|---|---|
| **Kawthaung Corsair** | 1.95 | 2 (round) | 2 (round) | 1.06 | 0.88 | `mgs-pirate` |

The follow-up ask — actual carved-bone letterforms, not just a heavy
slab — needed an axis none of the knobs reach: the *outline* itself.
[`make_pirate.py`](../pipeline/make_pirate.py) is that axis, a stage
that converts the expanded strokes into weathered filled contours: one
unioned silhouette per glyph, bone knuckles on open stroke ends, two
superimposed waves plus grain along every edge, deterministic chip
gouges, and two ornaments drawn from primitives (U+2620 ☠, U+2693 ⚓).
The output is a normal version-1 project full of `fill: true` contours,
so nothing downstream changes — and nothing upstream either: weight
must be baked in the skeletons first, because a fill contour has no pen
for a weight master to scale (`meta.variable: false`).

Three findings, each measured before it was believed:

**Winding is load-bearing.** Primitive polygons arrive with arbitrary
orientation, and under the nonzero rule two opposite windings cancel:
the first build rendered every knuckle with a white hole in it. All
primitives are rewound counter-clockwise before the union; contours
that *come out* of a union keep their windings, which now encode real
holes.

**Marks cannot afford the costume.** Full-strength weathering put 289
bounds warnings on the spec corpus — knuckled asat and kinzi rose to
y = 935–962 against the 900 ascender, and a fattened subjoined ဘ met
the below-dot in ကမ္ဘာ့တန်ဆာ, the same squeeze that once failed Sagaing
Square. Marks now weather at 0.45 amplitude, grow no knuckles, and are
clamped to their own nominal ink ceiling; crowns above y = 720 fade
their wave, and knuckles never form above y = 640 (a knob on a crown
lifts the ink-following anchor of every mark above it). With Thanlwin
Black's y 0.88 the shipped cut validates **0 FAIL, 19 / 9 WARN** —
inside the family band, with fontbakery at 0 FAIL.

**Bone feet, tucked shoulders.** A terminal at the baseline takes the
full condyle, pushed past the stroke end — the letters stand on bone
feet. A mid-height terminal takes knobs that bulge sideways only, axial
reach inside the original cap, so a stem's knuckle never raises the
glyph's ink ceiling.
