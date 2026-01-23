$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot"

# Always backup before deploy
powershell -ExecutionPolicy Bypass -File .\protect_backup.ps1

# Ensure correct branch
git checkout gh-pages-ui | Out-Null

# Deploy using your script (if exists)
if(Test-Path .\deploy_ui.ps1){
  powershell -ExecutionPolicy Bypass -File .\deploy_ui.ps1
}else{
  Write-Host "⚠️ deploy_ui.ps1 not found. Doing direct commit/push of docs/index.html"
}

# If docs/index.html changed (direct edits), commit/push it too
git add .\docs\index.html 2>

$status = git status --porcelain
if($status){
  git commit -m "UI deploy (safe wrapper)" | Out-Null
  git push origin gh-pages-ui
  Write-Host "✅ Pushed updated UI"
}else{
  Write-Host "ℹ️ No changes detected."
}
