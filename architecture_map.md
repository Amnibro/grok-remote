# Grok Remote — architecture map

**Updated:** 2026-08-18 · v1.9.5 auth cookie sliding refresh
## Auth cookie lifecycle (v1.9.5)
- `auth_mw` accepts `?key=` OR `grok_remote_key` cookie OR `X-Grok-Remote-Key` header; loopback
  bypasses. The WS handshake auths by cookie alone (client ws url never carries the key).
- **Every authenticated response now re-sets the 30-day cookie** (`supplied==token`), so the
  window slides with use. Before v1.9.5 only `?key=` requests (or loopback) refreshed it — a
  phone that paired once by QR hit a hard 30-day expiry: silent 401s on page + WS, nothing in
  the hub log (rejected before "client join"), /health green. Desktop tabs were immune via the
  loopback branch — "phone dead, PC fine" is the fingerprint of an expired cookie.
- Re-pair without touching the phone: `adb shell am start -a android.intent.action.VIEW -d
  "<keyed url from connect.url>"`.

**Updated:** 2026-08-19 · v1.9.5 Braid markdown + Work dock
## Chat format + Work (v1.9.5)
- `web/md.js` (from Braid) paints agent/user bubbles; KaTeX still queued after HTML.
- `web/work-dock.js` `#gwk` sheet: Work feed from `upsertTool`, Files via `/api/fs/*`.
- Command deck **Work**. Live stream already re-renders the full bubble per chunk.

**Updated:** 2026-08-18 · v1.9.3 pair phone + one-line session filters
## Pair + session rail (v1.9.3)
- Orbit menu + command deck Help: **Pair phone**. Loopback → `/pair`; LAN → Setup QR card.
- Session chips: Active / Live / Arch / All only. No cwd-origin "module" chips.
- `.sess-scope-rail` is nowrap + overflow-x auto (braid and base).
- Default brand GROK BUILD. Dead AMNI product skins remapped to Grok. Amni-Delve off the Apps menu.

**Updated:** 2026-08-17 · v1.9.2 hidden-tab persistence
## Hidden tab persistence (v1.9.2)
- **A browser tab cannot keep its own link alive.** Chrome throttles background timers and drops
  them to roughly once a minute after 5 minutes hidden. Any client-side "nothing arrived for N
  seconds, reconnect" rule therefore fires on a perfectly healthy socket. Liveness must be pushed
  from the hub: `_watch_loop` broadcasts `_x.ai/remote/hub` every 15s while clients are connected,
  and `ws.onmessage` stamps `linkLastRx` on every frame, so **no client timer is required**.
- `WebSocketResponse(heartbeat=12,autoping=True)` is NOT enough. Protocol pings are answered inside
  the browser's network stack and never reach `onmessage`, so they keep the TCP connection open
  while the app still believes the link is dead.
- Three client gates must stay consistent: `startPoll` (catch up every 15s while hidden, not never),
  `startLinkKeepalive` (never force-close from a hidden tab), `scheduleReconnect` (back off to 30s
  while hidden, never park forever — the old code re-parked on every retry).
- **Server-side persistence was already correct** and is not the bug: `handle_client` logs
  "client leave · in-flight turns stay on hub", `_watch_loop` keeps the agent connection with zero
  clients, and `LoopJobs._run` fires on its own task. A turn does not need a browser.
- Testing note: pages opened through CDP report `visibilityState:"visible"` even when another tab is
  selected, and minimising the window does not reach them. A hidden-tab claim cannot be verified
  through that harness — measure the server half in isolation and check the tab by hand.


**Updated:** 2026-08-14 · v1.8.2 stale-link loop
## Stale-link / attach (v1.8.2)
- Client pings answered in the hub read loop (never queued behind `session/load`).
- Hub→agent: no WS heartbeat; `ClientTimeout(total=None)`.
- `session/load` 90s; stale reconnect only after 45s idle and empty RPC queue.
- Agent spawn is `grok.exe` directly (cmd wrapper missed the bind).

