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
if (-not $Secret) { $Secret = $env:GROK_AGENT_SECRET }
if (-not $Secret) {
  $secretFile = Join-Path $PSScriptRoot ".ui-secret"
  if (Test-Path $secretFile) {
    $Secret = (Get-Content $secretFile -Raw).Trim()
  }
}
if (-not $Secret -or $Secret.Length -lt 16) {
  $bytes = New-Object byte[] 16
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  $Secret = ([BitConverter]::ToString($bytes) -replace "-","").ToLower()
  try { Set-Content -Path (Join-Path $PSScriptRoot ".ui-secret") -Value $Secret -NoNewline -Encoding ascii } catch {}
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
function Free-Port([int]$p, [string]$label) {
  $lines = netstat -ano | Select-String ":$p\s+.*LISTENING"
  if (-not $lines) { return }
  Write-Host "Claiming $label port $p (killing listeners)..." -ForegroundColor Yellow
  foreach ($ln in $lines) {
    $procId = ($ln.ToString().Trim() -split "\s+")[-1]
    if ($procId -match "^\d+$" -and [int]$procId -gt 0) {
      Write-Host "  taskkill /F /PID $procId"
      cmd /c "taskkill /F /PID $procId" 2>$null | Out-Null
    }
  }
  Start-Sleep -Seconds 1
}
$agentListening = $false
try { $agentListening = [bool](netstat -ano | Select-String ":$Port\s+.*LISTENING") } catch {}
$uiHealthy = $false
try {
  $h = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 -Uri "http://127.0.0.1:$UiPort/health"
  if ($h.StatusCode -eq 200 -and $h.Content -match 'ok') { $uiHealthy = $true }
} catch {}
if ($agentListening) { Write-Host "Agent already on :$Port — leaving it (mirror grok-build)" -ForegroundColor Green }
else { Free-Port $Port "agent" }
if ($uiHealthy) { Write-Host "UI already healthy on :$UiPort — leaving it" -ForegroundColor Green }
else { Free-Port $UiPort "UI" }
Write-Host ""
Write-Host "=== Grok Remote Control ===" -ForegroundColor Yellow
Write-Host "Grok:     $Grok"
Write-Host "CWD:      $Cwd"
Write-Host "Agent:    127.0.0.1:$Port  (localhost only)"
Write-Host "Phone UI: http://${lan}:${UiPort}/?key=$Secret"
Write-Host "Phone WS: ws://${lan}:${UiPort}/ws  (proxied, key-gated, secret server-side)"
Write-Host "Secret:   $Secret  (also the access key - anyone with this URL can use your agent)"
Write-Host ""
Write-Host "On Android: open  http://${lan}:${UiPort}/?key=$Secret&auto=1" -ForegroundColor Cyan
Write-Host "Never: Stop-Process -Name grok  (kills desktop TUI)" -ForegroundColor DarkYellow
Write-Host ""
$agentLog = Join-Path $logDir "agent.log"
$leaderFlag = "--no-leader"
if ((-not $NoLeader) -and ($env:GROK_REMOTE_LEADER -match '^(1|true|yes|on)$')) { $leaderFlag = "--leader" }
$agentArgs = @("agent", "--always-approve", $leaderFlag, "serve", "--bind", "127.0.0.1:$Port", "--secret", $Secret)
$agentCmd = Join-Path $logDir "run-agent.cmd"
@"
@echo off
cd /d "$Cwd"
set GROK_AGENT_SECRET=$Secret
"$Grok" $($agentArgs -join ' ') >> "$agentLog" 2>&1
"@ | Set-Content -Path $agentCmd -Encoding ASCII
if ($agentListening) {
  $ok = $true
  Write-Host "Agent OK (existing) on 127.0.0.1:$Port $leaderFlag" -ForegroundColor Green
} else {
  $agent = Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $agentCmd) -WorkingDirectory $Cwd -PassThru -WindowStyle Hidden
  $script:OurPids += $agent.Id
  $ok = $false
  for ($i = 0; $i -lt 25; $i++) {
    Start-Sleep -Seconds 1
    if (netstat -an | Select-String "127.0.0.1:$Port\s+.*LISTENING") { $ok = $true; break }
    if ($agent.HasExited) { Write-Host "Agent launcher exited early code=$($agent.ExitCode)" -ForegroundColor Red; break }
  }
  if (-not $ok) {
    Write-Host "Agent failed to listen on 127.0.0.1:$Port" -ForegroundColor Red
    Get-Content (Join-Path $logDir "agent.log") -ErrorAction SilentlyContinue | Select-Object -Last 40
    Stop-Ours; exit 1
  }
  Write-Host "Agent OK on 127.0.0.1:$Port $leaderFlag" -ForegroundColor Green
}
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
if ($uiHealthy) {
  Write-Host "UI already up — skip spawn (no disconnect)" -ForegroundColor Green
} elseif (-not $NoUi) {
  $py = (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
  if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source) }
  if (-not $py) { throw "python required for UI/proxy" }
  & $py -c "import aiohttp" 2>$null
  if ($LASTEXITCODE -ne 0) { & $py -m pip install aiohttp -q }
  $env:GROK_REMOTE_ENSURE_AGENT = "0"
  $logDirUi = $logDir
  $runUi = Join-Path $logDirUi "run-ui.cmd"
  $uiLine = "`"$py`" `"$(Join-Path $here 'server.py')`" --port $UiPort --bind 0.0.0.0 --agent-host 127.0.0.1 --agent-port $Port --secret $Secret --cwd `"$Cwd`" --ensure-agent >> `"$(Join-Path $logDirUi 'ui.out.log')`" 2>> `"$(Join-Path $logDirUi 'ui.err.log')`""
  @(
    "@echo off",
    "cd /d `"$here`"",
    "set GROK_AGENT_SECRET=$Secret",
    $uiLine
  ) | Set-Content -Path $runUi -Encoding ASCII
  $supPs1 = Join-Path $here "scripts\supervise-ui.ps1"
  if (Test-Path $supPs1) {
    $sup = Start-Process -FilePath "powershell.exe" -ArgumentList @(
      "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $supPs1,
      "-UiPort", "$UiPort", "-AgentPort", "$Port", "-Secret", $Secret, "-Cwd", $Cwd
    ) -WorkingDirectory $here -PassThru -WindowStyle Hidden
    $script:OurPids += $sup.Id
    $ui = $sup
    Write-Host "UI supervisor started (auto-restarts if it dies)" -ForegroundColor Green
  } else {
    $ui = Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $runUi) -WorkingDirectory $here -PassThru -WindowStyle Hidden
    $script:OurPids += $ui.Id
  }
  Start-Sleep -Seconds 4
  $uiOk = netstat -an | Select-String "0.0.0.0:$UiPort\s+.*LISTENING|\[::\]:$UiPort\s+.*LISTENING|:$UiPort\s+.*LISTENING"
  if (-not $uiOk) {
    Write-Host "UI failed to bind 0.0.0.0:$UiPort - is an old server holding the port?" -ForegroundColor Red
    Write-Host "Check: netstat -ano | findstr $UiPort" -ForegroundColor Yellow
    Get-Content (Join-Path $logDirUi "ui.err.log") -ErrorAction SilentlyContinue | Select-Object -Last 15
  } else {
    Write-Host "UI+proxy OK  http://${lan}:${UiPort}/" -ForegroundColor Green
  }
  $phoneUrl = "http://${lan}:${UiPort}/?key=$Secret&auto=1"
  $phoneUrl | Set-Content (Join-Path $here "connect.url") -Encoding ASCII
  try {
    $h = Invoke-RestMethod "http://127.0.0.1:${UiPort}/health?key=$Secret" -TimeoutSec 5
    if ($h.ok) { Write-Host "Health: agent reachable through proxy" -ForegroundColor Green }
    else { Write-Host "Health: agent NOT reachable - $($h.detail)" -ForegroundColor Red }
  } catch {
    Write-Host "Health check failed: $_" -ForegroundColor Yellow
  }
  Write-Host ""
  Write-Host "PHONE:  $phoneUrl" -ForegroundColor Cyan
  Write-Host "PC:     http://127.0.0.1:${UiPort}/?key=$Secret&auto=1" -ForegroundColor Cyan
  try {
    Start-Process ("http://127.0.0.1:${UiPort}/?key=$Secret&auto=1")
    Write-Host "Opened browser on this PC" -ForegroundColor Green
  } catch {}
}
Write-Host ""
Write-Host "Leave this window open, or use Desktop 'Grok Remote' (supervised). Ctrl+C stops remote only." -ForegroundColor DarkGray
try {
  while ($true) {
    Start-Sleep -Seconds 5
    if ($agent.HasExited) { Write-Host "Agent process exited" -ForegroundColor Red; break }
  }
} finally {
  Stop-Ours
  Write-Host "Stopped our remote PIDs: $($script:OurPids -join ', ')" -ForegroundColor Yellow
}
