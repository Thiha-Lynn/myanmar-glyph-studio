"""The brush stabilizer's promises, measured.

`web/js/stabilizer.js` is the one piece of the studio whose whole job is
a *feel*, which is exactly the kind of claim this project does not take
on trust. It is written as pure geometry with no DOM so it can be driven
from here: node evaluates the file with a stand-in `window`, replays a
path through it, and hands the polyline back as JSON.

What is pinned below is not the implementation but the four promises the
interface makes to someone drawing a letter:

  * off means off — strength 0 must not touch a single coordinate;
  * a hand shaking in place leaves a blot, not a scribble;
  * a stroke ENDS where the hand lifted (the old exponential average left
    it up to 28 font units short, a visible break in a Myanmar bowl);
  * turning the setting up steadies more, and never swallows a curl —
    the rope is capped by the curvature the hand is describing.

Skipped when node is not installed; CI runners have it.

    cd pipeline && python3 -m pytest tests/test_web_stabilizer.py -q
"""

import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
STABILIZER = ROOT / "web" / "js" / "stabilizer.js"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

# Replays a path through the module the way editor.js does: push() every
# raw sample, then finish() to spend the rope's lag.
DRIVER = """
var fs = require("fs");
global.window = {};
new Function(fs.readFileSync(process.argv[2], "utf8"))();
var job = JSON.parse(process.argv[3]);
var st = window.Stabilizer.create({
  strength: job.strength,
  unitsPerPx: job.unitsPerPx,
  start: job.path[0]
});
var out = [[job.path[0][0], job.path[0][1]]];
for (var i = 1; i < job.path.length; i++) {
  var got = st.push(job.path[i]);
  for (var j = 0; j < got.length; j++) out.push(got[j]);
}
st.finish().forEach(function (p) { out.push(p); });
console.log(JSON.stringify({
  points: out,
  radius: st.radius,
  radiusPx: window.Stabilizer.radiusPx(job.strength)
}));
"""


@pytest.fixture(scope="module")
def driver(tmp_path_factory):
    path = tmp_path_factory.mktemp("stab") / "driver.js"
    path.write_text(DRIVER, encoding="utf-8")
    return path


def stabilize(driver, path, strength, units_per_px=1.0):
    job = json.dumps({"strength": strength, "unitsPerPx": units_per_px,
                      "path": path})
    proc = subprocess.run([NODE, str(driver), str(STABILIZER), job],
                          capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def shaky_line(tremor_px=3.0, units_per_px=1.8, samples=120, length=400.0):
    """A straight stroke drawn by a real hand: an 8-12 Hz tremor is
    CORRELATED across samples at a 120 Hz pointer, which is why a short
    average barely touches it."""
    out = []
    for i in range(samples + 1):
        t = i / samples
        wobble = tremor_px * units_per_px * math.sin(i * 0.47)
        out.append([wobble, t * length])
    return out


def wobble_of(points):
    """rms distance from the true line x = 0."""
    return math.sqrt(sum(p[0] ** 2 for p in points) / len(points))


def test_off_means_off(driver):
    path = shaky_line()
    got = stabilize(driver, path, strength=0)["points"]
    assert got == [[p[0], p[1]] for p in path]


def test_a_hand_shaking_in_place_barely_marks_the_page(driver):
    """40 samples around a 6-unit circle: someone resting a shaky hand.
    The ink drifts a little while the rope pays out from the entry point
    (that ramp is what keeps stroke starts exact) and then locks."""
    path = [[6 * math.cos(i * 0.8), 6 * math.sin(i * 0.8)] for i in range(40)]
    got = stabilize(driver, path, strength=6, units_per_px=1.8)
    start = path[0]
    wander = max(math.hypot(p[0] - start[0], p[1] - start[1])
                 for p in got["points"])
    assert got["radius"] > 30              # the rope is far longer than the shake
    assert wander < got["radius"] * 0.3    # ...so the shake stays a blot


def test_a_stroke_ends_where_the_hand_lifted(driver):
    # the failure this replaced: an exponential average trails the pointer
    # forever, so the ink stopped short by the whole lag
    for strength in (1, 3, 6, 10):
        path = shaky_line()
        got = stabilize(driver, path, strength=strength)["points"]
        end, lift = got[-1], path[-1]
        gap = math.hypot(end[0] - lift[0], end[1] - lift[1])
        assert gap < 1.0, "strength %d ended %.1f units short" % (strength, gap)


def test_steadier_settings_steady_more(driver):
    path = shaky_line()
    raw = wobble_of(path)
    seen = []
    for strength in (0, 1, 3, 6, 10):
        seen.append(wobble_of(stabilize(driver, path, strength=strength)["points"]))
    assert seen[0] == pytest.approx(raw, rel=1e-6)   # 0 is the raw hand
    assert seen[-1] < raw * 0.5                      # 10 removes most of it
    for lighter, heavier in zip(seen, seen[1:]):
        assert heavier <= lighter + 1e-6             # monotone, no surprises


def test_a_curl_is_not_swallowed_by_a_long_rope(driver):
    """A constant rope rides about R^2/2r inside a curve of radius r, and
    at the heaviest setting R is longer than a Myanmar curl's radius —
    the curl would come out a blob. The curvature cap is what stops it."""
    radius, samples = 70.0, 200
    path = [[radius * math.cos(i / samples * 2 * math.pi),
             radius * math.sin(i / samples * 2 * math.pi)]
            for i in range(samples + 1)]
    got = stabilize(driver, path, strength=10, units_per_px=3.0)
    assert got["radius"] > radius        # the rope IS longer than the curl
    drawn = [math.hypot(p[0], p[1]) for p in got["points"][10:]]
    assert min(drawn) > radius * 0.75    # ...and the curl still has a hole
    assert sum(drawn) / len(drawn) > radius * 0.85


def test_the_rope_is_measured_on_the_screen_not_in_the_font(driver):
    """Hand tremor belongs to the hand, not to the zoom level: the same
    setting has to mean a bigger correction in font units when the view
    is zoomed in."""
    path = shaky_line()
    close = stabilize(driver, path, strength=5, units_per_px=1.0)
    far = stabilize(driver, path, strength=5, units_per_px=4.0)
    assert far["radius"] == pytest.approx(close["radius"] * 4)
    assert far["radiusPx"] == pytest.approx(close["radiusPx"])
