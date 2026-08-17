# CoreText cross-engine check

CI shapes with **HarfBuzz** — the engine Android, Chrome, Linux and
LibreOffice use. Apple platforms shape with **CoreText**. The two can
disagree, and a rule that works everywhere else can misfire on a Mac or
an iPhone; that is exactly what
[issue #14](https://github.com/Thiha-Lynn/myanmar-glyph-studio/issues/14)
asks people to check by hand.

On macOS it needs no hand. Build the shaper once:

```bash
cd pipeline/coretext
swiftc -O CoreTextShape.swift -o coretext-shape
```

then diff the engines over the whole corpus:

```bash
python3 pipeline/coretext_check.py \
    projects/myanmar-glyph-sans/MyanmarGlyphSans-Regular.ttf
python3 pipeline/coretext_check.py <font> --corpus pipeline/word_corpus.txt
```

It reports only differences that would **change the rendering**, and
stays quiet about the three kinds that don't:

* **mark reordering** — HarfBuzz reorders the tone dot before the asat,
  CoreText keeps storage order. They attach to different anchors, so the
  ink lands in the same place; the checker verifies that by position
  rather than assuming it.
* **font fallback** — where the font has no glyph, CoreText substitutes
  another font (for the whole run) while HarfBuzz emits `.notdef`. That
  is coverage, not a shaping difference.
* **malformed input** — when either engine inserts a dotted circle the
  cluster is not in Unicode storage order and both are *repairing* it;
  how much each salvages is engine-defined and says nothing about the
  font.

`pipeline/tests/test_spec_validation.py` runs it as a test on macOS and
skips elsewhere, so a Mac contributor's `pytest` covers Apple's engine
automatically.

**DirectWrite (Windows)** is covered the same way, by
[`pipeline/directwrite/`](../directwrite/) — that one runs in CI on a
`windows-latest` runner, so all three engines are now checked
automatically. The comparison itself is shared between the two checkers in
[`shaping_diff.py`](../shaping_diff.py).
