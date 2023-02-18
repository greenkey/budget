from decimal import Decimal

from src import sqlite
from src.repo_ledger import LedgerItems
from tests import factories


def test_insert_ledger_item(tmp_path):
    ledger_item = factories.LedgerItemFactory()
    db_path = f"{tmp_path}/test.db"
    repo = LedgerItems(db_path)
    repo.insert(ledger_item)

    with sqlite.db_context(db_path) as db:
        [result] = sqlite.query("SELECT * FROM ledger_items", db=db)
        assert result["tx_id"] == ledger_item.tx_id
        assert result["tx_date"] == ledger_item.tx_date.isoformat()
        assert result["tx_datetime"] == ledger_item.tx_datetime.strftime("%Y-%m-%d %H:%M:%S")
        assert result["amount"] == str(ledger_item.amount)
        assert result["currency"] == ledger_item.currency
        assert result["description"] == ledger_item.description
        assert result["account"] == ledger_item.account.value
        assert result["ledger_item_type"] == ledger_item.ledger_item_type.value
