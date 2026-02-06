raise SystemExit("DEPRECATED: use main_v7_once_v5 (CandlePack) or smoke_test_v2+")

# prototype/main_v7_once.py
"""
Prototype v7 - One Cycle Runner
--------------------------------
Purpose:
- Daily debugging fast: run only ONE iteration and exit
- Avoid infinite loops / long waits

What it does:
1) load_config()
2) login()
3) fetch spot 1H candles pack
4) basic CandlePack validation
5) log 1 HEARTBEAT event
6) print summary + exit
"""

from __future__ import annotations

import sys
import json
import traceback
from datetime import datetime, timezone

from prototype.config import load_config
from prototype.events import event_log
from prototype.shoonya_adapter_v3 import ShoonyaAdapter


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _print_json(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def run_once() -> int:
    event_log("BOOT", {"msg": "prototype v7 ONCE starting", "ts": _utc_now_iso()})

    # 1) Load config
    cfg = load_config()
    event_log(
        "CONFIG_OK",
        {
            "poll_sec": cfg.poll_sec,
            "nifty_spot_token": getattr(cfg, "nifty_spot_token", None),
            "spot_token": getattr(cfg, "spot_token", None),
        },
    )

    # 2) Broker init
    broker = ShoonyaAdapter()
    if not hasattr(broker, "login"):
        raise RuntimeError("ShoonyaAdapter missing method: login()")
    if not hasattr(broker, "get_spot_candles_1h_pack"):
        raise RuntimeError("ShoonyaAdapter missing method: get_spot_candles_1h_pack()")

    # 3) Login
    ok = broker.login()
    if not ok:
        # best-effort last_error if exists
        last_err = getattr(broker, "last_error", None)
        event_log("BROKER_LOGIN_FAIL", {"last_error": str(last_err)})
        print("FATAL: login failed:", last_err)
        return 2

    event_log("BROKER_LOGIN_OK", {"code": "OK"})
    print("✅ LOGIN OK")

    # 4) Fetch candles (1 cycle)
    spot_pack = broker.get_spot_candles_1h_pack()

    # 5) Validate CandlePack structure
    # We don't assume exact dataclass fields; we check common expected attributes.
    pack_info = {"type": type(spot_pack).__name__}

    if hasattr(spot_pack, "__dict__"):
        # keep safe subset
        d = dict(spot_pack.__dict__)
        # remove huge payload fields if any
        for k in list(d.keys()):
            if k.lower() in ("df", "data", "candles", "rows"):
                # show only length
                try:
                    d[k] = f"<len={len(d[k])}>"
                except Exception:
                    d[k] = "<hidden>"
        pack_info["attrs"] = d

    # attempt to extract close/ssboe safely
    close_val = None
    last_ssboe = 0

    for key in ("close", "last_close", "spot_close", "ltp", "intc"):
        if hasattr(spot_pack, key):
            try:
                close_val = getattr(spot_pack, key)
                break
            except Exception:
                pass

    for key in ("last_ssboe", "ssboe", "last_epoch"):
        if hasattr(spot_pack, key):
            try:
                last_ssboe = int(getattr(spot_pack, key) or 0)
                break
            except Exception:
                pass

    # 6) HEARTBEAT event (single)
    hb = {"close": close_val, "last_ssboe": last_ssboe}
    event_log("HEARTBEAT", hb)

    print("✅ SPOT PACK OK")
    print("HEARTBEAT =>")
    _print_json(hb)

    print("\nCandlePack summary =>")
    _print_json(pack_info)

    event_log("ONCE_DONE", {"status": "OK"})
    return 0


def main() -> None:
    try:
        code = run_once()
        raise SystemExit(code)
    except KeyboardInterrupt:
        print("\nCTRL+C received. Exiting.")
        event_log("STOPPED", {"reason": "KeyboardInterrupt"})
        raise
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        print("\n❌ RUNTIME_EXCEPTION:", msg)
        traceback.print_exc()

        event_log("RUNTIME_EXCEPTION", {"exc": msg})
        raise SystemExit(1)


if __name__ == "__main__":
    main()
