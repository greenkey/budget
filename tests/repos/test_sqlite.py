import datetime

from src import models
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
        assert result[i]["tx_datetime"] == ledger_item.tx_datetime.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        assert result[i]["amount"] == str(ledger_item.amount)
        assert result[i]["currency"] == ledger_item.currency
        assert result[i]["description"] == ledger_item.description
        assert result[i]["account"] == ledger_item.account
        assert result[i]["ledger_item_type"] == ledger_item.ledger_item_type.value


def test_set_augmented_data(db):
    ledger_item = factories.LedgerItemFactory()
    repo = LedgerItemRepo(db)
    repo.set_augmented_data([ledger_item.augmented_data])

    [result] = list(query("SELECT * FROM augmented_data", db=db))
    assert result["tx_id"] == ledger_item.tx_id
    assert result["amount_eur"] == str(ledger_item.augmented_data.amount_eur)
    assert result["counterparty"] == ledger_item.augmented_data.counterparty
    assert result["category"] == ledger_item.augmented_data.category
    assert result["sub_category"] == ledger_item.augmented_data.sub_category
    assert result["event_name"] == ledger_item.augmented_data.event_name


def test_update_augmented_data(db):
    ledger_item = factories.LedgerItemFactory()
    repo = LedgerItemRepo(db)
    repo.set_augmented_data([ledger_item.augmented_data])

    new_values = models.AugmentedData(
        tx_id=ledger_item.tx_id,
        amount_eur=ledger_item.augmented_data.amount_eur + 1,
    )
    repo.set_augmented_data([new_values])

    [result] = list(query("SELECT * FROM augmented_data", db=db))
    assert result["tx_id"] == ledger_item.tx_id
    assert result["amount_eur"] == str(new_values.amount_eur)
    assert result["counterparty"] == ledger_item.augmented_data.counterparty
    assert result["category"] == ledger_item.augmented_data.category
    assert result["sub_category"] == ledger_item.augmented_data.sub_category
    assert result["event_name"] == ledger_item.augmented_data.event_name


def test_filter_by_date_gte(db):
    repo = LedgerItemRepo(db)

    ledger_items = []
    for month in range(1, 13):
        ledger_items.append(
            factories.LedgerItemFactory(tx_datetime=f"2020-{month:02d}-01 12:00:00")
        )
    repo.insert(ledger_items)

    result = list(repo.filter(tx_datetime__gte=datetime.date(2020, 5, 1)))
    result = list(repo.filter(tx_datetime__gte=datetime.date(2020, 5, 1)))

    assert len(result) == 8
    assert all(
        ledger_item.tx_datetime >= datetime.datetime(2020, 5, 1, 0)
        for ledger_item in result
    )


def test_filter_by_isnull(db):
    repo = LedgerItemRepo(db)

    ledger_items = []
    for i in range(10):
        if i % 2 == 0:
            ledger_items.append(factories.LedgerItemFactory())
        else:
            ledger_items.append(
                factories.LedgerItemFactory(augmented_data__category=None)
            )
    repo.insert(ledger_items)

    result = list(repo.filter(category__isnull=True))

    assert len(result) == 5
    assert set(
        ledger_item.tx_id
        for ledger_item in result
        if ledger_item.augmented_data.category is None
    ) == {
        ledger_item.tx_id
        for ledger_item in ledger_items
        if ledger_item.augmented_data.category is None
    }


def test_insert_when_pulling(db):
    ledger_items = [factories.LedgerItemFactory() for _ in range(3)]
    repo = LedgerItemRepo(db)
    repo.insert(ledger_items)

    result = list(query("SELECT * FROM ledger_items", db=db))
    assert len(result) == 3
