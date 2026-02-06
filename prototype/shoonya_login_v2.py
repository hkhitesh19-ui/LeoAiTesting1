# prototype/shoonya_login_v2.py
"""
Shoonya login (v2) for NorenRestApiPy 0.0.22
- Loads .env automatically from repo root
- Uses NorenApi(host=..., websocket=...)
SAFE: no secrets printed
"""

import os
from pathlib import Path
import pyotp
from NorenRestApiPy.NorenApi import NorenApi


DEFAULT_HOST = "https://api.shoonya.com/NorenWClientTP/"
DEFAULT_WS   = "wss://api.shoonya.com/NorenWSTP/"


def _load_env():
    repo_root = Path(__file__).resolve().parents[1]
    env_path = repo_root / ".env"
    if not env_path.exists():
        return False

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v
    return True


def login():
    _load_env()

    UID = os.getenv("SHOONYA_USERID", "")
    PWD = os.getenv("SHOONYA_PASSWORD", "")
    TOTP_KEY = os.getenv("TOTP_SECRET", "")

    VC = os.getenv("SHOONYA_VENDOR_CODE", "")
    API_SECRET = os.getenv("SHOONYA_API_SECRET", "")
    IMEI = os.getenv("SHOONYA_IMEI", "")

    if not UID or not PWD or not TOTP_KEY:
        return None, "Missing env vars: SHOONYA_USERID/SHOONYA_PASSWORD/TOTP_SECRET"

    try:
        api = NorenApi(host=DEFAULT_HOST, websocket=DEFAULT_WS)
        otp = pyotp.TOTP(TOTP_KEY).now()

        ret = api.login(
            userid=UID,
            password=PWD,
            twoFA=otp,
            vendor_code=VC,
            api_secret=API_SECRET,
            imei=IMEI,
        )

        if ret and ret.get("stat") == "Ok":
            return api, None

        err = ret.get("emsg", "Unknown error") if ret else "No response"
        return None, f"Login failed: {err}"

    except Exception as e:
        return None, f"Login exception: {e}"
