---
description: Stop Grok Remote UI/proxy and remote agent serve only (keeps desktop TUI alive)
argument-hint: "[--keep-agent]"
allowed-tools: [Bash]
---

# /remote-stop

Stop **only** Grok Remote (never the desktop TUI, never grok by name). Arguments: $ARGUMENTS

## Run

Linux / macOS:

```sh
PLUGIN="${GROK_PLUGIN_ROOT:-$HOME/.grok/plugins/grok-remote}"
python3 "$PLUGIN/grok_remote_ctl.py" stop $ARGUMENTS
python3 "$PLUGIN/grok_remote_ctl.py" status
```

Windows (PowerShell):

```powershell
$PLUGIN = if ($env:GROK_PLUGIN_ROOT) { $env:GROK_PLUGIN_ROOT } else { "$env:USERPROFILE\.grok\plugins\grok-remote" }
powershell -NoProfile -ExecutionPolicy Bypass -File "$PLUGIN\scripts\stop-remote.ps1"
```

## Rules

- Stops the hub on **2421** (its systemd user unit if it has one, so it does not respawn) and the agent serve on **2419** only
- **Never** kill grok processes by name
- Tell the user: start again with `/remote`, `grok-remote start --force`, or the app launcher
