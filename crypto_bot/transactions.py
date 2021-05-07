import json
import datetime

import requests

from crypto_bot.crypto import get_price_changes, get_top_crypto
from crypto_bot.aws import S3

# Lista negra de Tokens con los que no operar. Descartaremos los stablecoin.
TOKEN_BLACKLIST = ["usd", "tether", "dai"]
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

    current_balance = None
    obj = S3.get_object(BUCKET_NAME, BALANCE_PATH)

    for line in obj["Body"].iter_lines():
        current_balance = line

    if current_balance is not None:
        current_balance = int(current_balance)

    else:
        current_balance = INITIAL_BALANCE
    print(f"Current balance is: {current_balance}")

    return current_balance


def get_open_positions():
    print("Getting positions...")
    obj = S3.get_object(BUCKET_NAME, OPEN_POSITIONS_PATH)

    positions = []
    for line in obj["Body"].iter_lines():
        positions.append(line.decode("utf-8"))

    return positions


def update_balance(balance):
    print(f"Updating balance to: {balance}")
    S3.put_object(BUCKET_NAME, BALANCE_PATH, balance)


def register_transaction(token, order, price, amount, timestamp):
    audit = [token, order, price, amount, timestamp]
    print(f"Registering transaction: {audit}")
    S3.append_to_object(BUCKET_NAME, TX_HISTORY_PATH, audit)


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
    timestamp = round(datetime.datetime.now().timestamp() * 1000)
    transaction = [token, price, limit, stop, amount, timestamp]
    print(f"Opening position: {transaction}")
    S3.append_to_object(BUCKET_NAME, OPEN_POSITIONS_PATH, transaction)
    register_transaction(token, "buy", price, amount, timestamp)


def evaluate_positions(positions, current_balance):
    print("Evaluating positions...")

    df = get_top_crypto(rank=20, market_cap_limit=1000000000)
    price_change_rank = get_price_changes(df, timeframe=12)

    n_positions = len(positions)

    if n_positions == 0:
        print("Opening 2 positions...")
        open_position(price_change_rank[0], current_balance / 2)
        open_position(price_change_rank[1], current_balance / 2)
        update_balance(0)
    if n_positions == 1:
        print("Opening 1 positions...")
        for position in price_change_rank:
            if position not in "".join(positions):
                open_position(position, current_balance)
                break
        update_balance(0)
    if n_positions == 2:
        print("Waiting till next execution...")
