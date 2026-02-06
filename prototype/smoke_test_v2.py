from __future__ import annotations
import json
from prototype.shoonya_adapter_v4 import ShoonyaAdapterV4
from prototype.contracts import CandlePack


def main():
    broker = ShoonyaAdapterV4()

    print("=== SMOKE TEST V2 (CandlePack Contract) ===")
    print("1) Login...")
    ok = broker.login()
    if not ok:
        raise SystemExit("FAIL: login failed: " + broker.last_error)
    print("✅ Login OK")

    print("2) Spot candles (CandlePack)...")
    pack = broker.get_spot_candles_1h_pack()

    if not isinstance(pack, CandlePack):
        raise SystemExit(f"FAIL: expected CandlePack, got {type(pack)}")

    if pack.close is None or pack.last_ssboe is None:
        raise SystemExit("FAIL: Contract broken: close/ssboe is None")

    print("✅ Spot OK")
    print(json.dumps(pack.to_dict(), indent=2))


if __name__ == "__main__":
    main()