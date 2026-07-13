# Guardian Council · SpaceXAI beauty + session isolation

Task: Modern/simplistic SpaceXAI UI (pulse borders, orbital status) + fix new-chat pulling old history.

## Architect
Single-file CSS tokens already drive themes. Extend with orbit + pulse-frame primitives bound to `--acc` / `--ok` / `--bad`. No new build step. Keep Electron + mobile layouts untouched structurally.

## Sentinel
New-chat bleed is a race: `session/load` / softCatchup can paint unscoped or stale events while `sid` flips. Require `sessionId===sid` always; unscoped only when `loadExpectSid===sid` and intentional replay. `sessionGen` + `sessionSwitching` must freeze catchup and abandon in-flight reloads.

## Scholar
SpaceX / mission-control cues: thin luminous borders, sparse chrome, status as satellite-around-planet (not traffic-light dots). Motion only for state (orbit when up, faster when busy, red planet offline). Prefer CSS animation over JS.

## Engineer
Patch `web/index.html` only. CSS: `.orbit-*`, `.pulse-frame`, remove `.dot`. JS: `loadExpectSid`, fix `silentReload` finally, single `touchLive`, gate `handleUpdate`. Deploy copy to installed plugin path.

## Pathfinder
Ship CSS+isolation first (v3.2), hard-refresh clients. Optional later: Lottie/WebGL backdrop — not needed for official-app feel if borders + orbit are crisp.

## Decision (majority)
Engineer + Architect + Sentinel + Scholar path: CSS orbit/pulse + strict session gating in-place. No new assets. Pathfinder agrees ship-now.
