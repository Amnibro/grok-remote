---
description: Stop Grok Remote UI/proxy and remote agent serve only (keeps desktop TUI alive)
argument-hint: ""
allowed-tools: [Bash]
---

# /remote-stop

Stop **only** Grok Remote (never desktop TUI by name).

## Run

```powershell
$PLUGIN = if ($env:GROK_PLUGIN_ROOT) { $env:GROK_PLUGIN_ROOT } elseif (Test-Path "$env:USERPROFILE\.grok\plugins\grok-remote\scripts\stop-remote.ps1") { "$env:USERPROFILE\.grok\plugins\grok-remote" } else { (Get-Location).Path }
powershell -NoProfile -ExecutionPolicy Bypass -File "$PLUGIN\scripts\stop-remote.ps1"
```

## Rules

- Kills listeners on **TCP 2421** (UI) and **2419** (remote agent serve) only
- **Never** `Stop-Process -Name grok`
- Confirm ports free with `netstat -ano | findstr "2421 2419"`
- Tell user: start again with `/remote` or Desktop **Grok Remote** shortcut
