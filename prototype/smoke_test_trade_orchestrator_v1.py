from prototype.trade_orchestrator_v1 import orchestrate
from prototype.spot_signal_engine_v1 import SpotSignal

def main():
    print("=== SMOKE TEST: TRADE ORCHESTRATOR V1 ===")

    ctx = {
        "spot_signal": SpotSignal(
            signal="WAIT",
            reason="No trend",
            spot_close=25064,
            ema20=25215,
            rsi19=58,
            supertrend=25180,
            ts="2026-01-24T13:00:00Z"
        ),
        "vix": 14.2,
        "prices": {"spot": 25064},
        "qty": 1,
        "capital": 125000
    }

    print(orchestrate(ctx))

if __name__ == "__main__":
    main()
