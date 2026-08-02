# Checklist — Grok Remote Braid layout (v37)

Date: 2026-07-29

## Goals
- [x] Reskin/relayout phone + desktop UI to clean BRAID shell aesthetic
- [x] Keep current mission-control chrome as **legacy** layout (switchable)
- [x] Default new users to **braid**
- [x] Persist choice (`localStorage.grok_remote_layout`) + `?skin=legacy|braid`
- [x] No functional regressions (sessions, send, tools, sheets)

## Steps
- [x] Backup `web/index.html` → `backups/index.html.v_braid_layout.bak`
- [x] Add `web/braid-layout.css`
- [x] Link CSS + early `data-layout` bootstrap in `index.html`
- [x] Layout chips in setup + theme sheet + command deck
- [x] JS: load/apply/set/toggle layout
- [x] Sync workspace copy
- [x] Update `architecture_map.md` + `changelog.md`
- [ ] Hard-refresh smoke (layout toggle, chat, sessions rail) — user confirm

## Out of scope
- Rewriting agent/WS protocol
- New themes museum packs
- Haven feature parity (voice channels, server bar)
