"""
SPOT vs FUT BASIS GUARD V1
"""

from dataclasses import dataclass
from datetime import datetime, timezone

MAX_BASIS = 40.0

@dataclass
class BasisDecision:
    allowed: bool
    basis: float
    reason: str
    ts: str

def check_spot_fut_basis(spot: float, future: float):
    basis = abs(future - spot)
    ts = datetime.now(timezone.utc).isoformat()

    if basis <= MAX_BASIS:
        return BasisDecision(True, basis, "Basis within limit", ts)

    return BasisDecision(False, basis, "Basis exceeds limit", ts)
