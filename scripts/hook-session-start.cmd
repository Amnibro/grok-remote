@echo off
REM Grok SessionStart hook — only starts remote if config.autostart is true
setlocal
if "%GROK_PLUGIN_ROOT%"=="" (
  REM global hook fallback: user plugin path
  if exist "%USERPROFILE%\.grok\plugins\grok-remote\scripts\ensure-running.ps1" (
    set "GROK_PLUGIN_ROOT=%USERPROFILE%\.grok\plugins\grok-remote"
  ) else (
    exit /b 0
  )
)
if not exist "%GROK_PLUGIN_ROOT%\scripts\ensure-running.ps1" exit /b 0
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%GROK_PLUGIN_ROOT%\scripts\ensure-running.ps1" -Reason session >nul 2>&1
exit /b 0
