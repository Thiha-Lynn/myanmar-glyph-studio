#!/usr/bin/env python3
"""Generate the sample Glyph Studio project by skeletonizing Padauk.

Usage:
    python3 make_sample.py Padauk-Regular.ttf GlyphStudioSample.glyphstudio.json
    python3 make_sample.py Padauk-Regular.ttf out.json --debug /tmp/skel-debug

For every glyph in the studio inventory (web/data/glyphs.js) this script
extracts a letterform SKELETON from Padauk (an OFL-licensed Myanmar font by
SIL International) and writes it as stroke centerlines in the project JSON
schema that web/js/store.js and json_to_ufo.py consume.  The result is a
complete demonstration project that exercises the whole stroke-based
pipeline: studio JSON -> UFO -> fontmake TTF with working Myanmar shaping.

How each glyph is produced
    1. Shape the entry's guide string with HarfBuzz + Padauk.  Shaping picks
       the correct variant glyphs automatically (subjoined forms, kinzi,
       wide medial-ra, dotted-circle mark forms, ...).
    2. Drop the "context" glyphs the contributor would not draw (the dotted
       circle, or the base consonant of a variant guide).  Output glyphs are
       matched to input characters through HarfBuzz cluster values (buffer
       cluster level CHARACTERS), which — unlike comparing glyph ids against
       a separately shaped context string — also excludes contextual
       ALTERNATES of the context characters (e.g. Padauk swaps NA for
       "u1014.alt" in front of a below-mark; its glyph id never occurs when
       NA is shaped alone).
    3. Composite the remaining glyph outlines at their shaped positions
       (fontTools glyf outlines, curves flattened to short line segments)
       and scale from Padauk's 1024 UPM into our 1000 UPM space.
    4. Rasterize with a nonzero-winding scanline fill (counters stay open).
    5. Thin the raster to a 1 px skeleton (Zhang-Suen).
    6. Trace the skeleton pixel graph into polylines, splitting at
       junctions; tiny connected components become single-point "dot"
       strokes (anusvara, dot-below, visarga are solid dots whose skeleton
       collapses to almost nothing).
    7. Simplify with Ramer-Douglas-Peucker and convert back to font units
       (y up, baseline 0 — the guide string is shaped from x=0 at baseline
       0, exactly where the studio paints it under the drawing canvas).
    8. Set every stroke's width to the glyph's mean ink thickness
       (ink area / skeleton length), clamped to a plausible pen range.

Glyphs whose skeleton comes out empty are retried at twice the raster
resolution before being reported as skipped.

Some stacks do not exist in Padauk (it renders e.g. WA + virama + WA with a
visible virama instead of a subjoined WA); those entries are skipped and
listed in the summary.  Where the inventory's guide does not reach the
variant glyph the entry documents (Padauk considers MA a narrow base, so
the wide medial-ra guide "မြ" yields the narrow form), the script retries
with equivalent alternate context characters (e.g. "ဃြ") until the shape
differs from the plain sibling glyph.

The virama (U+1039) is NOT generated: it is invisible in rendered Burmese,
and json_to_ufo.py synthesizes the empty zero-width control glyph whenever
subjoined forms or the kinzi are present.

Only stdlib + fontTools + uharfbuzz are required; Pillow is needed only for
the optional --debug PNG dumps.

Letterform skeletons are derived from Padauk, copyright (c) SIL
International, licensed under the SIL Open Font License 1.1.  The generated
project inherits that license (OFL-1.1).
"""

import argparse
import json
import math
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_inventory  # noqa: E402  (shared codepoint lists)

try:
    import uharfbuzz as hb
    from fontTools.pens.basePen import BasePen
    from fontTools.ttLib import TTFont
except ImportError:
    sys.exit("fontTools and uharfbuzz are required:  pip install -r requirements.txt uharfbuzz")

UPM_OUT = 1000            # studio / pipeline units per em
PX_PER_UNIT = 0.25        # raster resolution (retried at 2x when needed)
RDP_EPSILON_UNITS = 6.0   # simplification tolerance (= 1.5 px at 0.25 px/unit)
MIN_FRAGMENT_PX = 4       # skeleton paths shorter than this are noise
MIN_DOT_DIAMETER = 14     # units; smaller isolated blobs are discarded
WIDTH_MIN, WIDTH_MAX = 30, 110  # stroke width clamp, font units
CANVAS_PAD_UNITS = 60     # raster margin around the composited outlines

DOTTED = "◌"   # dotted circle, the standard mark carrier
VIRAMA = "္"
ASAT = "်"

