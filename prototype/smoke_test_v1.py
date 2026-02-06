from __future__ import annotations
import json
from prototype.config import load_config
from prototype.shoonya_adapter_v3 import ShoonyaAdapter

def main():
    cfg = load_config()
    broker = ShoonyaAdapter()

    print("=== SMOKE TEST V1 ===")
    print("1) Config OK")
    print("2) Login...")
    ok = broker.login()
    if not ok:
        raise SystemExit("FAIL: login failed")
    print("✅ Login OK")

    print("3) Spot candles...")
    pack = broker.get_spot_candles_1h_pack()
    # pack should be dict for now; later convert adapter to CandlePack return
    if not isinstance(pack, dict):
        raise SystemExit(f"FAIL: pack type {type(pack)}")

    close = pack.get("close")
    last_ssboe = pack.get("last_ssboe")
    print("✅ Spot OK")
    print(json.dumps({"close": close, "last_ssboe": last_ssboe}, indent=2))

if __name__ == "__main__":
    main()