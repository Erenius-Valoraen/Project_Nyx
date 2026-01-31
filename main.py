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
# contract1 = chain.find(25900, chain.expiries.weekly(expiry_skip_offset=0), "CE")
# contract2 = chain.find(26000, chain.expiries.weekly(expiry_skip_offset=0), "CE")

cc = chain.get_chain(chain.expiries.weekly())

# historicParam = {
#                 "exchange":"NFO",
#                 "symboltoken":'42512',
#                 "interval": "ONE_MINUTE",
#                 "fromdate": "2026-01-01 09:15",
#                 "todate": "2026-01-31 12:00"
#                 }

# pp(api.smartApi.getCandleData(historicParam))
api.candles("NIFTY10FEB2625300CE", 'ONE_MINUTE', '2026-01-01 09:15', '2026-01-31 12:00', type='opt')

# pp(chain.get_chain(chain.expiries.weekly()))
# paper_engine = PaperTrading(api)
# paper_engine.add_contract(contract1)
# paper_engine.add_contract(contract2)

# paper_engine.start()




