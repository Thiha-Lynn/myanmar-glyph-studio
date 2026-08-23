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
  var HISTORY_GLYPHS = 12;   // glyphs whose undo history is kept in memory
  var HISTORY_STEPS = 20;    // steps kept for a glyph you have left
  var TAPER_FULL = 2.2;      // screen px per ms counted as "a fast sweep"

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
    pressureAmount: 10, // 0 … 10 — how far pressure may move the width
    tiltAmount: 0,     // 0 … 10 — laying an Apple Pencil down broadens it
    stabilizer: 3,     // 0 (off) … 10 (heavy) — see js/stabilizer.js
    taper: 0,          // 0 (off) … 10: speed varies the width, for people
                       // drawing with a mouse or a finger instead of a pen
    touchDraws: true,  // flips off automatically once a stylus is detected
    penSeen: false,
    touchSeen: false,  // first finger on the canvas (gesture-hint hook)
    liveStroke: null,
    _stab: null,       // Stabilizer for the stroke being drawn
    _rawScr: null,     // where the pointer really is, screen px (the leash)
    _speed: 0,         // smoothed pointer speed, SCREEN px per ms
    _lastSample: null, // {x, y, t} of the previous raw sample, for the speed
    _shiftAnchor: null,// index the Shift-straight segment hinges on
    _penEraser: null,  // {id, tool} while the stylus's eraser end is down
    _histories: {},    // glyph name -> {undo, redo}: history survives a switch
    _histOrder: [],    // LRU of the glyph names holding history
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
      this.endStroke();
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

    /*
     * Switching glyphs used to throw the undo history away, so a wrong
     * turn discovered after a hop to the next letter was unrecoverable.
     * Each glyph now keeps its own stacks; the last HISTORY_GLYPHS of them
     * stay in memory (snapshots are whole-glyph JSON, so the count is
     * bounded on purpose) and the oldest is dropped.
     */
    setGlyph: function (g) {
      if (this.glyph && this.glyph.name !== g.name) this.stashHistory();
      this.glyph = g;
      this.liveStroke = null;
      this._dragAnchor = null;
      this._eraseGesture = null;
      var h = this._histories[g.name];
      this.undoStack = h ? h.undo : [];
      this.redoStack = h ? h.redo : [];
      if (window.VecTools) window.VecTools.reset();
      this.render();
    },

    stashHistory: function () {
      var name = this.glyph.name;
      if (!this.undoStack.length && !this.redoStack.length) {
        delete this._histories[name];
        return;
      }
      // Snapshots are whole-glyph JSON. Sixty of them per glyph is fine
      // while you are on it; twelve glyphs' worth of sixty is not, so a
      // stashed history keeps only its most recent steps.
      this._histories[name] = {
        undo: this.undoStack.slice(-HISTORY_STEPS),
        redo: this.redoStack.slice(-HISTORY_STEPS)
      };
      var order = this._histOrder;
      var at = order.indexOf(name);
      if (at >= 0) order.splice(at, 1);
      order.push(name);
      while (order.length > HISTORY_GLYPHS) delete this._histories[order.shift()];
    },

    setAnchorMode: function (on) {
      this.anchorMode = !!on;
      this.liveStroke = null;
      this._dragAnchor = null;
      this.endStroke();
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
      // Flip the stylus over: the eraser end of a Wacom/Surface pen reports
      // button 5 (buttons bit 32). Borrow the eraser for as long as that
      // end is down, then hand the tool back.
      if (e.pointerType === "pen" && (e.button === 5 || (e.buttons & 32)) &&
          this.tool !== "eraser" && !this.anchorMode) {
        this._penEraser = { id: e.pointerId, tool: this.tool };
        this.setTool("eraser");
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
          this.flushStab();
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
        this.endStroke();
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
      this.beginStroke(e, p);
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

    // ---- freehand input: stabilizer, width dynamics ---------------------
    /* A rope for this stroke, at this zoom. Null when steadying is off. */
    newStab: function (p) {
      if (!window.Stabilizer || !(this.stabilizer > 0)) return null;
      return window.Stabilizer.create({
        strength: this.stabilizer,
        unitsPerPx: 1 / this.s(),
        start: p
      });
    },

    beginStroke: function (e, p) {
      this._lastSample = null;
      // Seed the speed at a middling value: measured from zero, the first
      // points of every tapered stroke would come out at full thickness
      // before the real speed caught up, blobbing each entry.
      this._speed = TAPER_FULL * 0.35;
      this._shiftAnchor = null;
      this._rawScr = this.toScreen(e);
      this._stab = this.newStab(p);
      this.liveStroke = { width: this.penWidth, points: [this.strokePoint(p, e)] };
    },

    endStroke: function () {
      this._stab = null;
      this._rawScr = null;
      this._shiftAnchor = null;
      this._lastSample = null;
      this._speed = 0;
    },

    /* Pointer speed in SCREEN px per ms — a property of the hand, so it
       must not change meaning when the view is zoomed. */
    trackSpeed: function (e, scr) {
      var t = e.timeStamp || 0;
      var prev = this._lastSample;
      this._lastSample = { x: scr[0], y: scr[1], t: t };
      if (!prev) return;
      var dt = t - prev.t;
      if (dt <= 0) return;
      var v = Math.hypot(scr[0] - prev.x, scr[1] - prev.y) / dt;
      this._speed += (v - this._speed) * 0.3;
    },

    /*
     * One stored point, with its width. A stylus gives real pressure;
     * everyone else can have SPEED stand in for it — slow means pressing
     * in, fast means flicking away, which is how a brush behaves and how
     * the strokes of a Myanmar letter are actually written. Both land in
     * the same optional third element, which outline.js and the Python
     * pipeline already read.
     */
    /*
     * How far the stylus is laid over, 0 (upright) … 1 (flat on the
     * glass). Safari gives Apple Pencil's altitudeAngle in radians;
     * Chromium-family browsers give tiltX/tiltY in degrees. Both are
     * read, because an iPad and a Wacom should feel the same.
     */
    tiltOf: function (e) {
      if (!e) return 0;
      if (typeof e.altitudeAngle === "number" && isFinite(e.altitudeAngle)) {
        return Math.max(0, Math.min(1, 1 - e.altitudeAngle / (Math.PI / 2)));
      }
      if (typeof e.tiltX === "number" && (e.tiltX || e.tiltY)) {
        return Math.max(0, Math.min(1, Math.hypot(e.tiltX, e.tiltY) / 90));
      }
      return 0;
    },

    strokePoint: function (pt, e) {
      var w = null;
      var pen = e && e.pointerType === "pen";
      if (this.pressureEnabled && pen && e.pressure > 0) {
        // amount 10 is the curve the studio always had (0.35 + 1.3p);
        // lower amounts pull it toward a constant width, for pens (and
        // hands) with a narrow usable range
        var k = Math.max(0, Math.min(10, this.pressureAmount)) / 10;
        w = this.penWidth * (1 + k * (1.3 * e.pressure - 0.65));
      } else if (this.taper > 0) {
        var k = this.taper / 10;
        var vn = Math.min(1, this._speed / TAPER_FULL);
        w = this.penWidth *
          Math.max(0.4, Math.min(1.5, 1 + k * (0.45 - 0.9 * vn)));
      }
      // Tilt broadens the stroke the way laying a broad nib over does.
      // It multiplies whatever width dynamic is already in play, so a
      // stylus can use pressure and tilt together.
      if (pen && this.tiltAmount > 0) {
        var t = this.tiltOf(e);
        if (t > 0) {
          w = (w == null ? this.penWidth : w) *
            (1 + (this.tiltAmount / 10) * t * 0.6);
        }
      }
      var out = [Math.round(pt[0]), Math.round(pt[1])];
      if (w != null) out.push(Math.max(2, Math.round(w)));
      return out;
    },

    /*
     * Hold Shift while brushing and the stroke runs dead straight from
     * where Shift went down to the pointer — the stems and cross-bars of
     * a letter, drawn by hand but true. Let go and freehand resumes from
     * the end of the straight run.
     */
    shiftSegment: function (raw) {
      var pts = this.liveStroke.points;
      if (this._shiftAnchor == null) {
        this.flushStab();          // spend the rope's lag before hinging
        this._shiftAnchor = pts.length - 1;
      }
      pts.length = this._shiftAnchor + 1;
      var prev = pts[pts.length - 1];
      var end = [Math.round(raw[0]), Math.round(raw[1])];
      if (prev.length > 2) end.push(prev[2]);
      pts.push(end);
    },

    releaseShift: function (raw) {
      this._shiftAnchor = null;
      this._stab = this.newStab(raw);
    },

    /* Append whatever the rope is still holding, so a stroke ends where
       the hand lifted instead of one rope-length behind it. */
    flushStab: function () {
      if (!this._stab || !this.liveStroke || this._shiftAnchor != null) return;
      var pts = this.liveStroke.points;
      var prev = pts[pts.length - 1];
      var w = prev && prev.length > 2 ? prev[2] : null;
      this._stab.finish().forEach(function (q) {
        var out = [Math.round(q[0]), Math.round(q[1])];
        if (w != null) out.push(w);
        pts.push(out);
      });
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

      // A hovering Apple Pencil (M2 and later) announces itself before it
      // touches down: arm palm rejection then, rather than making the
      // first stroke the one that discovers it.
      if (e.pointerType === "pen" && !this.penSeen) {
        this.penSeen = true;
        this.touchDraws = false;
        if (this.onPenDetected) this.onPenDetected();
      }
      if (rec) { rec.x = scr[0]; rec.y = scr[1]; }
      this.hoverScr = scr;    // size ring + the corner coordinate readout
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
      if (!this.liveStroke) {
        // hovering with the brush: keep the nib ring under the cursor
        if (this.tool === "brush") this.requestRender();
        return;
      }

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
        var ev = events[i];
        var evScr = this.toScreen(ev);
        this.trackSpeed(ev, evScr);
        this._rawScr = evScr;
        // unrounded: the stabilizer works below one font unit
        var raw = this.px2units(evScr[0], evScr[1]);
        if (e.shiftKey) { this.shiftSegment(raw); continue; }
        if (this._shiftAnchor != null) this.releaseShift(raw);
        var got = this._stab ? this._stab.push(raw) : [raw];
        for (var j = 0; j < got.length; j++) {
          var pt = this.strokePoint(got[j], ev);
          var q = pts[pts.length - 1];
          var dx = pt[0] - q[0], dy = pt[1] - q[1];
          if (dx * dx + dy * dy > minDist2) pts.push(pt);
        }
      }
      this.requestRender();
    },

    up: function (e) {
      // A flipped stylus borrowed the eraser (see down): give the tool
      // back however this gesture ends — but only when it is the PEN
      // lifting, or a resting finger coming up would end the erase.
      var back = null;
      if (this._penEraser && this._penEraser.id === e.pointerId) {
        back = this._penEraser.tool;
        this._penEraser = null;
      }
      this.upGesture(e);
      if (back) this.setTool(back);
    },

    upGesture: function (e) {
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
      this.flushStab();
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
      this.endStroke();
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

    /*
     * What a font maker needs to see about the glyph in front of them:
     * the ink's bounds, the two sidebearings, and whether anything has
     * climbed above the ascender or dropped below the descender — which
     * the build validates and rejects far later, in a report, long after
     * the drawing that caused it is out of mind.
     */
    metrics: function () {
      if (!this.glyph) return null;
      var data = window.Store.getGlyph(this.glyph.name);
      var advance = data.advance || this.measureGuideAdvance();
      var b = window.Outline.bounds(window.Outline.glyphPolygons(data));
      if (!b) return { advance: advance, empty: true };
      return {
        advance: advance,
        empty: false,
        left: Math.round(b.xMin),
        right: Math.round(advance - b.xMax),
        width: Math.round(b.xMax - b.xMin),
        top: Math.round(b.yMax),
        bottom: Math.round(b.yMin),
        overAscender: b.yMax > 900,
        underDescender: b.yMin < -600
      };
    },

    /* Set the advance from the ink, giving it the same sidebearing on
       both sides as it already has on the left. */
    fitAdvance: function () {
      var m = this.metrics();
      if (!m || m.empty) return null;
      var data = window.Store.getGlyph(this.glyph.name);
      var side = Math.max(0, m.left);
      data.advance = Math.round(m.left + m.width + side);
      window.Store.emit();
      if (this.onInkChange) this.onInkChange(this.glyph.name);
      this.render();
      return data.advance;
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
    /*
     * Where the guide face actually puts its letters.
     *
     * The canvas has always drawn a line at 550 labelled "body", which is
     * the height TOP MARKS attach at (json_to_ufo's BODY). Read as a
     * height to draw up to — which is how a line across the canvas reads
     * — it is about 100 units too tall: measured, every Myanmar consonant
     * in Padauk tops out at 439–449 per 1000 em, and this project's own
     * font, traced against that same guide with no line to aim at, came
     * out ranging 420–458.
     *
     * So measure the guide face itself: render a spread of consonants
     * offscreen and read the ink's extremes. One line is honest for the
     * whole alphabet because Myanmar has NO overshoot — measured in
     * Padauk, round letters (ဝ ဂ ပ င ဒ သ) and flat ones (က ခ တ မ လ)
     * share their extremes exactly, unlike Latin, where an O must
     * overshoot an H. Works for a loaded guide font too, which is the
     * point: trace any face and the line follows it.
     */
    SAMPLE_LETTERS: "ကခဂငစဆညတထနပဖမလဝသဟအ",

    /*
     * Which letters this glyph should line up with. The inventory also
     * carries 188 Latin entries, and a Myanmar consonant height is the
     * wrong target for a capital H — Latin has two heights of its own,
     * and punctuation has no shared one at all.
     *
     * The Latin samples are FLAT letters only, because Latin (unlike
     * Myanmar) really does overshoot: measured in Padauk, H E X top at
     * 628 while O reaches 640, and x n u sit at 435-445 while o and v
     * round past them. A line at the round height would have every flat
     * letter drawn 12 units tall.
     */
    bandSample: function () {
      var cp = this.glyph && this.glyph.cp;
      if (!cp || cp >= 0x1000) return this.SAMPLE_LETTERS;
      var g = this.glyph.group || "";
      if (g === "latinUpper" || g === "latinDigits") return "HEX";
      if (g === "latinLower") return "xnu";
      if (g === "latinExtraLetters") {
        return this.glyph.guide &&
          this.glyph.guide === this.glyph.guide.toUpperCase() ? "HEX" : "xnu";
      }
      return null;   // punctuation and symbols share no height worth drawing
    },

    measureGuideBand: function () {
      var sample = this.bandSample();
      if (!sample) return null;
      var key = (window.GuideFont && window.GuideFont.isCustom() ?
                 "custom" : "padauk") + "|" + this.guideSize + "|" + sample;
      if (this._bandKey === key && this._band) return this._band;
      var band = null;
      try {
        var size = 480;                       // px; 1 px is ~2 font units
        var pad = Math.round(size * 0.9);
        var c = document.createElement("canvas");
        c.width = Math.round(size * 2.2);
        c.height = Math.round(size * 2.4);
        var g = c.getContext("2d", { willReadFrequently: true });
        g.fillStyle = "#000";
        g.textBaseline = "alphabetic";
        g.font = size + "px " + GUIDE_FONTS;
        var baseY = c.height - pad;
        // all of them at the same place: only the vertical extremes matter
        sample.split("").forEach(function (ch) {
          g.fillText(ch, 4, baseY);
        });
        var data = g.getImageData(0, 0, c.width, c.height).data;
        // half coverage, not any coverage: the antialiased fringe is
        // roughly a pixel wide, and at any lower threshold the line comes
        // out a fringe too high (measured 456 against a known 448)
        var top = -1;
        for (var y = 0; y < c.height && top < 0; y++) {
          for (var x = 0; x < c.width; x++) {
            if (data[(y * c.width + x) * 4 + 3] >= 128) { top = y; break; }
          }
        }
        if (top >= 0) {
          band = { top: Math.round((baseY - top) / size * this.guideSize) };
          // a face that measures nonsense (no coverage for the sample,
          // so the browser drew tofu or nothing) is no guide
          if (band.top < 200 || band.top > 900) band = null;
        }
      } catch (err) { band = null; }
      this._bandKey = key;
      this._band = band;
      return band;
    },

    /* The guide face changed (or finished loading): measure it again. */
    resetGuideBand: function () {
      this._bandKey = null;
      this._band = null;
      this.render();
    },

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
      var colMuted = css.getPropertyValue("--muted").trim() || "#777";
      var colGold = css.getPropertyValue("--gold").trim() || "#96701c";

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
      // 550 is where top marks attach, not where letters end — the label
      // used to imply otherwise, and letters were drawn to it
      hline(550, colFaint, false, "marks 550");
      var band = this.measureGuideBand();
      if (band) hline(band.top, colGold, true, "letters " + band.top);
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

      // brush: a ring the size of the nib, so the width can be seen
      // BEFORE the stroke instead of judged after it
      if (this.tool === "brush" && this.hoverScr && !this.anchorMode) {
        ctx.save();
        ctx.strokeStyle = colInk;
        ctx.globalAlpha = 0.32;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(this.hoverScr[0], this.hoverScr[1],
                Math.max(2, (this.penWidth / 2) * s), 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
      }

      // The leash. A steadied stroke lags the pointer by design, and
      // without a line drawn between the two that lag reads as a dropped
      // frame. Shown only once the gap is big enough to notice.
      if (this.liveStroke && this._stab && this._rawScr &&
          this._shiftAnchor == null) {
        var tipU = this._stab.tip();
        var tx = this.ux(tipU[0]), ty = this.uy(tipU[1]);
        var rx = this._rawScr[0], ry = this._rawScr[1];
        if (Math.hypot(rx - tx, ry - ty) > 4) {
          ctx.save();
          ctx.strokeStyle = colAccent;
          ctx.globalAlpha = 0.45;
          ctx.lineWidth = 1;
          ctx.setLineDash([3, 3]);
          ctx.beginPath();
          ctx.moveTo(tx, ty); ctx.lineTo(rx, ry);
          ctx.stroke();
          ctx.setLineDash([]);
          ctx.beginPath();
          ctx.arc(rx, ry, 4, 0, Math.PI * 2);
          ctx.stroke();
          ctx.restore();
        }
      }

      // selection boxes, node handles, pen path preview
      if (this.isVecTool() && window.VecTools) window.VecTools.render(this, ctx);

      if (this.anchorMode) this.renderAnchors(ctx, colAccent, colBg);

      // Where the pointer is, in font units. These are the numbers that
      // matter when a stroke has to land on the body line or stay inside
      // the advance, and reading them off the guides was guesswork.
      if (this.hoverScr) {
        var u = this.px2units(this.hoverScr[0], this.hoverScr[1]);
        ctx.save();
        ctx.fillStyle = colMuted;
        ctx.globalAlpha = 0.85;
        ctx.font = "11px ui-monospace, Menlo, Consolas, monospace";
        ctx.fillText("x " + Math.round(u[0]) + "   y " + Math.round(u[1]),
                     8, this.cssH - 8);
        ctx.restore();
      }
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