**Updated:** 2026-08-14 · v1.8.1 mirror grok-build
## Mirror grok-build (v1.8.1)
- Serve stays `--no-leader` so `:2419` binds (`--leader serve` attaches to TUI and never listens).
- Never `claim_port(:2419)` unless explicit force. Healthy UI/agent left alone on `/remote` start.
- Disk catch-up always runs (0.5–0.9s) so grok-build `updates.jsonl` paints on the phone.

## Radio + pair (v1.8.0)
- Cheap `GET /health` (no initialize). `GET /health/deep` for agent handshake.
- `GET /pair` loopback-only via `pairing.py`. QR SVGs get a `viewBox` (segno does not emit one) so CSS scale cannot clip the modules.
- Client: `#radioChip` RTT, `#chatMeta` cwd/sid, WS-first catch-up, faster reconnect.
- Braid: session cwd always shown; livebar extra visible.
**Updated:** 2026-08-12 · v39 chat load fast (long sessions)

## Chat load fast (v39)

| Piece | Behavior |
|-------|----------|
| Session index | `_rebuild_sid_index` maps sid→dirs (~2980 sessions, 130ms); 60s TTL; per-lookup cache 90s. A miss forces a rebuild **at most once per 5s** — unthrottled it cost 250 rebuilds per titles batch (19s stall) |
| Titles batch | `session_titles` resolves up to 250 sessions **in the executor**. On the event loop it froze every other handler while it worked |
| chat_only scan | Byte prefilter (`user_message_chunk` / `agent_message_chunk`); grow window up to **64MB**, reading only the newly exposed older prefix each round; coalesce **once at the end** (`_coalesce_chat` mutates its inputs, so per-round coalescing double-appends text) |
| Payload | `_trim_chat_text` caps event text at 120k |
| First paint | `HISTORY_PAGE=24`, `HISTORY_MAX_BYTES=450k`, chat-only only (no full-history fallback) |
| Client paint | Fast plain/code stubs while `historyPainting`; `upgradeRichBubbles` rAF after open |
| Older | Scroll-up loads chat_only pages (`max_bytes` 1.2M) |
| DOM | `FEED_DOM_CAP=72` |

## Stay-up + simple open (v38.2)

| Piece | Behavior |
|-------|----------|
| Supervisor | `scripts/supervise-ui.ps1` — health loop, respawn UI on death |
| Launch | Desktop **Grok Remote** → `ensure-running` (agent if needed + supervise) → `open-remote-ui` with `?key=` |
| Setup UI | Phone 3-step card (copy / QR / open PC); advanced under `<details>` |
| Chat open | v39: see **Chat load fast** |
| Memory | `FEED_DOM_CAP=72`, thought stubs on history, poll 1.2s, no catch-up when tab hidden |

## Session isolation (v38.1)

| Piece | Behavior |
|-------|----------|
| Titles | `POST /api/session/titles` hydrates rail from `summary.json` (`remote_title` / `generated_title` / `session_summary`) |
| Open | History response `title` applied via `adoptDiskTitle` so chat isn’t stuck as Untitled |
| Live busy | `busySid` + `setBusy(b, forSid)` — tools/thinking phase only for open session |
| Hub noise | `_x.ai/remote/client_rpc` / auto_permission ignored unless this session is busy |
| Events | Disk paint requires exact `params.sessionId` match; no 8-char fuzzy accept |
| Dir resolve | Multi-hit `find_session_dir` prefers cwd-encoded path before newest mtime |

## Wireless link (v38)

| Piece | Behavior |
|-------|----------|
| Client keepalive | App ping `_x.ai/remote/ping` every ~7–10s when idle; force reconnect if silent >40s |
| Reconnect | Never permanently gives up while page open; slow park after max tries; reset on visibility/`online` |
| Single-flight | `connectGen` + short settle after closing old socket (stops n=2 thrash from dual loops) |
| Soft drop | On WS close: keep **HTTP disk catch-up poll** so chat still moves; PC turn stays on hub |
| Cockpit | Removed second reconnect interval (was fighting main UI) |
| Hub | Client WS heartbeat 12s; hub watch re-ensures agent; responds with `_x.ai/remote/pong` |

