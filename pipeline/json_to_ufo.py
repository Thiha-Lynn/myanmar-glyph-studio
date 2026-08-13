#!/usr/bin/env python3
"""Convert a Glyph Studio project (.glyphstudio.json) into UFO font sources.

Usage:
    python3 json_to_ufo.py MyFont.glyphstudio.json build/

Then compile with fontmake:
    fontmake -u build/MyFont-Regular.ufo -o ttf --output-dir build/

What this adds beyond the in-browser draft TTF:
  * standard UFO source (one .glif per glyph) — diffable, PR-able, editable
    in any font editor (Fontra, FontForge, Glyphs, RoboFont)
  * auto-generated OpenType features for the mym2 shaping model:
      - blwf: subjoined (stacked) consonant substitutions  (က + ္ + က → stack)
      - rphf: kinzi
      - contextual variants (wide medial-ra, short u/uu) when drawn
  * auto-placed mark anchors (top/bottom) so ufo2ft's MarkFeatureWriter
    emits GPOS mark/mkmk positioning at build time.

The auto-anchors are a starting point, not a finish line: open the UFO in a
font editor to refine anchor positions once the sketches are in.

Stroke-to-outline expansion mirrors web/js/outline.js — keep them in sync.
"""

import json
import math
import sys
from pathlib import Path

try:
    import ufoLib2
except ImportError:
    sys.exit("ufoLib2 is required:  pip install -r requirements.txt")

UPM = 1000
ASCENDER = 900
DESCENDER = -600
BODY = 550
CAP_SEGMENTS = 8

# ---------------------------------------------------------------------------
# Glyph inventory knowledge (kept aligned with web/data/glyphs.js)
# ---------------------------------------------------------------------------

CONSONANTS = [
    (0x1000, "ka"), (0x1001, "kha"), (0x1002, "ga"), (0x1003, "gha"),
    (0x1004, "nga"), (0x1005, "ca"), (0x1006, "cha"), (0x1007, "ja"),
    (0x1008, "jha"), (0x1009, "nya"), (0x100A, "nnya"), (0x100B, "tta"),
    (0x100C, "ttha"), (0x100D, "dda"), (0x100E, "ddha"), (0x100F, "nna"),
    (0x1010, "ta"), (0x1011, "tha"), (0x1012, "da"), (0x1013, "dha"),
    (0x1014, "na"), (0x1015, "pa"), (0x1016, "pha"), (0x1017, "ba"),
    (0x1018, "bha"), (0x1019, "ma"), (0x101A, "ya"), (0x101B, "ra"),
    (0x101C, "la"), (0x101D, "wa"), (0x101E, "sa"), (0x101F, "ha"),
    (0x1020, "lla"), (0x1021, "a"),
]

OTHER_CODEPOINTS = {
    "i.indep-myanmar": 0x1023, "ii.indep-myanmar": 0x1024,
    "u.indep-myanmar": 0x1025, "uu.indep-myanmar": 0x1026,
    "e.indep-myanmar": 0x1027, "o.indep-myanmar": 0x1029,
    "au.indep-myanmar": 0x102A,
    "tallAa-myanmar": 0x102B, "aa-myanmar": 0x102C, "i-myanmar": 0x102D,
    "ii-myanmar": 0x102E, "u-myanmar": 0x102F, "uu-myanmar": 0x1030,
    "e-myanmar": 0x1031, "ai-myanmar": 0x1032, "anusvara-myanmar": 0x1036,
    "dotBelow-myanmar": 0x1037, "visarga-myanmar": 0x1038,
    "virama-myanmar": 0x1039, "asat-myanmar": 0x103A,
    "medialYa-myanmar": 0x103B, "medialRa-myanmar": 0x103C,
    "medialWa-myanmar": 0x103D, "medialHa-myanmar": 0x103E,
    "greatSa-myanmar": 0x103F,
    "zero-myanmar": 0x1040, "one-myanmar": 0x1041, "two-myanmar": 0x1042,
    "three-myanmar": 0x1043, "four-myanmar": 0x1044, "five-myanmar": 0x1045,
    "six-myanmar": 0x1046, "seven-myanmar": 0x1047, "eight-myanmar": 0x1048,
    "nine-myanmar": 0x1049,
    "sectionMark-myanmar": 0x104A, "section-myanmar": 0x104B,
    "locative-myanmar": 0x104C, "completed-myanmar": 0x104D,
    "aforementioned-myanmar": 0x104E, "genitive-myanmar": 0x104F,
}

