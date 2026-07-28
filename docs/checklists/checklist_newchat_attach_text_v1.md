# Checklist: New chat only + attach+text paint

- [x] Scan architecture / UI for New task, 9-dot Chat section, send path
- [x] Backup `web/index.html` → `backups/index.html.v_newchat_attach_text.bak`
- [x] Remove New task from sessions rail + New task/Sessions from command deck
- [x] Fix local user paint: `paintLocalUserTurn` (text+files one bubble; no pre-set echo skip)
- [x] Preserve `.att-prev`/`.file-chip` when `appendUser` re-renders text
- [x] Guard leftover task-sheet wiring for missing buttons
- [x] Changelog + architecture_map
- [x] Deploy to `~/.grok/plugins/grok-remote` + restart UI
- [ ] Push GitHub
- [x] Fix v36.1 duplicate You bubble (history catch-up echo)
- [ ] User confirm after hard refresh
