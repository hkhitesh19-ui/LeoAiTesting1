from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from prototype.issue_logger import IssueLogger
from prototype.events import event_log

# NOTE:
# config.load_config may return either:
# - dict-like (old style)
# - Config object/dataclass (new style)
from prototype.config import load_config  # type: ignore

from prototype.shoonya_adapter_v3 import ShoonyaAdapter  # type: ignore

from prototype.indicators import (
    calc_atr14,
    calc_ema,
    calc_rsi14,
    calc_supertrend,
)

OUTPUT_DIR = os.path.join("prototype", "outputs")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def cfg_get(cfg: Any, key: str, default: Any = None) -> Any:
    """
    Hardening helper:
    - if cfg is dict-like -> cfg.get
    - if cfg is object -> getattr
    """
    if cfg is None:
        return default

    # dict-like
    if hasattr(cfg, "get") and callable(getattr(cfg, "get")):
        try:
            return cfg.get(key, default)
        except Exception:
            return default

    # object/dataclass
    if hasattr(cfg, key):
        try:
            return getattr(cfg, key)
        except Exception:
            return default

    return default


@dataclass
class RuntimeCfg:
    poll_sec: int = 60
    atr_mult: float = 2.0
    rsi_min: float = 55.0
    ema_len: int = 20
    st_len: int = 10
    st_mult: float = 3.0


def build_runtime_cfg(cfg_raw: Any) -> RuntimeCfg:
    return RuntimeCfg(
        poll_sec=int(cfg_get(cfg_raw, "poll_sec", 60)),
        atr_mult=float(cfg_get(cfg_raw, "atr_mult", 2.0)),
        rsi_min=float(cfg_get(cfg_raw, "rsi_min", 55.0)),
        ema_len=int(cfg_get(cfg_raw, "ema_len", 20)),
        st_len=int(cfg_get(cfg_raw, "st_len", 10)),
        st_mult=float(cfg_get(cfg_raw, "st_mult", 3.0)),
    )


def compute_signal_from_spot_df(df):
    """
    Returns:
        snapshot: Dict[str, Any]
    """
    close_series = df["close"].astype(float).tolist()
    high_series = df["high"].astype(float).tolist()
    low_series = df["low"].astype(float).tolist()

    st_val, st_dir, st_prev = calc_supertrend(
        highs=high_series,
        lows=low_series,
        closes=close_series,
        period=10,
        multiplier=3.0,
    )
    rsi = calc_rsi14(close_series)
    ema20 = calc_ema(close_series, length=20)
    atr14 = calc_atr14(high_series, low_series, close_series)

    close = close_series[-1]

    # Example Conditions (customize later)
    conds = [
        close > ema20,          # trend
        st_dir == 1,            # supertrend bullish
        rsi >= 55.0,            # momentum
        atr14 > 0,              # sanity
    ]

    snapshot = {
        "close": close,
        "st_val": st_val,
        "st_dir": st_dir,
        "st_prev": st_prev,
        "rsi": rsi,
        "ema20": ema20,
        "atr14": atr14,
        "conds": conds,
    }
    return snapshot


def run() -> None:
    # Issue logger
    issue = IssueLogger(out_dir=OUTPUT_DIR)

    # Boot event
    event_log("BOOT", {"msg": "prototype v7 starting"})

    # Load config (may return dict or Config)
    cfg_raw = load_config()
    cfg = build_runtime_cfg(cfg_raw)

    broker = ShoonyaAdapter()
    ok = broker.login()
    if not ok:
        issue.track_runtime_error(
            "E_LOGIN",
            "Shoonya login failed",
            {"last_error": broker.last_error},
        )
        event_log("BROKER_LOGIN_FAIL", {"err": broker.last_error})
        return

    event_log("BROKER_LOGIN_OK", {"code": "OK"})

    last_candle_key: Optional[int] = None

    while True:
        try:
            # Use pack function to avoid SSL hang and to get meta
            spot_pack = broker.get_spot_candles_1h_pack()
            spot_df = spot_pack["df"]
            meta = spot_pack.get("meta", {})

            # candle time key - use ssboe if present
            candle_ts = int(meta.get("last_ssboe", 0)) if meta else 0

            # heartbeat
            event_log("HEARTBEAT", {
                "close": float(spot_df["close"].iloc[-1]),
                "last_ssboe": candle_ts,
            })

            # candle close detection
            if candle_ts and candle_ts != last_candle_key:
                last_candle_key = candle_ts

                snap = compute_signal_from_spot_df(spot_df)
                event_log("CANDLE_CLOSE_SIGNAL", {
                    "ssboe": candle_ts,
                    **snap
                })

            # mark healthy if no exception
            issue.mark_healthy()

        except Exception as e:
            issue.track_runtime_error(
                "E_RUNTIME",
                "Runtime exception in main loop",
                {"exc": repr(e)},
            )
            event_log("RUNTIME_EXCEPTION", {"exc": repr(e)})

        time.sleep(cfg.poll_sec)


if __name__ == "__main__":
    run()
