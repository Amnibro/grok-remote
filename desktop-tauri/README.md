# Grok Remote desktop (Tauri)

Window shell for the :2421 UI. Electron sources are in `../archive/electron-desktop/`.

Build: `npm install` then `npm run build`.

Run: `dist\GrokRemote.exe` or `src-tauri\target\release\grok-remote-desktop.exe`.

If :2421 is down, the exe starts `start.ps1`. Pairing key comes from `.ui-secret` or `logs/run-agent.cmd`.
