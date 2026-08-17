#!/usr/bin/env python3
"""Finding the repository checkout — for the tools that need one.

Most commands here work on files the user names: build a font, validate a
font, add kerning. Those work anywhere. But several are *repository
maintenance* commands — they regenerate data files inside `web/` or scan
`projects/` for built fonts — and they mean nothing outside a clone. They
travel in the wheel because they are part of the toolchain's story (and
because CI installs the package to run them), so an installed user can
type them by accident.

Before this guard they did not say so. `mgs-gallery` failed with a
FileNotFoundError naming a path inside site-packages, which reads as a
broken package rather than a tool used out of context; `mgs-book` was
worse, cheerfully creating `web/data/` *inside site-packages* and
reporting success.

The rule: locate the checkout by looking for the directories these tools
actually need, and if they are not there, say what happened in one line.
"""

import sys
from pathlib import Path

# Directories that only exist in a checkout, never in an installed package.
MARKERS = ("projects", "web")


def find_repo_root(start=None):
    """The checkout root containing this package, or None when installed.

    `start` is a path inside the tree (defaults to this module), so tests
    can point it somewhere that is deliberately not a checkout.
    """
    root = Path(start or __file__).resolve().parent.parent
    if all((root / m).is_dir() for m in MARKERS):
        return root
    return None


def repo_root(tool=None):
    """Same, but exit with an explanation instead of returning None."""
    root = find_repo_root()
    if root is not None:
        return root
    name = tool or Path(sys.argv[0]).name or "This command"
    sys.exit(
        f"{name}: this is a repository maintenance command — it regenerates\n"
        f"files in web/ or reads the fonts in projects/, so it needs a clone\n"
        f"of the repository rather than an installed package.\n\n"
        f"    git clone https://github.com/Thiha-Lynn/myanmar-glyph-studio\n"
        f"    cd myanmar-glyph-studio && pip install -e \".[dev]\"\n\n"
        f"Commands that work on your own files anywhere: mgs-build,\n"
        f"mgs-variable, mgs-validate, mgs-proof, mgs-kerning, mgs-postbuild."
    )


def help_if_asked(doc):
    """Print the module docstring for -h/--help and exit cleanly.

    These tools take positional paths and no options, so without this
    `--help` is read as a filename and dies in a traceback — a poor first
    impression for a command someone just installed.
    """
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print((doc or "").strip())
        raise SystemExit(0)
