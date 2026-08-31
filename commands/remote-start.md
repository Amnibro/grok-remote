---
description: Start Grok Remote UI + agent serve (idempotent). Safe from any Grok Build window.
argument-hint: "[cwd]"
allowed-tools: [Bash]
---

# /remote-start

Start Grok Remote for phone/desktop control. Arguments: $ARGUMENTS

## Run

```powershell
$PLUGIN = if ($env:GROK_PLUGIN_ROOT) { $env:GROK_PLUGIN_ROOT } elseif (Test-Path "$env:USERPROFILE\.grok\plugins\grok-remote\scripts\ensure-running.ps1") { "$env:USERPROFILE\.grok\plugins\grok-remote" } else { (Get-Location).Path }
$CWD = if ("$ARGUMENTS".Trim()) { "$ARGUMENTS".Trim() } else { (Get-Location).Path }
powershell -NoProfile -ExecutionPolicy Bypass -File "$PLUGIN\scripts\ensure-running.ps1" -Force -IgnoreConfig -Reason "command"
Start-Sleep -Seconds 2
try { Invoke-RestMethod "http://127.0.0.1:2421/health" -TimeoutSec 4 | ConvertTo-Json -Compress } catch { "health: $_" }
if (Test-Path "$PLUGIN\connect.url") { Get-Content "$PLUGIN\connect.url" }
```

## Tell the user

- Phone: `http://LAN_IP:2421/?auto=1` (same Wi‑Fi; not 127.0.0.1 on phone)
- PC browser: `http://127.0.0.1:2421/?auto=1`
- Stop: UI **Stop** button, `/remote-stop`, or Desktop **Grok Remote Stop**
- Pin: run `/remote` then UI **Pin**, or `scripts\install-shortcut.ps1`
- Windows app: https://github.com/Amnibro/grok-remote/releases/latest/download/GrokRemote.exe
