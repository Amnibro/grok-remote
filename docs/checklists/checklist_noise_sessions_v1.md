# Checklist — hide Azno/amni watchdog sessions from chat list v1

- [x] Scan architecture_map.md
- [x] Identify noise: Azno market-watch co-pilot sessions (~180 titles; ~hourly new chats)
- [x] Backup `web/index.html` (+ plugin sync targets)
- [x] Add `isNoiseSession(s)` title/cwd heuristics
- [x] Filter in `normalizeSessions` so list + pickBest + pins never surface them
- [x] Exclude noise from `pickBestSession` / auto-open (defense in depth)
- [x] Sync to `~/.grok/plugins/grok-remote/web/index.html`
- [x] Update architecture_map.md + changelog.md
- [x] Verify regex against live `generated_title` samples (669→190 noise; azno-v2 real analyses kept)
- [ ] User hard-refresh remote UI
