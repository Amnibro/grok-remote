# Checklist: desktop launch roots the hub in the repo -> rail empty, chats filed under "Ai" v1

- [x] Scan architecture_map.md (Launch row: Desktop -> ensure-running -> supervise)
- [x] Reproduce on live hub: /health cwd = repo root; 112/129 sessions -> "Ai" bucket, Chats=1, rail "No sessions yet"
- [x] Root cause: GrokRemote.exe -> ensure-running.ps1 (no -Cwd) -> $PWD fallback = repo root
- [x] Backups: backups/lib.rs.v1.9.x.bak, backups/ensure-running.ps1.v1.9.x.bak, backups/server.py.cwdguard.bak
- [x] ensure-running.ps1: -Cwd param, never $PWD when it is the plugin root, Documents\ai fallback, -PrintCwd probe
- [x] lib.rs spawn_stack: pass -Cwd on the ensure-running branch + GROK_PROJECT_DIR env
- [x] server.py: warn when --cwd resolves to the hub's own folder
- [x] live fix: POST /api/fs/root -> Documents\ai, rail repaints with real chats
- [x] restart supervisor with correct cwd so a respawn does not regress
- [x] cargo build --release desktop exe, copy to desktop-tauri/dist
- [x] regression test tests/test_ensure_running_cwd.py
- [x] architecture_map.md + changelog.md
- [x] mirror to ~/.grok/plugins/grok-remote (scripts only; web/index.html drift is another session's WIP)
- exact-chain verified 2026-09-03 08:51: GrokRemote.exe cold -> ensure-running -Cwd -> hub --cwd Documents\ai (pid 35352), agent 2419 untouched
