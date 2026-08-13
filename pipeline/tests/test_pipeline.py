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
    assert set(a) == {"top", "bottom"}
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


def test_wrap_sign_keeps_coordinates_and_zero_advance(tmp_path):
    font, _ = build(tmp_path, {
        "medialRa-myanmar": {"advance": None,
                             "strokes": [stroke([[0, 600], [700, 600],
                                                 [700, -100]], 50)]},
    })
    assert font["medialRa-myanmar"].width == 0
    assert ink_x_min(font, "medialRa-myanmar") < 0  # not re-aligned


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
    assert pts == [tuple(p) for p in contour]


def test_dotted_circle_is_mark_base(tmp_path):
    font, _ = build(tmp_path, {
        "uni25CC": {"advance": None,
                    "strokes": [stroke([[250, 275]], 30)]},
    })
    assert set(anchors_of(font, "uni25CC")) == {"top", "bottom"}


def test_extension_blocks_classified(tmp_path):
    font, _ = build(tmp_path, {
        # Ext-A Khamti KA: letter → base anchors
        "uniAA60": {"advance": None, "strokes": [BOX]},
        # Ext-B Shan SAW (Mn above) → attaching + stacking anchor
        "uniA9E5": {"advance": None,
                    "strokes": [stroke([[300, 700], [420, 700]], 40)]},
    })
    assert set(anchors_of(font, "uniAA60")) == {"top", "bottom"}
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
