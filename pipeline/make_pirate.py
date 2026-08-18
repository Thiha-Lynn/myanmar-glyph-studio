"""Weather a Glyph Studio project into a carved-bone adventure face.

    python3 make_pirate.py Source.glyphstudio.json Out.glyphstudio.json
    python3 make_pirate.py Source.json Out.json --width 1.04 --y 0.92

Takes a stroke-skeleton project (typically one written by make_sample.py)
and converts every glyph to weathered FILLED CONTOURS:

  * strokes are expanded through the project's own nib (the same
    json_to_ufo geometry the build would run) and unioned into one
    silhouette per glyph;
  * every open stroke end grows a bone knuckle — the double condyle
    bump that turns a plain terminal into crossed-bones lettering;
  * the silhouette is weathered: two superimposed waves and a fine
    jitter roughen each edge like driftwood, and occasional chips are
    gouged out of the ink like sword nicks;
  * two ornaments are drawn from scratch and weathered with the same
    machinery: U+2620 SKULL AND CROSSBONES and U+2693 ANCHOR.

The output is an ordinary version-1 project whose strokes are all
``{"fill": true}`` contours, so the standard pipeline (json_to_ufo →
fontmake) and the studio's own renderer consume it unchanged.  Weight
must therefore be baked into the SOURCE (make_sample --weight): a fill
contour has no pen for a weight axis to scale, which is why faces made
this way set ``meta.variable: false``.

Everything is deterministic: the noise is seeded from the glyph name,
so the same source project always weathers to the identical output.
"""

import argparse
import json
import math
import random
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import json_to_ufo as j2u  # noqa: E402  (the shared stroke/nib geometry)

try:
    import pathops
except ImportError:  # pragma: no cover
    sys.exit("skia-pathops is required:  pip install -r requirements.txt")


# ---------------------------------------------------------------------------
# Weathering parameters (font units).  RDP in json_to_ufo flattens features
# smaller than ~3 units on a letter-sized contour, so everything visible
# here has to clear that: the waves and chips do, the jitter is deliberately
# at the threshold so it reads as grain, not fur.
# ---------------------------------------------------------------------------

RESAMPLE_STEP = 15        # arc-length between vertices before displacing
WAVE1_AMP, WAVE1_LEN = 6.0, 150.0   # the sea swell
WAVE2_AMP, WAVE2_LEN = 3.0, 57.0    # the ripple on top of it
JITTER_AMP = 2.4          # per-vertex grain
CHIP_EVERY = 330          # expected perimeter units per chip
CHIP_DEPTH = (10.0, 16.0)  # gouge depth range
CHIP_MAX = 5              # per contour
MIN_PERIM_FOR_CHIPS = 260  # small marks stay unchipped
AMP_REF_PERIM = 1200.0    # full amplitude at this perimeter…
AMP_MIN_SCALE = 0.35      # …scaled down to this floor for tiny marks

BONE_KNOB = 0.95          # knuckle radius as a fraction of the half-width
BONE_SPREAD = 0.80        # knuckle centre offset from the stroke axis
BONE_FORWARD = 0.35       # knuckle centre push past the stroke end
BONE_MIN_HALF = 14.0      # thinner ends than this stay plain
BONE_FOOT_Y = 120         # below here a terminal is a foot: full knuckle
KNUCKLE_TOP_CEILING = 640  # above here no knuckles at all — a knob on a
                           # letter's crown lifts the ink-following mark
                           # anchors and every mark above it (asat rose to
                           # y=913 from a knob on ပ's stem)
TOP_DAMP_START, TOP_DAMP_END = 720.0, 820.0   # wave fade on tall crowns
TOP_DAMP_FLOOR = 0.3

ORNAMENT_ADVANCE = 1000

