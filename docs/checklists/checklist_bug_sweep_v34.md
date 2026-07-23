# Checklist — Bug Sweep v34

- [x] changelog.md mojibake repaired via iterative ftfy → 21KB clean, 48 entries intact; backup at `backups/changelog.md.mojibake.bak`
- [x] Root-caused the mojibake writers: `run-agent.cmd` written as ASCII+replace, `fs_read`'s BOM handling left a literal BOM char reachable via round-trip — both fixed in server.py
- [x] server.py: 6 security/correctness fixes (self-cancel hang, secret leak, netstat substring match, static path separator, duplicate broadcast responses) + 6 reliability fixes (live-tail partial-line drop, /health phantom dependency, cmd encoding, BOM handling, unconditional port claim, loop job expiry)
- [x] index.html session/messaging: XSS in esc()/autolink, msgQueue wiped on switch+reconnect, stale composerBoundSid on newSession, drainMsgQueue silent drop on false return, pending map orphaned on ws close
- [x] voice-mode.js: stopSpeak deadlock+leak, infinite mic-error restart loop
- [x] ide.js: save-to-wrong-file corruption (reviewDirty + onEditorInput), in-flight save race, dead Ctrl+Shift+S shortcut, closeTab stale highlight
- [ ] index.html LOW items deferred (documented in bug-sweep session, not applied): object URL leak on image attachments, text+attachments lost on send failure before dispatch confirms, blur-path viewport pin not force-cleared, inlineMd markdown edge cases (code-span protection), loadExpectSid doc/code drift
- [ ] index.html MEDIUM deferred: off-screen (bound) queue/fyi sends skip enqueue when target session's busy state is unknown; cancelTurn clears busy optimistically before agent confirms
- [x] Deploy: copied web/ + server.py to ~/.grok/plugins/grok-remote/
- [x] changelog.md updated; architecture_map.md unchanged (no architecture shift, just fixes)

## Follow-up: C1 auth (2026-07-23)

- [x] `make_auth_middleware(token)` in server.py — cookie-or-query-or-header key check on every route; token = the existing `--secret` (already required, already random-per-launch, no new distribution mechanism needed)
- [x] Exemptions: `?demo=1` (screenshot/privacy-safe mode), `/health` (boolean+sanitized-string liveness probe, polled unauthenticated by 3 existing scripts that don't know the secret in advance)
- [x] First request with `?key=<secret>` sets an httpOnly cookie (30d) — same-origin fetch/WS calls from the browser carry it automatically, zero client JS changes needed
- [x] start.ps1: `connect.url` and printed pairing links now embed `?key=$Secret`; own `/health` startup check updated to match (harmless since /health is exempt anyway)
- [x] desktop/main.js (Electron cockpit): secret lifted to module scope (`UI_SECRET`), `uiUrl()`/`stackHealthy()`/`chooseWorkspace()`'s fs/root POST all pass it
- [x] Smoke-tested live on a throwaway port: no-key→401, wrong-key→401, correct-key→200+cookie, cookie-only follow-up→200, `?demo=1`→200 bypass, `/health` unauthenticated→200 — all as designed
- [x] Deployed server.py + start.ps1 to `~/.grok/plugins/grok-remote/`; desktop/main.js is NOT part of the installed plugin (repo-only, run via `npm start` in `desktop/`) — fixed in the repo copy only
- [ ] Anthony: re-pair phone with the new `connect.url` (old bookmarked link with no `?key=` will now 401 once)
