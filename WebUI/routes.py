from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template, request

webui_bp = Blueprint("webui", __name__)


def _paper_engine():
    engine = current_app.config.get("PAPER_ENGINE")
    if engine is None:
        raise RuntimeError("PAPER_ENGINE not configured on Flask app")
    return engine


@webui_bp.get("/")
def index():
    engine = _paper_engine()
    contract = getattr(engine, "contract", None)
    return render_template(
        "index.html",
        contract_symbol=getattr(contract, "symbol", None),
    )


# @webui_bp.route("/dashboard")
# def webui_main():
#     return render_template("webui.html")




@webui_bp.get("/paper")
def paper_trading():
    engine = _paper_engine()
    contract = getattr(engine, "contract", None)
    return render_template(
        "main_terminal.html",
        contract_symbol=getattr(contract, "symbol", None),
    )


@webui_bp.get("/api/health")
def health():
    engine = _paper_engine()
    contract = getattr(engine, "contract", None)
    return jsonify(
        {
            "ok": True,
            "contract_symbol": getattr(contract, "symbol", None),
            "positions": len(getattr(engine, "positions", []) or []),
            "total_trades_executed": getattr(engine, "total_trades_executed", None),
        }
    )


@webui_bp.get("/api/state")
def state():
    """
    State snapshot matching terminal UI format.
    Note: Calling Position.update() uses existing logic and may fetch live depth/quotes.
    """
    engine = _paper_engine()

    positions_payload = []
    for p in getattr(engine, "positions", []) or []:
        market = None
        try:
            market = p.update()
        except Exception:
            # Keep the UI resilient even if market data is temporarily unavailable.
            market = None

        opening = getattr(p, "opening_order", None)
        contract = getattr(opening, "contract", None) if opening else None

        open_qty = getattr(p, "open_qty", 0)
        side = (
            "buy" if open_qty > 0
            else "sell" if open_qty < 0
            else "flat"
        )

        positions_payload.append({
            "id": getattr(opening, "identifier", None) if opening else None,
            "sym": getattr(contract, "symbol", None) if contract else None,
            "side": side,
            "orig_qty": getattr(opening, "quantity", 0) if opening else 0,
            "open_qty": open_qty,
            "entry": getattr(opening, "price", 0.0) if opening else 0.0,
            "ltp": market.get("ltp", 0.0) if market else 0.0,
            "bid": market.get("bid", 0.0) if market else 0.0,
            "ask": market.get("ask", 0.0) if market else 0.0,
            "open_pl": getattr(p, "open_pl", 0.0),
            "closed_pl": getattr(p, "closed_pl", 0.0),
            "is_open": getattr(p, "open", False),
        })

    return jsonify({
        "total_trades_executed": getattr(engine, "total_trades_executed", None),
        "positions": positions_payload,
    })


@webui_bp.post("/api/order")
def order():
    """
    Place a paper market order.

    Expected JSON:
      { "quantity": 1, "side": "buy" | "sell" }
    """
    engine = _paper_engine()
    payload = request.get_json(silent=True) or {}

    try:
        quantity = int(payload.get("quantity", 0))
    except Exception:
        quantity = 0

    side = (payload.get("side") or "").strip().lower()
    if quantity <= 0:
        return jsonify({"ok": False, "error": "quantity must be > 0"}), 400
    if side not in {"buy", "sell"}:
        return jsonify({"ok": False, "error": "side must be 'buy' or 'sell'"}), 400

    try:
        pos = engine.market_order(quantity, side)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify(
        {
            "ok": True,
            "position_open": getattr(pos, "open", None),
            "position_open_qty": getattr(pos, "open_qty", None),
            "total_trades_executed": getattr(engine, "total_trades_executed", None),
        }
    )

