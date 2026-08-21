# Checklist — catch-up chop fix v1 (2026-08-17)

Symptom: streamed Grok replies painted as several bubbles chopped mid-word ("R" / "ao — Amni-Connect…"), thinking split into multiple rows (65c / 138c).
Root cause: `paintDiskEvents` resets `curAgent`/`curThought`/`userWireBuf` at the top of EVERY batch. The live disk catch-up poll (500–900ms in v1.8.4) routes through the same function, so each poll batch opens a new bubble instead of continuing the open one.

- [x] Scan architecture_map.md
- [x] Backups: index.html.v_catchup_chop.bak, root_index.html.v_catchup_chop.bak, installed_index.html.v_catchup_chop.bak
- [x] Fix web/index.html — reset stream cursors only for replay/prepend paints
- [x] Fix root index.html (same bug, line ~3973)
- [x] Fix installed ~/.grok/plugins/grok-remote/web/index.html (live copy, v1.8.4 drift — edit in place, do NOT overwrite)
- [x] Playwright regression test tests/test_catchup_chop.mjs: FAIL on .bak (agentRows=2, "Lm|ao — …"), PASS on web (fixed), root (fixed), installed
- [x] Syntax check — Playwright page load executed all three without error
- [x] Update architecture_map.md + changelog.md
- [ ] Anthony confirms chopping gone on phone (hard-refresh the tab — served no-store, no server restart needed)

## Incident during rollout (same morning)
- [x] "Blank + unresponsive" after hard refresh = `_x.ai/sessions/list` timeout, NOT the paint fix (shell loaded, link live)
- [x] Proven: agent :2419 direct = 0.7s with full sessions; hub-forwarded rpcs vanished; detached in-flight RPCs climbing 1->15; busy tos-learn turn spamming failed reverse fs reads = wedged hub<->agent socket
- [x] restart-ui-only.ps1 (agent + secret untouched); its silent-relaunch + early health check noted in changelog; manual run-ui launch with per-instance log logs/ui.manual.log
- [x] Verified: /health ok, hub sessions/list 0.7s, headless page paints 19 rows / 3 sessions, wedged turn resumed running tools
- [x] Deleted tests/probe_wedge.py + probe_live_page.png (embedded key / private titles; public repo)
