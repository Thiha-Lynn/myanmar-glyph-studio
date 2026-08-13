#!/usr/bin/env python3
"""Generate studio inventory data files from the Unicode Character Database.

Emits web/data/glyphs-extended-ab.js: Myanmar Extended-A (U+AA60–AA7F,
Khamti Shan, Aiton, Pa'O) and Extended-B (U+A9E0–A9FF, Tai Laing and
Shan Pali) glyph records, the same record shape as glyphs-extended.js.

Also emits web/data/glyphs-latin-extra.js with the typographic
punctuation, symbols and accented Latin letters a font needs before it is
comfortable outside Burmese and plain English — quotation marks, dashes,
currency, and the Latin-1 letters that cover most European languages.

Names are uniXXXX production names, so pipeline/json_to_ufo.py resolves
codepoints and mark classification without any per-character tables.
Regenerate rather than hand-editing the output:

    python3 pipeline/gen_inventory.py web/data/glyphs-extended-ab.js

Myanmar Extended-C (U+116D0–116FF, Unicode 16) is intentionally NOT
emitted yet: this Python's unicodedata predates it and no common guide
font covers it. The pipeline already accepts its uXXXXX names.
"""

import json
import sys
import unicodedata
from pathlib import Path

BLOCKS = [
    {
        "range": (0xA9E0, 0xA9FF),
        "group": "extB",
        "en": "Tai Laing · Shan Pali (Ext-B)",
        "my": "တိုင်းလိုင် · ရှမ်းပါဠိ",
        "hint_my": "တိုင်းလိုင် အက္ခရာ",
    },
    {
        "range": (0xAA60, 0xAA7F),
        "group": "extA",
        "en": "Khamti Shan · Aiton (Ext-A)",
        "my": "ခန္တီးရှမ်း · အိုက်တွန်",
        "hint_my": "ခန္တီးရှမ်း အက္ခရာ",
    },
]

# Beyond the ASCII set in glyphs-latin.js: the punctuation, symbols and
# accented letters that make a font usable for real-world text.
# (U+003D "=" already ships in glyphs-latin.js — keep the sets disjoint)
LATIN_EXTRA_PUNCT = [
    0x003C, 0x003E, 0x005B, 0x005C, 0x005D, 0x005E, 0x005F, 0x0060,
    0x007B, 0x007C, 0x007D, 0x007E,
    0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2026, 0x2022,
]
# the whole Latin-1 symbol run (° · © ® ± ¼ ½ ¾ ¡ ¿ « » …) plus € and ™;
# U+00AD soft hyphen is invisible and U+00A0 is added by the build itself
LATIN_EXTRA_SYMBOLS = [cp for cp in range(0x00A1, 0x00C0) if cp != 0x00AD] + [
    0x00D7, 0x00F7, 0x2122, 0x20AC,
]
# every accented Latin-1 letter: French, German, Spanish, Portuguese,
# Italian, Nordic and Vietnamese-adjacent text all become possible
LATIN_EXTRA_LETTERS = [cp for cp in range(0x00C0, 0x0100)
                       if cp not in (0x00D7, 0x00F7)]

MARK_SUFFIX_EN = " — draw only the mark"
MARK_SUFFIX_MY = " — သင်္ကေတကိုသာ ဆွဲပါ"
DOTTED = "◌"


def short_name(cp):
    """UCD name minus the script prefix, in the inventory's Title Case."""
    full = unicodedata.name(chr(cp))
    words = full.removeprefix("MYANMAR ").split()
    return " ".join(w.capitalize() for w in words)


def record(cp, block):
    ch = chr(cp)
    cat = unicodedata.category(ch)
    is_mn = cat == "Mn"
    display = (DOTTED + ch) if cat in ("Mn", "Mc") else ch
    hint = short_name(cp) + (MARK_SUFFIX_EN if is_mn else "")
    hint_my = block["hint_my"] + (MARK_SUFFIX_MY if is_mn else "")
    return {
        "name": f"uni{cp:04X}",
        "cp": cp,
        "label": display,
        "guide": display,
        "hint": hint,
        "hintMy": hint_my,
        "mark": is_mn,
        "group": block["group"],
    }


