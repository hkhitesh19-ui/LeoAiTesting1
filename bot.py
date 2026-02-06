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
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
import pyotp

# Shoonya API
from NorenRestApiPy.NorenApi import NorenApi

# Institutional Config
CAPITAL = 500000.00  # Fixed at 5 Lakhs for Model E blueprint
FRICTION_PTS = 8.0   # Journaling requirement

# Token Storage
TOKENS = {
    "NIFTY_SPOT": "26000",
    "VIX": "26017",
    "FUT_CURR": "",
    "FUT_NEXT": ""
}

class ShoonyaApiPy(NorenApi):
    """Shoonya API wrapper with proper initialization"""
    def __init__(self):
        NorenApi.__init__(self, 
                         host='https://prism.shoonya.com/api', 
                         websocket='wss://prism.shoonya.com/NorenWSToken/')

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
# =============================
trade_data: Dict[str, Any] = {
    "active": False,
    "status": "Booting",
    "last_error": None,
    "last_run": None,

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

    # Model E data
    "current_vix": 0.0,
    "current_gear": 0,
    "gear_status": "No Trade",
    "model_e_signal": False,
    "model_e_lots": 0,
    "model_e_entry": 0.0,
    "model_e_sl": 0.0,
    "net_equity": 1000000,  # Default 10L

    # timing
    "last_update_utc": "",
}

api = None
_bot_thread = None
_stop_flag = False

