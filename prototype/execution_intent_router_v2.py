"""
EXECUTION INTENT ROUTER V2
Single source of truth for execution decision
"""

from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass
class ExecutionIntent:
    intent: str           # EXECUTE / WAIT
    gear: str | None
    reason: str
    ts: str

def route_execution(
    pending_ok: bool,
    prev_close_ok: bool,
    basis_ok: bool,
    vix_gear: str | None
):
    ts = datetime.now(timezone.utc).isoformat()

    if not pending_ok:
        return ExecutionIntent("WAIT", None, "PendingEntry not armed", ts)

    if not prev_close_ok:
        return ExecutionIntent("WAIT", None, "PrevClose filter blocked", ts)

    if not basis_ok:
        return ExecutionIntent("WAIT", None, "Spot–Fut basis exceeded", ts)

    if not vix_gear:
        return ExecutionIntent("WAIT", None, "VIX gear unavailable", ts)

    return ExecutionIntent(
        intent="EXECUTE",
        gear=vix_gear,
        reason=f"All guards passed → {vix_gear}",
        ts=ts
    )
