#!/usr/bin/env python3
"""Build web/data/tipitaka.js — the reader's curated canon selection.

ပိဋကတ် သုံးပုံ in the project's own fonts: one shelf of three books, a
handful of the most-recited texts from each basket, every syllable
rendered by the fonts this repository builds. The reader page
(web/tipitaka.html) turns this data into an immersive book.

Provenance, so the licensing stays boring: the segments are fetched
from SuttaCentral's Mahāsaṅgīti Tipiṭaka root text — the ancient canon
in ROMAN script, dedicated to the public domain — and converted to
Burmese script by this repository's own pali_translit.py, which is
verified against the VRI parallel edition at 62,729/62,729 words. No
modern Burmese edition's files are copied here.

    python3 make_tipitaka.py            # fetch, transliterate, write
    python3 make_tipitaka.py --offline  # reuse build-tipitaka/sc/ cache

Only stdlib is required (pali_translit is a sibling module).
"""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pali_translit import translit  # noqa: E402
from repo_paths import repo_root  # noqa: E402

RAW = ("https://raw.githubusercontent.com/suttacentral/sc-data/main/"
       "sc_bilara_data/root/pli/ms/")
CACHE = Path(__file__).resolve().parent / "build-tipitaka" / "sc"

# (basket, file path under RAW, uid, English title, Burmese title,
#  first segment kept, last segment kept — None = whole file)
SELECTION = [
    ("vinaya", "vinaya/pli-tv-kd/pli-tv-kd1_root-pli-ms.json",
     "pli-tv-kd1", "Bodhikathā — the Awakening",
     "ဗောဓိကထာ", None, "1.7.4"),
    ("sutta", "sutta/sn/sn56/sn56.11_root-pli-ms.json",
     "sn56.11", "Dhammacakkappavattana Sutta",
     "ဓမ္မစက္ကပ္ပဝတ္တနသုတ်", None, None),
    ("sutta", "sutta/kn/kp/kp5_root-pli-ms.json",
     "kp5", "Maṅgala Sutta", "မင်္ဂလသုတ်", None, None),
    ("sutta", "sutta/kn/kp/kp9_root-pli-ms.json",
     "kp9", "Metta Sutta", "မေတ္တသုတ်", None, None),
    ("sutta", "sutta/kn/dhp/dhp1-20_root-pli-ms.json",
     "dhp1-20", "Dhammapada — Yamakavagga",
     "ဓမ္မပဒ — ယမကဝဂ်", None, None),
    ("abhidhamma", "abhidhamma/ds/ds1/ds1.1_root-pli-ms.json",
     "ds1.1", "Dhammasaṅgaṇī — Mātikā",
     "ဓမ္မသင်္ဂဏီ မာတိကာ", None, None),
    ("abhidhamma", "abhidhamma/patthana/patthana1/"
     "patthana1.1_root-pli-ms.json",
     "patthana1.1", "Paṭṭhāna — Paccayuddesa",
     "ပဋ္ဌာန်း ပစ္စယုဒ္ဒေသ", None, "3.1"),
]