META = {
    "fontName": "Glyph Studio Sample",
    "styleName": "Regular",
    "author": ("Glyph Studio contributors; letterform skeletons derived from "
               "Padauk (c) SIL International, SIL Open Font License 1.1"),
    "license": "OFL-1.1",
}

# ---------------------------------------------------------------------------
# Glyph inventory (kept aligned with web/data/glyphs.js)
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

INDEPENDENT_VOWELS = [
    (0x1023, "i.indep"), (0x1024, "ii.indep"), (0x1025, "u.indep"),
    (0x1026, "uu.indep"), (0x1027, "e.indep"), (0x1029, "o.indep"),
    (0x102A, "au.indep"),
]

DEPENDENT_SIGNS = [
    (0x102B, "tallAa"), (0x102C, "aa"), (0x102D, "i"), (0x102E, "ii"),
    (0x102F, "u"), (0x1030, "uu"), (0x1031, "e"), (0x1032, "ai"),
    (0x1036, "anusvara"), (0x1037, "dotBelow"), (0x1038, "visarga"),
    (0x103A, "asat"),
]

MEDIALS = [
    (0x103B, "medialYa"), (0x103C, "medialRa"),
    (0x103D, "medialWa"), (0x103E, "medialHa"),
]

DIGITS = [
    (0x1040, "zero"), (0x1041, "one"), (0x1042, "two"), (0x1043, "three"),
    (0x1044, "four"), (0x1045, "five"), (0x1046, "six"), (0x1047, "seven"),
    (0x1048, "eight"), (0x1049, "nine"),
]

PUNCTUATION = [
    (0x104A, "sectionMark"), (0x104B, "section"), (0x104C, "locative"),
    (0x104D, "completed"), (0x104E, "aforementioned"), (0x104F, "genitive"),
    (0x103F, "greatSa"),
]

# Alternate context characters, tried in order when the guide itself cannot
# reach the variant glyph in Padauk (see module docstring).
SUB_ALT_TOPS = [chr(0x1000), chr(0x1010), chr(0x1015), chr(0x1019)]  # က တ ပ မ
WIDE_RA_ALT_BASES = [chr(0x1003), chr(0x1018), chr(0x101E)]          # ဃ ဘ သ
DESCENDER_ALT_BASES = [chr(0x100B), chr(0x1008), chr(0x100D)]        # ဋ ဈ ဍ


