from API.api_util import API, OptionChain
from Trading.paper_trading import PaperTrading
from WebUI.app import create_app

from dotenv import load_dotenv
import os

hostname = '127.0.0.1'
port = 29916
def build_paper_engine():
    """
    Mirrors the construction pattern in `main.py`, but does not start the terminal UI.
    """
    load_dotenv()

    api_key = os.getenv("API_KEY")
    username = os.getenv("USERNAME")
    pin = os.getenv("PIN")
    token = os.getenv("TOKEN")

    api = API()
    api.login(api_key, username, pin, token)
    api.prepare_resources(ignore_run_check=False)

    chain = OptionChain(api)
    contract1 = chain.find(25900, chain.expiries.weekly(expiry_skip_offset=0), "CE")
    contract2 = chain.find(26000, chain.expiries.weekly(expiry_skip_offset=0), "CE")

    engine = PaperTrading(api)
    engine.add_contract(contract1)
    engine.add_contract(contract2)

    return engine


def main():
    paper_engine = build_paper_engine()
    app = create_app(paper_engine=paper_engine)

    # Barebones dev server. Use a real WSGI server for production.
    print(f"Running on http://{hostname}:{port}")
    app.run(host=hostname, port=port, debug=True)




if __name__ == "__main__":
    main()

