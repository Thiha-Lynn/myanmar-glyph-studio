/*
 * The glyph drawing canvas.
 *
 * Everything is drawn in font units (1000 UPM, baseline y=0, y up) and mapped
 * to canvas pixels. The dimmed guide character is painted from a system
 * Myanmar font (Padauk / Myanmar MN / Noto Sans Myanmar / Myanmar Text) under
 * the ink so contributors trace their own letterforms over a correct skeleton.
 */
(function () {
  "use strict";

  var VIEW = { x0: -250, x1: 1350, yTop: 950, yBottom: -650 };
  var GUIDE_FONTS = 'Padauk, "Myanmar MN", "Noto Sans Myanmar", "Myanmar Text", sans-serif';

  var Editor = {
    canvas: null,
    ctx: null,
    scale: 1,
    glyph: null,        // current glyph descriptor from GLYPHS
    penWidth: 60,       // font units
    guideOpacity: 0.22,
    guideSize: 1000,    // font units (≈ font-size used to render the guide)
    tool: "pen",       // pen | eraser
    fillPreview: false,
    liveStroke: null,
    undoStack: [],
    redoStack: [],
    onInkChange: null,  // callback(glyphName)

    init: function (canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.resize();
      var self = this;
      window.addEventListener("resize", function () { self.resize(); });

      canvas.addEventListener("pointerdown", function (e) { self.down(e); });
      canvas.addEventListener("pointermove", function (e) { self.move(e); });
      window.addEventListener("pointerup", function (e) { self.up(e); });
      canvas.addEventListener("pointerleave", function (e) { self.up(e); });
      // block touch scrolling while sketching
      canvas.style.touchAction = "none";
    },

    resize: function () {
      var box = this.canvas.parentElement.getBoundingClientRect();
      var unitsW = VIEW.x1 - VIEW.x0;
      var unitsH = VIEW.yTop - VIEW.yBottom;
      var w = Math.max(320, box.width - 2);
      var h = w * (unitsH / unitsW);
      var maxH = window.innerHeight - 210;
      if (h > maxH) { h = Math.max(320, maxH); w = h * (unitsW / unitsH); }
      var dpr = window.devicePixelRatio || 1;
      this.canvas.width = Math.round(w * dpr);
      this.canvas.height = Math.round(h * dpr);
      this.canvas.style.width = w + "px";
      this.canvas.style.height = h + "px";
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      this.scale = w / unitsW;
      this.render();
    },

    setGlyph: function (g) {
      this.glyph = g;
      this.liveStroke = null;
      this.undoStack = [];
      this.redoStack = [];
      this.render();
    },

    // ---- coordinate mapping -------------------------------------------
    toUnits: function (e) {
      var rect = this.canvas.getBoundingClientRect();
      var px = e.clientX - rect.left;
      var py = e.clientY - rect.top;
      return [
        Math.round(VIEW.x0 + px / this.scale),
        Math.round(VIEW.yTop - py / this.scale)
      ];
    },
    ux: function (x) { return (x - VIEW.x0) * this.scale; },
    uy: function (y) { return (VIEW.yTop - y) * this.scale; },

    // ---- input ---------------------------------------------------------
    down: function (e) {
      if (!this.glyph) return;
      e.preventDefault();
      this.canvas.setPointerCapture && this.canvas.setPointerCapture(e.pointerId);
      var p = this.toUnits(e);
      if (this.tool === "eraser") { this.eraseAt(p); return; }
      this.liveStroke = { width: this.penWidth, points: [p] };
      this.render();
    },

    move: function (e) {
      if (!this.glyph) return;
      var p = this.toUnits(e);
      if (this.tool === "eraser" && e.buttons) { this.eraseAt(p); return; }
      if (!this.liveStroke) return;
      var pts = this.liveStroke.points;
      var q = pts[pts.length - 1];
      var dx = p[0] - q[0], dy = p[1] - q[1];
      if (dx * dx + dy * dy > 16) { pts.push(p); this.render(); }
    },

    up: function () {
      if (!this.glyph || !this.liveStroke) return;
      if (this.liveStroke.points.length >= 1) {
        this.pushUndo();
        window.Store.getGlyph(this.glyph.name).strokes.push(this.liveStroke);
        window.Store.emit();
        if (this.onInkChange) this.onInkChange(this.glyph.name);
      }
      this.liveStroke = null;
      this.render();
    },

    eraseAt: function (p) {
      var data = window.Store.getGlyph(this.glyph.name);
      var hitR = Math.max(40, this.penWidth);
      var before = data.strokes.length;
      data.strokes = data.strokes.filter(function (s) {
        return !s.points.some(function (q) {
          var dx = p[0] - q[0], dy = p[1] - q[1];
          return dx * dx + dy * dy < hitR * hitR;
        });
      });
      if (data.strokes.length !== before) {
        this.pushUndoSnapshot(before);
        window.Store.emit();
        if (this.onInkChange) this.onInkChange(this.glyph.name);
        this.render();
      }
    },

    // ---- history -------------------------------------------------------
    snapshot: function () {
      return JSON.stringify(window.Store.getGlyph(this.glyph.name).strokes);
    },
    pushUndo: function () {
      this.undoStack.push(this.snapshot());
      if (this.undoStack.length > 60) this.undoStack.shift();
      this.redoStack = [];
    },
    pushUndoSnapshot: function () { this.pushUndo(); },
    undo: function () {
      if (!this.undoStack.length || !this.glyph) return;
      this.redoStack.push(this.snapshot());
      window.Store.getGlyph(this.glyph.name).strokes =
        JSON.parse(this.undoStack.pop());
      window.Store.emit();
      if (this.onInkChange) this.onInkChange(this.glyph.name);
      this.render();
    },
    redo: function () {
      if (!this.redoStack.length || !this.glyph) return;
      this.undoStack.push(this.snapshot());
      window.Store.getGlyph(this.glyph.name).strokes =
        JSON.parse(this.redoStack.pop());
      window.Store.emit();
      if (this.onInkChange) this.onInkChange(this.glyph.name);
      this.render();
    },
    clearGlyph: function () {
      if (!this.glyph) return;
      this.pushUndo();
      window.Store.getGlyph(this.glyph.name).strokes = [];
      window.Store.emit();
      if (this.onInkChange) this.onInkChange(this.glyph.name);
      this.render();
    },

    // ---- guide metrics -------------------------------------------------
    measureGuideAdvance: function () {
      if (!this.glyph) return 600;
      this.ctx.save();
      this.ctx.font = "1000px " + GUIDE_FONTS;
      var w = this.ctx.measureText(this.glyph.guide).width;
      this.ctx.restore();
      return Math.round(w) || 600;
    },

    // ---- rendering -----------------------------------------------------
    render: function () {
      var ctx = this.ctx;
      if (!ctx) return;
      var css = getComputedStyle(document.documentElement);
      var colInk = css.getPropertyValue("--ink").trim() || "#222";
      var colFaint = css.getPropertyValue("--line").trim() || "#ddd";
      var colAccent = css.getPropertyValue("--accent").trim() || "#a8352f";
      var colBg = css.getPropertyValue("--canvas-bg").trim() || "#fff";

      var w = this.canvas.width, h = this.canvas.height;
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = colBg;
      ctx.fillRect(0, 0, w, h);
      ctx.restore();
      if (!this.glyph) return;

      // metric lines
      var self = this;
      function hline(y, color, dash, label) {
        ctx.save();
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        if (dash) ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(0, self.uy(y));
        ctx.lineTo(self.canvas.clientWidth, self.uy(y));
        ctx.stroke();
        if (label) {
          ctx.fillStyle = color;
          ctx.font = "10px system-ui, sans-serif";
          ctx.fillText(label, 4, self.uy(y) - 3);
        }
        ctx.restore();
      }
      function vline(x, color, dash) {
        ctx.save();
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        if (dash) ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(self.ux(x), 0);
        ctx.lineTo(self.ux(x), self.canvas.clientHeight);
        ctx.stroke();
        ctx.restore();
      }

      hline(900, colFaint, true, "ascender 900");
      hline(550, colFaint, false, "body 550");
      hline(0, colAccent, false, "baseline 0");
      hline(-600, colFaint, true, "descender −600");
      vline(0, colAccent, false);

      var advance = window.Store.getGlyph(this.glyph.name).advance ||
        this.measureGuideAdvance();
      vline(advance, colFaint, true);

      // dimmed guide character
      ctx.save();
      ctx.globalAlpha = this.guideOpacity;
      ctx.fillStyle = colInk;
      ctx.font = this.guideSize + "px " + GUIDE_FONTS;
      ctx.textBaseline = "alphabetic";
      ctx.fillText(this.glyph.guide, this.ux(0), this.uy(0));
      ctx.restore();

      // committed strokes + live stroke
      var strokes = window.Store.getGlyph(this.glyph.name).strokes.slice();
      if (this.liveStroke) strokes.push(this.liveStroke);

      if (this.fillPreview) {
        ctx.save();
        ctx.fillStyle = colInk;
        ctx.beginPath();
        strokes.forEach(function (s) {
          var poly = window.Outline.strokeToPolygon(s);
          if (!poly) return;
          poly.forEach(function (p, i) {
            var x = self.ux(p[0]), y = self.uy(p[1]);
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          });
          ctx.closePath();
        });
        ctx.fill("nonzero");
        ctx.restore();
      } else {
        ctx.save();
        ctx.strokeStyle = colInk;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        strokes.forEach(function (s) {
          if (!s.points.length) return;
          ctx.lineWidth = Math.max(1, s.width * self.scale);
          var pts = window.Outline.smooth(s.points.slice(), 1);
          ctx.beginPath();
          ctx.moveTo(self.ux(pts[0][0]), self.uy(pts[0][1]));
          if (pts.length === 1) {
            ctx.lineTo(self.ux(pts[0][0]) + 0.1, self.uy(pts[0][1]));
          }
          for (var i = 1; i < pts.length - 1; i++) {
            var mx = (pts[i][0] + pts[i + 1][0]) / 2;
            var my = (pts[i][1] + pts[i + 1][1]) / 2;
            ctx.quadraticCurveTo(
              self.ux(pts[i][0]), self.uy(pts[i][1]),
              self.ux(mx), self.uy(my));
          }
          if (pts.length > 1) {
            var last = pts[pts.length - 1];
            ctx.lineTo(self.ux(last[0]), self.uy(last[1]));
          }
          ctx.stroke();
        });
        ctx.restore();
      }
    }
  };

  window.Editor = Editor;
})();
