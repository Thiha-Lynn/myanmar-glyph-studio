# Kawthaung Corsair

**Black · weathered outlines · bone terminals · ☠ ⚓ ornaments · Myanmar + Latin-1** · SIL Open Font License 1.1

The pirate cut: every glyph looks carved from driftwood and old bone —
edges roll like a swell, stroke ends swell into bone knuckles, and the
odd chip is gouged out like a sword nick. It ships two drawn ornaments,
**U+2620 ☠ SKULL AND CROSSBONES** and **U+2693 ⚓ ANCHOR**, weathered
with the same machinery, so a poster can fly the Jolly Roger in plain
text. Named for Kawthaung, the port at Myanmar's southern tip where the
Andaman sea route into the Myeik archipelago begins — waters that hid
working pirates for centuries. It is the drawn-texture sibling of
[Myeik Treasure](../myeik-treasure/): Treasure squares its skeletons
with parametric knobs, Corsair weathers its outlines.

A note on what a font can carry: gold bevels, rope lashings and wood
grain are colour effects for a graphics tool. What a plain-text font
*can* carry is silhouette — weathered edges, bone terminals, chips —
and that is exactly the part this face carries.

## Where it came from

Nobody traced these letterforms by hand. They are the same skeletons as
every other family here, put through a new pipeline stage,
[`make_pirate.py`](../../pipeline/make_pirate.py), which converts a
stroke-skeleton project into weathered **filled contours**: it expands
the strokes through the project's nib, unions each glyph into one
silhouette, grows bone knuckles on open stroke ends, then displaces the
outline with two superimposed waves plus grain and gouges deterministic
chips (seeded per glyph name, so the build always reproduces exactly).

Marks weather gently and grow no knuckles — asat, kinzi and the
subjoined forms are engineered against 50-unit clearances and the 900
ascender, and the first full build measured what full-strength
weathering does to them: 289 bounds warnings. The shipped recipe
validates at **0 FAIL, 19 / 9 WARN** on the 1,486-cluster spec corpus
and the 711-word corpus — inside the range the other display families
occupy.

Rebuild it with:

```bash
mgs-sample web/fonts/Padauk-Regular.ttf base.json \
    --font-name "Kawthaung Corsair" --weight 1.95 --squircle 2
mgs-pirate base.json KawthaungCorsair.glyphstudio.json --width 1.06 --y 0.88
./pipeline/build.sh projects/kawthaung-corsair/KawthaungCorsair.glyphstudio.json build/
```

The face is single-weight (`meta.variable: false`): a fill contour has
no pen for a weight axis to scale, so weight is baked in at the
skeleton stage.

## Licence

SIL Open Font License 1.1, with Reserved Font Name "Kawthaung Corsair" —
see [OFL.txt](OFL.txt). The letterform skeletons derive from
[SIL Padauk](https://software.sil.org/padauk/); this is a Modified
Version under that licence, renamed as the OFL requires.
