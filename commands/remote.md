---
description: Live phone controller for Grok Build — start LAN remote (history, live stream, Skills, New Task)
argument-hint: "[start|stop|status|url|task] [cwd] [message…]"
allowed-tools: [Bash, Read, Glob]
---

# /remote

Run the **grok-remote** skill for: $ARGUMENTS

Follow `skills/remote/SKILL.md` in this plugin.

**Phone UI (after start):** open the printed `http://LAN_IP:2421/?auto=1` on the same Wi‑Fi.

- Sessions list + load (resident = live desktop)
- Full history (messages, thinking, tools, plans)
- Live stream + 0.8s catch-up for PC-side messages
- Back swipe / ‹ → Sessions (does not leave the site)
- **Skills** → slash commands
- **Task** → new session at a cwd + first prompt

Never `Stop-Process -Name grok`.
