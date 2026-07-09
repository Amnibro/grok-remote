## Install as a Grok plugin (/remote) — v1.1.0

**Public repo:** https://github.com/Amnibro/grok-remote

Anyone with Grok Build:

`ash
grok plugin install Amnibro/grok-remote --trust
grok plugin enable grok-remote
`

Then in the TUI: **/remote** · **/remote-stop** · **/remote status**

Local copy / dev:

`powershell
cd C:\Users\antho\Documents\ai\grok-remote
.\install-local.ps1
`

# Grok Remote Control (Android)

Chat with **Grok Build on your PC** from your phone — same agent, full tools, ACP over WebSocket.

## Install as a Grok plugin (`/remote`) — v1.1.0

```powershell
cd C:\Users\antho\Documents\ai\grok-remote
.\install-local.ps1
```

Local marketplace (listed as **grok-remote-market**):

```powershell
grok plugin marketplace add C:\Users\antho\Documents\ai\marketplace\grok-remote-market
```

Then in TUI: `/marketplace` or **`/remote`** · **`/remote-stop`** · **`/remote status`**

Listing blurb: *Live phone controller — session picker, history+thinking+tools, live stream, Skills, New Task, back-swipe to Sessions.*

Publish for others (GitHub / marketplace): see **[PUBLISH.md](./PUBLISH.md)**.

## Architecture

```
Android browser  --HTTP-->  grok-remote UI+proxy (:2421)
                 --WS /ws-->  (proxy) --> grok agent serve (127.0.0.1:2419)
                                              │
                     session picker ──────────┤
                     • New session            │
                     • Load existing (desktop)│  session/load
                     • Many chats OK          ▼
                                         tools / cwd on PC
```

- Phone only needs **one** URL: `http://LAN_IP:2421/`
- WebSocket is same-origin `ws://LAN_IP:2421/ws` (secret stays on PC)
- Protocol: ACP — `initialize` → **list sessions** → `session/new` **or** `session/load` → `session/prompt`
- Tools run on the PC, not the phone

## Multiple sessions

You can have many Grok chats at once (desktop TUI + phone + older history).

| Action on phone | What happens |
|-----------------|--------------|
| **Connect** | Opens WebSocket + ACP init only |
| **Session list** | `_x.ai/sessions/list` — all known chats |
| **Tap a row** | `session/load` — **replays full history** (user msgs, thoughts, tools, plans, recaps) then stays live |
| **+ New** | `session/new` — fresh remote chat |
| **Sessions** (header) | Switch without disconnecting the socket |
| **Think** (header) | Toggle visibility of thinking blocks |

### Live controller (history + state)

On `session/load`, Grok streams the transcript as ACP `session/update` events. The phone UI now **keeps** them (it used to clear the feed after load):

| Update | Shown as |
|--------|----------|
| `user_message_chunk` | Your bubbles |
| `agent_thought_chunk` | Collapsible “Thinking” |
| `agent_message_chunk` | Grok bubbles |
| `tool_call` / updates | Tool cards (title, status, output snippet) |
| `plan` | Plan block |
| `session_recap` | Recap strip |
| `turn_completed` / tasks | Status chips |
| queue / permission | Queue line + Allow/Deny cards |

Also pulls `_x.ai/prompt_history` for a prompt-count chip after load. Further desktop activity on a **resident** session continues streaming to the phone.

**Tips**

- Prefer **one writer** per session if desktop and phone both prompt the same id.
- Deep link: `http://LAN_IP:2421/?auto=1&session=019f4535-…`
- PC list: `grok sessions list`
- Hard-refresh the phone page after UI updates (cache-buster: add `?v=2`)

## Quick start (same Wi‑Fi)

On the PC (in the repo/workdir you want Grok to use):

```powershell
cd C:\Users\antho\Documents\ai\grok-remote
.\start.ps1 -Cwd C:\Users\antho\Documents\ai
```

On Android (**same Wi‑Fi as the PC**, not mobile data):

1. Open the printed URL, e.g. `http://192.168.0.7:2421/?auto=1`
2. Tap **Connect** if it doesn’t auto-connect
3. If stuck, tap **Health check** on the setup screen

### Why “never connects” usually happens

| Mistake | What goes wrong |
|---------|-----------------|
| Open `http://127.0.0.1:2421` on the phone | 127.0.0.1 is the *phone*, not the PC |
| Config pointed WS at `127.0.0.1:2420` | Phone can’t reach PC localhost |
| Agent/UI only bound to 127.0.0.1 | Phone never reaches either service |
| Phone on cellular / guest Wi‑Fi | Different network |

**Fixed design:** UI listens on `0.0.0.0:2421` and **proxies** `/ws` to the agent on `127.0.0.1`. Phone only needs one URL; secret stays on the PC.

Tap **Connect** if it doesn’t auto-connect.

## Flags

| Flag | Meaning |
|------|---------|
| `-Cwd PATH` | Agent working directory (your project) |
| `-AlwaysApprove` | Auto-approve tool runs (recommended for phone) |
| `-Port 2419` | Agent WebSocket port |
| `-UiPort 2421` | Mobile web UI port |
| `-Secret ...` | Fixed secret (else random each launch) |
| `-Tunnel` | cloudflared tunnel for the UI (see note) |
| `-NoUi` | Only agent serve (bring your own client) |

## Manual (no script)

```powershell
# Terminal 1 — agent (do not kill other grok PIDs)
$env:GROK_AGENT_SECRET = "mysecret"
grok agent --always-approve serve --bind 0.0.0.0:2419 --secret mysecret

# Terminal 2 — phone UI
python server.py --port 2421 --agent-host 192.168.1.10 --agent-port 2419 --secret mysecret --cwd C:\Users\antho\Documents\ai
```

## Off-network / mobile data

1. **VPN to home** (WireGuard/Tailscale) — easiest; phone uses LAN IPs.
2. **Two tunnels** (UI + agent WS), or a reverse proxy that terminates WSS and forwards both.
3. `-Tunnel` only exposes the **UI** by default; the WebSocket still needs a public `wss://` path to the agent (or VPN).

## Safety

- Random secret each run unless you set `-Secret`
- Prefer LAN/VPN over exposing agent to the open internet
- `-AlwaysApprove` lets tools run without phone prompts — only on trusted networks
- **Never** `Stop-Process -Name grok` — that kills *all* Grok sessions (including your desktop TUI)

## Files

| Path | Role |
|------|------|
| `start.ps1` | Launcher (agent + UI) |
| `server.py` | Serves mobile UI + `/config.json` |
| `web/index.html` | Phone chat client (ACP) |
| `logs/` | Agent/UI logs |

## Verify ACP

With agent listening:

```powershell
python _probe_acp.py "ws://127.0.0.1:2419/ws?server-key=YOUR_SECRET"
```
