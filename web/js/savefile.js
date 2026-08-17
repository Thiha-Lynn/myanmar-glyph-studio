/* Handing the user a file, on every platform this ships to.
 *
 * In a browser an <a download> click is the whole story. Inside the iOS
 * and Android app shells it is inert: WKWebView ignores the download
 * attribute on a blob: URL entirely, so pressing Export font did nothing
 * at all — no file, no error, no hint. That was the app's one purpose
 * failing silently, and it is exactly what testing on a real simulator
 * turned up that testing in a browser never could.
 *
 * So: one entry point. On the web it does what it always did — the same
 * three lines, so nothing about the site changes. Inside the app it
 * writes the file to the app's own cache directory and opens the native
 * share sheet, which is how a phone hands a file to Files, Drive, AirDrop
 * or a chat app.
 *
 * The Capacitor plugins are reached through window.Capacitor.Plugins
 * rather than an import, because web/ has no build step and must stay
 * openable straight from disk.
 */
(function () {
  "use strict";

  function isNative() {
    var C = window.Capacitor;
    return !!(C && typeof C.isNativePlatform === "function" &&
              C.isNativePlatform() && C.Plugins &&
              C.Plugins.Filesystem && C.Plugins.Share);
  }

  /* ArrayBuffer -> base64, which is what Filesystem.writeFile wants for
     binary. Chunked: a 100k-glyph font would blow the argument limit of
     String.fromCharCode applied to the whole array at once. */
  function toBase64(buffer) {
    var bytes = new Uint8Array(buffer);
    var chunk = 0x8000;
    var parts = [];
    for (var i = 0; i < bytes.length; i += chunk) {
      parts.push(String.fromCharCode.apply(
        null, bytes.subarray(i, i + chunk)));
    }
    return btoa(parts.join(""));
  }

  function webSave(filename, blob) {
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function nativeSave(filename, payload, isBinary, onError) {
    var P = window.Capacitor.Plugins;
    P.Filesystem.writeFile({
      path: filename,
      data: isBinary ? toBase64(payload) : payload,
      directory: "CACHE",
      encoding: isBinary ? undefined : "utf8"
    }).then(function (res) {
      return P.Share.share({
        title: filename,
        text: filename,
        url: res.uri,
        dialogTitle: "Save or send " + filename
      });
    }).catch(function (err) {
      // A cancelled share sheet rejects too — that is the user declining,
      // not a failure, and must not raise an alarm.
      var msg = (err && err.message) || String(err);
      if (/cancel/i.test(msg)) return;
      if (onError) onError(err);
      else alert("Could not save " + filename + ": " + msg);
    });
  }

  window.SaveFile = {
    isNative: isNative,

    /* text: a string. Used for the project file and SVG exports. */
    text: function (filename, text, mime, onError) {
      if (isNative()) return nativeSave(filename, text, false, onError);
      webSave(filename, new Blob([text], { type: mime || "text/plain" }));
    },

    /* binary: an ArrayBuffer. Used for the built TTF. */
    binary: function (filename, buffer, mime, onError) {
      if (isNative()) return nativeSave(filename, buffer, true, onError);
      webSave(filename, new Blob([buffer],
        { type: mime || "application/octet-stream" }));
    }
  };
})();
