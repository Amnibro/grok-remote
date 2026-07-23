# Changelog

## 2026-07-23 — Fix the desktop shortcut breaking under v35 auth (v35.1)

- **Symptom:** double-clicking "Grok Remote.lnk" opened the browser to a raw `{"error": "unauthorized ..."}` JSON response instead of the UI.
- **Cause 1:** `launch-remote.cmd` still opened the hardcoded `http://127.0.0.1:2421/?auto=1` with no key — it predated v35's auth requirement and was never updated. A first-pass fix tried extracting the secret via a nested `for /f` + inline PowerShell inside batch, which is exactly as fragile as it sounds and doesn't reliably run before the server's first-ever `connect.url` write completes anyway (a flat 2-second `timeout` before opening the browser, vs. the stack's actual multi-second boot time).
- **Cause 2 (the sneaky one):** the PowerShell fix-attempt itself, `scripts/open-remote-ui.ps1`, used an em-dash (`—`) inside a double-quoted string. Windows PowerShell 5.1 run via `-File` on a BOM-less UTF-8 script can misread that multibyte character and lose track of the string terminator — `"The string is missing the terminator"` — silently killing the script. `start.ps1` had the identical landmine in a `Write-Host` line, unrelated to this bug but caught by the same sweep. Same failure class as the changelog mojibake fixed earlier this session; scanned every `.ps1` in the repo and parse-checked all of them with the real Windows PowerShell tokenizer — all clean now.
- **Fix:** `launch-remote.cmd` now calls `scripts/open-remote-ui.ps1`, which polls `/health` (unauthenticated, exempt from auth) for up to 25s, then reads the already-correct `connect.url` (written by `start.ps1` as its last boot step, always carrying the current key) and opens *that* — no manual secret extraction anywhere. Falls back to a plain unkeyed URL with a console warning only if the stack genuinely never came up in time.
- Deployed to `~/.grok/plugins/grok-remote/`; live-tested end to end against a running instance (silent success = healthy path, correct keyed URL read from `connect.url`).

## 2026-07-23 — Auth: gate every endpoint behind the pairing secret (v35)

- **Gap:** none of the HTTP/WS endpoints required authentication — anyone on the LAN who found `:2421` could read/write any file under the workspace, inject prompts into any session, or kill the stack via `/api/stack/stop`. Called out as deferred (C1) at the end of the v34 bug sweep.
- **Fix:** every route now runs through `make_auth_middleware`, keyed on the existing `--secret` (already required at startup, already a fresh random value per launch — no new secret to manage). First request with `?key=<secret>` sets an httpOnly cookie; the browser then carries it automatically on every same-origin fetch/WS call, so **no client JS changes were needed**.
- **Exemptions:** `?demo=1` (privacy-safe sample-data mode, used for screenshots) and `/health` (a boolean + sanitized string, polled unauthenticated by three existing local scripts that don't know the secret ahead of time — persisting a shared-secret file for them was more machinery than the exposure justified).
- **Pairing:** `connect.url` and the printed "open on your phone" links now embed `?key=$Secret`. **Old bookmarked links without the key will 401 once — re-pair from a fresh `start.ps1` run.**
- **Desktop cockpit:** `desktop/main.js` now shares one `UI_SECRET` across window loads, the health poll, and the workspace-picker's `/api/fs/root` call (repo-only; not part of the installed plugin, which doesn't ship the Electron app).
- Live-smoke-tested on a throwaway port: unauthenticated → 401, wrong key → 401, correct key → 200 + cookie set, cookie-only follow-up → 200, `?demo=1` → 200, `/health` → 200 unauthenticated.

## 2026-07-23 — Hide Azno/amni watchdog sessions from chat list (v1)

