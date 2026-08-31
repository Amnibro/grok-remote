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
cd <repos>\grok-remote
.\install-local.ps1
```

Or:

```powershell
grok plugin install <repos>\grok-remote --trust
grok plugin enable grok-remote
```

### Local marketplace (already set up)

```powershell
grok plugin marketplace add <repos>\marketplace\grok-remote-market
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
cd <repos>\grok-remote
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

## 3b. Windows desktop app

The plugin is the hub (`:2421`). The optional **Tauri** window is a separate download (not inside the plugin, so install stays small).

| Get | URL |
|-----|-----|
| Product page | https://amni-scient.com/grok-remote.html |
| Portable exe | https://github.com/Amnibro/grok-remote/releases/latest/download/GrokRemote.exe |
| NSIS setup | https://github.com/Amnibro/grok-remote/releases/latest/download/Grok.Remote_1.4.4_x64-setup.exe |
| GitHub releases | https://github.com/Amnibro/grok-remote/releases |

Ship a new desktop build: `cd desktop-tauri && npm run build`, then attach `grok-remote-desktop.exe` as `GrokRemote.exe` plus the NSIS/MSI bundles to the GitHub release. Cloudflare/GitHub Pages is a poor host for the binary — prefer the release asset.

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
- [x] Windows desktop: GitHub release `GrokRemote.exe` + amni-scient product page
- [ ] Push to GitHub (your account)
- [ ] Optional marketplace repo
- [ ] `grok plugin validate` clean
- [ ] Fresh TUI: `/remote` works
