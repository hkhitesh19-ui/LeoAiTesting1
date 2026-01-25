from prototype.spot_signal_contracts import SpotSignal
from prototype.spot_signal_state_recorder_v1 import record_spot_signal
from datetime import datetime

def generate_spot_signal(
    close,
    ema20,
    rsi19,
    supertrend,
    supertrend_prev_red
):
    if (
        supertrend == 'GREEN'
        and not supertrend_prev_red
        and rsi19 < 65
        and close > ema20
    ):
        signal = SpotSignal(
            signal='READY',
            reason='Trend aligned',
            spot_close=close,
            ema20=ema20,
            rsi19=rsi19,
            supertrend=supertrend,
            ts=datetime.utcnow().isoformat() + 'Z'
        )
    else:
        signal = SpotSignal(
            signal='WAIT',
            reason='Trend conditions not satisfied',
            spot_close=close,
            ema20=ema20,
            rsi19=rsi19,
            supertrend=supertrend,
            ts=datetime.utcnow().isoformat() + 'Z'
        )

    record_spot_signal(signal)
    return signal
