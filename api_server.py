from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from bot import start_bot_thread

@app.on_event("startup")
def startup_event():
    start_bot_thread()


# ==========================================================
# App
# ==========================================================
app = FastAPI(title="TypeF API", version="1.0.0")

# CORS (Netlify)
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
# Runtime state (safe defaults)
# ==========================================================
BOT_CONNECTED = False

trade_data: Dict[str, Any] = {
    "active": False,
    "symbol": "NIFTY FUT",
    "entry_price": 0.0,
    "sl_price": 0.0,
    "ltp": 0.0,
    "close": 0.0,
    "display_ltp": 0.0,
    "trade_history": [],
}

# ==========================================================
# Try importing bot.py (optional)
# ==========================================================
try:
    import bot  # noqa

    if hasattr(bot, "trade_data") and isinstance(bot.trade_data, dict):
        trade_data = bot.trade_data
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
    Compatibility layer: supports old/new bot key names.
    Does NOT mutate global trade_data (caller should pass dict(trade_data)).
    """
    if not isinstance(td, dict):
        return {}

    # entry / sl
    if "entry_price" not in td and "entry" in td:
        td["entry_price"] = td.get("entry")
    if "sl_price" not in td and "sl" in td:
        td["sl_price"] = td.get("sl")

    # ltp / close
    if "ltp" not in td or td.get("ltp") is None:
        td["ltp"] = td.get("current_ltp") or td.get("display_ltp") or td.get("last_ltp") or 0.0

    if "close" not in td or td.get("close") is None:
        td["close"] = td.get("last_close") or td.get("close_price") or 0.0

    # display_ltp fallback
    try:
        if "display_ltp" not in td or float(td.get("display_ltp") or 0) == 0.0:
            td["display_ltp"] = td.get("current_ltp") or td.get("ltp") or td.get("close") or 0.0
    except Exception:
        td["display_ltp"] = td.get("current_ltp") or td.get("ltp") or td.get("close") or 0.0

    # symbol fallback
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

    # last close meta
    last_close_date: str = ""
    last_close_time: str = ""

    activeTrade: ActiveTradeModel = Field(default_factory=ActiveTradeModel)
    tradeHistory: List[TradeHistoryModel] = Field(default_factory=list)


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


@app.get("/get_status", response_model=StatusResponse, tags=["dashboard"])
def get_status_strict(response: Response):
    """
    STRICT JSON. Always returns same schema.
    """
    response.headers["Cache-Control"] = "no-store"

    td = normalize_trade_data(dict(trade_data))

    active = bool(td.get("active", False))

    entry = safe_float(td.get("entry_price"))
    sl = safe_float(td.get("sl_price"))

    ltp_val = safe_float(td.get("ltp"))
    close_val = safe_float(td.get("close"))
    display_val = safe_float(td.get("display_ltp"))
    if display_val == 0.0:
        display_val = ltp_val if ltp_val > 0 else close_val

    # pnl calc (basic)
    today_pnl = 0.0
    pnl_pct = 0.0
    if active and entry > 0 and display_val > 0:
        today_pnl = display_val - entry
        pnl_pct = (today_pnl / entry) * 100.0

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

    status_text = "Active" if active else "Searching"
    msg_text = "Market Open" if active else "Scanning"

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

@app.get("/bot_thread")
def bot_thread():
    try:
        from bot import _bot_thread
        return {"thread_alive": bool(_bot_thread and _bot_thread.is_alive())}
    except Exception as e:
        return {"thread_alive": False, "error": str(e)}


