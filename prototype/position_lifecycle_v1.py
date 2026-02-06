"""
POSITION LIFECYCLE MANAGER V1 (BACKWARD-COMPAT)
Single source of truth for trade state
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
from pathlib import Path

STATE_FILE = Path("prototype/outputs/papertrade_state.json")

@dataclass
class PositionState:
    state: str
    position: str | None
    entry_price: float | None
    entry_ts: str | None
    trades: int

def load_state() -> PositionState:
    if STATE_FILE.exists():
        raw = json.loads(STATE_FILE.read_text())

        # Backward compatibility
        state = raw.get("state", "FLAT")
        return PositionState(
            state=state,
            position=raw.get("position"),
            entry_price=raw.get("entry_price"),
            entry_ts=raw.get("entry_ts"),
            trades=raw.get("trades", 0)
        )

    return PositionState(
        state="FLAT",
        position=None,
        entry_price=None,
        entry_ts=None,
        trades=0
    )

def save_state(state: PositionState):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(asdict(state), indent=2))

def on_entry(position: str, price: float) -> PositionState:
    state = load_state()

    if state.state != "FLAT":
        return state

    now = datetime.now(timezone.utc).isoformat()
    state = PositionState(
        state="ENTERED",
        position=position,
        entry_price=price,
        entry_ts=now,
        trades=state.trades + 1
    )
    save_state(state)
    return state

def on_hold() -> PositionState:
    state = load_state()
    if state.state == "ENTERED":
        state.state = "HOLDING"
        save_state(state)
    return state

def on_exit() -> PositionState:
    state = load_state()
    if state.state in ("ENTERED", "HOLDING"):
        state = PositionState(
            state="FLAT",
            position=None,
            entry_price=None,
            entry_ts=None,
            trades=state.trades
        )
        save_state(state)
    return state