## Detach-safe turns (v37.7)

| Piece | Behavior |
|-------|----------|
| Soft close | Phone leave does not cancel PC turns; hub detaches reverse-RPC to itself |
| Resume | `visibilitychange` / `pageshow` / `online` re-arm reconnect and catch-up |

## Chat rename (v37.5)

| Piece | Behavior |
|-------|----------|
| UI | Session **Rename**, dbl-click title, `#chatTitle`, Command deck **Rename chat** |
| API | `POST /api/session/rename` `{sessionId,title,cwd?}` |
| Disk | `~/.grok/sessions/.../summary.json` → `remote_title` + `generated_title` |
| Local | `localStorage.grok_remote_titles` mirror (works if API fails) |
| Display | `sessionTitle()` prefers override → `remote_title` → `title` |

## Orbit status (v37.5)

| Piece | Behavior |
|-------|----------|
| Location | Header top-right cluster (`#orbit` + `#orbitStatus`) |
| States | offline / connecting / online / sync|think|tools|live / error |
| Visual | multi-ring SVG, dual sats, halo, LED corner, status pill |
| Header | `#status` text hidden (orbit owns “online”) |

## Layout skins (v37 → v37.1)

| Piece | Behavior |
|-------|----------|
| Default | **Braid** — clean shell; chat column uses full center width (`--braid-chat-pad`); bubbles up to ~920–1120px |
| Legacy | Previous mission-control chrome (pulse frames, orbit glow, denser cards, full filter stack) |
| Storage | `localStorage.grok_remote_layout` = `braid` \| `legacy` |
| URL | `?skin=braid` or `?skin=legacy` (not `?layout=` — that forces desktop/mobile width) |
| CSS | `web/braid-layout.css` gated by `html[data-layout="braid"]` |
| Controls | Setup + Theme sheet **Layout** chips; Command deck **Layout** toggles |
| Sessions rail (braid) | Compact head: **+ New chat** + refresh; one-line **Active / Live / Arch / All**; **⌕** opens **fixed** search/scope pop (`z-index:20060`); list always shows **top 3**, then **▸ N more** → **Older** section / **▴ Show less** (open chat kept in top set) |
| Livebar (braid) | link + phase + perm + effort; **···** expands git/cost/hint |

Early bootstrap in `<head>` sets `data-layout` before paint to avoid FOUC.

## Chat chrome (v36 → v36.2)

| Piece | Behavior |
|-------|----------|
| Sessions rail | **+ New chat** + Refresh only (no New task button) |
| Command deck (9-dot) | No New task / Sessions menu rows; Skills + Delivery remain |
| `paintLocalUserTurn` | One You bubble: stripped text then image/file previews |
| Echo skip | Do not pre-set `lastLocalUserPlain` before local paint; keep media nodes when re-rendering text |
| `selectedSid` / `paintSessionCurrent` | Rail `.current` + open badge follow the chat in the feed; set on open/new before async load finishes |

## Endpoint auth (v35)

Every HTTP/WS route runs through `make_auth_middleware(token)` in server.py, keyed on the existing `--secret` (already required at startup; already a fresh random value each launch via `start.ps1`/`desktop/main.js` — reused, not duplicated).

