from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class SignalPack:
    """
    STRICT CONTRACT:
    - decision: "CALL" | "PUT" | "NONE"
    - reason: str
    - close: float
    - meta: dict
    """
    decision: str
    reason: str
    close: float
    meta: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "close": self.close,
            "meta": self.meta,
        }