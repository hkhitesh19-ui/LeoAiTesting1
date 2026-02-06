from __future__ import annotations

import json
from prototype.config import load_config
from prototype.shoonya_adapter_v4 import ShoonyaAdapterV4


def run_once():
    cfg = load_config()
    broker = ShoonyaAdapterV4(spot_token=str(cfg.nifty_spot_token))

    ok = broker.login()
    if not ok:
        print("❌ LOGIN FAILED:", broker.last_error)
        return

    print("✅ LOGIN OK")

    pack = broker.get_spot_candles_1h_pack()
    print("✅ SPOT PACK OK")

    hb = {"close": pack.get("close"), "last_ssboe": pack.get("last_ssboe", 0)}
    print("HEARTBEAT =>")
    print(json.dumps(hb, indent=2))

    print("\nSpotPack summary =>")
    print(json.dumps(
        {
            "rows": len(pack.get("rows", [])),
            "meta": pack.get("meta", {}),
            "type_close": str(type(pack.get("close"))),
        },
        indent=2
    ))


if __name__ == "__main__":
    run_once()
