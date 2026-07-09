# Shared config location (user data, not the plugin tree)
function Get-GrokRemoteConfigPath {
  if ($env:GROK_PLUGIN_DATA) {
    $dir = $env:GROK_PLUGIN_DATA
  } else {
    $dir = Join-Path $env:USERPROFILE ".grok\plugin-data\grok-remote"
  }
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  return (Join-Path $dir "config.json")
}
function Get-GrokRemoteConfig {
  $path = Get-GrokRemoteConfigPath
  $defPath = $null
  if ($env:GROK_PLUGIN_ROOT) {
    $defPath = Join-Path $env:GROK_PLUGIN_ROOT "config.default.json"
  }
  $cfg = @{
    autostart = $false
    autostart_on_session = $true
    autostart_on_boot = $false
    cwd = ""
    ui_port = 2421
    agent_port = 2419
    always_approve = $true
    leader = $true
  }
  if ($defPath -and (Test-Path $defPath)) {
    try {
      $d = Get-Content $defPath -Raw | ConvertFrom-Json
      foreach ($p in $d.PSObject.Properties) { $cfg[$p.Name] = $p.Value }
    } catch {}
  }
  if (Test-Path $path) {
    try {
      $u = Get-Content $path -Raw | ConvertFrom-Json
      foreach ($p in $u.PSObject.Properties) { $cfg[$p.Name] = $p.Value }
    } catch {}
  }
  return [pscustomobject]$cfg
}
function Save-GrokRemoteConfig($cfg) {
  $path = Get-GrokRemoteConfigPath
  ($cfg | ConvertTo-Json -Depth 6) | Set-Content -Path $path -Encoding UTF8
  return $path
}
