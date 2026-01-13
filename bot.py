"""
Type F Trading Strategy Bot
Main bot file that handles Shoonya login, strategy execution, and trade management
"""

import os
import time
from datetime import datetime, timedelta
import pyotp
import threading

# Try to import NorenRestApiPy, if not available use fallback
try:
    from NorenRestApiPy.NorenApi import NorenApi
    NOREN_AVAILABLE = True
except ImportError:
    print("⚠️ NorenRestApiPy not installed. Installing dynamically...")
    try:
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "NorenRestApiPy==0.0.23"])
        from NorenRestApiPy.NorenApi import NorenApi
        NOREN_AVAILABLE = True
    except Exception as e:
        print(f"❌ Could not install NorenRestApiPy: {e}")
        # Create a dummy class for now
        class NorenApi:
            def __init__(self, *args, **kwargs):
                pass
        NOREN_AVAILABLE = False

# Telegram alert functions will be imported dynamically to avoid circular import
# Initialize with dummy functions
send_trade_entry_alert = lambda *args, **kwargs: None
send_trade_exit_alert = lambda *args, **kwargs: None
send_error_alert = lambda *args, **kwargs: None
emergency_stop_flag = False

def init_telegram_alerts():
    """Initialize Telegram alert functions (called after import)"""
    global send_trade_entry_alert, send_trade_exit_alert, send_error_alert, emergency_stop_flag
    try:
        from api_server import (
            send_trade_entry_alert as _entry,
            send_trade_exit_alert as _exit,
            send_error_alert as _error,
            emergency_stop_flag as _stop
        )
        send_trade_entry_alert = _entry
        send_trade_exit_alert = _exit
        send_error_alert = _error
        emergency_stop_flag = _stop
        print("✅ Telegram alerts initialized")
    except ImportError:
        print("⚠️ Telegram alerts not available")
        # Create dummy functions
        send_trade_entry_alert = lambda *args, **kwargs: None
        send_trade_exit_alert = lambda *args, **kwargs: None
        send_error_alert = lambda *args, **kwargs: None

# ==========================================
# Global Trade Data (Shared with api_server.py)
# ==========================================
trade_data = {
    "active": False,
    "last_run": None,
    "last_error": None,
    "entry_price": 0.0,
    "sl_price": 0.0,
    "target_price": 0.0,
    "fut_token": None,
    "symbol": "NIFTY FUT",
    "entry_time": None,
    "lot_size": 1,
    "trade_history": []
}

# ==========================================
# Shoonya API Configuration
# ==========================================
class ShoonyaApiPy(NorenApi):
    def __init__(self):
        NorenApi.__init__(self, 
            host='https://api.shoonya.com/NorenWClientTP/',
            websocket='wss://api.shoonya.com/NorenWSTP/'
        )

# Initialize API object (will be used by api_server.py)
api = ShoonyaApiPy()

# ==========================================
# Configuration from Environment Variables
# ==========================================
# Support both naming conventions
UID = os.getenv('UID') or os.getenv('SHOONYA_USERID')
PWD = os.getenv('PWD') or os.getenv('SHOONYA_PASSWORD')
TOTP_KEY = os.getenv('TOTP_KEY') or os.getenv('SHOONYA_API_SECRET')
VENDOR_CODE = os.getenv('VENDOR_CODE') or os.getenv('SHOONYA_VENDOR_CODE', 'NA')
APP_KEY = os.getenv('APP_KEY', '')
IMEI = os.getenv('IMEI') or os.getenv('SHOONYA_IMEI', 'abc1234')

# ==========================================
# Trading Parameters
# ==========================================
NIFTY_LOT_SIZE = 25  # 1 lot = 25 qty
RISK_PER_TRADE = 100  # Risk per point (can be adjusted)
TRADE_ACTIVE = False
CURRENT_POSITION = None

