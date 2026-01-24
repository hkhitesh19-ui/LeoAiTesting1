"""
PHASE 1 — SPOT SIGNAL BRAIN
Authoritative signal source: NIFTY SPOT (1H)
"""

from prototype.spot_signal_contracts import SpotSignal, now_ts

def generate_spot_signal(
    close: float,
    ema20: float,
    rsi19: float,
    supertrend: float,
    supertrend_prev_red: bool
) -> SpotSignal:

    entry_ok = (
        supertrend_prev_red
        and close > supertrend
        and close > ema20
        and rsi19 < 65
    )

    if entry_ok:
        return SpotSignal(
            signal="ENTRY_ARMED",
            reason="ST reversal + close>EMA20 + RSI<65",
            spot_close=float(close),
            ema20=float(ema20),
            rsi19=float(rsi19),
            supertrend=float(supertrend),
            ts=now_ts()
        )

    return SpotSignal(
        signal="WAIT",
        reason="Trend conditions not satisfied",
        spot_close=float(close),
        ema20=float(ema20),
        rsi19=float(rsi19),
        supertrend=float(supertrend),
        ts=now_ts()
    )
