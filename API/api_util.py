from SmartApi import SmartConnect 
import pyotp
from logzero import logger

import requests
import os
import pandas as pd
import datetime
from datetime import date
import json

import math
from tabulate import tabulate
from colorama import init, Fore, Back, Style

from bisect import bisect_left

from API.shutdown import ShutdownManager

# Initialize colorama for Windows compatibility
init(autoreset=True)

class API:
    """
    Core interface for interacting with the SmartApi ecosystem. This class handles 
    authentication, session management, and provides high-level methods for 
    fetching market data, managing resource files (JSON lookups), and retrieving 
    instrument tokens for both Equity and Options segments.
    """
    def __init__(self):
        """
        Initializes the API controller, sets up default directory paths for logging 
        and JSON metadata storage, and initializes the ShutdownManager to handle 
        clean application exits.
        """
        self.authToken = None
        self.feedToken = None
        self.exchanges = None
        
        # Define directory paths
        self.LOG_DIR = "logs/util"
        self.JSON_DIR = "jsonLookup"

        self.shutdown = ShutdownManager()

    def login(self, api_key, client_code, pin, qr_value):
        """
        Establishes a secure session with the SmartApi servers. It uses TOTP 
        authentication via the provided QR value, generates the necessary 
        JWT and Feed tokens for market data access, and retrieves the user's 
        allowed exchange segments.

        Args:
            api_key (str): The developer API key provided by the broker.
            client_code (str): The user's unique client ID.
            pin (str): The user's account PIN.
            qr_value (str): The secret key used for generating TOTP codes.
        """
        api_key = api_key
        username = client_code
        pwd = pin
        self.smartApi = SmartConnect(api_key)
        try:
            token = qr_value
            totp = pyotp.TOTP(token).now()
        except Exception as e:
            logger.error("Invalid Token: The provided token is not valid.")
            raise e

        correlation_id = "abcde"
        data = self.smartApi.generateSession(username, pwd, totp)

        if data['status'] == False:
            logger.error(data)
            
        else:
            authToken = data['data']['jwtToken']
            refreshToken = data['data']['refreshToken']
            feedToken = self.smartApi.getfeedToken()
            res = self.smartApi.getProfile(refreshToken)
            self.smartApi.generateToken(refreshToken)
            res=res['data']['exchanges']

            self.authToken = authToken
            self.feedToken = feedToken
            self.exchanges = res

    def prepare_resources(self, ignore_run_check=False):
        """
        Ensures the local environment is ready for trading operations. This includes 
        verifying directory existence, checking if the daily Scrip Master (instrument list) 
        has already been downloaded for the current date, and processing the master 
        file into optimized JSON segments for Nifty and Equity.

        Args:
            ignore_run_check (bool): If True, forces a re-download and re-processing 
                                    of resources even if they were already updated today.
        """
        # --- [NEW] Directory Safety Checks ---
        # This checks if folders exist; if not, it creates them.
        if not os.path.exists(self.LOG_DIR):
            os.makedirs(self.LOG_DIR, exist_ok=True)
            print(f"Created missing directory: {self.LOG_DIR}")

        if not os.path.exists(self.JSON_DIR):
            os.makedirs(self.JSON_DIR, exist_ok=True)
            print(f"Created missing directory: {self.JSON_DIR}")
        # -------------------------------------

        self.RUN_LOG = os.path.join(self.LOG_DIR, "last_run.txt")
        self.today = date.today().strftime("%Y-%m-%d")
        
        # 1. Check if the function ran successfully today
        if os.path.exists(self.RUN_LOG) and not ignore_run_check:
            try:
                with open(self.RUN_LOG, 'r') as f:
                    last_run_date = f.read().strip()
                    if last_run_date == self.today:
                        print(f"[{self.today}] Status: Already run successfully today. Skipping download.")
                        return
            except IOError:
                print("Warning: Could not read run log. Proceeding with download.")

        print(f"[{self.today}] Status: First run of the day. Starting download and processing.")

        self.download_scrip_master()
        self.make_equity_json()
        self.make_nifty_json()

    def download_scrip_master(self):
        """
        Fetches the complete Scrip Master JSON from the broker's server. This file 
        contains all tradable instruments across all exchanges. The file is saved 
        locally to minimize network calls during subsequent token lookups.
        """
        URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        FILE_NAME = "ScripMaster.json"
        
        # Uses the directory ensured in prepare_resources
        target_path = os.path.join(self.JSON_DIR, FILE_NAME)

        try:
            # pd.read_json handles the HTTP request and converts the data to a DataFrame
            df = pd.read_json(URL)
            
            # Save the DataFrame back to a JSON file
            df.to_json(target_path, orient='records', indent=4)
                
            print(f"Success: File downloaded and saved to '{target_path}'.")

            # 4. Log successful run date
            with open(self.RUN_LOG, 'w') as f:
                f.write(self.today)
                
        except requests.exceptions.RequestException as e:
            print(f"Error: Failed to download the file. Check URL or network connection. Error details: {e}")
        except Exception as e:
            print(f"An error occurred during Pandas processing or file write: {e}")

    # <Options> ----------------------------------------
    def make_nifty_json(self):
        """
        Filters the full Scrip Master file to extract only NIFTY index options (OPTIDX). 
        The resulting subset is saved to 'nifty_options.json' for significantly 
        faster lookup performance when building option chains.
        """
        input_file_path = os.path.join(self.JSON_DIR, "ScripMaster.json")
        output_file_path = os.path.join(self.JSON_DIR, "nifty_options.json")

        try:
            with open(input_file_path, "r") as infile:
                data = json.load(infile)

            filtered_entries = []
            for entry in data:
                if (entry.get("name") == "NIFTY" and
                    entry.get("exch_seg") == "NFO" and
                    entry.get("instrumenttype") == "OPTIDX"):
                    filtered_entries.append(entry)

            with open(output_file_path, "w") as outfile:
                json.dump(filtered_entries, outfile, indent=4)
            
            print(f"Filtered entries saved to '{output_file_path}'")

        except FileNotFoundError:
            print(f"Error: The input file '{input_file_path}' was not found.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def get_nifty_token(self, expiry, strike, option_type):
        """
        Retrieves the unique instrument token. Accepts DDMMMYY or DDMMMYYYY.
        """
        try:
            # 1. Normalize Expiry Format
            # Check if format is DDMMMYY (7 chars) like '03FEB26'
            if len(expiry) == 7:
                # Insert '20' before the last two digits: 03FEB + 20 + 26
                expiry = f"{expiry[:-2]}20{expiry[-2:]}"
            
            # 2. Normalize Strike (Ensure it's a float/int before multiplying)
            strike_json = float(strike) * 100
            option_type_json = option_type.upper()
            
            path = os.path.join(self.JSON_DIR, "nifty_options.json")
            
            with open(path, "r") as file:
                data = json.load(file)

            for contract in data:
                # Using str() comparison for strike to avoid float precision issues in JSON
                if (
                    contract.get("expiry") == expiry
                    and float(contract.get("strike")) == strike_json
                    and option_type_json in contract.get("symbol", "")
                ):
                    return contract.get("token")

        except FileNotFoundError:
            print(f"Error: The file '{path}' was not found.")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error processing data: {e}")

        return None
    
    def opt_ltp(self, expiry, strike, option_type):
        """
        Fetches the Last Traded Price (LTP) for a specific Nifty option contract.

        Args:
            expiry (str): Expiry date (e.g., '28JAN2026').
            strike (float): Strike price.
            option_type (str): 'CE' or 'PE'.

        Returns:
            float: The current LTP or 0 if the token cannot be found.
        """
        token = self.get_nifty_token(expiry, strike, option_type)
        if token:
            ltp_data = self.smartApi.ltpData(exchange="NFO", tradingsymbol= f"NIFTY{expiry}{strike}{option_type}", symboltoken=token)
            return ltp_data['data']['ltp']
        return 0
    
    def batch_opt_ltp(self, contracts, mode="LTP"):
        """
        Retrieves market data (LTP or Depth) for multiple option contracts in 
        a single API request to optimize performance and respect rate limits.

        Args:
            contracts (list): List of Contract objects or dictionaries containing 
                              expiry, strike, and option_type.
            mode (str): Data mode, typically "LTP" or "FULL".

        Returns:
            dict: A mapping of trading symbols to their respective LTP or market depth.
        """
        tokens = []
        if isinstance(contracts[0], Contract):
            for contract in contracts:
                tokens.append(contract.token)
        else:
            for contract in contracts:
                token = str(self.get_nifty_token(contract['expiry'], contract['strike'], contract['option_type']))
                if token and token != "None":
                    tokens.append(token)
        
        if not tokens:
            return {}

        data = self.smartApi.getMarketData(mode=mode, exchangeTokens= {
            "NFO": tokens
        })

        if not data.get('data'):
             return {}

        items = data["data"]["fetched"]
        if mode == "LTP":
            ltp_map = {}
            for item in items:
                symbol = item["tradingSymbol"]
                ltp = item["ltp"]
                ltp_map[symbol] = ltp
        
            return ltp_map
        
        else:
            depth_map = {}
            for symbol in items:
                depth_map[symbol['tradingSymbol']] = symbol['depth']
            
            return depth_map

    def opt_depth(self, expiry, strike, option_type):
        """
        Retrieves the market depth (bid/ask ladders) for a specific Nifty option.

        Args:
            expiry (str): Expiry date string.
            strike (float): Strike price.
            option_type (str): 'CE' or 'PE'.

        Returns:
            dict: The depth data containing the top 5 bids and asks.
        """
        token = self.get_nifty_token(expiry, strike, option_type)
        if not token: return None

        data = self.smartApi.getMarketData(mode="FULL", exchangeTokens= {
            "NFO": [str(token)]
        })
        return data['data']['fetched'][0]['depth']
    
    def opt_full(self, expiry, strike, option_type):
        """
        Retrieves the complete market data snapshot for an option contract, 
        including OHLC, LTP, volume, and depth.

        Args:
            expiry (str): Expiry date string.
            strike (float): Strike price.
            option_type (str): 'CE' or 'PE'.

        Returns:
            dict: Full market data payload for the instrument.
        """
        token = self.get_nifty_token(expiry, strike, option_type)
        if not token: return None

        data = self.smartApi.getMarketData(mode="FULL", exchangeTokens= {
            "NFO": [str(token)]
        })
        return data['data']['fetched'][0]

    def nifty_spot(self):
        """
        Retrieves the current spot price of the NIFTY 50 index from the NSE.

        Returns:
            float: The current index level of Nifty 50.
        """
        return self.smartApi.ltpData(exchange="NSE", tradingsymbol="NIFTY 50", symboltoken="99926000")['data']['ltp']
    
    def opt_token_raw(self, instrument):
        path = os.path.join(self.JSON_DIR, "nifty_options.json")

        with open(path, "r") as file:
            data = json.load(file)

        for contract in data:
            if (contract.get('symbol')) == instrument:
                token = contract.get('token')
        return token


    
    # </Options> --------------------------------------

    # <Equity> ----------------------------------------
    def make_equity_json(self):
        """
        Filters the Scrip Master to extract NSE equity instruments, excluding 
        derivatives and other segments. Saves the results to 'equity_nse.json' 
        for efficient stock token retrieval.
        """
        input_file_path = os.path.join(self.JSON_DIR, "ScripMaster.json")
        output_file_path = os.path.join(self.JSON_DIR, "equity_nse.json")

        try:
            with open(input_file_path, "r") as infile:
                data = json.load(infile)

            filtered_entries = []
            for entry in data:
                if (entry.get("exch_seg") == "NSE" and
                    entry.get("instrumenttype") == ""):
                    filtered_entries.append(entry)

            with open(output_file_path, "w") as outfile:
                json.dump(filtered_entries, outfile, indent=4)
            
            print(f"Filtered entries saved to '{output_file_path}'")

        except FileNotFoundError:
            print(f"Error: The input file '{input_file_path}' was not found.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def get_equity_token(self, symbol):
        """
        Retrieves the instrument token for a specific NSE equity symbol.

        Args:
            symbol (str): The trading symbol of the stock (e.g., 'RELIANCE').

        Returns:
            str: The instrument token if the symbol is found, otherwise None.
        """
        try:
            path = os.path.join(self.JSON_DIR, "equity_nse.json")
            with open(path, "r") as file:
                data = json.load(file)

            for equity in data:
                if equity.get("name") == symbol.strip().upper():
                    return equity.get("token")

        except FileNotFoundError:
            print(f"Error: The file '{path}' was not found.")
        return None

    def eq_ltp(self, symbol):
        """
        Fetches the current Last Traded Price (LTP) for an equity symbol.

        Args:
            symbol (str): The trading symbol of the stock.

        Returns:
            float: The current market price of the stock.
        """
        token = self.get_equity_token(symbol)
        ltp_data = self.smartApi.ltpData(exchange="NSE", tradingsymbol=symbol.strip().upper(), symboltoken=token)
        return ltp_data['data']['ltp']
    
    def batch_eq_ltp(self, symbols, mode="LTP"):
        """
        Fetches market data for a list of equity symbols in a single request.

        Args:
            symbols (list): A list of stock symbols.
            mode (str): Data mode, defaults to "LTP".

        Returns:
            dict: Mapping of symbols to their respective market prices.
        """
        tokens = []
        for symbol in symbols:
            token = str(self.get_equity_token(symbol))
            if token:
                tokens.append(token)
        
        data = self.smartApi.getMarketData(mode=mode, exchangeTokens= {
            "NSE": tokens
        })

        items = data["data"]["fetched"]
        ltp_map = {}
        for item in items:
            symbol = item["tradingSymbol"]
            ltp = item["ltp"]
            ltp_map[symbol] = ltp
        
        return ltp_map

    def eq_depth(self, symbol):
        """
        Retrieves the market depth (bid/ask ladder) for a specific equity stock.

        Args:
            symbol (str): The trading symbol.

        Returns:
            dict: The depth data including top bids and asks.
        """
        token = self.get_equity_token(symbol)
        data = self.smartApi.getMarketData(mode="FULL", exchangeTokens= {
            "NSE": [str(token)]
        })
        return data['data']['fetched'][0]['depth']
    
    def candles(self, symbol, interval, from_date, to_date, type='eq'):
        """
        Retrieves historical OHLC candle data for an equity instrument.

        Args:
            symbol (str): Trading symbol.
            interval (str): Timeframe (e.g., 'ONE_MINUTE', 'ONE_DAY').
            from_date (str): Start date/time (YYYY-MM-DD HH:MM).
            to_date (str): End date/time (YYYY-MM-DD HH:MM).

        Returns:
            list: Historical candle data payload.
        """
        if type=='eq':
            token = self.get_equity_token(symbol)
        elif type=='opt':
      
            path = os.path.join(self.JSON_DIR, "nifty_options.json")

            with open(path, "r") as file:
                data = json.load(file)

            for contract in data:
                if (contract.get('symbol')) == symbol:
                    token = contract.get('token')

        try:
            candles = self.smartApi.getCandleData(
                historicDataParams= {
                "exchange":"NSE" if type=='eq' else "NFO",
                "symboltoken":str(token),
                "interval":interval,
                "fromdate":from_date,
                "todate":to_date
                }
            )
        except Exception as e:
            print(e)
        # print(candles)
        return candles['data']
    # </Equity> --------------------------------------

# ------------------------------------------------------------------
# CLASSES: Contract, OptionChain, Expiry
# (These remain mostly the same, but OptionChain now creates directory if passed)
# ------------------------------------------------------------------

class Contract:
    """
    Represents a single derivative contract (Option). This class wraps raw contract 
    data and provides helper methods to fetch its current market price, depth, 
    and other relevant financial metrics.
    """
    def __init__(self, chain, contract_data):
        """
        Initializes the Contract object by parsing strike price and determining 
        if it is a Call (CE) or Put (PE) based on the symbol name.

        Args:
            chain (OptionChain): Reference to the parent OptionChain object.
            contract_data (dict): Raw dictionary data from the Scrip Master.
        """
        self.chain = chain
        self.data = contract_data
        self.token = contract_data.get('token')
        self.symbol = contract_data.get('symbol')
        self.expiry = contract_data.get('expiry')
        
        raw_strike = contract_data.get('strike', 0)
        self.strike = float(raw_strike) / 100
        
        if "PE" in self.symbol[-2:]:
            self.option_type = "PE"
        else:
            self.option_type = "CE"
    
    def ltp(self):
        """
        Retrieves the current Last Traded Price for this specific contract.

        Returns:
            float: The current market price.
        """
        return self.chain.api.opt_ltp(self.expiry, self.strike, self.option_type)

    def depth(self):
        """
        Retrieves the full market depth (order book) for this contract.

        Returns:
            dict: Object containing 'buy' (bids) and 'sell' (asks) lists.
        """
        return self.chain.api.opt_depth(self.expiry, self.strike, self.option_type)

    def bid(self):
        """
        Fetches the best available bid price (highest price a buyer is offering).

        Returns:
            float: The top bid price, or None if unavailable.
        """
        d = self.depth()
        return d.get('buy', [{}])[0].get('price', None) if d else None
    
    def ask(self):
        """
        Fetches the best available ask price (lowest price a seller is accepting).

        Returns:
            float: The top ask price, or None if unavailable.
        """
        d = self.depth()
        return d.get('sell', [{}])[0].get('price', None) if d else None

    def full(self):
        """
        Retrieves the full market data payload for this contract.

        Returns:
            dict: Complete snapshot including OHLC and volume.
        """
        return self.chain.api.opt_full(self.expiry, self.strike, self.option_type)

    def __repr__(self):
        """
        Returns a string representation of the Contract object for debugging.
        """
        return f"<Contract: {self.symbol} | Strike: {self.strike}>"

class OptionChain:
    """
    Manages a collection of Contract objects for a specific underlying asset. 
    It provides functionality to search for specific strikes, find At-The-Money (ATM) 
    contracts, and display formatted option chains in the console.
    """
    def __init__(self, api, json_path='jsonLookup/nifty_options.json'):
        """
        Initializes the OptionChain, ensures the lookup directory exists, 
        and pre-calculates the current spot price of the underlying index.

        Args:
            api (API): Instance of the API controller.
            json_path (str): Path to the filtered Nifty options JSON file.
        """
        self.api = api
        self.json_path = json_path
        self.chain_data = []
        self.expiries = Expiry()
        
        # Ensure directory exists for safety
        folder = os.path.dirname(self.json_path)
        if folder and not os.path.exists(folder):
             os.makedirs(folder, exist_ok=True)

        self.spot_price = float(self.api.nifty_spot())
        self.load_chain()

    def load_chain(self):
        """
        Loads the filtered option contract data from the local JSON file into memory.
        """
        try:
            if not os.path.exists(self.json_path):
                print(f"Warning: {self.json_path} not found. Chain is empty. Run api.prepare_resources() first.")
                return

            with open(self.json_path, 'r') as f:
                self.chain_data = json.load(f)
        except Exception as e:
            print(f"Error loading JSON: {e}")

    def find(self, offset, expiry_date, option_type):
        """
        Locates a specific contract based on its distance from the ATM strike 
        or an absolute strike price.

        Args:
            offset (int/float): If > 100, treated as an absolute strike price. 
                               If <= 100, treated as a strike step offset from ATM.
            expiry_date (str): Target expiry date.
            option_type (str): 'CE' or 'PE'.

        Returns:
            Contract: The matching contract object, or None if not found.
        """
        candidates = []
        
        for item in self.chain_data:
            item_expiry = item.get('expiry')
            item_symbol = item.get('symbol')
            
            is_ce = "CE" in item_symbol or item_symbol.endswith("CE")
            current_type = "CE" if is_ce else "PE"

            if item_expiry == expiry_date and current_type == option_type:
                candidates.append(Contract(self, item))

        if not candidates:
            print(f"No contracts found for {expiry_date} {option_type}")
            return None

        candidates.sort(key=lambda x: x.strike)
        atm_contract = min(candidates, key=lambda x: abs(x.strike - self.spot_price))
        atm_index = candidates.index(atm_contract)
        
        target_index = None
        if offset > 100:
            target_strike = float(offset)
            for idx, contract in enumerate(candidates):
                if contract.strike == target_strike:
                    return contract
            print(f"No contract found with strike {target_strike}")
            return None
        else:
            target_index = atm_index + offset

        if 0 <= target_index < len(candidates):
            return candidates[target_index]
        else:
            print(f"Strike offset {offset} is out of bounds for this chain.")
            return None


    def get_chain(self, expiry_date, num_strikes=20):
        """
        Returns a structured dictionary of Call and Put contracts surrounding 
        the ATM strike for a specific expiry.

        Args:
            expiry_date (str): The expiry date to filter for.
            num_strikes (int): The number of strikes to include above and below ATM.

        Returns:
            dict: Contains 'ce' and 'pe' lists of contracts with their relative offsets.
        """
        chain_map = {}
        
        # 1. Filter and map data
        for item in self.chain_data:
            if item.get('expiry') != expiry_date:
                continue 
            c = Contract(self, item)
            if c.strike not in chain_map:
                chain_map[c.strike] = {'CE': None, 'PE': None}
            chain_map[c.strike][c.option_type] = c

        if not chain_map:
            return {"atm": None, "ce": [], "pe": []}

        # 2. Sort strikes and find ATM index
        sorted_strikes = sorted(chain_map.keys())
        atm_strike = min(sorted_strikes, key=lambda x: abs(x - self.spot_price))
        atm_index = sorted_strikes.index(atm_strike)

        # 3. Determine the slice (num_strikes above and below ATM)
        start_idx = max(0, atm_index - num_strikes)
        end_idx = min(len(sorted_strikes), atm_index + num_strikes + 1)
        
        result = {
            "ce": [],
            "pe": []
        }

        # 4. Populate with index-based offsets
        for i in range(start_idx, end_idx):
            strike = sorted_strikes[i]
            # Offset is current index minus the ATM index
            offset = i - atm_index
            
            ce_contract = chain_map[strike]['CE']
            pe_contract = chain_map[strike]['PE']

            if ce_contract:
                result["ce"].append({
                    "offset": offset,
                    "strike": strike,
                    "contract": ce_contract
                })
                
            if pe_contract:
                result["pe"].append({
                    "offset": offset,
                    "strike": strike,
                    "contract": pe_contract
                })

        return result

    def get_full_chain(self, num_strikes=10):
        """
        Aggregates all relevant contracts across multiple standard expiries 
        (weekly, monthly, yearly, etc.) into a single nested dictionary.

        Returns:
            dict: Mapping of expiry dates to their respective CE and PE contracts.
        """
        contracts = {}
        expiries = [self.expiries.weekly(expiry_skip_offset=-1), self.expiries.weekly(), self.expiries.bi_weekly(), self.expiries.monthly(), self.expiries.half_yearly(), self.expiries.yearly()]

        for expiry in expiries:
            contracts[expiry] = {'ce': [], 'pe': []}
            options = self.get_chain(expiry, num_strikes)
            for option in options['ce']:
                contracts[expiry]['ce'].append(option['contract'])

            for option in options['pe']:
                contracts[expiry]['pe'].append(option['contract'])
        
        return contracts


    def display(self, expiry_date, num_strikes=10):
        """
        Prints a visually rich, color-coded table of the option chain to 
        the console. It highlights the ATM strike and shows LTPs for both 
        Calls and Puts.

        Args:
            expiry_date (str): The expiry to visualize.
            num_strikes (int): How many strikes to show around the ATM.
        """
        chain_map = {}
        for item in self.chain_data:
            if item.get('expiry') != expiry_date:
                continue 
            c = Contract(self, item)
            if c.strike not in chain_map:
                chain_map[c.strike] = {'CE': None, 'PE': None}
            chain_map[c.strike][c.option_type] = c

        if not chain_map:
            print(f"{Fore.RED}No data found for expiry: {expiry_date}{Style.RESET_ALL}")
            return

        sorted_strikes = sorted(chain_map.keys())
        atm_strike = min(sorted_strikes, key=lambda x: abs(x - self.spot_price))
        atm_index = sorted_strikes.index(atm_strike)

        start_idx = max(0, atm_index - num_strikes)
        end_idx = min(len(sorted_strikes), atm_index + num_strikes + 1)
        visible_strikes = sorted_strikes[start_idx:end_idx]

        contracts = []
        for strike in visible_strikes:
            contracts.append({'expiry': expiry_date, 'strike': strike, 'option_type': 'CE'})
            contracts.append({'expiry': expiry_date, 'strike': strike, 'option_type': 'PE'})
        
        ltp_map = self.api.batch_opt_ltp(contracts)

        table_rows = []
        for strike in visible_strikes:
            ce_contract = chain_map[strike]['CE']
            pe_contract = chain_map[strike]['PE']

            # Safe get for prices
            ce_key = f"NIFTY{expiry_date.replace('20', '')}{int(strike)}CE"
            pe_key = f"NIFTY{expiry_date.replace('20', '')}{int(strike)}PE"

            try:
                ce_price = f"{ltp_map.get(ce_key, 0.0):.2f}" if ce_contract else "-"
                pe_price = f"{ltp_map.get(pe_key, 0.0):.2f}" if pe_contract else "-"
            except:
                ce_price, pe_price = "-", "-"
            
            strike_display = f"{strike:.2f}"
            is_atm = (strike == atm_strike)
            
            if is_atm:
                fmt_ce = f"{Back.CYAN}{Fore.BLACK} {ce_price} {Style.RESET_ALL}"
                fmt_st = f"{Back.CYAN}{Fore.BLACK} {strike_display} {Style.RESET_ALL}"
                fmt_pe = f"{Back.CYAN}{Fore.BLACK} {pe_price} {Style.RESET_ALL}"
                strike_display = f"--> {strike_display} <--"
            else:
                fmt_ce = f"{Fore.GREEN}{ce_price}{Style.RESET_ALL}"
                fmt_st = f"{Style.BRIGHT}{strike_display}{Style.RESET_ALL}"
                fmt_pe = f"{Fore.RED}{pe_price}{Style.RESET_ALL}"

            table_rows.append([fmt_ce, fmt_st, fmt_pe])

        headers = [f"{Fore.GREEN}CALLS (LTP){Style.RESET_ALL}", "STRIKE", f"{Fore.RED}PUTS (LTP){Style.RESET_ALL}"]
        print(f"\nOption Chain for {Fore.YELLOW}{expiry_date}{Style.RESET_ALL} (Spot: {self.spot_price})")
        print(tabulate(table_rows, headers=headers, tablefmt="fancy_grid", stralign="center"))





class Expiry:
    """
    Utility class for calculating and retrieving standardized expiry dates 
    available in the instrument list. It identifies weekly, monthly, 
    and long-term expiries dynamically.
    """
    def __init__(self, json_path="jsonLookup/nifty_options.json"):
        """
        Loads the available expiry dates from the local JSON file and 
        sorts them chronologically for easier searching.

        Args:
            json_path (str): Path to the Nifty options JSON file.
        """
        # Folder check
        folder = os.path.dirname(json_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        if not os.path.exists(json_path):
             print(f"Warning: {json_path} not found. Expiry functions will fail until setup is run.")
             self.expiries = []
             return

        with open(json_path, "r") as f:
            data = json.load(f)

        self.expiries = sorted(
            {self._parse_date(item["expiry"]) for item in data}
        )

    def _parse_date(self, expiry_str):
        """
        Converts the broker's date string format into a Python date object.

        Args:
            expiry_str (str): Date string like '28JAN2026'.

        Returns:
            datetime.date: Parsed date object.
        """
        return datetime.datetime.strptime(expiry_str, "%d%b%Y").date()

    def _format_date(self, dt):
        """
        Converts a Python date object back into the broker's string format.

        Args:
            dt (datetime.date): Date object.

        Returns:
            str: Upper-cased date string (e.g., '28JAN2026').
        """
        return dt.strftime("%d%b%Y").upper()

    def _find_nearest_expiry(self, target_date):
        """
        Finds the closest available expiry date in the future relative to 
         the target date using binary search (bisect).

        Args:
            target_date (datetime.date): The date to search from.

        Returns:
            datetime.date: The nearest available future expiry.
        """
        if not self.expiries: return None
        
        pos = bisect_left(self.expiries, target_date)
        if pos == 0: return self.expiries[0]
        if pos == len(self.expiries): return self.expiries[-1]

        before = self.expiries[pos - 1]
        after = self.expiries[pos]

        return after


    def weekly(self, expiry_skip_offset=0, from_date=None):
        """
        Retrieves the nearest weekly expiry date.

        Args:
            expiry_skip_offset (int): Days to add/subtract before finding expiry.
            from_date (datetime.date): The starting date for the calculation.

        Returns:
            str: Formatted expiry date string.
        """
        if from_date is None: from_date = datetime.date.today()
        target = from_date + datetime.timedelta(weeks=0) + datetime.timedelta(days=expiry_skip_offset + 1)
        res = self._find_nearest_expiry(target)
        return self._format_date(res) if res else None

    def bi_weekly(self, expiry_skip_offset=0, from_date=None):
        """
        Retrieves the expiry date for the week following the current one.

        Args:
            expiry_skip_offset (int): Days to shift the calculation.
            from_date (datetime.date): The starting date.

        Returns:
            str: Formatted expiry date string.
        """
        if from_date is None: from_date = datetime.date.today()
        target = from_date + datetime.timedelta(weeks=1) + datetime.timedelta(days=expiry_skip_offset + 1)
        res = self._find_nearest_expiry(target)
        return self._format_date(res) if res else None

    def monthly(self, from_date=None):
        """
        Calculates the approximate target for the next monthly expiry.

        Args:
            from_date (datetime.date): The starting date.

        Returns:
            str: Formatted expiry date string.
        """
        if from_date is None: from_date = datetime.date.today()
        month = from_date.month + 1
        year = from_date.year
        if month > 12:
            month -= 12
            year += 1
        day = min(from_date.day, 28)
        target = datetime.date(year, month, day)
        res = self._find_nearest_expiry(target)
        return self._format_date(res) if res else None

    def half_yearly(self, from_date=None):
        """
        Calculates the target for a 6-month forward expiry.

        Args:
            from_date (datetime.date): The starting date.

        Returns:
            str: Formatted expiry date string.
        """
        if from_date is None: from_date = datetime.date.today()
        month = from_date.month + 6
        year = from_date.year
        if month > 12:
            month -= 12
            year += 1
        day = min(from_date.day, 28)
        target = datetime.date(year, month, day)
        res = self._find_nearest_expiry(target)
        return self._format_date(res) if res else None

    def yearly(self, from_date=None):
        """
        Calculates the target for an expiry one year from the current date.

        Args:
            from_date (datetime.date): The starting date.

        Returns:
            str: Formatted expiry date string.
        """
        if from_date is None: from_date = datetime.date.today()
        target = datetime.date(from_date.year + 1, from_date.month, min(from_date.day, 28))
        res = self._find_nearest_expiry(target)
        return self._format_date(res) if res else None