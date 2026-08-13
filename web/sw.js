/* Offline cache for the Glyph Studio (PWA).
 * Bump VERSION whenever any cached file changes. */
var VERSION = "v4";
var CACHE = "glyph-studio-" + VERSION;
var ASSETS = [
  ".",
  "index.html",
  "css/app.css",
  "data/glyphs.js",
  "js/i18n.js",
  "js/store.js",
  "js/outline.js",
  "js/editor.js",
  "js/fontexport.js",
  "js/app.js",
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
    fetch(e.request).then(function (res) {
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
