"""The studio and the pipeline must expand a stroke identically.

`web/js/outline.js` and `stroke_to_polygon` in `pipeline/json_to_ufo.py`
are two implementations of the same geometry, deliberately: one previews
in the browser what the other builds. CLAUDE.md's first rule about them
is "change both or neither", and until now that was enforced by reading
carefully. It is a bad thing to enforce by reading — a mismatch does not
crash, it just means a contributor draws one letterform and ships a
different one.

node can run the browser half directly, so the two can simply be asked
the same question. Each case below is a stroke the studio can produce;
the two polygons have to agree point for point.

Per-point widths get their own cases because the **Taper** setting made
them ordinary: before it, only a stylus wrote them, and none of the
committed projects contain a single one.

Skipped when node is not installed; CI runners have it.

    cd pipeline && python3 -m pytest tests/test_outline_mirror.py -q
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
OUTLINE_JS = ROOT / "web" / "js" / "outline.js"
NODE = shutil.which("node")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import json_to_ufo  # noqa: E402

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

DRIVER = """
var fs = require("fs");
global.window = {};
new Function(fs.readFileSync(process.argv[2], "utf8"))();
var job = JSON.parse(process.argv[3]);
window.Outline.setPen(job.pen);
console.log(JSON.stringify(window.Outline.strokeToPolygon(job.stroke)));
"""


@pytest.fixture(scope="module")
def driver(tmp_path_factory):
    path = tmp_path_factory.mktemp("outline") / "driver.js"
    path.write_text(DRIVER, encoding="utf-8")
    return path


def browser_polygon(driver, stroke, pen):
    job = json.dumps({"stroke": stroke, "pen": pen})
    proc = subprocess.run([NODE, str(driver), str(OUTLINE_JS), job],
                          capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


# Each is (name, stroke, pen). Pen 2 is the round nib every shipped
# family but the display faces uses; 4 and 8 are the squircle and slab.
CASES = [
    ("a plain stem",
     {"width": 60, "points": [[100, 0], [100, 550]]}, 2),
    ("a bowl with a corner",
     {"width": 60, "points": [[100, 0], [100, 550], [500, 550], [500, 0]]}, 2),
    ("a single point is a dot",
     {"width": 60, "points": [[300, 700]]}, 2),
    ("a tapered stroke (what Taper writes)",
     {"width": 60, "points": [[100, 0, 70], [100, 200, 55], [140, 420, 38],
                              [220, 540, 26]]}, 2),
    ("a tapered dot",
     {"width": 60, "points": [[300, 700, 92]]}, 2),
    ("widths on some points only (a stylus lifting)",
     {"width": 60, "points": [[0, 0], [200, 40, 44], [400, 0]]}, 2),
    ("a tapered stroke under a squircle nib",
     {"width": 60, "points": [[100, 0, 70], [100, 200, 55], [140, 420, 38],
                              [220, 540, 26]]}, 4),
    ("a tapered stroke under a slab nib",
     {"width": 60, "points": [[100, 0, 70], [100, 200, 55], [140, 420, 38],
                              [220, 540, 26]]}, 8),
    ("a filled contour passes straight through",
     {"fill": True, "points": [[0, 0], [100, 0], [100, 100], [0, 100]]}, 2),
    ("a stroke whose last two points share a position",
     {"width": 60, "points": [[0, 0], [200, 200], [260, 260], [260, 260, 30]]},
     2),
]


@pytest.mark.parametrize("name,stroke,pen",
                         CASES, ids=[c[0] for c in CASES])
def test_both_halves_expand_a_stroke_the_same_way(driver, name, stroke, pen):
    theirs = browser_polygon(driver, stroke, pen)
    ours = json_to_ufo.stroke_to_polygon(stroke, 1.0, pen)
    assert (ours is None) == (theirs is None), name
    if ours is None:
        return
    assert len(ours) == len(theirs), (
        "%s: pipeline emitted %d points, the studio %d"
        % (name, len(ours), len(theirs)))
    for i, (mine, yours) in enumerate(zip(ours, theirs)):
        assert mine[0] == pytest.approx(yours[0], abs=1e-9), "%s at %d" % (name, i)
        assert mine[1] == pytest.approx(yours[1], abs=1e-9), "%s at %d" % (name, i)


def test_the_default_nib_is_the_same_number_on_both_sides():
    proc = subprocess.run(
        [NODE, "-e",
         'global.window={};'
         'new Function(require("fs").readFileSync(process.argv[1],"utf8"))();'
         'window.Outline.setPen(999);'          # out of range → the default
         'console.log(window.Outline.getPen());',
         str(OUTLINE_JS)],
        capture_output=True, text=True, check=True)
    assert float(proc.stdout.strip()) == float(json_to_ufo.DEFAULT_PEN)
