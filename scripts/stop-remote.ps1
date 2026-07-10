# Stop ONLY Grok Remote UI (:2421) and remote agent serve (:2419).
# Never kills desktop TUI by process name. Never mass-kills python/grok.
param(
  [int]$UiPort = 2421,
  [int]$AgentPort = 2419,
  [switch]$KeepAgent
)
$ErrorActionPreference = "Continue"
function Get-ListenPids([int]$port) {
  $pids = @()
  $lines = netstat -ano 2>$null | Select-String "LISTENING"
  foreach ($ln in $lines) {
    $s = $ln.ToString().Trim()
    if ($s -notmatch (":{0}\s+" -f $port)) { continue }
    $parts = $s -split "\s+"
    $id = $parts[-1]
    if ($id -match "^\d+$" -and [int]$id -ne $PID) { $pids += [int]$id }
  }
  return ($pids | Select-Object -Unique)
}
function Stop-Pids($list, [string]$label) {
  $killed = @()
  foreach ($id in $list) {
    try {
      Write-Host "Stopping $label PID $id"
      $null = cmd /c "taskkill /F /PID $id" 2>&1
      $killed += $id
    } catch {
      Write-Host "  failed PID $id : $_" -ForegroundColor Yellow
    }
  }
  return $killed
}
$ui = Get-ListenPids $UiPort
$ag = @()
if (-not $KeepAgent) { $ag = Get-ListenPids $AgentPort }
$ku = Stop-Pids $ui "UI:$UiPort"
$ka = Stop-Pids $ag "Agent:$AgentPort"
Start-Sleep -Milliseconds 800
$leftUi = Get-ListenPids $UiPort
$leftAg = Get-ListenPids $AgentPort
Write-Host ""
Write-Host "Stopped UI PIDs:    $($ku -join ', ')"
Write-Host "Stopped Agent PIDs: $($ka -join ', ')"
if ($leftUi.Count) { Write-Host "STILL LISTENING UI $UiPort : $($leftUi -join ', ') (may need admin Task Manager)" -ForegroundColor Red }
else { Write-Host "UI port $UiPort free" -ForegroundColor Green }
if (-not $KeepAgent) {
  if ($leftAg.Count) { Write-Host "STILL LISTENING Agent $AgentPort : $($leftAg -join ', ')" -ForegroundColor Yellow }
  else { Write-Host "Agent port $AgentPort free" -ForegroundColor Green }
}
Write-Host "Desktop Grok TUI was not targeted by name."
