---
description: Start Grok Remote UI + agent serve (idempotent). Safe from any Grok Build window.
argument-hint: "[cwd]"
allowed-tools: [Bash]
---

# /remote-start

Start Grok Remote for phone/desktop control. Arguments: $ARGUMENTS

## Run

Linux / macOS:

```sh
PLUGIN="${GROK_PLUGIN_ROOT:-$HOME/.grok/plugins/grok-remote}"
CWD="${ARGUMENTS:-$PWD}"
python3 "$PLUGIN/grok_remote_ctl.py" start --force --cwd "$CWD" --wait 20
python3 "$PLUGIN/grok_remote_ctl.py" url --qr
```

Windows (PowerShell):

```powershell
$PLUGIN = if ($env:GROK_PLUGIN_ROOT) { $env:GROK_PLUGIN_ROOT } else { "$env:USERPROFILE\.grok\plugins\grok-remote" }
$CWD = if ("$ARGUMENTS".Trim()) { "$ARGUMENTS".Trim() } else { (Get-Location).Path }
powershell -NoProfile -ExecutionPolicy Bypass -File "$PLUGIN\scripts\ensure-running.ps1" -Force -IgnoreConfig -Reason "command" -Cwd $CWD
Start-Sleep -Seconds 2
if (Test-Path "$PLUGIN\connect.url") { Get-Content "$PLUGIN\connect.url" }
```

## Tell the user

- Phone: the printed `http://LAN_IP:2421/?…` link (same Wi‑Fi; not 127.0.0.1 on the phone)
- PC: `grok-remote open` (Linux/macOS) or the Start Menu shortcut (Windows)
- Stop: UI **Stop**, `/remote-stop`, or `grok-remote stop`
- Install + pin: Command deck → **Install app…**, or `grok-remote install --pin`
