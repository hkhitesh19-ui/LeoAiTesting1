# ============================
# TypeF Production Guard v5
# ============================
# FULL REWRITE (Institutional)
#
# Includes:
# 1) Backup critical files
# 2) Strict stale detection (UTC)
# 3) Level-1: restart bot
# 4) Level-2: restart service
# 5) Telegram alerts on recovery events
#
# Requires:
# setx TYPEF_ADMIN_TOKEN "TypeF_Admin_2026_...."
# setx TYPEF_TG_BOT_TOKEN "<telegram_bot_token>"
# setx TYPEF_TG_CHAT_ID "<chat_id>"
#
# Run:
# powershell -ExecutionPolicy Bypass -File .\production_guard.ps1
# ============================

$ErrorActionPreference = "Stop"

# ===== CONFIG =====
$API_BASE = "https://leoaitesting1.onrender.com"
$UI_URL   = "https://hkhitesh19-ui.github.io/LeoAiTesting1/"

$RECOVERY_ENABLED = $true
$DRY_RUN          = $false

$STALE_SECONDS    = 300   # 5 min strict
$L1_RETRIES       = 2
$L1_SLEEP_SECONDS = 30

$ADMIN_TOKEN  = $env:TYPEF_ADMIN_TOKEN
$TG_BOT_TOKEN = $env:TYPEF_TG_BOT_TOKEN
$TG_CHAT_ID   = $env:TYPEF_TG_CHAT_ID

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKUP_DIR = Join-Path $ROOT "_guard_backups"

# ===== LOG =====
function TS(){ return (Get-Date -Format "yyyy-MM-dd HH:mm:ss") }
function Info($m){ Write-Host "[INFO] $(TS) $m" }
function Ok($m){   Write-Host "[OK]   $(TS) $m" }
function Warn($m){ Write-Host "[WARN] $(TS) $m" }
function Fail($m){ Write-Host "[FAIL] $(TS) $m" }

# ===== TELEGRAM =====
function TgSend($text){
  if(-not $TG_BOT_TOKEN -or -not $TG_CHAT_ID){ return }
  try{
    $uri = "https://api.telegram.org/bot$TG_BOT_TOKEN/sendMessage"
    Invoke-RestMethod -Method Post -Uri $uri -Body @{
      chat_id = $TG_CHAT_ID
      text    = $text
      disable_web_page_preview = $true
    } | Out-Null
  }catch{
    # ignore telegram failures
  }
}

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
    $body = $null
    try{
      $code = $_.Exception.Response.StatusCode.value__
      $sr = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
      $body = $sr.ReadToEnd()
    }catch{ $code = 0 }
    return @{ ok=$false; code=$code; content=$body }
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
    }catch{ $code = 0 }
    return @{ ok=$false; code=$code; content=$body }
  }
}

function ParseJsonSafe($text){
  try { return ($text | ConvertFrom-Json) } catch { return $null }
}

function ToUtcDateSafe($s){
  try { return ([datetimeoffset]::Parse($s)).UtcDateTime } catch { return $null }
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
    TgSend "TypeF FAIL: TYPEF_ADMIN_TOKEN missing. Cannot recover."
    return $false
  }
  $h = @{ "X-ADMIN-TOKEN" = $ADMIN_TOKEN }
  $res = TryPost "$API_BASE/admin/restart_bot" $h
  if($res.code -eq 200){
    Ok "Level-1: restart_bot triggered (200)"
    TgSend "TypeF OK: Level-1 restart_bot triggered."
    return $true
  }
  Warn "Level-1: restart_bot failed HTTP=$($res.code) body=$($res.content)"
  TgSend "TypeF ALERT: Level-1 restart_bot failed HTTP=$($res.code)"
  return $false
}

function RestartService(){
  if(-not $ADMIN_TOKEN){
    Warn "ENV TYPEF_ADMIN_TOKEN not set. Can't call restart endpoints."
    TgSend "TypeF FAIL: TYPEF_ADMIN_TOKEN missing. Cannot recover."
    return $false
  }
  $h = @{ "X-ADMIN-TOKEN" = $ADMIN_TOKEN }
  $res = TryPost "$API_BASE/admin/restart_service" $h

  if($res.code -eq 200){
    Ok "Level-2: restart_service triggered (200)"
    TgSend "TypeF ALERT: Level-2 restart_service triggered."
    return $true
  }
  Warn "Level-2: restart_service returned HTTP=$($res.code) (service may still restart)"
  TgSend "TypeF ALERT: Level-2 restart_service called (HTTP=$($res.code))."
  return $true
}

# ===== MAIN =====
Info "Running production_guard.ps1 (v5)"
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
    TgSend "TypeF ALERT: Status JSON unavailable. Attempting Level-1 recovery."
    $ok = RestartBot
    if(-not $ok){
      Warn "Level-1 failed -> Level-2 restart"
      TgSend "TypeF ALERT: Level-1 failed. Triggering Level-2 restart."
      RestartService | Out-Null
    }
  }else{
    $botConn   = $st.bot_connected
    $botStatus = $st.botStatus.status
    $botMsg    = $st.botStatus.message

    $nowUtc = [datetime]::UtcNow
    $stTime = ToUtcDateSafe $st.server_time

    $isStale = $false
    $age = $null
    if($stTime){
      $age = (New-TimeSpan -Start $stTime -End $nowUtc).TotalSeconds
      if($age -gt $STALE_SECONDS){ $isStale = $true }
    }else{
      Warn "server_time parse failed -> treat stale"
      $isStale = $true
    }

    $needsRecovery = $false
    if($botConn -ne $true){ $needsRecovery = $true }
    if("$botStatus" -match "Error|Disconnected"){ $needsRecovery = $true }
    if($isStale){ $needsRecovery = $true }

    if($needsRecovery){
      Warn "Recovery trigger: bot_connected=$botConn botStatus=$botStatus stale=$isStale age=$age msg=$botMsg"
      TgSend "TypeF ALERT: Recovery trigger. bot_connected=$botConn botStatus=$botStatus stale=$isStale age=$age msg=$botMsg"

      $recovered = $false
      for($i=1; $i -le $L1_RETRIES; $i++){
        Info "Level-1 attempt $i/$L1_RETRIES"
        if(RestartBot){
          Start-Sleep -Seconds 5
          $st2 = GetStatusJson
          if($st2 -and $st2.bot_connected -eq $true){
            $st2Time = ToUtcDateSafe $st2.server_time
            $st2Stale = $true
            if($st2Time){
              $age2 = (New-TimeSpan -Start $st2Time -End ([datetime]::UtcNow)).TotalSeconds
              if($age2 -le $STALE_SECONDS){ $st2Stale = $false }
            }

            if(-not $st2Stale){
              Ok "Recovery success after Level-1"
              TgSend "TypeF OK: Recovery success after Level-1 bot restart."
              $recovered = $true
              break
            }
          }
        }
        Start-Sleep -Seconds $L1_SLEEP_SECONDS
      }

      if(-not $recovered){
        Warn "Level-1 did not recover -> Level-2 service restart"
        TgSend "TypeF ALERT: Level-1 did not recover. Triggering Level-2 restart."
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
