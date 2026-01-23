# prototype/inspect_searchscrip.py
"""
Inspect Shoonya searchscrip response for resolving NIFTY current month FUT.
SAFE: prints only instrument metadata, no secrets.
"""

from prototype.shoonya_login_v2 import login


def main():
    api, err = login()
    if not api:
        print("LOGIN FAIL:", err)
        return

    res = api.searchscrip("NFO", "NIFTY")

    print("TYPE:", type(res))
    if isinstance(res, dict):
        print("TOP_KEYS:", list(res.keys()))
        vals = res.get("values") or []
        print("values_count:", len(vals))

        for i, v in enumerate(vals[:25]):
            if isinstance(v, dict):
                # show only important keys
                keys = list(v.keys())
                slim = {k: v.get(k) for k in keys if k in ["tsym","token","symname","instname","dname","exch","expiry","optt","strprc"]}
                # fallback if slim empty
                if not slim:
                    slim = {k: v.get(k) for k in keys[:12]}
                print(f"[{i}] keys={keys}")
                print(f"    item={slim}")
            else:
                print(f"[{i}] NONDICT:", v)

    else:
        print("RAW:", res)


if __name__ == "__main__":
    main()
