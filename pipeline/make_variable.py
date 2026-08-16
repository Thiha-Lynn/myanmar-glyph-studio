#!/usr/bin/env python3
"""Build a WEIGHT-VARIABLE font from a single Glyph Studio drawing.

Because a sketch is stored as centre-lines plus a pen width, a whole weight
axis comes out of one drawing: thin the pen for Light, fatten it for Bold.
The point decimation in json_to_ufo deliberately keys off the unscaled
width, so every master has the identical point count and contour order and
the masters interpolate cleanly.

    python3 make_variable.py MyFont.glyphstudio.json build/
    python3 make_variable.py MyFont.glyphstudio.json build/ --weights 300,400,900
    python3 make_variable.py MyFont.glyphstudio.json build/ --no-compile

Writes one UFO per master plus a .designspace, then (unless --no-compile)
runs fontmake to produce a variable TTF with a `wght` axis, plus one static
TTF per master.

Pen scale per weight is derived from the weight class so that 400 is
exactly the drawing as sketched:  scale = (wght / 400) ** 0.62
— the exponent keeps Light readable and Black from closing its counters.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

try:
    from fontTools.designspaceLib import (AxisDescriptor, AxisLabelDescriptor,
                                          DesignSpaceDocument,
                                          InstanceDescriptor, SourceDescriptor)
except ImportError:
    sys.exit("fontTools is required:  pip install -r requirements.txt")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import json_to_ufo  # noqa: E402  (path shim above: see module docstring)
from json_to_ufo import RIBBI_STYLES  # noqa: E402

# weight class -> style name for the usual stops
STYLE_NAMES = {
    100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular",
    500: "Medium", 600: "SemiBold", 700: "Bold", 800: "ExtraBold",
    900: "Black",
}
DEFAULT_WEIGHTS = [300, 400, 700]


def pen_scale(weight):
    """Pen multiplier for a weight class; 400 is the drawing as sketched."""
    return round((weight / 400.0) ** 0.62, 4)


def style_for(weight):
    return STYLE_NAMES.get(weight, f"Weight{weight}")


def build(project_path, out_dir, weights, compile_font=True):
    project = json.loads(project_path.read_text(encoding="utf-8"))
    if project.get("format") != "mm-glyph-studio":
        sys.exit("Not a Glyph Studio project file")

    weights = sorted(set(weights))
    if 400 not in weights:
        sys.exit("The weight list must include 400 (the drawing as sketched)")
    family = project.get("meta", {}).get("fontName", "MyMyanmarFont")
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = DesignSpaceDocument()
    doc.elidedFallbackName = "Regular"
    axis = AxisDescriptor()
    axis.name, axis.tag = "Weight", "wght"
    axis.minimum, axis.maximum, axis.default = min(weights), max(weights), 400
    axis.map = [(w, w) for w in weights]
    # STAT labels, one per stop, so the variable font's style linking
    # matches its fvar instances (Regular is the elided default)
    axis.axisLabels = [
        AxisLabelDescriptor(name=style_for(w), userValue=w,
                            elidable=(w == 400))
        for w in weights
    ]
    doc.addAxis(axis)

    counts = {}
    for weight in weights:
        style = style_for(weight)
        scale = pen_scale(weight)
        ufo_path, drawn = json_to_ufo.build_ufo(
            project, out_dir, width_scale=scale, style_name=style,
            weight_class=weight)
        counts[style] = len(drawn)
        print(f"  {style:<12} wght {weight:<4} pen x{scale:<6} "
              f"{len(drawn)} glyphs  ->  {ufo_path.name}")

        source = SourceDescriptor()
        source.path = str(ufo_path)
        source.filename = ufo_path.name
        source.familyName = family
        source.styleName = style
        source.location = {"Weight": weight}
        if weight == 400:
            source.copyInfo = True
        doc.addSource(source)

        # named instances need their full legacy naming too, or the
        # variable font ships fvar entries with empty name records
        instance = InstanceDescriptor()
        instance.name = f"{family} {style}"
        instance.familyName = family
        instance.styleName = style
        instance.postScriptFontName = f"{family.replace(' ', '')}-{style}"
        if style in RIBBI_STYLES:
            instance.styleMapFamilyName = family
            instance.styleMapStyleName = style.lower()
        else:
            instance.styleMapFamilyName = f"{family} {style}"
            instance.styleMapStyleName = "regular"
        instance.location = {"Weight": weight}
        doc.addInstance(instance)

    if len(set(counts.values())) != 1:
        sys.exit(f"Masters disagree on glyph count ({counts}) — cannot "
                 "interpolate. This is a bug in the width scaling.")

    ds_path = out_dir / f"{family.replace(' ', '')}.designspace"
    doc.write(ds_path)
    print(f"Wrote {ds_path}")

    if not compile_font:
        print(f"\nNext:  fontmake -m {ds_path} -o variable ttf "
              f"--output-dir {out_dir}")
        return ds_path

    # variable and static are separate fontmake runs: asking for both in one
    # invocation trips an option-passing bug in fontmake's static path
    print("\nCompiling with fontmake …")
    for output in ("variable", "ttf"):
        subprocess.run(
            [sys.executable, "-m", "fontmake", "-m", str(ds_path),
             "-o", output, "--output-dir", str(out_dir)],
            check=True)
    for ttf in sorted(out_dir.rglob("*.ttf")):
        print(f"  built {ttf}")
    return ds_path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", type=Path)
    ap.add_argument("out_dir", type=Path, nargs="?", default=Path("build"))
    ap.add_argument("--weights", default=",".join(str(w) for w in DEFAULT_WEIGHTS),
                    help="comma-separated weight classes, must include 400")
    ap.add_argument("--no-compile", action="store_true",
                    help="write UFOs + designspace only")
    args = ap.parse_args()

    try:
        weights = [int(w) for w in args.weights.split(",") if w.strip()]
    except ValueError:
        sys.exit("--weights takes numbers, e.g. 300,400,700")
    build(args.project, args.out_dir, weights, not args.no_compile)


if __name__ == "__main__":
    main()
