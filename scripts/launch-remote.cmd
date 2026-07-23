@echo off
REM One-click: ensure Grok Remote is up, then open the UI
set "ROOT=%~dp0.."
set "ENSURE=%ROOT%\scripts\ensure-running.ps1"
if not exist "%ENSURE%" set "ENSURE=%USERPROFILE%\.grok\plugins\grok-remote\scripts\ensure-running.ps1"
if not exist "%ENSURE%" (
  echo ensure-running.ps1 not found
  pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ENSURE%" -Force -IgnoreConfig -Reason "shortcut"
set "OPENUI=%ROOT%\scripts\open-remote-ui.ps1"
if not exist "%OPENUI%" set "OPENUI=%USERPROFILE%\.grok\plugins\grok-remote\scripts\open-remote-ui.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%OPENUI%"
exit /b 0
