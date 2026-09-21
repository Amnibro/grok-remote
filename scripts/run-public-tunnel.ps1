# Cloudflare ingress for Grok Remote, same idea as amni-chat/scripts/run_tunnel.ps1
# Named token/config if present; otherwise a trycloudflare quick tunnel to :2421.
$ErrorActionPreference = "Stop"
$uiPort = 2421
if ($env:GROK_REMOTE_UI_PORT) { $uiPort = [int]$env:GROK_REMOTE_UI_PORT }
$hostName = $env:GROK_REMOTE_PUBLIC_URL
if ($hostName) { Write-Output "[grok-remote] public URL: $hostName" }
$cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cloudflared) {
  foreach ($c in @(
    "$env:ProgramFiles\cloudflared\cloudflared.exe",
    "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe"
  )) { if (Test-Path $c) { $cloudflared = @{ Source = $c }; break } }
}
if (-not $cloudflared) { throw "cloudflared not on PATH" }
$bin = $cloudflared.Source
$token = $env:GROK_REMOTE_TUNNEL_TOKEN
if (-not $token) {
  $svc = Get-CimInstance Win32_Service -Filter "Name='Cloudflared'" -ErrorAction SilentlyContinue
  if ($svc -and $svc.PathName -match '--token\s+([^\s"]+)') { $token = $Matches[1] }
}
if ($token -and $env:GROK_REMOTE_USE_NAMED_TUNNEL -eq "1") {
  Write-Output "[grok-remote] mode: named tunnel token (add a public hostname → http://127.0.0.1:$uiPort in Cloudflare Zero Trust)"
  & $bin tunnel run --token $token
  exit $LASTEXITCODE
}
Write-Output "[grok-remote] mode: quick tunnel → http://127.0.0.1:$uiPort"
& $bin tunnel --no-autoupdate --url "http://127.0.0.1:$uiPort"
exit $LASTEXITCODE
