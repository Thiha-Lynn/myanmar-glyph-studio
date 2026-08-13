#!/usr/bin/env python3
"""Collect community fonts into the gallery's static data directory.

Scans projects/*/ for a .glyphstudio.json (project metadata) and a built
TTF next to it, copies the TTF (and proof.png when present) into
web/gallery-data/<project>/ and writes web/gallery-data/fonts.json — the
manifest web/gallery.html renders with live previews.

Run it locally after building a font, or let CI do it (the Pages workflow
runs it before deploying web/):

    python3 pipeline/make_gallery.py            # repo-root relative
    python3 pipeline/make_gallery.py out-dir    # explicit target
"""

import json
import shutil
import sys
from pathlib import Path

try:
    from fontTools.ttLib import TTFont
except ImportError:  # metadata falls back to the project JSON
    TTFont = None

ROOT = Path(__file__).resolve().parent.parent


def font_record(project_dir, out_dir):
    jsons = sorted(project_dir.glob("*.glyphstudio.json"))
    ttfs = sorted(project_dir.glob("*.ttf"))
    if not jsons or not ttfs:
        return None
    project = json.loads(jsons[0].read_text(encoding="utf-8"))
    meta = project.get("meta", {})
    ttf = ttfs[0]

    drawn = sum(1 for g in project.get("glyphs", {}).values()
                if g.get("strokes"))

    family = meta.get("fontName", project_dir.name)
    style = meta.get("styleName", "Regular")
    glyph_count = None
    if TTFont is not None:
        try:
            tt = TTFont(ttf, lazy=True)
            glyph_count = tt["maxp"].numGlyphs
            name = tt["name"].getDebugName(1)
            if name:
                family = name
            tt.close()
        except Exception:
            pass

    dest = out_dir / project_dir.name
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ttf, dest / ttf.name)
    proof = project_dir / "proof.png"
    has_proof = proof.is_file()
    if has_proof:
        shutil.copy2(proof, dest / "proof.png")

    return {
        "dir": project_dir.name,
        "family": family,
        "style": style,
        "author": meta.get("author", ""),
        "license": meta.get("license", "OFL-1.1"),
        "file": f"{project_dir.name}/{ttf.name}",
        "proof": f"{project_dir.name}/proof.png" if has_proof else None,
        "drawnGlyphs": drawn,
        "glyphs": glyph_count,
        "bytes": ttf.stat().st_size,
    }


def main():
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        ROOT / "web" / "gallery-data")
    out_dir.mkdir(parents=True, exist_ok=True)

    fonts = []
    for project_dir in sorted((ROOT / "projects").iterdir()):
        if not project_dir.is_dir():
            continue
        rec = font_record(project_dir, out_dir)
        if rec:
            fonts.append(rec)

    manifest = {"fonts": fonts}
    (out_dir / "fonts.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"Wrote {out_dir / 'fonts.json'}: {len(fonts)} font(s)")


if __name__ == "__main__":
    main()
