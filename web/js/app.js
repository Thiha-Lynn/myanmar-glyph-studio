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
    ghost: "", tool: "brush", snap: false, eraserMode: "partial",
    eraserSize: 60, fillShape: false
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
        if (g.variant) chip.dataset.variant = g.variant;
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

  // ---- mobile: project menu sheet, thumb bar, folding test drive ---------
  function wireMobile() {
    var sheet = $("#menuSheet"), body = $("#sheetBody");
    var homes = [
      { node: $("#metaFields"), parent: $("#metaFields").parentNode, next: $("#metaFields").nextSibling },
      { node: $("#secondaryActions"), parent: $("#secondaryActions").parentNode, next: $("#secondaryActions").nextSibling }
    ];

    function openMenu() {
      homes.forEach(function (h) { body.appendChild(h.node); });
      sheet.hidden = false;
    }
    function closeMenu() {
      sheet.hidden = true;
      homes.forEach(function (h) { h.parent.insertBefore(h.node, h.next); });
    }
    $("#btnMenu").addEventListener("click", openMenu);
    $("#btnMenuClose").addEventListener("click", closeMenu);
    sheet.addEventListener("click", function (e) { if (e.target === this) closeMenu(); });
    // any action inside the sheet closes it, so the canvas comes straight back
    body.addEventListener("click", function (e) {
      if (e.target.closest(".btn") && !e.target.closest("#metaFields")) {
        setTimeout(closeMenu, 60);
      }
    });
    window.matchMedia("(max-width: 640px)").addEventListener("change", function (e) {
      if (!e.matches && !sheet.hidden) closeMenu();
    });

    // thumb bar
    var acts = {
      prev: function () { step(-1); },
      next: function () { step(1); },
      undo: function () { window.Editor.undo(); },
      redo: function () { window.Editor.redo(); },
      nextEmpty: nextUndrawn,
      tool: function () {
        setTool(window.Editor.tool === "eraser" ? "brush" : "eraser");
      }
    };
    $("#mobileBar").addEventListener("click", function (e) {
      var btn = e.target.closest("[data-act]");
      if (!btn) return;
      var fn = acts[btn.dataset.act];
      if (fn) { fn(); if (navigator.vibrate) { try { navigator.vibrate(8); } catch (err) {} } }
    });

    // folding test drive — the canvas gets the room by default on phones
    var td = $("#testdrive");
    if (window.matchMedia("(max-width: 640px)").matches) td.classList.add("collapsed");
    $("#btnTestToggle").addEventListener("click", function () {
      td.classList.toggle("collapsed");
      window.Editor.resize();
    });
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
  var CURSORS = {
    select: "default", direct: "default", pen: "crosshair", brush: "crosshair",
    line: "crosshair", rect: "crosshair", circle: "crosshair", eraser: "none"
  };

  /* Show only the option groups whose data-for lists the active tool
   * (anchor mode acts as a pseudo-tool for the options bar). */
  function syncOptionsBar() {
    var t = window.Editor.anchorMode ? "anchors" : window.Editor.tool;
    document.querySelectorAll("#toolOptions .opt-group[data-for]").forEach(function (g) {
      g.classList.toggle("show", g.dataset.for.split(" ").indexOf(t) >= 0);
    });
  }

  function syncRail() {
    var anchor = window.Editor.anchorMode;
    document.querySelectorAll("#toolRail [data-tool]").forEach(function (b) {
      b.classList.toggle("active", !anchor && b.dataset.tool === window.Editor.tool);
    });
    $("#btnAnchors").classList.toggle("active", anchor);
    $("#glyphCanvas").style.cursor =
      anchor ? "default" : (CURSORS[window.Editor.tool] || "crosshair");
    var mb = $("#mbTool");
    if (mb) mb.textContent = window.Editor.tool === "eraser" ? "🧽" : "✏️";
  }

  /* Enable/disable the contextual buttons from the vector-tool state. */
  function syncVecUI() {
    var st = window.VecTools.status();
    var chip = $("#selCount");
    chip.hidden = !st.sel;
    if (st.sel) chip.textContent = st.sel + " " + window.I18N.t("selected");
    ["#btnDup", "#btnFlipH", "#btnFlipV", "#btnSmoothSel", "#btnSimplify",
     "#btnCopySel", "#btnDelSel"].forEach(function (sel) {
      $(sel).disabled = !st.sel;
    });
    $("#btnPasteSel").disabled = !window.Editor.clipboard.length;
    $("#btnNodeType").disabled = !st.nodeIsBez;
    $("#btnNodeDel").disabled = !st.node;
    $("#btnReverse").disabled = !st.target;
    ["#btnPenDone", "#btnPenBack", "#btnPenCancel"].forEach(function (sel) {
      $(sel).disabled = !st.penNodes;
    });
    $("#btnPenClose").disabled = st.penNodes < 2;
    // the width slider mirrors the selection's stroke width in select mode
    if (window.Editor.tool === "select" && st.sel) {
      var w = window.VecTools.selWidth(window.Editor);
      if (w) { $("#penWidth").value = w; $("#penWidthVal").textContent = w; }
    }
  }

  function setTool(t) {
    window.Editor.setTool(t);   // also exits anchor mode + resets vec state
    if (t !== "select") {
      // restore the drawing width after select mode borrowed the slider
      $("#penWidth").value = prefs.penWidth;
      $("#penWidthVal").textContent = prefs.penWidth;
    }
    prefs.tool = t; savePrefs();
    syncRail();
    syncOptionsBar();
    syncVecUI();
  }

  function wireToolbar() {
    window.Editor.onToolChange = function () {
      prefs.tool = window.Editor.tool; savePrefs();
      syncRail(); syncOptionsBar(); syncVecUI();
    };
    window.VecTools.onSelectionChange = function () { syncVecUI(); };

    $("#penWidth").addEventListener("input", function () {
      $("#penWidthVal").textContent = this.value;
      if (window.Editor.tool === "select") return; // applied on release below
      window.Editor.penWidth = +this.value;
      prefs.penWidth = +this.value; savePrefs();
    });
    // in select mode the slider RE-WIDTHS the selected strokes (one undo step)
    $("#penWidth").addEventListener("change", function () {
      if (window.Editor.tool === "select" && window.VecTools.hasSelection()) {
        window.VecTools.applyWidth(window.Editor, +this.value);
      }
    });
    $("#stabilizer").addEventListener("input", function () {
      window.Editor.stabilizer = +this.value;
      prefs.stabilizer = +this.value; savePrefs();
    });
    $("#fillShape").addEventListener("change", function () {
      window.Editor.fillShape = this.checked;
      prefs.fillShape = this.checked; savePrefs();
    });
    $("#snapToggle").addEventListener("change", function () {
      window.Editor.snapEnabled = this.checked;
      prefs.snap = this.checked; savePrefs();
    });

    // eraser options
    function setEraserMode(m) {
      window.Editor.eraserMode = m;
      prefs.eraserMode = m; savePrefs();
      $("#eraserPartial").classList.toggle("active", m === "partial");
      $("#eraserStroke").classList.toggle("active", m === "stroke");
    }
    $("#eraserPartial").addEventListener("click", function () { setEraserMode("partial"); });
    $("#eraserStroke").addEventListener("click", function () { setEraserMode("stroke"); });
    setEraserMode(prefs.eraserMode === "stroke" ? "stroke" : "partial");
    $("#eraserSize").addEventListener("input", function () {
      window.Editor.eraserSize = +this.value;
      $("#eraserSizeVal").textContent = this.value;
      prefs.eraserSize = +this.value; savePrefs();
      window.Editor.render();
    });

    // pen-tool actions (touch users have no Enter/Esc)
    $("#btnPenDone").addEventListener("click", function () { window.VecTools.penFinish(window.Editor, false); });
    $("#btnPenClose").addEventListener("click", function () { window.VecTools.penFinish(window.Editor, true); });
    $("#btnPenBack").addEventListener("click", function () { window.VecTools.penBack(window.Editor); });
    $("#btnPenCancel").addEventListener("click", function () { window.VecTools.penCancel(window.Editor); });

    // selection actions
    $("#btnDup").addEventListener("click", function () { window.VecTools.duplicate(window.Editor); });
    $("#btnFlipH").addEventListener("click", function () { window.VecTools.flip(window.Editor, "h"); });
    $("#btnFlipV").addEventListener("click", function () { window.VecTools.flip(window.Editor, "v"); });
    $("#btnSmoothSel").addEventListener("click", function () { window.VecTools.smoothSel(window.Editor); });
    $("#btnSimplify").addEventListener("click", function () { window.VecTools.simplifySel(window.Editor); });
    $("#btnCopySel").addEventListener("click", function () {
      var n = window.VecTools.copy(window.Editor);
      if (n) { toast(n + " " + window.I18N.t("copied")); syncVecUI(); }
    });
    $("#btnPasteSel").addEventListener("click", function () { window.VecTools.paste(window.Editor); });
    $("#btnDelSel").addEventListener("click", function () { window.VecTools.deleteSel(window.Editor); });

    // node-editing actions
    $("#btnNodeType").addEventListener("click", function () { window.VecTools.toggleNodeType(window.Editor); });
    $("#btnNodeDel").addEventListener("click", function () { window.VecTools.deleteNode(window.Editor); });
    $("#btnReverse").addEventListener("click", function () { window.VecTools.reversePath(window.Editor); });
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
    document.querySelectorAll("#toolRail [data-tool]").forEach(function (b) {
      b.addEventListener("click", function () { setTool(b.dataset.tool); });
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
    $("#btnAnchors").addEventListener("click", function () {
      var on = !window.Editor.anchorMode;
      window.Editor.setAnchorMode(on);
      syncRail();
      syncOptionsBar();
      if (on) toast(window.I18N.t("anchorTip"));
    });
    $("#btnSVG").addEventListener("click", function () {
      if (!current) return;
      try { window.FontExport.downloadSVG(current); }
      catch (e) { alert(e.message); }
    });
    $("#btnSVGImport").addEventListener("click", function () {
      if (current) $("#svgFileInput").click();
    });
    $("#svgFileInput").addEventListener("change", function () {
      if (!this.files.length || !current) return;
      var reader = new FileReader();
      reader.onload = function () {
        try {
          var res = window.SVGImport.parse(reader.result);
          if (!res.strokes.length) { alert(window.I18N.t("svgEmpty")); return; }
          window.Editor.addStrokes(res.strokes);
          toast(res.strokes.length + " " + window.I18N.t("svgImported"));
        } catch (e) {
          alert("SVG import failed: " + e.message);
        }
      };
      reader.readAsText(this.files[0]);
      this.value = "";
    });

    // guide font: trace over a different face (stays on this device)
    $("#btnGuideFont").addEventListener("click", function () {
      if (window.GuideFont && window.GuideFont.isCustom()) {
        window.GuideFont.reset();
        this.classList.remove("active");
        toast(window.I18N.t("guideFontReset"));
      } else {
        $("#guideFontInput").click();
      }
    });
    $("#guideFontInput").addEventListener("change", function () {
      if (!this.files.length) return;
      window.GuideFont.use(this.files[0]).then(function (name) {
        $("#btnGuideFont").classList.add("active");
        toast(window.I18N.t("guideFontSet") + " " + name);
      }).catch(function (e) {
        alert("Could not load that font: " + (e.message || e));
      });
      this.value = "";
    });

    // zoom
    $("#btnZoomIn").addEventListener("click", function () { window.Editor.zoomStep(1.25); });
    $("#btnZoomOut").addEventListener("click", function () { window.Editor.zoomStep(0.8); });
    $("#btnZoomReset").addEventListener("click", function () { window.Editor.resetView(); });
    window.Editor.onViewChange = function () {
      $("#zoomLabel").textContent = Math.round(window.Editor.zoom * 100) + "%";
    };

    // settings panel toggle (guides, ghost, SVG, project tools)
    $("#btnMoreTools").addEventListener("click", function () {
      var panel = $("#settingsPanel");
      panel.hidden = !panel.hidden;
      this.classList.toggle("active", !panel.hidden);
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
      var ed = window.Editor, vt = window.VecTools;
      var mod = e.metaKey || e.ctrlKey;
      var k = e.key.length === 1 ? e.key.toLowerCase() : e.key;

      // hold Space (or drag the middle mouse button) to pan
      if (e.key === " ") {
        if (!e.repeat) {
          ed.spacePan = true;
          $("#glyphCanvas").style.cursor = "grab";
        }
        e.preventDefault();
        return;
      }

      if (mod && k === "z" && !e.shiftKey) {
        e.preventDefault();
        // while a pen path is in progress, undo removes its last point
        if (ed.tool === "pen" && vt.penActive()) vt.penBack(ed);
        else ed.undo();
        return;
      }
      if (mod && (k === "y" || (k === "z" && e.shiftKey))) { e.preventDefault(); ed.redo(); return; }
      if (mod && k === "a") {
        if (ed.tool === "select") { e.preventDefault(); vt.selectAll(ed); }
        return;
      }
      if (mod && k === "c") {
        if (ed.tool === "select" && vt.hasSelection()) {
          e.preventDefault();
          var n = vt.copy(ed);
          if (n) { toast(n + " " + window.I18N.t("copied")); syncVecUI(); }
        }
        return;
      }
      if (mod && k === "x") {
        if (ed.tool === "select" && vt.hasSelection()) { e.preventDefault(); vt.cut(ed); }
        return;
      }
      if (mod && k === "v") {
        if (ed.clipboard.length) {
          e.preventDefault();
          if (ed.tool !== "select") setTool("select");
          vt.paste(ed);
        }
        return;
      }
      if (mod && k === "d") {
        if (ed.tool === "select" && vt.hasSelection()) { e.preventDefault(); vt.duplicate(ed); }
        return;
      }
      if (mod) return; // leave other browser shortcuts alone

      // Enter/Esc/Del/arrows go to the active vector tool first
      if (ed.isVecTool() && vt.key(e, ed)) { e.preventDefault(); syncVecUI(); return; }

      if (k === "[") step(-1);
      else if (k === "]") step(1);
      else if (k === "n") nextUndrawn();
      else if (k === "v") setTool("select");
      else if (k === "d") setTool("direct");
      else if (k === "b") setTool("brush");
      else if (k === "p") setTool("pen");
      else if (k === "l") setTool("line");
      else if (k === "m") setTool("rect");
      else if (k === "o") setTool("circle");
      else if (k === "e") setTool("eraser");
      else if (k === "a") $("#btnAnchors").click();
      else if (k === "+" || k === "=") ed.zoomStep(1.25);
      else if (k === "-") ed.zoomStep(0.8);
      else if (k === "0") ed.resetView();
      else if (k === "f") $("#btnFocus").click();
      else if (e.key === "Escape" && document.body.classList.contains("focus")) $("#btnFocus").click();
    });
    document.addEventListener("keyup", function (e) {
      if (e.key === " ") {
        window.Editor.spacePan = false;
        syncRail(); // restores the tool cursor
      }
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
    window.Editor.snapEnabled = !!prefs.snap;
    window.Editor.fillShape = !!prefs.fillShape;
    window.Editor.eraserMode = prefs.eraserMode === "stroke" ? "stroke" : "partial";
    window.Editor.eraserSize = prefs.eraserSize || 60;
    $("#penWidth").value = prefs.penWidth;
    $("#penWidthVal").textContent = prefs.penWidth;
    $("#stabilizer").value = prefs.stabilizer;
    $("#guideOpacity").value = prefs.guideOpacity;
    $("#guideSize").value = prefs.guideSize;
    $("#pressureToggle").checked = prefs.pressure;
    $("#touchDraws").checked = prefs.touchDraws;
    $("#snapToggle").checked = !!prefs.snap;
    $("#fillShape").checked = !!prefs.fillShape;
    $("#eraserSize").value = window.Editor.eraserSize;
    $("#eraserSizeVal").textContent = window.Editor.eraserSize;

    buildBrowser();
    wireDrawer();
    wireMobile();
    wireToolbar();
    wireProject();
    wirePreview();
    applyTheme();
    applyLang();
    $("#fontName").value = window.Store.meta.fontName;
    $("#authorName").value = window.Store.meta.author;
    $("#previewText").textContent = $("#previewInput").value;
    selectGlyph(window.GLYPHS[0]);
    var TOOLS = ["select", "direct", "brush", "pen", "line", "rect", "circle", "eraser"];
    window.Editor.tool = TOOLS.indexOf(prefs.tool) >= 0 ? prefs.tool : "brush";
    syncRail();
    syncOptionsBar();
    syncVecUI();
    window.Editor.resetView();
    schedulePreview();

    // The guide face must be fetched before the canvas paints — a canvas
    // font string alone does not trigger a webfont download.
    if (window.GuideFont) {
      window.GuideFont.restore()
        .then(function (name) {
          if (name) $("#btnGuideFont").classList.add("active");
          return window.GuideFont.warmUp();
        })
        .then(function () {
          window.Editor.render();
          if (!window.Editor.guideShapesStacks()) {
            toast(window.I18N.t("guideNoShape"));
          }
        });
    }
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(function () { window.Editor.render(); });
    }

    // PWA: offline support + add-to-home-screen on tablets
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("sw.js").catch(function () { /* http or unsupported — fine */ });
    }
  });
})();
