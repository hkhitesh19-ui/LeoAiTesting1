# ============================
# apply_patch.ps1
# TypeF: Institutional Recovery Patch
# - Adds /admin/restart_bot and /admin/restart_service
# - Adds ADMIN_TOKEN auth helper
# - Improves bot.stop_bot() to join thread
# - Creates backups
# - Git commit + push (optional)
# ============================

param(
    [string]$ProjectRoot = ".",
    [string]$BackendUrl = "https://leoaitesting1.onrender.com",
    [switch]$GitPush,
    [switch]$RunTests
)

$ErrorActionPreference = "Stop"

function Info($m){ Write-Host "[INFO] $m" }
function Ok($m){ Write-Host "[OK]   $m" }
function Warn($m){ Write-Host "[WARN] $m" }
function Fail($m){ Write-Host "[FAIL] $m" }

function Assert-File($path) {
    if (-not (Test-Path $path)) { throw "Missing file: $path" }
}

function Backup-File($filePath, $backupDir) {
    $name = Split-Path $filePath -Leaf
    Copy-Item $filePath (Join-Path $backupDir "$name.bak") -Force
}

function Ensure-LineEndingLF([string]$text) {
    return $text -replace "`r`n", "`n"
}

# ----------------------------
# Start
# ----------------------------
Set-Location $ProjectRoot
Info "Root: $(Get-Location)"

$apiPath = Join-Path $ProjectRoot "api_server.py"
$botPath = Join-Path $ProjectRoot "bot.py"
Assert-File $apiPath
Assert-File $botPath

# Backup
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = Join-Path $ProjectRoot "_patch_backup\$stamp"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
Backup-File $apiPath $backupDir
Backup-File $botPath $backupDir
Ok "Backup created: $backupDir"

# ----------------------------
# Patch bot.py
# ----------------------------
Info "Patching bot.py..."
$bot = Get-Content $botPath -Raw
$bot = Ensure-LineEndingLF $bot

if ($bot -match "def stop_bot\(" -and $bot -notmatch "join\(timeout=8\)") {
    # Replace stop_bot() function block (simple safe approach)
    $pattern = "def stop_bot\(\):[\s\S]*?(?=\n\w|\Z)"
    $replacement = @'
def stop_bot():
    global _stop_flag, _bot_thread
    _stop_flag = True
    print("⚠️ Bot stop requested")

    try:
        if _bot_thread and _bot_thread.is_alive():
            _bot_thread.join(timeout=8)
            print("✅ Bot thread stopped")
    except Exception:
        pass

'@

    $newBot = [regex]::Replace($bot, $pattern, $replacement, 1)
    if ($newBot -eq $bot) {
        Warn "Could not safely replace stop_bot(); leaving unchanged."
    } else {
        Set-Content -Path $botPath -Value $newBot -Encoding UTF8
        Ok "bot.py stop_bot() patched"
    }
} else {
    Ok "bot.py already patched (or stop_bot not found)"
}

# ----------------------------
# Patch api_server.py
# ----------------------------
Info "Patching api_server.py..."
$api = Get-Content $apiPath -Raw
$api = Ensure-LineEndingLF $api

# Ensure Header import
if ($api -match "from fastapi import FastAPI, Query, HTTPException" -and $api -notmatch "Header") {
    $api = $api -replace "from fastapi import FastAPI, Query, HTTPException",
                         "from fastapi import FastAPI, Query, HTTPException, Header"
    Ok "Added Header import"
}

# Ensure time import
if ($api -match "`nimport os" -and $api -notmatch "`nimport time") {
    $api = $api -replace "`nimport os", "`nimport os`nimport time"
    Ok "Added import time"
}

