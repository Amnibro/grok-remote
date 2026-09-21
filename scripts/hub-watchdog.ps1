param(
  [int]$Port = 2421,
  [int]$IntervalSec = 10,
  [int]$TimeoutSec = 5,
  [int]$FailsBeforeKill = 3,
  [string]$HealthPath = "/health",
  [string]$RespawnExe = "",
  [string]$RespawnArgs = "",
  [string]$Name = "hub",
  [switch]$Once
)
$ErrorActionPreference = "Continue"
$root = if ($env:GROK_PLUGIN_ROOT) { $env:GROK_PLUGIN_ROOT } else { Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path) }
$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "watchdog.log"
function Log([string]$m) { $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m; Add-Content -Path $log -Value $line -ErrorAction SilentlyContinue; Write-Output $line }
function ListenerPid([int]$p) {
  $rows = netstat -ano | Select-String (":{0}\s+.*LISTENING" -f $p)
  foreach ($r in $rows) {
    $id = ($r.ToString().Trim() -split "\s+")[-1]
    if ($id -match "^\d+$" -and [int]$id -gt 0) { return [int]$id }
  }
  return 0
}
function Respawn {
  if (-not $RespawnExe) { Log "no respawn command set - leaving it to the external supervisor"; return }
  Log ("respawning: {0} {1}" -f $RespawnExe, $RespawnArgs)
  try {
    Start-Process -FilePath $RespawnExe -ArgumentList $RespawnArgs -WorkingDirectory $root -WindowStyle Hidden | Out-Null
    Start-Sleep -Seconds 4
    $back = ListenerPid $Port
    Log ("after respawn: listener pid={0}" -f $back)
  } catch { Log ("respawn failed: {0}" -f $_.Exception.Message) }
}
Log ("watchdog start name=$Name port=$Port path=$HealthPath every=${IntervalSec}s kill-after=$FailsBeforeKill fails")
$fails = 0
while ($true) {
  $ok = $false
  try {
    $h = Invoke-RestMethod ("http://127.0.0.1:{0}{1}" -f $Port, $HealthPath) -TimeoutSec $TimeoutSec
    if ($h) { $ok = $true }
  } catch { }
  if ($ok) {
    if ($fails -gt 0) { Log "health recovered after $fails fail(s)" }
    $fails = 0
  } else {
    $fails++
    $procId = ListenerPid $Port
    Log ("health fail {0}/{1} listener pid={2}" -f $fails, $FailsBeforeKill, $procId)
    if ($fails -ge $FailsBeforeKill) {
      if ($procId -gt 0) {
        Log ("wedged-but-alive: killing pid $procId so the supervisor can respawn")
        cmd /c "taskkill /F /PID $procId" 2>$null | Out-Null
        Start-Sleep -Seconds 2
        $still = Get-Process -Id $procId -ErrorAction SilentlyContinue
        Log ("after kill: pid alive={0}" -f (@($still).Count))
        Respawn
      } else {
        Log "no listener on port - nothing to kill"
        Respawn
      }
      $fails = 0
    }
  }
  if ($Once) { break }
  Start-Sleep -Seconds $IntervalSec
}
