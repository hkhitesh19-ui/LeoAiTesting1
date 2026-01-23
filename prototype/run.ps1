param(
  [Parameter(Mandatory=$true)]
  [string]$Module
)

$ErrorActionPreference = "Stop"

function Fail($msg) {
  Write-Host "FATAL: $msg" -ForegroundColor Red
  exit 1
}

# must be first statement: param() already is
$repo = Resolve-Path (Join-Path $PSScriptRoot "..") | Select-Object -ExpandProperty Path
Write-Host "RepoRoot: $repo"

Set-Location $repo

# ✅ enforce python module execution
$env:PYTHONPATH = $repo
Write-Host "PYTHONPATH=$env:PYTHONPATH"

# Load .env (in-process only)
$envFile = Join-Path $repo ".env"
if (!(Test-Path $envFile)) { Fail ".env missing at repo root: $envFile" }

Get-Content $envFile | ForEach-Object {
  $l = $_.Trim()
  if ($l -and -not $l.StartsWith("#")) {
    $p = $l.Split("=",2)
    if ($p.Length -eq 2) {
      $k = $p[0].Trim()
      $v = $p[1].Trim()
      if ($k) { Set-Item -Path ("Env:" + $k) -Value $v }
    }
  }
}
Write-Host "OK: .env loaded (keys hidden)"

# Python detection
$py = "py"
try {
  & $py -c "import sys; print(sys.executable)" | Out-Null
} catch {
  Fail "Python launcher 'py' not available. Install Python or fix PATH."
}
Write-Host "Python: $(& $py -c 'import sys; print(sys.executable)')"

# Import checks
Write-Host "Checking imports..."
& $py -c "import prototype; import importlib; importlib.import_module('$Module'); print('OK: imports good')"
if ($LASTEXITCODE -ne 0) { Fail "Import check failed. prototype package cannot be imported." }

# force module execution
Write-Host "RUN: py -m $Module"
& $py -m $Module
exit $LASTEXITCODE
