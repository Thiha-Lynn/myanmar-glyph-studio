#!/usr/bin/env python3
"""Fetch the full DatarrX Myanmar vocabulary and write it as a spec corpus.

`word_corpus.txt` holds 711 words — a greedy set cover chosen so that
between them they contain every one of the 1,213 distinct syllable
clusters in the source vocabulary. That is the corpus CI gates on,
because it is small, offline and complete *by construction*.

"Complete by construction" is a claim, though, and this is the tool that
checks it against reality: it downloads all 12,450 words of the
vocabulary the cover was drawn from and writes them as a corpus
`validate_spec.py` can read, so the cover's sufficiency can be re-tested
whenever the shaping rules change.

    python3 fetch_vocab.py                       # -> build-vocab/mwg_vocab_corpus.txt
    python3 fetch_vocab.py --out /tmp/vocab.txt
    python3 validate_spec.py MyFont.ttf --corpus build-vocab/mwg_vocab_corpus.txt

Deliberately not committed and deliberately not in the gating CI job. The
parquet is 41 MB, the vocabulary is CC BY 4.0 over a CC BY-SA Wiktionary
dump, and vendoring somebody else's dataset to save a download is a
licensing question this repo does not need to answer. Fetch it when you
want the wide sweep; the committed cover is what has to stay green.

Source: huggingface.co/datasets/DatarrX/myanmar-word-glyphs (CC BY 4.0),
vocabulary from my.wiktionary.org (CC BY-SA).

Dependencies: pyarrow  (pip install pyarrow — not in requirements.txt,
because nothing in the gating path needs it)
"""

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

DATASET = "DatarrX/myanmar-word-glyphs"
PARQUET_URL = (f"https://huggingface.co/datasets/{DATASET}"
               "/resolve/main/data/train_shard_0001.parquet")
DEFAULT_DIR = Path(__file__).resolve().parent / "build-vocab"

HEADER = f"""\
# Block V: the FULL DatarrX Myanmar Word Glyphs vocabulary.
#
# Every unique word in {DATASET} — the dataset
# word_corpus.txt's 711-word cover was drawn from. Downloaded by
# fetch_vocab.py; not committed (see that module's docstring).
#
# Dataset: huggingface.co/datasets/{DATASET} (CC BY 4.0)
# Vocabulary: my.wiktionary.org (CC BY-SA)
#
# Format: block<TAB>label<TAB>text
"""


def download(url, dest):
    """Fetch `url` to `dest`, reporting progress on a slow 41 MB pull."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {url}")
    try:
        with urllib.request.urlopen(url) as response:
            total = int(response.headers.get("Content-Length") or 0)
            got = 0
            with dest.open("wb") as out:
                while chunk := response.read(1 << 20):
                    out.write(chunk)
                    got += len(chunk)
                    if total:
                        print(f"\r  {got / 1e6:6.1f} / {total / 1e6:.1f} MB",
                              end="", flush=True)
            print()
    except urllib.error.URLError as exc:
        dest.unlink(missing_ok=True)
        sys.exit(f"download failed: {exc}")
    return dest


def vocabulary(parquet_path):
    """The unique word list, sorted, from the dataset's `text` column.

    The dataset is 49,800 rows: every word rendered in four augmentation
    states. Only the label matters here, so collapse to the distinct set.
    """
    try:
        import pyarrow.parquet as pq
    except ImportError:
        sys.exit("pyarrow is required to read the dataset:  pip install pyarrow")
    table = pq.ParquetFile(parquet_path).read(columns=["text"])
    return sorted({w for w in table.column("text").to_pylist() if w and w.strip()})


def write_corpus(words, out_path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"V\t\t{w}" for w in words)
    out_path.write_text(HEADER + body + "\n", encoding="utf-8")
    return out_path


def main():
    ap = argparse.ArgumentParser(
        description="Download the DatarrX Myanmar vocabulary as a spec corpus.")
    ap.add_argument("--out", type=Path,
                    default=DEFAULT_DIR / "mwg_vocab_corpus.txt",
                    help="corpus file to write")
    ap.add_argument("--parquet", type=Path,
                    default=DEFAULT_DIR / "train_shard_0001.parquet",
                    help="where to cache the downloaded dataset shard")
    ap.add_argument("--force", action="store_true",
                    help="re-download even if the cached shard is present")
    args = ap.parse_args()

    if args.force or not args.parquet.exists():
        download(PARQUET_URL, args.parquet)
    else:
        print(f"using cached {args.parquet}")

    words = vocabulary(args.parquet)
    out = write_corpus(words, args.out)
    print(f"{len(words)} unique words  ->  {out}")
    print("\nnow run:")
    print(f"  python3 validate_spec.py <font.ttf> --corpus {out}")


if __name__ == "__main__":
    main()
