from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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

bot_status: Dict[str, str] = {"status": "Searching", "message": "Scanning"}
today_pnl: float = 0.0
pnl_percentage: float = 0.0

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


def safe_get_live_ltp() -> float:
    """
    Prefer live LTP if bot is updating it.
    Falls back to close when market closed.
    """
    # expected keys from bot: ltp, close, display_ltp
    ltp = safe_float(trade_data.get("ltp"))
    close = safe_float(trade_data.get("close"))
    display_ltp = safe_float(trade_data.get("display_ltp"))

    if display_ltp > 0:
        return display_ltp
    if ltp > 0:
        return ltp
    return close


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

    active = bool(trade_data.get("active", False))

    entry = safe_float(trade_data.get("entry_price"))
    sl = safe_float(trade_data.get("sl_price"))
    ltp_val = safe_get_live_ltp()

    close_val = safe_float(trade_data.get("close"))
    display_val = safe_float(trade_data.get("display_ltp"))
    if display_val == 0.0:
        display_val = ltp_val if ltp_val > 0 else close_val

    # pnl calc (basic)
    _today_pnl = 0.0
    _pnl_pct = 0.0
    if active and entry > 0 and ltp_val > 0:
        _today_pnl = ltp_val - entry
        _pnl_pct = ((_today_pnl) / entry) * 100.0

    # history normalization
    history = trade_data.get("trade_history") or []
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

    # bot status
    status_text = "Active" if active else "Searching"
    msg_text = "Market Open" if active else "Scanning"

    payload = StatusResponse(
        version=(BUILD_COMMIT[:7] if BUILD_COMMIT else "local"),
        build_time=BUILD_TIME,
        server_time=datetime.now().isoformat(),
        bot_connected=BOT_CONNECTED,
        botStatus=BotStatusModel(status=status_text, message=msg_text),
        todayPnl=round(_today_pnl, 2),
        pnlPercentage=round(_pnl_pct, 3),
        activeTrade=ActiveTradeModel(
            symbol=safe_str(trade_data.get("symbol", "NIFTY FUT")) or "NIFTY FUT",
            entry=entry,
            sl=sl,
            ltp=safe_float(trade_data.get("ltp")),
            close=close_val,
            display_ltp=display_val,
        ),
        tradeHistory=trade_history,
    )

    return payload
