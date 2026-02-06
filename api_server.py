import os
import time
import threading
from datetime import datetime, timezone
from typing import Optional, Any, Dict

from fastapi import FastAPI, Response, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# =========================
# App init
# =========================
app = FastAPI(title="TypeF Backend API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Admin Auth
# =========================
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")


def require_admin_token(x_admin_token: str | None):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN not set on server")
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


# =========================
# Optional bot import
# =========================
bot = None
try:
    import bot as bot_module
    bot = bot_module
except Exception as e:
    bot = None


# =========================
# Models
# =========================
class BotStatusModel(BaseModel):
    status: str = "Searching"
    message: str = ""


class StatusResponse(BaseModel):
    version: str = "unknown"
    build_time: str = ""
    server_time: str = ""
    bot_connected: bool = False
    botStatus: BotStatusModel = Field(default_factory=BotStatusModel)
    todayPnl: float = 0.0
    pnlPercentage: float = 0.0
    ltp: float = 0.0
    lastClose: float = 0.0
    lastCloseTime: str = ""


# =========================
# Build metadata
# =========================
def _git_commit_short() -> str:
    # Render injects RENDER_GIT_COMMIT; fallback to env
    commit = os.getenv("RENDER_GIT_COMMIT", "") or os.getenv("GIT_COMMIT", "")
    if commit:
        return commit[:7]
    return "unknown"


BUILD_TIME = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# =========================
# Health / Version
# =========================
@app.get("/health", tags=["system"])
def health():
    return {"ok": True}


@app.get("/version", tags=["system"])
def version():
    return {
        "render_git_commit": os.getenv("RENDER_GIT_COMMIT", "unknown"),
        "build_commit": os.getenv("RENDER_GIT_COMMIT", "unknown"),
        "build_time": BUILD_TIME,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


# =========================
# Status API (STRICT JSON)
# =========================
@app.get("/get_status", response_model=StatusResponse, tags=["dashboard"])
def get_status_strict(response: Response):
    response.headers["Cache-Control"] = "no-store"

    # base values
    bot_connected = False
    bot_status = "Disconnected"
    bot_msg = "Bot not running"

    ltp = 0.0
    last_close = 0.0
    last_close_time = ""
    today_pnl = 0.0
<<<<<<< HEAD
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
            "ltp": current_ltp,  # ✅ Now showing live LTP!
            "close": trade_data.get("last_close", 0.0) or 0.0  # Last closing price
        },
        "tradeHistory": trade_history,
        # Model E Data
        "currentVix": trade_data.get("current_vix", 0.0),
        "currentGear": trade_data.get("current_gear", 0),
        "gearStatus": trade_data.get("gear_status", "No Trade"),
        "modelE": {
            "vix": trade_data.get("current_vix", 0.0),
            "gear": trade_data.get("current_gear", 0),
            "gearStatus": trade_data.get("gear_status", "No Trade"),
            "signal": trade_data.get("model_e_signal", False),
            "rsi": trade_data.get("model_e_rsi", 0.0),
            "st_direction": trade_data.get("model_e_st_direction", 0)
        }
    }
=======
    pnl_pct = 0.0
>>>>>>> 1dc31967a729137b9f9419ddceeaf5021372be03

    # try pull trade_data from bot if available
    if bot is not None:
        try:
            td: Dict[str, Any] = getattr(bot, "trade_data", {}) or {}

            # Connection inference
            # bot.trade_data should contain status like Running/LoginOK etc.
            runtime_status = str(td.get("status") or "").strip()
            is_ok = runtime_status.lower() in ["running", "loginok", "connected", "active"]

            bot_connected = bool(td.get("connected", False)) or is_ok

            if bot_connected:
                bot_status = runtime_status or "Running"
                bot_msg = "Bot OK"
            else:
                bot_status = "Disconnected"
                bot_msg = runtime_status or "Bot Disconnected"

            # Numeric fields
            def _f(x, default=0.0):
                try:
                    return float(x)
                except Exception:
                    return float(default)

            ltp = _f(td.get("ltp", 0))
            last_close = _f(td.get("lastClose", 0))
            last_close_time = str(td.get("lastCloseTime", "") or "")
            today_pnl = _f(td.get("todayPnl", 0))
            pnl_pct = _f(td.get("pnlPercentage", 0))

        except Exception as e:
            bot_connected = False
            bot_status = "Error"
            bot_msg = f"Bot exception: {e}"

    payload = StatusResponse(
        version=_git_commit_short(),
        build_time=BUILD_TIME,
        server_time=datetime.now(timezone.utc).isoformat(),  # ✅ UTC timezone-aware
        bot_connected=bot_connected,
        botStatus=BotStatusModel(status=bot_status, message=bot_msg),
        todayPnl=today_pnl,
        pnlPercentage=pnl_pct,
        ltp=ltp,
        lastClose=last_close,
        lastCloseTime=last_close_time,
    )
    return payload


# =========================
# Admin Recovery Endpoints
# =========================
@app.post("/admin/restart_bot", tags=["admin"])
def admin_restart_bot(x_admin_token: str | None = Header(default=None, alias="X-ADMIN-TOKEN")):
    require_admin_token(x_admin_token)

    if bot is None:
        raise HTTPException(status_code=500, detail="bot module not loaded")

    try:
        # stop if exists
        if hasattr(bot, "stop_bot"):
            try:
                bot.stop_bot()
            except Exception:
                pass

        # start thread
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

    def _exit():
        time.sleep(1)
        os._exit(0)

    threading.Thread(target=_exit, daemon=True).start()
    return {"ok": True, "message": "Service restart triggered"}

