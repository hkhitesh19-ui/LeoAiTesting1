from __future__ import annotations

import time
from prototype.config import load_config
from prototype.shoonya_adapter_v4 import ShoonyaAdapterV4
from prototype.contracts import CandlePack


def run() -> None:
    cfg = load_config()
    broker = ShoonyaAdapterV4()

    if not broker.login():
        raise SystemExit(f"LOGIN FAILED: {broker.last_error}")

    print("✅ main_v7_v4: LOGIN OK")

    while True:
        try:
            pack: CandlePack = broker.get_spot_candles_1h_pack()

            heartbeat = {
                "close": pack.close,
                "last_ssboe": pack.last_ssboe,
            }

            print("HEARTBEAT =>", heartbeat)

            # future:
            # indicators(pack)
            # signals(pack)
            # papertrade(pack)

        except Exception as e:
            print("RUNTIME_ERROR:", str(e))

        time.sleep(cfg.poll_sec)


if __name__ == "__main__":
    run()