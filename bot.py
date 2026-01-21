"""
TypeF Shoonya Bot (Production Clean)
- Render safe
- Starts via FastAPI startup -> start_bot_thread()
- Stable Shoonya login (TOTP)
- Selects current month NIFTY FUT token
- Updates trade_data with current_ltp + last_close (for market closed display)
"""

from __future__ import annotations

import os
import time
import threading
from datetime import datetime
from typing import Any, Dict, Optional

import pyotp
from NorenApi import NorenApi

# ==========================================================
# Shared runtime state (imported by api_server.py)
# ==========================================================
trade_data: Dict[str, Any] = {
    "active": False,

    # meta/status
    "last_run": None,
    "last_error": None,
    "status": "Booting",

    # instrument
    "symbol": "NIFTY FUT",
    "fut_token": None,

    # trade fields
    "entry_price": 0.0,
    "sl_price": 0.0,
    "target_price": 0.0,
    "entry_time": None,

    # prices
    "current_ltp": 0.0,
    "last_close": 0.0,
    "last_close_time": None,

    # history
    "trade_history": [],
}

# ==========================================================
# Thread state
# ==========================================================
_bot_thread: Optional[threading.Thread] = None
_stop_flag = False


# ==========================================================
# Shoonya wrapper
# ==========================================================
class ShoonyaApiPy(NorenApi):
    def __init__(self):
        super().__init__(
            host="https://api.shoonya.com/NorenWClientTP/",
            websocket="wss://api.shoonya.com/NorenWSTP/",
        )


api = ShoonyaApiPy()


# ==========================================================
# ENV
# ==========================================================
UID = os.getenv("SHOONYA_USERID")
PWD = os.getenv("SHOONYA_PASSWORD")

# Some repos use different names; support both
APP_KEY = os.getenv("SHOONYA_API_SECRET") or os.getenv("APP_KEY") or ""
VENDOR_CODE = os.getenv("SHOONYA_VENDOR_CODE") or os.getenv("VENDOR_CODE") or ""
IMEI = os.getenv("SHOONYA_IMEI") or os.getenv("IMEI") or "abc1234"

TOTP_KEY = os.getenv("TOTP_SECRET")


