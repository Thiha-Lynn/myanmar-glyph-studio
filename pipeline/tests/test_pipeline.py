"""Unit tests for json_to_ufo.py — the project-JSON → UFO conversion.

Fast (no fontmake compile): they build UFOs in a temp dir and inspect
glyphs, anchors, metrics, features and production names directly.

    cd pipeline && python3 -m pytest tests/ -q
"""

import sys
from pathlib import Path

import pytest
import ufoLib2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import json_to_ufo  # noqa: E402


def build(tmp_path, glyphs):
    project = {
        "format": "mm-glyph-studio",
        "version": 1,
        "meta": {"fontName": "Test", "styleName": "Regular", "author": "CI"},
        "glyphs": glyphs,
    }
    ufo_path, drawn = json_to_ufo.build_ufo(project, tmp_path)
    return ufoLib2.Font.open(ufo_path), set(drawn)


def stroke(points, width=60):
    return {"width": width, "points": points}


def anchors_of(font, name):
    return {a.name: (a.x, a.y) for a in font[name].anchors}


def ink_x_min(font, name):
    return min(p.x for c in font[name].contours for p in c.points)


BOX = stroke([[100, 0], [100, 550], [500, 550], [500, 0]])


def test_base_gets_top_and_bottom_anchors(tmp_path):
    font, _ = build(tmp_path, {"ka-myanmar": {"advance": None, "strokes": [BOX]}})
    a = anchors_of(font, "ka-myanmar")
    assert set(a) == {"top", "bottom", "stack"}
    assert a["top"][1] >= 590        # above the body line + clearance
    assert a["bottom"][1] <= -40
    assert font["ka-myanmar"].width > 550


def test_manual_anchor_overrides_auto(tmp_path):
    font, _ = build(tmp_path, {
        "i-myanmar": {"advance": None,
                      "strokes": [stroke([[200, 650], [400, 650]], 40)],
                      "anchors": {"_top": [321, 617]}},
    })
    a = anchors_of(font, "i-myanmar")
    assert a["_top"] == (321, 617)   # dragged position wins verbatim
    assert "top" in a                # stacking anchor still present (mkmk)


def test_marks_carry_stacking_anchor(tmp_path):
    font, _ = build(tmp_path, {
        "u-myanmar": {"advance": None,
                      "strokes": [stroke([[250, -150], [350, -150]], 40)]},
    })
    a = anchors_of(font, "u-myanmar")
    assert set(a) == {"_bottom", "bottom"}
    assert font["u-myanmar"].width == 0


def test_marks_are_zero_width_even_if_the_project_says_otherwise(tmp_path):
    # a non-spacing mark with an advance would double-space every syllable
    font, _ = build(tmp_path, {
        "u-myanmar": {"advance": 420,
                      "strokes": [stroke([[250, -150], [350, -150]], 40)]},
        "ka-myanmar.sub": {"advance": 500, "strokes": [BOX]},
    })
    assert font["u-myanmar"].width == 0
    assert font["ka-myanmar.sub"].width == 0


def test_spacing_sign_ink_left_aligned_when_auto(tmp_path):
    # aa (U+102C, Mc) sketched beside the ◌ carrier at x≈600
    font, _ = build(tmp_path, {
        "aa-myanmar": {"advance": None,
                       "strokes": [stroke([[600, 100], [600, 500]])]},
    })
    assert ink_x_min(font, "aa-myanmar") == pytest.approx(60, abs=2)
    assert font["aa-myanmar"].width < 300
    assert anchors_of(font, "aa-myanmar") == {}


def test_spacing_sign_untouched_when_advance_explicit(tmp_path):
    font, _ = build(tmp_path, {
        "aa-myanmar": {"advance": 411,
                       "strokes": [stroke([[600, 100], [600, 500]])]},
    })
    assert font["aa-myanmar"].width == 411
    assert ink_x_min(font, "aa-myanmar") > 500  # ink kept where drawn


