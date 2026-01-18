from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from logzero import logger
from API.api_util import API, OptionChain
from pprint import pp
from queue import Queue
import os
import time

API_KEY = "----"
CLIENT_CODE = "----"

api = API()
api.login(API_KEY, CLIENT_CODE, '---', "-----")
chain = OptionChain(api)
option = chain.find(9, "06JAN2026", "CE")

AUTH_TOKEN = api.authToken
FEED_TOKEN = api.feedToken
correlation_id = "abc123"
action = 1
mode = 3

token_list = [
    {
        "exchangeType": 2,
        "tokens": [option.token]
    }
]
token_list1 = [
    {
        "action": 0,
        "exchangeType": 1,
        "tokens": ["26009"]
    }
]

sws = SmartWebSocketV2(AUTH_TOKEN, API_KEY, CLIENT_CODE, FEED_TOKEN)
tick_queue = Queue()
def on_data(wsapp, message):
    tick_queue.put(message)

    now_ms = int(time.time() * 1000)

    # SmartAPI sends exchange timestamps inside the message dict
    ex_ts = message["exchange_timestamp"]

    os.system("clear")
    pp(message)

    if ex_ts:
        latency_ms = now_ms - ex_ts
        print(f"[LATENCY] {latency_ms} ms")
    # close_connection()

def on_open(wsapp):
    logger.info("on open")
    sws.subscribe(correlation_id, mode, token_list)
    # sws.unsubscribe(correlation_id, mode, token_list1)


def on_error(wsapp, error):
    logger.error(error)


def on_close(wsapp):
    logger.info("Close")



def close_connection():
    sws.close_connection()


# Assign the callbacks.
sws.on_open = on_open
sws.on_data = on_data
sws.on_error = on_error
sws.on_close = on_close

sws.connect()
