import requests
import datetime
import json
import pandas as pd

# Lista negra de Tokens con los que no operar. Descartaremos los stablecoin.
TOKEN_BLACKLIST = ["usd", "tether", "dai", "usd-coin", "binance-usd"]


def get_top_crypto(rank: int = 12, market_cap_limit: int = 1500000000):
    response = requests.request(
        "GET", "http://api.coincap.io/v2/assets", headers={}, data={"offset": 0}
    )
    data = json.loads(response.text)
    df_data = pd.json_normalize(data["data"])
    df_data = df_data[~df_data["id"].isin(TOKEN_BLACKLIST)]
    df_data["marketCapUsd"] = df_data["marketCapUsd"].astype("float")
    df_data["volumeUsd24Hr"] = df_data["volumeUsd24Hr"].astype("float")
    # Rank assets by biggest volume and upper limit mkcap
    df_data = df_data[df_data["marketCapUsd"] > market_cap_limit].sort_values(
        by=["volumeUsd24Hr"], ascending=False
    )
    return df_data.iloc[0:rank]["id"]


def get_price_changes(df, timeframe: int = 12, sort: bool = True):
    df.to_list()

    actual_timestamp = round(datetime.datetime.now().timestamp() * 1000)
    last_6hours_timestamp = datetime.datetime.now() - datetime.timedelta(
        hours=timeframe
    )
    last_6hours_timestamp = round(last_6hours_timestamp.timestamp() * 1000)

    price_url = (
        "http://api.coincap.io/v2/assets/{}/history?interval=h1&start={}&end={}"
    )

    price_change = {}
    for token in df.to_list():
        response = requests.request(
            "GET",
            price_url.format(token, last_6hours_timestamp, actual_timestamp),
            headers={},
            data={},
        )
        text = response.text
        data = json.loads(text)
        df_data_value = pd.json_normalize(data["data"])
        df_data_value["priceUsd"] = df_data_value["priceUsd"].astype("float")
        first_datapoint = df_data_value.iloc[0]["priceUsd"]
        last_datapoint = df_data_value.iloc[-1]["priceUsd"]
        increase = last_datapoint - first_datapoint
        # print(f"First datapoint: {first_datapoint} Last datapoint: {last_datapoint} Increase: {increase}")
        value_change = (increase / abs(first_datapoint)) * 100
        if value_change > 0:
            price_change[token] = value_change
    if sort:
        price_change = {
            k: v
            for k, v in sorted(
                price_change.items(), key=lambda item: item[1], reverse=True
            )
        }
    return list(price_change.keys())
