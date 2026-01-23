from __future__ import annotations

import json
from prototype.shoonya_adapter_v4 import ShoonyaAdapterV4


def main() -> None:
    broker = ShoonyaAdapterV4()

    ok = broker.login()
    if not ok:
        raise SystemExit(f"LOGIN FAILED: {broker.last_error}")

    print("✅ LOGIN OK (V4)")

    pack = broker.get_spot_candles_1h_pack()
    print("✅ SPOT PACK OK (CandlePack strict)")

    heartbeat = {
        "close": pack.close,
        "last_ssboe": pack.last_ssboe,
    }

    print("HEARTBEAT =>")
    print(json.dumps(heartbeat, indent=2))

    summary = {
        "rows": len(pack.rows),
        "meta": pack.meta,
        "type": str(type(pack)),
        "type_close": str(type(pack.close)),
        "type_ssboe": str(type(pack.last_ssboe)),
    }

    print("\nSpotPack summary =>")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()