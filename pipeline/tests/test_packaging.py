"""What the package does for someone who ran `pip install` and nothing else.

The commands here split in two: tools that work on files the user names
(build, validate, kerning) and repository maintenance commands that
regenerate `web/` data or scan `projects/`. Both ship in the wheel, so an
installed user can type either — and the second kind used to fail badly.
`mgs-gallery` raised FileNotFoundError on a path inside site-packages,
which reads as a broken package; `mgs-book` was worse, creating
`web/data/` *inside site-packages* and reporting success.

These tests pin the guard that replaced that behaviour. They do not need
an installed package: `find_repo_root` takes the starting path, so a temp
directory stands in for site-packages.

    cd pipeline && python3 -m pytest tests/ -q
"""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import repo_paths  # noqa: E402

PIPELINE = Path(__file__).resolve().parent.parent
ROOT = PIPELINE.parent

# Commands that regenerate repository data. Each must refuse to run
# outside a checkout rather than write somewhere surprising.
REPO_TOOLS = ["make_gallery", "gen_inventory", "make_showcase",
              "make_book", "make_pdf", "make_reference", "make_logo"]


def test_finds_the_checkout_from_inside_it():
    assert repo_paths.find_repo_root() == ROOT


def test_reports_no_checkout_when_the_markers_are_missing(tmp_path):
    # tmp_path stands in for site-packages: a directory holding the
    # package but none of the repository it was built from.
    fake_pkg = tmp_path / "site-packages" / "myanmar_glyph_studio"
    fake_pkg.mkdir(parents=True)
    assert repo_paths.find_repo_root(fake_pkg / "make_gallery.py") is None


def test_a_partial_tree_is_not_a_checkout(tmp_path):
    # projects/ alone is not enough — both markers must be present, or a
    # user's own folder called "projects" would pass for the repository.
    (tmp_path / "pkg").mkdir()
    (tmp_path / "projects").mkdir()
    assert repo_paths.find_repo_root(tmp_path / "pkg" / "x.py") is None


def test_the_refusal_names_the_tool_and_a_way_forward():
    with pytest.raises(SystemExit) as exc:
        _refuse()
    message = str(exc.value)
    assert "mgs-gallery" in message
    assert "git clone" in message
    # It must point at the commands that DO work when installed, or the
    # message just tells people the package is broken.
    assert "mgs-build" in message and "mgs-validate" in message


def _refuse():
    """Force the not-a-checkout branch regardless of where tests run."""
    original = repo_paths.find_repo_root
    repo_paths.find_repo_root = lambda *a, **k: None
    try:
        repo_paths.repo_root("mgs-gallery")
    finally:
        repo_paths.find_repo_root = original


@pytest.mark.parametrize("module", REPO_TOOLS)
def test_repo_tools_guard_before_touching_the_filesystem(module):
    source = (PIPELINE / f"{module}.py").read_text(encoding="utf-8")
    assert "repo_root(" in source, (
        f"{module}.py regenerates repository data but never calls "
        f"repo_root() — installed, it will write into site-packages")


@pytest.mark.parametrize("module", ["gen_inventory", "postbuild", "json_to_ufo"])
def test_help_is_not_read_as_a_filename(module):
    # These take positional paths and no options, so without the guard
    # `--help` is opened as a file and dies in a traceback.
    result = subprocess.run(
        [sys.executable, str(PIPELINE / f"{module}.py"), "--help"],
        capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr[-400:]
    assert "Traceback" not in result.stderr
    assert result.stdout.strip()
