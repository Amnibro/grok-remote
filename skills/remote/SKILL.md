---
name: remote
description: "Live phone/browser controller for Grok Build. Use for /remote, Android remote, mobile control, Grok-Remote. Starts LAN UI+ACP proxy with session picker, history+thinking+tools, live stream, Skills, New Task."
argument-hint: "[start|stop|status|url|task] [cwd] [message…]"
user-invocable: true
disable-model-invocation: false
allowed-tools: [Bash, Read, Glob]
compatibility: Requires Python 3, grok CLI, Windows PowerShell (start.ps1); aiohttp on first UI start
metadata:
  author: Anthony
  short-description: Live Android/browser remote for Grok Build
  version: "1.1.0"
---

# Grok Remote (`/remote`) v1.1

Start (or manage) **Grok-Remote**: a **live** phone controller for Grok Build (not history-only).

## What it does

1. Runs `grok agent --always-approve --leader serve` on **127.0.0.1:2419** (tools on this PC).
2. Runs UI + WebSocket **proxy** on **0.0.0.0:2421** (one phone URL; secret server-side).
3. Phone: session picker, full history (msgs/thoughts/tools/plans), **live stream + catch-up poll**, Skills palette, New Task (cwd), back-swipe → Sessions.

## Plugin paths

- Plugin root: use `GROK_PLUGIN_ROOT` if set, else the directory that contains `start.ps1` / `server.py` for this plugin.
- Scripts: `$PLUGIN/start.ps1`, `$PLUGIN/server.py`, `$PLUGIN/web/index.html`
- Data/logs: prefer `GROK_PLUGIN_DATA` when set, else `$PLUGIN/logs`

## Arguments (`$ARGUMENTS`)

Parse the first token:

| Arg | Action |
|-----|--------|
| *(empty)* or `start` | Start remote control for the current project cwd (`ensure-running.ps1 -Force -IgnoreConfig` or `start.ps1`) |
| `stop` | Run `scripts/stop-remote.ps1` — **only** listeners on 2421 + 2419 (never `Stop-Process -Name grok`) |
| `status` | Check ports 2419/2421, print connect URL, health |
| `url` | Print the LAN connect URL only |
| `task <cwd> [message…]` | Tell the user the phone **Task** button / deep link for a new session at cwd |
| extra path | Optional cwd override after the verb |

### UI stop + pin

- Header **Stop** posts `/api/stack/stop` (stops UI + remote agent serve; desktop TUI stays)
- Header **Pin** posts `/api/stack/shortcut` → Desktop + Start Menu shortcuts
- Desktop: **Grok Remote** / **Grok Remote Stop**; Start Menu folder **Grok Remote**
- Pin to taskbar: right-click Desktop shortcut → Pin to taskbar

### Phone UI features (tell the user)

- **Live stream** of desktop + phone turns (plus 0.8s catch-up poll for missed PC-side messages)
- **Back swipe / ‹** returns to **Sessions** (does not leave the site)
- **Skills** button → slash commands for the active session
- **Task** → new session at a stated folder + optional first prompt
- **Theme → UX**: auto-scroll, collapse think/code/tools, borders vs clean UI (device `localStorage`)
- **↓ Latest** FAB when scrolled up in chat
- Deep links: `?auto=1&session=<id>` · `?auto=1&task=<msg>&cwd=<path>`

Default cwd = the user's current workspace (session cwd), not the plugin directory.

## Steps — start

1. Resolve `PLUGIN_ROOT` (`GROK_PLUGIN_ROOT` or locate `start.ps1`).
2. Resolve `CWD` = argument path or current workspace.
3. On Windows, run (background / non-blocking for the TUI when possible):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$PLUGIN_ROOT\start.ps1" -Cwd "$CWD" -AlwaysApprove
```

   If `start.ps1` is long-running in the foreground, start it in a **new window** or background job so the chat stays usable:

```powershell
Start-Process powershell -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',"$PLUGIN_ROOT\start.ps1",'-Cwd',$CWD,'-AlwaysApprove') -WindowStyle Normal
```

4. Wait ~3s, read `$PLUGIN_ROOT\connect.url` if present, and call `http://127.0.0.1:2421/health` + `/config.json`.
5. Reply to the user with:
   - Phone URL: `http://<lan-ip>:2421/?auto=1`
   - Deep-link current session if known: `http://<lan-ip>:2421/?auto=1&session=<sessionId>`
   - Reminder: same Wi‑Fi; never open `127.0.0.1` on the phone
   - Reminder: never mass-kill `grok` processes

## Steps — stop

1. Prefer stopping PIDs recorded by the launcher / listening on **2421** (UI) and the **agent serve** port **2419** if that process was started for remote.
2. **Do not** run `Stop-Process -Name grok` or kill all grok PIDs.
3. Confirm ports released.

## Steps — status / url

1. `netstat` (or equivalent) for 2419/2421.
2. Fetch `/config.json` and `/health` when UI is up.
3. Print the LAN URL.

## Safety

- Secret stays server-side (proxy).
- Agent binds localhost; UI binds LAN.
- Auto-approve tools only for the remote agent serve process.
- Tell the user if firewall blocks inbound 2421.

## Autostart (`/remote-autostart`)

Config: `~/.grok/plugin-data/grok-remote/config.json` (or `GROK_PLUGIN_DATA`).

| Command | Effect |
|---------|--------|
| `/remote-autostart on` | `autostart=true`, SessionStart hook + global `~/.grok/hooks/grok-remote-autostart.json` |
| `/remote-autostart boot` | same + Windows logon task `GrokRemoteAutostart` |
| `/remote-autostart off` | disable flags, remove task + global hook |
| `/remote-autostart status` | show config + health |

Scripts: `scripts/install-autostart.ps1`, `scripts/ensure-running.ps1` (idempotent; no-op if `/health` ok).

Default `autostart` is **false** until the user enables it.

## Example user messages

- `/remote`
- `/remote start`
- `/remote status`
- `/remote stop`
- `/remote start C:\Users\me\project`
- `/remote-autostart on`
- `/remote-autostart boot`
- `/remote-autostart off`
