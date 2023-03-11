import datetime
from decimal import Decimal

from src import models
from tests import factories


def test_creating_from_dict():
    tx_dict = {
        "tx_id": "jhgfdcvbnjuygfv",
        "tx_date": "2021-01-01",
        "tx_datetime": "2021-01-01 12:00:00",
        "amount": "12.34",
        "currency": "EUR",
        "description": "test",
        "account": "Bank",
        "ledger_item_type": "transfer",
        "event_name": "test",
        "counterparty": "test",
        "category": "test",
        "labels": "test",
    }
    tx = models.LedgerItem(**tx_dict)

    assert tx.tx_id == "jhgfdcvbnjuygfv"
    assert tx.tx_date == datetime.date(2021, 1, 1)
    assert tx.tx_datetime == datetime.datetime(2021, 1, 1, 12, 0, 0)
    assert tx.amount == Decimal("12.34")
    assert tx.ledger_item_type == models.LedgerItemType.TRANSFER


def test_to_dict():
    tx = factories.LedgerItemFactory()
    tx_dict = models.asdict(tx)
    assert tx_dict["tx_date"] == tx.tx_date.isoformat()
    assert tx_dict["tx_datetime"] == tx.tx_datetime.strftime("%Y-%m-%d %H:%M:%S")
    assert tx_dict["amount"] == str(tx.amount)
    assert tx_dict["currency"] == tx.currency
    assert tx_dict["description"] == tx.description
    assert tx_dict["account"] == tx.account
    assert tx_dict["ledger_item_type"] == tx.ledger_item_type.value
    assert tx_dict["event_name"] == tx.event_name
    assert tx_dict["counterparty"] == tx.counterparty
    assert tx_dict["category"] == tx.category
    assert tx_dict["labels"] == tx.labels
