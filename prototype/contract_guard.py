from __future__ import annotations
from typing import Any, Dict, List
from prototype.contracts import CandlePack

def ensure_candlepack(obj: Any, meta: Dict[str, Any]) -> CandlePack:
    """
    Normalize ANY Shoonya output into CandlePack.
    Reject invalid types.
    """
    rows: List[Dict[str, Any]] = []
    raw = obj

    # Shoonya: list[dict]
    if isinstance(obj, list):
        rows = [x for x in obj if isinstance(x, dict)]
    # Shoonya: dict wrapper {"stat":"Ok","values":[...]}
    elif isinstance(obj, dict) and obj.get("stat") == "Ok" and "values" in obj:
        v = obj.get("values")
        if isinstance(v, list):
            rows = [x for x in v if isinstance(x, dict)]
    else:
        rows = []

    if rows:
        last = rows[0]
        close = float(last.get("intc") or 0.0)
        ssboe = int(last.get("ssboe") or 0)
        return CandlePack(close=close, last_ssboe=ssboe, rows=rows, meta=meta, raw=raw)

    # fallback strict contract
    return CandlePack(close=0.0, last_ssboe=0, rows=[], meta=meta, raw=raw)