/*
 * Glyph inventory for the Myanmar Glyph Studio.
 *
 * Each entry:
 *   name  – production glyph name (used in the UFO pipeline)
 *   cp    – Unicode codepoint, or null for unencoded variant glyphs
 *   label – short text shown on the glyph chip in the sidebar
 *   guide – string rendered dimmed underneath the drawing canvas
 *   hint  – one-line instruction for the contributor
 *   mark  – true when the glyph is a combining mark (guide shows a dotted
 *           circle; draw only the mark itself, never the circle)
 *   group – section key, see GLYPH_GROUPS below
 *
 * The base set covers the full Burmese portion of the Myanmar Unicode block
 * (U+1000–104F). The "variants" group holds the unencoded forms a real
 * shaping-capable font needs (subjoined consonants, kinzi, contextual
 * variants). Extend this file to add Mon / Shan / Karen coverage.
 */
(function () {
  "use strict";

  var DOTTED = "◌"; // ◌ dotted circle, the standard mark carrier

  var CONSONANTS = [
    [0x1000, "ka"], [0x1001, "kha"], [0x1002, "ga"], [0x1003, "gha"],
    [0x1004, "nga"], [0x1005, "ca"], [0x1006, "cha"], [0x1007, "ja"],
    [0x1008, "jha"], [0x1009, "nya"], [0x100a, "nnya"], [0x100b, "tta"],
    [0x100c, "ttha"], [0x100d, "dda"], [0x100e, "ddha"], [0x100f, "nna"],
    [0x1010, "ta"], [0x1011, "tha"], [0x1012, "da"], [0x1013, "dha"],
    [0x1014, "na"], [0x1015, "pa"], [0x1016, "pha"], [0x1017, "ba"],
    [0x1018, "bha"], [0x1019, "ma"], [0x101a, "ya"], [0x101b, "ra"],
    [0x101c, "la"], [0x101d, "wa"], [0x101e, "sa"], [0x101f, "ha"],
    [0x1020, "lla"], [0x1021, "a"]
  ];

  var INDEPENDENT_VOWELS = [
    [0x1023, "i.indep"], [0x1024, "ii.indep"], [0x1025, "u.indep"],
    [0x1026, "uu.indep"], [0x1027, "e.indep"], [0x1029, "o.indep"],
    [0x102a, "au.indep"]
  ];

  // [cp, name, isMark, hint]
  var DEPENDENT_SIGNS = [
    [0x102b, "tallAa", false, "Tall AA vowel sign (spacing, sits to the right)"],
    [0x102c, "aa", false, "AA vowel sign (spacing, sits to the right)"],
    [0x102d, "i", true, "I vowel — draw above the dotted circle only"],
    [0x102e, "ii", true, "II vowel — draw above the dotted circle only"],
    [0x102f, "u", true, "U vowel — draw below the dotted circle only"],
    [0x1030, "uu", true, "UU vowel — draw below the dotted circle only"],
    [0x1031, "e", false, "E vowel — rendered before the consonant"],
    [0x1032, "ai", true, "AI vowel — draw above the dotted circle only"],
    [0x1036, "anusvara", true, "Anusvara — small circle above"],
    [0x1037, "dotBelow", true, "Dot below (creaky tone)"],
    [0x1038, "visarga", false, "Visarga း (two dots, spacing)"],
    [0x103a, "asat", true, "Asat killer stroke — draw above only"]
  ];

  var MEDIALS = [
    [0x103b, "medialYa", "Medial YA ျ — hooks to the right of the base"],
    [0x103c, "medialRa", "Medial RA ြ — wraps around the base (narrow form)"],
    [0x103d, "medialWa", "Medial WA ွ — small loop below the base"],
    [0x103e, "medialHa", "Medial HA ှ — hook below the base"]
  ];

  var DIGITS = [
    [0x1040, "zero"], [0x1041, "one"], [0x1042, "two"], [0x1043, "three"],
    [0x1044, "four"], [0x1045, "five"], [0x1046, "six"], [0x1047, "seven"],
    [0x1048, "eight"], [0x1049, "nine"]
  ];

  var PUNCTUATION = [
    [0x104a, "sectionMark", "Little section mark ၊ (comma-like pause)"],
    [0x104b, "section", "Section mark ။ (full stop)"],
    [0x104c, "locative", "Symbol ၌ (locative)"],
    [0x104d, "completed", "Symbol ၍ (completed)"],
    [0x104e, "aforementioned", "Symbol ၎ (aforementioned)"],
    [0x104f, "genitive", "Symbol ၏ (genitive)"],
    [0x103f, "greatSa", "Great SA ဿ"]
  ];

  function ch(cp) { return String.fromCodePoint(cp); }

  var glyphs = [];

  CONSONANTS.forEach(function (row) {
    glyphs.push({
      name: row[1] + "-myanmar", cp: row[0], label: ch(row[0]),
      guide: ch(row[0]), hint: "Base consonant " + ch(row[0]),
      mark: false, group: "consonants"
    });
  });

  INDEPENDENT_VOWELS.forEach(function (row) {
    glyphs.push({
      name: row[1] + "-myanmar", cp: row[0], label: ch(row[0]),
      guide: ch(row[0]), hint: "Independent vowel " + ch(row[0]),
      mark: false, group: "vowels"
    });
  });

  DEPENDENT_SIGNS.forEach(function (row) {
    glyphs.push({
      name: row[1] + "-myanmar", cp: row[0], label: DOTTED + ch(row[0]),
      guide: DOTTED + ch(row[0]), hint: row[3],
      mark: row[2], group: "signs"
    });
  });

  MEDIALS.forEach(function (row) {
    glyphs.push({
      name: row[1] + "-myanmar", cp: row[0], label: DOTTED + ch(row[0]),
      guide: DOTTED + ch(row[0]), hint: row[2],
      mark: true, group: "medials"
    });
  });

  DIGITS.forEach(function (row) {
    glyphs.push({
      name: row[1] + "-myanmar", cp: row[0], label: ch(row[0]),
      guide: ch(row[0]), hint: "Digit " + ch(row[0]),
      mark: false, group: "digits"
    });
  });

  PUNCTUATION.forEach(function (row) {
    glyphs.push({
      name: row[1] + "-myanmar", cp: row[0], label: ch(row[0]),
      guide: ch(row[0]), hint: row[2],
      mark: false, group: "punctuation"
    });
  });

  // ---- Unencoded variant glyphs required for real shaping -----------------
  // Subjoined (stacked) consonant forms: the guide shows the stack (e.g. က္က);
  // the contributor draws ONLY the lower, subjoined letter.
  var VIRAMA = ch(0x1039);
  CONSONANTS.forEach(function (row) {
    // ka..bha + ma + la are the forms that actually occur in stacks; we offer
    // all of them and mark rare ones in the hint.
    glyphs.push({
      name: row[1] + "-myanmar.sub", cp: null,
      label: ch(row[0]) + "̲", // letter + combining low line, chip only
      guide: ch(row[0]) + VIRAMA + ch(row[0]),
      hint: "Subjoined form — draw ONLY the small lower " + ch(row[0]) + " of the stack",
      mark: true, group: "variants"
    });
  });

  glyphs.push({
    name: "kinzi-myanmar", cp: null, label: ch(0x1004) + ch(0x103a) + ch(0x1039),
    guide: ch(0x1004) + ch(0x103a) + ch(0x1039) + ch(0x1000),
    hint: "Kinzi — draw ONLY the small mark above the base (from င်္က)",
    mark: true, group: "variants"
  });

  glyphs.push({
    name: "medialRa-myanmar.wide", cp: null, label: DOTTED + ch(0x103c) + "+",
    guide: ch(0x1019) + ch(0x103c),
    hint: "Wide medial RA — wraps a wide base like မ; draw only the RA wrap",
    mark: true, group: "variants"
  });

  glyphs.push({
    name: "u-myanmar.alt", cp: null, label: DOTTED + ch(0x102f) + "*",
    guide: ch(0x1014) + ch(0x102f),
    hint: "Short U variant — used when the base has a descender; draw only the vowel",
    mark: true, group: "variants"
  });

  glyphs.push({
    name: "uu-myanmar.alt", cp: null, label: DOTTED + ch(0x1030) + "*",
    guide: ch(0x1014) + ch(0x1030),
    hint: "Short UU variant — used when the base has a descender; draw only the vowel",
    mark: true, group: "variants"
  });

  window.GLYPH_GROUPS = [
    { key: "consonants", en: "Consonants", my: "ဗျည်း" },
    { key: "vowels", en: "Independent vowels", my: "သရ (လွတ်)" },
    { key: "signs", en: "Vowel signs & tones", my: "သရသင်္ကေတ" },
    { key: "medials", en: "Medials", my: "ဗျည်းတွဲ" },
    { key: "digits", en: "Digits", my: "ဂဏန်း" },
    { key: "punctuation", en: "Punctuation & symbols", my: "ပုဒ်ဖြတ်" },
    { key: "variants", en: "Shaping variants (advanced)", my: "ပုံစံကွဲ" }
  ];

  window.GLYPHS = glyphs;

  window.GLYPH_BY_NAME = {};
  glyphs.forEach(function (g) { window.GLYPH_BY_NAME[g.name] = g; });
})();
