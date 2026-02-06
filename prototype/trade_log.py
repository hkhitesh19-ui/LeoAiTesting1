import csv
from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime

@dataclass
class TradeRow:
    trade_id: str
    trace_id: str
    entry_time_utc: str
    exit_time_utc: str
    regime: str

    spot_entry_ref: float
    fut_entry: float
    basis: float
    atr_spot: float
    hard_sl_fut: float

    fut_exit: float
    pnl_points: float
    pnl_value: float

    reason_exit: str

def write_trade_csv(path: str, row: TradeRow):
    file_exists = False
    try:
        with open(path, "r", encoding="utf-8") as _:
            file_exists = True
    except FileNotFoundError:
        file_exists = False

    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(row).keys()))
        if not file_exists:
            w.writeheader()
        w.writerow(asdict(row))
