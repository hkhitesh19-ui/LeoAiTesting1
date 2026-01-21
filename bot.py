"""
TypeF Shoonya Bot (Institutional v2)

- Render safe
- Starts via FastAPI startup -> start_bot_thread()
- Stable Shoonya login (TOTP)
- Selects current month NIFTY FUT token
- Updates trade_data with:
    ltp, lastClose, lastCloseTime  (api_server contract)
  and keeps compatibility:
    current_ltp, last_close, last_close_time
"""

import os
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any

# Shoonya
from NorenRestApiPy.NorenApi import NorenApi

# =============================
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
