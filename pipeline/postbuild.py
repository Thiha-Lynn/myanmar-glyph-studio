#!/usr/bin/env python3
"""Post-build TTF fixes applied after fontmake.

Adds the smart-dropout `prep` program (PUSHW 511, SCANCTRL, PUSHB 4,
SCANTYPE) that unhinted fonts need for clean rasterization on Windows
GDI/ClearType — the same fix gftools-fix-nonhinting applies, without the
extra dependency.

    python3 postbuild.py font.ttf [more.ttf ...]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repo_paths import help_if_asked  # noqa: E402

from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables.ttProgram import Program

SMART_DROPOUT = bytes([0xB8, 0x01, 0xFF, 0x85, 0xB0, 0x04, 0x8D])


def fix(path):
    font = TTFont(path)
    changed = False
    if "prep" not in font:
        prep = newTable("prep")
        prep.program = Program()
        prep.program.fromBytecode(SMART_DROPOUT)
        font["prep"] = prep
        changed = True
    if changed:
        font.save(path)
    print(f"{path}: {'smart-dropout prep added' if changed else 'already ok'}")


def main():
    help_if_asked(__doc__)
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for path in sys.argv[1:]:
        fix(path)


if __name__ == "__main__":
    main()
