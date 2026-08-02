# Checklist — detach-safe turns (navigate away)

- [x] Scan architecture_map / hub / client close path
- [x] Root cause: reverse RPC hub fulfillment missing; client rejects prompts on WS close
- [x] Backup server.py + index.html
- [x] Restore HubTerminal + `_handle_reverse` (fs/terminal/permission) on hub
- [x] Detach in-flight prompts on client leave (no cancel; reparent pending)
- [x] UI: soft-close does not fail the turn; keep session; visibility reconnect
- [x] Restart remote UI to load server.py (health ok=True hub_up=True)
- [x] Update architecture_map.md + changelog.md
- [ ] User confirms: leave page mid-turn, work continues, return sees result
