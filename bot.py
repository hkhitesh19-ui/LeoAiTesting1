<<<<<<< HEAD
"""
Model E Trading Strategy Bot (Render-ready)
Volatility-Adjusted Position Sizing (VAPS) with Structural Hedge
- Handles Shoonya login
- Finds NIFTY current month future token
- Provides LIVE LTP
- Model E strategy scanning (1-hour timeframe)
- VIX-based position sizing
- Keeps last_close LTP for after-market display
=======
﻿"""
TypeF Shoonya Bot (Institutional v2)

- Render safe
- Starts via FastAPI startup -> start_bot_thread()
- Stable Shoonya login (TOTP)
- Selects current month NIFTY FUT token
- Updates trade_data with:
    ltp, lastClose, lastCloseTime  (api_server contract)
  and keeps compatibility:
    current_ltp, last_close, last_close_time
>>>>>>> 1dc31967a729137b9f9419ddceeaf5021372be03
"""

import os
import time
import threading
<<<<<<< HEAD
from datetime import datetime, timedelta
import pyotp
=======
from datetime import datetime, timezone
from typing import Dict, Any
>>>>>>> 1dc31967a729137b9f9419ddceeaf5021372be03

# Shoonya
from NorenRestApiPy.NorenApi import NorenApi

<<<<<<< HEAD
# Model E Logic
try:
    from model_e_logic import calculate_model_e_indicators, get_vaps_lots, get_gear_from_vix, get_gear_status
    MODEL_E_AVAILABLE = True
except ImportError:
    print("⚠️ model_e_logic not available. Model E features disabled.")
    MODEL_E_AVAILABLE = False
    def calculate_model_e_indicators(*args, **kwargs): return None
    def get_vaps_lots(*args, **kwargs): return 0
    def get_gear_from_vix(*args, **kwargs): return 0
    def get_gear_status(*args, **kwargs): return "No Trade"


# ==============================
=======
# =============================
>>>>>>> 1dc31967a729137b9f9419ddceeaf5021372be03
# Shared runtime state
# =============================
trade_data: Dict[str, Any] = {
    "active": False,
    "status": "Booting",
    "last_error": None,

    # instrument
    "symbol": "",
    "fut_token": "",

    # API contract keys
    "ltp": 0.0,
    "lastClose": 0.0,
    "lastCloseTime": "",

    # compatibility keys (older)
    "current_ltp": 0.0,
    "last_close": 0.0,
    "last_close_time": None,

    # timing
    "last_run": "",
    "last_update_utc": "",
}

api = None
_bot_thread = None
_stop_flag = False


def telegram_send(msg: str):
    """
    Optional telegram: only if env vars exist.
    """
    try:
        token = os.getenv("TYPEF_TG_BOT_TOKEN", "")
        chat_id = os.getenv("TYPEF_TG_CHAT_ID", "")
        if not token or not chat_id:
            return
        import requests
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": msg}, timeout=8)
    except Exception:
        pass


def _safe_float(x) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


def shoonya_login() -> bool:
    global api

    UID = os.getenv("SHOONYA_USERID", "")
    PWD = os.getenv("SHOONYA_PASSWORD", "")
    TOTP_KEY = os.getenv("TOTP_SECRET", "")

    if not UID or not PWD or not TOTP_KEY:
        trade_data["last_error"] = "Missing env vars: SHOONYA_USERID/SHOONYA_PASSWORD/TOTP_SECRET"
        return False

    try:
        api = NorenApi()
        # NOTE: Shoonya login requires generated TOTP (your code already stable previously)
        import pyotp
        otp = pyotp.TOTP(TOTP_KEY).now()

        ret = api.login(userid=UID, password=PWD, twoFA=otp, vendor_code=os.getenv("SHOONYA_VENDOR_CODE",""),
                        api_secret=os.getenv("SHOONYA_API_SECRET",""), imei=os.getenv("SHOONYA_IMEI",""))

        if ret and ret.get("stat") == "Ok":
            trade_data["last_error"] = None
            telegram_send("🟢 TypeF Bot: Shoonya login OK")
            return True

        err = ret.get("emsg", "Unknown error") if ret else "No response"
        trade_data["last_error"] = f"Login failed: {err}"
        telegram_send(f"🔴 TypeF Bot: Login failed\n{err}")
        return False

    except Exception as e:
        trade_data["last_error"] = f"Login exception: {e}"
        telegram_send(f"🔴 TypeF Bot: Login exception\n{e}")
        return False


def select_current_month_nifty_fut_token() -> str:
    """
    Select first NIFTY FUT token from search results.
    """
    try:
        r = api.searchscrip(exchange="NFO", searchtext="NIFTY")
        if not r:
            return ""

        values = r.get("values") or []
        for item in values:
            tsym = item.get("tsym", "")
            token = item.get("token", "")
            if tsym.endswith("F") and token:
                trade_data["symbol"] = tsym
                trade_data["fut_token"] = token
                print(f"✅ FUT Selected: {tsym} | token={token}")
                return token
        return ""
    except Exception as e:
        trade_data["last_error"] = f"Token selection failed: {e}"
        return ""


def fetch_quote_prices() -> Dict[str, float]:
    """
    Returns {"ltp":..., "close":...}
    """
    token = trade_data.get("fut_token")
    if not token:
        return {"ltp": 0.0, "close": 0.0}

    q = api.get_quotes(exchange="NFO", token=token)
    if not q:
        return {"ltp": 0.0, "close": 0.0}

    ltp = q.get("lp") or q.get("ltp") or q.get("last_price")
    close = q.get("c") or q.get("close") or q.get("prev_close") or q.get("pclose")

    ltp_f = _safe_float(ltp)
    close_f = _safe_float(close)
    if close_f <= 0:
        close_f = ltp_f

    return {"ltp": ltp_f, "close": close_f}


<<<<<<< HEAD
        return ltp

    except Exception as e:
        trade_data["last_error"] = f"LTP fetch error: {e}"
        return float(trade_data.get("current_ltp") or 0.0)

# ==============================
# Model E Strategy Scanner
# ==============================
def scan_for_model_e():
    """
    Model E Strategy Scanner
    Scans for signals every 1 hour based on:
    - SuperTrend trend flip
    - RSI filter (< 65)
    - Price action (above ST line and EMA20)
    - VIX-based position sizing
    """
    try:
        if not MODEL_E_AVAILABLE:
            print("⚠️ Model E logic not available")
            return
        
        import pandas as pd
        
        # 1. Fetch 1-min historical data (last 24 hours = 1440 minutes)
        fut_token = trade_data.get("fut_token")
        if not fut_token:
            print("⚠️ FUT token not available for Model E scan")
            return
        
        # Get NIFTY spot token for historical data (26000 = NIFTY 50)
        nifty_spot_token = "26000"
        
        # Calculate time range (last 24 hours)
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        
        # Fetch historical data
        try:
            raw_data = api.get_time_price_series(
                exchange='NSE',
                token=nifty_spot_token,
                start_time=start_time.strftime('%Y-%m-%d %H:%M:%S'),
                end_time=end_time.strftime('%Y-%m-%d %H:%M:%S'),
                interval='1'
            )
            
            if not raw_data or len(raw_data) == 0:
                print("⚠️ No historical data available for Model E")
                return
            
            # Convert to DataFrame
            df_1min = pd.DataFrame(raw_data)
            df_1min.columns = ['time', 'open', 'high', 'low', 'close', 'volume']
            
            # Calculate indicators
            df_1h = calculate_model_e_indicators(df_1min)
            
            if df_1h.empty or len(df_1h) < 2:
                print("⚠️ Insufficient data for Model E analysis")
                return
            
            # Signal Candle (Last completed 1H candle)
            bar_i = df_1h.iloc[-1]
            bar_prev = df_1h.iloc[-2]
            
            # 2. Check Conditions
            trend_flip = (bar_i['st_direction'] == 1 and bar_prev['st_direction'] == -1)
            rsi_filter = bar_i['rsi'] < 65
            price_action = (bar_i['close'] > bar_i['st_line']) and (bar_i['close'] > bar_i['ema20'])
            
            # Update trade_data with current indicators
            trade_data['model_e_st_direction'] = int(bar_i['st_direction'])
            trade_data['model_e_rsi'] = float(bar_i['rsi'])
            trade_data['model_e_ema20'] = float(bar_i['ema20'])
            trade_data['model_e_st_line'] = float(bar_i['st_line'])
            
            # Get VIX
            try:
                vix_token = "26017"  # VIX token
                vix_data = api.get_quotes(exchange='NSE', token=vix_token)
                current_vix = float(vix_data.get('lp', 0))
                trade_data['current_vix'] = current_vix
                trade_data['current_gear'] = get_gear_from_vix(current_vix)
                trade_data['gear_status'] = get_gear_status(current_vix)
            except Exception as e:
                print(f"⚠️ VIX fetch error: {e}")
                current_vix = 0
                trade_data['current_vix'] = 0
                trade_data['current_gear'] = 0
                trade_data['gear_status'] = "No Trade"
            
            # Check if signal conditions met
            if trend_flip and rsi_filter and price_action:
                print(f"✅ Model E Signal Detected!")
                print(f"   Trend Flip: {trend_flip}")
                print(f"   RSI: {bar_i['rsi']:.2f} (< 65)")
                print(f"   Price > ST: {bar_i['close'] > bar_i['st_line']}")
                print(f"   Price > EMA20: {bar_i['close'] > bar_i['ema20']}")
                print(f"   VIX: {current_vix:.2f}")
                
                # Get VIX & Capital for position sizing
                net_equity = float(trade_data.get("net_equity", 1000000))  # Default 10L
                lots = get_vaps_lots(current_vix, net_equity)
                
                if lots > 0:
                    # Entry Logic
                    stop_loss = bar_i['close'] - (2.0 * bar_i['atr'])
                    entry_price = bar_i['close']
                    
                    print(f"   Lots: {lots}")
                    print(f"   Entry: {entry_price:.2f}")
                    print(f"   SL: {stop_loss:.2f}")
                    
                    # Execute trade (placeholder - implement execute_model_e_trade)
                    # execute_model_e_trade(lots, stop_loss, entry_price)
                    trade_data['model_e_signal'] = True
                    trade_data['model_e_lots'] = lots
                    trade_data['model_e_entry'] = entry_price
                    trade_data['model_e_sl'] = stop_loss
                else:
                    print(f"   ⚠️ No trade: Gear = 0 (VIX: {current_vix:.2f})")
                    trade_data['model_e_signal'] = False
            else:
                trade_data['model_e_signal'] = False
                print(f"ℹ️ Model E: No signal (Trend Flip: {trend_flip}, RSI: {bar_i['rsi']:.2f})")
                
        except Exception as e:
            print(f"❌ Model E scan error: {e}")
            trade_data["last_error"] = f"Model E scan error: {str(e)}"
            
    except Exception as e:
        print(f"❌ scan_for_model_e exception: {e}")
        trade_data["last_error"] = f"Model E exception: {str(e)}"

def start_bot_thread():
    global _BOT_THREAD_STARTED
    if _BOT_THREAD_STARTED:
        print("ℹ️ Bot thread already started, skipping.")
        return None
    _BOT_THREAD_STARTED = True

    t = threading.Thread(target=bot_loop, daemon=True)
    t.start()
    return t

# ==============================
# Main bot loop (auto-restored)
# ==============================
=======
>>>>>>> 1dc31967a729137b9f9419ddceeaf5021372be03
def bot_loop():
    global _stop_flag
    print("✅ BOT LOOP STARTED")
    trade_data["status"] = "Starting"
    trade_data["active"] = True

    # login retry loop
    while not _stop_flag:
        ok = shoonya_login()
        if ok:
            break
        trade_data["status"] = "LoginFailed"
        time.sleep(5)

    if _stop_flag:
        trade_data["status"] = "Stopped"
        return

<<<<<<< HEAD
    # ---- 3) Quote updater + Model E scanner loop ----
    last_scan_time = None
    scan_interval = 3600  # 1 hour in seconds
    
    while not _STOP_BOT:
=======
    trade_data["status"] = "LoginOK"

    # token selection retry
    while not _stop_flag:
        token = select_current_month_nifty_fut_token()
        if token:
            break
        trade_data["status"] = "TokenNotFound"
        time.sleep(5)

    if _stop_flag:
        trade_data["status"] = "Stopped"
        return

    trade_data["status"] = "Running"
    last_log_ts = 0

    while not _stop_flag:
>>>>>>> 1dc31967a729137b9f9419ddceeaf5021372be03
        try:
            trade_data["last_run"] = datetime.now(timezone.utc).isoformat()

            prices = fetch_quote_prices()
            ltp = prices["ltp"]
            close = prices["close"]

            # update trade_data keys (api_server contract + compatibility)
            if ltp > 0:
                trade_data["ltp"] = ltp
                trade_data["current_ltp"] = ltp

            if close > 0:
                trade_data["lastClose"] = close
                trade_data["last_close"] = close

                t = datetime.now().strftime("%H:%M:%S")
                trade_data["lastCloseTime"] = t
                trade_data["last_close_time"] = t

            trade_data["last_update_utc"] = datetime.now(timezone.utc).isoformat()

            now = time.time()
            if now - last_log_ts >= 60:
                last_log_ts = now
                print(f"✅ Prices | {trade_data.get('symbol')} ltp={trade_data.get('ltp')} close={trade_data.get('lastClose')}")

<<<<<<< HEAD
                # Model E scanning (every 1 hour)
                current_time = time.time()
                if last_scan_time is None or (current_time - last_scan_time) >= scan_interval:
                    if MODEL_E_AVAILABLE:
                        scan_for_model_e()
                    last_scan_time = current_time

=======
>>>>>>> 1dc31967a729137b9f9419ddceeaf5021372be03
            time.sleep(2)

        except Exception as e:
            trade_data["last_error"] = str(e)
            trade_data["status"] = "Error"
            print(f"❌ bot_loop error: {e}")
            time.sleep(5)

    trade_data["status"] = "Stopped"
    trade_data["active"] = False


def start_bot_thread():
    global _bot_thread, _stop_flag
    if _bot_thread and _bot_thread.is_alive():
        return
    _stop_flag = False
    _bot_thread = threading.Thread(target=bot_loop, daemon=True)
    _bot_thread.start()


def stop_bot():
    global _stop_flag
    _stop_flag = True
    trade_data["active"] = False
    trade_data["status"] = "Stopping"
