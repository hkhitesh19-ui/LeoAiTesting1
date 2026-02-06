"""
Model E Trading Logic
Volatility-Adjusted Position Sizing (VAPS) with Structural Hedge
"""

import pandas as pd
import pandas_ta as ta

def calculate_model_e_indicators(df_1min):
    """
    1-min data ko 1-hour mein convert karke indicators calculate karta hai.
    
    Args:
        df_1min: DataFrame with columns ['time', 'open', 'high', 'low', 'close', 'volume']
    
    Returns:
        df_1h: DataFrame with 1-hour candles and indicators
    """
    # 1. Resample to 1 Hour
    df_1min['time'] = pd.to_datetime(df_1min['time'])
    df_1h = df_1min.resample('1H', on='time').agg({
        'open': 'first', 
        'high': 'max', 
        'low': 'min', 
        'close': 'last', 
        'volume': 'sum'
    }).dropna()

    # 2. Add Indicators
    # SuperTrend: 21, 1.1
    st = ta.supertrend(df_1h['high'], df_1h['low'], df_1h['close'], length=21, multiplier=1.1)
    df_1h['st_direction'] = st['SUPERTd_21_1.1']  # 1 for Green, -1 for Red
    df_1h['st_line'] = st['SUPERT_21_1.1']

    # RSI: 19
    df_1h['rsi'] = ta.rsi(df_1h['close'], length=19)

    # EMA: 20
    df_1h['ema20'] = ta.ema(df_1h['close'], length=20)

    # ATR: 14
    df_1h['atr'] = ta.atr(df_1h['high'], df_1h['low'], df_1h['close'], length=14)

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
