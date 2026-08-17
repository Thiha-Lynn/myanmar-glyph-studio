# Sagaing Square

**Medium-bold · 14% condensed · maximally squared · slab nib · Myanmar + Latin-1** · SIL Open Font License 1.1

The most extreme face in the set: skeletons warped nearly to rectangles, a slab nib, and condensed hard. It reads as engineered rather than written, which is exactly what some signage and interface work wants. Named for the hills opposite Ava, stacked with white pagodas.

## Where it came from

Sagaing Square was not drawn by hand. It is the *same skeletons* as the other
families here, put through the pipeline's three knobs — stroke weight, the
superellipse nib the outline is expanded with, and a warp that squares the
skeletons before expansion — plus a width scale. That is the point of it:
one set of drawings, many faces, which is the argument this toolkit makes
about how a font family should be built.

Rebuild it with:

```bash
mgs-sample web/fonts/Padauk-Regular.ttf sagaing-square.glyphstudio.json \
    --font-name "Sagaing Square" --weight ... --squircle ...
./pipeline/build.sh projects/sagaing-square/SagaingSquare.glyphstudio.json build/
```

The exact recipe is in [docs/FIVE-FACES.md](../../docs/FIVE-FACES.md).

## Licence

SIL Open Font License 1.1, with Reserved Font Name "Sagaing Square" — see
[OFL.txt](OFL.txt). The letterform skeletons derive from
[SIL Padauk](https://software.sil.org/padauk/); this is a Modified Version
under that licence, renamed as the OFL requires.
