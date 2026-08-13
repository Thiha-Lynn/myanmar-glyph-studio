# Glyph Studio Sample

A complete demonstration project for the stroke-based pipeline. Every glyph
in `GlyphStudioSample.glyphstudio.json` is a stroke *skeleton* (centerline +
width), machine-extracted from the OFL-licensed
[Padauk](https://software.sil.org/padauk/) font by shaping each inventory
entry's guide string with HarfBuzz, rasterizing the outlines, thinning them
to one-pixel centerlines, and tracing those into studio strokes.

It exists so the repo always has a project that exercises the **full
pipeline** end to end: it can be loaded into the web studio (the **Load**
button) and edited like any hand-drawn project, and it builds into a
working font with real Myanmar shaping — subjoined stacks (`blwf`),
kinzi (`rphf`), wide medial-ra (`pres`), short u/uu variants (`blws`), and
GPOS mark/mkmk positioning from the auto-placed anchors.

## Coverage

109 drawn entries of the 112-glyph core studio inventory. Three are
skipped because Padauk has no subjoined form for them (it renders the
stack with a visible virama instead): `nya-myanmar.sub`, `wa-myanmar.sub`,
`ha-myanmar.sub`. The invisible virama (U+1039) is not drawn — the build
synthesizes the empty zero-width glyph the `blwf`/`rphf` rules consume.

## Build it

```sh
python3 pipeline/json_to_ufo.py projects/sample/GlyphStudioSample.glyphstudio.json build/
fontmake -u build/GlyphStudioSample-Regular.ufo -o ttf --output-dir build/
```

Quick shaping smoke test of the result (uses `uharfbuzz`): shaping
`က္က` must yield `ka-myanmar.sub`, `ကု` must position `u-myanmar` with a
GPOS offset, and `သင်္ဘော` / `ကြ` must shape without `.notdef`.

## Regenerate it

```sh
# from the repo root; Padauk-Regular.ttf from https://software.sil.org/padauk/
python3 pipeline/make_sample.py Padauk-Regular.ttf projects/sample/GlyphStudioSample.glyphstudio.json
```

`pipeline/make_sample.py` documents the extraction algorithm (HarfBuzz
cluster-based context exclusion, nonzero-winding rasterization, Zhang-Suen
thinning, junction-split tracing, Ramer-Douglas-Peucker simplification).
Padauk uses 1024 units/em; all coordinates are scaled into this project's
1000 units/em space.

## License and attribution

The letterform skeletons are derived from **Padauk, copyright (c) SIL
International**, licensed under the **SIL Open Font License 1.1**. This
project file and fonts built from it are likewise licensed under the
[SIL Open Font License 1.1](https://openfontlicense.org) and keep the
attribution in their `meta.author` field. The sample is a tracing aid and
pipeline demo, not a replacement for Padauk.
