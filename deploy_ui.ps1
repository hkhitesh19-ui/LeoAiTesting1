cd "C:\Users\Dell\Downloads\TypeF_GitHub_Ready\TypeF_GitHub_Ready"
git checkout gh-pages-ui

Copy-Item "F:\LeoAi_Testing_Cursor\deploy\index.html" ".\docs\index.html" -Force

git add docs/index.html

$diff = git diff --cached --name-only
if (-not $diff) {
  Write-Host "ℹ️ No UI changes to deploy."
  exit 0
}

$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
git commit -m "UI update $ts"
git push

Write-Host "✅ UI deployed to GitHub Pages"