def test_wrap_sign_keeps_coordinates_and_a_small_advance(tmp_path):
    """Medial ra wraps around its base: the advance must clear the wrap's
    left stem so the base lands INSIDE the wrap — zero would stack the base
    on top of the stem, and a full-width advance would push it outside."""
    font, _ = build(tmp_path, {
        "medialRa-myanmar": {"advance": None,
                             "strokes": [stroke([[0, 600], [700, 600],
                                                 [700, -100]], 50)]},
    })
    width = font["medialRa-myanmar"].width
    assert 0 < width < 400          # small, but not zero
    assert ink_x_min(font, "medialRa-myanmar") < 0  # not re-aligned


def test_wrap_sign_honours_a_stored_advance(tmp_path):
    font, _ = build(tmp_path, {
        "medialRa-myanmar": {"advance": 168,
                             "strokes": [stroke([[94, 600], [654, 600],
                                                 [654, -100]], 50)]},
    })
    assert font["medialRa-myanmar"].width == 168


def test_virama_ink_ignored_and_synthesized_empty(tmp_path):
    font, drawn = build(tmp_path, {
        "ta-myanmar": {"advance": None, "strokes": [BOX]},
        "ta-myanmar.sub": {"advance": None,
                           "strokes": [stroke([[200, -100], [400, -100]])]},
        "virama-myanmar": {"advance": None,
                           "strokes": [stroke([[100, -200], [300, -200]])]},
    })
    v = font["virama-myanmar"]
    assert v.width == 0
    assert len(v.contours) == 0      # sketched ink discarded
    assert v.unicode == 0x1039
    assert "feature blwf" in font.features.text


def test_kinzi_alone_synthesizes_virama_for_rphf(tmp_path):
    font, drawn = build(tmp_path, {
        "nga-myanmar": {"advance": None, "strokes": [BOX]},
        "asat-myanmar": {"advance": None,
                         "strokes": [stroke([[300, 640], [420, 640]], 30)]},
        "kinzi-myanmar": {"advance": None,
                          "strokes": [stroke([[250, 700], [400, 700]], 30)]},
    })
    assert "virama-myanmar" in {g.name for g in font}
    assert "feature rphf" in font.features.text


def test_no_empty_blws_block(tmp_path):
    # alt vowel + stacks drawn, but plain u missing → no rule, no empty block
    font, _ = build(tmp_path, {
        "ta-myanmar": {"advance": None, "strokes": [BOX]},
        "ta-myanmar.sub": {"advance": None,
                           "strokes": [stroke([[200, -100], [400, -100]])]},
        "u-myanmar.alt": {"advance": None,
                          "strokes": [stroke([[250, -120], [300, -120]], 30)]},
    })
    assert "feature blws" not in font.features.text


def test_blws_present_when_pair_complete(tmp_path):
    font, _ = build(tmp_path, {
        "ta-myanmar": {"advance": None, "strokes": [BOX]},
        "ta-myanmar.sub": {"advance": None,
                           "strokes": [stroke([[200, -100], [400, -100]])]},
        "u-myanmar": {"advance": None,
                      "strokes": [stroke([[250, -150], [350, -150]], 40)]},
        "u-myanmar.alt": {"advance": None,
                          "strokes": [stroke([[250, -120], [300, -120]], 30)]},
    })
    assert "feature blws" in font.features.text
    assert "sub @DESC_U u-myanmar' by u-myanmar.alt;" in font.features.text


def test_fill_stroke_contour_passes_through_verbatim(tmp_path):
    contour = [[100, 0], [500, 0], [500, 400], [100, 400]]
    font, _ = build(tmp_path, {
        "wa-myanmar": {"advance": None,
                       "strokes": [{"fill": True, "points": contour}]},
    })
    pts = [(p.x, p.y) for p in font["wa-myanmar"].contours[0].points]
    # every corner is square, so all four survive as on-curve points
    assert sorted(pts) == sorted(tuple(p) for p in contour)
    assert all(p.type == "line" for p in font["wa-myanmar"].contours[0].points)


def test_dotted_circle_is_mark_base(tmp_path):
    font, _ = build(tmp_path, {
        "uni25CC": {"advance": None,
                    "strokes": [stroke([[250, 275]], 30)]},
    })
    assert set(anchors_of(font, "uni25CC")) == {"top", "bottom", "stack"}


