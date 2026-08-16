"""Myanmar Glyph Studio — the font pipeline.

Installed as `myanmar_glyph_studio`; the modules live in `pipeline/` so
that the documented clone-and-run workflow keeps working unchanged:

    python3 pipeline/json_to_ufo.py MyFont.glyphstudio.json build/
    mgs-build MyFont.glyphstudio.json build/     # same thing, installed

Each module is also importable on its own (they add their own directory
to sys.path before importing siblings), so both entry points behave the
same whether the tool was pip-installed or run out of a checkout.
"""

__version__ = "0.4.0"
