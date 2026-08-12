#!/usr/bin/env python3
"""Render a visual shaping proof of a built Myanmar font.

Shapes each line of text with HarfBuzz (the same engine Android, Chrome,
Linux and LibreOffice use), then rasterizes the shaped, positioned glyph
outlines straight out of the font file. No system text stack is involved,
so the PNG shows exactly what your font tells the shaping engine to do —
no font fallback can sneak in and hide a missing glyph or a dead rule.

Usage:
    python3 proof.py <font.ttf> <textfile-or-literal-text> <out.png> [--size 96]

    python3 proof.py build/MyFont-Regular.ttf test_corpus.txt proof.png
    python3 proof.py build/MyFont-Regular.ttf "ကျွန်ုပ်တို့ မြန်မာစာ" quick.png --size 128

The second argument is read as a file if one exists at that path, otherwise
it is treated as literal text (a literal "\\n" splits it into lines). In
files, blank lines and lines starting with # are skipped, so
test_corpus.txt works as-is.

Output:
  * a PNG proof sheet — dark text on white, one input line per numbered
    row, the em scaled to --size pixels
  * per line, the shaped glyph-name sequence on stdout, hb-shape style:
    name=cluster@x_offset,y_offset+x_advance (offsets only when nonzero)

Characters the font does not map (they shape to .notdef) render as hollow
rectangles, so gaps in a work-in-progress font are visible at a glance
instead of crashing the proof.

Implementation notes:
  * outlines come from fontTools' glyph set; FlattenPen converts each
    quadratic (TrueType) or cubic (CFF) curve into CURVE_SEGMENTS line
    segments and decomposes composite glyphs
  * filling uses a scanline rasterizer with the NONZERO winding rule.
    Nonzero is load-bearing here: Glyph Studio glyphs are overlapping
    stroke polygons (nonzero merges them; even-odd would punch a hole at
    every stroke crossing), while counters like the hole of ဝ still work
    because they run in the opposite direction
  * everything is rasterized OVERSAMPLE× too large and box-filtered down,
    which anti-aliases without any extra dependency

Dependencies: fontTools, uharfbuzz, Pillow
    pip install fonttools uharfbuzz pillow
"""

import argparse
import math
import sys
from pathlib import Path

try:
    import uharfbuzz as hb
    from fontTools.pens.basePen import BasePen
    from fontTools.ttLib import TTFont
    from PIL import Image, ImageDraw
except ImportError as exc:
    sys.exit(f"Missing dependency ({exc}).  pip install fonttools uharfbuzz pillow")

CURVE_SEGMENTS = 16   # line segments per flattened curve
OVERSAMPLE = 4        # rasterize 4x, box-filter down (anti-aliasing)
LEADING = 0.45        # extra space between rows, in em
MARGIN = 0.5          # page margin, in em
PAPER = 255           # white background
INK = 0               # dark text
LABEL = 160           # gray row numbers


# ---------------------------------------------------------------------------
# Outline extraction: a flattening pen
# ---------------------------------------------------------------------------

class FlattenPen(BasePen):
    """Collects a glyph as closed polygons; curves become line segments.

    BasePen does the heavy lifting: it splits TrueType's multi-off-curve
    qCurveTo runs (with their implied on-curve points) into single
    quadratics for _qCurveToOne, and decomposes composite glyphs through
    the glyph set. We only evaluate each curve at CURVE_SEGMENTS steps.
    """

    def __init__(self, glyph_set):
        super().__init__(glyph_set)
        self.contours = []      # list of [(x, y), ...] closed polygons
        self._points = None

    def _moveTo(self, pt):
        self._points = [pt]

    def _lineTo(self, pt):
        self._points.append(pt)

    def _qCurveToOne(self, c, pt):
        x0, y0 = self._getCurrentPoint()
        for i in range(1, CURVE_SEGMENTS + 1):
            t = i / CURVE_SEGMENTS
            m = 1.0 - t
            self._points.append((
                m * m * x0 + 2.0 * m * t * c[0] + t * t * pt[0],
                m * m * y0 + 2.0 * m * t * c[1] + t * t * pt[1],
            ))

    def _curveToOne(self, c1, c2, pt):
        x0, y0 = self._getCurrentPoint()
        for i in range(1, CURVE_SEGMENTS + 1):
            t = i / CURVE_SEGMENTS
            m = 1.0 - t
            self._points.append((
                m * m * m * x0 + 3 * m * m * t * c1[0]
                + 3 * m * t * t * c2[0] + t * t * t * pt[0],
                m * m * m * y0 + 3 * m * m * t * c1[1]
                + 3 * m * t * t * c2[1] + t * t * t * pt[1],
            ))

    def _closePath(self):
        if self._points is not None and len(self._points) >= 3:
            self.contours.append(self._points)
        self._points = None

    _endPath = _closePath   # stray open contours: treat as closed


