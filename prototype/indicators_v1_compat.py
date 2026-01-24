from __future__ import annotations

from typing import Any, Dict

from prototype.contracts import CandlePack

# We will import indicators_v1 and auto-detect correct function name.
import prototype.indicators_v1 as base


def compute_indicators_v1(pack: CandlePack) -> Dict[str, Any]:
    """
    Compatibility wrapper.
    Ensures papertrade modules can always call compute_indicators_v1(pack).
    """
    # preferred names in descending order
    for fn_name in (
        "compute_indicators_v1",
        "compute_indicators",
        "compute_indicator_pack_v1",
        "compute_indicator_pack",
        "build_indicators_v1",
    ):
        fn = getattr(base, fn_name, None)
        if callable(fn):
            out = fn(pack)
            # normalize to dict
            if isinstance(out, dict):
                return out
            # some versions might return dataclass with to_dict
            if hasattr(out, "to_dict"):
                return out.to_dict()
            # fallback
            return {"close": float(pack.close), "raw": out}

    raise ImportError(
        "No compatible indicator function found in prototype.indicators_v1. "
        "Expected one of: compute_indicators_v1/compute_indicators/compute_indicator_pack_v1"
    )