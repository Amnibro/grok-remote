---
name: remote
description: "Live phone/browser controller for Grok Build. Use for /remote, Android remote, mobile control, Grok-Remote. Starts LAN UI+ACP proxy with session picker, history+thinking+tools, live stream, Skills, New Task."
argument-hint: "[start|stop|status|url|install|doctor|task] [cwd] [message…]"
user-invocable: true
disable-model-invocation: false
allowed-tools: [Bash, Read, Glob]
compatibility: Python 3.10+ and the grok CLI. Linux, macOS and Windows. aiohttp is set up on first start (private venv when the system Python is externally managed).
metadata:
  author: Anthony
  short-description: Live Android/browser remote for Grok Build
  version: "1.2.0"
---

# Grok Remote (`/remote`) v1.2

Start (or manage) **Grok Remote**: a **live** phone/browser controller for Grok Build.

## What it does

1. Runs `grok agent --always-approve --no-leader serve` on **127.0.0.1:2419** (tools on this PC).
2. Runs the UI + multi-client WebSocket hub on **0.0.0.0:2421** (one phone URL; the agent secret stays server-side).
3. Phone: session picker, full history, live stream, Skills palette, New Task, companion.

## One control CLI on every OS

`grok_remote_ctl.py` in the plugin root does everything. After `install` it is also on PATH as `grok-remote` (Linux/macOS, `~/.local/bin`).

```sh
PLUGIN="${GROK_PLUGIN_ROOT:-$HOME/.grok/plugins/grok-remote}"
python3 "$PLUGIN/grok_remote_ctl.py" <command>
```

On Windows use `python` and `%GROK_PLUGIN_ROOT%\grok_remote_ctl.py`; it delegates to the PowerShell scripts in `scripts\`.

| Command | Effect |
|---------|--------|
| `start --force [--cwd DIR] --wait 20` | start the hub if it is down (uses the systemd user unit when one is installed) |
| `stop [--keep-agent]` | stop only the hub on 2421 and its agent serve on 2419, never other grok processes |
| `restart` | restart the hub, keep the agent |
| `status [--json]` | ports, health, unit, autostart, launcher, pin state |
| `url [--qr] [--local]` | phone pairing link (with a terminal QR when `qrencode` is installed) |
| `open [--browser]` | start if needed, open the desktop app or an app-mode browser window |
| `install [--pin] [--autostart]` | app-menu launcher + icon + `grok-remote` CLI, optionally pin to taskbar/dock and start at login |
| `pin [--off]` | pin/unpin the launcher (KDE Plasma, GNOME, Cinnamon; other desktops get instructions) |
| `autostart on\|boot\|off\|status` | Grok SessionStart hook; `boot` also starts at login (systemd user unit, LaunchAgent, or Windows logon task) |
| `doctor` | checks Python, aiohttp, grok, ports, firewall, TTS, launcher, with the distro-specific fix for each |

## Arguments (`$ARGUMENTS`)

| Arg | Action |
|-----|--------|
| *(empty)* or `start` | `start --force --wait 20`, then `url` |
| `stop` | `stop` |
| `status` | `status` |
| `url` | `url --qr` |
| `install` | `install --pin` |
| `doctor` | `doctor` |
| `task <cwd> [message…]` | give the deep link `http://<lan-ip>:2421/?auto=1&task=<msg>&cwd=<path>` |
| extra path | cwd override for `start` |

Default cwd is the user's current workspace (session cwd), never the plugin directory.

## Reply to the user with

- Phone URL from `url` (same Wi‑Fi; never `127.0.0.1` on the phone)
- Deep link to the current session if known: `…/?auto=1&session=<sessionId>`
- If `doctor` reports a firewall row, give its fix line (phones cannot connect otherwise)

## Safety

- Never kill grok processes by name; `stop` only targets the hub and agent serve listening on the configured ports.
- The secret stays server-side. The agent binds localhost; the UI binds the LAN.
- Auto-approve applies only to the remote agent serve process.

## Config

`~/.grok/plugin-data/grok-remote/config.json` (or `GROK_PLUGIN_DATA`): `autostart`, `autostart_on_session`, `autostart_on_boot`, `cwd`, `ui_port`, `agent_port`.

## Example user messages

- `/remote`
- `/remote status`
- `/remote stop`
- `/remote start ~/code/project`
- `/remote install`
- `/remote-autostart boot`
