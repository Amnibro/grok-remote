---
description: Enable or disable Grok-Remote auto-start on Grok session start and/or Windows logon
argument-hint: "[on|off|status|boot] [cwd]"
allowed-tools: [Bash, Read]
---

# /remote-autostart

Manage auto-start for Grok-Remote. Arguments: $ARGUMENTS

## Parse first token

| Arg | Action |
|-----|--------|
| `on` / `enable` / empty | Enable autostart (session hook). Optional path = default cwd |
| `boot` | Enable session + Windows logon task |
| `off` / `disable` | Disable autostart and remove logon task |
| `status` | Show config path + flags + whether UI is healthy |

## Steps

1. Resolve plugin root (`GROK_PLUGIN_ROOT` or `~/.grok/plugins/grok-remote` or repo with `start.ps1`).
2. Run:

**on:**
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$PLUGIN\scripts\install-autostart.ps1" -Cwd "<workspace or arg>"
```

**boot:**
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$PLUGIN\scripts\install-autostart.ps1" -Boot -Cwd "<workspace>"
```

**off:**
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$PLUGIN\scripts\install-autostart.ps1" -Disable
```

**status:**
- Read `~/.grok/plugin-data/grok-remote/config.json` (or GROK_PLUGIN_DATA)
- `Invoke-RestMethod http://127.0.0.1:2421/health` if possible
- `schtasks /Query /TN GrokRemoteAutostart` if present

3. Tell the user clearly what was enabled and that a **new Grok session** is needed for SessionStart hooks to load.
