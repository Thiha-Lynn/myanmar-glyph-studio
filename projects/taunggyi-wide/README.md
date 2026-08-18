# Taunggyi Wide

**Medium · 28% wide · fully round · Myanmar + Latin-1** · SIL Open Font License 1.1

The banner face: the widest stance in the collection at an easy medium
weight, so headlines stretch across a page the way festival banners
stretch across a street. Named for the town whose sky fills with
balloons every Tazaungmon.

## Where it came from

Taunggyi Wide was not drawn by hand. It is the *same skeletons* as the
other families here, put through the pipeline's knobs — stroke weight and
a round nib — plus the width scale doing almost all of the talking. One
set of drawings, many faces: the argument this toolkit makes about how a
font family can be built.

Rebuild it with:

```bash
mgs-sample web/fonts/Padauk-Regular.ttf TaunggyiWide.glyphstudio.json \
    --font-name "Taunggyi Wide" --weight 1.05 --squircle 2
# apply width 1.28 / height 1.00, keep meta.pen 2, then:
./pipeline/build.sh projects/taunggyi-wide/TaunggyiWide.glyphstudio.json build/
```

The exact recipe is in [docs/FIVE-FACES.md](../../docs/FIVE-FACES.md).

## Licence

SIL Open Font License 1.1, with Reserved Font Name "Taunggyi Wide" — see
[OFL.txt](OFL.txt). The letterform skeletons derive from
[SIL Padauk](https://software.sil.org/padauk/); this is a Modified Version
under that licence, renamed as the OFL requires.
