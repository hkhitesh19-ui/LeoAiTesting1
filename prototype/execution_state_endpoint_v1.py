from prototype.execution_state_recorder_v1 import load_execution_state

def get_execution_state():
    state = load_execution_state()
    if state is None:
        return {
            'status': 'UNKNOWN',
            'gear': None,
            'reason': 'No execution state recorded yet',
            'ts': None
        }
    return state.__dict__
