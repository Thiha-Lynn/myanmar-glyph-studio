# Nway Oo Display

**Bold · 8% condensed · soft-squared · Myanmar + Latin-1** · SIL Open Font License 1.1

A bold poster face with gently squared bowls on a compact stance — for
headlines, banners, signs and covers. နွေဦး is the season of new starts,
and the name is meant to carry everything Burmese readers hear in it.

## Where it came from

Nway Oo Display was not drawn by hand. It is the *same skeletons* as the
other families here, put through the pipeline's knobs — stroke weight, a
superellipse warp that squares the skeletons, the nib the outline is
expanded with — plus a width scale. One set of drawings, many faces: the
argument this toolkit makes about how a font family can be built.

Rebuild it with:

```bash
mgs-sample web/fonts/Padauk-Regular.ttf NwayOoDisplay.glyphstudio.json \
    --font-name "Nway Oo Display" --weight 1.60 --squircle 3
# apply width 0.92 / height 0.96, set meta.pen 3, then:
./pipeline/build.sh projects/nway-oo-display/NwayOoDisplay.glyphstudio.json build/
```

The exact recipe is in [docs/FIVE-FACES.md](../../docs/FIVE-FACES.md).

## Licence

SIL Open Font License 1.1, with Reserved Font Name "Nway Oo Display" — see
[OFL.txt](OFL.txt). The letterform skeletons derive from
[SIL Padauk](https://software.sil.org/padauk/); this is a Modified Version
under that licence, renamed as the OFL requires.
