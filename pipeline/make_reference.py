#!/usr/bin/env python3
"""Build a reference corpus from a whole Wikisource category.

`word_corpus.txt` was built once, by hand, from a word list: 711 words
greedily chosen to contain every syllable cluster in a 12,450-word
vocabulary. It works, and nothing in the repository could reproduce it or
point the same idea at a different source. This does.

Give it a category of Burmese texts and it fetches them, segments them
into syllable clusters exactly as HarfBuzz does, and greedily selects the
smallest set of *passages* that between them contain every distinct
cluster it saw. The output is a corpus `validate_spec.py` reads and a
report of what the source actually contains.

    python3 make_reference.py                             # the Jātaka cycle
    python3 make_reference.py --category 'ကဏ္ဍ:ဇာတ်နိပါတ်' --limit 200
    python3 make_reference.py --out ../pipeline/jataka_corpus.txt

Default source: **ကဏ္ဍ:ဇာတ်နိပါတ်**, the 550 Jātaka stories — the cycle of
the Buddha's past lives, in the classical Burmese of ညောင်ကန်ဆရာတော်. It is
narrative prose across 538 separate stories, which makes it far richer in
distinct characters and clusters than any single book: place names,
personal names, Pali loanwords, numbers, and the full range of tone and
stacking that ordinary vocabulary lists never reach.

Licensing: transcriptions from မြန်မာဝီကီရင်းမြစ် (Burmese Wikisource) are
CC BY-SA 4.0 and the underlying Jātaka stories are ancient. The corpus
file carries that attribution in its header.

Dependencies: uharfbuzz (for cluster segmentation).
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

try:
    import uharfbuzz as hb
except ImportError:                                         # pragma: no cover
    sys.exit("uharfbuzz is required:  pip install -r requirements.txt")

ROOT = Path(__file__).resolve().parent.parent
API = "https://my.wikisource.org/w/api.php"
UA = ("myanmar-glyph-studio/0.4 (font rendering test; "
      "https://github.com/Thiha-Lynn/myanmar-glyph-studio)")
DEFAULT_CATEGORY = "ကဏ္ဍ:ဇာတ်နိပါတ်"
DEFAULT_OUT = Path(__file__).resolve().parent / "jataka_corpus.txt"
DEFAULT_FONT = ROOT / "web" / "fonts" / "Padauk-Regular.ttf"


def api(params):
    params.setdefault("format", "json")
    params.setdefault("formatversion", "2")
    url = f"{API}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.URLError as exc:
        sys.exit(f"could not reach Wikisource: {exc}")


def category_members(category, limit):
    titles, cont = [], {}
    while len(titles) < limit:
        data = api({"action": "query", "list": "categorymembers",
                    "cmtitle": category, "cmlimit": "500",
                    "cmnamespace": "0", **cont})
        titles += [m["title"] for m in data["query"]["categorymembers"]]
        if "continue" not in data:
            break
        cont = data["continue"]
    return titles[:limit]


def fetch_many(titles, batch=50):
    """Wikitext for many pages, 50 at a time — 538 pages in 11 requests."""
    out = {}
    for i in range(0, len(titles), batch):
        chunk = titles[i:i + batch]
        data = api({"action": "query", "prop": "revisions", "rvprop": "content",
                    "rvslots": "main", "titles": "|".join(chunk)})
        for page in data.get("query", {}).get("pages", []):
            revisions = page.get("revisions")
            if revisions:
                out[page["title"]] = revisions[0]["slots"]["main"]["content"]
        print(f"  fetched {min(i + batch, len(titles))}/{len(titles)}",
              flush=True)
    return out


def to_passages(wikitext):
    text = re.sub(r"\{\{.*?\}\}", "", wikitext, flags=re.S)
    text = re.sub(r"<ref.*?</ref>", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"'{2,}", "", text)
    text = re.sub(r"^[=*#:;]+\s*", "", text, flags=re.M)
    out = []
    for line in text.split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) > 40 and re.search(r"[က-႟]", line):
            out.append(line)
    return out


class Segmenter:
    """HarfBuzz cluster segmentation — the same grouping the validator uses."""

    def __init__(self, font_path):
        blob = hb.Blob.from_file_path(str(font_path))
        self.font = hb.Font(hb.Face(blob))

    def clusters(self, text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.font, buf)
        bounds = sorted({info.cluster for info in buf.glyph_infos})
        bounds.append(len(text))
        return {text[a:b] for a, b in zip(bounds, bounds[1:]) if text[a:b].strip()}


def greedy_cover(passages, seg):
    """Fewest passages that still contain every cluster the source shows.

    The same construction behind word_corpus.txt: repeatedly take whatever
    adds the most that is still missing, and stop when nothing adds
    anything. It is not the true minimum — that problem is NP-hard — but
    it lands within a few percent and runs in seconds.
    """
    sets = [(text, seg.clusters(text)) for text in passages]
    universe = set().union(*(s for _, s in sets)) if sets else set()
    chosen, covered = [], set()
    while covered != universe:
        best, gain = None, 0
        for text, clusters in sets:
            new = len(clusters - covered)
            if new > gain:
                best, gain = (text, clusters), new
        if best is None:
            break
        chosen.append(best[0])
        covered |= best[1]
    return chosen, universe


def main():
    ap = argparse.ArgumentParser(
        description="Build a reference corpus from a Wikisource category.")
    ap.add_argument("--category", default=DEFAULT_CATEGORY)
    ap.add_argument("--limit", type=int, default=600)
    ap.add_argument("--font", type=Path, default=DEFAULT_FONT,
                    help="font used only to segment clusters")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--block", default="J", help="corpus block letter")
    args = ap.parse_args()

    print(f"category: {args.category}")
    titles = category_members(args.category, args.limit)
    print(f"  {len(titles)} pages")
    pages = fetch_many(titles)

    passages, chars = [], Counter()
    for text in pages.values():
        for passage in to_passages(text):
            passages.append(passage)
            chars.update(passage)
    print(f"\n{len(passages)} passages, "
          f"{sum(len(p) for p in passages):,} characters")

    myanmar = {c for c in chars if "က" <= c <= "႟"}
    print(f"distinct Myanmar characters: {len(myanmar)}")

    seg = Segmenter(args.font)
    chosen, universe = greedy_cover(passages, seg)
    print(f"distinct syllable clusters: {len(universe):,}")
    print(f"greedy cover: {len(chosen)} passages hold all of them "
          f"({len(chosen) / max(1, len(passages)) * 100:.1f}% of the source)")

    header = [
        f"# Block {args.block}: reference corpus from {args.category}.",
        "#",
        f"# {len(chosen)} passages, greedily chosen so that between them they",
        f"# contain all {len(universe)} distinct syllable clusters and all",
        f"# {len(myanmar)} distinct Myanmar characters found across "
        f"{len(pages)} pages",
        f"# ({sum(len(p) for p in passages):,} characters of source text).",
        "#",
        "# Text: မြန်မာဝီကီရင်းမြစ် (Burmese Wikisource), CC BY-SA 4.0.",
        "# The underlying Jātaka stories are ancient; the Burmese rendering",
        "# is the classical one attributed to ညောင်ကန်ဆရာတော်.",
        "#",
        "# GENERATED by pipeline/make_reference.py — regenerate, do not edit.",
        "#",
        "# Format: block<TAB>label<TAB>text",
    ]
    body = [f"{args.block}\t\t{text}" for text in chosen]
    args.out.write_text("\n".join(header + body) + "\n", encoding="utf-8")
    print(f"\n{args.out}: {len(chosen)} rows "
          f"({args.out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
