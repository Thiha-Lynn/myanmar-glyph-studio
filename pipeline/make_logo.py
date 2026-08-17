#!/usr/bin/env python3
"""Generate the project's logo set from the project's own typeface.

A font project whose logo is set in somebody else's typeface is arguing
against itself. Worse, the old icon was `<text font-family="Padauk,…">`,
which renders as tofu on any machine without a Myanmar font — the exact
failure this project exists to fix. Everything here is drawn from Myanmar
Glyph Sans, the face this toolchain produced, and emitted as outline
paths, so it looks identical everywhere with nothing installed.

The mark is က (U+1000, the first letter of the alphabet) carrying the one
idea the project rests on: you draw a centre line and the pipeline grows
a letter around it. Both halves are real data — the outline is read from
the built TTF, the spine from the very strokes in the project file that
produced that outline. The spine lies inside the ink because it is what
the ink was grown from, not because it was drawn to look that way.

Text is laid out with HarfBuzz, the same engine the fonts are validated
with, so the Burmese line in the lockup is a live shaping proof.

    mgs-logo

Writes (all generated — edit this script, not the SVGs):
    web/icons/icon.svg              PWA / favicon mark
    web/icons/social-preview.svg    1200x630 link-share card (og:image)
    docs/images/logo-mark.svg       the mark alone
    docs/images/logo.svg            lockup for light backgrounds
    docs/images/logo-dark.svg       lockup for dark backgrounds

The card lives under web/ because that is the directory GitHub Pages
serves, and og:image needs a public URL.

The PNG rasters beside them (icon-180, icon-512, social-preview.png —
what app installers and link scrapers actually consume) are rendered
from these with headless Chrome; there is no Python rasteriser in this
toolchain and five files do not justify adding one:

    chrome --headless=new --window-size=512,512 \\
           --screenshot=web/icons/icon-512.png file://$PWD/web/icons/icon.svg
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repo_paths import repo_root  # noqa: E402

try:
    import uharfbuzz as hb
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
except ImportError:                                         # pragma: no cover
    sys.exit("needs fonttools + uharfbuzz:  pip install -r requirements.txt")

# The app's own tokens (web/css/app.css, manifest.webmanifest).
DARK = "#1d1713"          # dark surface
CREAM = "#ede3d2"         # the letter on dark
ACCENT = "#a8352f"        # brand red — readable on white
ACCENT_LIGHT = "#e0705c"  # dark-theme accent — readable on the dark card
GOLD = "#d2a544"          # frame line
MUTED_LIGHT = "#6b5e4c"
MUTED_DARK = "#a8977f"

MARK_CHAR = "က"
MARK_GLYPH_NAME = "ka-myanmar"
WORDMARK = "Myanmar Glyph Studio"
TAGLINE_MY = "မြန်မာဖောင့် ရေးဆွဲကိရိယာ"
SITE = "thiha-lynn.github.io/myanmar-glyph-studio"


def font_file(root, style="Bold"):
    return str(root / "projects" / "myanmar-glyph-sans"
               / f"MyanmarGlyphSans-{style}.ttf")


def shaped(font_path, text, em):
    """Lay `text` out with HarfBuzz; return (path_d, advance, ink).

    Coordinates come back in SVG space (y down) with the baseline at y=0
    and the first glyph starting at x=0, so callers only translate. `ink`
    is the measured bounding box (x_min, y_min, x_max, y_max) in the same
    space — Burmese hangs marks well below the baseline, so anything
    placed underneath has to be positioned from real extents rather than
    from a guess at the descender.
    """
    blob = hb.Blob.from_file_path(font_path)
    face = hb.Face(blob)
    hb_font = hb.Font(face)
    upm = face.upem
    scale = em / upm

    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hb_font, buf)

    tt = TTFont(font_path)
    glyph_set = tt.getGlyphSet()
    order = tt.getGlyphOrder()

    pen_x, commands = 0.0, []
    boxes = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = order[info.codepoint]
        if name == ".notdef":
            sys.exit(f"{Path(font_path).name} cannot render {text!r} — "
                     f"the logo must not ship a missing glyph")
        transform = (scale, 0, 0, -scale,
                     (pen_x + pos.x_offset) * scale, -pos.y_offset * scale)
        # One decimal is sub-pixel at any size these assets are used at,
        # and keeps the files a fraction of full float precision.
        pen = SVGPathPen(glyph_set, ntos=lambda v: f"{v:.1f}".rstrip("0")
                         .rstrip(".") or "0")
        glyph_set[name].draw(TransformPen(pen, transform))
        d = pen.getCommands()
        if d:
            commands.append(d)
        bounds = BoundsPen(glyph_set)
        glyph_set[name].draw(TransformPen(bounds, transform))
        if bounds.bounds:
            boxes.append(bounds.bounds)
        pen_x += pos.x_advance

    ink = (min(b[0] for b in boxes), min(b[1] for b in boxes),
           max(b[2] for b in boxes), max(b[3] for b in boxes)) if boxes else \
          (0, 0, pen_x * scale, 0)
    return " ".join(commands), pen_x * scale, ink


def mark_geometry(root, size, fill=0.72):
    """Place က in a square: returns (path_d, spine_d, scale, tx, baseline)."""
    path = font_file(root)
    tt = TTFont(path)
    bp = BoundsPen(tt.getGlyphSet())
    tt.getGlyphSet()[tt.getBestCmap()[ord(MARK_CHAR)]].draw(bp)
    x_min, y_min, x_max, y_max = bp.bounds
    upm = tt["head"].unitsPerEm

    # Size by measured ink, not by em, so a redrawn က cannot quietly shift
    # the mark off centre or change how big it looks.
    scale = (size * fill) / (x_max - x_min)
    ink_w = (x_max - x_min) * scale
    ink_h = (y_max - y_min) * scale
    tx = (size - ink_w) / 2 - x_min * scale
    baseline = (size - ink_h) / 2 + y_max * scale

    d, _, _ = shaped(path, MARK_CHAR, scale * upm)
    return d, spine_path(root, scale, tx, baseline), scale, tx, baseline


def spine_path(root, scale, tx, baseline):
    """The centre lines from the project file — what the designer drew."""
    project = next((root / "projects" / "myanmar-glyph-sans")
                   .glob("*.glyphstudio.json"))
    glyph = json.loads(project.read_text(encoding="utf-8"))["glyphs"][
        MARK_GLYPH_NAME]
    out = []
    for stroke in glyph["strokes"]:
        pts = stroke.get("points") or []
        if len(pts) < 2:
            continue
        out.append("".join(
            f"{'M' if i == 0 else 'L'}"
            f"{tx + p[0] * scale:.1f} {baseline - p[1] * scale:.1f}"
            for i, p in enumerate(pts)))
    return " ".join(out)


def mark_svg(root, size=512, standalone=True, spine=True):
    """The square mark.

    `spine` shows the drawn centre line inside the ink — the project's idea
    in one image, and legible from roughly 64px up. Below that it silts up,
    so the favicon and app icon are drawn without it.
    """
    d, spine_d, _, tx, baseline = mark_geometry(root, size)
    body = [
        f'<rect width="{size}" height="{size}" rx="{size * 0.1875:.0f}" '
        f'fill="{DARK}"/>',
        f'<rect x="{size * 0.055:.0f}" y="{size * 0.055:.0f}" '
        f'width="{size * 0.89:.0f}" height="{size * 0.89:.0f}" '
        f'rx="{size * 0.14:.0f}" fill="none" stroke="{GOLD}" '
        f'stroke-width="{size / 73:.1f}" opacity="0.9"/>',
        f'<line x1="{size * 0.13:.0f}" y1="{baseline:.1f}" '
        f'x2="{size * 0.87:.0f}" y2="{baseline:.1f}" stroke="{ACCENT_LIGHT}" '
        f'stroke-width="{size / 110:.1f}" opacity="0.55"/>',
        f'<path transform="translate({tx:.1f} {baseline:.1f})" d="{d}" '
        f'fill="{CREAM}"/>',
    ]
    if spine:
        body.append(
            f'<path d="{spine_d}" fill="none" stroke="{ACCENT}" '
            f'stroke-width="{size / 150:.1f}" stroke-linecap="round" '
            f'stroke-linejoin="round" opacity="0.55"/>')
    if not standalone:
        return body
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'role="img" aria-label="Myanmar Glyph Studio">\n'
        f'  <title>Myanmar Glyph Studio</title>\n  '
        + "\n  ".join(body) + "\n</svg>\n")


def lockup_svg(root, on_dark=False, mark=132, pad=28):
    """Mark + wordmark + Burmese tagline, on a transparent background."""
    ink = CREAM if on_dark else DARK
    muted = MUTED_DARK if on_dark else MUTED_LIGHT

    word_d, word_w, _ = shaped(font_file(root, "Bold"), WORDMARK, 62)
    tag_d, tag_w, _ = shaped(font_file(root, "Regular"), TAGLINE_MY, 38)

    text_x = pad + mark + 34
    width = text_x + max(word_w, tag_w) + pad
    height = mark + pad * 2
    word_base = height / 2 - 6
    tag_base = height / 2 + 46

    marks = mark_svg(root, mark, standalone=False)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width:.0f} {height:.0f}" role="img" '
        f'aria-label="Myanmar Glyph Studio">\n'
        f'  <title>Myanmar Glyph Studio</title>\n'
        f'  <g transform="translate({pad} {pad})">\n    '
        + "\n    ".join(marks) + "\n  </g>\n"
        f'  <path transform="translate({text_x:.0f} {word_base:.0f})" '
        f'd="{word_d}" fill="{ink}"/>\n'
        f'  <path transform="translate({text_x:.0f} {tag_base:.0f})" '
        f'd="{tag_d}" fill="{muted}"/>\n'
        f'</svg>\n')


def social_svg(root, width=1200, height=630):
    """The card shown when the repository or site is shared as a link.

    Every glyph on it — Latin and Burmese — is drawn from the font this
    project builds, which is the whole argument in one image.
    """
    mark = 168
    word_d, word_w, _ = shaped(font_file(root, "Bold"), WORDMARK, 76)
    tag_d, tag_w, _ = shaped(font_file(root, "Regular"), TAGLINE_MY, 42)
    sample = "ကျွန်ုပ်တို့၏ ဖောင့်"
    sample_d, sample_w, sample_ink = shaped(
        font_file(root, "Bold"), sample, 132)
    line_d, line_w, _ = shaped(font_file(root, "Regular"),
                               "Draw it. Shape it. Ship it.", 32)
    site_d, site_w, _ = shaped(font_file(root, "Regular"), SITE, 28)

    left, top = 88, 74
    rule_y = top + 214
    # The sample is the star: centre it in the space under the rule, then
    # put the footer below its LOWEST INK, not below its baseline. Burmese
    # below-marks reach far under the baseline — measuring is what keeps
    # the ့ of ကျွန်ုပ် off the line beneath it.
    sample_base = 452
    footer_y = max(sample_base + sample_ink[3] + 46, height - 52)
    gap = 26
    pair_w = line_w + gap + site_w
    pair_x = (width - pair_w) / 2

    marks = mark_svg(root, mark, standalone=False, spine=True)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Myanmar Glyph Studio — {TAGLINE_MY}">\n'
        f'  <title>Myanmar Glyph Studio</title>\n'
        f'  <rect width="{width}" height="{height}" fill="{DARK}"/>\n'
        f'  <g transform="translate({left} {top})">\n    '
        + "\n    ".join(marks) + "\n  </g>\n"
        f'  <path transform="translate({left + mark + 44} {top + 78})" '
        f'd="{word_d}" fill="{CREAM}"/>\n'
        f'  <path transform="translate({left + mark + 44} {top + 138})" '
        f'd="{tag_d}" fill="{MUTED_DARK}"/>\n'
        f'  <line x1="{left}" y1="{rule_y}" x2="{width - left}" '
        f'y2="{rule_y}" stroke="{GOLD}" stroke-width="2" opacity="0.45"/>\n'
        f'  <path transform="translate({(width - sample_w) / 2:.0f} '
        f'{sample_base})" d="{sample_d}" fill="{CREAM}"/>\n'
        f'  <path transform="translate({pair_x:.0f} {footer_y:.0f})" '
        f'd="{line_d}" fill="{ACCENT_LIGHT}"/>\n'
        f'  <path transform="translate({pair_x + line_w + gap:.0f} '
        f'{footer_y:.0f})" d="{site_d}" fill="{MUTED_DARK}"/>\n'
        f'</svg>\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()
    root = repo_root("mgs-logo")

    docs = args.out_dir or (root / "docs" / "images")
    docs.mkdir(parents=True, exist_ok=True)
    icons = root / "web" / "icons"
    icons.mkdir(parents=True, exist_ok=True)

    written = {
        # The app icon is also the favicon, so it is drawn without the
        # spine: at 16px the centre line silts the letter up.
        icons / "icon.svg": mark_svg(root, spine=False),
        docs / "logo-mark.svg": mark_svg(root, spine=True),
        docs / "logo.svg": lockup_svg(root, on_dark=False),
        docs / "logo-dark.svg": lockup_svg(root, on_dark=True),
        icons / "social-preview.svg": social_svg(root),
    }
    for path, text in written.items():
        path.write_text(text, encoding="utf-8")
        print(f"Wrote {path.relative_to(root)} ({len(text):,} bytes)")


if __name__ == "__main__":
    main()
