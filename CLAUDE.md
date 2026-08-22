# Working on this repository with an AI assistant

More and more contributions arrive with help from a coding assistant
(Claude Code, Copilot, Cursor, …). That is welcome here. This file is the
briefing such a tool should read first — the invariants that are not
obvious from the code, and that this project has already broken once
each and fixed the hard way.

Humans: [CONTRIBUTING.md](CONTRIBUTING.md) is your starting point and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) is the map. This file is a
condensed version of the traps, written for a tool that will otherwise
confidently do the wrong thing.

## The one rule that matters

**Measure it against Padauk before you believe it.** This is a
typography project, and typography advice — from a person, a model, or a
specification — is untrusted until it is measured against a real font.
This is not a stylistic preference. A 2026-08-14 external review
confidently gave vowel-attachment fractions of 0.35 when the measured
reality in Padauk is 0.78; implementing it would have broken every ကု in
the font. Three of its claims survived measurement, the rest did not.

If you cannot measure a claim, do not implement it. The tools to measure
with are already here:

```bash
mgs-validate <font.ttf>          # 1,486 spec clusters + 711 words + 1,633 Pali
python3 pipeline/coretext_check.py <font.ttf>   # vs Apple's engine (macOS)
pytest                                          # 81 tests, ~20s
```

## Pairs of files that must change together

The studio previews in the browser what the pipeline builds in Python.
Two implementations of the same maths, deliberately. Change both or
neither — a mismatch means contributors draw one thing and ship another:

| If you touch | You must also touch |
|---|---|
| stroke→outline expansion, pen nibs (`web/js/outline.js`) | `pipeline/json_to_ufo.py` |
| anchor defaults or roles (`web/js/anchors.js`) | `pipeline/json_to_ufo.py` |
| metrics (1000 UPM, baseline 0, body 550, asc +900, desc −600) | both sides |
| any file under `web/` | `web/sw.js` — bump `VERSION`, extend `ASSETS` |
| either corpus `.txt` | the counts quoted in TESTING.md, VALIDATION.md, OSS_APPLICATION.md, README, CHANGELOG |
| shaping rules in `json_to_ufo.py` | **rebuild every committed font** (below) |
| fused deep-stack pairs (`FUSED_STACKS` in `make_sample.py`) | `FUSED_STACK_PAIRS` in `json_to_ufo.py` + the fused entries in `web/data/glyphs.js` |

## Generated files — regenerate, never hand-edit

* `web/data/glyphs-extended*.js`, `glyphs-latin*.js` → `pipeline/gen_inventory.py`
* `web/data/showcase.js`, `vocabulary.js` → `pipeline/make_showcase.py`
* `web/data/book.js` → `pipeline/make_book.py`
* `web/data/tipitaka.js` + `tipitaka-index.js` → `pipeline/make_tipitaka.py` (curated texts from SuttaCentral's public-domain roman through `pali_translit.py`; the index is only the 61-book catalog — whole books are fetched at reading time from VRI's repository, never committed)
* `web/gallery-data/**` → `pipeline/make_gallery.py` (not committed)

`web/data/glyphs.js` is the one hand-maintained inventory file.

## Rebuilding the committed fonts

Shipped fonts live in `projects/` and go stale silently — this repo
shipped three-day-old variable fonts once, while the documentation
claimed zero failures. When any shaping rule changes:

```bash
python3 pipeline/make_variable.py projects/<name>/<Name>.glyphstudio.json dist/
# then copy Light/Regular/Bold/VF out of dist/<name>/variable/
```

`make_variable`'s Regular is name-table-identical to the committed
static, so all four weights come from that one path. The test suite
discovers every committed `.ttf` by glob, so a font cannot ship untested
— but only if you rebuilt it.

## Things that look like bugs and are not

* **Medial ra ြ keeps a small positive advance** and is GDEF *base*, not
  mark. HarfBuzz zeroes the advance of GDEF marks, which silently undoes
  the mechanism that moves the base inside the wrap.
* **`lookupflag` is sticky across named lookup blocks** within one
  feature block. A lookup that needs no filtering must say
  `lookupflag 0;` or it inherits the previous one's filtering set.
* **`UseMarkFilteringSet` hides every mark outside the set** — including
  marks a rule needs to *match on*. A mark in the context class but not
  the filtering set will never match.
* **The virama (U+1039) is synthesized empty** by the pipeline. Never
  draw one; project files must not contain one.
* **Myanmar digits are tabular.** The kerning tool refuses to touch
  them and fontbakery checks it.
* **The fonts register `mym2` only, never the legacy `mymr` tag.**
  HarfBuzz answers `mymr` with its Zawgyi shaper, which does no
  reordering — advertising the tag makes correctly encoded Unicode
  render wrong in any client that asks for it. Adding `mymr` back
  "for legacy engines" is the trap, not the fix.
* **ဋ ဌ ဍ ဎ ဏ ဠ have no underside.** Their tail crosses the whole
  glyph, so below-marks stand BESIDE their ink (Padauk's answer) and
  the seven stack pairs Padauk fuses are single traced glyphs
  (`FUSED_STACK_PAIRS`). A subjoined form centred under one of these
  letters is ink drawn through ink — အာယုဝဍ္ဎန was the report.

## House style

* Comments say *why*, and usually cite a measurement. `# Padauk lands
  every below-vowel at −439…−93` is the kind of comment this codebase
  wants; `# set the anchor` is not.
* Commit messages describe the change and the evidence for it, in plain
  sentences. Look at `git log` before writing one.
* No new dependencies without a reason that survives a sentence.
* Vanilla JS in `web/`, no build step. That is a feature: contributors
  edit a file and reload.
* Never invent contributor identities, fabricate history, or close an
  issue without the work behind it. This project's credibility is its
  main asset.

## Verifying a change actually works

```bash
pip install -e ".[dev]"
pytest                                   # everything
cd web && python3 -m http.server 8321    # the studio, no build step
mgs-proof build/MyFont-Regular.ttf "ကျွန်ုပ်တို့" proof.png
```

Shaping changes should be checked against Padauk with the same string in
both fonts, comparing the glyph names the shaper produced — not by
looking at the picture and deciding it seems fine.
