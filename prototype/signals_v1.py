from __future__ import annotations

from prototype.indicator_contracts import IndicatorPack
from prototype.signal_contracts import SignalPack


def generate_signal(ind: IndicatorPack) -> SignalPack:
    """
    SIGNAL RULES V1 (simple + deterministic):
    - CALL if close > EMA20 AND RSI > 55
    - PUT if close < EMA20 AND RSI < 45
    - else NONE
    """

    close = float(ind.close)
    ema20 = float(ind.ema_20)
    rsi14 = float(ind.rsi_14)

    if close > ema20 and rsi14 > 55:
        decision = "CALL"
        reason = "close>ema20 AND rsi>55"
    elif close < ema20 and rsi14 < 45:
        decision = "PUT"
        reason = "close<ema20 AND rsi<45"
    else:
        decision = "NONE"
        reason = "no edge"

    pack = SignalPack(
        decision=decision,
        reason=reason,
        close=close,
        meta={
            "ema20": ema20,
            "rsi14": rsi14,
        },
    )

    # HARD CONTRACT checks
    assert pack.decision in ("CALL", "PUT", "NONE")
    assert pack.close is not None

    return pack