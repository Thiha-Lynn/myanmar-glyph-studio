#!/usr/bin/env python3
"""Diff DirectWrite's shaping against HarfBuzz's, cluster by cluster.

CI shapes with HarfBuzz — the engine Android, Chrome, Linux and
LibreOffice use. Windows shapes with **DirectWrite**: Word, Edge, Notepad,
Office, every WPF and UWP app. The two can disagree, and issue #14 asks
for a person with a Windows machine to check by hand. It turns out not to
need one — GitHub's `windows-latest` runner is a real Windows box running
the real engine, so this runs in CI on every pull request.

    cl /EHsc /O2 /std:c++17 pipeline\\directwrite\\DirectWriteShape.cpp
    python pipeline\\directwrite_check.py ^
        projects\\myanmar-glyph-sans\\MyanmarGlyphSans-Regular.ttf

For every string in the corpus this shapes with both engines and compares
the glyph sequence (names, order, count) and the relative placements,
reporting only real disagreements — the comparison, and the false alarms
it has to ignore, live in `shaping_diff.py` alongside the CoreText check.

Only runs on Windows — DirectWrite is a Windows API. Everywhere else it
exits 0 with a note, so it is safe to call from a script.

    --corpus FILE   which corpus to shape (default: the spec corpus)
    --tolerance N   position slack in font units before it counts (default 12)
    --verbose       print every cluster, not just the disagreements
"""

import argparse
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHAPER = HERE / "directwrite" / "DirectWriteShape.exe"

sys.path.insert(0, str(HERE))
from shaping_diff import harfbuzz_runs, report  # noqa: E402
from validate_spec import UPM, FontUnderTest, load_corpus  # noqa: E402

ENGINE = "DirectWrite"

# DirectWrite takes a BCP-47 locale where HarfBuzz takes a language tag;
# `my-MM` is the Burmese equivalent of the `my` these fonts are shaped with.
LOCALE = "my-MM"


def directwrite_runs(font_path, texts, glyph_order):
    """{text: [(name, x, y), ...]} straight out of DirectWrite.

    The shaper reports glyph IDs, not names — DirectWrite has no notion of
    `post` names. Mapping them through the font's own glyph order (the same
    list validate_spec uses for HarfBuzz) is what makes the two runs
    comparable name for name.
    """
    if not SHAPER.exists():
        sys.exit(f"{SHAPER} not built — run:\n"
                 f"  cl /EHsc /O2 /std:c++17 "
                 f"{SHAPER.parent / 'DirectWriteShape.cpp'}")

    # A file, not argv: the corpus runs to thousands of clusters, and it
    # keeps Myanmar text away from the console code page entirely.
    with tempfile.TemporaryDirectory() as tmp:
        corpus_file = Path(tmp) / "corpus.txt"
        corpus_file.write_text("\n".join(texts) + "\n", encoding="utf-8")
        proc = subprocess.run(
            [str(SHAPER), str(font_path), str(corpus_file), str(UPM), LOCALE],
            capture_output=True, text=True, encoding="ascii")
    if proc.returncode != 0:
        sys.exit(f"DirectWriteShape failed: {proc.stderr.strip()}")

    out = {}
    for line in proc.stdout.splitlines():
        if "\t" not in line:
            continue
        index, _, run = line.partition("\t")
        try:
            text = texts[int(index)]
        except (ValueError, IndexError):
            continue
        glyphs = []
        for token in run.split():
            gid, _, pos = token.partition("@")
            x, _, y = pos.partition(",")
            gid = int(gid)
            name = glyph_order[gid] if gid < len(glyph_order) else f"gid{gid}"
            glyphs.append((name, float(x or 0), float(y or 0)))
        out[text] = glyphs
    return out


def main():
    ap = argparse.ArgumentParser(
        description="Diff DirectWrite shaping against HarfBuzz.")
    ap.add_argument("font", type=Path)
    ap.add_argument("--corpus", type=Path,
                    default=HERE / "spec_corpus.txt")
    ap.add_argument("--tolerance", type=float, default=12.0)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if platform.system() != "Windows":
        print("DirectWrite is a Windows API — skipping on "
              f"{platform.system()}. (HarfBuzz coverage still applies.)")
        return 0

    cases, _ = load_corpus(args.corpus)
    texts = list(dict.fromkeys(c.text for c in cases))
    font = FontUnderTest(args.font)

    return report(ENGINE, font, texts,
                  directwrite_runs(args.font, texts, font.glyph_order),
                  harfbuzz_runs(font, texts),
                  args.tolerance, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
