# Checklist — composer bind (type → sid) v33

- [x] Backup `web/index.html` → `backups/index.html.v33.bak`
- [x] `composerBoundSid` stamped on composer `input` / `focus` while a chat is open
- [x] Per-session `composerDrafts` saved on switch, restored on open
- [x] `resolveSendSid()` prefers typed bind over live `sid`
- [x] `sendPrompt` does not re-stamp from live `sid` when bind already set
- [x] `dispatchPromptPayload` uses pinned `sessionId` + `allowCrossSession`
- [x] Cross-chat send chips `sent → <id> (typed there)` when not viewing
- [x] Cancel/interject use target sid
- [x] Changelog + architecture_map
- [x] Commit / push / plugin sync
