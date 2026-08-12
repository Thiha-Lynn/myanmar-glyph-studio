/*
 * Project store: holds all sketch data, autosaves to localStorage, and
 * imports/exports the portable project JSON that the Python pipeline reads.
 *
 * Coordinate system (shared with the pipeline):
 *   font units, 1000 UPM, y grows UP, baseline at y = 0.
 *   Body height guide at y = 550, ascender +900, descender -600.
 *
 * Project JSON schema (version 1):
 * {
 *   "format": "mm-glyph-studio", "version": 1,
 *   "meta": { "fontName", "styleName", "author", "license": "OFL-1.1" },
 *   "glyphs": {
 *     "<glyphName>": {
 *       "advance": <number|null>,          // null = auto from guide/bbox
 *       "strokes": [ { "width": <units>, "points": [[x,y], ...] }, ... ]
 *     }                    // points may be [x,y,w] — w = per-point width
 *   }                      // in font units, recorded from stylus pressure
 * }
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
      return {
        format: "mm-glyph-studio",
        version: 1,
        meta: this.meta,
        glyphs: this.glyphs
      };
    },

    fromJSON: function (data) {
      if (!data || data.format !== "mm-glyph-studio") {
        throw new Error("Not a Glyph Studio project file");
      }
      this.meta = Object.assign({}, this.meta, data.meta || {});
      this.glyphs = data.glyphs || {};
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
