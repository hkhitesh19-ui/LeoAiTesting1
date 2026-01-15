"""
Type F Trading Strategy Bot (Render-ready)
- Handles Shoonya login
- Finds NIFTY current month future token
- Provides LIVE LTP
- Keeps last_close LTP for after-market display
- NO dynamic pip install
- NO circular import
"""

import os
import time
import threading
from datetime import datetime
import pyotp

# REQUIRED dependency (must be in requirements.txt)
from NorenApi import NorenApi


# ==============================
# Shared runtime state
# ==============================
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
            trade_data["last_close"] = ltp
            trade_data["last_close_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return ltp

    except Exception as e:
        trade_data["last_error"] = f"LTP fetch error: {e}"
        return float(trade_data.get("current_ltp") or 0.0)

def start_bot_thread():
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

    # ---- 3) Quote updater loop ----
    while True:
        try:
            tok = trade_data.get("fut_token")
            if tok:
                q = api.get_quotes(exchange="NFO", token=tok)

                if q and q.get("lp"):
                    ltp = float(q["lp"])
                    trade_data["current_ltp"] = ltp

                    # update last_close only if it exists
                    if q.get("c"):
                        trade_data["last_close"] = float(q["c"])
                        trade_data["last_close_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # if no live lp: keep last_close as fallback
            time.sleep(2)

        except Exception as e:
            trade_data["last_error"] = f"Quote loop error: {e}"
            print("⚠️ Quote loop error:", e)
            time.sleep(5)
        except Exception as e:
            trade_data["last_error"] = f"bot_loop exception: {e}"
            print("⚠️ bot_loop exception:", e)
            time.sleep(5)







