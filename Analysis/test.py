import csv
from datetime import datetime
from API.api_util import API, OptionChain, Expiry
# from fill_prob import FillProbabilityEstimator, simulate_fill_before_move
from ChartRender.display import CandlestickChart
from pprint import pp
import time
import requests
from collections import deque
import numpy as np
from dotenv import load_dotenv
# import smartwebsocketexamplev2 as web
import os



API_KEY = "------"
USERNAME = '-------'
PWD = '-----'
TOKEN = "------"

api = API()
api.login(API_KEY, USERNAME, PWD, TOKEN)
api.prepare_resources(ignore_run_check=False)

# --------------------------
# MAIN LOOP
# --------------------------
volume_history = deque(maxlen=60)   # track last 60 seconds
prev_volume = None

# estimator = FillProbabilityEstimator(my_size=4000, simulations=500)
exp = Expiry()

MIN_HISTORY_SECONDS = 10  # wait for volume history to build

order = None
count = 0

previous_quantity = 0



LOG_PATH = "depth_history/log.csv"

log_file = open(LOG_PATH, "a", newline="")
logger = csv.writer(log_file)

# Write header once
logger.writerow([
    "timestamp",
    "instrument",
    "best_bid_price", "best_bid_qty",
    "best_ask_price", "best_ask_qty",
    "vol_last_sec",
    "avg_vol_per_sec"
])
log_file.flush()


while True:
    start = time.perf_counter()



    chain = OptionChain(api)
    quotes = chain.find(26200, "20JAN2026", "CE").full()

    latency = time.perf_counter() - start

    os.system('clear')
    pp(quotes)
    print(f"Latency: {latency*1000:.2f} ms")
    print("-" * 40)
    print("Additional Info:")

    # ------------------------
    # FIXED VOLUME DELTA
    # ------------------------
    trade_volume = quotes['tradeVolume']

    if prev_volume is None:
        delta = 0
    else:
        raw_delta = trade_volume - prev_volume

        # If the delta is unrealistic (negative or > 200k per sec), clamp it
        if raw_delta <= 0 or raw_delta > 2000000:
            delta = 0
        else:
            delta = raw_delta

    prev_volume = trade_volume
    volume_history.append(delta)

    # 1-second volume
    vol_1s = volume_history[-1]

    # 60-second average volume per second
    avg_volume_sec = sum(volume_history) / len(volume_history)

    print(f"Volume last sec: {vol_1s} qty | {vol_1s/65:.1f} lots")
    print(f"Avg Volume/sec: {avg_volume_sec:.1f} qty | {(avg_volume_sec/65):.1f} lots")


    # ------------------------
    # LOGGING (BEST BID / ASK)
    # ------------------------
    depth = quotes["depth"]

    best_bid = depth["buy"][0]
    best_ask = depth["sell"][0]

    logger.writerow([
        datetime.now().isoformat(),
        quotes["tradingSymbol"],
        best_bid["price"],
        best_bid["quantity"],
        best_ask["price"],
        best_ask["quantity"],
        vol_1s,
        avg_volume_sec
    ])

    log_file.flush()


    count += 1
    time.sleep(1)