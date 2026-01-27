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


chain = OptionChain(api)
contract = chain.find(25900, chain.expiries.weekly(expiry_skip_offset=-1), "CE")

paper_engine = PaperTrading(api, contract)
paper_engine.start()

