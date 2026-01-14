from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import os
import requests
import threading
from datetime import datetime
from typing import Any, Dict, List

# ============================================================
# ENV
# ============================================================

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# IMPORTANT:
# Telegram polling (commands) causes 409 conflict if multiple instances run.
# Set this env var in Render to disable polling safely:
# DISABLE_TELEGRAM_POLLING=1
DISABLE_TELEGRAM_POLLING = os.getenv("DISABLE_TELEGRAM_POLLING", "0") == "1"

# ============================================================
# SAFE TELEGRAM ALERTS (send-only)
# ============================================================

def send_telegram_alert(message: str) -> bool:
    """
    Send Telegram alert (Markdown supported).
    NEVER raises (always safe).
    """
    try:
        if not TOKEN or not CHAT_ID:
            print("⚠️ Telegram creds missing (TELEGRAM_TOKEN / TELEGRAM_CHAT_ID).")
            return False

        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }

        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            return True

        print("❌ Telegram API error:", r.text)
        return False

    except Exception as e:
        print("❌ Telegram send failed:", e)
        return False


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(title="Type F Trading Bot API", version="1.0")

# CORS allow Netlify
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later set to ["https://leoaitesting1.netlify.app"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# IMPORT BOT DATA SAFELY
# ============================================================

BOT_CONNECTED = False
api = None

# This trade_data is always present (fallback)
trade_data: Dict[str, Any] = {
    "active": False,
    "last_run": None,
    "last_error": None,
    "entry_price": 0.0,
    "sl_price": 0.0,
    "fut_token": None,
    "symbol": "NIFTY FUT",
    "trade_history": [],
}

try:
    # bot.py should expose: trade_data, api
    from bot import trade_data as bot_trade_data, api as bot_api

    # if import works, use live references
    trade_data = bot_trade_data
    api = bot_api
    BOT_CONNECTED = True
    print("✅ bot.py connected: trade_data + api imported")

except Exception as e:
    BOT_CONNECTED = False
    api = None
    trade_data["last_error"] = f"bot.py import failed: {e}"
    print("⚠️ bot.py import failed. API will run in fallback mode.", e)


# ============================================================
# SHOONYA LIVE LTP (SAFE)
# ============================================================

def get_live_ltp() -> float:
    """
    Returns live LTP using Shoonya api.get_quotes().
    Always safe: never raises.
    """
    try:
        if not BOT_CONNECTED or api is None:
            return 0.0

        token = trade_data.get("fut_token")
        if not token:
            return 0.0

        res = api.get_quotes(exchange="NFO", token=str(token))
        if not res:
            return 0.0

        lp = res.get("lp", 0)  # lp is string in API sometimes
        try:
            return float(lp)
        except Exception:
            return 0.0

    except Exception as e:
        # don't crash endpoint
        trade_data["last_error"] = f"LTP fetch error: {e}"
        return 0.0


# ============================================================
# TELEGRAM COMMAND BOT (OPTIONAL)
# ============================================================

def init_telegram_command_bot():
    """
    Optional: starts Telegram polling for /status /stop.
    Disabled by env DISABLE_TELEGRAM_POLLING=1
    """
    if DISABLE_TELEGRAM_POLLING:
        print("✅ Telegram polling disabled via DISABLE_TELEGRAM_POLLING=1")
        return

    if not TOKEN or not CHAT_ID:
        print("⚠️ Telegram command bot disabled (missing creds).")
        return

    try:
        import telebot  # pyTelegramBotAPI

        command_bot = telebot.TeleBot(TOKEN, threaded=False)

        @command_bot.message_handler(commands=["status"])
        def handle_status(message):
            if str(message.chat.id) != str(CHAT_ID):
                command_bot.reply_to(message, "⛔ Unauthorized!")
                return

            active = bool(trade_data.get("active", False))
            entry = float(trade_data.get("entry_price", 0.0) or 0.0)
            sl = float(trade_data.get("sl_price", 0.0) or 0.0)
            ltp = float(get_live_ltp() or 0.0)

            pnl = 0.0
            if active and entry > 0 and ltp > 0:
                pnl = ltp - entry

            msg = "✅ *Bot Status*\n\n"
            msg += f"*Connected:* {'Yes' if BOT_CONNECTED else 'No'}\n"
            msg += f"*Active Trade:* {'Yes' if active else 'No'}\n\n"
            msg += f"*Symbol:* {trade_data.get('symbol', 'NIFTY FUT')}\n"
            msg += f"*Entry:* ₹{entry:,.2f}\n"
            msg += f"*LTP:* ₹{ltp:,.2f}\n"
            msg += f"*SL:* ₹{sl:,.2f}\n"
            msg += f"*PnL:* ₹{pnl:,.2f}\n"

            command_bot.reply_to(message, msg, parse_mode="Markdown")

        @command_bot.message_handler(commands=["stop", "exit", "emergency"])
        def handle_stop(message):
            if str(message.chat.id) != str(CHAT_ID):
                command_bot.reply_to(message, "⛔ Unauthorized!")
                return

            command_bot.reply_to(
                message,
                "🛑 *STOP REQUEST RECEIVED*\n\nBot will terminate now.",
                parse_mode="Markdown",
            )
            send_telegram_alert("🔴 *Bot stop requested from Telegram.*")

            # Terminate container
            import signal
            os.kill(os.getpid(), signal.SIGTERM)

        @command_bot.message_handler(commands=["help"])
        def handle_help(message):
            if str(message.chat.id) != str(CHAT_ID):
                command_bot.reply_to(message, "⛔ Unauthorized!")
                return

            command_bot.reply_to(
                message,
                "🤖 *Commands*\n\n"
                "/status - bot status\n"
                "/stop - terminate bot\n"
                "/help - show help\n",
                parse_mode="Markdown",
            )

        def runner():
            try:
                print("🤖 Telegram command bot polling started")
                send_telegram_alert("🟢 *Render bot online*\n\nTelegram commands active.")
                command_bot.polling(non_stop=True, timeout=60)
            except Exception as e:
                print("⚠️ Telegram polling error:", e)

        t = threading.Thread(target=runner, daemon=True)
        t.start()

    except Exception as e:
        print("⚠️ Telegram command bot init failed:", e)


# Start telegram command bot on startup (optional)
init_telegram_command_bot()


# ============================================================
# ROUTES
# ============================================================

@app.get("/")
async def root():
    return {"ok": True, "message": "Type F Trading Bot API is online"}


@app.get("/health")
async def health():
    return {
        "ok": True,
        "bot_connected": BOT_CONNECTED,
        "active_trade": bool(trade_data.get("active", False)),
        "last_run": trade_data.get("last_run"),
        "last_error": trade_data.get("last_error"),
        "ts": datetime.utcnow().isoformat(),
    }


@app.get("/start")
async def start():
    # (Start handled by bot.py itself; this only confirms API is live)
    return {"ok": True, "message": "Bot start requested / API live"}


@app.get("/get_status")
async def get_status():
    """
    Dashboard endpoint. MUST NEVER CRASH.
    """
    # safe values
    active = bool(trade_data.get("active", False))

    try:
        entry_price = float(trade_data.get("entry_price", 0.0) or 0.0)
    except Exception:
        entry_price = 0.0

    try:
        sl_price = float(trade_data.get("sl_price", 0.0) or 0.0)
    except Exception:
        sl_price = 0.0

    symbol = trade_data.get("symbol", "NIFTY FUT")

    current_ltp = float(get_live_ltp() or 0.0)

    today_pnl = 0.0
    pnl_percentage = 0.0
    if active and entry_price > 0 and current_ltp > 0:
        today_pnl = current_ltp - entry_price
        pnl_percentage = (today_pnl / entry_price) * 100

    # trade history safe list
    history: List[Dict[str, Any]] = []
    try:
        h = trade_data.get("trade_history", [])
        if isinstance(h, list):
            history = h
    except Exception:
        history = []

    return {
        "botStatus": {
            "status": "Active" if active else "Searching",
            "message": "Market Open" if active else "Scanning",
        },
        "todayPnl": round(today_pnl, 2),
        "pnlPercentage": round(pnl_percentage, 3),
        "activeTrade": {
            "symbol": symbol,
            "entry": entry_price,
            "sl": sl_price,
            "ltp": current_ltp,
        },
        "tradeHistory": history,
    }


@app.get("/telegram_test")
async def telegram_test():
    ok = send_telegram_alert("🧪 *Telegram Test*\n\nRender backend can send messages ✅")
    return {"ok": bool(ok), "message": "sent" if ok else "failed"}
