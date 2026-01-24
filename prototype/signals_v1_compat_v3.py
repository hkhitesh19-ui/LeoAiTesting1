from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict
from datetime import datetime, timezone

from prototype.signals_v1 import generate_signal as _legacy_signal


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_obj(d: Dict[str, Any]) -> Any:
    def conv(x):
        if isinstance(x, dict):
            return SimpleNamespace(**{k: conv(v) for k, v in x.items()})
        return x
    return conv(d)


def generate_signal_v1(indicators: Any) -> Dict[str, Any]:
    """
    COMPAT V3 — STRICT SIGNAL CONTRACT
    """
    if isinstance(indicators, dict):
        ind_obj = _to_obj(indicators)
        close = float(indicators.get("close", 0.0))
    else:
        ind_obj = indicators
        close = float(getattr(indicators, "close", 0.0))

    out = _legacy_signal(ind_obj)

    # Legacy returned nothing → HOLD
    if not isinstance(out, dict):
        return {
            "decision": "HOLD",
            "reason": "legacy_signal_none",
            "close": close,
            "meta": {},
            "ts": _now(),
        }

    # Enforce contract
    return {
        "decision": out.get("decision", "HOLD"),
        "reason": out.get("reason", "missing_reason"),
        "close": out.get("close", close),
        "meta": out.get("meta", {}),
        "ts": out.get("ts", _now()),
    }