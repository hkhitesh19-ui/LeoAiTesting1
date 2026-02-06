import json
from pathlib import Path

STATE_FILE = Path('prototype/outputs/spot_signal_state.json')

def load_last_spot_signal():
    if not STATE_FILE.exists():
        return None
    return json.loads(STATE_FILE.read_text())
