/*
 * SVG import: turn an SVG file's shapes into filled-contour strokes.
 *
 * This is the paper path into the studio: photograph or scan a sketch,
 * vectorize it (Inkscape "Trace bitmap", Illustrator "Image trace",
 * potrace, …), save as SVG and import it onto the current glyph. Every
 * <path>/<polygon>/<rect>/<circle>/<ellipse>/<line>/<polyline> becomes a
 * { fill: true, points: [...] } stroke — a ready-made closed contour that
 * outline.js and the pipeline use verbatim (nonzero winding, so holes
 * traced in the opposite direction stay holes).
 *
 * Coordinates: SVGs exported by the studio itself carry
 * data-glyphstudio-units="font" and re-import at their exact coordinates
 * (y flipped back). Anything else is uniformly scaled to fit the em box —
 * content bottom on the baseline, left edge at x=40.
 */
(function () {
  "use strict";

  var CURVE_SEGMENTS = 16;   // straight segments per bezier
  var MIN_SEG = 3;           // decimation: drop points closer than this (units)
  var MAX_POINTS = 20000;    // safety cap across all contours

  // ---- 2x3 affine matrices [a b c d e f] (SVG order) ---------------------
  var IDENTITY = [1, 0, 0, 1, 0, 0];

  function multiply(m, n) {
    return [
      m[0] * n[0] + m[2] * n[1],
      m[1] * n[0] + m[3] * n[1],
      m[0] * n[2] + m[2] * n[3],
      m[1] * n[2] + m[3] * n[3],
      m[0] * n[4] + m[2] * n[5] + m[4],
      m[1] * n[4] + m[3] * n[5] + m[5]
    ];
  }

  function apply(m, x, y) {
    return [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];
  }

  function parseTransform(str) {
    var m = IDENTITY;
    if (!str) return m;
    var re = /(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)/g;
    var match;
    while ((match = re.exec(str))) {
      var op = match[1];
      var args = match[2].split(/[\s,]+/).filter(function (s) { return s !== ""; })
        .map(parseFloat);
      var t = IDENTITY;
      if (op === "matrix" && args.length === 6) {
        t = args;
      } else if (op === "translate") {
        t = [1, 0, 0, 1, args[0] || 0, args[1] || 0];
      } else if (op === "scale") {
        t = [args[0], 0, 0, (args.length > 1 ? args[1] : args[0]), 0, 0];
      } else if (op === "rotate") {
        var a = (args[0] || 0) * Math.PI / 180;
        var cos = Math.cos(a), sin = Math.sin(a);
        if (args.length > 2) {
          var cx = args[1], cy = args[2];
          t = multiply(multiply([1, 0, 0, 1, cx, cy], [cos, sin, -sin, cos, 0, 0]),
            [1, 0, 0, 1, -cx, -cy]);
        } else {
          t = [cos, sin, -sin, cos, 0, 0];
        }
      } else if (op === "skewX") {
        t = [1, 0, Math.tan((args[0] || 0) * Math.PI / 180), 1, 0, 0];
      } else if (op === "skewY") {
        t = [1, Math.tan((args[0] || 0) * Math.PI / 180), 0, 1, 0, 0];
      }
      m = multiply(m, t);
    }
    return m;
  }

  // ---- path data ----------------------------------------------------------
  function tokenizePath(d) {
    var tokens = d.match(/[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?/g);
    return tokens || [];
  }

  function sampleCubic(p0, p1, p2, p3, out) {
    for (var i = 1; i <= CURVE_SEGMENTS; i++) {
      var t = i / CURVE_SEGMENTS, u = 1 - t;
      out.push([
        u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0],
        u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1]
      ]);
    }
  }

  function sampleQuad(p0, p1, p2, out) {
    for (var i = 1; i <= CURVE_SEGMENTS; i++) {
      var t = i / CURVE_SEGMENTS, u = 1 - t;
      out.push([
        u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
        u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]
      ]);
    }
  }

  /* SVG elliptical arc (endpoint parametrization) sampled into lines. */
  function sampleArc(p0, rx, ry, rotDeg, largeArc, sweep, p1, out) {
    rx = Math.abs(rx); ry = Math.abs(ry);
    if (!rx || !ry) { out.push(p1); return; }
    var phi = rotDeg * Math.PI / 180;
    var cosP = Math.cos(phi), sinP = Math.sin(phi);
    var dx = (p0[0] - p1[0]) / 2, dy = (p0[1] - p1[1]) / 2;
    var x1 = cosP * dx + sinP * dy;
    var y1 = -sinP * dx + cosP * dy;
    var lam = (x1 * x1) / (rx * rx) + (y1 * y1) / (ry * ry);
    if (lam > 1) { var s = Math.sqrt(lam); rx *= s; ry *= s; }
    var num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1;
    var den = rx * rx * y1 * y1 + ry * ry * x1 * x1;
    var co = Math.sqrt(Math.max(0, num / den)) * (largeArc !== sweep ? 1 : -1);
    var cxp = co * rx * y1 / ry;
    var cyp = -co * ry * x1 / rx;
    var cx = cosP * cxp - sinP * cyp + (p0[0] + p1[0]) / 2;
    var cy = sinP * cxp + cosP * cyp + (p0[1] + p1[1]) / 2;
    function angle(ux, uy, vx, vy) {
      var dot = ux * vx + uy * vy;
      var len = Math.hypot(ux, uy) * Math.hypot(vx, vy);
      var a = Math.acos(Math.min(1, Math.max(-1, dot / len)));
      return (ux * vy - uy * vx) < 0 ? -a : a;
    }
    var a0 = angle(1, 0, (x1 - cxp) / rx, (y1 - cyp) / ry);
    var dA = angle((x1 - cxp) / rx, (y1 - cyp) / ry,
                   (-x1 - cxp) / rx, (-y1 - cyp) / ry);
    if (!sweep && dA > 0) dA -= 2 * Math.PI;
    if (sweep && dA < 0) dA += 2 * Math.PI;
    var n = Math.max(4, Math.ceil(Math.abs(dA) / (Math.PI / CURVE_SEGMENTS)));
    for (var i = 1; i <= n; i++) {
      var a = a0 + dA * (i / n);
      var px = rx * Math.cos(a), py = ry * Math.sin(a);
      out.push([cosP * px - sinP * py + cx, sinP * px + cosP * py + cy]);
    }
  }

  /* Parse one path's d attribute into an array of contours (point arrays). */
  function pathToContours(d) {
    var toks = tokenizePath(d);
    var contours = [];
    var pts = null;
    var cur = [0, 0], start = [0, 0];
    var prevCubic = null, prevQuad = null;
    var i = 0, cmd = null;

    function num() { return parseFloat(toks[i++]); }
    function finish() {
      if (pts && pts.length >= 3) contours.push(pts);
      pts = null;
    }

    while (i < toks.length) {
      var t = toks[i];
      if (/^[A-Za-z]$/.test(t)) { cmd = t; i++; }
      else if (cmd === null) { break; }
      // implicit repeat: M/m repeats as L/l
      else if (cmd === "M") cmd = "L";
      else if (cmd === "m") cmd = "l";

      var rel = cmd === cmd.toLowerCase();
      var c = cmd.toUpperCase();
      var x, y, p1, p2, end;

      if (c === "Z") {
        finish();
        cur = start.slice();
        prevCubic = prevQuad = null;
        continue;
      }
      if (c === "M") {
        finish();
        x = num(); y = num();
        cur = rel ? [cur[0] + x, cur[1] + y] : [x, y];
        start = cur.slice();
        pts = [cur.slice()];
        prevCubic = prevQuad = null;
        continue;
      }
      if (!pts) pts = [cur.slice()];
      if (c === "L") {
        x = num(); y = num();
        cur = rel ? [cur[0] + x, cur[1] + y] : [x, y];
        pts.push(cur.slice());
        prevCubic = prevQuad = null;
      } else if (c === "H") {
        x = num();
        cur = [rel ? cur[0] + x : x, cur[1]];
        pts.push(cur.slice());
        prevCubic = prevQuad = null;
      } else if (c === "V") {
        y = num();
        cur = [cur[0], rel ? cur[1] + y : y];
        pts.push(cur.slice());
        prevCubic = prevQuad = null;
      } else if (c === "C" || c === "S") {
        if (c === "C") {
          p1 = [num(), num()];
          if (rel) { p1[0] += cur[0]; p1[1] += cur[1]; }
        } else {
          p1 = prevCubic
            ? [2 * cur[0] - prevCubic[0], 2 * cur[1] - prevCubic[1]]
            : cur.slice();
        }
        p2 = [num(), num()];
        end = [num(), num()];
        if (rel) {
          p2[0] += cur[0]; p2[1] += cur[1];
          end[0] += cur[0]; end[1] += cur[1];
        }
        sampleCubic(cur, p1, p2, end, pts);
        prevCubic = p2; prevQuad = null;
        cur = end;
      } else if (c === "Q" || c === "T") {
        if (c === "Q") {
          p1 = [num(), num()];
          if (rel) { p1[0] += cur[0]; p1[1] += cur[1]; }
        } else {
          p1 = prevQuad
            ? [2 * cur[0] - prevQuad[0], 2 * cur[1] - prevQuad[1]]
            : cur.slice();
        }
        end = [num(), num()];
        if (rel) { end[0] += cur[0]; end[1] += cur[1]; }
        sampleQuad(cur, p1, end, pts);
        prevQuad = p1; prevCubic = null;
        cur = end;
      } else if (c === "A") {
        var rx = num(), ry = num(), rot = num();
        var large = !!num(), sweep = !!num();
        end = [num(), num()];
        if (rel) { end[0] += cur[0]; end[1] += cur[1]; }
        sampleArc(cur, rx, ry, rot, large, sweep, end, pts);
        prevCubic = prevQuad = null;
        cur = end;
      } else {
        break; // unknown command
      }
    }
    finish();
    return contours;
  }

  // ---- shape elements → contours ------------------------------------------
  function shapeToContours(el) {
    var get = function (attr, dflt) {
      var v = parseFloat(el.getAttribute(attr));
      return isFinite(v) ? v : (dflt || 0);
    };
    var tag = el.tagName.toLowerCase();
    var pts, i;
    if (tag === "path") {
      return pathToContours(el.getAttribute("d") || "");
    }
    if (tag === "polygon" || tag === "polyline") {
      var nums = (el.getAttribute("points") || "")
        .split(/[\s,]+/).filter(function (s) { return s !== ""; }).map(parseFloat);
      pts = [];
      for (i = 0; i + 1 < nums.length; i += 2) pts.push([nums[i], nums[i + 1]]);
      return pts.length >= 3 ? [pts] : [];
    }
    if (tag === "rect") {
      var rx0 = get("x"), ry0 = get("y"), rw = get("width"), rh = get("height");
      if (!rw || !rh) return [];
      return [[[rx0, ry0], [rx0 + rw, ry0], [rx0 + rw, ry0 + rh], [rx0, ry0 + rh]]];
    }
    if (tag === "circle" || tag === "ellipse") {
      var cx = get("cx"), cy = get("cy");
      var erx = tag === "circle" ? get("r") : get("rx");
      var ery = tag === "circle" ? get("r") : get("ry");
      if (!erx || !ery) return [];
      pts = [];
      var n = CURVE_SEGMENTS * 4;
      for (i = 0; i < n; i++) {
        var a = (i / n) * Math.PI * 2;
        pts.push([cx + erx * Math.cos(a), cy + ery * Math.sin(a)]);
      }
      return [pts];
    }
    if (tag === "line") {
      // a bare line has no fillable area — give it a thin lozenge so
      // construction lines survive the import visibly
      var x1 = get("x1"), y1 = get("y1"), x2 = get("x2"), y2 = get("y2");
      var dx = x2 - x1, dy = y2 - y1;
      var len = Math.hypot(dx, dy) || 1;
      var nx = -dy / len * 2, ny = dx / len * 2;
      return [[[x1 + nx, y1 + ny], [x2 + nx, y2 + ny],
               [x2 - nx, y2 - ny], [x1 - nx, y1 - ny]]];
    }
    return [];
  }

  var SHAPE_TAGS = { path: 1, polygon: 1, polyline: 1, rect: 1, circle: 1, ellipse: 1, line: 1 };
  var SKIP_TAGS = { defs: 1, clippath: 1, mask: 1, pattern: 1, marker: 1, symbol: 1, style: 1, metadata: 1 };

  function collect(el, ctm, out) {
    var tag = el.tagName ? el.tagName.toLowerCase() : "";
    if (SKIP_TAGS[tag]) return;
    var m = ctm;
    var tr = el.getAttribute && el.getAttribute("transform");
    if (tr) m = multiply(ctm, parseTransform(tr));
    if (SHAPE_TAGS[tag]) {
      shapeToContours(el).forEach(function (contour) {
        out.push(contour.map(function (p) { return apply(m, p[0], p[1]); }));
      });
      return;
    }
    for (var i = 0; i < el.children.length; i++) collect(el.children[i], m, out);
  }

  function decimate(contour) {
    var out = [contour[0]];
    for (var i = 1; i < contour.length; i++) {
      var q = out[out.length - 1];
      var dx = contour[i][0] - q[0], dy = contour[i][1] - q[1];
      if (dx * dx + dy * dy >= MIN_SEG * MIN_SEG) out.push(contour[i]);
    }
    return out;
  }

  /*
   * Parse SVG text → { strokes: [{fill:true, points}], exact: bool }.
   * Throws on unparseable input.
   */
  function parse(svgText) {
    var doc = new DOMParser().parseFromString(svgText, "image/svg+xml");
    if (doc.querySelector("parsererror")) throw new Error("not a valid SVG file");
    var root = doc.documentElement;
    if (!root || root.tagName.toLowerCase() !== "svg") {
      throw new Error("no <svg> root element");
    }

    var contours = [];
    collect(root, IDENTITY, contours);
    contours = contours.filter(function (c) { return c.length >= 3; });
    if (!contours.length) return { strokes: [], exact: false };

    var exact = root.getAttribute("data-glyphstudio-units") === "font";
    var xMin = Infinity, yMin = Infinity, xMax = -Infinity, yMax = -Infinity;
    contours.forEach(function (c) {
      c.forEach(function (p) {
        if (p[0] < xMin) xMin = p[0];
        if (p[0] > xMax) xMax = p[0];
        if (p[1] < yMin) yMin = p[1];
        if (p[1] > yMax) yMax = p[1];
      });
    });

    var mapPoint;
    if (exact) {
      // studio export: already font units, y negated
      mapPoint = function (p) { return [Math.round(p[0]), Math.round(-p[1])]; };
    } else {
      // fit uniformly into the em box: bottom on the baseline, left at 40
      var w = Math.max(1, xMax - xMin), h = Math.max(1, yMax - yMin);
      var scale = Math.min(880 / h, 1250 / w);
      mapPoint = function (p) {
        return [Math.round((p[0] - xMin) * scale + 40),
                Math.round((yMax - p[1]) * scale)];
      };
    }

    var total = 0;
    var strokes = [];
    contours.forEach(function (c) {
      var pts = decimate(c.map(mapPoint));
      if (pts.length < 3 || total + pts.length > MAX_POINTS) return;
      total += pts.length;
      strokes.push({ fill: true, points: pts });
    });
    return { strokes: strokes, exact: exact };
  }

  window.SVGImport = { parse: parse };
})();
