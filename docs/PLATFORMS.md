# Running the studio on every platform

One `web/` directory ships five ways: as a website that installs as a
**PWA**, as **desktop apps** for macOS/Windows/Linux, as an **Android
APK**, as an **iOS app**, and — for the build pipeline — as a **pip
package**. Every app is the unchanged `web/` directory in a shell, so a
feature cannot exist on one platform and not another; there is one
implementation of each.

## The zero-download path: use the website

The studio is a PWA: open it, and it installs as a real app with its own
icon, running fully offline afterwards — including the bundled Padauk
guide font. That matters where mobile data is expensive or unreliable.

| Platform | How |
|---|---|
| **Android** (Chrome, Edge, Samsung Internet) | An **Install** bar appears; or menu → *Install app* |
| **iPhone / iPad** (Safari) | **Share** → *Add to Home Screen*. Draw with Apple Pencil; pressure varies the stroke |
| **Windows / macOS / Linux** (Chrome, Edge) | Install icon in the address bar, or menu → *Install* |
| **Any browser** | Just use <https://thiha-lynn.github.io/myanmar-glyph-studio/> |

If you only want "the studio as an app", this is the recommended path —
nothing to download, nothing to trust beyond your browser's sandbox.

## Download an installer

Every release since v0.5.0 attaches CI-built installers on the
[releases page](https://github.com/Thiha-Lynn/myanmar-glyph-studio/releases/latest):

| Platform | Asset | Notes |
|---|---|---|
| **macOS** (Apple silicon) | `Myanmar Glyph Studio-<version>-arm64.dmg` | Unsigned — see below |
| **macOS** (Intel) | `Myanmar Glyph Studio-<version>.dmg` | Unsigned — see below |
| **Windows** | `Myanmar Glyph Studio.Setup.<version>.exe` | SmartScreen will warn — see below |
| **Linux** (any distro) | `Myanmar Glyph Studio-<version>.AppImage` | `chmod +x`, then run |
| **Linux** (Debian/Ubuntu) | `myanmar-glyph-studio-desktop_<version>_amd64.deb` | `sudo dpkg -i` |
| **Android** | `myanmar-glyph-studio-v<version>.apk` | Sideload; Android asks you to allow the install |

**Read [DESKTOP.md](DESKTOP.md) before downloading a desktop build**: the
binaries are unsigned (code-signing certificates cost money this
community project does not have), so macOS and Windows each show a
warning the first time, and the doc walks through them honestly — along
with the recommendation to prefer the PWA if unsigned binaries make you
uncomfortable. The APK is likewise outside the Play Store; Android's
"install unknown apps" prompt is expected. [MOBILE.md](MOBILE.md) covers
it, and how the apps are built.

**iOS has no downloadable file** — Apple requires a paid developer
account to sign anything installable. The iOS app builds from the
committed [`mobile/`](../mobile) Capacitor project in a few minutes on a
Mac ([MOBILE.md](MOBILE.md)), and the PWA install above gives iPhone and
iPad users the same studio today, Apple Pencil included.

## Publishing to the app stores

Store listings need only signing keys and store accounts on top of what
is already in the repository — the native projects are generated from
[`mobile/`](../mobile) with `npx cap add`, and the shells load the same
`web/` directory, so a listed app never goes stale against the site:

- **Play Store / App Store** — build from `mobile/`
  ([MOBILE.md](MOBILE.md)), sign, and submit. Store review rejects apps
  that are "just a website" unless they add real value; the offline
  bundle and the locally shipped guide font are the argument to make.
- **Play Store, lighter alternative** — a Trusted Web Activity via
  [Bubblewrap](https://github.com/GoogleChromeLabs/bubblewrap) wraps the
  hosted site instead of bundling it. To remove the browser address bar,
  the generated `assetlinks.json` must be served at the domain root's
  `/.well-known/` path — on GitHub Pages that requires a custom domain or
  a `<user>.github.io` repository, which is why the shipped APK bundles
  the app instead.

## The pipeline as installable software

The drawing studio is the web app; turning a project into a fully shaped
font is the Python pipeline, and that installs anywhere Python 3.11+
runs:

```bash
pip install myanmar-glyph-studio
```

Sixteen `mgs-*` command-line tools (build, variable build, validate,
proof, kerning, …) with both test corpora inside the wheel — so any
Myanmar font on any machine can be audited with one command. The desktop
and mobile apps do **not** bundle the pipeline; they are the studio plus
its quick in-browser draft TTF export, exactly as on the web.

## Using the fonts you make — everywhere

A font built here is an ordinary TrueType file, so it works anywhere fonts
work. Nothing is locked to this toolkit.

**Video and motion**: Premiere Pro, After Effects, DaVinci Resolve, Final
Cut, CapCut and OBS all read installed system fonts — install the TTF and
it appears in the font menu. For Burmese text, prefer apps that use
HarfBuzz or CoreText; some older video tools shape text poorly for complex
scripts, so check that stacks and kinzi render before committing to a long
edit.

**Graphics and layout**: Photoshop, Illustrator, InDesign, Affinity,
Figma, Canva, Inkscape, GIMP, Krita. In Adobe apps turn on *World-Ready
Composer* (paragraph panel menu) for correct Myanmar shaping.

**Documents and PDF**: Word, Google Docs, LibreOffice, Pages, LaTeX. PDF
export embeds the font automatically, so the text stays correct on
machines that do not have it installed — that is what makes these fonts
practical for forms, books and government documents.

**Web**: ship the `.woff2` from a release (about a third the size of the
TTF) with `@font-face`, or the variable font for every weight in one file.

**Apps and games**: Unity (TextMeshPro Font Asset), Godot (FontFile),
Unreal (Font asset), Android (`res/font/`), iOS (`UIAppFonts`), Flutter
(`pubspec.yaml`), React Native / Expo (`expo-font`).

The OFL permits all of this — including commercial work and bundling
inside paid apps. The only rules are that the font is not sold on its own
and that derivatives stay under the OFL.
