import os
import json
import requests
import math

from binance.client import Client
from binance.enums import *
from loguru import logger


class BinanceConnector:

    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BinanceConnector, cls).__new__(cls)
            # Put any initialization here.
        return cls._instance

    def __init__(self) -> None:
        logger.info("Creating Binance client...")

        api_key = os.getenv("BINANCE_API_KEY")
        if api_key is None:
            raise RuntimeError("Missing BINANCE_API_KEY...")

        api_secret_key = os.getenv("BINANCE_SECRET_KEY")
        if api_secret_key is None:
            raise RuntimeError("Missing BINANCE_SECRET_KEY...")

        self._client = Client(api_key, api_secret_key)

    def _get_token_symbol(self, token: str):
        response = requests.request(
            "GET",
            f"http://api.coincap.io/v2/assets/{token}",
            headers={},
            data={},
        )
        text = response.text
        data = json.loads(text)
        data = data["data"]
        return data["symbol"]

    def _get_lot_size(self, symbol):
        response = requests.request(
            "GET",
            f"https://www.binance.com/api/v1/exchangeInfo",
            headers={},
            data={},
        )
        text = response.text
        data = json.loads(text)
        logger.info(data.keys())
        data = data["symbols"]
        for token in data:
            if token["symbol"] == symbol:
                for filter in token["filters"]:
                    if filter["filterType"] == "LOT_SIZE":
                        logger.info(
                            f"StepSize for {symbol} is: {filter['stepSize']}"
                        )
                        return float(filter["stepSize"])

    def get_token_balance(self, token: str):

        symbol = self._get_token_symbol(token)
        response = self._client.get_asset_balance(asset=symbol)
        logger.info(f"Current {token} balance: {response['free']}")
        return response["free"]

    def create_order(self, token: str, side: str, type: str, quantity: float):

        # Check: https://python-binance.readthedocs.io/en/latest/constants.html

        symbol = self._get_token_symbol(token)
        symbol = f"{symbol}USDT"
        step_size = self._get_lot_size(symbol)
        precision = int(round(-math.log(step_size, 10), 0))

        if type == ORDER_TYPE_MARKET:
            order = self._client.create_order(
                symbol=symbol,
                side=side,
                type=type,
                quantity=round(quantity, precision),
            )
            logger.info(f"Binance order: {order}")


binance = BinanceConnector()