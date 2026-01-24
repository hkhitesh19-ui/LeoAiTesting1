from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass
class PaperTradeState:
    """
    Persistent state for paper trading.
    - position: "CALL"/"PUT"/"" (flat)
    - entry_price: float (0.0 if flat)
    - entry_ts: ISO timestamp string
    - trades: total trade actions executed
    """
    position: str = ""
    entry_price: float = 0.0
    entry_ts: str = ""
    trades: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "PaperTradeState":
        if not isinstance(d, dict):
            return PaperTradeState()
        return PaperTradeState(
            position=str(d.get("position") or ""),
            entry_price=float(d.get("entry_price") or 0.0),
            entry_ts=str(d.get("entry_ts") or ""),
            trades=int(d.get("trades") or 0),
        )


class PaperTradeEngineV2:
    """
    Engine rules (V2):
    - If FLAT and signal decision in {"CALL","PUT"} -> ENTER
    - If IN POSITION and new decision is opposite -> EXIT + ENTER (flip)
    - If IN POSITION and same decision -> HOLD (no re-entry spam)
    """

    def __init__(self, state: Optional[PaperTradeState] = None) -> None:
        self.state = state or PaperTradeState()

    def step(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        signal expected shape:
        {
          "decision": "CALL"/"PUT"/"HOLD",
          "reason": "...",
          "close": float,
          "meta": dict,
          "ts": iso str
        }
        """
        decision = str(signal.get("decision") or "HOLD").upper()
        close = float(signal.get("close") or 0.0)
        ts = str(signal.get("ts") or "")

        # normalize
        if decision not in ("CALL", "PUT", "HOLD"):
            decision = "HOLD"

        # output skeleton
        order = {
            "decision": decision,
            "price": close,
            "reason": str(signal.get("reason") or ""),
            "ts": ts,
            "meta": signal.get("meta") or {},
        }

        action: Dict[str, Any] = {"action": "NONE"}

        # --- core rules ---
        if self.state.position == "":
            # FLAT
            if decision in ("CALL", "PUT"):
                self.state.position = decision
                self.state.entry_price = close
                self.state.entry_ts = ts
                self.state.trades += 1
                action = {
                    "action": "ENTER",
                    "position": decision,
                    "entry": close,
                    "reason": order["reason"],
                }
            else:
                action = {"action": "HOLD_FLAT", "reason": "decision=HOLD"}
        else:
            # IN POSITION
            if decision == "HOLD":
                action = {"action": "HOLD_IN_POSITION", "position": self.state.position}
            elif decision == self.state.position:
                # IMPORTANT: no re-entry spam
                action = {"action": "HOLD_SAME_SIGNAL", "position": self.state.position}
            else:
                # flip: EXIT + ENTER
                prev_pos = self.state.position
                prev_entry = self.state.entry_price

                # exit
                exit_price = close
                pnl = exit_price - prev_entry
                if prev_pos == "PUT":
                    pnl = prev_entry - exit_price

                # enter new
                self.state.position = decision
                self.state.entry_price = close
                self.state.entry_ts = ts
                self.state.trades += 2  # exit+enter count

                action = {
                    "action": "FLIP",
                    "exit": {
                        "position": prev_pos,
                        "entry": prev_entry,
                        "exit": exit_price,
                        "pnl": pnl,
                    },
                    "enter": {
                        "position": decision,
                        "entry": close,
                    },
                    "reason": "opposite signal",
                }

        return {
            "order": order,
            "action": action,
            "state": self.state.to_dict(),
        }
