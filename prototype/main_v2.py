# prototype/main_v2.py
import time
from datetime import datetime, timezone
import pandas as pd

from prototype.config import load_config
from prototype.observability import EventLogger, new_trace_id, ms
from prototype.error_codes import Err
from prototype.paper_broker import PaperBroker
from prototype.trade_log import TradeRow, write_trade_csv

from prototype.shoonya_adapter_v2 import ShoonyaAdapter, AdapterError


def utc_now():
    return datetime.now(timezone.utc)

def ist_now():
    return datetime.now(timezone.utc).astimezone()

def next_hour_candle_open_ist():
    """
    NSE aligned: 09:15, 10:15, 11:15...
    """
    now = ist_now()

    if now.minute < 15:
        target = now.replace(minute=15, second=0, microsecond=0)
    else:
        hour = now.hour + 1
        if hour >= 24:
            target = now.replace(hour=23, minute=59, second=59, microsecond=0)
        else:
            target = now.replace(hour=hour, minute=15, second=0, microsecond=0)

    return target

def sleep_until(dt_target):
    while True:
        now = ist_now()
        if now >= dt_target:
            return
        time.sleep(0.2)

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
    logger.log("BOOT", trace_id, {"msg": "prototype v2 starting", "capital": cfg.capital})

    broker = ShoonyaAdapter(trace_id=trace_id)

    try:
        broker.login()
    except Exception as e:
        logger.log("ERROR", trace_id, {"code": Err.SHOONYA_LOGIN_FAILED, "detail": str(e)})
        return

    logger.log("BROKER_LOGIN_OK", trace_id, {"code": Err.OK})

    pending_entry = False
    stored_atr = None
    stored_spot_close = None

    in_trade = False
    fut_symbol = None
    fut_entry = None
    hard_sl = None
    trade_id = None
    entry_time_utc = None
    regime = None

    while True:
        trace_id = new_trace_id()

        # 1) signal snapshot
        try:
            spot_df = broker.get_spot_candles_1h()
            if spot_df is None or len(spot_df) < 50:
                logger.log("ERROR", trace_id, {"code": Err.DATA_EMPTY, "detail": "spot candles empty"})
                time.sleep(2)
                continue

            st_val, st_dir, st_prev = supertrend(spot_df, cfg.st_len, cfg.st_mult)
            rsi_val = float(rsi(spot_df["close"], cfg.rsi_len).iloc[-1])
            ema20 = float(ema(spot_df["close"], cfg.ema_len).iloc[-1])
            atr_val = float(atr(spot_df, cfg.atr_len).iloc[-1])
            close = float(spot_df["close"].iloc[-1])

            cond1 = (st_prev == -1 and st_dir == 1)
            cond2 = (rsi_val < 65)
            cond3 = (close >= st_val)
            cond4 = (close > ema20)

            logger.log("SPOT_SIGNAL_SNAPSHOT", trace_id, {
                "close": close, "st_val": st_val, "st_dir": st_dir, "st_prev": st_prev,
                "rsi": rsi_val, "ema20": ema20, "atr14": atr_val,
                "conds": [cond1, cond2, cond3, cond4]
            })

            if (not in_trade) and cond1 and cond2 and cond3 and cond4:
                pending_entry = True
                stored_atr = atr_val
                stored_spot_close = close
                logger.log("PENDING_ENTRY", trace_id, {"msg": "conditions met on spot close", "atr": stored_atr})

        except Exception as e:
            logger.log("ERROR", trace_id, {"code": Err.SHOONYA_BAD_RESPONSE, "detail": str(e)})
            time.sleep(2)
            continue

        # 2) execute next candle open
        if pending_entry and (not in_trade):
            target_open = next_hour_candle_open_ist()
            sleep_until(target_open)
            time.sleep(cfg.exec_delay_sec)

            try:
                vix = float(broker.get_india_vix())
                fut_symbol, fut_ltp = broker.get_future_ltp()
            except Exception as e:
                logger.log("ERROR", trace_id, {"code": Err.SHOONYA_TIMEOUT, "detail": f"entry fetch fail: {e}"})
                pending_entry = False
                continue

            hard_sl = float(fut_ltp) - (cfg.sl_atr_mult * float(stored_atr))

            regime = "FUT_PUT_HEDGE" if vix >= cfg.vix_low_threshold else "RATIO_SPREAD"

            logger.log("ENTRY_DECISION", trace_id, {
                "vix": vix, "regime": regime, "fut_symbol": fut_symbol,
                "fut_entry": fut_ltp, "atr_spot": stored_atr, "hard_sl": hard_sl
            })

            trade_id = f"T{ms()}"
            entry_time_utc = utc_now().isoformat()

            paper.place_market(fut_symbol, "BUY", 65, ltp=fut_ltp)

            in_trade = True
            pending_entry = False
            fut_entry = float(fut_ltp)

            logger.log("ENTRY_FILLED", trace_id, {
                "trade_id": trade_id, "fut_symbol": fut_symbol, "fut_entry": fut_entry,
                "hard_sl": hard_sl
            })

        # 3) SL monitor
        if in_trade:
            try:
                _, fut_ltp = broker.get_future_ltp()
                fut_ltp = float(fut_ltp)
            except Exception as e:
                logger.log("ERROR", trace_id, {"code": Err.DATA_STALE, "detail": f"monitor fetch fail: {e}"})
                time.sleep(1)
                continue

            if hard_sl is not None and fut_ltp <= hard_sl:
                logger.log("SL_HIT", trace_id, {"fut_ltp": fut_ltp, "hard_sl": hard_sl})

                paper.place_market(fut_symbol, "SELL", 65, ltp=fut_ltp)

                exit_time_utc = utc_now().isoformat()
                pnl_points = fut_ltp - fut_entry
                pnl_value = pnl_points * 65

                write_trade_csv("prototype/outputs/paper_trades.csv", TradeRow(
                    trade_id=trade_id,
                    trace_id=trace_id,
                    entry_time_utc=entry_time_utc,
                    exit_time_utc=exit_time_utc,
                    regime=regime,
                    spot_entry_ref=float(stored_spot_close or 0.0),
                    fut_entry=float(fut_entry),
                    basis=float(fut_entry - float(stored_spot_close or fut_entry)),
                    atr_spot=float(stored_atr or 0.0),
                    hard_sl_fut=float(hard_sl),
                    fut_exit=float(fut_ltp),
                    pnl_points=float(pnl_points),
                    pnl_value=float(pnl_value),
                    reason_exit="SL_INTRABAR"
                ))

                in_trade = False
                fut_entry = None
                hard_sl = None
                trade_id = None
                regime = None

        time.sleep(cfg.poll_sec)


if __name__ == "__main__":
    run()
