from src import sqlite
from src.repo_ledger import LedgerItemRepo
from tests import factories


def test_insert_ledger_item(tmp_path):
    ledger_item = factories.LedgerItemFactory()
    db_path = f"{tmp_path}/test.db"
    repo = LedgerItemRepo(db_path)
    repo.insert([ledger_item])

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


def test_multiple_insert_ledger_item(tmp_path):
    ledger_items = [factories.LedgerItemFactory() for _ in range(3)]
    db_path = f"{tmp_path}/test.db"
    repo = LedgerItemRepo(db_path)
    repo.insert(ledger_items)

    with sqlite.db_context(db_path) as db:
        result = list(sqlite.query("SELECT * FROM ledger_items", db=db))
        assert len(result) == 3
        for i, ledger_item in enumerate(ledger_items):
            assert result[i]["tx_id"] == ledger_item.tx_id
            assert result[i]["tx_date"] == ledger_item.tx_date.isoformat()
            assert result[i]["tx_datetime"] == ledger_item.tx_datetime.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            assert result[i]["amount"] == str(ledger_item.amount)
            assert result[i]["currency"] == ledger_item.currency
            assert result[i]["description"] == ledger_item.description
            assert result[i]["account"] == ledger_item.account.value
            assert result[i]["ledger_item_type"] == ledger_item.ledger_item_type.value
