# The desktop app

The studio ships as a desktop application — a `.dmg` for macOS, an
installer `.exe` for Windows, an AppImage and `.deb` for Linux — for
people who prefer a real application to a browser tab. It is the **same
studio, byte for byte**: the `web/` directory is bundled unchanged into
the app and served over a private `app://` scheme, so everything behaves
exactly as on <https://thiha-lynn.github.io/myanmar-glyph-studio/>,
fully offline, projects autosaved locally, nothing sent anywhere.

Grab the files from the
[releases page](https://github.com/Thiha-Lynn/myanmar-glyph-studio/releases)
(each release's *Desktop apps* assets), or build them yourself — see below.

## Honest caveats, read before downloading

- **The binaries are unsigned.** Code-signing certificates cost real
  money every year (Apple ~US$99, Windows more) and this community
  project does not have them. What that means for you:
  - **macOS** will say the app "cannot be opened because the developer
    cannot be verified". Open **System Settings → Privacy & Security**,
    scroll to the blocked-app notice, and choose **Open Anyway** (once).
  - **Windows** SmartScreen will show "Windows protected your PC" —
    click **More info → Run anyway**.
  - If that makes you uncomfortable, that instinct is healthy: use the
    installable web app instead (next section), which runs inside your
    browser's sandbox and needs no download at all. The source for both
    is this repository, so you can also build the app yourself and sign
    nothing.
- **The Python build pipeline is not bundled.** The desktop app is the
  *drawing studio* (plus its quick in-browser draft TTF export). Turning
  a project into a fully shaped font still uses the
  [pipeline](../README.md#build-a-real-font-from-your-project), exactly
  as on the web.

## The zero-download alternative: install the web app

The studio is a PWA. Chrome/Edge (desktop and Android) and Safari (iOS
"Add to Home Screen") install it straight from the site — an icon, its
own window, full offline. [PLATFORMS.md](PLATFORMS.md) walks through
every platform. If you only want "the studio as an app", this is the
recommended path; the desktop bundles exist for people and organisations
where a downloadable installer is the expected shape of software.

## Build it yourself

```bash
# from a checkout — Node 20+
pip install fonttools brotli && python3 pipeline/make_gallery.py  # optional: bundle webfont kits
cd desktop
npm install
npm start                 # run unpackaged
npm run dist              # build installers for THIS platform into desktop/dist/
```

CI builds all three platforms via `.github/workflows/desktop.yml`
(manual run, or automatically attached to every published release).

## How it is put together

- `desktop/main.js` — the whole shell: a `BrowserWindow` with
  `contextIsolation`/`sandbox` on and Node integration off, a tiny
  `app://` file server over the bundled `web/` (so `fetch()` and webfont
  loading behave exactly like the website), external links pushed out to
  the system browser, and a `MGS_SELFTEST_OUT` mode that loads the app,
  captures a screenshot and exits — used to verify the packaged studio
  actually renders.
- `desktop/electron-builder.yml` — packaging targets. Unsigned on
  purpose (`identity: null`), see above.
- Electron was chosen over Tauri for now because it builds all three
  platforms from CI with no Rust toolchain and its Chromium engine is
  the exact engine the studio is developed against. The price is
  installer size (~100 MB). A Tauri wrapper (~10 MB) would render
  through each OS webview — worth revisiting once WKWebView/WebView2
  Myanmar shaping is verified by the same corpus the fonts are.
