from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from logzero import logger
from API.api_util import API, OptionChain
from queue import Queue
import os
import time
import threading
from datetime import datetime, timezone
from dotenv import load_dotenv

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from colorama import init, Fore, Style
init(autoreset=True) 
# Schema for the parquet file
SCHEMA = pa.schema([
    ("received_timestamp", pa.int64()),   # local time, ms precision
    ("exchange_timestamp", pa.int64()),
    ("sequence_number", pa.int64()),
    ("volume", pa.int64()),
    # Best 5 Buy (bid) — flattened
    ("bid1_price", pa.int64()), ("bid1_qty", pa.int64()), ("bid1_orders", pa.int64()),
    ("bid2_price", pa.int64()), ("bid2_qty", pa.int64()), ("bid2_orders", pa.int64()),
    ("bid3_price", pa.int64()), ("bid3_qty", pa.int64()), ("bid3_orders", pa.int64()),
    ("bid4_price", pa.int64()), ("bid4_qty", pa.int64()), ("bid4_orders", pa.int64()),
    ("bid5_price", pa.int64()), ("bid5_qty", pa.int64()), ("bid5_orders", pa.int64()),
    # Best 5 Sell (ask) — flattened
    ("ask1_price", pa.int64()), ("ask1_qty", pa.int64()), ("ask1_orders", pa.int64()),
    ("ask2_price", pa.int64()), ("ask2_qty", pa.int64()), ("ask2_orders", pa.int64()),
    ("ask3_price", pa.int64()), ("ask3_qty", pa.int64()), ("ask3_orders", pa.int64()),
    ("ask4_price", pa.int64()), ("ask4_qty", pa.int64()), ("ask4_orders", pa.int64()),
    ("ask5_price", pa.int64()), ("ask5_qty", pa.int64()), ("ask5_orders", pa.int64()),
])


def message_to_row(message: dict) -> dict:
    row = {
        "received_timestamp": time.time_ns() // 1_000_000,  # ns → ms
        "exchange_timestamp": message["exchange_timestamp"],
        "sequence_number": message["sequence_number"],
        "volume": message["volume_trade_for_the_day"],
    }
    for i, bid in enumerate(message.get("best_5_buy_data", []), start=1):
        row[f"bid{i}_price"]  = bid["price"]
        row[f"bid{i}_qty"]    = bid["quantity"]
        row[f"bid{i}_orders"] = bid["no of orders"]
    for i, ask in enumerate(message.get("best_5_sell_data", []), start=1):
        row[f"ask{i}_price"]  = ask["price"]
        row[f"ask{i}_qty"]    = ask["quantity"]
        row[f"ask{i}_orders"] = ask["no of orders"]
    return row


class ParquetWriter:
    """
    Buffers ticks in memory and flushes to parquet in batches.
    Appends to today's file; opens a new file on date rollover.
    """
    def __init__(self, symbol: str, base_dir: str = "data", flush_every: int = 20):
        self.symbol = symbol
        self.base_dir = base_dir
        self.flush_every = flush_every
        self._buffer: list[dict] = []
        self._writer: pq.ParquetWriter | None = None
        self._temp_path: str | None = None
        self._current_date: str | None = None
        self._lock = threading.Lock()

    def _date_str(self, ts_ms: int) -> str:
        return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")

    def _get_path(self, date_str: str) -> str:
        dir_path = os.path.join(self.base_dir, self.symbol, date_str)
        os.makedirs(dir_path, exist_ok=True)
        return os.path.join(dir_path, "ticks.parquet")

    def _rotate_if_needed(self, date_str: str):
        """Close current writer and open a new one if the date has changed."""
        if date_str != self._current_date:
            self._close_writer()
            self._current_date = date_str

    def _close_writer(self):
        if self._writer:
            self._writer.close()
            self._writer = None

            if self._temp_path and os.path.exists(self._temp_path):
                final_path = self._get_path(self._current_date)
                try:
                    if os.path.exists(final_path):
                        existing = pq.read_table(final_path)
                        new_data = pq.read_table(self._temp_path)
                        merged = pa.concat_tables([existing, new_data])
                        pq.write_table(merged, final_path)
                        os.remove(self._temp_path)
                    else:
                        os.rename(self._temp_path, final_path)
                except Exception as e:
                    print(f"ERROR during merge/rename: {e}")
                    import traceback
                    traceback.print_exc()

                self._temp_path = None

    def _get_writer(self, date_str: str) -> pq.ParquetWriter:
        if self._writer is None:
            self._temp_path = self._get_path(date_str) + ".tmp"
            self._writer = pq.ParquetWriter(self._temp_path, SCHEMA)
        return self._writer

    def write(self, message: dict):
        row = message_to_row(message)
        date_str = self._date_str(row["exchange_timestamp"])
        with self._lock:
            self._rotate_if_needed(date_str)
            self._buffer.append(row)
            if len(self._buffer) >= self.flush_every:
                self._flush(date_str)

    def _flush(self, date_str: str):
        """Must be called with self._lock held."""
        if not self._buffer:
            return
        table = pa.Table.from_pylist(self._buffer, schema=SCHEMA)
        self._get_writer(date_str).write_table(table)
        self._buffer.clear()
        print("")
        print(f"{Fore.GREEN}Wrote {self.symbol} quotes for {self.flush_every} ticks{Style.RESET_ALL}")

    def flush_and_close(self):
        with self._lock:
            if self._current_date:
                self._flush(self._current_date)
            self._close_writer()


class DataCollector:
    def __init__(self, api: API, symbols: list[str], base_dir: str = "data", flush_every: int = 5, silent=True):
        self.api = api
        self.symbols = symbols
        self.silent = silent
        # Build a token → (symbol, ParquetWriter) map
        self._token_map: dict[str, tuple[str, ParquetWriter]] = {}
        for symbol in symbols:
            token = self.api.get_equity_token(symbol=symbol)
            self._token_map[token] = (symbol, ParquetWriter(symbol, base_dir=base_dir, flush_every=flush_every))

    def _flush_all(self):
        for token, (symbol, writer) in self._token_map.items():
            writer.flush_and_close()

    def start(self):
        correlation_id = "abc123"
        mode = 3

        token_list = [
            {
                "exchangeType": 1,
                "tokens": list(self._token_map.keys())
            }
        ]

        sws = SmartWebSocketV2(
            self.api.authToken, self.api.api_key,
            self.api.username, self.api.feedToken
        )

        def on_data(wsapp, message):
            token = message.get("token")
            entry = self._token_map.get(token)
            if entry is None:
                logger.warning(f"Received data for unknown token: {token}")
                return
            symbol, writer = entry
            if not self.silent:
                print(f"{Style.DIM}received data for {symbol} | {Style.RESET_ALL}", end="")
            writer.write(message)

        def on_open(wsapp):
            logger.info("on open")
            sws.subscribe(correlation_id, mode, token_list)

        def on_error(wsapp, error):
            logger.error(error)

        def on_close(wsapp):
            logger.info("Connection closed — flushing parquet buffers")
            self._flush_all()

        def listen_for_quit():
            while True:
                if input().strip().lower() == "q":
                    logger.info("Closing connection...")
                    self._flush_all()
                    sws.close_connection()
                    break

        sws.on_open = on_open
        sws.on_data = on_data
        sws.on_error = on_error
        sws.on_close = on_close

        threading.Thread(target=listen_for_quit, daemon=True).start()

        sws.connect()