# Checklist — drop-prompt + slow load + Tauri desktop v40

- [x] Scan architecture_map.md
- [x] Backup web/index.html + server.py
- [x] Hub holds session/prompt until session/load Event for that sid (90s)
- [x] Client waits agent attach before send; sendInFlight queues instead of drop
- [x] Failed dispatch re-queues; hide horizon as soon as disk history returns
- [x] chat_only max scan 8MB; HISTORY_PAGE 16 / 180k bytes
- [x] Tauri desktop-tauri shell; Electron sources in archive/electron-desktop
- [x] Release exe built (`desktop-tauri/dist/GrokRemote.exe` + `src-tauri/target/release/grok-remote-desktop.exe`)
- [x] py_compile + copy to ~/.grok/plugins/grok-remote
- [x] architecture_map.md + changelog.md
- [ ] User confirms
