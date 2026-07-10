# Grok Remote — architecture map

**Updated:** 2026-07-10 · v14 spoiler-safe screenshots + demo mode

## Layout

```
grok-remote/
  web/index.html          # Phone + browser + Electron UI (default theme: grok)
  web/ide.js              # Built-in IDE + Grok Review
  server.py               # static + /ws proxy + /api/fs/*
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
| Grok variant | Official monochrome: pure black surfaces, white primary CTA, zinc accents |
| Motion | Row enter (`row-in`), hover lift ≤2px, focus rings, pill chrome, thin scrollbars |
| Ambient | Soft accent radial + faint grid mask (disabled on retro themes) |
| `#chatStage` | Chat column wrapper; `#horizonLoad` overlays **only this area** (above footer/composer) |
| Horizon | Accretion-disk loader + rotating space puns during session open/new |

Session isolation: `sessionGen`, `sessionSwitching`, `loadExpectSid`. Unscoped `session/update` only accepted during intentional load when `loadExpectSid===sid`. New chat clears `sid` first, re-clears feed after `session/new`, never sets `loadExpectSid`.

## Live status + sessions (v7)

| Piece | Behavior |
|-------|----------|
| Footer `#livebar` | `link` + phase: idle / waiting for response / thinking / responding / running tools |
| `setPhase` / `setBusy` | Driven by prompt send, thought/message/tool chunks, turn_completed, queue |
| Session list | Unwrap nested `result.sessions`; sort by `lastChangeUnixMs`; highlight open |
| Auto-open | After connect, open best session (cwd match + newest) unless `?session=` / `?task=` |
| Agent serve | `grok agent --always-approve --no-leader serve` (not `--leader serve`) |
| Hub | Retry ensure, cache initialize for multi-client, keep UI WS when agent flaps |

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
- Archive: per-row button; IDs in `localStorage.grok_remote_archived` (device-local hide, not server delete)
- Scope: `localStorage.grok_remote_sess_scope`

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

## Deploy path

Installed plugin web root: `~/.grok/plugins/grok-remote/web/index.html`  
(Copy from repo after UI changes; hard-refresh clients.)
