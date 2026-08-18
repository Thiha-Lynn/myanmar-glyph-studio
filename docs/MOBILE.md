# The mobile apps — Android and iOS

The studio has always run on a phone: it is a web app, and it installs to
the home screen. These are the same thing again as **real applications** —
an Android APK and an iOS app — for the Play Store, the App Store, and for
handing someone an installable file directly.

## What they are

A native shell around the unchanged `web/` directory, exactly like the
[desktop apps](DESKTOP.md). What ships is byte-for-byte what the website
serves: the same drawing code, the same shaping preview, the same glyph
inventory. No feature exists in one place and not another, because there
is only one implementation of each feature.

This is deliberate. The stroke-to-outline expansion in
[`web/js/outline.js`](../web/js/outline.js) already has to be kept in step
with its mirror in [`pipeline/json_to_ufo.py`](../pipeline/json_to_ufo.py),
and that pair is the single most delicate invariant in the project. A pure
native rewrite would have made it four or five copies of the geometry, in
four or five languages, for one maintainer to keep identical — and any
drift between them silently produces wrong fonts. The wrapper keeps it at
two.

## Building

```bash
cd mobile
npm install
npx cap sync            # copy web/ into both native projects

npx cap open ios        # opens Xcode
npx cap open android    # opens Android Studio
```

Or from the command line:

```bash
# Android — needs a JDK Gradle accepts (17 or 21, NOT 25) and the SDK
export JAVA_HOME=$(/usr/libexec/java_home -v 21)
export ANDROID_HOME=~/Library/Android/sdk
cd mobile/android && ./gradlew assembleDebug
# → app/build/outputs/apk/debug/app-debug.apk

# iOS — needs Xcode
xcodebuild -project mobile/ios/App/App.xcodeproj -scheme App \
           -sdk iphonesimulator -configuration Debug build
```

Two things that will bite, both hit while building this:

* **Gradle cannot read Java 25 class files** ("Unsupported class file
  major version 69"). Use JDK 17 or 21.
* Capacitor generates `compileSdkVersion = 36`. If your SDK manager only
  has up to 35, either install 36 or lower it in
  `mobile/android/variables.gradle`.

The generated `mobile/android/` and `mobile/ios/` directories are **not
committed** — `npx cap add android|ios` recreates them, the same way
`web/gallery-data/` is regenerated rather than stored. Only the
configuration is in git.

## Handing the user a file

A browser downloads a file with an `<a download>` click. Inside a
WebView that is inert — WKWebView ignores it on a `blob:` URL entirely —
so **Export font did nothing at all** in the first build: no file, no
error, no hint. That was the app's whole purpose failing silently, and
only running it on a simulator revealed it.

[`web/js/savefile.js`](../web/js/savefile.js) is the fix: one entry point
that keeps the plain `<a download>` on the web and, inside the app,
writes to the app's cache directory and opens the **native share sheet**
(Save to Files, AirDrop, Drive, a chat app). All three exports — the
draft TTF, a single glyph as SVG, and the project file — go through it.

## Signing and the stores, honestly

The builds produced here are **debug builds**. Publishing needs accounts
and keys that belong to the maintainer and cannot be automated away:

| | Needs |
|---|---|
| Play Store | a Google Play developer account, an upload keystore, and an `.aab` |
| App Store | an Apple Developer account, a signing certificate and provisioning profile |
| Sideloading | nothing — an unsigned APK installs on Android with "install unknown apps" enabled |

Until those exist, the honest distribution routes are the APK attached to
each release, and installing the site to the home screen, which needs
nothing at all and is what most people should do.

## Testing

Verified on an iPhone 17 simulator (iOS 26.1): the studio renders, a
traced stroke becomes ink, and Export font opens the share sheet with a
16 KB font file that iOS identifies as a font. The device-test page
([devicetest.html](https://thiha-lynn.github.io/myanmar-glyph-studio/devicetest.html))
is the right tool for judging shaping on a real handset — it renders
every cluster that has ever broken and writes the report for you.
