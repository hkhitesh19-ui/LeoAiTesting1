from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class IndicatorPack:
    """
    STRICT CONTRACT:
    - close: float
    - ema_20: float
    - ema_50: float
    - ema_200: float
    - rsi_14: float
    - adx_14: float
    - meta: dict
    """
    close: float
    ema_20: float
    ema_50: float
    ema_200: float
    rsi_14: float
    adx_14: float
    meta: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "close": self.close,
            "ema_20": self.ema_20,
            "ema_50": self.ema_50,
            "ema_200": self.ema_200,
            "rsi_14": self.rsi_14,
            "adx_14": self.adx_14,
            "meta": self.meta,
        }