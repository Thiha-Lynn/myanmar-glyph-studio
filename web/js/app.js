/*
 * UI wiring: glyph browser (with mobile drawer), toolbar, zoom controls,
 * focus mode, project actions, help modal, test-drive preview.
 */
(function () {
  "use strict";

  var $ = function (sel) { return document.querySelector(sel); };
  var current = null;

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  var isMobile = function () { return window.matchMedia("(max-width: 1000px)").matches; };

  // ---- glyph browser -----------------------------------------------------
  function buildBrowser() {
    var box = $("#glyphBrowser");
    box.innerHTML = "";
    window.GLYPH_GROUPS.forEach(function (grp) {
      var members = window.GLYPHS.filter(function (g) { return g.group === grp.key; });
      var det = document.createElement("details");
      det.open = grp.key === "consonants";
      var sum = document.createElement("summary");
      sum.appendChild(el("span", "grp-name", grp.en));
      sum.appendChild(el("span", "grp-my mm", grp.my));
      var prog = el("span", "grp-progress", "");
      prog.dataset.group = grp.key;
      sum.appendChild(prog);
      det.appendChild(sum);
      var grid = el("div", "chip-grid");
      members.forEach(function (g) {
        var chip = el("button", "chip mm", g.label);
        chip.title = g.name + " — " + g.hint;
        chip.dataset.glyph = g.name;
        chip.addEventListener("click", function () {
          selectGlyph(g);
          if (isMobile()) closeDrawer();
        });
        grid.appendChild(chip);
      });
      det.appendChild(grid);
      box.appendChild(det);
    });
    refreshBrowser();
  }

  function refreshBrowser() {
    document.querySelectorAll(".chip").forEach(function (chip) {
      var name = chip.dataset.glyph;
      chip.classList.toggle("drawn", window.Store.hasInk(name));
      chip.classList.toggle("active", current && current.name === name);
    });
    document.querySelectorAll(".grp-progress").forEach(function (p) {
      var key = p.dataset.group;
      var total = window.GLYPHS.filter(function (g) { return g.group === key; }).length;
      p.textContent = window.Store.drawnCount(key) + "/" + total;
    });
    var total = window.GLYPHS.length;
    $("#totalProgress").textContent =
      window.Store.drawnCount(null) + " / " + total + " glyphs drawn";
  }

  function selectGlyph(g) {
    current = g;
    window.Editor.setGlyph(g);
    $("#glyphTitle").textContent = g.label;
    $("#glyphName").textContent = g.name + (g.cp ? "  ·  U+" + g.cp.toString(16).toUpperCase() : "  ·  unencoded variant");
    $("#glyphHint").textContent = g.hint + (g.mark ? "  (do not draw the dotted circle)" : "");
    var adv = window.Store.getGlyph(g.name).advance;
    $("#advanceInput").value = adv || "";
    $("#advanceInput").placeholder = "auto " + window.Editor.measureGuideAdvance();
    refreshBrowser();
  }

  function step(dir) {
    if (!current) return;
    var idx = window.GLYPHS.indexOf(current);
    var next = window.GLYPHS[idx + dir];
    if (next) selectGlyph(next);
  }

  // ---- drawer (mobile) ---------------------------------------------------
  function openDrawer() {
    $("#sidebar").classList.add("open");
    $("#drawerOverlay").hidden = false;
  }
  function closeDrawer() {
    $("#sidebar").classList.remove("open");
    $("#drawerOverlay").hidden = true;
  }
  function wireDrawer() {
    $("#btnDrawer").addEventListener("click", function () {
      if ($("#sidebar").classList.contains("open")) closeDrawer(); else openDrawer();
    });
    $("#drawerOverlay").addEventListener("click", closeDrawer);
  }

  // ---- toolbar -----------------------------------------------------------
  function wireToolbar() {
    $("#penWidth").addEventListener("input", function () {
      window.Editor.penWidth = +this.value;
      $("#penWidthVal").textContent = this.value;
    });
    $("#stabilizer").addEventListener("input", function () {
      window.Editor.stabilizer = +this.value;
    });
    $("#guideOpacity").addEventListener("input", function () {
      window.Editor.guideOpacity = +this.value / 100;
      window.Editor.render();
    });
    $("#guideSize").addEventListener("input", function () {
      window.Editor.guideSize = +this.value;
      window.Editor.render();
    });
    $("#pressureToggle").addEventListener("change", function () {
      window.Editor.pressureEnabled = this.checked;
    });
    $("#touchDraws").addEventListener("change", function () {
      window.Editor.touchDraws = this.checked;
    });
    $("#toolPen").addEventListener("click", function () { setTool("pen"); });
    $("#toolEraser").addEventListener("click", function () { setTool("eraser"); });
    $("#btnUndo").addEventListener("click", function () { window.Editor.undo(); });
    $("#btnRedo").addEventListener("click", function () { window.Editor.redo(); });
    $("#btnClear").addEventListener("click", function () {
      if (confirm("Clear all strokes for this glyph?")) window.Editor.clearGlyph();
    });
    $("#fillPreview").addEventListener("change", function () {
      window.Editor.fillPreview = this.checked;
      window.Editor.render();
    });
    $("#advanceInput").addEventListener("change", function () {
      if (!current) return;
      var v = parseInt(this.value, 10);
      window.Store.getGlyph(current.name).advance = isNaN(v) ? null : v;
      window.Store.emit();
      window.Editor.render();
    });
    $("#btnPrev").addEventListener("click", function () { step(-1); });
    $("#btnNext").addEventListener("click", function () { step(1); });

    // zoom
    $("#btnZoomIn").addEventListener("click", function () { window.Editor.zoomStep(1.25); });
    $("#btnZoomOut").addEventListener("click", function () { window.Editor.zoomStep(0.8); });
    $("#btnZoomReset").addEventListener("click", function () { window.Editor.resetView(); });
    window.Editor.onViewChange = function () {
      $("#zoomLabel").textContent = Math.round(window.Editor.zoom * 100) + "%";
    };

    // compact toolbar toggle (small screens)
    $("#btnMoreTools").addEventListener("click", function () {
      $("#toolbar").classList.toggle("expanded");
      this.classList.toggle("active");
      window.Editor.resize();
    });

    // focus mode
    $("#btnFocus").addEventListener("click", function () {
      document.body.classList.toggle("focus");
      this.textContent = document.body.classList.contains("focus") ? "🗗" : "⛶";
      window.Editor.resize();
    });

    window.Editor.onPenDetected = function () {
      $("#touchDraws").checked = false;
      toast("Stylus detected — fingers now pan & zoom, the pen draws. Re-enable “Finger draws” to change.");
    };

    document.addEventListener("keydown", function (e) {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
      var mod = e.metaKey || e.ctrlKey;
      if (mod && e.key === "z" && !e.shiftKey) { e.preventDefault(); window.Editor.undo(); }
      else if (mod && (e.key === "y" || (e.key === "z" && e.shiftKey))) { e.preventDefault(); window.Editor.redo(); }
      else if (e.key === "[") step(-1);
      else if (e.key === "]") step(1);
      else if (e.key === "e") setTool("eraser");
      else if (e.key === "p" || e.key === "b") setTool("pen");
      else if (e.key === "+" || e.key === "=") window.Editor.zoomStep(1.25);
      else if (e.key === "-") window.Editor.zoomStep(0.8);
      else if (e.key === "0") window.Editor.resetView();
      else if (e.key === "f") $("#btnFocus").click();
      else if (e.key === "Escape" && document.body.classList.contains("focus")) $("#btnFocus").click();
    });
  }

  function setTool(t) {
    window.Editor.tool = t;
    $("#toolPen").classList.toggle("active", t === "pen");
    $("#toolEraser").classList.toggle("active", t === "eraser");
  }

  // ---- project actions ---------------------------------------------------
  function wireProject() {
    $("#fontName").addEventListener("input", function () {
      window.Store.meta.fontName = this.value.trim() || "MyMyanmarFont";
      window.Store.saveLocal();
    });
    $("#authorName").addEventListener("input", function () {
      window.Store.meta.author = this.value.trim();
      window.Store.saveLocal();
    });
    $("#btnSave").addEventListener("click", function () { window.Store.exportFile(); });
    $("#btnLoad").addEventListener("click", function () { $("#fileInput").click(); });
    $("#fileInput").addEventListener("change", function () {
      if (!this.files.length) return;
      window.Store.importFile(this.files[0], function (err) {
        if (err) { alert("Could not load project: " + err.message); return; }
        $("#fontName").value = window.Store.meta.fontName;
        $("#authorName").value = window.Store.meta.author;
        refreshBrowser();
        if (current) selectGlyph(current);
        schedulePreview();
      });
      this.value = "";
    });
    $("#btnExportTTF").addEventListener("click", function () {
      try {
        var n = window.FontExport.downloadTTF();
        toast("Font exported (" + n + " glyphs). Press Help to see how to install and use it anywhere.");
      } catch (e) { alert(e.message); }
    });
    $("#btnHelp").addEventListener("click", function () { $("#helpModal").hidden = false; });
    $("#btnHelpClose").addEventListener("click", function () { $("#helpModal").hidden = true; });
    $("#helpModal").addEventListener("click", function (e) {
      if (e.target === this) this.hidden = true;
    });
  }

  // ---- test drive --------------------------------------------------------
  var previewTimer = null;
  function schedulePreview() {
    clearTimeout(previewTimer);
    previewTimer = setTimeout(function () {
      window.FontExport.refreshPreview(function (err) {
        var box = $("#previewText");
        box.classList.toggle("empty", !!err);
      });
    }, 600);
  }

  function wirePreview() {
    $("#previewInput").addEventListener("input", function () {
      $("#previewText").textContent = this.value;
    });
    window.Editor.onInkChange = function () {
      refreshBrowser();
      schedulePreview();
    };
  }

  function toast(msg) {
    var t = $("#toast");
    t.textContent = msg;
    t.classList.add("show");
    setTimeout(function () { t.classList.remove("show"); }, 4200);
  }

  // ---- boot --------------------------------------------------------------
  document.addEventListener("DOMContentLoaded", function () {
    window.Store.loadLocal();
    window.Editor.init($("#glyphCanvas"));
    buildBrowser();
    wireDrawer();
    wireToolbar();
    wireProject();
    wirePreview();
    $("#fontName").value = window.Store.meta.fontName;
    $("#authorName").value = window.Store.meta.author;
    $("#previewText").textContent = $("#previewInput").value;
    selectGlyph(window.GLYPHS[0]);
    setTool("pen");
    window.Editor.resetView();
    // wait for system Myanmar fonts, then re-render the guide crisply
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(function () { window.Editor.render(); });
    }
    schedulePreview();
  });
})();
