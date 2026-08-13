# Bundled guide font

`Padauk-Regular.ttf` is the **unmodified** SIL Padauk 6.000 release, used as
the dimmed guide the studio draws underneath your ink. Bundling it means
stacked guides (က္က), kinzi (င်္က) and every ethnic-language letter render
correctly on any device — the system Myanmar fonts on Windows, macOS,
Android and iOS do not all shape these, which produced empty boxes in the
guides before.

| | |
|---|---|
| Version | 6.000 (2025-10-08) |
| Source | <https://github.com/silnrsi/font-padauk/releases/tag/v6.000> |
| SHA-256 | `3dd5406194518d903c423fc77822be4e8b6c9e6a75dfacda2eafc1a54e64cade` |
| Copyright | (c) 2002–2025 SIL International |
| License | [SIL Open Font License 1.1](OFL.txt) |
| Reserved Font Names | "Padauk", "Namkio", "Deemawso" |

**Do not modify this file.** The OFL permits redistributing the original
font with software (that is what we do here), but any modification —
including subsetting or converting it to WOFF2 — creates a Modified
Version, which may not use the reserved name "Padauk". If you need a
smaller or converted build, rename the font first and read
[OFL-FAQ](https://openfontlicense.org).

Padauk is also the reference the sample project traces
(`pipeline/make_sample.py`), and the reference for correct Myanmar shaping
behaviour when reviewing a font (`docs/TESTING.md`).

Contributors can load a *different* reference face at runtime — Studio →
**⚙ → Guide font** — for example to trace over their own earlier font. That
choice is stored in the browser only and never leaves the device.
