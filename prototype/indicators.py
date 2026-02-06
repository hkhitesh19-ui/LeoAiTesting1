from __future__ import annotations

import pandas as pd


# =========================
# Core indicator utilities
# =========================

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0)
    down = (-delta).clip(lower=0)

    ma_up = up.ewm(alpha=1 / period, adjust=False).mean()
    ma_down = down.ewm(alpha=1 / period, adjust=False).mean()

    rs = ma_up / (ma_down.replace(0, 1e-9))
    return 100 - (100 / (1 + rs))


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    """
    Returns:
      st_value: pd.Series
      st_dir:   pd.Series (+1 bullish, -1 bearish)

    Required columns: ['high','low','close']
    """
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)

    atr_val = atr(high, low, close, period)

    hl2 = (high + low) / 2.0
    upperband = hl2 + multiplier * atr_val
    lowerband = hl2 - multiplier * atr_val

    st = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)

    st.iloc[0] = upperband.iloc[0]
    direction.iloc[0] = -1

    for i in range(1, len(df)):
        prev_dir = direction.iloc[i - 1]

        cur_ub = upperband.iloc[i]
        cur_lb = lowerband.iloc[i]

        # final upper band
        if (cur_ub < upperband.iloc[i - 1]) or (close.iloc[i - 1] > upperband.iloc[i - 1]):
            final_ub = cur_ub
        else:
            final_ub = upperband.iloc[i - 1]

        # final lower band
        if (cur_lb > lowerband.iloc[i - 1]) or (close.iloc[i - 1] < lowerband.iloc[i - 1]):
            final_lb = cur_lb
        else:
            final_lb = lowerband.iloc[i - 1]

        if prev_dir == -1:
            if close.iloc[i] > final_ub:
                direction.iloc[i] = +1
                st.iloc[i] = final_lb
            else:
                direction.iloc[i] = -1
                st.iloc[i] = final_ub
        else:
            if close.iloc[i] < final_lb:
                direction.iloc[i] = -1
                st.iloc[i] = final_ub
            else:
                direction.iloc[i] = +1
                st.iloc[i] = final_lb

        upperband.iloc[i] = final_ub
        lowerband.iloc[i] = final_lb

    return st, direction


# ============================================
# Backward-compatible wrappers (Hardening)
# ============================================
# Goal: prototype.main_v7 (aur future) kabhi break na ho
# names mismatch se.


# --- Generic wrappers (MOST IMPORTANT) ---

def calc_ema(close: pd.Series, period: int = 20) -> float:
    s = ema(close.astype(float), int(period))
    return float(s.iloc[-1])


def calc_rsi(close: pd.Series, period: int = 14) -> float:
    s = rsi(close.astype(float), int(period))
    return float(s.iloc[-1])


def calc_atr(df: pd.DataFrame, period: int = 14) -> float:
    """
    df requires: high, low, close
    """
    a = atr(
        df["high"].astype(float),
        df["low"].astype(float),
        df["close"].astype(float),
        int(period),
    )
    return float(a.iloc[-1])


# --- Explicit legacy wrappers (keep forever) ---

def calc_ema20(close: pd.Series) -> float:
    return calc_ema(close, 20)


def calc_rsi14(close: pd.Series) -> float:
    return calc_rsi(close, 14)


def calc_atr14(df: pd.DataFrame) -> float:
    return calc_atr(df, 14)


def calc_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    """
    Returns tuple: (st_val_latest, st_dir_latest, st_dir_prev)
    """
    st, direction = supertrend(df, period=int(period), multiplier=float(multiplier))
    st_val = float(st.iloc[-1])
    st_dir = int(direction.iloc[-1])
    st_prev = int(direction.iloc[-2]) if len(direction) >= 2 else st_dir
    return st_val, st_dir, st_prev
