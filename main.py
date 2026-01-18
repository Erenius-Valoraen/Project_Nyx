from API.api_util import Contract, OptionChain, API
from Analysis.option_analyser import OptionAnalyser

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
contract = chain.find(26200, "20JAN2026", "CE")

analyser = OptionAnalyser(api)
analyser.init()
analyser.start(contract, logging=True)

