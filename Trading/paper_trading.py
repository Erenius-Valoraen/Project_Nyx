from API.api_util import Contract
from Trading.dashboard import DashboardApp

class Order:
    def __init__(self, contract: Contract, quantity, side, price, identifier=None, symbol="Instrument"):
        self.identifier = identifier
        self.quantity = quantity
        self.side = side
        self.price = price
        self.contract = contract
        self.symbol = self.contract.symbol

class Position:
    def __init__(self, opening_order: Order):
        self.opening_order = opening_order
        self.opening_qty = (
            opening_order.quantity
            if opening_order.side == "buy"
            else -opening_order.quantity
        )

        self.closing_orders = []
        self.closed_pl = 0.0
        self.open_pl = 0.0
        self.open_qty = self.opening_qty
        self.open = True

    def close(self, closing_order: Order):
        self.closing_orders.append(closing_order)

    def update(self):
        # ---- MARKET DATA ----
        contract = self.opening_order.contract
        ltp = contract.ltp()
        bid = contract.bid()
        ask = contract.ask()

        # ---- RECOMPUTE OPEN QTY (PURE) ----
        closing_effect = 0
        for o in self.closing_orders:
            if o.side == "sell":
                closing_effect -= o.quantity
            else:
                closing_effect += o.quantity

        self.open_qty = self.opening_qty + closing_effect

        entry = self.opening_order.price

        # ---- CLOSED P&L ----
        self.closed_pl = 0.0
        for o in self.closing_orders:
            if o.side == "sell":
                self.closed_pl += o.quantity * (o.price - entry)
            else:
                self.closed_pl += o.quantity * (entry - o.price)

        # ---- OPEN P&L (BID / ASK AWARE) ----
        if self.open_qty > 0:  # LONG → exit at BID
            self.open_pl = self.open_qty * (bid - entry)
        elif self.open_qty < 0:  # SHORT → exit at ASK
            self.open_pl = abs(self.open_qty) * (entry - ask)
        else:
            self.open_pl = 0.0
            self.open = False

        return {
            "ltp": ltp,
            "bid": bid,
            "ask": ask,
            "open_qty": self.open_qty,
        }

class PaperTrading:
    def __init__(self, api, contract: Contract):
        self.api = api
        self.contract = contract
        self.total_trades_executed = 0
        self.orders = []
        self.positions = []

    def start(self, logging=False, show_positions=True):

        if show_positions:
            app = DashboardApp(self)
            app.run()

    def market_order(self, quantity, side, identifier=None, symbol=None):
        current_bid = self.contract.bid()
        current_ask = self.contract.ask()
        price = current_ask if side == "buy" else current_bid

        signed_qty = quantity if side == "buy" else -quantity

        for p in self.positions:
            if not p.open:
                continue

            # Same direction → increase position
            if (p.open_qty > 0 and signed_qty > 0) or (p.open_qty < 0 and signed_qty < 0):
                p.open_qty += signed_qty
                return p

            # Opposite direction → close or flip
            closing_qty = min(abs(p.open_qty), abs(signed_qty))
            p.close(Order(self.contract, closing_qty, side, price, self.total_trades_executed))
            self.total_trades_executed += 1
            p.update()

            remaining_qty = abs(signed_qty) - closing_qty

            # FLIP POSITION
            if remaining_qty > 0:
                new_side = "buy" if signed_qty > 0 else "sell"
                new_position = Position(
                    Order(self.contract, remaining_qty, new_side, price, self.total_trades_executed)
                )
                self.positions.append(new_position)
                self.total_trades_executed += 1
                return new_position

            return p

        # No open position → open new
        position = Position(Order(self.contract, quantity, side, price, self.total_trades_executed))
        self.positions.append(position)
        self.total_trades_executed += 1
        return position

