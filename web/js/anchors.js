/*
 * Mark-attachment anchors: classification + default positions.
 *
 * The pipeline (json_to_ufo.py) auto-places anchors from each glyph's ink;
 * this module mirrors that logic so the studio can SHOW the anchors and let
 * contributors drag them. A dragged anchor is stored per glyph in the
 * project JSON as  anchors: { "<name>": [x, y] }  and overrides the
 * auto position at build time. Anchor names follow the UFO convention:
 *   top / bottom   on bases (where marks attach),
 *   _top / _bottom on marks (the point that attaches).
 *
 * Keep the sets and formulas in sync with pipeline/json_to_ufo.py.
 */
(function () {
  "use strict";

  var BODY = 550;

  var TOP_MARKS = {
    "i-myanmar": 1, "ii-myanmar": 1, "ai-myanmar": 1,
    "anusvara-myanmar": 1, "asat-myanmar": 1, "kinzi-myanmar": 1,
    "iAnusvara-myanmar": 1
  };
  var BOTTOM_MARKS = {
    "u-myanmar": 1, "uu-myanmar": 1, "dotBelow-myanmar": 1,
    "medialWa-myanmar": 1, "medialHa-myanmar": 1
  };
  // The long u/uu forms used under stacks (စက္ကူ) are body-height glyphs
  // that stand BESIDE the cluster, the way Padauk's spacing uni1030 does —
  // not below-marks. Hanging them off the stack put စက္ကူ's vowel at −1341.
  var SPACING_VOWELS = { "u-myanmar.alt": 1, "uu-myanmar.alt": 1 };
  // spacing signs rendered BEFORE the base: nothing attaches to them
  var PRE_BASE_SIGNS = { "e-myanmar": 1, "uni1084": 1 };
  // medial ra wraps its base and carries no anchors (the marks belong to
  // the base inside the wrap) — mirrors WRAP_SIGNS in json_to_ufo.py
  var WRAP_SIGNS = {
    "medialRa-myanmar": 1, "medialRa-myanmar.wide": 1,
    "medialRa-myanmar.tall": 1, "medialRa-myanmar.tall.wide": 1,
    "medialRa-myanmar.u": 1, "medialRa-myanmar.u.wide": 1,
    "medialRa-myanmar.u.tall": 1, "medialRa-myanmar.u.tall.wide": 1
  };
  var TOP_CLEARANCE = 60;   // ink-to-mark gap above a letter (Padauk: 76)
  var STACK_FLOOR = -50;    // deepest a subjoined letter may hang from
  var KINZI_SIDE_GAP = 225; // how far right of the kinzi the next mark sits
  var SIDE_GAP = 55;        // below-mark side chain: next ink starts this
                            // far right (50-unit clearance protocol + margin)
  // groups whose spacing glyphs don't carry mark anchors
  var NO_ANCHOR_GROUPS = { digits: 1, punctuation: 1 };
  var MYANMAR_RANGES = [
    [0x1000, 0x109F], [0xA9E0, 0xA9FF], [0xAA60, 0xAA7F], [0x116D0, 0x116FF]
  ];

  function inMyanmarBlocks(cp) {
    for (var i = 0; i < MYANMAR_RANGES.length; i++) {
      if (cp >= MYANMAR_RANGES[i][0] && cp <= MYANMAR_RANGES[i][1]) return true;
    }
    return false;
  }

  /* "base" | "spacing-sign" | "kinzi" | "top-mark" | "bottom-mark" |
     "stack-mark" | "ya-medial" | "auto-mark" | null */
  function roleFor(meta) {
    if (!meta) return null;
    if (WRAP_SIGNS[meta.name]) return null;
    if (meta.name === "medialYa-myanmar" ||
        meta.name === "medialYa-myanmar.wa" ||
        meta.name === "medialYa-myanmar.ha") return "ya-medial";
    if (meta.baseVariant) return "base";  // side-form bases (na-myanmar.alt …)
    if (SPACING_VOWELS[meta.name]) return "spacing-sign";
    if (meta.name === "kinzi-myanmar") return "kinzi";
    if (TOP_MARKS[meta.name]) return "top-mark";
    if (/\.sub$/.test(meta.name)) return "stack-mark";
    if (BOTTOM_MARKS[meta.name]) return "bottom-mark";
    // post-base spacing signs (ာ ါ း): sketched against the ◌ carrier but
    // not marks themselves, and marks DO attach to them — ကော် ကာံ
    if (!meta.mark && meta.guide && meta.guide.charAt(0) === "◌" &&
        !PRE_BASE_SIGNS[meta.name]) {
      return "spacing-sign";
    }
    if (meta.mark) return "auto-mark";
    if (meta.cp === 0x25CC || meta.name === "greatSa-myanmar") return "base";
    if (meta.cp && inMyanmarBlocks(meta.cp) &&
        meta.guide && meta.guide.charAt(0) !== "◌" &&
        !NO_ANCHOR_GROUPS[meta.group]) {
      return "base";
    }
    return null;
  }

  /*
   * The anchors this glyph carries, with their current positions:
   * [{name, x, y, manual}] — manual=true when the position was dragged
   * (stored in the project), false when it is the auto default.
   * Empty until the glyph has ink (there is nothing to anchor to).
   */
  // Lowest ink y inside the x band [x0, x1], or null when no ink there —
  // used by the leg-avoidance scan below (mirrors json_to_ufo.py).
  function columnDepth(polys, x0, x1) {
    var lowest = null;
    for (var i = 0; i < polys.length; i++) {
      var poly = polys[i];
      for (var j = 0; j < poly.length; j++) {
        var p = poly[j];
        if (p[0] >= x0 && p[0] <= x1 &&
            (lowest === null || p[1] < lowest)) lowest = p[1];
      }
    }
    return lowest;
  }

  // Where an above-mark attaches on a glyph whose ink tops at yMax: it
  // follows the ink so tall letters push their marks up, with BODY as the
  // floor. Mirrors top_anchor_y() in json_to_ufo.py.
  function topAnchorY(yMax) {
    return Math.max(yMax + TOP_CLEARANCE, BODY - 40);
  }

  function listFor(meta, data) {
    var role = roleFor(meta);
    if (!role) return [];
    var polys = window.Outline.glyphPolygons(data);
    var b = window.Outline.bounds(polys);
    if (!b) return [];
    var cx = (b.xMin + b.xMax) / 2;
    var cy = (b.yMin + b.yMax) / 2;

    // A subjoined form drawn at full body height is a SIDE form, not a
    // below form: Padauk stacks ဇ္ဈ by putting a spacing ဈ beside the
    // base. Hanging that drawing from a below anchor buries it at −916.
    // Measured, so a small subjoined ဈ still stacks underneath.
    if (role === "stack-mark" && b.yMax > 0) role = "spacing-sign";

    // Marks carry the attaching _anchor plus a base anchor on their outer
    // side, so further marks can stack on them (GPOS mkmk).
    var defaults = {};
    if (role === "base") {
      // vowel marks sit over the right bowl of wide two-bowl letters,
      // stacks hang from dead centre — mirrors json_to_ufo.py (Padauk
      // calibration: ကီ 0.73 / ကု 0.78 / ခု 0.56 / stacks 0.50)
      var w = Math.max(1, b.xMax - b.xMin);
      var mx = b.xMin + w * (w > 700 ? 0.75 : 0.55);
      // leg avoidance (below-marks only): if the letter's own ink descends
      // through the anchor spot (ည's tail), slide the BOTTOM anchor to the
      // nearest open column band — mirrors json_to_ufo.py; letters that
      // are deep everywhere keep the spot
      var bx = mx;
      var band = columnDepth(polys, mx - 50, mx + 50);
      if (band !== null && band < -160) {
        var best = null;
        for (var k = 0; k < 19; k++) {          // 0.40 … 0.85
          var cand = b.xMin + w * (0.40 + k * 0.025);
          var d = columnDepth(polys, cand - 50, cand + 50);
          if ((d === null || d >= -160) &&
              (best === null || Math.abs(cand - mx) < Math.abs(best - mx))) {
            best = cand;
          }
        }
        if (best !== null) bx = best;
      }
      defaults.top = [mx, topAnchorY(b.yMax)];
      // bottom marks stay near baseline depth even under deep legs (န ရ) —
      // the plain vowel beside the leg IS the side-form (Padauk zone
      // −95…−450); the subjoined letter is clamped to the same floor, or
      // န္န's stack lands at −890, in the next line of text
      defaults.bottom = [bx, Math.max(Math.min(b.yMin, 0), -50) - 40];
      defaults.stack = [cx, Math.max(Math.min(b.yMin, 0), STACK_FLOOR) - 40];
    } else if (role === "spacing-sign") {
      // ာ ါ and the long stack vowels are mark bases too: the asat of
      // ကော် and the anusvara of ကာံ sit on the SIGN, not on the letter.
      // The height stays in the normal above-mark band rather than
      // following the ink — a mark stacked over ါ's 875-unit stem lands at
      // 1303 and Windows clips it (Padauk's fused ော် tops out at 856).
      var sw = Math.max(1, b.xMax - b.xMin);
      var sx = b.xMin + sw * (sw > 700 ? 0.75 : 0.55);
      defaults.top = [sx, BODY - 40];
      defaults.bottom = [sx, Math.max(Math.min(b.yMin, 0), -50) - 40];
    } else if (role === "kinzi") {
      // a vowel after the kinzi lands BESIDE it (to the right, tops
      // aligned, like Padauk's fused kinzi+vowel glyphs): stacking it on
      // top sends သင်္ကြီ past the ascender and Windows clips it
      defaults._top = [cx, b.yMin - 20];
      defaults.top = [b.xMax + KINZI_SIDE_GAP, b.yMin - 20];
    } else if (role === "ya-medial") {
      // ကျု: the below-vowel sits BESIDE the ya-pinn's leg at normal depth
      // (side anchor); the top anchor keeps ကျိ working (ya intercepts the
      // mark's base scan)
      defaults.side = [b.xMax - 30, -40];
      defaults.top = [cx, topAnchorY(b.yMax)];
    } else if (role === "top-mark") {
      defaults._top = [cx, b.yMin - 20];
      defaults.top = [cx, b.yMax + 20];
    } else if (role === "bottom-mark") {
      // no plain "bottom" chain: marks that follow a below-mark chain
      // BESIDE it (side/_side, tops aligned) — ha right of wa in ကွှ, the
      // tone dot beside a deep hook in ရွှံ့ — mirrors json_to_ufo.py
      defaults._bottom = [cx, b.yMax + 20];
      defaults.side = [b.xMax, b.yMax + 20];
      defaults._side = [b.xMin - SIDE_GAP, b.yMax + 20];
    } else if (role === "stack-mark") {
      // a medial or tone after a stack chains BESIDE it, tops aligned —
      // the same rule below-marks follow; hanging it from the stack's own
      // bottom put က္ကွိ's ွ at −814
      defaults._stack = [cx, b.yMax + 20];
      defaults.side = [b.xMax, b.yMax + 20];
    } else if (role === "auto-mark") {
      if (cy >= BODY / 2) {
        defaults._top = [cx, b.yMin - 20];
        defaults.top = [cx, b.yMax + 20];
      } else {
        defaults._bottom = [cx, b.yMax + 20];
        defaults.bottom = [cx, b.yMin - 20];
      }
    }

    var stored = data.anchors || {};
    var out = [];
    Object.keys(defaults).forEach(function (name) {
      var pos = stored[name];
      var ok = Array.isArray(pos) && pos.length >= 2 &&
        isFinite(pos[0]) && isFinite(pos[1]);
      out.push({
        name: name,
        x: ok ? pos[0] : defaults[name][0],
        y: ok ? pos[1] : defaults[name][1],
        manual: !!ok
      });
    });
    return out;
  }

  window.Anchors = { roleFor: roleFor, listFor: listFor };
})();
