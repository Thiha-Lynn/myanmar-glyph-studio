"""make_pirate.py — the weathering stage behind Kawthaung Corsair.

These tests run on a tiny synthetic project (no font compile), so they
guard the invariants cheaply: determinism, the fill-contour output
contract, knuckles-on-bases-only, the quiet-mark ceiling, and that the
two drawn ornaments actually ship ink.
"""

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import make_pirate as mp  # noqa: E402


def _tiny_project():
    """One base with an L-shaped open stroke, one small top mark."""
    return {
        "format": "mm-glyph-studio",
        "version": 1,
        "meta": {"fontName": "T", "styleName": "Regular", "pen": 2},
        "glyphs": {
            "ka-myanmar": {
                "advance": 600,
                "strokes": [{"width": 80,
                             "points": [[100, 500], [100, 0], [500, 0]]}],
            },
            "asat-myanmar": {
                "advance": 0,
                "strokes": [{"width": 40,
                             "points": [[0, 820], [80, 880], [160, 820]]}],
            },
        },
    }


def _bounds(record):
    xs = [p[0] for s in record["strokes"] for p in s["points"]]
    ys = [p[1] for s in record["strokes"] for p in s["points"]]
    return min(xs), min(ys), max(xs), max(ys)


def test_deterministic():
    a = mp.build(_tiny_project())
    b = mp.build(copy.deepcopy(_tiny_project()))
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_output_is_fill_contours_and_single_weight():
    out = mp.build(_tiny_project(), width=1.06, y=0.88)
    assert out["version"] == 1
    assert out["meta"]["variable"] is False
    for name, record in out["glyphs"].items():
        for stroke in record["strokes"]:
            assert stroke.get("fill") is True, (name, stroke.keys())
            assert len(stroke["points"]) >= 3


def test_base_terminals_grow_knuckles():
    """The foot of the L (an open end at y=0) must bulge laterally past
    the plain stroke expansion: cap reach is half-width 40, a foot
    knuckle reaches (spread 0.80 + knob 0.95) * half ≈ 70."""
    out = mp.build(_tiny_project())
    x0, y0, x1, y1 = _bounds(out["glyphs"]["ka-myanmar"])
    assert y0 < -55, f"foot knuckle missing: ink bottom {y0}"


def test_quiet_marks_capped_and_unknuckled():
    """asat weathers gently and never rises past its nominal ceiling —
    the class of regression that put 289 bounds warnings on the first
    full build (knuckled asat at y=935 against the 900 ascender)."""
    assert mp._is_quiet("asat-myanmar")
    assert mp._is_quiet("ka-myanmar.sub")
    assert not mp._is_quiet("ka-myanmar")
    out = mp.build(_tiny_project())
    x0, y0, x1, y1 = _bounds(out["glyphs"]["asat-myanmar"])
    # nominal ceiling: skeleton top 880 + half-width 20 = 900
    assert y1 <= 900, f"quiet mark rose to {y1}"


def test_no_winding_cancellation():
    """Knuckle circles must union INTO the stroke, not cancel against
    it (the first build's white-holed knuckles): the silhouette of a
    single stroke plus knuckles is a handful of same-sign contours."""
    out = mp.build(_tiny_project())
    polys = [s["points"] for s in out["glyphs"]["ka-myanmar"]["strokes"]]
    areas = [mp._signed_area(p) for p in polys]
    largest = max(abs(a) for a in areas)
    assert abs(sum(areas)) > largest * 0.9, "opposite windings cancelled ink"


def test_ornaments_ship_ink():
    out = mp.build(_tiny_project())
    skull = out["glyphs"]["uni2620"]
    anchor = out["glyphs"]["uni2693"]
    # skull: silhouette plus at least eye/nose/teeth holes
    assert len(skull["strokes"]) >= 5
    # anchor: silhouette plus the ring hole
    assert len(anchor["strokes"]) >= 2
    for record in (skull, anchor):
        assert record["advance"] == mp.ORNAMENT_ADVANCE
        x0, y0, x1, y1 = _bounds(record)
        assert x1 - x0 > 500 and y1 - y0 > 500
        assert y0 > -600 and y1 < 900


def test_affine_scales_points_and_advance_together():
    project = _tiny_project()
    out = mp.build(project, width=2.0, y=0.5)
    ka = out["glyphs"]["ka-myanmar"]
    assert abs(ka["advance"] - 1200) < 1e-6
    x0, y0, x1, y1 = _bounds(ka)
    assert x1 > 900          # 500 * 2 + stroke radius
    assert y1 < 350          # 500 * 0.5 + radius + wave
