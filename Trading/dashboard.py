import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Input, Button
from textual.containers import Horizontal, Vertical
from textual import work
from rich.text import Text
import threading


class DashboardApp(App):
    CSS = """
    Screen {
        background: #0a0a0c;
    }

    DataTable {
        height: 1fr;
        border: double #00ff00;
        background: #121214;
    }

    DataTable > .datatable--header {
        background: #1e1e2e;
        color: #00ffff;
    }

    #order-bar {
        height: 3;
        padding: 0 2;
        background: #0f0f12;
    }

    #qty {
        width: 20;
        text-align: center;
        border: tall #aaaaaa;
        background: #1a1a1a;
        color: white;
    }

    #buy {
        background: #0a3;
        color: black;
        border: heavy #00ff88;
        width: 12;
    }

    #sell {
        background: #a00;
        color: white;
        border: heavy #ff4444;
        width: 12;
    }
    #cmd {
    border: tall #ff00ff;
    background: #1a1a1a;
    color: white;
    padding: 0 1;
    }

    #bottom-panel {
    dock: bottom;
    height: 6;
    background: #0f0f12;
    }
    """

    def __init__(self, trading_system):
        super().__init__()
        self.system = trading_system
        self.data_snapshot = []
        self._running = True
        self.lock = threading.Lock()

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(zebra_stripes=True)

        # ---- BOTTOM PANEL ----
        with Vertical(id="bottom-panel"):
            with Horizontal(id="order-bar"):
                yield Button("BUY", id="buy")
                yield Input(value="100", id="qty", placeholder="Quantity")
                yield Button("SELL", id="sell")

            yield Input(placeholder="Command: buy 100 | sell 50", id="cmd")

        yield Footer()

        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns(
            "ID", "Sym", "Side", "Orig", "Open Qty",
            "Entry", "Bid", "Ask", "LTP",
            "Open P&L", "Closed P&L", "Status"
        )

        self.set_interval(0.1, self.update_ui_from_snapshot)
        self.fetch_data_worker()

    # ===================== DATA FETCH =====================

    @work(exclusive=True, thread=True)
    def fetch_data_worker(self) -> None:
        import time

        while self._running:
            temp_data = []

            for pos in self.system.positions:
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

    @work(thread=True)
    def handle_order(self, side: str, qty: int) -> None:
        self.system.market_order(qty, side)
        self.notify(f"{side.upper()} {qty} sent")

    def _get_qty(self) -> int:
        try:
            return int(self.query_one("#qty").value)
        except ValueError:
            self.notify("Invalid quantity", severity="error")
            return 0

    def on_button_pressed(self, event: Button.Pressed) -> None:
        qty = self._get_qty()
        if qty <= 0:
            return

        if event.button.id == "buy":
            self.handle_order("buy", qty)
        elif event.button.id == "sell":
            self.handle_order("sell", qty)
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "cmd":
            return

        parts = event.value.strip().lower().split()
        if len(parts) != 2:
            self.notify("Usage: buy <qty> or sell <qty>", severity="warning")
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

        # Clear command bar ONLY (qty input remains untouched)
        event.input.value = ""

    
    def on_shutdown(self) -> None:
        self._running = False