# ==========================================================
# Telegram push-only (optional)
# ==========================================================
def telegram_send(message: str):
    try:
        import requests

        token = os.getenv("TELEGRAM_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            return

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass


# ==========================================================
# Login
# ==========================================================
def login_to_shoonya() -> bool:
    try:
        if not UID or not PWD or not TOTP_KEY:
            trade_data["last_error"] = "Missing env vars: SHOONYA_USERID/SHOONYA_PASSWORD/TOTP_SECRET"
            print("❌ Missing env: SHOONYA_USERID / SHOONYA_PASSWORD / TOTP_SECRET")
            return False

        key = TOTP_KEY.strip().replace(" ", "").upper()

        # validate base32 (A-Z2-7)
        for ch in key:
            if ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567":
                trade_data["last_error"] = "TOTP_SECRET invalid base32 format"
                print("❌ Invalid TOTP_SECRET format (must be base32 A-Z2-7)")
                return False

        totp_code = pyotp.TOTP(key).now()
        print(f"🔐 Shoonya login start UID={UID}")

        ret = api.login(
            userid=UID,
            password=PWD,
            twoFA=totp_code,
            vendor_code=VENDOR_CODE,
            api_secret=APP_KEY,
            imei=IMEI,
        )

        if ret and ret.get("stat") == "Ok":
            trade_data["last_error"] = None
            print("✅ Shoonya login OK")
            telegram_send("🟢 TypeF Bot: Shoonya login OK")
            return True

        err = ret.get("emsg", "Unknown error") if ret else "No response"
        trade_data["last_error"] = f"Login failed: {err}"
        print(f"❌ Shoonya login failed: {err}")
        telegram_send(f"🔴 TypeF Bot: Login failed\n{err}")
        return False

    except Exception as e:
        trade_data["last_error"] = f"Login exception: {e}"
        print(f"❌ Shoonya login exception: {e}")
        telegram_send(f"🔴 TypeF Bot: Login exception\n{e}")
        return False


# ==========================================================
# Token fetch (fixed return bug)
# ==========================================================
def get_nifty_fut_token() -> Optional[str]:
    """
    Find current month NIFTY FUT token.
    Symbols example: NIFTY27JAN26F, NIFTY28FEB26F
    """
    try:
        ret = api.searchscrip(exchange="NFO", searchtext="NIFTY")
        if not ret or "values" not in ret:
            print("❌ searchscrip failed (no values)")
            return None

        # Prefer first FUT ending with F and not options
        for s in ret["values"]:
            tsym = s.get("tsym", "") or s.get("symbol", "") or ""
            token = s.get("token")

            if not tsym.startswith("NIFTY"):
                continue
            if any(x in tsym for x in ["BANK", "FIN", "MID", "NXT50"]):
                continue
            if "CE" in tsym or "PE" in tsym:
                continue

            if tsym.endswith("F"):
                trade_data["symbol"] = tsym
                trade_data["fut_token"] = token
                print(f"✅ FUT Selected: {tsym} | token={token}")
                return token  # ✅ correct return inside loop

        print("⚠️ NIFTY FUT not found")
        return None

    except Exception as e:
        print(f"❌ get_nifty_fut_token error: {e}")
        return None


# ==========================================================
# Quote fetch
# ==========================================================
def _safe_float(x: Any) -> float:
    try:
        if x is None:
            return 0.0
        return float(x)
    except Exception:
        return 0.0


def fetch_quote_prices() -> Dict[str, float]:
    """
    Returns {"ltp":..., "close":...}
    - ltp: lp/ltp/last_price
    - close: close price if available else ltp fallback
    """
    token = trade_data.get("fut_token")
    if not token:
        return {"ltp": 0.0, "close": 0.0}

    q = api.get_quotes(exchange="NFO", token=token)  # correct arg exchange=
    if not q:
        return {"ltp": 0.0, "close": 0.0}

    ltp = q.get("lp") or q.get("ltp") or q.get("last_price")
    close = (
        q.get("c")
        or q.get("close")
        or q.get("close_price")
        or q.get("prev_close")
        or q.get("pc")
    )

    ltp_f = _safe_float(ltp)
    close_f = _safe_float(close)
    if close_f <= 0:
        close_f = ltp_f

    return {"ltp": ltp_f, "close": close_f}


# ==========================================================
# Bot loop
# ==========================================================
def bot_loop():
    global _stop_flag

    print("✅ BOT LOOP STARTED")
    trade_data["status"] = "Starting"

    # login retry loop
    while not _stop_flag:
        ok = login_to_shoonya()
        if ok:
            break
        trade_data["status"] = "LoginFailed"
        time.sleep(5)

    if _stop_flag:
        return

    trade_data["status"] = "LoginOK"

    # token selection retry
    while not _stop_flag:
        token = get_nifty_fut_token()
        if token:
            break
        trade_data["status"] = "TokenNotFound"
        time.sleep(5)

    if _stop_flag:
        return

    trade_data["status"] = "Running"

    # main loop
    last_log_ts = 0.0
    while not _stop_flag:
        try:
            trade_data["last_run"] = datetime.now().isoformat()

            prices = fetch_quote_prices()
            ltp = prices["ltp"]
            close = prices["close"]

            # update state (BACKEND CONTRACT SAFE)
# api_server.py expects: ltp, lastClose, lastCloseTime
# keep old keys too: current_ltp, last_close, last_close_time
if ltp > 0:
    trade_data["current_ltp"] = ltp
    trade_data["ltp"] = ltp

if close > 0:
    trade_data["last_close"] = close
    trade_data["lastClose"] = close

    trade_data["last_close_time"] = datetime.now().strftime("%H:%M:%S")
    trade_data["lastCloseTime"] = trade_data["last_close_time"]

from datetime import timezone
trade_data["last_update_utc"] = datetime.now(timezone.utc).isoformat()

            # reduce log spam
            now = time.time()
            if now - last_log_ts > 20:
                last_log_ts = now
                print(
                    f"✅ Prices | {trade_data.get('symbol')} "
                    f"ltp={trade_data.get('current_ltp')} close={trade_data.get('last_close')}"
                )

            time.sleep(2)

        except Exception as e:
            trade_data["last_error"] = str(e)
            trade_data["status"] = "Error"
            print(f"❌ bot_loop error: {e}")
            time.sleep(5)


# ==========================================================
# Thread start/stop
# ==========================================================
def start_bot_thread():
    global _bot_thread, _stop_flag
    if _bot_thread and _bot_thread.is_alive():
        print("✅ Bot thread already alive")
        return

    _stop_flag = False
    _bot_thread = threading.Thread(target=bot_loop, daemon=True)
    _bot_thread.start()
    print("✅ Bot thread started")


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



