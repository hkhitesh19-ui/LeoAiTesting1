# prototype/inspect_nifty_spot_token.py
from prototype.shoonya_login_v2 import login

def main():
    api, err = login()
    if not api:
        print("LOGIN FAIL:", err)
        return

    res = api.searchscrip("NSE", "NIFTY")
    print("TOP_KEYS:", list(res.keys()) if isinstance(res, dict) else type(res))
    vals = (res.get("values") or []) if isinstance(res, dict) else []
    print("values_count:", len(vals))

    for i, v in enumerate(vals[:20]):
        if isinstance(v, dict):
            print(i, {k: v.get(k) for k in ["exch","token","tsym","dname","instname","symname"] if k in v})
        else:
            print(i, v)

if __name__ == "__main__":
    main()