# ---------------------------------------------------------------------------
# Filling: NONZERO-winding scanline rasterizer
# ---------------------------------------------------------------------------

def rasterize(contours):
    """Fill closed polygons with the NONZERO winding rule.

    contours: lists of (x, y) in device pixels, y growing downward.
    Returns (mask, left, top): mask is a PIL 'L' image (255 = ink) whose
    pixel (0, 0) sits at device coordinate (left, top). None if blank.

    For every scanline we collect the x positions where edges cross the
    pixel-center line y+0.5, each crossing signed +1 (edge points down) or
    -1 (up). Sweeping the sorted crossings left to right, pixels are inked
    while the running winding sum is nonzero. A hole contour runs opposite
    to its outer contour, cancels the sum, and stays empty — which is how
    both real counters and the hollow .notdef box below get their holes.
    """
    xs = [x for contour in contours for x, _ in contour]
    if not xs:
        return None
    ys = [y for contour in contours for _, y in contour]
    left = math.floor(min(xs)) - 1
    top = math.floor(min(ys)) - 1
    width = math.ceil(max(xs)) - left + 2
    height = math.ceil(max(ys)) - top + 2
    if width * height > 64_000_000:     # runaway outline: refuse politely
        return None

    # Bucket edge crossings by scanline (top-inclusive, bottom-exclusive,
    # so an edge shared by two chained segments is counted exactly once).
    buckets = [[] for _ in range(height)]
    for contour in contours:
        n = len(contour)
        for i in range(n):
            x0, y0 = contour[i]
            x1, y1 = contour[(i + 1) % n]
            if y0 == y1:
                continue                # horizontal edges never cross y+0.5
            direction = 1
            if y0 > y1:
                x0, y0, x1, y1, direction = x1, y1, x0, y0, -1
            y0 -= top
            y1 -= top
            slope = (x1 - x0) / (y1 - y0)
            first = max(0, math.ceil(y0 - 0.5))
            last = min(height - 1, math.ceil(y1 - 0.5) - 1)
            x0 -= left
            for iy in range(first, last + 1):
                buckets[iy].append((x0 + (iy + 0.5 - y0) * slope, direction))

    pixels = bytearray(width * height)
    for iy, crossings in enumerate(buckets):
        if not crossings:
            continue
        crossings.sort()
        row = iy * width
        winding = 0
        span_start = 0.0
        for x, direction in crossings:
            if winding == 0:
                span_start = x          # entering ink
            winding += direction
            if winding == 0:            # back to zero: close the span
                a = max(0, math.ceil(span_start - 0.5))
                b = min(width, math.ceil(x - 0.5))
                if b > a:
                    pixels[row + a:row + b] = b"\xff" * (b - a)

    return Image.frombytes("L", (width, height), bytes(pixels)), left, top


# ---------------------------------------------------------------------------
# Glyphs -> cached oversampled masks
# ---------------------------------------------------------------------------