| Piece | Behavior |
|-------|----------|
| Bootstrap | First request with `?key=<secret>` in the query string is checked, then an httpOnly cookie (`grok_remote_key`, 30d) is set on the response |
| Steady state | Cookie sent automatically by the browser on same-origin fetch/WS — **no client JS reads or sends the key itself** |
| Fallback | `X-Grok-Remote-Key` header also accepted (non-browser callers) |
| Exempt | `?demo=1` (privacy-safe sample data, screenshots) and `/health` (boolean + sanitized string; polled unauthenticated by `ensure-running.ps1`, `start.ps1`'s own check, and the desktop cockpit before the stack — even — is known to be up) |
| Pairing | `connect.url` and printed links embed `?key=$Secret`; a link generated before v35 needs a fresh `start.ps1` run to pick up the key |
| Desktop cockpit | `desktop/main.js` holds one `UI_SECRET` for the window load, health poll, and fs/root POST — repo-only, not shipped with the installed plugin |

## Session noise filter (v1)

Automated Azno market-watch co-pilot ticks create a **new Grok session every run** (titles like *Azno Market Watch…*, *Market Watch Co-Pilot…*, *Azno TA Cache JSON to Ticker Verdicts*). Amni-chat/azno watchdog-style titles are treated the same.

| Piece | Behavior |
|-------|----------|
| `isNoiseSession(s)` | Title/cwd heuristics for market-watch, co-pilot ticker verdicts, TA cache OHLCV probes, amni-chat/azno watchdog labels |
| `normalizeSessions` | Drops noise from the in-memory list after `_x.ai/sessions/list` |
| `renderSessions` / `pickBestSession` | Defense-in-depth: never paint or auto-open noise |

Does **not** delete disk sessions under `~/.grok/sessions/` — only hides them from the remote chat rail.

## Layout

```
grok-remote/
  web/index.html          # Phone + browser + Electron UI (default theme: grok; default layout: braid)
  web/braid-layout.css    # BRAID shell overrides (data-layout=braid)
  web/voice-mode.js       # STT / conversational Go / XR HUD / Grok TTS playback
  web/ide.js              # Built-in IDE + Grok Review
  server.py               # static + /ws proxy + /api/fs/* + /api/tts
  start.ps1               # agent + UI launch
  scripts/capture-screenshots.mjs  # demo=1 Playwright PNGs for README
  scripts/launch-desktop.cmd
  desktop/                # Electron cockpit (auto-stack)
  docs/screenshots/       # public spoiler shots only
  skills/remote/
  commands/
  hooks/hooks.json
  config.default.json
```

## Privacy / spoiler (v14)

| Piece | Behavior |
|-------|----------|
| `body.privacy` | Blurs titles (`.sess .item .t`), paths, IDs, setup inputs, tool locs |
| Badge | Default `SPOILER ON · private screen`; Alt only if `can-hover` + `desktop` |
| `?demo=1` | Fake sessions + sample chat; no agent; safe for git screenshots |
| `?privacy=1` / `variant=` | Force spoiler / theme for captures without localStorage leaks |

## Cockpit v4

- Electron start → agent `:2419` + UI `:2421` without daily terminal
- IDE panel: workspace tree, tabs, save via `/api/fs/write`
- Grok Review: structured post-edit prompt into active session

## SpaceXAI chrome (v3.2 → v4.1)

| Element | Behavior |
|---------|----------|
| `#orbit` | SVG planet + satellite; `.on` green planet + orbit spin; `.busy` accent planet + fast spin; `.off` red planet paused |
| `.pulse-frame` | Thin theme-accent border with slow `frame-pulse` on header, setup, picker rail, feed, footer |
| Status copy | Livebar: `uplink` / `sync · burn…` / `standby` (mission-control tone) |
| Design tokens | `--ease`, `--dur`, `--elev-*`, `--glass`, `--hairline` |
| Grok variant | Full greyscale chrome (black/zinc); syntax tokens stay colored in code panes |
| Motion | Row enter (`row-in`), hover lift ≤2px, focus rings, pill chrome, thin scrollbars |
| Ambient | Soft accent radial + faint grid mask (disabled on retro themes) |
| `#chatStage` | Chat column wrapper; `#horizonLoad` overlays **only this area** (above footer/composer) |
| Horizon | Accretion-disk loader + rotating space puns during session open/new |

Session isolation: `sessionGen`, `sessionSwitching`, `loadExpectSid`. Unscoped `session/update` only accepted during intentional load when `loadExpectSid===sid`. New chat clears `sid` first, re-clears feed after `session/new`, never sets `loadExpectSid`.

## Chat chrome (v36)

| Piece | Behavior |
|-------|----------|
| Sessions rail | **+ New chat** + Refresh only (no New task) |
| Command deck | No New task / Sessions entries; Skills + Delivery remain |
| `paintLocalUserTurn` | One You bubble: stripped text + image/file previews |
| Echo skip | Do not set `lastLocalUserPlain` before local paint; media nodes preserved on text re-render |

## Composer bind (v33)

| Piece | Behavior |
|-------|----------|
| `composerBoundSid` | Set on composer `input` / `focus` to the open chat id (log where typed) |
| `composerDrafts[sid]` | Saved on chat switch; restored on open |
| `resolveSendSid()` | Prefers `composerBoundSid`, else live `sid` |
| `sendPrompt` | Freezes send target via resolve; does not overwrite bind from live `sid` if already set |
| `dispatchPromptPayload` | Always `session/prompt` with pinned `sessionId`; `allowCrossSession` for off-screen send |

## Detach-safe turns (v37.7)

Navigating away / phone sleep / tab background **must not cancel** the PC agent turn.

| Piece | Behavior |
|-------|----------|
| Hub reverse RPC | Hub fulfills `fs/*`, `terminal/*`, `session/request_permission` on the PC — **no phone required mid-tool** |
| Client leave | In-flight `session/prompt` RPCs are **detached** (reparented to hub), not cancelled |
| Soft WS close | UI keeps `sid`, does not reject prompts as errors; phase → `sync · bg on PC` |
| Reconnect | `visibilitychange` / `pageshow` / `online` re-arms reconnect; resume same session + disk catchup |
| maxReconnect | 80 (and keeps retrying while tab hidden) |

## Live status + sessions (v7)

| Piece | Behavior |
|-------|----------|
| Footer `#livebar` | `link` + phase: idle / waiting for response / thinking / responding / running tools |
| `setPhase` / `setBusy` | Driven by prompt send, thought/message/tool chunks, turn_completed, queue |
| Session list | Unwrap nested `result.sessions`; sort by `lastChangeUnixMs`; highlight open |
| Auto-open | After connect, open best session (cwd match + newest) unless `?session=` / `?task=` |
| Agent serve | `grok agent --always-approve --no-leader serve` (not `--leader serve`) |
| Hub | Retry ensure, cache initialize for multi-client, keep UI WS when agent flaps; reverse RPC owned by hub |

## Feature tour (v6)

| Entry | Behavior |
|-------|----------|
| Header **Tour** / setup **Feature tour** | Spotlight walkthrough (`#tourOverlay`) |
| First visit | Auto-start unless `localStorage.grok_remote_tour_done=1` |
| `?tour=1` | Force tour |
| **Paste tutorial prompt** | Composer + clipboard: product walkthrough script for Grok |

Pin: `POST /api/stack/shortcut` runs `scripts/install-shortcut.ps1`. Do **not** re-import `subprocess` inside `main_async` (scope bug).

## UI UX prefs (`web/index.html`)

| Key (`grok_remote_ux`) | Default | Effect |
|------------------------|---------|--------|
| `autoScroll` | true | Follow feed when `stickBottom` |
| `borders` | true | `body.bordered` vs `body.clean` |
| `collapseThink` | true | New/existing thought rows start collapsed |
| `collapseCode` | true | Fenced code blocks start collapsed |
| `collapseTools` | false | Tool cards start collapsed if true |

Controls: setup **UI / UX** chips + **Theme** sheet → same chips.  
**↓ Bottom** FAB always visible in chat (dims at end); click forces scroll to latest + re-enables auto-scroll.

## Sessions rail

- Independent scroll: `html/body` overflow hidden; `#picker` flex column; `.sess` list scrolls alone; `main` scrolls alone.
- **Search** text filter + **Scope** chips: Active (default) / Live / Archived / All
- Archive: per-row button; IDs via `POST /api/session/archived` (`ids[]` or `{id, archived}`) + localStorage mirror
- Scope: `localStorage.grok_remote_sess_scope`
- **Promote on message (v16):** `promoteSessionAfterMessage` on send — unarchives (`setArchivedFlag(id,false)`), marks `resident`+live, leaves Archived → Active, re-renders list + `fetchSessions`

## Voice + XR + Watch (v17 → v19)

| Piece | Behavior |
|-------|----------|
| **Mic** | Composer button next to `+` and box (`#btnComposerVoice`) → Go voice |
| **+** | **Attach only** (file picker) — no specials tray |
| **Specials** | ☰ menu **Tools** (Todos, Terminal, Git, Export, …) |
| **Chat view** | ☰ toggles: hide thinking / tools / edits / reads / code + collapse defaults |
| **XR / AR** | Auto-detect via `navigator.xr` (prefer AR); wearable UA → auto Go/XR; button shows when capable |
| **Watch** | `/watch` Galaxy/Wear OS companion (round UI, mic, session sync via `grok_remote_last`) |
| **Spoken replies** | Ack on send; summarized final answer on turn complete |
| **TTS** | `POST /api/tts` → xAI Grok TTS (`XAI_API_KEY`); else `speechSynthesis` |

Safety: Go/XR designed for glanceable status; full tool dumps are not spoken.

## Message delivery modes (v18)

| Mode | When agent busy | Behavior |
|------|-----------------|----------|
| **Interject** | Cancels current turn (`session/cancel`), then sends immediately with interject framing | Drop in-flight steps; handle user now |
| **Queue** (default) | Enqueues locally; drains on `turn_completed` / prompt resolve | Wait for a good pause, then apply guidance |
| **FYI** | Enqueues as context; never cancels | “Consider this; don’t stop the task” framing |

- **Send** always sends (never morphs to Cancel)
- **Cancel** (`#btnCancelTurn`) separate, visible only while busy → `session/cancel`
- Queue UI: `#queue` shows remote pending + agent queue note; dismiss with ×
- Pref: `localStorage.grok_remote_msg_mode`

## Themes

- `data-variant` + `data-mode` on `<html>`
- Product: scient, grok, ai, explore, calc, learn, crypt, haven, core
- X-like skins (UI labels): AIM-like, Win95-like, C64-like, Atari-like, Ubuntu-like, Matrix-like, DOS-like, Amiga-like
- Modes: dark, light
- Storage: `grok_remote_variant`, `grok_remote_mode`, `grok_remote_theme`

## Runtime ports (defaults)

| Service | Bind | Port |
|---------|------|------|
| Agent serve | 127.0.0.1 | 2419 |
| UI + WS proxy | 0.0.0.0 / LAN | 2421 |

## Chat rendering

- Agent/user bubbles run through `renderMdBlock` + fenced `makeCollapsibleCode`
- `highlightCode` → theme-token spans (`.tok-kw`, `.tok-str`, `.tok-num`, `.tok-cmt`, …)
- Attachments: `pendingFiles` → ACP content blocks (`text` / `image` / `resource`)
- Composer: `#btnAttach` + `#filePick` + `#attachBar`

## Chrome UX

- Sheets (theme/skills/task): translucent top-right flyouts (`.sheet` + fly-tr)
- Sidebar: `body.sidebar-collapsed` collapses desktop rail; `#railTab` reopens; storage `grok_remote_sidebar`

## Mobile viewport (v20)

| Piece | Behavior |
|-------|----------|
| `syncVisualViewport` | On composer focus, pin `body` to `visualViewport` height/top (`body.kb-open`) |
| `measureBottomStack` | Feed `padding-bottom` from measured `#foot` height (+ clearance) |
| `keepComposerInView` | Scroll feed so footer + textarea clear VV bottom |
| Orientation | `hardResetViewportShell` + multi-stage reflow; width/height flip treated as rotate |
| Desktop gate | `min-width:900` alone is not enough — need height ≥520 or fine pointer (blocks phone landscape rail) |
| `body.phone-landscape` | Compact single-column chrome while rotated |

## Deploy path

Installed plugin web root: `~/.grok/plugins/grok-remote/web/index.html`  
(Copy from repo after UI changes; hard-refresh clients.)
