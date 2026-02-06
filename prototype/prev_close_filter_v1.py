"""
PREVIOUS CLOSE FILTER V1
Ensures directional bias confirmation
"""

from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass
class PrevCloseDecision:
    allowed: bool
    reason: str
    ts: str

def check_prev_close(spot_close: float, prev_close: float):
    ts = datetime.now(timezone.utc).isoformat()

    if spot_close > prev_close:
        return PrevCloseDecision(True, "Spot above previous close", ts)

    return PrevCloseDecision(False, "Spot below previous close", ts)
