# ============================
# TypeF Production Guard v4
# ============================
# FULL REWRITE (stable, minimal, institutional)
#
# Features:
# - Backup critical files
# - Checks: /health /version /get_status
# - Level-1: restart bot thread
# - Level-2: restart service
# - SAFE stale detection:
#     * Uses backend server_time if parseable
#     * Otherwise falls back to /version server_time
#     * If still unknown -> does NOT false-trigger recovery
#
# Run daily:
# powershell -ExecutionPolicy Bypass -File .\production_guard.ps1
#
# Token:
# setx TYPEF_ADMIN_TOKEN "TypeF_Admin_2026_..."
# ============================

$ErrorActionPreference = "Stop"

# ===== CONFIG =====
$API_BASE = "https://leoaitesting1.onrender.com"
$UI_URL   = "https://hkhitesh19-ui.github.io/LeoAiTesting1/"

$RECOVERY_ENABLED = $true
$DRY_RUN          = $false

$STALE_SECONDS    = 600   # 10 min (safer default)
$L1_RETRIES       = 2
$L1_SLEEP_SECONDS = 30

$ADMIN_TOKEN = $env:TYPEF_ADMIN_TOKEN

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKUP_DIR = Join-Path $ROOT "_guard_backups"

# ===== LOG =====
function TS(){ return (Get-Date -Format "yyyy-MM-dd HH:mm:ss") }
function Info($m){ Write-Host "[INFO] $(TS) $m" }
function Ok($m){   Write-Host "[OK]   $(TS) $m" }
function Warn($m){ Write-Host "[WARN] $(TS) $m" }
function Fail($m){ Write-Host "[FAIL] $(TS) $m" }

# ===== UTILS =====
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

# ===== HTTP =====
function TryGet($url){
  try{
    $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 25
    return @{ ok=$true; code=$r.StatusCode; content=$r.Content }
  }catch{
    try{ $code = $_.Exception.Response.StatusCode.value__ } catch { $code = 0 }
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

# TIME SAFE:
# - do NOT assume UTC (backend may send naive time)
# - parse as local time, since backend string seems naive
function ToDateSafeLocal($s){
  try { return [datetime]::Parse($s) } catch { return $null }
}

function GetStatusJson(){
  $r = TryGet "$API_BASE/get_status"
  if($r.code -ne 200){ return $null }
  return (ParseJsonSafe $r.content)
}

function GetVersionJson(){
  $r = TryGet "$API_BASE/version"
  if($r.code -ne 200){ return $null }
  return (ParseJsonSafe $r.content)
}

# ===== RECOVERY =====
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

  if($res.code -eq 200){
    Ok "Level-2: restart_service triggered (200)"
    return $true
  }

  Warn "Level-2: restart_service returned HTTP=$($res.code) (service may still restart)"
  return $true
}

# ===== MAIN =====
Info "Running production_guard.ps1 (v4)"
Info "Root: $ROOT"
Info "DRY_RUN = $DRY_RUN"
Info "API_BASE: $API_BASE"
Info "UI_URL: $UI_URL"

BackupFiles

Info "Checking API endpoints..."
$health = TryGet "$API_BASE/health"
if($health.code -eq 200){ Ok "API /health OK" } else { Warn "API /health FAIL HTTP=$($health.code)" }

$ver = GetVersionJson
if($ver){
  Ok "API /version OK (commit=$($ver.render_git_commit) build_time=$($ver.build_time))"
}else{
  Warn "API /version FAIL"
}

$st = GetStatusJson
if($st){
  Ok "API /get_status OK"
}else{
  Warn "API /get_status FAIL"
}

if($RECOVERY_ENABLED -and (-not $DRY_RUN)){
  if($null -eq $st){
    Warn "Status JSON unavailable -> Level-1 recovery"
    $ok = RestartBot
    if(-not $ok){
      Warn "Level-1 failed -> Level-2 restart"
      RestartService | Out-Null
    }
  }else{
    $botConn   = $st.bot_connected
    $botStatus = $st.botStatus.status
    $botMsg    = $st.botStatus.message

    $now = Get-Date
    $stTime = ToDateSafeLocal $st.server_time

    $age = $null
    if($stTime){
      $age = (New-TimeSpan -Start $stTime -End $now).TotalSeconds
    }

    # SAFE stale evaluation:
    # only mark stale if we could calculate age
    $isStale = $false
    if($age -ne $null){
      if($age -gt $STALE_SECONDS){ $isStale = $true }
    }

    $needsRecovery = $false

    # strict triggers
    if($botConn -ne $true){ $needsRecovery = $true }
    if("$botStatus" -match "Error|Disconnected"){ $needsRecovery = $true }

    # stale is a weak trigger: stale only matters if bot not OK also
    if($isStale -and ($botConn -ne $true)){ $needsRecovery = $true }

    if($needsRecovery){
      Warn "Recovery trigger: bot_connected=$botConn botStatus=$botStatus stale=$isStale age=$age msg=$botMsg"

      $recovered = $false
      for($i=1; $i -le $L1_RETRIES; $i++){
        Info "Level-1 attempt $i/$L1_RETRIES"
        if(RestartBot){
          Start-Sleep -Seconds 5
          $st2 = GetStatusJson
          if($st2 -and $st2.bot_connected -eq $true){
            Ok "Recovery success after Level-1"
            $recovered = $true
            break
          }
        }
        Start-Sleep -Seconds $L1_SLEEP_SECONDS
      }

      if(-not $recovered){
        Warn "Level-1 did not recover -> Level-2 service restart"
        RestartService | Out-Null
      }
    }else{
      Ok "No recovery needed: bot healthy (age=$age stale=$isStale)"
    }
  }
}else{
  Warn "RECOVERY disabled or DRY_RUN true -> no restart actions"
}

Ok "Guard run complete."
