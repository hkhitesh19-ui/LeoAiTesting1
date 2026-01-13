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

# Render ke Environment Variables se values uthayega
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Emergency Stop Bot (Telegram se bot control karne ke liye)
emergency_stop_flag = False

if TOKEN and CHAT_ID:
    try:
        bot = telebot.TeleBot(TOKEN, threaded=False)
        
        @bot.message_handler(commands=['stop', 'exit', 'emergency'])
        def handle_emergency_stop(message):
            """Emergency Stop: Telegram se bot ko turant band kar dega"""
            global emergency_stop_flag
            
            # Security: Sirf authorized user hi stop kar sakta hai
            if str(message.chat.id) == str(CHAT_ID):
                emergency_stop_flag = True
                bot.reply_to(message, 
                    "🛑 *EMERGENCY STOP RECEIVED!*\n\n"
                    "⚠️ Exiting all positions...\n"
                    "⚠️ Shutting down bot...\n\n"
                    "_This action cannot be undone._",
                    parse_mode="Markdown"
                )
                
                send_telegram_alert("🔴 *EMERGENCY SHUTDOWN INITIATED*\n\nBot is stopping now!")
                
                # Yahan aapka exit logic aayega
                # Example: close_all_positions()
                # Example: cancel_all_orders()
                
                # Bot process ko kill kar dega (production mein use carefully)
                import signal
                os.kill(os.getpid(), signal.SIGTERM)
            else:
                bot.reply_to(message, "⛔ Unauthorized! You are not allowed to control this bot.")
        
        @bot.message_handler(commands=['status'])
        def handle_status(message):
            """Status Check: Bot ka current status check karne ke liye"""
            if str(message.chat.id) == str(CHAT_ID):
                # Get live data
                active = trade_data.get("active", False)
                entry = float(trade_data.get("entry_price", 0.0) or 0.0)
                sl = float(trade_data.get("sl_price", 0.0) or 0.0)
                ltp = get_live_ltp()
                
                # Calculate P&L
                pnl = 0.0
                if active and entry > 0 and ltp > 0:
                    pnl = ltp - entry
                
                status_text = "✅ *Bot Status: RUNNING*\n\n"
                
                if active and entry > 0:
                    status_text += f"📊 *Active Trade*\n"
                    status_text += f"Symbol: {trade_data.get('symbol', 'NIFTY FUT')}\n"
                    status_text += f"Entry: ₹{entry:,.2f}\n"
                    status_text += f"LTP: ₹{ltp:,.2f}\n"
                    status_text += f"SL: ₹{sl:,.2f}\n"
                    status_text += f"P&L: ₹{pnl:,.2f}\n\n"
                else:
                    status_text += "📊 Active Trades: 0\n"
                    status_text += "💰 Today's P&L: ₹0.00\n\n"
                
                status_text += "🕐 Server: Online\n"
                status_text += f"🔗 Bot Connected: {'Yes' if BOT_CONNECTED else 'No'}\n\n"
                status_text += "_Use /stop for emergency shutdown_"
                
                bot.reply_to(message, status_text, parse_mode="Markdown")
            else:
                bot.reply_to(message, "⛔ Unauthorized!")
        
        @bot.message_handler(commands=['help'])
        def handle_help(message):
            """Help: Available commands"""
            if str(message.chat.id) == str(CHAT_ID):
                bot.reply_to(message,
                    "🤖 *Type F Bot Commands*\n\n"
                    "/status - Check bot status\n"
                    "/stop - Emergency shutdown\n"
                    "/exit - Same as /stop\n"
                    "/emergency - Same as /stop\n"
                    "/help - Show this message\n\n"
                    "_Bot is actively monitoring markets_",
                    parse_mode="Markdown"
                )
        
        # Start bot polling in background thread
        def start_telegram_bot():
            try:
                print("🤖 Telegram Emergency Stop Bot started!")
                send_telegram_alert("🟢 *Bot is now ONLINE!*\n\n_Emergency stop commands are active_")
                bot.polling(non_stop=True, timeout=60)
            except Exception as e:
                print(f"⚠️ Telegram bot error: {e}")
        
        # Start in background thread so it doesn't block FastAPI
        telegram_thread = threading.Thread(target=start_telegram_bot, daemon=True)
        telegram_thread.start()
        
    except Exception as e:
        print(f"⚠️ Failed to initialize Telegram bot: {e}")
        bot = None
else:
    print("⚠️ Telegram credentials not set. Emergency stop feature disabled.")
    bot = None

def send_telegram_alert(message):
    """
    Telegram par alert bhejne ka function
    
    Args:
        message (str): The message to send (supports Markdown formatting)
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    if not TOKEN or not CHAT_ID:
        print("⚠️ Telegram Credentials missing! Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID")
        return False
        
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"  # Isse text bold/italic dikhega
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Telegram alert sent: {message[:50]}...")
            return True
        else:
            print(f"❌ Telegram Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Failed to send Telegram alert: {e}")
        return False

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
    entry_price = float(trade_data.get("entry_price", 0.0) or 0.0)
    
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
        
        if res and 'lp' in res:
            ltp = float(res['lp'])
            print(f"✅ Live LTP fetched: ₹{ltp:,.2f}")
            return ltp
        else:
            print(f"⚠️ LTP not found in response: {res}")
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
    entry_price = float(trade_data.get("entry_price", 0.0) or 0.0)
    sl_price = float(trade_data.get("sl_price", 0.0) or 0.0)
    
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
            "ltp": current_ltp  # ✅ Now showing live LTP!
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
