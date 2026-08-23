/*
 * The steady hand behind the brush.
 *
 * A tremor-free line is not the same thing as an averaged line. Averaging
 * — what this studio did before — treats shake and intent as one signal:
 * it rounds every corner, and it leaves the ink trailing the pointer
 * forever, so the stroke ENDS SHORT of where the hand lifted. Measured
 * against a 9 Hz tremor at the old default that gap was 6 font units, and
 * 28 at the heaviest setting: a visible break where a Myanmar bowl has to
 * close.
 *
 * This is the pulled-string model instead. The ink is dragged behind the
 * pointer on a rope of length R:
 *
 *   - move the pointer less than R — every tremor, every stair-step of a
 *     cheap touchscreen — and the ink does not move AT ALL. Shake is not
 *     attenuated, it is gone. That matters because real hand tremor is a
 *     8-12 Hz oscillation: at a 120 Hz pointer it is CORRELATED across a
 *     dozen samples, which a short average barely touches and a dead zone
 *     removes outright.
 *   - the lag never grows past R, and finish() spends it: the ink walks
 *     up to the true lift point, so strokes end where the hand ended.
 *
 * R is set in SCREEN pixels and converted to font units per stroke. Hand
 * tremor is a property of the hand, not of the zoom level, so one setting
 * must mean a bigger correction in font units when you are zoomed in on a
 * serif and a smaller one when the whole letter is on screen.
 *
 * A constant rope would cut curves — it rides about R²/2ρ inside a curve
 * of radius ρ, which at the heaviest setting is enough to swallow a curl
 * whole. So the rope is capped by the curvature the pointer is actually
 * describing (measured three-point on the RAW path, which keeps moving
 * even when a long rope has nearly frozen the ink, and whose tremor
 * cancels because the turn is signed rather than summed): no more rope
 * than sqrt(2·tol·ρ), for a tolerance that scales with the setting — and
 * never less than a quarter of it, because a hand shaking in place also
 * describes a tiny circle, and an uncapped cap would ink the wobble. It
 * also starts at zero and grows with the stroke, so the entry is exactly
 * where the hand put it.
 *
 * Constants below were measured, not guessed — see
 * pipeline/tests/test_web_stabilizer.py and docs/EDITOR.md.
 *
 * Pure geometry, no DOM: editor.js and the test drive it the same way.
 */
