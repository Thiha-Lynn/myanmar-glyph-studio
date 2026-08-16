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


def test_marks_carry_side_chain_anchors(tmp_path):
    # Below-marks chain BESIDE each other (side/_side, tops aligned), never
    # underneath: hanging the next mark below is how ရွှံ့'s tone dot ended
    # up 748 units deep. ha lands right of wa in ကွှ, u beside ha in ရှု.
    font, _ = build(tmp_path, {
        "u-myanmar": {"advance": None,
                      "strokes": [stroke([[250, -150], [350, -150]], 40)]},
    })
    a = anchors_of(font, "u-myanmar")
    assert set(a) == {"_bottom", "side", "_side"}
    assert a["side"][0] > a["_side"][0]       # side exits right, _side left
    assert a["side"][1] == a["_side"][1]      # chained marks align their tops
    assert font["u-myanmar"].width == 0


def test_marks_are_zero_width_even_if_the_project_says_otherwise(tmp_path):
    # a non-spacing mark with an advance would double-space every syllable
    font, _ = build(tmp_path, {
        "u-myanmar": {"advance": 420,
                      "strokes": [stroke([[250, -150], [350, -150]], 40)]},
        "ka-myanmar.sub": {"advance": 500,
                           "strokes": [stroke([[200, -180], [400, -180]])]},
    })
    assert font["u-myanmar"].width == 0
    assert font["ka-myanmar.sub"].width == 0


def test_subjoined_drawn_at_body_height_is_a_spacing_side_form(tmp_path):
    """ဇ္ဈ: Padauk stacks ဈ by putting a full-height spacing ဈ BESIDE the
    base, not a small one under it. A subjoined drawing whose ink rises
    above the baseline is that kind of form — treating it as a below-mark
    hangs an 847-unit glyph off the base and buries it at −916."""
    font, _ = build(tmp_path, {
        "jha-myanmar": {"advance": None, "strokes": [BOX]},
        # ink from −420 up to +430: a side form, not a below form
        "jha-myanmar.sub": {"advance": None,
                            "strokes": [stroke([[200, -420], [200, 430]])]},
        "ka-myanmar.sub": {"advance": None,
                           "strokes": [stroke([[200, -180], [400, -180]])]},
    })
    assert font["jha-myanmar.sub"].width > 0          # it advances the pen
    assert font["ka-myanmar.sub"].width == 0          # a real below-form
    cats = font.lib["public.openTypeCategories"]
    assert cats["jha-myanmar.sub"] == "base"
    assert cats["ka-myanmar.sub"] == "mark"


def test_spacing_sign_ink_left_aligned_when_auto(tmp_path):
    # aa (U+102C, Mc) sketched beside the ◌ carrier at x≈600
    font, _ = build(tmp_path, {
        "aa-myanmar": {"advance": None,
                       "strokes": [stroke([[600, 100], [600, 500]])]},
    })
    assert ink_x_min(font, "aa-myanmar") == pytest.approx(60, abs=2)
    assert font["aa-myanmar"].width < 300
    # …and it is a mark base as well: in ကော် the asat sits on the ာ, in
    # ကာံ the anusvara does. Without these the mark keeps its drawn
    # position at the pen and floats off the end of the cluster.
    assert set(anchors_of(font, "aa-myanmar")) == {"top", "bottom"}


def test_tall_spacing_sign_keeps_its_mark_in_the_normal_band(tmp_path):
    """ခေါ်: ါ is a 875-unit stem. An above-mark that followed the sign's
    own ink would land at 1303 — past usWinAscent, so Windows clips it.
    Padauk's fused ော် glyph tops out under the stem (856)."""
    font, _ = build(tmp_path, {
        "tallAa-myanmar": {"advance": None,
                           "strokes": [stroke([[600, 0], [600, 880]])]},
    })
    assert anchors_of(font, "tallAa-myanmar")["top"][1] == json_to_ufo.BODY - 40