def test_extension_blocks_classified(tmp_path):
    font, _ = build(tmp_path, {
        # Ext-A Khamti KA: letter → base anchors
        "uniAA60": {"advance": None, "strokes": [BOX]},
        # Ext-B Shan SAW (Mn above) → attaching + stacking anchor
        "uniA9E5": {"advance": None,
                    "strokes": [stroke([[300, 700], [420, 700]], 40)]},
    })
    assert set(anchors_of(font, "uniAA60")) == {"top", "bottom", "stack"}
    assert set(anchors_of(font, "uniA9E5")) == {"_top", "top"}
    assert font["uniA9E5"].width == 0


def test_production_names_are_valid_postscript(tmp_path):
    font, _ = build(tmp_path, {
        "ka-myanmar": {"advance": None, "strokes": [BOX]},
        "ta-myanmar.sub": {"advance": None,
                           "strokes": [stroke([[200, -100], [400, -100]])]},
        "kinzi-myanmar": {"advance": None,
                          "strokes": [stroke([[250, 700], [400, 700]], 30)]},
        "nga-myanmar": {"advance": None, "strokes": [BOX]},
        "asat-myanmar": {"advance": None,
                         "strokes": [stroke([[300, 640], [420, 640]], 30)]},
    })
    ps = font.lib["public.postscriptNames"]
    assert ps["ka-myanmar"] == "uni1000"
    assert ps["ta-myanmar.sub"] == "uni1010.sub"
    assert ps["kinzi-myanmar"] == "uni1004103A1039"
    assert ps["nbspace"] == "uni00A0"


def test_notdef_visible_and_whitespace_present(tmp_path):
    font, _ = build(tmp_path, {"ka-myanmar": {"advance": None, "strokes": [BOX]}})
    assert len(font[".notdef"].contours) == 2   # hollow box
    assert font["space"].unicode == 0x20
    assert font["nbspace"].unicode == 0xA0


def test_empty_and_unknown_glyphs_skipped(tmp_path):
    font, drawn = build(tmp_path, {
        "ka-myanmar": {"advance": None, "strokes": []},
        "kha-myanmar": {"advance": None, "strokes": [BOX]},
    })
    assert drawn == {"kha-myanmar"}
    assert "ka-myanmar" not in {g.name for g in font}


# ---------------------------------------------------------------------------
# curves, GDEF, kerning and weight masters
# ---------------------------------------------------------------------------

CURVE = stroke([[100, 0], [140, 300], [260, 460], [420, 380], [470, 120],
                [380, 20], [200, 30]], 60)


def test_outlines_are_curves_not_polygon_soup(tmp_path):
    font, _ = build(tmp_path, {"ka-myanmar": {"advance": None,
                                              "strokes": [CURVE]}})
    types = [p.type for c in font["ka-myanmar"].contours for p in c.points]
    assert "curve" in types                       # real cubic segments
    assert types.count(None) > 0                  # with off-curve controls


def test_decimation_compresses_a_hand_drawn_curve(tmp_path):
    """The circle a Myanmar letter is built on should cost a few segments,
    not the hundreds of points a drawn stroke arrives with."""
    import math
    ring = stroke([[500 + 220 * math.cos(i / 200 * 2 * math.pi),
                    300 + 220 * math.sin(i / 200 * 2 * math.pi)]
                   for i in range(201)], 55)
    font, _ = build(tmp_path, {"wa-myanmar": {"advance": None,
                                              "strokes": [ring]}})
    types = [p.type for c in font["wa-myanmar"].contours for p in c.points]
    segments = sum(1 for t in types if t is not None)
    raw = sum(len(p) for p in json_to_ufo.polygons_for({"strokes": [ring]}))
    assert raw > 400                       # a dense hand-drawn ring
    assert segments < raw / 5              # …becomes a handful of curves


def test_straight_lines_stay_straight(tmp_path):
    square = {"fill": True,
              "points": [[100, 0], [400, 0], [400, 300], [100, 300]]}
    font, _ = build(tmp_path, {"ka-myanmar": {"advance": None,
                                              "strokes": [square]}})
    pts = font["ka-myanmar"].contours[0].points
    assert all(p.type == "line" for p in pts)
    assert len(pts) == 4


