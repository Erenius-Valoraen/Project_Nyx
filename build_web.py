from WebUI.app import create_app
from WebUI.resource_prep import ChainPrep
from API.api_util import API
from dotenv import load_dotenv
import os
import threading
import webview
import sys

hostname = '127.0.0.1'
port = 29916
from dotenv import load_dotenv
import os
import sys

def load_env():
    import sys
    import os
    from dotenv import load_dotenv

    # Case 1: PyInstaller
    if getattr(sys, 'frozen', False):
        exe_path = sys.executable

        # If running as .app bundle
        if ".app/Contents/MacOS" in exe_path:
            base_path = exe_path.split(".app/Contents/MacOS")[0]
            base_path = os.path.dirname(base_path)
        else:
            base_path = os.path.dirname(exe_path)

    # Case 2: Normal Python run
    else:
        base_path = os.getcwd()

    env_path = os.path.join(base_path, ".env")

    if not os.path.exists(env_path):
        raise RuntimeError(
            f".env file not found.\n"
            f"Expected location:\n{env_path}\n\n"
            "Place .env next to the .app or executable."
        )

    load_dotenv(env_path)

def build_paper_engine():
    """
    Mirrors the construction pattern in `main.py`, but does not start the terminal UI.
    """
    load_env()

    api_key = os.getenv("API_KEY")
    username = os.getenv("USERNAME")
    pin = os.getenv("PIN")
    token = os.getenv("TOKEN")

    api = API()
    api.login(api_key, username, pin, token)
    api.prepare_resources(ignore_run_check=False)

    chain = ChainPrep(api)
    
    return chain.engine

def start_flask(app):
    """
    Starts the Flask app on a separate thread.
    """
    # Disable reloader for thread
    app.run(host=hostname, port=port, debug=False, use_reloader=False)

def resource_path(relative_path):
    """
    Get absolute path for PyInstaller packaged files.
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def main():
    paper_engine = build_paper_engine()
    app = create_app(paper_engine=paper_engine)

    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=start_flask, args=(app,))
    flask_thread.daemon = True
    flask_thread.start()

    # Launch pywebview GUI
    webview.create_window(
        "Trading Dashboard",
        f"http://{hostname}:{port}",
        width=1200,
        height=800,
        resizable=True
    )
    webview.start()

if __name__ == "__main__":
    main()