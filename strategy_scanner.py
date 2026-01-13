"""
Type F Strategy Scanner
Handles trade logging and Excel file management
"""

import os
from datetime import datetime

# Try to import pandas, if not available use CSV fallback
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    print("⚠️ pandas not installed. Using CSV fallback for logging.")
    PANDAS_AVAILABLE = False
    import csv

# Excel file path
EXCEL_FILE = "Type_F_Trading_Logs.xlsx"

def log_trade_to_excel(trade_record):
    """
    Log trade to Excel/CSV file
    
    Args:
        trade_record: dict with keys: time, symbol, type, entry, exit, pnl, reason
    """
    try:
        # Prepare data
        log_entry = {
            'Date': datetime.now().strftime('%Y-%m-%d'),
            'Time': datetime.now().strftime('%H:%M:%S'),
            'Symbol': trade_record.get('symbol', 'N/A'),
            'Type': trade_record.get('type', 'BUY'),
            'Entry': float(trade_record.get('entry', 0)),
            'Exit': float(trade_record.get('exit', 0)),
            'P&L': float(trade_record.get('pnl', 0)),
            'Reason': trade_record.get('reason', 'Manual'),
            'Entry Time': trade_record.get('time', ''),
            'Exit Time': trade_record.get('exitTime', '')
        }
        
        if PANDAS_AVAILABLE:
            # Use pandas for Excel
            if os.path.exists(EXCEL_FILE):
                df = pd.read_excel(EXCEL_FILE)
                df = pd.concat([df, pd.DataFrame([log_entry])], ignore_index=True)
            else:
                df = pd.DataFrame([log_entry])
            df.to_excel(EXCEL_FILE, index=False)
            print(f"✅ Trade logged to {EXCEL_FILE}")
        else:
            # Fallback: Use CSV
            csv_file = "Type_F_Trading_Logs.csv"
            file_exists = os.path.exists(csv_file)
            with open(csv_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=log_entry.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(log_entry)
            print(f"✅ Trade logged to {csv_file}")
        
    except Exception as e:
        print(f"❌ Error logging trade: {e}")

def get_today_trades():
    """
    Get today's trades from Excel/CSV
    Returns list of trade dicts
    """
    try:
        if PANDAS_AVAILABLE and os.path.exists(EXCEL_FILE):
            df = pd.read_excel(EXCEL_FILE)
            today = datetime.now().strftime('%Y-%m-%d')
            today_df = df[df['Date'] == today]
            return today_df.to_dict('records')
        elif os.path.exists("Type_F_Trading_Logs.csv"):
            # CSV fallback
            trades = []
            today = datetime.now().strftime('%Y-%m-%d')
            with open("Type_F_Trading_Logs.csv", 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('Date') == today:
                        trades.append(row)
            return trades
        return []
    except Exception as e:
        print(f"❌ Error reading trades: {e}")
        return []

def calculate_today_pnl():
    """
    Calculate total P&L for today
    """
    try:
        trades = get_today_trades()
        total_pnl = sum([float(trade.get('P&L', 0)) for trade in trades])
        return total_pnl
    except:
        return 0.0
