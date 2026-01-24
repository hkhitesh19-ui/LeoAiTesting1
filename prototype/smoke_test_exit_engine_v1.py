"""
SMOKE TEST — EXIT ENGINE V1
"""

from prototype.exit_engine_v1 import evaluate_exit

def main():
    print("=== SMOKE TEST: EXIT ENGINE V1 ===")

    print(evaluate_exit(
        risk_exit=True,
        signal_exit=True
    ))

    print(evaluate_exit(
        risk_exit=False,
        signal_exit=True
    ))

    print(evaluate_exit(
        risk_exit=False,
        signal_exit=False
    ))

if __name__ == "__main__":
    main()
