# Restart ONLY Grok Remote UI proxy on :2421 (does not kill other Python).
# Leaves agent on :2419 alone. Uses secret from logs\run-agent.cmd if present.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$uiPort = 2421
$agentPort = 2419
$secret = $env:GROK_AGENT_SECRET
if (-not $secret) {
  $cmd = Join-Path $env:USERPROFILE ".grok\plugins\grok-remote\logs\run-agent.cmd"
  if (Test-Path $cmd) {
    $line = Select-String -Path $cmd -Pattern "GROK_AGENT_SECRET=(\S+)" | Select-Object -First 1
    if ($line) { $secret = $line.Matches[0].Groups[1].Value }
  }
}
if (-not $secret) { throw "Set GROK_AGENT_SECRET or ensure run-agent.cmd exists" }
# kill listeners on UI port only
$lines = netstat -ano | Select-String ":$uiPort\s+.*LISTENING"
foreach ($ln in $lines) {
  $procId = ($ln.ToString().Trim() -split "\s+")[-1]
  if ($procId -match "^\d+$" -and [int]$procId -ne $PID) {
    Write-Host "Stopping PID $procId on :$uiPort"
    cmd /c "taskkill /F /PID $procId" | Out-Null
  }
}
Start-Sleep -Seconds 1
$logDir = Join-Path $here "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$cwd = Join-Path $env:USERPROFILE "Documents\ai"
$runUi = Join-Path $logDir "run-ui.cmd"
$py = (Get-Command python).Source
@(
  "@echo off",
  "cd /d `"$here`"",
  "`"$py`" server.py --port $uiPort --bind 0.0.0.0 --agent-host 127.0.0.1 --agent-port $agentPort --secret $secret --cwd `"$cwd`" >> `"$logDir\ui.out.log`" 2>> `"$logDir\ui.err.log`""
) | Set-Content -Path $runUi -Encoding ASCII
Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $runUi) -WindowStyle Hidden | Out-Null
Write-Host "UI launching -> http://127.0.0.1:$uiPort/"
Start-Sleep -Seconds 3
try {
  $h = Invoke-RestMethod "http://127.0.0.1:$uiPort/health" -TimeoutSec 5
  Write-Host "Health ok=$($h.ok) hub_up=$($h.hub_up)"
} catch {
  Write-Host "Health failed: $_"
  Get-Content (Join-Path $logDir "ui.err.log") -ErrorAction SilentlyContinue | Select-Object -Last 20
}
