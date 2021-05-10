import os
import argparse

from crypto_bot.transactions import (
    get_open_positions,
    get_current_balance,
    reset_balance,
    reset_positions,
    reset_transactions,
    evaluate_positions,
    INITIAL_BALANCE,
)


def main():
    """
    Llevar trackeados 3 ficheros:
    - Balance: balance acumulado de la cuenta tras cada liquidación
    - Posiciones abiertas: posiciones abiertas de tokens
    - Historico de transacciones: token, fecha de compra, valor en usd, cantidad
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", dest="reset", action="store_true")
    parser.set_defaults(reset=False)

    args = parser.parse_args()

    if args.reset:
        print("Reset...")
        reset_balance()
        reset_transactions()
        reset_positions()
        current_balance = INITIAL_BALANCE
    else:
        positions = get_open_positions()
        current_balance = get_current_balance()
        evaluate_positions(positions, current_balance)
