# Checklist: promote archived → live on message (v16)

- [x] Scan architecture_map.md
- [x] Guardian council
- [x] Backup web/index.html → backups/index.html.v16.bak
- [x] Harden promoteSessionAfterMessage (unarchive API, live badge, scope, list refresh)
- [x] Call promote on send (optimistic) + on prompt resolve
- [x] Fix loadArchive merge (server wins unless migrate)
- [x] Sync ~/.grok/plugins/grok-remote
- [x] Update architecture_map.md + changelog.md
- [ ] User confirms: archive a chat → message it → list shows live under Active
