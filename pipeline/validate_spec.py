#!/usr/bin/env python3
"""Validate a built Myanmar font against the shaping specification corpus.

This is the machine-checkable half of the Myanmar shaping specification
(docs/SHAPING_SPEC.md): every string in `spec_corpus.txt` — Blocks A–O,
~1500 clusters — is shaped with HarfBuzz and then *measured*, so a claim
like "all stacks render" is backed by coordinates instead of a glance at
a proof sheet.

    python3 validate_spec.py ../projects/myanmar-glyph-sans/MyanmarGlyphSans-Regular.ttf
    python3 validate_spec.py MyFont.ttf --reference ../web/fonts/Padauk-Regular.ttf
    python3 validate_spec.py MyFont.ttf --md ../docs/VALIDATION.md --json report.json
    python3 validate_spec.py MyFont.ttf --block D,J --verbose

What each case is checked for
-----------------------------
  coverage      every input character maps to a real glyph (no .notdef)
  dotted-circle HarfBuzz did not have to insert U+25CC to repair the input
  virama        U+1039 was consumed by blwf (no naked virama in the output)
  kinzi         င + ် + ္ became the kinzi mark, no full-size နga survives
  reorder       U+1031 ေ and the medial-ra wrap render BEFORE their base
  wrap          the base of a medial-ra cluster sits inside the wrap's ink
  attachment    every mark was moved by GPOS and lands over/under its base
  bounds        no positioned ink escapes the descender/ascender band
  collision     no two marks in a cluster overlap; clearance ≥ 50 units
  advance       the cluster advances (nothing collapses to zero width)

Severities
----------
  FAIL  the font is wrong — a shaping rule or an anchor needs fixing
  WARN  inside tolerance but worth a look (tight clearance, unusual depth)
  GAP   the glyph simply is not drawn yet (coverage, not a rule failure)
  SPEC  the *test datum* is malformed — the font behaved correctly
        (e.g. a vowel stored in visual order, or a non-Myanmar script);
        these are reported separately so they can never mask a real bug

Dependencies: fontTools, uharfbuzz  (pip install -r requirements.txt)
"""

import argparse
import json
import math
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

try:
    import uharfbuzz as hb
    from fontTools.pens.basePen import BasePen
    from fontTools.ttLib import TTFont
except ImportError as exc:                                  # pragma: no cover
    sys.exit(f"Missing dependency ({exc}).  pip install fonttools uharfbuzz")

# --- engine parameters (docs/SHAPING_SPEC.md §1) ---------------------------
UPM = 1000
ASCENDER = 900
# The medial-ra wrap is the script's one legitimate ascender-breaker: its
# hook must rise around the vowel ring it wraps. Padauk's wraps top out at
# 932–933 (normalized); 935 is the measured band for the wrap class only.
WRAP_ASCENDER = 935
DESCENDER = -600
MIN_MARK_CLEARANCE = 50      # spec: minimum 50-unit separation between marks
CURVE_SEGMENTS = 8           # flattening resolution for the collision test
MAX_POLY_POINTS = 96         # decimation cap per contour (collision test)
MARK_STRAY_TOLERANCE = 220   # how far a mark may sit outside the base ink

DOTTED_CIRCLE = 0x25CC
VIRAMA = 0x1039
ASAT = 0x103A
NGA = 0x1004
E_VOWEL = 0x1031
MEDIAL_RA = 0x103C
TALL_AA = 0x102B
AA = 0x102C

# Myanmar and its extension blocks; anything else in the corpus is a
# different script and cannot be the font's responsibility.
MYANMAR_RANGES = ((0x1000, 0x109F), (0xA9E0, 0xA9FF), (0xAA60, 0xAA7F),
                  (0x116D0, 0x116FF))

LANGUAGE_TAGS = {                     # Block K rows carry the language name
    "mon": "mnw", "shan": "shn", "s'gaw karen": "ksw", "sgaw karen": "ksw",
    "burmese": "my",
}


def is_myanmar(cp):
    return any(lo <= cp <= hi for lo, hi in MYANMAR_RANGES)


def uplus(text):
    return " ".join(f"U+{ord(c):04X}" for c in text)


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

SEVERITIES = ("FAIL", "WARN", "GAP", "SPEC")


