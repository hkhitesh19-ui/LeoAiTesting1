"""
SMOKE TEST — VIX GEAR SELECTOR
"""

from prototype.vix_gear_engine_v1 import select_gear_from_vix

def main():
    print("=== SMOKE TEST: VIX GEAR SELECTOR V1 ===")

    cases = [
        11.5,   # Low
        14.2,   # Mid
        21.8    # High
    ]

    for vix in cases:
        ctx = select_gear_from_vix(vix)
        print(ctx)

if __name__ == "__main__":
    main()
