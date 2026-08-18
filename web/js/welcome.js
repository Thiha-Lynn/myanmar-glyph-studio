/* First-visit welcome screen.
 *
 * The site's front door used to be the drawing canvas itself: a first-time
 * visitor landed inside a professional glyph editor with no explanation of
 * what the project is, what it produces, or that seven other pages exist.
 * This overlay is the missing home screen — shown once, over the live app
 * (the studio behind the blur is its own screenshot), with the pitch in
 * both languages and every page of the site one tap away.
 *
 * It deliberately never appears where it would be noise:
 *   - inside the desktop/mobile app shells (they installed it; they know),
 *   - on a #g= deep link (the link IS the destination),
 *   - for anyone with drawn glyphs in the autosave (they found the studio
 *     long before this screen existed — do not greet them),
 *   - after it has been seen once. The က brand mark reopens it any time.
 *
 * Page list and icons come from sitenav.js (window.SiteNav) — one list,
 * or they drift.
 */
(function () {
  "use strict";

  var SEEN_KEY = "mgs-welcome-seen";
  var STORE_KEY = "mm-glyph-studio-v1";   // store.js STORAGE_KEY

  function inAppShell() {
    // The desktop shell serves over its private app:// scheme and the
    // mobile shells inject window.Capacitor. Do NOT sniff "Electron" in
    // the user agent: plenty of ordinary embedded browsers carry it, and
    // they are exactly the first-time visitors this screen is for.
    return !!window.Capacitor || location.protocol === "app:";
  }

  function hasDrawnWork() {
    try {
      var raw = localStorage.getItem(STORE_KEY);
      if (!raw) return false;
      var data = JSON.parse(raw);
      var glyphs = data && data.glyphs;
      if (!glyphs) return false;
      for (var name in glyphs) {
        var g = glyphs[name];
        if (g && g.strokes && g.strokes.length) return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  function markSeen() {
    try { localStorage.setItem(SEEN_KEY, "1"); } catch (e) { /* private mode */ }
  }

  function seen() {
    try { return localStorage.getItem(SEEN_KEY) === "1"; } catch (e) { return true; }
  }

  var CSS =
    '.welcome-backdrop{position:fixed;inset:0;z-index:200;display:flex;' +
    'align-items:center;justify-content:center;padding:1rem;' +
    'background:rgba(18,14,11,.72);' +
    'background:color-mix(in srgb,var(--bg,#1d1713) 72%,transparent);' +
    '-webkit-backdrop-filter:blur(9px);backdrop-filter:blur(9px);' +
    'overflow-y:auto;overscroll-behavior:contain}' +
    '.welcome-panel{background:var(--surface,#27201a);color:var(--ink,#ede3d2);' +
    'border:1px solid var(--line,#3a3128);border-radius:16px;' +
    'max-width:34rem;width:100%;margin:auto;padding:1.6rem 1.5rem 1.3rem;' +
    'box-shadow:0 24px 70px rgba(0,0,0,.45)}' +
    '.welcome-brand{display:flex;align-items:center;gap:.8rem;margin:0 0 .9rem}' +
    '.welcome-mark{font-size:2.3rem;line-height:1;color:var(--accent,#a8352f)}' +
    '.welcome-brand h2{margin:0;font-size:1.3rem;line-height:1.2}' +
    '.welcome-brand p{margin:.15rem 0 0;font-size:.86rem;color:var(--muted,#a79885)}' +
    '.welcome-sample{font-size:1.7rem;line-height:1.9;text-align:center;' +
    'margin:.2rem 0 .9rem;padding:.55rem .4rem .7rem;border-radius:12px;' +
    'background:var(--surface-2,#302821);overflow-x:auto;white-space:nowrap}' +
    '.welcome-pitch{margin:0 0 1rem;padding:0;list-style:none;display:grid;gap:.5rem}' +
    '.welcome-pitch li{font-size:.92rem;line-height:1.45;padding-left:1.15rem;position:relative}' +
    '.welcome-pitch li::before{content:"✓";position:absolute;left:0;' +
    'color:var(--good,#3e7048);font-weight:700}' +
    '.welcome-pitch .my{display:block;font-size:.84rem;color:var(--muted,#a79885)}' +
    '.welcome-cta{display:flex;gap:.6rem;flex-wrap:wrap;margin:0 0 1.1rem}' +
    '.welcome-cta .btn{flex:1 1 12rem;min-height:46px;font-size:1rem;' +
    'display:inline-flex;align-items:center;justify-content:center;gap:.5rem}' +
    '.welcome-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(10.5rem,1fr));' +
    'gap:.3rem;margin:0 0 .9rem}' +
    '.welcome-grid a{display:flex;align-items:center;gap:.55rem;padding:.5rem .6rem;' +
    'border-radius:9px;text-decoration:none;color:inherit;font-size:.9rem;' +
    'min-height:44px;background:transparent}' +
    '.welcome-grid a:hover{background:var(--surface-2,#302821)}' +
    '.welcome-grid svg{color:var(--accent,#a8352f);flex:none}' +
    '.welcome-grid .my{display:block;font-size:.74rem;color:var(--muted,#a79885)}' +
    '.welcome-foot{font-size:.78rem;color:var(--muted,#a79885);margin:0;' +
    'border-top:1px solid var(--line,#3a3128);padding-top:.75rem}' +
    '.welcome-foot a{color:inherit}' +
    '.brand{cursor:pointer}' +
    '@media (max-width:480px){.welcome-panel{padding:1.2rem 1rem 1rem}' +
    '.welcome-sample{font-size:1.35rem}}' +
    '@media (prefers-reduced-motion:no-preference){' +
    '.welcome-panel{animation:welcomeIn .28s ease-out}' +
    '@keyframes welcomeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1}}}';

  function pageGrid() {
    var nav = window.SiteNav;
    if (!nav) return "";
    return nav.PAGES.filter(function (p) {
      return p.file !== "index.html";
    }).map(function (p) {
      var external = p.file.indexOf("http") === 0;
      return '<a href="' + p.file + '"' + (external ? ' rel="noopener"' : "") + ">" +
        nav.svg(p.icon) +
        "<span>" + p.en + '<span class="my">' + p.my + "</span></span></a>";
    }).join("");
  }

  var backdrop = null;

  function close() {
    markSeen();
    if (backdrop && backdrop.parentNode) backdrop.parentNode.removeChild(backdrop);
    backdrop = null;
    document.removeEventListener("keydown", onKey);
  }

  function onKey(e) {
    if (e.key === "Escape") close();
  }

  function show() {
    if (backdrop) return;
    if (!document.getElementById("welcome-css")) {
      var style = document.createElement("style");
      style.id = "welcome-css";
      style.textContent = CSS;
      document.head.appendChild(style);
    }

    backdrop = document.createElement("div");
    backdrop.className = "welcome-backdrop";
    backdrop.innerHTML =
      '<div class="welcome-panel" role="dialog" aria-modal="true" ' +
      'aria-label="Welcome to Myanmar Glyph Studio" tabindex="-1">' +
      '<div class="welcome-brand">' +
      '<span class="welcome-mark mm" aria-hidden="true">က</span>' +
      "<div><h2>Myanmar Glyph Studio</h2>" +
      '<p><span class="mm">မိမိစိတ်ကြိုက် ဖောင့်ရေးဆွဲပါ</span> · draw your own Myanmar font</p>' +
      "</div></div>" +
      '<div class="welcome-sample mm" aria-hidden="true">ကြီး မြို့ ကျွန်ုပ် စက္ကူ ရွှံ့ နွေဦး</div>' +
      '<ul class="welcome-pitch">' +
      "<li>Trace ≈150 glyph parts over dimmed guides — phone, tablet with a stylus, or desktop, fully offline." +
      '<span class="my mm">ဖုန်း၊ တက်ဘလက် သို့မဟုတ် ကွန်ပျူတာဖြင့် အရိပ်ပုံပေါ် လိုက်ရေးဆွဲပါ — အင်တာနက် မလိုပါ</span></li>' +
      "<li>The hard part is automatic: OpenType shaping, mark anchors and a real installable TTF are generated for you." +
      '<span class="my mm">ခက်ခဲသော OpenType အပိုင်းကို ကိရိယာက အလိုအလျောက် ပြုလုပ်ပြီး တပ်ဆင်နိုင်သော TTF ဖောင့် ထုတ်ပေးပါသည်</span></li>' +
      "<li>Everything you make is yours, under the SIL Open Font License — free for the whole community, forever." +
      '<span class="my mm">သင်ဖန်တီးသမျှ ဖောင့်အားလုံး SIL OFL ဖြင့် ထာဝရ အခမဲ့ဖြစ်သည်</span></li>' +
      "</ul>" +
      '<div class="welcome-cta">' +
      '<button type="button" class="btn primary" id="welcomeStart">✏️ Start drawing · <span class="mm">စတင်ရေးဆွဲမည်</span></button>' +
      '<a class="btn" href="gallery.html" id="welcomeGallery">See finished fonts · <span class="mm">ဖောင့်ပြခန်း</span></a>' +
      "</div>" +
      '<nav class="welcome-grid" aria-label="All pages">' + pageGrid() + "</nav>" +
      '<p class="welcome-foot">Installs as an app on any device and works offline · ' +
      '<a href="https://github.com/Thiha-Lynn/myanmar-glyph-studio" rel="noopener">open source (MIT + OFL)</a></p>' +
      "</div>";

    document.body.appendChild(backdrop);

    backdrop.addEventListener("click", function (e) {
      if (e.target === backdrop) close();
    });
    backdrop.querySelector("#welcomeStart").addEventListener("click", close);
    // Navigating away counts as having seen it — otherwise Back greets again.
    backdrop.addEventListener("click", function (e) {
      if (e.target.closest && e.target.closest("a")) markSeen();
    });
    document.addEventListener("keydown", onKey);
    backdrop.querySelector(".welcome-panel").focus();
  }

  function init() {
    // The brand mark reopens the welcome any time, on every visit.
    var brand = document.querySelector(".brand");
    if (brand) {
      brand.setAttribute("title", "About this project / အကြောင်း");
      brand.addEventListener("click", show);
    }

    if (inAppShell()) return;
    // app.js writes #g=<glyph> into the hash at boot, so the CURRENT hash
    // says nothing about how the visitor arrived. index.html captures the
    // landing hash before any app script runs; missing capture = be quiet.
    var landing = window.__mgsLandingHash;
    if (typeof landing !== "string") landing = location.hash;
    if (landing) return;                // deep links go straight to work
    if (seen()) return;
    if (hasDrawnWork()) { markSeen(); return; }
    show();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