- **Symptom:** remote session rail flooded with *Azno Market Watch*, *Market Watch Co-Pilot*, *Azno TA Cache…* chats — one new session per automated market-watch co-pilot tick (~hourly), plus similar watchdog labels
- **Cause:** Azno co-pilot spawns real Grok sessions (`azno-v2` cwd); list showed every ACP session as a human chat
- **Fix:** `isNoiseSession()` title/cwd filter; applied in `normalizeSessions`, `renderSessions`, and `pickBestSession` so noise never lists or auto-opens
- Does not delete disk history; hard-refresh remote UI after deploy
- Backup: `backups/index.html.v_noise_sessions.bak`
- Checklist: `docs/checklists/checklist_noise_sessions_v1.md`

## 2026-07-22 — Bug sweep: security, correctness, reliability (v34)

**Security**
- `esc()` never escaped `"`/`'`; autolinked URLs (`https?://[^\s<]+`) inject straight into `href="$2"` — a URL containing a quote could break out into a live attribute/event handler (stored XSS from any agent/tool output). Fixed: `esc()` now escapes quotes too.
- Agent connection secret (`?server-key=...`) could leak into `_last_err` on a handshake failure, surfaced verbatim on unauthenticated `/health` and `/api/stack/status`. Fixed: sanitized before storing.
- `_pump`'s cleanup path called `self._reader.cancel()`/`await self._reader` on itself when disconnect cleanup ran from inside the pump task — broke cleanup of the client `pending` map and `_rpc_futs` (both silently orphaned, hanging in-flight RPCs up to their full timeout). Fixed: guard against self-cancel; both maps are now rejected/cleared on disconnect.
- `netstat` port matching was substring-based (`:2421` matched `:24210`) — `claim_port`/`wait_port` could kill an unrelated process or falsely report a port bound. Fixed: exact port match on the parsed local-address column.
- `static` handler's root-containment check was missing the path-separator boundary (matches the class of bug `under_root()` already guards against). Now reuses `under_root()`.
- Agent-initiated requests (e.g. permission prompts) are broadcast to every connected client; every client's response was forwarded verbatim, so the agent could receive multiple responses to one request. Fixed: only the first response per broadcast request id is forwarded.

**Correctness**
- `msgQueue` (the cross-session remote message queue) was wiped on every chat switch (`clearSessionFeed`) and on reconnect — queued Queue/FYI messages vanished silently. The queue is already per-item session-tagged and `drainMsgQueue` already gates on it; neither function needed to touch it. Removed both wipes.
- `newSession` never stamped `composerBoundSid` — a stale bind from the previous chat could route a brand-new session's first message to the old chat instead. Now stamped on success, cleared on failure.
- `drainMsgQueue` only requeued on a thrown exception; a `false` return from `dispatchPromptPayload` (not connected, empty prompt, mid-switch) dropped the item while the feed still showed it as sent. Now requeues on `false` too.
- WebSocket `onclose` never rejected the `pending` RPC map — in-flight sends orphaned on disconnect instead of failing fast.
- ide.js: `reviewDirty`'s per-file save loop mutated `state.active` without calling `activate()`, so the editor kept showing the previously-open file while `onEditorInput` (keyed on `state.active`) wrote new keystrokes into the wrong tab's buffer — a subsequent save could write file A's content into file B on disk. Fixed: use `activate()`; `onEditorInput` now keys off the editor's own `dataset.rel`.
- ide.js: `saveActive` cleared the dirty flag unconditionally after `await`ing the write — edits typed during the network round-trip got silently marked clean (and could be discarded by `closeTab` with no warning). Now only clears dirty if the content is still what was saved.
- ide.js: Ctrl+Shift+S never fired `reviewActive` (uppercase `"S"` never matched the lowercase check) and, on platforms reporting lowercase, would have fired both save and review at once. Fixed.
- ide.js: `closeTab`'s tab-0 fallback skipped `activate()`, leaving the status line and tree highlight pointing at the closed file.
- voice-mode.js: `stopSpeak()` (the "Quiet" button) called `audioEl.pause()`, which fires neither `onended` nor `onerror` — the `grokSpeak` promise the drain loop was awaiting never settled, permanently hanging that loop and leaking the blob URL. Fixed with an explicit settle path invoked by both natural completion and manual stop.
- voice-mode.js: a fatal mic error (`not-allowed`, `audio-capture`, `service-not-allowed`) in Go/XR mode triggered an infinite `onend`→restart→`onerror` loop, flooding the feed with a chip roughly every 400ms. Fixed: fatal errors now stop voice mode instead of retrying.