def build_inventory():
    """Recreate the 118 studio entries plus the synthetic virama glyph.

    Each entry:
        name       production glyph name
        guide      string to shape (the studio's on-canvas reference)
        exclude    input character indices whose glyphs are context, not ink
        group      section key (for the summary)
        alternates [(guide, exclude), ...] fallback shapings
        differ_from  sibling glyph name this entry should not duplicate
        is_sub     True for subjoined stack entries (enables virama guard)
    """
    def entry(name, guide, group, exclude=(), alternates=(), differ_from=None,
              is_sub=False):
        return {
            "name": name, "guide": guide, "group": group,
            "exclude": frozenset(exclude), "alternates": list(alternates),
            "differ_from": differ_from, "is_sub": is_sub,
        }

    inv = []
    for cp, name in CONSONANTS:
        inv.append(entry(f"{name}-myanmar", chr(cp), "consonants"))
    for cp, name in INDEPENDENT_VOWELS:
        inv.append(entry(f"{name}-myanmar", chr(cp), "vowels"))
    for cp, name in DEPENDENT_SIGNS:
        inv.append(entry(f"{name}-myanmar", DOTTED + chr(cp), "signs",
                         exclude={0}))
    for cp, name in MEDIALS:
        inv.append(entry(f"{name}-myanmar", DOTTED + chr(cp), "medials",
                         exclude={0}))
    for cp, name in DIGITS:
        inv.append(entry(f"{name}-myanmar", chr(cp), "digits"))
    for cp, name in PUNCTUATION:
        inv.append(entry(f"{name}-myanmar", chr(cp), "punctuation"))

    # Subjoined (stacked) consonants: guide shows X + virama + X, we keep
    # only the lower letter.  When Padauk cannot form the same-letter stack
    # (it ligates the whole stack, or falls back to a visible virama), try
    # the same consonant under a few common top letters instead.
    for cp, name in CONSONANTS:
        c = chr(cp)
        alts = [(top + VIRAMA + c, {0}) for top in SUB_ALT_TOPS if top != c]
        inv.append(entry(f"{name}-myanmar.sub", c + VIRAMA + c, "variants",
                         exclude={0}, alternates=alts, is_sub=True))

    # Kinzi: NGA + ASAT + VIRAMA reordered above the following base.
    inv.append(entry("kinzi-myanmar",
                     chr(0x1004) + ASAT + VIRAMA + chr(0x1000), "variants",
                     exclude={3}))

    # Wide medial RA: the guide's base MA counts as narrow in Padauk, so
    # wide bases are tried until the shape differs from plain medialRa.
    inv.append(entry("medialRa-myanmar.wide", chr(0x1019) + chr(0x103C),
                     "variants", exclude={0},
                     alternates=[(b + chr(0x103C), {0})
                                 for b in WIDE_RA_ALT_BASES],
                     differ_from="medialRa-myanmar"))

    # Short u/uu variants: Padauk picks the alternate leg after deep
    # descender bases, not after NA — hence the alternates.
    for mark_cp, name, plain in ((0x102F, "u", "u-myanmar"),
                                 (0x1030, "uu", "uu-myanmar")):
        m = chr(mark_cp)
        inv.append(entry(f"{name}-myanmar.alt", chr(0x1014) + m, "variants",
                         exclude={0},
                         alternates=[(b + m, {0})
                                     for b in DESCENDER_ALT_BASES],
                         differ_from=plain))

    # Tall medial RA (narrow + wide): the wrap's hook rises so ိ/ီ/ဲ has
    # room over the wrapped base (Padauk: uni103C.alt.narr / .alt.wide,
    # shaped by ခြီ / ကြီ).
    II = chr(0x102E)
    inv.append(entry("medialRa-myanmar.tall",
                     chr(0x1001) + chr(0x103C) + II, "variants",
                     exclude={0, 2},
                     alternates=[(b + chr(0x103C) + II, {0, 2})
                                 for b in (chr(0x1019), chr(0x1015))],
                     differ_from="medialRa-myanmar"))
    inv.append(entry("medialRa-myanmar.tall.wide",
                     chr(0x1000) + chr(0x103C) + II, "variants",
                     exclude={0, 2},
                     alternates=[(b + chr(0x103C) + II, {0, 2})
                                 for b in WIDE_RA_ALT_BASES],
                     differ_from="medialRa-myanmar.wide"))

    # Side-form bases: Padauk swaps the BASE for a leg-free variant in
    # front of below-marks (နု ညွ ရူ → uni1014.alt / uni100A.alt /
    # uni101B.alt) so the mark has room beside it.
    for base_cp, name in ((0x1014, "na"), (0x100A, "nnya"), (0x101B, "ra")):
        c = chr(base_cp)
        inv.append(entry(f"{name}-myanmar.alt", c + chr(0x102F), "variants",
                         exclude={1},
                         alternates=[(c + chr(0x1030), {1})],
                         differ_from=f"{name}-myanmar"))

    # i + anusvara fused ligature (ကိံ → uni102D1036): the ring and the
    # dot are drawn as one mark, the dot tucked beside the ring instead of
    # stacked on top of it.
    inv.append(entry("iAnusvara-myanmar",
                     DOTTED + chr(0x102D) + chr(0x1036), "variants",
                     exclude={0}))

    # ---- everything beyond core Burmese ---------------------------------
    # The rest of the Myanmar block (Pali, Mon, Karen, Kayah, Shan, Palaung,
    # Khamti, Aiton), Myanmar Extended-A/B, the dotted circle and optional
    # Latin. All are plain single characters: marks are shaped on the ◌
    # carrier and the carrier's glyph is dropped, exactly as in the studio.
    covered = {cp for cp, _ in CONSONANTS + INDEPENDENT_VOWELS + DIGITS}
    covered |= {row[0] for row in DEPENDENT_SIGNS + MEDIALS + PUNCTUATION}
    covered.add(0x1039)          # virama: synthesized, never drawn

    def add_plain(cp, group):
        ch = chr(cp)
        category = unicodedata.category(ch)
        if category in ("Mn", "Mc"):
            inv.append(entry(f"uni{cp:04X}", DOTTED + ch, group, exclude={0}))
        else:
            inv.append(entry(f"uni{cp:04X}", ch, group))

    for lo, hi, group in ((0x1000, 0x109F, "myanmarExt"),
                          (0xA9E0, 0xA9FF, "extB"),
                          (0xAA60, 0xAA7F, "extA")):
        for cp in range(lo, hi + 1):
            if cp in covered:
                continue
            try:
                unicodedata.name(chr(cp))
            except ValueError:
                continue         # unassigned
            add_plain(cp, group)

    inv.append(entry("uni25CC", chr(0x25CC), "support"))

    for cp in list(range(0x0041, 0x005B)) + list(range(0x0061, 0x007B)):
        add_plain(cp, "latin")
    for cp in range(0x0030, 0x003A):
        add_plain(cp, "latinDigits")
    # exactly the latinPunct group of web/data/glyphs-latin.js
    for cp in (0x0021, 0x0022, 0x0023, 0x0024, 0x0025, 0x0026, 0x0027,
               0x0028, 0x0029, 0x002A, 0x002B, 0x002C, 0x002D, 0x002E,
               0x002F, 0x003A, 0x003B, 0x003D, 0x003F, 0x0040):
        add_plain(cp, "latinPunct")

    # the punctuation, symbols and accented letters that carry a font
    # beyond plain English (shared with the studio inventory)
    for group, codepoints in (
            ("latinExtraPunct", gen_inventory.LATIN_EXTRA_PUNCT),
            ("latinExtraSymbols", gen_inventory.LATIN_EXTRA_SYMBOLS),
            ("latinExtraLetters", gen_inventory.LATIN_EXTRA_LETTERS)):
        for cp in codepoints:
            try:
                unicodedata.name(chr(cp))
            except ValueError:
                continue
            add_plain(cp, group)

    # No virama entry: U+1039 is invisible in rendered Burmese, and
    # json_to_ufo.py synthesizes the empty zero-width glyph it needs.
    return inv


