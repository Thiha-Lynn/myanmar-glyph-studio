#!/usr/bin/env python3
"""Typeset a Burmese book as a PDF, set in a font this toolchain built.

Why draw outlines instead of embedding the font and letting the reader do
it: a PDF viewer has no shaping engine. Embedding a Myanmar font and
handing it a string produces the characters in storage order with no
reordering, no stacking, no mark positioning — the Zawgyi-era mess. The
only way a PDF shows correct Burmese is if the *producer* shapes the text
and places every glyph itself.

So that is what this does. HarfBuzz shapes each line exactly as it does
in the validator, and each positioned glyph's outline is written into the
page as a filled path. The result needs nothing installed, renders
identically everywhere, prints, and is a fair proof of the font — what
you see is the shaping this repository generated, not a viewer's guess.

    python3 make_pdf.py                                  # -> book.pdf
    python3 make_pdf.py --font projects/bagan-display/BaganDisplay-Bold.ttf
    python3 make_pdf.py --size 15 --page A4 --out /tmp/proof.pdf

Dependencies: fontTools, uharfbuzz (both already required).
"""

import argparse
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repo_paths import repo_root  # noqa: E402

try:
    import uharfbuzz as hb
    from fontTools.pens.basePen import BasePen
    from fontTools.ttLib import TTFont
except ImportError as exc:                                  # pragma: no cover
    sys.exit(f"Missing dependency ({exc}).  pip install fonttools uharfbuzz")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FONT = ROOT / "projects" / "bagan-display" / "BaganDisplay-Bold.ttf"
DEFAULT_BOOK = ROOT / "web" / "data" / "book.js"
DEFAULT_OUT = ROOT / "book.pdf"

# points; PDF's unit is 1/72 inch and its origin is bottom-left, y up —
# the same orientation as font units, so no flip is needed anywhere.
PAGES = {"A4": (595.28, 841.89), "A5": (419.53, 595.28),
         "LETTER": (612.0, 792.0)}


class PDFPen(BasePen):
    """Glyph outlines straight into a PDF content stream.

    BasePen turns the quadratic curves TrueType actually stores into the
    cubics PDF understands, so only the cubic case needs handling here.
    """

    def __init__(self, glyph_set, out, scale, dx, dy):
        super().__init__(glyph_set)
        self.out, self.s, self.dx, self.dy = out, scale, dx, dy

    def _pt(self, p):
        return f"{p[0] * self.s + self.dx:.2f} {p[1] * self.s + self.dy:.2f}"

    def _moveTo(self, p):
        self.out.append(f"{self._pt(p)} m")

    def _lineTo(self, p):
        self.out.append(f"{self._pt(p)} l")

    def _curveToOne(self, a, b, c):
        self.out.append(f"{self._pt(a)} {self._pt(b)} {self._pt(c)} c")

    def _closePath(self):
        self.out.append("h")


class Typesetter:
    def __init__(self, font_path, size):
        self.path = Path(font_path)
        blob = hb.Blob.from_file_path(str(font_path))
        self.hb = hb.Font(hb.Face(blob))
        self.tt = TTFont(font_path, lazy=True)
        self.glyph_set = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.upm = self.tt["head"].unitsPerEm
        self.size = size
        self.family = self.tt["name"].getDebugName(4) or self.path.stem
        self._outlines = {}
        self._tags = {}
        self.used = set()

    def shape(self, text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf)
        return list(zip(buf.glyph_infos, buf.glyph_positions))

    def width(self, text):
        return sum(p.x_advance for _, p in self.shape(text)) * self.size / self.upm

    def wrap(self, text, measure):
        """Greedy line breaking on the phrase spaces Burmese verse uses.

        Never breaks inside a run of Burmese: there are no word spaces to
        break on, and splitting a syllable cluster would be this script's
        rendering bug rather than the font's.
        """
        words, lines, line = text.split(" "), [], ""
        for word in words:
            trial = (line + " " + word).strip()
            if line and self.width(trial) > measure:
                lines.append(line)
                line = word
            else:
                line = trial
        if line:
            lines.append(line)
        return lines

    def outline(self, name):
        """One glyph's path, in font units, cached — see draw()."""
        if name not in self._outlines:
            ops = []
            pen = PDFPen(self.glyph_set, ops, 1.0, 0.0, 0.0)
            self.glyph_set[name].draw(pen)
            self._outlines[name] = "\n".join(ops)
        return self._outlines[name]

    def draw(self, text, x, y, out):
        """Place a shaped line, one XObject reference per glyph.

        Writing each glyph's outline inline at every occurrence produced a
        26 MB file for 34 pages — the same ka drawn from scratch a few
        thousand times. Defining every glyph once as a Form XObject and
        referencing it turns each placement into about forty bytes.
        """
        scale = self.size / self.upm
        pen_x = 0
        for info, pos in self.shape(text):
            name = self.order[info.codepoint]
            if self.outline(name):                    # skip blanks entirely
                self.used.add(name)
                gx = x + (pen_x + pos.x_offset) * scale
                gy = y + pos.y_offset * scale
                out.append(f"q {scale:.5f} 0 0 {scale:.5f} {gx:.2f} {gy:.2f} "
                           f"cm /{self.tag(name)} Do Q")
            pen_x += pos.x_advance
        return pen_x * scale

    def tag(self, name):
        """A short, valid PDF resource name for a glyph."""
        if name not in self._tags:
            self._tags[name] = f"G{len(self._tags)}"
        return self._tags[name]


