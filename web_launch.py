from WebUI.app import create_app
from WebUI.resource_prep import ChainPrep
from API.api_util import API
from dotenv import load_dotenv
import os

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

    chain = ChainPrep(api)
    return chain.engine


# ✅ CREATE ENGINE ONCE
paper_engine = build_paper_engine()

# ✅ EXPOSE FLASK APP AT MODULE LEVEL
app = create_app(paper_engine=paper_engine)


if __name__ == "__main__":
    # Dev-only server
    app.run(host="127.0.0.1", port=29916, debug=True)