# ---------------------------------------------------------------------------
# Shaping (uharfbuzz)
# ---------------------------------------------------------------------------

class Shaper:
    """Shape text with the source font; report glyphs with cluster + position.

    Buffer cluster level CHARACTERS keeps a 1:1 mapping between output
    glyphs and the input character(s) they came from, surviving the Myanmar
    shaper's reordering — that is what lets us drop context glyphs (and
    their contextual alternates) by input index.
    """

    def __init__(self, font_path):
        blob = hb.Blob.from_file_path(font_path)
        face = hb.Face(blob)
        self.font = hb.Font(face)
        self.upem = face.upem
        self.tt = TTFont(font_path)
        self.glyph_order = self.tt.getGlyphOrder()
        self.glyph_set = self.tt.getGlyphSet()
        virama_name = self.tt.getBestCmap().get(0x1039)
        self.virama_gid = (self.tt.getGlyphID(virama_name)
                           if virama_name else -1)

    def run(self, text):
        """-> [(gid, cluster, pen_start, x, y, x_advance)].

        pen_start is the pen x before this glyph; x/y are its drawing
        position (pen + offset).  Keeping both lets the caller re-origin
        spacing glyphs extracted after a context character.
        """
        buf = hb.Buffer()
        buf.cluster_level = hb.BufferClusterLevel.CHARACTERS
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.font, buf)
        out, x, y = [], 0, 0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            out.append((info.codepoint, info.cluster, x,
                        x + pos.x_offset, y + pos.y_offset, pos.x_advance))
            x += pos.x_advance
            y += pos.y_advance
        return out

    def glyph_name(self, gid):
        return self.glyph_order[gid]


def _reorigin(wanted):
    """Re-origin wanted glyphs and derive the glyph's true advance.

    wanted: [(gid, pen_start, x, y, x_adv)] in source font units.

    Attached marks (x_adv == 0) are positioned by the shaper with an
    x_offset that already cancels the context's advance, so they land near
    the origin on their own.  Spacing glyphs extracted after a context
    character (aa, tall aa, visarga, medials after the dotted circle) keep
    the context's pen advance in their coordinates — shift everything so
    the first spacing glyph starts at x = 0, and report the advance from
    that origin to the end of the last spacing glyph (0 for pure marks).
    """
    spacing = [w for w in wanted if w[4] > 0]
    origin = spacing[0][1] if spacing else 0
    placed = [(gid, x - origin, y) for gid, pen, x, y, adv in wanted]
    advance = max((pen + adv - origin for _, pen, _, _, adv in wanted
                   if adv > 0), default=0)
    return placed, max(0, advance)


def choose_shaping(shaper, item, produced):
    """Pick the first shaping attempt that isolates the wanted glyphs.

    Returns (placed, advance, note) where placed is [(gid, x, y), ...] and
    advance is the glyph's spacing width, both in source font units —
    or ([], 0, reason) when every attempt fails.
    """
    attempts = [(item["guide"], item["exclude"])] + item["alternates"]
    duplicate_fallback = None
    for i, (guide, exclude) in enumerate(attempts):
        run = shaper.run(guide)
        wanted = [(gid, pen, x, y, adv)
                  for gid, cluster, pen, x, y, adv in run
                  if cluster not in exclude]
        if not wanted:
            continue  # e.g. the whole stack ligated into the context glyph
        gids = frozenset(g for g, _, _, _, _ in wanted)
        if item["is_sub"] and shaper.virama_gid in gids:
            # Padauk rendered a visible virama: the stack does not exist.
            continue
        if item["differ_from"] and produced.get(item["differ_from"]) == gids:
            # Same glyph as the plain sibling — keep looking for the true
            # variant, but remember this shaping as a last resort.
            if duplicate_fallback is None:
                duplicate_fallback = wanted
            continue
        note = "" if i == 0 else f"via alternate context {guide!r}"
        placed, advance = _reorigin(wanted)
        return placed, advance, note
    if duplicate_fallback is not None:
        placed, advance = _reorigin(duplicate_fallback)
        return placed, advance, "duplicates its plain sibling"
    return [], 0, "shaping finds no non-context glyph"


