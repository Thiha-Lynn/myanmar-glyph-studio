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

SHIPPED = [
    ROOT / "projects" / "myanmar-glyph-sans" / "MyanmarGlyphSans-Regular.ttf",
    ROOT / "projects" / "myanmar-glyph-sans" / "MyanmarGlyphSans-Light.ttf",
    ROOT / "projects" / "myanmar-glyph-sans" / "MyanmarGlyphSans-Bold.ttf",
    ROOT / "projects" / "sample" / "GlyphStudioSample-Regular.ttf",
]


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
