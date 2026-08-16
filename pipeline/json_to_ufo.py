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
    "asat-myanmar", "kinzi-myanmar", "iAnusvara-myanmar",
}
# marks that attach BELOW a base
BOTTOM_MARKS = {
    "u-myanmar", "uu-myanmar", "dotBelow-myanmar",
    "medialWa-myanmar", "medialHa-myanmar",
}
# The long u/uu forms drawn for stacked clusters (စက္ကူ) are not below-marks
# at all: they are as tall as the letter body and belong BESIDE the cluster,
# to the right of the stack — which is what Padauk does (its uni1030 after a
# subjoined form is a spacing glyph with a 288-unit advance, ink −439…434,
# exactly the proportions of our .alt drawings). Hanging them from the
# stack's bottom anchor instead is how စက္ကူ's vowel reached −1341.
SPACING_VOWELS = {"u-myanmar.alt", "uu-myanmar.alt"}
# Spacing signs that render BEFORE their base. Marks never attach to these,
# so they carry no anchors (a mark following one in the cluster belongs to
# the base, which the shaper has already moved in front of).
PRE_BASE_SIGNS = {"e-myanmar", "uni1084"}
# subjoined consonants form their own attachment class: stacks hang from
# the base's CENTRE (Padauk: 0.50 of ink width) while below-vowels hang
# from its right bowl (0.78 on wide letters) — one shared anchor cannot
# serve both, so stacks use stack/_stack and vowels keep bottom/_bottom
STACK_MARKS = {f"{n}-myanmar.sub" for _, n in CONSONANTS}

BASE_NAMES = {f"{n}-myanmar" for _, n in CONSONANTS} | {"greatSa-myanmar"}

# Signs that wrap around their base (medial ra). Their sketched coordinates
# are kept as drawn, and their advance is SMALL BUT POSITIVE: it is what
# moves the pen past the wrap's left stem so the base lands inside the
# wrap. Zero would stack the base on top of that stem (Padauk gives U+103C
# an advance of 172/1024 for exactly this reason).
WRAP_SIGNS = {"medialRa-myanmar", "medialRa-myanmar.wide",
              "medialRa-myanmar.tall", "medialRa-myanmar.tall.wide",
              # fused wrap+u forms (Padauk's uni103C102F set): the sweep
              # retracts and the u bar stands in the opening — one drawing
              "medialRa-myanmar.u", "medialRa-myanmar.u.wide",
              "medialRa-myanmar.u.tall", "medialRa-myanmar.u.tall.wide"}
# fraction of the wrap's ink width that sits left of the base — only used
# when a project supplies no advance; reproduces Padauk's proportion
WRAP_ADVANCE_RATIO = 0.30

# Anchor names the studio may store per glyph ("anchors": {name: [x, y]}).
# side/_side chain marks BESIDE the previous below-mark at normal depth:
# ha to the right of wa (ကွှ), u beside wa (သွူ), the tone dot beside a deep
# hook (ရွှံ့) — Padauk solves all of these with ligatures (uni103D103E,
# uni103E102F) whose parts sit side by side; the side chain reproduces that
# geometry without extra artwork.
KNOWN_ANCHORS = {"top", "bottom", "_top", "_bottom", "stack", "_stack",
                 "side", "_side"}

SIGN_LSB = 60  # left sidebearing given to re-aligned spacing signs

# Vertical clearance between a letter's own ink and the mark above it.
# Measured on Padauk: its ကိ leaves 76 units between the base's ink top
# (448) and the ring's ink bottom (524). Ours adds 20 more on the mark's
# own _top anchor, so 60 here reproduces that gap — and keeps stacked
# above-marks inside the +900 ascender.
TOP_CLEARANCE = 60
# Deepest a subjoined letter may hang from, whatever the base's leg does.
# Same floor the below-vowels use: Padauk's subjoined band is −440…−80.
STACK_FLOOR = -50
# How far right of the kinzi's ink the next above-mark's centre is planted
# (half a vowel ring plus a gap): Padauk's fused kinzi+anusvara puts the
# added ink to the right of the hook (သင်္ခံ: 1098…1466 vs bare 1113…1301).
KINZI_SIDE_GAP = 225
# How far the kinzi.left variant's ink is pre-shifted when a medial ya
# follows in the cluster (the vowel then belongs to the ya and cannot chain
# beside the kinzi) — clears the vowel over the ya with ~200 units to spare
# on the widest base while staying over the base's body.
KINZI_MEDIAL_SHIFT = 250
# How far right of the base's bottom anchor the in-wrap u stroke plants.
# Unlike Padauk's shallow narrow frame (bar hanging in open space), our
# wraps draw a deep under-sweep ending in a right tail at base_x_max−48;
# the bar sits ON that tail and continues ~150 units below the sweep, so
# it reads as the tail descending — the stroke-below-the-wrap convention
# realised on this wrap design.
WRAPSTROKE_DX = 183

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


def column_depth(polys, x0, x1):
    """Lowest ink y inside the x band [x0, x1], or None when no ink there.

    The expanded stroke polygons are dense (smoothing quadruples the points),
    so sampling the polygon vertices is an accurate picture of where the
    letter actually descends.
    """
    lowest = None
    for poly in polys:
        for p in poly:
            if x0 <= p[0] <= x1 and (lowest is None or p[1] < lowest):
                lowest = p[1]
    return lowest


