"""
SMOKE TEST — PREVIOUS CLOSE FILTER V1
"""

from prototype.prev_close_filter_v1 import check_prev_close

def main():
    print("=== SMOKE TEST: PREV CLOSE FILTER V1 ===")

    print(check_prev_close(25100, 25050))  # ALLOW
    print(check_prev_close(24980, 25050))  # BLOCK

if __name__ == "__main__":
    main()
