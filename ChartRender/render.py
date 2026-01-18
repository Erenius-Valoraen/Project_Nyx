from API.api_util import API, OptionChain
from display import CandlestickChart
from pprint import pp
import streamlit as st

# Import UI module
import ChartRender.ui_layout as ui


API_KEY = "NXWtjMy1"
USERNAME = 'P50072393'
PWD = '0478'
TOKEN = "TYKE6XFO6VJIO6NJ2V5SF4AX7A"


# ---- STEP 1: UI Setup ----
ui.setup_page()
ui.render_sidebar()
ui.render_header()


# ---- STEP 2: Backend Logic ----
api = API()
api.login(API_KEY, USERNAME, PWD, TOKEN)
api.prepare_resources(ignore_run_check=False)

candles = api.eq_candles(
    "reliance",
    interval="FIVE_MINUTE",
    from_date="2025-06-01 09:15",
    to_date="2025-06-02 15:30",
)

chart = CandlestickChart(candles, symbol="RELIANCE")

# chain = OptionChain(api)
# pp(chain.find(10, "16DEC2025", "CE").depth())

# ---- STEP 3: Render Chart via UI wrapper ----
ui.render_chart_container(lambda: chart.render())