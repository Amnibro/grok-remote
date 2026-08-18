# Checklist — a hidden tab put its own link to sleep (v1.9.2)

Date: 2026-08-17

## Three gates, all reached by a background tab
1. `startPoll` — `if(document.visibilityState==="hidden")return;` so a hidden tab did **no**
   catch-up at all. A turn that finished behind your back had produced nothing on that tab.
2. `startLinkKeepalive` — a **4s** `setInterval` that force-closes the socket when
   `Date.now()-linkLastRx > 45000`. Chrome throttles background timers, and after 5 minutes hidden
   it drops them to roughly **once a minute** — so `silent` is past 45s on the first fire no matter
   how healthy the socket is. The stale-link guard closed the connection it exists to protect.
3. `scheduleReconnect` — `if(hidden && !midTurn && still hidden){scheduleReconnect(8000);return}`
   re-parked on every retry, so a link lost while hidden **never came back** until the tab was
   looked at.

The socket itself was fine: `web.WebSocketResponse(heartbeat=12,autoping=True)` sends protocol-level
pings, but those are handled by the browser's network stack and never surface as `onmessage`, so they
do not refresh `linkLastRx`. Liveness has to arrive as an application frame.

## Steps
- [x] Scan `architecture_map.md`
- [x] Backups: `backups/server.py.v1.9.1_pre_hidden_tab.bak`, `backups/web-index.html.v1.9.1_pre_hidden_tab.bak`
- [x] Server: `_watch_loop` broadcasts `_x.ai/remote/hub` every 15s while clients are connected.
      Reuses the method the client **already** handles (`onHubState`), so no new client handler and
      no unknown-method path. `ws.onmessage` sets `linkLastRx` on every frame, so this refreshes
      liveness with **zero client timers** — immune to throttling.
- [x] Client: hidden tabs catch up every 15s instead of never
- [x] Client: never force-close the link from a hidden tab
- [x] Client: back off the reconnect while hidden instead of parking forever
- [x] `server.py` parses; restarted the live UI with `scripts/restart-ui-only.ps1`

## Verified
- **Isolated A/B, idle client, sends nothing for 50s:** pre-fix server **0** application frames,
  patched server **4**. Fails on `backups/server.py.v1.9.1_pre_hidden_tab.bak`.
- **Live :2421 after restart:** 2 heartbeats in 40s to an idle client — the fix is running, not just
  on disk.
- **No regression on a visible tab:** patched page held **one** socket for 7+ minutes with zero
  reconnects and steady traffic (18/min = the 15s heartbeat plus pongs).

## NOT verified — needs 30 seconds of your time
The end-to-end background-tab behaviour could not be reproduced here. Pages opened through CDP
report `visibilityState:"visible"` even when another tab is selected, and minimising the Chrome
window did not reach those targets either — `msgsWhileHidden` came back **0 out of 3529** because
the page was never actually hidden, not because nothing arrived. So the mechanism above is proven
from the code and the server half is measured, but the "hidden tab keeps up" claim is not.

To confirm: open `http://127.0.0.1:2421/` in a normal Chrome tab, start a turn, switch to another
tab for **6+ minutes**, then come back. Expected now: the transcript is already current, no
"link stale · forcing reconnect" chip, no reconnect churn in the console.
