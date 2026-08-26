# Idempotent: start Grok Remote if enabled and not already healthy.
param(
  [switch]$Force,
  [switch]$IgnoreConfig,
  [string]$Reason = "manual"
)
$ErrorActionPreference = "Continue"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pluginRoot = if ($env:GROK_PLUGIN_ROOT) { $env:GROK_PLUGIN_ROOT } else { Split-Path -Parent $here }
. (Join-Path $here "config-path.ps1")
$logDir = if ($env:GROK_PLUGIN_DATA) { Join-Path $env:GROK_PLUGIN_DATA "logs" } else { Join-Path $pluginRoot "logs" }
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "autostart.log"
function Log([string]$m) {
  $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m
  Add-Content -Path $log -Value $line -ErrorAction SilentlyContinue
}
$cfg = Get-GrokRemoteConfig
if (-not $IgnoreConfig -and -not $Force) {
  if (-not $cfg.autostart) { Log "skip ($Reason): autostart=false"; exit 0 }
  if ($Reason -eq "session" -and $cfg.autostart_on_session -eq $false) { Log "skip (session): autostart_on_session=false"; exit 0 }
  if ($Reason -eq "boot" -and $cfg.autostart_on_boot -eq $false) { Log "skip (boot): autostart_on_boot=false"; exit 0 }
}
$uiPort = 2421
try { if ($cfg.ui_port) { $uiPort = [int]$cfg.ui_port } } catch {}
function PortOpen([int]$p) {
  try {
    $c = New-Object System.Net.Sockets.TcpClient
    $iar = $c.BeginConnect("127.0.0.1", $p, $null, $null)
    $ok = $iar.AsyncWaitHandle.WaitOne(400, $false) -and $c.Connected
    try { $c.Close() } catch {}
    return [bool]$ok
  } catch { return $false }
}
if (PortOpen $uiPort) {
  try {
    $h = Invoke-RestMethod ("http://127.0.0.1:{0}/health" -f $uiPort) -TimeoutSec 6
    if ($h.ok) { Log ("ok ({0}): already healthy on {1}" -f $Reason, $uiPort); exit 0 }
    Log ("listener up, health sluggish ({0})  - not killing" -f $Reason)
    exit 0
  } catch {
    Log ("listener up, health timed out ({0})  - not killing" -f $Reason)
    exit 0
  }
}
$cwdFromHook = $null
if ($Reason -eq "session") {
  try {
    $raw = [Console]::In.ReadToEnd()
    if ($raw -and $raw.Trim()) {
      $ev = $raw | ConvertFrom-Json
      if ($ev.cwd) { $cwdFromHook = [string]$ev.cwd }
      elseif ($ev.workspaceRoot) { $cwdFromHook = [string]$ev.workspaceRoot }
    }
  } catch {}
}
$cwd = $cfg.cwd
if (-not $cwd -or ("$cwd".Trim() -eq "")) {
  if ($cwdFromHook) { $cwd = $cwdFromHook }
  elseif ($env:GROK_PROJECT_DIR) { $cwd = $env:GROK_PROJECT_DIR }
  elseif ($PWD) { $cwd = $PWD.Path }
  else { $cwd = $env:USERPROFILE }
}
$start = Join-Path $pluginRoot "start.ps1"
$sup = Join-Path $pluginRoot "scripts\supervise-ui.ps1"
if (-not (Test-Path $start) -and -not (Test-Path $sup)) { Log "error: start.ps1 / supervise-ui.ps1 missing"; exit 0 }
$agentPort = 2419
try { if ($cfg.agent_port) { $agentPort = [int]$cfg.agent_port } } catch {}
$agentUp = $false
try {
  $al = netstat -ano | Select-String (":{0}\s+.*LISTENING" -f $agentPort)
  if ($al) { $agentUp = $true }
} catch {}
if (-not $agentUp -and (Test-Path $start)) {
  $psArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $start, "-Cwd", $cwd, "-UiPort", "$uiPort", "-Port", "$agentPort", "-NoUi")
  if ($cfg.always_approve -ne $false) { $psArgs += "-AlwaysApprove" }
  Log ("starting agent via start.ps1 ({0}) cwd={1}" -f $Reason, $cwd)
  try { Start-Process -FilePath "powershell.exe" -ArgumentList $psArgs -WindowStyle Hidden | Out-Null } catch { Log ("agent spawn failed: {0}" -f $_.Exception.Message) }
  Start-Sleep -Seconds 2
}
# cmd reads a batch file line by line while it runs, so rewriting this path under a live
# supervisor corrupts that loop mid-flight (it exits 0 within milliseconds). Give every
# supervisor its own file and let old ones age out.
$cmdSup = Join-Path $logDir ("cmd-supervise-{0}.cmd" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
Get-ChildItem (Join-Path $logDir "cmd-supervise-*.cmd") -ErrorAction SilentlyContinue |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-1) } |
  Remove-Item -Force -ErrorAction SilentlyContinue
