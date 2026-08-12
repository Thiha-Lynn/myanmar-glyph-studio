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
    save:           { en: "Save",           my: "သိမ်း" },
    load:           { en: "Load",           my: "ဖွင့်" },
    exportFont:     { en: "Export font",    my: "ဖောင့်ထုတ်" },
    help:           { en: "Help",           my: "အကူအညီ" },
    fontName:       { en: "Font name",      my: "ဖောင့်အမည်" },
    yourName:       { en: "Your name",      my: "သင့်အမည်" },
    yourNamePh:     { en: "for the OFL credit", my: "OFL မှတ်တမ်းအတွက်" },
    testDrive:      { en: "Test drive",     my: "စမ်းရေးကြည့်" },
    penW:           { en: "Pen",            my: "အထူ" },
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
    svg:            { en: "SVG",            my: "SVG" },
    nextUndrawn:    { en: "Next empty",     my: "နောက်အလွတ်" },
    drawnOf:        { en: "glyphs drawn",   my: "လုံး ဆွဲပြီး" },
    canvasTip:      { en: "Two fingers: pan & zoom · wheel: zoom", my: "လက်နှစ်ချောင်း — ရွှေ့/ချဲ့ · wheel — ချဲ့" },
    presets:        { en: "Try:",           my: "စမ်းရန်—" },
    unencoded:      { en: "unencoded variant", my: "ကုဒ်မဲ့ ပုံစံကွဲ" },
    noCircleNote:   { en: "(do not draw the dotted circle)", my: "(စက်ဝိုင်းအစက်ကို မဆွဲပါနှင့်)" }
  };

  var lang = "en";

  function t(key) {
    var row = STRINGS[key];
    return row ? (row[lang] || row.en) : key;
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
    document.documentElement.lang = lang === "my" ? "my" : "en";
  }

  window.I18N = {
    t: t,
    apply: apply,
    get lang() { return lang; },
    set: function (l) { lang = l === "my" ? "my" : "en"; apply(); }
  };
})();