def load_book(path):
    """Read the payload out of web/data/book.js without importing JS."""
    import json
    text = Path(path).read_text(encoding="utf-8")
    start = text.index("window.BOOK = ") + len("window.BOOK = ")
    end = text.rindex("}());")
    return json.loads(text[start:end].rstrip().rstrip(";"))


def build_pdf(book, setter, page, margin, leading, out_path, limit=None):
    width, height = page
    measure = width - 2 * margin
    body = setter.size * leading

    pages, stream, y = [], [], height - margin
    sheets = book["pages"][:limit] if limit else book["pages"]

    def flush():
        if stream:
            pages.append("\n".join(stream))

    for number, paragraphs in enumerate(sheets, 1):
        stream, y = ["0 g"], height - margin
        for para in paragraphs:
            for line in setter.wrap(para, measure):
                if y < margin + body:
                    flush()
                    stream, y = ["0 g"], height - margin
                setter.draw(line, margin, y, stream)
                y -= body
            y -= body * 0.35
        # folio, drawn in the same font as the body
        folio = f"{book['title']} · {number}"
        saved, setter.size = setter.size, setter.size * 0.55
        stream.append("0.45 g")
        setter.draw(folio, (width - setter.width(folio)) / 2,
                    margin * 0.55, stream)
        setter.size = saved
        flush()

    return write_pdf(pages, page, out_path, setter)


def write_pdf(page_streams, page, out_path, setter):
    """A minimal PDF 1.7 writer: one Form XObject per glyph, then references."""
    width, height = page
    objects = []           # 1-based; objects[i] is object i+1

    def add(body):
        objects.append(body)
        return len(objects)

    kids, page_ids = [], []
    root_id = 1            # reserved: catalog
    pages_id = 2           # reserved: page tree
    objects.append(b"")    # placeholder 1
    objects.append(b"")    # placeholder 2

    # every glyph the book actually used, defined once
    resources = []
    for name in sorted(setter.used):
        path = setter.outline(name) + "\nf"
        packed = zlib.compress(path.encode("ascii"), 9)
        gid = add(b"<< /Type /XObject /Subtype /Form /FormType 1 "
                  b"/BBox [-2000 -2000 4000 4000] /Resources << >> "
                  b"/Length %d /Filter /FlateDecode >>\nstream\n%s\nendstream"
                  % (len(packed), packed))
        resources.append(b"/%s %d 0 R" % (setter.tag(name).encode(), gid))
    res = (b"<< /XObject << %s >> >>" % b" ".join(resources)) if resources \
        else b"<< >>"
    res_id = add(res)

    for content in page_streams:
        raw = content.encode("ascii", "strict")
        packed = zlib.compress(raw, 9)
        sid = add(b"<< /Length %d /Filter /FlateDecode >>\nstream\n%s\nendstream"
                  % (len(packed), packed))
        pid = add(b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.2f %.2f] "
                  b"/Resources %d 0 R /Contents %d 0 R >>"
                  % (pages_id, width, height, res_id, sid))
        page_ids.append(pid)
        kids.append(b"%d 0 R" % pid)

    objects[root_id - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id
    objects[pages_id - 1] = (b"<< /Type /Pages /Count %d /Kids [%s] >>"
                             % (len(page_ids), b" ".join(kids)))

    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += b"%010d 00000 n \n" % off
    out += (b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objects) + 1, root_id, xref))

    Path(out_path).write_bytes(out)
    return len(page_ids), len(out)


def main():
    ap = argparse.ArgumentParser(
        description="Typeset the book as a PDF in a generated font.")
    ap.add_argument("--font", type=Path, default=DEFAULT_FONT)
    ap.add_argument("--book", type=Path, default=DEFAULT_BOOK)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--size", type=float, default=13.0, help="type size in pt")
    ap.add_argument("--leading", type=float, default=2.0, help="× the size")
    ap.add_argument("--margin", type=float, default=54.0, help="pt")
    ap.add_argument("--page", choices=sorted(PAGES), default="A5")
    ap.add_argument("--pages", type=int, default=None,
                    help="only the first N pages of the source")
    args = ap.parse_args()
    repo_root("mgs-pdf")   # renders the book data generated into web/data/

    if not args.font.is_file():
        sys.exit(f"font not found: {args.font}")
    if not args.book.is_file():
        sys.exit(f"book data not found: {args.book} — run make_book.py first")

    book = load_book(args.book)
    setter = Typesetter(args.font, args.size)
    count, size = build_pdf(book, setter, PAGES[args.page], args.margin,
                            args.leading, args.out, args.pages)
    print(f"{args.out}: {count} pages, {size / 1024:.0f} KB")
    print(f"  {book['title']} — {book['author']}")
    print(f"  set in {setter.family} at {args.size}pt on {args.page}")
    print("  every glyph drawn as vector outlines: no font embedded, no "
          "shaping needed in the reader")


if __name__ == "__main__":
    main()
