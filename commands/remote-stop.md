---
description: Stop Grok Remote UI/proxy and remote agent serve only (keeps desktop TUI alive)
argument-hint: ""
allowed-tools: [Bash]
---

# /remote-stop

Stop only Grok Remote processes:

1. Listener on **TCP 2421** (mobile UI + WS proxy)
2. Remote **agent serve** on **2419** if started for remote

## Hard rules

- **Never** `Stop-Process -Name grok` / kill every Grok PID
- Confirm ports free; report status to the user
