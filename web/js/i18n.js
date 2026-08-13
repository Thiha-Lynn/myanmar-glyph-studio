/*
 * Tiny two-language UI dictionary (English / Burmese).
 *
 * Elements opt in with data-i18n="key" (textContent),
 * data-i18n-title="key" (title tooltip) or data-i18n-ph="key" (placeholder).
 * Glyph hints carry their own translations in data/glyphs.js.
 */
(function () {
  "use strict";

  var STRINGS = {
    pen:            { en: "Pen",            my: "ဘောပင်" },
    line:           { en: "Line",           my: "မျဉ်း" },
    circle:         { en: "Circle",         my: "စက်ဝိုင်း" },
    erase:          { en: "Erase",          my: "ဖျက်" },
    clear:          { en: "Clear",          my: "အကုန်ဖျက်" },
    // tool rail tooltips
    toolSelect:     { en: "Select & transform (V)",           my: "ရွေး၍ ရွှေ့/ချဲ့/လှည့် (V)" },
    toolDirect:     { en: "Edit points (D)",                  my: "အမှတ်များ ပြင်ရန် (D)" },
    toolBrush:      { en: "Brush — freehand (B)",             my: "စုတ်တံ — လက်ဖြင့်ဆွဲ (B)" },
    toolPen:        { en: "Pen — click points, drag curves (P)", my: "ပင် — အမှတ်နှိပ်၊ ဆွဲ၍ကွေး (P)" },
    toolLine:       { en: "Line (L)",                         my: "မျဉ်း (L)" },
    toolRect:       { en: "Rectangle (M)",                    my: "စတုဂံ (M)" },
    toolCircle:     { en: "Circle — drag from center (O)",    my: "စက်ဝိုင်း — အလယ်မှဆွဲ (O)" },
    toolEraser:     { en: "Eraser (E)",                       my: "ခဲဖျက် (E)" },
    toolAnchors:    { en: "Anchor mode (A)",                  my: "ချိတ်မှတ် (A)" },
    // contextual options
    fillShape:      { en: "Fill",           my: "အပြည့်" },
    snap:           { en: "Snap",           my: "ကွက်ချိတ်" },
    done:           { en: "Done",           my: "ပြီးပြီ" },
    closePath:      { en: "Close",          my: "ပိတ်" },
    duplicate:      { en: "Duplicate",      my: "ပုံတူ" },
    smoothSel:      { en: "Smooth",         my: "ချော" },
    simplify:       { en: "Simplify",       my: "ရိုးရှင်း" },
    copy:           { en: "Copy",           my: "ကူး" },
    paste:          { en: "Paste",          my: "ကပ်" },
    copied:         { en: "stroke(s) copied — switch glyph and Paste to reuse them",
                      my: "မျဉ်းကူးပြီး — အက္ခရာပြောင်း၍ “ကပ်” နှိပ်ပါ" },
    cornerSmooth:   { en: "Corner/Smooth",  my: "ထောင့်/ချော" },
    deleteNode:     { en: "Delete point",   my: "အမှတ်ဖျက်" },
    reverse:        { en: "Reverse",        my: "ပြောင်းပြန်" },
    eraserPartial:  { en: "Partial",        my: "တစ်ပိုင်း" },
    eraserStroke:   { en: "Whole",          my: "တစ်ချောင်းလုံး" },
    eraserSize:     { en: "Size",           my: "အရွယ်" },
    selected:       { en: "selected",       my: "ခု ရွေးထား" },
    penHint:        { en: "click: corner · drag: curve · click the first point to close",
                      my: "နှိပ် — ထောင့် · ဆွဲ — ကွေး · ပထမအမှတ်ကိုနှိပ်၍ ပိတ်ပါ" },
    selectHint:     { en: "drag a box to select · handles scale, knob rotates",
                      my: "ဘောင်ဆွဲ၍ရွေးပါ · ထောင့်များဖြင့်ချဲ့၊ အလုံးဖြင့်လှည့်ပါ" },
    directHint:     { en: "click a path, drag its points · double-click the path to add a point",
                      my: "မျဉ်းကိုနှိပ်၍ အမှတ်များကိုဆွဲပါ · မျဉ်းပေါ် နှစ်ချက်နှိပ်၍ အမှတ်ထည့်ပါ" },
    anchorTipShort: { en: "drag the anchor points · double-click one to reset it",
                      my: "ချိတ်မှတ်များကိုဆွဲပါ · ပြန်ချိန်ရန် နှစ်ချက်နှိပ်ပါ" },
    save:           { en: "Save",           my: "သိမ်း" },
    load:           { en: "Load",           my: "ဖွင့်" },
    exportFont:     { en: "Export font",    my: "ဖောင့်ထုတ်" },
    help:           { en: "Help",           my: "အကူအညီ" },
    fontName:       { en: "Font name",      my: "ဖောင့်အမည်" },
    yourName:       { en: "Your name",      my: "သင့်အမည်" },
    yourNamePh:     { en: "for the OFL credit", my: "OFL မှတ်တမ်းအတွက်" },
    testDrive:      { en: "Test drive",     my: "စမ်းရေးကြည့်" },
    penW:           { en: "Width",          my: "အထူ" },
    brush:          { en: "Brush",          my: "စုတ်တံ" },
    steady:         { en: "Steady",         my: "တည်ငြိမ်" },
    guide:          { en: "Guide",          my: "လမ်းညွှန်" },
    size:           { en: "Size",           my: "အရွယ်" },
    penPressure:    { en: "Pen pressure",   my: "ပင်ဖိအား" },
    fingerDraws:    { en: "Finger draws",   my: "လက်ဖြင့်ဆွဲ" },
    fillPreview:    { en: "Fill preview",   my: "အပြည့်ပြ" },
    advance:        { en: "Advance",        my: "အကျယ်" },
    ghost:          { en: "Ghost",          my: "အရိပ်" },
    ghostNone:      { en: "no ghost",       my: "အရိပ်မပြ" },
    copyFrom:       { en: "Copy from…",     my: "ကူးယူရန်…" },
    center:         { en: "Center",         my: "ဗဟိုချ" },
    anchors:        { en: "Anchors",        my: "ချိတ်မှတ်" },
    anchorTip:      { en: "Drag the anchor points where marks should attach. Double-click one to reset it; press ⚓ again to draw.",
                      my: "သင်္ကေတတွဲမည့် ချိတ်မှတ်များကို ဆွဲရွှေ့ပါ။ ပြန်ချိန်ရန် နှစ်ချက်နှိပ်ပါ။ ပြန်ရေးဆွဲရန် ⚓ ကို ထပ်နှိပ်ပါ။" },
    svg:            { en: "SVG",            my: "SVG" },
    menu:           { en: "Project menu",   my: "မီနူး" },
    install:        { en: "Install",        my: "ထည့်သွင်း" },
    installPrompt:  { en: "Install the studio for offline drawing.",
                      my: "အင်တာနက်မလိုဘဲ ရေးဆွဲရန် ထည့်သွင်းပါ။" },
    installIOS:     { en: "Add to Home Screen: tap Share, then “Add to Home Screen”.",
                      my: "Share → “Add to Home Screen” နှိပ်၍ ထည့်သွင်းပါ။" },
    project:        { en: "Project",        my: "ပရောဂျက်" },
    guideFont:      { en: "Guide font",     my: "လမ်းညွှန်ဖောင့်" },
    guideFontSet:   { en: "Guides now trace",  my: "လမ်းညွှန်ဖောင့် —" },
    guideFontReset: { en: "Back to the built-in Padauk guides.",
                      my: "မူလ Padauk လမ်းညွှန်သို့ ပြန်သွားပြီ။" },
    guideNoShape:   { en: "Guides may be inaccurate — this device could not load the built-in Padauk guide font.",
                      my: "လမ်းညွှန်များ မမှန်နိုင်ပါ — Padauk ဖောင့် ဖွင့်၍မရပါ။" },
    importSvg:      { en: "Import SVG",     my: "SVG သွင်း" },
    svgImported:    { en: "outlines imported — Center or redraw to adjust.",
                      my: "မျဉ်းကွက်များ သွင်းပြီး — နေရာချရန် Center သုံးပါ။" },
    svgEmpty:       { en: "No drawable outlines found in that SVG.",
                      my: "ထို SVG တွင် သွင်းယူနိုင်သော မျဉ်းကွက် မတွေ့ပါ။" },
    nextUndrawn:    { en: "Next empty",     my: "နောက်အလွတ်" },
    drawnOf:        { en: "glyphs drawn",   my: "လုံး ဆွဲပြီး" },
    canvasTip:      { en: "Two fingers: pan & zoom · wheel: zoom", my: "လက်နှစ်ချောင်း — ရွှေ့/ချဲ့ · wheel — ချဲ့" },
    presets:        { en: "Try:",           my: "စမ်းရန်—" },
    unencoded:      { en: "unencoded variant", my: "ကုဒ်မဲ့ ပုံစံကွဲ" },
    noCircleNote:   { en: "(do not draw the dotted circle)", my: "(စက်ဝိုင်းအစက်ကို မဆွဲပါနှင့်)" },
    // share a single glyph as a text snippet (contributions without Git)
    glyphCopy:      { en: "Copy glyph",      my: "အက္ခရာကူး" },
    glyphPaste:     { en: "Paste glyph",     my: "အက္ခရာကပ်" },
    glyphCopied:    { en: "Glyph copied as text — paste it into an issue, a chat, or another studio.",
                      my: "အက္ခရာကို စာသားအဖြစ် ကူးပြီး — issue/chat ထဲ သို့မဟုတ် studio ထဲ ပြန်ကပ်နိုင်ပါတယ်။" },
    glyphEmpty:     { en: "Nothing drawn on this glyph yet.",
                      my: "ဒီအက္ခရာမှာ ဘာမှ မရေးဆွဲရသေးပါ။" },
    glyphCopyManual: { en: "Copy this text:", my: "ဒီစာသားကို ကူးယူပါ —" },
    glyphPastePrompt: { en: "Paste the glyph snippet:", my: "အက္ခရာစာသားကို ကပ်ထည့်ပါ —" },
    glyphPasteMismatch: { en: "This snippet is for a different glyph. Paste anyway?",
                      my: "ဒီစာသားက အခြားအက္ခရာအတွက်ပါ။ ဆက်ကပ်မလား?" },
    glyphPasted:    { en: "strokes pasted", my: "မျဉ်း ကပ်ပြီးပါပြီ" }
  };

  var lang = "en";

  /*
   * Community languages (Mon, Shan, S'gaw Karen, …) register themselves
   * from web/js/lang/<code>.js — see docs/TRANSLATING.md. Missing keys
   * fall back to English, so a partial translation is already useful.
   */
  var EXTRA = {};          // code -> {name, button, strings:{key:text}}
  var ORDER = ["en", "my"];

  function t(key) {
    if (EXTRA[lang] && EXTRA[lang].strings &&
        EXTRA[lang].strings[key] != null) {
      return EXTRA[lang].strings[key];
    }
    var row = STRINGS[key];
    if (!row) return key;
    return row[lang] != null ? row[lang] : row.en;
  }

  function apply() {
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      el.textContent = t(el.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-title]").forEach(function (el) {
      el.title = t(el.dataset.i18nTitle);
    });
    document.querySelectorAll("[data-i18n-ph]").forEach(function (el) {
      el.placeholder = t(el.dataset.i18nPh);
    });
    document.documentElement.lang = lang;
  }

  window.I18N = {
    t: t,
    apply: apply,
    get lang() { return lang; },
    set: function (l) {
      lang = (l === "en" || l === "my" || EXTRA[l]) ? l : "en";
      apply();
    },

    /* I18N.register("mnw", {name:"Mon", button:"မန်", strings:{…}}) */
    register: function (code, meta) {
      if (!code || !meta || !meta.strings) return;
      EXTRA[code] = meta;
      if (ORDER.indexOf(code) < 0) ORDER.push(code);
    },

    /* Every registered language, in cycle order, with its button label. */
    available: function () {
      return ORDER.map(function (code) {
        return {
          code: code,
          button: code === "en" ? "En"
                : code === "my" ? "မြ"
                : (EXTRA[code].button || code),
          name: code === "en" ? "English"
              : code === "my" ? "မြန်မာ"
              : (EXTRA[code].name || code)
        };
      });
    }
  };
})();
