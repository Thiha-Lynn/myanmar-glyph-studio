# Licensing notice

This project carries two licenses, because code and typefaces are
distributed differently in the font world.

## The toolkit — MIT

The studio (`web/`), the pipeline (`pipeline/`), the workflows and the docs
are [MIT licensed](LICENSE). Use them for anything, including commercially.

## The fonts — SIL Open Font License 1.1

Font files, glyph sketch data (`.glyphstudio.json`) and everything under
`projects/` are released under the
[SIL Open Font License 1.1](https://openfontlicense.org) — the standard
license of the open font world (Padauk, Noto, Google Fonts). Each family
folder ships the license text as `OFL.txt`. By contributing glyph data you
agree to this, and your name goes into the font's credits — see
[CONTRIBUTING.md](CONTRIBUTING.md).

The OFL keeps fonts free forever: anyone may use, embed, modify and
redistribute them, including in commercial products; they simply may not be
sold on their own, and derivatives stay under the OFL.

## Bundled third-party components

| Component | Origin | License |
|---|---|---|
| `web/vendor/opentype.min.js` | [opentype.js](https://github.com/opentypejs/opentype.js) | MIT |
| `web/fonts/Padauk-Regular.ttf` | [SIL Padauk 6.000](https://github.com/silnrsi/font-padauk), unmodified — the dimmed guide you trace | [OFL 1.1](web/fonts/OFL.txt) |
| `projects/sample/` letterform skeletons | derived from SIL Padauk | [OFL 1.1](projects/sample/OFL.txt) |

Padauk is Copyright (c) 2002–2025 SIL International, with Reserved Font
Names "Padauk", "Namkio" and "Deemawso". It is redistributed here
unmodified, as the OFL permits. Do not modify that file in place — see
[web/fonts/README.md](web/fonts/README.md).