# Marks are engineered to 50-unit clearances and ride anchor chains, so
# they weather gently and grow no knuckles: a bone end on a 60-unit mark
# reads as noise, and the first full build proved the geometry cost —
# knuckled asat/kinzi rose to y=935–962 against the 900 design ascender
# (289 bounds warnings), and a fattened subjoined ဘ met the below-dot in
# ကမ္ဘာ့တန်ဆာ (the same squeeze that once failed Sagaing Square).
MARK_AMP = 0.45


def _mark_names():
    names = (set(j2u.TOP_MARKS) | set(j2u.BOTTOM_MARKS)
             | set(j2u.STACK_MARKS) | set(j2u.SPACING_VOWELS))
    return names


def _is_quiet(name):
    """Glyphs that weather gently and grow no knuckles."""
    return (name in _mark_names() or name.endswith(".sub")
            or name == "uni25CC")


def _seed(*parts):
    return zlib.crc32(":".join(str(p) for p in parts).encode("utf-8"))


# ---------------------------------------------------------------------------
# pathops plumbing
# ---------------------------------------------------------------------------

def _signed_area(poly):
    total = 0.0
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        total += p[0] * q[1] - q[0] * p[1]
    return total / 2.0


def _ccw(poly):
    return poly if _signed_area(poly) >= 0 else poly[::-1]


def _polys_to_path(polys, normalize=False):
    """normalize=True rewinds every polygon counter-clockwise.  Primitive
    shapes (stroke expansions, knuckles, ornament parts) arrive with
    arbitrary winding, and two opposite windings CANCEL under the nonzero
    rule — the first build had white holes in every knuckle.  Contours
    that came out of a previous union already carry meaningful hole
    windings and must NOT be rewound."""
    path = pathops.Path()
    pen = path.getPen()
    for poly in polys:
        if len(poly) < 3:
            continue
        if normalize:
            poly = _ccw(poly)
        pen.moveTo((poly[0][0], poly[0][1]))
        for p in poly[1:]:
            pen.lineTo((p[0], p[1]))
        pen.closePath()
    return path

def _path_to_polys(path):
    polys, cur = [], None
    for verb, pts in path.segments:
        if verb == "moveTo":
            cur = [[pts[0][0], pts[0][1]]]
        elif verb == "lineTo":
            cur.append([pts[0][0], pts[0][1]])
        elif verb in ("qCurveTo", "curveTo"):
            # line-only input keeps skia in line-only output; tolerate a
            # stray curve by keeping its end point rather than dying
            for p in pts:
                if p is not None:
                    cur.append([p[0], p[1]])
        elif verb == "closePath" and cur:
            if len(cur) > 1 and cur[0] == cur[-1]:
                cur.pop()
            if len(cur) >= 3:
                polys.append(cur)
            cur = None
    return polys


def _union(polys):
    """Union of primitive polygons (rewound CCW first)."""
    path = _polys_to_path(polys, normalize=True)
    return _path_to_polys(pathops.simplify(path, fix_winding=True))


def _reunion(polys):
    """Re-simplify contours that already carry correct hole windings."""
    path = _polys_to_path(polys)
    return _path_to_polys(pathops.simplify(path, fix_winding=True))


def _difference(add_polys, cut_polys):
    if not cut_polys:
        return _union(add_polys)
    out = pathops.op(_polys_to_path(add_polys, normalize=True),
                     _polys_to_path(cut_polys, normalize=True),
                     pathops.PathOp.DIFFERENCE, fix_winding=True)
    return _path_to_polys(out)


# ---------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------

def _perimeter(poly):
    total = 0.0
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        total += math.hypot(q[0] - p[0], q[1] - p[1])
    return total


def _resample(poly, step):
    """Evenly spaced vertices along the closed polygon."""
    per = _perimeter(poly)
    n = max(8, int(round(per / step)))
    spacing = per / n
    out, acc = [], 0.0
    target = 0.0
    i = 0
    p = poly[0]
    out.append([p[0], p[1]])
    target += spacing
    while len(out) < n:
        q = poly[(i + 1) % len(poly)]
        seg = math.hypot(q[0] - p[0], q[1] - p[1])
        if acc + seg < target:
            acc += seg
            i += 1
            p = q
            continue
        t = (target - acc) / seg if seg else 0.0
        p = [p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]
        out.append([p[0], p[1]])
        acc = target
        target += spacing
    return out


