from __future__ import annotations

import json

from prototype.shoonya_adapter_v4 import ShoonyaAdapterV4
from prototype.contracts import CandlePack
from prototype.indicators_v1_compat import compute_indicators_v1
from prototype.signals_v1 import generate_signal_v1
from prototype.papertrade_engine_v1 import PaperTradeEngineV1


def main():
    print("=== SMOKE TEST: PAPERTRADE V1 ===")

    broker = ShoonyaAdapterV4()
    ok = broker.login()
    if not ok:
        raise SystemExit("FAIL: login failed: " + broker.last_error)
    print("✅ Login OK")

    pack = broker.get_spot_candles_1h_pack()
    if not isinstance(pack, CandlePack):
        raise SystemExit(f"FAIL: CandlePack expected, got {type(pack)}")
    print("✅ CandlePack OK")

    ind = compute_indicators_v1(pack)
    if not isinstance(ind, dict) or "close" not in ind:
        raise SystemExit("FAIL: IndicatorPack invalid")
    print("✅ IndicatorPack OK")

    sig = generate_signal_v1(ind)
    if not isinstance(sig, dict) or "decision" not in sig:
        raise SystemExit("FAIL: SignalPack invalid")
    print("✅ SignalPack OK")

    engine = PaperTradeEngineV1()
    out = engine.step(sig)

    if not isinstance(out, dict) or "state" not in out:
        raise SystemExit("FAIL: engine output invalid")
    print("✅ PaperTradeEngine OK")

    print(json.dumps({"signal": sig, "out": out}, indent=2))


if __name__ == "__main__":
    main()