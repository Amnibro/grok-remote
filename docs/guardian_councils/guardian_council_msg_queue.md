# Guardian council: remote message queue modes

**Task:** Interject / Queue / FYI delivery + separate Cancel beside Send.

## Proposals

| Guardian | Approach | Vote |
|----------|----------|------|
| Architect | Mode chips + local queue; Interject→`session/cancel` then prompt; Queue flush on `turn_completed`; FYI wrapper no cancel | yes |
| Sentinel | Send always sends; Cancel is dedicated; never hijack Enter for cancel when composing | yes |
| Scholar | Prefix framing so agent understands priority; paint queue with dismiss | yes |
| Engineer | Extend `sendPrompt(mode)`; `msgQueue[]`; `paintMsgQueue`; wire Cancel to `stopTurn` | yes |
| Pathfinder | Default mode **Queue** (safer on phone); persist `grok_remote_msg_mode` | yes |

## Decision

Majority: full three modes + separate Cancel; Queue default; FYI never cancels current work.
