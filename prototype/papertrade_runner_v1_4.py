from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

from prototype.shoonya_adapter_v4 import ShoonyaAdapterV4
from prototype.indicators_v1_compat import compute_indicators_v1
from prototype.signals_v1_compat_v2 import generate_signal_v1
from prototype.papertrade_engine_v1 import PaperTradeEngineV1


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_outdir() -> str:
    out_dir = r".\prototype\outputs"
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def log_event(event: str, data: Dict[str, Any]) -> None:
    """
    Minimal event logger (no dependency).
    Writes JSONL to prototype/outputs/events.jsonl
    """
    out_dir = _ensure_outdir()
    path = os.path.join(out_dir, "events.jsonl")
    line = json.dumps(
        {"ts": _utcnow(), "event": event, "trace_id": "", "data": data},
        ensure_ascii=False,
    )
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    log_event("BOOT", {"msg": "papertrade runner v1.4 starting", "ts": _utcnow()})

    broker = ShoonyaAdapterV4()
    engine = PaperTradeEngineV1()

    ok = broker.login()
    if not ok:
        log_event("RUNTIME_EXCEPTION", {"exc": "LOGIN_FAILED: " + broker.last_error})
        raise SystemExit("LOGIN FAILED: " + broker.last_error)

    print("✅ Login OK")
    log_event("BROKER_LOGIN_OK", {"code": "OK"})

    pack = broker.get_spot_candles_1h_pack()
    print("✅ CandlePack OK")

    ind = compute_indicators_v1(pack)
    print("✅ IndicatorPack OK")

    sig = generate_signal_v1(ind)
    print("✅ SignalPack OK")

    sig = dict(sig)
    sig["ts"] = _utcnow()

    result = engine.step(sig)

    out_dir = _ensure_outdir()
    path = os.path.join(out_dir, "papertrade.jsonl")
    line = json.dumps({"ts": _utcnow(), "signal": sig, "result": result}, ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

    log_event(
        "PAPERTRADE_STEP",
        {
            "decision": sig.get("decision"),
            "close": sig.get("close"),
            "action": (result or {}).get("action"),
        },
    )

    print("\nPAPERTRADE RESULT =>")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()