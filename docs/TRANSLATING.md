# Translating the studio · ဘာသာပြန်ခြင်း

The studio speaks English and Burmese today. **Adding your language —
Mon, Shan, S'gaw Karen, Kayah, Pa'O, or any other — is one small file
and no build step.** A partial translation is already useful: anything
you don't translate falls back to English automatically.

This is the friendly path for
[issue #13](https://github.com/Thiha-Lynn/myanmar-glyph-studio/issues/13).

## Add a language in three steps

**1. Create `web/js/lang/<code>.js`** — use the ISO 639 code of your
language (`mnw` Mon, `shn` Shan, `ksw` S'gaw Karen, `kyu` Kayah,
`blk` Pa'O …). Start from this template and translate as many strings
as you like:

```js
/* Mon interface strings for Myanmar Glyph Studio.
 * Contributed by <your name>. Untranslated keys fall back to English. */
window.I18N.register("mnw", {
  name: "Mon",          // language name shown in the tooltip
  button: "မန်",         // short label shown on the language button
  strings: {
    pen:        "…",    // the Bézier pen tool
    brush:      "…",    // freehand brush
    erase:      "…",
    clear:      "…",
    save:       "…",
    load:       "…",
    exportFont: "…",
    help:       "…",
    fontName:   "…",
    yourName:   "…",
    testDrive:  "…"
    // …every key from web/js/i18n.js works here — open that file and
    // copy the keys you want from the STRINGS table.
  }
});
```

**2. Load it** — in `web/index.html`, uncomment (or add) the line:

```html
<script src="js/lang/mnw.js"></script>
```

**3. Try it** — open `web/index.html` in any browser (no server needed)
and click the language button (top right) until your language appears.
The button cycles English → မြန်မာ → yours.

Then open a pull request with the two files, or — if Git is not your
thing — paste the whole file into
[issue #13](https://github.com/Thiha-Lynn/myanmar-glyph-studio/issues/13)
and a maintainer will land it with your name in the commit.

## What the keys mean

Every key lives in `web/js/i18n.js` in the `STRINGS` table with its
English and Burmese text side by side — the Burmese column is usually
the best hint for how a term is used. A few that need care:

| Key | Used for |
|---|---|
| `penW`, `steady`, `guide`, `size` | sliders: stroke width, stabilizer, guide dimming, guide size |
| `advance` | the glyph's horizontal width in font units |
| `anchors`, `anchorTip` | where vowel signs / marks attach |
| `ghost`, `copyFrom` | overlaying / copying another drawn glyph |
| `snap`, `fillShape` | grid snapping; filled (solid) shapes |
| `eraserPartial`, `eraserStroke` | the two eraser modes |
| `glyphCopy`, `glyphPaste` | sharing one glyph as a text snippet |

Typography terms often have no settled translation in minority
languages — choose what a reader of your language would actually
understand, and note open questions in your PR or issue comment.

## Glyph hints (the per-letter instructions)

Each glyph's drawing hint lives in `web/data/glyphs.js` as `hint`
(English) and `hintMy` (Burmese). Per-glyph hints for more languages are
a planned follow-up — UI strings are the place to start today.
