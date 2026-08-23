"""Everything the studio loads must survive going offline.

The studio is a PWA: `web/sw.js` lists the files to cache, and the house
rule in CLAUDE.md is that touching anything under `web/` means bumping
`VERSION` and extending `ASSETS`. Forgetting the second half is silent —
the app works perfectly in the tab you are testing in, because the
network is right there, and only fails for someone offline, or on the
first load after an update, with a missing script and no error anyone
sees.

This walks the other way round: every stylesheet and script the HTML
pages actually reference has to be in the cache list, and every path in
the cache list has to exist.

    cd pipeline && python3 -m pytest tests/test_web_assets.py -q
"""

import re
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent.parent / "web"


def cached_assets():
    text = (WEB / "sw.js").read_text(encoding="utf-8")
    block = text[text.index("var ASSETS"):text.index("];")]
    return set(re.findall(r'"([^"]+)"', block))


def referenced(page):
    """Local stylesheets and scripts a page loads, comments stripped —
    index.html carries a commented-out block of community language files
    that are deliberately not shipped yet."""
    text = re.sub(r"<!--.*?-->", "", page.read_text(encoding="utf-8"),
                  flags=re.DOTALL)
    refs = (re.findall(r'<script[^>]+src="([^"]+)"', text) +
            re.findall(r'<link[^>]+href="([^"]+)"', text))
    out = []
    for ref in refs:
        if ref.startswith(("http://", "https://", "//", "data:", "#")):
            continue
        out.append(ref.split("?")[0])
    return out


def test_every_page_loads_only_files_that_exist():
    missing = []
    for page in sorted(WEB.glob("*.html")):
        for ref in referenced(page):
            if not (WEB / ref).exists():
                missing.append("%s -> %s" % (page.name, ref))
    assert not missing, "dead references: " + ", ".join(missing)


def test_every_loaded_file_is_cached_for_offline_use():
    assets = cached_assets()
    gaps = []
    for page in sorted(WEB.glob("*.html")):
        if page.name not in assets:
            gaps.append("page %s is not in sw.js ASSETS" % page.name)
        for ref in referenced(page):
            if ref not in assets:
                gaps.append("%s loads %s, which sw.js does not cache"
                            % (page.name, ref))
    assert not gaps, "; ".join(gaps)


def test_the_cache_list_has_no_ghosts():
    strays = [a for a in cached_assets()
              if a not in (".",) and not (WEB / a).exists()]
    assert not strays, "sw.js caches files that are gone: %s" % sorted(strays)