# ---------------------------------------------------------------------------
# The whole-canon catalog: every mūla book of the Chaṭṭha Saṅgāyana
# edition, by its standard name. The reader fetches these ON DEMAND from
# VRI's own public repository (CORS-open, ~8× gzip on the wire) — nothing
# is vendored; the page states the attribution while you read. Burmese
# titles are produced by our verified transliterator from the standard
# Pali names, so the catalog cannot drift from the orthography the fonts
# are tested against. e0101n/e0102n are the Visuddhimagga — Buddhaghosa's
# path manual, bundled with this edition but NOT one of the three
# baskets — so they shelve under their own group, honestly labelled.
CANON = [
    ("vin01m.mul",  "vinaya", "pārājikapāḷi", ""),
    ("vin02m1.mul", "vinaya", "pācittiyapāḷi", ""),
    ("vin02m2.mul", "vinaya", "mahāvaggapāḷi", ""),
    ("vin02m3.mul", "vinaya", "cūḷavaggapāḷi", ""),
    ("vin02m4.mul", "vinaya", "parivārapāḷi", ""),
    ("s0101m.mul", "sutta", "sīlakkhandhavaggapāḷi", "ဒီဃနိကာယ်"),
    ("s0102m.mul", "sutta", "mahāvaggapāḷi", "ဒီဃနိကာယ်"),
    ("s0103m.mul", "sutta", "pāthikavaggapāḷi", "ဒီဃနိကာယ်"),
    ("s0201m.mul", "sutta", "mūlapaṇṇāsapāḷi", "မဇ္ဈိမနိကာယ်"),
    ("s0202m.mul", "sutta", "majjhimapaṇṇāsapāḷi", "မဇ္ဈိမနိကာယ်"),
    ("s0203m.mul", "sutta", "uparipaṇṇāsapāḷi", "မဇ္ဈိမနိကာယ်"),
    ("s0301m.mul", "sutta", "sagāthāvaggapāḷi", "သံယုတ္တနိကာယ်"),
    ("s0302m.mul", "sutta", "nidānavaggapāḷi", "သံယုတ္တနိကာယ်"),
    ("s0303m.mul", "sutta", "khandhavaggapāḷi", "သံယုတ္တနိကာယ်"),
    ("s0304m.mul", "sutta", "saḷāyatanavaggapāḷi", "သံယုတ္တနိကာယ်"),
    ("s0305m.mul", "sutta", "mahāvaggapāḷi", "သံယုတ္တနိကာယ်"),
    ("s0401m.mul", "sutta", "ekakanipātapāḷi", "အင်္ဂုတ္တရနိကာယ်"),
    ("s0402m1.mul", "sutta", "dukanipātapāḷi", "အင်္ဂုတ္တရနိကာယ်"),
    ("s0402m2.mul", "sutta", "tikanipātapāḷi", "အင်္ဂုတ္တရနိကာယ်"),
    ("s0402m3.mul", "sutta", "catukkanipātapāḷi", "အင်္ဂုတ္တရနိကာယ်"),
    ("s0403m1.mul", "sutta", "pañcakanipātapāḷi", "အင်္ဂုတ္တရနိကာယ်"),
    ("s0403m2.mul", "sutta", "chakkanipātapāḷi", "အင်္ဂုတ္တရနိကာယ်"),
    ("s0403m3.mul", "sutta", "sattakanipātapāḷi", "အင်္ဂုတ္တရနိကာယ်"),
    ("s0404m1.mul", "sutta", "aṭṭhakanipātapāḷi", "အင်္ဂုတ္တရနိကာယ်"),
    ("s0404m2.mul", "sutta", "navakanipātapāḷi", "အင်္ဂုတ္တရနိကာယ်"),
    ("s0404m3.mul", "sutta", "dasakanipātapāḷi", "အင်္ဂုတ္တရနိကာယ်"),
    ("s0404m4.mul", "sutta", "ekādasakanipātapāḷi", "အင်္ဂုတ္တရနိကာယ်"),
    ("s0501m.mul", "sutta", "khuddakapāṭhapāḷi", "ခုဒ္ဒကနိကာယ်"),
    ("s0502m.mul", "sutta", "dhammapadapāḷi", "ခုဒ္ဒကနိကာယ်"),
    ("s0503m.mul", "sutta", "udānapāḷi", "ခုဒ္ဒကနိကာယ်"),
    ("s0504m.mul", "sutta", "itivuttakapāḷi", "ခုဒ္ဒကနိကာယ်"),
    ("s0505m.mul", "sutta", "suttanipātapāḷi", "ခုဒ္ဒကနိကာယ်"),
    ("s0506m.mul", "sutta", "vimānavatthupāḷi", "ခုဒ္ဒကနိကာယ်"),
    ("s0507m.mul", "sutta", "petavatthupāḷi", "ခုဒ္ဒကနိကာယ်"),
    ("s0508m.mul", "sutta", "theragāthāpāḷi", "ခုဒ္ဒကနိကာယ်"),
    ("s0509m.mul", "sutta", "therīgāthāpāḷi", "ခုဒ္ဒကနိကာယ်"),
    ("s0510m1.mul", "sutta", "apadānapāḷi (1)", "ခုဒ္ဒကနိကာယ်"),
    ("s0510m2.mul", "sutta", "apadānapāḷi (2)", "ခုဒ္ဒကနိကာယ်"),
    ("s0511m.mul", "sutta", "buddhavaṁsapāḷi", "ခုဒ္ဒကနိကာယ်"),
    ("s0512m.mul", "sutta", "cariyāpiṭakapāḷi", "ခုဒ္ဒကနိကာယ်"),
    ("s0513m.mul", "sutta", "jātakapāḷi (1)", "ခုဒ္ဒကနိကာယ်"),
    ("s0514m.mul", "sutta", "jātakapāḷi (2)", "ခုဒ္ဒကနိကာယ်"),
    ("s0515m.mul", "sutta", "mahāniddesapāḷi", "ခုဒ္ဒကနိကာယ်"),
    ("s0516m.mul", "sutta", "cūḷaniddesapāḷi", "ခုဒ္ဒကနိကာယ်"),
    ("s0517m.mul", "sutta", "paṭisambhidāmaggapāḷi", "ခုဒ္ဒကနိကာယ်"),
    ("s0519m.mul", "sutta", "milindapañhapāḷi", "ခုဒ္ဒကနိကာယ်"),
    ("abh01m.mul", "abhidhamma", "dhammasaṅgaṇīpāḷi", ""),
    ("abh02m.mul", "abhidhamma", "vibhaṅgapāḷi", ""),
    ("abh03m1.mul", "abhidhamma", "dhātukathāpāḷi", ""),
    ("abh03m2.mul", "abhidhamma", "puggalapaññattipāḷi", ""),
    ("abh03m3.mul", "abhidhamma", "kathāvatthupāḷi", ""),
    ("abh03m4.mul", "abhidhamma", "yamakapāḷi (1)", ""),
    ("abh03m5.mul", "abhidhamma", "yamakapāḷi (2)", ""),
    ("abh03m6.mul", "abhidhamma", "yamakapāḷi (3)", ""),
    ("abh03m7.mul", "abhidhamma", "paṭṭhānapāḷi (1)", ""),
    ("abh03m8.mul", "abhidhamma", "paṭṭhānapāḷi (2)", ""),
    ("abh03m9.mul", "abhidhamma", "paṭṭhānapāḷi (3)", ""),
    ("abh03m10.mul", "abhidhamma", "paṭṭhānapāḷi (4)", ""),
    ("abh03m11.mul", "abhidhamma", "paṭṭhānapāḷi (5)", ""),
    ("e0101n.mul", "anna", "visuddhimagga (1)", ""),
    ("e0102n.mul", "anna", "visuddhimagga (2)", ""),
]

