from src.ledger_repos.sqlite import DuplicateStrategy, LedgerItemRepo, query
from tests import factories


def test_insert_ledger_item(db):
    ledger_items = [factories.LedgerItemFactory() for _ in range(3)]
    repo = LedgerItemRepo(db)
    repo.insert(ledger_items)

    result = list(query("SELECT * FROM ledger_items", db=db))
    assert len(result) == 3
    for i, ledger_item in enumerate(ledger_items):
        assert result[i]["tx_id"] == ledger_item.tx_id
        assert result[i]["tx_date"] == ledger_item.tx_date.isoformat()
        assert result[i]["tx_datetime"] == ledger_item.tx_datetime.strftime("%Y-%m-%d %H:%M:%S")
        assert result[i]["amount"] == str(ledger_item.amount)
        assert result[i]["currency"] == ledger_item.currency
        assert result[i]["description"] == ledger_item.description
        assert result[i]["account"] == ledger_item.account
        assert result[i]["ledger_item_type"] == ledger_item.ledger_item_type.value


def test_insert_when_importing_files(db):
    ledger_items = [factories.LedgerItemFactory() for _ in range(3)]
    repo = LedgerItemRepo(db)
    repo.insert(ledger_items, duplicate_strategy=DuplicateStrategy.SKIP)

    result = list(query("SELECT * FROM ledger_items", db=db))
    assert len(result) == 3
    assert {item["to_sync"] for item in result} == {True}


def test_insert_when_pulling(db):
    ledger_items = [factories.LedgerItemFactory() for _ in range(3)]
    repo = LedgerItemRepo(db)
    repo.insert(ledger_items, duplicate_strategy=DuplicateStrategy.REPLACE)

    result = list(query("SELECT * FROM ledger_items", db=db))
    assert len(result) == 3
    assert {item["to_sync"] for item in result} == {False}


def test_update(db):
    ledger_items = [factories.LedgerItemFactory() for _ in range(3)]
    repo = LedgerItemRepo(db)
    repo.insert(ledger_items)

    item_to_update = ledger_items[0]
    item_to_update.counterparty = "new counterparty"
    item_to_update.category = "new category"
    item_to_update.labels = "new labels"
    repo.update(item_to_update)

    result = list(query("SELECT * FROM ledger_items", db=db))
    assert len(result) == 3
    for item in result:
        if item["tx_id"] == item_to_update.tx_id:
            assert item["counterparty"] == item_to_update.counterparty
            assert item["category"] == item_to_update.category
            assert item["labels"] == item_to_update.labels
            assert item["to_sync"] == True
        else:
            assert item["to_sync"] == False


def test_get_updated_data_by_month(db):
    ledger_items = [factories.LedgerItemFactory() for _ in range(3)]
    repo = LedgerItemRepo(db)
    repo.insert(ledger_items)

    item_to_update = ledger_items[0]
    item_to_update.counterparty = "new counterparty"
    item_to_update.category = "new category"
    item_to_update.labels = "new labels"
    repo.update(item_to_update)

    result = list(repo.get_updated_data_by_month())
    assert len(result) == 1
    month, [record] = result[0]
    assert month == item_to_update.tx_date.strftime("%Y-%m")
    assert record.tx_id == item_to_update.tx_id