# Ensure ADMIN_TOKEN + helper
if ($api -notmatch "ADMIN_TOKEN\s*=\s*os\.getenv\(""ADMIN_TOKEN""") {
    $helperBlock = @'

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

def require_admin_token(x_admin_token: str | None):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN not set on server")
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

'@

    if ($api -match 'BUILD_TIME = os\.getenv\("BUILD_TIME", "N/A"\)') {
        $api = $api -replace '(BUILD_TIME = os\.getenv\("BUILD_TIME", "N/A"\))', "`$1$helperBlock"
        Ok "Added ADMIN_TOKEN helper after BUILD_TIME"
    } else {
        # fallback: add near top after app creation
        $api = $api -replace "(app\s*=\s*FastAPI\([^\)]*\)\s*)", "`$1$helperBlock"
        Ok "Added ADMIN_TOKEN helper after FastAPI()"
    }
} else {
    Ok "ADMIN_TOKEN helper already exists"
}

# Add restart endpoints (insert before if __name__ main)
if ($api -notmatch "/admin/restart_bot") {
    $routesBlock = @'

@app.post("/admin/restart_bot", tags=["admin"])
def admin_restart_bot(x_admin_token: str | None = Header(default=None, alias="X-ADMIN-TOKEN")):
    require_admin_token(x_admin_token)

    if "bot" not in globals():
        raise HTTPException(status_code=500, detail="bot module not loaded")

    try:
        # Stop existing bot loop
        if hasattr(bot, "stop_bot"):
            bot.stop_bot()
            time.sleep(2)

        # Start fresh bot thread
        if hasattr(bot, "start_bot_thread"):
            bot.start_bot_thread()
        else:
            raise HTTPException(status_code=500, detail="bot.start_bot_thread missing")

        return {"ok": True, "message": "Bot restart triggered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restart bot failed: {e}")


@app.post("/admin/restart_service", tags=["admin"])
def admin_restart_service(x_admin_token: str | None = Header(default=None, alias="X-ADMIN-TOKEN")):
    require_admin_token(x_admin_token)

    # Hard restart process; Render will relaunch container
    os._exit(1)

'@

    if ($api -match "if __name__ == ""__main__"":") {
        $api = $api -replace "if __name__ == ""__main__"":", ($routesBlock + "`nif __name__ == ""__main__"":")
        Ok "Added admin restart endpoints"
    } else {
        # append to end
        $api = $api + "`n" + $routesBlock
        Ok "Appended admin restart endpoints at EOF"
    }
} else {
    Ok "Restart endpoints already exist"
}

Set-Content -Path $apiPath -Value $api -Encoding UTF8
Ok "api_server.py patched"

# ----------------------------
# Git commit + push (optional)
# ----------------------------
if ($GitPush) {
    Info "Git commit/push enabled..."
    try {
        git status | Out-Host
        git add api_server.py bot.py | Out-Host
        git commit -m "Add admin restart endpoints + bot stop join (auto patch)" | Out-Host
        git push | Out-Host
        Ok "Git push completed (Render will redeploy if auto-deploy enabled)"
    } catch {
        Warn "Git step failed: $($_.Exception.Message)"
    }
} else {
    Info "Git push skipped. Run with -GitPush to auto commit/push."
}

# ----------------------------
# Tests (optional)
# ----------------------------
if ($RunTests) {
    Info "Running endpoint tests (requires ADMIN_TOKEN env var)..."
    $adminToken = $env:ADMIN_TOKEN
    if (-not $adminToken) {
        Warn "ADMIN_TOKEN env var not set locally. Skipping tests."
    } else {
        try {
            Info "Calling restart_bot..."
            Invoke-WebRequest `
                -Uri "$BackendUrl/admin/restart_bot" `
                -Method POST `
                -Headers @{ "X-ADMIN-TOKEN" = $adminToken } `
                -TimeoutSec 20 | Out-Null
            Ok "restart_bot called"
        } catch {
            Warn "restart_bot call failed: $($_.Exception.Message)"
        }

        try {
            Info "Fetching get_status..."
            $st = Invoke-RestMethod "$BackendUrl/get_status" -TimeoutSec 20
            $st | ConvertTo-Json -Depth 10 | Out-Host
            Ok "get_status OK"
        } catch {
            Warn "get_status failed: $($_.Exception.Message)"
        }
    }
} else {
    Info "Tests skipped. Run with -RunTests to test endpoints."
}

Ok "apply_patch.ps1 completed."
