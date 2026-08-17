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