class Finding:
    __slots__ = ("severity", "code", "message", "case")

    def __init__(self, severity, code, message):
        self.severity = severity
        self.code = code
        self.message = message
        self.case = None

    def __repr__(self):
        return f"<{self.severity} {self.code}: {self.message}>"

    def as_dict(self):
        return {"severity": self.severity, "code": self.code,
                "message": self.message,
                "block": self.case.block if self.case else None,
                "text": self.case.text if self.case else None}


# ---------------------------------------------------------------------------
# Outline access: flatten once, cache, reuse for bounds and collisions
# ---------------------------------------------------------------------------

class _FlattenPen(BasePen):
    """Glyph outline as closed polygons; curves become line segments."""

    def __init__(self, glyph_set):
        super().__init__(glyph_set)
        self.contours = []
        self._points = None

    def _moveTo(self, pt):
        self._points = [pt]

    def _lineTo(self, pt):
        self._points.append(pt)

    def _qCurveToOne(self, c, pt):
        x0, y0 = self._getCurrentPoint()
        for i in range(1, CURVE_SEGMENTS + 1):
            t = i / CURVE_SEGMENTS
            u = 1 - t
            self._points.append((u * u * x0 + 2 * u * t * c[0] + t * t * pt[0],
                                 u * u * y0 + 2 * u * t * c[1] + t * t * pt[1]))

    def _curveToOne(self, c1, c2, pt):
        x0, y0 = self._getCurrentPoint()
        for i in range(1, CURVE_SEGMENTS + 1):
            t = i / CURVE_SEGMENTS
            u = 1 - t
            self._points.append((
                u ** 3 * x0 + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0]
                + t ** 3 * pt[0],
                u ** 3 * y0 + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1]
                + t ** 3 * pt[1]))

    def _closePath(self):
        if self._points and len(self._points) > 2:
            self.contours.append(self._points)
        self._points = None

    def _endPath(self):
        self._closePath()


def _decimate(points, cap=MAX_POLY_POINTS):
    if len(points) <= cap:
        return points
    step = len(points) / cap
    return [points[int(i * step)] for i in range(cap)]


# ---------------------------------------------------------------------------
# The font under test
# ---------------------------------------------------------------------------

class ShapedGlyph:
    __slots__ = ("name", "gid", "cluster", "x", "y", "advance", "codepoint")

    def __init__(self, name, gid, cluster, x, y, advance):
        self.name, self.gid, self.cluster = name, gid, cluster
        self.x, self.y, self.advance = x, y, advance

    def __repr__(self):
        return f"{self.name}@{self.x},{self.y}"


