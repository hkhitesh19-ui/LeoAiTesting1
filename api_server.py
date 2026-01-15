from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os

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
            "activeTrade": {
    "symbol": "NIFTY FUT",
    "entry": float(trade_data.get("entry_price", 0.0)),
    "sl": float(trade_data.get("sl_price", 0.0)),
    "ltp": float(trade_data.get("current_ltp") or 0.0),
    "close": float(trade_data.get("last_close") or 0.0),
    "display_ltp": float(trade_data.get("current_ltp") or trade_data.get("last_close") or 0.0)
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
    "entry": float(trade_data.get("entry_price", 0.0)),
    "sl": float(trade_data.get("sl_price", 0.0)),
    "ltp": float(trade_data.get("current_ltp") or 0.0),
    "close": float(trade_data.get("last_close") or 0.0),
    "display_ltp": float(trade_data.get("current_ltp") or trade_data.get("last_close") or 0.0)
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
        print(f"⚠️ shutdown_event error: {e}")


