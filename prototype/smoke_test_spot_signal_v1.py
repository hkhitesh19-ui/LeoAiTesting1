"""
SMOKE TEST — SPOT SIGNAL ENGINE V1
"""

from prototype.spot_signal_engine_v1 import generate_spot_signal

def main():
    print("=== SMOKE TEST: SPOT SIGNAL ENGINE V1 ===")

    # Example from 24 Jan 2026 (NO TRADE case)
    spot_close = 25064
    ema20 = 25215
    rsi19 = 58
    supertrend = 25180
    st_prev_red = True

    sig = generate_spot_signal(
        close=spot_close,
        ema20=ema20,
        rsi19=rsi19,
        supertrend=supertrend,
        supertrend_prev_red=st_prev_red
    )

    assert sig.signal == "WAIT", "Expected WAIT signal"
    print("PASS:", sig)

if __name__ == "__main__":
    main()
