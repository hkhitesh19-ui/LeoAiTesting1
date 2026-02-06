# prototype/execution_intent_v1.py

from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ExecutionIntent:
    intent: str              # EXECUTE | WAIT
    gear: Optional[str]      # SAFE_FUTURE | RATIO_SPREAD | BULL_CALL_SPREAD
    reason: str
    ts: str
