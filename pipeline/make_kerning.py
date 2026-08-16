#!/usr/bin/env python3
"""Derive kerning pairs by measuring the drawn outlines.

The fonts carry full Latin alongside Myanmar — Burmese text is routinely
written with English words in it — but shipped with no kerning at all
(fontbakery: `gpos_kerning_info: lacks-kern-info`). Myanmar itself is not
kerned: its advances are fixed and everything else is mark attachment.
Latin is, and pairs like AV, To, Yo, P. fall apart without it.

This measures rather than guesses. For an ordered pair it walks both
outlines band by band, finds the narrowest place where the two letters
actually face each other, and compares that with the gap a flat-sided
control pair leaves (HH by default). Where an open shape — a diagonal, a
round side, an overhanging arm — leaves far more air than the control,
the pair is pulled in by the difference.

    python3 make_kerning.py MyFont.glyphstudio.json          # report only
    python3 make_kerning.py MyFont.glyphstudio.json --write   # store pairs
    python3 make_kerning.py MyFont.glyphstudio.json --max-pairs 400

Pairs land in the project file's `kerning` block, which json_to_ufo
already passes to the UFO for ufo2ft's KernFeatureWriter to compile into
GPOS. Nothing else in the pipeline changes.

Conservative on purpose: only pairs whose excess exceeds --threshold are
recorded, adjustments are clamped to --limit, and nothing is emitted for
Myanmar glyphs.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import json_to_ufo  # noqa: E402

# Latin letters and digits are the kernable set here; Myanmar is not
# kerned (fixed advances plus mark attachment), and punctuation joins in
# because ". " and "A." are among the worst-looking untouched pairs.
LATIN_UPPER = list(range(0x41, 0x5B))
LATIN_LOWER = list(range(0x61, 0x7B))
PUNCT = [0x2C, 0x2E, 0x3A, 0x3B, 0x21, 0x3F, 0x27, 0x22]
# Digits are deliberately absent. These fonts draw them TABULAR — one
# advance for all ten — so figures line up in columns; kerning any pair
# containing one destroys that alignment, and fontbakery fails the font
# for it (`tabular_kerning: has-tabular-kerning`). A font with
# proportional figures could kern them; this one must not.

BAND = 40          # sampling height, font units
CONTROL = ("uni0048", "uni0048")   # HH — two flat stems, the neutral gap


def outline_profile(polys):
    """Right-most and left-most ink per horizontal band.

    Returns {band_index: (x_min, x_max)} so two glyphs can be compared
    band by band without rasterising anything.
    """
    bands = {}
    for poly in polys:
        n = len(poly)
        for i in range(n):
            x0, y0 = poly[i]
            x1, y1 = poly[(i + 1) % n]
            steps = max(1, int(abs(y1 - y0) / (BAND / 4)) + 1)
            for s in range(steps + 1):
                t = s / steps
                x = x0 + (x1 - x0) * t
                y = y0 + (y1 - y0) * t
                b = int(y // BAND)
                lo, hi = bands.get(b, (x, x))
                bands[b] = (min(lo, x), max(hi, x))
    return bands


def pair_gap(left, right, left_adv):
    """Narrowest air between two glyphs, and how much they face each other.

    Returns (gap, confidence) or None when they never share a band.

    The narrowest gap alone is a trap. A period sits in two bands at the
    bottom; against a P it "sees" only the stem, never the bowl arching
    overhead, so the minimum reads enormous and a naive correction tucks
    the dot under the bowl. Confidence is the fraction of the taller
    glyph's height where the two actually face each other, and it scales
    the correction down exactly in those cases.
    """
    shared = set(left) & set(right)
    if not shared:
        return None
    gaps = []
    for b in shared:
        left_edge = left[b][1]                 # right-most ink of the left
        right_edge = right[b][0] + left_adv    # left-most ink of the right
        gaps.append(right_edge - left_edge)
    confidence = len(shared) / max(len(left), len(right), 1)
    return min(gaps), confidence


def main():
    ap = argparse.ArgumentParser(
        description="Derive kerning pairs from the drawn outlines.")
    ap.add_argument("project", type=Path)
    ap.add_argument("--write", action="store_true",
                    help="store the pairs in the project file")
    ap.add_argument("--threshold", type=float, default=35.0,
                    help="ignore excess air below this (font units)")
    ap.add_argument("--limit", type=float, default=120.0,
                    help="never pull a pair closer than this")
    ap.add_argument("--max-pairs", type=int, default=500)
    args = ap.parse_args()

    project = json.loads(args.project.read_text(encoding="utf-8"))
    glyphs = project.get("glyphs", {})

    def name_for(cp):
        return f"uni{cp:04X}"

    # measure every candidate once
    profiles, advances = {}, {}
    wanted = LATIN_UPPER + LATIN_LOWER + PUNCT
    for cp in wanted:
        name = name_for(cp)
        data = glyphs.get(name)
        if not data or not data.get("strokes"):
            continue
        polys = json_to_ufo.polygons_for(data)
        if not polys:
            continue
        x_min, _, x_max, _ = json_to_ufo.poly_bounds(polys)
        profiles[name] = outline_profile(polys)
        advances[name] = data.get("advance") or round(x_max + 60)

    if CONTROL[0] not in profiles:
        sys.exit("control pair (H) is not drawn — cannot calibrate")
    control, _ = pair_gap(profiles[CONTROL[0]], profiles[CONTROL[1]],
                          advances[CONTROL[0]])
    print(f"control gap (HH): {control:.0f} units from "
          f"{len(profiles)} measured glyphs")

    pairs = {}
    for lname in profiles:
        for rname in profiles:
            measured = pair_gap(profiles[lname], profiles[rname],
                                advances[lname])
            if measured is None:
                continue
            gap, confidence = measured
            excess = gap - control
            if excess <= args.threshold:
                continue
            value = -min((excess - args.threshold) * confidence, args.limit)
            if value > -args.threshold / 2:      # too small to be worth a pair
                continue
            pairs[f"{lname} {rname}"] = round(value)

    ranked = sorted(pairs.items(), key=lambda kv: kv[1])[:args.max_pairs]
    print(f"{len(pairs)} pairs exceed the threshold; keeping "
          f"{len(ranked)} tightest")
    for pair, value in ranked[:12]:
        left, right = pair.split()
        try:
            shown = f"{chr(int(left[3:], 16))}{chr(int(right[3:], 16))}"
        except ValueError:
            shown = pair
        print(f"   {shown}   {value:+.0f}")
    if len(ranked) > 12:
        print(f"   … {len(ranked) - 12} more")

    if args.write:
        project["kerning"] = dict(ranked)
        args.project.write_text(
            json.dumps(project, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(f"\nwrote {len(ranked)} pairs into {args.project.name}")
    else:
        print("\n(dry run — pass --write to store them)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
