from dataclasses import dataclass
from typing import Optional, Dict
import time

@dataclass
class PaperOrder:
    order_id: str
    symbol: str
    side: str  # BUY/SELL
    qty: int
    price: float
    ts_ms: int
    status: str  # SENT/FILLED/REJECTED

@dataclass
class Position:
    symbol: str
    qty: int
    avg_price: float

class PaperBroker:
    """
    Simulates order execution for prototype.
    - Market order fills instantly at passed LTP.
    - Maintains positions.
    """
    def __init__(self):
        self.orders: Dict[str, PaperOrder] = {}
        self.positions: Dict[str, Position] = {}

    def _oid(self):
        return f"PB{int(time.time()*1000)}"

    def place_market(self, symbol: str, side: str, qty: int, ltp: float) -> PaperOrder:
        oid = self._oid()
        order = PaperOrder(
            order_id=oid, symbol=symbol, side=side, qty=qty,
            price=float(ltp), ts_ms=int(time.time()*1000), status="FILLED"
        )
        self.orders[oid] = order
        self._apply_fill(order)
        return order

    def _apply_fill(self, o: PaperOrder):
        sign = 1 if o.side.upper() == "BUY" else -1
        new_qty = sign * o.qty

        pos = self.positions.get(o.symbol)
        if not pos:
            self.positions[o.symbol] = Position(symbol=o.symbol, qty=new_qty, avg_price=o.price)
            return

        # position update (simple average if same direction)
        if (pos.qty >= 0 and new_qty >= 0) or (pos.qty <= 0 and new_qty <= 0):
            total_qty = pos.qty + new_qty
            if total_qty != 0:
                pos.avg_price = ((pos.avg_price * abs(pos.qty)) + (o.price * abs(new_qty))) / abs(total_qty)
            pos.qty = total_qty
        else:
            # reducing/closing
            pos.qty = pos.qty + new_qty
            if pos.qty == 0:
                del self.positions[o.symbol]

    def get_positions(self):
        return list(self.positions.values())
