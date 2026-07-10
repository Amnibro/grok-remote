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
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:2421/?auto=1"
exit /b 0