def test_small_shapes_keep_their_detail(tmp_path):
    """A tone dot must not be flattened by the same tolerance as a letter."""
    dot = stroke([[300, 300]], 30)          # single point -> circle
    font, _ = build(tmp_path, {"dotBelow-myanmar": {"advance": None,
                                                    "strokes": [dot]}})
    pts = [p for c in font["dotBelow-myanmar"].contours for p in c.points]
    assert len(pts) >= 8                    # still round, not a triangle


def test_gdef_categories_split_marks_from_spacing_signs(tmp_path):
    font, _ = build(tmp_path, {
        "ka-myanmar": {"advance": None, "strokes": [BOX]},
        "i-myanmar": {"advance": None,
                      "strokes": [stroke([[200, 650], [400, 650]], 40)]},
        "aa-myanmar": {"advance": None,
                       "strokes": [stroke([[600, 100], [600, 500]])]},
    })
    cats = font.lib["public.openTypeCategories"]
    assert cats["ka-myanmar"] == "base"
    assert cats["i-myanmar"] == "mark"
    assert cats["aa-myanmar"] == "base"     # Mc spacing sign is NOT a mark


def test_kerning_and_groups_reach_the_ufo(tmp_path):
    project = {
        "format": "mm-glyph-studio", "version": 1,
        "meta": {"fontName": "Test"},
        "glyphs": {
            "ka-myanmar": {"advance": None, "strokes": [BOX]},
            "ta-myanmar": {"advance": None, "strokes": [BOX]},
        },
        "groups": {"public.kern1.round": ["ka-myanmar"]},
        "kerning": {"ka-myanmar ta-myanmar": -25},
    }
    ufo_path, _ = json_to_ufo.build_ufo(project, tmp_path)
    font = ufoLib2.Font.open(ufo_path)
    assert font.kerning[("ka-myanmar", "ta-myanmar")] == -25
    assert font.groups["public.kern1.round"] == ["ka-myanmar"]


def test_weight_masters_are_interpolation_compatible(tmp_path):
    project = {
        "format": "mm-glyph-studio", "version": 1,
        "meta": {"fontName": "Test"},
        "glyphs": {
            "ka-myanmar": {"advance": None, "strokes": [CURVE]},
            "i-myanmar": {"advance": None,
                          "strokes": [stroke([[200, 650], [400, 650]], 40)]},
        },
    }
    shapes, widths = {}, {}
    for style, scale, weight in (("Light", 0.8, 300), ("Regular", 1.0, 400),
                                 ("Bold", 1.5, 700)):
        out = tmp_path / style
        ufo_path, _ = json_to_ufo.build_ufo(project, out, width_scale=scale,
                                            style_name=style,
                                            weight_class=weight)
        font = ufoLib2.Font.open(ufo_path)
        assert font.info.openTypeOS2WeightClass == weight
        for name in ("ka-myanmar", "i-myanmar"):
            g = font[name]
            shapes.setdefault(name, set()).add(
                tuple((len(c.points), tuple(p.type for p in c.points))
                      for c in g.contours))
        xs = [p.x for c in font["ka-myanmar"].contours for p in c.points]
        widths[style] = max(xs) - min(xs)

    for name, sigs in shapes.items():
        assert len(sigs) == 1, f"{name} is not interpolatable across weights"
    # and the pen really did get heavier
    assert widths["Light"] < widths["Regular"] < widths["Bold"]


def test_pen_scale_matches_weight_class():
    from make_variable import pen_scale, style_for
    assert pen_scale(400) == 1.0
    assert pen_scale(300) < 1.0 < pen_scale(700)
    assert style_for(700) == "Bold"


def test_inked_spacing_glyph_never_stays_zero_width(tmp_path):
    """Some source fonts leave modifier letters at advance 0; a glyph with
    ink must still move the pen or it overprints its neighbour."""
    font, _ = build(tmp_path, {
        "uniAA70": {"advance": 0, "strokes": [BOX]},   # Lm modifier letter
    })
    assert font["uniAA70"].width > 0


def test_ink_left_of_the_origin_is_normalised(tmp_path):
    """A spacing glyph parked in negative space would otherwise derive a
    negative advance and get clamped to zero."""
    font, _ = build(tmp_path, {
        "uniAA70": {"advance": 0,
                    "strokes": [stroke([[-460, 560], [-100, 860]], 40)]},
    })
    assert font["uniAA70"].width > 0
    assert ink_x_min(font, "uniAA70") >= 0
