from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from datetime import datetime
import threading
import telebot  # pip install pyTelegramBotAPI

# ==========================================
# Telegram Alert System
# ==========================================

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Emergency stop flag
emergency_stop_flag = False

def send_telegram_alert(message: str) -> bool:
    """Send alert to Telegram (Markdown supported)."""
    if not TOKEN or not CHAT_ID:
        print("⚠️ Telegram Credentials missing! Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID")
        return False

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}

    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            return True
        else:
            print("❌ Telegram Error:", r.text)
            return False
    except Exception as e:
        print("❌ Telegram send failed:", e)
        return False


def send_trade_entry_alert(symbol, price, sl, strategy="Type F"):
    msg = f"""🚀 *STRATEGY ALERT: ENTRY*

*Strategy:* {strategy}
*Symbol:* {symbol}
*Entry Price:* ₹{price:,.2f}
*Stop Loss:* ₹{sl:,.2f}

_Time:_ {datetime.now().strftime('%I:%M:%S %p')}
"""
    return send_telegram_alert(msg)


def send_trade_exit_alert(symbol, entry, exit_price, pnl, reason="Exit"):
    pnl_emoji = "✅" if pnl >= 0 else "❌"
    msg = f"""{pnl_emoji} *STRATEGY ALERT: EXIT*

*Symbol:* {symbol}
*Entry:* ₹{entry:,.2f}
*Exit:* ₹{exit_price:,.2f}
*P&L:* ₹{pnl:,.2f}
*Reason:* {reason}

_Time:_ {datetime.now().strftime('%I:%M:%S %p')}
"""
    return send_telegram_alert(msg)


def send_error_alert(error_message: str):
    msg = f"""🔴 *BOT ERROR ALERT*

*Error:* {error_message}
*Time:* {datetime.now().strftime('%I:%M:%S %p')}

_Please check the logs immediately!_
"""
    return send_telegram_alert(msg)


# ==========================================
# FastAPI App
# ==========================================

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later you can restrict to netlify domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# Import from bot.py
# ==========================================

BOT_CONNECTED = False

try:
    # bot.py should define trade_data and api object
    from bot import trade_data, api
    BOT_CONNECTED = True
    print("✅ Successfully imported trade_data and api from bot.py")
except Exception as e:
    print("⚠️ bot.py import failed. Using mock trade_data.", e)
    trade_data = {
        "active": False,
        "last_run": None,
        "last_error": None,
        "entry_price": 0.0,
        "sl_price": 0.0,
        "fut_token": None,
        "symbol": "NIFTY FUT",
        "trade_history": [],
    }
    api = None
    BOT_CONNECTED = False


# ==========================================
# Telegram Command Bot (Optional)
# ==========================================

bot = None

if TOKEN and CHAT_ID:
    try:
        bot = telebot.TeleBot(TOKEN, threaded=False)

        @bot.message_handler(commands=["stop", "exit", "emergency"])
        def handle_emergency_stop(message):
            global emergency_stop_flag
            if str(message.chat.id) != str(CHAT_ID):
                bot.reply_to(message, "⛔ Unauthorized!")
                return

            emergency_stop_flag = True
            bot.reply_to(
                message,
                "🛑 *EMERGENCY STOP RECEIVED!*\n\n"
                "⚠️ Shutting down bot...\n\n"
                "_This action cannot be undone._",
                parse_mode="Markdown",
            )
            send_telegram_alert("🔴 *EMERGENCY SHUTDOWN INITIATED*\n\nBot is stopping now!")

            import signal
            os.kill(os.getpid(), signal.SIGTERM)

        @bot.message_handler(commands=["status"])
        def handle_status(message):
            if str(message.chat.id) != str(CHAT_ID):
                bot.reply_to(message, "⛔ Unauthorized!")
                return

            active = bool(trade_data.get("active", False))
            entry = float(trade_data.get("entry_price", 0.0) or 0.0)
            sl = float(trade_data.get("sl_price", 0.0) or 0.0)
            ltp = get_live_ltp()

            pnl = 0.0
            if active and entry > 0 and ltp > 0:
                pnl = ltp - entry

            text = "✅ *Bot Status: RUNNING*\n\n"
            if active and entry > 0:
                text += "📊 *Active Trade*\n"
                text += f"Symbol: {trade_data.get('symbol','NIFTY FUT')}\n"
                text += f"Entry: ₹{entry:,.2f}\n"
                text += f"LTP: ₹{ltp:,.2f}\n"
                text += f"SL: ₹{sl:,.2f}\n"
                text += f"P&L: ₹{pnl:,.2f}\n\n"
            else:
                text += "📊 Active Trades: 0\n"
                text += "💰 Today's P&L: ₹0.00\n\n"

            text += "🕐 Server: Online\n"
            text += f"🔗 Bot Connected: {'Yes' if BOT_CONNECTED else 'No'}\n\n"
            text += "_Use /stop for emergency shutdown_"

            bot.reply_to(message, text, parse_mode="Markdown")

        @bot.message_handler(commands=["help"])
        def handle_help(message):
            if str(message.chat.id) != str(CHAT_ID):
                bot.reply_to(message, "⛔ Unauthorized!")
                return

            bot.reply_to(
                message,
                "🤖 *Type F Bot Commands*\n\n"
                "/status - Check bot status\n"
                "/stop - Emergency shutdown\n"
                "/exit - Same as /stop\n"
                "/emergency - Same as /stop\n"
                "/help - Show this message\n",
                parse_mode="Markdown",
            )

        def start_telegram_bot():
            try:
                print("🤖 Telegram command bot started!")
                send_telegram_alert("🟢 *Bot is now ONLINE!*\n\nTelegram commands active: /status /stop")
                bot.polling(non_stop=True, timeout=60)
            except Exception as e:
                print("⚠️ Telegram bot error:", e)

        telegram_thread = threading.Thread(target=start_telegram_bot, daemon=True)
        telegram_thread.start()

    except Exception as e:
        print("⚠️ Failed to initialize Telegram bot:", e)
        bot = None
