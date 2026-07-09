# Grok Remote Control - agent (localhost) + UI/proxy (LAN) for Android
# Phone opens http://LAN_IP:2421/  - WebSocket is same-origin /ws (proxied).
param(
  [string]$Bind = "0.0.0.0",
  [int]$Port = 2419,
  [int]$UiPort = 2421,
  [string]$Cwd = "",
  [string]$Secret = "",
  [string]$Grok = "",
  [switch]$AlwaysApprove,
  [switch]$OpenFirewall,
  [switch]$NoUi,
  [switch]$NoLeader
)
$ErrorActionPreference = "Stop"
if (-not $Cwd) { $Cwd = (Get-Location).Path }
if (-not $Grok) {
  $cand = @(
    "$env:USERPROFILE\.grok\bin\grok.exe",
    (Get-Command grok -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
  ) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
  if (-not $cand) { throw "grok.exe not found" }
  $Grok = $cand
}
if (-not $Secret) {
  $bytes = New-Object byte[] 16
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  $Secret = ([BitConverter]::ToString($bytes) -replace "-","").ToLower()
}
$env:GROK_AGENT_SECRET = $Secret
function Get-LanIp {
  try {
    $c = New-Object System.Net.Sockets.UdpClient
    $c.Connect("8.8.8.8", 80)
    $ip = ([Net.IPEndPoint]$c.Client.LocalEndPoint).Address.ToString()
    $c.Close(); return $ip
  } catch { return "127.0.0.1" }
}
$lan = Get-LanIp
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $here "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$script:OurPids = @()
function Stop-Ours {
  foreach ($id in $script:OurPids) {
    try { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue } catch {}
  }
}
function Ensure-PortFree([int]$p) {
  $lines = netstat -ano | Select-String ":$p\s+.*LISTENING"
  if (-not $lines) { return }
  Write-Host "Port $p already in use:" -ForegroundColor Yellow
  $lines | ForEach-Object { Write-Host "  $_" }
}
Ensure-PortFree $Port
Ensure-PortFree $UiPort
Write-Host ""
Write-Host "=== Grok Remote Control ===" -ForegroundColor Yellow
Write-Host "Grok:     $Grok"
Write-Host "CWD:      $Cwd"
Write-Host "Agent:    127.0.0.1:$Port  (localhost only)"
Write-Host "Phone UI: http://${lan}:${UiPort}/"
Write-Host "Phone WS: ws://${lan}:${UiPort}/ws  (proxied, secret server-side)"
Write-Host "Secret:   $Secret"
Write-Host ""
Write-Host "On Android: open  http://${lan}:${UiPort}/?auto=1" -ForegroundColor Cyan
Write-Host "Never: Stop-Process -Name grok  (kills desktop TUI)" -ForegroundColor DarkYellow
Write-Host ""
$agentLog = Join-Path $logDir "agent.log"
$agentArgs = @("agent", "--always-approve", "serve", "--bind", "127.0.0.1:$Port", "--secret", $Secret)
if (-not $NoLeader -and $env:GROK_REMOTE_LEADER -eq "1") {
  $agentArgs = @("agent", "--always-approve", "--leader", "serve", "--bind", "127.0.0.1:$Port", "--secret", $Secret)
}
# Start grok serve directly (cmd-redirect sometimes swallows long-lived servers on Windows)
$agent = Start-Process -FilePath $Grok -ArgumentList $agentArgs -WorkingDirectory $Cwd -PassThru -WindowStyle Hidden
$script:OurPids += $agent.Id
$ok = $false
for ($i = 0; $i -lt 25; $i++) {
  Start-Sleep -Seconds 1
  if (netstat -an | Select-String "127.0.0.1:$Port\s+.*LISTENING") { $ok = $true; break }
  if ($agent.HasExited) { Write-Host "Agent process exited early code=$($agent.ExitCode)" -ForegroundColor Red; break }
}
if (-not $ok) {
  Write-Host "Agent failed to listen on 127.0.0.1:$Port" -ForegroundColor Red
  Get-Content (Join-Path $logDir "agent.log") -ErrorAction SilentlyContinue | Select-Object -Last 40
  Stop-Ours; exit 1
}
Write-Host "Agent OK on 127.0.0.1:$Port" -ForegroundColor Green
if ($OpenFirewall) {
  $rule = "Grok Remote UI $UiPort"
  try { netsh advfirewall firewall delete rule name="$rule" | Out-Null } catch {}
  try {
    netsh advfirewall firewall add rule name="$rule" dir=in action=allow protocol=TCP localport=$UiPort profile=private,domain | Out-Null
    Write-Host "Firewall: allow inbound TCP $UiPort (private/domain)" -ForegroundColor Green
  } catch {
    Write-Host "Firewall rule skipped (need admin): $_" -ForegroundColor Yellow
  }
}
$ui = $null
if (-not $NoUi) {
  $py = (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
  if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source) }
  if (-not $py) { throw "python required for UI/proxy" }
  & $py -c "import aiohttp" 2>$null
  if ($LASTEXITCODE -ne 0) { & $py -m pip install aiohttp -q }
  $uiArgs = @(
    (Join-Path $here "server.py"),
    "--port", "$UiPort",
    "--bind", "0.0.0.0",
    "--agent-host", "127.0.0.1",
    "--agent-port", "$Port",
    "--secret", $Secret,
    "--cwd", $Cwd
  )
  $ui = Start-Process -FilePath $py -ArgumentList $uiArgs -WorkingDirectory $here -PassThru -WindowStyle Hidden
  $script:OurPids += $ui.Id
  Start-Sleep -Seconds 2
  $uiOk = netstat -an | Select-String "0.0.0.0:$UiPort\s+.*LISTENING|\[::\]:$UiPort\s+.*LISTENING|:$UiPort\s+.*LISTENING"
  if (-not $uiOk) {
    Write-Host "UI failed to bind 0.0.0.0:$UiPort - is an old server holding the port?" -ForegroundColor Red
    Write-Host "Check: netstat -ano | findstr $UiPort" -ForegroundColor Yellow
  } else {
    Write-Host "UI+proxy OK  http://${lan}:${UiPort}/" -ForegroundColor Green
  }
  "http://${lan}:${UiPort}/?auto=1" | Set-Content (Join-Path $here "connect.url") -Encoding ASCII
  try {
    $h = Invoke-RestMethod "http://127.0.0.1:${UiPort}/health" -TimeoutSec 5
    if ($h.ok) { Write-Host "Health: agent reachable through proxy" -ForegroundColor Green }
    else { Write-Host "Health: agent NOT reachable - $($h.detail)" -ForegroundColor Red }
  } catch {
    Write-Host "Health check failed: $_" -ForegroundColor Yellow
  }
}
Write-Host ""
Write-Host "Press Ctrl+C to stop remote control only." -ForegroundColor DarkGray
try {
  while ($true) {
    Start-Sleep -Seconds 2
    if ($agent.HasExited) { Write-Host "Agent process exited" -ForegroundColor Red; break }
    if ($ui -and $ui.HasExited) { Write-Host "UI process exited" -ForegroundColor Red; break }
  }
} finally {
  Stop-Ours
  Write-Host "Stopped our remote PIDs: $($script:OurPids -join ', ')" -ForegroundColor Yellow
}
