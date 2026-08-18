# Inwa Light

**Light · 10% condensed · squircle nib · Myanmar + Latin-1** · SIL Open Font License 1.1

A quiet, slightly-squared light face with an airy, minimal feel — the
closest this monolinear pipeline comes to the restraint of East-Asian
gothic (maru-gothic) typography. True brush contrast needs modulated
strokes that a centre-line model cannot express, and this face does not
pretend otherwise. Named for ancient Inwa (Ava), four times the capital.

## Where it came from

Inwa Light was not drawn by hand. It is the *same skeletons* as the other
families here, put through the pipeline's knobs — a light stroke weight,
a gentle superellipse warp, a squircle nib — plus a width scale. One set
of drawings, many faces: the argument this toolkit makes about how a font
family can be built.

Rebuild it with:

```bash
mgs-sample web/fonts/Padauk-Regular.ttf InwaLight.glyphstudio.json \
    --font-name "Inwa Light" --weight 0.85 --squircle 4
# apply width 0.90 / height 1.00, set meta.pen 4, then:
./pipeline/build.sh projects/inwa-light/InwaLight.glyphstudio.json build/
```

The exact recipe is in [docs/FIVE-FACES.md](../../docs/FIVE-FACES.md).

## Licence

SIL Open Font License 1.1, with Reserved Font Name "Inwa Light" — see
[OFL.txt](OFL.txt). The letterform skeletons derive from
[SIL Padauk](https://software.sil.org/padauk/); this is a Modified Version
under that licence, renamed as the OFL requires.
