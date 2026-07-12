# Changelog

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
- **Scroll up** (or tap “earlier messages”) loads the previous page and prepends it
- API: `/api/session/history?limit=100&before=<byte>` + `meta.has_more` / `older_before`

## 2026-07-09 — Footer de-clutter + menu fonts + Amni-Delve

- ☰ menu uses UI `--font` / size (no fixed 12px mono)
- Removed above-composer clutter: no more “not a git repo”, cost strip, or always-on When busy row
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
- **FYI:** extra context only — never cancels; applied at next pause with “don’t stop” framing
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
