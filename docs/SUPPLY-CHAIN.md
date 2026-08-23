# Supply chain

What this repository ships, what builds it, and how much of that is
pinned, watched or attested — plus, honestly, what still is not.

The prompt for writing it down was an
[OpenSSF Scorecard](https://securityscorecards.dev) run that graded the
project **4.6** on 2026-08-18 with three checks at zero. Two of those
were real, mechanical gaps and are fixed; one cannot be fixed by a
project with one maintainer, and saying so is more useful than a number.

## What runs in CI is pinned to a commit

Every `uses:` in `.github/workflows/` names a 40-character commit SHA
with the version in a trailing comment:

```yaml
- uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7
```

A tag is a moving pointer: whoever can push to an action's repository can
repoint `v7` at new code, and it would run here on the next push, with a
token. A commit cannot be repointed. The comment is what keeps the pins
reviewable — and what Dependabot rewrites when it bumps one.

`pipeline/tests/test_workflow_hardening.py` fails if a workflow arrives
with a moving ref or an un-commented pin.

## Every workflow declares its token

Each workflow declares `permissions:` at the top, and the default is
`contents: read`. Where a job genuinely writes — attaching installers or
font zips to a release, uploading SARIF, publishing to PyPI — the write
is declared **on that job**, not on the workflow, so the other jobs in
the same file get a read-only token.

`build.yml` had no `permissions:` block at all until 2026-08-23, which is
what Scorecard's *Token-Permissions 0* was pointing at: it ran with
whatever the repository default grants.

## Python installs are hash-verified

`pipeline/requirements.txt` and its two smaller siblings are compiled
with `pip-compile --generate-hashes` from `.in` sources, and every CI job
installs them with `--require-hashes`. `pip install fonttools` takes
whatever PyPI serves that minute; a hashed pin cannot be substituted, so
a tampered or yanked-and-replaced release cannot enter a build.

| File | Used by | Holds |
|---|---|---|
| `requirements.txt` | the font builds, the test suite, contributors | the whole toolchain (51 pins) |
| `requirements-tools.txt` | the DirectWrite shaping check, the gallery kits | fontTools, uharfbuzz, brotli |
| `requirements-publish.txt` | the PyPI job | build, twine |

Edit the `.in`, then recompile:

```bash
pip install uv
cd pipeline && uv pip compile --universal --generate-hashes \
  --python-version 3.12 --output-file requirements.txt requirements.in
```

**`--universal` is the part that matters.** A lock resolved on one
platform silently omits the dependencies only another platform needs:
`keyring` requires `SecretStorage` on Linux and nowhere else, so the
first version of these files — compiled on macOS — installed perfectly
there and failed the Linux runner with *"In --require-hashes mode, all
requirements must have their versions pinned"*. The universal resolution
carries every platform's branch, each with its marker.

The package's own dependencies in `pyproject.toml` stay as `>=` ranges —
pinning the toolchain a project builds *with* is not the same as pinning
what people who `pip install myanmar-glyph-studio` are forced to resolve.

## Dependencies are watched — all of them now

Dependabot covers four trees: GitHub Actions, the Python toolchain in
`pipeline/`, and the two npm trees in `desktop/` and `mobile/`.

Those last two are new, and their absence is the whole story behind
Scorecard's *Vulnerabilities 0*: **49 advisories**, every one of them in
`desktop/` or `mobile/`, because nothing was watching them while every
other ecosystem stayed current. Electron had drifted **nine major
versions** behind (34 → 43), which is most of the count on its own; the
rest came through `electron-builder`'s dependency chain (`app-builder-lib`
below 26.15.0, and a critical `node-tar` path-traversal via `node-gyp`),
plus a `uuid` bounds-check advisory reaching `mobile/` through
`@capacitor/cli` → `xcode`, where upstream has no fix and an npm
`overrides` entry forces the patched version.

`npm audit` reports **0 vulnerabilities** in both trees as of 2026-08-23.
The test suite asserts that every `package-lock.json` in the repository
has a matching Dependabot entry, so a new one cannot arrive unwatched.

## Everything, audited (2026-08-23)

Four dependency manifests are tracked in this repository, and one file is
vendored. All five were checked at the v0.13.0 commit:

| What | Tool | Result |
|---|---|---|
| `desktop/package-lock.json` | `npm audit` | 0 vulnerabilities |
| `mobile/package-lock.json` | `npm audit` | 0 vulnerabilities |
| `pipeline/requirements.txt` | `pip-audit` | no known vulnerabilities |
| the whole installed Python environment (every transitive dependency) | `pip-audit --path` | no known vulnerabilities |
| `web/vendor/opentype.min.js` | OSV query | no advisories exist for opentype.js at any version |

`pyproject.toml`'s dependencies are a subset of
`pipeline/requirements.txt`, so they are covered by the same run. There
are no committed Gradle or CocoaPods files: Capacitor generates the
Android and iOS projects at build time from the Capacitor version, which
Dependabot watches.

To repeat any of it:

```bash
(cd desktop && npm audit) && (cd mobile && npm audit)
pip-audit -r pipeline/requirements.txt
```

## The one file no scanner can see

`web/vendor/opentype.min.js` is checked in rather than installed, so it
appears in no lockfile: `npm audit` cannot see it and Dependabot cannot
open a PR for it. It is the only third-party code here that could sit at
an old version indefinitely with nobody noticing.

Nothing needs fixing — opentype.js has no advisories at any version — but
the *ability to check* did. `web/vendor/README.md` now records the
package, the version (**1.3.4**, established by matching the bytes
against the official npm tarball, since the minified file carries no
version string), its SHA-256 and its licence;
`pipeline/tests/test_vendored_js.py` fails if the file changes without
that record changing, if a second vendored file appears undocumented, or
if anything other than `fontexport.js` starts calling into it.

## Releases say what built them

Every binary attached to a release — the font zips, the five desktop
installers, the Android APK — is attested with
[`actions/attest-build-provenance`](https://github.com/actions/attest-build-provenance),
and the SLSA provenance bundle ships beside it as `*.intoto.jsonl`. That
records which workflow, at which commit, on which runner produced the
file, verifiable with:

```bash
gh attestation verify <file> --repo Thiha-Lynn/myanmar-glyph-studio
```

The PyPI package is published through
[trusted publishing](https://docs.pypi.org/trusted-publishers/) — no API
token exists to leak — and carries PEP 740 attestations.

## What is still zero, and why

**Code-Review (0/13 approved changesets).** Every change here is opened
as a pull request, runs the full suite, and is merged by the person who
wrote it, because there is one maintainer. Scorecard counts *approved*
changesets, so the honest score is zero and will stay zero until somebody
else reviews. Enabling required reviews on a solo project would mean
either blocking every change or approving your own, and the second is
worse than the zero. **If you would like to review, say so in
[Discussions](https://github.com/Thiha-Lynn/myanmar-glyph-studio/discussions)**
— that is a contribution this project genuinely lacks.

**CII-Best-Practices (0).** Needs the project registered at
[bestpractices.dev](https://www.bestpractices.dev), which is a human
signing up. Not done yet.

**Fuzzing (0).** No fuzz target. The parsers that consume untrusted input
— project JSON and imported SVG in the browser, project JSON in the
pipeline — are the places where one would earn its keep; see
[SECURITY.md](../SECURITY.md) for what counts as a vulnerability there.

**Contributors (0) and Maintained (0).** Both are facts about the
project's age and its (currently single) contributor list, not settings.
They change by people arriving.

**Branch-Protection (−1).** Scorecard cannot read the branch protection
settings with the token it is given; the rules do exist — `main` requires
the `build` check to pass.
