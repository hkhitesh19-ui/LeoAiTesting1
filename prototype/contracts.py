from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass(frozen=True)
class CandlePack:
    """
    STRICT CONTRACT:
    - close: float (never None)
    - last_ssboe: int
    - rows: list[dict]
    - meta: dict

    This object MUST be returned by all candle fetch functions.
    """
    close: float
    last_ssboe: int
    rows: List[Dict[str, Any]]
    meta: Dict[str, Any]
    raw: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "close": self.close,
            "last_ssboe": self.last_ssboe,
            "rows": self.rows,
            "meta": self.meta,
        }