def js_record(r):
    parts = [
        f'name:{json.dumps(r["name"])}',
        f'cp:0x{r["cp"]:04X}',
        f'label:{json.dumps(r["label"], ensure_ascii=False)}',
        f'guide:{json.dumps(r["guide"], ensure_ascii=False)}',
        f'hint:{json.dumps(r["hint"], ensure_ascii=False)}',
        f'hintMy:{json.dumps(r["hintMy"], ensure_ascii=False)}',
        f'mark:{"true" if r["mark"] else "false"}',
        f'group:{json.dumps(r["group"])}',
    ]
    return "    {" + ", ".join(parts) + "},"


def latin_extra_record(cp, group):
    ch = chr(cp)
    name = unicodedata.name(ch).title()
    return {
        "name": f"uni{cp:04X}", "cp": cp, "label": ch, "guide": ch,
        "hint": f"Optional — {name}",
        "hintMy": f"မဖြစ်မနေမလို — {name}",
        "mark": False, "group": group,
    }


def write_latin_extra(out_path):
    groups = [
        ("latinExtraPunct", "Punctuation & quotes (optional)", "အပိုသင်္ကေတ",
         LATIN_EXTRA_PUNCT),
        ("latinExtraSymbols", "Symbols & currency (optional)", "သင်္ကေတများ",
         LATIN_EXTRA_SYMBOLS),
        ("latinExtraLetters", "Accented letters (optional)", "ဥရောပအက္ခရာ",
         LATIN_EXTRA_LETTERS),
    ]
    records = []
    for key, _, _, codepoints in groups:
        for cp in codepoints:
            try:
                unicodedata.name(chr(cp))
            except ValueError:
                continue
            records.append(latin_extra_record(cp, key))

    body = "\n".join(js_record(r) for r in records)
    group_js = ",\n".join(
        f'    {{ key: {json.dumps(k)}, en: {json.dumps(en)}, '
        f'my: {json.dumps(my, ensure_ascii=False)} }}'
        for k, en, my, _ in groups)
    out_path.write_text(f"""/*
 * OPTIONAL punctuation, symbols and accented Latin letters — what a font
 * needs before it is comfortable outside Burmese and plain English.
 * Leave them empty and nothing breaks.
 *
 * GENERATED by pipeline/gen_inventory.py — regenerate, don't hand-edit.
 */
(function () {{
  "use strict";
  var G = [
{body}
  ];
  window.GLYPH_GROUPS.push(
{group_js}
  );
  G.forEach(function (g) {{ window.GLYPHS.push(g); window.GLYPH_BY_NAME[g.name] = g; }});
}})();
""", encoding="utf-8")
    print(f"Wrote {out_path}: {len(records)} glyph records")


def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).resolve().parent.parent
        / "web" / "data" / "glyphs-extended-ab.js")
    write_latin_extra(out_path.parent / "glyphs-latin-extra.js")

    records, skipped = [], 0
    for block in BLOCKS:
        lo, hi = block["range"]
        for cp in range(lo, hi + 1):
            try:
                unicodedata.name(chr(cp))
            except ValueError:
                skipped += 1
                continue
            records.append(record(cp, block))

    groups = ",\n".join(
        f'    {{ key: {json.dumps(b["group"])}, '
        f'en: {json.dumps(b["en"], ensure_ascii=False)}, '
        f'my: {json.dumps(b["my"], ensure_ascii=False)} }}'
        for b in BLOCKS)

    body = "\n".join(js_record(r) for r in records)
    out = f"""/*
 * Myanmar Extended-A (U+AA60–AA7F: Khamti Shan, Aiton, Pa'O) and
 * Extended-B (U+A9E0–A9FF: Tai Laing, Shan Pali) coverage.
 *
 * GENERATED by pipeline/gen_inventory.py from the Unicode Character
 * Database — regenerate rather than hand-editing. Guides need a font
 * covering these blocks (Padauk or Noto Sans Myanmar).
 */
(function () {{
  "use strict";
  var G = [
{body}
  ];
  window.GLYPH_GROUPS.push(
{groups}
  );
  G.forEach(function (g) {{ window.GLYPHS.push(g); window.GLYPH_BY_NAME[g.name] = g; }});
}})();
"""
    out_path.write_text(out, encoding="utf-8")
    print(f"Wrote {out_path}: {len(records)} glyph records"
          + (f" ({skipped} unassigned codepoints skipped)" if skipped else ""))


if __name__ == "__main__":
    main()
