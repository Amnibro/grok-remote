param(
  [int]$UiPort = 2421,
  [int]$AgentPort = 2419,
  [string]$Secret = "",
  [string]$Cwd = "",
  [string]$Bind = "0.0.0.0"
)
$ErrorActionPreference = "Continue"
$pluginRoot = if ($env:GROK_PLUGIN_ROOT) { $env:GROK_PLUGIN_ROOT } else { Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path) }
$logDir = Join-Path $pluginRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
if (-not $Secret) { $Secret = $env:GROK_AGENT_SECRET }
if (-not $Secret) {
  $sf = Join-Path $pluginRoot ".ui-secret"
  if (Test-Path $sf) { $Secret = (Get-Content $sf -Raw).Trim() }
}
if (-not $Secret) {
  $cmd = Join-Path $logDir "run-agent.cmd"
  if (Test-Path $cmd) {
    $m = Select-String -Path $cmd -Pattern "GROK_AGENT_SECRET=(\S+)|--secret\s+(\S+)" | Select-Object -First 1
    if ($m) { $Secret = @($m.Matches[0].Groups[1].Value, $m.Matches[0].Groups[2].Value) | Where-Object { $_ } | Select-Object -First 1 }
  }
}
if (-not $Secret) { throw "No secret: set GROK_AGENT_SECRET or run start.ps1 once" }
if (-not $Cwd) { $Cwd = Join-Path $env:USERPROFILE "Documents\ai"; if (-not (Test-Path $Cwd)) { $Cwd = $env:USERPROFILE } }
$py = (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
if (-not $py) { $py = "python" }
$server = Join-Path $pluginRoot "server.py"
$env:GROK_AGENT_SECRET = $Secret
$supLog = Join-Path $logDir "supervisor.log"
function Log([string]$m) { Add-Content -Path $supLog -Value ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m) -ErrorAction SilentlyContinue }
Log "supervise-ui start port=$UiPort"
function PortOpen([int]$p) {
  try {
    $c = New-Object System.Net.Sockets.TcpClient
    $iar = $c.BeginConnect("127.0.0.1", $p, $null, $null)
    $ok = $iar.AsyncWaitHandle.WaitOne(400, $false) -and $c.Connected
    try { $c.Close() } catch {}
    return [bool]$ok
  } catch { return $false }
}
while ($true) {
  try {
    $h = Invoke-RestMethod ("http://127.0.0.1:{0}/health" -f $UiPort) -TimeoutSec 6
    if ($h.ok) { Start-Sleep -Seconds 8; continue }
  } catch {}
  if (PortOpen $UiPort) { Log "port $UiPort open, health slow  - not killing"; Start-Sleep -Seconds 8; continue }
  $lines = netstat -ano | Select-String (":{0}\s+.*LISTENING" -f $UiPort)
  foreach ($ln in $lines) {
    $procId = ($ln.ToString().Trim() -split "\s+")[-1]
    if ($procId -match "^\d+$" -and [int]$procId -gt 0) {
      Log "claim port $UiPort pid=$procId"
      cmd /c "taskkill /F /PID $procId" 2>$null | Out-Null
    }
  }
  Start-Sleep -Seconds 1
  Log "spawn server.py"
  $run = Join-Path $logDir "run-ui.cmd"
  $out = Join-Path $logDir "ui.out.log"
  $err = Join-Path $logDir "ui.err.log"
  @(
    "@echo off",
    "cd /d `"$pluginRoot`"",
    "set GROK_AGENT_SECRET=$Secret",
    "`"$py`" -u `"$server`" --port $UiPort --bind $Bind --agent-host 127.0.0.1 --agent-port $AgentPort --secret $Secret --cwd `"$Cwd`" --ensure-agent >> `"$out`" 2>> `"$err`""
  ) | Set-Content -Path $run -Encoding ASCII
  $p = Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $run) -WorkingDirectory $pluginRoot -WindowStyle Hidden -PassThru
  $deadline = (Get-Date).AddSeconds(20)
  $up = $false
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 2
    if ($p.HasExited) { Log ("ui launcher exited code={0}" -f $p.ExitCode); break }
    try {
      $h = Invoke-RestMethod ("http://127.0.0.1:{0}/health" -f $UiPort) -TimeoutSec 6
      if ($h.ok) { $up = $true; break }
    } catch {}
  }
  if (-not $up) { Log "ui failed to become healthy"; Start-Sleep -Seconds 3; continue }
  while ($true) {
    Start-Sleep -Seconds 8
    try {
      $h = Invoke-RestMethod ("http://127.0.0.1:{0}/health" -f $UiPort) -TimeoutSec 6
      if (-not $h.ok) { Log "health not ok · wait"; Start-Sleep -Seconds 8; continue }
    } catch {
      if (PortOpen $UiPort) { Log "health fail but port open  - not restarting"; continue }
      Log "health fail · restart"
      break
    }
  }
  $lines = netstat -ano | Select-String (":{0}\s+.*LISTENING" -f $UiPort)
  foreach ($ln in $lines) {
    $procId = ($ln.ToString().Trim() -split "\s+")[-1]
    if ($procId -match "^\d+$" -and [int]$procId -gt 0) {
      cmd /c "taskkill /F /PID $procId" 2>$null | Out-Null
    }
  }
  Start-Sleep -Seconds 2
}
