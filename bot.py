"""
Model E Trading Strategy Bot (Render-ready)
Volatility-Adjusted Position Sizing (VAPS) with Structural Hedge
- Handles Shoonya login
- Finds NIFTY current month future token
- Provides LIVE LTP
- Model E strategy scanning (1-hour timeframe)
- VIX-based position sizing
- Keeps last_close LTP for after-market display
"""

import os
import time
import threading
from datetime import datetime, timedelta
import pyotp

# REQUIRED dependency (must be in requirements.txt)
from NorenApi import NorenApi

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
# Shared runtime state
# ==============================
_BOT_THREAD_STARTED = False
_STOP_BOT = False

trade_data = {
    "active": False,

    # status/meta
    "last_run": None,
    "last_error": None,

    # instrument
    "symbol": "NIFTY FUT",
    "fut_token": None,

    # trade fields
    "entry_price": 0.0,
    "sl_price": 0.0,
    "target_price": 0.0,
    "entry_time": None,

    # ltp and fallback close
    "current_ltp": 0.0,
    "last_close": 0.0,
    "last_close_time": None,

    # history
    "trade_history": [],
}


# ==============================
# Shoonya API wrapper
# ==============================
class ShoonyaApiPy(NorenApi):
    def __init__(self):
        super().__init__(
            host="https://api.shoonya.com/NorenWClientTP/",
            websocket="wss://api.shoonya.com/NorenWSTP/",
        )


api = ShoonyaApiPy()


# ==============================
# ENV VARS (Render)
# ==============================
UID = os.getenv("SHOONYA_USERID")
PWD = os.getenv("SHOONYA_PASSWORD")
APP_KEY = os.getenv("SHOONYA_API_SECRET") or os.getenv("APP_KEY") or ""
VENDOR_CODE = os.getenv("SHOONYA_VENDOR_CODE") or os.getenv("VENDOR_CODE") or "NA"
vendor_code= os.getenv("VENDOR_CODE") or os.getenv("SHOONYA_VENDOR_CODE", "NA")
api_secret= os.getenv("APP_KEY") or os.getenv("SHOONYA_API_SECRET", "")
IMEI = os.getenv("IMEI") or os.getenv("SHOONYA_IMEI", "abc1234")


# Shoonya TOTP Secret (base32)
TOTP_KEY = os.getenv("TOTP_SECRET")