def test_pre_base_vowel_carries_no_anchors(tmp_path):
    # ေ renders in FRONT of its consonant, so nothing in the cluster
    # attaches to it — the marks belong to the base the shaper moved past
    font, _ = build(tmp_path, {
        "e-myanmar": {"advance": None,
                      "strokes": [stroke([[600, 100], [600, 500]])]},
    })
    assert anchors_of(font, "e-myanmar") == {}


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


def test_descender_base_keeps_plain_vowel_at_side_anchor(tmp_path):
    # Beside a deep leg the PLAIN vowel at the clamped side anchor is the
    # side-form (Padauk's u.med equivalent). The long stack-form .alt must
    # apply only after subjoined letters, and the bottom anchor must not
    # chase the descender below the -50 floor.
    deep = stroke([[250, 550], [250, -360]])
    font, _ = build(tmp_path, {
        "na-myanmar": {"advance": None, "strokes": [deep]},
        "ta-myanmar": {"advance": None, "strokes": [BOX]},
        "ta-myanmar.sub": {"advance": None,
                           "strokes": [stroke([[200, -100], [400, -100]])]},
        "u-myanmar": {"advance": None,
                      "strokes": [stroke([[250, -150], [350, -150]], 40)]},
        "u-myanmar.alt": {"advance": None,
                          "strokes": [stroke([[250, -120], [300, -120]], 30)]},
    })
    fea = font.features.text
    desc_class = fea.split("@DESC_U = [")[1].split("]")[0]
    assert "na-myanmar" not in desc_class          # bases keep the plain vowel
    assert "ta-myanmar.sub" in desc_class          # stacks take the long form
    a = anchors_of(font, "na-myanmar")
    assert a["bottom"][1] == -90                   # clamped, not -400
    # The subjoined letter is clamped to the same floor: following the leg
    # all the way down puts န္န's stack at −890, in the next line of text.
    # Padauk lands every subjoined form in the −440…−80 band whatever the
    # base does (uni1014.alt + uni1014.med).
    assert a["stack"][1] == -90


def test_long_alt_vowels_are_spacing_glyphs_beside_the_stack(tmp_path):
    """စက္ကူ: the long ူ drawn for stacked clusters is a body-height glyph
    that stands to the RIGHT of the stack — Padauk's spacing uni1030, 288
    units of advance. Hung from the stack's bottom anchor as a mark it
    reached −1341, 741 units past the descender."""
    font, _ = build(tmp_path, {
        "uu-myanmar": {"advance": None,
                       "strokes": [stroke([[250, -150], [350, -150]], 40)]},
        "uu-myanmar.alt": {"advance": None,
                           "strokes": [stroke([[250, -430], [250, 430]], 40)]},
    })
    assert font["uu-myanmar"].width == 0                  # a below-mark
    assert font["uu-myanmar.alt"].width > 0               # a spacing form
    cats = font.lib["public.openTypeCategories"]
    assert cats["uu-myanmar.alt"] == "base"
    assert set(anchors_of(font, "uu-myanmar.alt")) == {"top", "bottom"}


def test_subjoined_form_swaps_in_the_side_base(tmp_path):
    """န + ္ + န: Padauk drops the leg (uni1014.alt) before stacking, and
    so must we — the leg and the subjoined letter share the same space."""
    font, _ = build(tmp_path, {
        "na-myanmar": {"advance": None,
                       "strokes": [stroke([[250, 550], [250, -360]])]},
        "na-myanmar.alt": {"advance": None,
                           "strokes": [stroke([[250, 550], [250, -40]])]},
        "na-myanmar.sub": {"advance": None,
                           "strokes": [stroke([[200, -180], [400, -180]])]},
        "virama-myanmar": {"advance": None,
                           "strokes": [stroke([[100, -200], [300, -200]])]},
    })
    fea = font.features.text
    side = fea.split("lookup side_bases {")[1].split("} side_bases;")[0]
    assert "na-myanmar.sub" in side


