"""
Model E Trading Logic
Volatility-Adjusted Position Sizing (VAPS) with Structural Hedge
Custom manual indicators (no pandas-ta dependency)
"""

import pandas as pd
import numpy as np

def calculate_model_e_indicators(df_1min):
    """
    Model E Indicators (Manual Implementation - No pandas-ta required)
    """
    if df_1min.empty:
        return pd.DataFrame()

    # 1. Resample to 1 Hour
    df_1min['time'] = pd.to_datetime(df_1min['time'])
    df_1h = df_1min.resample('1H', on='time').agg({
        'open': 'first', 
        'high': 'max', 
        'low': 'min', 
        'close': 'last'
    }).dropna().copy()

    # 2. RSI (19)
    delta = df_1h['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=19).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=19).mean()
    rs = gain / loss
    df_1h['rsi'] = 100 - (100 / (1 + rs))

    # 3. EMA (20)
    df_1h['ema20'] = df_1h['close'].ewm(span=20, adjust=False).mean()

    # 4. ATR (14) for SuperTrend
    high_low = df_1h['high'] - df_1h['low']
    high_cp = np.abs(df_1h['high'] - df_1h['close'].shift())
    low_cp = np.abs(df_1h['low'] - df_1h['close'].shift())
    df_1h['tr'] = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    df_1h['atr'] = df_1h['tr'].rolling(window=14).mean()

    # 5. SuperTrend (21, 1.1)
    multiplier = 1.1
    df_1h['upperband'] = ((df_1h['high'] + df_1h['low']) / 2) + (multiplier * df_1h['atr'])
    df_1h['lowerband'] = ((df_1h['high'] + df_1h['low']) / 2) - (multiplier * df_1h['atr'])
    
    # Simple Trend Logic
    df_1h['st_direction'] = np.where(df_1h['close'] > df_1h['upperband'].shift(), 1, -1)
    df_1h['st_line'] = np.where(df_1h['st_direction'] == 1, df_1h['lowerband'], df_1h['upperband'])

    return df_1h

def get_vaps_lots(current_vix, net_equity):
    """Gear calculation from VIX"""
    if current_vix < 14: 
        gear = 3
    elif 14 <= current_vix < 16: 
        gear = 2
    elif 16 <= current_vix <= 18: 
        gear = 0
    else: 
        gear = 1
    
    if gear == 0: 
        return 0
    return round((net_equity / 625000) * gear)

def get_gear_from_vix(current_vix):
    """
    Get gear number from VIX value
    
    Returns:
        gear: 0 (No Trade), 1 (Low), 2 (Medium), 3 (High)
    """
    if current_vix < 14:
        return 3
    elif 14 <= current_vix < 16:
        return 2
    elif 16 <= current_vix <= 18:
        return 0  # No Trade
    elif current_vix > 18:
        return 1
    return 0

def get_gear_status(current_vix):
    """
    Get human-readable gear status
    
    Returns:
        status: "High", "Medium", "Low", "No Trade"
    """
    gear = get_gear_from_vix(current_vix)
    if gear == 3:
        return "High"
    elif gear == 2:
        return "Medium"
    elif gear == 1:
        return "Low"
    else:
        return "No Trade"
