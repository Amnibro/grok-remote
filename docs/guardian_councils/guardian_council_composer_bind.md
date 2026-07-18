# Guardian council — composer bind (log where typed)

## Question
Send always goes to the chat where text was typed, not the global `sid` at await completion.

## Architect
Pin target at type-time via `composerBoundSid`; drafts per session on switch. Majority: ship.

## Sentinel
Do not re-stamp bind from live `sid` on send (race). Cross-session dispatch only with explicit bind. Approve.

## Scholar
Matches message apps: draft owns a thread; send targets draft owner. Approve.

## Engineer
`stampComposerBind` on input/focus; `resolveSendSid`; queue items carry `sessionId`. Approve.

## Pathfinder
Chip when send lands off-screen. Approve.

## Ruling
5–0 ship type-time bind.
