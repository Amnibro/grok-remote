# Publishing Grok-Remote as a Grok marketplace / plugin item

## What “publish” means on Grok

Grok does **not** currently push community plugins to a single global xAI store from this CLI. Distribution works like this:

| Goal | How |
|------|-----|
| **You** get `/remote` on this machine | Local install (done via `install-local.ps1`) |
| **Teammates** install it | GitHub repo + `grok plugin install you/grok-remote --trust` |
| **Browseable marketplace** | Your own marketplace git repo with `marketplace.json` + `grok plugin marketplace add …` |
| Official Anthropic/xAI catalog | Separate process (PR to their public plugin repos if accepted) — not automatic |

## 1. Local install (slash commands on your PC)

```powershell
cd C:\Users\antho\Documents\ai\grok-remote
.\install-local.ps1
```

Or:

```powershell
grok plugin install C:\Users\antho\Documents\ai\grok-remote --trust
grok plugin enable grok-remote
```

### Local marketplace (already set up)

```powershell
grok plugin marketplace add C:\Users\antho\Documents\ai\marketplace\grok-remote-market
grok plugin marketplace list
```

In TUI: `/marketplace` → **grok-remote-market** → install **grok-remote** (v1.1.0).

User plugins live under `~/.grok/plugins/`. Reload with `/plugins` → `r`.

Then:

```
/remote
/remote status
/remote-stop
```

## 2. Publish for others (GitHub)

1. Create a public repo, e.g. `yourname/grok-remote`.
2. Push **this directory** as the repo root (includes `.claude-plugin/plugin.json`, `skills/`, `commands/`, `web/`, `server.py`, `start.ps1`).
3. Update `.claude-plugin/plugin.json` → `homepage` to that repo URL.
4. Tag a release:

```powershell
cd C:\Users\antho\Documents\ai\grok-remote
git init   # if needed
git add .
git commit -m "Grok-Remote v1.0.0"
git tag v1.0.0
git remote add origin https://github.com/YOURNAME/grok-remote.git
git push -u origin main --tags
```

Others install:

```bash
grok plugin install YOURNAME/grok-remote --trust
grok plugin enable grok-remote
```

Or pin a version:

```bash
grok plugin install YOURNAME/grok-remote@v1.0.0 --trust
```

Validate before push:

```bash
grok plugin validate .
```

## 3. Optional: personal marketplace catalog

Repo layout:

```
my-grok-marketplace/
  .claude-plugin/marketplace.json
  plugins/grok-remote/   # or source: url to your repo
```

Example `marketplace.json` entry:

```json
{
  "name": "my-marketplace",
  "description": "Anthony's Grok plugins",
  "owner": { "name": "Anthony" },
  "plugins": [
    {
      "name": "grok-remote",
      "description": "Control Grok Build from Android over LAN (ACP remote UI).",
      "category": "productivity",
      "source": {
        "source": "url",
        "url": "https://github.com/YOURNAME/grok-remote.git"
      },
      "homepage": "https://github.com/YOURNAME/grok-remote"
    }
  ]
}
```

Users:

```bash
grok plugin marketplace add YOURNAME/my-grok-marketplace
# or local:
grok plugin marketplace add C:\path\to\my-grok-marketplace
grok plugin marketplace list
```

Then install from the Marketplace tab (`/marketplace`) or CLI.

## 4. After install — how people use it

1. In Grok TUI: `/remote`
2. Open the printed URL on phone (same Wi‑Fi): `http://LAN_IP:2421/?auto=1`
3. Pick a **session** (resident = live desktop chat) — history + thoughts + tools load
4. Chat from the phone

## Checklist

- [x] `plugin.json` name `grok-remote`
- [x] Skill `skills/remote` → `/remote`
- [x] Commands `commands/remote.md`, `remote-stop.md`
- [x] Runtime files `start.ps1`, `server.py`, `web/`
- [ ] Push to GitHub (your account)
- [ ] Optional marketplace repo
- [ ] `grok plugin validate` clean
- [ ] Fresh TUI: `/remote` works
