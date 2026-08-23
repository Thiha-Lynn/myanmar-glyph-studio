"""Supply-chain rules for the workflows, enforced instead of remembered.

OpenSSF Scorecard graded this repository 0 on three checks at once
(2026-08-18, score 4.6 overall), and every one of them was a real,
mechanical gap rather than a judgement call:

  * **Token-Permissions 0** — `build.yml` declared no `permissions:` at
    all, so it ran with whatever the repository default grants.
  * **Pinned-Dependencies 0** — all 33 `uses:` referenced moving tags, so
    a compromised action release would have run here on the next push.
  * **Vulnerabilities 0** — 49 of them, all in `desktop/` and `mobile/`,
    the two npm trees Dependabot was not watching.

Fixing those once is easy. Keeping them fixed is what this file is for:
a new workflow written the old way fails here rather than a month later
in a report.

    cd pipeline && python3 -m pytest tests/test_workflow_hardening.py -q
"""

import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))

USES = re.compile(r"uses:\s*(\S+)")
PINNED = re.compile(r"^[A-Za-z0-9._/-]+@[0-9a-f]{40}$")

# Local actions (./.github/actions/...) and reusable workflows in this
# repository are not third-party code and need no hash.
def third_party(ref):
    return not ref.startswith("./") and not ref.startswith(".github/")


def load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_there_are_workflows_to_check():
    assert len(WORKFLOWS) >= 6


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_every_action_is_pinned_to_a_commit(path):
    """A tag can be moved; a commit cannot."""
    loose = []
    for ref in USES.findall(path.read_text(encoding="utf-8")):
        ref = ref.strip("\"'")
        if third_party(ref) and not PINNED.match(ref):
            loose.append(ref)
    assert not loose, (
        "%s uses moving refs: %s — pin to the commit SHA and leave the "
        "version in a trailing comment" % (path.name, loose))


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_every_pin_says_which_version_it_is(path):
    """A bare 40-hex string is unreviewable; the comment is what makes a
    Dependabot bump readable."""
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.search(r"uses:\s*(\S+@[0-9a-f]{40})", line)
        if m and "#" not in line.split(m.group(1))[1]:
            pytest.fail("%s: %s has no version comment" % (path.name, m.group(1)))


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_every_workflow_declares_its_token_permissions(path):
    data = load(path)
    assert data.get("permissions") is not None, (
        "%s inherits the repository default token — declare "
        "`permissions:` (contents: read unless it needs more)" % path.name)


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_write_access_is_scoped_to_the_job_that_needs_it(path):
    """Top-level `contents: write` hands every job in the file a token
    that can push to the repository."""
    top = load(path).get("permissions")
    if isinstance(top, dict):
        assert top.get("contents") != "write", (
            "%s grants contents: write to the whole workflow — move it to "
            "the job that attaches the release" % path.name)


def test_dependabot_watches_every_dependency_tree():
    """The 49 vulnerabilities were in the two trees it did not watch."""
    cfg = load(ROOT / ".github" / "dependabot.yml")
    watched = {(u["package-ecosystem"], u["directory"]) for u in cfg["updates"]}
    for ecosystem, directory in [("github-actions", "/"), ("pip", "/pipeline"),
                                 ("npm", "/desktop"), ("npm", "/mobile")]:
        assert (ecosystem, directory) in watched, (
            "dependabot does not watch %s in %s" % (ecosystem, directory))
    # every lockfile in the repository should have a matching entry
    for lock in ROOT.glob("*/package-lock.json"):
        directory = "/" + lock.parent.name
        assert ("npm", directory) in watched, (
            "%s is not watched by dependabot" % lock.relative_to(ROOT))


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_npm_installs_come_from_the_lockfile(path):
    """`npm install` may resolve differently from the committed lockfile —
    which would quietly undo the `uuid` override in mobile/ — while
    `npm ci` installs exactly what is locked and fails if package.json
    disagrees."""
    text = path.read_text(encoding="utf-8")
    assert not re.search(r"npm\s+install\b(?!\s+-g)", text), (
        "%s runs `npm install`; use `npm ci` so CI installs the lockfile"
        % path.name)


def test_released_binaries_carry_provenance():
    """Signed-Releases was 0: nothing shipped said what built it."""
    for name in ("release.yml", "desktop.yml", "mobile.yml"):
        text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        assert "actions/attest-build-provenance@" in text, (
            "%s attaches files to a release without attesting them" % name)
        assert ".intoto.jsonl" in text, (
            "%s attests but does not ship the bundle beside the files" % name)
