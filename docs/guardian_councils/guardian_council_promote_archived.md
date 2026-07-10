# Guardian council: archived session → live after message

**Task:** After messaging an archived session, session list auto-refreshes as live (unarchived).

## Proposals

| Guardian | Approach | Vote |
|----------|----------|------|
| Architect | On `session/prompt` send: unarchive via `POST {id, archived:false}`, mark `resident`+live, leave Archived scope → Active, `renderSessions` + `fetchSessions` | yes |
| Sentinel | Do not trust list-merge alone; pin-id unarchive API so server+local stay consistent; re-assert live after fetch | yes |
| Scholar | Existing `promoteSessionAfterMessage` exists in repo but **not** in plugin copy — sync is required; one-way archive merge can re-archive if local lags | yes |
| Engineer | Promote early in `sendPrompt` (after validation), not only after WS write; remove block comments in promote | yes |
| Pathfinder | Always show under Active with live badge even if agent list still says dormant until resident | yes |

## Decision (majority)

Implement Architect+Sentinel+Engineer: single-id unarchive, optimistic live mark, scope switch, immediate render, post-fetch re-assert, sync plugin.
