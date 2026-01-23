# prototype/main_v6.py
import time
from datetime import datetime, timezone
import pandas as pd

from prototype.config import load_config
from prototype.observability import EventLogger, new_trace_id, ms
from prototype.error_codes import Err
from prototype.paper_broker import PaperBroker
from prototype.trade_log import TradeRow, write_trade_csv

from prototype.shoonya_adapter_v3 import ShoonyaAdapter, AdapterError


def utc_now():
    return datetime.now(timezone.utc)

def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

def rsi(close, length=14):
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    avg_gain = up.ewm(alpha=1/length, adjust=False).mean()
    avg_loss = down.ewm(alpha=1/length, adjust=False).mean()
    rs = avg_gain / (avg_loss.replace(0, 1e-9))
    return 100 - (100 / (1 + rs))

def atr(df, length=14):
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/length, adjust=False).mean()

def supertrend(df, period=21, multiplier=1.1):
    _atr = atr(df, period)
    hl2 = (df["high"] + df["low"]) / 2.0
    upperband = hl2 + multiplier * _atr
    lowerband = hl2 - multiplier * _atr

    final_ub = upperband.copy()
    final_lb = lowerband.copy()
    close = df["close"]

    for i in range(1, len(df)):
        if upperband.iloc[i] < final_ub.iloc[i-1] or close.iloc[i-1] > final_ub.iloc[i-1]:
            final_ub.iloc[i] = upperband.iloc[i]
        else:
            final_ub.iloc[i] = final_ub.iloc[i-1]

        if lowerband.iloc[i] > final_lb.iloc[i-1] or close.iloc[i-1] < final_lb.iloc[i-1]:
            final_lb.iloc[i] = lowerband.iloc[i]
        else:
            final_lb.iloc[i] = final_lb.iloc[i-1]

    st = pd.Series(index=df.index, dtype="float64")
    dirn = pd.Series(index=df.index, dtype="int64")
    st.iloc[0] = final_lb.iloc[0]
    dirn.iloc[0] = 1

    for i in range(1, len(df)):
        if st.iloc[i-1] == final_ub.iloc[i-1]:
            if close.iloc[i] <= final_ub.iloc[i]:
                st.iloc[i] = final_ub.iloc[i]
                dirn.iloc[i] = -1
            else:
                st.iloc[i] = final_lb.iloc[i]
                dirn.iloc[i] = 1
        else:
            if close.iloc[i] >= final_lb.iloc[i]:
                st.iloc[i] = final_lb.iloc[i]
                dirn.iloc[i] = 1
            else:
                st.iloc[i] = final_ub.iloc[i]
                dirn.iloc[i] = -1

    return float(st.iloc[-1]), int(dirn.iloc[-1]), int(dirn.iloc[-2]) if len(dirn) > 1 else int(dirn.iloc[-1])


def run():
    cfg = load_config()
    logger = EventLogger("prototype/outputs/events.jsonl")
    paper = PaperBroker()

    trace_id = new_trace_id()
    logger.log("BOOT", trace_id, {"msg": "prototype v6 starting (timestamp candle detection)"})

    broker = ShoonyaAdapter(trace_id=trace_id)
    broker.login()
    logger.log("BROKER_LOGIN_OK", trace_id, {"code": Err.OK})

    last_ssboe = None
    last_heartbeat = 0

    while True:
        trace_id = new_trace_id()

        try:
            pack = broker.get_spot_candles_1h_pack(bars=70)
            spot_df = pack.df
            close = float(spot_df["close"].iloc[-1])
        except Exception as e:
            logger.log("ERROR", trace_id, {"code": Err.SHOONYA_TIMEOUT, "detail": f"spot candle fail: {e}"})
            time.sleep(3)
            continue

        # heartbeat each minute
        now = time.time()
        if now - last_heartbeat >= 60:
            last_heartbeat = now
            logger.log("HEARTBEAT", trace_id, {"close": close, "last_candle_time": pack.last_candle_time})

        # true candle close identity
        if last_ssboe is not None and pack.last_ssboe == last_ssboe:
            time.sleep(cfg.poll_sec)
            continue

        last_ssboe = pack.last_ssboe

        st_val, st_dir, st_prev = supertrend(spot_df, cfg.st_len, cfg.st_mult)
        rsi_val = float(rsi(spot_df["close"], cfg.rsi_len).iloc[-1])
        ema20 = float(ema(spot_df["close"], cfg.ema_len).iloc[-1])
        atr_val = float(atr(spot_df, cfg.atr_len).iloc[-1])

        cond1 = (st_prev == -1 and st_dir == 1)
        cond2 = (rsi_val < 65)
        cond3 = (close >= st_val)
        cond4 = (close > ema20)

        logger.log("CANDLE_CLOSE_SIGNAL", trace_id, {
            "candle_time": pack.last_candle_time,
            "ssboe": pack.last_ssboe,
            "close": close, "st_val": st_val, "st_dir": st_dir, "st_prev": st_prev,
            "rsi": rsi_val, "ema20": ema20, "atr14": atr_val,
            "conds": [cond1, cond2, cond3, cond4]
        })

        time.sleep(cfg.poll_sec)


if __name__ == "__main__":
    run()
