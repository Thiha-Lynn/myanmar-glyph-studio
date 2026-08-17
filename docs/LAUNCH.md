# Launch playbook — from local repo to community project

The checklist for taking this repository public and growing it into a
project the ecosystem visibly depends on. Work top to bottom; everything
in the repo itself is already prepared.

## 1. Publish the repository

1. Create the GitHub repository — suggested name **`myanmar-glyph-studio`**
   (short, searchable, says what it is). Description:
   *"Draw your own Myanmar font in the browser — guided tracing + automatic
   OpenType shaping (mym2). ဘရောက်ဇာထဲမှာ မြန်မာဖောင့် ရေးဆွဲပါ။"*
   Public, no template, **no** auto-added README/.gitignore/license (the
   repo already has them).
2. Push:

   ```bash
   git remote add origin git@github.com:OWNER/myanmar-glyph-studio.git
   git push -u origin main
   ```

3. Watch the **Actions** tab: the *Build fonts* workflow must go green
   (tests → build → proof → fontbakery). It is the repo's first public
   proof of engineering quality.

## 2. One-time repository settings

* **Pages** → Settings → Pages → Source: **GitHub Actions**. The studio
  deploys to `https://OWNER.github.io/myanmar-glyph-studio/` and the
  gallery to `…/gallery.html`. Put the studio URL in the repo's About box.
* **Discussions**: enable (Settings → Features). The issue-template
  contact links already point there.
* **Topics**: `myanmar`, `burmese`, `font`, `font-editor`, `opentype`,
  `harfbuzz`, `unicode`, `ufo`, `fontmake`, `pwa`, `drawing`.
* **Private vulnerability reporting**: enable (Settings → Code security) —
  SECURITY.md references it.
* **Branch protection** on `main`: require the *Build fonts* check to pass
  before merging PRs.
* Update the placeholder links: replace `OWNER/REPO` in
  `.github/ISSUE_TEMPLATE/config.yml`, and add badges to the top of
  README.md once the slug exists:

  ```markdown
  [![Build fonts](https://github.com/OWNER/myanmar-glyph-studio/actions/workflows/build.yml/badge.svg)](https://github.com/OWNER/myanmar-glyph-studio/actions/workflows/build.yml)
  [![Studio](https://img.shields.io/badge/studio-draw%20in%20browser-a8352f)](https://OWNER.github.io/myanmar-glyph-studio/)
  [![License: MIT + OFL](https://img.shields.io/badge/license-MIT%20%2B%20OFL--1.1-blue)](LICENSE)
  ```

## 3. First release

```bash
git tag v0.1.0
git push --tags
```

The *Release fonts* workflow attaches per-family zips (TTF + WOFF2 + proof
sheet + OFL) to a GitHub Release — the download link for people who will
never open a repository.

## 4. Make the ecosystem notice (visibility)

* PR the studio into
  [awesome-myanmar-unicode](https://github.com/khzaw/awesome-myanmar-unicode)
  — currently that list has **no font-creation tool at all**, so this adds
  a new category.
* Submit the tool page to [ScriptSource](https://scriptsource.org)
  (Myanmar script entry) and tell the
  [SIL Padauk](https://software.sil.org/padauk/) maintainers — the sample
  font credits them, and they know every Myanmar-font person alive.
* Post where Myanmar developers actually are: Myanmar developer Facebook
  groups, Telegram dev channels, r/myanmar — with a 30-second screen
  recording of drawing က and exporting a font on a phone.
* Reach out to design/CS departments and calligraphy communities: one
  workshop = many first glyphs.
* Publish the pipeline to PyPI. The workflow is wired
  (`.github/workflows/publish.yml`, trusted publishing — no token
  anywhere); what remains is the one-time pending-publisher form on
  pypi.org described in its header. A `pip install myanmar-glyph-studio`
  that works is a distribution channel, a dependents counter, and the
  first numeric signal any support program can check — and it lets
  anyone audit *any* Myanmar font with one command, which is its own
  kind of advertising.
* Take the validation findings upstream. The harness measures findings
  in the fonts the platforms ship
  ([VALIDATION.md](VALIDATION.md): Padauk 7, Noto Sans Myanmar 4,
  Microsoft Myanmar Text 7 — each carrying the calibration caveat).
  Re-verify one by hand first — the harness is calibrated to this
  project's conventions, and an upstream report must survive their
  scrutiny, not ours — then file it on
  [notofonts/myanmar](https://github.com/notofonts/myanmar) or the
  [Padauk tracker](https://github.com/silnrsi/font-padauk) with the
  cluster, the measurement and a rendering. One accepted upstream
  report is worth more than any self-reported number: it is the
  contributes-to-repos-they-don't-own signal every OSS program reads,
  and it puts the toolkit's name in front of the people who maintain
  Myanmar text rendering for everyone.

## 5. Grow real contributors (the metric that matters)

The Community-builder bar many OSS programs use is **20+ unique external
contributors with merged PRs in 12 months**. This project is unusually
well-shaped for it, because a *single drawn glyph is a legitimate PR*:

* Run a **glyph drive**: open one `glyph-contribution` issue per glyph
  group of a new community family, label them `good first issue`, and
  point beginners at the studio → draw → Save → PR flow (CONTRIBUTING.md
  documents it).
* Keep the gallery fresh — visible fonts with the contributor's name in
  the credits are the reward loop.
* Triage fast: first-PR contributors who wait a week don't come back.

## 6. Ongoing hygiene (already wired, keep it green)

* CI: unit tests, HarfBuzz shaping regression on the sample, fontbakery
  FAIL gate, WOFF2 builds. Dependabot updates actions + pip weekly.
* After going public, optionally add the
  [OpenSSF Scorecard action](https://github.com/ossf/scorecard-action) and
  badge — most of its checks (license, CI tests, dependency update tool,
  security policy, code review) are already satisfied.

## 7. Applying to support programs (e.g. Claude for Open Source)

Be honest about the stage: a fresh repo fits the *"maintain something the
ecosystem quietly depends on — apply anyway and tell us"* lane, not the
download-count lanes. The strongest possible application, in order:

1. **Launch first** (steps 1–4), so the repo shows real history: the
   engineering commits, green CI, the hosted studio, the gallery.
2. **Get the first external contributions** (step 5) — even 3–5 merged
   glyph PRs from strangers changes the story from "personal project" to
   "community infrastructure".
3. Then apply, leading with the niche-infrastructure argument: the only
   browser font-creation tool for the Myanmar script (≈40M readers), an
   underserved ecosystem still recovering from the Zawgyi/Unicode split;
   fonts ship under OFL to the whole community; the toolchain (UFO +
   fontmake + fontbakery + HarfBuzz proofs) is the same one Google Fonts
   onboarding expects.

Every claim in that pitch must be a link into the public repo: the CI
runs, the gallery, the merged community PRs, the releases.
