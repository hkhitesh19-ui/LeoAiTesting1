# prototype/risk_governor_v1.py

from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class RiskDecision:
    exit_now: bool
    reason: str
    ts: str

def evaluate_risk(
    position_type: str,
    mtm: float,
    capital: float,
    price: float | None = None,
    atr: float | None = None,
) -> RiskDecision:
    ts = datetime.utcnow().isoformat() + "Z"

    # OPTIONS risk (MTM based)
    if position_type == "OPTIONS":
        if mtm < 0 and abs(mtm) > (0.045 * capital):
            return RiskDecision(
                exit_now=True,
                reason="Options MTM loss > 4.5% capital",
                ts=ts,
            )

    # FUTURES risk (ATR based)
    if position_type == "FUT" and price is not None and atr is not None:
        if price <= (-2.0 * atr):
            return RiskDecision(
                exit_now=True,
                reason="FUT price hit ATR stop",
                ts=ts,
            )

    return RiskDecision(
        exit_now=False,
        reason="Risk within limits",
        ts=ts,
    )
