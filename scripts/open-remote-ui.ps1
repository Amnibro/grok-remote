# Waits for the UI to be healthy, then opens the browser WITH the pairing key.
# Never open a bare http://127.0.0.1:port/ — that 401s as raw JSON.
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
$url = ""
$connectFile = Join-Path $pluginRoot "connect.url"
if (Test-Path $connectFile) {
  $line = (Get-Content $connectFile -Raw).Trim()
  if ($line -match "^https?://" -and $line -match "[\?&]key=") { $url = $line }
}
if (-not $url) {
  $secretFile = Join-Path $pluginRoot ".ui-secret"
  $secret = ""
  if (Test-Path $secretFile) { $secret = (Get-Content $secretFile -Raw).Trim() }
  if ($secret) {
    $url = "http://127.0.0.1:$UiPort/?key=$secret&auto=1"
  } else {
    $url = "http://127.0.0.1:$UiPort/?auto=1"
  }
}
Start-Process $url
if (-not $healthy) {
  Write-Host ("Grok Remote did not report healthy within {0}s - check logs under {1}\logs" -f $TimeoutSec, $pluginRoot) -ForegroundColor Yellow
}
if ($url -notmatch "[\?&]key=") {
  Write-Host "Opened without a pairing key - expect 401 until connect.url or .ui-secret exists." -ForegroundColor Yellow
}
