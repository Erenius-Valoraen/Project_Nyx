from API.api_util import Contract, EquityContract, OptionChain, API
from Trading.paper_trading import PaperTrading
from API.streaming import OptionAnalyser
from Collector.collector import DataCollector

from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from logzero import logger
from queue import Queue



from pprint import pp
import time
from dotenv import load_dotenv
import os
load_dotenv()

API_KEY = os.getenv("API_KEY")
USERNAME = os.getenv("USERNAME")
PIN = os.getenv("PIN")
TOKEN = os.getenv("TOKEN")

api = API()
api.login(API_KEY, USERNAME, PIN, TOKEN)
api.prepare_resources(ignore_run_check=False)

#!/usr/bin/env python3
import json
from niftystocks import ns

JSON_PATH = "jsonLookup/equity_nse.json"  # update path if needed



nifty50_symbols = ns.get_nifty50()
with open(JSON_PATH) as f:
    data = json.load(f)
symbol_to_name = {
    entry["symbol"].replace("-EQ", ""): entry["name"]
    for entry in data
    if entry["symbol"].endswith("-EQ")
}
matched = []
unmatched = []
for sym in nifty50_symbols:
    if sym in symbol_to_name:
        matched.append(symbol_to_name[sym])
    else:
        unmatched.append(sym)

matched.append('HDFCNIFTY')

collector = DataCollector(api, matched, silent=False)
collector.start()