# ---------------------------------------------------------------------------
# Outline extraction (fontTools)
# ---------------------------------------------------------------------------

class FlattenPen(BasePen):
    """Collects closed contours, sampling every curve into line segments."""

    SAMPLES = 16

    def __init__(self, glyph_set):
        super().__init__(glyph_set)
        self.contours = []
        self._points = None

    def _moveTo(self, pt):
        self._points = [pt]

    def _lineTo(self, pt):
        self._points.append(pt)

    def _qCurveToOne(self, p1, p2):
        p0 = self._getCurrentPoint()
        for i in range(1, self.SAMPLES + 1):
            t = i / self.SAMPLES
            mt = 1.0 - t
            self._points.append((
                mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0],
                mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1],
            ))

    def _curveToOne(self, p1, p2, p3):  # cubics, in case of CFF sources
        p0 = self._getCurrentPoint()
        for i in range(1, self.SAMPLES + 1):
            t = i / self.SAMPLES
            mt = 1.0 - t
            self._points.append((
                mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0]
                + 3 * mt * t * t * p2[0] + t ** 3 * p3[0],
                mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1]
                + 3 * mt * t * t * p2[1] + t ** 3 * p3[1],
            ))

    def _closePath(self):
        if self._points and len(self._points) >= 3:
            self.contours.append(self._points)
        self._points = None

    def _endPath(self):  # open contours should not occur; treat as closed
        self._closePath()


def composite_contours(shaper, placed):
    """Outline every placed glyph at its shaped position, in studio units.

    Positions and outlines are in the source font's UPM (Padauk: 1024) and
    get scaled into the pipeline's 1000 UPM space here.
    """
    scale = UPM_OUT / shaper.upem
    contours = []
    for gid, x, y in placed:
        pen = FlattenPen(shaper.glyph_set)
        shaper.glyph_set[shaper.glyph_name(gid)].draw(pen)
        for contour in pen.contours:
            contours.append([((px + x) * scale, (py + y) * scale)
                             for px, py in contour])
    return contours


# ---------------------------------------------------------------------------
# Rasterization: nonzero-winding scanline fill
# ---------------------------------------------------------------------------

class Raster:
    """Binary image of the composited outlines plus the units<->px mapping."""

    def __init__(self, contours, px_per_unit):
        xs = [p[0] for c in contours for p in c]
        ys = [p[1] for c in contours for p in c]
        self.ppu = px_per_unit
        self.x0 = math.floor(min(xs)) - CANVAS_PAD_UNITS
        self.y1 = math.ceil(max(ys)) + CANVAS_PAD_UNITS
        self.width = int((math.ceil(max(xs)) + CANVAS_PAD_UNITS - self.x0)
                         * px_per_unit) + 1
        self.height = int((self.y1 - (math.floor(min(ys)) - CANVAS_PAD_UNITS))
                          * px_per_unit) + 1
        self.ink = self._fill(contours)

    def to_px(self, pt):
        return ((pt[0] - self.x0) * self.ppu, (self.y1 - pt[1]) * self.ppu)

    def to_units(self, px, py):
        """Pixel center -> font units (y flipped back up)."""
        return (self.x0 + (px + 0.5) / self.ppu,
                self.y1 - (py + 0.5) / self.ppu)

    def _fill(self, contours):
        """Nonzero-winding scanline fill -> set of filled (x, y) pixels.

        Pillow's polygon fill treats every contour as solid (even-odd at
        best), which would close the counters of ka, wa, etc.  A hand-rolled
        nonzero fill keeps holes exactly like the font renderer does.
        """
        rows = [[] for _ in range(self.height)]  # row -> [(x1,y1,x2,y2)]
        for contour in contours:
            pts = [self.to_px(p) for p in contour]
            for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
                if ay == by:
                    continue  # horizontal edges never cross a scanline center
                lo = max(0, math.ceil(min(ay, by) - 0.5))
                hi = min(self.height - 1, math.floor(max(ay, by) - 0.5))
                for row in range(lo, hi + 1):
                    rows[row].append((ax, ay, bx, by))
        ink = set()
        for row, edges in enumerate(rows):
            if not edges:
                continue
            yc = row + 0.5
            crossings = []
            for ax, ay, bx, by in edges:
                if (ay <= yc < by) or (by <= yc < ay):
                    t = (yc - ay) / (by - ay)
                    crossings.append((ax + t * (bx - ax), 1 if by > ay else -1))
            crossings.sort()
            winding, span_start = 0, 0.0
            for cx, direction in crossings:
                if winding == 0:
                    span_start = cx
                winding += direction
                if winding == 0:
                    first = max(0, math.ceil(span_start - 0.5))
                    last = min(self.width - 1, math.ceil(cx - 0.5) - 1)
                    for col in range(first, last + 1):
                        ink.add((col, row))
        return ink

    def nearest_background(self, px, py, cap=40):
        """Chebyshev distance from a pixel to the nearest background pixel."""
        for r in range(1, cap):
            for dx in range(-r, r + 1):
                for dy in (-r, r):
                    if (px + dx, py + dy) not in self.ink:
                        return r
            for dy in range(-r + 1, r):
                for dx in (-r, r):
                    if (px + dx, py + dy) not in self.ink:
                        return r
        return cap


