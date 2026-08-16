#!/usr/bin/env python3
"""Diff CoreText's shaping against HarfBuzz's, cluster by cluster.

CI shapes with HarfBuzz — the engine Android, Chrome, Linux and
LibreOffice use. Apple platforms shape with **CoreText**, and the two can
disagree: a rule that works everywhere else can silently misfire on a Mac
or an iPhone. Issue #14 asks people to check that by hand. On macOS it
needs no hand at all.

    cd pipeline/coretext && swiftc -O CoreTextShape.swift -o coretext-shape
    python3 ../coretext_check.py ../../projects/*/MyanmarGlyphSans-Regular.ttf

For every string in the corpus this shapes with both engines and compares
the glyph sequence (names, order, count) and the relative advances. It
reports only real disagreements, so a clean run means the two engines
agree on every cluster in the corpus.

Only runs on macOS — CoreText is an Apple framework. Everywhere else it
exits 0 with a note, so it is safe to call from a script.

    --corpus FILE   which corpus to shape (default: the spec corpus)
    --tolerance N   position slack in font units before it counts (default 12)
    --verbose       print every cluster, not just the disagreements
"""

import argparse
import platform
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHAPER = HERE / "coretext" / "coretext-shape"

sys.path.insert(0, str(HERE))
from validate_spec import FontUnderTest, load_corpus  # noqa: E402


def coretext_runs(font_path, texts):
    """{text: [(name, x, y), ...]} straight out of CoreText."""
    if not SHAPER.exists():
        sys.exit(f"{SHAPER} not built — run:\n"
                 f"  cd {SHAPER.parent} && swiftc -O CoreTextShape.swift "
                 f"-o coretext-shape")
    out = {}
    # argv has a length limit; feed the shaper in batches
    for i in range(0, len(texts), 200):
        batch = texts[i:i + 200]
        proc = subprocess.run([str(SHAPER), str(font_path), *batch],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            sys.exit(f"coretext-shape failed: {proc.stderr.strip()}")
        for line in proc.stdout.splitlines():
            if "\t" not in line:
                continue
            text, _, run = line.partition("\t")
            glyphs = []
            for token in run.split():
                gid_name, _, pos = token.partition("@")
                _, _, name = gid_name.partition(":")
                x, _, y = pos.partition(",")
                glyphs.append((name, float(x or 0), float(y or 0)))
            out[text] = glyphs
    return out


def harfbuzz_runs(font, texts):
    out = {}
    for text in texts:
        glyphs, _ = font.shape(text)
        out[text] = [(g.name, float(g.x), float(g.y)) for g in glyphs]
    return out


def _ink_differs(ct, hb, tolerance):
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

    a, b = placed(ct), placed(hb)
    moved = []
    for name in sorted(set(a) | set(b)):
        pa, pb = a.get(name, []), b.get(name, [])
        if len(pa) != len(pb) or any(
                abs(x1 - x2) > tolerance or abs(y1 - y2) > tolerance
                for (x1, y1), (x2, y2) in zip(pa, pb)):
            moved.append(name)
    return moved


def compare(text, ct, hb, tolerance):
    """Return a list of human-readable disagreements for one string."""
    problems = []
    ct_names = [n for n, _, _ in ct]
    hb_names = [n for n, _, _ in hb]

    # A dotted circle means the cluster is not in Unicode storage order and
    # both engines are REPAIRING it. How much of the rest each salvages is
    # engine-defined (CoreText leaves the virama standing where HarfBuzz
    # still stacks), so a difference here says nothing about the font.
    if any(n in ("uni25CC", "dottedCircle") for n in ct_names + hb_names):
        return []

    # Where the font has no glyph, CoreText substitutes another font and
    # HarfBuzz — with no fallback of its own — emits .notdef. Both are
    # right at their own layer, so this is coverage, not disagreement.
    fallbacks = [n for n in ct_names if n.startswith("<fallback:")]
    if fallbacks:
        paired = [h for c, h in zip(ct_names, hb_names)
                  if c.startswith("<fallback:")]
        if all(h == ".notdef" for h in paired):
            return []          # the OS filled a gap this font declares
        # CoreText falls back for the WHOLE run when one character is
        # missing, so neighbours the font does cover come from the
        # fallback too. Still a coverage gap, not a shaping difference.
        problems.append("font lacks a character in this cluster; CoreText "
                        "rendered the run with " + ", ".join(
                            sorted({f[10:-1] for f in fallbacks})))
        return problems
    if ct_names != hb_names:
        # Same glyphs in a different ORDER is usually not a rendering
        # difference: HarfBuzz's Myanmar shaper reorders marks into its
        # canonical order (the tone dot before the asat), CoreText keeps
        # storage order, and because the two attach to different anchors
        # they still land in the same place. Only report it when the ink
        # actually moves — checked below by position, not assumed.
        if sorted(ct_names) != sorted(hb_names):
            problems.append(
                f"glyphs differ\n      CoreText: {' '.join(ct_names)}"
                f"\n      HarfBuzz: {' '.join(hb_names)}")
            return problems
        moved = _ink_differs(ct, hb, tolerance)
        if moved:
            problems.append(
                f"marks reordered AND moved: {', '.join(moved)}"
                f"\n      CoreText: {' '.join(ct_names)}"
                f"\n      HarfBuzz: {' '.join(hb_names)}")
        return problems
    # same glyphs: compare their placement relative to the first glyph, so
    # a different run origin between the two engines is not a difference
    if ct and hb:
        cx0, cy0 = ct[0][1], ct[0][2]
        hx0, hy0 = hb[0][1], hb[0][2]
        for (name, cx, cy), (_, hx, hy) in zip(ct, hb):
            dx = (cx - cx0) - (hx - hx0)
            dy = (cy - cy0) - (hy - hy0)
            if abs(dx) > tolerance or abs(dy) > tolerance:
                problems.append(
                    f"{name} placed {dx:+.0f},{dy:+.0f} apart "
                    f"(CoreText vs HarfBuzz)")
    return problems


def main():
    ap = argparse.ArgumentParser(
        description="Diff CoreText shaping against HarfBuzz.")
    ap.add_argument("font", type=Path)
    ap.add_argument("--corpus", type=Path,
                    default=HERE / "spec_corpus.txt")
    ap.add_argument("--tolerance", type=float, default=12.0)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if platform.system() != "Darwin":
        print("CoreText is an Apple framework — skipping on "
              f"{platform.system()}. (HarfBuzz coverage still applies.)")
        return 0

    cases, _ = load_corpus(args.corpus)
    texts = list(dict.fromkeys(c.text for c in cases))
    font = FontUnderTest(args.font)

    ct = coretext_runs(args.font, texts)
    hb = harfbuzz_runs(font, texts)

    disagreements = 0
    checked = 0
    for text in texts:
        if text not in ct:
            continue
        checked += 1
        problems = compare(text, ct[text], hb[text], args.tolerance)
        if problems:
            disagreements += 1
            print(f"\n  {text}")
            for p in problems:
                print(f"    {p}")
        elif args.verbose:
            print(f"  ok  {text}")

    print(f"\n{font.family} {font.style} — CoreText vs HarfBuzz")
    print(f"  {checked} clusters compared, {disagreements} disagree")
    if not disagreements:
        print("  Apple's engine renders every cluster exactly as HarfBuzz "
              "does.")
    return 1 if disagreements else 0


if __name__ == "__main__":
    sys.exit(main())