# ==========================================
# Shoonya Login Function
# ==========================================
def login_to_shoonya():
    """
    Login to Shoonya API using credentials from environment variables
    Returns True if successful, False otherwise
    """
    global api
    
    try:
        if not all([UID, PWD, TOTP_KEY]):
            print("❌ Missing credentials! Set UID, PWD, TOTP_KEY environment variables")
            trade_data["last_error"] = "Missing credentials"
            return False
        
        # Generate TOTP
        totp = pyotp.TOTP(TOTP_KEY)
        totp_code = totp.now()
        
        print(f"🔐 Logging in to Shoonya with UID: {UID}")
        
        # Login
        ret = api.login(
            userid=UID,
            password=PWD,
            twoFA=totp_code,
            vendor_code=VENDOR_CODE,
            api_secret=APP_KEY,
            imei=IMEI
        )
        
        if ret and ret.get('stat') == 'Ok':
            print(f"✅ Shoonya login successful! Session: {ret.get('susertoken', 'N/A')[:20]}...")
            trade_data["last_error"] = None
            return True
        else:
            error_msg = ret.get('emsg', 'Unknown error') if ret else 'No response'
            print(f"❌ Shoonya login failed: {error_msg}")
            trade_data["last_error"] = f"Login failed: {error_msg}"
            send_error_alert(f"Shoonya login failed: {error_msg}")
            return False
            
    except Exception as e:
        print(f"❌ Login exception: {e}")
        trade_data["last_error"] = f"Login exception: {str(e)}"
        send_error_alert(f"Login exception: {str(e)}")
        return False

# ==========================================
# Get NIFTY Future Token
# ==========================================
def get_nifty_fut_token():
    """
    Get the current month NIFTY Future token
    Returns token as string or None
    """
    try:
        # Search for NIFTY futures
        ret = api.searchscrip(exchange='NFO', searchtext='NIFTY')
        
        if not ret or 'values' not in ret:
            print("❌ Failed to search NIFTY futures")
            return None
        
        # Find current month future (usually first in list)
        futures = ret['values']
        
        for fut in futures:
            symbol = fut.get('tsym', '')
            # Look for pattern like "NIFTY26JAN" or "NIFTY26FEB" (monthly futures)
            if 'NIFTY' in symbol and len(symbol) <= 15 and 'CE' not in symbol and 'PE' not in symbol:
                token = fut.get('token')
                print(f"✅ Found NIFTY Future: {symbol}, Token: {token}")
                trade_data["symbol"] = symbol
                trade_data["fut_token"] = token
                return token
        
        print("⚠️ Could not find current month NIFTY future")
        return None
        
    except Exception as e:
        print(f"❌ Error fetching NIFTY token: {e}")
        return None

# ==========================================
# Get Live Market Price
# ==========================================
def get_live_ltp(token):
    """
    Get live LTP for given token
    """
    try:
        if not token:
            return 0.0
        
        res = api.get_quotes(exchange='NFO', token=str(token))
        
        if res and 'lp' in res:
            ltp = float(res['lp'])
            return ltp
        else:
            print(f"⚠️ LTP not found in response")
            return 0.0
            
    except Exception as e:
        print(f"❌ Error fetching LTP: {e}")
        return 0.0

# ==========================================
# Type F Strategy Scanner
# ==========================================
def check_type_f_signal():
    """
    Check if Type F pattern is forming
    
    Type F Pattern (Simplified):
    - Price breaks below support
    - Forms a reversal candle
    - Entry on bounce with tight stop loss
    
    Returns: dict with signal info or None
    """
    try:
        token = trade_data.get("fut_token")
        if not token:
            return None
        
        # Get historical data (last 5 candles)
        # Note: You'll need to implement proper historical data fetching
        # For now, using live LTP as placeholder
        
        ltp = get_live_ltp(token)
        
        if ltp == 0:
            return None
        
        # Placeholder logic (Replace with your actual Type F strategy)
        # This is just a demo - implement your real strategy here
        
        # Example: Simple entry logic (for testing only)
        # In production, use proper technical indicators
        
        # For now, return None (no signal)
        # You can modify this to test with mock signals
        
        return None
        
    except Exception as e:
        print(f"❌ Strategy error: {e}")
        return None

