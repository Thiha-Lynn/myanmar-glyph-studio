# Claude for Open Source — the answers, ready to paste

The form asks three things. These are written to be true on the day they
are pasted: every number was re-measured against the GitHub API, PyPI and
the test suite on 2026-08-18, and every claim is checkable from a public
link in under ten minutes.

The companion document, [OSS_APPLICATION.md](OSS_APPLICATION.md), is the
longer reasoning — the lane table, what is missing, and what would change
it. This file is just the paste.

**Do not inflate any of it.** The engineering record is strong enough that
it should never be spent buying credibility for a reach claim it cannot
support.

## Field 1 — "Tell us about the project's reach and impact"

Myanmar Glyph Studio is a browser-based font-creation toolkit for the
Myanmar script — the writing system of Burmese, Mon, Shan, S'gaw and Pwo
Karen, Kayah, Palaung, Khamti and Aiton, read by roughly 40 million people.

Let me be straight about reach: the repository is five days old, has 4
stars, and no external contributors. I am applying on the gap it fills,
which is checkable in a click.

Myanmar is a complex script. A font is not pictures but parts plus
OpenType rules — contextual substitution and mark positioning (blwf, rphf,
pres, blws, GPOS mark/mkmk) — and nothing renders correctly until those
are right. That expertise is why 40 million readers have only a handful of
free Unicode fonts. Browser tools (Calligraphr, Glyphr Studio, FontStruct)
cannot produce complex-script shaping at all; desktop tools (FontForge,
Glyphs, FontLab) demand exactly the expertise that is missing. I could not
find any browser-based tool, for any complex script, that generates its
own shaping rules. This one does: trace ~150 parts over dimmed guides on a
phone, and the toolchain emits the shaping rules, mark anchors and UFO
sources, compiling through fontmake.

What I can offer instead of downloads is engineering you can verify in ten
minutes:

- A written shaping specification that a program checks: 1,486 synthetic
  clusters plus 711 real Burmese words covering all 1,213 syllable
  clusters in a 12,450-word vocabulary.
- All three shaping engines diffed automatically — HarfBuzz in CI, Apple
  CoreText via a Swift shaper, Microsoft DirectWrite via a C++ shaper on a
  Windows runner. 6,363 cluster comparisons per engine, zero differences.
- The same harness run over the fonts the platforms ship reports defects
  in each (Padauk 7, Noto Sans Myanmar 4, Microsoft Myanmar Text 7); mine
  clear both corpora at zero. Defects found in my own fonts are published
  in docs/VALIDATION.md rather than quietly fixed.
- 106 tests, fontbakery FAIL-gated CI, 8 font families under OFL, and the
  studio shipping as a web app, desktop apps for macOS/Windows/Linux, and
  Android and iOS apps — all running the same code.
- pip install myanmar-glyph-studio, so anyone can audit any Myanmar font
  with one command.

Everything produced is SIL OFL; the toolkit is MIT.

## Field 2 — "How will you use the subscription for your project?"

Three things, all of them the parts a single maintainer cannot buy time
for.

First, the expert OpenType work that gates coverage. The ဋ္ဌ stack still
renders as a tangle in real Pali-Burmese words and cannot be fixed with
anchors — it needs fused artwork plus a ligature rule, the way Padauk
solves it. Beyond that: Myanmar Extended-C, GDEF mark classes, and
per-language shaping for Mon, Shan and S'gaw Karen, each of which needs
its own test corpus before it can be trusted.

Second, reviewing community font submissions fast enough that first-time
contributors do not drift away. A drawn glyph is a legitimate pull
request here, and the difference between a contributor who returns and one
who does not is whether their first submission got specific, kind feedback
the same day — reading proof sheets and fontbakery output and saying which
glyph is two units off, not "looks good".

Third, Burmese-language documentation and tutorials for font-making, which
barely exist in Burmese at all. The interface is already bilingual; the
teaching material is not.

I am one person doing this beside a degree, and the binding constraint is
review-and-explain time rather than ideas or code. That is precisely what
this would buy.

## Field 3 — "Other info" (optional)

The repository is five days old and I would rather you knew the weak
numbers from me than found them yourself: 4 stars, 0 forks, no external
contributors, and 102 unique cloners of which most are CI. I meet none of
the five numeric lanes on the programme page and the repository documents
that verbatim in docs/OSS_APPLICATION.md, including the routes that would
change it.

The contributor graph shows three identities; they are all me. Commits
before 2026-08-16 predate the repository-local git identity, and .mailmap
maps them.
