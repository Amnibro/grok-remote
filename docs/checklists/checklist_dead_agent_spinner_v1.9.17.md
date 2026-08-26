# checklist_dead_agent_spinner_v1.9.17

Symptom: message sent from mobile to amni-browse spins forever. Desktop rail flickers on open and
chats will not select.

## What was actually wrong

- [x] **The grok agent was brain-dead, not busy.** `agent.spawn.log` ends at 2026-08-24T23:11:32
      with five `worker quit with fatal: Transport channel closed, when Auth(AuthorizationRequired)`.
      The process (PID 23628, up since 08-23) still answered `initialize` and `sessions/list` in
      0.01s and kept `/health` green, but burned **0.00s CPU over 6s**. `auth.json` refreshed at
      05:44 today and the long-lived process never picked it up.
- [x] The 08:27 prompt was forwarded (`[hub] prompt · sid=01a02cd3 · wait_load=False`) and produced
      nothing. `updates.jsonl` last written 08-23 23:16. **That message is lost.**
- [x] **`session/prompt` had no timeout at all.** It is sent raw and registered straight into
      `pending`, bypassing `req()`. Nothing could ever clear the spinner.
- [x] **`heal()` skipped exactly this case.** `if last_ask and last_tool and last_tool<last_ask:
      continue` — the tools replayed at 08:26 predate the 08:27 ask, so the job stayed `running=1`.

## Fix

- [x] Restarted the agent; hub auto-respawned it (PID 6696). Verified a real turn: first output
      1.8s, completed 4.1s, 41 chunks.
- [x] `startPromptWatch(id)` — watches total SILENCE (`lastLiveAt`), not elapsed time, so a long
      streaming turn is never killed. Rejects the pending prompt after `PROMPT_STALL_MS` (120s),
      clearing busy and chipping a real message. Tunable via `window.__promptStallMs`.
- [x] `work_board.heal()` marks `phase='stalled'`, `running=0` when a prompt is older than
      `STALL_SECS` (240) with zero activity since (`updated <= last_user_at + 5`).
- [x] Exposed `window.pending` beside the existing `window.msgQueue`.
- [x] Both `web/index.html` and root `index.html`.

## Verify

- [x] node --check both copies
- [x] tests/test_prompt_stall.mjs — 4 pass on fix, fails on backups/index.html.v1.9.17_pre_promptwatch.bak
- [x] tests/test_work_stall.py — passes on fix, fails on backups/work_board.py.v1.9.17_pre_stall.bak
- [x] live: both stale rows healed to `stalled running=False`
- [x] served md5 == local
- [ ] Anthony: RESEND the lost amni-browse message; reopen the desktop and say if the flicker is gone

## Open

- Desktop rail flicker NOT reproduced headless against a healthy hub (renderSessions 5x/15s,
  loadOlderHistory 0, no console errors, opening amni-browse painted 17 rows with no replay flood).
  Most likely it was `_x.ai/sessions/list` against the dead agent. Needs a re-test now the agent is alive.
- A stray argument-less `python -u server.py` appears on desktop open (PID 54424 on 08-24, PID 57348
  at 08:27 today), holding no port and no agent socket. Killed both. Spawner not identified — no
  script in `scripts/` or `start.ps1` writes an argument-less launch.