# ==========================================
# Place Order
# ==========================================
def place_order(symbol, token, qty, price, transaction_type='B', order_type='MKT'):
    """
    Place order on Shoonya
    
    Args:
        symbol: Trading symbol
        token: Instrument token
        qty: Quantity
        price: Price (for limit orders)
        transaction_type: 'B' for Buy, 'S' for Sell
        order_type: 'MKT' or 'LMT'
    """
    try:
        order = api.place_order(
            buy_or_sell=transaction_type,
            product_type='M',  # MIS (Intraday)
            exchange='NFO',
            tradingsymbol=symbol,
            quantity=qty,
            discloseqty=0,
            price_type=order_type,
            price=price if order_type == 'LMT' else 0,
            trigger_price=None,
            retention='DAY',
            remarks='Type_F_Bot'
        )
        
        if order and order.get('stat') == 'Ok':
            order_id = order.get('norenordno')
            print(f"✅ Order placed successfully! Order ID: {order_id}")
            return order_id
        else:
            error_msg = order.get('emsg', 'Unknown error') if order else 'No response'
            print(f"❌ Order failed: {error_msg}")
            send_error_alert(f"Order placement failed: {error_msg}")
            return None
            
    except Exception as e:
        print(f"❌ Order exception: {e}")
        send_error_alert(f"Order exception: {str(e)}")
        return None

# ==========================================
# Trade Management
# ==========================================
def enter_trade(signal):
    """
    Enter a trade based on signal
    """
    global TRADE_ACTIVE, CURRENT_POSITION
    
    try:
        symbol = signal['symbol']
        token = signal['token']
        entry = signal['entry']
        sl = signal['sl']
        target = signal.get('target', entry + (entry - sl) * 2)  # 1:2 RR
        
        # Calculate quantity based on risk
        qty = NIFTY_LOT_SIZE * trade_data.get("lot_size", 1)
        
        # Place order
        order_id = place_order(symbol, token, qty, entry, 'B', 'MKT')
        
        if order_id:
            # Update trade data
            trade_data["active"] = True
            trade_data["entry_price"] = entry
            trade_data["sl_price"] = sl
            trade_data["target_price"] = target
            trade_data["entry_time"] = datetime.now().isoformat()
            
            TRADE_ACTIVE = True
            CURRENT_POSITION = {
                'order_id': order_id,
                'symbol': symbol,
                'token': token,
                'qty': qty,
                'entry': entry,
                'sl': sl,
                'target': target
            }
            
            print(f"🚀 Trade entered: {symbol} @ ₹{entry:,.2f}")
            
            # Send Telegram alert
            send_trade_entry_alert(
                symbol=symbol,
                price=entry,
                sl=sl,
                strategy="Type F"
            )
            
            return True
    
    except Exception as e:
        print(f"❌ Error entering trade: {e}")
        send_error_alert(f"Trade entry error: {str(e)}")
        return False

def exit_trade(reason="Manual Exit", exit_price=None):
    """
    Exit current trade
    """
    global TRADE_ACTIVE, CURRENT_POSITION
    
    try:
        if not TRADE_ACTIVE or not CURRENT_POSITION:
            print("⚠️ No active trade to exit")
            return False
        
        symbol = CURRENT_POSITION['symbol']
        token = CURRENT_POSITION['token']
        qty = CURRENT_POSITION['qty']
        entry = CURRENT_POSITION['entry']
        
        # Get current price if not provided
        if not exit_price:
            exit_price = get_live_ltp(token)
        
        # Place exit order
        order_id = place_order(symbol, token, qty, exit_price, 'S', 'MKT')
        
        if order_id:
            # Calculate P&L
            pnl = (exit_price - entry) * qty
            
            # Update trade data
            trade_data["active"] = False
            
            # Add to history
            trade_record = {
                'time': trade_data.get("entry_time"),
                'symbol': symbol,
                'type': 'BUY',
                'entry': entry,
                'exit': exit_price,
                'pnl': pnl,
                'reason': reason,
                'exitTime': datetime.now().isoformat()
            }
            
            trade_data["trade_history"].insert(0, trade_record)
            
            # Keep only last 50 trades in memory
            if len(trade_data["trade_history"]) > 50:
                trade_data["trade_history"] = trade_data["trade_history"][:50]
            
            TRADE_ACTIVE = False
            CURRENT_POSITION = None
            
            print(f"🏁 Trade exited: {symbol} @ ₹{exit_price:,.2f} | P&L: ₹{pnl:,.2f}")
            
            # Send Telegram alert
            send_trade_exit_alert(
                symbol=symbol,
                entry=entry,
                exit=exit_price,
                pnl=pnl,
                reason=reason
            )
            
            # Log to Excel (if strategy_scanner exists)
            try:
                from strategy_scanner import log_trade_to_excel
                log_trade_to_excel(trade_record)
            except:
                pass
            
            return True
    
    except Exception as e:
        print(f"❌ Error exiting trade: {e}")
        send_error_alert(f"Trade exit error: {str(e)}")
        return False