def test_kinzi_chains_the_next_mark_beside_it(tmp_path):
    """သင်္ကြီ: a vowel stacked ON the kinzi lands at y 1345 and Windows
    clips it. Padauk ships fused kinzi+vowel glyphs with the vowel to the
    LEFT of the hook; the chain anchor reproduces that geometry."""
    font, _ = build(tmp_path, {
        "kinzi-myanmar": {"advance": None,
                          "strokes": [stroke([[250, 700], [400, 700]], 30)]},
    })
    a = anchors_of(font, "kinzi-myanmar")
    assert a["top"][0] > a["_top"][0]        # the next mark goes to the RIGHT
    assert a["top"][1] == a["_top"][1]       # at the same height, not above


# ---------------------------------------------------------------------------
# medial-cluster variants and their contextual rules
# ---------------------------------------------------------------------------

YA = stroke([[-180, 400], [-40, 430], [60, 300], [60, -380]], 50)
WA = stroke([[220, -120], [380, -120], [380, -400], [220, -400]], 45)
HA = stroke([[250, -110], [250, -420], [330, -420]], 45)
RA_WRAP = {"advance": 168,
           "strokes": [stroke([[94, 850], [620, 850], [620, -380],
                               [94, -380]], 50)]}


def test_ya_medial_gets_side_anchor_beside_leg(tmp_path):
    # ကျု: the vowel sits beside the leg at normal below-vowel depth, not
    # hanging from the leg's bottom (the old bottom anchor at yMin−40)
    font, _ = build(tmp_path, {
        "medialYa-myanmar": {"advance": 158, "strokes": [YA]},
    })
    a = anchors_of(font, "medialYa-myanmar")
    assert set(a) == {"side", "top"}
    assert a["side"][1] == -40                # normal depth, not −420
    assert a["side"][0] > 0                   # beside the leg's outer edge


def test_ya_beforewa_variant_and_pres_rule(tmp_path):
    # ကျွ nests wa UNDER THE BASE (Padauk: uni103B103D) — a ya variant with
    # a tucked side anchor, substituted only when wa/ha follows
    font, drawn = build(tmp_path, {
        "medialYa-myanmar": {"advance": 158, "strokes": [YA]},
        "medialWa-myanmar": {"advance": None, "strokes": [WA]},
    })
    assert "medialYa-myanmar.beforewa" in drawn
    a = anchors_of(font, "medialYa-myanmar.beforewa")
    assert a["side"][0] < -200                # tucked left, under the base
    assert "top" in a                         # ကျွိ still gets its i-ring
    assert ("sub medialYa-myanmar' [medialWa-myanmar] "
            "by medialYa-myanmar.beforewa;") in font.features.text
    cats = font.lib["public.openTypeCategories"]
    assert cats["medialYa-myanmar.beforewa"] == "base"


def test_small_variants_synthesized_for_ra_context(tmp_path):
    # After the medial-ra wrap, below-marks shrink to fit INSIDE the wrap
    # (Padauk: uni103D103E.small & friends)
    font, drawn = build(tmp_path, {
        "ka-myanmar": {"advance": None, "strokes": [BOX]},
        "medialRa-myanmar": RA_WRAP,
        "medialWa-myanmar": {"advance": None, "strokes": [WA]},
        "medialHa-myanmar": {"advance": None, "strokes": [HA]},
    })
    assert {"medialWa-myanmar.small", "medialHa-myanmar.small"} <= drawn
    big = font["medialWa-myanmar"].getBounds(font)
    small = font["medialWa-myanmar.small"].getBounds(font)
    assert small.yMax == pytest.approx(big.yMax, abs=2)   # top edge kept
    assert (small.yMax - small.yMin) < 0.8 * (big.yMax - big.yMin)
    fea = font.features.text
    assert "feature psts" in fea
    assert ("sub @RA_WRAPS @RA_BASES medialWa-myanmar' "
            "by medialWa-myanmar.small;") in fea
    # second-mark pass: a mark chained onto an already-small one (ကြွှ)
    assert ("sub @RA_WRAPS @RA_BASES @BELOW_SMALLS medialHa-myanmar' "
            "by medialHa-myanmar.small;") in fea
    assert "UseMarkFilteringSet" in fea.split("feature psts")[1]