# ---------------------------------------------------------------------------
# Zhang-Suen thinning
# ---------------------------------------------------------------------------

def zhang_suen(ink):
    """Thin a set of (x, y) pixels to a 1 px wide skeleton."""
    skeleton = set(ink)

    def survives(p, step):
        x, y = p
        # P2..P9: clockwise from north
        n = [(x, y - 1), (x + 1, y - 1), (x + 1, y), (x + 1, y + 1),
             (x, y + 1), (x - 1, y + 1), (x - 1, y), (x - 1, y - 1)]
        b = [q in skeleton for q in n]
        count = sum(b)
        if not 2 <= count <= 6:
            return True
        transitions = sum(1 for i in range(8) if not b[i] and b[(i + 1) % 8])
        if transitions != 1:
            return True
        p2, p4, p6, p8 = b[0], b[2], b[4], b[6]
        if step == 1:
            return (p2 and p4 and p6) or (p4 and p6 and p8)
        return (p2 and p4 and p8) or (p2 and p6 and p8)

    changed = True
    while changed:
        changed = False
        for step in (1, 2):
            doomed = [p for p in skeleton if not survives(p, step)]
            if doomed:
                skeleton.difference_update(doomed)
                changed = True
    return skeleton


# ---------------------------------------------------------------------------
# Skeleton graph: build, trace into polylines
# ---------------------------------------------------------------------------

DIAGONALS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
ORTHOGONALS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def build_graph(skeleton):
    """8-neighbour adjacency, dropping diagonal edges that merely shortcut
    an existing orthogonal 2-step path (they would inflate node degrees and
    turn every L-corner into a fake junction)."""
    adj = {p: [] for p in skeleton}
    for x, y in skeleton:
        for dx, dy in ORTHOGONALS:
            q = (x + dx, y + dy)
            if q in skeleton:
                adj[(x, y)].append(q)
        for dx, dy in DIAGONALS:
            q = (x + dx, y + dy)
            if q in skeleton and (x + dx, y) not in skeleton \
                    and (x, y + dy) not in skeleton:
                adj[(x, y)].append(q)
    return adj


def connected_components(adj):
    seen, components = set(), []
    for start in adj:
        if start in seen:
            continue
        stack, component = [start], []
        seen.add(start)
        while stack:
            p = stack.pop()
            component.append(p)
            for q in adj[p]:
                if q not in seen:
                    seen.add(q)
                    stack.append(q)
        components.append(component)
    return components


def trace_paths(component, adj):
    """Walk the component's edges into polylines, splitting at junctions.

    Every edge is consumed exactly once: first from endpoints (degree 1),
    then from junctions (degree > 2), finally whatever remains are pure
    cycles.  Paths run through degree-2 pixels and stop at anything else.
    """
    unused = {p: set(adj[p]) for p in component}
    degree = {p: len(adj[p]) for p in component}

    def consume(a, b):
        unused[a].discard(b)
        unused[b].discard(a)

    def walk(start, first):
        path = [start, first]
        consume(start, first)
        prev, cur = start, first
        while degree[cur] == 2 and cur != start:
            nxt = next((q for q in unused[cur] if q != prev),
                       next(iter(unused[cur]), None))
            if nxt is None:
                break
            consume(cur, nxt)
            path.append(nxt)
            prev, cur = cur, nxt
        return path

    paths = []
    for kind in ("endpoint", "junction", "cycle"):
        for p in component:
            if kind == "endpoint" and degree[p] != 1:
                continue
            if kind == "junction" and degree[p] <= 2:
                continue
            while unused[p]:
                paths.append(walk(p, next(iter(unused[p]))))
    return paths


