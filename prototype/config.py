from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _repo_root() -> Path:
    # prototype folder ke 1 level upar repo root
    return Path(__file__).resolve().parent.parent


def _load_env_if_present() -> None:
    """
    Minimal .env loader: repo root .env read.
    dotenv dependency nahi chahiye.
    """
    env_path = _repo_root() / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        # do not override already set env
        os.environ.setdefault(k, v)


@dataclass(frozen=True)
class Config:
    # Required (Shoonya)
    shoonya_userid: str
    shoonya_password: str
    shoonya_vendor_code: str
    shoonya_api_secret: str
    shoonya_imei: str
    shoonya_totp_secret: str

    # Optional
    poll_sec: int = 60

    # Tokens (Spot)
    nifty_spot_token: str = ""
    spot_token: str = ""


def load_config() -> Config:
    _load_env_if_present()

    def _need(name: str) -> str:
        v = os.getenv(name, "").strip()
        if not v:
            raise RuntimeError(f"Missing env: {name}")
        return v

    def _opt(name: str, default: str = "") -> str:
        return os.getenv(name, default).strip()

    poll = int(os.getenv("POLL_SEC", "60"))

    cfg = Config(
        shoonya_userid=_need("SHOONYA_USERID"),
        shoonya_password=_need("SHOONYA_PASSWORD"),
        shoonya_vendor_code=_need("SHOONYA_VENDOR_CODE"),
        shoonya_api_secret=_need("SHOONYA_API_SECRET"),
        shoonya_imei=_need("SHOONYA_IMEI"),
        shoonya_totp_secret=_need("TOTP_SECRET"),
        poll_sec=poll,
        nifty_spot_token=_opt("NIFTY_SPOT_TOKEN", ""),
        spot_token=_opt("SPOT_TOKEN", ""),
    )
    return cfg
