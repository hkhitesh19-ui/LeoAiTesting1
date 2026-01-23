# prototype/run_prototype_v4.ps1
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

# set this 0 for real strategy mode
$env:FORCE_ONE_TRADE = "0"
Write-Host "FORCE_ONE_TRADE=$env:FORCE_ONE_TRADE"

& $py -m prototype.main_v4
