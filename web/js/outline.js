/*
 * Stroke → outline expansion.
 *
 * Sketches are stored as center-line polylines with a stroke width. Points
 * are [x, y] or [x, y, w] where w is a per-point width in font units
 * (recorded from stylus pressure). Each stroke expands into a closed
 * polygon: offset the polyline to both sides and close it with caps shaped
 * by the project's nib (see penRadius — round by default, squared as the
 * exponent rises).
 * Overlapping strokes fill correctly because TrueType uses the nonzero
 * winding rule and every polygon we emit winds the same way.
 *
 * The same algorithm is mirrored in pipeline/json_to_ufo.py — keep in sync.
 */
(function () {
  "use strict";

  var CAP_SEGMENTS = 8; // half-circle cap resolution
  var DEFAULT_PEN = 2;  // superellipse exponent: 2 round, 4 squircle, 8 slab

  /* How far the unit nib reaches in direction theta. Polar form, because
     the stroke sides are offset along the NORMAL and the cap has to be
     described the same way or the two do not meet. 2 gives 1.0 everywhere
     and the maths collapses back to a circle. Mirror of _pen_radius(). */
  function penRadius(theta, n) {
    if (n === DEFAULT_PEN) return 1;
    var c = Math.abs(Math.cos(theta)), s = Math.abs(Math.sin(theta));
    return Math.pow(Math.pow(c, n) + Math.pow(s, n), -1 / n);
  }

  var penShape = DEFAULT_PEN;
  function setPen(n) {
    n = parseFloat(n);
    penShape = (isFinite(n) && n >= 2 && n <= 12) ? n : DEFAULT_PEN;
  }

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
    var steps = penShape === DEFAULT_PEN ? CAP_SEGMENTS : CAP_SEGMENTS * 3;
    for (var i = 0; i <= steps; i++) {
      var a = a0 + (a1 - a0) * (i / steps);
      var rr = r * penRadius(a, penShape);
      out.push([cx + rr * Math.cos(a), cy + rr * Math.sin(a)]);
    }
  }

  function circle(cx, cy, r) {
    var out = [];
    var n = CAP_SEGMENTS * (penShape === DEFAULT_PEN ? 4 : 8);
    for (var i = 0; i < n; i++) {
      var a = (i / n) * Math.PI * 2;
      var rr = r * penRadius(a, penShape);
      out.push([cx + rr * Math.cos(a), cy + rr * Math.sin(a)]);
    }
    return out;
  }

  /*
   * Expand one stroke {width, points} into one closed polygon
   * (array of [x, y]). Returns null for empty strokes.
   * A stroke marked fill:true is already a closed contour (e.g. an
   * imported SVG outline): its points ARE the polygon, no expansion.
   */
  function strokeToPolygon(stroke) {
    if (stroke.fill) {
      return (stroke.points && stroke.points.length >= 3)
        ? stroke.points : null;
    }
    var baseR = Math.max(1, stroke.width / 2);
    var pts = dedupe(stroke.points, baseR * 0.35);
    if (!pts.length) return null;
    if (pts.length === 1) {
      return circle(pts[0][0], pts[0][1], ptWidth(pts[0], stroke.width) / 2);
    }

    pts = smooth(pts, 2);

    // per-point radii (pressure) and normals, averaged at joints
    var radii = [], normals = [], angles = [];
    var i, dx, dy, len;
    for (i = 0; i < pts.length; i++) {
      radii.push(Math.max(1, ptWidth(pts[i], stroke.width) / 2));
      var a = pts[Math.max(0, i - 1)];
      var b = pts[Math.min(pts.length - 1, i + 1)];
      dx = b[0] - a[0]; dy = b[1] - a[1];
      len = Math.hypot(dx, dy) || 1;
      normals.push([-dy / len, dx / len]);
      angles.push(Math.atan2(dx / len, -dy / len));
    }

    // Offset by the nib's reach in each normal direction, not a bare
    // radius: that is what fattens the flats and thins the diagonals.
    var left = [], right = [];
    for (i = 0; i < pts.length; i++) {
      var n = normals[i], r = radii[i], ang = angles[i];
      var outR = r * penRadius(ang, penShape);
      var backR = r * penRadius(ang + Math.PI, penShape);
      left.push([pts[i][0] + n[0] * outR, pts[i][1] + n[1] * outR]);
      right.push([pts[i][0] - n[0] * backR, pts[i][1] - n[1] * backR]);
    }

    var poly = left.slice();

    // end cap: half-circle from left offset around to right offset
    var pe = pts[pts.length - 1];
    var ae = angles[angles.length - 1];
    arc(pe[0], pe[1], radii[radii.length - 1], ae, ae - Math.PI, poly);

    for (i = right.length - 1; i >= 0; i--) poly.push(right[i]);

    // start cap
    var ps = pts[0];
    var as = angles[0] + Math.PI;
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
    smooth: smooth,
    // the project's nib shape, so the canvas previews what the build emits
    setPen: setPen,
    getPen: function () { return penShape; }
  };
})();
