"""
SMOKE TEST — PENDING ENTRY ENGINE V1
"""

from prototype.pending_entry_engine_v1 import PendingEntryState, update_pending_entry
from types import SimpleNamespace

def main():
    print("=== SMOKE TEST: PENDING ENTRY V1 ===")

    state = PendingEntryState()
    sig = SimpleNamespace(signal="ENTRY_ARMED")

    t1 = "2026-01-24T10:00:00Z"
    state, out1 = update_pending_entry(state, sig, t1)
    print(out1, state)

    t2 = "2026-01-24T11:00:00Z"
    state, out2 = update_pending_entry(state, sig, t2)
    print(out2, state)

if __name__ == "__main__":
    main()
