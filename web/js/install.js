/*
 * "Install the app" affordance.
 *
 * The studio is a PWA: installed, it gets its own icon, runs full-screen
 * and works offline (the service worker caches everything, including the
 * Padauk guide font). Chrome/Edge/Android fire beforeinstallprompt, which
 * we defer and hand to a button; iOS has no such event, so Safari users
 * get the Share → Add to Home Screen instruction instead.
 */
(function () {
  "use strict";

  var DISMISS_KEY = "mm-glyph-studio-install-dismissed";
  var deferred = null;

  function isStandalone() {
    return window.matchMedia("(display-mode: standalone)").matches ||
      window.navigator.standalone === true;
  }

  function isIOS() {
    return /iphone|ipad|ipod/i.test(navigator.userAgent) ||
      // iPadOS 13+ reports as Mac, but has touch
      (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  }

  function dismissed() {
    try { return localStorage.getItem(DISMISS_KEY) === "1"; }
    catch (e) { return false; }
  }

  function remember() {
    try { localStorage.setItem(DISMISS_KEY, "1"); } catch (e) {}
  }

  function show(message, actionLabel, onAction) {
    var bar = document.createElement("div");
    bar.className = "install-bar";
    var text = document.createElement("span");
    text.textContent = message;
    bar.appendChild(text);
    if (onAction) {
      var go = document.createElement("button");
      go.className = "btn primary";
      go.textContent = actionLabel;
      go.addEventListener("click", function () {
        onAction();
        bar.remove();
      });
      bar.appendChild(go);
    }
    var close = document.createElement("button");
    close.className = "btn icon-btn";
    close.setAttribute("aria-label", "Dismiss");
    close.textContent = "✕";
    close.addEventListener("click", function () {
      remember();
      bar.remove();
    });
    bar.appendChild(close);
    document.body.appendChild(bar);
  }

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferred = e;
    if (dismissed() || isStandalone()) return;
    show(window.I18N ? window.I18N.t("installPrompt") : "Install the studio",
      window.I18N ? window.I18N.t("install") : "Install", function () {
        deferred.prompt();
        deferred = null;
        remember();
      });
  });

  window.addEventListener("appinstalled", remember);

  document.addEventListener("DOMContentLoaded", function () {
    if (isStandalone() || dismissed() || !isIOS()) return;
    // Safari never fires beforeinstallprompt — tell people the manual steps
    setTimeout(function () {
      show(window.I18N ? window.I18N.t("installIOS")
        : "Add to Home Screen: tap Share, then “Add to Home Screen”.");
    }, 4000);
  });
})();
