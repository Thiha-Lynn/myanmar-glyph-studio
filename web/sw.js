/* Offline cache for the Glyph Studio (PWA).
 * Bump VERSION whenever any cached file changes. */
var VERSION = "v20";
var CACHE = "glyph-studio-" + VERSION;
var ASSETS = [
  ".",
  "index.html",
  "gallery.html",
  "css/app.css",
  "data/glyphs.js",
  "data/glyphs-extended.js",
  "data/glyphs-extended-ab.js",
  "data/glyphs-latin.js",
  "data/glyphs-latin-extra.js",
  "js/i18n.js",
  "js/guidefont.js",
  "js/store.js",
  "fonts/Padauk-Regular.ttf",
  "js/outline.js",
  "js/anchors.js",
  "js/svgimport.js",
  "js/vectools.js",
  "js/editor.js",
  "js/fontexport.js",
  "js/app.js",
  "js/install.js",
  "js/gallery.js",
  "vendor/opentype.min.js",
  "manifest.webmanifest",
  "icons/icon.svg",
  "icons/icon-180.png",
  "icons/icon-512.png"
];

self.addEventListener("install", function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) { return c.addAll(ASSETS); })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) {
        return k.indexOf("glyph-studio-") === 0 && k !== CACHE;
      }).map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

/* network-first for same-origin, falling back to cache when offline */
self.addEventListener("fetch", function (e) {
  if (e.request.method !== "GET") return;
  if (new URL(e.request.url).origin !== self.location.origin) return;
  e.respondWith(
    // no-cache: always revalidate with the server so app updates land on
    // the next load instead of waiting out the browser's heuristic cache
    fetch(e.request, { cache: "no-cache" }).then(function (res) {
      if (res.ok) {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
      }
      return res;
    }).catch(function () {
      return caches.match(e.request, { ignoreSearch: true });
    })
  );
});
