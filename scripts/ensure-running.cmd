@echo off
REM Works from cmd.exe or PowerShell: ensure-running.cmd [-Force]
setlocal
set "SCRIPT=%~dp0ensure-running.ps1"
if not exist "%SCRIPT%" (
  echo Missing: %SCRIPT%
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" %*
exit /b %ERRORLEVEL%
