from __future__ import annotations

import os
import time
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Response, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ==========================================================
# App
# ==========================================================
app = FastAPI(title="TypeF API", version="1.0.0")


ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

def require_admin_token(x_admin_token: str | None):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN not set on server")
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
# CORS (GitHub Pages UI / any static site)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================================
# Build / Version metadata
# ==========================================================
BUILD_COMMIT = os.getenv("RENDER_GIT_COMMIT") or os.getenv("GIT_COMMIT") or "local"
BUILD_TIME = os.getenv("BUILD_TIME") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ==========================================================
# Import bot (optional)
# ==========================================================
BOT_CONNECTED = False
bot = None

# Safe fallback trade_data if bot not imported
trade_data: Dict[str, Any] = {
    "active": False,
    "last_run": None,
    "last_error": None,
    "status": "Booting",

    "symbol": "NIFTY FUT",
    "fut_token": None,

    "entry_price": 0.0,
    "sl_price": 0.0,
    "target_price": 0.0,
    "entry_time": None,

    "current_ltp": 0.0,
    "last_close": 0.0,
    "last_close_time": None,

    "trade_history": [],
}

try:
    import bot as bot_module  # noqa

    bot = bot_module
    if hasattr(bot_module, "trade_data") and isinstance(bot_module.trade_data, dict):
        trade_data = bot_module.trade_data
        BOT_CONNECTED = True
        print("✅ bot.py connected: trade_data imported")
    else:
        print("⚠️ bot.py imported but trade_data missing/invalid")
except Exception as e:
    BOT_CONNECTED = False
    print(f"⚠️ bot import failed: {e}")

# ==========================================================
# Helpers
# ==========================================================
def safe_float(x: Any) -> float:
    try:
        if x is None:
            return 0.0
        return float(x)
    except Exception:
        return 0.0


def safe_str(x: Any) -> str:
    try:
        return "" if x is None else str(x)
    except Exception:
        return ""


