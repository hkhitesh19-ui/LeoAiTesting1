# prototype/main_v5.py
import os
import time
from datetime import datetime, timezone
import pandas as pd

from prototype.config import load_config
from prototype.observability import EventLogger, new_trace_id, ms
from prototype.error_codes import Err
from prototype.paper_broker import PaperBroker
from prototype.trade_log import TradeRow, write_trade_csv
from prototype.shoonya_adapter_v2 import ShoonyaAdapter


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

    st_val = float(st.iloc[-1])
    st_dir = int(dirn.iloc[-1])
    st_prev = int(dirn.iloc[-2]) if len(dirn) > 1 else st_dir
    return st_val, st_dir, st_prev


def run():
    cfg = load_config()
    logger = EventLogger("prototype/outputs/events.jsonl")
    paper = PaperBroker()

    trace_id = new_trace_id()
    logger.log("BOOT", trace_id, {"msg": "prototype v5 starting"})

    broker = ShoonyaAdapter(trace_id=trace_id)
    broker.login()
    logger.log("BROKER_LOGIN_OK", trace_id, {"code": Err.OK})

    last_candle_ts = None
    last_heartbeat = 0

    while True:
        trace_id = new_trace_id()

        try:
            # get raw list too from adapter if available
            spot_df = broker.get_spot_candles_1h()
        except Exception as e:
            logger.log("ERROR", trace_id, {"code": Err.SHOONYA_TIMEOUT, "detail": f"spot candle fetch fail: {e}"})
            time.sleep(3)
            continue

        close = float(spot_df["close"].iloc[-1])

        now = time.time()
        if now - last_heartbeat >= 60:
            last_heartbeat = now
            logger.log("HEARTBEAT", trace_id, {"close": close})

        # candle identity = last row index (monotonic in adapter v2 output)
        candle_id = int(len(spot_df) - 1)
        if last_candle_ts is not None and candle_id == last_candle_ts:
            time.sleep(cfg.poll_sec)
            continue

        last_candle_ts = candle_id

        st_val, st_dir, st_prev = supertrend(spot_df, cfg.st_len, cfg.st_mult)
        rsi_val = float(rsi(spot_df["close"], cfg.rsi_len).iloc[-1])
        ema20 = float(ema(spot_df["close"], cfg.ema_len).iloc[-1])
        atr_val = float(atr(spot_df, cfg.atr_len).iloc[-1])

        cond1 = (st_prev == -1 and st_dir == 1)
        cond2 = (rsi_val < 65)
        cond3 = (close >= st_val)
        cond4 = (close > ema20)

        logger.log("CANDLE_CLOSE_SIGNAL", trace_id, {
            "close": close, "st_val": st_val, "st_dir": st_dir, "st_prev": st_prev,
            "rsi": rsi_val, "ema20": ema20, "atr14": atr_val,
            "conds": [cond1, cond2, cond3, cond4]
        })

        if not (cond1 and cond2 and cond3 and cond4):
            time.sleep(cfg.poll_sec)
            continue

        # ENTRY
        vix = float(broker.get_india_vix())
        fut_symbol, fut_ltp = broker.get_future_ltp()

        trade_id = f"T{ms()}"
        entry_time_utc = utc_now().isoformat()
        hard_sl = float(fut_ltp) - (cfg.sl_atr_mult * float(atr_val))

        paper.place_market(fut_symbol, "BUY", 65, ltp=fut_ltp)

        logger.log("ENTRY_FILLED", trace_id, {
            "trade_id": trade_id, "fut": fut_symbol, "entry": fut_ltp,
            "hard_sl": hard_sl, "vix": vix
        })

        # monitor for 30 sec
        start = time.time()
        fut_exit = fut_ltp
        reason = "TIMEBOX_EXIT"
        while time.time() - start < 30:
            _, ltp2 = broker.get_future_ltp()
            fut_exit = float(ltp2)
            if fut_exit <= hard_sl:
                reason = "SL_INTRABAR"
                break
            time.sleep(1)

        paper.place_market(fut_symbol, "SELL", 65, ltp=fut_exit)
        exit_time_utc = utc_now().isoformat()

        pnl_points = float(fut_exit - fut_ltp)
        pnl_value = pnl_points * 65

        write_trade_csv("prototype/outputs/paper_trades.csv", TradeRow(
            trade_id=trade_id,
            trace_id=trace_id,
            entry_time_utc=entry_time_utc,
            exit_time_utc=exit_time_utc,
            regime="LIVE",
            spot_entry_ref=float(close),
            fut_entry=float(fut_ltp),
            basis=0.0,
            atr_spot=float(atr_val),
            hard_sl_fut=float(hard_sl),
            fut_exit=float(fut_exit),
            pnl_points=float(pnl_points),
            pnl_value=float(pnl_value),
            reason_exit=reason
        ))

        time.sleep(cfg.poll_sec)


if __name__ == "__main__":
    run()
