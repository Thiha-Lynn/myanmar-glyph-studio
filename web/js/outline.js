/*
 * Stroke → outline expansion.
 *
 * Sketches are stored as center-line polylines with a stroke width. Points
 * are [x, y] or [x, y, w] where w is a per-point width in font units
 * (recorded from stylus pressure). Each stroke expands into a closed
 * polygon: offset the polyline to both sides and close it with round caps.
 * Overlapping strokes fill correctly because TrueType uses the nonzero
 * winding rule and every polygon we emit winds the same way.
 *
 * The same algorithm is mirrored in pipeline/json_to_ufo.py — keep in sync.
 */
(function () {
  "use strict";

  var CAP_SEGMENTS = 8; // half-circle cap resolution

  function ptWidth(p, fallback) {
    return (p.length > 2 && p[2] > 0) ? p[2] : fallback;
  }

  function dedupe(points, minDist) {
    var out = [];
    for (var i = 0; i < points.length; i++) {
      var p = points[i];
      if (!out.length) { out.push(p); continue; }
      var q = out[out.length - 1];
      var dx = p[0] - q[0], dy = p[1] - q[1];
      if (dx * dx + dy * dy >= minDist * minDist) out.push(p);
    }
    // keep the true endpoint so short strokes don't shrink
    if (out.length && points.length > 1) {
      var last = points[points.length - 1];
      var tail = out[out.length - 1];
      if (last[0] !== tail[0] || last[1] !== tail[1]) out.push(last);
    }
    return out;
  }

  // Chaikin corner-cutting: cheap, stable smoothing for hand input.
  // Interpolates the optional per-point width as well.
  function smooth(points, iterations) {
    function lerp(p, q, t) {
      var out = [p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t];
      if (p.length > 2 || q.length > 2) {
        var pw = p.length > 2 ? p[2] : q[2];
        var qw = q.length > 2 ? q[2] : p[2];
        out.push(pw + (qw - pw) * t);
      }
      return out;
    }
    for (var it = 0; it < iterations; it++) {
      if (points.length < 3) return points;
      var out = [points[0]];
      for (var i = 0; i < points.length - 1; i++) {
        out.push(lerp(points[i], points[i + 1], 0.25));
        out.push(lerp(points[i], points[i + 1], 0.75));
      }
      out.push(points[points.length - 1]);
      points = out;
    }
    return points;
  }

  function arc(cx, cy, r, a0, a1, out) {
    for (var i = 0; i <= CAP_SEGMENTS; i++) {
      var a = a0 + (a1 - a0) * (i / CAP_SEGMENTS);
      out.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
    }
  }

  function circle(cx, cy, r) {
    var out = [];
    var n = CAP_SEGMENTS * 4;
    for (var i = 0; i < n; i++) {
      var a = (i / n) * Math.PI * 2;
      out.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
    }
    return out;
  }

  /*
   * Expand one stroke {width, points} into one closed polygon
   * (array of [x, y]). Returns null for empty strokes.
   */
  function strokeToPolygon(stroke) {
    var baseR = Math.max(1, stroke.width / 2);
    var pts = dedupe(stroke.points, baseR * 0.35);
    if (!pts.length) return null;
    if (pts.length === 1) {
      return circle(pts[0][0], pts[0][1], ptWidth(pts[0], stroke.width) / 2);
    }

    pts = smooth(pts, 2);

    // per-point radii (pressure) and normals, averaged at joints
    var radii = [], normals = [];
    var i, dx, dy, len;
    for (i = 0; i < pts.length; i++) {
      radii.push(Math.max(1, ptWidth(pts[i], stroke.width) / 2));
      var a = pts[Math.max(0, i - 1)];
      var b = pts[Math.min(pts.length - 1, i + 1)];
      dx = b[0] - a[0]; dy = b[1] - a[1];
      len = Math.hypot(dx, dy) || 1;
      normals.push([-dy / len, dx / len]);
    }

    var left = [], right = [];
    for (i = 0; i < pts.length; i++) {
      var n = normals[i], r = radii[i];
      left.push([pts[i][0] + n[0] * r, pts[i][1] + n[1] * r]);
      right.push([pts[i][0] - n[0] * r, pts[i][1] - n[1] * r]);
    }

    var poly = left.slice();

    // end cap: half-circle from left offset around to right offset
    var pe = pts[pts.length - 1], ne = normals[pts.length - 1];
    var ae = Math.atan2(ne[1], ne[0]);
    arc(pe[0], pe[1], radii[radii.length - 1], ae, ae - Math.PI, poly);

    for (i = right.length - 1; i >= 0; i--) poly.push(right[i]);

    // start cap
    var ps = pts[0], ns = normals[0];
    var as = Math.atan2(-ns[1], -ns[0]);
    arc(ps[0], ps[1], radii[0], as, as - Math.PI, poly);

    return poly;
  }

  function glyphPolygons(glyphData) {
    var polys = [];
    (glyphData.strokes || []).forEach(function (s) {
      var p = strokeToPolygon(s);
      if (p) polys.push(p);
    });
    return polys;
  }

  function bounds(polys) {
    var xMin = Infinity, yMin = Infinity, xMax = -Infinity, yMax = -Infinity;
    polys.forEach(function (poly) {
      poly.forEach(function (p) {
        if (p[0] < xMin) xMin = p[0];
        if (p[0] > xMax) xMax = p[0];
        if (p[1] < yMin) yMin = p[1];
        if (p[1] > yMax) yMax = p[1];
      });
    });
    if (xMin === Infinity) return null;
    return { xMin: xMin, yMin: yMin, xMax: xMax, yMax: yMax };
  }

  window.Outline = {
    strokeToPolygon: strokeToPolygon,
    glyphPolygons: glyphPolygons,
    bounds: bounds,
    smooth: smooth
  };
})();
