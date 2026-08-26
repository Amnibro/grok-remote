# checklist_session_wedge_v1.9.15

Symptom: navigate away from a chat, or run a long complex turn, and the chat stops
responding. Link stays green. Restarting the hub clears it.

## Root causes found

- [x] **A. `_sid_load` / `_sid_load_ev` survive an upstream drop.** `_close_unlocked` clears
  `pending`, `_rpc_futs`, `_terms` but not the session/load bookkeeping. A `session/load`
  in flight when the agent socket dies leaves `sid` in `_sid_load` with an Event that is
  never set. From then on: every `session/load` for that sid takes the `_dup()` branch and
  waits 20s on a dead Event (client gives up at 12s, all 3 retries), and every
  `session/prompt` for that sid stalls 20s first. Permanent per-session wedge.
- [x] **B. `_load_ok` is never invalidated.** After an agent respawn the hub answers
  `session/load` from cache and never tells the new agent process to load the session, so
  prompts go to a session the agent does not have.
- [x] **C. `_broadcast` mutes slow clients forever.** A 0.8s `send_str` timeout removes the
  client from `self.clients` but leaves the socket open. `handle_client` keeps answering
  pings, so the link reads live while the client receives nothing. Fires exactly when a
  long run streams hard at a phone on a slow link.

## Fix

- [x] Collapse `_sid_load` + `_sid_load_ev` + `_load_ok` into one `_loads` map
      (`sid -> {ev, res}`), one helper to finish an entry.
- [x] `_close_unlocked` sets every waiter and clears `_loads` (fixes A and B together).
- [x] Waits are 10s so they resolve inside the client's 12s `session/load` timeout.
- [x] Send failure in `_go` finishes the entry so a retry re-sends upstream.
- [x] `_broadcast` closes the socket for any client it drops. No silent mute.
- [x] `_loads` bounded at 64 entries.
- [x] `/api/session/prompt` path updated to the new map.

## Verify

- [x] py_compile clean
- [x] tests/test_hub_session_wedge.py — fails on the .bak, passes on the fix
- [x] existing tests still pass
- [x] live restart (fresh supervisor cmd-supervise-20260824-1915) · hub_up true · initialize 0.02s · 2 concurrent session/load 0.02s
- [ ] Anthony confirms on phone over a long run
