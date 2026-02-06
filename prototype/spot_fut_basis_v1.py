# prototype/spot_fut_basis_v1.py

from dataclasses import dataclass
from datetime import datetime

MAX_BASIS_POINTS = 50  # configurable safety threshold

@dataclass(frozen=True)
class BasisDecision:
    allowed: bool
    basis: float
    reason: str
    ts: str

def check_basis(spot: float, future: float) -> BasisDecision:
    basis = future - spot

    if abs(basis) > MAX_BASIS_POINTS:
        return BasisDecision(
            allowed=False,
            basis=basis,
            reason="Basis exceeds limit",
            ts=datetime.utcnow().isoformat() + "Z"
        )

    return BasisDecision(
        allowed=True,
        basis=basis,
        reason="Basis within limit",
        ts=datetime.utcnow().isoformat() + "Z"
    )
