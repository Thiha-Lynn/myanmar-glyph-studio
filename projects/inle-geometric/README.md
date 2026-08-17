# Inle Geometric

**Medium · 16% condensed · squared skeletons · squircle nib · Myanmar + Latin-1** · SIL Open Font License 1.1

Condensed and squared: the skeletons are warped toward a superellipse before the pen ever touches them, so the bowls themselves are less circular, not just the terminals. For dense tables, labels and signage. Named for the lake whose stilt houses stand in straight lines.

## Where it came from

Inle Geometric was not drawn by hand. It is the *same skeletons* as the other
families here, put through the pipeline's three knobs — stroke weight, the
superellipse nib the outline is expanded with, and a warp that squares the
skeletons before expansion — plus a width scale. That is the point of it:
one set of drawings, many faces, which is the argument this toolkit makes
about how a font family should be built.

Rebuild it with:

```bash
mgs-sample web/fonts/Padauk-Regular.ttf inle-geometric.glyphstudio.json \
    --font-name "Inle Geometric" --weight ... --squircle ...
./pipeline/build.sh projects/inle-geometric/InleGeometric.glyphstudio.json build/
```

The exact recipe is in [docs/FIVE-FACES.md](../../docs/FIVE-FACES.md).

## Licence

SIL Open Font License 1.1, with Reserved Font Name "Inle Geometric" — see
[OFL.txt](OFL.txt). The letterform skeletons derive from
[SIL Padauk](https://software.sil.org/padauk/); this is a Modified Version
under that licence, renamed as the OFL requires.