def hollow_box_contours(advance, upm):
    """A hollow rectangle (font units) standing in for .notdef / missing.

    Outer contour and inner contour run in opposite directions, so the
    NONZERO fill leaves the middle empty — a visible frame, not a blot.
    """
    width = advance if advance >= upm * 0.3 else upm * 0.55
    x0, x1 = width * 0.10, width * 0.90
    y0, y1 = 0.0, upm * 0.68
    t = upm * 0.05
    outer = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]                    # CCW
    inner = [(x0 + t, y0 + t), (x0 + t, y1 - t),
             (x1 - t, y1 - t), (x1 - t, y0 + t)]                        # CW
    return [outer, inner]


class GlyphRenderer:
    """Rasterizes glyphs once per name and caches the oversampled mask."""

    def __init__(self, ttfont, px_per_em):
        self.glyph_set = ttfont.getGlyphSet()
        self.upm = ttfont["head"].unitsPerEm
        self.scale = px_per_em * OVERSAMPLE / self.upm   # device px per unit
        self._cache = {}

    def mask(self, glyph_name, missing, advance):
        """(mask, left, top) relative to the glyph origin on the baseline,
        in oversampled device pixels — or None for blank glyphs (space)."""
        key = ("\x00box", round(advance)) if missing else (glyph_name, 0)
        if key in self._cache:
            return self._cache[key]
        if missing:
            contours = hollow_box_contours(advance, self.upm)
        else:
            pen = FlattenPen(self.glyph_set)
            try:
                self.glyph_set[glyph_name].draw(pen)
                contours = pen.contours
            except Exception:            # unreadable outline: show the gap
                contours = hollow_box_contours(advance, self.upm)
        s = self.scale
        device = [[(x * s, -y * s) for x, y in c] for c in contours]
        result = rasterize(device)       # font y-up -> raster y-down
        self._cache[key] = result
        return result


# ---------------------------------------------------------------------------
# Shaping and page layout
# ---------------------------------------------------------------------------

def shape_line(hb_font, text):
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()       # Myanmar text -> mym2 shaper
    hb.shape(hb_font, buf)
    return list(zip(buf.glyph_infos, buf.glyph_positions))


def format_run(shaped, glyph_names):
    """hb-shape style summary: name=cluster@xoff,yoff+xadvance."""
    parts = []
    for info, pos in shaped:
        name = glyph_names[info.codepoint]
        item = f"{name}={info.cluster}"
        if pos.x_offset or pos.y_offset:
            item += f"@{pos.x_offset},{pos.y_offset}"
        item += f"+{pos.x_advance}"
        parts.append(item)
    return "|".join(parts)


