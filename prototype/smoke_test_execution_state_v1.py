from prototype.execution_state_recorder_v1 import record_execution_state, load_execution_state

def main():
    print("=== SMOKE TEST: EXECUTION STATE RECORDER V1 ===")

    record_execution_state(
        status="WAIT",
        gear=None,
        reason="SpotSignal=WAIT"
    )

    state = load_execution_state()
    print(state)

if __name__ == "__main__":
    main()
