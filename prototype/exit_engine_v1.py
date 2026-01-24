"""
EXIT ENGINE V1
Route-1 (Risk) + Route-2 (Signal)
"""

from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass
class ExitDecision:
    exit: bool
    route: str | None
    reason: str
    ts: str

def evaluate_exit(
    risk_exit: bool,
    signal_exit: bool
) -> ExitDecision:

    ts = datetime.now(timezone.utc).isoformat()

    # Route 1 — Intrabar Risk Exit (highest priority)
    if risk_exit:
        return ExitDecision(
            exit=True,
            route="INTRABAR_RISK",
            reason="Risk governor triggered",
            ts=ts
        )

    # Route 2 — Signal Exit (next candle)
    if signal_exit:
        return ExitDecision(
            exit=True,
            route="SIGNAL_EXIT",
            reason="SuperTrend Red AND RSI > 40",
            ts=ts
        )

    return ExitDecision(
        exit=False,
        route=None,
        reason="No exit condition met",
        ts=ts
    )
