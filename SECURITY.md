# Security Policy

## Reporting a vulnerability

If you find a security issue in the studio (`web/`), the build pipeline
(`pipeline/`), or the CI workflows, please **do not open a public issue**.
Email **koshanlay1994@gmail.com** (or **6631503092@lamduan.mfu.ac.th**)
with the details, or use GitHub's
[private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guided-security-advisories)
if it is enabled on the repository. You will get a response within a week.

## Scope notes

* The studio is a static, dependency-light web app: the only bundled
  third-party code is `web/vendor/opentype.min.js`. Project files
  (`.glyphstudio.json`) and imported SVGs are parsed in the browser —
  malformed-input crashes are ordinary bugs, but anything that leads to
  script execution from a crafted project/SVG file is a security issue.
* The pipeline consumes untrusted project JSON from pull requests in CI.
  Anything that makes `json_to_ufo.py` / `fontmake` execute code from a
  crafted project file is a security issue.
* Fonts built by CI from community PRs are artifacts; they are only
  published to the gallery after a maintainer merges the PR.

## How the build itself is protected

Actions pinned to commits, least-privilege workflow tokens, Dependabot on
every dependency tree, and SLSA provenance attached to every released
binary — with an honest list of what is *not* covered — are written up in
[docs/SUPPLY-CHAIN.md](docs/SUPPLY-CHAIN.md).

To check that a file you downloaded came from this repository:

```bash
gh attestation verify <file> --repo Thiha-Lynn/myanmar-glyph-studio
```

## Supported versions

The `main` branch and the latest release are supported with fixes.
