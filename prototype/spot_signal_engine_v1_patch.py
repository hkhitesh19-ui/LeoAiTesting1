from prototype.spot_signal_state_recorder_v1 import record_spot_signal
from prototype.spot_signal_engine_v1 import generate_spot_signal as _gen

def generate_spot_signal(*args, **kwargs):
    signal = _gen(*args, **kwargs)
    record_spot_signal(signal)
    return signal
