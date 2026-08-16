#!/usr/bin/env python3
"""Report what a studio translation is still missing.

Translating the interface (issue #13) means filling in two lists that
live in different files, and it is easy to finish one and forget the
other — or to leave a key out and never notice, because the studio falls
back to English silently. This prints the gap.

    python3 i18n_check.py                 # every registered language
    python3 i18n_check.py --lang my       # one language
    python3 i18n_check.py --todo my       # paste-ready stub of what's left
    mgs-i18n-check --lang mnw             # same, installed

What it reads (no dependencies, no build step):
  * web/js/i18n.js       — the built-in STRINGS table: {key: {en, my, …}}
  * web/js/lang/*.js     — community languages added with I18N.register()
  * web/data/glyphs*.js  — per-glyph instructions (hint / hintMy)

Exit status is 0 unless --strict is given and something is missing, so it
can gate a translation PR in CI.
"""

import argparse
import json
import re
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"

# "key: { en: "…", my: "…" }" — the built-in table. Values may contain
# escaped quotes, so match lazily up to a quote not preceded by a backslash.
_ENTRY = re.compile(
    r"(\w+)\s*:\s*\{([^{}]*)\}", re.S)
_LANGVAL = re.compile(r"(\w+)\s*:\s*\"((?:[^\"\\]|\\.)*)\"")
_REGISTER = re.compile(r"I18N\.register\(\s*\"(\w+)\"", re.S)
_HINT = re.compile(r"hint(My)?\s*:\s*\"((?:[^\"\\]|\\.)*)\"")


def read(path):
    return path.read_text(encoding="utf-8") if path.exists() else ""


def builtin_strings():
    """{key: {lang: text}} from the STRINGS table in web/js/i18n.js."""
    src = read(WEB / "js" / "i18n.js")
    if "var STRINGS" not in src:
        return {}
    body = src.split("var STRINGS", 1)[1]
    body = body.split("\n  };", 1)[0]
    out = {}
    for key, inner in _ENTRY.findall(body):
        langs = {lang: text for lang, text in _LANGVAL.findall(inner)}
        if langs:
            out[key] = langs
    return out


def community_languages():
    """{code: {key: text}} from web/js/lang/*.js (I18N.register calls)."""
    out = {}
    for path in sorted((WEB / "js" / "lang").glob("*.js")):
        src = read(path)
        m = _REGISTER.search(src)
        if not m:
            continue
        strings = {}
        if "strings" in src:
            body = src.split("strings", 1)[1]
            strings = {k: v for k, v in _LANGVAL.findall(body)}
        out[m.group(1)] = strings
    return out


def glyph_hints():
    """(total, translated) instruction counts across the glyph inventories."""
    total = translated = 0
    for path in sorted((WEB / "data").glob("glyphs*.js")):
        for is_my, text in _HINT.findall(read(path)):
            if is_my:
                translated += 1 if text.strip() else 0
            else:
                total += 1
    return total, translated


def report(langs, strings, only=None, as_todo=None):
    keys = sorted(strings)
    base = "en"
    rows = []
    for code in langs:
        if only and code != only:
            continue
        have = {k for k in keys if strings[k].get(code, "").strip()}
        missing = [k for k in keys if k not in have]
        rows.append((code, len(have), len(keys), missing))

    if as_todo:
        missing = dict(rows).get(as_todo) if False else None
        for code, _, _, miss in rows:
            if code != as_todo:
                continue
            print(f"// {len(miss)} string(s) still English in '{code}'.")
            print(f"// Fill in the values and keep them in web/js/i18n.js "
                  f"(built-in) or a web/js/lang/{code}.js register() call.")
            print("{")
            for k in miss:
                en = strings[k].get(base, "")
                print(f'  {k}: "",'.ljust(34) + f"// {en}")
            print("}")
        return

    width = max((len(c) for c, *_ in rows), default=4)
    print(f"{'lang'.ljust(width)}  strings      missing")
    print("-" * (width + 24))
    for code, have, total, missing in rows:
        pct = 100 * have / total if total else 100
        flag = "" if not missing else f"  ({', '.join(missing[:4])}"
        if len(missing) > 4:
            flag += f", +{len(missing) - 4} more"
        flag += ")" if missing else ""
        print(f"{code.ljust(width)}  {have:3}/{total:<3} {pct:5.1f}%  "
              f"{len(missing):3}{flag}")


def main():
    ap = argparse.ArgumentParser(
        description="Report untranslated studio strings and glyph hints.")
    ap.add_argument("--lang", help="only this language code")
    ap.add_argument("--todo", metavar="LANG",
                    help="print a paste-ready stub of the missing strings")
    ap.add_argument("--json", action="store_true", help="machine-readable")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero when anything is missing")
    args = ap.parse_args()

    strings = builtin_strings()
    if not strings:
        sys.exit(f"no STRINGS table found under {WEB} — run from a checkout")
    langs = sorted({lang for v in strings.values() for lang in v})
    extra = community_languages()

    if args.json:
        doc = {
            "languages": {
                code: {
                    "translated": sum(
                        1 for k in strings if strings[k].get(code, "").strip()),
                    "total": len(strings),
                    "missing": sorted(
                        k for k in strings
                        if not strings[k].get(code, "").strip()),
                } for code in langs},
            "community_files": {c: len(s) for c, s in extra.items()},
            "glyph_hints": dict(zip(("total", "translated"), glyph_hints())),
        }
        print(json.dumps(doc, ensure_ascii=False, indent=2))
    elif args.todo:
        report(langs, strings, as_todo=args.todo)
        return 0
    else:
        report(langs, strings, only=args.lang)
        total, my = glyph_hints()
        print(f"\nglyph instructions: {my}/{total} carry a Burmese hint")
        if extra:
            print("community language files: " + ", ".join(
                f"{c} ({n} strings)" for c, n in sorted(extra.items())))
        else:
            print("community language files: none yet — see docs/TRANSLATING.md")

    if args.strict:
        gaps = sum(1 for k in strings for c in langs
                   if not strings[k].get(c, "").strip())
        return 1 if gaps else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
