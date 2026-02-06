from __future__ import annotations

import json
from datetime import datetime, timezone

from prototype.shoonya_adapter_v4 import ShoonyaAdapterV4
from prototype.indicators_v1 import compute_indicators_v1
from prototype.signals_v1 import generate_signal_v1
from prototype.papertrade_engine_v1 import PaperTradeEngineV1
from prototype.event_logger import log_event


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def main():
    log_event("BOOT", {"msg": "papertrade runner v1 starting", "ts": _utcnow()})

    broker = ShoonyaAdapterV4()
    engine = PaperTradeEngineV1()

    ok = broker.login()
    if not ok:
        log_event("RUNTIME_EXCEPTION", {"exc": "LOGIN_FAILED: " + broker.last_error})
        raise SystemExit("LOGIN FAILED: " + broker.last_error)

    print("✅ Login OK")

    pack = broker.get_spot_candles_1h_pack()
    print("✅ CandlePack OK")

    ind = compute_indicators_v1(pack)
    print("✅ IndicatorPack OK")

    sig = generate_signal_v1(ind)
    print("✅ SignalPack OK")

    # attach timestamp
    sig = dict(sig)
    sig["ts"] = _utcnow()

    result = engine.step(sig)

    # write papertrade jsonl
    path = r".\prototype\outputs\papertrade.jsonl"
    line = json.dumps(
        {"ts": _utcnow(), "signal": sig, "result": result},
        ensure_ascii=False
    )
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

    log_event("PAPERTRADE_STEP", {
        "decision": sig.get("decision"),
        "close": sig.get("close"),
        "action": result.get("action"),
    })

    print("\nPAPERTRADE RESULT =>")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()