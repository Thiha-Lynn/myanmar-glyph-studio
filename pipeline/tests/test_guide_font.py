"""What the bundled guide face is, measured — because the studio draws it.

`web/fonts/Padauk-Regular.ttf` is not decoration. Contributors trace it,
and the canvas now draws a line at the height its letters actually reach,
measured from the rendered face at runtime. That line encodes two claims
about Myanmar type that came from measuring this file, and both would be
silently wrong if the bundled guide were ever swapped:

  * **Myanmar does not overshoot.** Round letters (ဝ ဂ ပ င ဒ သ) and flat
    ones (က ခ တ မ လ) reach exactly the same height, so ONE line is an
    honest target for the whole alphabet. Latin does not work this way,
    which is the second claim.
  * **Latin, in this same face, does overshoot** — O rides past H — so
    the studio samples flat letters only when the glyph being drawn is
    Latin, and a different height for capitals than for x-height.

The third claim is the one that started it: every consonant tops out
around 448 per 1000 em, about a hundred units BELOW the line the canvas
used to label "body 550" — which is where marks attach, not where
letters end.

    cd pipeline && python3 -m pytest tests/test_guide_font.py -q
"""

from pathlib import Path

import pytest
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

GUIDE = Path(__file__).resolve().parent.parent.parent / "web" / "fonts" / "Padauk-Regular.ttf"

# the studio's own em; Padauk is 1024, so everything is normalised
UPM = 1000

ROUND = "ဝဂပငဒသ"
FLAT = "ကခတမလ"
CONSONANTS = "ကခဂဃငစဆဇညဋဌဍဎဏတထဒဓနပဖဗဘမယရလဝသဟဠအ"


@pytest.fixture(scope="module")
def face():
    font = TTFont(GUIDE)
    return font, font.getGlyphSet(), font.getBestCmap(), font["head"].unitsPerEm


def top_of(face, ch):
    font, glyphs, cmap, upm = face
    name = cmap.get(ord(ch))
    if name is None:
        return None
    pen = BoundsPen(glyphs)
    glyphs[name].draw(pen)
    return None if pen.bounds is None else pen.bounds[3] * UPM / upm


def test_the_guide_font_is_where_the_studio_expects_it():
    assert GUIDE.exists(), "the bundled guide face is missing"


def test_myanmar_letters_do_not_overshoot(face):
    """Round and flat letters share a height, so one line fits all."""
    round_tops = [top_of(face, c) for c in ROUND]
    flat_tops = [top_of(face, c) for c in FLAT]
    assert all(t is not None for t in round_tops + flat_tops)
    spread = max(round_tops + flat_tops) - min(round_tops + flat_tops)
    assert spread < 5, (
        "round %r vs flat %r — if Myanmar started overshooting, one "
        "letter-height line would no longer be honest"
        % (round_tops, flat_tops))


def test_every_consonant_reaches_about_the_same_height(face):
    tops = [t for t in (top_of(face, c) for c in CONSONANTS) if t is not None]
    assert len(tops) >= 30
    assert max(tops) - min(tops) < 15
    assert 435 < sum(tops) / len(tops) < 460, (
        "the studio draws its letter-height line from this; the canvas "
        "also draws the mark line at 550, a hundred units higher")


def test_letters_stop_far_below_the_mark_line(face):
    """The line labelled 550 is where top marks attach (json_to_ufo's
    BODY), not a height to draw to — this is the gap that used to be
    invisible."""
    tops = [t for t in (top_of(face, c) for c in CONSONANTS) if t is not None]
    assert 550 - max(tops) > 80


def test_latin_in_the_same_face_does_overshoot(face):
    """Which is why the studio samples flat letters for Latin."""
    flat_caps = max(top_of(face, c) for c in "HEX")
    round_cap = top_of(face, "O")
    assert round_cap > flat_caps + 5, (
        "flat caps %.0f, O %.0f" % (flat_caps, round_cap))
    flat_lower = max(top_of(face, c) for c in "xnu")
    assert top_of(face, "o") > flat_lower - 1
    # ...and that Latin capitals are a different height entirely from
    # Myanmar letters, so sharing one line would be wrong
    myanmar = max(top_of(face, c) for c in CONSONANTS)
    assert flat_caps - myanmar > 100
