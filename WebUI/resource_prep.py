from API.api_util import API, OptionChain
from Trading.paper_trading import PaperTrading

class ChainPrep:
    def __init__(self, api):
        self.api = api
        self.engine = PaperTrading(self.api)
        self.init_chain()
        self.init_equity()
   
    def init_chain(self):

        chain = OptionChain(self.api)
        options = chain.get_full_chain(num_strikes=10)

        all_contracts = [
            contract 
            for expiry in options.values() 
            for contract_list in expiry.values() 
            for contract in contract_list
        ]
        for contract in all_contracts:
            self.engine.add_contract(contract)
    
    def init_equity(self):
        self.engine.add_equity('RELIANCE')
