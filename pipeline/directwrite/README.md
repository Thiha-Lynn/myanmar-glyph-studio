# DirectWrite cross-engine check

CI shapes with **HarfBuzz** — the engine Android, Chrome, Linux and
LibreOffice use. Windows shapes with **DirectWrite**: Word, Edge, Notepad,
Office, every WPF and UWP app. The two can disagree, and a rule that works
everywhere else can misfire on Windows; that is the half of
[issue #14](https://github.com/Thiha-Lynn/myanmar-glyph-studio/issues/14)
that was left for a volunteer with a Windows machine.

It does not need one. GitHub's `windows-latest` runner **is** a Windows
box with the real engine, and the compiler is already installed — so this
now runs on every pull request, next to the HarfBuzz corpus.

Build the shaper once (from a *Developer Command Prompt*, or after running
`vcvars64.bat`, so `cl.exe` is on PATH):

```bat
cd pipeline\directwrite
cl /EHsc /O2 /std:c++17 DirectWriteShape.cpp
```

then diff the engines over the whole corpus:

```bat
python pipeline\directwrite_check.py ^
    projects\myanmar-glyph-sans\MyanmarGlyphSans-Regular.ttf
python pipeline\directwrite_check.py <font> --corpus pipeline\word_corpus.txt
```

## What it actually calls

`IDWriteTextAnalyzer::GetGlyphs` followed by `GetGlyphPlacements` — the
real OpenType shaping engine, the same code path `IDWriteTextLayout` runs
internally. Going through the analyzer instead of a layout keeps the font
under test the **only** font in play: at this layer DirectWrite never
silently falls back to another family, so a character the font lacks comes
back as glyph 0 and compares straight against HarfBuzz's `.notdef`.

The shaper prints glyph **IDs**, not names — DirectWrite has no notion of
`post` names. `directwrite_check.py` maps them through the font's own
glyph order, the same list `validate_spec.py` uses for HarfBuzz, so both
runs name glyphs identically.

It reports only differences that would **change the rendering**, sharing
that logic (and its false-alarm exclusions) with the CoreText check in
[`pipeline/shaping_diff.py`](../shaping_diff.py):

* **mark reordering** — HarfBuzz reorders the tone dot before the asat;
  another engine may keep storage order. They attach to different anchors,
  so the ink lands in the same place; the checker verifies that by
  position rather than assuming it.
* **malformed input** — when either engine inserts a dotted circle the
  cluster is not in Unicode storage order and both are *repairing* it; how
  much each salvages is engine-defined and says nothing about the font.

`pipeline/tests/test_spec_validation.py` runs it as a test on Windows and
skips elsewhere, so a Windows contributor's `pytest` covers Microsoft's
engine automatically — as `pipeline/coretext/` does for Apple's.

## What is still worth a human

All three major engines are now checked automatically, so what remains is
the thing automation cannot judge: whether the result **looks right** to a
reader of Burmese, on real hardware, at real sizes — and whether an older
Windows (or an app that still uses the pre-DirectWrite Uniscribe path)
behaves the same. The
[device test page](https://thiha-lynn.github.io/myanmar-glyph-studio/devicetest.html)
is still the way to report that.