CODEPOINTS = {f"{n}-myanmar": cp for cp, n in CONSONANTS}
CODEPOINTS.update(OTHER_CODEPOINTS)

# marks that attach ABOVE a base
TOP_MARKS = {
    "i-myanmar", "ii-myanmar", "ai-myanmar", "anusvara-myanmar",
    "asat-myanmar", "kinzi-myanmar",
}
# marks that attach BELOW a base
BOTTOM_MARKS = {
    "u-myanmar", "uu-myanmar", "dotBelow-myanmar",
    "medialWa-myanmar", "medialHa-myanmar",
    "u-myanmar.alt", "uu-myanmar.alt",
} | {f"{n}-myanmar.sub" for _, n in CONSONANTS}

BASE_NAMES = {f"{n}-myanmar" for _, n in CONSONANTS} | {"greatSa-myanmar"}


# ---------------------------------------------------------------------------
# Stroke -> outline expansion (mirror of web/js/outline.js)
# ---------------------------------------------------------------------------

def _dedupe(points, min_dist):
    out = []
    for p in points:
        if not out:
            out.append(p)
            continue
        q = out[-1]
        if (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 >= min_dist ** 2:
            out.append(p)
    if out and len(points) > 1 and tuple(points[-1]) != tuple(out[-1]):
        out.append(points[-1])
    return out


def _pt_width(p, fallback):
    return p[2] if len(p) > 2 and p[2] > 0 else fallback


def _lerp(p, q, t):
    out = [p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]
    if len(p) > 2 or len(q) > 2:
        pw = p[2] if len(p) > 2 else q[2]
        qw = q[2] if len(q) > 2 else p[2]
        out.append(pw + (qw - pw) * t)
    return out


def _smooth(points, iterations=2):
    for _ in range(iterations):
        if len(points) < 3:
            return points
        out = [points[0]]
        for p, q in zip(points, points[1:]):
            out.append(_lerp(p, q, 0.25))
            out.append(_lerp(p, q, 0.75))
        out.append(points[-1])
        points = out
    return points


def _arc(cx, cy, r, a0, a1, out):
    for i in range(CAP_SEGMENTS + 1):
        a = a0 + (a1 - a0) * (i / CAP_SEGMENTS)
        out.append([cx + r * math.cos(a), cy + r * math.sin(a)])


def _circle(cx, cy, r):
    n = CAP_SEGMENTS * 4
    return [[cx + r * math.cos(2 * math.pi * i / n),
             cy + r * math.sin(2 * math.pi * i / n)] for i in range(n)]


def stroke_to_polygon(stroke):
    """Points are [x, y] or [x, y, w] (per-point pressure width)."""
    base_r = max(1.0, stroke["width"] / 2.0)
    pts = _dedupe(stroke["points"], base_r * 0.35)
    if not pts:
        return None
    if len(pts) == 1:
        return _circle(pts[0][0], pts[0][1],
                       _pt_width(pts[0], stroke["width"]) / 2.0)
    pts = _smooth(pts, 2)

    radii, normals = [], []
    for i in range(len(pts)):
        radii.append(max(1.0, _pt_width(pts[i], stroke["width"]) / 2.0))
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy) or 1.0
        normals.append([-dy / length, dx / length])

    left = [[p[0] + n[0] * r, p[1] + n[1] * r]
            for p, n, r in zip(pts, normals, radii)]
    right = [[p[0] - n[0] * r, p[1] - n[1] * r]
             for p, n, r in zip(pts, normals, radii)]

    poly = list(left)
    pe, ne = pts[-1], normals[-1]
    ae = math.atan2(ne[1], ne[0])
    _arc(pe[0], pe[1], radii[-1], ae, ae - math.pi, poly)
    poly.extend(reversed(right))
    ps, ns = pts[0], normals[0]
    a_s = math.atan2(-ns[1], -ns[0])
    _arc(ps[0], ps[1], radii[0], a_s, a_s - math.pi, poly)
    return poly


