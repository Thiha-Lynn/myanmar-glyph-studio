# Metta Round

**Heavy · 15% wide · fully round · Myanmar + Latin-1** · SIL Open Font License 1.1

The bubble face: the heaviest weight in the collection on the widest
stance, every terminal round. မေတ္တာ is loving-kindness — this is the face
for stickers, celebration banners, and anything you would draw hearts in
the margins of.

## Where it came from

Metta Round was not drawn by hand. It is the *same skeletons* as the other
families here, put through the pipeline's knobs — stroke weight and a
round nib — plus a width scale that gives the bowls room to be as generous
as the weight wants. One set of drawings, many faces: the argument this
toolkit makes about how a font family can be built.

Rebuild it with:

```bash
mgs-sample web/fonts/Padauk-Regular.ttf MettaRound.glyphstudio.json \
    --font-name "Metta Round" --weight 1.90 --squircle 2
# apply width 1.15 / height 0.94, keep meta.pen 2, then:
./pipeline/build.sh projects/metta-round/MettaRound.glyphstudio.json build/
```

The exact recipe is in [docs/FIVE-FACES.md](../../docs/FIVE-FACES.md).

## Licence

SIL Open Font License 1.1, with Reserved Font Name "Metta Round" — see
[OFL.txt](OFL.txt). The letterform skeletons derive from
[SIL Padauk](https://software.sil.org/padauk/); this is a Modified Version
under that licence, renamed as the OFL requires.
