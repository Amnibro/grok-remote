# Guardian Council — UI/UX options

**Task:** Autoscroll, collapse regions, borders vs clean  
**Date:** 2026-07-09

## Architect
Ship device-local prefs (`localStorage`) with chips on setup + theme sheet so no server config is required. Defaults: auto-scroll on, collapse think+code, tools expanded, borders on.

## Sentinel
Do not change wire protocol or ACP. Jump FAB must not force network. Collapsed state is presentation-only; live stream still appends full content.

## Scholar
Match existing theme chip patterns (`mode-chip`, paint hosts). Persist under `grok_remote_ux` next to `grok_remote_variant` / `mode`.

## Engineer
Reuse DOM: thought-row / tool / collapsible.code classes; one `applyCollapseDefaults` for existing nodes; new nodes read `ux` at create time. Fix collapse-code path so toggling code chip updates open bubbles.

## Pathfinder
Clean mode keeps light left/right edge accents so bubbles stay scannable without heavy borders — better than fully borderless flat text on mobile.

## Decision (majority)
LocalStorage UX prefs + Theme sheet chips + collapsible regions + jump FAB + clean edge accents. No new backend.
