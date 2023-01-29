import sqlite3
from datetime import date, datetime
from decimal import Decimal

import pytest

from src import migrations, models, operations, query
from tests.factories import LedgerItemFactory


def test_store_ledger_items(db: sqlite3.Connection):
    ledger_items = [
        LedgerItemFactory(),
        LedgerItemFactory(),
    ]
    operations.store_ledger_items(ledger_items, db=db)

    result = query.query("SELECT * FROM ledger_items", db=db)
    assert sorted(
        models.LedgerItem(
            tx_date=date.fromisoformat(item["tx_date"]),
            tx_datetime=datetime.fromisoformat(item["tx_datetime"]),
            amount=Decimal(item["amount"]),
            currency=item["currency"],
            description=item["description"],
            account=models.Account(item["account"]),
            ledger_item_type=models.LedgerItemType(item["ledger_item_type"]),
        )
        for item in result
    ) == sorted(ledger_items)


# pytest fixture to create a temporary database
@pytest.fixture
def db():
    db_path = ":memory:"
    # open sqlite database
    with sqlite3.connect(db_path) as conn:
        migrations.migrate(conn)
        yield conn
