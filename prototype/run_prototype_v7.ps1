$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
Write-Host "RepoRoot: $repo"
Set-Location $repo

# Load .env into current PowerShell process
$envFile = Join-Path $repo ".env"
if (-not (Test-Path $envFile)) {
  throw ".env not found at $envFile"
}

Get-Content $envFile | ForEach-Object {
  $l = $_.Trim()
  if ($l -and -not $l.StartsWith("#")) {
    $p = $l.Split("=", 2)
    if ($p.Length -eq 2) {
      $k = $p[0].Trim()
      $v = $p[1].Trim()
      Set-Item -Path ("Env:" + $k) -Value $v
    }
  }
}

# Required env keys
$required = @(
  "SHOONYA_USERID",
  "SHOONYA_PASSWORD",
  "SHOONYA_VENDOR_CODE",
  "SHOONYA_API_SECRET",
  "SHOONYA_IMEI",
  "TOTP_SECRET"
)

foreach ($r in $required) {
  if (-not (Get-Item ("Env:" + $r) -ErrorAction SilentlyContinue)) {
    throw "Missing required env: $r"
  }
}

Write-Host "OK: .env loaded (keys present)"
Write-Host "Python: $((Get-Command py).Source)"

# Useful test flags
$env:FORCE_ONE_TRADE = "0"
$env:MAX_RUNTIME_SEC = "600"
$env:ENTRY_TIMEBOX_SEC = "120"
$env:INTRA_POLL_SEC = "2"

py .\prototype\main_v7.py
