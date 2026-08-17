/*
 * Project store: holds all sketch data, autosaves to localStorage, and
 * imports/exports the portable project JSON that the Python pipeline reads.
 *
 * Coordinate system (shared with the pipeline):
 *   font units, 1000 UPM, y grows UP, baseline at y = 0.
 *   Body height guide at y = 550, ascender +900, descender -600.
 *
 * Project JSON schema (version 1; every addition is optional/backward
 * compatible):
 * {
 *   "format": "mm-glyph-studio", "version": 1,
 *   "meta": { "fontName", "styleName", "author", "license": "OFL-1.1" },
 *   "glyphs": {
 *     "<glyphName>": {
 *       "advance": <number|null>,          // null = auto from guide/bbox
 *       "strokes": [ { "width": <units>, "points": [[x,y], ...] }, ... ],
 *       "anchors": { "top": [x,y], ... }   // optional: mark anchors the
 *     }                                    //   contributor dragged; auto
 *   }                                      //   placed when absent
 * }
 * Stroke points may be [x,y,w] — w = per-point width in font units,
 * recorded from stylus pressure. A stroke may instead be a filled contour
 * { "fill": true, "points": [...] } (closed outline, e.g. imported SVG).
 */
(function () {
  "use strict";

  var STORAGE_KEY = "mm-glyph-studio-v1";

  var Store = {
    meta: {
      fontName: "MyMyanmarFont",
      styleName: "Regular",
      author: "",
      license: "OFL-1.1"
    },
    glyphs: {}, // name -> { advance, strokes }
    listeners: [],

    onChange: function (fn) { this.listeners.push(fn); },

    emit: function () {
      var self = this;
      this.listeners.forEach(function (fn) { fn(self); });
      this.saveLocal();
    },

    getGlyph: function (name) {
      if (!this.glyphs[name]) this.glyphs[name] = { advance: null, strokes: [] };
      return this.glyphs[name];
    },

    hasInk: function (name) {
      var g = this.glyphs[name];
      return !!(g && g.strokes && g.strokes.length);
    },

    drawnCount: function (groupKey) {
      var n = 0;
      window.GLYPHS.forEach(function (g) {
        if (groupKey && g.group !== groupKey) return;
        if (Store.hasInk(g.name)) n++;
      });
      return n;
    },

    saveLocal: function () {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(this.toJSON()));
      } catch (e) {
        // localStorage full or unavailable — non-fatal, export still works
      }
    },

    loadLocal: function () {
      try {
        var raw = localStorage.getItem(STORAGE_KEY);
        if (raw) this.fromJSON(JSON.parse(raw));
      } catch (e) { /* corrupted autosave — start fresh */ }
    },

    toJSON: function () {
      // omit untouched glyph records (browsing the sidebar creates empty
      // ones via getGlyph) so project files and PR diffs stay clean
      var glyphs = {};
      Object.keys(this.glyphs).forEach(function (name) {
        var g = Store.glyphs[name];
        if (!g) return;
        var hasInk = g.strokes && g.strokes.length;
        var hasAnchors = g.anchors && Object.keys(g.anchors).length;
        if (hasInk || hasAnchors || g.advance != null) glyphs[name] = g;
      });
      return {
        format: "mm-glyph-studio",
        version: 1,
        meta: this.meta,
        glyphs: glyphs
      };
    },

    fromJSON: function (data) {
      if (!data || data.format !== "mm-glyph-studio") {
        throw new Error("Not a Glyph Studio project file");
      }
      this.meta = Object.assign({}, this.meta, data.meta || {});
      this.glyphs = data.glyphs || {};
      // The nib travels with the project, so the canvas previews the shape
      // the build will actually emit. Without this a squircle-nib font
      // would be drawn round here and compile squared, which is exactly
      // the mismatch web/js/outline.js and json_to_ufo.py exist to avoid.
      if (window.Outline && window.Outline.setPen) {
        window.Outline.setPen(this.meta.pen);
      }
    },

    exportFile: function () {
      var blob = new Blob([JSON.stringify(this.toJSON(), null, 1)],
        { type: "application/json" });
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = (this.meta.fontName || "project") + ".glyphstudio.json";
      a.click();
      URL.revokeObjectURL(a.href);
    },

    importFile: function (file, done) {
      var reader = new FileReader();
      var self = this;
      reader.onload = function () {
        try {
          self.fromJSON(JSON.parse(reader.result));
          self.emit();
          if (done) done(null);
        } catch (e) {
          if (done) done(e);
        }
      };
      reader.readAsText(file);
    }
  };

  window.Store = Store;
})();
