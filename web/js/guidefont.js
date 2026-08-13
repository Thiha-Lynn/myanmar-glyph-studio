/*
 * Guide font management.
 *
 * The dimmed letter you trace comes from a real Myanmar font. The studio
 * bundles SIL Padauk (web/fonts/, OFL) so stacks and kinzi render correctly
 * on every device — system Myanmar fonts often cannot shape them and show
 * empty boxes instead.
 *
 * Contributors can also load their OWN reference face (trace over an
 * earlier font of theirs, or a style they admire). That file is kept in
 * IndexedDB on the device and never uploaded anywhere.
 */
(function () {
  "use strict";

  var DB = "mm-glyph-studio", STORE = "prefs", KEY = "guideFont";
  var FAMILY = "GlyphStudioGuide";
  var loaded = null; // FontFace currently installed

  function openDB() {
    return new Promise(function (resolve, reject) {
      if (!window.indexedDB) { reject(new Error("no IndexedDB")); return; }
      var req = indexedDB.open(DB, 1);
      req.onupgradeneeded = function () {
        if (!req.result.objectStoreNames.contains(STORE)) {
          req.result.createObjectStore(STORE);
        }
      };
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error); };
    });
  }

  function idb(mode, fn) {
    return openDB().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, mode);
        var req = fn(tx.objectStore(STORE));
        tx.oncomplete = function () { resolve(req && req.result); };
        tx.onerror = function () { reject(tx.error); };
      });
    });
  }

  function install(buffer, name) {
    var face = new FontFace(FAMILY, buffer);
    return face.load().then(function (f) {
      if (loaded) { try { document.fonts.delete(loaded); } catch (e) {} }
      document.fonts.add(f);
      loaded = f;
      if (window.Editor) window.Editor.render();
      return name;
    });
  }

  window.GuideFont = {
    family: FAMILY,

    /* True once a custom face is active (the bundled Padauk is used
       otherwise — it needs no registration, it is in the CSS stack). */
    isCustom: function () { return !!loaded; },

    /* Load a user-picked font file and remember it on this device. */
    use: function (file) {
      return file.arrayBuffer().then(function (buf) {
        return install(buf.slice(0), file.name).then(function (name) {
          return idb("readwrite", function (store) {
            store.put({ name: name, buffer: buf }, KEY);
          }).catch(function () { /* private mode — still active this session */ })
            .then(function () { return name; });
        });
      });
    },

    /* Re-install the remembered face at startup, if any. */
    restore: function () {
      return idb("readonly", function (store) { return store.get(KEY); })
        .then(function (rec) {
          if (!rec || !rec.buffer) return null;
          return install(rec.buffer, rec.name);
        })
        .catch(function () { return null; });
    },

    /* Back to the bundled Padauk. */
    reset: function () {
      if (loaded) { try { document.fonts.delete(loaded); } catch (e) {} }
      loaded = null;
      if (window.Editor) window.Editor.render();
      return idb("readwrite", function (store) { store.delete(KEY); })
        .catch(function () { /* nothing stored */ });
    },

    /*
     * Make sure the guide face is actually downloaded before the canvas
     * paints — a canvas font string does not trigger a webfont fetch.
     */
    warmUp: function () {
      if (!document.fonts || !document.fonts.load) return Promise.resolve();
      return document.fonts.load('64px Padauk', 'ကမြ').catch(function () {});
    },

    /*
     * Does the active guide face SHAPE Myanmar (form the က္က stack), or is
     * the browser falling back to a face that just lines glyphs up? Used to
     * warn contributors that their guides are unreliable.
     */
    shapesStacks: function (ctx) {
      if (!ctx) return true;
      ctx.save();
      ctx.font = '100px ' + (loaded ? '"' + FAMILY + '", ' : '') +
        'Padauk, "Myanmar MN", "Noto Sans Myanmar", "Myanmar Text", sans-serif';
      var stack = ctx.measureText("က္က").width;
      var single = ctx.measureText("က").width;
      ctx.restore();
      if (!single) return true;
      // a real stack is far narrower than two letters side by side
      return stack < single * 1.6;
    }
  };
})();