def test_vowels_take_tall_forms_after_ja_and_wa(tmp_path):
    """ကျု မွု: after the post-base medials, တစ်ချောင်းငင် is the TALL
    spacing stroke (Padauk's default uni102F, ink −429…423), never the
    curl beside the leg. ha stays visible in the filter so ရှု keeps the
    curl (Padauk's ha+u ligature is curl-deep)."""
    font, drawn = build(tmp_path, {
        "medialYa-myanmar": {"advance": 158, "strokes": [YA]},
        "medialWa-myanmar": {"advance": None, "strokes": [WA]},
        "medialHa-myanmar": {"advance": None, "strokes": [HA]},
        "u-myanmar": {"advance": None,
                      "strokes": [stroke([[250, -150], [350, -150]], 40)]},
        "u-myanmar.alt": {"advance": None,
                          "strokes": [stroke([[250, -430], [250, 430]], 40)]},
    })
    fea = font.features.text
    lookup = fea.split("lookup medial_vowels")[1].split("} medial_vowels")[0]
    assert ("sub [medialYa-myanmar medialYa-myanmar.beforewa "
            "medialWa-myanmar] u-myanmar' by u-myanmar.alt;") in lookup
    # ha is neither context nor filter: the rule fires straight through it
    # (Padauk's လျှု takes the tall stroke), while ရှု stays safe because
    # the base ra before the ha is always visible and blocks the match
    assert "medialHa-myanmar" not in lookup


def test_wrap_vowels_take_stroke_and_tall_forms(tmp_path):
    """ကြု: inside the wrap the u is the synthesized straight stroke
    hanging from the under-sweep (Padauk's fused uni103C102F); ကြူ: the
    uu stands AFTER the cluster as the tall spacing form (Padauk တြူ)."""
    font, drawn = build(tmp_path, {
        "ka-myanmar": {"advance": None, "strokes": [BOX]},
        "medialRa-myanmar": RA_WRAP,
        "u-myanmar": {"advance": None,
                      "strokes": [stroke([[250, -150], [350, -150]], 40)]},
        "uu-myanmar": {"advance": None,
                       "strokes": [stroke([[250, -150], [370, -150]], 40)]},
        "uu-myanmar.alt": {"advance": None,
                           "strokes": [stroke([[250, -430], [250, 430]], 40)]},
    })
    assert "u-myanmar.wrapstroke" in drawn
    g = font["u-myanmar.wrapstroke"]
    assert g.width == 0                                   # a mark
    box = g.getBounds(font)
    assert box.yMax < -200 and box.yMin < -520    # continues below the sweep
    a = anchors_of(font, "u-myanmar.wrapstroke")
    assert a["_bottom"][0] < box.xMin                     # plants ink RIGHT
    assert "side" in a                                    # dot chains beside
    fea = font.features.text
    psts = fea.split("feature psts")[1]
    assert ("sub @RA_WRAPS @RA_BASES u-myanmar' "
            "by u-myanmar.wrapstroke;") in psts
    assert ("sub @RA_WRAPS @RA_BASES uu-myanmar' "
            "by uu-myanmar.alt;") in psts
    assert "u-myanmar.small" not in fea                   # curls stay out


