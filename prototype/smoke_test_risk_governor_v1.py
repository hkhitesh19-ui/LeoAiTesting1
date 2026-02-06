"""
SMOKE TEST — RISK GOVERNOR V1
"""

from prototype.risk_governor_v1 import check_risk

def main():
    print("=== SMOKE TEST: RISK GOVERNOR V1 ===")

    print(check_risk(
        gear="RATIO_SPREAD",
        capital=125000,
        mtm_loss=6000
    ))

    print(check_risk(
        gear="SAFE_FUTURE",
        capital=125000,
        fut_price=24980,
        fut_entry=25100,
        atr=50
    ))

if __name__ == "__main__":
    main()