def polygons_for(glyph_data):
    polys = []
    for stroke in glyph_data.get("strokes", []):
        poly = stroke_to_polygon(stroke)
        if poly:
            polys.append(poly)
    return polys


def poly_bounds(polys):
    xs = [p[0] for poly in polys for p in poly]
    ys = [p[1] for poly in polys for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------------------
# UFO construction
# ---------------------------------------------------------------------------

def draw_glyph(ufo_glyph, polys):
    pen = ufo_glyph.getPen()
    for poly in polys:
        pen.moveTo((round(poly[0][0]), round(poly[0][1])))
        for p in poly[1:]:
            pen.lineTo((round(p[0]), round(p[1])))
        pen.closePath()


def add_anchor(glyph, name, x, y):
    glyph.appendAnchor({"name": name, "x": round(x), "y": round(y)})


def build_ufo(project, out_dir):
    meta = project.get("meta", {})
    family = meta.get("fontName", "MyMyanmarFont")
    style = meta.get("styleName", "Regular")
    author = meta.get("author", "")

    font = ufoLib2.Font()
    info = font.info
    info.familyName = family
    info.styleName = style
    info.unitsPerEm = UPM
    info.ascender = ASCENDER
    info.descender = DESCENDER
    info.xHeight = BODY
    info.capHeight = ASCENDER
    info.openTypeOS2TypoAscender = ASCENDER + 100
    info.openTypeOS2TypoDescender = DESCENDER - 50
    info.openTypeOS2WinAscent = ASCENDER + 200
    info.openTypeOS2WinDescent = abs(DESCENDER) + 150
    info.openTypeHheaAscender = ASCENDER + 100
    info.openTypeHheaDescender = DESCENDER - 50
    info.copyright = f"Copyright {author or 'the project contributors'}"
    info.openTypeNameLicense = (
        "This Font Software is licensed under the SIL Open Font License, "
        "Version 1.1. https://openfontlicense.org"
    )
    if author:
        info.openTypeNameDesigner = author

    # .notdef and space
    notdef = font.newGlyph(".notdef")
    notdef.width = 600
    space = font.newGlyph("space")
    space.width = 500
    space.unicode = 0x20

    drawn = []
    for name, data in project.get("glyphs", {}).items():
        polys = polygons_for(data)
        if not polys:
            continue
        g = font.newGlyph(name)
        draw_glyph(g, polys)
        x_min, y_min, x_max, y_max = poly_bounds(polys)

        is_mark = name in TOP_MARKS or name in BOTTOM_MARKS
        adv = data.get("advance")
        if adv is None:
            adv = 0 if is_mark else round(x_max + 60)
        g.width = max(0, adv)
        cp = CODEPOINTS.get(name)
        if cp:
            g.unicode = cp

        cx = (x_min + x_max) / 2
        if name in BASE_NAMES:
            add_anchor(g, "top", cx, max(y_max, BODY) + 40)
            add_anchor(g, "bottom", cx, min(y_min, 0) - 40)
        elif name in TOP_MARKS:
            add_anchor(g, "_top", cx, y_min - 20)
        elif name in BOTTOM_MARKS:
            add_anchor(g, "_bottom", cx, y_max + 20)

        drawn.append(name)

    # The blwf/rphf rules consume U+1039 VIRAMA, but the studio never asks
    # contributors to draw it (it is invisible in rendered Burmese).  When
    # any subjoined form exists, synthesize an empty zero-width virama so
    # stacking works in every user-drawn font.
    if "virama-myanmar" not in drawn and any(n.endswith(".sub") for n in drawn):
        v = font.newGlyph("virama-myanmar")
        v.width = 0
        v.unicode = 0x1039
        drawn.append("virama-myanmar")

    font.features.text = generate_features(set(drawn))

    out_dir.mkdir(parents=True, exist_ok=True)
    ufo_path = out_dir / f"{family.replace(' ', '')}-{style}.ufo"
    font.save(ufo_path, overwrite=True)
    return ufo_path, drawn


# ---------------------------------------------------------------------------
# OpenType feature generation (mym2 starter rules)
# ---------------------------------------------------------------------------

def generate_features(drawn):
    """Emit only rules whose glyphs were actually drawn."""
    lines = [
        "# Auto-generated Myanmar shaping features (mym2 starter set).",
        "# Regenerated by json_to_ufo.py — refine by hand as the font matures.",
        "languagesystem DFLT dflt;",
        "languagesystem mym2 dflt;",
        "",
    ]

    # blwf: virama + consonant -> subjoined form
    subs = [
        (f"{n}-myanmar", f"{n}-myanmar.sub")
        for _, n in CONSONANTS
        if f"{n}-myanmar.sub" in drawn and f"{n}-myanmar" in drawn
    ]
    if subs and "virama-myanmar" in drawn:
        lines.append("feature blwf {")
        lines.append("  script mym2;")
        for base, sub in subs:
            lines.append(f"  sub virama-myanmar {base} by {sub};")
        lines.append("} blwf;")
        lines.append("")

    # rphf: kinzi (nga + asat + virama, engine-reordered to follow the base)
    if {"kinzi-myanmar", "nga-myanmar", "asat-myanmar", "virama-myanmar"} <= drawn:
        lines.append("feature rphf {")
        lines.append("  script mym2;")
        lines.append("  sub nga-myanmar asat-myanmar virama-myanmar by kinzi-myanmar;")
        lines.append("} rphf;")
        lines.append("")

    # pres: wide medial-ra in front of wide bases
    wide_bases = [
        f"{n}-myanmar" for n in
        ("kha", "gha", "ca", "cha", "jha", "nnya", "ttha", "ddha", "nna",
         "ta", "tha", "dha", "na", "bha", "ma", "ya", "la", "sa", "ha", "a")
        if f"{n}-myanmar" in drawn
    ]
    if "medialRa-myanmar.wide" in drawn and "medialRa-myanmar" in drawn and wide_bases:
        lines.append(f"@WIDE_BASES = [{' '.join(wide_bases)}];")
        lines.append("feature pres {")
        lines.append("  script mym2;")
        lines.append("  sub medialRa-myanmar' @WIDE_BASES by medialRa-myanmar.wide;")
        lines.append("} pres;")
        lines.append("")

    # blws: short u/uu after bases with descenders or subjoined forms
    desc_ctx = [f"{n}-myanmar.sub" for _, n in CONSONANTS
                if f"{n}-myanmar.sub" in drawn]
    for base_v, alt_v in (("u-myanmar", "u-myanmar.alt"),
                          ("uu-myanmar", "uu-myanmar.alt")):
        if alt_v in drawn and base_v in drawn and desc_ctx:
            lines.append(f"@DESC_{base_v.split('-')[0].upper()} = [{' '.join(desc_ctx)}];")
    if any(f"{v}-myanmar.alt" in drawn for v in ("u", "uu")) and desc_ctx:
        lines.append("feature blws {")
        lines.append("  script mym2;")
        if "u-myanmar.alt" in drawn and "u-myanmar" in drawn:
            lines.append("  sub @DESC_U u-myanmar' by u-myanmar.alt;")
        if "uu-myanmar.alt" in drawn and "uu-myanmar" in drawn:
            lines.append("  sub @DESC_UU uu-myanmar' by uu-myanmar.alt;")
        lines.append("} blws;")
        lines.append("")

    # mark/mkmk GPOS is generated automatically by ufo2ft's MarkFeatureWriter
    # from the top/bottom anchors placed on each glyph.
    return "\n".join(lines)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    project_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    project = json.loads(project_path.read_text(encoding="utf-8"))
    if project.get("format") != "mm-glyph-studio":
        sys.exit("Not a Glyph Studio project file")
    ufo_path, drawn = build_ufo(project, out_dir)
    print(f"Wrote {ufo_path}  ({len(drawn)} drawn glyphs)")
    print("Next:  fontmake -u", ufo_path, "-o ttf --output-dir", out_dir)


if __name__ == "__main__":
    main()