# ==============================
# Helper: Telegram send (NO polling)
# ==============================
def telegram_send(message: str):
    """
    Send telegram alert (push-only). No polling.
    """
    try:
        import requests
        token = os.getenv("TELEGRAM_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if not token or not chat_id:
            return

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass


# ==============================
# Login
# ==============================
def login_to_shoonya() -> bool:
    try:
        if not UID or not PWD or not TOTP_KEY:
            trade_data["last_error"] = "Missing UID/PWD/TOTP_KEY"
            print("❌ Missing SHOONYA_USERID / SHOONYA_PASSWORD / TOTP_SECRET env vars")
            return False

        key = TOTP_KEY.strip().replace(" ", "").upper()

        # must be base32 only
        for ch in key:
            if ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567":
                trade_data["last_error"] = "TOTP_KEY invalid format"
                print("❌ Invalid TOTP_KEY (must be base32 A-Z2-7)")
                return False

        totp_code = pyotp.TOTP(key).now()
        print(f"🔐 Logging in to Shoonya with UID: {UID}")

        ret = api.login(
            userid=UID,
            password=PWD,
            twoFA=totp_code,
            vendor_code=VENDOR_CODE,
            api_secret=APP_KEY,
            imei=IMEI,
        )

        print("DEBUG LOGIN RET:", ret)



        if ret and ret.get("stat") == "Ok":
            trade_data["last_error"] = None
            print("✅ Shoonya login OK")
            telegram_send("🟢 *Type F Bot Online*\nShoonya login successful ✅")
            return True

        err = ret.get("emsg", "Unknown error") if ret else "No response"
        trade_data["last_error"] = f"Login failed: {err}"
        print(f"❌ Shoonya login failed: {err}")
        telegram_send(f"🔴 *Shoonya Login Failed*\n{err}")
        return False

    except Exception as e:
        trade_data["last_error"] = f"Login exception: {e}"
        print(f"❌ Login exception: {e}")
        telegram_send(f"🔴 *Login Exception*\n{e}")
        return False


# ==============================
# Token fetch
# ==============================
def get_nifty_fut_token() -> str | None:
    """
    Find current month NIFTY FUT token. Prefer symbols like:
    NIFTY27JAN26F, NIFTY28FEB26F etc.
    """
    try:
        ret = api.searchscrip(exchange="NFO", searchtext="NIFTY")
        if not ret or "values" not in ret:
            print("❌ searchscrip failed (no values)")
            return None

        for s in ret["values"]:
            tsym = (s.get("tsym") or "").upper()
            token = s.get("token")

            # strict filters
            if not tsym.startswith("NIFTY"):
                continue
            if "BANK" in tsym or "FIN" in tsym or "MID" in tsym or "NXT50" in tsym:
                continue
            if "CE" in tsym or "PE" in tsym:
                continue
            if tsym.endswith("F"):  # Futures usually end with F
                trade_data["symbol"] = tsym
                trade_data["fut_token"] = token
                print(f"✅ FUT Selected: {tsym} | token={token}")
            return token

        print("⚠️ NIFTY FUT not found in search results")
        return None

    except Exception as e:
        print(f"❌ get_nifty_fut_token error: {e}")
        return None


# ==============================
# LTP fetch
# ==============================
def get_live_ltp() -> float:
    """
    Fetch live LTP for NIFTY FUT token.
    Also maintains last_close for market closed display.
    """
    try:
        token = trade_data.get("fut_token")
        if not token:
            return 0.0

        # Correct param is exchange= not exch=
        q = api.get_quotes(exchange="NFO", token=token)
        if not q:
            return float(trade_data.get("current_ltp") or 0.0)

        lp = q.get("lp") or q.get("last_price") or q.get("ltp")
        if lp is None:
            return float(trade_data.get("current_ltp") or 0.0)

        ltp = float(lp)

        # update current ltp always
        trade_data["current_ltp"] = ltp

        # If market closed, store as last_close once
        # (if ltp looks valid and time exists)
        if ltp > 0:
            trade_data["last_close"] = float(q.get("pc", q.get("c", ltp)))
            trade_data["last_close_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
def bot_loop():
    global trade_data

    # ---- 1) Ensure login once ----
    if not login_to_shoonya():
        print("❌ bot_loop: login failed, will retry in loop")
    else:
        print("✅ bot_loop: login OK")

    # ---- 2) Resolve NIFTY FUT token once ----
    if not trade_data.get("fut_token"):
        tok = get_nifty_fut_token()
        trade_data["fut_token"] = tok
        print("✅ FUT token:", tok)

    # ---- 3) Quote updater + Model E scanner loop ----
    last_scan_time = None
    scan_interval = 3600  # 1 hour in seconds
    
    while not _STOP_BOT:
        try:
            tok = trade_data.get("fut_token")
            if tok:
                q = api.get_quotes(exchange="NFO", token=tok)

                if q and q.get("lp"):
                    ltp = float(q.get("lp", q.get("pc", 0)))
                    trade_data["current_ltp"] = ltp

                    # update last_close only if it exists
                    if q.get("c"):
                        trade_data["last_close"] = float(q.get("pc", q.get("c", 0)))
                        trade_data["last_close_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Model E scanning (every 1 hour)
                current_time = time.time()
                if last_scan_time is None or (current_time - last_scan_time) >= scan_interval:
                    if MODEL_E_AVAILABLE:
                        scan_for_model_e()
                    last_scan_time = current_time

            time.sleep(2)

        except Exception as e:
            trade_data["last_error"] = f"Quote loop error: {e}"
            print("⚠️ Quote loop error:", e)
            time.sleep(5)
        except Exception as e:
            trade_data["last_error"] = f"bot_loop exception: {e}"
            print("⚠️ bot_loop exception:", e)
            time.sleep(5)











def stop_bot():
    global _STOP_BOT
    _STOP_BOT = True
    print("🛑 stop_bot(): stop flag set True")
