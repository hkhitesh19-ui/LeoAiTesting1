from __future__ import annotations

import time
from typing import Any, Dict, Optional

from prototype.config import load_config
from prototype.contracts import CandlePack
from prototype.contract_guard import ensure_candlepack
from prototype.shoonya_login_v2 import login


class AdapterError(RuntimeError):
    pass


class ShoonyaAdapterV4:
    """
    PRODUCTION CONTRACT (V4):
    - get_spot_candles_1h_pack() ALWAYS returns CandlePack
    - no dict/list mixed outputs
    - close never None
    - last_ssboe never None
    """

    def __init__(self) -> None:
        self.cfg = load_config()
        self.api = None
        self.last_error: str = ""
        self.max_attempts: int = 3
        self.http_backoff_sec: int = 2

    def login(self) -> bool:
        api, err = login()
        if not api or err:
            self.last_error = str(err or "LOGIN_FAILED")
            return False
        self.api = api
        return True

    def _need_api(self):
        if self.api is None:
            raise AdapterError("NOT_LOGGED_IN")

    def get_spot_candles_1h_pack(self, lookback_hours: int = 72) -> CandlePack:
        """
        Fetch NIFTY spot candles (1h interval) using Shoonya get_time_price_series.
        STRICT: returns CandlePack always.
        """
        self._need_api()

        token = str(getattr(self.cfg, "nifty_spot_token", "") or "")
        if not token:
            raise AdapterError("CONFIG_MISSING_TOKEN")

        exchange = "NSE"
        interval = "60"

        # start time: now - lookback_hours
        now = int(time.time())
        start = now - (lookback_hours * 3600)

        meta: Dict[str, Any] = {
            "exchange": exchange,
            "token": token,
            "interval": interval,
            "lookback_hours": lookback_hours,
        }

        last_err: Optional[str] = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                out = self.api.get_time_price_series(
                    exchange=exchange,
                    token=token,
                    starttime=str(start),
                    interval=interval,
                )

                # normalize (list/dict wrapper) into CandlePack
                pack = ensure_candlepack(out, meta=meta)

                # HARD CONTRACT asserts
                if pack.close is None:
                    raise AdapterError("CONTRACT_BROKEN: close is None")
                if pack.last_ssboe is None:
                    raise AdapterError("CONTRACT_BROKEN: last_ssboe is None")

                return pack

            except Exception as e:
                last_err = str(e)
                self.last_error = last_err
                if attempt < self.max_attempts:
                    time.sleep(self.http_backoff_sec * attempt)
                    continue
                raise AdapterError(f"E_SPOT_CANDLES_FAILED: {last_err}") from e

        raise AdapterError(f"E_SPOT_CANDLES_FAILED: {last_err}")