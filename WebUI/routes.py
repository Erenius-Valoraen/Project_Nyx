from __future__ import annotations
import re
from turtle import mode
from flask import Blueprint, current_app, jsonify, render_template, request
from datetime import datetime
webui_bp = Blueprint("webui", __name__)


def _paper_engine():
    engine = current_app.config.get("PAPER_ENGINE")
    if engine is None:
        raise RuntimeError("PAPER_ENGINE not configured on Flask app")
    return engine




# =========================
# PAGES
# =========================

@webui_bp.get("/")
def index():
    engine = _paper_engine()
    return render_template(
        "index.html",
        contract_symbol=engine.selected_symbol,
        contracts=list(engine.contracts.keys()),
    )


@webui_bp.get("/paper")
def paper_trading():
    engine = _paper_engine()
    return render_template(
        "main_terminal.html",
        contract_symbol=engine.selected_symbol,
        contracts=list(engine.contracts.keys()),
    )


# =========================
# API
# =========================

@webui_bp.get("/api/health")
def health():
    engine = _paper_engine()
    return jsonify(
        {
            "ok": True,
            "selected_contract": engine.selected_symbol,
            "contracts": list(engine.contracts.keys()),
            "positions": len(engine.get_positions()),
            "total_trades_executed": engine.total_trades_executed,
        }
    )


@webui_bp.get("/api/state")
def state():
    engine = _paper_engine()

    # ONE market fetch, ONE update pass
    market_updates = engine.update_open_positions()
    market_map = {p: data for p, data in market_updates}

    payload = []

    for p in engine.get_positions():
        opening = p.opening_order
        contract = opening.contract if opening else None

        market = market_map.get(p)

        open_qty = p.open_qty
        side = "buy" if open_qty > 0 else "sell" if open_qty < 0 else "flat"

        payload.append({
            "id": opening.identifier if opening else None,
            "sym": contract.symbol if contract else None,
            "side": side,
            "orig_qty": opening.quantity if opening else 0,
            "open_qty": open_qty,
            "entry": opening.price if opening else 0.0,
            "ltp": market["ltp"] if market else p.close_ltp or 0.0,
            "bid": market["bid"] if market else p.close_bid or 0.0,
            "ask": market["ask"] if market else p.close_ask or 0.0,
            "open_pl": p.open_pl,
            "closed_pl": p.closed_pl,
            "is_open": p.open,
        })

    return jsonify({
        "selected_contract": engine.selected_symbol,
        "positions": payload,
        "total_trades_executed": engine.total_trades_executed,
    })


@webui_bp.post("/api/order")
def order():
    engine = _paper_engine()
    payload = request.get_json(silent=True) or {}

    try:
        quantity = int(payload.get("quantity", 0))
    except Exception:
        quantity = 0

    side = (payload.get("side") or "").lower().strip()

    if quantity <= 0:
        return jsonify({"ok": False, "error": "quantity must be > 0"}), 400
    if side not in {"buy", "sell"}:
        return jsonify({"ok": False, "error": "side must be buy/sell"}), 400

    try:
        pos = engine.market_order_selected(quantity, side)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify({
        "ok": True,
        "selected_contract": engine.selected_symbol,
        "open_qty": pos.open_qty,
        "total_trades_executed": engine.total_trades_executed,
    })


@webui_bp.post("/api/select_contract")
def select_contract():
    engine = _paper_engine()
    payload = request.get_json(silent=True) or {}
    symbol = (payload.get("symbol") or "").strip()

    try:
        engine.select_contract(symbol)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    return jsonify({
        "ok": True,
        "selected_contract": engine.selected_symbol,
    })

@webui_bp.post("/api/opt_ltp")
def opt_ltp():
    engine = _paper_engine()
    payload = request.get_json(silent=True) or {}
    contracts = payload.get("contracts")
    contract_data = []

    for instrument in contracts[:49]:
        inst_data = split_option_symbol(instrument)
        contract_data.append({
            'expiry': inst_data['Expiry'],
            'strike': inst_data['Strike'],
            'option_type': inst_data['Type']
        })
    # data = {
    #         'expiry': contract['Expiry'],
    #         'strike': contract['Strike'],
    #         'option_type': contract['Type']
    #     }

    ltp = engine.api.batch_opt_ltp(contract_data, mode="LTP")
    return jsonify({
        "ok": True,
        "data": ltp#should go here

    })

def split_option_symbol(symbol):
    # Regex Breakdown:
    # ([A-Z]+)         : Matches the instrument name (e.g., NIFTY)
    # (\d{2}[A-Z]{3}\d{2}) : Matches the expiry date (e.g., 03FEB26)
    # (\d+)            : Matches the strike price (e.g., 25600)
    # (CE|PE)          : Matches the option type (CE or PE)
    pattern = r"^([A-Z]+)(\d{2}[A-Z]{3}\d{2})(\d+)(CE|PE)$"
    
    match = re.match(pattern, symbol)
    
    if match:
        return {
            "Instrument": match.group(1),
            "Expiry": match.group(2),
            "Strike": match.group(3),
            "Type": match.group(4)
        }
    else:
        return "Invalid Symbol Format"

@webui_bp.get('/api/nifty_ltp')
def nifty_ltp():
    api = _paper_engine().api
    niftyPrice = api.nifty_spot()

    return jsonify({
        'ok': True,
        'response': {"ltp": niftyPrice}
    })

@webui_bp.post("/api/candles")
def nifty_ohlc():
    """
    Returns historical OHLC candles for NIFTY
    time must be UNIX timestamp (seconds)
    """
    engine = _paper_engine()
    payload = request.get_json(silent=True) or {}
    instrument = payload.get("instrument")
    timeframe = payload.get("timeframe")
    # Use UTC instead of local time
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    # print(instrument)
    # print(timeframe)
    IST_OFFSET = 5*3600 + 30*60 #+5HOURS 30 MINUTES FOR INDIAN TIME
    candles = engine.api.candles(instrument, timeframe, '2000-01-01 09:15', current_time, type='opt')

    converted_data = []

    for entry in candles:
        # entry structure: [timestamp, open, high, low, close, volume]
        
        # Parse ISO-8601 string and convert to Unix timestamp (seconds)
        unix_time = int(datetime.fromisoformat(entry[0]).timestamp())
        
        ist_display_timestamp = unix_time + IST_OFFSET
        
        converted_data.append({
            "time": ist_display_timestamp,
            "open": entry[1],
            "high": entry[2],
            "low": entry[3],
            "close": entry[4]
        })

    # candles = [
    #     {
    #         "time": 1706784000,
    #         "open": 22540,
    #         "high": 22610,
    #         "low": 22520,
    #         "close": 22590
    #     },
    #     # ...
    # ]

    return jsonify(converted_data)