(function () {
  "use strict";

  /* Rope length in screen pixels. 0 = off (the raw pointer, untouched);
     3 (the default) is about a finger's worth of tremor; 10 is the
     "drawing with a mouse on a bumpy table" setting. */
  function radiusPx(strength) {
    var s = +strength;
    if (!isFinite(s) || s <= 0) return 0;
    return 2 + Math.min(10, s) * 3.2;
  }

  /* How much of the remaining distance the ink covers per sample once the
     rope is taut. 1 = pure rope (crisp, but faceted on jittery input); a
     little less rounds the facets off. The extra lag it costs is repaid
     by finish(). */
  function ease(strength) {
    return Math.max(0.5, 1 - 0.045 * clampStrength(strength));
  }

  /* Raw samples averaged before the rope sees them. The rope handles
     correlated tremor; this handles the digitizer's own white noise,
     which averaging IS the right tool for. Kept short — 4 samples at
     120 Hz is 33 ms, far below any intentional movement. */
  function preSamples(strength) {
    return Math.min(4, 1 + Math.round(clampStrength(strength) / 3));
  }

  function clampStrength(s) {
    s = +s;
    return isFinite(s) ? Math.min(10, Math.max(0, s)) : 0;
  }

  /*
   * create({strength, unitsPerPx, start})
   *   push(raw)  -> [] or [[x, y]] — the stabilized point(s) to append
   *   finish()   -> the catch-up tail, ending on the last raw point
   *   tip()      -> where the ink currently is
   *
   * Coordinates are font units throughout; unitsPerPx is 1 / editor scale.
   */
  function create(opts) {
    opts = opts || {};
    var strength = clampStrength(opts.strength);
    var upp = opts.unitsPerPx > 0 ? opts.unitsPerPx : 1;
    var R = radiusPx(strength) * upp;      // rope length, font units
    var k = ease(strength);
    var tol = Math.max(1.5, 0.06 * R);     // how far inside a curve to ride
    var winMin = 12 * upp, winMax = 24 * upp;
    var maxWin = Math.max(winMin, Math.min(winMax, R * 2.5));
    var preN = preSamples(strength);

    var start = opts.start || [0, 0];
    var tip = [start[0], start[1]];
    var lastRaw = [start[0], start[1]];    // the true pointer, for finish()
    var dir = null;                        // unit vector of the ink's travel
    var travel = 0;                        // ink laid down so far
    var pre = [[start[0], start[1]]];      // pre-average ring
    var win = [[start[0], start[1]]];      // raw-path window for curvature
    var winLen = 0;
    var rho = Infinity;                    // turn radius the hand is describing

    function averaged(raw) {
      pre.push(raw);
      if (pre.length > preN) pre.shift();
      var sx = 0, sy = 0;
      for (var i = 0; i < pre.length; i++) { sx += pre[i][0]; sy += pre[i][1]; }
      return [sx / pre.length, sy / pre.length];
    }

    /* Three-point turn radius over the last maxWin of raw path. Signed
       turn, so tremor cancels instead of accumulating. */
    function trackCurvature(p) {
      var prev = win[win.length - 1];
      var step = Math.hypot(p[0] - prev[0], p[1] - prev[1]);
      if (step <= 0) return;
      win.push(p);
      winLen += step;
      while (winLen > maxWin && win.length > 3) {
        var a = win[0], b = win[1];
        winLen -= Math.hypot(b[0] - a[0], b[1] - a[1]);
        win.shift();
      }
      if (win.length < 3 || winLen < 10) return;
      var m = win[Math.floor((win.length - 1) / 2)];
      var last = win[win.length - 1];
      var v1x = m[0] - win[0][0], v1y = m[1] - win[0][1];
      var v2x = last[0] - m[0], v2y = last[1] - m[1];
      var l1 = Math.hypot(v1x, v1y), l2 = Math.hypot(v2x, v2y);
      if (l1 < 1e-6 || l2 < 1e-6) return;
      var cross = (v1x * v2y - v1y * v2x) / (l1 * l2);
      var dot = (v1x * v2x + v1y * v2y) / (l1 * l2);
      var turn = Math.abs(Math.atan2(cross, dot));
      rho = turn > 1e-4 ? ((l1 + l2) / 2) / turn : Infinity;
    }

    return {
      radius: R,

      tip: function () { return [tip[0], tip[1]]; },

      /* Feed one raw pointer sample; get back what to draw (if anything). */
      push: function (raw) {
        lastRaw = [raw[0], raw[1]];
        if (R <= 0) { tip = [raw[0], raw[1]]; return [[raw[0], raw[1]]]; }

        var p = averaged([raw[0], raw[1]]);
        trackCurvature(p);

        var dx = p[0] - tip[0], dy = p[1] - tip[1];
        var dist = Math.hypot(dx, dy);
        if (dist <= 0) return [];

        var r = R;
        // No more rope than the curve the hand is drawing can afford —
        // but never less than a quarter of it, or a hand shaking in place
        // describes a tiny circle, the cap collapses, and the wobble is
        // faithfully inked.
        if (isFinite(rho)) {
          r = Math.max(Math.min(r, Math.sqrt(2 * tol * rho)), R * 0.25);
        }
        // ...and none at all at the very start, so the entry is exact
        r = Math.min(r, travel * 0.6);
        // a reversal is intent, not tremor: let the ink into the corner
        if (dir) {
          var fwd = (dx / dist) * dir[0] + (dy / dist) * dir[1];
          if (fwd < 0.5) r *= 0.35 + 0.65 * (fwd + 1) / 1.5;
        }
        if (dist <= r) return [];        // inside the dead zone: shake, drop it

        // stand r behind the pointer, easing into that spot
        var t = ((dist - r) / dist) * k;
        var nx = tip[0] + dx * t, ny = tip[1] + dy * t;
        var mx = nx - tip[0], my = ny - tip[1];
        var moved = Math.hypot(mx, my);
        if (moved <= 0) return [];
        dir = [mx / moved, my / moved];
        travel += moved;
        tip = [nx, ny];
        return [[nx, ny]];
      },

      /*
       * Spend the lag. The rope is at most R long, so the ink is at most R
       * short of where the hand lifted — walk it there in steps dense
       * enough for the outline expander to cap cleanly.
       */
      finish: function () {
        var out = [];
        if (R <= 0) return out;
        var dx = lastRaw[0] - tip[0], dy = lastRaw[1] - tip[1];
        var dist = Math.hypot(dx, dy);
        if (dist < 1) return out;
        var steps = Math.max(1, Math.min(12,
          Math.round(dist / Math.max(4, R * 0.4))));
        for (var i = 1; i <= steps; i++) {
          out.push([tip[0] + dx * (i / steps), tip[1] + dy * (i / steps)]);
        }
        tip = [lastRaw[0], lastRaw[1]];
        return out;
      }
    };
  }

  window.Stabilizer = {
    create: create,
    radiusPx: radiusPx,
    ease: ease,
    preSamples: preSamples
  };
})();
