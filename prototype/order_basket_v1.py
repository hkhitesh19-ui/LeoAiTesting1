# prototype/order_basket_v1.py

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass(frozen=True)
class OrderLeg:
    side: str           # BUY / SELL
    instrument: str     # FUT / CE / PE
    strike: Optional[int]
    qty: int

@dataclass(frozen=True)
class OrderBasket:
    gear: str
    legs: List[OrderLeg]
    risk_note: str
    ts: str

def build_order_basket(gear: str, atm: int) -> OrderBasket:
    ts = datetime.utcnow().isoformat() + "Z"

    if gear == "SAFE_FUTURE":
        return OrderBasket(
            gear=gear,
            legs=[
                OrderLeg("BUY", "FUT", None, 1),
                OrderLeg("BUY", "PE", atm, 1),
            ],
            risk_note="Future + ATM Put hedge",
            ts=ts,
        )

    if gear == "RATIO_SPREAD":
        return OrderBasket(
            gear=gear,
            legs=[
                OrderLeg("BUY", "CE", atm + 200, 2),
                OrderLeg("SELL", "CE", atm - 100, 1),
            ],
            risk_note="Low VIX gamma ratio spread",
            ts=ts,
        )

    if gear == "BULL_CALL_SPREAD":
        return OrderBasket(
            gear=gear,
            legs=[
                OrderLeg("BUY", "CE", atm - 100, 1),
                OrderLeg("SELL", "CE", atm + 200, 1),
            ],
            risk_note="High VIX defined-risk spread",
            ts=ts,
        )

    raise ValueError(f"Unsupported gear: {gear}")
