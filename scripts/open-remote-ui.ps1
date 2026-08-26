param([int]$UiPort = 2421, [int]$TimeoutSec = 30, [switch]$NoBrowser)
$ErrorActionPreference = "Continue"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pluginRoot = Split-Path -Parent $here
$healthy = $false
$deadline = (Get-Date).AddSeconds($TimeoutSec)
while ((Get-Date) -lt $deadline) {
  try {
    $h = Invoke-RestMethod "http://127.0.0.1:$UiPort/health" -TimeoutSec 2
    if ($h.ok) { $healthy = $true; break }
  } catch {}
  Start-Sleep -Milliseconds 400
}
$url = ""
$connectFile = Join-Path $pluginRoot "connect.url"
if (Test-Path $connectFile) {
  $line = (Get-Content $connectFile -Raw).Trim()
  if ($line -match "^https?://" -and $line -match "[\?&]key=") { $url = $line }
}
if (-not $url) {
  try {
    $c = Invoke-RestMethod "http://127.0.0.1:$UiPort/config.json" -TimeoutSec 3
    if ($c.ui) { $url = [string]$c.ui }
  } catch {}
}
if (-not $url) {
  $secretFile = Join-Path $pluginRoot ".ui-secret"
  $secret = ""
  if (Test-Path $secretFile) { $secret = (Get-Content $secretFile -Raw).Trim() }
  if (-not $secret) { $secret = $env:GROK_AGENT_SECRET }
  if ($secret) { $url = "http://127.0.0.1:$UiPort/?key=$secret&auto=1" }
  else { $url = "http://127.0.0.1:$UiPort/?auto=1" }
}
if ($url -notmatch "auto=") { $url += ($(if ($url -match "\?") { "&" } else { "?" }) + "auto=1") }
if (-not $NoBrowser) {
  try { Start-Process $url } catch { Write-Host "Could not open browser: $url" }
}
Write-Host $url
if (-not $healthy) {
  Write-Host ("Grok Remote not healthy within {0}s  - run Desktop shortcut again or scripts\ensure-running.ps1 -Force" -f $TimeoutSec) -ForegroundColor Yellow
}
if ($url -notmatch "[\?&]key=") {
  Write-Host "Opened without pairing key  - expect 401 until stack restarts with a secret." -ForegroundColor Yellow
}