BASKETS = [
    ("vinaya", "Vinaya Piṭaka", "ဝိနယပိဋက",
     "The basket of discipline — where the canon's story begins, under "
     "the Bodhi tree."),
    ("sutta", "Sutta Piṭaka", "သုတ္တန္တပိဋက",
     "The discourses — the first sermon and the verses every Myanmar "
     "reader knows by heart."),
    ("abhidhamma", "Abhidhamma Piṭaka", "အဘိဓမ္မပိဋက",
     "The systematic teaching — the mātikā and the twenty-four "
     "conditions, recited daily across Myanmar."),
]


def seg_key(k):
    """'sn56.11:2.3' -> (2, 3, …) for ordering and slicing."""
    return tuple(int(x) for x in re.findall(r"\d+", k.split(":", 1)[1]))


def full_key(k):
    """Order across uids too: dhp1-20 holds dhp1: … dhp20: interleaved."""
    prefix, _, rest = k.partition(":")
    return (tuple(int(x) for x in re.findall(r"\d+", prefix)),
            seg_key(k))


def fetch(path, offline):
    dest = CACHE / path.replace("/", "__")
    if dest.exists():
        return json.loads(dest.read_text(encoding="utf-8"))
    if offline:
        sys.exit(f"--offline but {dest.name} is not cached")
    CACHE.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(RAW + path, timeout=120) as resp:
        data = resp.read()
    dest.write_bytes(data)
    return json.loads(data)


TAGS = re.compile(r"<[^>]+>")


