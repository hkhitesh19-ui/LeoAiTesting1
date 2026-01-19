$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $(Resolve-Path "$PSScriptRoot")
Set-Location $root

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$bk = Join-Path $root "_backups"
New-Item -ItemType Directory -Force -Path $bk | Out-Null

$files = @(
  "docs\index.html",
  "api_server.py",
  "bot.py",
  "requirements.txt",
  ".env.example"
)

foreach($f in $files){
  if(Test-Path $f){
    Copy-Item $f (Join-Path $bk ("$($f -replace '[\\\/:]','_').BACKUP_$ts")) -Force
  }
}

Write-Host "✅ Backup done -> _backups\ (timestamp=$ts)"
