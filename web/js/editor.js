/*
 * The glyph drawing canvas.
 *
 * Everything is drawn in font units (1000 UPM, baseline y=0, y up) and mapped
 * to canvas pixels through a zoomable/pannable view transform. The dimmed
 * guide character is painted from a system Myanmar font (Padauk / Myanmar MN /
 * Noto Sans Myanmar / Myanmar Text) under the ink so contributors trace their
 * own letterforms over a correct skeleton.
 *
 * Input:
 *   - mouse / trackpad: draw with click-drag, wheel or pinch-gesture to zoom
 *   - touch: one finger draws (until a stylus is detected), two fingers
 *     always pan/zoom
 *   - stylus (Apple Pencil etc.): draws with optional pressure-variable
 *     width; once a pen is seen, bare fingers pan instead of drawing
 *     (palm rejection) unless "Finger draws" is re-enabled
 */
(function () {
  "use strict";

  var VIEW = { x0: -250, x1: 1350, yTop: 950, yBottom: -650 };
  var GUIDE_FONTS = 'Padauk, "Myanmar MN", "Noto Sans Myanmar", "Myanmar Text", sans-serif';
  var ZOOM_MIN = 0.4, ZOOM_MAX = 6;

  var Editor = {
    canvas: null,
    ctx: null,
    baseScale: 1,
    zoom: 1,
    ox: VIEW.x0,      // unit coords of the canvas top-left corner
    oy: VIEW.yTop,
    glyph: null,       // current glyph descriptor from GLYPHS
    penWidth: 60,      // font units
    guideOpacity: 0.22,
    guideSize: 1000,   // font units
    tool: "pen",      // pen | eraser
    fillPreview: false,
    pressureEnabled: true,
    stabilizer: 3,     // 0 (off) … 10 (heavy)
    touchDraws: true,  // flips off automatically once a stylus is detected
    penSeen: false,
    liveStroke: null,
    _stabPoint: null,
    pointers: {},      // pointerId -> {type, x, y} (screen px)
    gesture: null,     // {dist, mid:[px,py], startZoom, startOx, startOy}
    undoStack: [],
    redoStack: [],
    onInkChange: null, // callback(glyphName)
    onViewChange: null,

    init: function (canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.resize();
      var self = this;
      window.addEventListener("resize", function () { self.resize(); });

      canvas.addEventListener("pointerdown", function (e) { self.down(e); });
      canvas.addEventListener("pointermove", function (e) { self.move(e); });
      window.addEventListener("pointerup", function (e) { self.up(e); });
      window.addEventListener("pointercancel", function (e) { self.up(e); });
      canvas.addEventListener("wheel", function (e) { self.wheel(e); }, { passive: false });
      canvas.style.touchAction = "none";
    },

    resize: function () {
      var box = this.canvas.parentElement.getBoundingClientRect();
      var w = Math.max(280, box.width);
      var h = Math.max(240, box.height || 0);
      if (!box.height) h = w; // fallback before layout settles
      var dpr = window.devicePixelRatio || 1;
      this.canvas.width = Math.round(w * dpr);
      this.canvas.height = Math.round(h * dpr);
      this.canvas.style.width = w + "px";
      this.canvas.style.height = h + "px";
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      this.cssW = w;
      this.cssH = h;
      // fit the whole VIEW box at zoom 1
      this.baseScale = Math.min(
        w / (VIEW.x1 - VIEW.x0),
        h / (VIEW.yTop - VIEW.yBottom)
      );
      this.clampView();
      this.render();
    },

    s: function () { return this.baseScale * this.zoom; },

    setGlyph: function (g) {
      this.glyph = g;
      this.liveStroke = null;
      this.undoStack = [];
      this.redoStack = [];
      this.render();
    },

    // ---- view transform ------------------------------------------------
    ux: function (x) { return (x - this.ox) * this.s(); },
    uy: function (y) { return (this.oy - y) * this.s(); },
    px2units: function (px, py) {
      return [this.ox + px / this.s(), this.oy - py / this.s()];
    },
    toScreen: function (e) {
      var rect = this.canvas.getBoundingClientRect();
      return [e.clientX - rect.left, e.clientY - rect.top];
    },
    toUnits: function (e) {
      var p = this.toScreen(e);
      var u = this.px2units(p[0], p[1]);
      return [Math.round(u[0]), Math.round(u[1])];
    },

    clampView: function () {
      var s = this.s();
      var viewW = this.cssW / s, viewH = this.cssH / s;
      var margin = 200;
      this.ox = Math.min(Math.max(this.ox, VIEW.x0 - viewW + margin), VIEW.x1 - margin);
      var oyMax = VIEW.yTop + viewH - margin;
      var oyMin = VIEW.yBottom + margin;
      this.oy = Math.min(Math.max(this.oy, oyMin), oyMax);
    },

    zoomAt: function (px, py, factor) {
      var before = this.px2units(px, py);
      this.zoom = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, this.zoom * factor));
      var after = this.px2units(px, py);
      this.ox += before[0] - after[0];
      this.oy += before[1] - after[1];
      this.clampView();
      this.render();
      if (this.onViewChange) this.onViewChange();
    },

    zoomStep: function (factor) {
      this.zoomAt(this.cssW / 2, this.cssH / 2, factor);
    },

    resetView: function () {
      this.zoom = 1;
      this.ox = VIEW.x0;
      this.oy = VIEW.yTop;
      // center horizontally when the canvas is wider than the view box
      var extraW = this.cssW / this.s() - (VIEW.x1 - VIEW.x0);
      if (extraW > 0) this.ox = VIEW.x0 - extraW / 2;
      this.clampView();
      this.render();
      if (this.onViewChange) this.onViewChange();
    },

    wheel: function (e) {
      e.preventDefault();
      var p = this.toScreen(e);
      var factor = Math.pow(1.0018, -e.deltaY);
      // trackpad pinch arrives as wheel+ctrlKey with small deltas
      if (e.ctrlKey) factor = Math.pow(1.008, -e.deltaY);
      this.zoomAt(p[0], p[1], factor);
    },

    // ---- input ---------------------------------------------------------
    activeTouches: function () {
      var out = [];
      for (var id in this.pointers) {
        if (this.pointers[id].type === "touch") out.push(this.pointers[id]);
      }
      return out;
    },

    down: function (e) {
      if (!this.glyph) return;
      e.preventDefault();
      this.canvas.setPointerCapture && this.canvas.setPointerCapture(e.pointerId);
      var scr = this.toScreen(e);
      this.pointers[e.pointerId] = { type: e.pointerType, x: scr[0], y: scr[1] };

      if (e.pointerType === "pen" && !this.penSeen) {
        this.penSeen = true;
        this.touchDraws = false;
        if (this.onPenDetected) this.onPenDetected();
      }

      var touches = this.activeTouches();
      if (e.pointerType === "touch" && touches.length === 2) {
        // second finger: abandon any live stroke, start pinch/pan gesture
        this.liveStroke = null;
        this._stabPoint = null;
        var a = touches[0], b = touches[1];
        this.gesture = {
          dist: Math.hypot(a.x - b.x, a.y - b.y),
          mid: [(a.x + b.x) / 2, (a.y + b.y) / 2]
        };
        this.render();
        return;
      }

      var drawsInk = e.pointerType !== "touch" || this.touchDraws;
      if (!drawsInk) {
        // single-finger pan mode (stylus workflow)
        this.pointers[e.pointerId].panning = true;
        return;
      }

      var p = this.toUnits(e);
      if (this.tool === "eraser") { this.eraseAt(p); return; }
      this._stabPoint = p.slice(0, 2);
      this.liveStroke = { width: this.penWidth, points: [this.inputPoint(e, p)] };
      this.render();
    },

    inputPoint: function (e, unitP) {
      // stabilize: exponential pull toward the raw point
      var raw = unitP || this.toUnits(e);
      var pt;
      if (this.stabilizer > 0 && this._stabPoint) {
        var k = 1 / (1 + this.stabilizer * 0.6);
        this._stabPoint = [
          this._stabPoint[0] + (raw[0] - this._stabPoint[0]) * k,
          this._stabPoint[1] + (raw[1] - this._stabPoint[1]) * k
        ];
        pt = [Math.round(this._stabPoint[0]), Math.round(this._stabPoint[1])];
      } else {
        pt = [raw[0], raw[1]];
      }
      // stylus pressure → per-point width
      if (this.pressureEnabled && e.pointerType === "pen" && e.pressure > 0) {
        pt.push(Math.round(this.penWidth * (0.35 + 1.3 * e.pressure)));
      }
      return pt;
    },

    move: function (e) {
      if (!this.glyph) return;
      var rec = this.pointers[e.pointerId];
      var scr = this.toScreen(e);

      // two-finger pinch/pan
      if (this.gesture && rec && rec.type === "touch") {
        rec.x = scr[0]; rec.y = scr[1];
        var touches = this.activeTouches();
        if (touches.length >= 2) {
          var a = touches[0], b = touches[1];
          var dist = Math.hypot(a.x - b.x, a.y - b.y);
          var mid = [(a.x + b.x) / 2, (a.y + b.y) / 2];
          var factor = this.gesture.dist ? dist / this.gesture.dist : 1;
          this.zoomAt(mid[0], mid[1], factor);
          // pan by midpoint drift
          var s = this.s();
          this.ox -= (mid[0] - this.gesture.mid[0]) / s;
          this.oy += (mid[1] - this.gesture.mid[1]) / s;
          this.clampView();
          this.gesture.dist = dist;
          this.gesture.mid = mid;
          this.render();
        }
        return;
      }

      // single-finger pan (stylus workflow)
      if (rec && rec.panning) {
        var sc = this.s();
        this.ox -= (scr[0] - rec.x) / sc;
        this.oy += (scr[1] - rec.y) / sc;
        rec.x = scr[0]; rec.y = scr[1];
        this.clampView();
        this.render();
        return;
      }

      if (rec) { rec.x = scr[0]; rec.y = scr[1]; }
      var p = this.toUnits(e);
      if (this.tool === "eraser" && e.buttons) { this.eraseAt(p); return; }
      if (!this.liveStroke) return;

      // use coalesced events for high-frequency stylus input
      var events = (e.getCoalescedEvents && e.getCoalescedEvents().length)
        ? e.getCoalescedEvents() : [e];
      var pts = this.liveStroke.points;
      var minDist2 = Math.pow(2.5 / this.s(), 2) * 4; // denser when zoomed in
      for (var i = 0; i < events.length; i++) {
        var pt = this.inputPoint(events[i], this.toUnits(events[i]));
        var q = pts[pts.length - 1];
        var dx = pt[0] - q[0], dy = pt[1] - q[1];
        if (dx * dx + dy * dy > minDist2) pts.push(pt);
      }
      this.render();
    },

    up: function (e) {
      delete this.pointers[e.pointerId];
      if (this.activeTouches().length < 2) this.gesture = null;
      if (!this.glyph || !this.liveStroke) return;
      if (this.liveStroke.points.length >= 1) {
        this.pushUndo();
        window.Store.getGlyph(this.glyph.name).strokes.push(this.liveStroke);
        window.Store.emit();
        if (this.onInkChange) this.onInkChange(this.glyph.name);
      }
      this.liveStroke = null;
      this._stabPoint = null;
      this.render();
    },

    eraseAt: function (p) {
      var data = window.Store.getGlyph(this.glyph.name);
      // screen-consistent hit radius: ~18 px regardless of zoom
      var hitR = Math.max(this.penWidth * 0.6, 18 / this.s());
      var before = data.strokes.length;
      this._preSnapshot = this.snapshot();
      data.strokes = data.strokes.filter(function (s) {
        return !s.points.some(function (q) {
          var dx = p[0] - q[0], dy = p[1] - q[1];
          return dx * dx + dy * dy < hitR * hitR;
        });
      });
      if (data.strokes.length !== before) {
        this.pushUndo();
        window.Store.emit();
        if (this.onInkChange) this.onInkChange(this.glyph.name);
        this.render();
      } else {
        this._preSnapshot = null;
      }
    },

    // ---- history -------------------------------------------------------
    snapshot: function () {
      return JSON.stringify(window.Store.getGlyph(this.glyph.name).strokes);
    },
    pushUndo: function () {
      // snapshot BEFORE the change being made: callers snapshot pre-mutation
      this.undoStack.push(this._preSnapshot || this.snapshot());
      if (this.undoStack.length > 60) this.undoStack.shift();
      this.redoStack = [];
      this._preSnapshot = null;
    },
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
      this._preSnapshot = this.snapshot();
      window.Store.getGlyph(this.glyph.name).strokes = [];
      this.pushUndo();
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

      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = colBg;
      ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
      ctx.restore();
      if (!this.glyph) return;

      var self = this;
      var s = this.s();

      // fine grid when zoomed in (precision aid)
      if (this.zoom >= 1.5) {
        ctx.save();
        ctx.strokeStyle = colFaint;
        ctx.globalAlpha = 0.35;
        ctx.lineWidth = 1;
        var step = this.zoom >= 3 ? 50 : 100;
        var x0 = Math.floor(this.ox / step) * step;
        var y0 = Math.ceil(this.oy / step) * step;
        ctx.beginPath();
        for (var gx = x0; self.ux(gx) < self.cssW; gx += step) {
          ctx.moveTo(self.ux(gx), 0); ctx.lineTo(self.ux(gx), self.cssH);
        }
        for (var gy = y0; self.uy(gy) < self.cssH; gy -= step) {
          ctx.moveTo(0, self.uy(gy)); ctx.lineTo(self.cssW, self.uy(gy));
        }
        ctx.stroke();
        ctx.restore();
      }

      function hline(y, color, dash, label) {
        ctx.save();
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        if (dash) ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(0, self.uy(y));
        ctx.lineTo(self.cssW, self.uy(y));
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
        ctx.lineTo(self.ux(x), self.cssH);
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

      // dimmed guide character — guideSize is in FONT UNITS, scaled to px
      ctx.save();
      ctx.globalAlpha = this.guideOpacity;
      ctx.fillStyle = colInk;
      ctx.font = (this.guideSize * s) + "px " + GUIDE_FONTS;
      ctx.textBaseline = "alphabetic";
      ctx.fillText(this.glyph.guide, this.ux(0), this.uy(0));
      ctx.restore();

      // committed strokes + live stroke
      var strokes = window.Store.getGlyph(this.glyph.name).strokes.slice();
      if (this.liveStroke) strokes.push(this.liveStroke);

      var hasPressure = function (st) {
        return st.points.some(function (p) { return p.length > 2; });
      };

      ctx.save();
      ctx.fillStyle = colInk;
      ctx.strokeStyle = colInk;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      strokes.forEach(function (st) {
        if (!st.points.length) return;
        if (self.fillPreview || hasPressure(st)) {
          // faithful filled rendering (also used for pressure strokes)
          var poly = window.Outline.strokeToPolygon(st);
          if (!poly) return;
          ctx.beginPath();
          poly.forEach(function (p, i) {
            var x = self.ux(p[0]), y = self.uy(p[1]);
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          });
          ctx.closePath();
          ctx.fill("nonzero");
        } else {
          ctx.lineWidth = Math.max(1, st.width * s);
          var pts = window.Outline.smooth(st.points.slice(), 1);
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
        }
      });
      ctx.restore();
    }
  };

  window.Editor = Editor;
})();