class FontUnderTest:
    """One font file, three views: HarfBuzz shapes it, fontTools reads its
    outlines and GDEF classes, and the cmap answers coverage questions."""

    def __init__(self, path):
        self.path = Path(path)
        data = self.path.read_bytes()
        self.hb_font = hb.Font(hb.Face(hb.Blob(data)))
        self.tt = TTFont(str(self.path), fontNumber=0, lazy=True)
        # Everything below works in 1000 units/em, whatever the font uses,
        # so one set of thresholds compares this font with the reference.
        self.hb_font.scale = (UPM, UPM)
        self.upm = self.tt["head"].unitsPerEm
        os2 = self.tt["OS/2"]
        # normalised to 1000 upm so the thresholds read the same in any font
        self.win_ascent = round(os2.usWinAscent * 1000 / self.upm)
        self.win_descent = round(os2.usWinDescent * 1000 / self.upm)
        self.glyph_order = self.tt.getGlyphOrder()
        self._glyph_names = set(self.glyph_order)
        self.cmap = self.tt.getBestCmap()
        self.glyph_set = self.tt.getGlyphSet()
        gdef = self.tt.get("GDEF")
        self.gdef_classes = {}
        if gdef is not None and getattr(gdef.table, "GlyphClassDef", None):
            self.gdef_classes = dict(gdef.table.GlyphClassDef.classDefs)
        self._outline_cache = {}
        self._bbox_cache = {}
        self.family = self._name(1)
        self.style = self._name(2)
        self.scripts = self._script_tags()

    def _name(self, nid):
        rec = self.tt["name"].getDebugName(nid)
        return rec or self.path.stem

    def _script_tags(self):
        tags = {}
        for tbl in ("GSUB", "GPOS"):
            t = self.tt.get(tbl)
            if t is None:
                continue
            tags[tbl] = sorted(
                {(r.ScriptTag, tuple(sorted(l.LangSysTag for l in r.Script.LangSysRecord)))
                 for r in t.table.ScriptList.ScriptRecord})
        return tags

    # -- outlines ----------------------------------------------------------
    def outline(self, name):
        polys = self._outline_cache.get(name)
        if polys is None:
            pen = _FlattenPen(self.glyph_set)
            try:
                self.glyph_set[name].draw(pen)
            except Exception:                                # pragma: no cover
                pen.contours = []
            s = UPM / self.upm
            polys = [_decimate([(x * s, y * s) for x, y in c])
                     for c in pen.contours]
            self._outline_cache[name] = polys
        return polys

    def bbox(self, name):
        """Ink bounds (x_min, y_min, x_max, y_max) or None when blank."""
        if name in self._bbox_cache:
            return self._bbox_cache[name]
        box = None
        for contour in self.outline(name):
            for x, y in contour:
                box = (x, y, x, y) if box is None else (
                    min(box[0], x), min(box[1], y),
                    max(box[2], x), max(box[3], y))
        self._bbox_cache[name] = box
        return box

    def is_mark(self, name):
        return self.gdef_classes.get(name) == 3

    def covers(self, cp):
        return cp in self.cmap

    def gid_of(self, cp):
        """Glyph id the cmap maps this codepoint to, or None."""
        name = self.cmap.get(cp)
        if name is None:
            return None
        try:
            return self.glyph_order.index(name)
        except ValueError:
            return None

    def has_subjoined(self, cp):
        """Is a `.sub` form drawn for the consonant at this codepoint?"""
        base = self.cmap.get(cp)
        if not base:
            return False
        stem = base.split(".")[0]
        return any(n in self._glyph_names for n in (f"{stem}.sub", f"{base}.sub"))

    # -- shaping -----------------------------------------------------------
    def shape(self, text, language="my", features=None):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.direction = "ltr"
        buf.script = "Mymr"
        buf.language = language
        hb.shape(self.hb_font, buf, features)
        out, pen_x, pen_y = [], 0, 0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            name = (self.glyph_order[info.codepoint]
                    if info.codepoint < len(self.glyph_order) else
                    f"gid{info.codepoint}")
            g = ShapedGlyph(name, info.codepoint, info.cluster,
                            pen_x + pos.x_offset, pen_y + pos.y_offset,
                            pos.x_advance)
            out.append(g)
            pen_x += pos.x_advance
            pen_y += pos.y_advance
        return out, pen_x


# ---------------------------------------------------------------------------
# Geometry helpers for the collision protocol
# ---------------------------------------------------------------------------

def _seg_dist(p, q, r, s):
    """Shortest distance between segments pq and rs (0 when they cross)."""
    def dot(a, b):
        return a[0] * b[0] + a[1] * b[1]

    def sub(a, b):
        return (a[0] - b[0], a[1] - b[1])

    def point_seg(pt, a, b):
        ab = sub(b, a)
        denom = dot(ab, ab)
        if denom == 0:
            return math.dist(pt, a)
        t = max(0.0, min(1.0, dot(sub(pt, a), ab) / denom))
        return math.dist(pt, (a[0] + ab[0] * t, a[1] + ab[1] * t))

    d1 = (q[0] - p[0], q[1] - p[1])
    d2 = (s[0] - r[0], s[1] - r[1])
    denom = d1[0] * d2[1] - d1[1] * d2[0]
    if denom:
        t = ((r[0] - p[0]) * d2[1] - (r[1] - p[1]) * d2[0]) / denom
        u = ((r[0] - p[0]) * d1[1] - (r[1] - p[1]) * d1[0]) / denom
        if 0 <= t <= 1 and 0 <= u <= 1:
            return 0.0
    return min(point_seg(p, r, s), point_seg(q, r, s),
               point_seg(r, p, q), point_seg(s, p, q))


