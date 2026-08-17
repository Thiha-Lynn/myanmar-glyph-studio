# Mandalay Slab

**Medium · 10% wide · slab nib · Myanmar + Latin-1** · SIL Open Font License 1.1

A wide, sturdy text face cut with a near-rectangular nib, so the terminals end flat instead of rounded. The extra width gives Burmese stacked clusters room to breathe at small sizes. Named for the city whose grid was laid out square.

## Where it came from

Mandalay Slab was not drawn by hand. It is the *same skeletons* as the other
families here, put through the pipeline's three knobs — stroke weight, the
superellipse nib the outline is expanded with, and a warp that squares the
skeletons before expansion — plus a width scale. That is the point of it:
one set of drawings, many faces, which is the argument this toolkit makes
about how a font family should be built.

Rebuild it with:

```bash
mgs-sample web/fonts/Padauk-Regular.ttf mandalay-slab.glyphstudio.json \
    --font-name "Mandalay Slab" --weight ... --squircle ...
./pipeline/build.sh projects/mandalay-slab/MandalaySlab.glyphstudio.json build/
```

The exact recipe is in [docs/FIVE-FACES.md](../../docs/FIVE-FACES.md).

## Licence

SIL Open Font License 1.1, with Reserved Font Name "Mandalay Slab" — see
[OFL.txt](OFL.txt). The letterform skeletons derive from
[SIL Padauk](https://software.sil.org/padauk/); this is a Modified Version
under that licence, renamed as the OFL requires.
