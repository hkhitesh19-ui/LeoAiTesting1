from dataclasses import dataclass
from datetime import datetime, timezone

def now_ts():
    return datetime.now(timezone.utc).isoformat()

@dataclass(frozen=True)
class ExecutionIntent:
    intent: str           # EXECUTE / WAIT
    gear: str | None
    reason: str
    ts: str
