/*
 * Draft TTF export + live in-browser preview.
 *
 * This produces an installable DRAFT font: every sketched glyph becomes a
 * filled outline at its Unicode codepoint. It is meant for quick testing of
 * your letterforms in real apps. It does NOT contain the OpenType shaping
 * rules (subjoined stacks, kinzi, mark positioning) — those are added by the
 * pipeline build (pipeline/json_to_ufo.py + fontmake), which turns the same
 * project file into a properly shaping mym2 font.
 */
(function () {
  "use strict";

  function glyphPath(polys) {
    var path = new opentype.Path();
    polys.forEach(function (poly) {
      poly.forEach(function (p, i) {
        var x = Math.round(p[0]), y = Math.round(p[1]);
        if (i === 0) path.moveTo(x, y); else path.lineTo(x, y);
      });
      path.close();
    });
    return path;
  }

  function buildFont() {
    var notdef = new opentype.Glyph({
      name: ".notdef", unicode: 0, advanceWidth: 600,
      path: new opentype.Path()
    });
    var space = new opentype.Glyph({
      name: "space", unicode: 0x20, advanceWidth: 500,
      path: new opentype.Path()
    });
    var glyphs = [notdef, space];

    var measure = function (g) {
      window.Editor.glyph = window.Editor.glyph; // no-op; measured below
      var ctx = window.Editor.ctx;
      ctx.save();
      ctx.font = '1000px Padauk, "Myanmar MN", "Noto Sans Myanmar", "Myanmar Text", sans-serif';
      var w = ctx.measureText(g.guide).width;
      ctx.restore();
      return Math.round(w) || 600;
    };

    var shiftX = function (polys, dx) {
      return polys.map(function (poly) {
        return poly.map(function (p) { return [p[0] + dx, p[1]]; });
      });
    };

    var included = 0;
    window.GLYPHS.forEach(function (g) {
      if (!window.Store.hasInk(g.name)) return;
      var data = window.Store.getGlyph(g.name);
      var polys = window.Outline.glyphPolygons(data);
      if (!polys.length) return;
      var adv = data.advance;
      if (adv == null) {
        var b = window.Outline.bounds(polys);
        var besideCarrier = g.guide && g.guide.charAt(0) === "◌";
        if (g.mark) {
          // marks take no advance; ink sketched beside the ◌ carrier is
          // shifted back so it lands roughly over the preceding base
          // (the full pipeline positions marks properly via GPOS anchors)
          adv = 0;
          if (besideCarrier) polys = shiftX(polys, -measure({ guide: "◌" }));
        } else if (besideCarrier && b.xMin > 60) {
          // spacing sign sketched beside the carrier: left-align the ink
          var dx = 60 - b.xMin;
          polys = shiftX(polys, dx);
          adv = Math.round(b.xMax + dx + 60);
        } else {
          adv = Math.round(b.xMax + 60);
          var guideAdv = measure(g);
          // prefer the guide's advance when the drawing roughly matches it
          if (Math.abs(guideAdv - adv) < 250) adv = guideAdv;
        }
      }
      var spec = {
        name: g.name,
        advanceWidth: Math.max(0, adv),
        path: glyphPath(polys)
      };
      if (g.cp) spec.unicode = g.cp;
      glyphs.push(new opentype.Glyph(spec));
      included++;
    });

    if (!included) throw new Error("Nothing drawn yet — sketch some glyphs first.");

    var meta = window.Store.meta;
    return new opentype.Font({
      familyName: (meta.fontName || "MyMyanmarFont") + " Draft",
      styleName: meta.styleName || "Regular",
      unitsPerEm: 1000,
      ascender: 900,
      descender: -600,
      designer: meta.author || undefined,
      license: "SIL Open Font License 1.1",
      licenseURL: "https://openfontlicense.org",
      glyphs: glyphs
    });
  }

  var previewFace = null;

  window.FontExport = {
    downloadTTF: function () {
      var font = buildFont();
      var buf = font.toArrayBuffer();
      var blob = new Blob([buf], { type: "font/ttf" });
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = (window.Store.meta.fontName || "MyMyanmarFont") + "-Draft.ttf";
      a.click();
      URL.revokeObjectURL(a.href);
      return font.glyphs.length;
    },

    /*
     * Export the current glyph as a standalone SVG (for design tools,
     * stickers, logos — creative reuse beyond the font itself).
     */
    downloadSVG: function (glyphMeta) {
      var data = window.Store.getGlyph(glyphMeta.name);
      var polys = window.Outline.glyphPolygons(data);
      if (!polys.length) throw new Error("Nothing drawn on this glyph yet.");
      var d = polys.map(function (poly) {
        return "M" + poly.map(function (p) {
          return Math.round(p[0]) + " " + Math.round(-p[1]);
        }).join("L") + "Z";
      }).join("");
      var b = window.Outline.bounds(polys);
      var pad = 40;
      var vb = [Math.floor(b.xMin - pad), Math.floor(-b.yMax - pad),
                Math.ceil(b.xMax - b.xMin + pad * 2),
                Math.ceil(b.yMax - b.yMin + pad * 2)].join(" ");
      // data-glyphstudio-units marks the file as font-unit exact, so
      // re-importing it (Import SVG) restores the identical coordinates
      var svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="' + vb +
        '" data-glyphstudio-units="font"><path d="' + d +
        '" fill="currentColor" fill-rule="nonzero"/></svg>\n';
      var blob = new Blob([svg], { type: "image/svg+xml" });
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = glyphMeta.name + ".svg";
      a.click();
      URL.revokeObjectURL(a.href);
    },

    /*
     * Load the draft font into the page under the family "GlyphStudioPreview"
     * so the test-drive box shows your actual drawn letterforms.
     */
    refreshPreview: function (done) {
      var font;
      try { font = buildFont(); }
      catch (e) { if (done) done(e); return; }
      var buf = font.toArrayBuffer();
      var face = new FontFace("GlyphStudioPreview", buf);
      face.load().then(function (loaded) {
        if (previewFace) document.fonts.delete(previewFace);
        previewFace = loaded;
        document.fonts.add(loaded);
        if (done) done(null, font.glyphs.length);
      }).catch(function (e) { if (done) done(e); });
    }
  };
})();
