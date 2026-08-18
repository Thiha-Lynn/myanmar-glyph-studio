# Myeik Treasure

**Black · 8% wide · slab nib · squared bowls · Myanmar + Latin-1** · SIL Open Font License 1.1

The adventure cut: heavy, wide, flat-ended strokes with squared-off
bowls — lettering for treasure maps, ship names, wanted posters and
pirate-comic covers. Named for the Myeik archipelago, whose eight
hundred islands hid actual pirates for actual centuries.

A note on what a font can carry: the letterforms are the skeleton of
that poster style. Wood grain, rope, gold bevels and skull-and-crossbones
are layered on in a graphics tool — no plain-text font format renders
texture, and this project does not pretend otherwise.

## Where it came from

Myeik Treasure was not drawn by hand. It is the *same skeletons* as the
other families here, put through the pipeline's knobs — the heaviest
weight the slab nib validates cleanly at, a strong superellipse warp
that squares the bowls, the flat nib that ends every stroke like a cut
plank, plus a width stretch and a stocky vertical compression. One set
of drawings, many faces: the argument this toolkit makes about how a
font family can be built. (Weight 2.0 was tried and rejected — the slab
nib at black weight trips 95 geometry warnings; 1.85 validates at 14.)

Rebuild it with:

```bash
mgs-sample web/fonts/Padauk-Regular.ttf MyeikTreasure.glyphstudio.json \
    --font-name "Myeik Treasure" --weight 1.85 --squircle 5
# apply width 1.08 / height 0.90, set meta.pen 8, then:
./pipeline/build.sh projects/myeik-treasure/MyeikTreasure.glyphstudio.json build/
```

The exact recipe is in [docs/FIVE-FACES.md](../../docs/FIVE-FACES.md).

## Licence

SIL Open Font License 1.1, with Reserved Font Name "Myeik Treasure" — see
[OFL.txt](OFL.txt). The letterform skeletons derive from
[SIL Padauk](https://software.sil.org/padauk/); this is a Modified Version
under that licence, renamed as the OFL requires.
