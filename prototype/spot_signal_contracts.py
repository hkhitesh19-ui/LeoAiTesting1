from dataclasses import dataclass
from typing import Literal
from datetime import datetime

SignalType = Literal["ENTRY_ARMED", "WAIT"]

@dataclass
class SpotSignal:
    signal: SignalType
    reason: str
    spot_close: float
    ema20: float
    rsi19: float
    supertrend: float
    ts: str

def now_ts() -> str:
    return datetime.utcnow().isoformat() + "Z"
