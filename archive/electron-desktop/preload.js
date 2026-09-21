const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld("grokRemote", {
  isElectron: true,
  autoConnect: true,
  getCwd: () => ipcRenderer.invoke("get-cwd"),
  setCwd: (p) => ipcRenderer.invoke("set-cwd", p),
  pickFolder: () => ipcRenderer.invoke("pick-folder"),
  getStatus: () => ipcRenderer.invoke("stack-status"),
  ensureStack: () => ipcRenderer.invoke("ensure-stack"),
  stopStack: () => ipcRenderer.invoke("stop-stack"),
  openExternal: (url) => ipcRenderer.invoke("open-external", url),
  newSessionUrl: (opts) => ipcRenderer.invoke("new-session-url", opts || {}),
  platform: process.platform
});