def _point_in_poly(pt, poly):
    x, y, inside = pt[0], pt[1], False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            xin = (x1 - x0) * (y - y0) / (y1 - y0) + x0
            if x < xin:
                inside = not inside
    return inside


def _translated(polys, dx, dy):
    return [[(x + dx, y + dy) for x, y in c] for c in polys]


def ink_clearance(polys_a, polys_b):
    """0.0 when the two ink shapes overlap, otherwise their gap in units.

    Bounding boxes prune the work: only shapes whose boxes come within
    MIN_MARK_CLEARANCE of each other are compared contour by contour.
    """
    def box(polys):
        xs = [x for c in polys for x, _ in c]
        ys = [y for c in polys for _, y in c]
        return min(xs), min(ys), max(xs), max(ys)

    if not polys_a or not polys_b:
        return math.inf
    ax0, ay0, ax1, ay1 = box(polys_a)
    bx0, by0, bx1, by1 = box(polys_b)
    gap_x = max(bx0 - ax1, ax0 - bx1, 0)
    gap_y = max(by0 - ay1, ay0 - by1, 0)
    if gap_x or gap_y:                       # boxes already apart
        box_gap = math.hypot(gap_x, gap_y)
        if box_gap >= MIN_MARK_CLEARANCE:
            return box_gap                   # far enough, no ink test needed
    # boxes touch or nearly touch: measure the real ink
    for ca in polys_a:
        for cb in polys_b:
            if _point_in_poly(ca[0], cb) or _point_in_poly(cb[0], ca):
                return 0.0
    best = math.inf
    for ca in polys_a:
        for i in range(len(ca)):
            p, q = ca[i], ca[(i + 1) % len(ca)]
            for cb in polys_b:
                for j in range(len(cb)):
                    r, s = cb[j], cb[(j + 1) % len(cb)]
                    d = _seg_dist(p, q, r, s)
                    if d == 0.0:
                        return 0.0
                    if d < best:
                        best = d
    return best


# ---------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------

class Case:
    __slots__ = ("block", "label", "text", "language")

    def __init__(self, block, label, text):
        self.block, self.label, self.text = block, label, text
        self.language = LANGUAGE_TAGS.get(label.strip().lower(), "my")

    def __repr__(self):
        return f"[{self.block}] {self.text}"


