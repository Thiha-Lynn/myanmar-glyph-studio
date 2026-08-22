#!/usr/bin/env python3
"""Fetch the Pali Canon in Burmese script and write it as a spec corpus.

ပိဋကတ် သုံးပုံ — the Tipiṭaka — is the largest body of Burmese-script
text in existence, and its Pali orthography leans on exactly the shaping
this project's fonts must get right: stacked consonants on every line,
kinzi, the deep-descender letters, medials inside conjuncts. A font that
renders the canon renders anything.

This downloads the 61 canonical (mūla) books of the Chaṭṭha Saṅgāyana
edition in Burmese script from the Vipassana Research Institute's XML
repository, converts them to plain text, and writes one corpus file per
basket plus a combined one, in the format validate_spec.py reads:

    python3 fetch_tipitaka.py                  # -> build-tipitaka/
    python3 validate_spec.py MyFont.ttf \\
        --corpus pipeline/build-tipitaka/tipitaka_corpus.txt

Deliberately not committed, for the same reason fetch_vocab.py's parquet
is not: VRI publishes these files for free non-commercial use with
attribution, and vendoring them into an MIT/OFL repository is a
licensing question this repo does not need to answer. The canon text
itself is ancient and public domain; the committed reader data
(web/data/tipitaka.js) is built by make_tipitaka.py from SuttaCentral's
public-domain Mahāsaṅgīti root text through this repo's own
transliterator, and never from these files.

Source: github.com/VipassanaTech/tipitaka-xml (mymr/*.mul.xml),
the Chaṭṭha Saṅgāyana Tipiṭaka of the Vipassana Research Institute —
attribution with thanks; files are UTF-16 TEI with <p> paragraphs.

Only stdlib is required.
"""

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAW = "https://raw.githubusercontent.com/VipassanaTech/tipitaka-xml/main/mymr/"
DEFAULT_DIR = Path(__file__).resolve().parent / "build-tipitaka"

# The 61 mūla files, named by the CSCD scheme: prefix v = Vinaya,
# s = Suttanta (first digit: 1 DN, 2 MN, 3 SN, 4 AN, 5 KN), abh = Abhidhamma,
# e = the two paracanonical "extra" books counted with KN in this edition.
VINAYA = ["vin01m.mul", "vin02m1.mul", "vin02m2.mul",
          "vin02m3.mul", "vin02m4.mul"]
SUTTA = (["s0101m.mul", "s0102m.mul", "s0103m.mul"]
         + ["s0201m.mul", "s0202m.mul", "s0203m.mul"]
         + [f"s030{i}m.mul" for i in range(1, 6)]
         + ["s0401m.mul", "s0402m1.mul", "s0402m2.mul", "s0402m3.mul",
            "s0403m1.mul", "s0403m2.mul", "s0403m3.mul",
            "s0404m1.mul", "s0404m2.mul", "s0404m3.mul", "s0404m4.mul"]
         + ["s0501m.mul", "s0502m.mul", "s0503m.mul", "s0504m.mul",
            "s0505m.mul", "s0506m.mul", "s0507m.mul", "s0508m.mul",
            "s0509m.mul", "s0510m1.mul", "s0510m2.mul", "s0511m.mul",
            "s0512m.mul", "s0513m.mul", "s0514m.mul", "s0515m.mul",
            "s0516m.mul", "s0517m.mul", "s0519m.mul"]
         + ["e0101n.mul", "e0102n.mul"])
ABHIDHAMMA = (["abh01m.mul", "abh02m.mul"]
              + [f"abh03m{i}.mul" for i in range(1, 12)])
BASKETS = [("vinaya", VINAYA), ("sutta", SUTTA), ("abhidhamma", ABHIDHAMMA)]

TAG = re.compile(r"<[^>]+>")
NOTE = re.compile(r"<note>[^<]*</note>")

MYANMAR_TOKEN = re.compile(r"[\u1000-\u109F\uAA60-\uAA7F\uA9E0-\uA9FF]+")
BASES = (set(range(0x1000, 0x1022)) | set(range(0x1023, 0x102B))
         | {0x103F} | set(range(0x1040, 0x104A)))


def syllable_clusters(token):
    """Split a token into orthographic clusters: a new cluster starts at
    every base letter that is not glued to the previous one by a virama."""
    out, cur, prev_virama = [], "", False
    for ch in token:
        cp = ord(ch)
        if cp in BASES and cur and not prev_virama:
            out.append(cur)
            cur = ch
        else:
            cur += ch
        prev_virama = cp == 0x1039
    if cur:
        out.append(cur)
    return out


