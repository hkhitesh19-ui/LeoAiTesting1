"""
SMOKE TEST — EXECUTION INTENT ROUTER V2
"""

from prototype.execution_intent_router_v2 import route_execution

def main():
    print("=== SMOKE TEST: EXECUTION ROUTER V2 ===")

    print(route_execution(
        pending_ok=True,
        prev_close_ok=True,
        basis_ok=True,
        vix_gear="SAFE_FUTURE"
    ))

    print(route_execution(
        pending_ok=True,
        prev_close_ok=False,
        basis_ok=True,
        vix_gear="SAFE_FUTURE"
    ))

if __name__ == "__main__":
    main()
