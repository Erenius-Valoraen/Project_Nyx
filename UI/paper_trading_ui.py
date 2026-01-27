import threading
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Input, Button
from textual.containers import Horizontal, Vertical
from textual import work
from rich.text import Text


class DashboardApp(App):
    CSS_PATH = "ui.css"

    BINDINGS = [
        ("ctrl+c", "quit", "Force Quit"),
    ]

    def __init__(self, trading_system):
        super().__init__()
        self.system = trading_system
        self.data_snapshot = []
        self._running = True
        self.lock = threading.Lock()

        self.symbols = list(self.system.contracts.keys())
        self.symbol_index = 0

    # ===================== LAYOUT =====================

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(zebra_stripes=True)

        with Vertical(id="bottom-panel"):
            with Horizontal(id="order-bar"):
                yield Input(
                    value=self.current_symbol(),
                    placeholder="Symbol",
                    id="symbol",
                    classes="symbol",
                )
                yield Button("Buy", id="buy", classes="buy")
                yield Input(value="100", placeholder="Qty", id="qty", classes="qty")
                yield Button("Sell", id="sell", classes="sell")

            yield Input(
                placeholder="Command: buy 100 | sell 50",
                id="command_bar",
                classes="command",
            )

        yield Footer()

    # ===================== SYMBOL HANDLING =====================

    def current_symbol(self) -> str:
        if not self.symbols:
            return ""
        return self.symbols[self.symbol_index]

    def cycle_symbol(self, direction: int):
        if not self.symbols:
            return

        self.symbol_index = (self.symbol_index + direction) % len(self.symbols)
        self.query_one("#symbol").value = self.current_symbol()
        self.notify(f"Selected {self.current_symbol()}")

    # ===================== INIT =====================

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns(
            "ID", "Sym", "Side", "Orig", "Open Qty",
            "Entry", "Bid", "Ask", "LTP",
            "Open P&L", "Closed P&L", "Status"
        )

        self.set_interval(0.1, self.update_ui_from_snapshot)
        self.fetch_data_worker()

    # ===================== KEY HANDLING =====================

    def on_key(self, event) -> None:
        el = self.focused

        # Do not cycle symbols while typing
        if isinstance(el, Input) and el.id in ("qty", "command_bar"):
            return

        if event.key == "up":
            self.cycle_symbol(-1)
            event.stop()
        elif event.key == "down":
            self.cycle_symbol(1)
            event.stop()

    # ===================== DATA FETCH =====================

    @work(exclusive=True, thread=True)
    def fetch_data_worker(self) -> None:
        import time

        while self._running:
            temp_data = []

            for pos in self.system.get_positions():
                md = pos.update()
                open_qty = md["open_qty"]

                side = (
                    "buy" if open_qty > 0
                    else "sell" if open_qty < 0
                    else "flat"
                )

                temp_data.append({
                    "id": pos.opening_order.identifier,
                    "sym": pos.opening_order.symbol,
                    "side": side,
                    "orig_qty": pos.opening_order.quantity,
                    "open_qty": open_qty,
                    "entry": pos.opening_order.price,
                    "ltp": md["ltp"],
                    "bid": md["bid"],
                    "ask": md["ask"],
                    "open_pl": pos.open_pl,
                    "closed_pl": pos.closed_pl,
                    "is_open": pos.open,
                })

            with self.lock:
                self.data_snapshot = temp_data

            time.sleep(0.1)

    # ===================== UI UPDATE =====================

    def update_ui_from_snapshot(self) -> None:
        table = self.query_one(DataTable)

        with self.lock:
            rows = list(self.data_snapshot)

        table.clear()

        for d in rows:
            side_color = (
                "spring_green3" if d["side"] == "buy"
                else "deep_pink3" if d["side"] == "sell"
                else "grey50"
            )

            pl_style = "bold green" if d["open_pl"] >= 0 else "bold red"
            status = Text("OPEN", style="bold green") if d["is_open"] else Text("CLOSED", style="dim")

            table.add_row(
                str(d["id"]),
                d["sym"],
                Text(d["side"].upper(), style=f"bold {side_color}"),
                str(d["orig_qty"]),
                str(d["open_qty"]),
                f"{d['entry']:.2f}",
                f"{d['bid']:.2f}",
                f"{d['ask']:.2f}",
                f"{d['ltp']:.2f}",
                Text(f"{d['open_pl']:,.2f}", style=pl_style),
                Text(
                    f"{d['closed_pl']:,.2f}",
                    style="green" if d["closed_pl"] >= 0 else "red"
                ),
                status,
            )

    # ===================== ORDER HANDLING =====================

    def _get_qty(self) -> int:
        try:
            return int(self.query_one("#qty").value)
        except ValueError:
            self.notify("Invalid quantity", severity="error")
            return 0

    @work(thread=True)
    def handle_order(self, side: str, qty: int) -> None:
        symbol = self.current_symbol()
        self.system.market_order(symbol, qty, side)
        self.notify(f"{side.upper()} {symbol} {qty} sent")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        qty = self._get_qty()
        if qty <= 0:
            return

        if event.button.id == "buy":
            self.handle_order("buy", qty)
        elif event.button.id == "sell":
            self.handle_order("sell", qty)

    # ===================== COMMAND BAR =====================

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "command_bar":
            return

        parts = event.value.strip().lower().split()
        if len(parts) != 2:
            self.notify("Usage: buy <qty> | sell <qty>", severity="warning")
            return

        side, qty = parts
        if side not in ("buy", "sell"):
            self.notify("Invalid side", severity="error")
            return

        try:
            qty = int(qty)
        except ValueError:
            self.notify("Invalid quantity", severity="error")
            return

        self.handle_order(side, qty)
        event.input.value = ""

    # ===================== SHUTDOWN =====================

    def on_shutdown(self) -> None:
        self._running = False