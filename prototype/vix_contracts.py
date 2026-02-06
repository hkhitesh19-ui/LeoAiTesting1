from dataclasses import dataclass
from datetime import datetime, timezone

def now_ts():
    return datetime.now(timezone.utc).isoformat()

@dataclass(frozen=True)
class VixContext:
    vix: float
    gear: str
    reason: str
    ts: str
