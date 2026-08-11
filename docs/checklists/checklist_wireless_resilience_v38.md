# Checklist — wireless resilience v38 (2026-08-07)

- [x] Backup index.html, server.py, cockpit-features.js
- [x] Client: app-level WS keepalive + silent-death detect
- [x] Client: never permanently give up reconnect while page open
- [x] Client: single-flight connect (no n=2 thrash)
- [x] Client: disk catch-up poll survives soft WS drop
- [x] Client: disable dual reconnect in cockpit-features.js
- [x] Server: client heartbeat 12s; hub ping handler; upstream keepalive
- [x] Sync web/index.html → root index.html + ~/.grok/plugins/grok-remote
- [x] Restart UI only; verify /health
- [x] Update architecture_map.md + changelog.md
