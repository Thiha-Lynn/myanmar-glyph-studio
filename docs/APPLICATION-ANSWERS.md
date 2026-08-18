# Claude for Open Source — the answers, ready to paste

Three fields on the form, three answers below. Every number was
re-measured against the GitHub API, PyPI and the test suite on
**2026-08-18**, and every claim is checkable from a public link in under
ten minutes.

The longer reasoning — the lane table, what is missing, what would change
it — is in [OSS_APPLICATION.md](OSS_APPLICATION.md). This file is the
paste.

**Do not inflate any of it.** The engineering record is strong enough
that it should never be spent buying credibility for a reach claim it
cannot support. A reviewer who checks three claims and finds them exact
will believe the fourth.

The through-line is the community, not the tool: Burmese has a handful of
free Unicode fonts, and the minority languages that share the script have
almost none. That sentence is true, verifiable, and the most compelling
thing this project can say — and it was buried in earlier drafts under an
apology about star counts.

---

## Field 1 — "Tell us about the project's reach and impact"

The form offers four things to answer with: downloads, GitHub activity,
who depends on it, **or the gap it fills**. This answers on the gap,
names the weak numbers before a reviewer can find them, and spends its
length on evidence instead.

> The Myanmar script is read by about 40 million people, and it is
> written by more than a dozen languages that have almost no digital type
> at all: Shan, Mon, S'gaw and Pwo Karen, Kayah, Pa'O, Palaung, Khamti,
> Aiton, Tai Laing, and Pali. Burmese has a handful of free Unicode
> fonts. The minority languages that share the script have, in practice,
> almost none — and every one of them is in this toolkit's inventory of
> 480 glyphs, because that is the point of it.
>
> The reason is structural, not cultural. Myanmar is a complex script: a
> font is not a set of pictures but parts plus OpenType rules —
> contextual substitution and mark positioning (blwf, rphf, pres, blws,
> GPOS mark/mkmk) — and nothing renders correctly until those rules are
> right. That expertise is rare and concentrated far from the people who
> need the fonts. It is why the Zawgyi/Unicode split took a decade to
> recover from, and why a Shan or Karen speaker who can draw beautifully
> still cannot ship a font.
>
> Myanmar Glyph Studio removes that barrier. You trace about 150 glyph
> parts over dimmed guides — on a phone, which is the device the
> community actually has — and the toolchain generates the shaping rules,
> mark anchors and UFO sources, then compiles a real font through the
> standard fontmake stack. No font engineering required, and no desktop
> computer required.
>
> I would rather you heard the numbers from me: the repository is five
> days old, has 4 stars, and no external contributors yet. What I can
> offer instead is engineering that is public and checkable in ten
> minutes.
>
> - A written shaping specification that a program verifies: 1,486
>   synthetic clusters plus 711 real Burmese words, chosen to cover all
>   1,213 syllable clusters in a 12,450-word vocabulary.
> - All three shaping engines diffed automatically — HarfBuzz in CI,
>   Apple CoreText via a Swift shaper, Microsoft DirectWrite via a C++
>   shaper on a Windows runner: 6,363 cluster comparisons per engine,
>   zero rendering differences.
> - The same harness run over the fonts the platforms ship reports
>   defects in each of them — Padauk 7, Noto Sans Myanmar 4, Microsoft
>   Myanmar Text 7 — while the fonts here clear both corpora at zero.
>   Defects found in my own fonts are published in docs/VALIDATION.md
>   rather than quietly fixed.
> - 106 tests, fontbakery-gated CI, 8 font families under the SIL Open
>   Font License, 16 command-line tools, and 14 documents. The studio
>   runs as a web app, as desktop apps for macOS/Windows/Linux, and as
>   Android and iOS apps — all from one codebase, so a feature cannot
>   exist on one platform and not another.
> - pip install myanmar-glyph-studio lets anyone audit any Myanmar font
>   with one command.
>
> Everything produced is SIL OFL; the toolkit is MIT.

The benchmark bullet is the strongest sentence available. "My font passes
my tests" proves nothing; "my tests find real defects in the fonts Apple,
Google and Microsoft ship, and my own fonts clear them at zero" proves
the tests are real.

