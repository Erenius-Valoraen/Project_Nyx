from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template, request

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
    payload = []

    for p in engine.get_positions():
        try:
            market = p.update()
        except Exception:
            market = None

        opening = p.opening_order
        contract = opening.contract if opening else None

        open_qty = p.open_qty
        side = "buy" if open_qty > 0 else "sell" if open_qty < 0 else "flat"

        payload.append({
            "id": opening.identifier if opening else None,
            "sym": contract.symbol if contract else None,
            "side": side,
            "orig_qty": opening.quantity if opening else 0,
            "open_qty": open_qty,
            "entry": opening.price if opening else 0.0,
            "ltp": market["ltp"] if market else 0.0,
            "bid": market["bid"] if market else 0.0,
            "ask": market["ask"] if market else 0.0,
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