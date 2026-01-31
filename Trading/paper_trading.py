from API.api_util import Contract, API, OptionChain
from UI.paper_trading_ui import DashboardApp


# =========================
# ORDER
# =========================

class Order:
    def __init__(self, contract: Contract, quantity, side, price, identifier=None):
        self.identifier = identifier
        self.quantity = quantity
        self.side = side              # "buy" | "sell"
        self.price = price
        self.contract = contract
        self.symbol = contract.symbol


# =========================
# POSITION
# =========================

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

        # 🔒 Frozen values after close
        self.close_bid = None
        self.close_ask = None
        self.close_ltp = None

    def close(self, closing_order: Order):
        self.closing_orders.append(closing_order)

    # ----------------------------------
    # BULK MARKET UPDATE (NO API CALLS)
    # ----------------------------------

    def update_from_market(self, market: dict):
        symbol = self.opening_order.contract.symbol

        # =========================
        # CLOSED POSITION → FROZEN
        # =========================
        if not self.open:
            return {
                "symbol": symbol,
                "ltp": self.close_ltp,
                "bid": self.close_bid,
                "ask": self.close_ask,
                "open_qty": 0,
                "open_pl": 0.0,
                "closed_pl": self.closed_pl,
                "open": False,
            }

        data = market.get(symbol)
        if not data:
            return None

        bid = data["bid"]
        ask = data["ask"]
        ltp = data["ltp"]

        # ---- OPEN QTY ----
        closing_effect = 0
        for o in self.closing_orders:
            closing_effect += -o.quantity if o.side == "sell" else o.quantity

        self.open_qty = self.opening_qty + closing_effect
        entry = self.opening_order.price

        # ---- CLOSED P&L ----
        self.closed_pl = 0.0
        for o in self.closing_orders:
            if o.side == "sell":
                self.closed_pl += o.quantity * (o.price - entry)
            else:
                self.closed_pl += o.quantity * (entry - o.price)

        # ---- OPEN / CLOSE LOGIC ----
        if self.open_qty > 0:
            self.open_pl = self.open_qty * (bid - entry)

        elif self.open_qty < 0:
            self.open_pl = abs(self.open_qty) * (entry - ask)

        else:
            # 🔒 POSITION JUST CLOSED
            self.open = False
            self.open_pl = 0.0

            self.close_bid = bid
            self.close_ask = ask
            self.close_ltp = ltp

        return {
            "symbol": symbol,
            "ltp": ltp,
            "bid": bid,
            "ask": ask,
            "open_qty": self.open_qty,
            "open_pl": self.open_pl,
            "closed_pl": self.closed_pl,
            "open": self.open,
        }


# =========================
# PAPER TRADING ENGINE
# =========================

class PaperTrading:
    def __init__(self, api: API):
        self.api = api

        self.contracts: dict[str, Contract] = {}
        self.positions: dict[str, list[Position]] = {}

        self.selected_symbol: str | None = None
        self.total_trades_executed = 0

        self.chain = OptionChain(self.api)

    # -------------------------
    # CONTRACT MANAGEMENT
    # -------------------------

    def add_contract(self, contract: Contract):
        symbol = contract.symbol
        self.contracts[symbol] = contract
        self.positions.setdefault(symbol, [])

        if self.selected_symbol is None:
            self.selected_symbol = symbol

    def select_contract(self, symbol: str):
        if symbol not in self.contracts:
            raise ValueError(f"Unknown contract: {symbol}")
        self.selected_symbol = symbol

    @property
    def selected_contract(self) -> Contract | None:
        if not self.selected_symbol:
            return None
        return self.contracts[self.selected_symbol]

    # -------------------------
    # UI
    # -------------------------

    def start(self, show_positions=True):
        if show_positions:
            app = DashboardApp(self)
            app.run()

    # -------------------------
    # MARKET DATA (STUB)
    # -------------------------

    def fetch_market_snapshot(self) -> dict:
        """
        Fetch bid/ask/ltp for ALL contracts at once.

        Expected return format:
        {
            "SYMBOL": {
                "bid": float,
                "ask": float,
                "ltp": float
            },
            ...
        }
        """
        contracts = []
        seen = set()

        for plist in self.positions.values():
            for p in plist:
                if not p.open:
                    continue

                contract = p.opening_order.contract
                if contract.symbol not in seen:
                    contracts.append(contract)
                    seen.add(contract.symbol)

        if not contracts:
            return {}

        data = self.api.batch_opt_ltp(contracts, mode="FULL")

        processed_data = {}

        for symbol, book in data.items():
            processed_data[symbol] = {
                "bid": float(book["buy"][0]["price"]),
                "ask": float(book["sell"][0]["price"]),
                "ltp": (
                    float(book["buy"][0]["price"]) +
                    float(book["sell"][0]["price"])
                ) / 2,
            }

        return processed_data

    # -------------------------
    # BULK POSITION UPDATE
    # -------------------------

    def update_open_positions(self):
        market = self.fetch_market_snapshot()

        results = []
        for plist in self.positions.values():
            for p in plist:
                if not p.open:
                    continue
                data = p.update_from_market(market)
                if data:
                    results.append((p, data))

        return results

    # -------------------------
    # ORDER EXECUTION
    # -------------------------

    def market_order(self, symbol: str, quantity: int, side: str, identifier=None):
        if symbol not in self.contracts:
            raise ValueError(f"Contract not registered: {symbol}")

        contract = self.contracts[symbol]
        positions = self.positions[symbol]

        bid = contract.bid()
        ask = contract.ask()
        price = ask if side == "buy" else bid

        signed_qty = quantity if side == "buy" else -quantity

        for p in positions:
            if not p.open:
                continue

            # SAME DIRECTION → ADD
            if (p.open_qty > 0 and signed_qty > 0) or (p.open_qty < 0 and signed_qty < 0):
                p.close(Order(contract, abs(signed_qty), side, price, self.total_trades_executed))
                self.total_trades_executed += 1
                return p

            # OPPOSITE DIRECTION → CLOSE / FLIP
            closing_qty = min(abs(p.open_qty), abs(signed_qty))
            p.close(Order(contract, closing_qty, side, price, self.total_trades_executed))
            self.total_trades_executed += 1

            remaining = abs(signed_qty) - closing_qty

            if remaining > 0:
                new_side = "buy" if signed_qty > 0 else "sell"
                new_pos = Position(
                    Order(contract, remaining, new_side, price, self.total_trades_executed)
                )
                positions.append(new_pos)
                self.total_trades_executed += 1
                return new_pos

            return p

        # NO OPEN POSITION → OPEN NEW
        pos = Position(
            Order(contract, quantity, side, price, self.total_trades_executed)
        )
        positions.append(pos)
        self.total_trades_executed += 1
        return pos

    # -------------------------
    # SELECTED CONTRACT ORDERS
    # -------------------------

    def market_order_selected(self, quantity: int, side: str, identifier=None):
        if not self.selected_symbol:
            raise RuntimeError("No contract selected")

        return self.market_order(
            self.selected_symbol,
            quantity,
            side,
            identifier,
        )

    # -------------------------
    # HELPERS
    # -------------------------

    def get_positions(self):
        return [p for plist in self.positions.values() for p in plist]

    def get_open_positions(self):
        return [p for p in self.get_positions() if p.open]