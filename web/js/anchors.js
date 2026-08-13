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
    "anusvara-myanmar": 1, "asat-myanmar": 1, "kinzi-myanmar": 1
  };
  var BOTTOM_MARKS = {
    "u-myanmar": 1, "uu-myanmar": 1, "dotBelow-myanmar": 1,
    "medialWa-myanmar": 1, "medialHa-myanmar": 1,
    "u-myanmar.alt": 1, "uu-myanmar.alt": 1
  };
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

  /* "base" | "top-mark" | "bottom-mark" | "auto-mark" | null */
  function roleFor(meta) {
    if (!meta) return null;
    if (TOP_MARKS[meta.name]) return "top-mark";
    if (BOTTOM_MARKS[meta.name] || /\.sub$/.test(meta.name)) return "bottom-mark";
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
  function listFor(meta, data) {
    var role = roleFor(meta);
    if (!role) return [];
    var polys = window.Outline.glyphPolygons(data);
    var b = window.Outline.bounds(polys);
    if (!b) return [];
    var cx = (b.xMin + b.xMax) / 2;
    var cy = (b.yMin + b.yMax) / 2;

    // Marks carry the attaching _anchor plus a base anchor on their outer
    // side, so further marks can stack on them (GPOS mkmk).
    var defaults = {};
    if (role === "base") {
      defaults.top = [cx, Math.max(b.yMax, BODY) + 40];
      defaults.bottom = [cx, Math.min(b.yMin, 0) - 40];
    } else if (role === "top-mark") {
      defaults._top = [cx, b.yMin - 20];
      defaults.top = [cx, b.yMax + 20];
    } else if (role === "bottom-mark") {
      defaults._bottom = [cx, b.yMax + 20];
      defaults.bottom = [cx, b.yMin - 20];
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