def path_length(path):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1])
               for a, b in zip(path, path[1:]))


# ---------------------------------------------------------------------------
# Ramer-Douglas-Peucker simplification
# ---------------------------------------------------------------------------

def rdp(points, epsilon):
    if len(points) < 3:
        return list(points)
    ax, ay = points[0]
    bx, by = points[-1]
    dx, dy = bx - ax, by - ay
    seg_len = math.hypot(dx, dy)
    worst_i, worst_d = 0, -1.0
    for i in range(1, len(points) - 1):
        px, py = points[i]
        if seg_len == 0:
            d = math.hypot(px - ax, py - ay)
        else:
            d = abs(dx * (ay - py) - dy * (ax - px)) / seg_len
        if d > worst_d:
            worst_i, worst_d = i, d
    if worst_d <= epsilon:
        return [points[0], points[-1]]
    left = rdp(points[:worst_i + 1], epsilon)
    right = rdp(points[worst_i:], epsilon)
    return left[:-1] + right


# ---------------------------------------------------------------------------
# Per-glyph pipeline: contours -> strokes
# ---------------------------------------------------------------------------

def extract_strokes(contours, px_per_unit):
    """Skeletonize composited contours into studio strokes (font units)."""
    raster = Raster(contours, px_per_unit)
    if not raster.ink:
        return []
    skeleton = zhang_suen(raster.ink)
    adj = build_graph(skeleton)

    polylines, dots, skeleton_len = [], [], 0.0
    for component in connected_components(adj):
        if len(component) < MIN_FRAGMENT_PX:
            # A solid dot (anusvara, dot-below, ...) thins down to almost a
            # single pixel: recover its size from the original ink instead.
            cx = sum(p[0] for p in component) / len(component)
            cy = sum(p[1] for p in component) / len(component)
            radius_px = raster.nearest_background(round(cx), round(cy))
            diameter = 2.0 * radius_px / px_per_unit
            if diameter >= MIN_DOT_DIAMETER:
                x, y = raster.to_units(cx, cy)
                dots.append({
                    "width": int(min(WIDTH_MAX, max(WIDTH_MIN, diameter))),
                    "points": [[round(x), round(y)]],
                })
            continue
        for path in trace_paths(component, adj):
            if len(path) < MIN_FRAGMENT_PX:
                continue
            skeleton_len += path_length(path)
            polylines.append(path)

    # Mean ink thickness -> the glyph's uniform stroke width.
    width = WIDTH_MIN
    if skeleton_len > 0:
        thickness_px = len(raster.ink) / max(1.0, skeleton_len)
        width = int(min(WIDTH_MAX, max(WIDTH_MIN, thickness_px / px_per_unit)))

    strokes = []
    for path in polylines:
        simplified = rdp(path, RDP_EPSILON_UNITS * px_per_unit)
        points, last = [], None
        for px, py in simplified:
            x, y = raster.to_units(px, py)
            pt = [round(x), round(y)]
            if pt != last:
                points.append(pt)
            last = pt
        if len(points) >= 2:
            strokes.append({"width": width, "points": points})
    return strokes + dots


def solid_shape_stroke(contours):
    """One dot standing in for a solid shape whose skeleton vanished.

    Only for shapes that are close to round — anything longer than it is
    wide would be badly served by a disc, and is better reported as
    skipped than silently mangled.
    """
    xs = [p[0] for contour in contours for p in contour]
    ys = [p[1] for contour in contours for p in contour]
    if not xs:
        return []
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    if width <= 0 or height <= 0:
        return []
    if max(width, height) / min(width, height) > 1.6:
        return []
    return [{
        "width": round(min(width, height)),
        "points": [[round((min(xs) + max(xs)) / 2), round((min(ys) + max(ys)) / 2)]],
    }]


