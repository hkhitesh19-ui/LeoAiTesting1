# prototype/login_diagnose.py
"""
Diagnose Shoonya login (SAFE):
- loads .env automatically
- ensures repo root is in sys.path so root bot.py can import
- does not print secrets
"""

import os
import sys
import traceback
from pathlib import Path


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_env_from_repo_root(repo_root: Path) -> bool:
    env_path = repo_root / ".env"
    if not env_path.exists():
        print(f"FAIL: .env not found at: {env_path}")
        return False

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and (k not in os.environ):
            os.environ[k] = v

    print("OK: .env loaded into python process (values hidden)")
    return True


def main():
    repo_root = get_repo_root()

    # ensure root imports work (bot.py is in repo root)
    sys.path.insert(0, str(repo_root))
    print("OK: sys.path injected repo root")

    load_env_from_repo_root(repo_root)

    required = [
        "SHOONYA_USERID",
        "SHOONYA_PASSWORD",
        "SHOONYA_VENDOR_CODE",
        "SHOONYA_API_SECRET",
        "SHOONYA_IMEI",
        "TOTP_SECRET",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print("FAIL: missing env keys:", missing)
        return
    print("OK: env keys present")

    # import bot.py
    try:
        import bot
        print("OK: bot imported:", getattr(bot, "__file__", "unknown"))
    except Exception as e:
        print("FAIL: bot import error:", e)
        print(traceback.format_exc(limit=5))
        return

    # run login
    try:
        api = bot.shoonya_login()
        if api is None:
            print("FAIL: bot.shoonya_login returned None")
            return

        print("OK: bot.shoonya_login returned API object:", type(api))

        interesting = ["susertoken", "token", "session_token", "userid"]
        found = {}
        for k in interesting:
            if hasattr(api, k):
                v = getattr(api, k)
                found[k] = ("SET" if v else "EMPTY")
        if found:
            print("INFO: api fields present:", found)

        print("LOGIN DIAG DONE OK")

    except Exception as e:
        print("FAIL: Exception during login:", e)
        print(traceback.format_exc(limit=5))


if __name__ == "__main__":
    main()
