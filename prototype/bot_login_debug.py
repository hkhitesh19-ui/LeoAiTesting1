# prototype/bot_login_debug.py
"""
Debug bot.shoonya_login() safely.

Goal:
- find real failure reason for login_return=False
- do NOT print secrets
"""

import os
import sys
import traceback
from pathlib import Path


def load_env(repo_root: Path):
    env_path = repo_root / ".env"
    if not env_path.exists():
        print("FAIL: .env not found:", env_path)
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def masked_env_status():
    keys = [
        "SHOONYA_USERID",
        "SHOONYA_PASSWORD",
        "SHOONYA_VENDOR_CODE",
        "SHOONYA_API_SECRET",
        "SHOONYA_IMEI",
        "TOTP_SECRET",
    ]
    return {k: ("SET" if os.getenv(k) else "MISSING") for k in keys}


def main():
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))

    load_env(repo_root)

    print("ENV STATUS:", masked_env_status())

    try:
        import bot
        print("OK: bot imported from:", bot.__file__)
        print("INFO: has bot.api:", hasattr(bot, "api"))
        print("INFO: bot.api type:", type(getattr(bot, "api", None)).__name__)
    except Exception as e:
        print("FAIL: bot import error:", e)
        print(traceback.format_exc(limit=10))
        return

    try:
        print("---- calling bot.shoonya_login() ----")
        res = bot.shoonya_login()
        print("login_return:", res, type(res))

        api_obj = getattr(bot, "api", None)
        print("bot.api after login:", type(api_obj).__name__)

        # If API object exists, test minimal quote call capability
        if api_obj is not None:
            # token test: India VIX token 26017
            try:
                if hasattr(api_obj, "get_quotes"):
                    q = api_obj.get_quotes("NSE", "26017")
                    print("OK: api.get_quotes works, keys:", list(q.keys()) if isinstance(q, dict) else type(q))
                else:
                    print("WARN: api has no get_quotes method")
            except Exception as e:
                print("WARN: quote call failed:", e)

        print("DONE")

    except Exception as e:
        print("FAIL: exception calling shoonya_login:", e)
        print(traceback.format_exc(limit=20))


if __name__ == "__main__":
    main()
