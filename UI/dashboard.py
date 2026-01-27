# from textual.app import App
# from UI.paper_trading_ui import PaperTraderScreen
# from textual.screen import Screen
# from textual.widgets import Header, Footer, DataTable, Input, Button
# from textual.containers import Horizontal, Vertical
# from textual import work
# from rich.text import Text
# import threading
# import time


# class DashboardApp(App):
#     CSS_PATH = "ui.css"

#     BINDINGS = [
#         ("1", "paper", "Paper Trader"),
#         ("2", "positions", "Positions"),
#         ("3", "logs", "Logs"),
#         ("ctrl+c", "quit", "Quit"),
#     ]

#     def __init__(self, trading_system):
#         super().__init__()
#         self.system = trading_system

#     def on_mount(self):
#         # Install screen definitions
#         self.install_screen(PaperTraderScreen(), name="paper")

#         # FIRST screen must be PUSHED, not switched
#         self.push_screen("paper")

#     # ---------- ROUTES ----------

#     def action_paper(self):
#         self.switch_screen("paper")

#     def action_positions(self):
#         self.notify("Positions screen coming soon")

#     def action_logs(self):
#         self.notify("Logs screen coming soon")