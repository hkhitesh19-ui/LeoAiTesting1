from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Literal


Decision = Literal["CALL", "PUT", "NO_TRADE"]


@dataclass(frozen=True)
class PaperTradeOrder:
    """
    Strict contract for papertrade execution.
    """
    decision: Decision
    price: float
    reason: str
    ts: str
    meta: Dict[str, Any]


@dataclass(frozen=True)
class PaperTradeState:
    """
    In-memory papertrade state (V1).
    - position: None / "CALL" / "PUT"
    - entry_price: float
    - entry_ts: str
    """
    position: Optional[Decision]
    entry_price: float
    entry_ts: str
    trades: int


class PaperTradeEngineV1:
    """
    V1 rules:
    - If NO position and decision in {CALL,PUT} => enter
    - If in position and opposite decision => exit then enter new
    - If in position and NO_TRADE => hold
    - Logs only (no broker orders)
    """
    def __init__(self) -> None:
        self.state = PaperTradeState(position=None, entry_price=0.0, entry_ts="", trades=0)

    def step(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        # Required fields
        decision: Decision = signal["decision"]
        close: float = float(signal["close"])
        reason: str = str(signal.get("reason", ""))
        ts: str = str(signal.get("ts", ""))  # can be empty in V1
        meta: Dict[str, Any] = dict(signal.get("meta", {}) or {})

        st = self.state

        # default action
        action = {"action": "HOLD", "position": st.position, "pnl": 0.0}

        # enter
        if st.position is None:
            if decision in ("CALL", "PUT"):
                self.state = PaperTradeState(position=decision, entry_price=close, entry_ts=ts, trades=st.trades + 1)
                action = {"action": "ENTER", "position": decision, "entry": close, "reason": reason}
            else:
                action = {"action": "NO_TRADE", "position": None}

            return {
                "order": PaperTradeOrder(decision=decision, price=close, reason=reason, ts=ts, meta=meta).__dict__,
                "action": action,
                "state": self.state.__dict__,
            }

        # already in position
        assert st.position in ("CALL", "PUT")

        # flip
        if decision in ("CALL", "PUT") and decision != st.position:
            pnl = close - st.entry_price if st.position == "CALL" else st.entry_price - close
            # exit old
            exit_action = {"action": "EXIT", "position": st.position, "exit": close, "pnl": pnl}
            # enter new
            self.state = PaperTradeState(position=decision, entry_price=close, entry_ts=ts, trades=st.trades + 1)
            enter_action = {"action": "ENTER", "position": decision, "entry": close, "reason": reason}

            return {
                "order": PaperTradeOrder(decision=decision, price=close, reason=reason, ts=ts, meta=meta).__dict__,
                "action": {"flip": True, "exit": exit_action, "enter": enter_action},
                "state": self.state.__dict__,
            }

        # hold
        if decision == "NO_TRADE":
            pnl_live = close - st.entry_price if st.position == "CALL" else st.entry_price - close
            action = {"action": "HOLD", "position": st.position, "pnl_live": pnl_live}
        else:
            # same side signal
            pnl_live = close - st.entry_price if st.position == "CALL" else st.entry_price - close
            action = {"action": "HOLD_SAME_SIDE", "position": st.position, "pnl_live": pnl_live, "reason": reason}

        return {
            "order": PaperTradeOrder(decision=decision, price=close, reason=reason, ts=ts, meta=meta).__dict__,
            "action": action,
            "state": self.state.__dict__,
        }