---

## Field 2 — "How will you use the subscription for your project?"

Concrete expert work, each item tied back to the people it serves, ending
on the actual bottleneck.

> Three things, all of them the parts a single maintainer cannot buy time
> for.
>
> First, the expert OpenType work that gates coverage for the languages
> with the least support. The ဋ္ဌ stack still renders as a tangle in real
> Pali-Burmese words such as ကမ္မဋ္ဌာန်း, and it cannot be fixed with
> anchors — those letters descend across their whole width, so the
> subjoined form would have to sit below the design limit; it needs fused
> artwork plus a ligature rule, the way Padauk solves it. Beyond that:
> per-language shaping for Mon, Shan and S'gaw Karen, each needing its
> own test corpus before it can be trusted, plus Myanmar Extended-C and
> GDEF mark classes. Shaping correctness is exactly where a
> minority-language font quietly fails, and exactly where there is nobody
> to ask.
>
> Second, reviewing community font submissions fast enough that
> first-time contributors do not drift away. A single drawn glyph is a
> legitimate pull request here — the barrier is deliberately low — and
> the difference between a contributor who returns and one who does not
> is whether their first submission got specific, kind feedback the same
> day: reading proof sheets and fontbakery output and saying which glyph
> is two units off and why, not "looks good".
>
> Third, Burmese-language documentation and tutorials for font-making,
> which barely exist in Burmese at all, and do not exist in Shan or Mon.
> The interface is already bilingual; the teaching material is not, and
> that is the real barrier for the people this is for.
>
> I am one person doing this beside a degree. The binding constraint is
> review-and-explain time, not ideas or code — which is precisely what
> this would buy.

---

## Field 3 — "Other info" (optional)

**This field is a single-line input**, so it renders as one paragraph;
that is the form, not a formatting mistake. It volunteers every weakness
a reviewer would find anyway — and then closes on coverage, which is
real, rather than on reach, which is not.

It names the `claude` identity in the contributor graph deliberately. The
graph shows it as the second-largest contributor, because 37 early
commits carry `Co-Authored-By` trailers; a reviewer at Anthropic will see
that immediately. Disclosed in one clause it reads as ordinary — the repo
has shipped a CLAUDE.md briefing since early on — while an application
that described the graph without mentioning it would be inaccurate about
the one thing that reader is best placed to check.

> I would rather you heard the weak numbers from me than found them
> yourself: five days old, 4 stars, 0 forks, no external contributors,
> 102 unique cloners of which most are CI. I meet none of the five
> numeric lanes and the repository concedes that lane by lane in
> docs/OSS_APPLICATION.md, along with the routes that would change it.
> Three things a reviewer may notice. The contributor graph shows four
> identities: three are mine (commits before 2026-08-16 predate the
> repository-local git identity; .mailmap maps them), and the fourth is
> "claude" — the project is openly AI-assisted, 37 early commits carry
> co-author trailers, and CLAUDE.md documents the working agreement.
> Five of the eight font families were generated parametrically from one
> set of skeletons rather than drawn by hand; docs/FIVE-FACES.md states
> that in its second paragraph, with no contributor credited for them.
> And what is genuinely unusual here is not the reach but the coverage:
> the inventory spans the full Myanmar block plus Extended-A and
> Extended-B, so a Shan, Mon, Karen, Kayah, Palaung, Khamti, Aiton or Tai
> Laing speaker can draw their own font in a browser today. Links:
> github.com/Thiha-Lynn/myanmar-glyph-studio ·
> thiha-lynn.github.io/myanmar-glyph-studio ·
> pypi.org/project/myanmar-glyph-studio

---

## Before pressing Submit

1. **Select the repository.** The form needs
   `Thiha-Lynn/myanmar-glyph-studio` chosen through "Select repo on
   GitHub" — it is required, and it authenticates, so only the maintainer
   can do it.
2. **Read the Burmese with your own eyes**: ဋ္ဌ and ကမ္မဋ္ဌာန်း. In an
   application about Myanmar typography a wrong letter is the worst
   possible typo.
3. **Agree with Field 3 before sending it.** It is candid on purpose, and
   it carries your name.
