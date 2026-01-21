# ============================
# TypeF Production Guard v2
# ============================
# Purpose:
# - Institutional safety checks
# - Detect stale backend/bot issues
# - Level-1 Recovery: restart bot thread
# - Level-2 Recovery: restart backend service
# - Backup + lightweight git hygiene (optional)
#
# Run:
# powershell -ExecutionPolicy Bypass -File .\production_guard.ps1
#
# Security:
# - Token must be in ENV: TYPEF_ADMIN_TOKEN
#   setx TYPEF_ADMIN_TOKEN "..."
#
# ============================

$ErrorActionPreference = "Stop"

# ====== CONFIG ======
$API_BASE = "https://leoaitesting1.onrender.com"
$UI_URL   = "https://hkhitesh19-ui.github.io/LeoAiTesting1/"

# Recovery behavior
$RECOVERY_ENABLED = $true
$DRY_RUN          = $false

# stale threshold (server_time age)
$STALE_SECONDS    = 300  # 5 minutes

# Level-1 attempts
$L1_RETRIES       = 2
$L1_SLEEP_SECONDS = 30

# Token (ENV preferred)
$ADMIN_TOKEN = $env:TYPEF_ADMIN_TOKEN

# local repo paths
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKUP_DIR = Join-Path $ROOT "_guard_backups"

# ====== LOG HELPERS ======
function TS(){ return (Get-Date -Format "yyyy-MM-dd HH:mm:ss") }
function Info($m){ Write-Host "[INFO] $(TS) $m" }
function Ok($m){ Write-Host "[OK]   $(TS) $m" }
function Warn($m){ Write-Host "[WARN] $(TS) $m" }
function Fail($m){ Write-Host "[FAIL] $(TS) $m" }

# ====== HTTP HELPERS ======
function TryGet($url){
  try{
    $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 20
    return @{ ok=$true; code=$r.StatusCode; content=$r.Content }
  }catch{
    try{
      $code = $_.Exception.Response.StatusCode.value__
    }catch{ $code = 0 }
    return @{ ok=$false; code=$code; content=$null }
  }
}

function TryPost($url, $headers){
  try{
    $r = Invoke-WebRequest -Method Post -Uri $url -Headers $headers -UseBasicParsing -TimeoutSec 40
    return @{ ok=$true; code=$r.StatusCode; content=$r.Content }
  }catch{
    $body = $null
    try{
      $code = $_.Exception.Response.StatusCode.value__
      $sr = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
      $body = $sr.ReadToEnd()
    }catch{
      $code = 0
    }
    return @{ ok=$false; code=$code; content=$body }
  }
}

function ParseJsonSafe($text){
  try { return ($text | ConvertFrom-Json) } catch { return $null }
}

function ToDateTimeSafe($s){
  try { return [datetime]::Parse($s) } catch { return $null }
}

# ====== RECOVERY CALLS ======
function RestartBot(){
  if(-not $ADMIN_TOKEN){
    Warn "ENV TYPEF_ADMIN_TOKEN not set. Can't call restart endpoints."
    return $false
  }
  $h = @{ "X-ADMIN-TOKEN" = $ADMIN_TOKEN }
  $res = TryPost "$API_BASE/admin/restart_bot" $h
  if($res.code -eq 200){
    Ok "Level-1: restart_bot triggered (200)"
    return $true
  }
  Warn "Level-1: restart_bot failed HTTP=$($res.code) body=$($res.content)"
  return $false
}

function RestartService(){
  if(-not $ADMIN_TOKEN){
    Warn "ENV TYPEF_ADMIN_TOKEN not set. Can't call restart endpoints."
    return $false
  }
  $h = @{ "X-ADMIN-TOKEN" = $ADMIN_TOKEN }
  $res = TryPost "$API_BASE/admin/restart_service" $h

  # service may exit immediately, so request can fail by connection close
  if($res.code -eq 200){
    Ok "Level-2: restart_service triggered (200)"
    return $true
  }
  Warn "Level-2: restart_service returned HTTP=$($res.code) (service may still restart)"
  return $true
}

