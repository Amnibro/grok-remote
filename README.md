# Grok Remote

**Live phone/browser controller for [Grok Build](https://x.ai)** — control your PC agent from Android (or any browser) over the LAN.

**Repo:** https://github.com/Amnibro/grok-remote  

**Plugin:** `/remote` · `/remote-stop`

## Install (anyone)

```bash
grok plugin install Amnibro/grok-remote --trust
grok plugin enable grok-remote
```

Pin a version:

```bash
grok plugin install Amnibro/grok-remote@v1.1.0 --trust
```

In the TUI, reload plugins if needed (`/plugins` → `r`), then:

```
/remote
```

Open the printed URL on your phone (same Wi‑Fi), e.g. `http://192.168.x.x:2421/?auto=1`.

## What you get

| Feature | Detail |
|---------|--------|
| Session picker | List + load desktop / historical chats (`resident` = live) |
| Full history | Messages, thinking, tools, plans, recaps on load |
| Live stream | ACP updates + ~0.8s catch-up for PC-side prompts |
| Skills | Quick slash-command palette |
| New Task | New session at a stated cwd + optional first prompt |
| Back swipe | Returns to Sessions (does not leave the site) |
| One phone URL | UI proxies WebSocket; agent secret stays on the PC |

## Manual start (without the plugin)

```powershell
cd path\to\grok-remote
.\start.ps1 -Cwd C:\path\to\your\project
```

## Architecture

```
Phone browser  --HTTP-->  UI+proxy :2421
               --WS /ws-->  (proxy) --> grok agent serve 127.0.0.1:2419
                                              │
                                         tools / files on PC
```

## Safety

- Prefer same Wi‑Fi / VPN; don’t expose the agent to the open internet without care.
- Never `Stop-Process -Name grok` (kills every Grok session on the machine).
- `/remote-stop` only stops remote UI + remote agent serve.

## License

MIT — see [LICENSE](./LICENSE).

## Docs

- [PUBLISH.md](./PUBLISH.md) — marketplaces and distribution
- Plugin skill: `skills/remote/SKILL.md`
