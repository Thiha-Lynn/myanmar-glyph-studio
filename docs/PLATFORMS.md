# Running the studio on every platform

The studio is a **PWA**: one codebase that installs as a real app on
Android, iOS, Windows, macOS, Linux and ChromeOS, runs offline, and gets
its own home-screen icon. That is deliberate — a solo-maintained project
cannot keep three native codebases honest, and nothing here needs a native
API that the web platform lacks (stylus pressure, file import/export and
offline storage all work).

## Install it as an app (no store, no download)

| Platform | How |
|---|---|
| **Android** (Chrome, Edge, Samsung Internet) | An **Install** bar appears; or menu → *Install app* |
| **iPhone / iPad** (Safari) | **Share** → *Add to Home Screen*. Draw with Apple Pencil; pressure varies the stroke |
| **Windows / macOS / Linux** (Chrome, Edge) | Install icon in the address bar, or menu → *Install* |
| **Any browser** | Just use <https://thiha-lynn.github.io/myanmar-glyph-studio/> |

Once installed the whole app — including the bundled Padauk guide font —
is cached, so it keeps working with no connection. That matters where
mobile data is expensive or unreliable.

## Publishing to the app stores

If you want a Play Store or App Store listing, wrap the PWA rather than
rewriting it. Both wrappers load the same hosted site, so the app never
goes stale.

### Android — Trusted Web Activity

[Bubblewrap](https://github.com/GoogleChromeLabs/bubblewrap) turns the
manifest into a signed APK/AAB. It needs Node and a JDK:

```bash
npm i -g @bubblewrap/cli
bubblewrap init --manifest https://thiha-lynn.github.io/myanmar-glyph-studio/manifest.webmanifest
bubblewrap build          # produces app-release-signed.apk / .aab
```

Answer the prompts with the application ID you want (for example
`dev.myanmarglyph.studio`). To remove the browser address bar, publish the
generated `assetlinks.json` at
`https://thiha-lynn.github.io/.well-known/assetlinks.json` — note that on
GitHub Pages this must live in a repository published at the domain root,
so a custom domain or a `<user>.github.io` repository is required.

### iOS — WKWebView shell

Apple does not accept a bare PWA, so a thin shell is needed. The smallest
honest option is [Capacitor](https://capacitorjs.com):

```bash
npm i -D @capacitor/cli @capacitor/core @capacitor/ios
npx cap init "Myanmar Glyph Studio" dev.myanmarglyph.studio --web-dir=web
npx cap add ios
npx cap open ios          # then set signing and run/archive in Xcode
```

Building and signing requires macOS, Xcode and a paid Apple Developer
account — that part cannot be automated from this repository.

**Before submitting either store listing**, note that both stores reject
apps that are "just a website" unless they add real value. Bundling the
app offline (which the service worker already does) and shipping the
guide font locally is the argument to make.

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
