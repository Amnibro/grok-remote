const { app, BrowserWindow, Menu, shell, ipcMain, dialog } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const http = require("http");
const fs = require("fs");
const crypto = require("crypto");
const UI_PORT = Number(process.env.GROK_REMOTE_UI_PORT || 2421);
const AGENT_PORT = Number(process.env.GROK_REMOTE_AGENT_PORT || 2419);
let workspaceCwd = process.env.GROK_REMOTE_CWD || path.join(process.env.USERPROFILE || process.env.HOME || "", "Documents", "ai");
let mainWindow = null;
let stackProc = null;
let stackKids = [];
function rootDir() {
  if (app.isPackaged) return path.join(process.resourcesPath);
  return path.join(__dirname, "..");
}
function resolveUiSecret() {
  if (process.env.GROK_AGENT_SECRET) return process.env.GROK_AGENT_SECRET;
  const secretFile = path.join(rootDir(), ".ui-secret");
  try {
    const existing = fs.readFileSync(secretFile, "utf8").trim();
    if (existing.length >= 16) return existing;
  } catch {}
  const fresh = crypto.randomBytes(16).toString("hex");
  try { fs.writeFileSync(secretFile, fresh, "utf8"); } catch {}
  return fresh;
}
const UI_SECRET = resolveUiSecret();
process.env.GROK_AGENT_SECRET = UI_SECRET;
function httpGet(url, timeoutMs = 2000) {
  return new Promise((resolve) => {
    const req = http.get(url, { timeout: timeoutMs }, (res) => {
      let d = "";
      res.on("data", (c) => (d += c));
      res.on("end", () => {
        try {
          resolve({ ok: res.statusCode === 200, body: JSON.parse(d) });
        } catch {
          resolve({ ok: res.statusCode === 200, body: d });
        }
      });
    });
    req.on("error", () => resolve({ ok: false }));
    req.on("timeout", () => {
      req.destroy();
      resolve({ ok: false });
    });
  });
}
async function stackHealthy() {
  const h = await httpGet(`http://127.0.0.1:${UI_PORT}/health?key=${UI_SECRET}`);
  return !!(h.ok && h.body && (h.body.ok === true || h.body.ok === "true"));
}
function findGrok() {
  const home = process.env.USERPROFILE || process.env.HOME || "";
  const cands = [path.join(home, ".grok", "bin", "grok.exe"), path.join(home, ".grok", "bin", "grok"), "grok"];
  for (const c of cands) {
    if (c === "grok") return c;
    if (fs.existsSync(c)) return c;
  }
  return "grok";
}
function findPython() {
  return process.env.PYTHON || "python";
}
function startStack(cwd) {
  return new Promise(async (resolve) => {
    if (await stackHealthy()) return resolve({ ok: true, already: true });
    const root = rootDir();
    const startPs1 = path.join(root, "start.ps1");
    const secret = UI_SECRET;
    const useCwd = cwd || workspaceCwd;
    if (process.platform === "win32" && fs.existsSync(startPs1)) {
      stackProc = spawn(
        "powershell.exe",
        ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", startPs1, "-Cwd", useCwd, "-AlwaysApprove", "-UiPort", String(UI_PORT), "-Port", String(AGENT_PORT), "-NoLeader"],
        { cwd: root, windowsHide: true, env: process.env }
      );
    } else {
      const grok = findGrok();
      const py = findPython();
      const agent = spawn(grok, ["agent", "--always-approve", "serve", "--bind", `127.0.0.1:${AGENT_PORT}`, "--secret", secret], { cwd: useCwd, windowsHide: true, env: process.env });
      const ui = spawn(py, [path.join(root, "server.py"), "--port", String(UI_PORT), "--bind", "0.0.0.0", "--agent-host", "127.0.0.1", "--agent-port", String(AGENT_PORT), "--secret", secret, "--cwd", useCwd], { cwd: root, windowsHide: true, env: process.env });
      stackKids = [agent, ui];
      stackProc = ui;
    }
    let tries = 0;
    const tick = async () => {
      tries++;
      if (await stackHealthy()) return resolve({ ok: true, started: true });
      if (tries > 50) return resolve({ ok: false, error: "timeout waiting for health" });
      setTimeout(tick, 500);
    };
    setTimeout(tick, 800);
  });
}
function stopStack() {
  try {
    if (stackProc && !stackProc.killed) stackProc.kill();
  } catch {}
  for (const p of stackKids) {
    try {
      if (p && !p.killed) p.kill();
    } catch {}
  }
  stackKids = [];
  stackProc = null;
  if (process.platform === "win32") {
    try {
      spawn("powershell.exe", ["-NoProfile", "-Command", `$ports=@(${UI_PORT},${AGENT_PORT}); foreach($port in $ports){ Get-NetTCPConnection -LocalPort $port -State Listen -EA SilentlyContinue | ForEach-Object { $op=$_.OwningProcess; $cl=(Get-CimInstance Win32_Process -Filter \"ProcessId=$op\" -EA SilentlyContinue).CommandLine; if($cl -match 'serve|server.py|start.ps1'){ Stop-Process -Id $op -Force -EA SilentlyContinue } } }`], { windowsHide: true });
    } catch {}
  }
}
function uiUrl(extra) {
  const q = new URLSearchParams({ key: UI_SECRET, auto: "1", desktop: "1", electron: "1", layout: "desktop", cwd: workspaceCwd, v: String(Date.now()) });
  if (extra) Object.entries(extra).forEach(([k, v]) => q.set(k, v));
  return `http://127.0.0.1:${UI_PORT}/?${q.toString()}`;
}
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1000,
    minHeight: 680,
    backgroundColor: "#0a0b0e",
    title: "Grok Remote · Cockpit",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  });
  mainWindow.loadURL(uiUrl({ ide: "1" }));
  mainWindow.webContents.setWindowOpenHandler(({ url: u }) => {
    shell.openExternal(u);
    return { action: "deny" };
  });
}
async function chooseWorkspace() {
  const r = await dialog.showOpenDialog(mainWindow, { properties: ["openDirectory", "createDirectory"], title: "Choose workspace folder", defaultPath: workspaceCwd });
  if (r.canceled || !r.filePaths[0]) return null;
  workspaceCwd = r.filePaths[0];
  try {
    await fetchJson(`http://127.0.0.1:${UI_PORT}/api/fs/root?key=${UI_SECRET}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path: workspaceCwd }) });
  } catch {}
  return workspaceCwd;
}
function fetchJson(url, opts) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const lib = http;
    const req = lib.request({ hostname: u.hostname, port: u.port, path: u.pathname + u.search, method: (opts && opts.method) || "GET", headers: (opts && opts.headers) || {} }, (res) => {
      let d = "";
      res.on("data", (c) => (d += c));
      res.on("end", () => {
        try {
          resolve(JSON.parse(d));
        } catch (e) {
          reject(e);
        }
      });
    });
    req.on("error", reject);
    if (opts && opts.body) req.write(opts.body);
    req.end();
  });
}
function buildMenu() {
  const template = [
    {
      label: "File",
      submenu: [
        {
          label: "Open workspace…",
          accelerator: "CmdOrCtrl+O",
          click: async () => {
            const p = await chooseWorkspace();
            if (p && mainWindow) mainWindow.loadURL(uiUrl({ ide: "1", cwd: p }));
          }
        },
        {
          label: "Ensure stack running",
          click: async () => {
            const r = await startStack(workspaceCwd);
            dialog.showMessageBox(mainWindow, { type: r.ok ? "info" : "error", message: r.ok ? "Remote stack is up — no terminal needed." : "Failed: " + (r.error || "unknown") });
            if (r.ok && mainWindow) mainWindow.loadURL(uiUrl({ ide: "1" }));
          }
        },
        {
          label: "Stop remote stack",
          click: () => {
            stopStack();
            dialog.showMessageBox(mainWindow, { type: "info", message: "Stop requested for remote stack only (not other Grok sessions)." });
          }
        },
        { type: "separator" },
        { label: "Open in browser", click: () => shell.openExternal(uiUrl()) },
        { type: "separator" },
        { role: "quit" }
      ]
    },
    {
      label: "IDE",
      submenu: [
        {
          label: "Toggle IDE panel",
          accelerator: "CmdOrCtrl+\\\\",
          click: () => mainWindow && mainWindow.webContents.executeJavaScript("window.grokIde&&window.grokIde.toggle()")
        },
        {
          label: "Grok Review active file",
          accelerator: "CmdOrCtrl+Shift+R",
          click: () => mainWindow && mainWindow.webContents.executeJavaScript("window.grokIde&&window.grokIde.reviewActive&&window.grokIde.reviewActive()")
        },
        {
          label: "Grok Review all dirty",
          click: () => mainWindow && mainWindow.webContents.executeJavaScript("window.grokIde&&window.grokIde.reviewDirty&&window.grokIde.reviewDirty()")
        }
      ]
    },
    {
      label: "Session",
      submenu: [
        {
          label: "New Grok session here…",
          accelerator: "CmdOrCtrl+N",
          click: () => {
            if (!mainWindow) return;
            mainWindow.loadURL(uiUrl({ task: "Ready for IDE edits and Grok Review on this workspace.", cwd: workspaceCwd, ide: "1" }));
          }
        },
        {
          label: "Refresh UI",
          click: () => mainWindow && mainWindow.loadURL(uiUrl({ ide: "1" }))
        }
      ]
    },
    {
      label: "View",
      submenu: [{ role: "reload" }, { role: "toggleDevTools" }, { type: "separator" }, { role: "resetZoom" }, { role: "zoomIn" }, { role: "zoomOut" }, { type: "separator" }, { role: "togglefullscreen" }]
    }
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}
ipcMain.handle("get-cwd", () => workspaceCwd);
ipcMain.handle("set-cwd", async (_e, p) => {
  if (p && fs.existsSync(p)) workspaceCwd = p;
  return workspaceCwd;
});
ipcMain.handle("pick-folder", async () => chooseWorkspace());
ipcMain.handle("stack-status", async () => ({ healthy: await stackHealthy(), uiPort: UI_PORT, agentPort: AGENT_PORT, cwd: workspaceCwd }));
ipcMain.handle("ensure-stack", async () => startStack(workspaceCwd));
ipcMain.handle("stop-stack", async () => {
  stopStack();
  return { ok: true };
});
ipcMain.handle("open-external", async (_e, url) => {
  await shell.openExternal(url);
  return { ok: true };
});
ipcMain.handle("new-session-url", async (_e, opts) => {
  const o = opts || {};
  return uiUrl({ task: o.task || "New session from Grok Remote cockpit", cwd: o.cwd || workspaceCwd, ide: "1" });
});
app.whenReady().then(async () => {
  buildMenu();
  if (!fs.existsSync(workspaceCwd)) {
    try {
      fs.mkdirSync(workspaceCwd, { recursive: true });
    } catch {}
  }
  const r = await startStack(workspaceCwd);
  if (!r.ok) {
    dialog.showErrorBox("Grok Remote", "Could not start agent/UI stack automatically.\n" + (r.error || "") + "\nInstall Grok CLI + Python, then File → Ensure stack running.\nNo separate terminal is required once those exist.");
  }
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
app.on("before-quit", () => {
  if (process.env.GROK_REMOTE_STOP_ON_QUIT === "1") stopStack();
});
