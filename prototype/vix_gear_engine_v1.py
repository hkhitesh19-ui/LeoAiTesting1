"""
PHASE 2A — INDIA VIX GEAR SELECTOR
"""

from prototype.vix_contracts import VixContext, now_ts

def select_gear_from_vix(vix: float) -> VixContext:
    vix = float(vix)

    if vix < 13:
        return VixContext(
            vix=vix,
            gear="RATIO_SPREAD",
            reason="Low VIX < 13 → Gamma expansion",
            ts=now_ts()
        )

    if 13 <= vix <= 18:
        return VixContext(
            vix=vix,
            gear="SAFE_FUTURE",
            reason="Mid VIX 13–18 → Trend with hedge",
            ts=now_ts()
        )

    return VixContext(
        vix=vix,
        gear="BULL_CALL_SPREAD",
        reason="High VIX > 18 → Sell IV",
        ts=now_ts()
    )