**Reliability**
- Live-tail polling (`read_session_updates(..., live=True)`) could read a partial trailing line mid-write from the agent, fail to parse it, and still advance `end_pos` past it — permanently dropping that event from the stream. Fixed: trim the read to the last complete line.
- `/health` imported `websockets`, a package never installed by this project (only `aiohttp` is auto-installed) — reported unhealthy forever regardless of actual agent state. Rewritten to reuse the already-imported `aiohttp` client.
- `run-agent.cmd` was written with `encoding="ascii",errors="replace"` — any non-ASCII character in the workspace path corrupted the launch command. Switched to UTF-8 (same class of bug as the changelog mojibake incident this pass started from).
- `fs_read`'s UTF-8-sig fallback branch was unreachable (a BOM decodes fine under plain `"utf-8"`, just leaving a literal `﻿` in the content) — could seed exactly the kind of encoding corruption found in `changelog.md`. Now decodes `utf-8-sig` first.
- `--claim-ports` was documented as opt-in but the UI port was claimed unconditionally on every startup even without the flag. Fixed.
- Legacy loop jobs missing `expires_at` (older save format) were purged on the very next load instead of getting the intended 7-day grace window.
- `kill_pids_list`/`lan_ip`: added explicit UTF-8 decoding to `taskkill` output (matching the netstat call's existing convention) and fixed a socket handle leak on connection failure.
- `changelog.md` (914KB, doubly re-encoded mojibake from a non-UTF-8 write somewhere in the toolchain) repaired via iterative `ftfy` passes back to its original ~21KB / 48 entries; root cause addressed above (`run-agent.cmd` encoding, `fs_read` BOM handling).

Deployed to `~/.grok/plugins/grok-remote/` (web/ + server.py). Backups of every touched file under `backups/`.

## 2026-07-18 — Composer bind: send to chat where typed (v33)

- **Log where typed:** `composerBoundSid` stamps on composer input/focus; send uses that id, not live `sid` after await
- Per-session drafts: switch chat saves/restores composer text; empty chat does not steal an in-flight bind at send time
- Cross-chat send allowed with pinned `sessionId` + chip `sent → <id> (typed there)`
- Cancel/interject already target the same bound sid

## 2026-07-13 — Cancel/interject immediate + session-pin sends (v31)

- **Cancel** always fires `session/cancel` on the captured session id immediately (no cockpit-only path that can stall)
- **Interject** cancels then prompts without the 350ms delay
- **Wrong-chat send:** pin `sessionId` + `sessionGen` at send start; abort if chat switched mid-await; queue items store session id
- Session switch rejects pending prompts and drops other-chat queue items

## 2026-07-13 — Calm scroll settle on open/send (v30)

- Remove multi-rAF / multi-timeout scroll spam that caused twitchy feed on chat load and send
- `forceScrollBottom`: single `scrollTop` set; optional one soft settle (~80–120ms); no `scrollIntoView` fight
- Live follow uses one assignment only; open/send/jump use pin + single settle

## 2026-07-13 — Scroll: open-only pin + Bottom jump (v29)

- **No more tool-step whiplash:** live updates only follow when you are already at the bottom (`stickBottom`); execute/write/stream no longer re-pin scroll
- **↓ Bottom** button shows when you scroll up; tap to jump to latest
- **Chat open** still snaps to bottom once; **send** pins once so you see your message
- Older history: larger page (80), no bottom snap while prepending; scroll position preserved

## 2026-07-13 — Double-send + mobile autoscroll (v28)

- **Double You bubbles:** `sendInFlight` gate (Enter/click race); stronger local-echo dedupe vs agent `user_message_chunk` (12s window + plain-text match)
- **Mobile scroll:** ignore scroll-stick flips during keyboard/viewport reflow; wider atBottom slop when `kb-open`; force bottom on send/focus/agent paint

## 2026-07-13 — Product README + screenshot revamp

- Regenerated `docs/screenshots/*` from `?demo=1` only (no real chats)
- Capture script: command deck, tools, orbit, skills, theme gallery, phone, spoiler
- README rewritten as product tour (Grok default + Scient/Matrix/Ubuntu/Commodore/light)

## 1.3.0 — 2026-07-13

- Strip INTERJECT / AGENT SETUP / system-reminder / REMOTE LOOP chrome from You bubbles
- Hub `/loop` (no CLI TUI required) + `/effort` via ACP `session/set_model`
- History: closed bubbles per turn when switching chats
- Mobile keyboard / rotate reflow; command deck menu; todo badge fix
- Plugin + package version aligned to **1.3.0**

## 2026-07-13 — Hide instruction chrome in You bubbles (v27)

- Harden `stripPromptChrome`: strip `[INTERJECT…]`, `[FYI…]`, `[Queued…]`, `[AGENT SETUP]…[END]`, `[REMOTE LOOP…]`, `<system-reminder>…` (multi-pass, not start-only)
- Fixes Remote painting delivery-mode / persona / scheduler wrappers above the real user text

## 2026-07-12 — Chat switch history: one bubble per turn (v25)

- **Switch-only bug:** disk history is coalesced full turns, but the live streaming buffer still reused one You/Grok bubble — older turns vanished when opening another chat
- History/replay path now paints each user/agent event as its **own closed bubble**
- Fallback: if chat-only paint is empty, retry full history / cwd-less resolve; warn+retry if events painted zero DOM rows

## 2026-07-12 — History: restore You bubbles on refresh (v24)

- **Bug:** chat-only disk history has no `turn_completed`, so `curUser` stayed open and every user line overwrote the first You bubble — looked like older messages vanished
- **Fix:** start a new You bubble when wire buffer is empty; clear `curUser` on agent/tool/thought; skip local-echo dedupe during history replay

## 2026-07-12 — Composer shake + hide agent setup in chat (v23)

- **Shake fix:** multi-line typing no longer force-scrolls the feed every keystroke; pad updates stabilize scroll by footer delta only
- **Setup chrome:** persona / mode wrappers still sent to the agent, but stripped from You bubbles (local echo + wire + history)
- Pushed prior commits; this ships shake + display strip

## 2026-07-12 — Command deck menu + todo badge fix (v22)

- **Why "Todo 4":** `paintTodoBadge` overwrote the whole Tools row button with `todo N` (open count). Now keeps **Todos** label + badge key (`3/4`, `board`)
- **Command deck:** glass panel, brand header, live status chips, icon rows, pop-in, 3×3 glyph trigger (replaces plain ☰)
- Tools inject with icons; status bar refreshes while menu open

## 2026-07-12 — ☰ menu dedupe (v21)

- Flattened upper-right menu: Chat · Tools · Hide · Collapse · Apps · Appearance · Help
- **Permission** is one cycle control (Always → Ask → Plan), same as livebar
- Removed duplicate **Fonts** (Theme sheet), **Go voice / XR** (composer), hide/collapse chips from Theme UX
- Hide/collapse as compact 2-column grids; denser menu chrome

## 2026-07-12 — Keyboard clearance + rotate formatting (v20)

- **Keyboard:** pin shell to `visualViewport` whenever the composer is focused (not only when inset >48px); re-measure footer stack and lift feed so last messages clear keyboard + bottom bar
- **Rotate:** hard-reset body pin + CSS vars (`--vv-h`, `--feed-pad-bottom`, …); multi-stage reflow through ~1.6s; detect width/height flip as orientation
- **Phone landscape:** do not enter desktop sidebar layout when wide-but-short without fine pointer (`body.phone-landscape` stays single-column)
- Composer font-size 16px (iOS zoom guard); tighter max height while keyboard open

## 2026-07-09 — Mobile keyboard + orientation reflow

- Pin shell to **visualViewport height/top** while typing (iOS-safe baseline when unfocused)
- Feed padding = measured footer height so chat clears keyboard + bottom bar
- **Rotate** portrait↔landscape: multi-stage reflow (reset composer height, layout, stack pad, scroll)
- Permission chip/menu; always-approve skips plan approve UI
- Markdown lettered lists + safer path chips

## 2026-07-09 — Fix mixed history across sessions

- Abort stale history paints when `sessionGen` / `sid` changes mid-load (race was blending chats)
- Live updates require a matching `sessionId` (no unscoped bleed)
- Disk live catchup + older pages check session identity; history API stamps `resolvedDir`
- `find_session_dir` prefers cwd match; multi-hit fallback picks newest only

## 2026-07-09 — Start server reliability + faster chat open

- **Start server:** force-spawn agent with UI secret; if hub still 401s, kill/rebind and retry; clearer error toast
- **Chat open:** paint **disk messages first** (chat-only, ~80, small byte window); reveal UI immediately
- `session/load` + commands run **in background** with live-stream suppressed (no full agent replay dump)
- Skip blocking `_x.ai/prompt_history` on open

## 2026-07-09 — Fast history: last 100 + scroll-up load

- Open session loads only the **latest ~100** disk events (smaller read window)
- **Scroll up** (or tap "earlier messages") loads the previous page and prepends it
- API: `/api/session/history?limit=100&before=<byte>` + `meta.has_more` / `older_before`

## 2026-07-09 — Footer de-clutter + menu fonts + Amni-Delve

- ☰ menu uses UI `--font` / size (no fixed 12px mono)
- Removed above-composer clutter: no more "not a git repo", cost strip, or always-on When busy row
- Git + turns/ctx move into the **livebar** (only when useful); Interject/Queue/FYI only while busy
- **Amni-Delve** always in ☰ · Voice & wear; owner auto-unlock for Anthony/Amni paths

## 2026-07-09 — Fix new chat inheriting old user messages

- **Root cause:** `softCatchup` painted full `_x.ai/prompt_history` when `promptCount===0`, so **New chat** filled with prior turns
- **Fix:** `sessionFresh` gate; skip prompt-history backfill on empty/new sessions; only append prompt deltas after a known baseline; hard-clear feed/queue on new/open

## 2026-07-09 — Composer UX + XR detect + Watch v19

- **+** is attach-only; **Mic** sits beside the composer for Go voice
- Special functions moved to top-right **☰** (Todos, Terminal, Git, Export, …)
- **Chat view** toggles in ☰: hide/collapse thinking, tools, edits, reads, code
- **XR/AR autodetect** (`navigator.xr` + wearable UA); prefers AR when available
- **Galaxy Watch companion** at `/watch` (round UI, mic, session sync)
- Git strip stays under composer; tools tray removed from +

## 2026-07-09 — Message queue modes + Cancel v18

- **Interject / Queue / FYI** chips above composer (`When busy`)
- **Interject:** cancel current steps → send now
- **Queue:** hold until a good pause (`turn_completed`), then send with guidance framing
- **FYI:** extra context only — never cancels; applied at next pause with "don't stop" framing
- **Cancel** button beside **Send** (Send no longer turns into Cancel)
- Queue strip shows pending remote items (dismissible) + agent queue note

## 2026-07-09 — Voice Go + XR/AR + Grok TTS v17

- **Dictate / Go / XR** controls in composer tools + floating `#voiceHud`
- **Go mode:** continuous voice-to-text, pause-to-send for on-the-go tasks
- **XR/AR mode:** large smartwear-friendly HUD; WebXR immersive-ar/vr when the browser supports it
- Spoken replies are **ack on task receipt** + **summarized final answer** only (not full tool chatter)
- **Real Grok voice:** `POST /api/tts` → `https://api.x.ai/v1/tts` (needs `XAI_API_KEY`); browser `speechSynthesis` fallback
- `GET /api/voice/status` reports TTS readiness; voice picker (eve, ara, leo, …)

## 2026-07-09 — Promote archived → live on message v16

- Messaging an **archived** session unarchives it (`POST {id, archived:false}`), marks it **live**/resident, switches scope Archived → Active, and **auto-refreshes** the session list
- Promote runs optimistically on send + again on prompt resolve
- Archive load no longer re-merges stale local IDs over a successful server unarchive (merge only on `migrate`)
- Synced to `~/.grok/plugins/grok-remote`

## 2026-07-10 — Polish v15 (syntax, greyscale, tools, tour, repo)

- **Syntax colors** fixed in tool edits/reads (token CSS covered `.code-with-lines` / tool panes; removed `!important` greys that killed tokens)
- **Grok theme** full greyscale chrome (no green status accents); code keeps distinct syntax hues
- **Delve** hidden for normal users (owner unlock only; code kept)
- **Composer + tray** clearer labels + Chat/Work/Share groups
- **Tour** reworked steps, prep focus, no auto-hijack on first run (gentle chip instead)
- **Screenshots** varied non-spoiler sample session views; README/CONTRIBUTING/package.json professionalized

## 2026-07-10 — Spoiler-safe Grok screenshots v14

- Privacy blurs **session titles** (not just paths); stronger blur; title tooltips stripped when spoiler on
- Spoiler badge: **private screen** by default; **hold Alt to peek** only on real desktop (`can-hover.desktop`)
- Default product theme remains **Grok**; `applyTheme` fallback no longer lands on Scient
- `?demo=1&variant=grok&privacy=1` scrubbed sessions for public captures; `scripts/capture-screenshots.mjs`
- README shots retaken — no personal paths/chats, Grok dark default, phone without Alt

## 2026-07-10 — Menu stacking + code line numbers / syntax

- Header ☰ / orbit menus use `position:fixed` + high z-index so they paint above chat
- Thinking renders markdown + fenced code (syntax colors)
- Tool in/out, reads, edits: line numbers + token highlighting
- Markdown fenced code blocks no longer skipped

## 2026-07-10 — Live CLI→remote disk catch-up

- Remote polls `updates.jsonl` via `/api/session/history?live=1&since=<bytes>` every 500ms
- Thinking / tools / agent text from desktop TUI (same session id) stream into remote without hard refresh
- EventId de-dupe keeps history paint + live tail from double-rendering

## 2026-07-10 — Start Server + port claim + reconnect guard v8

- **Start Server** header + setup button → `POST /api/stack/start` (kills stale :2419, spawns `grok agent --no-leader serve`, rebinds hub)
- **Boot:** UI claims free :2421 listeners; auto-starts agent if missing; `start.ps1` kills :2419/:2421 before bind
- **Reconnect:** max 5 tries, no infinite reconnecting #N loop; agent error no longer thrashing; after give-up → hit Start Server
- Auto-connect: if `/health` agent down, Start Server first then connect

## 2026-07-10 — Live status + init/session reliability v7

- **Root cause of init failed:** agent serve was down / started with wrong `--leader` flag (means *attach to leader*, not run server). Fixed launcher to `--no-leader serve` via cmd append (no stdout pipe hang).
- **Hub:** keep client WS open when agent is briefly down; retry ensure; cache `initialize` for multi-client; fast connect timeouts; clearer offline errors.
- **Session list:** unwrap nested `result.result.sessions`; sort/auto-open by `lastChangeUnixMs` (opens this chat: latest).
- **Live status bar:** bottom strip shows **idle / waiting for response / thinking / responding / running tools** with pulse dot; header short status.
- **Reconnect:** auto-retry on close/init fail; auto-open best session after connect.
- Restart stack: `scripts\restart-ui-only.ps1` + `logs\run-agent.cmd`; hard-refresh remote UI.

## 2026-07-10 — Pin fix + feature tour v6

- **Pin bugfix:** local `import subprocess` inside `main_async` except-block made nested handlers fail with *cannot access free variable 'subprocess'…* when aiohttp was already installed. Use module-level `subprocess` only.
- **Feature tour:** header **Tour** + setup **Feature tour**; 12-step spotlight walkthrough; first-run auto; `?tour=1` force; localStorage `grok_remote_tour_done`.
- **Tutorial prompt:** **Paste tutorial prompt** fills composer + clipboard for a live Grok-narrated walkthrough of all features.
- Restart UI on `:2421` after pull; hard-refresh clients.

## 2026-07-10 — Stop button + pin/start from anywhere

- UI header **Stop** → `POST /api/stack/stop` (UI + agent serve only; never mass-kill grok)
- UI **Pin** → `POST /api/stack/shortcut` creates Desktop + Start Menu shortcuts
- Scripts: `stop-remote.ps1`, `launch-remote.cmd`, `install-shortcut.ps1`
- Commands: `/remote-start`, hardened `/remote-stop`
- Desktop shortcuts installed: **Grok Remote** + **Grok Remote Stop**

## 2026-07-09 — Claude-gap pack v5.1

Closer to Claude Code day-to-day flow:

- **Stop turn** button (session/cancel) while agent is busy
- **Git strip** branch/sha/dirty + `/api/git/status|diff|log` + Δ working-tree diff
- **Context meter** live est. fill; `/cost` slash helper
- **Todos board** (plan sync + manual); badge count
- **Slash autocomplete** for skills + local `/clear /cost /diff /stop /agents /compact`
- **Open tool paths in IDE** (click 📄 locs)
- **Copy** on message hover
- **MD** inject AGENTS.md / CLAUDE.md into composer
- APIs: `/api/git/*`, `/api/project/context`

Restart UI server (`:2421`) for new routes; hard-refresh clients.

## 2026-07-09 — UX fix: contrast, horizon loader, terminal lag v4.2

- Contrast: solid bubbles, readable `--tx`/`--soft`/`--mut`, softened Grok mono (no pure black/white)
- **Event horizon loader** lives in `#chatStage` (chat area above composer only — not header/fullscreen)
- Space puns rotate under the spinning accretion disk while history/session loads
- Terminal stream: throttled paint, no auto-open spam, badge on `$_` instead, skip during replay
- Header no-wrap scroll; cockpit bar height capped

## 2026-07-09 — xAI product UX polish v4.1b

- Design tokens: `--ease`, `--elev-*`, `--glass`, `--hairline`
- Near-black monochrome base; **Grok** variant as official black/white product look (white CTA)
- Hover/focus/active micro-motion on header, chips, sessions, tools, composer, sheets
- Message row enter animation; glass header/footer; refined scrollbars
- Soft ambient glow + grid; reduced-motion + retro-theme exclusions
- Deployed to plugin + marketplace copies

## 2026-07-09 — Claude-gap cockpit features v5.0

High impact: inline red/green diffs + accept/reject hunk apply; @ workspace file picker; plan approve/edit/hold; Always-allow permission; terminal stream pane; background tasks list/cancel/notify  
Medium: chat search; local checkpoints; voice PTT; reconnect resume; HTML export (spoiler-aware)  
Diff: pin sessions bar; cost budgets; Delve launcher  

Files: `web/cockpit-features.js`, index wiring. Hard-refresh after stack up.

## 2026-07-09 — Full skills palette v4.3

- **Disk skill scan** `/api/skills/list`: `~/.grok/skills`, bundled, plugins, marketplace-cache, project skills + plugin commands
- Skills UI merges agent `commands/list` + disk scan; source chips + filter
- Advanced skills (design, execute-plan, review, …) appear even if agent list is sparse
- Restart UI server required

## 2026-07-09 — Multi-client hub + history snap v4.2

- **WS hub:** one shared agent connection; fan-out `session/update` to all phone/desktop clients; route RPC replies to the requester
- **History open:** hide feed while loading, then `snapChatToBottom` (no scroll-from-top marathon)
- Restart UI on :2421 required for hub

## 2026-07-09 — Personas & directions v4.1

- **Persona flyout:** personalities (Concise, Unhinged, Programmer, Engineer, Manager, Clown, Warlord, …)
- **Directions:** Build, Debug, Review, Explore, Plan, Ship, Refactor, Security, Docs, Teach, Speedrun
- Setup preamble on first send per session; **Inject setup now** button
- **Risk** persona owner-gated (`Users\antho` path or `?owner=1` unlock); not shown to others by default
- Prefs: `grok_remote_persona`, `grok_remote_direction`

## 2026-07-09 — Cockpit IDE + auto-stack + Grok Review v4.0

- **Electron auto-stack:** launch app → agent + UI proxy (no daily terminal)
- **`scripts/launch-desktop.cmd`** double-click entry
- **FS API** on UI server: `/api/fs/list|read|write|root` (workspace sandboxed)
- **Built-in IDE** panel: tree, tabs, editor, Save, Folder, New session here
- **Grok Review:** post-edit bug-check prompt for active / dirty files
- Desktop menus: Open workspace, IDE review shortcuts, New session

## 2026-07-09 — X-like labels + Ubuntu Yaru-ish v3.7

- Skin labels: **AIM-like**, **Win95-like**, **C64-like**, **Atari-like**, **Ubuntu-like**, **Matrix-like**, **DOS-like**, **Amiga-like**
- **Ubuntu-like:** modern Yaru-ish slate surfaces + orange accent (not old aubergine-only)

## 2026-07-09 — Tool payloads + rename skins v3.6

- **Tool cards:** merge rawInput/rawOutput/locations/content across updates; real titles (kind + path/cmd); no empty white bars
- Earlier playful aliases replaced by X-like naming

## 2026-07-09 — Code colors + collapsible rail + flyouts v3.5

- **Syntax colors** in fenced code: keywords/strings/numbers/comments/fns use theme tokens (`--acc`, `--ok`, `--you`, …)
- **Collapsible sessions rail:** « Hide / ☰ / edge tab; pref `grok_remote_sidebar`
- **Top-right flyouts:** Theme, Skills, Task open frosted glass panels sliding from top-right (Esc closes)

## 2026-07-09 — Legacy themes v3.4

- **Legacy palettes:** AIM, Win95, Commodore 64, Atari, Ubuntu, Matrix, MS-DOS, Amiga Workbench
- Full surface overrides (fonts, radius, chrome) + dark/light twists
- Theme picker groups **Product** then **Legacy · retro**
- Win95 bevel chrome, Amiga/Win95 title bars, Matrix phosphor glow

## 2026-07-09 — Chat polish + attachments v3.3

- **Markdown render:** headings, lists, bold/italic, inline code, tables, blockquotes, links, path chips, fenced code cards
- **Consistent bubbles:** solid 1px borders (no hover jitter); tools/cards match radius; cleaner clean-mode edge accents
- **File upload:** 📎 attach / drag-drop / paste; images as ACP `image` blocks; text/code as resource + fenced body
- Limits: 8 files, 6MB each · hard-refresh clients (`?v=3`)

## 2026-07-09 — SpaceXAI beauty + session isolation v3.2

- **Orbital status dial:** satellite orbits planet (spin when linked, fast when busy, red offline)
- **Pulse frames:** thin theme-accent borders on header / rail / feed / footer / setup
- **Polish:** bubble glow, composer focus halo, session card hover lift, reduced-motion safe
- **New-chat history bug:** clear `sid` first; `loadExpectSid` gates unscoped load stream; abandon softCatchup/silentReload across `sessionGen`; re-wipe feed after `session/new`
- Deployed to `~/.grok/plugins/grok-remote/web` + marketplace plugin copy

## 2026-07-09 — Sessions scroll + jump + archive v2

- **↓ Bottom** always on in chat (not only when scrolled up); forced scroll + `scrollIntoView`
- **Independent scrolls:** body locked; session rail list vs chat feed scroll separately
- **Archive / Unarchive** per session (localStorage); scope chips Active · Live · Archived · All + search
- Layout: picker-head sticky controls, `.sess` flex scroll region

## 2026-07-09 — UX options v1

- **Auto-scroll:** toggle on setup/Theme UX chips; stick-to-bottom while reading live; jump FAB
- **Collapse:** thinking rows, fenced code, tool cards — defaults + per-block tap
- **Borders vs clean:** bordered cards or clean edge-accent layout
- Prefs: `localStorage.grok_remote_ux`
