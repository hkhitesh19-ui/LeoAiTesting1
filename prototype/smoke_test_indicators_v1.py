from __future__ import annotations
import json

from prototype.shoonya_adapter_v4 import ShoonyaAdapterV4
from prototype.contracts import CandlePack
from prototype.indicator_contracts import IndicatorPack
from prototype.indicators_v1 import compute_indicators


def main():
    print("=== SMOKE TEST: INDICATORS V1 ===")

    broker = ShoonyaAdapterV4()
    ok = broker.login()
    if not ok:
        raise SystemExit("FAIL: login failed: " + broker.last_error)
    print("✅ Login OK")

    pack = broker.get_spot_candles_1h_pack()
    if not isinstance(pack, CandlePack):
        raise SystemExit(f"FAIL: expected CandlePack, got {type(pack)}")
    print("✅ CandlePack OK")

    ind = compute_indicators(pack)
    if not isinstance(ind, IndicatorPack):
        raise SystemExit(f"FAIL: expected IndicatorPack, got {type(ind)}")
    print("✅ IndicatorPack OK")

    print(json.dumps(ind.to_dict(), indent=2))


if __name__ == "__main__":
    main()