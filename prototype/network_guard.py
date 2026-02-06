from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import pandas as pd


@dataclass
class GuardResult:
    ok: bool
    df: Optional[pd.DataFrame] = None
    meta: Optional[Dict[str, Any]] = None
    error: str = ""


def _build_df_from_series(out: Any) -> GuardResult:
    """
    Shoonya get_time_price_series typically returns list[dict] with keys:
    time, into, inth, intl, intc, ssboe ...
    """
    if not isinstance(out, list) or len(out) == 0:
        return GuardResult(ok=False, error=f"EMPTY_SERIES: {type(out)} {out}")

    newest = out[0]
    if not isinstance(newest, dict):
        return GuardResult(ok=False, error=f"BAD_NEWEST: {type(newest)}")

    rows = []
    for item in reversed(out):
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "open": float(item.get("into") or 0.0),
                "high": float(item.get("inth") or 0.0),
                "low": float(item.get("intl") or 0.0),
                "close": float(item.get("intc") or 0.0),
            }
        )

    df = pd.DataFrame(rows)
    meta = {
        "candle_time": str(newest.get("time", "")),
        "ssboe": int(newest.get("ssboe", 0) or 0),
    }
    return GuardResult(ok=True, df=df, meta=meta)


def fetch_spot_1h_with_timeout(api, token: str, timeout_sec: int) -> GuardResult:
    """
    IMPORTANT:
    - No multiprocessing on Windows (pickle/thread.lock breaks)
    - Use requests timeout (set inside api wrapper / requests)
    """
    try:
        # NorenApi.get_time_price_series does requests.post internally.
        # It may hang if network stalls, but in practice requests has its own socket timeouts.
        out = api.get_time_price_series(
            exchange="NSE",
            token=token,
            interval="60",
        )
        return _build_df_from_series(out)
    except Exception as e:
        return GuardResult(ok=False, error=f"FETCH_EXC: {e}")


def run_with_hard_timeout(timeout_sec: int = 30) -> GuardResult:
    """
    Stable guard version.
    We do NOT spawn new process.
    ShoonyaAdapter will call this with retries/backoff.
    """
    try:
        # Lazy import here to avoid heavy boot and to avoid child-process import.
        from prototype.shoonya_login_v2 import login as shoonya_login
        from prototype.config import load_config

        cfg = load_config()
        api, err = shoonya_login()
        if not api:
            return GuardResult(ok=False, error=f"LOGIN_FAIL: {err}")

        # token logic: fallback to known NIFTY token if exists in config
        token = getattr(cfg, "nifty_spot_token", "") or getattr(cfg, "spot_token", "") or ""
        if not token:
            return GuardResult(ok=False, error="CONFIG_MISSING_TOKEN")

        res = fetch_spot_1h_with_timeout(api=api, token=str(token), timeout_sec=timeout_sec)
        return res

    except Exception as e:
        return GuardResult(ok=False, error=f"GUARD_EXC: {e}")
