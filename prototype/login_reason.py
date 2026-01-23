# prototype/login_reason.py
"""
Get Shoonya login failure reason from bot.trade_data["last_error"] (SAFE).
"""

import os
import sys
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


def main():
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))
    load_env(repo_root)

    import bot

    ok = bot.shoonya_login()
    print("login_ok:", ok)

    td = getattr(bot, "trade_data", {})
    last_error = td.get("last_error", None) if isinstance(td, dict) else None
    print("last_error:", last_error)


if __name__ == "__main__":
    main()
