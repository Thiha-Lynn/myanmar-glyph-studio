/*
 * Myanmar Glyph Studio — desktop shell.
 *
 * The studio is the same static web/ directory the website serves; this
 * process only gives it a window and a file loader. No Node integration
 * reaches the page, nothing phones home, and the Python build pipeline is
 * NOT bundled — this is the drawing studio, exactly as on the web, for
 * people who prefer a real application to a browser tab.
 *
 * Files are served over a private app:// scheme instead of file:// so
 * that fetch(), FontFace loading and relative URLs behave exactly as they
 * do on the website.
 */
"use strict";

const { app, BrowserWindow, protocol, shell } = require("electron");
const fs = require("fs/promises");
const path = require("path");

const APP_HOST = "app://mgs/";

// Must be declared before app is ready.
protocol.registerSchemesAsPrivileged([
  { scheme: "app", privileges: { standard: true, secure: true, supportFetchAPI: true } },
]);

function webRoot() {
  return app.isPackaged
    ? path.join(process.resourcesPath, "web")
    : path.join(__dirname, "..", "web");
}

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".webmanifest": "application/manifest+json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".ttf": "font/ttf",
  ".woff2": "font/woff2",
  ".txt": "text/plain; charset=utf-8",
  ".md": "text/plain; charset=utf-8",
};

async function serve(request) {
  const root = webRoot();
  let pathname;
  try {
    pathname = decodeURIComponent(new URL(request.url).pathname);
  } catch (e) {
    return new Response("bad request", { status: 400 });
  }
  if (pathname.endsWith("/")) pathname += "index.html";
  const file = path.normalize(path.join(root, pathname));
  if (file !== root && !file.startsWith(root + path.sep)) {
    return new Response("forbidden", { status: 403 });
  }
  try {
    const body = await fs.readFile(file);
    const type = MIME[path.extname(file).toLowerCase()] || "application/octet-stream";
    return new Response(body, { headers: { "content-type": type } });
  } catch (e) {
    return new Response("not found", { status: 404 });
  }
}

function isExternal(url) {
  return /^https?:/i.test(url);
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1360,
    height: 900,
    minWidth: 760,
    minHeight: 560,
    backgroundColor: "#faf7f2",
    title: "Myanmar Glyph Studio",
    icon: path.join(__dirname, "build", "icon.png"), // used on Linux; mac/win use the bundle icon
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  // Links out of the studio (SIL, GitHub, Hugging Face…) belong in the
  // user's real browser. Anything else stays inside the app scheme.
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (isExternal(url)) shell.openExternal(url);
    return { action: "deny" };
  });
  win.webContents.on("will-navigate", (event, url) => {
    if (!url.startsWith(APP_HOST)) {
      event.preventDefault();
      if (isExternal(url)) shell.openExternal(url);
    }
  });

  win.loadURL(APP_HOST + "index.html");
  return win;
}

// --- self-test ------------------------------------------------------------
// MGS_SELFTEST_OUT=<png path> runs the app headlessly enough to prove the
// packaged studio actually renders: load, wait for paint, save a
// screenshot, dump the page's console, exit. Used by local verification —
// not part of the packaged app's behaviour.
function selfTest(win, outPath) {
  const messages = [];
  win.webContents.on("console-message", (ev, level, message) => {
    messages.push({ level, message });
  });
  const deadline = setTimeout(() => {
    process.stdout.write("SELFTEST TIMEOUT\n");
    app.exit(2);
  }, 30000);
  win.webContents.on("did-finish-load", () => {
    setTimeout(async () => {
      try {
        const image = await win.webContents.capturePage();
        await fs.writeFile(outPath, image.toPNG());
        process.stdout.write(
          "SELFTEST OK " + outPath + "\n" +
          messages.map((m) => "console[" + m.level + "] " + m.message).join("\n") + "\n"
        );
        clearTimeout(deadline);
        app.exit(0);
      } catch (e) {
        process.stdout.write("SELFTEST FAIL " + e.message + "\n");
        clearTimeout(deadline);
        app.exit(1);
      }
    }, 2500);
  });
}

app.whenReady().then(() => {
  protocol.handle("app", serve);
  const win = createWindow();
  if (process.env.MGS_SELFTEST_OUT) selfTest(win, process.env.MGS_SELFTEST_OUT);

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  app.quit();
});
