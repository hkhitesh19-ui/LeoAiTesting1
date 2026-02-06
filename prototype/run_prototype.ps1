# prototype/run_prototype.ps1
$ErrorActionPreference = "Stop"

# Always run from repo root
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "RepoRoot: $repoRoot"
Write-Host "Python:" (py -c "import sys; print(sys.executable)")

# ---- Load .env into current session (DO NOT print secrets)
$envFile = Join-Path $repoRoot ".env"
if (-not (Test-Path $envFile)) {
  throw "Missing .env file at repo root: $envFile"
}

Get-Content $envFile | ForEach-Object {
  $line = $_.Trim()
  if ($line.Length -eq 0) { return }
  if ($line.StartsWith("#")) { return }

  $parts = $line.Split("=", 2)
  if ($parts.Length -ne 2) { return }

  $k = $parts[0].Trim()
  $v = $parts[1].Trim()

  if (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'"))) {
    $v = $v.Substring(1, $v.Length-2)
  }

  if ($k) {
    Set-Item -Path ("Env:" + $k) -Value $v
  }
}

# sanity check (keys exist; do NOT reveal values)
$required = @("SHOONYA_USERID","SHOONYA_PASSWORD","SHOONYA_VENDOR_CODE","SHOONYA_API_SECRET","SHOONYA_IMEI","TOTP_SECRET")
foreach ($r in $required) {
  if (-not (Test-Path ("Env:" + $r))) {
    throw "Env missing after .env load: $r"
  }
}
Write-Host "OK: .env loaded (keys present)"

# Ensure outputs folder exists
New-Item -ItemType Directory -Path ".\prototype\outputs" -Force | Out-Null

# Run module for correct imports
py -m prototype.main
