# prototype/smoke_run.py
"""
Smoke test for prototype:
- login
- fetch VIX
- fetch FUT LTP
- place paper entry
- force SL hit immediately
- write paper_trades.csv
"""

import time
from datetime import datetime, timezone

from prototype.observability import EventLogger, new_trace_id, ms
from prototype.paper_broker import PaperBroker
from prototype.trade_log import TradeRow, write_trade_csv
from prototype.shoonya_adapter import ShoonyaAdapter


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def main():
    trace_id = new_trace_id()
    logger = EventLogger("prototype/outputs/events.jsonl")
    paper = PaperBroker()

    api = ShoonyaAdapter(trace_id=trace_id)
    logger.log("SMOKE_BOOT", trace_id, {"msg": "smoke test start"})

    api.login()
    vix = api.get_india_vix()
    fut_symbol, fut_ltp = api.get_future_ltp()

    logger.log("SMOKE_BROKER_OK", trace_id, {"vix": vix, "fut_symbol": fut_symbol, "fut_ltp": fut_ltp})

    trade_id = f"SMOKE_{ms()}"
    entry_time = utc_now()

    # entry
    paper.place_market(fut_symbol, "BUY", 65, ltp=fut_ltp)

    # force SL hit
    hard_sl = fut_ltp - 10
    fut_exit = hard_sl - 1  # forced breach

    # exit
    paper.place_market(fut_symbol, "SELL", 65, ltp=fut_exit)

    exit_time = utc_now()
    pnl_points = fut_exit - fut_ltp
    pnl_value = pnl_points * 65

    write_trade_csv("prototype/outputs/paper_trades.csv", TradeRow(
        trade_id=trade_id,
        trace_id=trace_id,
        entry_time_utc=entry_time,
        exit_time_utc=exit_time,
        regime="SMOKE",
        spot_entry_ref=0.0,
        fut_entry=float(fut_ltp),
        basis=0.0,
        atr_spot=0.0,
        hard_sl_fut=float(hard_sl),
        fut_exit=float(fut_exit),
        pnl_points=float(pnl_points),
        pnl_value=float(pnl_value),
        reason_exit="SMOKE_SL"
    ))

    logger.log("SMOKE_DONE", trace_id, {"trade_id": trade_id, "pnl_value": pnl_value})
    print("OK: smoke test completed, CSV written")


if __name__ == "__main__":
    main()
