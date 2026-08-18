# Pathein Poster

**Bold · 12% condensed · fully round · Myanmar + Latin-1** · SIL Open Font License 1.1

A round, condensed poster black — the counterpart to Nway Oo Display's
squared cut. Where Nway Oo is angular and civic, Pathein Poster is warm
and hand-painted, the lettering of a parasol workshop's shop sign. Named
for the town of the painted umbrellas.

## Where it came from

Pathein Poster was not drawn by hand. It is the *same skeletons* as the
other families here, put through the pipeline's knobs — a heavy stroke
weight, a round nib, a condensing width scale and a small vertical
compression that keeps the fattened marks inside the design band. One
set of drawings, many faces: the argument this toolkit makes about how a
font family can be built.

Rebuild it with:

```bash
mgs-sample web/fonts/Padauk-Regular.ttf PatheinPoster.glyphstudio.json \
    --font-name "Pathein Poster" --weight 1.75 --squircle 2
# apply width 0.88 / height 0.92, keep meta.pen 2, then:
./pipeline/build.sh projects/pathein-poster/PatheinPoster.glyphstudio.json build/
```

The exact recipe is in [docs/FIVE-FACES.md](../../docs/FIVE-FACES.md).

## Licence

SIL Open Font License 1.1, with Reserved Font Name "Pathein Poster" — see
[OFL.txt](OFL.txt). The letterform skeletons derive from
[SIL Padauk](https://software.sil.org/padauk/); this is a Modified Version
under that licence, renamed as the OFL requires.
