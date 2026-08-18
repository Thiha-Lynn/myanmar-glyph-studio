# Claude for Open Source — application material

Everything needed to submit to <https://claude.com/contact-sales/claude-for-oss>,
with every number re-measured on **2026-08-18** against the GitHub API and,
where it is an engineering claim, re-run rather than quoted.

**Repository:** <https://github.com/Thiha-Lynn/myanmar-glyph-studio>
**Live tool:** <https://thiha-lynn.github.io/myanmar-glyph-studio/>
**Gallery:** <https://thiha-lynn.github.io/myanmar-glyph-studio/gallery.html>
**Maintainer:** Thiha Lynn (GitHub `@Thiha-Lynn`) ·
koshanlay1994@gmail.com · 6631503092@lamduan.mfu.ac.th (the address on
the Claude-for-OSS application)
**Licenses:** MIT (toolkit) · SIL OFL 1.1 (every font produced)

---

The paste-ready answers live in
[APPLICATION-ANSWERS.md](APPLICATION-ANSWERS.md); this file is the
reasoning behind them.

## 1. The submit-tonight pack

The form authenticates with GitHub, then asks for your email, a short
statement of how you would use Claude, and a qualification explanation
capped at **500 words**. Paste-ready answers follow. Everything in them
is true as of today and checkable from public links.

### Field: repository / project

```
Myanmar Glyph Studio — https://github.com/Thiha-Lynn/myanmar-glyph-studio
Live: https://thiha-lynn.github.io/myanmar-glyph-studio/
```

### Field: qualification explanation (468 words — under the 500 cap)

> I maintain Myanmar Glyph Studio, a browser-based font-creation toolkit
> for the Myanmar script — the writing system of Burmese, Mon, Shan,
> S'gaw and Pwo Karen, Kayah, Palaung, Khamti and Aiton, read by roughly
> 40 million people.
>
> Let me be straight about the numeric lanes: I meet none of them. The
> repository is five days old, has five stars, and no external contributors
> yet. I am applying under "if you maintain something the ecosystem
> quietly depends on, apply anyway and tell us about it" — with the
> honest amendment that nothing depends on it *yet*. What I can offer
> instead is a checkable claim about the gap it fills and the standard it
> is built to.
>
> Myanmar is a complex script. A font is not a set of pictures but parts
> plus OpenType rules — contextual substitutions and mark positioning
> (blwf, rphf, pres, blws, GPOS mark/mkmk) — and nothing renders
> correctly until those are right. That expertise is why a community of
> 40 million readers has only a handful of free Unicode fonts, and why
> the Zawgyi/Unicode split took over a decade to recover from. Browser
> tools (Calligraphr, Glyphr Studio, FontStruct) cannot produce
> complex-script shaping at all; desktop tools (FontForge, Glyphs,
> FontLab) demand exactly the expertise that is missing. I could not find
> any browser-based tool, for any complex script, that generates its own
> shaping rules. This one does: you trace about 150 glyph parts over
> dimmed guides on a phone, tablet or desktop (a complete Burmese font;
> the optional minority-language and Latin groups take the inventory to
> 484), and the toolchain emits the shaping rules, mark anchors and UFO
> sources, compiling through the standard stack (fontmake, fontTools,
> fontbakery).
>
> The part worth checking is the engineering, because it is public and
> reproducible in ten minutes:
>
> - A written shaping specification (docs/SHAPING_SPEC.md) that a program
>   checks: 1,486 synthetic clusters, plus 711 real Burmese words chosen
>   to cover all 1,213 syllable clusters in a 12,450-word vocabulary.
> - All three shaping engines diffed automatically: HarfBuzz in CI, Apple
>   CoreText via a Swift shaper, Microsoft DirectWrite via a C++ shaper on
>   a Windows runner. 6,363 cluster comparisons per engine, zero
>   rendering differences.
> - The same harness run over the fonts the platforms ship reports
>   defects in each of them (Padauk 7, Noto Sans Myanmar 4, Microsoft
>   Myanmar Text 7); mine clear both corpora at zero.
> - Defects found in my own shipped fonts are written up in
>   docs/VALIDATION.md rather than quietly fixed.
>
> Everything produced is SIL OFL; the toolkit is MIT.
>
> What I would do with Claude: the remaining work is expert OpenType
> (Myanmar Extended-C, per-language shaping for Mon, Shan and Karen),
> reviewing community font submissions fast enough that first-time
> contributors do not drift away, and writing Burmese-language
> documentation for font-making, which barely exists. I am one person
> doing this beside a job, and the binding constraint is review-and-
> explain time. That is precisely what this would buy.

