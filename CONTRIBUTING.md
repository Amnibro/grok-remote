# Contributing to Grok Remote

Thanks for helping. Keep changes small, testable, and free of personal machine paths in docs or screenshots.

## Setup

1. Clone the repo.
2. Install a recent Python 3 and (for screenshots) Chrome + `npm install` in the repo root if you use Playwright.
3. Start the UI from the repo:

```powershell
.\start.ps1 -Cwd .
```

Open `http://127.0.0.1:2421/?demo=1` for a safe UI with sample sessions.

## Guidelines

- **No secrets or personal paths** in commits (cwd, session titles, LAN IPs in docs screenshots).
- Prefer `?demo=1` for public screenshots.
- Default product theme is **Grok** (greyscale). Other accents stay optional.
- Delve and owner-only personas stay behind owner unlock — don’t surface them in default UI.
- Keep `web/index.html` and plugin copy in `~/.grok/plugins/grok-remote` in sync when testing locally.

## Screenshots

```bash
node scripts/capture-screenshots.mjs
```

Writes `docs/screenshots/*.png` from the running UI on `:2421`.

## PRs

- Clear description of *why*.
- Note any new ports, config keys, or slash commands.
- Update `changelog.md` and `architecture_map.md` when behavior changes.

## License

By contributing you agree your changes are under the MIT license.
