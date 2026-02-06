"""
PENDING ENTRY STATE ENGINE V1
Ensures execution only at Candle N+1 open
"""

from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass
class PendingEntryState:
    armed_at: str | None = None
    pending: bool = False

def update_pending_entry(state: PendingEntryState, spot_signal, candle_ts: str):
    if spot_signal.signal == "ENTRY_ARMED" and not state.pending:
        state.pending = True
        state.armed_at = candle_ts
        return state, "ARMED"

    if state.pending and candle_ts > state.armed_at:
        return state, "READY"

    return state, "WAIT"
