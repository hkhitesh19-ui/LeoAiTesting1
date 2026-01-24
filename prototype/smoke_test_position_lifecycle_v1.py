"""
SMOKE TEST — POSITION LIFECYCLE V1
"""

from prototype.position_lifecycle_v1 import (
    on_entry, on_hold, on_exit, load_state
)

def main():
    print("=== SMOKE TEST: POSITION LIFECYCLE V1 ===")

    print("ENTRY:", on_entry("PUT", 25064.75))
    print("HOLD:", on_hold())
    print("EXIT:", on_exit())
    print("FINAL:", load_state())

if __name__ == "__main__":
    main()
