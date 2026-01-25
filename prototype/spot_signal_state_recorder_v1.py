import json
from pathlib import Path
from prototype.spot_signal_contracts import SpotSignal

STATE_FILE = Path('prototype/outputs/spot_signal_state.json')

def record_spot_signal(signal: SpotSignal):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(signal.__dict__, indent=2))

def load_last_spot_signal():
    if not STATE_FILE.exists():
        return None
    return json.loads(STATE_FILE.read_text())
