# Grok Remote Desktop (Electron cockpit)

**Double‑click launch** — no terminal required for day‑to‑day use. Electron starts the Grok agent serve + UI proxy, opens the cockpit, and can create sessions on its own.

## One-time setup

```powershell
cd C:\Users\antho\Documents\ai\grok-remote\desktop
npm install
```

Needs: **Node 18+**, **Grok CLI** (`%USERPROFILE%\.grok\bin\grok.exe`), **Python 3** (+ `aiohttp` auto-installed by server).

## Launch (no terminal after install)

```text
scripts\launch-desktop.cmd
```

or:

```powershell
cd desktop
npm start
```

On start the app:

1. Spawns **agent** `127.0.0.1:2419` + **UI/proxy** `:2421` if not healthy  
2. Opens the desktop window (auto-connect)  
3. Enables **IDE** + **Grok Review**  

## Built-in IDE

| Action | How |
|--------|-----|
| Toggle IDE | **IDE** header button · `Ctrl+\` · menu IDE |
| Browse / edit | File tree · tabs · editor |
| Save | **Save** · `Ctrl+S` (writes on the PC via `/api/fs/write`) |
| Grok Review | **Grok Review** — sends structured bug-check prompt for the active file |
| Review dirty | All unsaved/saved dirty buffers |
| Workspace | **Folder…** or File → Open workspace |
| New session | **New session here** or Session → New Grok session |

Workspace FS is sandboxed to the chosen root (`/api/fs/*` on the local UI server).

## Menu

| Item | Action |
|------|--------|
| File → Open workspace… | Pick project folder |
| File → Ensure stack running | Start agent+UI if down |
| File → Stop remote stack | Stop only serve/UI |
| IDE → Grok Review… | Post-edit review |
| Session → New Grok session here… | Fresh session at workspace |

## Env

| Var | Meaning |
|-----|---------|
| `GROK_REMOTE_CWD` | Default workspace |
| `GROK_REMOTE_UI_PORT` | Default `2421` |
| `GROK_REMOTE_AGENT_PORT` | Default `2419` |
| `GROK_REMOTE_STOP_ON_QUIT=1` | Kill stack when Electron closes |

Phone clients still use `http://LAN:2421/?auto=1` on the same stack.
