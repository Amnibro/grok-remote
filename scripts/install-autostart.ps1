# Enable Grok-Remote autostart (Grok SessionStart + optional Windows logon)
param(
  [switch]$Boot,
  [switch]$NoSession,
  [string]$Cwd = "",
  [switch]$Disable
)
$ErrorActionPreference = "Stop"
$pluginRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if ($env:GROK_PLUGIN_ROOT) { $pluginRoot = $env:GROK_PLUGIN_ROOT }
. (Join-Path $pluginRoot "scripts\config-path.ps1")
$cfg = Get-GrokRemoteConfig
if ($Disable) {
  $cfg.autostart = $false
  $cfg.autostart_on_boot = $false
  $path = Save-GrokRemoteConfig $cfg
  # remove scheduled task if present
  schtasks /Delete /TN "GrokRemoteAutostart" /F 2>$null | Out-Null
  # remove global hook mirror if we installed one
  $gh = Join-Path $env:USERPROFILE ".grok\hooks\grok-remote-autostart.json"
  if (Test-Path $gh) { Remove-Item $gh -Force }
  Write-Host "Autostart DISABLED. Config: $path"
  exit 0
}
$cfg.autostart = $true
$cfg.autostart_on_session = -not $NoSession
$cfg.autostart_on_boot = [bool]$Boot
if ($Cwd) { $cfg.cwd = $Cwd }
elseif (-not $cfg.cwd) { $cfg.cwd = (Get-Location).Path }
$path = Save-GrokRemoteConfig $cfg
Write-Host "Autostart ENABLED"
Write-Host "  config:  $path"
Write-Host "  session: $($cfg.autostart_on_session)  (Grok SessionStart hook)"
Write-Host "  boot:    $($cfg.autostart_on_boot)  (Windows logon task)"
Write-Host "  cwd:     $($cfg.cwd)"
# Global hook so it runs even if plugin hook discovery is flaky
$hooksDir = Join-Path $env:USERPROFILE ".grok\hooks"
New-Item -ItemType Directory -Force -Path $hooksDir | Out-Null
$cmd = Join-Path $pluginRoot "scripts\hook-session-start.cmd"
$hookJson = @{
  hooks = @{
    SessionStart = @(
      @{
        hooks = @(
          @{ type = "command"; command = "`"$cmd`""; timeout = 15 }
        )
      }
    )
  }
} | ConvertTo-Json -Depth 8
Set-Content -Path (Join-Path $hooksDir "grok-remote-autostart.json") -Value $hookJson -Encoding UTF8
Write-Host "  hook:    ~/.grok/hooks/grok-remote-autostart.json"
if ($Boot) {
  $ensure = Join-Path $pluginRoot "scripts\ensure-running.ps1"
  $tr = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ensure`" -Reason boot"
  schtasks /Create /TN "GrokRemoteAutostart" /TR $tr /SC ONLOGON /RL LIMITED /F | Out-Null
  Write-Host "  task:    GrokRemoteAutostart (ONLOGON)"
}
Write-Host ""
Write-Host "Restart Grok (or open a new session) to pick up the SessionStart hook."
Write-Host "Disable later:  .\scripts\install-autostart.ps1 -Disable"