def _normals(poly):
    """Unit normals from central differences (sign is arbitrary but
    consistent along the contour)."""
    n = len(poly)
    out = []
    for i in range(n):
        a, b = poly[i - 1], poly[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy) or 1.0
        out.append((-dy / length, dx / length))
    return out


def _winding(pt, poly):
    x, y = pt
    wn = 0
    for i in range(len(poly)):
        x0, y0 = poly[i][0], poly[i][1]
        x1, y1 = poly[(i + 1) % len(poly)][0], poly[(i + 1) % len(poly)][1]
        if y0 <= y:
            if y1 > y and (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0) > 0:
                wn += 1
        elif y1 <= y and (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0) < 0:
            wn -= 1
    return wn


def _in_ink(pt, contours):
    return sum(_winding(pt, c) for c in contours) != 0


# ---------------------------------------------------------------------------
# bone knuckles
# ---------------------------------------------------------------------------

def _circle_poly(cx, cy, r, segs=20):
    return [[cx + r * math.cos(2 * math.pi * i / segs),
             cy + r * math.sin(2 * math.pi * i / segs)] for i in range(segs)]


def _stroke_open_ends(stroke, width_scale=1.0):
    """(point, outward unit direction, half width) for each open end."""
    if stroke.get("fill"):
        return []
    pts = stroke.get("points") or []
    if len(pts) < 2:
        return []
    w = stroke.get("width", 40) * width_scale
    gap = math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1])
    if gap < w * 1.15:          # a loop: the seam is not a terminal
        return []
    ends = []
    for idx, direction in ((0, -1), (len(pts) - 1, 1)):
        p = pts[idx]
        half = j2u._pt_width(p, stroke.get("width", 40)) * width_scale / 2.0
        # walk inward until we are far enough away for a stable direction
        j = idx
        while 0 <= j - direction < len(pts):
            j -= direction
            if math.hypot(pts[j][0] - p[0], pts[j][1] - p[1]) >= half * 0.8:
                break
        q = pts[j]
        dx, dy = p[0] - q[0], p[1] - q[1]
        length = math.hypot(dx, dy)
        if not length:
            continue
        ends.append(([p[0], p[1]], (dx / length, dy / length), half))
    return ends


def bone_knuckles(glyph_data, width_scale=1.0, pen=j2u.DEFAULT_PEN):
    """Knob polygons for every open stroke end that is a real terminal.

    Ends that die inside another stroke's ink are junctions, not
    terminals — a knob there would read as a boil, so they stay plain.
    """
    strokes = glyph_data.get("strokes", [])
    knobs = []
    for si, stroke in enumerate(strokes):
        ends = _stroke_open_ends(stroke, width_scale)
        if not ends:
            continue
        others = [j2u.stroke_to_polygon(s, width_scale, pen)
                  for oi, s in enumerate(strokes) if oi != si]
        others = [_ccw(o) for o in others if o]
        for p, d, half in ends:
            if half < BONE_MIN_HALF or p[1] > KNUCKLE_TOP_CEILING:
                continue
            probe = (p[0] + d[0] * half * 0.6, p[1] + d[1] * half * 0.6)
            if others and _in_ink(probe, others):
                continue
            if p[1] <= BONE_FOOT_Y:
                # a foot: the classic condyle, pushed past the end
                r, spread, forward = (half * BONE_KNOB, half * BONE_SPREAD,
                                      half * BONE_FORWARD)
            else:
                # mid-height: tucked knobs that bulge sideways only —
                # axial reach 0.05 + 0.85 stays inside the cap's 1.0, so
                # the terminal never lifts the glyph's ink ceiling
                r, spread, forward = half * 0.85, half * 0.85, half * 0.05
            cx = p[0] + d[0] * forward
            cy = p[1] + d[1] * forward
            px, py = -d[1], d[0]
            knobs.append(_circle_poly(cx + px * spread, cy + py * spread, r))
            knobs.append(_circle_poly(cx - px * spread, cy - py * spread, r))
    return knobs


