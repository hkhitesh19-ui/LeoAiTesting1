# prototype/run_prototype_v3.ps1
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Write-Host "RepoRoot: $RepoRoot"
$py = (Get-Command py).Source
Write-Host "Python: $py"

# load .env
$envFile = Join-Path $RepoRoot ".env"
Get-Content $envFile | ForEach-Object {
  $l=$_.Trim()
  if($l -and -not $l.StartsWith('#') -and $l.Contains('=')){
    $p=$l.Split('=',2)
    $k=$p[0].Trim()
    $v=$p[1].Trim()
    Set-Item -Path ("Env:" + $k) -Value $v
  }
}

# Force one trade for validation
$env:FORCE_ONE_TRADE = "1"
Write-Host "FORCE_ONE_TRADE=1"

& $py -m prototype.main_v3
