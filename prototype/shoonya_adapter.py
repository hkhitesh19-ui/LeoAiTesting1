    def get_spot_candles_1h(self) -> pd.DataFrame:
        """
        Real NIFTY spot 1H candles from Shoonya.

        Token:
          NSE NIFTY spot index = 26000
        Fields mapping:
          into=open, inth=high, intl=low, intc=close
        """
        if not self.api:
            raise AdapterError("E_NOT_LOGGED_IN", "Must login first")

        if not hasattr(self.api, "get_time_price_series"):
            raise AdapterError("E_CANDLE_METHOD_MISSING", "api.get_time_price_series not available")

        import time as _time

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

        # required columns present?
        needed = ["ssboe", "into", "inth", "intl", "intc"]
        for c in needed:
            if c not in df.columns:
                raise AdapterError("E_CANDLE_SCHEMA", f"missing candle column: {c}", {"cols": list(df.columns)})

        # convert numeric
        for c in ["ssboe", "into", "inth", "intl", "intc"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        df = df.dropna(subset=["ssboe", "into", "inth", "intl", "intc"])

        # sort oldest -> newest
        df = df.sort_values("ssboe").reset_index(drop=True)

        # rename to strategy schema
        df = df.rename(columns={
            "into": "open",
            "inth": "high",
            "intl": "low",
            "intc": "close",
        })

        return df[["open", "high", "low", "close"]]
