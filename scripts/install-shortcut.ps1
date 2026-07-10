# Create Desktop + Start Menu shortcuts for Grok Remote. Optional taskbar pin tip.
param(
  [switch]$Desktop = $true,
  [switch]$StartMenu = $true,
  [switch]$OpenFolder
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pluginRoot = if ($env:GROK_PLUGIN_ROOT) { $env:GROK_PLUGIN_ROOT } else { Split-Path -Parent $here }
$launch = Join-Path $pluginRoot "scripts\launch-remote.cmd"
if (-not (Test-Path $launch)) { $launch = Join-Path $here "launch-remote.cmd" }
if (-not (Test-Path $launch)) { throw "launch-remote.cmd missing" }
$stop = Join-Path $pluginRoot "scripts\stop-remote.ps1"
if (-not (Test-Path $stop)) { $stop = Join-Path $here "stop-remote.ps1" }
$w = New-Object -ComObject WScript.Shell
function New-Lnk([string]$path, [string]$target, [string]$args, [string]$work, [string]$desc) {
  $s = $w.CreateShortcut($path)
  $s.TargetPath = $target
  if ($args) { $s.Arguments = $args }
  $s.WorkingDirectory = $work
  $s.WindowStyle = 7
  $s.Description = $desc
  $s.IconLocation = "$env:SystemRoot\System32\shell32.dll,13"
  $s.Save()
  Write-Host "Created $path"
}
$desk = [Environment]::GetFolderPath("Desktop")
$startDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Grok Remote"
if ($StartMenu) { New-Item -ItemType Directory -Force -Path $startDir | Out-Null }
if ($Desktop) {
  New-Lnk (Join-Path $desk "Grok Remote.lnk") $launch "" $pluginRoot "Start Grok Remote UI + open browser"
  if (Test-Path $stop) {
    New-Lnk (Join-Path $desk "Grok Remote Stop.lnk") "powershell.exe" "-NoProfile -ExecutionPolicy Bypass -File `"$stop`"" $pluginRoot "Stop Grok Remote only"
  }
}
if ($StartMenu) {
  New-Lnk (Join-Path $startDir "Grok Remote.lnk") $launch "" $pluginRoot "Start Grok Remote UI + open browser"
  if (Test-Path $stop) {
    New-Lnk (Join-Path $startDir "Stop Grok Remote.lnk") "powershell.exe" "-NoProfile -ExecutionPolicy Bypass -File `"$stop`"" $pluginRoot "Stop Grok Remote only"
  }
}
Write-Host ""
Write-Host "Pin to taskbar / Start:" -ForegroundColor Cyan
Write-Host "  1. Open Start Menu -> Grok Remote"
Write-Host "  2. Right-click 'Grok Remote' -> Pin to Start"
Write-Host "  3. Or right-click the Desktop shortcut -> Show more options -> Pin to taskbar"
Write-Host "  4. From any Grok Build chat: /remote   or   /remote start"
Write-Host "  5. Stop: UI header 'Stop Remote' button, or /remote stop, or Desktop 'Grok Remote Stop'"
if ($OpenFolder) { Start-Process explorer.exe $startDir }
