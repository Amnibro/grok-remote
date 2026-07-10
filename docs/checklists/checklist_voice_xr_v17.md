# Checklist: voice + conversational + XR/AR (v17)

- [x] Scan architecture_map.md
- [x] Guardian council (`docs/guardian_councils/guardian_council_voice_xr.md`)
- [x] Backup web/index.html, cockpit-features.js, server.py
- [x] Server: POST /api/tts + GET /api/voice/status (xAI Grok TTS proxy)
- [x] web/voice-mode.js: STT, hands-free Go, XR HUD, ack+summary TTS
- [x] Wire UI (Dictate / Go / XR, HUD, menu, turn hooks)
- [x] Wire ack+summary into session flow (onTaskSent / onTurnDone)
- [x] Voice acks for Queue / FYI / Interject delivery modes (v18 bridge)
- [x] Sync ~/.grok/plugins/grok-remote (hashes match)
- [x] architecture_map.md + changelog.md (v17 section)
- [ ] User: hard-refresh UI, restart server for /api/tts, set XAI_API_KEY for real Grok voice
