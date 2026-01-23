# prototype/shoonya_adapter_v2.py
"""
Shoonya Adapter V2 (prototype) - clean stable file.

Features:
- login (shoonya_login_v2)
- India VIX
- current month NIFTY FUT resolver
- FUT LTP
- Spot NIFTY 1H candles via get_time_price_series
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
import pandas as pd
import time as _time

from prototype.shoonya_login_v2 import login as shoonya_login_v2


class AdapterError(Exception):
    def __init__(self, code: str, msg: str, detail: Optional[dict] = None):
        super().__init__(f"{code}: {msg}")
        self.code = code
        self.msg = msg
        self.detail = detail or {}


class ShoonyaAdapter:
    def __init__(self, trace_id: str = ""):
        self.trace_id = trace_id
        self.api = None
        self._fut_cache = None  # (tsym, token)

    def login(self):
        api, err = shoonya_login_v2()
        if not api:
            raise AdapterError("E_LOGIN_FAIL", err or "login failed")
        self.api = api
        return api

    def get_quote(self, exch: str, token: str) -> Dict[str, Any]:
        if not self.api:
            raise AdapterError("E_NOT_LOGGED_IN", "Must login first")

        if not hasattr(self.api, "get_quotes"):
            raise AdapterError("E_QUOTE_METHOD", "NorenApi missing get_quotes()")

        q = self.api.get_quotes(exch, token)
        if not isinstance(q, dict):
            raise AdapterError("E_QUOTE_BAD", "Quote not dict", {"type": str(type(q))})
        return q

    def _extract_ltp(self, q: Dict[str, Any]) -> Optional[float]:
        for k in ("lp", "ltp", "LTP", "last_price", "lastPrice", "c", "close"):
            if k in q and q[k] not in (None, ""):
                try:
                    return float(q[k])
                except Exception:
                    return None
        return None

    def get_india_vix(self) -> float:
        q = self.get_quote("NSE", "26017")
        ltp = self._extract_ltp(q)
        if ltp is None:
            raise AdapterError("E_VIX_PARSE", "VIX parse failed", {"keys": list(q.keys())})
        return float(ltp)

    def resolve_current_month_nifty_fut(self) -> Tuple[str, str]:
        if self._fut_cache:
            return self._fut_cache

        if not self.api:
            raise AdapterError("E_NOT_LOGGED_IN", "Must login first")

        res = self.api.searchscrip("NFO", "NIFTY")
        if not isinstance(res, dict) or "values" not in res:
            raise AdapterError("E_SEARCH_BAD", "searchscrip bad response", {"type": str(type(res))})

        values = res.get("values") or []
        if not values:
            raise AdapterError("E_SEARCH_EMPTY", "searchscrip returned empty list")

        candidates = []
        for v in values:
            if not isinstance(v, dict):
                continue
            inst = (v.get("instname") or "").upper()
            symname = (v.get("symname") or "").upper()
            tsym = (v.get("tsym") or "").upper()
            token = (v.get("token") or "")
            exd = (v.get("exd") or "")

            if inst == "FUTIDX" and symname == "NIFTY" and tsym.startswith("NIFTY") and tsym.endswith("F") and token:
                candidates.append((exd, tsym, token))

        if not candidates:
            raise AdapterError("E_FUT_NOT_FOUND", "No NIFTY FUTIDX found", {"seen": len(values)})

        candidates.sort(key=lambda x: x[0])
        _, tsym, token = candidates[0]

        self._fut_cache = (tsym, token)
        return self._fut_cache

    def get_future_ltp(self) -> Tuple[str, float]:
        tsym, token = self.resolve_current_month_nifty_fut()
        q = self.get_quote("NFO", token)
        ltp = self._extract_ltp(q)
        if ltp is None:
            raise AdapterError("E_FUT_LTP_PARSE", "Unable to parse FUT LTP", {"keys": list(q.keys())})
        return tsym, float(ltp)

    def get_spot_candles_1h(self) -> pd.DataFrame:
        if not self.api:
            raise AdapterError("E_NOT_LOGGED_IN", "Must login first")

        if not hasattr(self.api, "get_time_price_series"):
            raise AdapterError("E_CANDLE_METHOD_MISSING", "api.get_time_price_series not available")

        now = int(_time.time())
        frm = now - (15 * 24 * 3600)

        out = self.api.get_time_price_series(
            exchange="NSE",
            token="26000",
            starttime=str(frm),
            endtime=str(now),
            interval="60"
        )

        if not isinstance(out, list) or len(out) == 0:
            raise AdapterError("E_CANDLE_EMPTY", "spot candle response empty", {"type": str(type(out))})

        df = pd.DataFrame(out)

        needed = ["ssboe", "into", "inth", "intl", "intc"]
        for c in needed:
            if c not in df.columns:
                raise AdapterError("E_CANDLE_SCHEMA", f"missing candle column: {c}", {"cols": list(df.columns)})

        for c in ["ssboe", "into", "inth", "intl", "intc"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        df = df.dropna(subset=needed)
        df = df.sort_values("ssboe").reset_index(drop=True)

        df = df.rename(columns={"into": "open", "inth": "high", "intl": "low", "intc": "close"})
        return df[["open", "high", "low", "close"]]
