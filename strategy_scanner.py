"""
Type F Strategy Scanner
Handles trade logging and Excel file management
"""

import pandas as pd
import os
from datetime import datetime

# Excel file path
EXCEL_FILE = "Type_F_Trading_Logs.xlsx"

def log_trade_to_excel(trade_record):
    """
    Log trade to Excel file
    
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
        
        # Check if file exists
        if os.path.exists(EXCEL_FILE):
            # Read existing data
            df = pd.read_excel(EXCEL_FILE)
            # Append new row
            df = pd.concat([df, pd.DataFrame([log_entry])], ignore_index=True)
        else:
            # Create new DataFrame
            df = pd.DataFrame([log_entry])
        
        # Save to Excel
        df.to_excel(EXCEL_FILE, index=False)
        print(f"✅ Trade logged to {EXCEL_FILE}")
        
    except Exception as e:
        print(f"❌ Error logging to Excel: {e}")

def get_today_trades():
    """
    Get today's trades from Excel
    Returns list of trade dicts
    """
    try:
        if not os.path.exists(EXCEL_FILE):
            return []
        
        df = pd.read_excel(EXCEL_FILE)
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Filter today's trades
        today_df = df[df['Date'] == today]
        
        # Convert to list of dicts
        trades = today_df.to_dict('records')
        
        return trades
        
    except Exception as e:
        print(f"❌ Error reading Excel: {e}")
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
