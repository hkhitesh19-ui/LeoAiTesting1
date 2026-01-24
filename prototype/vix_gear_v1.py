"""
VIX GEAR LOGIC V1
Pure decision logic — no side effects
"""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class VixContext:
    vix: float
    gear: str
    reason: str
    ts: str


def select_gear(vix: float) -> VixContext:
    ts = datetime.now(timezone.utc).isoformat()

    if vix < 13:
        return VixContext(
            vix=vix,
            gear="RATIO_SPREAD",
            reason="Low VIX < 13 → Gamma expansion",
            ts=ts,
        )

    if 13 <= vix <= 18:
        return VixContext(
            vix=vix,
            gear="SAFE_FUTURE",
            reason="Mid VIX 13–18 → Trend with hedge",
            ts=ts,
        )

    return VixContext(
        vix=vix,
        gear="BULL_CALL_SPREAD",
        reason="High VIX > 18 → Sell IV",
        ts=ts,
    )
