"""Shaping-spec regression tests — validate_spec.py against the SHIPPED fonts.

The committed TTFs in projects/ are the toolchain's own output; if the spec
corpus finds a FAIL-severity problem in them, either the pipeline regressed
or a rebuilt font was not re-committed. WARNs are design-band notes shared
with Padauk (its ra-wrap tops out at 933 too) and do not gate.

    cd pipeline && python3 -m pytest tests/test_spec_validation.py -q
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import validate_spec as vs  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
CORPUS = Path(__file__).resolve().parent.parent / "spec_corpus.txt"
WORDS = Path(__file__).resolve().parent.parent / "word_corpus.txt"

# Discovered, never listed. A hand-written list is only correct until
# someone ships a file that is not on it: the two variable fonts were
# committed for three days rendering 437 vocabulary words wrong — stacks
# sinking past usWinDescent, asat detaching, kinzi colliding — because
# every one of those bugs had been fixed in a rebuild the VFs never got,
# and nothing tested them. Globbing means a shipped font cannot be
# forgotten; it can only be deleted.
SHIPPED = sorted((ROOT / "projects").glob("*/**/*.ttf"))


def test_discovery_found_every_shipped_font():
    """A glob that matches nothing makes every test below vacuously pass.

    So name what has to be there — the variable fonts especially, since
    they are the ones that went stale unnoticed, and a parametrised test
    over an empty list is exactly how that would stay quiet.
    """
    found = {p.name for p in SHIPPED}
    assert {
        "MyanmarGlyphSans-Regular.ttf",
        "MyanmarGlyphSans-Light.ttf",
        "MyanmarGlyphSans-Bold.ttf",
        "MyanmarGlyphSans-VF.ttf",
        "GlyphStudioSample-Regular.ttf",
        "GlyphStudioSample-VF.ttf",
        "NwayOoDisplay-Regular.ttf",
        "MettaRound-Regular.ttf",
        "InwaLight-Regular.ttf",
        "TaunggyiWide-Regular.ttf",
        "PatheinPoster-Regular.ttf",
    } <= found, f"shipped fonts missing from discovery: {found}"


def test_corpus_parses_and_covers_all_blocks():
    cases, titles = vs.load_corpus(CORPUS)
    assert len(cases) > 1400
    assert {c.block for c in cases} == set("ABCDEFGHIJKLMNO")
    assert all(c.text.strip() for c in cases)
    # Block K rows carry their language override
    assert {c.language for c in cases if c.block == "K"} >= {"mnw", "shn", "ksw"}


@pytest.mark.parametrize("corpus", [CORPUS, WORDS], ids=["spec", "words"])
@pytest.mark.parametrize("font_path", SHIPPED, ids=lambda p: p.stem)
def test_shipped_font_has_no_spec_failures(font_path, corpus):
    if not font_path.exists():
        pytest.skip(f"{font_path.name} not present")
    cases, _ = vs.load_corpus(corpus)
    font = vs.FontUnderTest(font_path)
    report = vs.run(font, cases)
    fails = [f for f in report.findings if f.severity == "FAIL"]
    detail = "\n".join(
        f"  [{f.case.block}] {f.case.text}: {f.message}" for f in fails[:12])
    assert not fails, f"{len(fails)} FAIL findings:\n{detail}"


def test_geometry_helpers():
    # overlapping squares touch; distant squares report their real gap
    a = [[(0, 0), (100, 0), (100, 100), (0, 100)]]
    b = [[(50, 50), (150, 50), (150, 150), (50, 150)]]
    c = [[(300, 0), (400, 0), (400, 100), (300, 100)]]
    assert vs.ink_clearance(a, b) == 0.0
    assert vs.ink_clearance(a, c) == pytest.approx(200, abs=1)
    # one polygon fully inside another is an overlap, not a clearance
    inner = [[(40, 40), (60, 40), (60, 60), (40, 60)]]
    assert vs.ink_clearance(a, inner) == 0.0


def test_shaping_diff_ignores_engine_quirks_but_not_real_differences():
    """The cross-engine comparison's exclusions, checked on every platform.

    These are pure functions, so the rules that let CoreText and
    DirectWrite disagree *harmlessly* with HarfBuzz stay under test on the
    Linux runner too — where neither engine exists.
    """
    import shaping_diff as sd

    ka = ("uni1000", 0.0, 0.0)

    # A blank against .notdef is the two engines saying "this font has no
    # glyph here" differently. DirectWrite blanks it, HarfBuzz boxes it.
    assert sd.compare([ka, ("space", 500.0, 0.0)],
                      [ka, (".notdef", 500.0, 0.0)], 12) == []
    # ...but a blank where HarfBuzz drew real ink means Windows would DROP
    # ink this font draws. That has to stay reportable.
    assert sd.compare([ka, ("space", 500.0, 0.0)],
                      [ka, ("uni103C", 500.0, 0.0)], 12)

    # A blank INSERTED where HarfBuzz inserted nothing: repairing a
    # malformed cluster means a dotted circle, and a font without U+25CC
    # gets a blank from DirectWrite and nothing from HarfBuzz. It draws
    # nothing and, here, shifts nothing.
    e = ("uni1031", 0.0, 0.0)
    assert sd.compare([e, ("space", 562.0, 0.0), ("uni1000", 562.0, 0.0)],
                      [e, ("uni1000", 562.0, 0.0)], 12) == []
    # ...but a blank that pushes the rest of the cluster along really does
    # change the spacing, and must not be waved through.
    assert sd.compare([e, ("space", 562.0, 0.0), ("uni1000", 1000.0, 0.0)],
                      [e, ("uni1000", 562.0, 0.0)], 12)

    # Marks reordered by one engine but landing in the same place: the
    # picture is identical, so it is not a difference.
    assert sd.compare([ka, ("dot", 100.0, 50.0), ("asat", 100.0, 800.0)],
                      [ka, ("asat", 100.0, 800.0), ("dot", 100.0, 50.0)],
                      12) == []
    # Reordered AND moved is a difference.
    assert sd.compare([ka, ("dot", 100.0, 50.0), ("asat", 100.0, 800.0)],
                      [ka, ("asat", 100.0, 800.0), ("dot", 100.0, -400.0)],
                      12)

    # Same glyphs, one of them displaced past the tolerance.
    assert sd.compare([ka, ("dot", 100.0, 50.0)],
                      [ka, ("dot", 100.0, -300.0)], 12)
    # Within tolerance is agreement.
    assert sd.compare([ka, ("dot", 100.0, 50.0)],
                      [ka, ("dot", 100.0, 44.0)], 12) == []

    # A dotted circle means both engines are repairing malformed input.
    assert sd.compare([ka, ("uni25CC", 100.0, 0.0)],
                      [("uni25CC", 0.0, 0.0), ka], 12) == []

    # CoreText substituting another font for a gap the font declares.
    assert sd.compare([ka, ("<fallback:Helvetica>", 500.0, 0.0)],
                      [ka, (".notdef", 500.0, 0.0)], 12) == []


def _cross_engine_check(engine, system, shaper, checker, hint):
    """Run one platform engine against HarfBuzz over both corpora.

    CI shapes with HarfBuzz; Apple platforms shape with CoreText and
    Windows with DirectWrite, and any of them can disagree — the gap issue
    #14 exists to cover. On the platform itself, with its shaper built, it
    closes automatically; everywhere else this skips.
    """
    import platform
    import subprocess
    if platform.system() != system:
        pytest.skip(f"{engine} is a {system} engine")
    pipeline = Path(__file__).resolve().parent.parent
    if not (pipeline / shaper).exists():
        pytest.skip(f"{Path(shaper).name} not built ({hint})")
    font = ROOT / "projects" / "myanmar-glyph-sans" / "MyanmarGlyphSans-Regular.ttf"
    if not font.exists():
        pytest.skip("shipped font not present")
    for corpus in (CORPUS, WORDS):
        proc = subprocess.run(
            [sys.executable, str(pipeline / checker), str(font),
             "--corpus", str(corpus)],
            capture_output=True, text=True)
        assert proc.returncode == 0, (
            f"{engine} disagrees with HarfBuzz on {corpus.name}:\n"
            + proc.stdout[-2000:])


def test_coretext_agrees_with_harfbuzz_on_macos():
    _cross_engine_check(
        "CoreText", "Darwin", "coretext/coretext-shape", "coretext_check.py",
        "see pipeline/coretext/README.md")


def test_directwrite_agrees_with_harfbuzz_on_windows():
    _cross_engine_check(
        "DirectWrite", "Windows", "directwrite/DirectWriteShape.exe",
        "directwrite_check.py", "see pipeline/directwrite/README.md")
