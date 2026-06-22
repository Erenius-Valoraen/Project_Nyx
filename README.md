# Project Nyx

A keyboard-driven **paper-trading terminal for index options**, built on top of a live broker market-data feed. Nyx connects to the Angel One SmartAPI, streams real-time option quotes and order-book depth, and lets you place simulated market orders against live prices — tracking positions and profit/loss in real time without risking capital. It runs both as a terminal (TUI) application and as a browser-based trading terminal.

> ⚠️ This is a paper-trading / educational project. It places **simulated** orders only and does not execute real trades. It is not financial advice or a production trading system.

## What it does

- **Connects to live market data** via the Angel One SmartAPI, handling TOTP-based authentication, session/token management, and the daily instrument master ("Scrip Master") download and lookup.
- **Builds option chains** for NIFTY weekly/monthly expiries, resolving strikes and instrument tokens on demand.
- **Streams real-time quotes and order-book depth**, computing live metrics such as per-second traded volume and feed latency.
- **Simulates trading** through a paper-trading engine that models orders, positions, partial closes, and open/closed P&L against live bid/ask prices — with no real money involved.
- **Presents two front-ends**: a rich terminal UI and a web-based trading terminal with a live chart, option chain, positions panel, and keyboard-first controls.

## Architecture

Nyx is organized into focused modules, with a clean split between the broker/data layer, the simulation engine, and the presentation layers.

```
.
├── API/                  # Market-data layer over the broker API
│   ├── api_util.py       #   Auth, session, option-chain & token resolution, candles
│   ├── streaming.py      #   Live quote/depth streaming + per-second metrics
│   └── shutdown.py       #   Coordinated thread shutdown
├── SmartApi/             # Angel One SmartAPI client (broker SDK + websocket)
├── Trading/
│   └── paper_trading.py  # Order / Position / PaperTrading engine (simulated fills, P&L)
├── Simulator/            # Scenario simulation scaffolding
├── Analysis/
│   └── depth_visualiser.py  # Heatmap-style visualization of recorded order-book depth
├── UI/                   # Terminal (TUI) dashboard
├── WebUI/                # Flask web terminal
│   ├── app.py            #   App factory (paper engine injected)
│   ├── routes.py         #   JSON API: state, order, contract select, candles, LTP
│   ├── templates/        #   Server-rendered terminal pages & components
│   └── static/js/        #   Modular front-end (see below)
├── main.py               # TUI entry point
├── launch.py             # Web entry point (dev server)
└── web_launch.py         # Web entry point (gunicorn/production)
```

### Backend

The `API` class wraps the broker SDK and exposes higher-level operations — login via TOTP, resource preparation, option-chain construction, historical candles, and batched last-traded-price lookups. The `PaperTrading` engine consumes live market data and maintains `Order` and `Position` objects, computing open and closed P&L on each update in a single market-fetch pass (bulk updates rather than per-position API calls, to keep the refresh loop cheap).

The web layer is a small Flask app using an app-factory pattern, with the paper engine injected into app config. The routes expose a compact JSON API — `/api/state` for the current positions snapshot, `/api/order` to place a simulated market order, `/api/select_contract`, `/api/candles` for chart data, and live LTP endpoints.

### Front-end

The browser terminal is built with vanilla ES modules (no framework), organized by responsibility:

- **`core/`** — transport, API wrappers, a central `state` store, and a 1-second **poller** that refreshes positions and pushes them into state.
- **`features/`** — option chain, trading (orders, positions, command bar), and the live chart (TradingView Lightweight Charts).
- **`ui/`** — layout, views, inputs, and **global hotkeys** (`b`/`s` to buy/sell, `1`/`2` to switch views, `f` for fullscreen, `Tab` to focus quantity) for a keyboard-first, terminal-like workflow.
- **`sync/`** — keeps the DOM in sync with the central state on each refresh.

### Order-book depth analysis

`Analysis/depth_visualiser.py` reads recorded depth logs (bid/ask prices, quantities, per-second and rolling volume) and renders them as a time-vs-price heatmap, making it possible to inspect how liquidity at each price level evolved over a session.

## Tech stack

- **Python** — backend, data layer, paper-trading engine
- **Flask + gunicorn** — web terminal and JSON API
- **Angel One SmartAPI** (`smartapi-python`) — broker connectivity, with `pyotp` for TOTP auth
- **pandas / numpy** — data handling
- **Textual / Rich** — terminal UI and live rendering
- **JavaScript (ES modules)** — front-end terminal
- **TradingView Lightweight Charts** — candlestick charting
- **matplotlib / plotly** — depth and analysis visualizations

## Getting started

> Requires a valid Angel One trading account and SmartAPI credentials. Even so, all order placement in Nyx is simulated.

```bash
pip install -r requirements.txt
```

Create a `.env` file (see `.env.example`) with your SmartAPI credentials:

```
API_KEY   = "your api key"
USERNAME  = "your client id"
PIN       = "your pin"
TOKEN     = "your TOTP secret"
```

**Run the terminal (TUI) version:**

```bash
python main.py
```

**Run the web terminal (dev):**

```bash
python launch.py
# then open http://127.0.0.1:29916
```

**Run the web terminal (production-style):**

```bash
gunicorn web_launch:app
```

## Notes and caveats

- Credentials are read from environment variables and never committed; `.env` is git-ignored and only `.env.example` is tracked.
- Position state is held in memory by the running engine, so it resets when the server restarts — there is no persistence layer.
- The web UI uses 1-second polling rather than a push socket to the browser; the broker websocket is used server-side for the market feed.
- Built and tested against NIFTY index options on the NSE/NFO segment.

## Possible extensions

- Replace browser polling with server-sent events or websockets for lower-latency UI updates.
- Add a persistence layer so positions and trade history survive restarts.
- Expand the simulator into a full historical replay / backtesting mode.
- Add limit and stop orders alongside the current market-order flow.
