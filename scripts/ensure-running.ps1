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
if (-not (Test-Path $start)) { Log "error: start.ps1 missing"; exit 0 }
$agentPort = 2419
try { if ($cfg.agent_port) { $agentPort = [int]$cfg.agent_port } } catch {}
$psArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $start, "-Cwd", $cwd, "-UiPort", "$uiPort", "-Port", "$agentPort")
if ($cfg.always_approve -ne $false) { $psArgs += "-AlwaysApprove" }
Log ("starting ({0}) cwd={1} ui={2}" -f $Reason, $cwd, $uiPort)
try {
  Start-Process -FilePath "powershell.exe" -ArgumentList $psArgs -WindowStyle Hidden | Out-Null
  Log "spawned start.ps1"
} catch {
  Log ("spawn failed: {0}" -f $_.Exception.Message)
}
exit 0