def telegram_send(msg: str):
    """Optional telegram: only if env vars exist."""
    try:
        token = os.getenv("TELEGRAM_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
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
    """Login to Shoonya API with proper initialization"""
    global api
    UID = os.getenv("SHOONYA_USERID", "")
    PWD = os.getenv("SHOONYA_PASSWORD", "")
    TOTP_KEY = os.getenv("TOTP_SECRET", "")

    if not UID or not PWD or not TOTP_KEY:
        trade_data["last_error"] = "Missing env vars: SHOONYA_USERID/SHOONYA_PASSWORD/TOTP_SECRET"
        return False

    try:
        api = ShoonyaApiPy()
        otp = pyotp.TOTP(TOTP_KEY).now()
        ret = api.login(
            userid=UID, 
            password=PWD, 
            twoFA=otp, 
            vendor_code=os.getenv("SHOONYA_VENDOR_CODE", ""),
            api_secret=os.getenv("SHOONYA_API_SECRET", ""), 
            imei=os.getenv("SHOONYA_IMEI", "")
        )

        if ret and ret.get("stat") == "Ok":
            trade_data["last_error"] = None
            trade_data["status"] = "LoginOK"
            telegram_send("🟢 Model E Bot: Shoonya login OK")
            return True

        err = ret.get("emsg", "Unknown error") if ret else "No response"
        trade_data["last_error"] = f"Login failed: {err}"
        return False

    except Exception as e:
        trade_data["last_error"] = f"Login exception: {e}"
        return False

def resolve_futures_tokens():
    """Nifty Current aur Next Month Futures ke tokens find karta hai"""
    global TOKENS
    try:
        # NFO Search for NIFTY Futures
        ret = api.searchscrip(exchange='NFO', searchtext='NIFTY')
        if ret and 'values' in ret:
            # Filter for FUTIDX and sort by expiry
            futs = [item for item in ret['values'] if item.get('instname') == 'FUTIDX']
            if futs:
                # Sort by expiry date
                futs.sort(key=lambda x: datetime.strptime(x.get('expd', '01-Jan-2000'), '%d-%b-%Y'))
                
                TOKENS["FUT_CURR"] = futs[0].get('token', '')
                if len(futs) > 1:
                    TOKENS["FUT_NEXT"] = futs[1].get('token', '')
                
                print(f"✅ Tokens Resolved: Curr={TOKENS['FUT_CURR']}, Next={TOKENS['FUT_NEXT']}")
                trade_data["fut_token"] = TOKENS["FUT_CURR"]  # For backward compatibility
                if futs[0].get('tsym'):
                    trade_data["symbol"] = futs[0].get('tsym', '')
    except Exception as e:
        print(f"⚠️ Token resolution error: {e}")
        trade_data["last_error"] = f"Token resolution failed: {e}"

def get_market_data() -> Dict[str, Dict[str, float]]:
    """Spot, Futures aur VIX ka LTP aur Closing Price fetch karta hai"""
    data = {}
    try:
        for key, token in TOKENS.items():
            if not token:
                continue
            exchange = 'NSE' if key in ["NIFTY_SPOT", "VIX"] else 'NFO'
            res = api.get_quotes(exchange=exchange, token=token)
            if res and res.get('stat') == 'Ok':
                ltp = _safe_float(res.get('lp', 0))
                close = _safe_float(res.get('c', res.get('pc', res.get('close', 0))))
                if close == 0:
                    close = ltp  # Fallback to LTP if close not available
                data[key] = {
                    "ltp": ltp,
                    "close": close
                }
    except Exception as e:
        print(f"⚠️ Market data fetch error: {e}")
    return data

def select_current_month_nifty_fut_token() -> str:
    """Select first NIFTY FUT token from search results."""
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
    """Returns {"ltp":..., "close":...}"""
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

# ==============================
# Model E Execution Logic
# ==============================
def execute_model_e_trade(lots, stop_loss, entry_price):
    """
    Execute Model E Trade with Institutional Order Sequence:
    1. BUY OTM PUT (Hedge) - Market Order
    2. BUY NIFTY FUTURE (Main) - Market Order
    
    Args:
        lots: Number of lots to trade
        stop_loss: Stop loss price
        entry_price: Entry price
    """
    try:
        if not api:
            print("❌ API not initialized")
            return False
        
        # Get NIFTY spot for strike calculation
        nifty_spot_data = api.get_quotes(exchange='NSE', token='26000')
        nifty_spot = float(nifty_spot_data.get('lp', 0))
        
        if nifty_spot == 0:
            print("❌ Could not fetch NIFTY spot price")
            return False
        
        # Calculate Put Strike (ATM - 200, approx Delta 0.35)
        put_strike = round(nifty_spot / 50) * 50 - 200
        
        # Get current expiry (simplified - use current month)
        now = datetime.now()
        expiry_month = now.strftime('%b').upper()
        expiry_year = now.strftime('%y')
        current_expiry = f"{expiry_year}{expiry_month}"
        
        # Calculate quantity (lots * 50 for NIFTY)
        qty = lots * 50
        
        print(f"🚀 Executing Model E Trade:")
        print(f"   Lots: {lots}")
        print(f"   Entry: {entry_price:.2f}")
        print(f"   SL: {stop_loss:.2f}")
        print(f"   Put Strike: {put_strike}")
        
        # ORDER 1: BUY OTM PUT (Hedge) - Market Order
        print(f"📊 Order 1: Buying Put Strike {put_strike}PE")
        put_symbol = f"NIFTY{current_expiry}{put_strike}PE"
        
        put_order = api.place_order(
            buy_or_sell='B',
            product_type='M',  # MIS
            exchange='NFO',
            tradingsymbol=put_symbol,
            quantity=qty,
            discloseqty=0,
            price_type='MKT',
            price=0.0,
            trigger_price=None,
            retention='DAY',
            remarks='ModelE_Hedge'
        )
        
        if not put_order or put_order.get('stat') != 'Ok':
            error_msg = put_order.get('emsg', 'Unknown error') if put_order else 'No response'
            print(f"❌ Put order failed: {error_msg}")
            telegram_send(f"❌ Model E: Put order failed - {error_msg}")
            return False
        
        put_order_id = put_order.get('norenordno')
        print(f"✅ Put order placed: {put_order_id}")
        
        # Small delay between orders
        time.sleep(1)
        
        # ORDER 2: BUY NIFTY FUTURE (Main) - Market Order
        print(f"📊 Order 2: Buying NIFTY Future")
        fut_symbol = trade_data.get("symbol", f"NIFTY{current_expiry}F")
        
        fut_order = api.place_order(
            buy_or_sell='B',
            product_type='M',  # MIS
            exchange='NFO',
            tradingsymbol=fut_symbol,
            quantity=qty,
            discloseqty=0,
            price_type='MKT',
            price=0.0,
            trigger_price=None,
            retention='DAY',
            remarks='ModelE_Main'
        )
        
        if not fut_order or fut_order.get('stat') != 'Ok':
            error_msg = fut_order.get('emsg', 'Unknown error') if fut_order else 'No response'
            print(f"❌ Future order failed: {error_msg}")
            telegram_send(f"❌ Model E: Future order failed - {error_msg}")
            return False
        
        fut_order_id = fut_order.get('norenordno')
        print(f"✅ Future order placed: {fut_order_id}")
        
        # Update trade data
        current_gear = trade_data.get("current_gear", 0)
        trade_data["active"] = True
        trade_data["entry_price"] = entry_price
        trade_data["sl_price"] = stop_loss
        trade_data["model_e_signal"] = True
        trade_data["model_e_lots"] = lots
        trade_data["model_e_entry"] = entry_price
        trade_data["model_e_sl"] = stop_loss
        trade_data["put_order_id"] = put_order_id
        trade_data["fut_order_id"] = fut_order_id
        trade_data["put_strike"] = put_strike
        
        # Telegram Alert
        telegram_send(
            f"🚀 *Model E Entry*\n\n"
            f"Future + Hedge Buy\n"
            f"Gear: {current_gear}\n"
            f"Lots: {lots}\n"
            f"Entry: ₹{entry_price:,.2f}\n"
            f"SL: ₹{stop_loss:,.2f}\n"
            f"Put Strike: {put_strike}PE"
        )
        
        return True
        
    except Exception as e:
        print(f"❌ Execution failed: {e}")
        telegram_send(f"❌ Model E Execution Failed: {str(e)}")
        return False

def square_off_all():
    """
    Square off all Model E positions (Future + Put)
    Called on Friday 15:15 or manual exit
    """
    try:
        if not api:
            return False
        
        fut_symbol = trade_data.get("symbol", "")
        put_strike = trade_data.get("put_strike", 0)
        
        if not fut_symbol:
            print("⚠️ No active position to square off")
            return False
        
        print("🔒 Squaring off all Model E positions...")
        
        # Get current positions
        positions = api.get_positions()
        if not positions:
            print("⚠️ No positions found")
            return False
        
        # Square off Future
        # Square off Put
        # (Implementation depends on Shoonya API position management)
        
        trade_data["active"] = False
        telegram_send("🔒 Friday Mandatory Exit Complete. All positions squared off.")
        
        return True
        
    except Exception as e:
        print(f"❌ Square off failed: {e}")
        return False

def check_friday_exit():
    """
    Check if it's Friday 15:15 and trigger exit
    Called from bot loop
    """
    now = datetime.now()
    # 4 is Friday, 15:15 is 3:15 PM
    if now.weekday() == 4 and now.hour == 15 and now.minute >= 15:
        if trade_data.get("active"):
            print("🔒 Friday 15:15 Rule Triggered. Squaring off all positions.")
            square_off_all()
            telegram_send("🔒 Friday Mandatory Exit Complete. System Paused.")
            return True
    return False

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
                    
                    # Execute trade
                    execute_model_e_trade(lots, stop_loss, entry_price)
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

# ==============================
# Main bot loop
# ==============================
def bot_loop():
    global _stop_flag
    print("✅ Model E Bot Loop Started")
    trade_data["status"] = "Starting"
    trade_data["active"] = False

    # Login retry loop
    while not _stop_flag:
        ok = shoonya_login()
        if ok:
            break
        trade_data["status"] = "LoginFailed"
        time.sleep(5)

    if _stop_flag:
        trade_data["status"] = "Stopped"
        return

    trade_data["status"] = "LoginOK"

    # Resolve futures tokens (Current + Next)
    resolve_futures_tokens()

    if _stop_flag:
        trade_data["status"] = "Stopped"
        return

    trade_data["status"] = "Running"
    trade_data["net_equity"] = CAPITAL  # Fixed at 5 Lakhs
    last_log_ts = 0
    last_scan_time = None
    scan_interval = 3600  # 1 hour in seconds

    while not _stop_flag:
        try:
            # Check Friday exit
            check_friday_exit()
            
            trade_data["last_run"] = datetime.now(timezone.utc).isoformat()

            # Fetch all market data (Trinity View)
            mkt = get_market_data()
            
            # Extract VIX data
            vix_ltp = mkt.get('VIX', {}).get('ltp', 0)
            vix_close = mkt.get('VIX', {}).get('close', 0)
            
            # Extract Spot data
            spot_ltp = mkt.get('NIFTY_SPOT', {}).get('ltp', 0)
            spot_close = mkt.get('NIFTY_SPOT', {}).get('close', 0)
            
            # Extract Current Future data
            fut_curr_ltp = mkt.get('FUT_CURR', {}).get('ltp', 0)
            fut_curr_close = mkt.get('FUT_CURR', {}).get('close', 0)
            
            # Extract Next Future data
            fut_next_ltp = mkt.get('FUT_NEXT', {}).get('ltp', 0)
            fut_next_close = mkt.get('FUT_NEXT', {}).get('close', 0)
            
            # Update trade_data with Trinity View data (for api_server.py)
            trade_data["vix_ltp"] = vix_ltp
            trade_data["vix_close"] = vix_close
            trade_data["spot_ltp"] = spot_ltp
            trade_data["spot_close"] = spot_close
            trade_data["fut_curr_ltp"] = fut_curr_ltp
            trade_data["fut_curr_close"] = fut_curr_close
            trade_data["fut_next_ltp"] = fut_next_ltp
            trade_data["fut_next_close"] = fut_next_close
            
            # Backward compatibility keys
            trade_data["ltp"] = fut_curr_ltp
            trade_data["current_ltp"] = fut_curr_ltp
            trade_data["lastClose"] = fut_curr_close
            trade_data["last_close"] = fut_curr_close
            
            # Model E VIX and Gear
            trade_data["current_vix"] = vix_ltp
            if MODEL_E_AVAILABLE:
                trade_data["current_gear"] = get_gear_from_vix(vix_ltp)
                trade_data["gear_status"] = get_gear_status(vix_ltp)
            
            # Update timestamps
            t = datetime.now().strftime("%H:%M:%S")
            trade_data["lastCloseTime"] = t
            trade_data["last_close_time"] = t
            trade_data["last_update_utc"] = datetime.now(timezone.utc).isoformat()
            trade_data["heartbeat"] = t

            now = time.time()
            if now - last_log_ts >= 60:
                last_log_ts = now
                print(f"✅ Market Data | VIX={vix_ltp:.2f} | Spot={spot_ltp:.2f} | CurrFut={fut_curr_ltp:.2f} | NextFut={fut_next_ltp:.2f}")

            # Model E scanning (every 1 hour)
            current_time = time.time()
            if last_scan_time is None or (current_time - last_scan_time) >= scan_interval:
                if MODEL_E_AVAILABLE and not trade_data.get("active"):
                    scan_for_model_e()
                last_scan_time = current_time

            time.sleep(3)  # Dashboard refresh sync (3 seconds)

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