def monitor_trade():
    """
    Monitor active trade for SL/Target hit
    """
    global TRADE_ACTIVE, CURRENT_POSITION
    
    try:
        if not TRADE_ACTIVE or not CURRENT_POSITION:
            return
        
        token = CURRENT_POSITION['token']
        sl = CURRENT_POSITION['sl']
        target = CURRENT_POSITION['target']
        
        # Get current price
        ltp = get_live_ltp(token)
        
        if ltp == 0:
            return
        
        # Check Stop Loss
        if ltp <= sl:
            print(f"🛑 Stop Loss Hit! LTP: ₹{ltp:,.2f}")
            exit_trade(reason="Stop Loss Hit", exit_price=ltp)
        
        # Check Target
        elif ltp >= target:
            print(f"🎯 Target Hit! LTP: ₹{ltp:,.2f}")
            exit_trade(reason="Target Hit", exit_price=ltp)
        
    except Exception as e:
        print(f"❌ Error monitoring trade: {e}")

# ==========================================
# Main Bot Loop
# ==========================================
def bot_loop():
    """
    Main trading bot loop
    Runs continuously during market hours
    """
    global emergency_stop_flag
    
    print("🤖 Type F Trading Bot Started")
    print("=" * 50)
    
    # Initialize Telegram alerts
    init_telegram_alerts()
    
    # Login to Shoonya
    if not login_to_shoonya():
        print("❌ Bot cannot start without valid login")
        return
    
    # Get NIFTY Future token
    token = get_nifty_fut_token()
    if not token:
        print("❌ Bot cannot start without NIFTY token")
        return
    
    print("✅ Bot initialization complete")
    print("🔍 Starting strategy scanner...")
    print("=" * 50)
    
    # Main loop
    while True:
        try:
            # Check for emergency stop
            if emergency_stop_flag:
                print("🛑 Emergency stop received!")
                if TRADE_ACTIVE:
                    exit_trade(reason="Emergency Stop")
                break
            
            trade_data["last_run"] = datetime.now().isoformat()
            
            # If trade is active, monitor it
            if TRADE_ACTIVE:
                monitor_trade()
            else:
                # Scan for new signals
                signal = check_type_f_signal()
                
                if signal:
                    print(f"📊 Type F Signal detected!")
                    enter_trade(signal)
            
            # Sleep for 5 seconds before next iteration
            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\n⚠️ Bot stopped by user")
            if TRADE_ACTIVE:
                print("⚠️ Trade still active! Exiting...")
                exit_trade(reason="Manual Stop")
            break
            
        except Exception as e:
            print(f"❌ Bot loop error: {e}")
            trade_data["last_error"] = str(e)
            send_error_alert(f"Bot loop error: {str(e)}")
            time.sleep(10)  # Wait before retrying
    
    print("🤖 Bot stopped")

# ==========================================
# Start Bot in Background Thread
# ==========================================
def start_bot():
    """
    Start the bot in a background thread
    """
    bot_thread = threading.Thread(target=bot_loop, daemon=True)
    bot_thread.start()
    print("✅ Bot thread started")

# ==========================================
# Auto-start when module is imported
# ==========================================
if __name__ == "__main__":
    # If running directly, start bot
    bot_loop()
else:
    # If imported by api_server, start in background
    start_bot()