else:
    print("⚠️ Telegram credentials not set. Telegram commands disabled.")
    bot = None


# ==========================================
# Helper: Live LTP
# ==========================================

def get_live_ltp() -> float:
    """
    Fetch live LTP from Shoonya API using FUT token stored in trade_data.
    Returns 0.0 if not available.
    """
    try:
        if not BOT_CONNECTED or api is None:
            return 0.0

        token = trade_data.get("fut_token")
        if not token:
            return 0.0

        res = api.get_quotes(exchange="NFO", token=str(token))
        if res and "lp" in res:
            return float(res.get("lp", 0) or 0.0)

        return 0.0
    except Exception as e:
        print("❌ LTP fetch error:", e)
        return 0.0


# ==========================================
# Routes
# ==========================================

@app.get("/")
async def root():
    return {"message": "Type F Trading Bot API", "status": "online"}


@app.get("/start")
async def start_bot():
    """
    Start bot is handled in bot.py thread in your system.
    This endpoint just confirms server is running.
    """
    return {
        "ok": True,
        "message": "Bot started",
        "bot_connected": BOT_CONNECTED,
        "status": "running" if trade_data.get("active") else "scanning",
    }


@app.get("/health")
async def health():
    active = bool(trade_data.get("active", False))
    entry_price = float(trade_data.get("entry_price", 0.0) or 0.0)

    return {
        "ok": True,
        "running": active,
        "bot_connected": BOT_CONNECTED,
        "last_run": trade_data.get("last_run"),
        "last_error": trade_data.get("last_error"),
        "has_active_trade": active and entry_price > 0,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/get_status")
async def get_status():
    """
    Dashboard endpoint.
    MUST NEVER CRASH.
    """
    # safe defaults
    active = bool(trade_data.get("active", False))
    entry_price = float(trade_data.get("entry_price", 0.0) or 0.0)
    sl_price = float(trade_data.get("sl_price", 0.0) or 0.0)
    symbol = trade_data.get("symbol", "NIFTY FUT")

    current_ltp = 0.0
    try:
        current_ltp = float(get_live_ltp() or 0.0)
    except Exception:
        current_ltp = 0.0

    # pnl calc
    today_pnl = 0.0
    pnl_percentage = 0.0
    if active and entry_price > 0 and current_ltp > 0:
        today_pnl = current_ltp - entry_price
        pnl_percentage = ((current_ltp - entry_price) / entry_price) * 100

    # trade history safe
    try:
        trade_history = trade_data.get("trade_history", [])
        if trade_history is None:
            trade_history = []
    except Exception:
        trade_history = []

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
        "tradeHistory": trade_history,
    }


@app.get("/telegram_test")
async def telegram_test():
    ok = send_telegram_alert("🧪 *Telegram Test*\\n\\nTelegram integration is working ✅")
    return {"ok": bool(ok), "message": "Test alert sent" if ok else "Failed to send test alert"}
