/*
 * Community font gallery: renders gallery-data/fonts.json (written by
 * pipeline/make_gallery.py) as cards with a live @font-face preview.
 * Static, no dependencies; works offline once the PWA has cached it.
 */
(function () {
  "use strict";

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function fmtBytes(n) {
    if (!n) return "";
    return n >= 1048576 ? (n / 1048576).toFixed(1) + " MB"
                        : Math.round(n / 1024) + " KB";
  }

  function card(font, index) {
    var box = el("div", "card");
    var head = el("h2", null, font.family +
      (font.style && font.style !== "Regular" ? " " + font.style : ""));
    box.appendChild(head);

    var metaBits = [];
    if (font.author) metaBits.push("by " + font.author);
    if (font.glyphs) metaBits.push(font.glyphs + " glyphs");
    if (font.bytes) metaBits.push(fmtBytes(font.bytes));
    var meta = el("div", "meta", metaBits.join(" · ") + " ");
    meta.appendChild(el("span", "badge", font.license || "OFL-1.1"));
    box.appendChild(meta);

    var preview = el("div", "preview mm", document.getElementById("tryText").value);
    preview.dataset.preview = "1";
    box.appendChild(preview);

    var actions = el("div", "actions");
    var dl = el("a", null, "⬇ Download TTF");
    dl.href = "gallery-data/" + font.file;
    dl.setAttribute("download", "");
    actions.appendChild(dl);
    if (font.proof) {
      var proof = el("a", null, "🔍 Shaping proof");
      proof.href = "gallery-data/" + font.proof;
      proof.target = "_blank";
      proof.rel = "noopener";
      actions.appendChild(proof);
    }
    box.appendChild(actions);

    // load the real font and swap the preview onto it
    var faceName = "GalleryFont" + index;
    var face = new FontFace(faceName, "url(gallery-data/" + font.file + ")");
    face.load().then(function (loaded) {
      document.fonts.add(loaded);
      preview.style.fontFamily = '"' + faceName + '", Padauk, "Myanmar MN", ' +
        '"Noto Sans Myanmar", "Myanmar Text", sans-serif';
    }).catch(function () {
      preview.textContent = "(could not load " + font.file + ")";
      preview.style.fontSize = "14px";
    });

    return box;
  }

  function wirePreviewInput() {
    var input = document.getElementById("tryText");
    var update = function () {
      document.querySelectorAll("[data-preview]").forEach(function (p) {
        p.textContent = input.value;
      });
    };
    input.addEventListener("input", update);
    document.querySelectorAll(".tryrow button").forEach(function (b) {
      b.addEventListener("click", function () {
        input.value = b.dataset.t;
        update();
      });
    });
  }

  fetch("gallery-data/fonts.json", { cache: "no-cache" })
    .then(function (res) {
      if (!res.ok) throw new Error(res.status);
      return res.json();
    })
    .then(function (manifest) {
      var grid = document.getElementById("grid");
      var fonts = manifest.fonts || [];
      if (!fonts.length) {
        document.getElementById("empty").hidden = false;
        return;
      }
      fonts.forEach(function (f, i) { grid.appendChild(card(f, i)); });
    })
    .catch(function () {
      document.getElementById("empty").hidden = false;
    });

  wirePreviewInput();
})();
