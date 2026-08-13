/*
 * Vector editing tools: Selection/transform, Direct node editing, Bézier Pen.
 *
 * These give the studio Illustrator-style editing on top of the existing
 * stroke model. Everything a tool produces or edits remains an ordinary
 * project stroke:
 *
 *   { width, points: [[x,y,(w)], ...] }        centre-line, expanded on build
 *   { fill: true, points: [...] }              closed filled contour
 *
 * Pen-tool paths additionally carry the OPTIONAL fields
 *   bez:    [[ax,ay, inx,iny, outx,outy], ...] Bézier nodes (absolute coords)
 *   closed: true
 * so they stay fully re-editable in the node editor. `points` is ALWAYS the
 * flattened polyline of `bez` — the web preview, the draft TTF export and the
 * Python pipeline all read only `points`/`width`/`fill`, so project files stay
 * backward and forward compatible (schema version stays 1; pipeline ignores
 * the extra keys).
 *
 * The Editor owns the canvas, view transform and undo stack; it routes
 * pointer events here while its tool is "select" | "direct" | "pen".
 * Undo integration follows the editor's convention: set
 * editor._preSnapshot = editor.snapshot() BEFORE mutating, then
 * editor.pushUndo() once the gesture commits.
 */
(function () {
  "use strict";

  // ---------------------------------------------------------------- geometry
  function dist2(ax, ay, bx, by) {
    var dx = ax - bx, dy = ay - by;
    return dx * dx + dy * dy;
  }

  function segDist2(px, py, ax, ay, bx, by) {
    var vx = bx - ax, vy = by - ay;
    var l2 = vx * vx + vy * vy;
    var t = l2 ? ((px - ax) * vx + (py - ay) * vy) / l2 : 0;
    t = Math.max(0, Math.min(1, t));
    return dist2(px, py, ax + vx * t, ay + vy * t);
  }

  function polyDist2(pts, x, y, closed) {
    if (!pts.length) return Infinity;
    if (pts.length === 1) return dist2(x, y, pts[0][0], pts[0][1]);
    var best = Infinity, n = pts.length, i, d;
    for (i = 0; i < n - 1; i++) {
      d = segDist2(x, y, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]);
      if (d < best) best = d;
    }
    if (closed) {
      d = segDist2(x, y, pts[n - 1][0], pts[n - 1][1], pts[0][0], pts[0][1]);
      if (d < best) best = d;
    }
    return best;
  }

  function pointInPoly(pts, x, y) {
    var inside = false;
    for (var i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      var xi = pts[i][0], yi = pts[i][1], xj = pts[j][0], yj = pts[j][1];
      if ((yi > y) !== (yj > y) &&
          x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }

  function lerp(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]; }

  function cubicAt(p0, p1, p2, p3, t) {
    var u = 1 - t;
    var a = u * u * u, b = 3 * u * u * t, c = 3 * u * t * t, d = t * t * t;
    return [a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
            a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]];
  }

  function clone(v) { return JSON.parse(JSON.stringify(v)); }
  function r1(v) { return Math.round(v * 10) / 10; } // 0.1-unit node precision

  /* Ramer–Douglas–Peucker on [x,y,(w)] points; keeps endpoint widths. */
  function rdp(points, epsilon) {
    if (points.length < 3) return points.slice();
    var keep = {};
    keep[0] = true; keep[points.length - 1] = true;
    (function recurse(first, last) {
      var ax = points[first][0], ay = points[first][1];
      var bx = points[last][0], by = points[last][1];
      var worst = -1, worstI = -1;
      for (var i = first + 1; i < last; i++) {
        var d = segDist2(points[i][0], points[i][1], ax, ay, bx, by);
        if (d > worst) { worst = d; worstI = i; }
      }
      if (worst > epsilon * epsilon && worstI > 0) {
        keep[worstI] = true;
        recurse(first, worstI);
        recurse(worstI, last);
      }
    })(0, points.length - 1);
    return points.filter(function (_, i) { return keep[i]; });
  }

  // ------------------------------------------------------------- bez helpers
  // node = [ax, ay, inx, iny, outx, outy]  (handles in absolute coords)
  function nodeAnchor(n) { return [n[0], n[1]]; }
  function nodeIn(n) { return [n[2], n[3]]; }
  function nodeOut(n) { return [n[4], n[5]]; }

  /* Flatten a bez node list to an integer polyline. For stroked closed
   * paths the polyline returns to the first point, so the existing round
   * end caps overlap at the seam and the loop renders solid — identically
   * in the web preview and the pipeline (no expansion changes needed). */
  function flattenBez(nodes, closed, forFill) {
    var pts = [];
    var segs = closed ? nodes.length : nodes.length - 1;
    for (var i = 0; i < segs; i++) {
      var a = nodes[i], b = nodes[(i + 1) % nodes.length];
      var p0 = nodeAnchor(a), p1 = nodeOut(a), p2 = nodeIn(b), p3 = nodeAnchor(b);
      var len = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]) +
                Math.hypot(p2[0] - p1[0], p2[1] - p1[1]) +
                Math.hypot(p3[0] - p2[0], p3[1] - p2[1]);
      var n = Math.max(4, Math.min(64, Math.round(len / 7)));
      for (var k = 0; k < n; k++) {
        var q = cubicAt(p0, p1, p2, p3, k / n);
        var pt = [Math.round(q[0]), Math.round(q[1])];
        var prev = pts[pts.length - 1];
        if (!prev || prev[0] !== pt[0] || prev[1] !== pt[1]) pts.push(pt);
      }
    }
    if (closed) {
      // stroked loops revisit the start so the caps seal the seam;
      // filled contours close implicitly and skip the duplicate
      if (!forFill) pts.push([Math.round(nodes[0][0]), Math.round(nodes[0][1])]);
    } else {
      var last = nodes[nodes.length - 1];
      var lp = [Math.round(last[0]), Math.round(last[1])];
      var tail = pts[pts.length - 1];
      if (!tail || tail[0] !== lp[0] || tail[1] !== lp[1]) pts.push(lp);
    }
    return pts;
  }

  function reflatten(stroke) {
    stroke.points = flattenBez(stroke.bez, !!stroke.closed, !!stroke.fill);
  }

  function isSmoothNode(n) {
    var lin = Math.hypot(n[2] - n[0], n[3] - n[1]);
    var lout = Math.hypot(n[4] - n[0], n[5] - n[1]);
    if (lin < 1 || lout < 1) return false;
    var cross = (n[2] - n[0]) * (n[5] - n[1]) - (n[3] - n[1]) * (n[4] - n[0]);
    var dot = (n[2] - n[0]) * (n[4] - n[0]) + (n[3] - n[1]) * (n[5] - n[1]);
    // handles roughly opposite: angle between them near 180°
    return dot < 0 && Math.abs(cross) / (lin * lout) < 0.12;
  }

  // ---------------------------------------------------------------- helpers
  function strokesOf(ed) {
    return window.Store.getGlyph(ed.glyph.name).strokes;
  }

  function strokeHit(ed, st, x, y) {
    var tol = Math.max(10 / ed.s(), 8);
    if (st.fill) {
      return pointInPoly(st.points, x, y) ||
             polyDist2(st.points, x, y, true) <= tol * tol;
    }
    var r = Math.max((st.width || 2) / 2 + 4, tol);
    return polyDist2(st.points, x, y, false) <= r * r;
  }

  /* Topmost stroke under a unit-space point, or -1. */
  function hitStrokeIndex(ed, x, y) {
    var arr = strokesOf(ed);
    for (var i = arr.length - 1; i >= 0; i--) {
      if (arr[i].points && arr[i].points.length && strokeHit(ed, arr[i], x, y)) return i;
    }
    return -1;
  }

  function bboxOf(ed, indices) {
    var arr = strokesOf(ed);
    var x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    indices.forEach(function (idx) {
      var st = arr[idx];
      if (!st) return;
      st.points.forEach(function (p) {
        if (p[0] < x0) x0 = p[0];
        if (p[0] > x1) x1 = p[0];
        if (p[1] < y0) y0 = p[1];
        if (p[1] > y1) y1 = p[1];
      });
    });
    if (x0 === Infinity) return null;
    return { x0: x0, y0: y0, x1: x1, y1: y1,
             cx: (x0 + x1) / 2, cy: (y0 + y1) / 2 };
  }

  function hitRadius(e) {
    return (e && e.pointerType === "touch") ? 16 : 10;
  }

  // ============================================================== the module
  var VT = {
    // selection tool state
    sel: [],
    mode: null,          // "move" | "scale" | "rotate" | "marquee" | null
    marquee: null,       // {x0,y0,x1,y1} units while rubber-banding
    onSelectionChange: null,

    // direct tool state
    dIdx: -1,            // stroke being node-edited
    dNode: -1,           // selected node/point
    dDrag: null,         // "node" | "in" | "out" | null

    // pen tool state
    penNodes: [],
    penCursor: null,
    penCloseHover: false,

    _gesture: null,      // per-drag scratch
    _lastTap: null,      // synthesized double-tap for touch

    // ------------------------------------------------------------ lifecycle
    reset: function () {
      this.sel = [];
      this.mode = null;
      this.marquee = null;
      this.dIdx = -1;
      this.dNode = -1;
      this.dDrag = null;
      this.penNodes = [];
      this.penCursor = null;
      this.penCloseHover = false;
      this._gesture = null;
      this.changed();
    },

    /* After undo/redo/glyph switch: stroke indices are stale. */
    softReset: function () {
      this.sel = [];
      this.mode = null;
      this.marquee = null;
      this.dIdx = -1;
      this.dNode = -1;
      this.dDrag = null;
      this._gesture = null;
      this.changed();
    },

    changed: function () {
      if (this.onSelectionChange) this.onSelectionChange(this.status());
    },

    status: function () {
      var ds = this.dIdx >= 0 ? this._dStroke() : null;
      return {
        sel: this.sel.length,
        node: this.dNode >= 0,
        target: !!ds,
        nodeIsBez: this.dNode >= 0 && !!(ds && ds.bez),
        penNodes: this.penNodes.length
      };
    },

    hasSelection: function () { return this.sel.length > 0; },
    penActive: function () { return this.penNodes.length > 0; },

    _commitStart: function (ed) {
      ed._preSnapshot = ed.snapshot();
    },
    _commitEnd: function (ed, changed) {
      if (changed) {
        ed.pushUndo();
        window.Store.emit();
        if (ed.onInkChange) ed.onInkChange(ed.glyph.name);
      } else {
        ed._preSnapshot = null;
      }
      ed.render();
    },

    /* An in-progress transform/node drag is abandoned (e.g. a second finger
     * landed and pinch-zoom takes over): restore pre-drag geometry. */
    cancelDrag: function (ed) {
      if (this._gesture && ed._preSnapshot) {
        ed.restore(ed._preSnapshot);
        ed._preSnapshot = null;
      }
      this._gesture = null;
      this.mode = null;
      this.marquee = null;
      this.dDrag = null;
    },

    // ------------------------------------------------- synthetic double tap
    _tapTrack: function (e, ed) {
      var p = ed.toScreen(e);
      var last = this._lastTap;
      this._lastTap = { x: p[0], y: p[1], t: e.timeStamp };
      return !!(last && e.timeStamp - last.t < 380 &&
                dist2(p[0], p[1], last.x, last.y) < 24 * 24);
    },

    // ================================================================ router
    down: function (e, ed) {
      var p = ed.toUnits(e);
      var isDbl = this._tapTrack(e, ed);
      if (ed.tool === "select") {
        if (isDbl && this._selDbl(e, ed, p)) return;
        this._selDown(e, ed, p);
      } else if (ed.tool === "direct") {
        if (isDbl && this._dirDbl(e, ed, p)) return;
        this._dirDown(e, ed, p);
      } else if (ed.tool === "pen") {
        // double-click/tap places the final point and finishes the path
        if (isDbl && this.penNodes.length >= 2) { this.penFinish(ed, false); return; }
        this._penDown(e, ed, p);
      }
    },

    move: function (e, ed) {
      var p = ed.toUnits(e);
      if (ed.tool === "select") this._selMove(e, ed, p);
      else if (ed.tool === "direct") this._dirMove(e, ed, p);
      else if (ed.tool === "pen") this._penMove(e, ed, p);
    },

    up: function (e, ed) {
      if (ed.tool === "select") this._selUp(e, ed);
      else if (ed.tool === "direct") this._dirUp(e, ed);
      else if (ed.tool === "pen") this._penUp(e, ed);
    },

    key: function (e, ed) {
      // returns true when the key was consumed
      if (ed.tool === "pen" && this.penNodes.length) {
        if (e.key === "Enter") { this.penFinish(ed, false); return true; }
        if (e.key === "Escape") { this.penCancel(ed); return true; }
        if (e.key === "Backspace" || e.key === "Delete") { this.penBack(ed); return true; }
      }
      if (e.key === "Escape") {
        if (ed.tool === "select" && this.sel.length) { this.sel = []; this.changed(); ed.render(); return true; }
        if (ed.tool === "direct" && (this.dNode >= 0 || this.dIdx >= 0)) {
          this.dNode = -1; this.dIdx = -1; this.changed(); ed.render(); return true;
        }
        return false;
      }
      if (e.key === "Delete" || e.key === "Backspace") {
        if (ed.tool === "select" && this.sel.length) { this.deleteSel(ed); return true; }
        if (ed.tool === "direct" && this.dNode >= 0) { this.deleteNode(ed); return true; }
        return false;
      }
      var arrows = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1] };
      if (arrows[e.key] && ed.tool === "select" && this.sel.length) {
        var step = e.shiftKey ? 20 : 2;
        this.nudge(ed, arrows[e.key][0] * step, arrows[e.key][1] * step);
        return true;
      }
      return false;
    },

    // ======================================================== SELECTION tool
    _selHandles: function (ed) {
      var b = bboxOf(ed, this.sel);
      if (!b) return null;
      var sx0 = ed.ux(b.x0), sx1 = ed.ux(b.x1);
      var sy0 = ed.uy(b.y1), sy1 = ed.uy(b.y0); // screen: top uses unit yMax
      var mx = (sx0 + sx1) / 2, my = (sy0 + sy1) / 2;
      return {
        b: b,
        pts: [ // order matters: corners then sides; anchor = opposite index
          { x: sx0, y: sy0, kind: "corner", ax: b.x1, ay: b.y0 }, // TL ↔ BR
          { x: sx1, y: sy0, kind: "corner", ax: b.x0, ay: b.y0 }, // TR ↔ BL
          { x: sx1, y: sy1, kind: "corner", ax: b.x0, ay: b.y1 }, // BR ↔ TL
          { x: sx0, y: sy1, kind: "corner", ax: b.x1, ay: b.y1 }, // BL ↔ TR
          { x: mx, y: sy0, kind: "sideY", ax: b.x0, ay: b.y0 },   // top edge
          { x: sx1, y: my, kind: "sideX", ax: b.x0, ay: b.y0 },   // right edge
          { x: mx, y: sy1, kind: "sideY", ax: b.x0, ay: b.y1 },   // bottom
          { x: sx0, y: my, kind: "sideX", ax: b.x1, ay: b.y0 }    // left
        ],
        rotate: { x: mx, y: sy0 - 26 }
      };
    },

    _selDbl: function (e, ed, p) {
      var idx = hitStrokeIndex(ed, p[0], p[1]);
      if (idx < 0) return false;
      // double-click a stroke: jump into the node editor on it
      this.sel = [];
      this.dIdx = idx;
      this.dNode = -1;
      if (ed.requestTool) ed.requestTool("direct");
      this.changed();
      ed.render();
      return true;
    },

    _selDown: function (e, ed, p) {
      var scr = ed.toScreen(e);
      var hr = hitRadius(e);
      var H = this.sel.length ? this._selHandles(ed) : null;
      var idx0 = hitStrokeIndex(ed, p[0], p[1]);
      var onSelected = idx0 >= 0 && this.sel.indexOf(idx0) >= 0;

      if (H) {
        if (dist2(scr[0], scr[1], H.rotate.x, H.rotate.y) <= hr * hr) {
          this._commitStart(ed);
          this._gesture = {
            kind: "rotate", changed: false,
            base: this.sel.map(function (i) { return clone(strokesOf(ed)[i]); }),
            cx: H.b.cx, cy: H.b.cy,
            a0: Math.atan2(p[1] - H.b.cy, p[0] - H.b.cx)
          };
          this.mode = "rotate";
          return;
        }
        for (var i = 0; i < H.pts.length; i++) {
          var h = H.pts[i];
          // on skinny selections the side handles sit ON the ink — a press
          // that also hits a selected stroke means "move", not "scale"
          if (h.kind !== "corner" && onSelected) continue;
          if (dist2(scr[0], scr[1], h.x, h.y) <= hr * hr) {
            this._commitStart(ed);
            this._gesture = {
              kind: "scale", changed: false,
              base: this.sel.map(function (k) { return clone(strokesOf(ed)[k]); }),
              handle: h, start: p.slice()
            };
            this.mode = "scale";
            return;
          }
        }
      }

      var idx = idx0;
      var insideBox = H && p[0] >= H.b.x0 && p[0] <= H.b.x1 &&
                      p[1] >= H.b.y0 && p[1] <= H.b.y1;

      if (idx >= 0 || insideBox) {
        if (idx >= 0 && this.sel.indexOf(idx) < 0) {
          if (e.shiftKey) this.sel.push(idx);
          else this.sel = [idx];
          this.changed();
        } else if (idx >= 0 && e.shiftKey) {
          // shift-click an already-selected stroke: deselect it, no drag
          this.sel = this.sel.filter(function (k) { return k !== idx; });
          this.changed();
          ed.render();
          return;
        }
        this._commitStart(ed);
        var altDup = false;
        if (e.altKey && this.sel.length) {
          // Alt-drag duplicates, then moves the copies
          var arr = strokesOf(ed);
          var copies = this.sel.map(function (k) { return clone(arr[k]); });
          var first = arr.length;
          copies.forEach(function (c) { arr.push(c); });
          this.sel = copies.map(function (_, k) { return first + k; });
          altDup = true;
          this.changed();
        }
        this._gesture = {
          kind: "move", changed: altDup, moved: false,
          base: this.sel.map(function (k) { return clone(strokesOf(ed)[k]); }),
          start: p.slice(), clickIdx: idx, shift: e.shiftKey
        };
        this.mode = "move";
        return;
      }

      // empty space: marquee (shift extends existing selection)
      this._gesture = { kind: "marquee", start: p.slice(), shift: e.shiftKey,
                        prev: this.sel.slice() };
      this.marquee = { x0: p[0], y0: p[1], x1: p[0], y1: p[1] };
      this.mode = "marquee";
      ed.render();
    },

    _applyFromBase: function (ed, xform, su) {
      var arr = strokesOf(ed);
      var g = this._gesture;
      this.sel.forEach(function (idx, k) {
        var b = g.base[k], t = arr[idx];
        if (!b || !t) return;
        t.points = b.points.map(function (pt) {
          var q = xform(pt[0], pt[1]);
          var o = [Math.round(q[0]), Math.round(q[1])];
          if (pt.length > 2) o.push(Math.max(2, Math.round(pt[2] * su)));
          return o;
        });
        if (b.width != null) t.width = Math.max(2, Math.round(b.width * su));
        if (b.bez) {
          t.bez = b.bez.map(function (n) {
            var a = xform(n[0], n[1]), h1 = xform(n[2], n[3]), h2 = xform(n[4], n[5]);
            return [r1(a[0]), r1(a[1]), r1(h1[0]), r1(h1[1]), r1(h2[0]), r1(h2[1])];
          });
        }
      });
    },

    _selMove: function (e, ed, p) {
      var g = this._gesture;
      if (!g || !e.buttons) return;

      if (g.kind === "marquee") {
        this.marquee.x1 = p[0];
        this.marquee.y1 = p[1];
        ed.render();
        return;
      }
      if (g.kind === "move") {
        var dx = p[0] - g.start[0], dy = p[1] - g.start[1];
        if (!g.moved && dx * dx + dy * dy < Math.pow(3 / ed.s(), 2)) return;
        g.moved = true;
        if (e.shiftKey) { if (Math.abs(dx) > Math.abs(dy)) dy = 0; else dx = 0; }
        this._applyFromBase(ed, function (x, y) { return [x + dx, y + dy]; }, 1);
        g.changed = true;
        ed.render();
        return;
      }
      if (g.kind === "scale") {
        var h = g.handle, ax = h.ax, ay = h.ay;
        var fx = 1, fy = 1;
        // a degenerate axis (flat/thin selection) must not explode the factor
        var axisOk = function (d) { return Math.abs(d) >= 8; };
        if (h.kind === "corner") {
          var d0 = Math.hypot(g.start[0] - ax, g.start[1] - ay);
          var d1 = Math.hypot(p[0] - ax, p[1] - ay);
          if (d0 < 8) return;
          if (e.shiftKey) { // free (non-uniform) with Shift
            fx = axisOk(g.start[0] - ax) ? (p[0] - ax) / (g.start[0] - ax) : 1;
            fy = axisOk(g.start[1] - ay) ? (p[1] - ay) / (g.start[1] - ay) : 1;
          } else {
            fx = fy = d1 / d0;
          }
        } else if (h.kind === "sideX") {
          fx = axisOk(g.start[0] - ax) ? (p[0] - ax) / (g.start[0] - ax) : 1;
        } else {
          fy = axisOk(g.start[1] - ay) ? (p[1] - ay) / (g.start[1] - ay) : 1;
        }
        var lim = function (f) {
          if (!isFinite(f)) return 1;
          var s = f < 0 ? -1 : 1;
          return s * Math.min(40, Math.max(0.02, Math.abs(f)));
        };
        fx = lim(fx); fy = lim(fy);
        var su = (Math.abs(fx) + Math.abs(fy)) / 2;
        this._applyFromBase(ed, function (x, y) {
          return [ax + (x - ax) * fx, ay + (y - ay) * fy];
        }, su);
        g.changed = true;
        ed.render();
        return;
      }
      if (g.kind === "rotate") {
        var a1 = Math.atan2(p[1] - g.cy, p[0] - g.cx);
        var da = a1 - g.a0;
        if (e.shiftKey) da = Math.round(da / (Math.PI / 12)) * (Math.PI / 12);
        var cos = Math.cos(da), sin = Math.sin(da), cx = g.cx, cy = g.cy;
        this._applyFromBase(ed, function (x, y) {
          var rx = x - cx, ry = y - cy;
          return [cx + rx * cos - ry * sin, cy + rx * sin + ry * cos];
        }, 1);
        g.changed = true;
        ed.render();
      }
    },

    _selUp: function (e, ed) {
      var g = this._gesture;
      this._gesture = null;
      this.mode = null;
      if (!g) return;

      if (g.kind === "marquee") {
        var m = this.marquee;
        this.marquee = null;
        var x0 = Math.min(m.x0, m.x1), x1 = Math.max(m.x0, m.x1);
        var y0 = Math.min(m.y0, m.y1), y1 = Math.max(m.y0, m.y1);
        var tiny = (x1 - x0) < 4 / ed.s() && (y1 - y0) < 4 / ed.s();
        if (tiny) {
          if (!g.shift) this.sel = [];      // click on empty space: deselect
        } else {
          var picked = [];
          strokesOf(ed).forEach(function (st, i) {
            if (!st.points) return;
            for (var k = 0; k < st.points.length; k++) {
              var pt = st.points[k];
              if (pt[0] >= x0 && pt[0] <= x1 && pt[1] >= y0 && pt[1] <= y1) {
                picked.push(i);
                return;
              }
            }
          });
          if (g.shift) {
            var set = {};
            g.prev.concat(picked).forEach(function (i) { set[i] = true; });
            this.sel = Object.keys(set).map(Number).sort(function (a, b) { return a - b; });
          } else {
            this.sel = picked;
          }
        }
        this.changed();
        ed.render();
        return;
      }

      if (g.kind === "move" && !g.moved) {
        // it was a plain click: selection already updated on down
        this._commitEnd(ed, g.changed); // alt-duplicate counts as a change
        return;
      }
      this._commitEnd(ed, g.changed);
    },

    // ------------------------------------------------- selection operations
    selectAll: function (ed) {
      var arr = strokesOf(ed);
      this.sel = arr.map(function (_, i) { return i; })
        .filter(function (i) { return arr[i].points && arr[i].points.length; });
      this.changed();
      ed.render();
    },

    deleteSel: function (ed) {
      if (!this.sel.length) return;
      this._commitStart(ed);
      var kill = {};
      this.sel.forEach(function (i) { kill[i] = true; });
      var g = window.Store.getGlyph(ed.glyph.name);
      g.strokes = g.strokes.filter(function (_, i) { return !kill[i]; });
      this.sel = [];
      this.changed();
      this._commitEnd(ed, true);
    },

    duplicate: function (ed) {
      if (!this.sel.length) return;
      this._commitStart(ed);
      var arr = strokesOf(ed);
      var copies = this.sel.map(function (i) { return clone(arr[i]); });
      var OFF = 24; // offset the copies so they are visibly separate
      copies.forEach(function (c) {
        c.points.forEach(function (p) { p[0] += OFF; p[1] -= OFF; });
        if (c.bez) c.bez.forEach(function (n) {
          n[0] += OFF; n[2] += OFF; n[4] += OFF;
          n[1] -= OFF; n[3] -= OFF; n[5] -= OFF;
        });
      });
      var first = arr.length;
      copies.forEach(function (c) { arr.push(c); });
      this.sel = copies.map(function (_, k) { return first + k; });
      this.changed();
      this._commitEnd(ed, true);
    },

    copy: function (ed) {
      if (!this.sel.length) return 0;
      var arr = strokesOf(ed);
      ed.clipboard = this.sel.map(function (i) { return clone(arr[i]); });
      return ed.clipboard.length;
    },

    cut: function (ed) {
      var n = this.copy(ed);
      if (n) this.deleteSel(ed);
      return n;
    },

    paste: function (ed) {
      if (!ed.clipboard || !ed.clipboard.length) return 0;
      this._commitStart(ed);
      var arr = strokesOf(ed);
      var first = arr.length;
      var copies = clone(ed.clipboard);
      copies.forEach(function (c) { arr.push(c); });
      this.sel = copies.map(function (_, k) { return first + k; });
      this.changed();
      this._commitEnd(ed, true);
      return copies.length;
    },

    nudge: function (ed, dx, dy) {
      if (!this.sel.length) return;
      this._commitStart(ed);
      var arr = strokesOf(ed);
      this.sel.forEach(function (i) {
        var st = arr[i];
        st.points.forEach(function (p) { p[0] += dx; p[1] += dy; });
        if (st.bez) st.bez.forEach(function (n) {
          n[0] += dx; n[2] += dx; n[4] += dx;
          n[1] += dy; n[3] += dy; n[5] += dy;
        });
      });
      this._commitEnd(ed, true);
    },

    flip: function (ed, axis) {
      if (!this.sel.length) return;
      var b = bboxOf(ed, this.sel);
      if (!b) return;
      this._commitStart(ed);
      var arr = strokesOf(ed);
      var fx = axis === "h" ? -1 : 1, fy = axis === "h" ? 1 : -1;
      var mapP = function (x, y) {
        return [b.cx + (x - b.cx) * fx, b.cy + (y - b.cy) * fy];
      };
      this.sel.forEach(function (i) {
        var st = arr[i];
        st.points = st.points.map(function (p) {
          var q = mapP(p[0], p[1]);
          var o = [Math.round(q[0]), Math.round(q[1])];
          if (p.length > 2) o.push(p[2]);
          return o;
        });
        st.points.reverse(); // keep winding sense for filled contours
        if (st.bez) {
          st.bez = st.bez.map(function (n) {
            var a = mapP(n[0], n[1]), h1 = mapP(n[2], n[3]), h2 = mapP(n[4], n[5]);
            // reversal also swaps in/out handles
            return [r1(a[0]), r1(a[1]), r1(h2[0]), r1(h2[1]), r1(h1[0]), r1(h1[1])];
          }).reverse();
        }
      });
      this._commitEnd(ed, true);
    },

    smoothSel: function (ed) {
      if (!this.sel.length) return;
      this._commitStart(ed);
      var arr = strokesOf(ed);
      var did = false;
      this.sel.forEach(function (i) {
        var st = arr[i];
        if (st.fill || st.bez || st.points.length < 3) return;
        st.points = window.Outline.smooth(st.points, 1).map(function (p) {
          var o = [Math.round(p[0]), Math.round(p[1])];
          if (p.length > 2) o.push(Math.round(p[2]));
          return o;
        });
        did = true;
      });
      this._commitEnd(ed, did);
    },

    simplifySel: function (ed) {
      if (!this.sel.length) return;
      this._commitStart(ed);
      var arr = strokesOf(ed);
      var did = false;
      this.sel.forEach(function (i) {
        var st = arr[i];
        if (st.bez || st.points.length < 5) return;
        var out = rdp(st.points, 4);
        if (out.length < st.points.length) { st.points = out; did = true; }
      });
      this._commitEnd(ed, did);
    },

    applyWidth: function (ed, w) {
      if (!this.sel.length) return;
      this._commitStart(ed);
      var arr = strokesOf(ed);
      var did = false;
      this.sel.forEach(function (i) {
        var st = arr[i];
        if (st.fill || st.width == null) return;
        var ratio = st.width > 0 ? w / st.width : 1;
        st.points.forEach(function (p) {
          if (p.length > 2) p[2] = Math.max(2, Math.round(p[2] * ratio));
        });
        st.width = w;
        did = true;
      });
      this._commitEnd(ed, did);
    },

    /* Average width of the selected strokes (for priming the width slider). */
    selWidth: function (ed) {
      var arr = strokesOf(ed);
      var sum = 0, n = 0;
      this.sel.forEach(function (i) {
        var st = arr[i];
        if (st && !st.fill && st.width) { sum += st.width; n++; }
      });
      return n ? Math.round(sum / n) : null;
    },

    // ========================================================== DIRECT tool
    _dStroke: function () { return this.dIdx >= 0 ? this._dArr[this.dIdx] : null; },
    get _dArr() { return window.Store.getGlyph(window.Editor.glyph.name).strokes; },

    _dirNodes: function (st) {
      // unified node list: bez anchors, or the raw polyline points
      if (st.bez) return st.bez.map(nodeAnchor);
      return st.points;
    },

    _dirHitNode: function (e, ed, st) {
      var scr = ed.toScreen(e);
      var hr = hitRadius(e);
      var nodes = this._dirNodes(st);
      var best = -1, bestD = hr * hr;
      for (var i = 0; i < nodes.length; i++) {
        var d = dist2(scr[0], scr[1], ed.ux(nodes[i][0]), ed.uy(nodes[i][1]));
        if (d <= bestD) { best = i; bestD = d; }
      }
      return best;
    },

    _dirDown: function (e, ed, p) {
      var scr = ed.toScreen(e);
      var hr = hitRadius(e);
      var st = this._dStroke();

      // 1) grab a handle of the selected bez node
      if (st && st.bez && this.dNode >= 0 && this.dNode < st.bez.length) {
        var n = st.bez[this.dNode];
        var hIn = dist2(scr[0], scr[1], ed.ux(n[2]), ed.uy(n[3])) <= hr * hr;
        var hOut = dist2(scr[0], scr[1], ed.ux(n[4]), ed.uy(n[5])) <= hr * hr;
        if (hIn || hOut) {
          this._commitStart(ed);
          this.dDrag = hIn && !hOut ? "in" : "out";
          this._gesture = {
            kind: "handle", changed: false,
            smooth: isSmoothNode(n),
            lenIn: Math.hypot(n[2] - n[0], n[3] - n[1]),
            lenOut: Math.hypot(n[4] - n[0], n[5] - n[1])
          };
          return;
        }
      }

      // 2) grab a node of the current stroke
      if (st) {
        var ni = this._dirHitNode(e, ed, st);
        if (ni >= 0) {
          this.dNode = ni;
          this._commitStart(ed);
          this.dDrag = "node";
          this._gesture = {
            kind: "node", changed: false,
            base: clone(st.bez ? st.bez : st.points),
            start: p.slice()
          };
          this.changed();
          ed.render();
          return;
        }
      }

      // 3) pick another stroke (or empty space clears the target)
      var idx = hitStrokeIndex(ed, p[0], p[1]);
      this.dIdx = idx;
      this.dNode = -1;
      this.dDrag = null;
      this.changed();
      ed.render();
    },

    _dirMove: function (e, ed, p) {
      if (!e.buttons || !this._gesture) return;
      var st = this._dStroke();
      if (!st) return;
      var g = this._gesture;

      if (g.kind === "handle") {
        var n = st.bez[this.dNode];
        var hp = ed.snapPoint ? ed.snapPoint(p) : p;
        if (this.dDrag === "out") { n[4] = r1(hp[0]); n[5] = r1(hp[1]); }
        else { n[2] = r1(hp[0]); n[3] = r1(hp[1]); }
        if (g.smooth && !e.altKey) {
          // mirror the opposite handle's direction, preserving its length
          var isOut = this.dDrag === "out";
          var hx = isOut ? n[4] : n[2], hy = isOut ? n[5] : n[3];
          var dx = hx - n[0], dy = hy - n[1];
          var len = Math.hypot(dx, dy);
          if (len > 1) {
            var other = isOut ? g.lenIn : g.lenOut;
            var ox = n[0] - dx / len * other, oy = n[1] - dy / len * other;
            if (isOut) { n[2] = r1(ox); n[3] = r1(oy); }
            else { n[4] = r1(ox); n[5] = r1(oy); }
          }
        }
        reflatten(st);
        g.changed = true;
        ed.render();
        return;
      }

      if (g.kind === "node") {
        var dx2 = p[0] - g.start[0], dy2 = p[1] - g.start[1];
        if (st.bez) {
          var b = g.base[this.dNode];
          var moved = ed.snapPoint
            ? ed.snapPoint([b[0] + dx2, b[1] + dy2]) : [b[0] + dx2, b[1] + dy2];
          var mx = moved[0] - b[0], my = moved[1] - b[1];
          var node = st.bez[this.dNode];
          node[0] = r1(b[0] + mx); node[1] = r1(b[1] + my);
          node[2] = r1(b[2] + mx); node[3] = r1(b[3] + my);
          node[4] = r1(b[4] + mx); node[5] = r1(b[5] + my);
          reflatten(st);
        } else {
          // freehand polyline: move the grabbed point with a smooth local
          // falloff so hand-drawn lines bend instead of spiking
          var R = Math.max(60, (st.width || 40) * 1.4);
          var grabbed = g.base[this.dNode];
          for (var i = 0; i < st.points.length; i++) {
            var bp = g.base[i];
            var d = Math.hypot(bp[0] - grabbed[0], bp[1] - grabbed[1]);
            if (d >= R && i !== this.dNode) continue;
            var w = i === this.dNode ? 1 : Math.pow(1 - (d / R) * (d / R), 2);
            st.points[i][0] = Math.round(bp[0] + dx2 * w);
            st.points[i][1] = Math.round(bp[1] + dy2 * w);
          }
        }
        g.changed = true;
        ed.render();
      }
    },

    _dirUp: function (e, ed) {
      var g = this._gesture;
      this._gesture = null;
      this.dDrag = null;
      if (g && (g.kind === "handle" || g.kind === "node")) {
        this._commitEnd(ed, g.changed);
      }
    },

    _dirDbl: function (e, ed, p) {
      var st = this._dStroke();
      if (!st) return false;

      // double-click a node: toggle smooth/corner (bez) — delete (polyline)
      var ni = this._dirHitNode(e, ed, st);
      if (ni >= 0) {
        this.dNode = ni;
        if (st.bez) this.toggleNodeType(ed);
        else this.deleteNode(ed);
        return true;
      }

      // double-click on the path: insert a node there
      var tol = Math.max((st.width || 20), 14 / ed.s());
      if (polyDist2(st.points, p[0], p[1], !!(st.closed || st.fill)) <= tol * tol) {
        this.insertNode(ed, p);
        return true;
      }
      return false;
    },

    toggleNodeType: function (ed) {
      var st = this._dStroke();
      if (!st || !st.bez || this.dNode < 0) return;
      this._commitStart(ed);
      var nodes = st.bez, i = this.dNode, n = nodes[i];
      if (isSmoothNode(n) || Math.hypot(n[2] - n[0], n[3] - n[1]) > 1 ||
          Math.hypot(n[4] - n[0], n[5] - n[1]) > 1) {
        // → corner: collapse the handles
        n[2] = n[0]; n[3] = n[1]; n[4] = n[0]; n[5] = n[1];
      } else {
        // → smooth: aim the handles along the neighbours
        var N = nodes.length;
        var prev = nodes[(i - 1 + N) % N], next = nodes[(i + 1) % N];
        var hasPrev = st.closed || i > 0, hasNext = st.closed || i < N - 1;
        var ref1 = hasPrev ? prev : n, ref2 = hasNext ? next : n;
        var dx = ref2[0] - ref1[0], dy = ref2[1] - ref1[1];
        var len = Math.hypot(dx, dy) || 1;
        dx /= len; dy /= len;
        var lp = hasPrev ? Math.hypot(prev[0] - n[0], prev[1] - n[1]) * 0.3 : 0;
        var ln = hasNext ? Math.hypot(next[0] - n[0], next[1] - n[1]) * 0.3 : 0;
        n[2] = r1(n[0] - dx * lp); n[3] = r1(n[1] - dy * lp);
        n[4] = r1(n[0] + dx * ln); n[5] = r1(n[1] + dy * ln);
      }
      reflatten(st);
      this._commitEnd(ed, true);
    },

    insertNode: function (ed, p) {
      var st = this._dStroke();
      if (!st) return;
      this._commitStart(ed);
      if (st.bez) {
        // find nearest (segment, t) by dense sampling, then de Casteljau split
        var nodes = st.bez;
        var segs = st.closed ? nodes.length : nodes.length - 1;
        var best = { d: Infinity, seg: 0, t: 0.5 };
        for (var i = 0; i < segs; i++) {
          var a = nodes[i], b = nodes[(i + 1) % nodes.length];
          var p0 = nodeAnchor(a), p1 = nodeOut(a), p2 = nodeIn(b), p3 = nodeAnchor(b);
          for (var k = 1; k < 48; k++) {
            var t = k / 48;
            var q = cubicAt(p0, p1, p2, p3, t);
            var d = dist2(q[0], q[1], p[0], p[1]);
            if (d < best.d) best = { d: d, seg: i, t: t };
          }
        }
        var A = nodes[best.seg], B = nodes[(best.seg + 1) % nodes.length];
        var P0 = nodeAnchor(A), P1 = nodeOut(A), P2 = nodeIn(B), P3 = nodeAnchor(B);
        var t0 = best.t;
        var q0 = lerp(P0, P1, t0), q1 = lerp(P1, P2, t0), q2 = lerp(P2, P3, t0);
        var s0 = lerp(q0, q1, t0), s1 = lerp(q1, q2, t0);
        var m = lerp(s0, s1, t0);
        A[4] = r1(q0[0]); A[5] = r1(q0[1]);
        B[2] = r1(q2[0]); B[3] = r1(q2[1]);
        var newNode = [r1(m[0]), r1(m[1]), r1(s0[0]), r1(s0[1]), r1(s1[0]), r1(s1[1])];
        nodes.splice(best.seg + 1, 0, newNode);
        this.dNode = best.seg + 1;
        reflatten(st);
      } else {
        var pts = st.points;
        var bi = 0, bd = Infinity;
        for (var j = 0; j < pts.length - 1; j++) {
          var dd = segDist2(p[0], p[1], pts[j][0], pts[j][1], pts[j + 1][0], pts[j + 1][1]);
          if (dd < bd) { bd = dd; bi = j; }
        }
        var np = [Math.round(p[0]), Math.round(p[1])];
        if (pts[bi].length > 2 && pts[bi + 1] && pts[bi + 1].length > 2) {
          np.push(Math.round((pts[bi][2] + pts[bi + 1][2]) / 2));
        }
        pts.splice(bi + 1, 0, np);
        this.dNode = bi + 1;
      }
      this.changed();
      this._commitEnd(ed, true);
    },

    deleteNode: function (ed) {
      var st = this._dStroke();
      if (!st || this.dNode < 0) return;
      this._commitStart(ed);
      if (st.bez) {
        st.bez.splice(this.dNode, 1);
        if (st.bez.length < 2) {
          this._dArr.splice(this.dIdx, 1);
          this.dIdx = -1;
        } else {
          reflatten(st);
        }
      } else {
        st.points.splice(this.dNode, 1);
        // a filled contour needs 3+ points to stay drawable
        if (st.points.length < (st.fill ? 3 : 2)) {
          this._dArr.splice(this.dIdx, 1);
          this.dIdx = -1;
        }
      }
      this.dNode = -1;
      this.changed();
      this._commitEnd(ed, true);
    },

    reversePath: function (ed) {
      var st = this._dStroke();
      if (!st) return;
      this._commitStart(ed);
      st.points.reverse();
      if (st.bez) {
        st.bez = st.bez.map(function (n) {
          return [n[0], n[1], n[4], n[5], n[2], n[3]];
        }).reverse();
      }
      this.dNode = -1;
      this._commitEnd(ed, true);
    },

    // ============================================================= PEN tool
    _penDown: function (e, ed, p) {
      var scr = ed.toScreen(e);
      // close the path by clicking the first node again
      if (this.penNodes.length >= 2) {
        var f = this.penNodes[0];
        if (dist2(scr[0], scr[1], ed.ux(f[0]), ed.uy(f[1])) <= 14 * 14) {
          this._gesture = { kind: "penClose" };
          return;
        }
      }
      var sp = ed.snapPoint ? ed.snapPoint(p) : p;
      this.penNodes.push([sp[0], sp[1], sp[0], sp[1], sp[0], sp[1]]);
      this._gesture = { kind: "penDrag" };
      this.changed();
      ed.render();
    },

    _penMove: function (e, ed, p) {
      if (e.buttons && this._gesture) {
        if (this._gesture.kind === "penDrag" && this.penNodes.length) {
          // dragging pulls out symmetric handles → a smooth node
          var n = this.penNodes[this.penNodes.length - 1];
          n[4] = r1(p[0]); n[5] = r1(p[1]);
          n[2] = r1(2 * n[0] - p[0]); n[3] = r1(2 * n[1] - p[1]);
          ed.render();
        }
        return;
      }
      // hover: live preview of the next segment + close-path highlight
      this.penCursor = p;
      if (this.penNodes.length >= 2) {
        var scr = ed.toScreen(e);
        var f = this.penNodes[0];
        this.penCloseHover =
          dist2(scr[0], scr[1], ed.ux(f[0]), ed.uy(f[1])) <= 14 * 14;
      } else {
        this.penCloseHover = false;
      }
      ed.render();
    },

    _penUp: function (e, ed) {
      var g = this._gesture;
      this._gesture = null;
      if (g && g.kind === "penClose") this.penFinish(ed, true);
    },

    penFinish: function (ed, closed) {
      var nodes = this.penNodes;
      this.penNodes = [];
      this.penCursor = null;
      this.penCloseHover = false;
      if (nodes.length < 2) { this.changed(); ed.render(); return; }
      var st = { width: ed.penWidth, points: [] };
      st.bez = clone(nodes);
      if (closed) {
        st.closed = true;
        if (ed.fillShape) st.fill = true;
      }
      st.points = flattenBez(st.bez, !!st.closed, !!st.fill);
      ed.addStrokes([st]); // handles undo + persistence + preview refresh
      this.changed();
    },

    penCancel: function (ed) {
      this.penNodes = [];
      this.penCursor = null;
      this.penCloseHover = false;
      this._gesture = null;
      this.changed();
      ed.render();
    },

    penBack: function (ed) {
      if (!this.penNodes.length) return;
      this.penNodes.pop();
      this.changed();
      ed.render();
    },

    // ============================================================ rendering
    render: function (ed, ctx) {
      var css = getComputedStyle(document.documentElement);
      var accent = css.getPropertyValue("--accent").trim() || "#a8352f";
      var selCol = css.getPropertyValue("--select").trim() || "#2f6fb8";
      var bg = css.getPropertyValue("--canvas-bg").trim() || "#fff";

      if (ed.tool === "select") this._renderSelect(ed, ctx, selCol, bg);
      else if (ed.tool === "direct") this._renderDirect(ed, ctx, selCol, accent, bg);
      else if (ed.tool === "pen") this._renderPen(ed, ctx, selCol, accent, bg);
    },

    _outlinePath: function (ed, ctx, pts) {
      ctx.beginPath();
      for (var i = 0; i < pts.length; i++) {
        var x = ed.ux(pts[i][0]), y = ed.uy(pts[i][1]);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
    },

    _handleSquare: function (ctx, x, y, r, fill, stroke) {
      ctx.fillStyle = fill;
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.rect(x - r, y - r, r * 2, r * 2);
      ctx.fill();
      ctx.stroke();
    },

    _renderSelect: function (ed, ctx, selCol, bg) {
      var arr = strokesOf(ed);
      var self = this;
      ctx.save();

      // highlight each selected stroke's centre line
      ctx.strokeStyle = selCol;
      ctx.lineWidth = 1.4;
      this.sel.forEach(function (i) {
        var st = arr[i];
        if (!st || !st.points.length) return;
        self._outlinePath(ed, ctx, st.points);
        if (st.fill || st.closed) ctx.closePath();
        ctx.stroke();
      });

      var H = this.sel.length ? this._selHandles(ed) : null;
      if (H) {
        var x0 = ed.ux(H.b.x0), x1 = ed.ux(H.b.x1);
        var yT = ed.uy(H.b.y1), yB = ed.uy(H.b.y0);
        ctx.strokeStyle = selCol;
        ctx.setLineDash([5, 4]);
        ctx.lineWidth = 1.2;
        ctx.strokeRect(x0, yT, x1 - x0, yB - yT);
        ctx.setLineDash([]);
        // rotation stem + knob
        ctx.beginPath();
        ctx.moveTo((x0 + x1) / 2, yT);
        ctx.lineTo(H.rotate.x, H.rotate.y);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(H.rotate.x, H.rotate.y, 5.5, 0, Math.PI * 2);
        ctx.fillStyle = bg;
        ctx.fill();
        ctx.stroke();
        for (var i = 0; i < H.pts.length; i++) {
          this._handleSquare(ctx, H.pts[i].x, H.pts[i].y, 4.5, bg, selCol);
        }
      }

      if (this.marquee) {
        var m = this.marquee;
        var mx0 = ed.ux(Math.min(m.x0, m.x1)), mx1 = ed.ux(Math.max(m.x0, m.x1));
        var my0 = ed.uy(Math.max(m.y0, m.y1)), my1 = ed.uy(Math.min(m.y0, m.y1));
        ctx.strokeStyle = selCol;
        ctx.setLineDash([4, 3]);
        ctx.lineWidth = 1;
        ctx.strokeRect(mx0, my0, mx1 - mx0, my1 - my0);
        ctx.setLineDash([]);
        ctx.globalAlpha = 0.08;
        ctx.fillStyle = selCol;
        ctx.fillRect(mx0, my0, mx1 - mx0, my1 - my0);
        ctx.globalAlpha = 1;
      }
      ctx.restore();
    },

    _renderDirect: function (ed, ctx, selCol, accent, bg) {
      var st = this._dStroke();
      if (!st || !st.points.length) return;
      var self = this;
      ctx.save();

      ctx.strokeStyle = selCol;
      ctx.lineWidth = 1.4;
      this._outlinePath(ed, ctx, st.points);
      if (st.fill || st.closed) ctx.closePath();
      ctx.stroke();

      if (st.bez) {
        // handles of the selected node (and its neighbours' shared curve)
        if (this.dNode >= 0 && this.dNode < st.bez.length) {
          var n = st.bez[this.dNode];
          var ax = ed.ux(n[0]), ay = ed.uy(n[1]);
          [[n[2], n[3]], [n[4], n[5]]].forEach(function (h) {
            var hx = ed.ux(h[0]), hy = ed.uy(h[1]);
            ctx.strokeStyle = selCol;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(ax, ay);
            ctx.lineTo(hx, hy);
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(hx, hy, 4, 0, Math.PI * 2);
            ctx.fillStyle = bg;
            ctx.fill();
            ctx.stroke();
          });
        }
        st.bez.forEach(function (node, i) {
          self._handleSquare(ctx, ed.ux(node[0]), ed.uy(node[1]), 4,
            i === self.dNode ? selCol : bg, selCol);
        });
      } else {
        // polyline points: draw at most ~150 dots, but the grabbed one always
        var n = st.points.length;
        var step = Math.max(1, Math.floor(n / 150));
        ctx.fillStyle = selCol;
        for (var i = 0; i < n; i += step) {
          var p = st.points[i];
          ctx.beginPath();
          ctx.arc(ed.ux(p[0]), ed.uy(p[1]), 2.4, 0, Math.PI * 2);
          ctx.fill();
        }
        if (this.dNode >= 0 && this.dNode < n) {
          var q = st.points[this.dNode];
          this._handleSquare(ctx, ed.ux(q[0]), ed.uy(q[1]), 4.5, selCol, bg);
        }
      }
      ctx.restore();
    },

    _renderPen: function (ed, ctx, selCol, accent, bg) {
      var nodes = this.penNodes;
      var self = this;
      ctx.save();

      if (nodes.length) {
        // committed part of the path
        ctx.strokeStyle = selCol;
        ctx.lineWidth = 1.6;
        ctx.beginPath();
        ctx.moveTo(ed.ux(nodes[0][0]), ed.uy(nodes[0][1]));
        for (var i = 0; i < nodes.length - 1; i++) {
          var a = nodes[i], b = nodes[i + 1];
          ctx.bezierCurveTo(
            ed.ux(a[4]), ed.uy(a[5]),
            ed.ux(b[2]), ed.uy(b[3]),
            ed.ux(b[0]), ed.uy(b[1]));
        }
        ctx.stroke();

        // rubber band to the cursor (or back to the start when closing)
        if (this.penCursor && !this._gesture) {
          var last = nodes[nodes.length - 1];
          var tx = this.penCloseHover ? nodes[0][0] : this.penCursor[0];
          var ty = this.penCloseHover ? nodes[0][1] : this.penCursor[1];
          ctx.setLineDash([4, 3]);
          ctx.lineWidth = 1.1;
          ctx.beginPath();
          ctx.moveTo(ed.ux(last[0]), ed.uy(last[1]));
          ctx.bezierCurveTo(
            ed.ux(last[4]), ed.uy(last[5]),
            ed.ux(tx), ed.uy(ty),
            ed.ux(tx), ed.uy(ty));
          ctx.stroke();
          ctx.setLineDash([]);
        }

        // node markers; the first gets a ring when closing is possible
        nodes.forEach(function (n, i) {
          var x = ed.ux(n[0]), y = ed.uy(n[1]);
          // live handles of the node being dragged out
          if (i === nodes.length - 1 && self._gesture &&
              self._gesture.kind === "penDrag" &&
              (n[4] !== n[0] || n[5] !== n[1])) {
            ctx.strokeStyle = selCol;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(ed.ux(n[2]), ed.uy(n[3]));
            ctx.lineTo(ed.ux(n[4]), ed.uy(n[5]));
            ctx.stroke();
            [[n[2], n[3]], [n[4], n[5]]].forEach(function (h) {
              ctx.beginPath();
              ctx.arc(ed.ux(h[0]), ed.uy(h[1]), 3.5, 0, Math.PI * 2);
              ctx.fillStyle = bg;
              ctx.fill();
              ctx.stroke();
            });
          }
          self._handleSquare(ctx, x, y, 4, i === 0 && self.penCloseHover ? selCol : bg, selCol);
          if (i === 0 && nodes.length >= 2) {
            ctx.strokeStyle = selCol;
            ctx.beginPath();
            ctx.arc(x, y, 9, 0, Math.PI * 2);
            ctx.stroke();
          }
        });
      }
      ctx.restore();
    }
  };

  window.VecTools = VT;
})();
