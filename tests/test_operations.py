import sqlite3
from src import models, operations

from tests.factories import LedgerItemFactory
import pytest


def test_store_ledger_items(db: sqlite3.Connection):
    ledger_items = [
        LedgerItemFactory(),
        LedgerItemFactory(),
    ]
    operations.store_ledger_items(ledger_items, db=db)

    result = db.execute('SELECT * FROM ledger_items')
    print(result)


# pytest fixture to create a temporary database
@pytest.fixture
def db():
    db_path = ':memory:'
    # open sqlite database
    with sqlite3.connect(db_path) as conn:
        init_db(conn)
        yield conn


def init_db(conn):
    # create tables if they don't exist
    conn.execute('''
        CREATE TABLE IF NOT EXISTS ledger_items (
            id INTEGER PRIMARY KEY,
            tx_date DATE,
            tx_datetime DATETIME,
            amount DECIMAL,
            currency TEXT,
            description TEXT,
            account TEXT,
            ledger_item_type TEXT
        )''')
