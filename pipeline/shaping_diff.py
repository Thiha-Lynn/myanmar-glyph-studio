#!/usr/bin/env python3
"""Diff a platform text engine's shaping against HarfBuzz's, cluster by cluster.

CI shapes with HarfBuzz — the engine Android, Chrome, Linux and LibreOffice
use. Apple platforms shape with **CoreText**, Windows with **DirectWrite**,
and any of the three can disagree: a rule that works everywhere else can
silently misfire on one platform. Issue #14 asks people to check that by
hand; on the platform itself it needs no hand at all.

Both engine checkers drive their comparison from here —
`coretext_check.py` on macOS, `directwrite_check.py` on Windows — so the
two report the same way and a fix to the comparison lands in both:

    engine_runs = {text: [(glyph_name, x, y), ...]}   # the platform engine
    hb_runs     = harfbuzz_runs(font, texts)          # the reference

Positions are in the font's own units (both sides normalised to 1000/em by
their callers), measured relative to each run's first glyph, so a different
run origin between two engines is not counted as a difference.

What this deliberately does NOT report, because none of it is a font bug:

* **Reordered marks that land in the same place.** HarfBuzz's Myanmar
  shaper reorders marks into its canonical order (the tone dot before the
  asat); a platform engine may keep storage order. The two marks attach to
  different anchors, so the picture is identical — checked by coordinate,
  never assumed.
* **Dotted circles.** Both engines are repairing input that is not in
  Unicode storage order, and how much each salvages is engine-defined.
* **Font fallback.** Where the font has no glyph, an engine may substitute
  another font while HarfBuzz — with no fallback of its own — emits
  `.notdef`. That is a coverage gap this font already declares.
"""

import sys

FALLBACK_PREFIX = "<fallback:"


def use_utf8_stdout():
    """Make it safe to print Myanmar text on any console.

    A Windows console is cp1252 by default, so the first cluster this
    report tries to print raises UnicodeEncodeError and the run dies
    before saying what it found — which is exactly when the output
    matters. Replace what a terminal genuinely cannot draw; never crash
    on it.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):        # not a reconfigurable
            pass                                    # text stream; leave it


def harfbuzz_runs(font, texts):
    """{text: [(name, x, y), ...]} from the reference engine."""
    out = {}
    for text in texts:
        glyphs, _ = font.shape(text)
        out[text] = [(g.name, float(g.x), float(g.y)) for g in glyphs]
    return out


def ink_differs(engine_run, hb_run, tolerance):
    """Glyph names whose placement really differs between the two runs.

    Both runs are normalised to their own first glyph, then each glyph
    name's set of positions is compared. Reordering alone cancels out;
    anything left is ink that would land somewhere else on screen.
    """
    def placed(run):
        if not run:
            return {}
        x0, y0 = run[0][1], run[0][2]
        out = {}
        for name, x, y in run:
            out.setdefault(name, []).append((round(x - x0), round(y - y0)))
        return {k: sorted(v) for k, v in out.items()}

    a, b = placed(engine_run), placed(hb_run)
    moved = []
    for name in sorted(set(a) | set(b)):
        pa, pb = a.get(name, []), b.get(name, [])
        if len(pa) != len(pb) or any(
                abs(x1 - x2) > tolerance or abs(y1 - y2) > tolerance
                for (x1, y1), (x2, y2) in zip(pa, pb)):
            moved.append(name)
    return moved


def compare(engine_run, hb_run, tolerance, engine="the platform engine"):
    """Human-readable disagreements for one string, or [] when they agree."""
    problems = []
    eng_names = [n for n, _, _ in engine_run]
    hb_names = [n for n, _, _ in hb_run]

    # A dotted circle means the cluster is not in Unicode storage order and
    # both engines are REPAIRING it. How much of the rest each salvages is
    # engine-defined (CoreText leaves the virama standing where HarfBuzz
    # still stacks), so a difference here says nothing about the font.
    if any(n in ("uni25CC", "dottedCircle") for n in eng_names + hb_names):
        return []

    # Where the font has no glyph, an engine that owns the whole text stack
    # substitutes another font; HarfBuzz emits .notdef. Both are right at
    # their own layer, so this is coverage, not disagreement.
    fallbacks = [n for n in eng_names if n.startswith(FALLBACK_PREFIX)]
    if fallbacks:
        paired = [h for e, h in zip(eng_names, hb_names)
                  if e.startswith(FALLBACK_PREFIX)]
        if all(h == ".notdef" for h in paired):
            return []          # the OS filled a gap this font declares
        # CoreText falls back for the WHOLE run when one character is
        # missing, so neighbours the font does cover come from the
        # fallback too. Still a coverage gap, not a shaping difference.
        problems.append(f"font lacks a character in this cluster; {engine} "
                        "rendered the run with " + ", ".join(
                            sorted({f[len(FALLBACK_PREFIX):-1]
                                    for f in fallbacks})))
        return problems

    if eng_names != hb_names:
        # Same glyphs in a different ORDER is usually not a rendering
        # difference: HarfBuzz's Myanmar shaper reorders marks into its
        # canonical order (the tone dot before the asat), a platform engine
        # may keep storage order, and because the two attach to different
        # anchors they still land in the same place. Only report it when
        # the ink actually moves — checked below by position, not assumed.
        if sorted(eng_names) != sorted(hb_names):
            problems.append(
                f"glyphs differ\n      {engine}: {' '.join(eng_names)}"
                f"\n      HarfBuzz: {' '.join(hb_names)}")
            return problems
        moved = ink_differs(engine_run, hb_run, tolerance)
        if moved:
            problems.append(
                f"marks reordered AND moved: {', '.join(moved)}"
                f"\n      {engine}: {' '.join(eng_names)}"
                f"\n      HarfBuzz: {' '.join(hb_names)}")
        return problems

    # same glyphs: compare their placement relative to the first glyph, so
    # a different run origin between the two engines is not a difference
    if engine_run and hb_run:
        ex0, ey0 = engine_run[0][1], engine_run[0][2]
        hx0, hy0 = hb_run[0][1], hb_run[0][2]
        for (name, ex, ey), (_, hx, hy) in zip(engine_run, hb_run):
            dx = (ex - ex0) - (hx - hx0)
            dy = (ey - ey0) - (hy - hy0)
            if abs(dx) > tolerance or abs(dy) > tolerance:
                problems.append(
                    f"{name} placed {dx:+.0f},{dy:+.0f} apart "
                    f"({engine} vs HarfBuzz)")
    return problems


def report(engine, font, texts, engine_runs, hb_runs, tolerance,
           verbose=False):
    """Print every disagreement and the tally. Returns a process exit code."""
    use_utf8_stdout()
    disagreements = 0
    checked = 0
    for text in texts:
        if text not in engine_runs:
            continue
        checked += 1
        problems = compare(engine_runs[text], hb_runs[text], tolerance,
                           engine)
        if problems:
            disagreements += 1
            print(f"\n  {text}")
            for p in problems:
                print(f"    {p}")
        elif verbose:
            print(f"  ok  {text}")

    print(f"\n{font.family} {font.style} — {engine} vs HarfBuzz")
    print(f"  {checked} clusters compared, {disagreements} disagree")
    if not disagreements:
        print(f"  {engine} renders every cluster exactly as HarfBuzz does.")
    return 1 if disagreements else 0