def debug_dump(contours, strokes, px_per_unit, path):
    """Optional PNG: ink in grey, skeleton strokes in red (needs Pillow)."""
    from PIL import Image
    raster = Raster(contours, px_per_unit)
    img = Image.new("RGB", (raster.width, raster.height), (255, 255, 255))
    pixels = img.load()
    for x, y in raster.ink:
        pixels[x, y] = (200, 200, 200)
    for stroke in strokes:
        pts = [raster.to_px([p[0], p[1]]) for p in stroke["points"]]
        if len(pts) == 1:
            pts = pts * 2
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            steps = max(1, int(math.hypot(bx - ax, by - ay)))
            for i in range(steps + 1):
                t = i / steps
                x = int(ax + t * (bx - ax))
                y = int(ay + t * (by - ay))
                if 0 <= x < raster.width and 0 <= y < raster.height:
                    pixels[x, y] = (220, 30, 30)
    img.save(path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Skeletonize Padauk into a sample Glyph Studio project.")
    parser.add_argument("source_font", help="path to Padauk-Regular.ttf")
    parser.add_argument("output_json", help="path to write *.glyphstudio.json")
    parser.add_argument("--debug", metavar="DIR",
                        help="write a per-glyph raster+skeleton PNG here")
    parser.add_argument("--font-name", help="family name for the project")
    parser.add_argument("--author", help="author credit for the project")
    parser.add_argument("--core-only", action="store_true",
                        help="core Burmese only (the 118-entry studio set)")
    args = parser.parse_args(argv)

    meta = dict(META)
    if args.font_name:
        meta["fontName"] = args.font_name
    if args.author:
        meta["author"] = args.author

    shaper = Shaper(args.source_font)
    inventory = build_inventory()
    if args.core_only:
        core = {"consonants", "vowels", "signs", "medials", "digits",
                "punctuation", "variants"}
        inventory = [i for i in inventory if i["group"] in core]

    glyphs = {}
    produced = {}          # name -> frozenset of source gids (differ_from)
    skipped = []           # (name, reason)
    notes = []             # (name, note)
    by_group = {}          # group -> [done, total]

    for item in inventory:
        name, group = item["name"], item["group"]
        by_group.setdefault(group, [0, 0])[1] += 1

        placed, advance_src, note = choose_shaping(shaper, item, produced)
        if not placed:
            skipped.append((name, note))
            print(f"  skip {name:26s} {note}")
            continue

        contours = composite_contours(shaper, placed)
        if not contours:
            skipped.append((name, "wanted glyphs have no outlines"))
            print(f"  skip {name:26s} wanted glyphs have no outlines")
            continue

        strokes, scale = [], PX_PER_UNIT
        for scale in (PX_PER_UNIT, PX_PER_UNIT * 2):
            strokes = extract_strokes(contours, scale)
            if strokes:
                break
        if not strokes:
            # A solid, roughly round shape (the bullet •, a filled dot)
            # thins away to nothing: there is no centre-LINE, only a centre
            # POINT. Keep it as a single-point stroke, which the outline
            # expander draws as a disc of that width.
            strokes = solid_shape_stroke(contours)
            if strokes:
                note = (note + "; " if note else "") + "solid shape kept as a dot"
        if not strokes:
            skipped.append((name, "empty skeleton even at 2x raster scale"))
            print(f"  skip {name:26s} empty skeleton even at 2x raster scale")
            continue
        if scale != PX_PER_UNIT:
            note = (note + "; " if note else "") + "rasterized at 2x scale"

        # real advance from the source font, scaled into 1000 UPM
        # (explicit 0 keeps attached marks zero-width in the build)
        glyphs[name] = {
            "advance": round(advance_src * UPM_OUT / shaper.upem),
            "strokes": strokes,
        }
        produced[name] = frozenset(g for g, _, _ in placed)
        by_group[group][0] += 1
        if note:
            notes.append((name, note))

        src = "+".join(shaper.glyph_name(g) for g, _, _ in placed)
        print(f"  ok   {name:26s} {len(strokes):2d} strokes  "
              f"w={strokes[0]['width']:3d}  from {src}")

        if args.debug:
            debug_dir = Path(args.debug)
            debug_dir.mkdir(parents=True, exist_ok=True)
            debug_dump(contours, strokes, scale, debug_dir / f"{name}.png")

    project = {
        "format": "mm-glyph-studio",
        "version": 1,
        "meta": meta,
        "glyphs": glyphs,
    }
    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(project, ensure_ascii=False, indent=1),
                        encoding="utf-8")

    print("\nSummary")
    for group, (done, total) in by_group.items():
        print(f"  {group:12s} {done}/{total}")
    print(f"  total        {len(glyphs)}/{len(inventory)} glyphs "
          f"-> {out_path}")
    if notes:
        print("Notes")
        for name, note in notes:
            print(f"  {name}: {note}")
    if skipped:
        print("Skipped")
        for name, reason in skipped:
            print(f"  {name}: {reason}")
    print("Next:  python3 json_to_ufo.py", out_path, "build/")


if __name__ == "__main__":
    main()