def normalize_trade_data(td: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compatibility layer for different bot versions:
    - ltp = current_ltp
    - close = last_close
    - display_ltp fallback
    """
    if not isinstance(td, dict):
        return {}

    # Normalize keys
    if "ltp" not in td or td.get("ltp") is None:
        td["ltp"] = td.get("current_ltp") or 0.0

    if "close" not in td or td.get("close") is None:
        td["close"] = td.get("last_close") or 0.0

    # display_ltp fallback
    disp = safe_float(td.get("display_ltp"))
    if disp == 0.0:
        td["display_ltp"] = td.get("current_ltp") or td.get("ltp") or td.get("close") or 0.0

    # defaults
    if not td.get("symbol"):
        td["symbol"] = "NIFTY FUT"

    return td


# ==========================================================
# API Models (STRICT CONTRACT)
# ==========================================================
class BotStatusModel(BaseModel):
    status: str = "Searching"
    message: str = "Scanning"


class ActiveTradeModel(BaseModel):
    symbol: str = "NIFTY FUT"
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


class StatusResponse(BaseModel):
    version: str = Field(default="local")
    build_time: str = Field(default="")
    server_time: str = Field(default="")
    bot_connected: bool = False
    botStatus: BotStatusModel = Field(default_factory=BotStatusModel)
    todayPnl: float = 0.0
    pnlPercentage: float = 0.0

    last_close_date: str = ""
    last_close_time: str = ""

    activeTrade: ActiveTradeModel = Field(default_factory=ActiveTradeModel)
    tradeHistory: List[TradeHistoryModel] = Field(default_factory=list)


# ==========================================================
# Bot thread auto-start (safe)
# ==========================================================
def start_bot_thread_safe():
    """
    Starts bot thread if available and not already started.
    Will NOT crash API if bot not present.
    """
    try:
        if not bot:
            return

        if hasattr(bot, "start_bot_thread"):
            bot.start_bot_thread()
            print("✅ Bot thread start called from FastAPI startup")
            return

        # fallback: if bot has internal loop method
        if hasattr(bot, "bot_loop"):
            # create thread only if missing
            if not hasattr(bot, "_bot_thread") or not getattr(bot, "_bot_thread"):
                th = threading.Thread(target=bot.bot_loop, daemon=True)
                setattr(bot, "_bot_thread", th)
                th.start()
                print("✅ Bot thread started (fallback)")
    except Exception as e:
        print(f"⚠️ start_bot_thread_safe error: {e}")


@app.on_event("startup")
def on_startup():
    start_bot_thread_safe()


# ==========================================================
# Routes
# ==========================================================
@app.get("/", tags=["system"])
def root():
    return {"ok": True, "service": "TypeF API", "commit": BUILD_COMMIT[:7]}


@app.api_route("/health", methods=["GET", "HEAD"], tags=["system"])
def health():
    return {"ok": True}


@app.get("/version", tags=["system"])
def version():
    return {
        "render_git_commit": os.getenv("RENDER_GIT_COMMIT", "unknown"),
        "git_commit": os.getenv("GIT_COMMIT", "unknown"),
        "build_commit": BUILD_COMMIT,
        "build_time": BUILD_TIME,
        "server_time": datetime.now().isoformat(),
        "bot_connected": BOT_CONNECTED,
    }


@app.get("/bot_thread", tags=["debug"])
def bot_thread():
    try:
        if not bot:
            return {"thread_alive": False, "error": "bot not imported"}

        if hasattr(bot, "_bot_thread"):
            th = getattr(bot, "_bot_thread")
            alive = bool(th and th.is_alive())
            return {"thread_alive": alive}

        return {"thread_alive": False, "error": "bot._bot_thread not found"}
    except Exception as e:
        return {"thread_alive": False, "error": str(e)}


@app.get("/debug_trade_data", tags=["debug"])
def debug_trade_data():
    try:
        if not bot:
            return {"ok": False, "error": "bot not imported"}
        if not hasattr(bot, "trade_data"):
            return {"ok": False, "error": "bot.trade_data not found"}
        return {"ok": True, "trade_data": bot.trade_data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/get_status", response_model=StatusResponse, tags=["dashboard"])
def get_status_strict(response: Response):
    """
    STRICT JSON contract always same.
    """
    response.headers["Cache-Control"] = "no-store"

    td = normalize_trade_data(dict(trade_data))

    # status
    bot_runtime_status = safe_str(td.get("status")) or ""
    active = bool(td.get("active", False))

    # prices
    entry = safe_float(td.get("entry_price"))
    sl = safe_float(td.get("sl_price"))
    ltp_val = safe_float(td.get("ltp"))
    close_val = safe_float(td.get("close"))
    display_val = safe_float(td.get("display_ltp"))
    if display_val == 0.0:
        display_val = ltp_val if ltp_val > 0 else close_val

    # pnl placeholders
    today_pnl = 0.0
    pnl_pct = 0.0

    # history normalization
    history = td.get("trade_history") or []
    if not isinstance(history, list):
        history = []

    trade_history: List[TradeHistoryModel] = []
    for t in history[:50]:
        if isinstance(t, dict):
            trade_history.append(
                TradeHistoryModel(
                    time=safe_str(t.get("time")) or None,
                    symbol=safe_str(t.get("symbol")),
                    type=safe_str(t.get("type")),
                    entry=safe_float(t.get("entry")),
                    exit=safe_float(t.get("exit")),
                    pnl=safe_float(t.get("pnl")),
                )
            )

    # bot status text (accurate)
    if active:
        status_text = "Active"
        msg_text = "Market Open"
    else:
        if BOT_CONNECTED:
            status_text = bot_runtime_status or "Running"
            msg_text = "Bot OK"
        else:
            status_text = "Disconnected"
            msg_text = "Bot Not Connected"

    payload = StatusResponse(
        version=(BUILD_COMMIT[:7] if BUILD_COMMIT else "local"),
        build_time=BUILD_TIME,
        server_time=datetime.now().isoformat(),
        bot_connected=BOT_CONNECTED,
        botStatus=BotStatusModel(status=status_text, message=msg_text),
        todayPnl=round(today_pnl, 2),
        pnlPercentage=round(pnl_pct, 3),
        last_close_date=datetime.now().strftime("%d-%b-%Y"),
        last_close_time=datetime.now().strftime("%H:%M:%S"),
        activeTrade=ActiveTradeModel(
            symbol=safe_str(td.get("symbol")) or "NIFTY FUT",
            entry=entry,
            sl=sl,
            ltp=ltp_val,
            close=close_val,
            display_ltp=display_val,
        ),
        tradeHistory=trade_history,
    )
    return payload


@app.post("/admin/restart_bot", tags=["admin"])
def admin_restart_bot(x_admin_token: str | None = Header(default=None, alias="X-ADMIN-TOKEN")):
    require_admin_token(x_admin_token)

    if "bot" not in globals():
        raise HTTPException(status_code=500, detail="bot module not loaded")

    try:
        # Stop existing bot loop
        if hasattr(bot, "stop_bot"):
            bot.stop_bot()
            time.sleep(2)

        # Start fresh bot thread
        if hasattr(bot, "start_bot_thread"):
            bot.start_bot_thread()
        else:
            raise HTTPException(status_code=500, detail="bot.start_bot_thread missing")

        return {"ok": True, "message": "Bot restart triggered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restart bot failed: {e}")


@app.post("/admin/restart_service", tags=["admin"])
def admin_restart_service(x_admin_token: str | None = Header(default=None, alias="X-ADMIN-TOKEN")):
    require_admin_token(x_admin_token)

    # Hard restart process; Render will relaunch container
    os._exit(1)

