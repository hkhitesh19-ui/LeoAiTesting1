"""
PNL ENGINE V1
Computes MTM, Realized PnL, Equity Curve
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json

PNL_FILE = Path("prototype/outputs/pnl_state.json")
EQUITY_FILE = Path("prototype/outputs/equity_curve.jsonl")

@dataclass
class PnLState:
    realized: float
    unrealized: float
    equity: float
    ts: str

def load_pnl() -> PnLState:
    if PNL_FILE.exists():
        return PnLState(**json.loads(PNL_FILE.read_text()))
    return PnLState(0.0, 0.0, 0.0, datetime.now(timezone.utc).isoformat())

def save_pnl(pnl: PnLState):
    PNL_FILE.parent.mkdir(parents=True, exist_ok=True)
    PNL_FILE.write_text(json.dumps(asdict(pnl), indent=2))

def mark_to_market(entry: float, current: float, qty: int) -> float:
    return (current - entry) * qty

def on_tick(entry: float, current: float, qty: int):
    pnl = load_pnl()
    pnl.unrealized = mark_to_market(entry, current, qty)
    pnl.equity = pnl.realized + pnl.unrealized
    pnl.ts = datetime.now(timezone.utc).isoformat()
    save_pnl(pnl)

    EQUITY_FILE.open("a").write(
        json.dumps({"ts": pnl.ts, "equity": pnl.equity}) + "\n"
    )
    return pnl

def on_exit(realized_pnl: float):
    pnl = load_pnl()
    pnl.realized += realized_pnl
    pnl.unrealized = 0.0
    pnl.equity = pnl.realized
    pnl.ts = datetime.now(timezone.utc).isoformat()
    save_pnl(pnl)

    EQUITY_FILE.open("a").write(
        json.dumps({"ts": pnl.ts, "equity": pnl.equity}) + "\n"
    )
    return pnl
