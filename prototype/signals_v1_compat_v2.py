from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict

from prototype.signals_v1 import generate_signal as _generate_signal


def _dict_to_obj(d: Dict[str, Any]) -> Any:
    """
    Convert dict indicators into object-style access (ind.close, ind.ema_20, etc.)
    Nested dicts are also converted recursively.
    """
    def conv(x: Any) -> Any:
        if isinstance(x, dict):
            return SimpleNamespace(**{k: conv(v) for k, v in x.items()})
        if isinstance(x, list):
            return [conv(v) for v in x]
        return x

    return conv(d)


def generate_signal_v1(indicators: Any) -> Dict[str, Any]:
    """
    COMPAT V2:
    - Accepts dict or IndicatorPack-like object
    - Ensures signals_v1.generate_signal() always gets an object with dot access
    """
    # If already object with attributes, keep it
    if not isinstance(indicators, dict):
        try:
            return _generate_signal(indicators)
        except Exception:
            # fallback to dict conversion if object behaves like dict
            if hasattr(indicators, "to_dict") and callable(getattr(indicators, "to_dict")):
                indicators = indicators.to_dict()

    if not isinstance(indicators, dict):
        raise TypeError(f"generate_signal_v1 expects dict/IndicatorPack, got {type(indicators)}")

    obj = _dict_to_obj(indicators)
    return _generate_signal(obj)