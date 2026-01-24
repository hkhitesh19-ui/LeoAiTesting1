"""
SMOKE TEST — EXECUTION INTENT BUILDER V1
"""

from types import SimpleNamespace
from prototype.execution_intent_engine_v1 import build_execution_intent
from prototype.vix_gear_engine_v1 import select_gear_from_vix

def main():
    print("=== SMOKE TEST: EXECUTION INTENT V1 ===")

    # Case 1: Spot not armed
    spot_wait = SimpleNamespace(signal="WAIT")
    vix_mid = select_gear_from_vix(14.5)

    out1 = build_execution_intent(spot_wait, vix_mid)
    print(out1)

    # Case 2: Spot armed
    spot_arm = SimpleNamespace(signal="ENTRY_ARMED")
    out2 = build_execution_intent(spot_arm, vix_mid)
    print(out2)

if __name__ == "__main__":
    main()