# ---------------------------------------------------------------------------
# weathering
# ---------------------------------------------------------------------------

def _amp_scale(perimeter):
    return max(AMP_MIN_SCALE, min(1.0, perimeter / AMP_REF_PERIM))


def weather_contour(poly, rng, all_contours, amp=1.0):
    """Waves + grain + chips on one closed contour."""
    per = _perimeter(poly)
    scale = _amp_scale(per) * amp
    pts = _resample(poly, RESAMPLE_STEP)
    normals = _normals(pts)
    n = len(pts)
    per = _perimeter(pts)

    phase1 = rng.uniform(0, 2 * math.pi)
    phase2 = rng.uniform(0, 2 * math.pi)
    # wavelengths snap to a whole number of periods so the seam is smooth
    k1 = max(1, round(per / WAVE1_LEN))
    k2 = max(1, round(per / WAVE2_LEN))

    arc = 0.0
    out = []
    for i, (p, nm) in enumerate(zip(pts, normals)):
        if i:
            q = pts[i - 1]
            arc += math.hypot(p[0] - q[0], p[1] - q[1])
        t = arc / per
        disp = (WAVE1_AMP * scale * math.sin(2 * math.pi * k1 * t + phase1)
                + WAVE2_AMP * scale * math.sin(2 * math.pi * k2 * t + phase2)
                + JITTER_AMP * scale * rng.uniform(-1.0, 1.0))
        if p[1] > TOP_DAMP_START:
            # crowns carry the ink-following mark anchors: waves up there
            # push every mark in the chain over the 900 ascender
            f = (p[1] - TOP_DAMP_START) / (TOP_DAMP_END - TOP_DAMP_START)
            disp *= max(TOP_DAMP_FLOOR, 1.0 - f * (1.0 - TOP_DAMP_FLOOR))
        out.append([p[0] + nm[0] * disp, p[1] + nm[1] * disp])

    if per >= MIN_PERIM_FOR_CHIPS and amp >= 1.0:
        chips = min(CHIP_MAX, int(per / CHIP_EVERY))
        taken = []
        for _ in range(chips):
            i = rng.randrange(n)
            if any(min(abs(i - j), n - abs(i - j)) < 5 for j in taken):
                continue
            nm = normals[i]
            depth = rng.uniform(*CHIP_DEPTH) * max(0.6, scale)
            probe_in = (out[i][0] + nm[0] * 3.0, out[i][1] + nm[1] * 3.0)
            sign = 1.0 if _in_ink(probe_in, all_contours) else -1.0
            # a chip may not bite deeper than the ink behind it
            floor = (out[i][0] + nm[0] * sign * (depth + 8),
                     out[i][1] + nm[1] * sign * (depth + 8))
            if not _in_ink(floor, all_contours):
                continue
            for di, frac in ((-1, 0.35), (0, 1.0), (1, 0.35)):
                v = out[(i + di) % n]
                v[0] += nm[0] * sign * depth * frac
                v[1] += nm[1] * sign * depth * frac
            taken.append(i)
    return out


def weather_glyph(name, polys, salt="", amp=1.0, cap_top=False):
    """Weather a unioned silhouette; deterministic per glyph name.

    cap_top clamps the weathered ink to the silhouette's own nominal
    ceiling: marks like kinzi sit designed-flush against the 900
    ascender, and even a 2-unit outward ripple there is a warning."""
    ceiling = (max(p[1] for poly in polys for p in poly) - 0.5
               if cap_top and polys else None)
    out = []
    for ci, poly in enumerate(polys):
        rng = random.Random(_seed(salt, name, ci))
        weathered = weather_contour(poly, rng, polys, amp)
        if ceiling is not None:
            for v in weathered:
                if v[1] > ceiling:
                    v[1] = ceiling
        out.append(weathered)
    return _reunion(out)