def greedy_cover(rows):
    """The smallest word list that still contains every distinct cluster.

    Same design as word_corpus.txt's 711-word cover of the vocabulary:
    complete by construction, small enough to gate CI on. Deterministic —
    ties break toward the shorter, then alphabetically earlier word — so
    regenerating against unchanged source text reproduces the file.
    """
    freq = {}
    token_clusters = {}
    for _, _, text in rows:
        for tok in MYANMAR_TOKEN.findall(text):
            if tok not in token_clusters:
                token_clusters[tok] = set(syllable_clusters(tok))
            for c in token_clusters[tok]:
                freq[c] = freq.get(c, 0) + 1
    need = set(freq)
    cover = []
    while need:
        best = None
        best_key = None
        for tok, cs in token_clusters.items():
            gain = len(cs & need)
            if not gain:
                continue
            key = (-gain, len(tok), tok)
            if best_key is None or key < best_key:
                best, best_key = tok, key
        cover.append(best)
        need -= token_clusters[best]
    return cover, len(freq)


def fetch(name, dest):
    url = RAW + name + ".xml"
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            data = resp.read()
    except urllib.error.URLError as exc:
        sys.exit(f"download failed for {name}: {exc}")
    dest.write_bytes(data)
    return data


def extract_text(xml_bytes):
    """TEI XML (UTF-16) -> plain paragraphs of Burmese-script Pali."""
    text = xml_bytes.decode("utf-16")
    text = NOTE.sub("", text)          # editorial variant notes, not canon
    out = []
    for m in re.finditer(r"<p\b[^>]*>(.*?)</p>", text, re.S):
        para = TAG.sub("", m.group(1))
        para = re.sub(r"\s+", " ", para).strip()
        if para:
            out.append(para)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Fetch the Burmese-script Tipitaka as spec corpora.")
    ap.add_argument("--out", type=Path, default=DEFAULT_DIR,
                    help="directory for the XML and corpus files")
    ap.add_argument("--basket", choices=[b for b, _ in BASKETS],
                    help="fetch a single basket instead of all three")
    ap.add_argument("--write-cover", type=Path, metavar="FILE",
                    help="also write the greedy cluster-cover word list "
                         "(this is how pali_corpus.txt is regenerated)")
    args = ap.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    xml_dir = args.out / "xml"
    xml_dir.mkdir(exist_ok=True)

    baskets = [(b, files) for b, files in BASKETS
               if args.basket in (None, b)]
    combined = []
    total_paras = 0
    for basket, files in baskets:
        rows = []
        for name in files:
            cached = xml_dir / f"{name}.xml"
            data = cached.read_bytes() if cached.exists() else fetch(name, cached)
            paras = extract_text(data)
            rows += [(basket[:3].upper(), name, p) for p in paras]
            print(f"  {name}: {len(paras)} paragraphs")
        out = args.out / f"{basket}_corpus.txt"
        with out.open("w", encoding="utf-8") as fh:
            fh.write(f"# Block {basket[:3].upper()}: {basket} pitaka, "
                     "Chattha Sangayana ed. (VRI) — fetched, not committed.\n"
                     "# Format: block<TAB>label<TAB>text\n")
            for block, label, p in rows:
                fh.write(f"{block}\t{label}\t{p}\n")
        combined += rows
        total_paras += len(rows)
        print(f"{out}: {len(rows)} paragraphs")

    if args.basket is None:
        out = args.out / "tipitaka_corpus.txt"
        with out.open("w", encoding="utf-8") as fh:
            fh.write("# The whole canon, all three baskets — see the per-"
                     "basket files for provenance.\n"
                     "# Format: block<TAB>label<TAB>text\n")
            for block, label, p in combined:
                fh.write(f"{block}\t{label}\t{p}\n")
        print(f"{out}: {total_paras} paragraphs, "
              f"{sum(len(p) for _, _, p in combined):,} characters")

    if args.write_cover:
        cover, n_clusters = greedy_cover(combined)
        with args.write_cover.open("w", encoding="utf-8") as fh:
            fh.write(
                "# Block P: Pali — a greedy cluster cover of the whole "
                "Tipitaka.\n"
                "#\n"
                f"# {len(cover)} words that between them contain every one "
                f"of the {n_clusters}\n"
                "# distinct syllable clusters in the 61 canonical books of "
                "the Chattha\n"
                "# Sangayana edition (Burmese script) — the same "
                "complete-by-construction\n"
                "# design as word_corpus.txt. Individual ancient Pali "
                "words, selected by\n"
                "# pipeline/fetch_tipitaka.py --write-cover; regenerate "
                "with that flag\n"
                "# rather than editing. Source edition: "
                "github.com/VipassanaTech/tipitaka-xml\n"
                "# (Vipassana Research Institute), used with attribution "
                "and thanks.\n"
                "#\n"
                "# Format: block<TAB>label<TAB>text\n")
            for i, tok in enumerate(cover):
                fh.write(f"P\tcover-{i:04d}\t{tok}\n")
        print(f"{args.write_cover}: {len(cover)} words covering "
              f"{n_clusters} clusters")


if __name__ == "__main__":
    main()
