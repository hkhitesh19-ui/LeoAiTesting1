"""
TRADE ORCHESTRATOR V1
Single authoritative decision loop
"""

from datetime import datetime, timezone

from prototype.spot_signal_engine_v1 import SpotSignal
from prototype.vix_gear_selector_v1 import select_gear
from prototype.execution_router_v2 import route_execution
from prototype.order_basket_v1 import build_order_basket
from prototype.position_lifecycle_v1 import on_entry, on_exit, load_state
from prototype.pnl_engine_v1 import on_tick, on_exit as pnl_exit
from prototype.exit_engine_v1 import evaluate_exit
from prototype.risk_governor_v1 import evaluate_risk

def orchestrate(context: dict):
    """
    context must contain:
    spot_signal, vix, prices, qty, capital
    """
    state = load_state()

    # ENTRY LOGIC
    if state.state == "FLAT":
        sig: SpotSignal = context["spot_signal"]
        if sig.signal != "BUY":
            return {"status": "WAIT", "reason": "SpotSignal=WAIT"}

        intent = route_execution(context)
        if intent.intent != "EXECUTE":
            return {"status": "WAIT", "reason": intent.reason}

        basket = build_order_basket(intent.gear, context["prices"]["spot"])
        new_state = on_entry(intent.gear, context["prices"]["spot"])

        return {
            "status": "ENTERED",
            "basket": basket,
            "state": new_state
        }

    # POSITION MANAGEMENT
    if state.state in ("ENTERED", "HOLDING"):
        pnl = on_tick(
            entry=state.entry_price,
            current=context["prices"]["spot"],
            qty=context["qty"]
        )

        risk = evaluate_risk(context)
        exit_decision = evaluate_exit(context)

        if risk.exit_now or exit_decision.exit:
            pnl_exit(pnl.realized)
            final_state = on_exit()
            return {
                "status": "EXITED",
                "reason": risk.reason or exit_decision.reason,
                "state": final_state
            }

        return {
            "status": "HOLDING",
            "pnl": pnl,
            "state": state
        }
