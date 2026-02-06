param(
  [string]$Tag = "prototype-v7"
)

Write-Host "=== RELEASE GUARD ==="

git status --porcelain | Out-String | % { $s = $_.Trim(); if ($s) { 
  Write-Host "❌ Working tree dirty. Commit/stash first."
  exit 1
}}

Write-Host "✅ Git clean"

Write-Host "Running smoke test..."
py -m prototype.smoke_test_v1
if ($LASTEXITCODE -ne 0) {
  Write-Host "❌ Smoke test failed."
  exit 1
}

Write-Host "✅ Smoke test passed"

git tag -a $Tag -m "Release $Tag"
git show $Tag --quiet

Write-Host "✅ Tagged: $Tag"