# Match the supervisor process itself, not anything that merely mentions it. A shell whose
# command line contained the word used to count as "already running", so this script would
# skip the spawn and nothing ever started.
$cmdAlive = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq "cmd.exe" -and $_.CommandLine -and $_.CommandLine -match "cmd-supervise" })
# Supervisors have stacked before: several loops each respawning the server every few seconds,
# all fighting for the port so none of them ever holds it. Keep the oldest, retire the rest,
# and clear out any server.py that is running without owning the port.
if ($cmdAlive.Count -gt 1) {
  $keep = ($cmdAlive | Sort-Object CreationDate | Select-Object -First 1).ProcessId
  foreach ($p in $cmdAlive) { if ($p.ProcessId -ne $keep) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } }
  Log ("retired {0} duplicate supervisor(s), kept {1}" -f ($cmdAlive.Count - 1), $keep)
  $cmdAlive = @($cmdAlive | Where-Object { $_.ProcessId -eq $keep })
}
if (PortOpen $uiPort) {
  Log ("port {0} is open  - skip orphan kill" -f $uiPort)
} else {
  $orphans = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "^python" -and $_.CommandLine -and $_.CommandLine -match "server\.py" -and ($_.CommandLine -like ("*" + $pluginRoot + "*") -or $_.CommandLine -like "*\grok-remote\*") })
  if ($orphans.Count) {
    foreach ($o in $orphans) { Stop-Process -Id $o.ProcessId -Force -ErrorAction SilentlyContinue }
    Log ("cleared {0} server.py process(es) with port {1} down" -f $orphans.Count, $uiPort)
    Start-Sleep -Milliseconds 600
  }
}
if (-not $cmdAlive) {
  $secret = $env:GROK_AGENT_SECRET
  if (-not $secret) {
    $sf = Join-Path $pluginRoot ".ui-secret"
    if (Test-Path $sf) { $secret = (Get-Content $sf -Raw).Trim() }
  }
  if (-not $secret) {
    $rac = Join-Path $logDir "run-agent.cmd"
    if (Test-Path $rac) {
      $m = Select-String -Path $rac -Pattern "GROK_AGENT_SECRET=(\S+)|--secret\s+(\S+)" | Select-Object -First 1
      if ($m) { $secret = @($m.Matches[0].Groups[1].Value, $m.Matches[0].Groups[2].Value) | Where-Object { $_ } | Select-Object -First 1 }
    }
  }
  $py = (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
  if (-not $py) { $py = "C:\Users\antho\AppData\Local\Programs\Python\Python312\python.exe" }
  # cmd holds an exclusive lock on a >> target. Two supervisors sharing one log meant the
  # second could not even launch python: the redirect failed, the line never ran, and it span
  # at "exit=0" forever. Per-instance logs remove the collision.
  $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $outLog = Join-Path $logDir ("ui-{0}.out.log" -f $stamp)
  $errLog = Join-Path $logDir ("ui-{0}.err.log" -f $stamp)
  Get-ChildItem (Join-Path $logDir "ui-*.log") -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-3) } |
    Remove-Item -Force -ErrorAction SilentlyContinue
  if ($secret -and (Test-Path (Join-Path $pluginRoot "server.py"))) {
    $body = @"
@echo off
cd /d "$pluginRoot"
set GROK_AGENT_SECRET=$secret
echo [%date% %time%] cmd-supervise start>> logs\supervisor.log
set WAIT=4
set FAILS=0
:loop
echo [%date% %time%] spawn>> logs\supervisor.log
"$py" -u server.py --port $uiPort --bind 0.0.0.0 --agent-host 127.0.0.1 --agent-port $agentPort --secret $secret --cwd "$cwd" --ensure-agent >> "$outLog" 2>> "$errLog"
set RC=%ERRORLEVEL%
rem a digit touching >> is read as a file handle, so keep a space before the redirect
echo [%date% %time%] exit=%RC% >> logs\supervisor.log
if "%RC%"=="97" (
echo [%date% %time%] healthy instance owns the port - supervisor exiting>> logs\supervisor.log
goto :eof
)
set /a FAILS+=1
if %FAILS% GEQ 12 (
echo [%date% %time%] 12 failed starts - standing down, the keepalive task will try again>> logs\supervisor.log
goto :eof
)
ping -n %WAIT% 127.0.0.1 >nul
set /a WAIT=%WAIT%*2
if %WAIT% GTR 61 set WAIT=61
goto loop
"@
    [System.IO.File]::WriteAllText($cmdSup, $body)
    try {
      Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $cmdSup) -WindowStyle Hidden | Out-Null
      Log ("spawned cmd-supervise hidden ({0}) ui={1}" -f $Reason, $uiPort)
    } catch {
      Log ("cmd-supervise failed: {0}" -f $_.Exception.Message)
    }
  } elseif (Test-Path $sup) {
    Log ("starting supervise-ui ({0}) ui={1}" -f $Reason, $uiPort)
    $supArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $sup, "-UiPort", "$uiPort", "-AgentPort", "$agentPort", "-Cwd", $cwd)
    try { Start-Process -FilePath "powershell.exe" -ArgumentList $supArgs -WindowStyle Hidden | Out-Null; Log "spawned supervise-ui.ps1" } catch { Log ("supervise spawn failed: {0}" -f $_.Exception.Message) }
  }
} else {
  Log ("cmd-supervise already running ({0})" -f $Reason)
}
if (-not (Test-Path $cmdSup) -and (Test-Path $start) -and -not $cmdAlive) {
  $psArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $start, "-Cwd", $cwd, "-UiPort", "$uiPort", "-Port", "$agentPort")
  if ($cfg.always_approve -ne $false) { $psArgs += "-AlwaysApprove" }
  Log ("fallback start.ps1 ({0})" -f $Reason)
  try { Start-Process -FilePath "powershell.exe" -ArgumentList $psArgs -WindowStyle Hidden | Out-Null } catch {}
}
exit 0
