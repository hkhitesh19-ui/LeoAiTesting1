# prototype/run_prototype_v2.ps1
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Write-Host "RepoRoot: $RepoRoot"

$py = (Get-Command py).Source
Write-Host "Python: $py"

# load .env into current PS session
$envFile = Join-Path $RepoRoot ".env"
if (!(Test-Path $envFile)) { throw ".env not found: $envFile" }

Get-Content $envFile | ForEach-Object {
  $l=$_.Trim()
  if($l -and -not $l.StartsWith('#') -and $l.Contains('=')){
    $p=$l.Split('=',2)
    $k=$p[0].Trim()
    $v=$p[1].Trim()
    Set-Item -Path ("Env:" + $k) -Value $v
  }
}

Write-Host "OK: .env loaded (keys present)"

& $py -m prototype.main_v2
