from __future__ import annotations

from typing import Any, Dict
import prototype.signals_v1 as base


def generate_signal_v1(indicators: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compatibility wrapper.

    Ensures papertrade always imports:
      from prototype.signals_v1_compat import generate_signal_v1
    regardless of internal function names in prototype.signals_v1.
    """
    for fn_name in (
        "generate_signal_v1",
        "generate_signal",
        "build_signal_v1",
        "build_signal",
        "signal_v1",
        "make_signal_v1",
    ):
        fn = getattr(base, fn_name, None)
        if callable(fn):
            out = fn(indicators)
            if isinstance(out, dict):
                return out
            if hasattr(out, "to_dict"):
                return out.to_dict()
            return {"decision": "HOLD", "reason": "bad_signal_type", "raw": out}

    raise ImportError(
        "No compatible signal function found in prototype.signals_v1. "
        "Expected one of: generate_signal_v1/generate_signal/build_signal_v1"
    )