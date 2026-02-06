"""
Model E Trading Logic
Volatility-Adjusted Position Sizing (VAPS) with Structural Hedge
Custom manual indicators (no pandas-ta dependency)
"""

import pandas as pd
import numpy as np

def calculate_model_e_indicators(df_1min):
    """
    1-min data ko 1-hour mein convert karke indicators calculate karta hai.
    Manual implementation - no pandas-ta dependency for faster builds.
    
    Args:
        df_1min: DataFrame with columns ['time', 'open', 'high', 'low', 'close', 'volume']
    
    Returns:
        df_1h: DataFrame with 1-hour candles and indicators
    """
    # Resample to 1 Hour
    df_1min['time'] = pd.to_datetime(df_1min['time'])
    df_1h = df_1min.resample('1H', on='time').agg({
        'open': 'first', 
        'high': 'max', 
        'low': 'min', 
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    # RSI (Period 19)
    delta = df_1h['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=19).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=19).mean()
    rs = gain / loss
    df_1h['rsi'] = 100 - (100 / (1 + rs))

    # EMA (Period 20)
    df_1h['ema20'] = df_1h['close'].ewm(span=20, adjust=False).mean()

    # ATR (Period 14) for SuperTrend
    high_low = df_1h['high'] - df_1h['low']
    high_cp = np.abs(df_1h['high'] - df_1h['close'].shift())
    low_cp = np.abs(df_1h['low'] - df_1h['close'].shift())
    df_1h['tr'] = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    df_1h['atr'] = df_1h['tr'].rolling(window=14).mean()

    # SuperTrend (21, 1.1)
    # Note: Simplified manual implementation for production stability
    multiplier = 1.1
    df_1h['upperband'] = ((df_1h['high'] + df_1h['low']) / 2) + (multiplier * df_1h['atr'])
    df_1h['lowerband'] = ((df_1h['high'] + df_1h['low']) / 2) - (multiplier * df_1h['atr'])
    
    # Logic for trend direction (simplified for initial check)
    df_1h['st_direction'] = 1  # Simplified for initial check
    df_1h['st_line'] = df_1h['lowerband']  # Simplified

    return df_1h

def get_vaps_lots(current_vix, net_equity):
    """
    Volatility Adjusted Position Sizing Logic
    
    Args:
        current_vix: Current VIX value
        net_equity: Net equity/capital available
    
    Returns:
        lots: Number of lots to trade (0 if no trade)
    """
    gear = 0
    if current_vix < 14:
        gear = 3
    elif 14 <= current_vix < 16:
        gear = 2
    elif 16 <= current_vix <= 18:
        gear = 0  # No Trade
    elif current_vix > 18:
        gear = 1

    if gear == 0:
        return 0
    
    lots = round((net_equity / 625000) * gear)
    return max(0, lots)

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