def load_corpus(path):
    cases, titles = [], {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if line.startswith("#"):
            m = re.match(r"#\s*(?:---\s*)?Block ([A-Z]):\s*(.+)$", line)
            if m:
                titles.setdefault(m.group(1), m.group(2).strip())
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        cases.append(Case(parts[0], parts[1], parts[2]))
    return cases, titles


# ---------------------------------------------------------------------------
# The checks
# ---------------------------------------------------------------------------

def clusters_of(glyphs):
    groups = defaultdict(list)
    for g in glyphs:
        groups[g.cluster].append(g)
    return [groups[k] for k in sorted(groups)]


def check_case(font, case, glyphs, total_advance):
    """Every measurement for one shaped string. Returns [Finding, ...]."""
    findings = []
    text = case.text
    names = [g.name for g in glyphs]

    # -- coverage ---------------------------------------------------------
    missing = [ch for ch in text
               if not ch.isspace() and not font.covers(ord(ch))]
    if missing:
        out_of_script = [c for c in missing if not is_myanmar(ord(c))]
        in_script = [c for c in missing if is_myanmar(ord(c))]
        if in_script:
            findings.append(Finding(
                "GAP", "coverage",
                "not in the font: " + ", ".join(
                    f"{c} ({uplus(c)} {unicodedata.name(c, '?')})"
                    for c in dict.fromkeys(in_script))))
        if out_of_script:
            findings.append(Finding(
                "SPEC", "wrong-script",
                "not Myanmar text: " + ", ".join(
                    f"{c} ({uplus(c)} {unicodedata.name(c, '?')})"
                    for c in dict.fromkeys(out_of_script))))
    if any(g.gid == 0 for g in glyphs) and not missing:
        findings.append(Finding("FAIL", "notdef",
                                ".notdef in the output with every character "
                                "mapped — a substitution produced it"))

    # -- HarfBuzz had to repair the input ---------------------------------
    dotted = [g for g in glyphs if font.cmap.get(DOTTED_CIRCLE) == g.name
              or g.name in ("uni25CC", "dottedCircle")]
    if dotted:
        lead = text.lstrip()[:1]
        findings.append(Finding(
            "SPEC", "dotted-circle",
            f"HarfBuzz inserted U+25CC because {lead} ({uplus(lead)} "
            f"{unicodedata.name(lead, '?')}) opens the cluster — Unicode "
            "stores a dependent sign AFTER its consonant, and the shaper "
            "supplies the missing base"))

    # -- blwf consumed the virama ------------------------------------------
    if any(n in ("virama-myanmar", "uni1039") for n in names):
        for i, ch in enumerate(text):
            if ord(ch) != VIRAMA:
                continue
            after = text[i + 1] if i + 1 < len(text) else ""
            if not after or not font.covers(ord(after)):
                break
            if font.has_subjoined(ord(after)):
                findings.append(Finding(
                    "FAIL", "virama",
                    f"virama survived before {after} — its subjoined form is "
                    "drawn, so the blwf rule is dead"))
            else:
                findings.append(Finding(
                    "GAP", "virama",
                    f"no subjoined form drawn for {after} "
                    f"({uplus(after)}) — the stack cannot be built"))
            break

    # -- kinzi -------------------------------------------------------------
    # Name-free (MyanmarText ships opaque glyphNN names): rphf fired iff
    # the standalone-nga glyph is GONE from the kinzi's own cluster. A bare
    # င in another cluster is just another syllable's letter (သင်္ချိုင်း
    # legitimately ends in င်).
    nga_gid = font.gid_of(NGA)
    if nga_gid is not None:
        for m in re.finditer("င်္", text):
            in_cluster = [g for g in glyphs if g.cluster == m.start()]
            if any(g.gid == nga_gid for g in in_cluster):
                findings.append(Finding(
                    "FAIL", "kinzi",
                    "a full-size င survived where the kinzi belongs "
                    "(rphf did not fire or half-fired)"))
                break

    # Geometry can only be judged when every glyph in the cluster exists:
    # an undrawn base shapes to .notdef and its marks have nothing to
    # attach to, which would cascade into attachment and collision
    # "failures" that say nothing about the rules.
    if not glyphs or any(f.code == "coverage" for f in findings):
        return findings

    # -- geometry ----------------------------------------------------------
    base_boxes, mark_boxes = [], []
    for g in glyphs:
        box = font.bbox(g.name)
        if box is None:
            continue
        placed = (box[0] + g.x, box[1] + g.y, box[2] + g.x, box[3] + g.y)
        (mark_boxes if font.is_mark(g.name) else base_boxes).append((g, placed))

    # Ink must stay in the designed band, and above all inside the font's
    # own clipping box: Windows and most browsers clip at usWinAscent /
    # usWinDescent, so ink outside that is not a tight fit but a bug the
    # reader sees as a chopped-off vowel.
    # (2-unit epsilon: fonts like MyanmarText design their wrap exactly AT
    # the clip line, and upm rescaling adds float noise)
    for g, box in base_boxes + mark_boxes:
        if box[1] < -font.win_descent - 2:
            findings.append(Finding(
                "FAIL", "clipped",
                f"{g.name} sinks to y={box[1]:.0f}, past usWinDescent "
                f"(−{font.win_descent}) — clipped on Windows"))
        elif box[1] < DESCENDER - 1:
            findings.append(Finding(
                "WARN", "bounds",
                f"{g.name} sinks to y={box[1]:.0f}, past the design "
                f"descender ({DESCENDER})"))
        # ဩ/ဪ carry the same wrap sweep as part of their own letterform
        # (Padauk's top at 932, exactly its wrap height)
        is_wrap = ("medialRa" in g.name or g.name.startswith("uni103C")
                   or g.name in ("o.indep-myanmar", "au.indep-myanmar",
                                 "uni1029", "uni102A"))
        top_limit = WRAP_ASCENDER if is_wrap else ASCENDER
        if box[3] > font.win_ascent + 2:
            findings.append(Finding(
                "FAIL", "clipped",
                f"{g.name} rises to y={box[3]:.0f}, past usWinAscent "
                f"({font.win_ascent}) — clipped on Windows"))
        elif box[3] > top_limit + 1:
            findings.append(Finding(
                "WARN", "bounds",
                f"{g.name} rises to y={box[3]:.0f}, past the design "
                f"{'wrap band' if is_wrap else 'ascender'} ({top_limit})"))

    # every mark must have been moved by GPOS and land near its cluster
    if base_boxes:
        for g, box in mark_boxes:
            if g.x == 0 and g.y == 0 and g.name not in ("space", "nbspace"):
                findings.append(Finding(
                    "WARN", "attachment",
                    f"{g.name} was not repositioned by GPOS (offset 0,0) — "
                    "the mark/mkmk anchor pair may be missing"))
            span = [b for _, b in base_boxes if b[0] <= box[2] and b[2] >= box[0]]
            if not span:
                # Chained marks legitimately sit right of every base: in
                # ကျို့ the tone dot chains beside the ု, which itself sits
                # beside the ya leg — Padauk renders the dot at the same
                # spot. Stray means far from EVERY other ink in the cluster.
                others = [b for og, b in base_boxes + mark_boxes if og is not g]
                nearest = min(
                    (max(b[0] - box[2], box[0] - b[2], 0) for b in others),
                    default=0)
                if nearest > MARK_STRAY_TOLERANCE:
                    findings.append(Finding(
                        "FAIL", "attachment",
                        f"{g.name} sits {nearest:.0f} units clear of every "
                        "other glyph in the cluster — it is not attached"))

    # marks must not collide with one another
    for i in range(len(mark_boxes)):
        gi, bi = mark_boxes[i]
        for j in range(i + 1, len(mark_boxes)):
            gj, bj = mark_boxes[j]
            if gi.cluster != gj.cluster:
                continue
            gap_x = max(bj[0] - bi[2], bi[0] - bj[2], 0)
            gap_y = max(bj[1] - bi[3], bi[1] - bj[3], 0)
            if math.hypot(gap_x, gap_y) >= MIN_MARK_CLEARANCE:
                continue
            clearance = ink_clearance(
                _translated(font.outline(gi.name), gi.x, gi.y),
                _translated(font.outline(gj.name), gj.x, gj.y))
            if clearance == 0.0:
                findings.append(Finding(
                    "FAIL", "collision",
                    f"{gi.name} and {gj.name} overlap"))
            elif clearance < MIN_MARK_CLEARANCE:
                findings.append(Finding(
                    "WARN", "clearance",
                    f"{gi.name}/{gj.name} clear by only {clearance:.0f} units "
                    f"(spec minimum {MIN_MARK_CLEARANCE})"))

    # -- pre-base reordering ----------------------------------------------
    # ေ is stored AFTER its consonant and must render BEFORE it. Compare
    # inside one cluster only: in a sentence the e of the second syllable
    # legitimately follows the first syllable's consonant.
    if chr(E_VOWEL) in text and font.covers(E_VOWEL):
        e_name = font.cmap[E_VOWEL]
        for group in clusters_of(glyphs):
            for k, g in enumerate(group):
                if g.name != e_name:
                    continue
                before = [o for o in group[:k] if not font.is_mark(o.name)]
                if before:
                    findings.append(Finding(
                        "FAIL", "reorder",
                        f"ေ (U+1031) rendered after {before[0].name} instead "
                        "of in front of it — the run was not shaped with the "
                        "Myanmar model"))
                break

    # -- medial ra wrap ----------------------------------------------------
    if chr(MEDIAL_RA) in text and font.covers(MEDIAL_RA):
        wraps = [(g, b) for g, b in base_boxes + mark_boxes
                 if g.name.startswith("medialRa") or g.name.startswith("uni103C")]
        order = {id(g): i for i, g in enumerate(glyphs)}
        for g, wbox in wraps:
            # The wrapped letter is the FIRST base after the wrap — not the
            # widest one: a trailing ာ or း belongs outside the wrap and
            # would look like a huge overhang.
            after = sorted(((og, ob) for og, ob in base_boxes
                            if og.cluster == g.cluster and og is not g
                            and order[id(og)] > order[id(g)]),
                           key=lambda t: order[id(t[0])])
            if not after:
                continue
            base_g, bbox_ = after[0]
            if bbox_[0] < wbox[0] - 1:
                findings.append(Finding(
                    "FAIL", "wrap",
                    f"{base_g.name} starts left of the {g.name} wrap "
                    f"({bbox_[0]:.0f} < {wbox[0]:.0f}) — the wrap advance is "
                    "wrong or GDEF marks it as a mark"))
            overhang = bbox_[2] - wbox[2]
            if overhang > 100:
                findings.append(Finding(
                    "WARN", "wrap",
                    f"{base_g.name} overhangs {g.name} by {overhang:.0f} units "
                    "— the wide wrap variant should have been selected"))

    # -- the cluster occupies space ---------------------------------------
    if total_advance <= 0 and text.strip():
        findings.append(Finding("FAIL", "advance",
                                "the whole run advances 0 units"))
    return findings


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class Report:
    def __init__(self, font, corpus_path):
        self.font = font
        self.corpus_path = corpus_path
        self.findings = []
        self.cases = 0
        self.glyphs = 0
        self.block_titles = {}
        self.per_block = defaultdict(lambda: defaultdict(int))
        self.shape_seconds = 0.0
        self.check_seconds = 0.0
        self.reference = None
        self.ref_only_clean = []

    def add(self, case, findings):
        """Record one case; returns its worst severity ("PASS" when clean)."""
        self.cases += 1
        for f in findings:
            f.case = case
            self.findings.append(f)
            self.per_block[case.block][f.severity] += 1
        worst = min((f.severity for f in findings),
                    key=SEVERITIES.index, default="PASS")
        self.per_block[case.block]["cases"] += 1
        if worst == "PASS":
            self.per_block[case.block]["PASS"] += 1
        return worst

    # -- block level verdicts ---------------------------------------------
    def block_status(self, block):
        b = self.per_block[block]
        if b.get("FAIL"):
            return "FAIL"
        if b.get("WARN") or b.get("GAP"):
            return "PASS*"
        return "PASS"

    def summary_counts(self):
        return Counter(f.severity for f in self.findings)


def run(font, cases, blocks=None, reference=None):
    report = Report(font, None)
    t_shape = t_check = 0.0
    for case in cases:
        if blocks and case.block not in blocks:
            continue
        t0 = time.perf_counter()
        glyphs, advance = font.shape(case.text, case.language)
        t1 = time.perf_counter()
        findings = check_case(font, case, glyphs, advance)
        t2 = time.perf_counter()
        t_shape += t1 - t0
        t_check += t2 - t1
        report.glyphs += len(glyphs)
        worst = report.add(case, findings)
        if reference is not None and worst in ("FAIL", "GAP"):
            ref_glyphs, ref_adv = reference.shape(case.text, case.language)
            ref_findings = check_case(reference, case, ref_glyphs, ref_adv)
            ref_bad = [f for f in ref_findings if f.severity in ("FAIL", "GAP")]
            if not ref_bad:
                report.ref_only_clean.append(case)
    report.shape_seconds = t_shape
    report.check_seconds = t_check
    return report


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_text_report(report, titles, verbose=False, limit=6):
    font = report.font
    print(f"\n{font.family} {font.style}   ({font.path.name})")
    print(f"corpus: {report.cases} cases, {report.glyphs} shaped glyphs")
    counts = report.summary_counts()
    print("findings: " + (", ".join(f"{counts[s]} {s}" for s in SEVERITIES
                                    if counts[s]) or "none"))
    print()
    hdr = f"{'Block':<6}{'Cases':>6}{'Pass':>6}{'FAIL':>6}{'WARN':>6}{'GAP':>5}{'SPEC':>6}  Status  Title"
    print(hdr)
    print("-" * len(hdr))
    for block in sorted(report.per_block):
        b = report.per_block[block]
        print(f"{block:<6}{b['cases']:>6}{b['PASS']:>6}{b['FAIL']:>6}"
              f"{b['WARN']:>6}{b['GAP']:>5}{b['SPEC']:>6}  "
              f"{report.block_status(block):<7} {titles.get(block, '')[:44]}")
    print()

    by_code = defaultdict(list)
    for f in report.findings:
        by_code[(f.severity, f.code)].append(f)
    for sev in SEVERITIES:
        rows = [(code, fs) for (s, code), fs in by_code.items() if s == sev]
        if not rows:
            continue
        print(f"== {sev} " + "=" * 60)
        for code, fs in sorted(rows, key=lambda r: -len(r[1])):
            print(f"  {code} ({len(fs)})")
            # One line per distinct message: 92 cases hitting the same
            # too-tall wrap glyph is one fact, not 92 findings to read.
            groups = defaultdict(list)
            for f in fs:
                groups[f.message].append(f)
            ordered = sorted(groups.items(), key=lambda kv: -len(kv[1]))
            shown = ordered if verbose else ordered[:limit]
            for message, hits in shown:
                blocks = "".join(sorted({h.case.block for h in hits}))
                where = ", ".join(h.case.text for h in hits[:3])
                if len(hits) > 3:
                    where += f", … ({len(hits)} cases in {blocks})"
                print(f"    {message}")
                print(f"        {where}")
            if len(ordered) > len(shown):
                print(f"    … {len(ordered) - len(shown)} more distinct")
        print()

    if report.ref_only_clean:
        print(f"== reference gap ({len(report.ref_only_clean)}) " + "=" * 40)
        print("  cases the reference font shapes cleanly and this one does not:")
        for case in report.ref_only_clean[:20]:
            print(f"    [{case.block}] {case.text}")
        if len(report.ref_only_clean) > 20:
            print(f"    … {len(report.ref_only_clean) - 20} more")
        print()

    per_1000 = (report.shape_seconds / max(report.glyphs, 1)) * 1000 * 1000
    print(f"performance: shaping {report.shape_seconds * 1000:.0f} ms for "
          f"{report.glyphs} glyphs  →  {per_1000:.1f} ms per 1000 glyphs")
    print(f"             geometry checks {report.check_seconds * 1000:.0f} ms")


def write_json(report, titles, path):
    counts = report.summary_counts()
    doc = {
        "font": {"family": report.font.family, "style": report.font.style,
                 "file": report.font.path.name,
                 "upm": report.font.upm,
                 "scripts": report.font.scripts},
        "cases": report.cases,
        "glyphs": report.glyphs,
        "counts": {s: counts[s] for s in SEVERITIES},
        "blocks": {b: {"title": titles.get(b, ""),
                       "status": report.block_status(b),
                       **{k: v for k, v in report.per_block[b].items()}}
                   for b in sorted(report.per_block)},
        "performance": {
            "ms_per_1000_glyphs":
                round((report.shape_seconds / max(report.glyphs, 1)) * 1e6, 2),
            "shape_ms": round(report.shape_seconds * 1000, 1)},
        "findings": [f.as_dict() for f in report.findings],
    }
    Path(path).write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    return doc


def main():
    ap = argparse.ArgumentParser(
        description="Validate a Myanmar font against the shaping spec corpus.")
    ap.add_argument("font", type=Path)
    ap.add_argument("--corpus", type=Path,
                    default=Path(__file__).parent / "spec_corpus.txt")
    ap.add_argument("--reference", type=Path,
                    help="reference font (Padauk) for gap comparison")
    ap.add_argument("--block", help="comma-separated block letters to run")
    ap.add_argument("--json", type=Path, help="write the full report as JSON")
    ap.add_argument("--verbose", action="store_true",
                    help="list every finding, not the first few per code")
    ap.add_argument("--fail-on", default="FAIL",
                    choices=["FAIL", "WARN", "GAP", "none"],
                    help="exit non-zero at this severity (default FAIL)")
    args = ap.parse_args()

    cases, titles = load_corpus(args.corpus)
    font = FontUnderTest(args.font)
    reference = FontUnderTest(args.reference) if args.reference else None
    blocks = set(args.block.upper().split(",")) if args.block else None

    report = run(font, cases, blocks, reference)
    print_text_report(report, titles, args.verbose)
    if args.json:
        write_json(report, titles, args.json)
        print(f"\nJSON report: {args.json}")

    counts = report.summary_counts()
    if args.fail_on != "none":
        threshold = SEVERITIES.index(args.fail_on)
        bad = sum(counts[s] for s in SEVERITIES
                  if SEVERITIES.index(s) <= threshold)
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
