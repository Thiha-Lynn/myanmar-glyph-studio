# The drawing side of the studio

Everything else in this repository is about what happens *after* a letter
exists: expansion into outlines, shaping rules, validation against three
engines. This page is about the minute before that — a hand, a pointer,
and the stroke it is trying to lay down.

Most of it is one file, [`web/js/stabilizer.js`](../web/js/stabilizer.js),
plus the input path in [`web/js/editor.js`](../web/js/editor.js).

## Steady — the hand that does not shake

Somebody drawing 147 letters with a mouse, a finger, or a pen on a cheap
tablet is fighting their own tremor the whole way. The **Steady** slider
(brush options, 0–10) is the answer, and how it works decides whether the
letters come out looking drawn or looking wobbly.

### Why not just average the input

The obvious approach, and the one this studio shipped first, is an
exponential moving average: each new point is pulled a fraction of the
way toward the pointer. It has two flaws that are not obvious until you
have drawn a few hundred glyphs with it.

**It cannot tell shake from intent.** An average attenuates *everything*
by the same factor: a tremor and a deliberate corner are the same signal
to it, so turning the setting up enough to kill the first also rounds off
the second.

**It never catches up.** The ink trails the pointer by a lag that is
proportional to speed and never resolves, so when you lift, the stroke
stops short of where your hand was — by 6 font units at the old default
and 28 at the heaviest setting. On a Myanmar bowl that is a visible gap
exactly where the curve has to close.

### The pulled string

The ink is dragged behind the pointer on a rope of length R:

* move the pointer **less than R** and the ink does not move at all.
  Tremor is not attenuated, it is gone. This matters more than it sounds:
  physiological hand tremor is an 8–12 Hz oscillation, so at a 120 Hz
  pointer it is *correlated* across a dozen samples — an average over
  three of them barely touches it, while a dead zone removes it outright.
* move further and the ink follows exactly, one R behind, so the
  curvature of a deliberate curve survives.
* the lag is bounded by R and never grows, and `finish()` spends it: when
  you lift, the ink walks up to the true last point. **Strokes end where
  the hand ended**, at every setting.

R is set in *screen pixels* and converted to font units per stroke. Hand
tremor belongs to the hand, not to the zoom level, so one setting has to
mean a bigger correction in font units when you are zoomed in on a serif
and a smaller one when the whole letter is on screen.

Three corrections keep the model honest:

| Problem | Correction |
|---|---|
| A constant rope rides ≈ R²/2ρ *inside* a curve of radius ρ — at Steady 10 the rope is longer than a Myanmar curl's radius, so the curl would come out a blob | Cap the rope at `sqrt(2·tol·ρ)`, where ρ is the turn radius the pointer is actually describing, measured three-point on the raw path (it keeps moving even when a long rope has nearly frozen the ink, and its tremor cancels because the turn is signed rather than summed) |
| A hand shaking *in place* also describes a tiny circle, so that cap would collapse to nothing and ink the wobble faithfully | Never shorten the rope below a quarter of its length |
| A stroke that begins with a rope already paid out starts in the wrong place | R grows from zero with the stroke, so the entry is exactly where you put it |

### What it is worth

`node pipeline/stabilizer/bench.js` replays four shapes a Myanmar letter
is made of — a stem, a bowl, a tight curl, a square corner — drawn by a
simulated hand, and measures how far the result strays from the shape
that hand meant. Numbers are font units on a 1000 upm em.

```
PHYSIOLOGICAL TREMOR — 9 Hz, ±3 px, plus ±0.7 px of digitizer noise
shape   Steady |      1     3     6    10  |  ink left short of the lift point
stem       was |   3.4   2.6   1.8   1.2  |     1    6   13   24
           now |   2.4   2.0   1.6   1.2  |     0    0    0    0
bowl       was |   3.4   2.6   1.8   1.8  |     3   10   18   28
           now |   2.4   2.0   1.7   1.6  |     0    0    0    0
curl       was |   3.3   2.6   2.5   4.3  |     2    6   12   20
           now |   2.4   2.0   2.1   3.4  |     0    0    0    0
corner     was |   3.5   2.6   1.9   1.8  |     2    8   17   27
           now |   2.5   2.2   1.9   2.0  |     0    0    0    0
```

Better or equal in 14 of 16 cells, and the endpoint gap is gone
everywhere. The gains are largest at the light settings people actually
leave switched on, and largest of all on the curl, which is where the old
filter got *worse* as you turned it up.

One honest caveat, which is why the benchmark prints it: against **white
sensor noise alone** — no tremor — a plain average is the mathematically
right tool, and at heavy settings on curved shapes it still wins. That
case is also the one that flattered the old design, which is exactly why
the tremor model is the one the constants were tuned against.

The properties, rather than the numbers, are pinned in
[`pipeline/tests/test_web_stabilizer.py`](../pipeline/tests/test_web_stabilizer.py):
node drives the module directly, so the promises are part of `pytest`.

### Seeing the lag

A steadied stroke lags the pointer by design, and without something drawn
between the two that lag reads as a dropped frame. While a steadied
stroke is live, a dashed leash runs from the ink to a small ring at the
real pointer position. It appears only once the gap is wide enough to
notice.

## Taper — width from speed

A stylus reports pressure and the studio has always used it. Everyone
else got a constant width. **Taper** (0–10) lets *speed* stand in: press
slowly and the stroke thickens, flick and it thins away, which is how a
brush behaves and how the strokes of a Myanmar letter are written.

It writes the same optional third element of each point that pressure
does — `[x, y, width]` — which
[`web/js/outline.js`](../web/js/outline.js) and
[`pipeline/json_to_ufo.py`](../pipeline/json_to_ufo.py) already read, so
a tapered stroke needs nothing new anywhere else in the toolchain. A
stylus still wins where it is present: real pressure beats a guess.

