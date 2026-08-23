/*
 * What the brush stabilizer is worth, in font units.
 *
 *     node pipeline/stabilizer/bench.js
 *
 * The studio's rule is that a claim about typography gets measured before
 * it is believed, and "steadies a shaky hand" is exactly such a claim.
 * This replays four shapes a Myanmar letter is actually made of, drawn by
 * a simulated hand, through the algorithm the studio shipped BEFORE
 * (an exponential moving average) and the one in web/js/stabilizer.js,
 * and reports how far each result strays from the shape the hand meant.
 *
 * The tremor model is the point. Physiological hand tremor is an 8-12 Hz
 * oscillation, so at a 120 Hz pointer it is CORRELATED across a dozen
 * samples: an average over three of them barely touches it, while a dead
 * zone removes it outright. Benchmarking against white noise instead —
 * the obvious thing to reach for — flatters any averaging filter and
 * would have sent this design the wrong way, so both are reported.
 *
 * Columns are the rms distance from the intended shape, in font units of
 * a 1000 upm em, at Steady = 1 / 3 / 6 / 10. "end" is how far the ink
 * finished from where the hand lifted, which is the number that made the
 * old algorithm untenable: an average trails the pointer forever.
 */
var fs = require("fs");
var path = require("path");

var target = process.argv[2] || path.join(__dirname, "..", "..", "web", "js", "stabilizer.js");
global.window = {};
new Function(fs.readFileSync(target, "utf8"))();
var Stabilizer = window.Stabilizer;

var UPP = 1.8;      // font units per screen pixel, the default fit
var RATE = 120;     // Hz, a normal pointer
var SPEED = 500;    // font units per second, an unhurried stroke

var seed = 987654321;
function rnd() {
  seed = (seed * 1103515245 + 12345) & 0x7fffffff;
  return seed / 0x7fffffff;
}

/* ---- the hand ---------------------------------------------------------- */

function sampleAlong(fn, len) {
  var n = Math.max(8, Math.round((len / SPEED) * RATE));
  var out = [];
  for (var i = 0; i <= n; i++) out.push(fn(i / n).concat([i / RATE]));
  return out;
}

function withTremor(pts, tremorPx, whitePx) {
  var f = 9, ph1 = rnd() * 6.283, ph2 = rnd() * 6.283;
  return pts.map(function (p) {
    var t = p[2];
    return [
      p[0] + tremorPx * UPP * Math.sin(2 * Math.PI * f * t + ph1) +
        (rnd() - 0.5) * 2 * whitePx * UPP,
      p[1] + tremorPx * UPP * Math.sin(2 * Math.PI * f * t * 1.07 + ph2) +
        (rnd() - 0.5) * 2 * whitePx * UPP
    ];
  });
}

/* ---- the two algorithms ------------------------------------------------ */

// what the studio shipped until the rope replaced it
function movingAverage(raw, strength) {
  if (strength <= 0) return raw.map(function (p) { return [p[0], p[1]]; });
  var k = 1 / (1 + strength * 0.6);
  var s = [raw[0][0], raw[0][1]], out = [[s[0], s[1]]];
  for (var i = 1; i < raw.length; i++) {
    s = [s[0] + (raw[i][0] - s[0]) * k, s[1] + (raw[i][1] - s[1]) * k];
    out.push([s[0], s[1]]);
  }
  return out;
}

function pulledString(raw, strength) {
  var st = Stabilizer.create({
    strength: strength, unitsPerPx: UPP, start: raw[0]
  });
  var out = [[raw[0][0], raw[0][1]]];
  for (var i = 1; i < raw.length; i++) {
    var got = st.push(raw[i]);
    for (var j = 0; j < got.length; j++) out.push(got[j]);
  }
  st.finish().forEach(function (p) { out.push(p); });
  return out;
}

/* ---- the shapes -------------------------------------------------------- */

var SHAPES = [
  { name: "stem",   len: 700,
    fn: function (t) { return [0, t * 700]; } },
  { name: "bowl",   len: 250 * Math.PI * 1.4,
    fn: function (t) {
      var a = t * Math.PI * 1.4;
      return [250 * Math.cos(a), 250 * Math.sin(a)];
    } },
  { name: "curl",   len: 70 * Math.PI * 1.6,
    fn: function (t) {
      var a = t * Math.PI * 1.6;
      return [70 * Math.cos(a), 70 * Math.sin(a)];
    } },
  { name: "corner", len: 800,
    fn: function (t) {
      return t < 0.5 ? [t * 800, 0] : [400, (t - 0.5) * 800];
    } }
];

function idealPolyline(shape) {
  var p = [];
  for (var i = 0; i <= 600; i++) p.push(shape.fn(i / 600));
  return p;
}

function strayFrom(out, ideal) {
  var sum = 0;
  out.forEach(function (p) {
    var best = Infinity;
    for (var i = 1; i < ideal.length; i++) {
      var a = ideal[i - 1], b = ideal[i];
      var vx = b[0] - a[0], vy = b[1] - a[1];
      var l2 = vx * vx + vy * vy;
      var t = l2 ? ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / l2 : 0;
      t = Math.max(0, Math.min(1, t));
      var dx = p[0] - (a[0] + vx * t), dy = p[1] - (a[1] + vy * t);
      var d = Math.hypot(dx, dy);
      if (d < best) best = d;
    }
    sum += best * best;
  });
  return Math.sqrt(sum / out.length);
}

/* ---- the report -------------------------------------------------------- */

var STRENGTHS = [1, 3, 6, 10];

function report(title, tremorPx, whitePx) {
  console.log("\n" + title);
  console.log("shape   Steady |      1     3     6    10  |  ink left short of the lift point");
  SHAPES.forEach(function (shape) {
    var ideal = idealPolyline(shape);
    [["was", movingAverage], ["now", pulledString]].forEach(function (algo) {
      var row = [], ends = [];
      STRENGTHS.forEach(function (s) {
        seed = 987654321;
        var raw = withTremor(sampleAlong(shape.fn, shape.len), tremorPx, whitePx);
        var out = algo[1](raw, s);
        row.push(strayFrom(out, ideal).toFixed(1));
        var lift = raw[raw.length - 1], end = out[out.length - 1];
        ends.push(Math.hypot(end[0] - lift[0], end[1] - lift[1]).toFixed(0));
      });
      console.log(
        (algo[0] === "was" ? shape.name : "").padEnd(8) + algo[0].padStart(6) +
        " | " + row.map(function (v) { return v.padStart(5); }).join(" ") +
        "  |  " + ends.map(function (v) { return v.padStart(4); }).join(" "));
    });
  });
}

report("PHYSIOLOGICAL TREMOR — 9 Hz, +-3 px, plus +-0.7 px of digitizer noise",
       3, 0.7);
report("A SHAKIER HAND — 9 Hz, +-6 px", 6, 1);
report("WHITE SENSOR NOISE ALONE — +-2 px (averaging's best case)", 0, 2);
console.log("\nunits are font units of a 1000 upm em; the em is the height of the letter.");
