# prototype/execution_router_v2.py

from datetime import datetime
from prototype.execution_intent_v1 import ExecutionIntent
from prototype.prev_close_filter_v1 import check_prev_close
from prototype.spot_fut_basis_v1 import check_basis
from prototype.vix_gear_v1 import select_gear

def route_execution(spot_signal, vix, prev_close, spot_price, fut_price):
    if spot_signal.signal != "BUY":
        return ExecutionIntent(
            intent="WAIT",
            gear=None,
            reason=f"SpotSignal={spot_signal.signal}",
            ts=datetime.utcnow().isoformat() + "Z"
        )

    prev = check_prev_close(spot_price, prev_close)
    if not prev.allowed:
        return ExecutionIntent(
            intent="WAIT",
            gear=None,
            reason="PrevClose filter blocked",
            ts=datetime.utcnow().isoformat() + "Z"
        )

    basis = check_basis(spot_price, fut_price)
    if not basis.allowed:
        return ExecutionIntent(
            intent="WAIT",
            gear=None,
            reason="Spot–FUT basis blocked",
            ts=datetime.utcnow().isoformat() + "Z"
        )

    gear_ctx = select_gear(vix)

    return ExecutionIntent(
        intent="EXECUTE",
        gear=gear_ctx.gear,
        reason=f"All guards passed → {gear_ctx.gear}",
        ts=datetime.utcnow().isoformat() + "Z"
    )