### Field: how you would use Claude (short version, 81 words)

> Three things. First, the expert OpenType work that gates coverage:
> Myanmar Extended-C, GDEF mark classes, and per-language shaping tests
> for Mon, Shan and S'gaw Karen. Second, reviewing community font
> submissions — reading proof sheets and fontbakery output to give a
> first-time contributor specific, kind feedback the same day, because a
> slow first review is the main reason new contributors disappear. Third,
> Burmese-language documentation and tutorials for font-making, which
> barely exist in Burmese. I am one maintainer; the constraint is
> review-and-explain time.

---

## 2. The lane table — measured, not estimated

| Lane | Bar | Measured 2026-08-18 | Fit |
|---|---|---|---|
| Maintainers / library authors | 500+ dependent repos, 100+ dependent packages, or 200k+ monthly downloads | **Published to PyPI 2026-08-17** — [`pip install myanmar-glyph-studio`](https://pypi.org/project/myanmar-glyph-studio/) (0.7.0, via GitHub OIDC trusted publishing, no API token). That makes the software installable rather than merely installable-in-principle; it does **not** approach the bar — zero dependents, and downloads are the publish itself. Nine tagged releases; v0.8.0 ships thirteen font families plus desktop installers for macOS/Windows/Linux **and an Android APK** | ✗ |
| Core contributors | Committer on CPython/Rust/Node/Apache/CNCF-class projects | No | ✗ |
| Active contributors | 100+ PRs merged into repos you don't own, 12 mo | **0** (`author:Thiha-Lynn is:merged -user:Thiha-Lynn` → 0; 40 merged PRs total, all in this repo) | ✗ |
| Community builders | 20+ unique external contributors merged, 12 mo | **0** | ✗ |
| Critical infrastructure | OpenSSF criticality ≥ 0.4 | Created 2026-08-13; 5 stars, 0 forks, 0 watchers, 0 dependents → ≈ 0 | ✗ |

**Nought for five, and not narrowly.** Reach in the last fortnight: 58
views from 4 unique visitors. (293 clones from 102 "uniques" is almost
entirely CI — do not quote it as human interest; a reviewer will know.)

That is a statement about *age and reach*, not about quality. The
engineering below is real and reproducible. But the lanes measure reach,
and reach is what is missing — so the application must be written from
the engineering and must say the stage out loud. An application that
stretches "quietly depended on" into a claim of existing dependents
invites the reviewer to check, find nothing, and discount everything
else. The record here is strong enough that it should never be spent
buying credibility for a reach claim it cannot support.

---

## 3. Three things only you can do before submitting

1. **Publish to PyPI — done, 2026-08-17; now at 0.7.0.**
   [`pip install myanmar-glyph-studio`](https://pypi.org/project/myanmar-glyph-studio/)
   installs 0.7.0, uploaded by [`publish.yml`](../.github/workflows/publish.yml)
   over GitHub OIDC trusted publishing: no API token exists in the
   repository, its secrets, or on any machine. Verified by installing
   from the real index into a clean virtualenv and running a console
   script, not by trusting the workflow's green tick.

   It does not approach the downloads lane and the table above says so.
   What it changes is that "installable software" is a link rather than
   an assertion, and that anyone can now audit any Myanmar font with one
   command from a fresh machine — which is the argument this project
   makes, in a form a stranger can run.

   *The first attempt failed and the reason is worth keeping: the upload
   authenticated perfectly and was rejected `400` because
   `Natural Language :: Burmese` is not a valid PyPI classifier — its
   list has no Burmese or Myanmar entry at all. `twine check --strict`
   does not validate classifiers, so nothing local caught it. A test now
   checks every classifier against the list PyPI itself uses.*

2. **The commit history now explains itself — one optional step left.**
   Resolved 2026-08-17: [`.mailmap`](../.mailmap) maps all three git
   identities (the machine's old university-account identity, a personal
   email, and an early name typo) to `Thiha-Lynn`; the README's
   community section says the same in one line; and the package
   metadata's maintainer field names the same identity — it was about to
   go to PyPI carrying the old one. GitHub's Insights graph ignores
   `.mailmap`, so it will keep drawing three avatars; the README line is
   what explains that where a reviewer looks. The one thing only you can
   still do: add the personal email to your GitHub account's verified
   addresses (Settings → Emails), and its 7 commits re-attribute to
   `@Thiha-Lynn` in Insights immediately. The university address belongs
   to its own account and stays as explained history — do not claim it.

3. **Say the stage plainly, in your own words.** Five days old, one
   maintainer, built to fill a gap you hit yourself. The programme
   explicitly invites this case. The age is only fatal if you hide it.

**Do not** pad the history to look busier — no synthetic commits, no
commits authored under other people's accounts, no issues closed without
the work behind them. Manufactured activity is easy to spot and fatal to
the honest case above.

---

## 4. Engineering evidence (all public, all linkable)

* **A written shaping specification, machine-checked.**
  [`docs/SHAPING_SPEC.md`](SHAPING_SPEC.md) states the model — anchor
  formulas with coordinates, glyph classes, GSUB order, a 50-unit
  collision protocol — and `pipeline/validate_spec.py` *measures* a font
  against it: **1,486 synthetic clusters** (every consonant × vowel ×
  medial, stacks, kinzi, tall-aa, torture text, Mon/Shan/Karen) and
  **711 real Burmese words covering all 1,213 syllable clusters** in a
  12,450-word Wiktionary vocabulary. Findings are graded so a malformed
  test string can never mask a real defect. Results:
  [`docs/VALIDATION.md`](VALIDATION.md).
* **Verified on every shaping engine that matters, automatically.**
  Myanmar is composed by the text engine, not the font, so the same file
  can render differently per platform. All three are diffed in software:
  HarfBuzz in CI (Android, Chrome, Linux); **CoreText** via a Swift
  shaper that runs as a test on any Mac (`pipeline/coretext/`); and
  **DirectWrite** via a C++ shaper calling `IDWriteTextAnalyzer` on a
  `windows-latest` runner, so Windows is covered on every pull request
  (`pipeline/directwrite/`). Current result, re-measured 2026-08-17:
  **6,363 cluster comparisons against Apple's engine and 6,363 against
  Microsoft's, zero rendering differences either way** (1,410 spec
  clusters + 711 words, × 3 weights). What is left for a person is
  judgement, not geometry — and the repo ships a
  [device-test page](https://thiha-lynn.github.io/myanmar-glyph-studio/devicetest.html)
  that walks anyone through it and writes the report.
* **Automated quality gates on every push and PR:** **117 tests**
  (`pipeline/tests/`, 116 passing + 1 platform-skipped), both shaping
  corpora against *every* shipped font file — discovered by glob, so a
  font cannot ship untested — a HarfBuzz regression that fails the build
  if the reference font drops any glyph, and fontbakery's universal
  profile gated on FAIL. See the
  [Actions tab](https://github.com/Thiha-Lynn/myanmar-glyph-studio/actions).
* **Validated against the whole of a real vocabulary.** Beyond the
  711-word CI corpus, `pipeline/fetch_vocab.py` runs all **12,450** words
  of the [DatarrX Myanmar Word Glyphs](https://huggingface.co/datasets/DatarrX/myanmar-word-glyphs)
  vocabulary through the same checker: 0 FAIL in every shipped
  font, with the remaining WARN-level findings confined to the
  benchmark classes the reference fonts themselves trip. The wide sweep exists to test the *cover*, and has never found
  anything the 711 words miss — a result about corpus design, published
  rather than assumed.
* **A second corpus built from literature.** `pipeline/make_reference.py`
  segments a whole Wikisource category into syllable clusters and greedily
  selects the fewest passages covering every one: on the 538-story Jātaka
  cycle (3.66M characters) that is **1,605 distinct clusters**, a third
  more than the vocabulary holds. It found two real defects on its first
  run.
* **Showcases that show their work.**
  [showcase.html](https://thiha-lynn.github.io/myanmar-glyph-studio/showcase.html)
  renders 60 hard clusters beside the reference font with the glyphs the
  shaper produced and the ink distance between them, then the complete
  glyph inventory, then all 12,450 vocabulary words as a browsable atlas.
  It is also a working QA instrument: it found a contextual-form bug
  (ကွှု) that both corpora score as passing, because a vowel in the wrong
  shape is still perfectly positioned.
* **Real font engineering, not a wrapper:** stroke→outline expansion
  mirrored in JS and Python, generated `mym2` feature code, automatic
  mark anchors with in-browser anchor editing, virama synthesis,
  production glyph names, kerning measured from the drawn outlines
  (with tabular figures correctly excluded), smart-dropout hinting,
  WOFF2 output.
* **One drawing, many faces.** Sketches are centre-lines plus a pen, so
  the pipeline derives a whole `wght` axis from a single drawing, and a
  superellipse nib plus a skeleton warp produce genuinely different
  faces from the same source — demonstrated live at
  [styles.html](https://thiha-lynn.github.io/myanmar-glyph-studio/styles.html)
  and shipped as **Bagan Display**, a squircle display face.
* **Benchmarked, not self-graded.** The same harness over the fonts the
  major platforms ship reports findings in each — Padauk 7, Noto Sans
  Myanmar 4, Microsoft's Myanmar Text 7 — while the fonts here clear both
  corpora at **0 FAIL in every weight**, with single-digit WARN counts of
  the same neighbour/clearance classes Padauk itself trips.
* **Runs as an application too:** macOS DMG, Windows installer, Linux
  AppImage/deb, built by CI for every release — the same `web/` directory
  served over a private scheme, offline and sandboxed
  ([docs/DESKTOP.md](DESKTOP.md)). Unsigned, and the documentation says
  so before the download link.
* **Community-ready:** Code of Conduct, security policy with private
  reporting, Dependabot, four issue templates, PR template, contributor
  guide, a full Burmese README (`README.my.md`), SUPPORT.md, CHANGELOG.md,
  CITATION.cff, a repository map ([ARCHITECTURE.md](ARCHITECTURE.md)),
  per-family OFL compliance, topical labels, and tagged releases whose
  assets are built by CI — v0.7.0 carries per-family font zips, desktop
  installers for all three platforms, and the Android APK. GitHub community profile
  at 100%, four standing invitations written out in
  [CONTRIBUTING.md](../CONTRIBUTING.md#where-to-start--four-standing-invitations)
  and surfaced on the site itself at
  [contribute.html](https://thiha-lynn.github.io/myanmar-glyph-studio/contribute.html)
  — where the people using the studio actually are, rather than only in a
  markdown file a visitor has to go looking for — and a
  [CLAUDE.md](../CLAUDE.md) briefing so contributions made with a coding
  assistant do not trip the project's invariants.
* **Installable software:**
  [`pip install myanmar-glyph-studio`](https://pypi.org/project/myanmar-glyph-studio/)
  — or `pip install -e ".[dev]"` from a checkout — gives sixteen
  command-line tools (build, variable build, proof, validate,
  CoreText diff, kerning, showcase, gallery, book, PDF, i18n check, …)
  with PEP 621 metadata and an SPDX licence expression; both corpora ship
  inside the wheel, so any Myanmar font anywhere can be audited with one
  command. *(On PyPI since 2026-08-17 — §3.1.)*
* **A real editor, not a toy:** the studio ships professional vector
  tools (Bézier pen with permanently editable paths, selection with
  transform handles, node editing, cross-glyph copy/paste, snapping,
  partial eraser) in vanilla JS with no build step, fully translated into
  Burmese, working offline as a PWA on phones and tablets.

---

## 5. What a reviewer can verify in ten minutes

| Claim | How they check it |
|---|---|
| It actually works in a browser | Open the studio, trace a letter, press Export font |
| The fonts are real and shaped | Download from the gallery, type ကျွန်ုပ်တို့ |
| Three engines agree | `docs/VALIDATION.md`, then the Actions tab (DirectWrite job) |
| The tests exist and pass | `pip install -e ".[dev]" && pytest` → 116 passed, 1 skipped |
| The benchmark is honest | `mgs-validate` any Myanmar font on their own machine |
| The defects are disclosed | `docs/VALIDATION.md` — including bugs in our own fonts |
| Nothing is padded | Insights → Contributors, Commits, Actions history |

Rough check before hitting submit: could a reviewer verify every claim
from public links in ten minutes, and would every one come back true? If
a claim needs them to take your word for it, cut it — what is left is
stronger than what you removed.

---

## 6. If the answer is no

It is a rolling programme with a hard cap, and a decline is not a verdict
on the work. The record gets stronger every week without any change of
strategy, and the routes that would flip a lane are already written down:

* **Community-builder lane (0 → 20 external contributors):** the glyph
  drive in [LAUNCH.md](LAUNCH.md) §5 and the four standing invitations
  in [CONTRIBUTING.md](../CONTRIBUTING.md#where-to-start--four-standing-invitations)
  — no ticket to claim, partial work welcome. Even three merged glyph
  PRs from strangers change the story from "personal project" to
  "community infrastructure".
* **Downloads lane:** PyPI is done (§3.1); next, the fonts themselves to
  Google Fonts / a package repository.
* **Third-party validation:** an accepted PR to awesome-myanmar-unicode,
  a ScriptSource entry, a mention from SIL or the Noto community, or a
  write-up by anyone who is not the maintainer.
* **Evidence of dependency:** a font made with this tool shipping in
  something real; a Myanmar organisation or localisation team using it in
  a documented workflow. One of those, linkable, turns the sentence in
  §1 from aspiration into fact — and that is the version of this
  application that wins on the merits rather than on candour.