def test_traced_fused_forms_take_over_from_synthesis(tmp_path):
    """When the traced fused glyphs exist (Padauk's uni103C102F and
    uni103B103D sets), they replace the synthesized approximations: the
    wrap+ု pair becomes the fused wrap plus an invisible ghost, and
    beforewa+wa ligates — one woven drawing instead of crossed strokes."""
    font, drawn = build(tmp_path, {
        "ka-myanmar": {"advance": None, "strokes": [BOX]},
        "medialRa-myanmar": RA_WRAP,
        "medialRa-myanmar.u": {"advance": 168,
                               "strokes": [stroke([[94, 850], [620, 850],
                                                   [620, -380]], 50),
                                           stroke([[500, -60], [500, -420]],
                                                  50)]},
        "medialYa-myanmar": {"advance": 158, "strokes": [YA]},
        "medialYa-myanmar.wa": {"advance": 158,
                                "strokes": [YA, WA]},
        "medialWa-myanmar": {"advance": None, "strokes": [WA]},
        "u-myanmar": {"advance": None,
                      "strokes": [stroke([[250, -150], [350, -150]], 40)]},
    })
    assert "u-myanmar.ghost" in drawn            # synthesized deletion target
    assert "u-myanmar.wrapstroke" not in drawn   # fallback stands down
    g = font["u-myanmar.ghost"]
    assert g.width == 0 and len(g.contours) == 0
    fea = font.features.text
    psts = fea.split("feature psts")[1]
    assert ("sub medialRa-myanmar' @RA_BASES u-myanmar "
            "by medialRa-myanmar.u;") in psts
    assert ("sub @RA_WRAPS_U @RA_BASES u-myanmar' "
            "by u-myanmar.ghost;") in psts
    assert ("sub medialYa-myanmar.beforewa medialWa-myanmar "
            "by medialYa-myanmar.wa;") in fea.split("lookup ya_fuse")[1]
    # the fused wrap keeps wrap-sign treatment: advance, no re-alignment
    assert font["medialRa-myanmar.u"].width == 168
    # …and the ligature carries the ya anchors for rings and chains
    assert {"side", "top"} <= set(anchors_of(font, "medialYa-myanmar.wa"))


def test_ra_side_lookup_sees_through_ha(tmp_path):
    """ရှု: ra swaps to its side form ACROSS the ha (Padauk: ra.alt +
    ha ligature) — its lookup filters to u/uu only, while the shared
    lookup keeps ha visible because နှ swaps ON the ha."""
    deep = stroke([[250, 550], [250, -360]])
    font, _ = build(tmp_path, {
        "ra-myanmar": {"advance": None, "strokes": [deep]},
        "ra-myanmar.alt": {"advance": None,
                           "strokes": [stroke([[250, 550], [250, -40]])]},
        "na-myanmar": {"advance": None, "strokes": [deep]},
        "na-myanmar.alt": {"advance": None,
                           "strokes": [stroke([[250, 550], [250, -40]])]},
        "medialHa-myanmar": {"advance": None, "strokes": [HA]},
        "u-myanmar": {"advance": None,
                      "strokes": [stroke([[250, -150], [350, -150]], 40)]},
    })
    fea = font.features.text
    ra_lookup = fea.split("lookup side_bases_ra")[1].split("} side_bases_ra")[0]
    assert "sub ra-myanmar' [u-myanmar] by ra-myanmar.alt;" in ra_lookup
    assert "medialHa-myanmar" not in ra_lookup        # sees through the ha
    na_lookup = fea.split("lookup side_bases ")[1].split("} side_bases;")[0]
    assert "medialHa-myanmar" in na_lookup            # ha stays visible here


def test_no_small_variants_without_medial_ra(tmp_path):
    font, drawn = build(tmp_path, {
        "ka-myanmar": {"advance": None, "strokes": [BOX]},
        "medialWa-myanmar": {"advance": None, "strokes": [WA]},
    })
    assert "medialWa-myanmar.small" not in drawn
    assert "feature psts" not in font.features.text


def test_tall_wrap_rule_and_sticky_lookupflag_reset(tmp_path):
    # ကြီ: the wrap grows tall when ိ/ီ/ဲ sits over the wrapped base. The
    # tall lookup's filtering set is STICKY within the feature block — the
    # ya_tuck lookup after it must reset it or ကျွ silently stops tucking.
    font, drawn = build(tmp_path, {
        "ka-myanmar": {"advance": None, "strokes": [BOX]},
        "medialRa-myanmar": RA_WRAP,
        "medialRa-myanmar.tall": {"advance": 168,
                                  "strokes": [stroke([[94, 950], [620, 950],
                                                      [620, -380]], 50)]},
        "i-myanmar": {"advance": None,
                      "strokes": [stroke([[200, 650], [400, 650]], 40)]},
        "medialYa-myanmar": {"advance": 158, "strokes": [YA]},
        "medialWa-myanmar": {"advance": None, "strokes": [WA]},
    })
    fea = font.features.text
    assert ("sub medialRa-myanmar' @TALLABLE_BASES @RA_TALL_TRIGGERS "
            "by medialRa-myanmar.tall;") in fea
    # the reset guards the tuck rule against inheriting the filtering set
    ya_lookup = fea.split("lookup ya_tuck")[1]
    assert "lookupflag 0;" in ya_lookup
    assert font["medialRa-myanmar.tall"].width == 168   # wrap keeps advance


