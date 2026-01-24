from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict

from prototype.config import load_config
from prototype.contracts import CandlePack
from prototype.indicators_v1 import compute_indicators
from prototype.papertrade_engine_v2 import PaperTradeEngineV2, PaperTradeState
from prototype.shoonya_adapter_v4 import ShoonyaAdapterV4
from prototype.signals_v1_compat import generate_signal_v1


OUT_DIR = os.path.join("prototype", "outputs")
STATE_PATH = os.path.join(OUT_DIR, "papertrade_state.json")
JOURNAL_PATH = os.path.join(OUT_DIR, "papertrade.jsonl")
EVENTS_PATH = os.path.join(OUT_DIR, "events.jsonl")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_out_dir() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)


def _append_jsonl(path: str, obj: Dict[str, Any]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _log_event(event: str, data: Dict[str, Any]) -> None:
    _append_jsonl(EVENTS_PATH, {"ts": _now_iso(), "event": event, "trace_id": "", "data": data})


def _load_state() -> PaperTradeState:
    if not os.path.exists(STATE_PATH):
        return PaperTradeState()
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        return PaperTradeState.from_dict(d)
    except Exception:
        return PaperTradeState()


def _save_state(state: PaperTradeState) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, indent=2)


def main() -> None:
    _ensure_out_dir()
    cfg = load_config()

    _log_event("BOOT", {"msg": "papertrade runner v2 starting", "ts": _now_iso()})

    broker = ShoonyaAdapterV4()
    ok = broker.login()
    if not ok:
        _log_event("BROKER_LOGIN_FAIL", {"error": broker.last_error})
        raise SystemExit("LOGIN FAILED: " + broker.last_error)

    _log_event("BROKER_LOGIN_OK", {"code": "OK"})
    print("✅ Login OK")

    # persistent engine
    state = _load_state()
    engine = PaperTradeEngineV2(state=state)

    poll = int(getattr(cfg, "poll_sec", 60) or 60)
    cycles = int(os.getenv("PAPERTRADE_CYCLES", "0") or 0)  # 0 => infinite loop

    cycle = 0
    while True:
        cycle += 1

        # --- fetch candles ---
        pack: CandlePack = broker.get_spot_candles_1h_pack()
        print("✅ CandlePack OK")

        # --- indicators ---
        ind = compute_indicators(pack)
        print("✅ IndicatorPack OK")

        # --- signal ---
        sig = generate_signal_v1(ind)
        sig["ts"] = _now_iso()
        print("✅ SignalPack OK")

        # --- papertrade step ---
        out = engine.step(sig)

        _save_state(engine.state)

        _append_jsonl(
            JOURNAL_PATH,
            {
                "ts": _now_iso(),
                "signal": sig,
                "result": out,
            },
        )

        _log_event(
            "PAPERTRADE_STEP",
            {
                "decision": sig.get("decision"),
                "close": sig.get("close"),
                "action": out.get("action"),
                "state": out.get("state"),
            },
        )

        print("\nPAPERTRADE RESULT =>")
        print(json.dumps(out, indent=2))

        if cycles > 0 and cycle >= cycles:
            print(f"\n✅ DONE: PAPERTRADE_CYCLES={cycles}")
            break

        time.sleep(poll)


if __name__ == "__main__":
    main()
