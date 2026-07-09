# Install Grok-Remote into ~/.grok/plugins and enable it for /remote
$ErrorActionPreference = "Stop"
$src = Split-Path -Parent $MyInvocation.MyCommand.Path
$dstRoot = Join-Path $env:USERPROFILE ".grok\plugins"
$dst = Join-Path $dstRoot "grok-remote"
$grok = Join-Path $env:USERPROFILE ".grok\bin\grok.exe"
if (-not (Test-Path $grok)) {
  $g = Get-Command grok -ErrorAction SilentlyContinue
  if ($g) { $grok = $g.Source } else { throw "grok.exe not found" }
}
New-Item -ItemType Directory -Force -Path $dstRoot | Out-Null
Write-Host "Validating plugin at $src"
& $grok plugin validate $src
if ($LASTEXITCODE -ne 0) { Write-Host "validate returned $LASTEXITCODE (continuing if only warnings)" -ForegroundColor Yellow }
Write-Host "Installing (copy) -> $dst"
if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
Copy-Item -Recurse -Force $src $dst
# drop local runtime junk from install copy
@("logs","runtime-config.json","connect.url","__pycache__") | ForEach-Object {
  $p = Join-Path $dst $_
  if (Test-Path $p) { Remove-Item -Recurse -Force $p -ErrorAction SilentlyContinue }
}
Write-Host "CLI install --trust"
& $grok plugin install $dst --trust
Write-Host "Enable grok-remote"
& $grok plugin enable grok-remote 2>$null
& $grok plugin list
Write-Host ""
Write-Host "Done. Restart Grok TUI or press r in /plugins to reload." -ForegroundColor Green
Write-Host "Then run:  /remote" -ForegroundColor Cyan
