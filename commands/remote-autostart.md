---
description: Enable or disable Grok Remote auto-start on Grok session start and/or at login
argument-hint: "[on|off|status|boot] [cwd]"
allowed-tools: [Bash, Read]
---

# /remote-autostart

Manage auto-start for Grok Remote. Arguments: $ARGUMENTS

| Arg | Action |
|-----|--------|
| `on` / `enable` / empty | Enable autostart on Grok SessionStart. Optional path = default cwd |
| `boot` | Same + start at login (systemd user unit on Linux, LaunchAgent on macOS, logon task on Windows) |
| `off` / `disable` | Disable autostart, the login entry and the global hook |
| `status` | Config path, flags, unit state |

## Run

Linux / macOS (map `enable`→`on`, `disable`→`off`):

```sh
PLUGIN="${GROK_PLUGIN_ROOT:-$HOME/.grok/plugins/grok-remote}"
python3 "$PLUGIN/grok_remote_ctl.py" autostart <on|boot|off|status> [--cwd "<path>"]
```

Windows (PowerShell):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$PLUGIN\scripts\install-autostart.ps1" -Cwd "<workspace>"        # on
powershell -NoProfile -ExecutionPolicy Bypass -File "$PLUGIN\scripts\install-autostart.ps1" -Boot -Cwd "<workspace>"  # boot
powershell -NoProfile -ExecutionPolicy Bypass -File "$PLUGIN\scripts\install-autostart.ps1" -Disable                  # off
```

Tell the user what was enabled and that a **new Grok session** is needed for SessionStart hooks to load.
