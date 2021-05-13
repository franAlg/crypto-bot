import os
import json
import datetime

import requests
from binance.enums import *
from loguru import logger

from crypto_bot.crypto import get_price_changes, get_top_crypto
from crypto_bot.aws import S3
from crypto_bot.binance import binance


INITIAL_BALANCE = 500

BUCKET_NAME = "cryptobotmetadata"
BALANCE_PATH = "balances.txt"  # balance
OPEN_POSITIONS_PATH = (
    "open_positions.txt"  # token, limit, stop, buy_price, amount, timestamp
)
TX_HISTORY_PATH = "transactions_history.txt"  # token, order(buy/sell), price, amount, timestamp


def reset_balance():
    S3.put_object(BUCKET_NAME, BALANCE_PATH, INITIAL_BALANCE)


def reset_positions():
    S3.put_object(BUCKET_NAME, OPEN_POSITIONS_PATH, empty=True)


def reset_transactions():
    S3.put_object(BUCKET_NAME, TX_HISTORY_PATH, empty=True)


def get_current_balance() -> int:

    current_balance = binance.get_token_balance("tether")
    logger.info(f"Current balance is: {current_balance}")

    return float(current_balance)


def get_open_positions():
    logger.info("Getting positions...")
    obj = S3.get_object(BUCKET_NAME, OPEN_POSITIONS_PATH)

    positions = []
    for line in obj["Body"].iter_lines():
        positions.append(json.loads(line.decode("utf-8")))

    return positions


def update_balance(balance):
    logger.info(f"Updating balance to: {balance}")
    S3.put_object(BUCKET_NAME, BALANCE_PATH, balance)


def register_transaction(audit):
    logger.info(f"Registering transaction: {json.dumps(audit)}")
    S3.append_to_object(BUCKET_NAME, TX_HISTORY_PATH, json.dumps(audit))


def open_position(token, amount):
    # Get token info
    response = requests.request(
        "GET", f"http://api.coincap.io/v2/assets/{token}", headers={}, data={}
    )
    text = response.text
    data = json.loads(text)
    data = data["data"]
    price = float(data["priceUsd"])
    limit = 0.05 * price + price
    stop = price - 0.02 * price
    amount = amount / price
    timestamp = round(datetime.datetime.now().timestamp() * 1000)
    transaction = {
        "token": token,
        "price": price,
        "limit": limit,
        "stop": stop,
        "amount": amount,
        "timestamp": timestamp,
    }
    logger.info(f"Opening position: {transaction}")
    binance.create_order(token, SIDE_BUY, ORDER_TYPE_MARKET, amount)

    S3.append_to_object(
        BUCKET_NAME, OPEN_POSITIONS_PATH, json.dumps(transaction)
    )
    audit = {
        "token": token,
        "order": "buy",
        "price": price,
        "amount": amount,
        "timestamp": timestamp,
    }

    register_transaction(audit)


def evaluate_positions(positions, current_balance):
    logger.info("Evaluating positions...")

    rank = int(os.getenv("CRYPTO_RANK", "20"))
    market_cap_limit = int(os.getenv("CRYPTO_MARKET_CAP_LIMIT", "1000000000"))
    timeframe = int(os.getenv("CRYPTO_TIMEFRAME", "12"))

    df = get_top_crypto(rank=rank, market_cap_limit=market_cap_limit)
    price_change_rank = get_price_changes(df, timeframe=timeframe)

    n_positions = len(positions)

    if len(price_change_rank) > 0:
        if n_positions == 0:
            logger.info("Opening 2 positions...")
            open_position(price_change_rank[0], current_balance / 2)
            if len(price_change_rank) > 1:
                current_balance = get_current_balance()
                open_position(price_change_rank[1], current_balance)
                update_balance(0)
            else:
                logger.info(
                    "List rank only has one token... skipping one open order until next execution"
                )
                update_balance(get_current_balance())
        if n_positions == 1:
            logger.info("Opening 1 positions...")
            for position in price_change_rank:
                if position not in " ".join(
                    [item["token"] for item in positions]
                ):
                    open_position(position, current_balance)
                    break
            update_balance(0)
        if n_positions == 2:
            logger.info("Waiting till next execution...")
    else:
        logger.info("No positions to open... waiting till next execution")


def evaluate_sell_positions(positions, current_balance):

    updated = False
    for index, position in enumerate(positions):
        # Get token info
        response = requests.request(
            "GET",
            f"http://api.coincap.io/v2/assets/{position['token']}",
            headers={},
            data={},
        )
        text = response.text
        data = json.loads(text)
        data = data["data"]
        price = float(data["priceUsd"])
        if price > position["limit"]:
            updated = True
            position["price"] = price
            position["stop"] = position["limit"] - 0.02 * position["limit"]
            position["limit"] = 0.05 * price + price
            position["timestamp"] = round(
                datetime.datetime.now().timestamp() * 1000
            )
            logger.info(f"Updated open position: {json.dumps(position)}")
            register_transaction(position)
        elif price < position["stop"]:

            binance.get_token_balance(position["token"])
            binance.create_order(
                position["token"],
                SIDE_SELL,
                ORDER_TYPE_MARKET,
                position["amount"],
            )
            audit = {
                "token": position["token"],
                "order": "sell",
                "price": position["stop"],
                "amount": position["amount"],
                "timestamp": round(datetime.datetime.now().timestamp() * 1000),
            }
            profit = position["stop"] * position["amount"]
            register_transaction(audit)
            update_balance(current_balance + profit)
            del positions[index]
        else:
            logger.info(f"No changes in position: {position['token']}")

    if updated:
        positions = [json.dumps(item) for item in positions]
        S3.put_object(BUCKET_NAME, OPEN_POSITIONS_PATH, "\n".join(positions))