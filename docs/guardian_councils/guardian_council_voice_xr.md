# Guardian council: voice + conversational + XR/AR

**Task:** On-the-go voice-to-text, conversational access, XR/AR smartwear shell; spoken replies = task-receipt ack + summarized final answer via real Grok TTS.

## Proposals

| Guardian | Approach | Vote |
|----------|----------|------|
| Architect | Server proxy `POST /api/tts` → `api.x.ai/v1/tts`; client hands-free STT (Web Speech) + TTS play; XR HUD mode (`body.voice-xr`) | yes |
| Sentinel | Never expose `XAI_API_KEY` to browser; fallback `speechSynthesis` if no key; keep driving UX glanceable (large type, few taps) | yes |
| Scholar | Speak only ack + short summary (not full tool dump); strip markdown/code before TTS | yes |
| Engineer | New `voice-mode.js`; hook send + turn_completed; continuous listen with pause-to-send; optional WebXR AR | yes |
| Pathfinder | Modes: Dictate · Go (conversational) · XR/AR; voice_id `eve` default, user pickable | yes |

## Decision

Majority: Architect+Sentinel+Engineer — proxy TTS, conversational Go mode, XR shell, ack+summary only, browser STT + Grok TTS with speechSynthesis fallback.