def scale_about_top(polys, s):
    """Scale polygons by s about the top-centre of their joint bounds.

    Used for the .small below-mark variants that must fit INSIDE the
    medial-ra wrap: keeping the top edge fixed preserves the attachment
    relationship while the ink shrinks upward, clear of the wrap's
    under-stroke.
    """
    if not polys:
        return polys
    x0, _, x1, y1 = poly_bounds(polys)
    cx = (x0 + x1) / 2
    return [[[cx + (p[0] - cx) * s, y1 + (p[1] - y1) * s] for p in poly]
            for poly in polys]


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


def top_anchor_y(y_max):
    """Where an above-mark attaches on a glyph whose ink tops at y_max.

    Follows the ink so tall letters push their marks up, with BODY as the
    floor so a short letter still carries its mark at the usual height.
    """
    return max(y_max + TOP_CLEARANCE, BODY - 40)


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

    # space and no-break space — Burmese spaces are narrower than Latin
    # practice (Padauk uses 378/1000); 500 made word gaps read as holes
    space = font.newGlyph("space")
    space.width = 380
    space.unicode = 0x20
    nbspace = font.newGlyph("nbspace")
    nbspace.width = 380
    nbspace.unicode = 0xA0

    drawn = []
    categories = {}   # glyph -> GDEF class, written as public.openTypeCategories
    ink_right = {}    # glyph -> right edge of its ink, for the pres measurement
    advances = {}     # glyph -> advance width
    base_glyphs = []  # glyphs that carry top/bottom anchors
    # Side-chain clearances are optical: a heavier master's strokes bulge
    # toward each other by half the extra pen on each facing edge, so the
    # anchor-level gap grows with the pen to keep the INK gap at the
    # designed 55 units in every weight (46 ≈ the typical stroke width).
    pen_pad = max(0, round(46 * (width_scale - 1.0)))
    geo = {}          # sources for the synthesized contextual variants below
    variant_sources = {"medialWa-myanmar", "medialHa-myanmar",
                       "u-myanmar", "uu-myanmar", "medialYa-myanmar",
                       "kinzi-myanmar"}
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
        is_mark = (name in TOP_MARKS or name in BOTTOM_MARKS
                   or name in STACK_MARKS)
        if not is_mark and cp and name not in BASE_NAMES:
            is_mark = unicodedata.category(chr(cp)) == "Mn"
        if name in SPACING_VOWELS:
            is_mark = False          # a spacing form, see SPACING_VOWELS

        x_min, y_min, x_max, y_max = poly_bounds(polys)
        adv = data.get("advance")

        # Now that the ink is measured: a "subjoined" form drawn at full
        # body height is not a below-form at all. Padauk's ဈ stacks as a
        # SPACING glyph beside its base (uni1008.med, ink −429…423) rather
        # than under it, and hanging that 847-unit drawing from a below
        # anchor buries it at −916. Decided by measurement, so a font that
        # draws a small ဈ under the base still gets the below treatment.
        if name in STACK_MARKS and y_max > 0:
            is_mark = False

        # Spacing signs (Mc: aa, tall-aa, e-vowel, visarga, medial-ya and
        # the extension equivalents) are sketched beside the ◌ carrier,
        # which bakes the carrier's width into their coordinates. When the
        # advance is automatic, left-align the ink so the sign gets a normal
        # sidebearing instead of the carrier-sized gap.
        is_spacing_sign = (not is_mark and name not in WRAP_SIGNS
                           and (name in SPACING_VOWELS
                                or name in STACK_MARKS
                                or (cp is not None
                                    and unicodedata.category(chr(cp)) == "Mc")))
        auto_advance = not adv and not is_mark and name not in WRAP_SIGNS
        # …and the same normalisation rescues any spacing glyph whose ink
        # sits left of the origin (some source fonts park modifier letters
        # in negative space to overprint the previous letter), which would
        # otherwise yield a negative — so clamped to zero — advance.
        realigned = (auto_advance and (is_spacing_sign and x_min > SIGN_LSB
                                       or x_min < 0))
        if realigned:
            dx = SIGN_LSB - x_min
            polys = [[[p[0] + dx, p[1]] for p in poly] for poly in polys]
            x_min += dx
            x_max += dx

        # Anchors are measured on the UNSCALED reference drawing (under the
        # same left-alignment), not on this master's pen-scaled ink: every
        # weight master then derives the IDENTICAL anchor coordinates, so
        # attachment heights stay at the design position in every weight —
        # the Bold pen no longer pushes its marks 10–20 units higher — and
        # the masters interpolate cleanly. The ink bulges ±half the extra
        # pen around those fixed spots, which is exactly how a fixed-anchor
        # family behaves.
        if ref_polys is polys or width_scale == 1.0:
            ax_min, ay_min, ax_max, ay_max = x_min, y_min, x_max, y_max
            anchor_polys = polys
        else:
            ax_min, ay_min, ax_max, ay_max = poly_bounds(ref_polys)
            if realigned:
                adx = SIGN_LSB - ax_min
                anchor_polys = [[[p[0] + adx, p[1]] for p in poly]
                                for poly in ref_polys]
                ax_min += adx
                ax_max += adx
            else:
                anchor_polys = ref_polys

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

        cx = (ax_min + ax_max) / 2
        cy = (ay_min + ay_max) / 2
        # Vowel marks sit over the letter's right bowl on wide two-bowl
        # letters and just right of centre on narrow ones — calibrated
        # against Padauk on the traced sample: ကီ lands at 0.73 and ကု at
        # 0.78 of the ink width, ခု at 0.56. Stacked consonants stay at
        # dead centre (0.50) via their own stack anchor.
        ink_w = max(1, ax_max - ax_min)
        mark_x = ax_min + ink_w * (0.75 if ink_w > 700 else 0.55)
        # Leg avoidance (BELOW-marks only — top marks never meet the leg):
        # when the letter's own ink descends through the anchor spot (ည's
        # tail sweeps under its right bowl), slide the bottom anchor to the
        # nearest genuinely open column band so the below-mark is not drawn
        # through the leg. Letters with a clear underside at the preferred
        # spot (က ခ န ရ …) are untouched, and letters that are deep
        # everywhere keep the preferred spot — the −50 depth clamp already
        # handles those.
        bottom_x = mark_x
        if not is_mark:
            band = column_depth(anchor_polys, mark_x - 50, mark_x + 50)
            if band is not None and band < -160:
                best = None
                for i in range(19):                    # 0.40 … 0.85
                    cand = ax_min + ink_w * (0.40 + i * 0.025)
                    d = column_depth(anchor_polys, cand - 50, cand + 50)
                    if (d is None or d >= -160) and (
                            best is None
                            or abs(cand - mark_x) < abs(best - mark_x)):
                        best = cand
                if best is not None:
                    bottom_x = best
        # U+25CC DOTTED CIRCLE also carries base anchors: shaping engines
        # place it under isolated marks, and the mark must attach to it.
        is_myanmar_base = bool(
            cp and not is_mark
            and ((in_myanmar_blocks(cp)
                  and unicodedata.category(chr(cp)) == "Lo")
                 or cp == 0x25CC))
        # Side-form base variants (na-myanmar.alt …) carry the same anchors
        # as the letters they stand in for: they are swapped in by GSUB in
        # front of below-marks, and the marks must still find their spots.
        is_base_variant = (not is_mark and "." in name
                           and name.partition(".")[0] in BASE_NAMES
                           and name not in WRAP_SIGNS)
        # Marks carry the attaching _anchor plus a plain anchor on their
        # outer side so further marks can stack on them (GPOS mkmk).
        if name in BASE_NAMES or is_base_variant or (
                name not in TOP_MARKS
                and name not in BOTTOM_MARKS
                and name not in STACK_MARKS
                and is_myanmar_base):
            # bottom marks stay near baseline depth even when the base has
            # a deep leg (န ရ ဋ …): the PLAIN vowel tucked beside the leg
            # is Padauk's own side-form solution — its u.med is 355 units
            # tall, the same size as our plain ု, sitting at y −95…−450.
            # The −50 floor puts ours at −90…−441. Never substitute the
            # long stack-form .alt here (it is 868 units tall and belongs
            # under subjoined letters only). Stacks keep full ink depth.
            anchor("top", mark_x, top_anchor_y(ay_max))
            anchor("bottom", bottom_x, max(min(ay_min, 0), -50) - 40)
            # …and the subjoined letter hangs from the same clamped depth:
            # Padauk lands every subjoined form in the −440…−80 band whatever
            # the base does (uni1014.alt + uni1014.med, uni101B + uni101B.med),
            # because following the leg all the way down puts န္န at −890 —
            # 290 units past the descender, into the next line of text.
            anchor("stack", cx, max(min(ay_min, 0), STACK_FLOOR) - 40)
            if not is_base_variant:
                # variants are GSUB-only stand-ins: they never follow a
                # wrap and must not skew the wide-base measurement
                base_glyphs.append(name)
        elif (name.startswith("medialYa-myanmar")
                and name != "medialYa-myanmar.beforewa"):
            # ကျု: the below-vowel sits BESIDE the ya-pinn's leg at normal
            # below-vowel depth (Padauk renders u/uu as spacing forms after
            # the leg, at −95…−450 — never hanging from the leg's bottom).
            # The side anchor's x puts the attaching mark's ink just right
            # of the leg; its y −40 lands the mark's top at −60.
            # A top anchor must come with it: once ya is a mark base, it
            # intercepts the backwards base scan, so ကျိ would lose its
            # i-ring without one (Padauk anchors i over the ya curve too).
            anchor("side", ax_max - 30, -40)
            anchor("top", cx, top_anchor_y(ay_max))
        elif is_spacing_sign and name not in PRE_BASE_SIGNS:
            # Post-base spacing signs (ာ ါ and the long stack vowels) are
            # mark bases too: in ကော် the asat sits over the ာ, in ကာံ the
            # anusvara does — Padauk pulls both back onto the sign. Without
            # anchors here the mark keeps its drawn position at the pen and
            # floats off the end of the cluster.
            #
            # The height does NOT follow the sign's ink: ါ is a 875-unit
            # stem, and a mark above THAT lands at 1303 — past usWinAscent,
            # clipped by Windows. Padauk's fused ော် glyph keeps the asat
            # under the stem's own top (856), so the mark stays in the band
            # every other above-mark uses and crosses the stem instead.
            anchor("top", mark_x, BODY - 40)
            if name in SPACING_VOWELS:
                # A tone mark after the tall vowel stroke sits BESIDE it at
                # mid depth, never underneath (the stroke's own ink runs to
                # −438): Padauk's ကျို့ puts the dot 26 units right of the
                # stroke at −135…−300.
                anchor("bottom", ax_max + 110 + pen_pad, -115)
            else:
                anchor("bottom", bottom_x + pen_pad,
                       max(min(ay_min, 0), -50) - 40)
        elif name == "kinzi-myanmar":
            # A vowel after the kinzi lands BESIDE it, not on top of it:
            # stacking a second above-mark on the kinzi sends သင်္ကြီ's ii to
            # y 1345 — past usWinAscent, so Windows and browsers clip it.
            # Padauk ships fused kinzi+vowel glyphs for exactly this, and
            # they put the vowel to the RIGHT of the hook: its plain kinzi
            # spans 1113…1301 in သင်္ခ, its fused kinzi+anusvara 1098…1466
            # in သင်္ခံ — all of the added ink is on the right. This anchor
            # reproduces that geometry without extra artwork.
            anchor("_top", cx, ay_min - 20)
            anchor("top", ax_max + KINZI_SIDE_GAP + pen_pad, ay_min - 20)
        elif name in TOP_MARKS:
            anchor("_top", cx, ay_min - 20)
            anchor("top", cx, ay_max + 20)
        elif name in BOTTOM_MARKS:
            # No plain "bottom" chain here: hanging the next mark UNDER a
            # below-mark is how ရွှံ့ ended up 748 units deep. Marks that
            # follow a below-mark chain BESIDE it instead (side/_side):
            # tops aligned, next ink starting 55 units right (the spec's
            # 50-unit clearance protocol plus a margin) — which is the
            # geometry of Padauk's uni103D103E / uni103E102F ligatures.
            anchor("_bottom", cx, ay_max + 20)
            anchor("side", ax_max, ay_max + 20)
            anchor("_side", ax_min - 55 - pen_pad, ay_max + 20)
        elif name in STACK_MARKS:
            anchor("_stack", cx, ay_max + 20)
            # A medial or tone mark after a stack chains BESIDE it, tops
            # aligned — the same rule below-marks follow. Hanging it from
            # the stack's own bottom put က္ကွိ's ွ at −814; Padauk keeps
            # every part of the cluster inside the −610…0 band.
            anchor("side", ax_max, ay_max + 20)
        elif is_mark:
            # extension-language mark: decide the attachment side from
            # where the ink was drawn relative to the letter body
            if cy >= BODY / 2:
                anchor("_top", cx, ay_min - 20)
                anchor("top", cx, ay_max + 20)
            else:
                anchor("_bottom", cx, ay_max + 20)
                anchor("bottom", cx, ay_min - 20)

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
        if name in variant_sources:
            geo[name] = (polys, ref_polys, adv)
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

    # ---- synthesized contextual variants (no extra artwork needed) -------
    # Padauk covers the awkward medial clusters with dedicated ligature and
    # small-form glyphs; these variants reproduce that behaviour from the
    # contributor's own drawing.
    #
    # X.small (wa/ha/u/uu, 75%): a below-mark after the medial-ra wrap must
    # fit INSIDE the wrap — full-size ink crosses the wrap's under-stroke
    # (Padauk's own answer is uni103D103E.small & friends). Anchored high
    # (_bottom at y_max−30) so the ink tucks right under the base.
    SMALL_SCALE = 0.75
    if "medialRa-myanmar" in drawn:
        for src in ("medialWa-myanmar", "medialHa-myanmar",
                    "u-myanmar", "uu-myanmar"):
            if src not in geo:
                continue
            polys_m, ref_m, _ = geo[src]
            vname = src + ".small"
            g = font.newGlyph(vname)
            tp = scale_about_top(polys_m, SMALL_SCALE)
            tr = tp if ref_m is polys_m else scale_about_top(ref_m, SMALL_SCALE)
            draw_glyph(g, tp, ref_polys=tr)
            g.width = 0
            # anchors from the reference-scaled geometry: every master
            # derives identical coordinates (see the a-bounds convention)
            vx0, _, vx1, vy1 = poly_bounds(tr)
            add_anchor(g, "_bottom", (vx0 + vx1) / 2, vy1 - 30)
            add_anchor(g, "side", vx1, vy1 + 20)
            add_anchor(g, "_side", vx0 - 55 - pen_pad, vy1 + 20)
            categories[vname] = "mark"
            drawn.append(vname)

    # medialYa.beforewa: ကျွ nests the wa UNDER THE BASE inside the ya hook
    # (Padauk: uni103B103D, wa centred ≈220 units left of the ya origin) —
    # not beside the leg where ကျု's vowel goes. A ya variant with its side
    # anchor at that tuck position, substituted only when wa/ha follows,
    # gives each context its own geometry.
    if "medialYa-myanmar" in geo and any(
            n in drawn for n in ("medialWa-myanmar", "medialHa-myanmar")):
        polys_m, ref_m, ya_adv = geo["medialYa-myanmar"]
        vname = "medialYa-myanmar.beforewa"
        g = font.newGlyph(vname)
        draw_glyph(g, polys_m, ref_polys=ref_m)
        g.width = max(0, ya_adv)
        vx0, _, vx1, vy1 = poly_bounds(ref_m)   # reference geometry
        add_anchor(g, "top", (vx0 + vx1) / 2, top_anchor_y(vy1))
        add_anchor(g, "side", vx0 - 225, -40)
        categories[vname] = "base"
        drawn.append(vname)

    # kinzi.left: in base+kinzi+medial-ya clusters (အင်္ကျီ) the top vowel
    # attaches to the YA — a base glyph, so the mark chain restarts and the
    # vowel cannot chain beside the kinzi. Over a wide base the two marks
    # then share the same airspace (kinzi at 0.75 of the base, the vowel
    # over the ya curve) and collide by ~40 units. Padauk's fused
    # kinzi+vowel glyphs put the kinzi PART well to the left (သင်္ချိုင်း:
    # fused ink from 1019 under a base starting at 1024); this variant is
    # the same ink pre-shifted left, substituted only when a ya follows.
    if "kinzi-myanmar" in geo:
        polys_m, ref_m, _ = geo["kinzi-myanmar"]
        vname = "kinzi-myanmar.left"
        g = font.newGlyph(vname)
        draw_glyph(g, polys_m, ref_polys=ref_m)
        g.width = 0
        vx0, vy0, vx1, _ = poly_bounds(ref_m)   # reference geometry
        # same ink; the attaching anchor sits RIGHT of centre, so GPOS
        # pulls the whole glyph left of the base's mark spot by the shift
        add_anchor(g, "_top", (vx0 + vx1) / 2 + KINZI_MEDIAL_SHIFT, vy0 - 20)
        add_anchor(g, "top", vx1 + KINZI_SIDE_GAP + pen_pad, vy0 - 20)
        categories[vname] = "mark"
        drawn.append(vname)

    # u.wrapstroke: inside the medial-ra wrap, တစ်ချောင်းငင် is written as
    # a straight stroke hanging from the wrap's under-sweep, not the curl —
    # Padauk fuses it into the wrap (uni103C102F: a vertical bar with a
    # small rightward tail near the wrapped base's right bowl, descending
    # to −429). One synthesized mark reproduces that for every wrap
    # variant: a monolinear bar built with the project's own pen, whose
    # attachment anchor plants it WRAPSTROKE_DX right of the base's bottom
    # anchor — which lands it at the base's right bowl edge (Padauk's spot)
    # for narrow and wide bases alike.
    fused_wraps = [n for n in ("medialRa-myanmar.u", "medialRa-myanmar.u.wide",
                               "medialRa-myanmar.u.tall",
                               "medialRa-myanmar.u.tall.wide") if n in drawn]
    if fused_wraps and "u-myanmar" in drawn:
        # The wrap+u fusion consumes the ု character: the wrap glyph is
        # swapped for its fused form and the vowel becomes this invisible
        # zero-width mark (same trick as the synthesized empty virama).
        # It carries the chain anchors so မြို့'s tone dot still lands
        # beside the fused bar instead of under the base.
        g = font.newGlyph("u-myanmar.ghost")
        g.width = 0
        add_anchor(g, "_bottom", 0, -40)
        add_anchor(g, "side", 220, -95)
        categories["u-myanmar.ghost"] = "mark"
        drawn.append("u-myanmar.ghost")
    if (not fused_wraps and "medialRa-myanmar" in drawn
            and "u-myanmar" in drawn):
        vname = "u-myanmar.wrapstroke"
        g = font.newGlyph(vname)
        path = {"width": 48, "points": [[0, -250], [0, -470], [5, -515],
                                        [28, -545], [70, -557]]}
        bar = [stroke_to_polygon(path, width_scale)]
        bar_ref = ([stroke_to_polygon(path, 1.0)]
                   if width_scale != 1.0 else bar)
        draw_glyph(g, bar, ref_polys=bar_ref)
        g.width = 0
        vx0, _, vx1, vy1 = poly_bounds(bar_ref)   # reference geometry
        cxs = (vx0 + vx1) / 2
        add_anchor(g, "_bottom", cxs - WRAPSTROKE_DX, -40)
        # the tone dot of မြို့ chains beside the stroke at mid depth
        add_anchor(g, "side", vx1 + 55 + pen_pad, -95)
        categories[vname] = "mark"
        drawn.append(vname)

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
                                                  advances),
        bases=base_glyphs)

    # PostScript production names: the friendly source names carry hyphens,
    # which are not valid in shipped glyph names. ufo2ft renames at compile
    # time from this mapping (uniXXXX / uXXXXX, suffixes preserved).
    ps_names = {}
    for gname in drawn:
        base, dot, suffix = gname.partition(".")
        if base == "kinzi-myanmar":
            ps_names[gname] = "uni1004103A1039" + dot + suffix  # AGL ligature
            continue
        if base == "iAnusvara-myanmar":
            ps_names[gname] = "uni102D1036" + dot + suffix      # AGL ligature
            continue
        # whole name first: the independent-vowel names contain a dot of
        # their own (o.indep-myanmar → U+1029), and splitting at it would
        # orphan them from their codepoint
        cp = name_to_codepoint(gname)
        if cp:
            ps = f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:04X}"
            ps_names[gname] = ps
            continue
        cp = name_to_codepoint(base) if dot else None
        if cp:
            ps = f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:04X}"
            ps_names[gname] = ps + dot + suffix
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

    The base does NOT have to end before the wrap's ink does: in
    traditional designs the narrow hook finishes over the base's right
    shoulder, with the base poking a little past it. Calibrated against
    Padauk's own narrow/wide split measured on the traced sample project:
    every base Padauk keeps narrow overhangs the wrap by at most ~73
    units, every base it widens overhangs by 136+ — so 100 splits the
    gap. (The old strict rule sent nearly every letter to the wide wrap,
    which is why ခြ ပြ မြ looked loose.)
    """
    narrow = "medialRa-myanmar"
    if narrow not in ink_right:
        return None
    wrap_reach = ink_right[narrow]
    base_start = advances.get(narrow, 0)
    return sorted(name for name in base_glyphs
                  if base_start + ink_right.get(name, 0) > wrap_reach + 100)


def generate_features(drawn, wide_bases=None, bases=None):
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
    base_cls = [n for n in (bases or []) if n in drawn]
    pres_lookups = []
    if "medialRa-myanmar.wide" in drawn and "medialRa-myanmar" in drawn and wide_bases:
        lines.append(f"@WIDE_BASES = [{' '.join(wide_bases)}];")
        pres_lookups.append([
            "  lookup ra_wide {",
            "    sub medialRa-myanmar' @WIDE_BASES by medialRa-myanmar.wide;",
            "  } ra_wide;"])
    # Tall wraps: the hook rises when ိ/ီ/ဲ sits over the WRAPPED base
    # (Padauk: ကြီ → uni103C.alt.wide, ခြီ → uni103C.alt.narr). A separate
    # lookup AFTER ra_wide, so the narrow/wide choice is made first and
    # this one only adds height. The filtering set leaves only the trigger
    # marks visible: ကြွီ still goes tall across the intervening ွ.
    tall_triggers = [n for n in ("i-myanmar", "ii-myanmar", "ai-myanmar")
                     if n in drawn]
    tall_pairs = [(p, t) for p, t in
                  (("medialRa-myanmar", "medialRa-myanmar.tall"),
                   ("medialRa-myanmar.wide", "medialRa-myanmar.tall.wide"))
                  if p in drawn and t in drawn]
    if tall_pairs and tall_triggers and base_cls:
        lines.append(f"@RA_TALL_TRIGGERS = [{' '.join(tall_triggers)}];")
        lines.append(f"@TALLABLE_BASES = [{' '.join(base_cls)}];")
        block = [
            "  lookup ra_tall {",
            "    lookupflag UseMarkFilteringSet @RA_TALL_TRIGGERS;"]
        for plain, tall in tall_pairs:
            block.append(f"    sub {plain}' @TALLABLE_BASES "
                         f"@RA_TALL_TRIGGERS by {tall};")
        block.append("  } ra_tall;")
        pres_lookups.append(block)
    # ya before wa/ha: swap in the variant whose side anchor tucks the
    # following mark under the base (ကျွ), instead of beside the leg (ကျု)
    ya_targets = [n for n in ("medialWa-myanmar", "medialHa-myanmar")
                  if n in drawn]
    if "medialYa-myanmar.beforewa" in drawn and ya_targets:
        pres_lookups.append([
            "  lookup ya_tuck {",
            # lookupflag is STICKY within a feature block: without the
            # reset this lookup inherits ra_tall's filtering set, which
            # hides the wa it must see (ကျွ silently stops tucking)
            "    lookupflag 0;",
            f"    sub medialYa-myanmar' [{' '.join(ya_targets)}] "
            "by medialYa-myanmar.beforewa;",
            "  } ya_tuck;"])
    # …then fuse the pair into the traced ligature where one is drawn:
    # the hook, leg and tucked medial are one woven drawing (Padauk's
    # uni103B103D / uni103B103E) — overlaying the separate pieces
    # crosses their strokes (ကျွ လျှ).
    ya_ligs = [(m, f"medialYa-myanmar.{s}")
               for m, s in (("medialWa-myanmar", "wa"),
                            ("medialHa-myanmar", "ha"))
               if f"medialYa-myanmar.{s}" in drawn and m in drawn]
    if "medialYa-myanmar.beforewa" in drawn and ya_ligs:
        block = ["  lookup ya_fuse {", "    lookupflag 0;"]
        for m, lig in ya_ligs:
            block.append(
                f"    sub medialYa-myanmar.beforewa {m} by {lig};")
        block.append("  } ya_fuse;")
        pres_lookups.append(block)
    if pres_lookups:
        lines.append("feature pres {")
        for block in pres_lookups:
            lines.extend(block)
        lines.append("} pres;")
        lines.append("")

    # blws: short u/uu after subjoined forms AND after bases whose own ink
    # descends below the baseline (န ရ ဋ ဌ ဠ — measured, not listed).
    # The mark-filtering set lets the context see through intervening
    # marks (ကျွန်ုပ် is န + ် + ု: the asat must not break the match)
    # while still matching the u/uu target itself.
    # The long .alt vowels apply ONLY after subjoined forms — beside a
    # descender leg the plain vowel at the clamped side anchor is already
    # Padauk's med-form answer (see the anchor comment above).
    sub_ctx = [f"{n}-myanmar.sub" for _, n in CONSONANTS
               if f"{n}-myanmar.sub" in drawn]
    desc_ctx = list(sub_ctx)
    blws_rules = []
    filter_marks = list(sub_ctx)  # subjoined forms are marks the context
    if desc_ctx:                  # must SEE (skipping them breaks စက္ကူ)
        for base_v, alt_v in (("u-myanmar", "u-myanmar.alt"),
                              ("uu-myanmar", "uu-myanmar.alt")):
            if alt_v in drawn and base_v in drawn:
                cls = f"@DESC_{base_v.split('-')[0].upper()}"
                lines.append(f"{cls} = [{' '.join(desc_ctx)}];")
                blws_rules.append(f"  sub {cls} {base_v}' by {alt_v};")
                filter_marks.append(base_v)
    # Side-form bases: swap the base itself for its leg-free variant in
    # front of below-marks (Padauk: နု→uni1014.alt, ညွ→uni100A.alt,
    # ရူ→uni101B.alt — measured per base: ra only swaps before u/uu, ရွ
    # stays plain). The filtering set holds ONLY the trigger marks, so the
    # swap still fires across an intervening top mark (နို့) or asat
    # (ကျွန်ုပ် — Padauk swaps there too).
    # A subjoined letter is a below-form too: န + ္ + န stacks the second
    # န under the first, and with the leg still there the stack is pushed
    # to −890. Padauk swaps the same side form in (uni1014.alt +
    # uni1014.med) — but leaves ရ alone (ရ္ရ keeps the plain letter), so
    # the trigger lists stay per-base, measured rather than assumed.
    stack_trigs = tuple(f"{n}-myanmar.sub" for _, n in CONSONANTS)
    # ra gets a lookup of its own: its filtering set holds ONLY u/uu, so
    # the swap looks straight through an intervening ha — Padauk's ရှု is
    # ra.alt + its ha+u ligature. In the shared lookup ha must stay
    # visible (နှ swaps ON the ha itself), which would block ရှု.
    side_specs = (
        ("na-myanmar", ("u-myanmar", "uu-myanmar", "medialWa-myanmar",
                        "medialHa-myanmar", "medialYa-myanmar",
                        "medialYa-myanmar.beforewa") + stack_trigs, "na"),
        ("nnya-myanmar", ("u-myanmar", "uu-myanmar", "medialWa-myanmar",
                          "medialHa-myanmar") + stack_trigs, "na"),
        ("ra-myanmar", ("u-myanmar", "uu-myanmar"), "ra"),
    )
    side_rules = []
    side_filter = set()
    ra_side_rules = []
    ra_side_filter = set()
    for side_base, trigger_names, group in side_specs:
        alt = f"{side_base}.alt"
        trigs = [t for t in trigger_names if t in drawn]
        if alt in drawn and side_base in drawn and trigs:
            rule = f"    sub {side_base}' [{' '.join(trigs)}] by {alt};"
            if group == "ra":
                ra_side_rules.append(rule)
                ra_side_filter.update(trigs)
            else:
                side_rules.append(rule)
                side_filter.update(t for t in trigs
                                   if not t.startswith("medialYa"))
    # After the post-base medials ja and wa, ု/ူ take their TALL spacing
    # forms — Padauk renders ကျု မွု လျှု မွှူ with the full-height
    # straight stroke (its default spacing uni102F/uni1030, ink −429…423)
    # standing after the medial, never the curl beside it. ha is NOT in
    # the filtering set, so the ja/wa context fires straight through an
    # intervening ha (Padauk's လျှု is uni103B103E + the tall stroke).
    # ရှု still keeps the short curl: there the ha follows a BASE, and
    # bases are always visible to the context, so [ja|wa] cannot match.
    medial_ctx = [n for n in ("medialYa-myanmar", "medialYa-myanmar.beforewa",
                              "medialYa-myanmar.wa", "medialYa-myanmar.ha",
                              "medialWa-myanmar") if n in drawn]
    medial_rules = []
    medial_filter = {"medialWa-myanmar"} & set(drawn)
    for base_v, alt_v in (("u-myanmar", "u-myanmar.alt"),
                          ("uu-myanmar", "uu-myanmar.alt")):
        if base_v in drawn and alt_v in drawn and medial_ctx:
            medial_rules.append(
                f"    sub [{' '.join(medial_ctx)}] {base_v}' by {alt_v};")
            medial_filter.add(base_v)
    if blws_rules or side_rules or ra_side_rules or medial_rules:
        lines.append("feature blws {")
        if blws_rules:
            lines.append("  lookup desc_vowels {")
            lines.append("    lookupflag UseMarkFilteringSet "
                         f"[{' '.join(filter_marks)}];")
            lines.extend("  " + r for r in blws_rules)
            lines.append("  } desc_vowels;")
        if medial_rules:
            lines.append("  lookup medial_vowels {")
            lines.append("    lookupflag UseMarkFilteringSet "
                         f"[{' '.join(sorted(medial_filter))}];")
            lines.extend(medial_rules)
            lines.append("  } medial_vowels;")
        if side_rules:
            lines.append("  lookup side_bases {")
            lines.append("    lookupflag UseMarkFilteringSet "
                         f"[{' '.join(sorted(side_filter))}];")
            lines.extend(side_rules)
            lines.append("  } side_bases;")
        if ra_side_rules:
            lines.append("  lookup side_bases_ra {")
            lines.append("    lookupflag UseMarkFilteringSet "
                         f"[{' '.join(sorted(ra_side_filter))}];")
            lines.extend(ra_side_rules)
            lines.append("  } side_bases_ra;")
        lines.append("} blws;")
        lines.append("")

    # abvs: i + anusvara fuse into the drawn ligature (ကိံ → uni102D1036),
    # the dot tucked beside the ring instead of stacked tall above it —
    # and the kinzi slides left when a medial ya follows (အင်္ကျီ), since
    # the vowel then belongs to the ya and would overlap the kinzi's spot.
    abvs_rules = []
    if {"iAnusvara-myanmar", "i-myanmar", "anusvara-myanmar"} <= drawn:
        abvs_rules.append(
            "  sub i-myanmar anusvara-myanmar by iAnusvara-myanmar;")
    kinzi_ya = [n for n in ("medialYa-myanmar", "medialYa-myanmar.beforewa",
                            "medialYa-myanmar.wa", "medialYa-myanmar.ha")
                if n in drawn]
    if "kinzi-myanmar.left" in drawn and kinzi_ya:
        abvs_rules.append(
            f"  sub kinzi-myanmar' [{' '.join(kinzi_ya)}] "
            "by kinzi-myanmar.left;")
    if abvs_rules:
        lines.append("feature abvs {")
        lines.extend(abvs_rules)
        lines.append("} abvs;")
        lines.append("")

    # psts: what happens to a below-mark after the medial-ra wrap. The
    # medials wa/ha shrink to .small variants that fit INSIDE the wrap
    # (its under-stroke passes beneath the base — full-size ink would
    # cross it); two passes so a mark chained onto an already-small one
    # still shrinks (ကြွှ). The VOWELS take Padauk's fused-ligature
    # geometry instead: ု becomes the straight stroke hanging from the
    # wrap's under-sweep (uni103C102F: တစ်ချောင်းငင် drawn as a bar, not
    # the curl), and ူ becomes the tall spacing form standing AFTER the
    # cluster (Padauk တြူ). The filtering set makes intervening other
    # marks (ကြို's i) invisible to the context while keeping the
    # below-marks themselves visible.
    smalls = [(n, f"{n}.small")
              for n in ("medialWa-myanmar", "medialHa-myanmar")
              if f"{n}.small" in drawn and n in drawn]
    ra_cls = [n for n in ("medialRa-myanmar", "medialRa-myanmar.wide",
                          "medialRa-myanmar.tall",
                          "medialRa-myanmar.tall.wide")
              if n in drawn]
    # fused wrap+u pairs: (plain wrap, its traced fused form)
    fused_pairs = [(w, f"medialRa-myanmar.u{sfx}") for w, sfx in
                   (("medialRa-myanmar", ""),
                    ("medialRa-myanmar.wide", ".wide"),
                    ("medialRa-myanmar.tall", ".tall"),
                    ("medialRa-myanmar.tall.wide", ".tall.wide"))
                   if w in drawn and f"medialRa-myanmar.u{sfx}" in drawn]
    wrap_fused = (fused_pairs and "u-myanmar.ghost" in drawn
                  and "u-myanmar" in drawn)
    wrap_u = (not wrap_fused and "u-myanmar.wrapstroke" in drawn
              and "u-myanmar" in drawn)
    wrap_uu = ("uu-myanmar.alt" in drawn and "uu-myanmar" in drawn)
    if (smalls or wrap_fused or wrap_u or wrap_uu) and ra_cls and base_cls:
        lines.append(f"@RA_WRAPS = [{' '.join(ra_cls)}];")
        lines.append(f"@RA_BASES = [{' '.join(base_cls)}];")
        lines.append("feature psts {")
        filter_set = [n for n, _ in smalls] + [v for _, v in smalls]
        if wrap_u or wrap_fused:
            filter_set.append("u-myanmar")
        if wrap_uu:
            filter_set.append("uu-myanmar")
        lines.append(
            f"  lookupflag UseMarkFilteringSet [{' '.join(filter_set)}];")
        for n, v in smalls:
            lines.append(f"  sub @RA_WRAPS @RA_BASES {n}' by {v};")
        if smalls:
            lines.append(
                f"@BELOW_SMALLS = [{' '.join(v for _, v in smalls)}];")
            for n, v in smalls:
                lines.append(
                    f"  sub @RA_WRAPS @RA_BASES @BELOW_SMALLS {n}' by {v};")
        if wrap_fused:
            # feaLib allows one marked run per rule, so the fusion is two
            # steps: the wrap swaps to its fused form in front of the ု,
            # then the ု behind an already-fused wrap becomes the ghost
            lines.append(
                f"@RA_WRAPS_U = [{' '.join(f for _, f in fused_pairs)}];")
            for w, fused in fused_pairs:
                lines.append(f"  sub {w}' @RA_BASES u-myanmar by {fused};")
            lines.append("  sub @RA_WRAPS_U @RA_BASES u-myanmar' "
                         "by u-myanmar.ghost;")
        if wrap_u:
            lines.append("  sub @RA_WRAPS @RA_BASES u-myanmar' "
                         "by u-myanmar.wrapstroke;")
        if wrap_uu:
            lines.append("  sub @RA_WRAPS @RA_BASES uu-myanmar' "
                         "by uu-myanmar.alt;")
        lines.append("} psts;")
        lines.append("")

    # mark/mkmk GPOS is generated automatically by ufo2ft's MarkFeatureWriter
    # from the top/bottom/side anchors placed on each glyph.
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
