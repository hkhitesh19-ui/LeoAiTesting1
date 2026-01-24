from prototype.execution_state_recorder_v1 import record_execution_state
from prototype.execution_state_endpoint_v1 import get_execution_state

def main():
    print('=== SMOKE TEST: EXECUTION STATE ENDPOINT V1 ===')

    record_execution_state(
        status='WAIT',
        gear=None,
        reason='SpotSignal=WAIT'
    )

    resp = get_execution_state()
    print(resp)

if __name__ == '__main__':
    main()
