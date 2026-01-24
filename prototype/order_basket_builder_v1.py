"""
ORDER BASKET BUILDER V1
Builds trade legs based on VIX gear
"""

from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass
class OrderLeg:
    side: str        # BUY / SELL
    instrument: str  # FUT / CE / PE
    strike: int | None
    qty: int

@dataclass
class OrderBasket:
    gear: str
    legs: list
    risk_note: str
    ts: str

def build_order_basket(
    gear: str,
    spot: int,
    lot_size: int = 65
):
    ts = datetime.now(timezone.utc).isoformat()

    if gear == "SAFE_FUTURE":
        return OrderBasket(
            gear=gear,
            legs=[
                OrderLeg("BUY", "FUT", None, 1),
                OrderLeg("BUY", "PE", spot, 1),
            ],
            risk_note="Future + ATM Put hedge",
            ts=ts
        )

    if gear == "RATIO_SPREAD":
        return OrderBasket(
            gear=gear,
            legs=[
                OrderLeg("BUY", "CE", spot + 200, 2),
                OrderLeg("SELL", "CE", spot - 100, 1),
            ],
            risk_note="Low VIX gamma ratio spread",
            ts=ts
        )

    if gear == "BULL_CALL_SPREAD":
        return OrderBasket(
            gear=gear,
            legs=[
                OrderLeg("BUY", "CE", spot - 100, 1),
                OrderLeg("SELL", "CE", spot + 200, 1),
            ],
            risk_note="High VIX defined-risk spread",
            ts=ts
        )

    raise ValueError("Unsupported gear")
