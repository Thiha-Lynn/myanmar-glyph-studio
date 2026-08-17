# Shwe Hair

**Light · normal width · round nib · Myanmar + Latin-1** · SIL Open Font License 1.1

A hairline text face. At 0.70 of the reference stroke it is the lightest thing this pipeline will build and still shape correctly — for captions, secondary text, and interfaces that want to whisper. Named for the gold leaf that Burmese shrines are covered in, which is thinner than anything else you will ever handle.

## Where it came from

Shwe Hair was not drawn by hand. It is the *same skeletons* as the other
families here, put through the pipeline's three knobs — stroke weight, the
superellipse nib the outline is expanded with, and a warp that squares the
skeletons before expansion — plus a width scale. That is the point of it:
one set of drawings, many faces, which is the argument this toolkit makes
about how a font family should be built.

Rebuild it with:

```bash
mgs-sample web/fonts/Padauk-Regular.ttf shwe-hair.glyphstudio.json \
    --font-name "Shwe Hair" --weight ... --squircle ...
./pipeline/build.sh projects/shwe-hair/ShweHair.glyphstudio.json build/
```

The exact recipe is in [docs/FIVE-FACES.md](../../docs/FIVE-FACES.md).

## Licence

SIL Open Font License 1.1, with Reserved Font Name "Shwe Hair" — see
[OFL.txt](OFL.txt). The letterform skeletons derive from
[SIL Padauk](https://software.sil.org/padauk/); this is a Modified Version
under that licence, renamed as the OFL requires.