# ---------------------------------------------------------------------------
# the two ornaments
# ---------------------------------------------------------------------------

def _capsule(p0, p1, r, segs=10):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    a0 = math.atan2(uy, ux) + math.pi / 2
    pts = []
    for i in range(segs + 1):
        a = a0 + math.pi * i / segs
        pts.append([x1 + r * math.cos(a), y1 + r * math.sin(a)])
    for i in range(segs + 1):
        a = a0 + math.pi + math.pi * i / segs
        pts.append([x0 + r * math.cos(a), y0 + r * math.sin(a)])
    return pts


def _bone(p0, p1, r, knob):
    """A capsule with the classic double knuckle at both ends."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    polys = [_capsule(p0, p1, r)]
    for (ex, ey), sign in ((p0, -1), (p1, 1)):
        cx = ex + ux * sign * r * 0.35
        cy = ey + uy * sign * r * 0.35
        for s in (1, -1):
            polys.append(_circle_poly(cx + px * s * r * 0.85,
                                      cy + py * s * r * 0.85, knob))
    return polys


def _ellipse_poly(cx, cy, rx, ry, segs=28):
    return [[cx + rx * math.cos(2 * math.pi * i / segs),
             cy + ry * math.sin(2 * math.pi * i / segs)] for i in range(segs)]


def _rect_poly(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def skull_glyph():
    """U+2620 SKULL AND CROSSBONES, drawn from primitives."""
    add = []
    # crossed bones first, so the skull face sits on top of them
    add += _bone((205, -60), (775, 300), 30, 40)
    add += _bone((205, 300), (775, -60), 30, 40)
    # cranium and jaw
    add.append(_ellipse_poly(490, 470, 238, 252))
    add.append(_ellipse_poly(490, 250, 150, 120))
    cut = [
        _ellipse_poly(398, 468, 64, 76),     # eye sockets
        _ellipse_poly(582, 468, 64, 76),
        [[490, 392], [443, 300], [537, 300]],  # nasal cavity
        _rect_poly(437, 138, 452, 232),      # teeth slots
        _rect_poly(482, 130, 497, 232),
        _rect_poly(527, 138, 542, 232),
    ]
    return _difference(add, cut)


def anchor_glyph():
    """U+2693 ANCHOR, drawn from primitives."""
    add = []
    # ring
    ring_outer = _ellipse_poly(490, 705, 88, 88)
    add.append(ring_outer)
    # shank, stock, crown arc
    add.append(_capsule((490, 630), (490, 60), 33))
    add.append(_capsule((305, 505), (675, 505), 28))
    cx, cy, R, half = 490, 330, 272, 33
    outer, inner = [], []
    for i in range(25):
        a = math.radians(197 + (343 - 197) * i / 24)
        outer.append([cx + (R + half) * math.cos(a),
                      cy + (R + half) * math.sin(a)])
        inner.append([cx + (R - half) * math.cos(a),
                      cy + (R - half) * math.sin(a)])
    add.append(outer + inner[::-1])
    # flukes: arrowheads at the arm tips, pointing up and out
    for tip_a, sign in ((197, -1), (343, 1)):
        a = math.radians(tip_a)
        tx, ty = cx + R * math.cos(a), cy + R * math.sin(a)
        # tangent pointing outward along the arm
        tang = (sign * -math.sin(a), sign * math.cos(a))
        px, py = -tang[1], tang[0]
        apex = (tx + tang[0] * 95, ty + tang[1] * 95)
        add.append([[apex[0], apex[1]],
                    [tx + px * 62, ty + py * 62],
                    [tx - px * 62, ty - py * 62]])
    cut = [_ellipse_poly(490, 705, 52, 52)]
    return _difference(add, cut)


# ---------------------------------------------------------------------------
# project transform
# ---------------------------------------------------------------------------

def affine_record(record, w, y):
    """Scale a skeleton record in place: points, bez, advance — together."""
    if w == 1.0 and y == 1.0:
        return record
    for stroke in record.get("strokes", []):
        for p in stroke.get("points", []):
            p[0] *= w
            p[1] *= y
        for b in stroke.get("bez", []):
            for i in range(0, 6, 2):
                b[i] *= w
                b[i + 1] *= y
    if "advance" in record:
        record["advance"] = record["advance"] * w
    for anchor in (record.get("anchors") or {}).values():
        anchor[0] *= w
        anchor[1] *= y
    return record


def _round_polys(polys):
    out = []
    for poly in polys:
        rounded = []
        for p in poly:
            q = [round(p[0]), round(p[1])]
            if not rounded or q != rounded[-1]:
                rounded.append(q)
        if len(rounded) > 1 and rounded[0] == rounded[-1]:
            rounded.pop()
        if len(rounded) >= 3:
            out.append(rounded)
    return out


def pirate_record(name, record, pen, salt=""):
    """One glyph: expand, knuckle, union, weather → fill contours."""
    polys = j2u.polygons_for(record, 1.0, pen)
    if not polys:
        return {"advance": record.get("advance", 500), "strokes": []}
    quiet = _is_quiet(name)
    knuckles = [] if quiet else bone_knuckles(record, 1.0, pen)
    silhouette = _union(polys + knuckles)
    weathered = _round_polys(
        weather_glyph(name, silhouette, salt, MARK_AMP if quiet else 1.0,
                      cap_top=quiet))
    return {
        "advance": record.get("advance", 500),
        "strokes": [{"fill": True, "points": poly} for poly in weathered],
    }


def build(project, width=1.0, y=1.0, salt=""):
    pen = j2u.pen_exponent(project)
    glyphs = project.get("glyphs", {})
    out_glyphs = {}
    for name, record in glyphs.items():
        record = affine_record(json.loads(json.dumps(record)), width, y)
        out_glyphs[name] = pirate_record(name, record, pen, salt)

    for name, polys in (("uni2620", skull_glyph()),
                        ("uni2693", anchor_glyph())):
        if name in out_glyphs:
            continue
        weathered = _round_polys(weather_glyph(name, polys, salt))
        out_glyphs[name] = {
            "advance": ORNAMENT_ADVANCE,
            "strokes": [{"fill": True, "points": p} for p in weathered],
        }

    meta = dict(project.get("meta") or {})
    meta["variable"] = False       # fill contours carry no pen to scale
    meta["notes"] = ("Weathered fill-contour face generated by "
                     "make_pirate.py: bone-knuckle terminals, wave-roughened "
                     "edges, chip gouges; ornaments U+2620 and U+2693.")
    return {
        "format": project.get("format", "mm-glyph-studio"),
        "version": 1,
        "meta": meta,
        "glyphs": out_glyphs,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Weather a skeleton project into a carved-bone face.")
    ap.add_argument("source", type=Path,
                    help="source *.glyphstudio.json (stroke skeletons)")
    ap.add_argument("output", type=Path,
                    help="path to write the weathered project")
    ap.add_argument("--width", type=float, default=1.0,
                    help="widen the skeletons first (affine, default 1.0)")
    ap.add_argument("--y", type=float, default=1.0,
                    help="vertical scale applied first (default 1.0)")
    ap.add_argument("--font-name", default=None,
                    help="override meta.fontName in the output")
    ap.add_argument("--salt", default="",
                    help="vary the weathering (same salt = same output)")
    args = ap.parse_args(argv)

    project = json.loads(args.source.read_text(encoding="utf-8"))
    out = build(project, args.width, args.y, args.salt)
    if args.font_name:
        out["meta"]["fontName"] = args.font_name
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                           encoding="utf-8")
    total = sum(len(g["strokes"]) for g in out["glyphs"].values())
    print(f"{args.output}: {len(out['glyphs'])} glyphs, "
          f"{total} weathered contours")


if __name__ == "__main__":
    main()
