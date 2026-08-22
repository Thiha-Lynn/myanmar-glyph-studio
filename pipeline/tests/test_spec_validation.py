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
        "MyeikTreasure-Regular.ttf",
        "KawthaungCorsair-Regular.ttf",
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


# ---------------------------------------------------------------------------
# The reference font as the gate: what Padauk draws as one glyph, we draw
# as one glyph.
# ---------------------------------------------------------------------------

REFERENCE = ROOT / "web" / "fonts" / "Padauk-Regular.ttf"
VIRAMA = "္"
# ဋ ဌ ဍ ဎ ဏ ဠ — the letters whose tail runs the width of the glyph.
DEEP_LETTERS = [chr(cp) for cp in range(0x100B, 0x1011) if cp != 0x1010]
DEEP_LETTERS.append("ဠ")


def _reference_font():
    if not REFERENCE.exists():
        pytest.skip("bundled Padauk reference not present")
    return vs.FontUnderTest(REFERENCE)


def test_every_stack_the_reference_fuses_is_in_the_inventory():
    """ဍ္ဎ shipped as a tangle for a week because this test did not exist.

    Two of Padauk's seven fused deep stacks had been traced; the other
    five were left stacking a subjoined form under a full-width tail,
    which is exactly the tangle the traced pair existed to avoid. The
    reference font states the whole set — so read it, do not list it.
    """
    ref = _reference_font()
    expected = set()
    for top in DEEP_LETTERS:
        for bottom in DEEP_LETTERS:
            glyphs, _ = ref.shape(top + VIRAMA + bottom)
            if len(glyphs) == 1 and glyphs[0].name.startswith("uni"):
                expected.add(glyphs[0].name)
    assert expected, "reference font fused nothing — is this Padauk?"
    import json
    project = json.loads(
        (ROOT / "projects" / "myanmar-glyph-sans"
         / "MyanmarGlyphSans.glyphstudio.json").read_text(encoding="utf-8"))
    missing = sorted(expected - set(project["glyphs"]))
    assert not missing, (
        "Padauk draws these stacks as one glyph and the project has no "
        f"artwork for them: {missing}")


# The four pairs Padauk answers with a subjoined SIZE this project does
# not have. Its subjoined forms come in two sizes — uni100D.med at ~75%
# of the letter and uni100D.sml at ~55% — and after ဍ, whose tail leaves
# the smallest pocket of the six, only the .sml one fits at any position.
# Ours are all one size (the .med one), so these four stay worse than the
# reference until a small subjoined class exists. None of them occurs in
# either corpus, in the 12,450-word vocabulary, or in the Jataka text:
# they are spellable, not written. Listed rather than tolerated silently,
# and the test still fails if the list has to grow.
KNOWN_DEEP_STACK_GAPS = {"ဍ္ဋ", "ဍ္ဌ", "ဍ္ဏ", "ဍ္ဠ"}


@pytest.mark.parametrize("font_path", SHIPPED, ids=lambda p: p.stem)
def test_every_font_fuses_the_stacks_the_reference_fuses(font_path):
    """The structural half of the check, and it holds at every weight.

    A pair Padauk draws as one glyph must shape to one glyph here too. A
    font that stacks a subjoined form under a full-width tail instead is
    the ဍ္ဎ tangle again, whatever the pen is doing.
    """
    if not font_path.exists():
        pytest.skip(f"{font_path.name} not present")
    ref = _reference_font()
    font = vs.FontUnderTest(font_path)
    unfused = []
    for top in DEEP_LETTERS:
        for bottom in DEEP_LETTERS:
            text = top + VIRAMA + bottom
            ref_glyphs, _ = ref.shape(text)
            if len(ref_glyphs) != 1:
                continue                       # Padauk stacks it too
            ours, _ = font.shape(text)
            if len(ours) != 1:
                unfused.append(f"{text}: {[g.name for g in ours]}")
    assert not unfused, (
        f"{font_path.name} stacks what Padauk fuses:\n  " + "\n  ".join(unfused))


# The four pairs Padauk answers with a subjoined SIZE this project does
# not have. Its subjoined forms come in two sizes — uni100D.med at ~75%
# of the letter and uni100D.sml at ~55% — and after ဍ, whose tail leaves
# the smallest pocket of the six, only the .sml one fits at any position.
# Ours are all one size (the .med one), so these four stay worse than the
# reference until a small subjoined class exists. None of them occurs in
# either corpus, in the 12,450-word vocabulary, or in the Jataka text:
# they are spellable, not written. Listed rather than tolerated silently,
# and the test still fails if the list has to grow.
KNOWN_DEEP_STACK_GAPS = {"ဍ္ဋ", "ဍ္ဌ", "ဍ္ဏ", "ဍ္ဠ"}

# Ink-on-ink area scales with the pen: a black display cut doubles every
# stroke and doubles the square units where two strokes cross, without
# anything having moved. So the geometric comparison runs on the face
# whose weight matches the reference — the display cuts are covered by
# the structural test above, which no pen can affect.
REGULAR_WEIGHT_FACE = (ROOT / "projects" / "myanmar-glyph-sans"
                       / "MyanmarGlyphSans-Regular.ttf")


def test_deep_stacks_are_never_drawn_through_each_other():
    """A subjoined form under a full-width tail is ink on ink.

    Measured against the reference rather than against a constant: some
    of the 36 pairs overlap a little in Padauk too, and a threshold
    picked out of the air would either miss the tangles or fail the
    reference implementation. What must not happen is being *worse* than
    the font we trace.
    """
    if not REGULAR_WEIGHT_FACE.exists():
        pytest.skip("shipped font not present")
    ref = _reference_font()
    font = vs.FontUnderTest(REGULAR_WEIGHT_FACE)
    worse = []
    for top in DEEP_LETTERS:
        for bottom in DEEP_LETTERS:
            text = top + VIRAMA + bottom
            if text in KNOWN_DEEP_STACK_GAPS:
                continue
            ours = _cluster_ink_overlap(font, text)
            theirs = _cluster_ink_overlap(ref, text)
            if ours > theirs + 2000:
                worse.append(f"{text}: {ours:.0f} vs Padauk {theirs:.0f}")
    assert not worse, (
        "MyanmarGlyphSans-Regular draws ink through ink where Padauk does "
        "not:\n  " + "\n  ".join(worse))


def test_the_known_deep_stack_gaps_are_still_only_those_four():
    """An allowlist that is never re-checked is a licence, not a record."""
    ref = _reference_font()
    font = vs.FontUnderTest(REGULAR_WEIGHT_FACE)
    still_bad = set()
    for text in KNOWN_DEEP_STACK_GAPS:
        if (_cluster_ink_overlap(font, text)
                > _cluster_ink_overlap(ref, text) + 2000):
            still_bad.add(text)
    fixed = KNOWN_DEEP_STACK_GAPS - still_bad
    assert not fixed, (
        f"these are no longer worse than Padauk — take them off "
        f"KNOWN_DEEP_STACK_GAPS: {sorted(fixed)}")


def _cluster_ink_overlap(font, text):
    """Total ink-on-ink area between the glyphs of one shaped cluster."""
    glyphs, _ = font.shape(text)
    total = 0.0
    for i, a in enumerate(glyphs):
        for b in glyphs[i + 1:]:
            if a.cluster != b.cluster:
                continue
            total += vs.ink_overlap_area(
                vs._translated(font.outline(a.name), a.x, a.y),
                vs._translated(font.outline(b.name), b.x, b.y))
    return total
