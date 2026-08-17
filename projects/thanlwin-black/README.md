# Thanlwin Black

**Black · normal width · round nib · Myanmar + Latin-1** · SIL Open Font License 1.1

The heaviest face here at 2.05 of the reference stroke, with the drawing compressed 12% vertically so the marks above a cluster stay inside the design ascender — bolding lifts them, because their anchors follow the base's ink. For headlines and covers. Named for the river that carries the most water in the country.

## Where it came from

Thanlwin Black was not drawn by hand. It is the *same skeletons* as the other
families here, put through the pipeline's three knobs — stroke weight, the
superellipse nib the outline is expanded with, and a warp that squares the
skeletons before expansion — plus a width scale. That is the point of it:
one set of drawings, many faces, which is the argument this toolkit makes
about how a font family should be built.

Rebuild it with:

```bash
mgs-sample web/fonts/Padauk-Regular.ttf thanlwin-black.glyphstudio.json \
    --font-name "Thanlwin Black" --weight ... --squircle ...
./pipeline/build.sh projects/thanlwin-black/ThanlwinBlack.glyphstudio.json build/
```

The exact recipe is in [docs/FIVE-FACES.md](../../docs/FIVE-FACES.md).

## Licence

SIL Open Font License 1.1, with Reserved Font Name "Thanlwin Black" — see
[OFL.txt](OFL.txt). The letterform skeletons derive from
[SIL Padauk](https://software.sil.org/padauk/); this is a Modified Version
under that licence, renamed as the OFL requires.
