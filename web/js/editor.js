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
 *   - mouse / trackpad: draw with click-drag, wheel or pinch-gesture to zoom,
 *     middle-drag or hold Space to pan
 *   - touch: one finger draws (until a stylus is detected), two fingers
 *     always pan/zoom
 *   - stylus (Apple Pencil etc.): draws with optional pressure-variable
 *     width; once a pen is seen, bare fingers pan instead of drawing
 *     (palm rejection) unless "Finger draws" is re-enabled
 *
 * Tools: brush (freehand), line, rect, circle, eraser (whole-stroke or
 * partial) live here; the vector tools (select/transform, direct node
 * editing, Bézier pen) live in vectools.js and get the pointer events
 * routed to them.
 */
(function () {
  "use strict";

  var VIEW = { x0: -250, x1: 1350, yTop: 950, yBottom: -650 };
  // GlyphStudioGuide = a face the contributor loaded; Padauk = the bundled
  // guide font (web/fonts/), which shapes stacks the system fonts often can't
  var GUIDE_FONTS = '"GlyphStudioGuide", Padauk, "Myanmar MN", "Noto Sans Myanmar", "Myanmar Text", sans-serif';
  var ZOOM_MIN = 0.4, ZOOM_MAX = 6;
  var TAP_MS = 350, TAP_SLOP = 14;  // multi-finger tap tolerances

  function buzz(ms) {
    try { if (navigator.vibrate) navigator.vibrate(ms); } catch (e) {}
  }

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
    tool: "brush",    // brush | pen | select | direct | line | rect | circle | eraser
    snapEnabled: false,
    fillShape: false,  // pen/rect/circle commit as filled contours
    eraserMode: "partial", // "partial" splits strokes; "stroke" removes whole
    eraserSize: 60,    // font units (diameter)
    clipboard: [],     // copied strokes, shared across glyphs
    spacePan: false,   // Space held: any pointer pans
    hoverScr: null,    // last hover position (eraser ring)
    _eraseGesture: null,
    onToolChange: null,
    anchorMode: false, // drag mark-attachment anchors instead of drawing
    _dragAnchor: null, // {name} while an anchor is being dragged
    _lastAnchorTap: null, // {name, t} for double-tap-to-reset
    ghostName: null,   // another glyph's strokes shown as a style reference
    fillPreview: false,
    pressureEnabled: true,
    stabilizer: 3,     // 0 (off) … 10 (heavy)
    touchDraws: true,  // flips off automatically once a stylus is detected
    penSeen: false,
    touchSeen: false,  // first finger on the canvas (gesture-hint hook)
    liveStroke: null,
    _stabPoint: null,
    _rect: null,       // cached canvas rect: cleared on resize, refreshed per stroke
    _rafPending: false,
    pointers: {},      // pointerId -> {type, x, y} (screen px)
    gesture: null,     // {dist, mid:[px,py], startZoom, startOx, startOy}
    _multi: null,      // multi-finger tap tracking: {max, t0, moved}
    undoStack: [],
    redoStack: [],
    onInkChange: null, // callback(glyphName)
    onViewChange: null,
    onTouchSeen: null,

    init: function (canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.resize();
      var self = this;
      window.addEventListener("resize", function () { self.resize(); });
      // Re-fit when the surrounding layout changes size without a window
      // resize: soft keyboard, rotation, panels opening. Observing the
      // parent (not the canvas, whose inline px size we set ourselves)
      // avoids a feedback loop.
      if (window.ResizeObserver) {
        new ResizeObserver(function () { self.resize(); })
          .observe(canvas.parentElement);
      }
      window.addEventListener("scroll", function () { self._rect = null; }, true);

      canvas.addEventListener("pointerdown", function (e) { self.down(e); });
      canvas.addEventListener("pointermove", function (e) { self.move(e); });
      window.addEventListener("pointerup", function (e) { self.up(e); });
      window.addEventListener("pointercancel", function (e) { self.up(e); });
      canvas.addEventListener("pointerleave", function () {
        if (self.hoverScr) { self.hoverScr = null; self.render(); }
      });
      canvas.addEventListener("wheel", function (e) { self.wheel(e); }, { passive: false });
      canvas.style.touchAction = "none";
    },

    isVecTool: function () {
      return this.tool === "select" || this.tool === "direct" || this.tool === "pen";
    },

    /* Central tool switch: leaves any in-progress vector state cleanly. */
    setTool: function (t) {
      if (t === this.tool) return;
      if (window.VecTools) {
        if (this.tool === "pen" && window.VecTools.penActive()) {
          window.VecTools.penCancel(this);
        }
        window.VecTools.softReset();
      }
      this.liveStroke = null;
      this._stabPoint = null;
      this._eraseGesture = null;
      this.hoverScr = null;
      this.tool = t;
      if (this.anchorMode) this.setAnchorMode(false);
      if (this.onToolChange) this.onToolChange(t);
      this.render();
    },

    /* Vector tools may ask for a different tool (double-click → node editor). */
    requestTool: function (t) {
      this.tool = t;
      if (this.onToolChange) this.onToolChange(t);
      this.render();
    },

    /* Optional-grid + guide-line snapping for precise tools. */
    snapPoint: function (p) {
      if (!this.snapEnabled) return p;
      var g = 10;
      var x = Math.round(p[0] / g) * g;
      var y = Math.round(p[1] / g) * g;
      var t = Math.max(8 / this.s(), 6);
      [0, 550, 900, -600].forEach(function (gy) {
        if (Math.abs(p[1] - gy) < t) y = gy;
      });
      var adv = this.glyph
        ? (window.Store.getGlyph(this.glyph.name).advance || this.measureGuideAdvance())
        : 0;
      [0, adv].forEach(function (gx) {
        if (Math.abs(p[0] - gx) < t) x = gx;
      });
      return [x, y];
    },

    resize: function () {
      this._rect = null;
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
      this._dragAnchor = null;
      this._eraseGesture = null;
      this.undoStack = [];
      this.redoStack = [];
      if (window.VecTools) window.VecTools.reset();
      this.render();
    },

    setAnchorMode: function (on) {
      this.anchorMode = !!on;
      this.liveStroke = null;
      this._dragAnchor = null;
      this._stabPoint = null;
      if (on && window.VecTools) {
        if (this.tool === "pen" && window.VecTools.penActive()) {
          window.VecTools.penCancel(this);
        }
        window.VecTools.softReset();
      }
      this.render();
    },

    // ---- view transform ------------------------------------------------
    ux: function (x) { return (x - this.ox) * this.s(); },
    uy: function (y) { return (this.oy - y) * this.s(); },
    px2units: function (px, py) {
      return [this.ox + px / this.s(), this.oy - py / this.s()];
    },
    toScreen: function (e) {
      // Cached: getBoundingClientRect forces layout, and this runs once per
      // coalesced sample — up to 240 Hz under a stylus. The cache is cleared
      // on resize/scroll and refreshed at every pointerdown, and the canvas
      // cannot move mid-stroke (touch-action none, no page scroll).
      var rect = this._rect ||
        (this._rect = this.canvas.getBoundingClientRect());
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
      this.requestRender();
      if (this.onViewChange) this.onViewChange();
    },

    /* Collapse per-pointer-sample renders into one per animation frame —
       wheel spins and pinches arrive far faster than the screen refreshes. */
    requestRender: function () {
      if (this._rafPending) return;
      this._rafPending = true;
      var self = this;
      window.requestAnimationFrame(function () {
        self._rafPending = false;
        self.render();
      });
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
      this._rect = this.canvas.getBoundingClientRect(); // fresh per stroke
      var scr = this.toScreen(e);
      // Register the pointer BEFORE capturing: setPointerCapture throws if the
      // browser no longer considers the pointer active, and losing the record
      // would strand a finger and break pinch/tap tracking.
      this.pointers[e.pointerId] = { type: e.pointerType, x: scr[0], y: scr[1] };
      try {
        if (this.canvas.setPointerCapture) this.canvas.setPointerCapture(e.pointerId);
      } catch (err) { /* pointer already gone — bookkeeping above still holds */ }

      if (e.pointerType === "pen" && !this.penSeen) {
        this.penSeen = true;
        this.touchDraws = false;
        if (this.onPenDetected) this.onPenDetected();
      }
      if (e.pointerType === "touch" && !this.touchSeen) {
        this.touchSeen = true;
        if (this.onTouchSeen) this.onTouchSeen();
      }

      // middle mouse button or held Space: temporary hand tool
      if (e.button === 1 || this.spacePan) {
        this.pointers[e.pointerId].panning = true;
        return;
      }

      var touches = this.activeTouches();
      if (e.pointerType === "touch") {
        // track the gesture so a quick multi-finger tap can mean undo/redo
        if (!this._multi) this._multi = { max: 0, t0: e.timeStamp, moved: false };
        this._multi.max = Math.max(this._multi.max, touches.length);
      }
      if (e.pointerType === "touch" && touches.length >= 2) {
        // A second finger means pinch/pan — but never at the cost of work.
        // A brush stroke that was genuinely underway (not the split-second
        // start of a two-finger gesture) is committed rather than destroyed:
        // a resting palm or thumb used to eat it. A two-finger tap right
        // after still cancels it — the tap's undo removes what we commit.
        if (this.tool === "brush" && this.liveStroke && this._multi &&
            this.liveStroke.points.length >= 2 &&
            (e.timeStamp - this._multi.t0 > 250 ||
             this.strokeLength(this.liveStroke.points) > 120)) {
          this.pushUndo();
          window.Store.getGlyph(this.glyph.name).strokes.push(this.liveStroke);
          window.Store.emit();
          if (this.onInkChange) this.onInkChange(this.glyph.name);
        }
        // A part-done erase has already mutated the ink; seal it as an undo
        // step instead of dropping the snapshot (which left the deletion in
        // the store with no history entry).
        if (this._eraseGesture && this._eraseGesture.changed) {
          this._preSnapshot = this._eraseGesture.snap;
          this.pushUndo();
          window.Store.emit();
          if (this.onInkChange) this.onInkChange(this.glyph.name);
        }
        this.liveStroke = null;
        this._stabPoint = null;
        this._eraseGesture = null;
        if (window.VecTools) window.VecTools.cancelDrag(this);
        var a = touches[0], b = touches[1];
        this.gesture = {
          dist: Math.hypot(a.x - b.x, a.y - b.y),
          mid: [(a.x + b.x) / 2, (a.y + b.y) / 2]
        };
        this.render();
        return;
      }

      if (this.anchorMode) {
        // drag an anchor; double-tap resets it to auto; empty press pans
        var hit = this.anchorAt(scr[0], scr[1]);
        if (hit) {
          var lastTap = this._lastAnchorTap;
          this._lastAnchorTap = { name: hit.name, t: e.timeStamp };
          if (lastTap && lastTap.name === hit.name &&
              e.timeStamp - lastTap.t < 400) {
            this.resetAnchor(hit.name);
            return;
          }
          this._preSnapshot = this.snapshot();
          this._dragAnchor = { name: hit.name };
        } else {
          this.pointers[e.pointerId].panning = true;
        }
        return;
      }

      var drawsInk = e.pointerType !== "touch" || this.touchDraws;
      if (!drawsInk) {
        // single-finger pan mode (stylus workflow)
        this.pointers[e.pointerId].panning = true;
        return;
      }

      if (this.isVecTool()) {
        window.VecTools.down(e, this);
        return;
      }

      var p = this.toUnits(e);
      if (this.tool === "eraser") {
        this._eraseGesture = { changed: false, snap: this.snapshot() };
        this.eraseAt(p);
        return;
      }
      if (this.tool === "line" || this.tool === "circle" || this.tool === "rect") {
        this._shapeStart = this.snapPoint(p);
        this.liveStroke = { width: this.penWidth, points: [this._shapeStart] };
        this.render();
        return;
      }
      this._stabPoint = p.slice(0, 2);
      this.liveStroke = { width: this.penWidth, points: [this.inputPoint(e, p)] };
      this.render();
    },

    rectPoints: function (a, b) {
      // closed loop: back to the start so the caps seal the corner
      return [
        [a[0], a[1]], [b[0], a[1]], [b[0], b[1]], [a[0], b[1]], [a[0], a[1]]
      ];
    },

    circlePoints: function (c, edge) {
      var r = Math.max(4, Math.hypot(edge[0] - c[0], edge[1] - c[1]));
      var n = Math.max(24, Math.min(72, Math.round(r / 10)));
      var pts = [];
      for (var i = 0; i <= n; i++) {
        var a = (i / n) * Math.PI * 2;
        pts.push([Math.round(c[0] + r * Math.cos(a)),
                  Math.round(c[1] + r * Math.sin(a))]);
      }
      return pts;
    },

    strokeLength: function (pts) {
      var L = 0;
      for (var i = 1; i < pts.length; i++) {
        L += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
      }
      return L;
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
          if (this._multi &&
              (Math.abs(dist - this.gesture.dist) > TAP_SLOP ||
               Math.hypot(mid[0] - this.gesture.mid[0],
                          mid[1] - this.gesture.mid[1]) > TAP_SLOP)) {
            this._multi.moved = true;   // a real pinch/pan, not a tap
          }
          this.zoomAt(mid[0], mid[1], factor);
          // pan by midpoint drift
          var s = this.s();
          this.ox -= (mid[0] - this.gesture.mid[0]) / s;
          this.oy += (mid[1] - this.gesture.mid[1]) / s;
          this.clampView();
          this.gesture.dist = dist;
          this.gesture.mid = mid;
          this.requestRender();
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
        this.requestRender();
        return;
      }

      if (rec) { rec.x = scr[0]; rec.y = scr[1]; }
      var p = this.toUnits(e);

      if (this._dragAnchor) {
        var gd = window.Store.getGlyph(this.glyph.name);
        if (!gd.anchors) gd.anchors = {};
        gd.anchors[this._dragAnchor.name] = [p[0], p[1]];
        this.render();
        return;
      }
      if (this.anchorMode) return;

      if (this.isVecTool()) {
        window.VecTools.move(e, this);
        return;
      }

      if (this.tool === "eraser") {
        // ring cursor follows the pointer even when hovering
        this.hoverScr = scr;
        if (e.buttons && this._eraseGesture) this.eraseAt(p);
        else this.requestRender();
        return;
      }
      if (!this.liveStroke) return;

      if (this.tool === "line") {
        var lp = this.snapPoint(p);
        if (e.shiftKey) {
          // constrain to 45° steps
          var dx = p[0] - this._shapeStart[0], dy = p[1] - this._shapeStart[1];
          var ang = Math.round(Math.atan2(dy, dx) / (Math.PI / 4)) * (Math.PI / 4);
          var len = Math.hypot(dx, dy);
          lp = [Math.round(this._shapeStart[0] + len * Math.cos(ang)),
                Math.round(this._shapeStart[1] + len * Math.sin(ang))];
        }
        this.liveStroke.points = [this._shapeStart, lp];
        this.render();
        return;
      }
      if (this.tool === "rect") {
        var rp = this.snapPoint(p);
        if (e.shiftKey) {
          // square
          var w = rp[0] - this._shapeStart[0], h = rp[1] - this._shapeStart[1];
          var side = Math.max(Math.abs(w), Math.abs(h));
          rp = [this._shapeStart[0] + (w < 0 ? -side : side),
                this._shapeStart[1] + (h < 0 ? -side : side)];
        }
        this.liveStroke.points = this.rectPoints(this._shapeStart, rp);
        this.render();
        return;
      }
      if (this.tool === "circle") {
        this.liveStroke.points = this.circlePoints(this._shapeStart, this.snapPoint(p));
        this.render();
        return;
      }

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
      this.requestRender();
    },

    up: function (e) {
      delete this.pointers[e.pointerId];
      if (this.activeTouches().length < 2) this.gesture = null;

      // multi-finger tap shortcuts, resolved once every finger is up:
      // two fingers = undo, three = redo (the Procreate/Notes convention)
      if (e.pointerType === "touch" && this._multi &&
          !Object.keys(this.pointers).length) {
        var m = this._multi;
        this._multi = null;
        if (!m.moved && m.max >= 2 && e.timeStamp - m.t0 < TAP_MS) {
          if (m.max === 2) { this.undo(); buzz(12); }
          else if (m.max >= 3) { this.redo(); buzz([12, 40, 12]); }
          this.liveStroke = null;
          this.render();
          return;
        }
      }

      if (!this.glyph) return;
      if (this._dragAnchor) {
        this._dragAnchor = null;
        this.pushUndo();          // uses the pre-drag snapshot
        window.Store.emit();
        this.render();
        return;
      }
      if (this.isVecTool()) {
        window.VecTools.up(e, this);
        return;
      }
      if (this._eraseGesture) {
        var eg = this._eraseGesture;
        this._eraseGesture = null;
        if (eg.changed) {
          this._preSnapshot = eg.snap;   // one undo step per erase drag
          this.pushUndo();
          window.Store.emit();
          if (this.onInkChange) this.onInkChange(this.glyph.name);
        }
        this.render();
        return;
      }
      if (!this.liveStroke) return;
      if (this.liveStroke.points.length >= 1) {
        // shapes drawn with Fill on become closed filled contours
        if (this.fillShape && (this.tool === "rect" || this.tool === "circle") &&
            this.liveStroke.points.length >= 4) {
          var pts = this.liveStroke.points.slice(0, -1); // drop closing dup
          this.liveStroke = { fill: true, points: pts };
        }
        this.pushUndo();
        window.Store.getGlyph(this.glyph.name).strokes.push(this.liveStroke);
        window.Store.emit();
        if (e.pointerType === "touch") buzz(8);  // "stroke landed" feedback
        if (this.onInkChange) this.onInkChange(this.glyph.name);
      }
      this.liveStroke = null;
      this._stabPoint = null;
      this.render();
    },

    eraserRadius: function () {
      // never smaller than ~14 screen px so it stays tappable when zoomed out
      return Math.max(this.eraserSize / 2, 14 / this.s());
    },

    /* Erase under p. "stroke" mode removes whole strokes (the classic
     * behaviour); "partial" rubs points out and splits strokes in two like a
     * raster eraser. Undo is one step per drag gesture (see down/up). */
    eraseAt: function (p) {
      var data = window.Store.getGlyph(this.glyph.name);
      var hitR = this.eraserRadius();
      var hitR2 = hitR * hitR;
      var changed = false;

      function inPoly(pts, x, y) {
        var inside = false;
        for (var i = 0, j = pts.length - 1; i < pts.length; j = i++) {
          var xi = pts[i][0], yi = pts[i][1], xj = pts[j][0], yj = pts[j][1];
          if ((yi > y) !== (yj > y) &&
              x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside;
        }
        return inside;
      }
      var near = function (q, r2) {
        var dx = p[0] - q[0], dy = p[1] - q[1];
        return dx * dx + dy * dy < r2;
      };
      var fillHit = function (st) {
        return inPoly(st.points, p[0], p[1]) ||
               st.points.some(function (q) { return near(q, hitR2); });
      };

      if (this.eraserMode === "stroke") {
        var before = data.strokes.length;
        data.strokes = data.strokes.filter(function (s) {
          if (s.fill) return !fillHit(s);
          // fat strokes stay tappable anywhere on their body
          var r2 = Math.max(hitR2, Math.pow((s.width || 0) * 0.6, 2));
          return !s.points.some(function (q) { return near(q, r2); });
        });
        changed = data.strokes.length !== before;
      } else {
        // sparse polylines (line tool, pen flattening at low zoom) must be
        // densified first, or the rub only hits the stored points instead of
        // the drawn segments between them
        var densify = function (pts, maxGap) {
          var out2 = [pts[0]];
          for (var i = 1; i < pts.length; i++) {
            var a = pts[i - 1], b = pts[i];
            var d = Math.hypot(b[0] - a[0], b[1] - a[1]);
            var n = Math.ceil(d / maxGap);
            for (var k = 1; k < n; k++) {
              var t = k / n;
              var q = [Math.round(a[0] + (b[0] - a[0]) * t),
                       Math.round(a[1] + (b[1] - a[1]) * t)];
              if (a.length > 2 && b.length > 2) {
                q.push(Math.round(a[2] + (b[2] - a[2]) * t));
              }
              out2.push(q);
            }
            out2.push(b);
          }
          return out2;
        };
        var segNear = function (pts) {
          for (var i = 1; i < pts.length; i++) {
            var a = pts[i - 1], b = pts[i];
            var vx = b[0] - a[0], vy = b[1] - a[1];
            var l2 = vx * vx + vy * vy;
            var t = l2 ? ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / l2 : 0;
            t = Math.max(0, Math.min(1, t));
            var dx = p[0] - (a[0] + vx * t), dy = p[1] - (a[1] + vy * t);
            if (dx * dx + dy * dy < hitR2) return true;
          }
          return pts.length === 1 && near(pts[0], hitR2);
        };
        var out = [];
        data.strokes.forEach(function (st) {
          if (st.fill) {
            // filled contours cannot be split — rub deletes them whole
            if (fillHit(st)) changed = true; else out.push(st);
            return;
          }
          if (!segNear(st.points)) { out.push(st); return; }
          var runs = [], cur = [];
          densify(st.points, Math.max(8, hitR * 0.5)).forEach(function (q) {
            if (near(q, hitR2)) {
              if (cur.length) { runs.push(cur); cur = []; }
            } else {
              cur.push(q);
            }
          });
          if (cur.length) runs.push(cur);
          changed = true;
          runs.forEach(function (r) {
            // the split parts are plain polylines again (bez no longer applies)
            if (r.length >= 2) out.push({ width: st.width, points: r });
          });
        });
        data.strokes = out;
      }

      if (changed && this._eraseGesture) this._eraseGesture.changed = true;
      this.render();
    },

    // ---- anchors ---------------------------------------------------------
    anchorList: function () {
      if (!this.glyph) return [];
      return window.Anchors.listFor(
        this.glyph, window.Store.getGlyph(this.glyph.name));
    },

    anchorAt: function (px, py) {
      var list = this.anchorList();
      for (var i = 0; i < list.length; i++) {
        var dx = px - this.ux(list[i].x);
        var dy = py - this.uy(list[i].y);
        if (dx * dx + dy * dy <= 18 * 18) return list[i];
      }
      return null;
    },

    resetAnchor: function (name) {
      var g = window.Store.getGlyph(this.glyph.name);
      if (!g.anchors || !(name in g.anchors)) return;
      this._preSnapshot = this.snapshot();
      delete g.anchors[name];
      if (!Object.keys(g.anchors).length) delete g.anchors;
      this._dragAnchor = null;
      this.pushUndo();
      window.Store.emit();
      this.render();
    },

    // ---- history -------------------------------------------------------
    snapshot: function () {
      var g = window.Store.getGlyph(this.glyph.name);
      return JSON.stringify({ strokes: g.strokes, anchors: g.anchors || null });
    },
    restore: function (snap) {
      var g = window.Store.getGlyph(this.glyph.name);
      var s = JSON.parse(snap);
      if (Object.prototype.toString.call(s) === "[object Array]") {
        g.strokes = s; // legacy strokes-only snapshot
        return;
      }
      g.strokes = s.strokes || [];
      if (s.anchors) g.anchors = s.anchors; else delete g.anchors;
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
      this.restore(this.undoStack.pop());
      // selection/node indices may now point at different strokes
      if (window.VecTools) window.VecTools.softReset();
      window.Store.emit();
      if (this.onInkChange) this.onInkChange(this.glyph.name);
      this.render();
    },
    redo: function () {
      if (!this.redoStack.length || !this.glyph) return;
      this.undoStack.push(this.snapshot());
      this.restore(this.redoStack.pop());
      if (window.VecTools) window.VecTools.softReset();
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

    /* Shift all ink so it sits horizontally centered in the advance width. */
    centerInk: function () {
      if (!this.glyph) return;
      var data = window.Store.getGlyph(this.glyph.name);
      if (!data.strokes.length) return;
      var polys = window.Outline.glyphPolygons(data);
      var b = window.Outline.bounds(polys);
      if (!b) return;
      var advance = data.advance || this.measureGuideAdvance();
      var dx = Math.round((advance - (b.xMax - b.xMin)) / 2 - b.xMin);
      if (!dx) return;
      this._preSnapshot = this.snapshot();
      data.strokes.forEach(function (s) {
        s.points.forEach(function (p) { p[0] += dx; });
      });
      this.pushUndo();
      window.Store.emit();
      if (this.onInkChange) this.onInkChange(this.glyph.name);
      this.render();
    },

    /* Append ready-made strokes (e.g. from an SVG import) with undo. */
    addStrokes: function (strokes) {
      if (!this.glyph || !strokes || !strokes.length) return;
      this._preSnapshot = this.snapshot();
      var dst = window.Store.getGlyph(this.glyph.name);
      dst.strokes = dst.strokes.concat(strokes);
      this.pushUndo();
      window.Store.emit();
      if (this.onInkChange) this.onInkChange(this.glyph.name);
      this.render();
    },

    /* Copy all strokes from another glyph onto this one (deep copy). */
    copyFrom: function (srcName) {
      if (!this.glyph || srcName === this.glyph.name) return;
      var src = window.Store.getGlyph(srcName);
      if (!src.strokes.length) return;
      this._preSnapshot = this.snapshot();
      var dst = window.Store.getGlyph(this.glyph.name);
      dst.strokes = dst.strokes.concat(JSON.parse(JSON.stringify(src.strokes)));
      this.pushUndo();
      window.Store.emit();
      if (this.onInkChange) this.onInkChange(this.glyph.name);
      this.render();
    },

    /* Does the guide face shape Myanmar (form stacks)? See GuideFont. */
    guideShapesStacks: function () {
      return !window.GuideFont || window.GuideFont.shapesStacks(this.ctx);
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

      // ghost: another drawn glyph as a translucent style reference
      if (this.ghostName && this.ghostName !== this.glyph.name &&
          window.Store.hasInk(this.ghostName)) {
        ctx.save();
        ctx.globalAlpha = 0.3;
        ctx.strokeStyle = colAccent;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        window.Store.getGlyph(this.ghostName).strokes.forEach(function (st) {
          if (!st.points.length) return;
          ctx.lineWidth = Math.max(1, (st.width || 2) * s);
          ctx.beginPath();
          st.points.forEach(function (p, i) {
            var x = self.ux(p[0]), y = self.uy(p[1]);
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          });
          if (st.points.length === 1) {
            ctx.lineTo(self.ux(st.points[0][0]) + 0.1, self.uy(st.points[0][1]));
          }
          ctx.stroke();
        });
        ctx.restore();
      }

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
        if (st.fill || self.fillPreview || hasPressure(st)) {
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

      // eraser: dashed ring showing the rub radius
      if (this.tool === "eraser" && this.hoverScr) {
        ctx.save();
        ctx.strokeStyle = colAccent;
        ctx.setLineDash([4, 3]);
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.arc(this.hoverScr[0], this.hoverScr[1],
                this.eraserRadius() * s, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
      }

      // selection boxes, node handles, pen path preview
      if (this.isVecTool() && window.VecTools) window.VecTools.render(this, ctx);

      if (this.anchorMode) this.renderAnchors(ctx, colAccent, colBg);
    },

    /* Anchor handles: solid ring = dragged (stored), dashed ring = auto. */
    renderAnchors: function (ctx, colAccent, colBg) {
      var self = this;
      this.anchorList().forEach(function (a) {
        var x = self.ux(a.x), y = self.uy(a.y);
        ctx.save();
        ctx.lineWidth = 2;
        ctx.strokeStyle = colAccent;
        ctx.fillStyle = colBg;
        if (!a.manual) ctx.setLineDash([3, 3]);
        ctx.beginPath();
        ctx.arc(x, y, 9, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.moveTo(x - 14, y); ctx.lineTo(x + 14, y);
        ctx.moveTo(x, y - 14); ctx.lineTo(x, y + 14);
        ctx.stroke();
        ctx.fillStyle = colAccent;
        ctx.font = "11px system-ui, sans-serif";
        ctx.fillText(a.name, x + 13, y - 11);
        ctx.restore();
      });
    }
  };

  window.Editor = Editor;
})();
