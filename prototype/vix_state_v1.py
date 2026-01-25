import json
from pathlib import Path

STATE_FILE = Path('prototype/outputs/vix_state.json')

def load_last_vix_context():
    if not STATE_FILE.exists():
        return None
    return json.loads(STATE_FILE.read_text())
