/* Site navigation — one list, one set of icons, every page.
 *
 * Before this, each page hand-wrote its own nav. They drifted: the same
 * page was called "Rendering showcase" on three pages and "Measured
 * showcase" on a fourth, the link order differed everywhere, the nav sat
 * above the title on one page and below two paragraphs on another — and
 * devicetest.html was reachable from exactly one page in the whole site,
 * with no nav of its own to get back out.
 *
 * A shared component rather than seven copies, because the failure mode
 * of seven copies is exactly what happened. Adding a page here adds it
 * to every nav at once.
 *
 * Icons are inline SVG, not emoji: emoji render differently on every
 * platform (and several of the ones used here — ✦ 🖊 🫧 — fall back to
 * tofu or a wildly different picture depending on the font), which is a
 * poor look for a project about correct rendering. Reported by a reader,
 * Chan Nyein. They inherit currentColor and match the drawing tool rail:
 * 24×24 viewBox, fill none, stroke-width 1.6.
 *
 * Usage: put <nav data-sitenav></nav> where the nav belongs and load
 * this with defer. Pass data-sitenav="compact" for icon-only.
 */
(function () {
  "use strict";

  var ICONS = {
    studio: '<path d="M4 20l4.5-1L18 9.5 15.5 7 6 16.5 5 21z"/><path d="M14.5 8L17 10.5"/>',
    gallery: '<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="8.5" cy="10" r="1.5"/><path d="M21 15.5l-4.5-4.5-4 4-2-2L3.5 17"/>',
    showcase: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/>',
    specimen: '<path d="M12 3l2.1 5.4L19.5 10l-5.4 2.1L12 17.5l-2.1-5.4L4.5 10l5.4-1.6z"/>',
    styles: '<path d="M12 3c-4.9 0-9 3.6-9 8.2 0 4.5 3.6 7.8 8 7.8 1.4 0 2.4-.9 2.4-2 0-1-.6-1.6-.6-2.4 0-.9.7-1.5 1.7-1.5H16c3 0 5-2 5-5C21 5.9 17 3 12 3z"/><circle cx="7.5" cy="11" r="1"/><circle cx="11" cy="7.5" r="1"/><circle cx="15.5" cy="8.5" r="1"/>',
    book: '<path d="M4 5.5C4 4.7 4.7 4 5.5 4H10a2 2 0 012 2v13a2 2 0 00-2-1.6H5.5A1.5 1.5 0 014 16z"/><path d="M20 5.5c0-.8-.7-1.5-1.5-1.5H14a2 2 0 00-2 2v13a2 2 0 012-1.6h4.5a1.5 1.5 0 001.5-1.4z"/>',
    devicetest: '<rect x="7" y="2.5" width="10" height="19" rx="2.2"/><path d="M10.5 18.5h3"/>',
    contribute: '<path d="M12 20.5s-7.2-4.3-7.2-9.4A4.1 4.1 0 0112 8.6a4.1 4.1 0 017.2 2.5c0 5.1-7.2 9.4-7.2 9.4z"/>',
    source: '<path d="M9.5 8.5L5.5 12l4 3.5"/><path d="M14.5 8.5l4 3.5-4 3.5"/>'
  };

  // Order is deliberate: draw first, then look at what came out, then the
  // proofs, then the source. Burmese labels carry in the tooltip because
  // the row has to stay one line on a phone.
  var PAGES = [
    { file: "index.html", icon: "studio", en: "Studio", my: "ရေးဆွဲရန်" },
    { file: "gallery.html", icon: "gallery", en: "Font gallery", my: "ဖောင့်ပြခန်း" },
    { file: "specimen.html", icon: "specimen", en: "Type specimen", my: "စာလုံးပုံစံ" },
    { file: "styles.html", icon: "styles", en: "Font styles", my: "ဖောင့်စတိုင်များ" },
    { file: "showcase.html", icon: "showcase", en: "Rendering showcase", my: "ရေးသားပြသချက်" },
    { file: "book.html", icon: "book", en: "Reading proof", my: "စာအုပ်ဖြင့် စမ်းသပ်ချက်" },
    { file: "devicetest.html", icon: "devicetest", en: "Device test", my: "ဖုန်းပေါ်တွင် စမ်းရန်" },
    { file: "contribute.html", icon: "contribute", en: "Contribute", my: "လက်တွဲပါ" },
    { file: "https://github.com/Thiha-Lynn/myanmar-glyph-studio", icon: "source", en: "Source", my: "ကုဒ်" }
  ];

  var CSS =
    '.sitenav{display:flex;flex-wrap:wrap;gap:.15rem .1rem;align-items:center;' +
    'margin:.85rem 0 0;font-size:.92rem;-webkit-overflow-scrolling:touch}' +
    '.sitenav a{display:inline-flex;align-items:center;gap:.4rem;' +
    'padding:.42rem .6rem;border-radius:8px;text-decoration:none;color:inherit;' +
    'opacity:.72;white-space:nowrap;line-height:1;touch-action:manipulation}' +
    '.sitenav a:hover{opacity:1;background:rgba(128,128,128,.14)}' +
    '.sitenav a[aria-current="page"]{opacity:1;font-weight:600;' +
    'background:rgba(128,128,128,.16)}' +
    '.sitenav a[aria-current="page"] svg{color:var(--accent,#a8352f)}' +
    '.sitenav svg{display:block;flex:none}' +
    '.sitenav-compact a{padding:.42rem}' +
    /* Phones: one sideways-scrolling row rather than a wrapped block that
       pushes the actual page content below the fold. */
    '@media (max-width:640px){.sitenav{flex-wrap:nowrap;overflow-x:auto;' +
    'gap:0;margin-top:.6rem;padding-bottom:.2rem}' +
    '.sitenav::-webkit-scrollbar{display:none}' +
    '.sitenav a{font-size:.86rem;padding:.5rem .5rem}}' +
    '@media (pointer:coarse){.sitenav a{min-height:44px}}';

  function svg(name) {
    return '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" ' +
      'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" ' +
      'stroke-linejoin="round" aria-hidden="true">' + ICONS[name] + '</svg>';
  }

  function currentFile() {
    var path = location.pathname.replace(/\/+$/, "");
    var file = path.slice(path.lastIndexOf("/") + 1);
    return file || "index.html";   // "/" and "/index.html" are the same page
  }

  var HIDDEN = 'style="position:absolute;width:1px;height:1px;' +
    'overflow:hidden;clip:rect(0 0 0 0)"';

  function render(host) {
    var here = currentFile();
    var mode = host.getAttribute("data-sitenav") || "";
    // "toolbar" borrows the app's own button classes so these sit in the
    // studio's header without looking like a second design system.
    var toolbar = mode === "toolbar";
    var compact = toolbar || mode === "compact";

    if (!toolbar) {
      host.className = "sitenav" + (compact ? " sitenav-compact" : "");
    }
    host.setAttribute("aria-label", "Site sections");

    host.innerHTML = PAGES.map(function (p) {
      var external = p.file.indexOf("http") === 0;
      var isHere = !external && p.file === here;
      // In the studio's own toolbar a link back to the studio is noise.
      if (toolbar && isHere) return "";
      return '<a href="' + p.file + '"' +
        (toolbar ? ' class="btn icon-btn"' : "") +
        (external ? ' rel="noopener"' : "") +
        (isHere ? ' aria-current="page"' : "") +
        ' title="' + p.en + " · " + p.my + '">' + svg(p.icon) +
        (compact ? '<span ' + HIDDEN + '>' + p.en + '</span>'
                 : '<span>' + p.en + '</span>') +
        '</a>';
    }).join("");
  }

  function init() {
    var hosts = document.querySelectorAll("[data-sitenav]");
    if (!hosts.length) return;
    if (!document.getElementById("sitenav-css")) {
      var style = document.createElement("style");
      style.id = "sitenav-css";
      style.textContent = CSS;
      document.head.appendChild(style);
    }
    Array.prototype.forEach.call(hosts, render);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
