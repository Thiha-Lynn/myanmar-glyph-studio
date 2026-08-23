"""The one dependency no scanner can see.

`web/vendor/opentype.min.js` is checked in rather than installed. No
lockfile mentions it, so `npm audit` never sees it and Dependabot cannot
open a PR for it — it is the only piece of third-party code in this
repository that could sit at an old version indefinitely with nobody
noticing.

There is nothing to fix today: opentype.js has no advisories at all, at
any version (OSV, 2026-08-23). What these tests protect is the ability to
*check* — the file's identity is recorded in `web/vendor/README.md`, and
swapping the file without updating that record fails here rather than
leaving a mystery blob in the repository.

    cd pipeline && python3 -m pytest tests/test_vendored_js.py -q
"""

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
VENDOR = ROOT / "web" / "vendor"
RECORD = VENDOR / "README.md"


def recorded():
    """(filename, version, sha256) as written down in the vendor README."""
    text = RECORD.read_text(encoding="utf-8")
    row = re.search(r"\|\s*`([^`]+)`\s*\|.*?\|\s*\*\*([^*]+)\*\*\s*\|", text)
    digest = re.search(r"sha256\s+([0-9a-f]{64})", text)
    assert row, "no vendored-file row found in web/vendor/README.md"
    assert digest, "no sha256 recorded in web/vendor/README.md"
    return row.group(1), row.group(2).strip(), digest.group(1)


def test_the_vendor_directory_is_documented():
    assert RECORD.exists(), "web/vendor/ has no README recording what is in it"


def test_every_vendored_file_is_accounted_for():
    """A second file could be added without a word; this notices."""
    files = {p.name for p in VENDOR.iterdir()
             if p.is_file() and p.name != "README.md"}
    name, _, _ = recorded()
    assert files == {name}, (
        "web/vendor/ holds %s but README.md documents %s — record it, "
        "with its version and hash" % (sorted(files), name))


def test_the_vendored_file_is_the_version_it_claims_to_be():
    name, version, want = recorded()
    got = hashlib.sha256((VENDOR / name).read_bytes()).hexdigest()
    assert got == want, (
        "%s does not match the hash recorded for %s.\n"
        "  recorded %s\n  actual   %s\n"
        "If you updated it on purpose, update web/vendor/README.md too — "
        "that table is the only record of which version this is, because "
        "the minified file carries no version string."
        % (name, version, want, got))


# `opentype.Path` — the library's global, case-sensitively. The prose
# in welcome.js says "OpenType shaping" about the format, which is a
# different thing entirely and must not count as a dependency.
CALLS = re.compile(r"\bopentype\s*\.")


def test_only_fontexport_uses_it():
    """The blast radius, asserted: if another module starts depending on
    the vendored library, the note in the README stops being true."""
    users = sorted(js.name for js in (ROOT / "web" / "js").rglob("*.js")
                   if CALLS.search(js.read_text(encoding="utf-8")))
    assert users == ["fontexport.js"], (
        "web/vendor/README.md says fontexport.js is the only caller, "
        "but these call into the library: %s" % users)
