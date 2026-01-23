from __future__ import annotations

from typing import List, Dict, Any
from prototype.contracts import CandlePack
from prototype.indicator_contracts import IndicatorPack


def _get_close_series(pack: CandlePack) -> List[float]:
    """
    Shoonya candle rows: latest first
    We reverse to oldest->newest for indicator calculations.
    """
    rows = pack.rows[::-1]
    closes: List[float] = []
    for r in rows:
        try:
            closes.append(float(r.get("intc") or 0.0))
        except Exception:
            closes.append(0.0)
    return closes


def ema(series: List[float], period: int) -> float:
    if not series or period <= 0:
        return 0.0
    k = 2.0 / (period + 1.0)
    e = series[0]
    for x in series[1:]:
        e = (x * k) + (e * (1.0 - k))
    return float(e)


def rsi(series: List[float], period: int = 14) -> float:
    if len(series) < period + 1:
        return 0.0

    gains = 0.0
    losses = 0.0

    for i in range(1, period + 1):
        diff = series[i] - series[i - 1]
        if diff >= 0:
            gains += diff
        else:
            losses += abs(diff)

    avg_gain = gains / period
    avg_loss = losses / period

    for i in range(period + 1, len(series)):
        diff = series[i] - series[i - 1]
        gain = diff if diff > 0 else 0.0
        loss = abs(diff) if diff < 0 else 0.0
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - (100.0 / (1.0 + rs)))


def adx_stub(series: List[float], period: int = 14) -> float:
    """
    ADX needs high/low series too.
    For now: stubbed value (0.0) but STRICT field always present.
    Next version will compute full ADX using into/inth/intl.
    """
    return 0.0


def compute_indicators(pack: CandlePack) -> IndicatorPack:
    closes = _get_close_series(pack)
    close_last = float(closes[-1]) if closes else float(pack.close)

    out = IndicatorPack(
        close=close_last,
        ema_20=ema(closes, 20),
        ema_50=ema(closes, 50),
        ema_200=ema(closes, 200),
        rsi_14=rsi(closes, 14),
        adx_14=adx_stub(closes, 14),
        meta={
            "rows": len(pack.rows),
            "source": "CandlePack",
            "note": "ADX stubbed in v1 (will implement full in v2)",
        },
    )

    # HARD CONTRACT (no None)
    assert out.close is not None
    assert out.ema_20 is not None
    assert out.ema_50 is not None
    assert out.ema_200 is not None
    assert out.rsi_14 is not None
    assert out.adx_14 is not None

    return out