# ====== BACKUP ======
function EnsureDir($p){
  if(-not (Test-Path $p)){ New-Item -ItemType Directory -Path $p | Out-Null }
}

function BackupFiles(){
  EnsureDir $BACKUP_DIR
  $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
  $dest = Join-Path $BACKUP_DIR $stamp
  EnsureDir $dest

  $files = @("api_server.py","bot.py","requirements.txt","production_guard.ps1")
  foreach($f in $files){
    $src = Join-Path $ROOT $f
    if(Test-Path $src){
      Copy-Item $src (Join-Path $dest $f) -Force
    }
  }
  Ok "Backup created: $dest"
}

# ====== MAIN ======
Info "Running production_guard.ps1 (v2)"
Info "Root: $ROOT"
Info "DRY_RUN = $DRY_RUN"
Info "API_BASE: $API_BASE"
Info "UI_URL: $UI_URL"

BackupFiles

# ---- health check
Info "Checking API endpoints..."
$health = TryGet "$API_BASE/health"
if($health.code -eq 200){ Ok "API /health OK" } else { Warn "API /health FAIL HTTP=$($health.code)" }

$ver = TryGet "$API_BASE/version"
if($ver.code -eq 200){
  $vj = ParseJsonSafe $ver.content
  if($vj){
    Ok "API /version OK (commit=$($vj.render_git_commit) build_time=$($vj.build_time))"
  }else{
    Ok "API /version OK"
  }
}else{
  Warn "API /version FAIL HTTP=$($ver.code)"
}

$statusRes = TryGet "$API_BASE/get_status"
if($statusRes.code -eq 200){
  Ok "API /get_status OK"
}else{
  Warn "API /get_status FAIL HTTP=$($statusRes.code)"
}

# ---- recovery decision
if($RECOVERY_ENABLED -and (-not $DRY_RUN)){
  $st = $null
  if($statusRes.code -eq 200){ $st = ParseJsonSafe $statusRes.content }

  if($null -eq $st){
    Warn "Status JSON unavailable -> Level-1 recovery attempt"
    $ok = RestartBot
    if(-not $ok){
      Warn "Level-1 failed -> Level-2 service restart"
      RestartService | Out-Null
    }
  }else{
    $serverTime = ToDateTimeSafe $st.server_time
    $botConn    = $st.bot_connected
    $botStatus  = $st.botStatus.status
    $botMsg     = $st.botStatus.message

    $isStale = $false
    if($serverTime){
      $age = (New-TimeSpan -Start $serverTime -End (Get-Date)).TotalSeconds
      if($age -gt $STALE_SECONDS){ $isStale = $true }
    }else{
      Warn "server_time parse failed -> treat as stale"
      $isStale = $true
    }

    $needsRecovery = $false
    if($botConn -ne $true){ $needsRecovery = $true }
    if($isStale){ $needsRecovery = $true }
    if("$botStatus" -match "Error|Disconnected"){ $needsRecovery = $true }

    if($needsRecovery){
      Warn "Recovery trigger: bot_connected=$botConn botStatus=$botStatus stale=$isStale msg=$botMsg"

      $recovered = $false
      for($i=1; $i -le $L1_RETRIES; $i++){
        Info "Level-1 attempt $i/$L1_RETRIES"
        if(RestartBot){
          Start-Sleep -Seconds 5
          $st2Res = TryGet "$API_BASE/get_status"
          if($st2Res.code -eq 200){
            $st2 = ParseJsonSafe $st2Res.content
            if($st2 -and $st2.bot_connected -eq $true){
              Ok "Recovery success after Level-1"
              $recovered = $true
              break
            }
          }
        }
        Start-Sleep -Seconds $L1_SLEEP_SECONDS
      }

      if(-not $recovered){
        Warn "Level-1 did not recover -> Level-2 service restart"
        RestartService | Out-Null
      }
    }else{
      Ok "No recovery needed: bot healthy"
    }
  }
}else{
  Warn "RECOVERY disabled or DRY_RUN true -> no restart actions"
}

Ok "Guard run complete."
