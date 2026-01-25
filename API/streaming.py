from API.api_util import API, OptionChain, Contract
import time
from datetime import datetime
from collections import deque
import csv
import threading

from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

import os

console = Console()


class OptionAnalyser:
    def __init__(self, api: API):
        self.api = api

        self.running = False
        self.thread = None

        self.latest_quotes = None
        self.latest_metrics = {}

        # to handle threading shutdown
        self.api.shutdown.enabled = True
        self.api.shutdown.register(self)

    # ---------- RENDERING ----------
    def _render(self, quotes, metrics, latency_ms):
        table = Table(expand=True, show_header=True, header_style="bold cyan")

        table.add_column("Bid Qty", justify="right")
        table.add_column("Bid", justify="right")
        table.add_column("Ask", justify="right")
        table.add_column("Ask Qty", justify="right")

        for i, (b, a) in enumerate(zip(quotes["depth"]["buy"], quotes["depth"]["sell"])):
            is_best = i == 0    

            bid_style = "bold green" if is_best else "green"
            ask_style = "bold red" if is_best else "red"

            table.add_row(
                Text(str(b["quantity"]), style=bid_style),
                Text(f"{b['price']:.2f}", style=bid_style),
                Text(f"{a['price']:.2f}", style=ask_style),
                Text(str(a["quantity"]), style=ask_style),
            )

        header = Text()
        header.append(f"{quotes['tradingSymbol']}\n", style="bold yellow")
        header.append(
            f"LTP: {quotes['ltp']:.2f}  "
            f"Change: {quotes['netChange']:.2f} "
            f"({quotes['percentChange']:.2f}%)\n",
            style="green" if quotes["netChange"] >= 0 else "red"
        )
        header.append(
            f"Vol 1s: {metrics['vol_1s']} | "
            f"Avg Vol/sec: {metrics['avg_vol_sec']:.1f}\n"
        )
        header.append(f"Latency: {latency_ms:.1f} ms")

        return Panel.fit(
            table,
            title=header,
            border_style="blue"
        )

    # ---------- WORKER THREAD ----------
    def _run(self, contract: Contract, display=True, logging=True):
        volume_history = deque(maxlen=60)
        prev_volume = None

        if logging:
            try:
                log_file = open("depth_history/log.csv", "a", newline="")
                logger = csv.writer(log_file)
            except FileNotFoundError:
                os.makedirs("depth_history", exist_ok=True)
                log_file = open("depth_history/log.csv", "a", newline="")
                logger = csv.writer(log_file)

        self.running = True

        with Live(refresh_per_second=4, console=console) as live:
            while self.running:
                start = time.perf_counter()

                quotes = contract.full()
                self.latest_quotes = quotes

                latency = (time.perf_counter() - start) * 1000

                trade_volume = quotes["tradeVolume"]
                delta = max(trade_volume - prev_volume, 0) if prev_volume else 0
                prev_volume = trade_volume

                volume_history.append(delta)

                avg_vol_sec = sum(volume_history) / len(volume_history)

                self.latest_metrics = {
                    "vol_1s": delta,
                    "avg_vol_sec": avg_vol_sec,
                    "timestamp": datetime.now()
                }

                if display:
                    panel = self._render(quotes, self.latest_metrics, latency)
                    live.update(panel)

                if logging:
                    depth = quotes["depth"]
                    logger.writerow([
                        datetime.now().isoformat(),
                        quotes["tradingSymbol"],
                        depth["buy"][0]["price"],
                        depth["buy"][0]["quantity"],
                        depth["sell"][0]["price"],
                        depth["sell"][0]["quantity"],
                        delta,
                        avg_vol_sec
                    ])
                    log_file.flush()

                time.sleep(1)

        if logging:
            log_file.close()

    # ---------- CONTROL ----------
    def start(self, contract, display=True, logging=True):
        if self.running:
            return

        self.thread = threading.Thread(
            target=self._run,
            args=(contract, display, logging),
            daemon=False
        )
        self.thread.start()

    def stop(self):
        self.running = False

    def quotes(self):
        return self.latest_quotes
    