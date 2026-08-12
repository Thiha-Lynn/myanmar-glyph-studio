#!/usr/bin/env bash
# Build a shaping-capable TTF from a Glyph Studio project file.
#
#   ./build.sh path/to/MyFont.glyphstudio.json [output-dir]
#
set -euo pipefail

PROJECT="${1:?usage: ./build.sh <project.glyphstudio.json> [output-dir]}"
OUT="${2:-build}"

python3 "$(dirname "$0")/json_to_ufo.py" "$PROJECT" "$OUT"

UFO=$(ls -d "$OUT"/*.ufo | head -1)
fontmake -u "$UFO" -o ttf --output-dir "$OUT"

echo
echo "Done. TTF written to $OUT/"
echo "Test the shaping with HarfBuzz, e.g.:"
echo "  hb-view $OUT/*.ttf 'ကျွန်ုပ်တို့ မြန်မာစာ' --output-file proof.png"