def build_text(basket, path, uid, title, title_my, first, last, offline):
    segments = fetch(path, offline)
    lo = seg_key(f"x:{first}") if first else None
    hi = seg_key(f"x:{last}") if last else None
    heads, paras, current = [], [], []
    group = None
    truncated = False
    ordered = sorted(segments, key=full_key)
    first_prefix = ordered[0].partition(":")[0]
    for key in ordered:
        prefix = key.partition(":")[0]
        pos = seg_key(key)
        if pos[0] == 0:                      # :0.x — the edition's headings
            if prefix == first_prefix:       # not each verse's story title
                heads.append(translit(TAGS.sub("", segments[key]).strip()))
            continue
        if lo and pos < lo:
            continue
        if hi and pos[: len(hi)] > hi:
            truncated = True
            break
        text = TAGS.sub("", segments[key]).strip()
        if not text:
            continue
        # Verse files (dhp) address each LINE with a single number and
        # each verse with its uid; prose addresses each SENTENCE with the
        # last number and its paragraph with everything before it. Group
        # by everything but the last component, keep verse line breaks.
        this_group = (prefix,) + pos[:-1]
        if this_group != group:
            if current:
                paras.append(current)
            current = []
            group = this_group
        current.append((translit(text), len(pos) == 1))
    if current:
        paras.append(current)
    joined = ["\n".join(t for t, _ in p) if p[0][1]
              else " ".join(t for t, _ in p) for p in paras]
    return {
        "id": uid, "title": title, "titleMy": title_my,
        "heads": [h for h in heads if h],
        "paras": joined, "excerpt": truncated,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Generate web/data/tipitaka.js for the reader page.")
    ap.add_argument("--offline", action="store_true",
                    help="use only the cached downloads")
    ap.add_argument("--out", type=Path,
                    default=None, help="output path (default web/data/)")
    args = ap.parse_args(argv)
    root = repo_root("mgs-tipitaka")
    out = args.out or root / "web" / "data" / "tipitaka.js"

    data = {"baskets": []}
    for bid, title, title_my, blurb in BASKETS:
        texts = [build_text(*sel, args.offline)
                 for sel in SELECTION if sel[0] == bid]
        data["baskets"].append({
            "id": bid, "title": title, "titleMy": title_my,
            "blurb": blurb,
            "texts": [{k: v for k, v in t.items() if k != "basket"}
                      for t in texts],
        })
        for t in texts:
            n = sum(len(p) for p in t["paras"])
            print(f"  {bid:10} {t['id']:14} {len(t['paras']):3} paragraphs, "
                  f"{n:,} chars{' (excerpt)' if t['excerpt'] else ''}")

    books = []
    xml_dir = Path(__file__).resolve().parent / "build-tipitaka" / "xml"
    for fid, group, roman, nikaya in CANON:
        base = roman.split(" (")[0].replace("ṁ", "ṃ")
        vol = roman[len(base):].strip() if roman.startswith(base) else ""
        title_my = translit(base) + ((" " + vol) if vol else "")
        cached = xml_dir / f"{fid}.xml"
        kb = round(cached.stat().st_size / 2048) if cached.exists() else None
        books.append({"id": fid, "group": group, "roman": roman,
                      "title": title_my, "nikaya": nikaya, "kb": kb})
    index = {
        "raw": ("https://raw.githubusercontent.com/VipassanaTech/"
                "tipitaka-xml/main/mymr/"),
        "books": books,
    }
    index_out = out.parent / "tipitaka-index.js"
    index_out.write_text(
        "/*\n"
        " * The whole-canon catalog for the reader's on-demand mode —\n"
        " * GENERATED by pipeline/make_tipitaka.py. Books are fetched at\n"
        " * reading time from the Chaṭṭha Saṅgāyana XML the Vipassana\n"
        " * Research Institute publishes (with attribution and thanks);\n"
        " * only this small catalog of standard book names lives here.\n"
        " */\n"
        "(function () {\n"
        '  "use strict";\n'
        f"  window.TIPITAKA_INDEX = "
        f"{json.dumps(index, ensure_ascii=False, indent=1)};\n"
        "}());\n",
        encoding="utf-8")
    print(f"{index_out}: {len(books)} books, "
          f"{index_out.stat().st_size / 1024:.0f} KB")

    body = json.dumps(data, ensure_ascii=False, indent=1)
    out.write_text(
        "/*\n"
        " * ပိဋကတ် သုံးပုံ — curated Tipiṭaka selection for the reader "
        "(web/tipitaka.html).\n"
        " *\n"
        " * GENERATED by pipeline/make_tipitaka.py — regenerate rather "
        "than hand-editing.\n"
        " * Text: the Mahāsaṅgīti Tipiṭaka root edition as published by "
        "SuttaCentral\n"
        " * (public domain), transliterated into Burmese script by "
        "pipeline/pali_translit.py\n"
        " * (verified against the VRI parallel edition, 62,729/62,729 "
        "words).\n"
        " */\n"
        "(function () {\n"
        '  "use strict";\n'
        f"  window.TIPITAKA = {body};\n"
        "}());\n",
        encoding="utf-8")
    size = out.stat().st_size
    print(f"{out}: {size/1024:.0f} KB")


if __name__ == "__main__":
    main()
