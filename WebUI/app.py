from __future__ import annotations

from flask import Flask

from WebUI.routes import webui_bp
import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
def create_app(*, paper_engine) -> Flask:
    """
    App factory for the Flask web UI.

    `paper_engine` is an instance of `Trading.paper_trading.PaperTrading`.
    We keep it injected here to avoid changing existing logic.
    """
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["PAPER_ENGINE"] = paper_engine

    app.register_blueprint(webui_bp)
    return app

