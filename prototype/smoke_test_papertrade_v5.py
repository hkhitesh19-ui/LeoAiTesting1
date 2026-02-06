from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict

from prototype.contracts import CandlePack
from prototype.indicators_v1 import compute_indicators
from prototype.papertrade_engine_v2 import PaperTradeEngineV2
from prototype.shoonya_adapter_v4 import ShoonyaAdapterV4
from prototype.signals_v1_compat import generate_signal_v1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ind_to_dict(ind: Any) -> Dict[str, Any]:
    # Accept dict
    if isinstance(ind, dict):
        return ind

    # If IndicatorPack-like with to_dict()
    if hasattr(ind, "to_dict") and callable(getattr(ind, "to_dict")):
        out = ind.to_dict()
        if isinstance(out, dict):
            return out

    # If dataclass
    if hasattr(ind, "__dict__"):
        d = dict(ind.__dict__)
        if isinstance(d, dict):
            return d

    raise TypeError(f"Unsupported indicators type: {type(ind)}")


def main() -> None:
    print("=== SMOKE TEST: PAPERTRADE V5 (IndicatorPack COMPAT) ===")

    broker = ShoonyaAdapterV4()
    ok = broker.login()
    if not ok:
        raise SystemExit("FAIL: login failed: " + broker.last_error)
    print("✅ Login OK")

    pack: CandlePack = broker.get_spot_candles_1h_pack()
    if not isinstance(pack, CandlePack):
        raise SystemExit(f"FAIL: expected CandlePack, got {type(pack)}")
    if pack.close is None or pack.last_ssboe is None:
        raise SystemExit("FAIL: CandlePack contract broken")
    print("✅ CandlePack OK")

    ind_obj = compute_indicators(pack)
    ind = _ind_to_dict(ind_obj)
    print("✅ IndicatorPack OK (normalized)")

    sig = generate_signal_v1(ind)
    if not isinstance(sig, dict) or "decision" not in sig:
        raise SystemExit("FAIL: signal invalid")
    sig["ts"] = _now_iso()
    print("✅ SignalPack OK")

    engine = PaperTradeEngineV2()
    out1 = engine.step(sig)
    out2 = engine.step(sig)  # SAME signal -> must not ENTER again

    print("✅ PaperTradeEngine V2 OK")
    print(json.dumps({"first": out1, "second": out2}, indent=2))

    a2 = (out2.get("action") or {}).get("action")
    if a2 == "ENTER":
        raise SystemExit("FAIL: re-entry spam detected (ENTER twice)")

    print("✅ PASS: No re-entry spam")


if __name__ == "__main__":
    main()