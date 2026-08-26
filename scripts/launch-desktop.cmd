@echo off
setlocal
cd /d "%~dp0.."
set EXE=%~dp0..\desktop-tauri\src-tauri\target\release\grok-remote-desktop.exe
set DIST=%~dp0..\desktop-tauri\dist\GrokRemote.exe
if exist "%EXE%" (
  start "" "%EXE%"
  goto :eof
)
if exist "%DIST%" (
  start "" "%DIST%"
  goto :eof
)
echo Build the Tauri exe first: cd desktop-tauri ^&^& npm install ^&^& npm run build
endlocal
