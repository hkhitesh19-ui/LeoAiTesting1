# prototype/inspect_candle_methods.py
from prototype.shoonya_login_v2 import login

def main():
    api, err = login()
    if not api:
        print("LOGIN FAIL:", err)
        return

    methods = [m for m in dir(api) if "series" in m.lower() or "time" in m.lower() or "candle" in m.lower()]
    print("CANDLE RELATED METHODS:", methods)

if __name__ == "__main__":
    main()
