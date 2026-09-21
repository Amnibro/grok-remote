param([switch]$Stop,[switch]$Status)
$ErrorActionPreference = "Continue"
$root = if ($env:GROK_PLUGIN_ROOT) { $env:GROK_PLUGIN_ROOT } else { Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path) }
$wd = Join-Path $root "scripts\hub-watchdog.ps1"
$py = (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
if (-not $py) { $py = "C:\Users\antho\AppData\Local\Programs\Python\Python312\python.exe" }
$tag = "hub-watch" + "dog.ps1"
function Running {
  $me = $PID
  @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.ProcessId -ne $me -and $_.CommandLine -like ("*" + $tag + "*") })
}
function Which($p) { if ($p.CommandLine -like "*motion*") { "motion" } else { "hub" } }
if ($Status) { Running | ForEach-Object { "{0}  pid={1}" -f (Which $_), $_.ProcessId }; if (-not (Running).Count) { "none running" }; return }
if ($Stop) { Running | ForEach-Object { "stopping {0} pid={1}" -f (Which $_), $_.ProcessId; Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; return }
$have = @{}
Running | ForEach-Object { $have[(Which $_)] = $_.ProcessId }
if ($have.ContainsKey("hub")) { "hub watchdog already running pid=" + $have["hub"] }
else {
  Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",$wd,"-Name","hub","-Port","2421","-HealthPath","/health") | Out-Null
  "started hub watchdog"
}
if ($have.ContainsKey("motion")) { "motion watchdog already running pid=" + $have["motion"] }
else {
  Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File",$wd,"-Name","motion","-Port","2423","-HealthPath","/motion/state","-FailsBeforeKill","2","-RespawnExe",$py,"-RespawnArgs",(Join-Path $root "motion_service.py")) | Out-Null
  "started motion watchdog"
}
Start-Sleep -Seconds 2
Running | ForEach-Object { "  now: {0} pid={1}" -f (Which $_), $_.ProcessId }
