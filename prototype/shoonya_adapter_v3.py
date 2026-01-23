from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from prototype.network_guard import run_with_hard_timeout, GuardResult


class AdapterError(RuntimeError):
    pass


def _normalize_candle_item(x: Any) -> Optional[Dict[str, Any]]:
    if x is None:
        return None
    if isinstance(x, dict):
        return x
    if isinstance(x, (tuple, list)):
        # best effort mapping: time, open, high, low, close
        if len(x) >= 5:
            return {
                "time": str(x[0]),
                "into": x[1],
                "inth": x[2],
                "intl": x[3],
                "intc": x[4],
            }
        return None
    return None


def _as_float(v: Any) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


class ShoonyaAdapter:
    """
    Stable adapter interface for main_v7:
      - login()
      - last_error
      - get_spot_candles_1h_pack()  -> returns dict: {"df": DataFrame, "meta": dict}
    """

    def __init__(self):
        self.api = None
        self.last_error: str = ""
        self.hard_timeout_sec: int = 35
        self.http_backoff_sec: int = 5
        self.max_attempts: int = 3

    def login(self) -> bool:
        try:
            from prototype.shoonya_login_v2 import login as shoonya_login
            api, err = shoonya_login()
            if not api:
                self.last_error = str(err or "LOGIN_FAILED")
                return False
            self.api = api
            self.last_error = ""
            return True
        except Exception as e:
            self.last_error = f"LOGIN_EXC: {e}"
            return False

    def get_spot_candles_1h_pack(self) -> Dict[str, Any]:
        """
                # --- Normalize output to CandlePack ---
        # out can be list[dict] OR dict OR already CandlePack
        if isinstance(out, dict) and out.get("stat") == "Ok" and "values" in out:
            # sometimes APIs return dict wrapper
            out = out["values"]

        if isinstance(out, list) and len(out) > 0 and isinstance(out[0], dict):
            # expected list of candle dicts
            last = out[0]  # shoonya gives latest first
            close = float(last.get("intc") or 0.0)
            ssboe = int(last.get("ssboe") or 0)

            return {
                "close": close,
                "last_ssboe": ssboe,
                "rows": out,
            }

        # fallback: return minimal pack
        return {
            "close": None,
            "last_ssboe": 0,
            "rows": [],
            "raw": out,
        }

          {"df": pd.DataFrame, "meta": {"candle_time": str, "ssboe": int}}
        """
        last_err = ""
        for attempt in range(1, self.max_attempts + 1):
            try:
                res: GuardResult = run_with_hard_timeout(timeout_sec=self.hard_timeout_sec)

                if not isinstance(res, GuardResult):
                    raise AdapterError(f"GUARD_BAD_RETURN: {type(res)}")

                if not res.ok:
                    last_err = res.error or "UNKNOWN_GUARD_ERROR"
                    raise AdapterError(last_err)

                if res.df is None or res.meta is None:
                    raise AdapterError("GUARD_MISSING_DATA")

                for col in ("open", "high", "low", "close"):
                    if col not in res.df.columns:
                        raise AdapterError(f"Bad candle df schema: missing {col}")

                return {"df": res.df, "meta": res.meta}

            except Exception as e:
                last_err = str(e)
                self.last_error = last_err
                if attempt < self.max_attempts:
                    time.sleep(self.http_backoff_sec * attempt)
                    continue
                raise AdapterError(f"E_SPOT_CANDLES_FAILED: Failed after retries: {last_err}") from e

        raise AdapterError(f"E_SPOT_CANDLES_FAILED: {last_err}")


# optional legacy helper
def build_df_from_shoonya_series(out2: Any) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    if not isinstance(out2, list) or len(out2) == 0:
        raise AdapterError(f"CANDLES_EMPTY: {out2}")

    newest_raw = _normalize_candle_item(out2[0])
    if not newest_raw:
        raise AdapterError(f"NEWEST_CANDLE_BAD_FORMAT: {type(out2[0])}")

    out_rev = list(reversed(out2))

    rows = []
    for item in out_rev:
        c = _normalize_candle_item(item)
        if not c:
            continue
        rows.append(
            {
                "open": _as_float(c.get("into")),
                "high": _as_float(c.get("inth")),
                "low": _as_float(c.get("intl")),
                "close": _as_float(c.get("intc")),
            }
        )

    df = pd.DataFrame(rows)
    meta = {
        "candle_time": str(newest_raw.get("time", "")),
        "ssboe": int(newest_raw.get("ssboe", 0) or 0),
    }
    return df, meta
