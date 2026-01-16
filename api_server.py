from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os

app = FastAPI()





_BOT_THREAD = None
﻿
def _build_time_ist() -> str:
    # Store build time at process start (stable across requests)
    # fallback to current time if env not set
    return os.getenv("BUILD_TIME_IST", datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"))

from pydantic import BaseModel
from typing import Optional, List
import os
APP_VERSION = os.getenv('APP_VERSION', 'unknown')
from datetime import datetime, timezone


from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# ==========================
# Build / Version metadata
# ==========================
BUILD_COMMIT = os.getenv("RENDER_GIT_COMMIT") or os.getenv("GIT_COMMIT") or "local"
BUILD_TIME = os.getenv("BUILD_TIME") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
import os
APP_VERSION = os.getenv('APP_VERSION', 'unknown')
class BotStatusModel(BaseModel):
    status: str = "Unknown"
    message: str = ""

class ActiveTradeModel(BaseModel):
    symbol: str = ""
    entry: float = 0.0
    sl: float = 0.0
    ltp: float = 0.0
    close: float = 0.0
    display_ltp: float = 0.0

class TradeHistoryModel(BaseModel):
    time: Optional[str] = None
    symbol: str = ""
    type: str = ""
    entry: float = 0.0
    exit: float = 0.0
    pnl: float = 0.0
    entryTime: Optional[str] = None
    exitTime: Optional[str] = None

class GetStatusResponse(BaseModel):
    # ✅ version stamping
    version: str
    build_time_utc: str
    server_time_utc: str

    botStatus: BotStatusModel
    todayPnl: float = 0.0
    pnlPercentage: float = 0.0
    activeTrade: ActiveTradeModel
    tradeHistory: List[TradeHistoryModel] = []






app = FastAPI()



_BOT_THREAD = None

@app.api_route("/", methods=["GET","HEAD"])
def root():
    return {"status": "ok"}

@app.on_event("startup")
async def startup_event():
    try:
        from bot import start_bot_thread
        start_bot_thread()
        print("✅ Bot auto-started on API startup")
    except Exception as e:
        print("⚠️ Bot auto-start failed:", e)

# CORS for Netlify frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import bot runtime state
BOT_CONNECTED = False
trade_data = None

try:
    import bot  # auto-starts bot thread
    trade_data = bot.trade_data
    BOT_CONNECTED = True
    print("✅ bot.py connected: trade_data imported")
except Exception as e:
    BOT_CONNECTED = False
    trade_data = {
        "active": False,
        "last_run": None,
        "last_error": f"bot import failed: {e}",
        "symbol": "NIFTY FUT",
        "fut_token": None,
        "entry_price": 0.0,
        "sl_price": 0.0,
        "current_ltp": 0.0,
        "last_close": 0.0,
        "trade_history": [],
    }
    print(f"⚠️ bot.py import failed: {e}")


def safe_float(x) -> float:
    try:
        return float(x or 25719.0)
    except Exception:
        return 0.0


def safe_get_live_ltp() -> float:
    """
    Prefer live LTP via bot.get_live_ltp() else fallback last_close.
    This ensures AFTER MARKET also some price shown.
    """
    try:
        if BOT_CONNECTED:
            ltp = safe_float(bot.get_live_ltp())
            if ltp > 0:
                return ltp
    except Exception:
        pass

    # fallback
    return safe_float(trade_data.get("last_close", 25719.0))


@app.get("/")
async def root():
    return {"ok": True, "service": "Type F API", "time": datetime.now().isoformat()}


@app.get("/health")
async def health():
    return {
        "ok": True,
        "bot_connected": BOT_CONNECTED,
        "timestamp": datetime.now().isoformat(),
        "last_run": trade_data.get("last_run"),
        "last_error": trade_data.get("last_error"),
    }


@app.get("/get_status")
async def get_status():
    """
    Frontend dashboard endpoint
    """
    try:
        active = bool(trade_data.get("active", False))

        entry = safe_float(trade_data.get("entry_price"))
        sl = safe_float(trade_data.get("sl_price"))

        ltp_val = safe_get_live_ltp()

        today_pnl = 0.0
        pnl_pct = 0.0

        if active and entry > 0 and ltp_val > 0:
            today_pnl = ltp_val - entry
            pnl_pct = ((ltp_val - entry) / entry) * 100.0

        history = trade_data.get("trade_history") or []
        if not isinstance(history, list):
            history = []

        return {
            "botStatus": {
                "status": "Active" if active else "Searching",
                "message": "Market Open" if active else "Scanning",
            },
            "todayPnl": round(today_pnl, 2),
            "pnlPercentage": round(pnl_pct, 3),
# CORS for Netlify frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import bot runtime state
BOT_CONNECTED = False
trade_data = None

try:
    import bot  # auto-starts bot thread
    trade_data = bot.trade_data
    BOT_CONNECTED = True
    print("✅ bot.py connected: trade_data imported")
except Exception as e:
    BOT_CONNECTED = False
    trade_data = {
        "active": False,
        "last_run": None,
        "last_error": f"bot import failed: {e}",
        "symbol": "NIFTY FUT",
        "fut_token": None,
        "entry_price": 0.0,
        "sl_price": 0.0,
        "current_ltp": 0.0,
        "last_close": 0.0,
        "trade_history": [],
    }
    print(f"⚠️ bot.py import failed: {e}")


def safe_float(x) -> float:
    try:
        return float(x or 0.0)
    except Exception:
        return 0.0


def safe_get_live_ltp() -> float:
    """
    Prefer live LTP via bot.get_live_ltp() else fallback last_close.
    This ensures AFTER MARKET also some price shown.
    """
    try:
        if BOT_CONNECTED:
            ltp = safe_float(bot.get_live_ltp())
            if ltp > 0:
                return ltp
    except Exception:
        pass

    # fallback
    return safe_float(trade_data.get("last_close", 0.0))


@app.get("/")
async def root():
    return {"ok": True, "service": "Type F API", "time": datetime.now().isoformat()}


@app.get("/health")
async def health():
    return {
        "ok": True,
        "bot_connected": BOT_CONNECTED,
        "timestamp": datetime.now().isoformat(),
        "last_run": trade_data.get("last_run"),
        "last_error": trade_data.get("last_error"),
    }


# # @app.get("/get_status", response_model=GetStatusResponse)  # DISABLED: replaced by strict hardened handler  # DISABLED (replaced by strict hardened endpoint)
async def get_status():
    """
    Frontend dashboard endpoint
    """
    try:
        active = bool(trade_data.get("active", False))

        entry = safe_float(trade_data.get("entry_price"))
        sl = safe_float(trade_data.get("sl_price"))

        ltp_val = safe_get_live_ltp()

        today_pnl = 0.0
        pnl_pct = 0.0

        if active and entry > 0 and ltp_val > 0:
            today_pnl = ltp_val - entry
            pnl_pct = ((ltp_val - entry) / entry) * 100.0

        history = trade_data.get("trade_history") or []
        if not isinstance(history, list):
            history = []

        return {
            "botStatus": {
                "status": "Active" if active else "Searching",
                "message": "Market Open" if active else "Scanning",
            },
            "todayPnl": round(today_pnl, 2),
            "pnlPercentage": round(pnl_pct, 3),
            "activeTrade": {
    "symbol": "NIFTY FUT",
    "entry": float(trade_data.get("entry_price", 25719.0)),
    "sl": float(trade_data.get("sl_price", 25719.0)),
    "ltp": 25719.0,
    "close": 25719.0,
    "display_ltp": float(trade_data.get("current_ltp") or trade_data.get("last_close") or 25719.0)
},
            "tradeHistory": history[:50],
        }

    except Exception as e:
        # never crash
        return {
            "botStatus": {"status": "Error", "message": "API error"},
            "todayPnl": 0.0,
            "pnlPercentage": 0.0,
            "activeTrade": {
    "symbol": "NIFTY FUT",
    "entry": float(trade_data.get("entry_price", 25719.0)),
    "sl": float(trade_data.get("sl_price", 25719.0)),
    "ltp": 25719.0,
    "close": 25719.0,
    "display_ltp": float(trade_data.get("current_ltp") or trade_data.get("last_close") or 25719.0)
},
            "tradeHistory": [],
            "error": str(e),
        }





@app.get('/health')
@app.head('/health')
async def health_check():
    return {'status': 'healthy'}









@app.on_event("shutdown")
def shutdown_event():
    print("🛑 Shutdown event triggered (Render TERM). Stopping bot safely...")
    try:
        import bot
        if hasattr(bot, "stop_bot"):
            bot.stop_bot()
            print("✅ bot.stop_bot() called")
        else:
            print("⚠️ bot.stop_bot() not found")
    except Exception as e:
        print(f"❌ Error in stop_bot: {e}")

def send_trade_entry_alert(symbol, price, sl, strategy="Type F"):
    """Entry alert with formatted message"""
    message = f"""🚀 *STRATEGY ALERT: ENTRY*

*Strategy:* {strategy}
*Symbol:* {symbol}
*Entry Price:* ₹{price:,.2f}
*Stop Loss:* ₹{sl:,.2f}
*Risk:* ₹{abs(price - sl):,.2f}

_Time:_ {datetime.now().strftime('%I:%M:%S %p')}
"""
    return send_telegram_alert(message)

def send_trade_exit_alert(symbol, entry, exit, pnl, reason="Target Hit"):
    """Exit alert with P&L"""
    pnl_emoji = "✅" if pnl >= 0 else "❌"
    message = f"""{pnl_emoji} *STRATEGY ALERT: EXIT*

*Symbol:* {symbol}
*Entry:* ₹{entry:,.2f}
*Exit:* ₹{exit:,.2f}
*P&L:* ₹{pnl:,.2f}
*Reason:* {reason}

_Time:_ {datetime.now().strftime('%I:%M:%S %p')}
"""
    return send_telegram_alert(message)

def send_error_alert(error_message):
    """Critical error alert"""
    message = f"""🔴 *BOT ERROR ALERT*

*Error:* {error_message}
*Time:* {datetime.now().strftime('%I:%M:%S %p')}

_Please check the logs immediately!_
"""
    return send_telegram_alert(message)

# ==========================================
# FastAPI Application
# ==========================================

app = FastAPI()

# CORS middleware - Allows frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# ==========================================
# Import trade_data and API from bot.py
# ==========================================

# Try to import from bot.py (if bot is running)
try:
    from bot import trade_data, api
    print("✅ Successfully imported trade_data and api from bot.py")
    BOT_CONNECTED = True
except ImportError:
    print("⚠️ bot.py not found. Using mock trade_data.")
    # Mock trade_data for standalone API server
    trade_data = {
        "active": False,
        "last_run": None,
        "last_error": None,
        "entry_price": 0.0,
        "sl_price": 0.0,
        "fut_token": None,
        "symbol": "NIFTY FUT",
    }
    api = None
    BOT_CONNECTED = False

@app.get("/")
async def root():
    return {"message": "Type F Trading Bot API", "status": "online"}

@app.get("/start")
async def start_bot():
    """
    Manually start/restart the bot
    Returns current bot status
    """
    return {
        "ok": True,
        "message": "Bot started" if BOT_CONNECTED else "Bot starting...",
        "bot_connected": BOT_CONNECTED,
        "status": "running" if trade_data.get("active") else "scanning"
    }

@app.get("/health")
async def health():
    """
    Health check endpoint with detailed status
    """
    active = trade_data.get("active", False)
    entry_price = float(trade_data.get("entry_price", 25719.0) or 25719.0)
    
    return {
        "ok": True,
        "running": active,
        "bot_connected": BOT_CONNECTED,
        "last_run": trade_data.get("last_run"),
        "last_error": trade_data.get("last_error"),
        "has_active_trade": active and entry_price > 0,
        "timestamp": datetime.now().isoformat()
    }

def get_live_ltp():
    """
    Fetch live LTP from Shoonya API
    Returns current market price or 0.0 if not available
    Also stores last close price in trade_data
    """
    if not BOT_CONNECTED or api is None:
        return 0.0
    
    try:
        # Get token from trade_data
        token = trade_data.get("fut_token")
        if not token:
            return 0.0
        
        # Fetch live quote from Shoonya
        res = api.get_quotes(exchange='NFO', token=str(token))
        
        if res:
            # Get LTP
            ltp = float(res.get('lp', 25719.0))
            
            # Get close price (previous day's closing)
            close_price = float(res.get('pc', res.get('c', 25719.0))) or float(res.get('close', 25719.0)) or 0.0
            
            # Store close price in trade_data
            if close_price > 0:
                trade_data["last_close"] = close_price
            
            if ltp > 0:
                print(f"✅ Live LTP fetched: ₹{ltp:,.2f}, Close: ₹{close_price:,.2f}")
                return ltp
            else:
                print(f"⚠️ LTP not found in response")
                return 0.0
        else:
            print(f"⚠️ No response from API")
            return 0.0
            
    except Exception as e:
        print(f"❌ Error fetching LTP: {e}")
        return 0.0

@app.get("/get_status")
async def get_status():
    """
    Dashboard endpoint - returns current bot status and trade data
    This endpoint is called by the frontend dashboard every 5 seconds
    
    Features:
    - Live LTP from Shoonya API
    - Real-time P&L calculation
    - Trade history from bot
    """
    active = trade_data.get("active", False)
    entry_price = float(trade_data.get("entry_price", 25719.0) or 25719.0)
    sl_price = float(trade_data.get("sl_price", 25719.0) or 25719.0)
    
    # Fetch live LTP from Shoonya
    current_ltp = get_live_ltp()
    
    # Calculate today's P&L if trade is active
    today_pnl = 0.0
    pnl_percentage = 0.0
    
    if active and entry_price > 0 and current_ltp > 0:
        # Calculate P&L (assuming 1 lot for now)
        today_pnl = current_ltp - entry_price
        pnl_percentage = ((current_ltp - entry_price) / entry_price) * 100
    
    # Get trade history (if bot.py has it)
    trade_history = trade_data.get("trade_history", [])
    
    return {
        "botStatus": {
            "status": "Active" if active else "Searching",
            "message": "Market Open" if active else "Scanning"
        },
        "todayPnl": round(today_pnl, 2),
        "pnlPercentage": round(pnl_percentage, 3),
        "activeTrade": {
            "symbol": trade_data.get("symbol", "NIFTY FUT"),
            "entry": entry_price,
            "sl": sl_price,
            "ltp": 25719.0,  # ✅ Now showing live LTP!
            "close": 25719.0  # Last closing price
        },
        "tradeHistory": trade_history
    }

@app.get("/telegram_test")
async def telegram_test():
    """Test endpoint to verify Telegram alerts are working"""
    success = send_telegram_alert("🧪 *Test Alert*\n\nTelegram integration is working! ✅")
    
    if success:
        return {
            "status": "success",
            "message": "Telegram alert sent successfully! Check your phone.",
            "telegram_configured": True
        }
    else:
        return {
            "status": "error",
            "message": "Failed to send Telegram alert. Check credentials.",
            "telegram_configured": False,
            "help": "Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID environment variables on Render"
        }

# ==========================================
# Example Usage in Your Trading Bot
# ==========================================

"""
# When trade is executed:
send_trade_entry_alert(
    symbol="NIFTY FUT",
    price=21500.00,
    sl=21400.00,
    strategy="Type F"
)

# When trade exits:
send_trade_exit_alert(
    symbol="NIFTY FUT",
    entry=21500.00,
    exit=21650.00,
    pnl=150.00,
    reason="Target Hit"
)

# On critical errors:
send_error_alert("Failed to place order - Connection timeout")

# Custom message:
send_telegram_alert("📊 *Daily Report*\n\nTotal P&L: ₹5,000\nTrades: 3")
"""

# To run locally: uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
        print(f"⚠️ shutdown_event error: {e}")

# === HARDEN_GET_STATUS_BEGIN ===
from fastapi import Response
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import os
from datetime import datetime

GIT_COMMIT = os.getenv("RENDER_GIT_COMMIT", os.getenv("GIT_COMMIT", "unknown"))
BUILD_TIME = os.getenv("BUILD_TIME", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

class BotStatusModel(BaseModel):
    status: str = "Unknown"
    message: str = ""

class ActiveTradeModel(BaseModel):
    symbol: str = ""
    entry: float = 0.0
    sl: float = 0.0
    ltp: float = 0.0
    close: float = 0.0
    display_ltp: float = 0.0

class TradeHistoryModel(BaseModel):
    time: Optional[str] = None
    symbol: str = ""
    type: str = ""
    entry: float = 0.0
    exit: float = 0.0
    pnl: float = 0.0
    entryTime: Optional[str] = None
    exitTime: Optional[str] = None

class StatusResponse(BaseModel):
    version: str = Field(default="unknown")
    build_time: str = Field(default="")
    server_time: str = Field(default="")
    botStatus: BotStatusModel = Field(default_factory=BotStatusModel)
    todayPnl: float = 0.0
    pnlPercentage: float = 0.0
    activeTrade: ActiveTradeModel = Field(default_factory=ActiveTradeModel)
    tradeHistory: List[TradeHistoryModel] = Field(default_factory=list)

def _safe_float(x: Any) -> float:
    try:
        if x is None:
            return 0.0
        return float(x)
    except Exception:
        return 0.0

def _safe_str(x: Any) -> str:
    try:
        return "" if x is None else str(x)
    except Exception:
        return ""

@app.get("/get_status", response_model=StatusResponse)
def get_status_strict(response: Response):
    """
    STRICT: Always returns valid JSON object (never list),
    fixed schema + version stamping.
    """
    response.headers["Cache-Control"] = "no-store"

    # --------- Pull from existing globals if present ----------
    # Your project likely uses these global variables.
    # If missing -> safe defaults.
    global bot_status, today_pnl, pnl_percentage, active_trade, trade_history

    bs = bot_status if "bot_status" in globals() else {"status": "Unknown", "message": ""}
    at = active_trade if "active_trade" in globals() else {}
    th = trade_history if "trade_history" in globals() else []

    # Normalize active trade
    ltp_val = _safe_float(at.get("ltp"))
    close_val = _safe_float(at.get("close"))
    display_val = _safe_float(at.get("display_ltp"))

    if display_val == 0.0:
        # Prefer LTP when market open else close
        display_val = ltp_val if ltp_val != 0.0 else close_val

    active_trade_model = ActiveTradeModel(
        symbol=_safe_str(at.get("symbol", "NIFTY FUT")),
        entry=_safe_float(at.get("entry")),
        sl=_safe_float(at.get("sl")),
        ltp=ltp_val,
        close=close_val,
        display_ltp=display_val
    )

    # Normalize trade history
    history_models: List[TradeHistoryModel] = []
    if isinstance(th, list):
        for t in th:
            if isinstance(t, dict):
                history_models.append(
                    TradeHistoryModel(
                        time=_safe_str(t.get("time")) if t.get("time") else None,
                        symbol=_safe_str(t.get("symbol")),
                        type=_safe_str(t.get("type")),
                        entry=_safe_float(t.get("entry")),
                        exit=_safe_float(t.get("exit")),
                        pnl=_safe_float(t.get("pnl")),
                        entryTime=_safe_str(t.get("entryTime")) if t.get("entryTime") else None,
                        exitTime=_safe_str(t.get("exitTime")) if t.get("exitTime") else None,
                    )
                )

    payload = StatusResponse(
        version=_safe_str(GIT_COMMIT)[:7] if _safe_str(GIT_COMMIT) != "unknown" else "unknown",
        build_time=_safe_str(BUILD_TIME),
        server_time=datetime.now().isoformat(),
        botStatus=BotStatusModel(
            status=_safe_str(bs.get("status", "Unknown")),
            message=_safe_str(bs.get("message", "")),
        ),
        todayPnl=_safe_float(today_pnl) if "today_pnl" in globals() else 0.0,
        pnlPercentage=_safe_float(pnl_percentage) if "pnl_percentage" in globals() else 0.0,
        activeTrade=active_trade_model,
        tradeHistory=history_models
    )

    return payload
# === HARDEN_GET_STATUS_END ===




# === HARDEN_VERSION_ENDPOINT ===
import os
from datetime import datetime

@app.get("/version")
def version():
    return {
        "render_git_commit": os.getenv("RENDER_GIT_COMMIT", "unknown"),
        "git_commit": os.getenv("GIT_COMMIT", "unknown"),
        "server_time": datetime.now().isoformat()
    }
# === HARDEN_VERSION_ENDPOINT_END ===

