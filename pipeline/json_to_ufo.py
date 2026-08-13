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
  * mark anchors (top/bottom on bases, _top/_bottom plus a stacking anchor
    on marks) so ufo2ft's MarkFeatureWriter emits GPOS mark/mkmk positioning
    at build time.

Anchors are auto-placed from the ink; positions dragged in the studio's
anchor mode (stored per glyph as "anchors": {name: [x, y]}) override the
auto placement. The UFO stays editable in any font editor for finer work.

Stroke-to-outline expansion mirrors web/js/outline.js — keep them in sync.
"""

import json
import math
import re
import sys
import unicodedata
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

_UNI_NAME = re.compile(r"^uni([0-9A-Fa-f]{4})$")
_U_NAME = re.compile(r"^u([0-9A-Fa-f]{5,6})$")  # supplementary plane (u116D0…)


def name_to_codepoint(name):
    """Friendly names via CODEPOINTS; uniXXXX/uXXXXX production names directly.

    The extended-coverage and optional-Latin inventories
    (web/data/glyphs-extended.js, glyphs-extended-ab.js, glyphs-latin.js)
    use uniXXXX names (uXXXXX beyond the BMP, e.g. Myanmar Extended-C), so
    the pipeline needs no per-character tables for them.
    """
    cp = CODEPOINTS.get(name)
    if cp:
        return cp
    m = _UNI_NAME.match(name) or _U_NAME.match(name)
    return int(m.group(1), 16) if m else None


# Blocks whose letters act as mark-carrying bases: core Myanmar, Extended-B
# (Tai Laing, Shan Pali), Extended-A (Khamti Shan), Extended-C (Unicode 16).
MYANMAR_BLOCKS = ((0x1000, 0x109F), (0xA9E0, 0xA9FF),
                  (0xAA60, 0xAA7F), (0x116D0, 0x116FF))


def in_myanmar_blocks(cp):
    return any(lo <= cp <= hi for lo, hi in MYANMAR_BLOCKS)

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

# Signs that wrap around their base (medial ra). Their sketched coordinates
# are kept as drawn, and their advance is SMALL BUT POSITIVE: it is what
# moves the pen past the wrap's left stem so the base lands inside the
# wrap. Zero would stack the base on top of that stem (Padauk gives U+103C
# an advance of 172/1024 for exactly this reason).
WRAP_SIGNS = {"medialRa-myanmar", "medialRa-myanmar.wide"}
# fraction of the wrap's ink width that sits left of the base — only used
# when a project supplies no advance; reproduces Padauk's proportion
WRAP_ADVANCE_RATIO = 0.30

# Anchor names the studio may store per glyph ("anchors": {name: [x, y]}).
KNOWN_ANCHORS = {"top", "bottom", "_top", "_bottom"}

SIGN_LSB = 60  # left sidebearing given to re-aligned spacing signs

# the four styles that may share a legacy family name
RIBBI_STYLES = {"Regular", "Bold", "Italic", "Bold Italic"}


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


def stroke_to_polygon(stroke, width_scale=1.0):
    """Points are [x, y] or [x, y, w] (per-point pressure width).

    A stroke marked "fill": true is already a closed contour (e.g. an
    imported SVG outline): its points ARE the polygon, no expansion.

    width_scale thickens or thins the stroke — this is how weight masters
    are derived from one drawing. Point decimation deliberately uses the
    UNSCALED width, so every weight produces the identical point count and
    contour order and the masters interpolate.
    """
    if stroke.get("fill"):
        pts = stroke.get("points") or []
        return pts if len(pts) >= 3 else None
    base_r = max(1.0, stroke["width"] / 2.0)
    pts = _dedupe(stroke["points"], base_r * 0.35)
    if not pts:
        return None
    if len(pts) == 1:
        return _circle(pts[0][0], pts[0][1],
                       _pt_width(pts[0], stroke["width"]) * width_scale / 2.0)
    pts = _smooth(pts, 2)

    radii, normals = [], []
    for i in range(len(pts)):
        radii.append(max(1.0, _pt_width(pts[i], stroke["width"])
                         * width_scale / 2.0))
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


def polygons_for(glyph_data, width_scale=1.0):
    polys = []
    for stroke in glyph_data.get("strokes", []):
        poly = stroke_to_polygon(stroke, width_scale)
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

RDP_EPSILON = 3.0     # max font units a decimated point may stray (see below)
RDP_RELATIVE = 0.006  # …but never more than this fraction of the contour size
RDP_FLOOR = 0.6       # …and never less than this, so tiny marks keep detail
CORNER_DEGREES = 50   # sharper turns than this stay crisp (on-curve)


def _rdp_indices(points, epsilon, first, last, keep):
    """Ramer-Douglas-Peucker, collecting the indices worth keeping."""
    ax, ay = points[first][0], points[first][1]
    bx, by = points[last][0], points[last][1]
    dx, dy = bx - ax, by - ay
    norm = math.hypot(dx, dy)
    worst, worst_i = -1.0, None
    for i in range(first + 1, last):
        px, py = points[i][0], points[i][1]
        if norm:
            d = abs(dy * px - dx * py + bx * ay - by * ax) / norm
        else:
            d = math.hypot(px - ax, py - ay)
        if d > worst:
            worst, worst_i = d, i
    if worst_i is not None and worst > epsilon:
        _rdp_indices(points, epsilon, first, worst_i, keep)
        keep.add(worst_i)
        _rdp_indices(points, epsilon, worst_i, last, keep)


def contour_plan(poly, epsilon=RDP_EPSILON, corner_degrees=CORNER_DEGREES):
    """Decide the shape of one contour: which points to keep, and which of
    them are corners.

    Stroke expansion emits a dense polygon (smoothing quadruples the point
    count). Decimating it and marking only real corners as on-curve turns
    that polygon into a compact, genuinely curved TrueType contour: smooth
    where the hand was smooth, crisp where the letter turns.

    Returns [(index_into_poly, is_on_curve), …], or [] for a degenerate
    contour. Computed from ONE geometry and reused across weight masters,
    so every master stays interpolation-compatible.
    """
    rounded = [(round(p[0]), round(p[1])) for p in poly]
    uniq = [i for i in range(len(rounded))
            if i == 0 or rounded[i] != rounded[i - 1]]
    while len(uniq) > 1 and rounded[uniq[0]] == rounded[uniq[-1]]:
        uniq.pop()
    if len(uniq) < 3:
        return []

    pts = [rounded[i] for i in uniq]
    # Scale the tolerance to the contour: 3 units is invisible on a letter
    # but would flatten a tone dot, so small shapes keep their detail.
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    diagonal = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    epsilon = max(RDP_FLOOR, min(epsilon, diagonal * RDP_RELATIVE))

    keep = {0, len(pts) - 1}
    _rdp_indices(pts, epsilon, 0, len(pts) - 1, keep)
    kept = sorted(keep)
    if len(kept) < 3:
        kept = list(range(len(pts)))

    limit = math.radians(corner_degrees)
    plan = []
    for n, k in enumerate(kept):
        a = pts[kept[n - 1]]
        b = pts[k]
        c = pts[kept[(n + 1) % len(kept)]]
        turn = abs(math.atan2(c[1] - b[1], c[0] - b[0])
                   - math.atan2(b[1] - a[1], b[0] - a[0]))
        if turn > math.pi:
            turn = 2 * math.pi - turn
        plan.append((uniq[k], turn > limit))

    # a fully smooth contour still needs one on-curve point: a contour of
    # nothing but off-curve points is a TrueType special case that several
    # tools (notably overlap removal) cannot read
    if not any(on for _, on in plan):
        plan[0] = (plan[0][0], True)
    return plan


def _curve_segments(points):
    """[(x, y, on_curve)] -> closed list of (start, control, end) segments.

    Off-curve runs follow the TrueType reading: consecutive control points
    imply an on-curve point at their midpoint. control is None for a
    straight line.
    """
    start = next((i for i, p in enumerate(points) if p[2]), 0)
    ordered = points[start:] + points[:start]
    origin = (ordered[0][0], ordered[0][1])
    cur = origin
    pending, segments = [], []
    for x, y, on_curve in ordered[1:] + [ordered[0]]:
        if not on_curve:
            pending.append((x, y))
            continue
        if not pending:
            segments.append((cur, None, (x, y)))
        else:
            for i, control in enumerate(pending):
                if i < len(pending) - 1:
                    nxt = pending[i + 1]
                    end = ((control[0] + nxt[0]) / 2.0,
                           (control[1] + nxt[1]) / 2.0)
                else:
                    end = (x, y)
                segments.append((cur, control, end))
                cur = end
            pending = []
        cur = (x, y)
    return origin, segments


def _quad_to_cubic(p0, q, p1):
    """Exact quadratic -> cubic control points."""
    return ((p0[0] + 2.0 / 3.0 * (q[0] - p0[0]),
             p0[1] + 2.0 / 3.0 * (q[1] - p0[1])),
            (p1[0] + 2.0 / 3.0 * (q[0] - p1[0]),
             p1[1] + 2.0 / 3.0 * (q[1] - p1[1])))


def draw_glyph(ufo_glyph, polys, smooth=True, ref_polys=None):
    """Write the expanded polygons into the glyph as cubic contours.

    Cubic is the native curve of UFO sources, so what lands in the .ufo is
    what Fontra, FontForge, Glyphs and RoboFont expect to open, and ufo2ft
    converts it to TrueType quadratics at build time.

    ref_polys supplies the geometry the contour plan is computed from.
    Weight masters pass the reference (unscaled) polygons so every master
    keeps identical point counts and curve structure, which is what makes
    them interpolatable.
    """
    pen = ufo_glyph.getPen()
    reference = ref_polys if ref_polys is not None else polys
    r = lambda p: (round(p[0]), round(p[1]))   # noqa: E731
    for poly, ref in zip(polys, reference):
        plan = contour_plan(ref)
        if not plan:
            continue
        pts = [(poly[i][0], poly[i][1], on) for i, on in plan]
        if not smooth:
            pen.moveTo(r(pts[0]))
            for p in pts[1:]:
                pen.lineTo(r(p))
            pen.closePath()
            continue
        origin, segments = _curve_segments(pts)
        pen.moveTo(r(origin))
        for p0, control, p1 in segments:
            if control is None:
                pen.lineTo(r(p1))
            else:
                c1, c2 = _quad_to_cubic(p0, control, p1)
                pen.curveTo(r(c1), r(c2), r(p1))
        pen.closePath()


def add_anchor(glyph, name, x, y):
    glyph.appendAnchor({"name": name, "x": round(x), "y": round(y)})


def build_ufo(project, out_dir, width_scale=1.0, style_name=None,
              weight_class=400):
    """Build one UFO master.

    width_scale derives weights from a single drawing (see make_variable.py);
    style_name/weight_class name that master.
    """
    meta = project.get("meta", {})
    family = meta.get("fontName", "MyMyanmarFont")
    style = style_name or meta.get("styleName", "Regular")
    author = meta.get("author", "")

    font = ufoLib2.Font()
    info = font.info
    info.familyName = family
    info.styleName = style
    info.openTypeOS2WeightClass = weight_class
    # Legacy (nameID 1/2) naming: only Regular/Bold/Italic/Bold Italic may
    # share one family name. Every other weight becomes its own legacy
    # family — "Family Light / Regular" — while the typographic family
    # (nameID 16/17) keeps them together as one family for modern apps.
    if style in RIBBI_STYLES:
        info.styleMapFamilyName = family
        info.styleMapStyleName = style.lower()
    else:
        info.styleMapFamilyName = f"{family} {style}"
        info.styleMapStyleName = "regular"
        info.openTypeNamePreferredFamilyName = family
        info.openTypeNamePreferredSubfamilyName = style
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
    # gasp: grid-fit + antialias at every size (fontbakery: gasp check)
    info.openTypeGaspRangeRecords = [
        {"rangeMaxPPEM": 0xFFFF, "rangeGaspBehavior": [0, 1, 2, 3]},
    ]

    # .notdef must be visible (a hollow box), per the OpenType spec
    notdef = font.newGlyph(".notdef")
    notdef.width = 600
    pen = notdef.getPen()
    pen.moveTo((80, 0)); pen.lineTo((520, 0))
    pen.lineTo((520, 700)); pen.lineTo((80, 700)); pen.closePath()
    pen.moveTo((140, 60)); pen.lineTo((140, 640))
    pen.lineTo((460, 640)); pen.lineTo((460, 60)); pen.closePath()

    # space and no-break space
    space = font.newGlyph("space")
    space.width = 500
    space.unicode = 0x20
    nbspace = font.newGlyph("nbspace")
    nbspace.width = 500
    nbspace.unicode = 0xA0

    drawn = []
    categories = {}   # glyph -> GDEF class, written as public.openTypeCategories
    ink_right = {}    # glyph -> right edge of its ink, for the pres measurement
    advances = {}     # glyph -> advance width
    base_glyphs = []  # glyphs that carry top/bottom anchors
    for name, data in project.get("glyphs", {}).items():
        if name == "virama-myanmar":
            # U+1039 is invisible in rendered Burmese — ignore any sketched
            # ink and let the synthesizer below emit the empty control glyph.
            continue
        polys = polygons_for(data, width_scale)
        if not polys:
            continue

        # The contour plan is always taken from the drawing as sketched,
        # before any re-alignment below: every weight master must decide
        # the same points and corners or the masters cannot interpolate.
        ref_polys = polygons_for(data, 1.0) if width_scale != 1.0 else polys

        cp = name_to_codepoint(name)

        # Mark classification: curated sets for the core Burmese inventory;
        # the Unicode category (Mn = non-spacing mark) for everything else,
        # so the extended ethnic-language groups need no hand-kept tables.
        is_mark = name in TOP_MARKS or name in BOTTOM_MARKS
        if not is_mark and cp and name not in BASE_NAMES:
            is_mark = unicodedata.category(chr(cp)) == "Mn"

        x_min, y_min, x_max, y_max = poly_bounds(polys)
        adv = data.get("advance")

        # Spacing signs (Mc: aa, tall-aa, e-vowel, visarga, medial-ya and
        # the extension equivalents) are sketched beside the ◌ carrier,
        # which bakes the carrier's width into their coordinates. When the
        # advance is automatic, left-align the ink so the sign gets a normal
        # sidebearing instead of the carrier-sized gap.
        is_spacing_sign = (not is_mark and cp is not None
                           and unicodedata.category(chr(cp)) == "Mc"
                           and name not in WRAP_SIGNS)
        auto_advance = not adv and not is_mark and name not in WRAP_SIGNS
        # …and the same normalisation rescues any spacing glyph whose ink
        # sits left of the origin (some source fonts park modifier letters
        # in negative space to overprint the previous letter), which would
        # otherwise yield a negative — so clamped to zero — advance.
        if auto_advance and (is_spacing_sign and x_min > SIGN_LSB
                             or x_min < 0):
            dx = SIGN_LSB - x_min
            polys = [[[p[0] + dx, p[1]] for p in poly] for poly in polys]
            x_min += dx
            x_max += dx

        g = font.newGlyph(name)
        draw_glyph(g, polys, ref_polys=ref_polys)
        if cp:
            g.unicode = cp

        # Non-spacing marks never advance the pen: the shaper positions them
        # onto the base, and a stored advance would double-space every
        # syllable. Wrapping signs DO advance, just barely — see WRAP_SIGNS.
        if is_mark:
            adv = 0
        elif not adv and name in WRAP_SIGNS:
            adv = max(1, round((x_max - x_min) * WRAP_ADVANCE_RATIO))
        elif not adv:
            # None, or a stored 0 on a spacing glyph that has ink: a glyph
            # with visible outlines must move the pen or it overprints its
            # neighbour (some source fonts leave modifier letters at 0)
            adv = round(x_max + 60)
        g.width = max(0, adv)

        # ---- anchors: hand-placed positions from the studio win ----------
        manual = data.get("anchors") or {}
        placed = set()

        def anchor(anchor_name, ax, ay, _g=g, _manual=manual, _placed=placed):
            pos = _manual.get(anchor_name)
            if (isinstance(pos, (list, tuple)) and len(pos) >= 2
                    and all(isinstance(v, (int, float)) for v in pos[:2])):
                ax, ay = pos[0], pos[1]
            add_anchor(_g, anchor_name, ax, ay)
            _placed.add(anchor_name)

        cx = (x_min + x_max) / 2
        cy = (y_min + y_max) / 2
        # U+25CC DOTTED CIRCLE also carries base anchors: shaping engines
        # place it under isolated marks, and the mark must attach to it.
        is_myanmar_base = bool(
            cp and not is_mark
            and ((in_myanmar_blocks(cp)
                  and unicodedata.category(chr(cp)) == "Lo")
                 or cp == 0x25CC))
        # Marks carry the attaching _anchor plus a plain anchor on their
        # outer side so further marks can stack on them (GPOS mkmk).
        if name in BASE_NAMES or (name not in TOP_MARKS
                                  and name not in BOTTOM_MARKS
                                  and is_myanmar_base):
            anchor("top", cx, max(y_max, BODY) + 40)
            anchor("bottom", cx, min(y_min, 0) - 40)
            base_glyphs.append(name)
        elif name in TOP_MARKS:
            anchor("_top", cx, y_min - 20)
            anchor("top", cx, y_max + 20)
        elif name in BOTTOM_MARKS:
            anchor("_bottom", cx, y_max + 20)
            anchor("bottom", cx, y_min - 20)
        elif is_mark:
            # extension-language mark: decide the attachment side from
            # where the ink was drawn relative to the letter body
            if cy >= BODY / 2:
                anchor("_top", cx, y_min - 20)
                anchor("top", cx, y_max + 20)
            else:
                anchor("_bottom", cx, y_max + 20)
                anchor("bottom", cx, y_min - 20)

        # honor hand-placed anchors the heuristics would not have emitted
        for anchor_name in sorted(set(manual) & (KNOWN_ANCHORS - placed)):
            anchor(anchor_name, 0, 0)

        # GDEF class: non-spacing marks are "mark", everything else "base".
        # Stated explicitly so spacing signs (Mc: aa, medial ya …) are not
        # mistaken for marks by the shaper.
        #
        # The wrapping medial ra must NOT be a mark here: HarfBuzz zeroes the
        # advance of GDEF marks, and its small advance is exactly what moves
        # the base inside the wrap.
        categories[name] = "mark" if is_mark else "base"
        ink_right[name] = x_max
        advances[name] = adv
        drawn.append(name)

    # The blwf/rphf rules consume U+1039 VIRAMA, but the studio never asks
    # contributors to draw it (it is invisible in rendered Burmese).  When
    # any subjoined form or the kinzi exists, synthesize an empty zero-width
    # virama so stacking and kinzi work in every user-drawn font.
    if any(n.endswith(".sub") for n in drawn) or "kinzi-myanmar" in drawn:
        v = font.newGlyph("virama-myanmar")
        v.width = 0
        v.unicode = 0x1039
        categories["virama-myanmar"] = "mark"
        drawn.append("virama-myanmar")

    font.lib["public.openTypeCategories"] = categories

    # Optional kerning carried straight through to the UFO, so ufo2ft's
    # KernFeatureWriter emits GPOS kern. Project JSON:
    #   "groups":  { "public.kern1.round": ["ka-myanmar", ...] },
    #   "kerning": { "ka-myanmar ta-myanmar": -20 }   (space-separated pair)
    groups = project.get("groups") or {}
    if groups:
        font.groups = {k: list(v) for k, v in groups.items()}
    kerning = {}
    for pair, value in (project.get("kerning") or {}).items():
        parts = pair.split() if " " in pair else pair.split(",")
        if len(parts) == 2:
            kerning[(parts[0].strip(), parts[1].strip())] = value
    if kerning:
        font.kerning = kerning

    font.features.text = generate_features(
        set(drawn), wide_bases=measure_wide_bases(base_glyphs, ink_right,
                                                  advances))

    # PostScript production names: the friendly source names carry hyphens,
    # which are not valid in shipped glyph names. ufo2ft renames at compile
    # time from this mapping (uniXXXX / uXXXXX, suffixes preserved).
    ps_names = {}
    for gname in drawn:
        if gname == "kinzi-myanmar":
            ps_names[gname] = "uni1004103A1039"  # AGL ligature form
            continue
        base, dot, suffix = gname.partition(".")
        cp = name_to_codepoint(base if dot else gname)
        if cp:
            ps = f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:04X}"
            ps_names[gname] = ps + (dot + suffix if dot else "")
    ps_names["nbspace"] = "uni00A0"
    font.lib["public.postscriptNames"] = ps_names

    out_dir.mkdir(parents=True, exist_ok=True)
    ufo_path = out_dir / f"{family.replace(' ', '')}-{style}.ufo"
    font.save(ufo_path, overwrite=True)
    return ufo_path, drawn


# ---------------------------------------------------------------------------
# OpenType feature generation (mym2 starter rules)
# ---------------------------------------------------------------------------

def measure_wide_bases(base_glyphs, ink_right, advances):
    """Which base letters overflow the narrow medial-ra wrap?

    Medial ra ြ wraps around the letter that follows it, and the letter
    only fits if the wrap reaches past it. Rather than hard-code which
    letters are "wide" — which is a property of the drawing, not of the
    script — measure it: the base sits at the wrap's advance, so it fits
    when its ink ends before the wrap's ink does.

    Returns the base glyphs that need the wide variant, or None when the
    font has no narrow ra to compare against.
    """
    narrow = "medialRa-myanmar"
    if narrow not in ink_right:
        return None
    wrap_reach = ink_right[narrow]
    base_start = advances.get(narrow, 0)
    return sorted(name for name in base_glyphs
                  if base_start + ink_right.get(name, 0) > wrap_reach - 20)


def generate_features(drawn, wide_bases=None):
    """Emit only rules whose glyphs were actually drawn.

    Rules are written before any script statement so they register under
    every declared languagesystem: DFLT (fallback shaping), mym2 (the
    current Myanmar shaping model) and mymr (legacy engines).
    """
    lines = [
        "# Auto-generated Myanmar shaping features (mym2 starter set).",
        "# Regenerated by json_to_ufo.py — refine by hand as the font matures.",
        "languagesystem DFLT dflt;",
        "languagesystem mym2 dflt;",
        "languagesystem mymr dflt;",
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
        for base, sub in subs:
            lines.append(f"  sub virama-myanmar {base} by {sub};")
        lines.append("} blwf;")
        lines.append("")

    # rphf: kinzi (nga + asat + virama, engine-reordered to follow the base)
    if {"kinzi-myanmar", "nga-myanmar", "asat-myanmar", "virama-myanmar"} <= drawn:
        lines.append("feature rphf {")
        lines.append("  sub nga-myanmar asat-myanmar virama-myanmar by kinzi-myanmar;")
        lines.append("} rphf;")
        lines.append("")

    # pres: wide medial-ra in front of the bases that overflow the narrow one
    if wide_bases is None:
        # no measurement available — fall back to the letters that are wide
        # in most Burmese designs
        wide_bases = [
            f"{n}-myanmar" for n in
            ("ka", "kha", "gha", "ca", "cha", "jha", "nnya", "ttha", "ddha",
             "nna", "ta", "tha", "dha", "na", "bha", "ma", "ya", "la", "sa",
             "ha", "a")
        ]
    wide_bases = [n for n in wide_bases if n in drawn]
    if "medialRa-myanmar.wide" in drawn and "medialRa-myanmar" in drawn and wide_bases:
        lines.append(f"@WIDE_BASES = [{' '.join(wide_bases)}];")
        lines.append("feature pres {")
        lines.append("  sub medialRa-myanmar' @WIDE_BASES by medialRa-myanmar.wide;")
        lines.append("} pres;")
        lines.append("")

    # blws: short u/uu after bases with descenders or subjoined forms
    desc_ctx = [f"{n}-myanmar.sub" for _, n in CONSONANTS
                if f"{n}-myanmar.sub" in drawn]
    blws_rules = []
    if desc_ctx:
        for base_v, alt_v in (("u-myanmar", "u-myanmar.alt"),
                              ("uu-myanmar", "uu-myanmar.alt")):
            if alt_v in drawn and base_v in drawn:
                cls = f"@DESC_{base_v.split('-')[0].upper()}"
                lines.append(f"{cls} = [{' '.join(desc_ctx)}];")
                blws_rules.append(f"  sub {cls} {base_v}' by {alt_v};")
    if blws_rules:
        lines.append("feature blws {")
        lines.extend(blws_rules)
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
