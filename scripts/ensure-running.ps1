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
try {
  $h = Invoke-RestMethod ("http://127.0.0.1:{0}/health" -f $uiPort) -TimeoutSec 2
  if ($h.ok) { Log ("ok ({0}): already healthy on {1}" -f $Reason, $uiPort); exit 0 }
  Log ("health not ok ({0}): restarting" -f $Reason)
} catch {
  Log ("not running ({0}): {1}" -f $Reason, $_.Exception.Message)
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
$cmdSup = Join-Path $logDir "cmd-supervise.cmd"
$cmdAlive = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -and $_.CommandLine -match "cmd-supervise\.cmd" }
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
  if (-not $py) { $py = "python" }
  if ($secret -and (Test-Path (Join-Path $pluginRoot "server.py"))) {
    $body = @"
@echo off
cd /d "$pluginRoot"
set GROK_AGENT_SECRET=$secret
echo [%date% %time%] cmd-supervise start>> logs\supervisor.log
:loop
echo [%date% %time%] spawn>> logs\supervisor.log
"$py" -u server.py --port $uiPort --bind 0.0.0.0 --agent-host 127.0.0.1 --agent-port $agentPort --secret $secret --cwd "$cwd" --ensure-agent >> logs\ui.out.log 2>> logs\ui.err.log
echo [%date% %time%] exit=%ERRORLEVEL%>> logs\supervisor.log
if "%ERRORLEVEL%"=="97" (
echo [%date% %time%] healthy instance owns the port - supervisor exiting>> logs\supervisor.log
goto :eof
)
ping -n 4 127.0.0.1 >nul
goto loop
"@
    [System.IO.File]::WriteAllText($cmdSup, $body)
    try {
      $null = ([wmiclass]"Win32_Process").Create("cmd.exe /c `"$cmdSup`"")
      Log ("spawned cmd-supervise ({0}) ui={1}" -f $Reason, $uiPort)
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
