"""
SMOKE TEST — SPOT FUT BASIS GUARD V1
"""

from prototype.spot_fut_basis_guard_v1 import check_spot_fut_basis

def main():
    print("=== SMOKE TEST: SPOT–FUT BASIS V1 ===")

    print(check_spot_fut_basis(25000, 25025))  # ALLOW
    print(check_spot_fut_basis(25000, 25100))  # BLOCK

if __name__ == "__main__":
    main()