def test_side_form_bases_substituted_before_below_marks(tmp_path):
    # နု: the base itself swaps for its leg-free .alt in front of below
    # marks; the variant carries full base anchors but must not join the
    # wide-base measurement (it never follows a wrap in text)
    deep_na = stroke([[100, 500], [100, 0], [250, 550], [250, -360]])
    flat_alt = stroke([[100, 500], [100, 0], [250, 550], [250, -30]])
    font, drawn = build(tmp_path, {
        "na-myanmar": {"advance": None, "strokes": [deep_na]},
        "na-myanmar.alt": {"advance": None, "strokes": [flat_alt]},
        "u-myanmar": {"advance": None,
                      "strokes": [stroke([[250, -150], [350, -150]], 40)]},
        "medialRa-myanmar": RA_WRAP,
        "medialRa-myanmar.wide": {"advance": 168,
                                  "strokes": [stroke([[94, 850], [900, 850],
                                                      [900, -380]], 50)]},
    })
    fea = font.features.text
    assert "lookup side_bases" in fea
    assert "sub na-myanmar' [u-myanmar] by na-myanmar.alt;" in fea
    a = anchors_of(font, "na-myanmar.alt")
    assert {"top", "bottom", "stack"} <= set(a)
    cats = font.lib["public.openTypeCategories"]
    assert cats["na-myanmar.alt"] == "base"
    ra_bases = fea.split("@RA_BASES = [")[1].split("]")[0]
    assert "na-myanmar.alt" not in ra_bases
    assert "na-myanmar" in ra_bases


def test_i_anusvara_ligature(tmp_path):
    # ကိံ: ring + dot fuse into the drawn uni102D1036 ligature (a top mark)
    font, drawn = build(tmp_path, {
        "ka-myanmar": {"advance": None, "strokes": [BOX]},
        "i-myanmar": {"advance": None,
                      "strokes": [stroke([[200, 650], [400, 650]], 40)]},
        "anusvara-myanmar": {"advance": None,
                             "strokes": [stroke([[300, 700]], 30)]},
        "iAnusvara-myanmar": {"advance": None,
                              "strokes": [stroke([[200, 650], [420, 650]],
                                                 40)]},
    })
    fea = font.features.text
    assert ("sub i-myanmar anusvara-myanmar by iAnusvara-myanmar;"
            in fea.split("feature abvs")[1])
    a = anchors_of(font, "iAnusvara-myanmar")
    assert set(a) == {"_top", "top"}
    assert font["iAnusvara-myanmar"].width == 0
    assert font.lib["public.postscriptNames"]["iAnusvara-myanmar"] == "uni102D1036"


def test_leg_avoidance_moves_bottom_anchor_off_a_right_leg(tmp_path):
    # A letter whose tail descends under its right bowl (ည): the below-mark
    # anchor slides left to the nearest open column band instead of drawing
    # the mark through the tail. The wide bowl spans x 100…900 at baseline;
    # the leg drops deep at x 700…780.
    bowl = stroke([[100, 0], [900, 0]], 40)
    body = stroke([[100, 0], [100, 550], [900, 550], [900, 0]], 40)
    leg = stroke([[740, 0], [740, -400]], 40)
    font, _ = build(tmp_path, {
        "nnya-myanmar": {"advance": None, "strokes": [body, bowl, leg]},
    })
    a = anchors_of(font, "nnya-myanmar")
    # preferred 0.75 of ink ≈ x 710 — its ±50 band catches the leg; the
    # anchor slides to the nearest band that clears it (leg ink starts 720)
    assert a["bottom"][0] < 700
    assert a["bottom"][1] == -90              # depth clamp still applies
