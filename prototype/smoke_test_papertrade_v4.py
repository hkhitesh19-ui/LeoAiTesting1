from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from prototype.contracts import CandlePack
from prototype.indicators_v1 import compute_indicators
from prototype.papertrade_engine_v2 import PaperTradeEngineV2
from prototype.shoonya_adapter_v4 import ShoonyaAdapterV4
from prototype.signals_v1_compat import generate_signal_v1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    print("=== SMOKE TEST: PAPERTRADE V4 (STATEFUL ENGINE) ===")

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

    ind = compute_indicators(pack)
    if not isinstance(ind, dict):
        raise SystemExit(f"FAIL: indicators must be dict, got {type(ind)}")
    print("✅ IndicatorPack OK")

    sig = generate_signal_v1(ind)
    if not isinstance(sig, dict) or "decision" not in sig:
        raise SystemExit("FAIL: signal invalid")
    sig["ts"] = _now_iso()
    print("✅ SignalPack OK")

    engine = PaperTradeEngineV2()
    out1 = engine.step(sig)
    out2 = engine.step(sig)  # SAME signal again -> should NOT re-enter

    print("✅ PaperTradeEngine V2 OK")
    print(json.dumps({"first": out1, "second": out2}, indent=2))

    # assert: second action cannot be ENTER (no re-entry spam)
    a2 = (out2.get("action") or {}).get("action")
    if a2 == "ENTER":
        raise SystemExit("FAIL: re-entry spam detected (ENTER twice)")

    print("✅ PASS: No re-entry spam")


if __name__ == "__main__":
    main()