Off by default — it changes the shape of what you draw, and that should
be a decision.

## Drawing with a stylus

The studio has always read stylus pressure. Two settings under **⚙** make
that a tool rather than a fixed behaviour, and both are stylus-only —
they do nothing under a finger or a mouse.

**Pressure** (0–10) is how far pressure may move the width. 10 is the
curve the studio always had, `0.35 + 1.3p`; lower amounts pull it toward
a constant width, which is what you want with a pen (or a hand) whose
usable range is narrow, and 0 turns it off. It replaced a checkbox, and
an old unticked box becomes an amount of 0.

**Tilt** (0–10) broadens the stroke as you lay the pen over, the way a
chisel nib does. Safari gives Apple Pencil's `altitudeAngle`; Chromium
browsers give `tiltX`/`tiltY`; both are read, so an iPad and a Wacom feel
the same. It multiplies whatever width dynamic is already in play, so
pressure and tilt work together.

Both write the same optional per-point width that the pipeline already
reads. Nothing else in the toolchain had to change.

Two smaller things a pen user meets first:

* **Palm rejection arms on hover.** An Apple Pencil that supports hover
  announces itself before it touches down, so the switch to
  pen-draws/fingers-pan happens then, instead of the first stroke being
  the one that discovers it.
* **Flip the pen over** and the eraser end borrows the eraser for as long
  as it is down — and hands the tool back when *that* pointer lifts, so a
  resting finger coming up does not end the erase.

## On an iPad

An iPad in portrait is 1032 points wide, which is *above* the studio's
drawer breakpoint — so the glyph list was a permanent 300-point column
with no way to dismiss it while drawing. **☰** now folds it away at any
width and remembers the choice; on the iPad that is the difference
between a 648-point canvas and a 948-point one.

The canvas also refuses iPadOS's callout and text selection, so a resting
palm cannot raise a menu over your drawing.

## The numbers under the glyph's name

Ink width, the two sidebearings (◧ ◨), and how far the ink reaches above
and below the baseline — turning red when it passes the ascender (900) or
the descender (−600), which the full build checks and reports much later,
in a file nobody reads mid-drawing. **⚙ → Fit width** sets the advance
from the ink with the same sidebearing on both sides; **Center** moves
the ink inside the advance you already have.

## The letter-height line

The canvas has always drawn a line at 550. It was labelled "body", and a
line across a canvas reads as *the height to draw up to*. It is not: 550
is where top marks attach (`BODY` in `json_to_ufo.py`).

Measured in the bundled Padauk, every Myanmar consonant tops out at
**439–449 per 1000 em** — around a hundred units below that line. This
project's own font, traced against that same guide with nothing to aim
at, came out ranging 420 to 458.

So the canvas now measures the guide face itself — it renders a spread of
consonants offscreen and reads the ink's top edge — and draws a gold line
there, labelled with the number. Trace a different face with **Guide
font** and the line follows it.

One line is honest for the whole alphabet because **Myanmar does not
overshoot**: measured in Padauk, round letters (ဝ ဂ ပ င ဒ သ) and flat
ones (က ခ တ မ လ) share their extremes exactly. Latin, in the same file,
does overshoot — O reaches 640 where H E X stop at 628 — so when the
glyph being drawn is Latin the studio samples flat letters only, and uses
cap height for capitals and x-height for lowercase. Those measurements
are pinned in
[`pipeline/tests/test_guide_font.py`](../pipeline/tests/test_guide_font.py),
so swapping the bundled guide re-checks them.

The 550 line is still drawn, now labelled **marks 550**, because that is
what it is.

## The rest of the drawing panel

| | |
|---|---|
| **Nib ring** | The brush cursor is a ring the size of the actual nib, so width is something you see before the stroke instead of judging after it. |
| **Corner readout** | The pointer's position in font units, bottom left. These are the numbers that matter when a stroke has to land on the body line at 550 or stay inside the advance. |
| **Shift** | Held mid-stroke, the stroke runs dead straight from where Shift went down to the pointer — stems and cross-bars, drawn by hand but true. Let go and freehand resumes from the end of the straight run. |
| **`,` and `.`** | Brush width or eraser size from the keyboard (Shift for bigger steps) — focus mode and a stylus in the other hand should not mean reaching for a slider. |
| **Flip the stylus** | A Wacom or Surface pen's eraser end borrows the eraser for as long as it is down, then hands your tool back. |
| **Per-glyph undo** | Undo history belongs to the glyph, not to the session, so hopping to the next letter and back no longer throws it away. The last 12 glyphs keep their stacks. |
| **Find a letter** | The filter above the glyph list matches the letter itself, the Unicode name, a code point, the English or Burmese hint, or the group. While a filter is on, `[` `]` and **Next empty** walk only the matches — filter to “shan” and the arrows step through that block alone. `/` jumps to the box. |
| **☰** | Folds the glyph list away at any screen width (on phones it is the drawer, as before). |

## Where the code lives

| File | What it holds |
|---|---|
| `web/js/stabilizer.js` | The rope. Pure geometry, no DOM — which is why a test can drive it. |
| `web/js/editor.js` | Pointer routing, the freehand sampling loop, width dynamics, undo, the canvas. |
| `web/js/vectools.js` | Select, direct node editing, the Bézier pen. |
| `web/js/outline.js` | Stroke → outline expansion. **Mirrored in `pipeline/json_to_ufo.py`** — change both or neither. |

The stabilizer deliberately is *not* in that mirrored set: it shapes the
points a hand produces, before they are stored. The pipeline reads the
stored polyline and never needs to know how it was steadied.
