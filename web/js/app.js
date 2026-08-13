/*
 * UI wiring: glyph browser (with mobile drawer), toolbar, zoom controls,
 * theme & language toggles, ghost/copy helpers, focus mode, project actions,
 * help modal, test-drive preview, PWA registration, preference persistence.
 */
(function () {
  "use strict";

  var $ = function (sel) { return document.querySelector(sel); };
  var current = null;

  var PREFS_KEY = "mm-glyph-studio-prefs";
  var prefs = {
    theme: "auto", lang: "en", penWidth: 60, stabilizer: 3,
    guideOpacity: 22, guideSize: 1000, pressure: true, touchDraws: true,
    ghost: ""
  };

  function savePrefs() {
    try { localStorage.setItem(PREFS_KEY, JSON.stringify(prefs)); } catch (e) {}
  }
  function loadPrefs() {
    try {
      var raw = localStorage.getItem(PREFS_KEY);
      if (raw) Object.assign(prefs, JSON.parse(raw));
    } catch (e) {}
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  var isMobile = function () { return window.matchMedia("(max-width: 1000px)").matches; };

  // ---- theme ---------------------------------------------------------------
  var THEME_ICONS = { auto: "🌗", light: "☀️", dark: "🌙" };
  function applyTheme() {
    if (prefs.theme === "auto") {
      document.documentElement.removeAttribute("data-theme");
    } else {
      document.documentElement.setAttribute("data-theme", prefs.theme);
    }
    $("#btnTheme").textContent = THEME_ICONS[prefs.theme];
    window.Editor.render();
  }

  // ---- language --------------------------------------------------------
  function applyLang() {
    window.I18N.set(prefs.lang);
    $("#btnLang").textContent = prefs.lang === "my" ? "En" : "မြ";
    buildBrowser();
    if (current) selectGlyph(current);
  }

  // ---- glyph browser -----------------------------------------------------
  function buildBrowser() {
    var box = $("#glyphBrowser");
    box.innerHTML = "";
    window.GLYPH_GROUPS.forEach(function (grp) {
      var members = window.GLYPHS.filter(function (g) { return g.group === grp.key; });
      var det = document.createElement("details");
      det.open = grp.key === "consonants";
      var sum = document.createElement("summary");
      var first = prefs.lang === "my" ? grp.my : grp.en;
      var second = prefs.lang === "my" ? grp.en : grp.my;
      sum.appendChild(el("span", "grp-name" + (prefs.lang === "my" ? " mm" : ""), first));
      sum.appendChild(el("span", "grp-my" + (prefs.lang === "my" ? "" : " mm"), second));
      var prog = el("span", "grp-progress", "");
      prog.dataset.group = grp.key;
      sum.appendChild(prog);
      det.appendChild(sum);
      var grid = el("div", "chip-grid");
      members.forEach(function (g) {
        var chip = el("button", "chip mm", g.label);
        chip.title = g.name + " — " + (prefs.lang === "my" && g.hintMy ? g.hintMy : g.hint);
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
      window.Store.drawnCount(null) + " / " + total + " " + window.I18N.t("drawnOf");
    refreshGlyphSelects();
  }

  function refreshGlyphSelects() {
    ["#ghostSelect", "#copySelect"].forEach(function (sel) {
      var box = $(sel);
      var prev = box.value;
      box.innerHTML = "";
      box.appendChild(new Option(sel === "#ghostSelect" ? window.I18N.t("ghostNone") : "—", ""));
      window.GLYPHS.forEach(function (g) {
        if (!window.Store.hasInk(g.name)) return;
        // copying a glyph onto itself is meaningless — hide it from Copy from
        if (sel === "#copySelect" && current && g.name === current.name) return;
        box.appendChild(new Option(g.label, g.name));
      });
      box.value = prev;
      if (box.selectedIndex < 0) box.value = "";
    });
    if (prefs.ghost && $("#ghostSelect").value !== prefs.ghost) {
      $("#ghostSelect").value = prefs.ghost;
      if ($("#ghostSelect").selectedIndex < 0) $("#ghostSelect").value = "";
    }
  }

  function selectGlyph(g) {
    current = g;
    window.Editor.setGlyph(g);
    $("#glyphTitle").textContent = g.label;
    $("#glyphName").textContent = g.name +
      (g.cp ? "  ·  U+" + g.cp.toString(16).toUpperCase()
            : "  ·  " + window.I18N.t("unencoded"));
    var hint = prefs.lang === "my" && g.hintMy ? g.hintMy : g.hint;
    $("#glyphHint").textContent = hint + (g.mark ? "  " + window.I18N.t("noCircleNote") : "");
    $("#glyphHint").classList.toggle("mm", prefs.lang === "my");
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

  function nextUndrawn() {
    if (!current) return;
    var list = window.GLYPHS;
    var start = list.indexOf(current);
    for (var i = 1; i <= list.length; i++) {
      var g = list[(start + i) % list.length];
      if (!window.Store.hasInk(g.name)) { selectGlyph(g); return; }
    }
    toast("All " + list.length + " glyphs have ink — congratulations! 🎉");
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
  var TOOL_BUTTONS = { pen: "#toolPen", line: "#toolLine", circle: "#toolCircle", eraser: "#toolEraser" };

  function setTool(t) {
    window.Editor.tool = t;
    Object.keys(TOOL_BUTTONS).forEach(function (k) {
      $(TOOL_BUTTONS[k]).classList.toggle("active", t === k);
    });
  }

  function wireToolbar() {
    $("#penWidth").addEventListener("input", function () {
      window.Editor.penWidth = +this.value;
      $("#penWidthVal").textContent = this.value;
      prefs.penWidth = +this.value; savePrefs();
    });
    $("#stabilizer").addEventListener("input", function () {
      window.Editor.stabilizer = +this.value;
      prefs.stabilizer = +this.value; savePrefs();
    });
    $("#guideOpacity").addEventListener("input", function () {
      window.Editor.guideOpacity = +this.value / 100;
      prefs.guideOpacity = +this.value; savePrefs();
      window.Editor.render();
    });
    $("#guideSize").addEventListener("input", function () {
      window.Editor.guideSize = +this.value;
      prefs.guideSize = +this.value; savePrefs();
      window.Editor.render();
    });
    $("#pressureToggle").addEventListener("change", function () {
      window.Editor.pressureEnabled = this.checked;
      prefs.pressure = this.checked; savePrefs();
    });
    $("#touchDraws").addEventListener("change", function () {
      window.Editor.touchDraws = this.checked;
      prefs.touchDraws = this.checked; savePrefs();
    });
    Object.keys(TOOL_BUTTONS).forEach(function (k) {
      $(TOOL_BUTTONS[k]).addEventListener("click", function () { setTool(k); });
    });
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
    $("#btnNextUndrawn").addEventListener("click", nextUndrawn);

    // ghost & copy & center & svg
    $("#ghostSelect").addEventListener("change", function () {
      window.Editor.ghostName = this.value || null;
      prefs.ghost = this.value; savePrefs();
      window.Editor.render();
    });
    $("#copySelect").addEventListener("change", function () {
      if (this.value) window.Editor.copyFrom(this.value);
      this.value = "";
    });
    $("#btnCenter").addEventListener("click", function () { window.Editor.centerInk(); });
    $("#btnSVG").addEventListener("click", function () {
      if (!current) return;
      try { window.FontExport.downloadSVG(current); }
      catch (e) { alert(e.message); }
    });

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

    // theme & language
    $("#btnTheme").addEventListener("click", function () {
      prefs.theme = prefs.theme === "auto" ? "light" : prefs.theme === "light" ? "dark" : "auto";
      savePrefs(); applyTheme();
    });
    $("#btnLang").addEventListener("click", function () {
      prefs.lang = prefs.lang === "my" ? "en" : "my";
      savePrefs(); applyLang();
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
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" ||
          e.target.tagName === "SELECT") return;
      var mod = e.metaKey || e.ctrlKey;
      if (mod && e.key === "z" && !e.shiftKey) { e.preventDefault(); window.Editor.undo(); }
      else if (mod && (e.key === "y" || (e.key === "z" && e.shiftKey))) { e.preventDefault(); window.Editor.redo(); }
      else if (e.key === "[") step(-1);
      else if (e.key === "]") step(1);
      else if (e.key === "n") nextUndrawn();
      else if (e.key === "e") setTool("eraser");
      else if (e.key === "p" || e.key === "b") setTool("pen");
      else if (e.key === "l") setTool("line");
      else if (e.key === "o") setTool("circle");
      else if (e.key === "+" || e.key === "=") window.Editor.zoomStep(1.25);
      else if (e.key === "-") window.Editor.zoomStep(0.8);
      else if (e.key === "0") window.Editor.resetView();
      else if (e.key === "f") $("#btnFocus").click();
      else if (e.key === "Escape" && document.body.classList.contains("focus")) $("#btnFocus").click();
    });
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
  var PRESETS = [
    { label: "က္က", text: "စက္ကူ ဗုဒ္ဓ မန္တလေး" },
    { label: "င်္", text: "သင်္ဘော အင်္ဂါ" },
    { label: "ျြွှ", text: "ကျောင်း ကြီး ကျွန် မြွှေ" },
    { label: "ုူ", text: "ကုန် ပူ နူး ကူး" },
    { label: "၀-၉", text: "၀၁၂၃၄၅၆၇၈၉ ၊ ။" },
    { label: "ပန်ဂရမ်", text: "သီဟိုဠ်မှ ဉာဏ်ကြီးရှင်သည် အာယုဝဍ္ဎနဆေးညွှန်းစာကို ဇလွန်ဈေးဘေး ဗာဒံပင်ထက် အဓိဋ္ဌာန်လျက် ဂဃနဏဖတ်ခဲ့သည်။" }
  ];

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
    var row = $("#presetRow");
    PRESETS.forEach(function (p) {
      var b = el("button", "btn preset mm", p.label);
      b.title = p.text;
      b.addEventListener("click", function () {
        $("#previewInput").value = p.text;
        $("#previewText").textContent = p.text;
      });
      row.appendChild(b);
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
    loadPrefs();
    window.Store.loadLocal();
    window.Editor.init($("#glyphCanvas"));

    // restore preferences into the editor + controls
    window.Editor.penWidth = prefs.penWidth;
    window.Editor.stabilizer = prefs.stabilizer;
    window.Editor.guideOpacity = prefs.guideOpacity / 100;
    window.Editor.guideSize = prefs.guideSize;
    window.Editor.pressureEnabled = prefs.pressure;
    window.Editor.touchDraws = prefs.touchDraws;
    window.Editor.ghostName = prefs.ghost || null;
    $("#penWidth").value = prefs.penWidth;
    $("#penWidthVal").textContent = prefs.penWidth;
    $("#stabilizer").value = prefs.stabilizer;
    $("#guideOpacity").value = prefs.guideOpacity;
    $("#guideSize").value = prefs.guideSize;
    $("#pressureToggle").checked = prefs.pressure;
    $("#touchDraws").checked = prefs.touchDraws;

    buildBrowser();
    wireDrawer();
    wireToolbar();
    wireProject();
    wirePreview();
    applyTheme();
    applyLang();
    $("#fontName").value = window.Store.meta.fontName;
    $("#authorName").value = window.Store.meta.author;
    $("#previewText").textContent = $("#previewInput").value;
    selectGlyph(window.GLYPHS[0]);
    setTool("pen");
    window.Editor.resetView();
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(function () { window.Editor.render(); });
    }
    schedulePreview();

    // PWA: offline support + add-to-home-screen on tablets
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("sw.js").catch(function () { /* http or unsupported — fine */ });
    }
  });
})();
