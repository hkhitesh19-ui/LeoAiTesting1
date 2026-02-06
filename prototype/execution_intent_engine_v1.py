"""
PHASE 2B — EXECUTION INTENT BUILDER
Combines:
- SpotSignal (Phase 1)
- VixContext (Phase 2A)
"""

from prototype.execution_intent_contracts import ExecutionIntent, now_ts

def build_execution_intent(spot_signal, vix_ctx) -> ExecutionIntent:
    # Spot must explicitly ARM entry
    if spot_signal.signal != "ENTRY_ARMED":
        return ExecutionIntent(
            intent="WAIT",
            gear=None,
            reason=f"SpotSignal={spot_signal.signal}",
            ts=now_ts()
        )

    # Spot OK → use VIX gear
    return ExecutionIntent(
        intent="EXECUTE",
        gear=vix_ctx.gear,
        reason=f"Spot OK + VIX gear {vix_ctx.gear}",
        ts=now_ts()
    )
