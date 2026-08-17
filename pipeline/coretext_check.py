#!/usr/bin/env python3
"""Diff CoreText's shaping against HarfBuzz's, cluster by cluster.

CI shapes with HarfBuzz — the engine Android, Chrome, Linux and
LibreOffice use. Apple platforms shape with **CoreText**, and the two can
disagree: a rule that works everywhere else can silently misfire on a Mac
or an iPhone. Issue #14 asks people to check that by hand. On macOS it
needs no hand at all.

    cd pipeline/coretext && swiftc -O CoreTextShape.swift -o coretext-shape
    python3 ../coretext_check.py ../../projects/*/MyanmarGlyphSans-Regular.ttf

For every string in the corpus this shapes with both engines and compares
the glyph sequence (names, order, count) and the relative advances. It
reports only real disagreements, so a clean run means the two engines
agree on every cluster in the corpus. The comparison itself — and the
three false-alarm classes it has to ignore — lives in `shaping_diff.py`,
shared with the Windows/DirectWrite checker.

Only runs on macOS — CoreText is an Apple framework. Everywhere else it
exits 0 with a note, so it is safe to call from a script.

    --corpus FILE   which corpus to shape (default: the spec corpus)
    --tolerance N   position slack in font units before it counts (default 12)
    --verbose       print every cluster, not just the disagreements
"""

import argparse
import platform
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHAPER = HERE / "coretext" / "coretext-shape"

sys.path.insert(0, str(HERE))
from shaping_diff import harfbuzz_runs, report  # noqa: E402
from validate_spec import FontUnderTest, load_corpus  # noqa: E402

ENGINE = "CoreText"


def coretext_runs(font_path, texts):
    """{text: [(name, x, y), ...]} straight out of CoreText."""
    if not SHAPER.exists():
        sys.exit(f"{SHAPER} not built — run:\n"
                 f"  cd {SHAPER.parent} && swiftc -O CoreTextShape.swift "
                 f"-o coretext-shape")
    out = {}
    # argv has a length limit; feed the shaper in batches
    for i in range(0, len(texts), 200):
        batch = texts[i:i + 200]
        proc = subprocess.run([str(SHAPER), str(font_path), *batch],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            sys.exit(f"coretext-shape failed: {proc.stderr.strip()}")
        for line in proc.stdout.splitlines():
            if "\t" not in line:
                continue
            text, _, run = line.partition("\t")
            glyphs = []
            for token in run.split():
                gid_name, _, pos = token.partition("@")
                _, _, name = gid_name.partition(":")
                x, _, y = pos.partition(",")
                glyphs.append((name, float(x or 0), float(y or 0)))
            out[text] = glyphs
    return out


def main():
    ap = argparse.ArgumentParser(
        description="Diff CoreText shaping against HarfBuzz.")
    ap.add_argument("font", type=Path)
    ap.add_argument("--corpus", type=Path,
                    default=HERE / "spec_corpus.txt")
    ap.add_argument("--tolerance", type=float, default=12.0)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if platform.system() != "Darwin":
        print("CoreText is an Apple framework — skipping on "
              f"{platform.system()}. (HarfBuzz coverage still applies.)")
        return 0

    cases, _ = load_corpus(args.corpus)
    texts = list(dict.fromkeys(c.text for c in cases))
    font = FontUnderTest(args.font)

    return report(ENGINE, font, texts,
                  coretext_runs(args.font, texts),
                  harfbuzz_runs(font, texts),
                  args.tolerance, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
