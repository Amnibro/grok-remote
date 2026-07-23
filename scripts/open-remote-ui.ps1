# Waits for the UI to actually be healthy, then opens the browser with the current pairing key.
# Called by launch-remote.cmd after ensure-running.ps1 has (asynchronously) started the stack.
param([int]$UiPort = 2421, [int]$TimeoutSec = 25)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pluginRoot = Split-Path -Parent $here
$healthy = $false
$deadline = (Get-Date).AddSeconds($TimeoutSec)
while ((Get-Date) -lt $deadline) {
  try {
    $h = Invoke-RestMethod "http://127.0.0.1:$UiPort/health" -TimeoutSec 2
    if ($h.ok) { $healthy = $true; break }
  } catch {}
  Start-Sleep -Milliseconds 500
}
$url = "http://127.0.0.1:$UiPort/?auto=1"
if ($healthy) {
  $connectFile = Join-Path $pluginRoot "connect.url"
  if (Test-Path $connectFile) {
    $line = (Get-Content $connectFile -Raw).Trim()
    if ($line -match "^https?://") { $url = $line }
  }
}
Start-Process $url
if (-not $healthy) {
  Write-Host ("Grok Remote did not report healthy within {0}s - opened without a pairing key, expect a 401." -f $TimeoutSec) -ForegroundColor Yellow
  Write-Host ("Check logs at " + $pluginRoot + "\logs\ui.err.log and " + $pluginRoot + "\logs\agent.log") -ForegroundColor Yellow
}
