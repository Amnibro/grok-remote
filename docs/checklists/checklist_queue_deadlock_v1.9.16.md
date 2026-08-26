# checklist_queue_deadlock_v1.9.16

Symptom: user messages pile up in the queue and never send, until a restart, hard refresh or
cancel — then they all come out FIFO.

## Root causes

- [x] **Circular gate.** `_x.ai/queue/changed` with `entries=[]` and no `runningPromptId` is the
  agent reporting itself idle, but the handler refused to clear `busy` while `msgQueue.length`
  was non-zero, and `drainMsgQueue` refused to run while `busy`. Neither side could move. Cancel
  / refresh / restart clear `busy` by another path, which is why those three "fix" it and the
  whole backlog flushes at once.
- [x] **Edge-triggered drain, no re-arm.** Every early return in `drainMsgQueue` (msgDrainBusy,
  no sid, socket down, sessionSwitching, busy, 400ms rate limit) dropped the wakeup with nothing
  scheduled. One blocked attempt parked the queue until an unrelated event happened to call
  `scheduleMsgDrain` again.

## Fix

- [x] Drop `!msgQueue.length` from the busy-clear in the `_x.ai/queue/changed` handler. The
      agent's queue state describes the AGENT; the client's outbound queue is unrelated to it.
- [x] `armMsgRetry()` — one 1.5s ticker, alive while anything is queued. Every early return in
      `drainMsgQueue` arms it, so does the `finally`, `scheduleMsgDrain` and `enqueueMsg`.
- [x] Patched BOTH copies: `web/index.html` (served) and root `index.html` (source).

## Verify

- [x] node --check on the extracted script block, both copies
- [x] tests/test_queue_deadlock.mjs — real page under playwright-core, drives handleMsg /
      setBusy / msgQueue directly. 3 of 4 fail on backups/index.html.v1.9.16_pre_queue_deadlock.bak
- [x] served file md5 == local web/index.html (Cache-Control: no-store, no restart needed)
- [ ] Anthony confirms: queue a few while a turn runs, they should go one per turn with no stall

## Found while here, NOT fixed

- `tests/test_ui_chrome.py` is 12/19 failing against the shipped UI. Two of those failures
  (`test_queue_drains_on_safe_pause`, `test_queue_x_puts_text_back_in_box`) describe a different
  queue design — `queueDrainAllowed` / `markQueueSafe` / `startQueueWatch` / `unqueueToBox`,
  draining on a 2.2s stream-silence pause instead of gating on `busy`. Those identifiers exist in
  no copy, backup or archive. Left alone pending a call on whether that design is still wanted.
