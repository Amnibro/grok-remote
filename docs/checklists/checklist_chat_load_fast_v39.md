# Checklist — chat load fast v39

- [x] Scan architecture_map.md
- [x] Backup server.py + web/index.html
- [x] Session dir index + 90s cache (find_session_dir)
- [x] chat_only: byte prefilter + up to 64MB scan + coalesce before cut
- [x] Cap returned chat text (_trim_chat_text)
- [x] Client: HISTORY_PAGE 24, fast history paint, deferred rich upgrade
- [x] Client: skip code highlight during historyPainting
- [x] Client: load older uses chat_only
- [x] Drop full-history fallback on open (chat_only only)
- [x] Sync ~/.grok/plugins/grok-remote
- [x] py_compile server.py
- [x] Benchmark top sessions ~20–140ms for 24 msgs
- [x] Update architecture_map.md + changelog.md
- [ ] User confirms phone open is snappy on long chats
