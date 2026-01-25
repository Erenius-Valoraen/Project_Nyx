
import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Input
from textual import work
from rich.text import Text
import threading

class DashboardApp(App):
    CSS = """
    Screen { background: #0a0a0c; }
    DataTable { height: 1fr; border: double #00ff00; background: #121214; }
    DataTable > .datatable--header { background: #1e1e2e; color: #00ffff; }
    Input { dock: bottom; border: tall #ff00ff; background: #1a1a1a; color: #ffffff; }
    """

    def __init__(self, trading_system):
        super().__init__()
        self.system = trading_system
        self.data_snapshot = []
        self.lock = threading.Lock() # Protects the snapshot during read/write

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(zebra_stripes=True)
        yield Input(placeholder="buy/sell <qty>", id="cmd")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns(
    "ID", "Sym", "Side", "Orig", "Open Qty",
    "Entry", "Bid", "Ask", "LTP",
    "Open P&L", "Closed P&L", "Status"
)
        self.set_interval(0.1, self.update_ui_from_snapshot) # Very fast UI refresh
        self.fetch_data_worker() # Start background loop

    @work(exclusive=True, thread=True)
    def fetch_data_worker(self) -> None:
        while True:
            temp_data = []

            for pos in self.system.positions:
                md = pos.update()

                open_qty = md["open_qty"]
                side = "buy" if open_qty > 0 else "sell" if open_qty < 0 else "flat"

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

            import time
            time.sleep(0.1)

    def update_ui_from_snapshot(self) -> None:
        table = self.query_one(DataTable)

        with self.lock:
            display_list = list(self.data_snapshot)

        table.clear()

        for d in display_list:
            if d["side"] == "buy":
                side_color = "spring_green3"
            elif d["side"] == "sell":
                side_color = "deep_pink3"
            else:
                side_color = "grey50"

            pl_style = "bold green" if d["open_pl"] >= 0 else "bold red"
            status_text = Text("OPEN", style="bold green") if d["is_open"] else Text("CLOSED", style="dim white")

            table.add_row(
                str(d["id"]),
                str(d["sym"]),
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
                status_text,
            )

    @work(thread=True)
    def handle_order(self, side: str, qty: int) -> None:
        self.system.market_order(qty, side)
        self.notify(f"Order Sent: {side.upper()} {qty}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        parts = event.value.strip().lower().split()
        if len(parts) == 2:
            self.handle_order(parts[0], int(parts[1]))
        self.query_one("#cmd").value = ""