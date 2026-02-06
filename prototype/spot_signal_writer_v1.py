import json
from pathlib import Path

STATE_FILE = Path('prototype/outputs/spot_signal_state.json')

def record_spot_signal(signal):
    STATE_FILE.write_text(json.dumps(signal, indent=2, default=str))
