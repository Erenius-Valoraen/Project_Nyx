from API.api_util import Contract, OptionChain, API
from Trading.paper_trading import PaperTrading
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


import time
start_time = time.time()
chain = OptionChain(api)


contract = chain.find(25600, chain.expiries.weekly(), "CE")



trader = PaperTrading(api, contract)
trader.start()