def render_line(shaped, renderer, glyph_names):
    """Rasterize one shaped line onto its own mask.

    Returns (mask, left, top) in final (non-oversampled) pixels relative
    to the pen start (x=0) and the baseline (y=0), or None if the line
    made no ink. The mask keeps whatever overshoots the em box (deep
    stacks, high kinzi) instead of clipping it.
    """
    s = renderer.scale
    placements = []
    pen_x = pen_y = 0
    for info, pos in shaped:
        gid = info.codepoint
        name = glyph_names[gid]
        entry = renderer.mask(name, gid == 0, pos.x_advance)
        if entry is not None:
            mask, gleft, gtop = entry
            placements.append((
                mask,
                round((pen_x + pos.x_offset) * s) + gleft,
                round(-(pen_y + pos.y_offset) * s) + gtop,
            ))
        pen_x += pos.x_advance
        pen_y += pos.y_advance
    if not placements:
        return None

    min_x = min(px for _, px, _ in placements)
    min_y = min(py for _, _, py in placements)
    max_x = max(px + m.width for m, px, _ in placements)
    max_y = max(py + m.height for m, _, py in placements)
    # Snap the crop to the oversample grid so the downscale keeps the
    # baseline exactly where the layout math expects it.
    min_x -= min_x % OVERSAMPLE
    min_y -= min_y % OVERSAMPLE
    max_x += -max_x % OVERSAMPLE
    max_y += -max_y % OVERSAMPLE

    canvas = Image.new("L", (max_x - min_x, max_y - min_y), 0)
    for mask, px, py in placements:
        canvas.paste(255, (px - min_x, py - min_y), mask)
    small = canvas.resize(
        (canvas.width // OVERSAMPLE, canvas.height // OVERSAMPLE),
        Image.Resampling.BOX,
    )
    return small, min_x // OVERSAMPLE, min_y // OVERSAMPLE


def read_lines(arg):
    """A file path if it exists, else literal text ('\\n' splits lines)."""
    path = Path(arg)
    if path.is_file():
        raw = path.read_text(encoding="utf-8").splitlines()
    else:
        raw = arg.replace("\\n", "\n").splitlines()
    lines = []
    for line in raw:
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Render a HarfBuzz shaping proof sheet for a built font.",
        usage="proof.py <font.ttf> <textfile-or-literal-text> <out.png> [--size 96]",
    )
    parser.add_argument("font", help="built font to test (.ttf / .otf)")
    parser.add_argument("text", help="text file (one test string per line, "
                                     "# comments skipped) or literal text")
    parser.add_argument("output", help="proof sheet PNG to write")
    parser.add_argument("--size", type=int, default=96, metavar="PX",
                        help="pixels per em (default: 96)")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    font_path = Path(args.font)
    if not font_path.is_file():
        sys.exit(f"Font not found: {font_path}")
    lines = read_lines(args.text)
    if not lines:
        sys.exit("No test strings (file empty or all comments?)")
    size = max(12, min(args.size, 400))

    # One font file, two views: HarfBuzz shapes it, fontTools reads outlines.
    blob = hb.Blob(font_path.read_bytes())
    hb_font = hb.Font(hb.Face(blob))     # default scale = units per em
    ttfont = TTFont(str(font_path), lazy=True)
    glyph_names = ttfont.getGlyphOrder()
    upm = ttfont["head"].unitsPerEm
    hhea = ttfont["hhea"]
    ascent = hhea.ascent if hhea.ascent > 0 else round(upm * 0.8)
    descent = hhea.descent if hhea.descent < 0 else -round(upm * 0.4)

    px = size / upm                      # final pixels per font unit
    renderer = GlyphRenderer(ttfont, size)

    rendered = []
    total_boxes = 0
    for number, text in enumerate(lines, 1):
        shaped = shape_line(hb_font, text)
        boxes = sum(1 for info, _ in shaped if info.codepoint == 0)
        total_boxes += boxes
        print(f"[{number:02d}] {text}")
        note = f"   ({boxes} missing -> hollow box)" if boxes else ""
        print(f"     {format_run(shaped, glyph_names)}{note}")
        rendered.append(render_line(shaped, renderer, glyph_names))

    # Assemble the sheet: one row per line, baselines on a fixed grid.
    margin = round(size * MARGIN)
    label_w = 14 + 7 * len(str(len(lines)))
    row_h = round((ascent - descent) * px + size * LEADING)
    lefts = [left for entry in rendered if entry for _, left, _ in [entry]]
    text_x = margin + label_w - min(0, min(lefts, default=0))
    width = max((entry[0].width + entry[1] for entry in rendered if entry),
                default=size) + text_x + margin
    height = 2 * margin + row_h * len(lines)

    sheet = Image.new("L", (width, height), PAPER)
    draw = ImageDraw.Draw(sheet)
    for i, entry in enumerate(rendered):
        baseline = margin + i * row_h + round(ascent * px)
        draw.text((margin // 2, baseline - 12), f"{i + 1:02d}", fill=LABEL)
        if entry is None:
            continue
        mask, left, top = entry
        sheet.paste(INK, (text_x + left, baseline + top), mask)
    sheet.save(args.output)

    print(f"\nWrote {args.output}  ({width}x{height} px, {len(lines)} lines, "
          f"{total_boxes} missing-glyph boxes)")


if __name__ == "__main__":
    main()
