import os
import argparse

from crypto_bot.transactions import (
    get_open_positions,
    get_current_balance,
    evaluate_sell_positions,
    INITIAL_BALANCE,
)


def main():
    """
    Llevar trackeados 3 ficheros:
    - Balance: balance acumulado de la cuenta tras cada liquidación
    - Posiciones abiertas: posiciones abiertas de tokens
    - Historico de transacciones: token, fecha de compra, valor en usd, cantidad
    """

    positions = get_open_positions()

    # check position prices
    # if above limit, move stop and new limit
    current_balance = get_current_balance()
    evaluate_sell_positions(positions, current_balance)
