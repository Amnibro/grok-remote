# Checklist: companion senses + attention loop v1 (toward Cortana)

- [x] Scan architecture_map.md (XR companion body, motion service, brain/voice modules)
- [x] Inventory: body+voice+gesture+gaze+idle life exist; NO autonomous perception->reaction; mic is push-to-talk
- [x] Backups: backups/xr.html.presenses.bak, backups/server.py.presenses.bak
- [x] companion_env.py + GET /api/companion/env (foreground window, running turns, latest tool, asks, time)
- [x] web/xr-senses.js: presence (camera motion), hands-free ears (name-addressed), env poll, percept log, reflexes, budgeted deliberate reactions
- [x] xr.html: Senses toggle, ask(text,{silent}) for reactions, window.__react + window.__senses
- [x] tests: tests/test_companion_env.py, tests/test_xr_senses.mjs (addressed detection, budget, reflex table)
- [x] hub restart for the new route; verify curl /api/companion/env
- [x] browser verify: inject arrive -> wave reflex + spoken reaction; inject work_done; [[quiet]] path stays silent
- [x] docs/companion-roadmap.md, architecture_map.md, changelog.md
- [x] mirror (xr-senses.js + companion_env.py only; plugin xr.html was edited 18:44 today by another session, NOT overwritten) xr.html/xr-senses.js/companion_env.py to the plugin dir (server.py NOT mirrored: repo is ahead)

## Follow-up 2026-09-04: side rails
- [x] Backup web/xr-hud.js + xr-brain.js (backups/*.prerail.bak)
- [x] Coalescer rewrite, raw onEvent path, list filter + ellipsis, viewing bar
- [x] tests/test_xr_hud.mjs; inline module + brain + hud node --check OK
- [x] Browser verify: 5 chat rows / 4 work rows for a tool turn (was 11 / 64), chip 34x14px, her live session selected
- [x] changelog + architecture_map; roadmap "interact from the disc" section

## Follow-up 2026-09-04: floor contact
- [x] Measured: hips world y 0, feet -0.90 (1.01 m below the pad); bind-local hips z = -1.012, up axis = z
- [x] Backup backups/xr.html.prehipsclamp.bak
- [x] Bind-aware hips clamp (lateral pinned, vertical deviation > 0.5 rejected)
- [x] Verified: skinned mesh floor 0.005-0.022 across 3 bases + 4 gestures, height 1.70 m
- [x] tests/test_hips_clamp.mjs; changelog + architecture_map + roadmap (subagent question answered)

## Follow-up 2026-09-04: interior surfaces
- [x] Backup backups/xr.html.preinterior.bak
- [x] Inward-normal reject inside a 0.135 head sphere (bind-space head bone, axis agnostic)
- [x] Verified: 5509 rejected, 0 inward-facing points left, worst dot 0.12
- [x] tests/test_interior_cull.mjs; changelog + architecture_map + roadmap (Cortana surface plan)

## Follow-up 2026-09-04: hover + surface
- [x] Root cause of "hovering doing splits": dissolve band 0.12-0.55 erased legs (rig was already correct, bind matrix is identity)
- [x] Backups: xr.html.prefade.bak, xr.html.presurface.bak
- [x] Fade band moved to -0.045..0.075
- [x] Hologram surface pass (fresnel rim + scanline, skinned ShaderMaterial, depth write), ?surface=0 escape hatch
- [x] Verified by offscreen render -> /api/xr/see -> read jpg: boots on the pad, full silhouette, face clean

## Follow-up 2026-09-04b: shell alignment, sealed face, squat
- [x] Backups: xr-motion.js.prehips.bak (xr.html backups from earlier passes cover the shell)
- [x] Shell DetachedBindMode + depth prepass + SURF.keep; verified points-only vs shell-only renders coincide, straight-on face clean
- [x] Hips clamp 1.5; stripRoot keeps GLB hips; gestureSkip; SQUAT_ALIAS reversed crouch_to_stand
- [x] Verified hips 1.017 -> 0.412 -> 1.011, feet planted at the bottom; squat render saved
- [x] Mirrored xr-motion.js to plugin (identical base); xr.html NOT mirrored (other session's copy)
- [ ] motion_service.py refuse list / emote table (other live session) still turns squat into a bow
