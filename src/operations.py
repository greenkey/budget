import sqlite3
from typing import Iterable
from src import data


def store_ledger_items(ledger_items: Iterable[data.LedgerItem], db: sqlite3.Connection) -> None:
    """
    Store the ledger items in the database
    """
    # TODO: if no db is passed, use the default one
    # bulk insert the ledger items
    db.executemany('''
        INSERT INTO ledger_items (
            tx_date,     tx_datetime,    amount,         currency,   description,    account,    ledger_item_type
        ) VALUES (
            :tx_date,    :tx_datetime,   :amount,        :currency,  :description,   :account,   :ledger_item_type
        )
    ''', map(data.asdict, ledger_items))
